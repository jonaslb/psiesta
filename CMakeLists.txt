cmake_minimum_required(VERSION 3.26)
project(psiesta Fortran)

find_package(MPI REQUIRED)
include_directories(SYSTEM ${MPI_INCLUDE_PATH})

# Fix broken netcdf includes, siesta uses some built-in cmake
# stuff that uses the nf-config tool which is a custom netcdf-specific
# "we have pkgconfig at home" type solution, which doesn't work.
# So, just use pkg-config directly...
find_package(PkgConfig REQUIRED)
pkg_check_modules(
    NetCDF_Fortran REQUIRED IMPORTED_TARGET netcdf-fortran
)

# Wow, getting Siesta to just fucking use a normal scalapack...
# Imagine writing hundreds of lines of custom package finding code
# and it doesn't work but a simple one-liner would have sufficed..
pkg_check_modules(
    SCALAPACK REQUIRED IMPORTED_TARGET scalapack
)
# The above is perfectly fine but Siesta needs the below instead
set(SCALAPACK_DETECTION 0)
set(CustomScalapack_FOUND 1)
set(SCALAPACK_LIBRARY "scalapack")
set(SL_FLAGS ${SCALAPACK_LDFLAGS})
list(APPEND SL_FLAGS ${SCALAPACK_CFLAGS})
list(JOIN SL_FLAGS " " SCALAPACK_LINKER_FLAG)
# string(REPLACE ";" " " SCALAPACK_LINKER_FLAG "${SCALAPACK_LDFLAGS}")
# set(SCALAPACK_LINKER_FLAG ${SCALAPACK_LDFLAGS_STR})
message(SCALAPACK_LINKER_FLAG= "${SCALAPACK_LINKER_FLAG}")
# message(INFO SCALAPACK_LIBRARY "${SCALAPACK_LIBRARY}")
# message(INFO SCALAPACK_LINKER_FLAG "${SCALAPACK_LINKER_FLAG}")

set(SIESTA_WITH_MPI 1)
add_subdirectory("subprojects/siesta")

target_include_directories(
   SIESTA.libncdf
   PUBLIC
   ${NetCDF_Fortran_INCLUDE_DIRS}
)

# Todo: now just build the local F, the pyx to C and finally compile C..
# and find out how to make it all work as python module!

# According to skbuild core docs..
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
add_library(
    fpsiesta_f90
    STATIC
    "src/psiesta/c_bindings/fpsiesta.f90"
)
target_link_libraries(
    fpsiesta_f90
    PRIVATE
    SIESTA.libsiesta
    ${MPI_C_LIBRARIES}
)
