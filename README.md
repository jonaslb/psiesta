# PSiesta: Siesta as a Python library

This repository contains Python bindings for the [Siesta as a subroutine](https://bazaar.launchpad.net/~siesta-maint/siesta/trunk/files/head:/Util/SiestaSubroutine/) functionality in Siesta.
Currently you can mpi-execute siesta controlled from Python. There are some limitations:
It's still all based on fdf-files, and you can only run a calculation, get energy, forces and stress, alter the structure, and then hot-rerun the calculation. Example:

```python
from mpi4py import MPI
import numpy as np
import sisl as si
from _psiesta import FSiesta  # structure is undecided / due to poc build process, hence the underscore

rank = MPI.COMM_WORLD.Get_rank()

# Read geometry on all nodes: You can also do it on rank 0 only and broadcast with mpi4py
geometry = si.get_sile("graphene.fdf").read_geometry()
my_run = FSiesta("graphene")  # Start a siesta session with given label.fdf. Uses comm_world by default
energy, forces, stress = my_run.run(locations=geometry.xyz, cell=geometry.sc.cell)
H = si.get_sile("graphene/graphene.fdf").read_hamiltonian()
print(f"Energy: {energy}. Max force: {np.max(np.linalg.norm(forces, axis=1))}")

# Mutate the geometry and rerun
geometry.xyz[0, 0] += 0.05
new_results = my_run.run(geometry.xyz)
H2 = si.get_sile("graphene/graphene.fdf").read_hamiltonian()

# Now  make a file for later comparison of results / usage in e-ph coupling calculation?
dH = H2-H
if rank == 0:
  dH.write("deltaH-no-correction.nc")  # for later calculations

my_run.quit()  # gracefully exit siesta
```

You could execute the above script with eg. `mpirun -n 4 python3 myscript.py`. Siesta will then run inside the Python processes.
'Siesta as a subroutine' has the ability to get other properties, but the bindings are not made yet. Also it is todo to find out what Siesta even exposes through this interface.
In any case, anything relevant can still be extracted from calculation directory (eg. the tshs-file, although I'm not certain whether editing it will make it work as a restart file).

So, although this provides Python-integration, Siesta is still a file-based calculator. The Python control 'only' makes it easier to do calculations where many custom displacements are needed.


## Building
Please see the `setup.py` docstring. Currently most link parameters etc. are hardcoded.
There is probably not really any way around having to do some manual work if you use a different setup than intel+mkl which it is set up for now.
But if you can think of a good way solve this, perhaps eg. by integrating with the arch.make in siesta-obj, please make an issue or pull request :)

## Behaviour
See also `siesta/Util/SiestaSubroutine/README`.
The fsiesta module that this is based on copies all fdf and psf-files from your working directory `<cwd>` into `<cwd>/<systemlabel>` where `<systemlabel>` is the label you give.
In that folder it will then start reading from `<systemlabel>.fdf` as a regular Siesta calculation.
The only difference here compared to a regular run is that immediately after the scf cycle, you can pull out some information you like to treat in Python.
You can also change the structure and restart the calculation.
