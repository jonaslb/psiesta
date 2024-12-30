cmake_minimum_required(VERSION 3.26)
project(
    psiesta
    LANGUAGES
        Fortran
        C
        CXX
)

# MPI is required here
find_package(MPI REQUIRED)
# There is something with MPI not always getting included going on,
# adding MPI to system fixes it (and is maybe not too unreasonable?)
include_directories(
    SYSTEM
    ${MPI_INCLUDE_PATH}
    ${MPI_C_INCLUDE_PATH}
    ${MPI_Fortran_INCLUDE_PATH}
)
set(SIESTA_WITH_MPI 1)  # also force-enable in siesta

# Scalapack workarounds (FindSCALAPACK.cmake is full broken in common
# Linux distributions, i.e. will crash cmake)
option(USE_SYSTEM_SCALAPACK "Use system-provided SCALAPACK module" OFF)
if(NOT USE_SYSTEM_SCALAPACK)
    # Custom FindSCALAPACK because the one in common Linux distributions
    # is full broken (will abort cmake early).
    list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/scalapack")
    message(STATUS "Using custom FindSCALAPACK.cmake")
else()
    message(STATUS "Using system-provided SCALAPACK find module")
endif()
find_package(SCALAPACK REQUIRED)

# Now try to mangle those siesta variables...
# Probably not exactly right but I'm not sure there is a right way in general
# set(SCALAPACK_DETECTION 0)
# set(CustomScalapack_FOUND 1)
# set(SL_FLAGS ${SCALAPACK_LDFLAGS})
# list(APPEND SL_FLAGS ${SCALAPACK_CFLAGS})
# list(JOIN SL_FLAGS " " SCALAPACK_LINKER_FLAG)
# set(SCALAPACK_LIBRARY ${SCALAPACK_LINKER_FLAG})

# Shared lib
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
# Flook is documented to be incompatible with being used in shared
# lib. I don't know why but it doesn't work, so disable it.
set(SIESTA_WITH_FLOOK 0)
# Now actually include the SIESTA project
add_subdirectory("subprojects/siesta")

# Fix broken netcdf includes, siesta uses some built-in cmake
# stuff that uses the nf-config tool which is a custom netcdf-specific
# "we have pkgconf at home" type solution, which doesn't work.
# So, just use pkgconf directly...
find_package(PkgConfig REQUIRED)
pkg_check_modules(
    NetCDF_Fortran REQUIRED IMPORTED_TARGET netcdf-fortran
)
target_include_directories(
   SIESTA.libncdf
   PUBLIC
   ${NetCDF_Fortran_INCLUDE_DIRS}
)

# Now the actual code in this repo...
add_library(
    fpsiesta_f90
    STATIC
    "src/psiesta/c_bindings/fpsiesta.f90"
)
# message(FATAL_ERROR MPI_Fortran_LIBRARIES="${MPI_Fortran_LIBRARIES}")
target_link_libraries(
    fpsiesta_f90
    PRIVATE
    SIESTA.libsiesta
    MPI::MPI_C
    MPI::MPI_Fortran
)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
add_custom_command(
    OUTPUT
        ${CMAKE_CURRENT_SOURCE_DIR}/src/psiesta/_psiesta.c
    COMMAND ${Python_EXECUTABLE} -m cython -3
        ${CMAKE_CURRENT_SOURCE_DIR}/src/psiesta/_psiesta.pyx
    WORKING_DIRECTORY
        ${CMAKE_CURRENT_SOURCE_DIR}/src/psiesta
    DEPENDS
        ${CMAKE_CURRENT_SOURCE_DIR}/src/psiesta/_psiesta.pyx
)
add_compile_definitions(NPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION)
set_source_files_properties(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/psiesta/_psiesta.c
    PROPERTIES LANGUAGE CXX
)
python_add_library(
    psiesta_comp_lib
    MODULE
    ${CMAKE_CURRENT_SOURCE_DIR}/src/psiesta/_psiesta.c
)
target_link_libraries(
    psiesta_comp_lib
    PRIVATE
    fpsiesta_f90
    Python::Module
)
# add_executable(
#     scalapacktest
#     scalapacktest.f90
# )
# target_link_libraries(
#     scalapacktest
#     PRIVATE
#     SCALAPACK::SCALAPACK
# )