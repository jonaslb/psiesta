from mpi4py import MPI


def test_imports_under_mpi():
    import psiesta

    assert psiesta.FilePSiesta is not None
    assert MPI.COMM_WORLD.Get_size() >= 1
