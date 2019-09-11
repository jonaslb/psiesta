#!/usr/bin/env python3
"""PSiesta: Siesta as a Python library
To build/install, please follow these instructions:
1. Compile siesta and the 'SiestaSubroutine' library in your Siesta Obj dir: `make siesta lib`
2. OBJ=/my/libraries/siesta/Obj ./setup.py install [--user] [--prefix=<prefix>]
setup.py will use the Makefile in your Obj dir to decide compilation flags, includes, etc.
It is necessary that externally linked libraries, eg. Flook, if used, is compiled with -fPIC.
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
import re


# args = \
#     "-qopenmp -lmkl_intel_thread -lmkl_core -lmkl_intel_lp64 -lmkl_blas95_lp64 "\
#     "-lmkl_lapack95_lp64 -lmkl_scalapack_lp64 -lmkl_blacs_intelmpi_lp64 -lnetcdff -lnetcdf "\
#     "-lhdf5_fortran -lhdf5 -lz -lmkl_avx512 -lmkl_def "
#
# siestalib = "libSiestaForces.a libfdf.a libwxml.a libxmlparser.a MatrixSwitch.a libSiestaXC.a "\
#             "libmpi_f90.a libncdf.a libfdict.a"
# siestalib = [str(SIESTAOBJ/t) for t in siestalib.split(" ")]


BUILD_ANY_ARG = {"build", "install", "bdist", "develop"}
if any(x in cmd.lower() for cmd in sys.argv for x in BUILD_ANY_ARG):
    BUILD = True


@contextmanager
def cd(where):
    old = Path.cwd()
    os.chdir(where)
    yield
    os.chdir(old)


def startswith(search, what):
    match = re.search(r'\s+'.join(what.split()), search)
    return match is not None


def get_build_args(objdir):
    p = sp.run("make --dry-run siesta.o", shell=True, universal_newlines=True, stdout=sp.PIPE,
               check=True, cwd=objdir)
    line = next(l for l in p.stdout.split("\n") if "siesta.F" in l and "-c " in l)
    args = line.split()
    mpifort = args[0]
    compile_args = list(filter(
        # eg. -fopenmp -fexpensive-optimizations -qopenmp -DMPI -march=native -xHost -O3
        lambda a: any(a.startswith(x) for x in ("-f", "-q", "-D", "-m", "-x", "-O")), args
    ))
    includes = list(filter(lambda a: a.startswith("-I"), args))
    return mpifort, compile_args, [f"-I{SIESTAOBJ!s}/"] + includes


def get_link_args(objdir, compiler):
    p = sp.run("make --dry-run siesta", shell=True, universal_newlines=True, stdout=sp.PIPE,
               check=True, cwd=objdir)
    output = p.stdout.split("\n")
    linestart = next(i for i, l in enumerate(output) if startswith(l, f"{compiler} -o siesta\\s"))
    for i, l in enumerate(output[linestart:]):
        if not l.endswith("\\"):
            break
    lineend = linestart + i + 1
    args = "\n".join(output[linestart:lineend]).replace("\\\n", " ").split()
    libpath = list(filter(lambda a: a.startswith("-L"), args))
    runlibpath = list(filter(lambda a: a.startswith("-Wl,-rpath="), args))
    libs = list(filter(lambda a: a.startswith("-l"), args))
    siestalibs = ["libSiestaForces.a"] + list(filter(lambda a: a.endswith(".a"), args))
    return libpath, runlibpath, libs, siestalibs


def ensure_build_fsiesta(objdir):
    libf = objdir / "libSiestaForces.a"
    if not libf.is_file():
        sp.run("make lib", shell=True, check=True, cwd=objdir)


def build_fortran(compiler, c_args, includes):
    # TODO: Always builds inplace, maybe monkey the Cython extension some more? (avoid building until setup())
    # -fp-model source?
    cmd = f"{compiler} -c {' '.join(c_args)} {' '.join(includes)} -o fpsiesta.o fpsiesta.f90"
    print(cmd)
    sp.run(cmd, shell=True, check=True, cwd=Path(__file__).parent/"psiesta"/"c_bindings")


extargs = dict(
    name='psiesta._psiesta',
    sources=['psiesta/_psiesta.pyx']
)
if BUILD:
    SIESTAOBJ = os.environ.get("OBJ")
    if SIESTAOBJ is None or SIESTAOBJ == "":
        raise ValueError("You must specify the siesta obj dir (OBJ=/my/siesta/Obj python3 setup.py...)")
    SIESTAOBJ = Path(SIESTAOBJ).resolve()
    ensure_build_fsiesta(SIESTAOBJ)

    fc, comp_args, includes = get_build_args(SIESTAOBJ)
    if "-fp-model" in comp_args:
        # intel argument. works fine without it. it needs a second argument that we aren't parsing
        del comp_args[comp_args.index("-fp-model")]
    print(f"DETECTED FC: {fc}")
    print(f"DETECTED compiler args: {comp_args}")
    print(f"DETECTED includes: {includes}")
    build_fortran(fc, comp_args, includes)
    fortranlib = dict(
        ifort="ifcore", mpiifort="ifcore"
    ).get(fc, "gfortran")
    lpaths, runlibpaths, libs, siestalibs = get_link_args(SIESTAOBJ, fc)
    lpprint = '\n'.join(lpaths)
    print(f"DETECTED lpaths=[multiline][\n{lpprint}\n]")
    lpprint = '\n'.join(runlibpaths)
    print(f"DETECTED runpaths=[multiline][\n{lpprint}\n]")
    print(f"DETECTED libs={libs}")
    print(f"DETECTED siestalibs={siestalibs}")
    extargs.update(dict(
        extra_compile_args=comp_args,
        library_dirs=[l[2:] for l in lpaths],
        runtime_library_dirs=[r[11:] for r in runlibpaths],
        libraries=[fortranlib] + [l[2:] for l in libs],
        extra_objects=["psiesta/c_bindings/fpsiesta.o"] + [str(SIESTAOBJ/l) for l in siestalibs],
        include_dirs=[i[2:] for i in includes]
    ))

cythonmods = cythonize([Extension(**extargs)])

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
