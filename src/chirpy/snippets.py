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

import numpy as _np
import warnings
from . import config


# --- code snippets
def extract_keys(dict1, **defaults):
    '''Updates the key/value pairs of defaults with those of dict1.
       Similar to defaults.update(dict1), but it does not ADD any new keys to
       defaults.'''
    return {_s: dict1.get(_s, defaults[_s]) for _s in defaults}


def tracked_extract_keys(dict1, **defaults):
    '''Updates the key/value pairs of defaults with those of dict1.
       Similar to defaults.update(dict1), but it does not ADD any new keys to
       defaults.
       Warns if existing data is changed.'''
    msg = defaults.pop('msg', 'in dict1!')
    new_dict = {_s: dict1.get(_s, defaults[_s]) for _s in defaults}
    return tracked_update(defaults, new_dict, msg=msg)


def tracked_update(dict1, dict2, msg='in dict1!'):
    '''Update dict1 with dict2 but warns if existing data is changed'''
    for _k2 in dict2:
        _v1 = dict1.get(_k2)
        _v2 = dict2.get(_k2)
        if _v1 is not None:
            if not equal(_v1, _v2):
                with warnings.catch_warnings():
                    warnings.warn('Overwriting existing key '
                                  '\'{}\' '.format(_k2) + msg,
                                  config.ChirPyWarning,
                                  stacklevel=2)
    dict1.update(dict2)
    return dict1


def equal(a, b):
    '''return all-equal regardless of type'''
    if isinstance(a, _np.ndarray) or isinstance(b, _np.ndarray):
        return _np.all(a == b)
    else:
        return a == b


def _unpack_tuple(x):
    """ Unpacks one-element tuples for use as return values

        Taken from:
        https://github.com/numpy/numpy/blob/v1.20.0/numpy/lib/arraysetops.py
        Copyright (c) 2005-2021, NumPy Developers.

        """
    if len(x) == 1:
        return x[0]
    else:
        return x
