# scikit-build-core Migration Notes

This branch is a proof-of-concept for replacing the old Meson/mesonpep517 build with scikit-build-core and CMake.

## Goal

PSiesta should build its Python extension with CMake while using upstream Siesta's native CMake build directly. The intended integration story is simpler than the old Meson branch: stop maintaining a custom Siesta Meson fork and link against upstream Siesta as a CMake subproject or installed CMake package.

## Current Shape

The POC keeps the existing Python and binding design:

- `psiesta/_psiesta.pyx` remains the Cython layer.
- `psiesta/c_bindings/fpsiesta.f90` remains the small Fortran `bind(c)` shim.
- The shim still calls the historical `fsiesta` API: `siesta_launch`, `siesta_units`, `siesta_forces`, `siesta_get`, and `siesta_quit`.
- The Python API is intentionally unchanged for now.

The new top-level `CMakeLists.txt` currently:

- Enables C and Fortran.
- Finds Python, NumPy, Cython, and MPI.
- Builds `_psiesta` as a Python extension module.
- Fetches upstream Siesta by default with CMake `FetchContent`.
- Allows pointing at an existing Siesta checkout via `PSIESTA_SIESTA_SOURCE_DIR`.
- Allows a future installed-package mode via `PSIESTA_USE_SYSTEM_SIESTA`.

## Siesta Build Defaults

For the subroutine binding POC, the CMake integration sets these Siesta defaults before adding/fetching Siesta:

- `SIESTA_TESTS=OFF`
- `SIESTA_INSTALL=OFF`
- `SIESTA_WITH_MPI=ON`
- `SIESTA_WITH_PEXSI=OFF`
- `SIESTA_SHARED_LIBS=OFF`
- `CMAKE_POSITION_INDEPENDENT_CODE=ON`

The MPI subroutine mode is the relevant one for PSiesta because Siesta is linked into the Python extension rather than contacted through pipes or sockets.

## Build Commands

With build isolation:

```bash
python -m pip wheel . -v
```

Without build isolation, after installing Python build requirements in the active environment:

```bash
python -m pip wheel . -v --no-build-isolation
```

Using an existing Siesta checkout:

```bash
python -m pip wheel . -v -Ccmake.define.PSIESTA_SIESTA_SOURCE_DIR=/path/to/siesta
```

## Current Verification State

The POC reaches CMake when using build isolation. The current host environment does not have a visible Fortran compiler, so configuration stops at:

```text
No CMAKE_Fortran_COMPILER could be found.
```

The next meaningful test needs an environment with a Fortran compiler and MPI compiler wrappers available.

## Expected Next Issues

After a Fortran-capable environment is available, the next integration points to check are:

- The exact upstream Siesta CMake target name for `libsiesta`.
- Whether Siesta's Fortran module include directories propagate to `fpsiesta.f90`.
- Whether minor API updates are needed in `fpsiesta.f90` for current upstream Siesta modules.
- Whether all desired Siesta optional dependencies are discoverable through CMake.
- Whether static linking into the Python extension is clean with MPI and position-independent code.

## Non-Goals For This POC

- Refreshing the Python API.
- Designing a full Python abstraction for FDF input.
- Building redistributable wheels.
- Supporting cross-node MPI packaging.
- Removing Meson files before the CMake path is proven.
