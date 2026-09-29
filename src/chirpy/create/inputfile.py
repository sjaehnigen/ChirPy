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

"""Writers for simple quantum-chemistry input files."""

from ..interface import cpmd


class QMCalculation():
    """Container for basic quantum-calculation settings."""

    def __init__(self, *args, **kwargs):
        """Initialise default calculation parameters."""
        self.functional = None
        self.type = 'MD sampling'
        self.eps = 1.E-7

    def write_input_file(self, fn, code='cpmd'):
        """Write an input file for the selected backend."""
        if code == 'cpmd':
            cpmd.CPMDjob().write_input_file(fn)
