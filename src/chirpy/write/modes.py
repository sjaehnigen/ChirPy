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


def xvibsWriter(filename, n_atoms, numbers, pos_aa, freqs, modes):
    '''Write an XVIBS file with Cartesian displacements in angstrom'''

    obuffer = '&XVIB\n NATOMS\n %d\n COORDINATES\n' % n_atoms
    for n, r in zip(numbers, pos_aa):
        obuffer += ' %d  %16.12f  %16.12f  %16.12f\n' % tuple([n] + list(r))
    obuffer += ' FREQUENCIES\n %d\n' % len(freqs)
    for f in freqs:
        obuffer += ' %16.12f\n' % f
    obuffer += ' MODES\n'
    n_modes, atoms, three = modes.shape
    modes = modes.reshape((n_modes * atoms, 3))
    for mode in modes:
        obuffer += ' %16.12f  %16.12f  %16.12f\n' % tuple(mode)
    obuffer += '&END\n'

    with open(filename, 'w') as f:
        f.write(obuffer)
