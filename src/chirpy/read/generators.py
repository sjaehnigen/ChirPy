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


from itertools import islice, zip_longest
import warnings
import numpy as np
# import io
import bz2 as _bz2
from tqdm import tqdm

from .. import config


def _gen(f):
    '''Global generator for all formats'''
    # byte stream:
    # return (line for line in f if b'NEW DATA' not in line)
    return (line for line in f if 'NEW DATA' not in line and '#' not in line)


# def _bopen(*args, **kwargs):
#     '''Open and automatically decompress file if necessary.
#        Supported compressors: bz2
#
#        Read-only support of compressed files.
#        '''
#     if kwargs.get('bz2') or args[0].split('.')[-1] == 'bz2':
#         return _bz2.open(args[0], 'rb')
#     else:
#         return open(args[0], 'rb')  #, buffer_size=4096)

def _open(*args, **kwargs):
    '''Open and automatically decompress file if necessary.
       Supported compressors: bz2

       Read-only support of compressed files.
       '''
    if kwargs.get('bz2') or args[0].split('.')[-1] == 'bz2':
        return _bz2.open(args[0], 'rt')
    else:
        return open(*args)


def _get(_it, kernel, **kwargs):
    '''Gets batch of lines defined by _n_lines and processes
       it with given _kernel. Returns processed data.'''

    n_lines = kwargs.get('n_lines')

    _range = kwargs.pop("range", (0, 1, float('inf')))
    if len(_range) == 2:
        r0, r1 = _range
        _ir = 1
    elif len(_range) == 3:
        r0, _ir, r1 = _range
    else:
        raise ValueError('Given range is not a tuple of length 2 or 3!')

    _sk = kwargs.pop("skip", [])

    class _line_iterator():
        '''self._r ... the frame that will be returned next (!)'''
        def __init__(self):
            self.current_line = 0
            self._it = _it
            self._r = 0
            self._skip = _sk
            self._offset = 0
            while self._r < r0:
                [next(_it) for _ik in range(n_lines)]
                if self._r + self._offset in _sk:
                    self._skip.remove(self._r + self._offset)
                    self._offset += 1
                else:
                    self._r += 1

        def __iter__(self):
            return self

        def __next__(self):
            while (self._r - r0) % _ir != 0 or self._r + self._offset in _sk:
                [next(_it) for _ik in range(n_lines)]
                if self._r + self._offset in _sk:
                    self._skip.remove(self._r + self._offset)
                    self._offset += 1
                else:
                    self._r += 1

            try:
                return islice(_it, n_lines)

            finally:
                self._r += 1
                if r1 > 0 and self._r > r1:
                    raise StopIteration()

    _data = _line_iterator()
    while True:
        try:
            # --- NB: islice does not raise StopIteration, but returns []!
            yield kernel(next(_data), **kwargs)
        except StopIteration:
            if r1 != np.inf and _data._r < r1 - _data._offset:
                warnings.warn('reached early end of trajectory'
                              f' at step {_data._r}',
                              config.ChirPyWarning, stacklevel=15)
            break


def _reader(FN, n_lines, kernel,
            convert=1,
            verbose=config.__verbose__,
            **kwargs):
    '''Opens file, checks contents, and parses arguments,
       kernel, and generator.'''
    with _open(FN, 'r', **kwargs) as _f:
        _it = _gen(_f)
        data = tqdm(_get(_it,
                         kernel,
                         convert=convert,
                         n_lines=n_lines,
                         **kwargs),
                    desc="%30s" % FN,
                    disable=not verbose)

        if np.size(data) == 0:
            raise ValueError('given input and arguments '
                             'do not yield any data')
        else:
            for _d in data:
                yield _d


def _dummy_kernel(frame, **kwargs):
    '''Simplest _kernel. Does nothing.'''
    return frame


def _container(reader_a, fn_a, args_a=(), kwargs_a=()):
    '''Assemble multiple readers in one generator.
       reader_a/fn_a/args_a/kwargs_a are iterables
       of reader functions and their filenames + arguments.'''
    try:
        for _frame in zip_longest(*map(
             lambda x: x[0](x[1], *x[2], **x[3]),
             # i.e.: reader(fn,   *args, **kwargs)
             zip_longest(reader_a, fn_a, args_a, kwargs_a, fillvalue={})
             )):
            # -- frame = (out0, out1, out2, ...)
            yield list(zip_longest(*_frame))
    except TypeError:
        raise ValueError('unexpected end of thread in container. '
                         'Do your files have the same length?')
