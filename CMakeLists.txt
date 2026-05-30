cmake_minimum_required(VERSION 3.20)

project(
  PSiesta
  VERSION 0.3.0
  LANGUAGES C Fortran
)

include(FetchContent)
include(GNUInstallDirs)

option(PSIESTA_FETCH_SIESTA "Fetch/build Siesta as a CMake subproject" ON)
option(PSIESTA_USE_SYSTEM_SIESTA "Use an installed Siesta CMake package" OFF)
set(PSIESTA_SIESTA_SOURCE_DIR "" CACHE PATH "Existing Siesta source checkout")
set(PSIESTA_SIESTA_GIT_REPOSITORY "https://gitlab.com/siesta-project/siesta.git" CACHE STRING "Siesta git repository")
set(PSIESTA_SIESTA_GIT_TAG "master" CACHE STRING "Siesta git tag, branch, or commit")

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(MPI REQUIRED COMPONENTS C Fortran)

execute_process(
  COMMAND "${Python_EXECUTABLE}" -c "import numpy; print(numpy.get_include())"
  OUTPUT_VARIABLE NumPy_INCLUDE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)

find_program(CYTHON_EXECUTABLE cython REQUIRED)

if(PSIESTA_USE_SYSTEM_SIESTA)
  find_package(SIESTA CONFIG REQUIRED)
elseif(PSIESTA_SIESTA_SOURCE_DIR)
  set(SIESTA_TESTS OFF CACHE BOOL "" FORCE)
  set(SIESTA_INSTALL OFF CACHE BOOL "" FORCE)
  set(SIESTA_WITH_MPI ON CACHE BOOL "" FORCE)
  set(SIESTA_WITH_PEXSI OFF CACHE BOOL "" FORCE)
  set(SIESTA_SHARED_LIBS OFF CACHE BOOL "" FORCE)
  add_subdirectory("${PSIESTA_SIESTA_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/_deps/siesta-build")
elseif(PSIESTA_FETCH_SIESTA)
  set(SIESTA_TESTS OFF CACHE BOOL "" FORCE)
  set(SIESTA_INSTALL OFF CACHE BOOL "" FORCE)
  set(SIESTA_WITH_MPI ON CACHE BOOL "" FORCE)
  set(SIESTA_WITH_PEXSI OFF CACHE BOOL "" FORCE)
  set(SIESTA_SHARED_LIBS OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(
    siesta
    GIT_REPOSITORY "${PSIESTA_SIESTA_GIT_REPOSITORY}"
    GIT_TAG "${PSIESTA_SIESTA_GIT_TAG}"
  )
  FetchContent_MakeAvailable(siesta)
else()
  message(FATAL_ERROR "Set one of PSIESTA_USE_SYSTEM_SIESTA, PSIESTA_SIESTA_SOURCE_DIR, or PSIESTA_FETCH_SIESTA")
endif()

set(_siesta_target "")
foreach(candidate IN ITEMS SIESTA::libsiesta SIESTA.libsiesta SIESTA-libsiesta siesta.libsiesta siesta-libsiesta)
  if(TARGET "${candidate}")
    set(_siesta_target "${candidate}")
    break()
  endif()
endforeach()
if(NOT _siesta_target)
  message(FATAL_ERROR "Could not find the upstream Siesta libsiesta CMake target")
endif()
message(STATUS "Using Siesta target: ${_siesta_target}")

set(_psiesta_c "${CMAKE_CURRENT_BINARY_DIR}/psiesta/_psiesta.c")
add_custom_command(
  OUTPUT "${_psiesta_c}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/psiesta"
  COMMAND "${CYTHON_EXECUTABLE}" -3 "${CMAKE_CURRENT_SOURCE_DIR}/psiesta/_psiesta.pyx" -o "${_psiesta_c}"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/psiesta/_psiesta.pyx"
  VERBATIM
)

Python_add_library(_psiesta MODULE
  "${_psiesta_c}"
  "${CMAKE_CURRENT_SOURCE_DIR}/psiesta/c_bindings/fpsiesta.f90"
  WITH_SOABI
)

target_include_directories(_psiesta PRIVATE "${NumPy_INCLUDE_DIR}")
target_link_libraries(_psiesta PRIVATE
  "${_siesta_target}"
  MPI::MPI_C
  MPI::MPI_Fortran
)

install(TARGETS _psiesta LIBRARY DESTINATION psiesta)
install(FILES
  "psiesta/__init__.py"
  "psiesta/ase.py"
  "psiesta/psiesta.py"
  DESTINATION psiesta
)
