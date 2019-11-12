# PSiesta: Siesta as a Python library

This repository contains Python bindings for the [Siesta as a subroutine](https://bazaar.launchpad.net/~siesta-maint/siesta/trunk/files/head:/Util/SiestaSubroutine/) functionality in Siesta.
Currently you can mpi-execute siesta controlled from Python.
It's still based on fdf-files, but you can run a calculation, get energy, forces and stress, *then alter the structure in Python, and hot-rerun the calculation*.

As an example, the following `myscript.py` could be executed with `mpirun -n 8 python3 myscript.py`:

```python
import numpy as np; from mpi4py import MPI
import sisl as si
from psiesta import FSiesta  # the fsiesta name comes from the siesta module that its built on

# Read geometry on all nodes: You can also do it on rank 0 only and broadcast with mpi4py
geometry = si.get_sile("graphene.fdf").read_geometry()
my_run = FSiesta("graphene")  # Start a siesta session with given label.fdf. Uses comm_world by default
energy, forces, stress = my_run.run(geometry)  # The DFT calculation happens here
H = si.get_sile("graphene/graphene.fdf").read_hamiltonian()
print(f"Energy: {energy}. Max force: {np.max(np.linalg.norm(forces, axis=1))}")
print(f"Fermi energy: {my_run.get_fermi_energy()}")

# Mutate the geometry and rerun
geometry.xyz[0, 0] += 0.05
new_results = my_run.run(geometry)  # new_results is a namedtuple
H2 = si.get_sile("graphene/graphene.fdf").read_hamiltonian()

# Now  make a file for later comparison of results / usage in e-ph coupling calculation?
dH = H2-H
if MPI.COMM_WORLD.Get_rank() == 0:
  dH.write("deltaH-no-correction.nc")  # for later calculations

my_run.quit()  # gracefully exit siesta
```

Siesta will run inside the Python processes.
Relevant properties, other than those returned directly, can be read from the output files in the calculation directory in-between runs.
It is recommended to use [sisl](https://github.com/zerothi/sisl) for this.

There are some details: You *must* specify `MD.TypeOfRun forces` in your fdf-file in order to have Siesta properly receive coordinates from Python.
Further you may have to use a patched Siesta (there are two bugs that might cause crashes) -- see [JonasLB's Siesta branch on Gitlab](gitlab.com/jonaslb/siesta) for the patched version.


## Obtaining source, building and installing
You can obtain the source by simply cloning this repository.
To build, you must have a properly set up `arch.make` for Siesta in your Obj-dir, and you must have at least compiled Siesta there (see the note above for a patched Siesta).
You can then run `OBJ=/my/custom/siesta/Obj/ python3 setup.py install [--user] [--prefix=<prefix>]` (or use `build` instead of `install`) to build Psiesta.
The setup.py-file makes use of Siesta's own `Makefile` (which includes your `arch.make`) in combination with `--dry-run` to extract the compilation and link arguments.
It *should* work for both intel and gnu compilers, but be aware that LTO can complicate things, and ensure that any external libraries that are used (eg. flook) are compiled with `-fPIC`.

On some platforms it is necessary to link more libraries than Siesta is otherwise compiled with. It is currently a little unclear why, but in one case I needed to use `EXTRA_COMP_ARGS="-lmkl_avx512 -lmkl_def"` (which the setup.py-file will recognize).

## Behaviour
See also [the SiestaSubroutine readme](https://bazaar.launchpad.net/~siesta-maint/siesta/trunk/view/head:/Util/SiestaSubroutine/README).
In summary, the fsiesta module that this is based on copies all fdf and psf-files from your working directory `<cwd>` into `<cwd>/<systemlabel>` where `<systemlabel>` is the label you give.
In that folder it will then start reading from `<systemlabel>.fdf` and putting any output files like a regular Siesta calculation, except with the structure provided from Python.

### A short summary:

* These details may change in future versions of Psiesta, so make sure to stay updated.
* Put `MD.TypeOfRun forces` in the fdf-file. This is needed for siesta to accept coordinates from Python.
* Start Siesta with `siesta = FSiesta("<mylabel>")`. Siesta will create a `mylabel` work directory and copy `fdf` and `psf` files in there. You can only do this once.
* Run Siesta with `result = siesta.run(geom=None, xyz=None, cell=None)`. If you provide `geom`, it should be an object with `.xyz` and `.cell` attributes (eg. a sisl geometry), and then you mustn't specify them by their keyword. On the first run, both must be specified either by geom or keywords, but on second and following runs, you can specify `xyz` or `cell` only, if you like. Returns a namedtuple with members: `energy`, `forces`, `stress`.
* Get eg. the fermi-energy with `siesta.get_fermi_energy()`. More properties could be exposed like this in the future or perhaps included in the results along with the total energy and forces.
* Get eg. the hamiltonian or other properties that were written to files. [Sisl](https://github.com/zerothi/sisl) is recommended.
* Mutate your system (eg. a phonon mode or custom md-step), re-run siesta, and get the properties again.
* Calling `siesta.quit()` is really optional. It calls the `siesta_end` subroutine, which closes file descriptors and outputs timing information.

### Some limitations:

* Only a few properties can currently be fetched via the bindings. Other properties must be obtained via the output-files. This may be further complicated by the fact that there's currently no way to call `siesta_analyze` so the log-file only contains a few things. Feel free to create an issue if you'd like something in particular, or send a PR if you've implemented it already.
* Only one `FSiesta` object may exist on each mpi process. This is a limitation from fsiesta/siesta itself, further stemming from the fact that Siesta was never originally designed to be used as an 'object calculator' but rather as a monolithic program.
* For the same reason as above, you don't get an exception when eg. the fdf-file contains an error. Instead, the whole process dies.
