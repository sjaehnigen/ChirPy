# ----------------------------------------------------------------------
#
#  ChirPy
#
#    A python package for chirality, dynamics, and molecular vibrations.
#
#    https://github.com/sjaehnigen/chirpy
#
#
#  Copyright (c) 2020-2025, The ChirPy Developers.
#
#
#  Released under the GNU General Public Licence, v3 or later
#
#   ChirPy is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published
#   by the Free Software Foundation, either version 3 of the License,
#   or any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.
#   If not, see <https://www.gnu.org/licenses/>.
#
# ----------------------------------------------------------------------

import os as _os
import copy as _copy
import numpy as _np
import warnings as _warnings

from ..topology.dissection import assign_molecule as _assign_molecule
from ..topology.dissection import define_molecules as _define_molecules
from ..topology.mapping import cell_vec as _cell_vec
from ..topology.mapping import cell_l_deg as _get_cell_aa_deg
from ..topology.mapping import detect_lattice as _get_symmetry
from ..classes.core import CORE as _CORE
from ..classes.trajectory import XYZ
from ..classes.system import Molecule as _Molecule
from .. import constants
from ..visualise import print_info
from ..config import ChirPyWarning as _ChirPyWarning


class _BoxObject(_CORE):

    # --- DEV log
    # volume is determined by _cell_vec_aa() / cell_vec_aa()
    # methods that are allowed to manipulate _cell_vec_aa and/or volume_aa3:
    # __init__, __pow__ (via __mul__)
    # plan: check routine compares _method() to method and complains
    # Symmetry should be determined from cell_aa
    # empty-box init allowed (bare)
    # --- END

    def __init__(self, *args, **kwargs):
        '''
        members: list of (n, XYZFrame object) tuples with n being
                 the no. of molecules within the box'''
        self.members = kwargs.get("members", [])
        self.member_set = kwargs.get("members", [])
        self.origin_aa = kwargs.get('origin_aa', _np.zeros((3)).astype(float))
        self.cell_aa_deg = kwargs.get('cell_aa_deg', _np.zeros(6,))
        self.pbc = kwargs.get('pbc', True)
        if len(args) != 0:
            self.__dict__.update(self.read(*args, **kwargs).__dict__)
        self.symmetry = kwargs.get('symmetry', _get_symmetry(self.cell_aa_deg))
        _BoxObject._sync_class(self)
        self.cell_vec_aa = self._cell_vec_aa(**kwargs)
        self.volume_aa3 = self._volume_aa3()
        self._clean_members()

    @classmethod
    def read(cls, *args, **kwargs):
        if kwargs.get('define_molecules') is not None:
            kwargs['wrap_molecules'] = True
        else:
            kwargs['wrap'] = True
        _load = _Molecule(*args, **kwargs)

        nargs = {}
        nargs['cell_aa_deg'] = _load.cell_aa_deg
        if _np.any(_load.cell_aa_deg == 0.):
            _warnings.warn('Cannot detect cell dimensions!',
                           _ChirPyWarning,
                           stacklevel=2)

        if _load.mol_map is not None:
            return cls(
                    members=[(1, _s)
                             for _s in _load.XYZ._frame.split(
                             _load.mol_map)],
                    **nargs)
        else:
            return cls(members=[(1, _load.XYZ)],
                       **nargs)

    def _cell_vec_aa(self, **kwargs):
        return _cell_vec(self.cell_aa_deg)

    def _cell_aa_deg(self):
        if hasattr(self, 'cell_aa_deg'):
            if _get_symmetry(self.cell_aa_deg) not in [
                    None, 'void']:
                return self.cell_aa_deg
        if hasattr(self, 'cell_vec_aa'):
            return _get_cell_aa_deg(self.cell_vec_aa)

    def _volume_aa3(self):
        return _np.dot(self.cell_vec_aa[0],
                       _np.cross(self.cell_vec_aa[1], self.cell_vec_aa[2]))

    def _sync_class(self):
        '''Calculates intensive properties only'''
        self.n_members = len(self.members)
        self.mass_amu = sum([_n * sum(_m.masses_amu)
                             for _n, _m in self.member_set])
        self.n_atoms = sum([_n * _m.n_atoms for _n, _m in self.members])
        try:
            self.cell_aa_deg = self._cell_aa_deg()
        except AttributeError:
            pass
        if not hasattr(self, 'symmetry'):
            self.symmetry = _get_symmetry(self.cell_aa_deg)
    # def routine: check all xx attributes against _xx() methods

    def split_members(self):
        new_members = []
        for _ii, (_i, _m) in enumerate(self.members):
            mol_map = tuple(_define_molecules(
                                       _m.pos_aa,
                                       _m.symbols,
                                       cell_aa_deg=self.cell_aa_deg
                                       ))
            new_members += [(_i*1, _s)
                            for _s in _m.split(mol_map)]
        self.members = new_members
        self._sync_class()
        self._clean_members()

    def _clean_members(self):
        if self.n_members == 0:
            return None
        _eq = _np.zeros((self.n_members,) * 2)

        if self.n_members > 1:
            for _i, _m in self.members:
                _m.wrap_molecules(_np.zeros((_m.n_atoms)).astype(int))

        for _ii, (_i, _m) in enumerate(self.members):
            _eq[_ii, _ii:] = _np.array([
                          bool(_m._is_equal(_n, noh=True, atol=2.)[0])
                          for _j, _n in self.members[_ii:]
                          ])

        _eq = [_np.argwhere(_ee == 1.0).flatten().tolist() for _ee in _eq]
        _N = self.n_members
        _M = self.n_members
        _ass = _np.zeros((_N)).astype(int)
        _sp = 0
        for _im in range(_N):
            if _ass[_im] == 0:
                _sp += 1
                _ass, _M = _assign_molecule(_ass, _sp, _N, _eq, _im, _M)
            if _M == 0:
                break
        _n, _m = _np.array(self.members).T
        self.member_set = [(_n[_ass == _i].sum(), _m[_ass == _i][0])
                           for _i in _np.unique(_ass)]
        self._sync_class()

    def __add__(self, other):
        '''Combine members of different systems'''
        if not isinstance(other, _BoxObject):
            raise TypeError('unsupported operand type(s) for +: '
                            '\'%s\' and \'%s\''
                            % (type(self).__name__, type(other).__name__))
        new = _copy.deepcopy(self)
        if _np.allclose(self.cell_vec_aa, other.cell_vec_aa):
            new.members += other.members
        else:
            raise AttributeError('The two objects have different '
                                 'cell attributes!')
        new._sync_class()
        new._clean_members()
        return new
        # Later: choose largest cell param and lowest symmetry

    def __mul__(self, other):
        '''Multiply system keeping box size constant'''
        new = _copy.deepcopy(self)
        if isinstance(other, int):
            for _i in range(other-1):
                new += self
        # elif isinstance(other, _BoxObject):
        # ToDo: connect it to pow
        else:
            raise TypeError('unsupported operand type(s) for *: \
\'%s\' and \'%s\'' % (type(self).__name__, type(other).__name__))
        return new

    def __pow__(self, other):
        '''Multiply system and scale box accordingly'''
        _warnings.warn('pow() in beta state. Proceed with care!',
                       _ChirPyWarning,
                       stacklevel=2)
        if not isinstance(other, int):
            raise TypeError('unsupported operand type(s) for *: '
                            '\'%s\' and \'%s\''
                            % (type(self).__name__, type(other).__name__))
        new = _copy.deepcopy(self)
        new.members *= other
        new._cell_vec_aa = lambda: other ** (1/3) * self._cell_vec_aa()
        new.cell_vec_aa = new._cell_vec_aa()
        new.volume_aa3 = new._volume_aa3()
        new._sync_class()
        new._clean_members()
        return new

    def _mol_map(self):
        _imol = 0
        mol_map = []
        for _m in self.member_set:
            for _i in range(_m[0]):
                mol_map += _m[1].n_atoms * [_imol]
                _imol += 1
        return _np.array(mol_map)

    def print_info(self) -> None:
        # ToDo: use self._print_info = [print_info.XXX]
        print_info.print_header(self)
        print('%-12s %s' % ('Periodic', self.pbc))
        print('%12d Members\n%12d Atoms\n%12.4f amu\n%12.4f aa3' %
              (self.n_members, self.n_atoms, self.mass_amu, self.volume_aa3))
        print_info.print_cell(self)
        print(77 * '–')
        print('%45s %8s %12s' % ('File', 'No.', 'Molar Mass'))
        print(77 * '-')
        print('\n'.join(['%45s %8d %12.4f' %
                         (getattr(_m[1], '_fn', ''),
                          _m[0],
                          sum(_m[1].masses_amu))
                         for _m in self.member_set]))
        print(77 * '–')

    def create(self, **kwargs):
        # most important class (must not be adapted within derived classes)
        # work in progress... # creates a system object (Supercell)
        pass

    def write(self, fn, **kwargs):
        wrap_molecules = kwargs.pop("wrap_molecules", False)
        _SC = self.create(**kwargs)
        _SC.wrap()
        if wrap_molecules:
            _SC.define_molecules()
            _SC.wrap_molecules()
        _SC.write(fn)


class MolecularCrystal(_BoxObject):
    def _sync_class(self):
        if _np.any(self.cell_aa_deg == 0.) or self.cell_aa_deg is None:
            raise ValueError('%s requires valid cell dimensions!'
                             % self.__class__.__name__)

        self.lattice = _get_symmetry(self.cell_aa_deg)
        _BoxObject._sync_class(self)

    def propagate(self, frame, multiply=(1, 1, 1), priority=(0, 1, 2)):
        '''Convolute FRAME object with unitcell.'''
        frame.cell_aa_deg = self.cell_aa_deg
        frame.repeat(multiply, priority=priority)
        self.cell_aa_deg = frame.cell_aa_deg

        return frame

    def create(self, verbose=True, **kwargs):
        _SC = self.members[0][1]
        _SC._axis_pointer = -2
        # _mol = 0
        # mol_map = [_mol] * len(_SC.symbols)
        for _i in range(self.members[0][0]-1):
            _SC += self.members[0][1]
        #    _mol += 1
        #    mol_map += [_mol] * len(self.members[0][1].symbols)

        for _m in self.members[1:]:
            for _i in range(_m[0]):
                _SC += _m[1]
        #        _mol += 1
        #        mol_map += [_mol] * len(self.members[0][1].symbols)

        # multiply = kwargs.get('multiply', (1, 1, 1))
        # _uc_mol_map = mol_map
        # for _repeat in range(1, _np.prod(multiply)):
        #   mol_map = _np.concatenate((mol_map, _uc_mol_map+_np.amax(mol_map)))

        _MOL = _Molecule(XYZ=self.propagate(_SC, **kwargs),
                         # mol_map=mol_map,
                         cell_aa_deg=self.cell_aa_deg)
        # ToDO: incremental mol_map broken, recovered by define_molecules()
        #       (reason?: original mol map wrong due to too small cell)

        _MOL.define_molecules(silent=True)
        _MOL.sort_atoms(_np.argsort(_MOL.mol_map, kind='stable'))
        if verbose:
            _MOL.print_info()

        return _MOL


_solvents = {}


class Solution(_BoxObject):
    def __init__(self, *args, **kwargs):
        self.solvent = kwargs.get("solvent")
        self.rho_g_cm3 = kwargs.get("rho_g_cm3", 1.0)
        self.solutes = kwargs.get("solutes", [])
        self.c_mol_L = kwargs.get("c_mol_L", [1.0])

        # ToDo: ask for max atoms, max volume or max counts of members etc.
        # to get simulation cell ready

        if self.solvent is None:
            raise AttributeError('You have to specify a solvent as coordinate '
                                 'file or select one from the library!')
        if self.solvent in _solvents:
            self.solvent = _solvents[self.solvent]
        if 0. in self.c_mol_L:
            raise ValueError('You have to specify non-zero values of '
                             'concentration!')

        _slt = [XYZ(_s) for _s in self.solutes]
        _slv = XYZ(self.solvent)

        # --- CALCULATE INTENSIVE PROPERTIES (per 1L)
        _c_slv_mol_L = (1000 * self.rho_g_cm3 -
                        sum([_c * _o.masses_amu.sum()
                             for _c, _o in zip(self.c_mol_L, _slt)])
                        ) / _slv.masses_amu.sum()

        if _c_slv_mol_L <= _np.amax(self.c_mol_L):
            raise ValueError('The given solutes\' concentrations exceed '
                             'density of %.2f!\n' % self.rho_g_cm3)

        _c_min_mol_L = _np.amin(self.c_mol_L)

        # --- CALCULATE EXTENSIVE PROPERTIES
        # Get counts of solvent relative to solutes
        # default: set lowest c to 1
        _n = (self.c_mol_L + [_c_slv_mol_L]) / _c_min_mol_L

        def _dev_warning(_d, _id):
            with _warnings.catch_warnings():
                if _d > 0.01:
                    _warnings.warn('Member counts differ from input value by '
                                   'more than 1%%:\n  - %s\n' % _id,
                                   _ChirPyWarning,
                                   stacklevel=2)
        [_dev_warning(abs(round(_in) - _in) /
                      _in, ([self.solvent] + self.solutes)[_ii])
         for _ii, _in in enumerate(_n)]

        nargs = {_k: kwargs.get(_k) for _k in kwargs.keys()
                 if _k not in [
                        "solvent",
                        "rho_g_cm3",
                        "solutes",
                        "c_mol_L",
                        "member_set",
                        ]}

        with _warnings.catch_warnings():
            _warnings.filterwarnings('ignore', category=_ChirPyWarning)
            _BoxObject.__init__(
                        self,
                        symmetry='orthorhombic',
                        members=[(int(round(_in)), _is)
                                 for _in, _is in zip(_n, _slt + [_slv])],
                        **nargs)  # by definition solvent is the last member

        del _slt, _slv, _c_slv_mol_L, _n, _c_min_mol_L, _dev_warning

    @classmethod
    def read(cls, fn, **kwargs):
        _tmp = _BoxObject.read(fn, **kwargs)
        _out = cls.__new__(cls)
        for _key in _tmp.__dict__:
            setattr(_out, _key, getattr(_tmp, _key))
        _out._sync_class()
        return _out

    def _cell_vec_aa(self, **kwargs):
        # ToDo: what to do if cell_aa argument given here?
        # ==> check if total volume is the same;
        # if yes use the given cell values, otherwise raise Exception
        if self.symmetry == 'orthorhombic':  # should be cubic
            return _np.diag(3 * [(self.mass_amu /
                                 self.rho_g_cm3 /
                                 (constants.avog * 1E-24)) ** (1/3)])

    def _c_mol_L(self):
        return [_m[0] / (constants.avog * 1E-27) / self.volume_aa3
                for _m in self.member_set]

    def _rho_g_cm3(self):
        return self.mass_amu / (constants.avog * 1E-24) / self.volume_aa3

    def _sync_class(self):
        _BoxObject._sync_class(self)
        self.c_mol_L = self._c_mol_L()
        self.rho_g_cm3 = self._rho_g_cm3()

    def print_info(self):
        _BoxObject.print_info(self)
        print('%12.4f g / cm³' % self.rho_g_cm3)
        print('\n'.join(map('{:12.4f} mol / L'.format, self.c_mol_L)))

    def create(self, **kwargs):
        return self._fill_box(**kwargs)

    def _fill_box(self, verbose=False, sort_atoms=False, write_pdb=True):
        '''requires packmol
           sort_atoms ... sort atoms alphabetically (False: sorted by resid)'''
        # --- calculate packmol box
        _box_aa = _np.concatenate((self.origin_aa, _np.dot(_np.ones((3)),
                                  self.cell_vec_aa)))
        # --- if periodic: add vacuum edges
        if self.pbc:
            _box_aa += _np.array([1., 1., 1., -1., -1., -1.])

        with open('packmol.inp', 'w') as f:

            f.write('tolerance 2.000' + 2*'\n')
            f.write('filetype pdb' + 2*'\n')
            f.write('output .simbox.pdb' + '\n')

            # --- supress any RuntimeWarning from PDBReader for missing cell

            for _im, _m in enumerate(self.member_set):
                _fn = '.member-%03d.pdb' % _im
                _m[1].mol_map = _np.zeros_like(_m[1].symbols)
                with _warnings.catch_warnings():
                    _warnings.filterwarnings('ignore', category=_ChirPyWarning)
                    _m[1].write(_fn)
                f.write('\n')
                f.write('structure %s' % _fn + '\n')
                f.write('  number %d' % _m[0] + '\n')
                f.write('  inside box ' + ' '.join(map('{:.3f}'.format,
                                                   _box_aa)) + '\n')
                f.write('end structure' + '\n')

        if verbose:
            print("Calling packmol ... (see packmol.log)")
        _err = _os.system("packmol < packmol.inp > packmol.log")
        if _err == 32512:
            raise ImportError("could not fill box. Is packmol installed?")
        elif _err != 0:
            raise ValueError("unexpected packmol error")

        if verbose:
            print("Done.")

        with _warnings.catch_warnings():
            _warnings.filterwarnings('ignore', category=_ChirPyWarning)
            _load = _Molecule(".simbox.pdb",
                              cell_aa_deg=self._cell_aa_deg(),
                              mol_map=self._mol_map())

        self.mol_map = self._mol_map()
        _load.define_molecules(silent=True)
        _load.sort_atoms(_np.argsort(_load.mol_map, kind='stable'))
        if self.pbc:
            _load.center_molecule(0)
        if sort_atoms:
            _load.sort_atoms()
        if write_pdb:
            _load.write("topology.pdb", rewind=False)

        # --- clean files
        # _os.remove(".tmp_packmol.inp")
        for _im, _m in enumerate(self.member_set):
            _os.remove(".member-%03d.pdb" % _im)
        _os.remove(".simbox.pdb")

        #with _warnings.catch_warnings():
        #    _warnings.filterwarnings('ignore', category=_ChirPyWarning)
        #    _load = _Molecule("topology.pdb")
        return _Molecule("topology.pdb")
