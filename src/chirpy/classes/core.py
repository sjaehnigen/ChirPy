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

import pickle
import itertools
import warnings
import numpy as np

from multiprocessing import Pool
from itertools import product, combinations_with_replacement
from functools import partial

from tqdm import tqdm

from .. import config


class PALARRAY():
    '''Class for parallel processing of array data.
       Processes data in a nested grid
       (i.e. all combinations of indices)'''

    def __init__(self, func, *data, repeat=1,
                 n_cores=config.__pal_n_cores__,
                 upper_triangle=False,
                 axis=0,
                 **kwargs):
        '''Parallel array process setup.
           With executable func(*args) and set of data arrays, data,
           whereas len(data) = len(args).

           If <func> returns multiple values, its annotation has to be set to
           tuple.

           kwargs contains global keyword arguments that are passed to func.

           Calculate upper_triangle matrix only, if len(data)==1 and repeat==2
           (optional).

           Output: array of shape (len(data[0], len(data[1]), ...)'''

        self.f = partial(func, **kwargs)
        self.multiple_returns = func.__annotations__.get('return') is tuple
        self.pool = Pool(n_cores)

        if axis != 0:
            self.data = tuple([np.moveaxis(_d, axis, 0) for _d in data])
        else:
            self.data = tuple([_d for _d in data])
        self._length = np.prod([len(_d) for _d in data])**repeat
        self._ut = False
        self.repeat = repeat

        if upper_triangle:
            self._ut = True
            if len(data) == 1 and repeat == 2:
                self.array = combinations_with_replacement(self.data[0], 2)
            else:
                raise ValueError('Upper triangle requires one data array with '
                                 'repeat=2!')
        else:
            self.array = product(*self.data, repeat=repeat)

    def run(self, verbose=config.__verbose__):
        try:
            _dtype = float
            if self.multiple_returns:
                _dtype = 'object'
            result = np.array(list(tqdm(
                         self.pool.istarmap(self.f, self.array),
                         desc=f'{self.f.func.__name__} (PALARRAY)',
                         total=self._length - int(
                                           self._ut *
                                           (self._length-len(self.data[0])) / 2
                                           ),
                         disable=not verbose,
                         )), dtype=_dtype)

            _l = self.repeat * tuple([len(_d) for _d in self.data])
            if self._ut:
                res_result = np.zeros(_l + result.shape[1:])
                res_result[np.triu_indices(_l[0])] = result

                return res_result

            else:
                return result.reshape(_l + result.shape[1:])

        except KeyboardInterrupt:
            print("KeyboardInterrupt in PALARRAY")

        finally:
            self.pool.terminate()
            self.pool.join()


class CORE():
    def __init__(self, *args, **kwargs):
        self._print_info = []

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        self = self.__add__(other)
        return self

    def __rsub__(self, other):
        return self.__sub__(other)

    def __isub__(self, other):
        self = self.__sub__(other)
        return self

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        self = self.__mul__(other)
        return self

    def __ipow__(self, other):
        self = self.__pow__(other)
        return self

    def dump(self, FN):
        with open(FN, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, FN):
        with open(FN, "rb") as f:
            _load = pickle.load(f)
        if not isinstance(_load, cls):
            warnings.warn(f"{FN} does not contain {cls.__name__}. Trying to "
                          "convert.", config.ChirPyWarning, stacklevel=2)
            _load = convert_object(_load, cls)

        # if hasattr(_load, 'data'):
            # warnings.warn(f"Found data with shape {_load.data.shape}.",
            #               stacklevel=2)

        if hasattr(_load, '_sync_class'):
            _load._sync_class()

        return _load

    def print_info(self):
        print('')
        print(77 * '–')
        print('%-12s' % self.__class__.__name__)
        print(77 * '–')
        print('')

        if not hasattr(self, '_print_info'):
            return

        for _func in self._print_info:
            _func(self)


class ITERATOR():
    def __init__(self, *args, **kwargs):
        self._kernel = CORE
        # self._gen_init = iter([])
        self._gen = iter([])

        self._kwargs = {}
        # --- initialise list of masks
        self._kwargs['_masks'] = []

        # --- keep kwargs for iterations
        self._kwargs.update(kwargs)

        # --- Get first frame for free (NB: if _fr <0 iterator is fresh)
        self.sneak()

        # --- Store original skip information as it is consumed by generator
        self._kwargs['_skip'] = self._kwargs['skip'].copy()

    def __iter__(self):
        return self

    def __next__(self):
        frame = next(self._gen)

        out = {'data': frame}

        self._fr += self._st
        self._kwargs.update(out)

        self._frame = self._kernel(**self._kwargs)

        # --- check for stored masks
        for _f, _f_args, _f_kwargs in self._kwargs['_masks']:
            if isinstance(_f, str):
                getattr(self._frame, _f)(*_f_args, **_f_kwargs)
            elif callable(_f):
                self._frame = _f(self._frame, *_f_args, **_f_kwargs)

        self.__dict__.update(self._frame.__dict__)

        return self._fr

    @classmethod
    def _from_list(cls, LIST, **kwargs):
        a = cls(LIST[0], **kwargs)
        for _f in LIST[1:]:
            b = cls(_f, **kwargs)
            a += b
        return a

    def _copy(self):
        '''return an exact copy of the iterator [BETA]
           not a deepcopy ? '''
        new = self.__new__(self.__class__)
        new.__dict__.update(self.__dict__)
        # --- split generator
        self._gen_old = self._gen
        self._gen, new._gen = itertools.tee(self._gen_old, 2)
        del self._gen_old

        return new

    def __add__(self, other):
        new = self._copy()
        if self._frame._is_similar(other._frame)[0] == 1:
            new._gen = itertools.chain(self._gen, other._gen)
            return new
        else:
            raise ValueError('Cannot combine frames of different size!')

    def sneak(self, verbose=config.__verbose__):
        '''Load next frame without exhausting iterator (important for loops)'''
        # --- split generator
        self._gen_old = self._gen
        self._gen, self._gen_aux = itertools.tee(self._gen_old, 2)

        # --- get free frame
        try:
            next(self)
        except (RuntimeError, StopIteration):
            with warnings.catch_warnings():  # --- do not warn only once
                warnings.warn('reached end of trajectory',
                              config.ChirPyWarning, stacklevel=3)
                del self._gen_old
                del self._gen_aux
                # raise StopIteration('reached end of trajectory')
                return

        if verbose:
            with warnings.catch_warnings():  # --- do not warn only once
                warnings.warn(f'sneak frame {self._fr}',
                              config.ChirPyWarning, stacklevel=2)
        self._fr -= self._st

        # --- reset generator
        self._gen = self._gen_aux
        del self._gen_old

    def rewind(self):
        '''Reinitialises the iterator'''
        if '_skip' in self._kwargs:
            self._kwargs['skip'] = self._kwargs['_skip'].copy()
        self.__init__(*self._fn, **self._kwargs)

    def _unwind(self, *args, **kwargs):
        '''Unwinds the Iterator according to <length> or until it is exhausted
           constantly executing the given frame-owned function and passing
           through given arguments.
           Events are dictionaries with (relative) frames
           as keys and some action as argument that are only
           executed when the Iterator reaches the value of the
           key.
           (This can partially also be done with masks.)
           '''
        func = kwargs.pop('func', None)
        events = kwargs.pop('events', {})
        length = kwargs.pop('length', None)
        _fr = 0
        for _ifr in itertools.islice(self, length):
            kwargs['frame'] = _ifr
            if isinstance(func, str):
                getattr(self._frame, func)(*args, **kwargs)
            elif callable(func):
                func(self, *args, **kwargs)
            if _fr in events:
                if isinstance(events[_fr], dict):
                    kwargs.update(events[_fr])
            _fr += 1

        if length is not None:
            # --- get next frame for free (NB: _fr is not updated!)
            self.sneak()

    @staticmethod
    def _mask(obj, func, *args, **kwargs):
        '''Adds a frame-owned function that is called with every __next__()
           before returning.'''
        obj._kwargs['_masks'].append(
                (func, args, kwargs),
                )
        if len(obj._kwargs['_masks']) > 10:
            warnings.warn('Too many masks on iterator!', config.ChirPyWarning,
                          stacklevel=2)

    def merge(self, other, axis=-1, dim1=None, dim2=None):
        '''Merge horizontically with another iterator (of equal length).
           Specify axis 0 or 1/-1 to combine atoms or data, respectively
           (default: -1).
           Specify cartesian dimensions to be used from data by dim1/dim2
           as slice:
              e.g. take indices 0 to 3 --> slice(0, 3)  [default for axis=-1]
                   take all indices --> slice(None)     [default for axis=0]
           <Other> iterator must not be used anymore!
           To concatenate iterators along the frame axis, use "+".
           '''
        if dim1 is None:
            if axis in (-1, 1):
                dim1 = slice(0, 3)
            else:
                dim1 = slice(None)
        if dim2 is None:
            if axis in (-1, 1):
                dim2 = slice(0, 3)
            else:
                dim2 = slice(None)

        def _add(obj1, obj2):
            '''combine two frames'''
            obj1._axis_pointer = axis
            obj2._axis_pointer = axis

            obj1.data = obj1.data[..., dim1]
            obj2.data = obj2.data[..., dim2]

            obj1 += obj2
            return obj1

        def _func(obj1, obj2):
            # --- next(obj1) is called before loading mask
            try:
                next(obj2)
                return _add(obj1, obj2)
            except StopIteration:
                with warnings.catch_warnings():
                    warnings.warn('Merged iterator exhausted!',
                                  RuntimeWarning,
                                  stacklevel=2)
                raise StopIteration('')

        self._frame = _add(self._frame, other._frame)
        self.__dict__.update(self._frame.__dict__)

        self._mask(self, _func, other)

    def mask_duplicate_frames(self, verbose=config.__verbose__, **kwargs):
        '''The printed numbers include the offset frame number,
           i.e. adding the number of frame 0, but not the stored mask
           '''
        def split_comment(comment):
            # ---- cp2k comment syntax, add more if required
            if 'i = ' in comment:
                return int(comment.split()[2].rstrip(','))
            elif 'Iteration:' in comment:
                return int(comment.split('_')[1].rstrip())
            else:
                raise TypeError('Cannot get frame info from comments!')

        def _func(obj, **kwargs):
            _skip = obj._kwargs.get('skip', [])
            _timesteps = obj._kwargs.get('_timesteps', [])
            _ts = split_comment(obj._frame.comments)
            if _ts not in _timesteps:
                _timesteps.append(_ts)
            else:
                if verbose:
                    print(obj._fr, ' doublet of ', _ts)
                _skip.append(obj._fr)
            obj._kwargs.update({'_timesteps': _timesteps})
            obj._kwargs.update({'skip': _skip})

        _keep = self._kwargs['range']
        _masks = self._kwargs['_masks']
        _offset = split_comment(self._frame.comments)

        if self._kwargs['range'][1] != 1:
            warnings.warn('Setting range increment to 1 for doublet search!',
                          config.ChirPyWarning,
                          stacklevel=2)
            self._kwargs['range'] = (_keep[0], 1, _keep[2])
            self.rewind()

        if len(self._kwargs['_masks']) > 0:
            warnings.warn('Disabling masks for doublet search! %s' % _masks,
                          config.ChirPyWarning,
                          stacklevel=2)
            self._kwargs['_masks'] = []

        self._kwargs['_timesteps'] = []
        kwargs['func'] = _func
        try:
            self._unwind(**kwargs)
        except ValueError:
            raise ValueError('Broken trajectory! Stopped at frame %s (%s)'
                             % (self._fr, self.comments))

        # ToDo: re-add this warning without using numpy
        if len(np.unique(_diff := np.diff(self._kwargs['_timesteps']))) != 1:
            warnings.warn(
             "CRITICAL: Found varying timesteps! "
             f"{(np.argwhere(np.diff(_diff)!=0).flatten()[1::2]+_offset).tolist()}",
             config.ChirPyWarning, stacklevel=2)  # 0-based index

        if verbose:
            print('Duplicate frames in %s according to range %s:' % (
                    self._fn,
                    self._kwargs['range']
                    ), (np.array(self._kwargs['skip']) + _offset).tolist())

        self._kwargs['_masks'] = _masks
        self._kwargs['range'] = _keep

        # --- Store original skip information as it is consumed by generator
        self._kwargs['_skip'] = self._kwargs['skip'].copy()

        if kwargs.get('rewind', True):
            self.rewind()

        return self._kwargs['skip']


class AttrDict(dict):
    '''Converts dictionary keys into attributes'''
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        # --- protect built-in namespace of dict
        for _k in self:
            if _k in dir(self):
                raise NameError("Trying to alter namespace of built-in "
                                "dict method!", _k)
        self.__dict__ = self

    def __setitem__(self, key, value):
        if key in dir(self):
            raise NameError("Trying to alter namespace of built-in "
                            "dict method!", key)
        super(AttrDict, self).__setitem__(key, value)


_known_objects = {
        'VectorField': {
            'VectorField': [],
            'CurrentDensity': [],
            'TDElectronDensity': ['j'],
            'TDElectronicState': ['j'],
            },
        'ScalarField': {
            'ScalarField': [],
            'ElectronDensity': [],
            'WaveFunction': [],
            'WannierFunction': [],
            'TDElectronDensity': ['rho'],
            'TDElectronicState': ['psi'],
            # 'TDElectronicState': ['psi1'],
            }
        }

_attributes = {
        'VectorField': [
            'data',
            'cell_vec_au',
            'origin_au',
            'pos_au',
            'cell_vec_aa',
            'origin_aa',
            'pos_aa',
            'numbers',
            'comments'
            ],
        'ScalarField': [
            'data',
            'cell_vec_au',
            'origin_au',
            'pos_au',
            'cell_vec_aa',
            'origin_aa',
            'pos_aa',
            'numbers',
            'comments'
            ],
        }


def convert_object(source, target):
    '''source is an object and target is a class'''
    try:
        _ko = _known_objects[target.__name__]

    except KeyError:
        raise TypeError('Unsupported conversion target: '
                        f'{target.__name__}')

    src = source
    src_name = source.__class__.__name__
    if src_name in _ko:
        for attr in _ko[src_name]:
            src = getattr(src, attr)
    else:
        raise TypeError(f'{target.__name__} cannot proselytize to '
                        '{source.__class__.__name__}!')

    obj = target.__new__(target)
    for attr in _attributes[target.__name__]:
        try:
            value = getattr(src, attr)
            setattr(obj, attr, value)
        except AttributeError:
            warnings.warn(f'{source} object has no attribute \'{attr}\'',
                          config.ChirPyWarning, stacklevel=2)

    return obj
