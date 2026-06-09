from pathlib import Path
from shutil import copyfile

import numpy as np
import pytest
import sisl as si

from psiesta import FilePSiesta


FIXTURES = Path(__file__).resolve().parent / "fixtures"
H_PSML = FIXTURES / "H.psml"


@pytest.fixture
def h_psml():
    if not H_PSML.exists():
        pytest.skip("H.psml is required for PSiesta smoke calculations")
    return H_PSML


@pytest.fixture
def psiesta_workdir(tmp_path, h_psml):
    copyfile(h_psml, tmp_path / "H.psml")
    return tmp_path


@pytest.fixture
def h_atom_geom():
    return si.Geometry(
        [[0.0, 0.0, 0.0]],
        atoms=[si.Atom("H")],
        lattice=si.Lattice([8.0, 8.0, 8.0]),
    )


@pytest.fixture
def h2_geom():
    return si.Geometry(
        [[0.0, 0.0, 0.0], [0.9, 0.0, 0.0]],
        atoms=[si.Atom("H"), si.Atom("H")],
        lattice=si.Lattice([10.0, 10.0, 10.0]),
    )


def _fdf(spin_polarized=False):
    spin = "SpinPolarized true\n" if spin_polarized else ""
    return """
NumberOfSpecies 1
%block ChemicalSpeciesLabel
  1 1 H
%endblock ChemicalSpeciesLabel

PAO.BasisSize SZ
MeshCutoff 20 Ry
XC.functional GGA
XC.authors PBE
MaxSCFIterations 1
SCF.MustConverge false
DM.Tolerance 1.d-2
DM.MixingWeight 0.3
SolutionMethod diagon
WriteMullikenPop 0
WriteForces true
""" + spin


def _calculator(psiesta_workdir, h_psml, label, geom, spin_polarized=False):
    calc = FilePSiesta(_fdf(spin_polarized=spin_polarized), psiesta_workdir, label, geometry=geom)
    copyfile(h_psml, calc.label_dir / "H.psml")
    return calc


def _assert_result_is_technical_smoke_ok(result, natoms):
    assert np.isfinite(result.energy)
    assert result.forces.shape == (natoms, 3)
    assert result.stress.shape == (3, 3)
    assert np.all(np.isfinite(result.forces))
    assert np.all(np.isfinite(result.stress))


def test_h_atom_in_box_runs(psiesta_workdir, h_psml, h_atom_geom):
    calc = _calculator(psiesta_workdir, h_psml, "h_atom", h_atom_geom, spin_polarized=True)

    result = calc.run(h_atom_geom)

    _assert_result_is_technical_smoke_ok(result, len(h_atom_geom))


def test_h2_in_box_runs(psiesta_workdir, h_psml, h2_geom):
    calc = _calculator(psiesta_workdir, h_psml, "h2", h2_geom)

    result = calc.run(h2_geom)

    _assert_result_is_technical_smoke_ok(result, len(h2_geom))


def test_h2_can_rerun_with_perturbed_geometry(psiesta_workdir, h_psml, h2_geom):
    calc = _calculator(psiesta_workdir, h_psml, "h2_rerun", h2_geom)

    first = calc.run(h2_geom)
    moved = h2_geom.copy()
    moved.xyz[1, 0] += 0.02
    second = calc.run(moved)

    _assert_result_is_technical_smoke_ok(first, len(h2_geom))
    _assert_result_is_technical_smoke_ok(second, len(h2_geom))
