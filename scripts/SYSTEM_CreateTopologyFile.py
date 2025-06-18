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
import chirpy as cp


def main():
    '''Create a topology file from input.'''
    parser = argparse.ArgumentParser(
        description="Create a topology file from input.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument(
            "fn",
            help="Input structure file (xyz.pdb,xvibs,...)"
            )
    parser.add_argument(
            "--input_format",
            help="Input file format (e.g. xyz, pdb, cpmd; optional).",
            default=None,
            )
    parser.add_argument(
            "--center_coords",
            nargs='+',
            help="Center atom list (id starting from 0) in cell \
                    and wrap or \'True\' for selecting all atoms.",
            default=False,
            )
    parser.add_argument(
            "--center_molecule",
            help="Center residue (resid as given in fn_topo) in \
                    cell and wrap (requires a topology file).",
            default=None,
            type=int,
            )

    parser.add_argument(
            "--center_of_geometry", "--cog",
            help="Do not use atom masses as weights for centering and \
                    wrapping of molecules",
            action='store_true',
            default=False,
            )
    parser.add_argument(
            "--cell_aa_deg",
            nargs=6,
            help="Cell parameters a b c al be ga in angstrom/degree.",
            type=float,
            default=None
            )
    parser.add_argument(
            "--keep_molecules",
            action='store_true',
            help="Do not re-write molecular assignment.",
            default=False
            )
    parser.add_argument(
            "--keep_positions",
            action='store_true',
            help="Do not modifiy positions at all (wrap, center, ...).",
            default=False
            )
    parser.add_argument(
            "--wrap_molecules",
            action='store_true',
            help="Wrap molecules instead of atoms into cell.",
            default=False
            )
    parser.add_argument(
            "--verbose",
            action='store_true',
            help="Print info and progress.",
            default=False,
            )
    parser.add_argument(
            "--outputfile", "-o", "-f",
            help="Output file name",
            default='out.pdb'
            )
    parser.add_argument(
            "--write_centers",
            action='store_true',
            help="Output molecular centers to as mol-<outfile>.",
            default=False,
            )
    parser.add_argument(
            "--sort",
            action='store_true',
            help="Alphabetically sort atoms",
            default=False
            )
    parser.add_argument(
            "--clean",
            action='store_true',
            help="Remove misplaced atoms from system (ALPHA)",
            default=False
            )
    args = parser.parse_args()

    cp.config.set_verbose(args.verbose)

    read_args = cp.snippets.extract_keys(
                                   vars(args),
                                   sort=False,
                                   wrap_molecules=False,
                                   weights='masses',
                                   center_molecule=None,
                                   cell_aa_deg=None,
                                   verbose=False,
                                   )

    # --- adjustments ro read_args from parsing
    if not args.keep_molecules:
        read_args['define_molecules'] = True

    if bool(args.center_coords):
        if args.center_coords[0] == 'True':
            read_args['center_coords'] = True
        elif args.center_coords[0] == 'False':
            read_args['center_coords'] = False
        else:
            read_args['center_coords'] = [int(_a) for _a in args.center_coords]

    if args.center_of_geometry:
        read_args['weights'] = None

    if args.keep_positions:
        read_args['center_coords'] = False
        read_args['center_molecule'] = None
        read_args['wrap_molecules'] = False

    i_fmt = args.input_format
    if i_fmt is None:
        i_fmt = args.fn.split('.')[-1].lower()
    if args.cell_aa_deg is None:
        del read_args['cell_aa_deg']

    _load = cp.classes.system.Molecule(args.fn, **read_args, fmt=i_fmt)
    _load._check_distances(clean=args.clean)

    # --- keep only coordinates
    if hasattr(_load, 'Modes'):
        del _load.Modes

    if args.wrap_molecules:
        # --- redundant?
        if args.verbose:
            print(f'Atom weights for molecular centers: {_load.weights}')
        _load.wrap_molecules()  # algorithm='heavy_atom')
    elif not args.keep_positions:
        _load.wrap()
    _load.write(args.outputfile)

    if args.write_centers:
        _centers_aa = _load.XYZ._frame._get_center_of_weight(
                mask=_load.mol_map,
                weights=_load.weights
                )
        n_mols = len(_centers_aa)
        cp.classes.trajectory.XYZFrame(
                symbols=n_mols*('X',),
                data=_centers_aa,
                comments='molecular centers',
                cell_aa_deg=_load.cell_aa_deg,
                ).write('mol-'+args.outputfile, mol_map=list(range(n_mols)))


if (__name__ == "__main__"):
    main()
