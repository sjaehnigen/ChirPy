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

from chirpy.visualise import timeline
from chirpy.topology import motion
from chirpy.topology import mapping
from chirpy.classes import system
from chirpy import constants


def main():
    parser = argparse.ArgumentParser(
         description="Analyse motion of atoms in trajectory and plot results.",
         formatter_class=argparse.ArgumentDefaultsHelpFormatter
         )
    parser.add_argument(
            "fn",
            help="Trajectory file (xyz, ...)"
            )
    parser.add_argument(
            "--fn_vel",
            help="Additional trajectory file with velocities (optional)."
                 "Assumes atomic units.",
            default=None,
            )
    parser.add_argument(
            "--range",
            nargs=3,
            help="Range of frames to read (start, step, stop)",
            default=None,
            type=int,
            )
    # parser.add_argument("--fn_topo",
    #                     help="Topology file containing metadata (cell, \
    #                             molecules, ...).",
    #                     default=None,
    #                     )
    parser.add_argument(
            "--subset",
            nargs='+',
            help="Atom list (id starting from 0).",
            type=int,
            default=None,
            )
    parser.add_argument(
            "--noplot",
            default=False,
            action='store_true',
            help="Do not plot results."
            )
    args = parser.parse_args()
    no_plot = args.noplot
    if args.subset is None:
        del args.subset
    if args.range is None:
        del args.range

    if no_plot:
        plot = 0
    else:
        plot = 1

    _files = [args.fn]
    if args.fn_vel is not None:
        _files.append(args.fn_vel)

    largs = vars(args)

    # --- load data into object
    _load = system.Supercell(*_files, **largs)
    _w = _load.XYZ.masses_amu * constants.m_amu_au

    def get_p_and_v():
        try:
            while True:
                next(_load.XYZ)
                _p = _load.XYZ.pos_aa * constants.l_aa2au
                _v = _load.XYZ.vel_au
                yield _p, _v

        except StopIteration:
            pass

    subset = largs.get('subset', slice(None))

    def get_results():
        _it = get_p_and_v()
        try:
            while True:
                _p, _v = next(_it)
                _com = mapping.cowt(_p, _w, subset=subset)
                _lin = motion.linear_momenta(_v, _w, subset=subset)
                _ang, _moI = motion.angular_momenta(_p, _v, _w, origin=_com,
                                                    subset=subset, moI=True)
                yield _com, _lin, _ang, _moI

        except StopIteration:
            pass

    center_of_masses, linear_momenta, angular_momenta, moment_of_inertia = \
        tuple(zip(*[_r for _r in get_results()]))

    center_of_masses = np.array(center_of_masses)
    linear_momenta = np.array(linear_momenta)
    angular_momenta = np.array(angular_momenta)
    moment_of_inertia = np.array(moment_of_inertia)

    n_frames = len(center_of_masses)
    n_dof = 3*len(_w[subset])

    # --- translational and rotational temperatures (BETA), scaled from 3 to
    # all DOF
    T_trans = (linear_momenta**2 / _w.sum()
               / constants.k_B_au).sum() / n_frames / n_dof
    T_rot = (angular_momenta**2 / moment_of_inertia[:, None]
             / constants.k_B_au).sum() / n_frames / n_dof

    print('T(trans):\r\t\t\t\t%f' % T_trans)
    print('T(rot):\r\t\t\t\t%f' % T_rot)

    step_n = np.arange(n_frames)

    timeline.show_and_interpolate_array(
         step_n, center_of_masses[:, 0], 'com_x', 'step', 'com_x', plot)
    timeline.show_and_interpolate_array(
         step_n, center_of_masses[:, 1], 'com_y', 'step', 'com_y', plot)
    timeline.show_and_interpolate_array(
         step_n, center_of_masses[:, 2], 'com_z', 'step', 'com_z', plot)
    timeline.show_and_interpolate_array(
         step_n, linear_momenta[:, 0], 'lin_mom_x', 'step', 'lin_mom_x', plot)
    timeline.show_and_interpolate_array(
         step_n, linear_momenta[:, 1], 'lin_mom_y', 'step', 'lin_mom_y', plot)
    timeline.show_and_interpolate_array(
         step_n, linear_momenta[:, 2], 'lin_mom_z', 'step', 'lin_mom_z', plot)
    timeline.show_and_interpolate_array(
         step_n, angular_momenta[:, 0], 'ang_mom_x', 'step', 'ang_mom_x', plot)
    timeline.show_and_interpolate_array(
         step_n, angular_momenta[:, 1], 'ang_mom_y', 'step', 'ang_mom_y', plot)
    timeline.show_and_interpolate_array(
         step_n, angular_momenta[:, 2], 'ang_mom_z', 'step', 'ang_mom_z', plot)


if __name__ == "__main__":
    main()
