from pathlib import Path
import importlib
import tempfile
from shutil import copyfile
from mpi4py import MPI
import sisl as si
from io import StringIO
from contextlib import contextmanager
import os


_first_lib_loc = None


def _fdf_to_content(fdflike, base_dir=None, geometry=None):
    base_dir = base_dir or str(Path().resolve())
    f = fdflike
    fdf_is_content = (
        (   # A list of strings (eg from readlines or str.splitlines)
            not isinstance(f, str) and hasattr(f, "__iter__")
            and all(isinstance(s, str) for s in f)
        )   # Or just a multiline string
        or (isinstance(f, str) and "\n" in f)
    )
    if fdf_is_content and not isinstance(f, str):
        if all(l.endswith("\n") for l in fdflike):
            fdflike = "".join(fdflike)
        else:
            fdflike = "\n".join(fdflike)
    if fdf_is_content:
        if geometry is None:
            sile = si.io.fdfSileSiesta("_placeholder_" + hex(id(fdflike)))
            sile._directory = base_dir
            sile.fh = StringIO(fdflike)
            geometry = sile.read_geometry()
    else:
        p = Path(fdflike)
        if not p.exists():
            raise ValueError("fdflike could not be understood as content or path")
        if geometry is None:
            geometry = si.get_sile(p, base=base_dir).read_geometry()
        fdflike = p.read_text()
    return fdflike, geometry


class _FSiestaLibAsClass:
    def __init__(self, working_dir=".", comm=MPI.COMM_WORLD):
        """Since Siesta was never intended to be an 'object-style' calculator, but rather a monolithic
        program, we need to jump through hoops to obtain such behaviour anyway.
        Here the linked siesta library is *copied* to a new location on each object instantiation.
        This is necessary to keep the different Siesta instances from interfering with each others' memory.
        This class is intended to be subclassed, providing only the Lib->Class wrapper functionality.
        """
        global _first_lib_loc
        self.launched = False
        self.working_dir = working_dir
        self.comm = comm

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

    @contextmanager
    def in_working_dir(self):
        previous_dir = Path().cwd()
        try:
            os.chdir(self.working_dir)
            yield
        finally:
            os.chdir(previous_dir)

    def launch(self, label):
        with self.in_working_dir():
            self._fsiesta = self._module.FSiesta(label, mpi_comm=self.comm)
        self.launched = True

    def run(self, **kwargs):
        if not self.launched:
            raise ValueError("Siesta not launched yet")
        elif not self._fsiesta.active:
            raise ValueError("The fsiesta instance is not active - did you quit it?")
        with self.in_working_dir():
            r = self._fsiesta.run(**kwargs)
        return r

    def get_fermi_energy(self):
        self._fsiesta.get_fermi_energy()

    def __del__(self):
        # It is not possible to fully unload a library in Python. But we can call Siesta's quit
        # subroutine to deallocate some memory, close files etc.
        if os.chdir is None:
            print("Cannot safely call siesta quit due to python shutdown...")
        if self.launched and self._fsiesta.active and os.chdir is not None:
            previous_dir = Path().cwd()
            try:  # avoid using the contextmanager as it may be None on Python shutdown
                os.chdir(self.working_dir)
                # Siesta likes to say 'Job completed', print note to avoid confusion
                if self.comm.Get_rank and self.comm.Get_rank() == 0:
                    print("Siesta calculator __del__ message: ", end="")
                self._fsiesta.quit()
            finally:
                os.chdir(previous_dir)
        self._tmplib.unlink()  # Remove library copy
        if sum(1 for _ in self._tmpdir.iterdir()) == 0:  # And tmp lib dir if empty
            self._tmpdir.rmdir()


class FilePSiesta(_FSiestaLibAsClass):
    def __init__(self, main_fdf, working_dir, label, geometry=None, comm=MPI.COMM_WORLD):
        """File-based Siesta calculator object. You need to have already set up the fdf files for a valid
        Siesta calculation in `working_dir`. You cannot change the number of atoms or the basis (specie, orbitals)
        but the positions and cell can be changed. If you want to change the number of atoms (or the basis),
        you need to start a new calculator.

        Parameters
        ----------
        main_fdf : string or list of strings or pathlike, required
            The main fdf file (either the content (multiline str) or path to content)
        working_dir : pathlike, required
            A directory containing supplementary files for the siesta calculation. A directory with label as name
            is created. The actual Siesta calculation executes the main_fdf file in there.
        label : str, required
            The label to use. You must use a separate label for each calculation in same working dir.
        geometry : sisl.Geometry, optional
            If not given, it is read from the main_fdf.
        comm : mpi4py.Comm, optional
            If not given, uses MPI.COMM_WORLD
        """
        super().__init__(working_dir=working_dir, comm=comm)

        fdf, self.geom0 = _fdf_to_content(main_fdf, base_dir=working_dir, geometry=geometry)

        self.label = label
        self.label_dir = self.working_dir / self.label
        self.label_dir.mkdir(exist_ok=True)
        self.launch(self.label)

        self.geom0.write(self.label_dir / f"{label}_struct.fdf")
        fdf_prepend = (
            "MD.TypeOfRun forces\n"
            f"SystemLabel {label}\n"
            f"%include {label}_struct.fdf\n"
        )
        if comm.Get_rank() == 0:
            with (self.label_dir / (self.label + ".fdf")).open("w") as f:
                f.write(fdf_prepend)
                f.write(fdf)
        comm.Barrier()

        self.last_result = None
        self.last_geom = self.geom0

    def run(self, geom=None):
        if geom is None:
            geom = self.geom0
        result = super().run(geom=geom)
        self.last_result = result
        self.last_geom = geom
        return result

    def get_sile(self):
        return si.get_sile(self.label_dir / (self.label + ".fdf"))

    def read_hamiltonian(self):
        with self.get_sile() as sile:
            H = sile.read_hamiltonian()
        return H

    def read_density_matrices(self):
        with self.get_sile() as sile:
            DM, EDM = sile.read_density_matrices()
        return DM, EDM

    def __del__(self):
        super().__del__()  # todo: necessary?
