cimport numpy as np
import numpy as np
from collections import Namedtuple
from mpi4py import MPI

RunOutput = Namedtuple("RunOutput", "e forces")

cdef extern:
    void fpsiesta_launch(char* label, int* mpi_comm)
    void fpsiesta_forces(char* label, int* na, double* xa, double* e, double* fa)
    void fpsiesta_quit(char* label)


class FSiesta:
    def __init__(self, label, mpi_comm=None):
        self.label = label
        if mpi_comm is None:
            mpi_comm = MPI.COMM_WORLD
        self.mpi_comm = mpi_comm
        self.locations = None
        fpsiesta_launch(label.encode(), mpi_comm.py2f())
        self.active = True

    def run(self, locations):
        if not self.active:
            raise ValueError()
        if not locations.flags["C_CONTIGUOUS"]:
            locations = np.ascontiguousarray(locations)
        if self.locations is not None and locations.shape != self.locations.shape:
            raise ValueError()
        self.locations = locations
        cdef double[::1] loc_view = locations
        cdef int na = locations.shape[0]
        cdef int e = 0
        forces = np.zeros_like(locations)
        cdef double[::1] force_view = forces
        fpsiesta_forces(label.encode(), &na, &locations[0], &force_view)
        return RunOutput(e, forces)

    def quit(self):
        if not self.active:
            raise ValueError()
        fpsiesta_quit(self.label.encode())
        self.active = False
