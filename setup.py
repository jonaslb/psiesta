#!/usr/bin/env python3
"""PSiesta: Siesta as a Python library
To build/install, please follow these instructions:
0. Have intel compiler and mkl: The linking is not setup to work with foss (yet)
1. Compile the 'SiestaSubroutine' library in your Siesta Obj dir: `make lib`
2. OBJ=/my/libraries/siesta/Obj ./setup.py install [--user] [--prefix=<prefix>]
"""
import setuptools  # noqa
from distutils.core import setup
from distutils.extension import Extension
from pathlib import Path
from Cython.Build import cythonize
import numpy as np
from contextlib import contextmanager
import os
import subprocess as sp
from itertools import chain
import sys


SIESTAOBJ = os.environ.get("OBJ")
if SIESTAOBJ is None or SIESTAOBJ == "":
    raise ValueError("You must specify the siesta obj dir (OBJ=/my/siesta/Obj python3 setup.py...)")
SIESTAOBJ = Path(SIESTAOBJ)


@contextmanager
def cd(where):
    old = Path.cwd()
    os.chdir(where)
    yield
    os.chdir(old)


args = \
    "-qopenmp -lmkl_intel_thread -lmkl_core -lmkl_intel_lp64 -lmkl_blas95_lp64 "\
    "-lmkl_lapack95_lp64 -lmkl_scalapack_lp64 -lmkl_blacs_intelmpi_lp64 -lnetcdff -lnetcdf "\
    "-lhdf5_fortran -lhdf5 -lz -lmkl_avx512 -lmkl_def "

siestalib = "libSiestaForces.a libfdf.a libwxml.a libxmlparser.a MatrixSwitch.a libSiestaXC.a "\
            "libmpi_f90.a libncdf.a libfdict.a"
siestalib = [str(SIESTAOBJ/t) for t in siestalib.split(" ")]


def build_fortran():
    # TODO: Make this nice and all? Like the cython extension
    with cd(Path(__file__).parent/"psiesta"/"c_bindings"):
        cmd = f"mpiifort -fPIC -c -O3 -xHost -I{SIESTAOBJ!s}/ -fp-model source -qopenmp -o fpsiesta.o fpsiesta.f90"
        print(cmd)
        sp.run(cmd, shell=True, check=True)


build_fortran()

cythonmods = cythonize([
    Extension(
        'psiesta._psiesta',
        ['psiesta/_psiesta.pyx'],
        extra_compile_args=['-fPIC', '-O3', '-xHost', "-qopenmp"],
        # TODO: In gcc use -lgfortran instead of ifcore
        libraries=["ifcore"] + [lib[2:] for lib in args.split(" ") if lib.startswith("-l")],
        extra_objects=["psiesta/c_bindings/fpsiesta.o"] + siestalib,
        include_dirs=[str(SIESTAOBJ)],
    )
])

setup(
    name="psiesta",
    include_dirs=[np.get_include()],
    ext_modules=cythonmods,
    zip_safe=False,
    install_requires=[
        "numpy",
        "mpi4py",
    ],
    packages=['psiesta'],
    version='0.1',
    description='Siesta as a Python library',
    author="Jonas Lundholm Bertelsen",
    url="https://github.com/jonaslb/psiesta",
    license="GPLv3+",
)
