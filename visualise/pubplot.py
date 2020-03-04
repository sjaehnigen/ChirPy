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


import numpy as np
import warnings


class pub_label():
    def __init__(self,  ax,  **kwargs):
        self.ax = ax
        self.X = kwargs.get('X',  1400)
        self.Y = kwargs.get('Y',  0.0)
        self.color = kwargs.get('color',  'black')
        self.size = kwargs.get('size',  24)
        self.stancil = kwargs.get('stancil',  r'\textbf{%s}')
        self.sep = kwargs.get('sep',  0.0)
        self.alpha = kwargs.get('alpha',  1.0)

    def print(self,  string,  **kwargs):
        for _key in self.__dict__.keys():
            setattr(self,  _key,  kwargs.get(_key,  getattr(self,  _key)))
            try:
                del kwargs[_key]
            except KeyError:
                pass
        self.ax.text(self.X,  self.Y + self.sep,  self.stancil % string,
                     color=self.color,  alpha=self.alpha,  size=self.size,
                     **kwargs)


def source_params(matplotlib):
    # mpl.rcParams.update({
    # 'font.size':16,
    # 'axes.linewidth':6,
    # 'xtick.major.width':4,
    # 'ytick.major.width':4,
    # 'xtick.major.size':13,
    # 'ytick.major.size':13,
    # 'grid.linewidth':4,
    # 'grid.color':'0.8',
    # })
    matplotlib.rc('xtick',  labelsize=22)
    matplotlib.rc('ytick',  labelsize=22)
    matplotlib.rc('font',   size=22)

    # matplotlib.rcParams['pdf.fonttype'] = 42
    # matplotlib.rcParams['ps.fonttype'] = 42
    # matplotlib.rc('font',
    # **{'family':'sans-serif', 'sans-serif':['Helvetica']}) #gives warning
    matplotlib.rcParams['mathtext.fontset'] = 'stixsans'
    matplotlib.rc('text',  usetex=True)
    matplotlib.rcParams['text.latex.preamble'] = [
                                r'\usepackage[utf8]{inputenc}',
                                # r'\usepackage[T1]{fontenc}',
                                r'\usepackage{upgreek}',
                                r'\usepackage{bm}',
                                # r'\usepackage[warn]{textcomp}',
                                # r'\usepackage{siunitx}',
                                # r'\sisetup{detect-all}',
                                r'\usepackage{xcolor}',
                                r'\usepackage{amsmath}',
                                r'\usepackage{helvet}',
                                r'\usepackage{sansmath}',
                                r'\sansmath',
                                r'\def\mymathhyphen{{\hbox{-}}}']
    matplotlib.rcParams.update({'mathtext.default':  'regular'})


def make_nice_ax(p):
    '''p object ... AxesSubplot'''
    p.tick_params('both',  length=5,   width=3,  which='minor')
    p.tick_params('both',  length=10,  width=3,  which='major')
    p.tick_params(axis='both',  which='both',  pad=10,  direction='out')
    # , top=False, right=False)
    # p.yaxis.set_ticks_position('left')
    # p.spines['top'].set_visible(False)
    p.spines['top'].set_linewidth(3.0)
    p.spines['bottom'].set_linewidth(3.0)
    p.spines['left'].set_linewidth(3.0)
    p.spines['right'].set_linewidth(3.0)


def multiplot(ax, x_a, y_a, **kwargs):
    global _shift  # unique variable used by pub_label class
    try:
        n_plots = len(y_a)
    except TypeError:
        n_plots = y_a.shape[0]
    fill = kwargs.get('fill',  False)  # ToDo: Rename argument, refers to std
    bool_a = kwargs.get('bool_a',  n_plots * [True])
    std_a = kwargs.get('std_a')
    _exp = kwargs.get('exp')
    _sty_exp = kwargs.get('style_exp', '-')
    _alpha_exp = kwargs.get('alpha_exp', 1.0)
    if _exp is not None:
        e,  xe = _exp[:,  1],  _exp[:,  0]
    xlim = kwargs.get('xlim',  (np.amin(np.array(np.hstack(x_a))),
                                np.amax(np.array(np.hstack(x_a)))))
    ylim = kwargs.get('ylim')
    sep = kwargs.get('sep',  5)  # separation between plots in percent
    color_a = kwargs.get('color_a',
                         ['mediumblue',
                          'crimson',
                          'green',
                          'goldenrod',
                          'pink'])
    sty_a = kwargs.get('style_a',  n_plots * ['-'])
    alpha_a = kwargs.get('alpha_a',  n_plots * [1.0])
    f_alpha_a = kwargs.get('fill_alpha_a',  n_plots * [0.25])
    stack = kwargs.get('stack_plots',  True)
    pile_up = kwargs.get('pile_up',  False)  # fill space between plots
    hatch_a = kwargs.get('hatch_a',  n_plots * [None])
    pass_through = kwargs.get('pass_through',  {})

    if not isinstance(y_a, list):
        raise TypeError('Expected list for y_a!')
    if x_a.__class__ is not list:
        x_a = [np.array([_x for _x in x_a])] * n_plots
    if color_a.__class__ is not list:
        color_a = [color_a] * n_plots
    if sty_a.__class__ is not list:
        sty_a = [sty_a] * n_plots
    if alpha_a.__class__ is not list:
        alpha_a = [alpha_a] * n_plots
    if f_alpha_a.__class__ is not list:
        f_alpha_a = [f_alpha_a] * n_plots

    if pile_up and any([stack,  fill]):
        warnings.warn('pile_up set: automatically setting stack_plots and fill'
                      ' argument to False, respectively!', stacklevel=2)
        stack = False
        fill = False

    if any(len(_a) != n_plots for _a in [y_a,  bool_a]):
        raise ValueError('Inconsistent no. of plots in lists!')

    if fill and any(_a is None for _a in [std_a]):
        raise AttributeError('Need std_a argument for "fill" option!')

    # --- Calculate hspace per plot and ylim
    _slc = [slice(*sorted(np.argmin(np.abs(_x_a-_x)) for _x in xlim))
            for _x_a in x_a]
    if _exp is not None:
        _slce = slice(*sorted(np.argmin(np.abs(xe-_x)) for _x in xlim))

    try:
        _shift = max([np.amax(_y[_s]) - np.amin(_y[_s])
                      for _y, _s in zip(y_a, _slc)])
        if _exp is not None:
            _shift = max(np.amax(e[_slce]) - np.amin(e[_slce]), _shift)
        _shift *= (1 + sep / 100)

    except ValueError:
        warnings.warn('Could not calculate plot shift. Good luck!',
                      RuntimeWarning,
                      stacklevel=2)

    if stack:
        print(_shift)
        _y_a = [_y-_shift*_i for _i, _y in enumerate(y_a)]
        if _exp is not None:
            _e = e-n_plots*_shift
    else:
        _y_a = y_a
        if _exp is not None:
            _e = e

    if ylim is None:  # add routine for pile_up option
        ylim = (min([np.amin(_y[_s]) for _y, _s in zip(_y_a, _slc)]),
                max([np.amax(_y[_s]) for _y, _s in zip(_y_a, _slc)]))
        if _exp is not None:
            ylim = (min(ylim[0], np.amin(_e[_slce])),
                    max(ylim[1], np.amax(_e[_slce])))
        ylim = (ylim[0]-0.25*_shift, ylim[1]+0.25*_shift)

    # --- plot reference (experiment)
    if _exp is not None:
        ax.plot(xe, _e, _sty_exp, alpha=_alpha_exp, lw=3, color='black',
                label='exp.')

    # --- plot data
    if fill:
        for _b, _x, _y, _st, _c, _al, _s, _fal in zip(bool_a,
                                                      x_a,
                                                      _y_a,
                                                      sty_a,
                                                      color_a,
                                                      alpha_a,
                                                      std_a,
                                                      f_alpha_a):
            if _b:
                ax.fill_between(_x,  _y+_s,  _y-_s,  color=_c,  alpha=_fal)
                ax.plot(_x, _y, _st, lw=3, color=_c, alpha=_al)
    if pile_up:
        if not np.allclose(np.unique(x_a),  x_a[0]):
            raise ValueError('pile_up argument requires identical x content!')
        _last = np.zeros_like(_y_a[0])
        for _b,  _x,  _y,  _st,  _ha,  _c,  _al,  _fal in zip(bool_a,
                                                              x_a,
                                                              _y_a,
                                                              sty_a,
                                                              hatch_a,
                                                              color_a,
                                                              alpha_a,
                                                              f_alpha_a):
            if _b:
                ax.fill_between(_x, _last, _last + _y,
                                lw=0, color=_c, alpha=_fal,  hatch=_ha)
                _last += _y
                ax.plot(_x, _last, _st, lw=3, color=_c, alpha=_al)
    else:
        for _b, _x, _y, _st, _c, _al in zip(bool_a,
                                            x_a,
                                            _y_a,
                                            sty_a,
                                            color_a,
                                            alpha_a):
            if _b:
                ax.plot(_x, _y, _st, lw=3, color=_c, alpha=_al, **pass_through)

    # --- layout
    make_nice_ax(ax)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    # --- export label object (beta)
    # LB is simply returned can be retrieved (or not)

    if stack:
        LB = [pub_label(
                        ax,
                        color=_c,
                        X=np.mean(xlim),
                        Y=-_shift * _i,
                        alpha=_al,
                        sep=0.2 * _shift
                    ) for _i,  (_c, _al) in enumerate(zip(color_a, alpha_a))] \
                 + [pub_label(
                        ax,
                        color='black',
                        X=np.mean(xlim),
                        Y=-n_plots * _shift,
                        sep=0.2 * _shift,
                        stancil=r'\emph{%s}'
                    )] * (_exp is not None)

    else:
        LB = [pub_label(ax,
                        color=_c,
                        X=np.mean(xlim),
                        Y=np.mean(ylim),
                        alpha=_al) for _c, _al in zip(color_a, alpha_a)] \
             + [pub_label(ax,
                          color='black',
                          X=np.mean(xlim),
                          Y=np.mean(ylim),
                          stancil=r'\emph{%s}')] * (_exp is not None)

    return LB


def histogram(ax_a, data_a, **kwargs):  # needs a list of ax
    '''BETA'''
    global _shift
    _shift = 0
    n_plots = len(data_a)
    color_a = kwargs.get('color_a', ['#607c8e',
                                     '#c85a53',
                                     '#7ea07a',
                                     '#c4a661',
                                     '#3c4142', ])
    alpha_a = kwargs.get('alpha_a', n_plots*[kwargs.get('alpha', 1.0)])
    bool_a = kwargs.get('bool_a', n_plots*[True])
    xlim = kwargs.get('range')
    ylim = kwargs.get('ylim')
    sum_one = kwargs.get('sum_to_one', False)  # exclusive with density
    edges = kwargs.get('edges', False)  # exclusive with density
    # ToDo: routine for automatic (and equal!) range for all data_a
    bins = kwargs.get('bins')  # Quick workaround
    # sep = kwargs.get('sep', 0.0)

    if color_a.__class__ is not list:
        color_a = [color_a] * n_plots
    if alpha_a.__class__ is not list:
        alpha_a = [alpha_a] * n_plots

    if sum_one:
        weights_a = [np.ones_like(_d) / _d.shape[0] for _d in data_a]
    else:
        weights_a = kwargs.get('weights_a', [np.ones_like(_d)
                                             for _d in data_a])
    # ToDo: this is clumsy; get routine that read AND deletes argument
    #       OR use .pop() or do not pass-through kwargs
    for key in ['color_a',
                'color',
                'alpha_a',
                'alpha',
                'bool_a',
                'weights',
                'weights_a',
                'sum_to_one',
                'edges',
                'facecolor',
                'edgecolor',
                'bins',
                'sep',
                'ylim']:
        try:
            del kwargs[key]
        except KeyError:
            pass

    # _bin_width=(xlim[1]-xlim[0])/bins #use system variable?
    for _i, (ax, _b, _d, _c, _al, _wg) in enumerate(zip(ax_a,
                                                        bool_a,
                                                        data_a,
                                                        color_a,
                                                        alpha_a,
                                                        weights_a)):
        if _b and not edges:
            _h, _b_e = np.histogram(_d, bins=bins, range=kwargs.get('range'))
#            _b_e+=_i*sep*_bin_width
            # a = ax.hist(_d, bins=_b_e, color=_c, alpha=_al, weights=_wg,
            # bottom=-_i*sep, **kwargs)
#        elif edges: a = ax.hist(_h, bins=_b_e, facecolor='None',
        # edgecolor=_c, alpha=_al, **kwargs)

        make_nice_ax(ax)
        ax.set_xlim(*xlim)
        if ylim is not None:
            ax.set_ylim(*ylim)

    # --- export label object (beta)

    LB = [pub_label(ax, color=_c, Y=0.0, X=np.mean(_d), alpha=_al)
          for ax, _c, _al, _d in zip(ax_a, color_a, alpha_a, data_a)]

    return LB
