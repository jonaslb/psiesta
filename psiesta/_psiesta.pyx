cimport numpy as np
import numpy as np
from collections import namedtuple
from mpi4py import MPI
from psiesta.runoutput import RunOutput
from psiesta._signal2exception import raise_on_sigabrt

cdef extern:
    void fpsiesta_launch(char* label, int* mpi_comm)
    void fpsiesta_forces(char* label, int* na, double* xa, double* cell, double* e, double* fa, double* stress)
    void fpsiesta_get(char* label, char* property, double* value, char* units)
    void fpsiesta_fermi_energy(char* label, double* value)
    void fpsiesta_quit(char* label)

class FSiesta:
    def __init__(self, label, mpi_comm=None):
        """Start a siesta 'session' for given label using given mpi_comm (default MPI_WORLD)."""
        self.label = label
        if mpi_comm is None:
            mpi_comm = MPI.COMM_WORLD
        self.mpi_comm = mpi_comm
        self._xyz = None
        self._cell = None
        cdef int mpiint = mpi_comm.py2f()
        fpsiesta_launch(self.label.encode(), &mpiint)
        self.active = True
        self._has_run = False

    def _get_valid_xyz(self, xyz):
        if xyz is None:
            if self._xyz is None:
                raise ValueError("No xyz provided")
            return self._xyz
        elif (self._xyz is not None and self._xyz.shape != xyz.shape) or (xyz.shape[1] != 3):
            raise ValueError("Shape mismatch")
        self._xyz = np.ascontiguousarray(xyz)
        return self._xyz

    def _get_valid_cell(self, cell):
        if cell is None:
            if self._cell is None:
                raise ValueError("No cell provided")
            return self._cell
        elif cell.shape != (3, 3):
            raise ValueError("Shape mismatch")
        self._cell = np.ascontiguousarray(cell)
        return self._cell

    def _geomloccell_contiguous(self, geom, xyz, cell):
        if geom is not None:
            if xyz is not None or cell is not None:
                raise ValueError("when geom is given, xyz and cell cannot be given")
            xyz = geom.xyz
            cell = geom.cell
        return self._get_valid_xyz(xyz), self._get_valid_cell(cell)

    def run(self, geom=None, xyz=None, cell=None, run_analyse=True):
        if not self.active:
            raise ValueError("This siesta session is shut down")
        self._has_run = True
        xyz, cell = self._geomloccell_contiguous(geom, xyz, cell)

        cdef double[:, ::1] loc_view = xyz
        cdef int na = xyz.shape[0]
        cdef double e = 0
        forces = np.zeros_like(xyz)
        cdef double[:, ::1] force_view = forces
        stress = np.zeros((3, 3), dtype=np.float64)
        cdef double[:, ::1] stressview = stress
        cdef double[:, ::1] cellview = cell

        with raise_on_sigabrt():
            fpsiesta_forces(self.label.encode(), &na, &loc_view[0, 0], &cellview[0, 0], &e, &force_view[0, 0], &stressview[0, 0])
        return RunOutput(e, forces, stress)

    def _get(self, what, np.ndarray [np.float64_t, ndim=1] output_array):
        raise NotImplementedError("Siesta currently exposes 0 properties through this method")
        cdef double[::1] output_view = output_array
        cdef int unitslen
        cdef char* units
        fpsiesta_get(self.label.encode(), what.encode(), &output_array[0], units)
        return (<bytes> units).decode()

    def get_fermi_energy(self):
        cdef double Ef
        if not self._has_run:
            raise ValueError("You didn't use .run() yet")
        fpsiesta_fermi_energy(self.label.encode(), &Ef)
        return Ef

    def quit(self):
        if not self.active:
            raise ValueError()
        fpsiesta_quit(self.label.encode())
        self.active = False
