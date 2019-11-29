from .psiesta import FilePSiesta
import sisl as si
from ase.calculators.interface import Calculator
import numpy as np


class FilePSiestaASE(FilePSiesta, Calculator):
    def __init__(self, *args, atom_converter=None, **kwargs):
        """ASE interface for FilePSiesta calculator, please see that class for the docs.

        Additional parameters
        ---------------------
        atom_converter : function, optional
            A converter that turns ase atoms into sisl geometry. By default uses
            sisl.Geometry.fromASE, but you may want to use a custom function (eg. setting atom
            labels or such differently).
        """
        super().__init__(*args, **kwargs)
        if atom_converter is None:
            self._atoms2geom = si.Geometry.fromASE
        else:
            self._atoms2geom = atom_converter

    def need_rerun(self, geom):
        return (
            (self.last_result is None)
            or np.any(np.linalg.norm(geom.xyz-self.last_geom.xyz, axis=0) > 1e-4)
            )

    def _run_if_needed(self, atoms):
        if atoms is None:
            geom = self.last_geom
        else:
            geom = self._atoms2geom(atoms)
        if self.need_rerun(geom):
            self.run(geom)

    def get_potential_energy(self, atoms=None, force_consistent=False):
        self._run_if_needed(atoms)
        return self.last_result.energy

    def get_forces(self, atoms):
        self._run_if_needed(atoms)
        return self.last_result.forces.copy()

    def get_stress(self, atoms):
        self._run_if_needed(atoms)
        return self.last_result.stress.copy()

    def calculation_required(self, atoms, quantities):
        return self.need_rerun(self._atoms2geom(atoms))

    def get_fermi_level(self):
        if self.last_result is not None:
            return self.get_fermi_energy()
        return None
