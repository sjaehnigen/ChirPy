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
import os
import warnings

from chirpy.classes import quantum


def main():
    parser = argparse.ArgumentParser(
            description="Post-process CPMD CURRENTS output and write objects to\
                         disc. All files have to have the same grid and a \
                         common origin!",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
            )
    parser.add_argument(
            "--dir",
            help="Working directory",
            default="."
            )
    parser.add_argument(
            "--format",
            help="File format of CPMD output (currently supported: cube)",
            default='cube'
            )
    parser.add_argument(
            "--compression",
            help="File compression (supported: bz2, npy[DEPRECATED])",
            default=None
            )
    parser.add_argument(
            "--density",
            help="DENSITY file name radical",
            default='DENSITY-000001'
            )
    parser.add_argument(
            "--current",
            help="CURRENT file name radical",
            default='CURRENT-000001-%d'
            )
    parser.add_argument(
            "--state0",
            help="STATE real part file name radical",
            default='C0-000001-S%02d'
            )
    parser.add_argument(
            "--state1",
            help="STATE imaginary part file name radical",
            default='C1-000001-S%02d'
            )
    parser.add_argument(
            "--current_state",
            help="CURRENT state file name radical",
            default='CURRENT-000001-S%02d-%d'
            )
    parser.add_argument(
            "--crop",
            help="Reduce grid boundaries based by given number of points",
            type=int,
            default=0
            )
    parser.add_argument(
            "--auto_crop",
            action='store_true',
            help="Reduce grid boundaries based on density threshold",
            default=False
            )
    parser.add_argument(
            "--save_cropped",
            action='store_true',
            help="Save cropped grid data as files with -CROPPED extension",
            default=False
            )
    parser.add_argument(
            "--ignore_states",
            action='store_true',
            help="Do not post-process states even if existing",
            default=False
            )
    parser.add_argument(
            "--ignore_fragments",
            action='store_true',
            help="Do not post-process fragments even if existing (i.e., \
                  folders of format: 'fragment_000')",
            default=False
            )
    args = parser.parse_args()

    # ------ NPY only: open DENSITY cube file that contains grid metadata
    kwargs = {}
    if args.compression == 'npy':
        warnings.warn("Loading from numpy arrays will no longer be supported "
                      "in future versions. Use dump()/load() tools of the "
                      "individual objects, instead.",
                      FutureWarning,
                      stacklevel=2)

        _topo = quantum.ElectronDensity(args.density + ".cube")
        kwargs.update({_k: getattr(_topo, _k)
                       for _k in ['comments',
                                  'origin_au',
                                  'cell_vec_au',
                                  'pos_au',
                                  'numbers']
                       })
    # ----------------------------------------------------------------------

    global WDIR
    WDIR = args.dir

    def _assemble_file(fn,
                       fmt=args.format,
                       compression=args.compression):
        _FN = os.path.join(WDIR, fn) + '.' + fmt
        if compression is not None:
            _FN += '.' + compression
        return _FN

    def _recurse_states():
        print('Recursing time-dependent electronic states ...')
        _n = 1
        while os.path.isfile(_assemble_file(args.state0 % _n)):
            print(_n)
            _FN = (args.state1 % _n, args.state0 % _n) + tuple(
                    args.current_state % (_n, _i) for _i in (1, 2, 3))

            _sys = quantum.TDElectronicState(
                            *tuple(_assemble_file(_f) for _f in _FN[1:]),
                            psi1=_assemble_file(_FN[0]),
                            **kwargs
                            )

            if _V != 0:
                _sys.crop(_V)
                if args.save_cropped:
                    print('Saving cropped state ...')
                    _sys.psi1.write(_assemble_file(_FN[0] + '-CROPPED',
                                    compression=None))
                    _sys.psi.write(_assemble_file(_FN[1] + '-CROPPED',
                                   compression=None))
                    _sys.j.write(*tuple(_assemble_file(_f + '-CROPPED',
                                                       compression=None)
                                        for _f in _FN[2:]))
            # --- write object
            print('Saving TDElectronicState object...')
            _sys.dump(os.path.join(WDIR, 'TDElectronicState-%02d.obj' % _n))
            del _sys
            _n += 1

    def _recurse_fragments():
        print('Recursing fragments ...')
        _n = 0
        _fdir = os.path.join(args.dir, 'fragment_%03d' % _n)
        while os.path.isdir(_fdir):
            print(f"Fragment no. {_n}")
            global WDIR
            WDIR = _fdir
            print('Loading time-dependent electron density ...')
            _FN = (args.density,) + tuple(args.current % _i
                                          for _i in (1, 2, 3))

            _sys = quantum.TDElectronDensity(
                                      *tuple(_assemble_file(_f) for _f in _FN),
                                      **kwargs
                                      )
            if _V != 0:
                _sys.crop(_V)
                if args.save_cropped:
                    print('Saving cropped density ...')
                    _sys.rho.write(_assemble_file(_FN[0] + '-CROPPED',
                                                  compression=None))
                    _sys.j.write(*tuple(_assemble_file(_f + '-CROPPED',
                                                       compression=None)
                                        for _f in _FN[1:]))

            print('Saving TDElectronDensity object...')
            _sys.dump(os.path.join(WDIR, 'TDElectronDensity.obj'))
            del _sys

            if not args.ignore_states:
                _recurse_states()
            print('Done.')
            print(77 * '-')
            _n += 1
            _fdir = os.path.join(args.dir, 'fragment_%03d' % _n)

    # --- START
    print('Loading time-dependent electron density ...')
    _FN = (args.density,) + tuple(args.current % _i for _i in (1, 2, 3))

    _sys = quantum.TDElectronDensity(
                                *tuple(_assemble_file(_f) for _f in _FN),
                                **kwargs
                                )

    _sys.rho.print_info()

    # --- crop or no crop
    _V = args.crop
    if args.auto_crop:
        _V = _sys.auto_crop(thresh=_sys.rho.threshold/2)
    if _V != 0:
        print(' --> Crop %s' % _V)
    _sys.rho.print_info()

    # --- save
    if _V != 0 and args.save_cropped:
        print('Saving cropped density ...')
        _sys.rho.write(_assemble_file(_FN[0] + '-CROPPED', compression=None))
        _sys.j.write(*tuple(_assemble_file(_f + '-CROPPED', compression=None)
                            for _f in _FN[1:]))

    print('Saving TDElectronDensity object...')
    _sys.dump(os.path.join(WDIR, 'TDElectronDensity.obj'))
    del _sys

    if not args.ignore_states:
        _recurse_states()
    print('Done.')
    print(77 * '-')

    if not args.ignore_fragments:
        _recurse_fragments()

    print('ALL DONE.')


if __name__ == "__main__":
    main()
