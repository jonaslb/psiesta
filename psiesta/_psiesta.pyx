cimport numpy as np
import numpy as np
from collections import namedtuple
from mpi4py import MPI

RunOutput = namedtuple("RunOutput", "energy forces stress")

cdef extern:
    void fpsiesta_launch(char* label, int* mpi_comm)
    void fpsiesta_forces(char* label, int* na, double* xa, double* cell, double* e, double* fa, double* stress)
    void fpsiesta_quit(char* label)


class FSiesta:
    def __init__(self, label, mpi_comm=None):
        """Start a siesta 'session' for given label using given mpi_comm (default MPI_WORLD)."""
        self.label = label
        if mpi_comm is None:
            mpi_comm = MPI.COMM_WORLD
        self.mpi_comm = mpi_comm
        self.locations = None
        self.cell = None
        cdef int mpiint = mpi_comm.py2f()
        fpsiesta_launch(self.label.encode(), &mpiint)
        self.active = True

    def run(self, locations=None, cell=None):
        if ((locations is None and self.locations is None) or
            (cell is None and self.cell is None)):
            raise ValueError("You must have provided locations and cell at least once")
        if locations is not None:
            if self.locations is not None:
                assert locations.shape == self.locations.shape
            self.locations = locations
            if not locations.flags["C_CONTIGUOUS"]:
                self.locations = np.ascontiguousarray(locations)
        if cell is not None:
            assert cell.shape == (3, 3)
            self.cell = cell
            if not cell.flags["C_CONTIGUOUS"]:
                self.cell = np.ascontiguousarray(cell)
        if not self.active:
            raise ValueError("This siesta session is shut down")

        cdef double[:, ::1] loc_view = locations
        cdef int na = locations.shape[0]
        cdef double e = 0
        forces = np.zeros_like(locations)
        cdef double[:, ::1] force_view = forces
        stress = np.zeros((3, 3), dtype=np.float64)
        cdef double[:, ::1] stressview = stress
        cdef double[:, ::1] cellview = cell

        fpsiesta_forces(self.label.encode(), &na, &loc_view[0, 0], &cellview[0, 0], &e, &force_view[0, 0], &stressview[0, 0])
        return RunOutput(e, forces, stress)

    def quit(self):
        if not self.active:
            raise ValueError()
        fpsiesta_quit(self.label.encode())
        self.active = False
