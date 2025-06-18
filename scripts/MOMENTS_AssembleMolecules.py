#!/usr/bin/env python
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

import argparse
import numpy as np
import warnings
import tqdm

from chirpy.create.moments import OriginGauge
from chirpy.classes import system, trajectory
from chirpy.topology import mapping
from chirpy import constants
from chirpy.physics import classical_electrodynamics as ed
from chirpy.interface import cpmd
from chirpy import config


def main():
    parser = argparse.ArgumentParser(
            description="Process MOMENTS output of electronic (Wannier)\
                         states and add (classical) nuclear contributions to\
                         generate molecular moments based on a given\
                         topology.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
            )
    parser.add_argument(
            "TOPOLOGY",
            help="PDB file with topology including cell specifications"
            )
    parser.add_argument(
            "TRAJECTORY",
            help="(classical) nuclear part with positions and velocities."
            )
    parser.add_argument(
            "MOMENTS",
            help="(quantum) electronic part with localised (Wannier) gauge "
                 "positions, current dipole, and magnetic dipole moments."
            )
    parser.add_argument(
            "--T_format",
            help="File format of TRAJECTORY (e.g. xyz, tinker, cpmd)",
            default='cpmd',
            )
    parser.add_argument(
            "--M_format",
            help="File format of MOMENTS (e.g. cpmd, tinker)",
            default='cpmd',
            )
    parser.add_argument(
            "--T_units",
            help="Column units of TRAJECTORY.",
            default='default',
            )
    parser.add_argument(
            "--M_units",
            help="Column units of MOMENTS.",
            default='default',
            )
    parser.add_argument(
            "--electronic_centers",
            help="(Wannier) centers of charge of electronic part "
                 "(for better assignment of electrons and --position_form)."
            )
    parser.add_argument(
            "--EC_format",
            help="File format of --electronic_centers (e.g. cpmd, tinker)",
            default='cpmd',
            )
    parser.add_argument(
            "--EC_units",
            help="Column units of --electronic_centers.",
            default='default',
            )
    parser.add_argument(
            "--position_form",
            action='store_true',
            help="also compute the electric dipole moment and add it to "
                 "the output file.",
            default=False,
            )
    parser.add_argument(
            "--center_of_geometry", "--cog",
            help="Do not use atom masses as weights for centering and \
                    wrapping of molecules",
            action='store_true',
            default=False,
            )
    parser.add_argument(
            "--range",
            nargs=3,
            help="Frame range for reading files. Frame numbers are not "
                 "preserved in output",
            default=None,
            type=int,
            )
    parser.add_argument(
            "--batch_size",
            help="No. of frames processed at once. Needs to be reduced for "
                 "very large molecules or low memory availability.",
            default=1000000,
            type=int,
            )
    parser.add_argument(
            "--outputfile", "-o", "-f",
            help="Output file name",
            default='MOL'
            )
    parser.add_argument(
            "--do_not_join",
            action='store_true',
            help="Do not join molecules before computing gauge (faster). "
                 "Enable ONLY if molecules are not broken across boundaries.",
            default=False,
            )
    parser.add_argument(
            "--ignore_electronic_magnetization",
            action='store_true',
            help="Do not include magnetic polarization of the "
                 "electronic wave function (use centers of charge only).",
            default=False,
            )
    parser.add_argument(
            "--ignore_electronic_polarization",
            action='store_true',
            help="Do not include electric polarization of the "
                 "electronic wave function (use centers of charge only).",
            default=False,
            )
    parser.add_argument(
            "--verbose",
            action='store_true',
            help="Print info and progress.",
            default=False,
            )

    args = parser.parse_args()
    if args.range is None:
        args.range = (0, 1, float('inf'))
    config.set_verbose(args.verbose)

    if not args.center_of_geometry:
        weights = 'masses'
    else:
        weights = None

    if args.verbose:
        print('Preparing data ...')
    SYS = system.Supercell(args.TRAJECTORY,
                           fmt=args.T_format,
                           range=args.range,
                           units=args.T_units,
                           fn_topo=args.TOPOLOGY,
                           weights=weights,
                           # --- generate mol centers, costly
                           wrap_molecules=False,
                           )
    MOMENTS = trajectory.MOMENTS(args.MOMENTS,
                                 fmt=args.M_format,
                                 range=args.range,
                                 units=args.M_units,
                                 )
    if args.electronic_centers is not None:
        CENTERS = trajectory.XYZ(args.electronic_centers,
                                 fmt=args.EC_format,
                                 range=args.range,
                                 units=args.EC_units,
                                 # fn_topo=args.TOPOLOGY,
                                 )
    if args.verbose:
        print('')

    def _get_batch(batch=None):
        _return = (
                MOMENTS.expand(batch=batch, ignore_warning=True),
                SYS.XYZ.expand(batch=batch, ignore_warning=True),
                )
        if args.electronic_centers is not None:
            _return += (CENTERS.expand(batch=batch, ignore_warning=True),)
        else:
            _return += (None,)
        return _return

    _iframe = 0
    while True:
        if args.verbose:
            print(f'Loading batch [{_iframe}:{_iframe+args.batch_size}]')
        ELE, NUC, WC = _get_batch(batch=args.batch_size)
        if None in [ELE, NUC]:
            if args.verbose:
                print('--- END OF TRAJECTORY')
            break
        if not args.do_not_join:
            if args.verbose:
                print('Wrapping molecules ...')
                print(f'Atom weights for molecular centers: {weights}')

            NUC.wrap_molecules(SYS.mol_map, weights=weights)
        else:
            if args.verbose:
                print('Computing molecular centers ...')
            if not args.center_of_geometry:
                NUC.get_center_of_mass(mask=SYS.mol_map, join_molecules=False)
            else:
                NUC.get_center_of_geometry(mask=SYS.mol_map,
                                           join_molecules=False)

        if args.verbose:
            print('Assembling moments ...')

        # --- test for neutrality of charge
        if (_total_charge := ELE.n_atoms * (-2) +
                constants.symbols_to_valence_charges(NUC.symbols).sum()) != 0.:
            warnings.warn(f'Got non-zero cell charge {_total_charge}!',
                          config.ChirPyWarning, stacklevel=2)

        n_map = np.array(SYS.mol_map)
        _cell = SYS.cell_aa_deg

        if args.ignore_electronic_magnetization:
            ELE.m_au *= 0
        if args.ignore_electronic_polarization:
            ELE.c_au *= 0

        # --- generate classical nuclear moments
        Qn_au = constants.symbols_to_valence_charges(NUC.symbols)
        gauge_n = OriginGauge(
               origin_aa=NUC.pos_aa,
               current_dipole_au=ed.current_dipole_moment(NUC.vel_au, Qn_au),
               magnetic_dipole_au=np.zeros_like(NUC.vel_au),
               charge_au=Qn_au,
               cell_aa_deg=_cell,
               )

        # --- load Wannier data and get nearest atom assignment
        gauge_e = OriginGauge(
               origin_aa=ELE.pos_aa,
               current_dipole_au=ELE.c_au,
               magnetic_dipole_au=ELE.m_au,
               charge_au=-2,
               cell_aa_deg=_cell,
               )

        # --- shift gauge to electric centers (optional)
        if args.electronic_centers is not None:
            gauge_e.shift_origin_gauge(WC.pos_aa)
        if args.position_form:
            if args.M_format != 'cpmd':
                warnings.warn('assuming valence charges for atoms. No core '
                              'electrons considered.',
                              stacklevel=2)
            for _gauge in [gauge_e, gauge_n]:
                _gauge.d_au = np.zeros_like(_gauge.c_au)
                _gauge._set += 'd'

        # --- ensure that electronic centers have the same order
        #     (not guaranteed by CPMD output) + assignment
        #     This assumes that the number of centers per nucleus
        #     does not change.

        # --- to ensure correct wrapping of the centers, we switch to the
        #     distributed nuclear gauge, before switching to the distributed
        #     molecular gauge

        wc_origins_aa = []
        _noh = np.array(NUC.symbols) != 'H'

        for _iiframe in tqdm.tqdm(
                              range(ELE.n_frames),
                              disable=not args.verbose,
                              desc='map electronic centers --> nuclei',
                              ):
            # --- find nearest heavy nucleus
            N = np.arange(gauge_n.n_units)[_noh][
                    mapping.nearest_neighbour(
                        gauge_e.r_au[_iiframe] * constants.l_au2aa,
                        gauge_n.r_au[_iiframe, _noh] * constants.l_au2aa,
                        cell=_cell
                        )
                    ]
            # --- molecular assignment
            _e_map = n_map[N]
            _slist = np.argsort(_e_map)

            # --- tweak OriginGauge
            gauge_e.r_au[_iiframe] = gauge_e.r_au[_iiframe, _slist]
            gauge_e.c_au[_iiframe] = gauge_e.c_au[_iiframe, _slist]
            gauge_e.m_au[_iiframe] = gauge_e.m_au[_iiframe, _slist]
            gauge_e.q_au[_iiframe] = gauge_e.q_au[_iiframe, _slist]
            # if args.position_form:
            #     gauge_e.d_au[_iiframe] = gauge_e.d_au[_iiframe, _slist]

            # --- remember position of reference
            wc_origins_aa.append(NUC.pos_aa[_iiframe, N][_slist])

        e_map = np.sort(_e_map)
        # --- shift electronic gauge to reference nuclei
        gauge_e.shift_origin_gauge(np.array(wc_origins_aa))

        # --- combine nuclear and electronic contributions
        gauge = gauge_e + gauge_n
        assignment = np.concatenate((e_map, n_map))

        # --- NB: After joining molecules and assigning electronic centers the
        #     cell has to be switched off to avoid re-wrapping!
        gauge.cell_au_deg = None

        # --- shift to molecular origins
        if not args.center_of_geometry:
            _com = NUC.mol_com_aa
        else:
            _com = NUC.mol_cog_aa
        gauge.shift_origin_gauge(_com, assignment)

        # --- test for neutrality of charge
        if np.any((_mol := gauge.q_au != 0.0)):
            warnings.warn('Got non-zero charge for (frame, molecule) '
                          f'{tuple(zip(*np.where(_mol)))}: {gauge.q_au[_mol]}',
                          config.ChirPyWarning, stacklevel=2)

        # --- write output
        append = False
        if _iframe > 0:
            append = True

        if args.position_form:
            _data = np.concatenate((gauge.r_au*constants.l_au2aa,
                                    gauge.c_au,
                                    gauge.m_au,
                                    gauge.d_au), axis=-1)
        else:
            _data = np.concatenate((gauge.r_au*constants.l_au2aa,
                                    gauge.c_au,
                                    gauge.m_au), axis=-1)

        if args.verbose:
            print('Writing output ...')
        cpmd.cpmdWriter(
                 args.outputfile,
                 _data,
                 frames=list(range(_iframe, _iframe+args.batch_size)),
                 append=append,
                 write_atoms=False)

        _iframe += args.batch_size

    if args.verbose:
        print('Done.')


if __name__ == "__main__":
    main()
