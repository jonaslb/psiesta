# [PSiesta](https://github.com/jonaslb/psiesta): Siesta as a Python library

This repository contains Python bindings for the [Siesta as a subroutine](https://gitlab.com/siesta-project/siesta/tree/master/Util/SiestaSubroutine) functionality in the Siesta density functional theory software.
PSiesta does not simply execute the Siesta executable, it has Siesta built-in as a library.
That means you can use it similarly to how you would GPAW, ie. with MPI in the Python code.
You must still specify your Siesta-options in an fdf-file (it would be nice if we had a Python abstraction instead, but we don't have such a thing yet).
There is also an [ASE](https://gitlab.com/ase/ase) interface.

## Example

The following `myscript.py` could be executed with `mpirun -n 8 python3 -m mpi4py myscript.py`:

```python
from mpi4py import MPI
import sisl as si
from ase.optimize import QuasiNewton
from psiesta import FilePSiesta
from psiesta.ase import AseFilePSiesta

# mpi rank
rank = MPI.COMM_WORLD.Get_rank()

# Create the geometry
geom = si.geom.graphene()

# Make the calculator object.
# Arguments:       main_fdf,      working_dir,       label,      geometry, comm=MPI.COMM_WORLD
calc = FilePSiesta("options.fdf", "working/siesta/", "graphene", geometry=geom)

# Run siesta_forces for the given geometry.
energy, forces, stress = calc.run(geom)
if rank == 0:
    H = calc.read_hamiltonian()
    print(f"Energy: {energy}.")
    print(f"Fermi energy: {calc.get_fermi_energy()}")

# Mutate the geometry and run again
geom.xyz[0, 0] += 0.05
new_results = calc.run(geom)  # new_results is a namedtuple

# Write dH for later use
if rank == 0:
    H2 = calc.read_hamiltonian()
    dH = H2-H
    dH.write("my-deltaH.nc")

# Other example: Optimize with ASE:
atoms = geom.toASE()
atoms.set_calculator(AseFilePSiesta(
    # main_fdf, working_dir, label, geometry=None, comm=MPI.COMM_WORLD, atoms_converter=si.Geometry.fromASE
    "options.fdf", "workingdir/siesta/", "aseopt", geometry=geom
))
atoms.rattle(stdev=0.03)
opt = QuasiNewton(atoms, traj="optimize.traj")
opt.run(fmax=0.01)
```

Siesta will run inside the Python processes.
Relevant properties, other than those returned directly, can be read from the output files in the calculation directory in-between runs.
It is recommended to use [sisl](https://github.com/zerothi/sisl) for this.
There are some shortcuts for the hamiltonian (as shown above), as well as density matrices and fermi energy.

You should use a Siesta version later than the git master as of 2020-06-10, as a few fixes regarding library operation were merged at this point.


## Obtaining source, building and installing
You can obtain the source by simply cloning this repository.

You only need to execute `pip3 install .` to install PSiesta.
You may use the flags `--user` to install for yourself only.

Note that for some reason, the default pip behavour of using build isolation is an extremely slow process.
You can speed up the process by using `--no-build-isolation`, but then you must install the build dependencies manually first: `mesonpep517` and `ninja`.

Under the hood, `pkgconfig` is used via Meson to find all dependencies and link flags.
Siesta is currently built from a custom branch based on the upstream PSML branch with meson build instructions added.

## Behaviour
See also [the SiestaSubroutine readme](https://gitlab.com/siesta-project/siesta/tree/master/Util/SiestaSubroutine/README).
In summary, the fsiesta module that this is based on copies all fdf and psf-files from your working directory `<cwd>` into `<cwd>/<systemlabel>` where `<systemlabel>` is the label you give.
In that folder it will then start reading from `<systemlabel>.fdf`.
Ensuring that this file exists is handled by the Python wrapper.
It will also prepend some settings to your fdf-file: Notably `MD.TypeOfRun forces` is enforced to make Siesta accept given coordinates. It also sets the system label and configures the geometry.


### Some limitations:

* Only a few properties can currently be fetched directly via the bindings. Other properties must be obtained via the output-files.
  Feel free to create an issue if you'd like something in particular built-in, or send a PR if you've implemented it already.
* You don't get an exception when eg. the fdf-file contains an error. Instead, the whole process dies.
  This is because on error, Siesta intentionally kills itself which unfortunately includes the Python process.