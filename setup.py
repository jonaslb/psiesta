#!/usr/bin/env python3
""" PSiesta: Siesta as a Python library
To install, please follow these instructions:
1. Compile the 'SiestaSubroutine' library in your Siesta Obj dir: `make lib`
2. OBJ=/my/libraries/siesta/Obj ./setup.py install [--user] [--prefix=/custom/prefix/]
"""
import setuptools  # noqa
from distutils.core import setup
from distutils.extension import Extension
from pathlib import Path
from Cython.Distutils import build_ext
import numpy as np
from contextlib import contextmanager
import os
import subprocess as sp
from itertools import chain


# 1. in your siesta obj dir: `make lib`
# 2. OBJ=/my/siesta/Obj/ FC=mpiifort ./setup.py

# Need to $FC -o fpsiesta.a -c psiesta/c_bindings/fpsiesta.f90 $OBJ/{libSiestaForces.a,*.mod}
# then $CC -shared -pthread -fPIC -fwrapv -O2 -Wall -fno-strict-aliasing  -I/usr/include/python3.7\
# -o _psiesta.so _psiesta/psiesta.c psiesta/c_bindings/fpsiesta.a -lgfortran
# possibly -lifcore for intel (other flags i dont know)

SIESTAOBJ = Path(os.environ.get("OBJ"))
if SIESTAOBJ == Path(""):
    raise ValueError("You must specify the siesta obj dir")


@contextmanager
def cd(where):
    old = Path.cwd()
    os.chdir(where)
    yield
    os.chdir(old)


args = \
    "-qopenmp -lmkl_intel_thread -lmkl_core -lmkl_intel_lp64 -lmkl_blas95_lp64 "\
    "-lmkl_lapack95_lp64 -lmkl_scalapack_lp64 -lmkl_blacs_intelmpi_lp64 -lnetcdff -lnetcdf "\
    "-lhdf5_fortran -lhdf5 -lz "

test = "libSiestaForces.a libfdf.a libwxml.a libxmlparser.a MatrixSwitch.a libSiestaXC.a libmpi_f90.a libncdf.a libfdict.a"
test = [str(SIESTAOBJ/t) for t in test.split(" ")]

def build_fortran():
    with cd(Path(__file__).parent/"psiesta"/"c_bindings"):
        cmd = f"mpiifort -fPIC -c -O3 -xHost -I{SIESTAOBJ!s}/ -fp-model source -qopenmp -o fpsiesta.o fpsiesta.f90"
        print(cmd)
        sp.run(cmd, shell=True, check=True)
        cmd = f"mpiifort -fPIC -O3 -xHost -I{SIESTAOBJ!s}/ -o fpsiesta.a fpsiesta.o "
        fmods = chain(SIESTAOBJ.glob("*.a"),)  # SIESTAOBJ.glob("*.mod")
        fmods = test
        # lets see if -l{all the libs} is necessary or what
        cmd += " ".join(str(fmod) for fmod in fmods)
        cmd += " " + args
        print(cmd)
        sp.run(cmd, shell=True, check=True)


ext_modules = [
    Extension(
        '_psiesta',  # name
        ['psiesta/_psiesta.pyx'],  # source
        # other compile args for the compiler (icc for now)
        extra_compile_args=['-fPIC', '-O3', '-xHost', "-qopenmp"],
        # other files to link to
        # extra_link_args=["psiesta/c_bindings/fpsiesta.a"],
        # i think! needed -lgfortran at least
        libraries=["ifcore"] + [lib[2:] for lib in args.split(" ") if lib.startswith("-l")],
        extra_objects=["psiesta/c_bindings/fpsiesta.a"],
        include_dirs=[str(SIESTAOBJ)],
    )
]

build_fortran()

setup(
    name="psiesta",
    cmdclass={'build_ext': build_ext},
    include_dirs=[np.get_include()],
    ext_modules=ext_modules,
)
