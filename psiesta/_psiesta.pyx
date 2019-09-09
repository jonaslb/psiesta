cimport numpy as np
import numpy as np
from collections import namedtuple
from mpi4py import MPI

RunOutput = namedtuple("RunOutput", "e forces")

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
        cdef int mpiint = mpi_comm.py2f()
        fpsiesta_launch(self.label.encode(), &mpiint)
        self.active = True

    def run(self, locations):
        if not self.active:
            raise ValueError()
        if not locations.flags["C_CONTIGUOUS"]:
            locations = np.ascontiguousarray(locations)
        if self.locations is not None and locations.shape != self.locations.shape:
            raise ValueError()
        self.locations = locations
        print(locations.shape)
        cdef double[:, ::1] loc_view = locations
        cdef int na = locations.shape[0]
        cdef double e = 0
        forces = np.zeros_like(locations)
        cdef double[:, ::1] force_view = forces
        fpsiesta_forces(self.label.encode(), &na, &loc_view[0, 0], &e, &force_view[0, 0])
        return RunOutput(e, forces)

    def quit(self):
        if not self.active:
            raise ValueError()
        fpsiesta_quit(self.label.encode())
        self.active = False
