# Build Environment

This repository uses a split build environment:

- Nix provides the native scientific build stack.
- uv manages Python build isolation and Python dependencies from `pyproject.toml`.

This keeps compilers, MPI, BLAS/LAPACK, NetCDF, and other native libraries out of the host system package manager while avoiding duplicated Python dependency metadata in Nix.

## Requirements

Install Nix with flakes enabled. On Linux, daemon mode is recommended even for a single-user workstation because `/nix/store` remains root-owned and builds go through the normal Nix daemon path.

The user does not need to be a trusted Nix user for the commands below.

## Development Shell

Enter the development shell with:

```bash
nix develop
```

Or run one command inside it:

```bash
nix develop -c <command>
```

The shell provides the native build environment from `flake.nix`, including:

- C, C++, and Fortran compilers.
- OpenMPI compiler wrappers, with `CC=mpicc`, `CXX=mpicxx`, and `FC=mpifort`.
- CMake, Ninja, and `pkg-config`.
- BLAS, LAPACK, ScaLAPACK, NetCDF C/Fortran, HDF5, FFTW, libxc, readline, zlib, and curl.
- `uv` for Python dependency resolution and PEP 517 builds.

Check the shell with:

```bash
nix develop -c sh -c 'cc --version && mpicc --version && mpifort --version && cmake --version && uv --version'
```

## Building A Wheel

Build the wheel with:

```bash
nix develop -c uv build --wheel
```

`uv` reads `pyproject.toml`, creates an isolated Python build environment, installs the declared Python build requirements, and calls the scikit-build-core backend. scikit-build-core then configures and builds the CMake project.

By default, the CMake project fetches upstream Siesta and builds it as a subproject. The build output is written under `build/`, and the wheel is written under `dist/`.

## Using An Existing Siesta Checkout

To build against an existing Siesta source checkout instead of fetching it, pass the CMake definition through uv/scikit-build-core:

```bash
nix develop -c uv build --wheel --config-setting=cmake.define.PSIESTA_SIESTA_SOURCE_DIR=/path/to/siesta
```

## Build Artifacts

Expected local artifacts include:

- `build/` for scikit-build-core, CMake, and fetched Siesta build trees.
- `dist/` for generated wheels.
- `~/.cache/uv/` for uv-managed Python build environments and downloads.
- `/nix/store` and `/nix/var/nix` for Nix-managed native dependencies and build metadata.

The Nix-managed system state is garbage-collectable through normal Nix commands. The repository build artifacts can be removed with:

```bash
rm -rf build dist
```
