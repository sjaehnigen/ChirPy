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

"""Helpers for writing simple PyMOL command files."""


import sys as _sys
import copy as _copy
import numpy as _np

known_types = {'modevectors': 'Modevectors',
               'molecule': 'Molecule',  # default
               'volume': 'Volume',
               'selection': 'Selection',
               'surface': 'Surface',
               'distance': 'Distance',
               }


class PymolObject():
    """Container for one or more named PyMOL objects."""

    def __init__(self, *args, **kwargs):
        """Create a PyMOL object wrapper from the requested type."""

        name = kwargs.get('name', 'obj1')
        self.__name__ = name
        try:
            setattr(
                    self,
                    name,
                    eval(
                        known_types[kwargs.get('type', 'molecule')]
                        )(*args, **kwargs)
                    )
        except KeyError:
            print('ERROR: Unkown type  % s!' % kwargs.get('type'))
            _sys.exit(1)

    def __add__(self, other):
        """Return a combined wrapper containing objects from both operands."""

        new = _copy.deepcopy(self)
        for name in other.__name__.split('+'):
            if not hasattr(new, name):
                setattr(new, name, getattr(other, name))
                new.__name__ += '+'+name
            else:
                print('skipping attribute  % s' % name)  # later maybe merge
        return new

    def __iadd__(self, other):
        """Append objects from another wrapper in place."""

        for name in other.__name__.split('+'):
            if not hasattr(self, name):
                setattr(self, name, getattr(other, name))
                self.__name__ += '+'+name
            else:
                print('skipping object  % s' % name)  # later maybe merge
        return self

    def write(self, fn):
        """Write all contained PyMOL commands to a file."""

        with open(fn, 'w') as f:
            f.write('# Pymolrc File generated with ChirPy\n')
        for name in self.__name__.split('+'):
            getattr(self, name).write(fn)


class NamedObject():
    """Base class for simple named PyMOL objects."""

    def __init__(self, *args, **kwargs):
        """Store the object name and run type-specific initialisation."""

        self.__name__ = kwargs.get('name', 'obj1')
        self._type_init(*args, **kwargs)

    def _type_init(self):
        """Initialise type-specific object data."""

        pass

    def rename(self):
        """Rename the object."""

        pass
# class UnnamedObject():

# working class, named classes


class Modevectors(NamedObject):
    """Defines vectors in space. Expects a numpy array of vectors and a
       corresponding array of starting points. A common origin is possible."""
    def _type_init(self, p0, p1, **kwargs):
        """Store vector start and end points plus display settings."""

        if len(p0.shape) != 2:
            raise TypeError('Please give a 2-dimensional array of points!')
        if p0.shape[1] != 3:
            raise TypeError('Please give an array of points with three '
                            'coordinates!')
        if p0.shape != p1.shape:
            raise TypeError('The given point arrays do not have the same '
                            'shape!')
        self.p0 = p0
        self.p1 = p1
        lengths = _np.linalg.norm(p0-p1, axis=1)
        # defaults
        self.cutoff = kwargs.get('cutoff', 0.0)
        self.cut = kwargs.get('cut', 0.0)
        self.factor = kwargs.get('factor', 1.0)
        # self.head_length = kwargs.get('head_length', 0.3) # my own default
        self.head_length = kwargs.get('head_length',  # t = 1 - d/length
                                      self.factor * _np.mean(lengths) * 0.4)
        self.head = kwargs.get('head', self.factor * _np.mean(lengths)*0.100)
        self.tail = kwargs.get('tail', self.factor * _np.mean(lengths)*0.033)
        self.notail = bool(kwargs.get('notail', False))
        self.headrgb = str(kwargs.get('headrgb', (1.0, 1.0, 1.0)))
        self.tailrgb = str(kwargs.get('tailrgb', (1.0, 1.0, 1.0)))

    def write(self, fn):
        """Append the modevector commands for this object to a file."""

        with open(fn, 'a') as f:
            for ip, (p0, p1) in enumerate(zip(*[self.p0, self.p1])):
                f.write('pseudoatom p0, name=C, resi =  % d, ' % ip)
                f.write('pos = [ % 12.6f,  % 12.6f,  % 12.6f]\n' % tuple(p0))
                f.write('pseudoatom p1, name=C, resi =  % d, ' % ip)
                f.write('pos = [ % 12.6f,  % 12.6f,  % 12.6f]\n' % tuple(p1))
            f.write('import modevectors\n')
            f.write('modevectors p0, p1, atom="C", outname= % s, '
                    % self.__name__)
            f.write('head_length= % f, ' % self.head_length)
            f.write('head= % f, ' % self.head)
            f.write('tail= % f, ' % self.tail)
            if self.notail:
                f.write('notail=1, ')
            f.write('cutoff= % f, ' % self.cutoff)
            f.write('cut= % f, ' % self.cut)
            f.write('factor= % f, ' % self.factor)
            f.write('headrgb= % s, ' % self.headrgb)
            f.write('tailrgb= % s, ' % self.tailrgb)
            f.write('\n')
            f.write('delete p0\n')
            f.write('delete p1\n')


class Selection(NamedObject):
    """Placeholder for PyMOL selection objects."""

    def __init__(self, **kwargs):
        """Initialise a selection placeholder."""

        print('This is a selection')


class Surface(NamedObject):
    """Placeholder for PyMOL surface objects."""

    def __init__(self, **kwargs):
        """Initialise a surface placeholder."""
        pass


class Volume(NamedObject):
    """Placeholder for PyMOL volume objects."""

    def __init__(self, **kwargs):
        """Initialise a volume placeholder."""
        pass


class Molecule(NamedObject):
    """Placeholder for PyMOL molecule objects."""

    def __init__(self, **kwargs):
        """Initialise a molecule placeholder."""

        print('I have my own initial method')


class Distance(NamedObject):
    """Placeholder for PyMOL distance objects."""

    def __init__(self, **kwargs):
        """Initialise a distance placeholder."""
        pass

# # unnamed classes
# class Colours(UnnamedObject):
# class Ray(UnnamedObject):
# class Light(UnnamedObject):
# class View(UnnamedObject):
