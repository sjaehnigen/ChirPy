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


import numpy as np
import copy
import warnings as _warnings
from itertools import product

from .. import constants
from ..mathematics.algebra import change_euclidean_basis as ceb
from ..mathematics.algebra import kabsch_algorithm, rotate_vector, angle, \
        signed_angle, vector, dihedral

from ..snippets import _unpack_tuple
from ..config import ChirPyWarning as _ChirPyWarning

# NB: the molecules have to be sequentially numbered starting with 0
# the script will transform them starting with 0
# Get rid of class dependence


def dist_crit_aa(symbols):
    '''Get distance criteria matrix for bond between atoms (in angstrom)
       http://www.ks.uiuc.edu/Research/vmd/vmd-1.9.1/ug/node26.html
       '''
    natoms = len(symbols)
    crit_aa = np.zeros((natoms, natoms))
    _r = np.array(constants.symbols_to_rvdw(symbols)) / 100.0
    crit_aa = (_r[:, None] + _r[None, :])
    crit_aa *= 0.6
    return crit_aa


def dec(prop, indices, n_ind=None, axis=0):
    """decompose prop according to indices
       n_ind: interpret numerical entries of indices and return empty arrays
       for missing indices"""
    if n_ind is not None:
        iterator = range(n_ind)
    else:
        iterator = set(indices)
    if isinstance(prop, (tuple, list)):
        assert axis == 0, 'cannot process axis != 0 for tuple or list'
        assert len(prop) == len(indices), \
            'lenght of index array does not match atom data'
        return [
            type(prop)([
                prop[k] for k, j_mol in enumerate(indices) if j_mol == i_mol
                ]) for i_mol in iterator
            ]
    else:
        _indices = np.array(indices)
        assert prop.shape[axis] == len(indices), \
            'length of index array does not match data: ' + \
            f'{len(_indices)}, {prop.shape}'
        return [
                np.take(prop, np.where(_indices == i_mol)[0], axis=axis)
                for i_mol in iterator
            ]


def cowt(pos, wt, axis=-2, mask=None, subset=slice(None)):
    '''Calculate centre of weight, consider periodic boundaries before
       calling this method.
       Optional mask with (0-based) indices of units for subset.'''

    _pos = np.moveaxis(pos, axis, 0)
    if not hasattr(wt, '__len__'):
        _wt = np.ones(len(_pos)) * wt
    else:
        _wt = np.array(wt)

    if mask is not None:
        _dwt = dec(_wt[subset], mask)
        _dpos = dec(_pos[subset], mask)
        return np.moveaxis(np.array([cowt(_p, _w, axis=0)
                                     for _w, _p in zip(_dwt, _dpos)]),
                           0, axis)

    _slc = (subset,) + (len(_pos.shape)-1) * (None,)

    return np.sum(_pos[subset] * _wt[_slc], axis=0) / _wt[subset].sum()


def cell_l_deg(cell_vec, multiply=(1, 1, 1)):
    '''Convert cell vectors into box info. Unit of l (length) equal to the one
       used in cell vector.
       cell_vec as 3×3 array
       '''
    _m = np.array(multiply)
    return np.concatenate((
        np.linalg.norm(cell_vec * _m[:, None], axis=-1),
        np.array([
            angle(cell_vec[1], cell_vec[2]),
            angle(cell_vec[0], cell_vec[2]),
            angle(cell_vec[0], cell_vec[1])
            ]) * 180./np.pi
        ))


def cell_vec(cell, n_fields=3, priority=(0, 1, 2)):
    '''cell as np.array/list of: a b c al be ga
       n_fields: usually 3

       Priority defines the alignment of non-rectangular objects in cartesian
       space; by convention the z axis is the odd one (i.e. not aligned), and
       cell vectors are calculated accordingly (e.g. in VMD); here, this
       corresponds to priority (0,1,2). Any deviation (e.g. z-axis IS aligned,
       alpha > 90°, ...) can be taken account for by adjusting priority, and
       the correct cell vectors are calculated. However, VMD or other
       programmes may still calculate wrong cell vectors. Hence, ...
       Priority should always be (0,1,2) and symmetry conventions be used
       (e.g. for monoclinic cells: beta is the angle > 90°; CPMD wants alpha
       to be >90° but this is wrong and CELL VECTORS should be used instead)
       '''
    if isinstance(cell, list):
        cell = np.array(cell)

    abc, albega = cell[:3], cell[3:] * np.pi / 180.
    cell_vec = np.zeros((3, n_fields))
    v0, v1, v2 = priority
    cell_vec[v0, v0] = abc[v0]
    cell_vec[v1, v1] = abc[v1] * np.sin(albega[(3 - v0 - v1)])
    cell_vec[v1, v0] = abc[v1] * np.cos(albega[(3 - v0 - v1)])
    cell_vec[v2, v2] = abc[v2] * np.sin(albega[(3 - v0 - v2)]) \
        * np.sin(albega[(3 - v1 - v2)])
    cell_vec[v2, v0] = abc[v2] * np.cos(albega[(3 - v0 - v2)])
    cell_vec[v2, v1] = abc[v2] * np.cos(albega[(3 - v1 - v2)])

    return cell_vec


def cell_volume(cell, n_fields=3):
    _cell_vec = cell_vec(cell, n_fields=n_fields)

    return np.dot(_cell_vec[0], np.cross(_cell_vec[1], _cell_vec[2]))


def detect_lattice(cell, priority=(0, 1, 2)):
    '''Obtain lattice system from cell measures.
       Does not care of axis order priority.
       '''
    if cell is None:
        return None
    if np.any(cell == 0.):
        return None

    abc, albega = cell[:3], cell[3:]
    _a = np.invert(np.diff(np.round(abc, decimals=3)).astype(bool))
    _b = np.invert(np.diff(np.round(albega, decimals=3)).astype(bool))

    if np.all(albega == 90.0):
        if np.all(_a):
            return 'cubic'
        elif not np.any(_a):
            return 'orthorhombic'
        else:
            return 'tetragonal'

    if np.sum(albega == 90.0) == 2:
        if 120 in albega and np.any(_a * _b):
            return 'hexagonal'
        elif not np.any(_a):
            return 'monoclinic'
        else:
            _warnings.warn("Unusual lattice!", _ChirPyWarning, stacklevel=2)
            return 'triclinic'

    elif np.all(abc == abc[0]) and np.all(albega == albega[0]):
        return 'rhombohedral'

    else:
        return 'triclinic'


def wrap_pbc(positions, cell):
    '''positions: shape ([n_frames,] n_atoms, three)
       cell: [ a b c al be ga ]'''

    if (lattice := detect_lattice(cell)) not in [None, 'void']:
        if lattice in ['cubic', 'orthorhombic', 'tetragonal']:
            # --- fast
            return positions - np.floor(positions/cell[:3]) * cell[:3]

        else:
            # --- more expensive (ToDo: optimise tensordot, ceb; has np.cross)
            _cell_vec = cell_vec(cell)  # checked: inexpensive
            return positions - np.tensordot(
                                        np.floor(ceb(positions, _cell_vec)),
                                        _cell_vec,
                                        axes=1
                                        )
    else:
        return positions


def dihedral_pbc(p0, p1, p2, p3, cell=None):
    '''p0 <– p1 –> p2 –> p3  with or without periodic boundaries
       accepts cell argument (a b c al be ga).
       '''
    v0 = vector_pbc(p1, p0, cell)
    v1 = vector_pbc(p1, p2, cell)
    v2 = vector_pbc(p2, p3, cell)

    return dihedral(v0, v1, v2)


def angle_pbc(p0, p1, p2, cell=None, signed=False):
    '''p0 <– p1 –> p2  with or without periodic boundaries
       accepts cell argument (a b c al be ga).
       '''
    v0 = vector_pbc(p1, p0, cell)
    v1 = vector_pbc(p1, p2, cell)

    if signed:
        return signed_angle(v0, v1)
    else:
        return angle(v0, v1)


def vector_pbc(p0, p1, cell=None, return_pbc_bool=False, **kwargs):
    '''p1 – p0 with or without periodic boundaries
       accepts cell argument (a b c al be ga).
       '''
    _d = vector(p0, p1)
    if cell is not None:
        _d2 = _d - _pbc_shift(_d, cell, **kwargs)
        if return_pbc_bool:
            # return _d2, not np.allclose(_d, _d2)
            return _d2, _d == _d2
        _d = _d2
    return _d


def mean_pbc(positions, cell=None, axis=0, wrap=True):
    '''average position of atoms without periodic jumps


       cell ... [a b c al be ga]
       positions ... array of shape (N, [n_atoms, dim])
       wrap ... wrap average position into cell
       '''

    mean = np.mean(
                unwrap_pbc(positions, cell=cell, axis=axis),
                axis=axis,
                )
    if wrap:
        return wrap_pbc(mean, cell=cell)
    else:
        return mean


def unwrap_pbc(positions, reference=None, cell=None, axis=0, mode='naive'):
    '''get smooth trajectory of positions without periodic jumps

       positions ... array of shape (n_frames, [n_atoms, dim])
       reference ... positions array of shape(1, [n_atoms, dim] that is
                     prepended to positions before unwrapping.
                     NB: The reference is going to be the first frame of the
                     returned positions.
       mode ...      How to treat non-orthorhombic cells (see _pbc_shift)
       '''

    if cell is not None:
        if reference is None:
            reference = np.take(positions, [0], axis=axis)
        _d = np.diff(positions, axis=axis, prepend=reference)
        _d2 = _d - _pbc_shift(_d, cell, mode=mode)
        return np.cumsum(_d2, axis=axis) + reference
    else:
        return positions


# --- backward compatibility
def distance_pbc(*args, **kwargs):
    return vector_pbc(*args, **kwargs)


def _pbc_shift(_d, cell, mode='naive', priority='auto'):
    '''_d in aa of shape ...
       cell: [ a b c al be ga ]

       Mode defines how non-orthorhombic cells are treated.

       naive ... use fractional coordinates for cubic-style wrap
       priority ... apply cell vectors sequentially according to priority
       accurate ... choose minimum distance from 27 possible wrapping scenarios

       Naive does not yield the minimum distance but ensures the original shape
       of the unit cell.
       Priority creates a rectangular shape and yields minumum image for almost
       all cases.
       Accurate slows down because all 27 possibilities need to be created.

       Naive works for (shortest) distances as long as the maximum distance to
       be found is smaller than half the shortest distance between crystal
       layers.
       '''

    if all([_a <= 0.0 for _a in cell[:3]]):
        return np.zeros_like(_d)

    if not all([_a == 90.0 for _a in cell[3:]]):
        _cell_vec = cell_vec(cell)
        match mode:
            case 'priority':
                if priority == 'auto':
                    _n_nonzero = (_cell_vec**2 > 1.E-8).sum(1)
                    if sum(_n_nonzero == 2) > 1 or sum(_n_nonzero == 3) > 1:
                        _warnings.warn('found general format for cell. '
                                       'Transform into restricted form to '
                                       'avoid wrapping errors',
                                       _ChirPyWarning, stacklevel=2)
                    _order = np.argsort(_n_nonzero)[::-1]
                else:
                    _order = priority

                _d_pbc = copy.deepcopy(_d)
                for _i in _order:
                    _d_pbc -= \
                            np.around(_d_pbc/_cell_vec[_i, _i])[..., _i, None]\
                            * _cell_vec[_i]
                return _d - _d_pbc

            case 'accurate':
                _lattice_combinations = \
                    list(product([0, 1, -1], repeat=3)) @ _cell_vec
                _I = np.argmin(
                        np.linalg.norm(
                            [_d - _L for _L in _lattice_combinations],
                            axis=-1
                            ),
                        axis=0
                        )
                return np.take(_lattice_combinations, _I, axis=0)

            case 'naive' | _:
                _c = ceb(_d, _cell_vec)
                return np.tensordot(np.around(_c), _cell_vec, axes=1)

    else:
        return np.around(_d/cell[:3]) * cell[:3]


# --- ToDo: rename the next two methods
def get_cell_coordinates(positions, cell, angular=False):
    '''Transform Cartesian coordinates into cell vector basis.
       angular=True for transformation of angular magnitudes
       of the form p × p or p × v
       '''
    _cell_vec = cell_vec(cell)
    if angular:
        _cell_vec = np.linalg.det(_cell_vec) * np.linalg.inv(_cell_vec).T
    return ceb(positions, _cell_vec)


def get_cartesian_coordinates(positions, cell, angular=False):
    '''Transform cell coordinates into Cartesian basis
       angular=True for transformation of angular magnitudes
       of the form p × p or p × v
       '''
    _cell_vec = cell_vec(cell)
    if angular:
        _cell_vec = np.linalg.det(_cell_vec) * np.linalg.inv(_cell_vec).T

    return positions @ _cell_vec
    # match len(positions.shape):
    #     case 1:
    #         return np.einsum('i, ij -> j',
    #                          positions,
    #                          _cell_vec
    #                          )
    #     case 2:
    #         return np.einsum('ni, ij -> nj',
    #                          positions,
    #                          _cell_vec
    #                          )
    #     case 3:
    #         return np.einsum('kni, ij -> knj',
    #                          positions,
    #                          _cell_vec
    #                          )


def distance_matrix(p0, p1=None, cell=None, cartesian=False,
                    return_pbc_bool=False, **kwargs):
    '''Expects one or two args of shape (n_atoms, three) ... (FRAME).
       Order: p0, p1 ==> d = p1 - p0

       Supports periodic boundaries (give cell as [x, y, z, al, be, ga];
                                     angles in degrees).
       '''
    # ToDo: the following lines explode memory for many atoms
    #   ==> do coarse mapping beforehand
    # (overlapping batches) or set a max limit for n_atoms
    # For now:
    if p1 is None:
        p1 = p0

    # if len(p0.shape) > 2 or len(p1.shape) > 2:
    #     raise ValueError('distance_matrix only accepts positions of shape '
    #                      '(n_atoms, dim) or (n_frames, dim)!')
    if (_max := max(p0.shape[0], p1.shape[0])) > 10000:
        print(_max)
        raise MemoryError('Too many atoms for molecular recognition'
                          '(>10000 atom support in a future version)!'
                          )
    if return_pbc_bool:
        dist_array, B = vector_pbc(p0[:, None], p1[None, :], cell=cell,
                                   return_pbc_bool=return_pbc_bool, **kwargs)
    else:
        dist_array = vector_pbc(p0[:, None], p1[None, :], cell=cell, **kwargs)

    if cartesian:
        _return = (dist_array,)
    else:
        _return = (np.linalg.norm(dist_array, axis=-1),)

    if return_pbc_bool:
        _return += (B,)

    return _unpack_tuple(_return)


def neighbour_matrix(pos_aa, symbols, cell_aa_deg=None,
                     return_distances=False, cartesian=False,
                     return_pbc_bool=False):
    '''Create sparse matrix with entries 1 for neighbouring atoms.
       Expects positions in angstrom of shape (n_atoms, three).
       '''
    symbols = np.array(symbols)
    if return_pbc_bool:
        dist_array, B = distance_matrix(pos_aa, cell=cell_aa_deg,
                                        cartesian=cartesian,
                                        return_pbc_bool=return_pbc_bool,
                                        mode='naive')
    else:
        dist_array = distance_matrix(pos_aa, cell=cell_aa_deg,
                                     cartesian=cartesian,
                                     mode='naive')
    # --- working copy
    if cartesian:
        _dist_array = np.linalg.norm(dist_array, axis=-1)
    else:
        _dist_array = copy.deepcopy(dist_array)
    _dist_array[_dist_array == 0.0] = 'Inf'

    # --- ToDo: Do valency check instead

    # --- clean matrix for hydrogen atoms
    _hind = symbols == 'H'
    _hmin = np.argmin(_dist_array[_hind], axis=-1)
    _dist_array[_hind] = 'Inf'
    _dist_array[:, _hind] = 'Inf'
    _dist_array[_hind, _hmin] = 0.0
    _dist_array[_hmin, _hind] = 0.0
    crit_aa = dist_crit_aa(symbols)

    _return = (_dist_array <= crit_aa,)
    if return_distances:
        _return += (dist_array,)
    if return_pbc_bool:
        _return += (B,)

    return _unpack_tuple(_return)


def nearest_neighbour(p0, p1=None, cell=None, ignore=None,
                      return_distances=False):
    if p1 is None:
        p1 = p0
    _dists = distance_matrix(p0, p1, cell=cell)
    if ignore is not None:
        _dists[:, ignore] = np.inf
    if not return_distances:
        return np.argmin(_dists, axis=1)
    else:
        return np.argmin(_dists, axis=1), np.amin(_dists, axis=1)


def close_neighbours(p0, cell=None, crit=None, symbols=None):
    _dM = distance_matrix(p0, cell=cell)
    if crit is None:
        if symbols is None:
            crit = 1.E-7
        else:
            crit = dist_crit_aa(symbols) / 2.0

    return [(_i, [(_j, _dM[_i, _j]) for _j in np.argwhere(_idM).flatten()])
            for _i, _idM in enumerate(np.triu(_dM <= crit, k=1))
            if np.any(_idM)]


def connectivity(pos_aa, symbols, cell_aa_deg=None):
    '''For each atom return covalently bound neighbours.
       pos_aa:       np.array of shape (n_atoms, three) in angstrom
       symbols:      tuple of length n_atoms containing element symbols
       cell_aa_deg:  cell parametres (1 b c al be ga) in angstrom/degrees
                     (optional)
    '''
    neighs = neighbour_matrix(pos_aa, symbols, cell_aa_deg=cell_aa_deg)
    return [np.argwhere(_n).ravel() for _n in neighs]


def join_molecules(pos_aa, mol_map, cell_aa_deg,
                   weights=None,
                   algorithm='connectivity',
                   symbols=None,
                   connectivity=None,
                   fast_forward=True,
                   reference=None,
                   ):
    '''pos_aa (in angstrom) with shape ([n_frames,] n_atoms, three)
    Has still problems with cell-spanning molecules
    Molecules have to be numbered starting with 0!

    fast_forward ... join molecules for first frame only and track atom
                     positions based on this frame (unwrap positions). Exact
                     for immutable topologies, quite reliabe otherwise (double
                     check required!).
    reference ... if algorithm is set to 'reference', use reference positions
                   (1, n_atoms, three) of already joined molecules.
                   Similar to fast_forward.
    '''
    if 0 not in mol_map:
        raise TypeError('Given mol_map not an enumeration of indices!' %
                        mol_map)
    pos_aa = np.moveaxis(pos_aa, -2, 0)
    _shape = pos_aa.shape
    n_atoms = _shape[0]
    if weights is None:
        weights = np.ones((n_atoms))
    w = dec(weights, mol_map)

    try:
        _sym = dec(symbols, mol_map)
    except TypeError:
        if algorithm == 'connectivity':
            raise ValueError('connectivity requires symbols argument')
        _sym = np.ones((n_atoms))

    _pos_aa = dec(pos_aa, mol_map)
    mol_com_aa = []
    # --- NB: looping over molecules to reduce memory overhead
    # for _i, (_w, _s, _p) in tqdm.tqdm(
    #                         enumerate(zip(w, _sym, _pos_aa)),
    #                         disable=not config.__verbose__,
    #                         desc='join molecules',
    #                         total=len(_sym),
    #                         ):
    for _i, (_w, _s, _p) in enumerate(zip(w, _sym, _pos_aa)):
        if len(_p.shape) == 3:
            _frames = True
            n_frames = _shape[1]
            _p_ref = _p[:, 0]
        else:
            _frames = False
            _p_ref = _p

        if algorithm == 'connectivity':
            # --- ToDo: do not always recalculate D and N (store it in object)
            N, D, B = neighbour_matrix(_p_ref, _s,
                                       cell_aa_deg=cell_aa_deg,
                                       return_distances=True,
                                       cartesian=True,
                                       return_pbc_bool=True)
            if not _frames and B.all():  # --- molecule not broken
                # --- ensure mol cowt lies within cell
                c_aa = cowt(_p, _w, axis=0)
                _delta = wrap_pbc(c_aa, cell_aa_deg) - c_aa
                mol_com_aa.append(c_aa + _delta)
                ind = np.array(mol_map) == _i
                pos_aa[ind] = _p + _delta[None]
                continue

            _m_n_atoms = len(_p)
            if _frames and not fast_forward:
                _p_ref = _p.reshape((_m_n_atoms, -1))
            P = np.zeros_like(_p_ref)
            n = np.zeros(_m_n_atoms).astype(bool)
            # --- set reference particle
            # ----- closest to its neighbours:
            # _r = np.argmin(np.linalg.norm(D, axis=(1, 2)))
            # ----- w/ weighting:
            _r = np.argmin(np.linalg.norm(D, axis=(1, 2)) / _w)
            # ----- closests to cell center (for tetragonal cells):
            # _r = np.argmin(np.linalg.norm(_p_ref - cell_aa_deg[None, :3]/2,
            #                               axis=-1) / _w)

            n[_r] = True
            P[n] = _p_ref[n]
            n0 = n  # np.zeros(_m_n_atoms).astype(bool)
            n_1 = np.ones(_m_n_atoms).astype(bool)
            _n_iter = 0
            while True:
                if (_S_n0 := n0.sum()) == n_1.sum():
                    if _S_n0 < _m_n_atoms:
                        # _warnings.warn("connectivity interrupted in "
                        #                "molecular map.", _ChirPyWarning,
                        #                stacklevel=2)
                        # --- create additional link to nearest atom
                        not_n0 = (np.ones(_m_n_atoms) - n0).astype(bool)
                        _r = np.argmin(
                                np.linalg.norm(D[n0][:, not_n0],
                                               axis=-1)
                                )
                        _ind = np.unravel_index(_r, (_S_n0, _m_n_atoms-_S_n0))
                        N[np.argwhere(n0)[_ind[0]],
                          np.argwhere(not_n0)[_ind[1]]] = 1
                    else:
                        break
                m = np.einsum('ij, i -> j', N, n0.astype(int))
                n = m.astype(bool)
                if _frames and not fast_forward:
                    # --- process all frames individually
                    # --- assuming constant connectivity through N
                    # --- ToDo: if N is constant, fast_forward is always exact
                    #           ---> implement variable N
                    _D = np.moveaxis(np.array(
                        [distance_matrix(_p[n0, _ii], _p[n, _ii],
                                         cell=cell_aa_deg, cartesian=True)
                         # for _ii in tqdm.tqdm(
                         #              range(n_frames),
                         #              disable=not config.__verbose__,
                         #              desc=f'mol {_i} (iteration {_n_iter})',
                         #              )]), 0, -2)
                         for _ii in range(n_frames)]), 0, -2)
                    _D = _D.reshape((n0.sum(), n.sum(), -1))
                    _NP = np.einsum('ijk, ij -> jk', P[n0, None]+_D,
                                    N[n0][:, n])
                    P[n] = _NP / m[n, None]
                else:
                    _NP = np.einsum('ijk, ij -> jk', P[n0, None]+D[n0], N[n0])
                    P[n] = _NP[n] / m[n, None]
                n_1 = copy.deepcopy(n0)
                n0 |= n
                _n_iter += 1
                if _n_iter >= _m_n_atoms:
                    raise ValueError('could not join molecules after '
                                     f'{_n_iter} iterations. Perhaps '
                                     'the connectivity is interrupted.')

            if _frames:
                if not fast_forward:
                    P = P.reshape((_m_n_atoms, n_frames, 3))
                else:
                    P = unwrap_pbc(
                            _p,
                            reference=P[:, None],
                            cell=cell_aa_deg,
                            axis=-2,
                            )

        elif algorithm == 'reference':
            if _frames:
                raise NotImplementedError('joining molecules with reference ',
                                          'only available for single frames')
            _ref = dec(reference, mol_map)
            P = unwrap_pbc(
                    _p[None],
                    reference=_ref[_i][None],
                    cell=cell_aa_deg,
                    axis=0,
                    )[-1]

        # --- legacy code
        # elif algorithm == 'closest':
        #     # --- find atom that is closest to its counterparts
        #     # --- ToDo: NOT WORKING well for cell-spanning molecules
        #     _r = np.argmin(np.linalg.norm(distance_matrix(
        #                                               _p_ref,
        #                                               cell=cell_aa_deg,
        #                                               ),
        #                                   axis=1))
        # elif algorithm == 'heavy_atom':
        #     # --- fast, but error-prone: use the heaviest atom as reference
        #     _r = np.argmax(_w)

        else:
            raise ValueError(f'got unknown algorithm {algorithm} for joining '
                             'molecules')

        c_aa = cowt(P, _w, axis=0)
        # --- ensure mol cowt lies within cell
        #     (ToDo: make this optional)
        #     (ToDo: choose _r such that this line is no required)
        #       ---> actually possible? use B?
        _delta = wrap_pbc(c_aa, cell_aa_deg) - c_aa
        mol_com_aa.append(c_aa + _delta)
        ind = np.array(mol_map) == _i
        pos_aa[ind] = P + _delta[None]

        # --- legacy code (2)
        # --- complete mols
        # _p -= _pbc_shift(_p - _p[_r, :], cell_aa_deg)
        # c_aa = cowt(_p, _w, axis=0)
        # mol_com_aa.append(c_aa)
        # _p -= c_aa[None, :]

        # # --- wrap molecular com into cell
        # #     (performance bottleneck?)
        # mol_com_aa = wrap(np.array(mol_com_aa), cell_aa_deg)

        # # --- wrap set of pos
        # for _i, _com in enumerate(mol_com_aa):
        #     # --- in-loop to retain order (np.argsort=unreliable)
        #     ind = np.array(mol_map) == _i
        #     pos_aa[ind] = _pos_aa[_i] + _com[None, :]

    return np.moveaxis(pos_aa, 0, -2), np.moveaxis(np.array(mol_com_aa), 0, -2)


def get_atom_spread(pos):
    return np.array([np.amax(_p) - np.amin(_p)
                     for _p in np.moveaxis(pos, -1, 0)])


def align_atoms(positions, weights, reference=None, subset=slice(None),
                data=None, return_Rmatrix=False):
    '''Align atoms within trajectory or with respect to an external reference.

       positions ... array of shape ([n_frames,] n_atoms, three)
       weights   ... float or iterable of length n_atoms
       data      ... list of supplemental atom data (e.g., [velocities,]) to be
                     transformed along with positions
                     (each data item: array of shape like positions)
       return_Rmatrix ... for each frame return the rotation matrix that
                          aligns the coordinates to the reference
       '''

    _sub = subset
    _data = data

    # --- no frame dimension: set it to one
    if len(positions) == 2:
        pos_mob = np.array([copy.deepcopy(positions)])

    else:
        pos_mob = copy.deepcopy(positions)

    if not hasattr(weights, '__len__'):
        w = np.ones(pos_mob.shape[-2]) * weights
    else:
        w = np.array(weights)

    # --- get subset data sets
    # --- default reference: frame 0
    if reference is None:
        reference = positions[0][_sub]
    _s_pos_ref = copy.deepcopy(reference)
    _s_pos_mob = pos_mob[:, _sub]

    # --- get com of data sets
    com_ref = cowt(_s_pos_ref, w[_sub], axis=-2)
    com_mob = cowt(_s_pos_mob, w[_sub], axis=-2)

    # --- apply com (reference can be frame or trajectory)
    _i_s_pos_ref = np.moveaxis(_s_pos_ref, -2, 0)
    _s_pos_ref = np.moveaxis(_i_s_pos_ref - com_ref[(None,)], 0, -2)
    _i_pos_mob = np.moveaxis(pos_mob, -2, 0)
    pos_mob = np.moveaxis(_i_pos_mob - com_mob[(None,)], 0, -2)
    # --- repeat
    _s_pos_mob = pos_mob[:, _sub]
    del _i_s_pos_ref, _i_pos_mob

    Rmatrix = ()
    for frame, P in enumerate(_s_pos_mob):
        U = kabsch_algorithm(P * w[_sub, None], _s_pos_ref * w[_sub, None])
        pos_mob[frame] = rotate_vector(pos_mob[frame], U)
        if _data is not None:
            for _d in _data:
                _d[frame] = rotate_vector(_d[frame], U)
        Rmatrix += (U,)

    # --- define return shift
    com_return = com_ref

    _slc = (len(pos_mob.shape) - len(com_return.shape)) * (None,)
    pos_mob += com_return[_slc]

    _return = (pos_mob,)
    if _data is not None:
        _return += (_data,)
    if return_Rmatrix:
        _return += (np.array(Rmatrix),)

    return _unpack_tuple(_return)


def find_methyl_groups(pos, symbols, hetatm=False, cell_aa_deg=None):
    '''pos of shape (n_atoms, n_fields) (FRAME)
       Outformat is C H H H'''

    dist_array = distance_matrix(pos, cell=cell_aa_deg)
    n_atoms = len(symbols)
    symbols = np.array(symbols)

    indh = symbols == 'H'
    if hetatm:
        ind = symbols != 'H'
    else:
        ind = symbols == 'C'
    ids = np.arange(n_atoms) + 1
    out = [[ids[i], [ids[j] for j in range(n_atoms)
            if dist_array[i, j] < dist_crit_aa(symbols)[i, j] and indh[j]]]
           for i in range(n_atoms) if ind[i]]

    out = '\n'.join(['A%03d ' % i[0]+'A%03d A%03d A%03d' % tuple(i[1])
                     for i in out if len(i[1]) == 3])

    print(out)


def isHB(*args, **kwargs):
    return ishydrogenbond(*args, **kwargs)


def ishydrogenbond(positions, donor, acceptor, hydrogens,
                   cell=None,
                   dist_crit=3.0,
                   angle_crit=130):
    '''Returns a bool / an array of bools stating if there is a
       hydrogen bond (HB) between donor and acceptor (heavy atoms).

       positions … position array of shape (n_atoms, 3)
       donor/acceptor … atom indices of heavy atoms donating/accepting HBs
       hydrogen … indices of the (sub)set of hydrogen atoms

       dist_crit … float in units of positions
       angle_crit … float in degrees

       returns: bool array of shape (n_donors, n_acceptors)
       '''

    _angle_crit = angle_crit / 180 * np.pi
    _hyd = np.array(hydrogens)

    if len(positions.shape) != 2:
        raise ValueError('Expected shape length 2 for positions, got %s: %s'
                         % (len(positions.shape), positions.shape))

    # --- sinussatz für maximale O-H-O-Kette
    dist_crit_dha = dist_crit / np.sin(_angle_crit) \
        * np.sin((np.pi - _angle_crit) / 2) * 2

    _dist_da = distance_matrix(positions[donor], positions[acceptor],
                               cell=cell)
    _eligible = _dist_da <= dist_crit

    # --- loop over eligible pairs and find H atom
    answer = np.zeros((len(donor), len(acceptor))).astype(bool)

    for _d, _a in np.argwhere(_eligible):
        _ai = acceptor[_a]
        _di = donor[_d]

        _dist_dah = distance_matrix(positions[[_di, _ai]], positions[_hyd],
                                    cell=cell)
        _pre_h = np.argwhere(_dist_dah[0] <= dist_crit_dha / 2.).flatten()

        if len(_pre_h) == 0:
            _warnings.warn('No hydrogen atom found at donor %d' % _di,
                           _ChirPyWarning,
                           stacklevel=2)

        _h = np.argmin(_dist_dah[1, _pre_h])
        _hi = _hyd[_pre_h][_h]

        if _dist_dah[:, _pre_h[_h]].sum(axis=0) <= dist_crit_dha:
            _angle_dah = angle_pbc(*positions[[_di, _hi, _ai]], cell=cell)
            if _angle_dah >= _angle_crit:
                answer[_d, _a] = True

    return answer


def guess_atom_types(pos_aa,
                     symbols,
                     cell_aa_deg=None,
                     classification='integer',
                     similarity='connectivity',
                     order=1):
    '''Define atom types and assign them to each atom using similarity kernel
       (default: connectivity).
       Atom types can be arbitrary integers (default) or actual pre-defined
       types as used by common force fields (NOT YET IMPLEMENTED).

       pos_aa:       np.array of shape (n_atoms, three) in angstrom
       symbols:      tuple of length n_atoms containing element symbols
       cell_aa_deg:  cell parametres (1 b c al be ga) in angstrom/degrees
                     (optional)

       Return:       tuple of atom types
    '''
    if classification != 'integer':
        raise NotImplementedError('Only integer classification supported!')

    # duplicate of method in dissection; ToDo: externalise/unify method
    # (and rename it)
    def assign_molecule(molecule, n_mol, n_atoms, neigh_map, atom, atom_count):
        '''This method can do more than molecules! See BoxObject
        molecule … assignment
        n_mol … species counter
        n_atoms … total number of entries
        neigh_map … list of neighbour atoms per atom
        atom … current line in reading neighbour map
        atom_count … starts with n_atoms until zero
        '''
        molecule[atom] = n_mol
        atom_count -= 1
        for _i in neigh_map[atom]:
            if molecule[_i] == 0:
                molecule, atom_count = assign_molecule(
                    molecule,
                    n_mol,
                    n_atoms,
                    neigh_map,
                    _i,
                    atom_count
                    )
                # print(atom_count)
            if atom_count == 0:
                break
        return molecule, atom_count

    def assign_types(character, kernel):
        '''general evaluation of similarity kernel'''
        similarity = np.array([[_i for _i, _ch1 in enumerate(character)
                                if _ch1 == _ch0]
                               for _ch0 in character])
        n_types = 0
        n_atoms = atom_count = len(character)

        atom_types = np.zeros((n_atoms)).astype(int)

        for atom in range(n_atoms):
            if atom_types[atom] == 0:
                n_types += 1
                atom_types, atom_count = assign_molecule(atom_types,
                                                         n_types,
                                                         n_atoms,
                                                         similarity,
                                                         atom,
                                                         atom_count)
            if atom_count == 0:
                break

        return atom_types

    if similarity == 'connectivity':
        _core = connectivity(pos_aa, symbols, cell_aa_deg=cell_aa_deg)

        _character = [(_s,) for _s in symbols]
        if order > 0:
            _character = [_ch + tuple(sorted(np.array(symbols)[_s]))
                          for _ch, _s in zip(_character, _core)]
        if order > 1:
            _character = [_ch + tuple(sorted(
                                        [tuple(sorted(np.array(symbols)[_ss]))
                                         for _ss in _core[_s]]
                                        ))
                          for _ch, _s in zip(_character, _core)]

        def _kernel(x, y):
            return x == y

    elif similarity == 'SOAP':
        raise NotImplementedError('SOAP kernels are not yet supported!')

    else:
        raise ValueError('Unknown similarity kernel: %s' % similarity)

    atom_types = assign_types(_character, _kernel)

    return atom_types
