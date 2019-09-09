# PSiesta: Siesta as a Python library

This repository contains Python bindings for the 'Siesta as a subroutine' functionality in Siesta.
When it works, it should allow you to do things like:

```python
from mpi4py import MPI
import numpy as np
import sisl a si
from psiesta import FSiesta
# Read geometry on all nodes: You can also do it on rank 0 only and broadcast with mpi4py
geometry = si.get_sile("graphene.fdf").read_geometry()
my_run = FSiesta("graphene")  # Start a siesta session with given label.fdf. Uses comm_world by default
energy, forces = my_run.run(geometry.xyz)
print(f"Energy: {energy}. Max force: {np.max(np.linalg.norm(forces, axis=1))}")
# Mutate the geometry and rerun
geometry.xyz[0, 0] += 0.05
energy, forces = my_run.run(geometry.xyz)
my_run.quit()
```
which you should then be able to run with `mpirun -n 4 python3 myscript.py`.
'Siesta as a subroutine' has the ability to get other properties, but the bindings are not made yet.

Perhaps in the future this repository could evolve into an ase calculator.
I would also like to be able to extract eg. the hamiltonian at each step (as a sisl object).
