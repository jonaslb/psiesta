from pathlib import Path
import importlib
import tempfile
from shutil import copyfile
from .util import chdir
from mpi4py import MPI
import sisl as si
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

_first_lib_loc = None


class _FSiestaLibAsClass:
    def __init__(self):
        """Since Siesta was never intended to be an 'object-style' calculator, but rather a monolithic
        program, we need to jump through hoops to obtain such behaviour anyway.
        Here the linked siesta library is *copied* to a new location on each object instantiation.
        This is necessary to keep the different Siesta instances from interfering with each others' memory.
        This class is intended to be subclassed, providing only the Lib->Class wrapper functionality.
        """
        global _first_lib_loc
        self.launched = False

        if _first_lib_loc is None:
            # It appears that importlib will "update" find_spec when it has been loaded once,
            # ie. it will look at a previous temporary file which may have been deleted.
            # Hence we use _first_lib_loc to work around it.
            original_path = Path(importlib.util.find_spec("psiesta._psiesta").origin)
            _first_lib_loc = original_path
        else:
            original_path = _first_lib_loc

        self._tmpdir = Path(tempfile.mkdtemp(prefix="fsiesta_"))
        self._name = hex(id(self))
        self._tmplib = self._tmpdir / self._name
        copyfile(original_path, self._tmplib)

        name = "_psiesta"
        self._loader = importlib.machinery.ExtensionFileLoader(name, str(self._tmplib))
        self._spec = importlib.util.spec_from_loader(name, self._loader)
        self._module = importlib.util.module_from_spec(self._spec)
        self._loader.exec_module(self._module)

    def launch(self, label):
        self._fsiesta = self._module.FSiesta(label, mpi_comm=comm)
        self.launched = True

    def run(self, **kwargs):
        if not self.launched:
            raise ValueError("Siesta not launched yet")
        elif not self._fsiesta.active:
            raise ValueError("The fsiesta instance is not active - did you quit it?")
        return self._fsiesta.run(**kwargs)

    def get_fermi_energy(self):
        self._fsiesta.get_fermi_energy()

    def __del__(self):
        if self.launched and self._fsiesta.active:
            self._fsiesta.quit()  # Dealloc memory (Siesta's own responsibility! will leak otherwise)
        self._tmplib.unlink()  # Remove library copy
        if sum(1 for _ in self._tmpdir.iterdir()) == 0:  # And tmp lib dir if empty
            self._tmpdir.rmdir()


class FilePSiesta(_FSiestaLibAsClass):
    def __init__(self, main_fdf, working_dir, label, geometry=None):
        """File-based Siesta calculator object. You need to have already set up the fdf files for a valid
        Siesta calculation in `working_dir`. You cannot change the number of atoms or the basis (specie, orbitals)
        but the positions and cell can be changed. If you want to change the number of atoms (or the basis),
        you need to start a new calculator.

        Parameters
        ----------
        main_fdf : pathlike, required
            The main fdf file.
        working_dir : pathlike, required
            A directory containing supplementary files for the siesta calculation. A directory with label as name
            is created. The actual Siesta calculation executes the main_fdf file in there.
        label : str
            The label to use. If you are running several calculations, use a new label for each.
        """
        if geometry is None:
            self.geom0 = si.get_sile(main_fdf).read_geometry()
        else:
            self.geom0 = geometry
        self.working_dir = Path(working_dir)
        super().__init__()
        self.label = label
        self.label_dir = self.working_dir / self.label
        self.label_dir.mkdir(exist_ok=True)
        with chdir(self.working_dir):
            self.launch(self.label)
        self.geom0.write(self.label_dir / f"{label}_struct.fdf")
        fdf_prepend = [
            "MD.TypeOfRun forces\n",
            f"SystemLabel {label}\n",
            f"%include {label}_struct.fdf\n"
        ]
        if rank == 0:
            fdf_contents = list(Path(main_fdf).open())
            (self.label_dir / (self.label + ".fdf")).open("w").writelines(fdf_prepend + fdf_contents)

        self.last_result = None
        self.last_geom = self.geom0

    def run(self, geom=None):
        if geom is None:
            geom = self.geom0
        with chdir(self.working_dir):
            result = super().run(geom=geom)
            self.last_result = result
            self.last_geom = geom
        return result

    @property
    def main_sile(self):
        return si.get_sile(self.label_dir / (self.label + ".fdf"))

    def read_hamiltonian(self):
        with self.main_sile as sile:
            H = sile.read_hamiltonian()
        return H

    def read_density_matrices(self):
        with self.main_sile as sile:
            DM, EDM = sile.read_density_matrices()
        return DM, EDM

    def __del__(self):
        # TODO: chdir may have been set to None if python is shutting down, handle it better
        if chdir is None:
            self.launched = False  # dont call fsiesta quit
            super().__del__()
            return
        with chdir(self.working_dir):
            super().__del__()
