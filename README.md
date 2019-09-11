# PSiesta: Siesta as a Python library

This repository contains Python bindings for the [Siesta as a subroutine](https://bazaar.launchpad.net/~siesta-maint/siesta/trunk/files/head:/Util/SiestaSubroutine/) functionality in Siesta.
Currently you can mpi-execute siesta controlled from Python.
It's still based on fdf-files, but you can run a calculation, get energy, forces and stress, *then alter the structure in Python, and hot-rerun the calculation*. Example:

```python
from mpi4py import MPI
import numpy as np
import sisl as si
from psiesta import FSiesta  # the fsiesta name comes from the siesta module that its built on

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
Relevant properties, other than those returned directly, can be read from the output files in the calculation directory in-between runs.
It is recommended to use [sisl](https://github.com/zerothi/sisl) for this.

So, although these bindings provide Python-integration, Siesta is still a file-based calculator.
The Python control primarily makes it easier to do calculations where many custom displacements are needed.

An important limitation is that you can only create the one `FSiesta` object once on each mpi process.
This is a limitation from fsiesta/siesta itself, further stemming from the fact that Siesta was never originally designed to be used as an 'object calculator' but rather as a monolithic program.

## Building
You must have a properly set up `arch.make` for Siesta. In your Siesta Obj-dir, you must have at least compiled Siesta.
You can then run `OBJ=/my/custom/siesta/Obj/ python3 setup.py install [--user] [--prefix=<prefix>]` (or use `build` instead of `install`) to build Psiesta.
It makes use of Siesta's own `Makefile` (which includes your `arch.make`) in combination with `--dry-run` to extract the compilation and link arguments.
It *should* work for both intel and gnu compilers, but be aware that LTO can complicate things, and ensure that any external libraries that are used (eg. flook) are compiled with `-fPIC`.

## Behaviour
See also [the SiestaSubroutine readme](https://bazaar.launchpad.net/~siesta-maint/siesta/trunk/view/head:/Util/SiestaSubroutine/README).
In summary, the fsiesta module that this is based on copies all fdf and psf-files from your working directory `<cwd>` into `<cwd>/<systemlabel>` where `<systemlabel>` is the label you give.
In that folder it will then start reading from `<systemlabel>.fdf` and putting any output files like a regular Siesta calculation, except with the structure provided from Python.
