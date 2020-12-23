#!/usr/bin/env mpirun -n 4 python3 -m mpi4py
"""
A "slow" test to see if it works and also judge performance a bit.
On a AMD 1600X this file (see shebang) runs in about :
- 109s with O0 march=native
- 54 s with O1 march=native
- 49-50s with O2 march=native
- low 49s with O3 march=native
- 49-50s with O3 march=native funroll-loops
Also tried some other loop related options but basically I don't think they give anything. O3 is fine.
(march=native is also no big deal, so I've disabled it)
"""
from mpi4py import MPI
import sisl as si
from psiesta import FilePSiesta
import numpy as np
from datetime import datetime
import shutil
import sys
import subprocess as sp
from pathlib import Path

rank = MPI.COMM_WORLD.rank

if rank == 0:
    sp.run(['zstd', '-d', '-f', 'C.psf.zst'])

t0 = datetime.now()

g = si.geom.graphene().tile(5, 0).tile(5, 1)
fdf = """
TS.HS.Save True
SolutionMethod diagon
PAO.BasisSize SZP
"""
calc = FilePSiesta(fdf, '.', 'tenbyten', geometry=g)
calc.run()
g.xyz[25, 2] += 0.03
calc.run()
del calc

t1 = datetime.now()

if rank == 0:
    print(f"Time taken: {t1-t0}")
    if "keep" not in sys.argv:
        shutil.rmtree('tenbyten')
    Path('C.psf').unlink()