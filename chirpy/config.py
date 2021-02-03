# -------------------------------------------------------------------
#
#  ChirPy
#
#    A buoyant python package for analysing supramolecular
#    and electronic structure, chirality and dynamics.
#
#    https://hartree.chimie.ens.fr/sjaehnigen/chirpy.git
#
#
#  Copyright (c) 2010-2020, The ChirPy Developers.
#
#
#  Released under the GNU General Public Licence, v3
#
#   ChirPy is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published
#   by the Free Software Foundation, either version 3 of the License.
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
# -------------------------------------------------------------------

import sys
import importlib
import warnings
from IPython import get_ipython


__verbose__ = True


def set_verbose(s):
    '''Enable/disable chirpy runtime verbosity.'''
    global __verbose__
    __verbose__ = bool(s)
    # --- apply changes to loaded modules, except for this config module
    modules = tuple(sys.modules.values())
    for module in modules:
        if 'chirpy' in module.__name__ and 'config' not in module.__name__:
            importlib.reload(module)


# --- check if run in ipython/jupyter notebook
if get_ipython() is not None:
    if "IPKernelApp" in get_ipython().config:
        warnings.warn('jupyter: enabling chirpy verbosity', stacklevel=2)
        set_verbose(True)
