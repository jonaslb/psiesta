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


def build_fortran():
    with cd(Path(__file__)/"psiesta"/"c_bindings"):
        cmd = f"mpiifort -fPIC -O3 -xHost -o fpsiesta.a -c fpsiesta.f90"\
              f"{SIESTAOBJ!s}/libSiestaForces.a "
        fmods = SIESTAOBJ.glob("*.mod")
        # lets see if -l{all the libs} is necessary or what
        cmd += " ".join(str(fmod) for fmod in fmods)
        sp.run(cmd, shell=True)


ext_modules = [
    Extension(
        '_psiesta',  # name
        ['psiesta/_psiesta.pyx'],  # source
        # other compile args for the compiler (icc for now)
        extra_compile_args=['-fPIC', '-O3', '-xHost'],
        # other files to link to
        # extra_link_args=["psiesta/c_bindings/fpsiesta.a"],
        libraries=["ifcore"],  # i think! needed -lgfortran at least
        extra_objects=["psiesta/c_bindings/fpsiesta.a"],
    )
]


setup(
    name="psiesta",
    cmdclass={'build_ext': build_ext},
    include_dirs=[np.get_include()],
    ext_modules=ext_modules,
)
