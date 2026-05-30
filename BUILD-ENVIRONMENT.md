# Build Environment Notes

This project needs a substantial native scientific build stack to build upstream Siesta and the PSiesta extension. The goal is to avoid installing that stack globally with the system package manager.

## Preferred Direction: Nix Dev Shell

The preferred direction is to use Nix for the native build environment while keeping `pyproject.toml` as the source of truth for the Python package.

Nix should provide:

- C, C++, and Fortran compilers.
- CMake and Ninja.
- `pkg-config`.
- MPI, likely OpenMPI for local multi-process runs.
- BLAS, LAPACK, and ScaLAPACK.
- NetCDF C and Fortran.
- Siesta optional libraries such as libxc, libpsml, libfdf, xmlf90, libgridxc, and FFTW where available.
- Python plus build-time Python tools such as `pip`, `scikit-build-core`, `cython`, and `numpy`.

The agent can work naturally with this setup by prefixing commands with `nix develop -c`, for example:

```bash
nix develop -c python -m pip wheel . -v --no-build-isolation
nix develop -c python -m pip install -v --no-build-isolation -e .
```

This keeps the normal repository filesystem and avoids container bind-mount or shell-attach friction.

## Nix Staging Plan

Use Nix in two stages.

Stage 1: development shell only.

Nix supplies native dependencies and Python build tools. PSiesta itself is still built by pip/scikit-build-core from `pyproject.toml`.

Stage 2: full Nix packaging if useful.

Once the CMake build works, Siesta and PSiesta can optionally become proper Nix derivations for stronger reproducibility. This is more work and should not block the POC.

## Python Dependency Duplication

Avoid duplicating runtime Python dependencies in the environment definition where possible. Runtime dependencies belong in `pyproject.toml`.

For the initial Nix shell, only duplicate Python packages required to build without isolation:

- `scikit-build-core`
- `cython`
- `numpy`
- `pip`

If this still feels too duplicated, an alternative is to let Nix provide native libraries plus `uv`, then let `uv` resolve the Python dependencies from `pyproject.toml`.

## Siesta Source Strategy

Initially, let PSiesta's CMake build fetch upstream Siesta with `FetchContent`. This is convenient for proving the integration.

Later, if stricter reproducibility is desired, Siesta can be provided by Nix instead:

- As a fixed source input.
- As a Nix-built CMake package.
- As a source path passed to PSiesta with `PSIESTA_SIESTA_SOURCE_DIR`.

## Why Not Containers First

Containers remain a reasonable fallback, but they are less convenient for this POC:

- The agent must run commands through the container boundary.
- Build paths and caches are more awkward.
- MPI can work locally in containers, but host integration can become fiddly.
- Editing on the host while building in a container is workable but less direct than a Nix shell.

## Why Not Conda/Pixi First

Conda-forge likely has many of the required scientific packages, and pixi would be practical. However, this project prefers avoiding conda-style environment management and duplicated dependency metadata. Nix is a better match for a clean native toolchain shell while keeping Python packaging metadata in `pyproject.toml`.

## Immediate Need

The current host lacks a visible Fortran compiler. The first useful environment milestone is a shell where these commands work:

```bash
cc --version
mpicc --version
mpifort --version
cmake --version
python -c "import numpy; print(numpy.get_include())"
```

Once that is available, rerun the scikit-build-core POC from inside the environment.
