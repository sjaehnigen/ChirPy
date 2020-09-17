#!/usr/bin/env python
# ------------------------------------------------------
#
#  ChirPy
#
#    A buoyant python package for analysing supramolecular
#    and electronic structure, chirality and dynamics.
#
#
#  Developers:
#    2010-2016  Arne Scherrer
#    since 2014 Sascha Jähnigen
#
#  https://hartree.chimie.ens.fr/sjaehnigen/chirpy.git
#
# ------------------------------------------------------

import argparse
import numpy as np
import matplotlib.pyplot as plt
import warnings

from chirpy.physics import statistical_mechanics
from chirpy.classes import system


def main():
    parser = argparse.ArgumentParser(
         description="Analyse motion of atoms in trajectory and plot results.",
         formatter_class=argparse.ArgumentDefaultsHelpFormatter
         )
    parser.add_argument(
            "fn",
            help="Trajectory file (xyz, ...). Dummy if --fn_vel is used."
            )
    parser.add_argument(
            "--fn_vel",
            help="Additional trajectory file with velocities (optional)."
                 "Assumes atomic units. Skips fn.",
            default=None,
            )
    parser.add_argument(
            "--range",
            nargs=3,
            help="Range of frames to read (start, step, stop)",
            default=None,
            type=int,
            )
    parser.add_argument("--fn_topo",
                        help="Topology file containing metadata (cell, \
                                molecules, ...).",
                        default=None,
                        )
    parser.add_argument(
            "--subset",
            nargs='+',
            help="Atom list (id starting from 0).",
            type=int,
            default=None,
            )
    parser.add_argument(
            "--T",
            help="Reference temperature in K.",
            type=float,
            default=None,
            )
    parser.add_argument(
            "--element",
            help="Show results only for given atom species.",
            default=None,
            )

    # parser.add_argument(
    #         "--noplot",
    #         default=False,
    #         action='store_true',
    #         help="Do not plot results."
    #         )
    args = parser.parse_args()
    # no_plot = args.noplot
    if args.range is None:
        del args.range
    if args.subset is None:
        args.subset = slice(None)

    largs = vars(args)
    if args.fn_vel is not None:
        args.fn = args.fn_vel
    _load = system.Supercell(args.fn, **largs)
    _w = np.array(_load.XYZ.masses_amu)

    if args.element is not None:
        _s = np.array(_load.XYZ.symbols)[args.subset]
        _ind = np.argwhere(_s == args.element).flatten()
        if args.subset is None:
            args.subset = args.subset[_ind]
        else:
            args.subset = _ind

    print('Analysed atoms (symbols):\n%s' %
          np.array(_load.XYZ.symbols)[args.subset])

    def get_v():
        try:
            while True:
                next(_load.XYZ)
                if args.fn_vel is not None:
                    _v = _load.XYZ.pos_aa
                else:
                    _v = _load.XYZ.vel_au
                yield _v

        except StopIteration:
            pass

    _vel_au = np.array([_v[args.subset] for _v in get_v()])
    e_kin_au = statistical_mechanics.kinetic_energies(_vel_au, _w[args.subset])
    _n_f_dof = 6
    if args.element is not None:
        warnings.warn('Element mode: Switching off conservation of '
                      'degrees of freedom.')
        _n_f_dof = 0
    T_K = np.average(statistical_mechanics.temperature_from_energies(
                                            e_kin_au,
                                            fixed_dof=_n_f_dof
                                            ))
    print(f'MD temperature: {T_K} K')
    if args.T is None:
        args.T = T_K

    _vel_au = np.linalg.norm(_vel_au, axis=-1).ravel()

    plt.hist(_vel_au, lw=0.1, ec='k', bins=100, density=True, label=args.fn)

    _ideal = [statistical_mechanics.maxwell_boltzmann_distribution(
                            args.T,
                            _m,
                            option='velocity'
                            ) for _m in _w[args.subset]]
    X = np.linspace(0, np.amax(_vel_au), 200)
    PDF = np.array([list(map(_ii, X)) for _ii in _ideal]).sum(axis=0) / len(_ideal)
    plt.plot(X, PDF, label=f'Maxwell-Boltzmann (T={args.T}K)')

    plt.xlabel('Velocity in a.u.')
    plt.ylabel('Probability density in 1/a.u.')
    title = 'Velocity Distribution'
    if args.element is not None:
        title += f' (element {args.element})'
    plt.title(title)
    plt.legend(loc='upper right')
    plt.show()



if __name__ == "__main__":
    main()
