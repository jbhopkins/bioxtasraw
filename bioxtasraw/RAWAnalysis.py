'''
Created on Mar 23, 2010

@author: specuser

#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************
'''
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip, str
from io import open
import six

try:
    import queue
except ImportError:
    import Queue as queue

import sys
import os
import copy
import multiprocessing
import threading
import time
import platform
import collections
import traceback
import tempfile
import shutil

import numpy as np
import wx
import wx.lib.agw.flatnotebook as flatNB
from wx.lib.agw import ultimatelistctrl as ULC
import wx.lib.scrolledpanel as scrolled
import wx.grid
from scipy import integrate
import scipy.stats as stats
import matplotlib

matplotlib.rcParams['backend'] = 'WxAgg'
matplotlib.rc('image', origin = 'lower')        # turn image upside down.. x,y, starting from lower left

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
import matplotlib.colors as mplcol
from mpl_toolkits.mplot3d import Axes3D
from  matplotlib.colors import colorConverter as cc

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWSettings as RAWSettings
import bioxtasraw.RAWCustomCtrl as RAWCustomCtrl
import bioxtasraw.SASCalc as SASCalc
import bioxtasraw.SASFileIO as SASFileIO
import bioxtasraw.SASM as SASM
import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.RAWCustomDialogs as RAWCustomDialogs
import bioxtasraw.SASProc as SASProc
import bioxtasraw.BIFT as BIFT
import bioxtasraw.DENSS as DENSS
import bioxtasraw.SECM as SECM
import bioxtasraw.SASUtils as SASUtils
import bioxtasraw.REGALS as REGALS
import bioxtasraw.RAWAPI as RAWAPI

class UVConcentrationDialog(wx.Dialog):
    def __init__(self, parent, title, selected_sasms, bg_sasm):
        wx.Dialog.__init__(self, None, title = title)
        self.SetSize(self._FromDIP((250,150)))

        layout_sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = UVConcentrationPanel(self, 'UVConcPanel', selected_sasms = selected_sasms, bg_sasm = bg_sasm)

        layout_sizer.Add(self.panel, 0)
        layout_sizer.Add(self.CreateButtonSizer( wx.OK | wx.CANCEL ), 0,
            flag=wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, border=self._FromDIP(10))
        self.Bind(wx.EVT_BUTTON, self.OnOKButton, id = wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnCancelButton, id=wx.ID_CANCEL)
        self.SetSizerAndFit(layout_sizer)

        SASUtils.set_best_size(self)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def OnOKButton(self, event):
        self.panel.processAndSaveAll()
        event.Skip()

    def OnCancelButton(self, event):
        event.Skip()

class UVConcentrationPanel(wx.Panel):

    def __init__(self, parent, name, selected_sasms = None, bg_sasm = None):
        wx.Panel.__init__(self, parent, -1, name = name)

        self.selected_sasms = selected_sasms
        self.bg_sasm = bg_sasm

        main_frame = wx.FindWindowByName('MainFrame')
        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.extc_values = {'Lysozyme'  : [26.4, 2.64],
                            'BSA'       : [6.7, 0.67],
                            'IgG'       : [13.7, 1.37],
                            'Abs=1mg/ml': [10, 1.0]}

        self.extc_choices = ['Lysozyme', 'BSA', 'IgG', 'Abs=1mg/ml', 'Custom']
        self.unit_choices = ['E1% [ml/(10mg) cm^-1]', 'E0.1% [ml/mg cm^-1]']

        self.spin_ctrl_ids = {'UVDarkTransmission' : [wx.NewControlId(), wx.NewControlId(), 'UV Dark', 0],
                              'UVTransmissionBg'   : [wx.NewControlId(), wx.NewControlId(), 'UV Transmission (Bg)', 2.0],
                              'UVTransmissionSamp' : [wx.NewControlId(), wx.NewControlId(), 'UV Transmission (Sample)', 1.0],
                              'UVPathlength'       : [wx.NewControlId(), wx.NewControlId(), 'UV Path Length [mm]', 1.5],
                              'UVExtinctionCoeff'  : [wx.NewControlId(), wx.NewControlId(), 'Extinction Coeff.', 24.0]}

        self.all_spins = ['UVDarkTransmission', 'UVTransmissionBg',
            'UVTransmissionSamp', 'UVPathlength', 'UVExtinctionCoeff']
        self.double_spins = ['UVPathlength', 'UVExtinctionCoeff']


        self._initLayout()
        self._initValues()
        self.onChoiceUpdate(None)
        #self._updateCalculation()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _calcConcentration(self, A = None):
        #A=lec
        if A is None:
            A = float(self.absorb_ctrl.GetValue())

        l = (self.spin_ctrl_ids['UVPathlength'][3] / 10.) #in cm
        e = self.spin_ctrl_ids['UVExtinctionCoeff'][3]

        c = A / (float(l)*float(e))

        if self.units_choice.GetStringSelection() == self.unit_choices[0]:
            c = c * 10

        return c

    def onSpinUpdate(self, event):
        for each in self.spin_ctrl_ids:
            spin_id, button_id, label, val = self.spin_ctrl_ids[each]

            ctrl = wx.FindWindowById(spin_id)
            self.spin_ctrl_ids[each][3] = float(ctrl.GetValue())

        self._updateCalculation()

    def onChoiceUpdate(self, event):

        idx = self.units_choice.GetSelection()
        key = self.extc_choice.GetStringSelection()

        if key == 'Custom':
            return

        ctrl = wx.FindWindowById(self.spin_ctrl_ids['UVExtinctionCoeff'][0])
        ctrl.SetValue(self.extc_values[key][idx])
        self.spin_ctrl_ids['UVExtinctionCoeff'][3]=self.extc_values[key][idx]

        self._updateCalculation()

    def _updateCalculation(self):
        a = self._calcAbsorbance()
        c = self._calcConcentration(a)

        self.absorb_ctrl.SetValue(str(round(a, 4)))
        self.conc_ctrl.SetValue(str(round(c, 4)))

    def _calcAbsorbance(self):
        #A = log10(I0/I)

        blank_val = self.spin_ctrl_ids['UVTransmissionBg'][3]
        dark_val = self.spin_ctrl_ids['UVDarkTransmission'][3]
        trans_int = self.spin_ctrl_ids['UVTransmissionSamp'][3]

        I0 = blank_val - dark_val
        I = trans_int - dark_val
        reverse_sign = False
        frac = 0

        try:
            frac = float(I0)/float(I)

            if frac < 1:
               frac = float(I)/float(I0)
               reverse_sign = True

            a = np.log10(frac)
        except ZeroDivisionError:
            a = 0

        if np.isnan(a) or np.isinf(a):
            a = 0

        if reverse_sign:
            a = -a

        return a

    def _initValues(self):
        bg_data = self.bg_sasm.getParameter('analysis')['uvvis']

        # For background
        for key in bg_data:
            if bg_data[key] is not None:

                if key == 'UVTransmission':
                    spin_key = 'UVTransmissionBg'
                else:
                    spin_key = key

                ctrl = wx.FindWindowById(self.spin_ctrl_ids[spin_key][0])

                if key in self.double_spins:
                    ctrl.SetValue(float(bg_data[key]))
                else:
                    ctrl.SetValue(float(bg_data[key]))

                self.spin_ctrl_ids[spin_key][3] = float(bg_data[key])

        samp_data = self.selected_sasms[0].getParameter('analysis')['uvvis']
        ctrl = wx.FindWindowById(self.spin_ctrl_ids['UVTransmissionSamp'][0])
        ctrl.SetValue(samp_data['UVTransmission'])
        self.spin_ctrl_ids['UVTransmissionSamp'][3]=float(samp_data['UVTransmission'])

        self.bg_txt.SetLabel(self.bg_sasm.getParameter('filename'))
        self.sample_txt.SetLabel(self.selected_sasms[0].getParameter('filename'))

    def setSampleValues(self, sasm):
        samp_data = sasm.getParameter('analysis')['uvvis']
        self.spin_ctrl_ids['UVTransmissionSamp'][3]=float(samp_data['UVTransmission'])

    def updateGui(self):
        ctrl = wx.FindWindowById(self.spin_ctrl_ids['UVTransmissionSamp'][0])
        ctrl.SetValue(self.spin_ctrl_ids['UVTransmissionSamp'][3])

    def _initLayout(self):

        layout_sizer = wx.BoxSizer(wx.VERTICAL)

        self.extc_choice = wx.Choice(self, -1, choices = self.extc_choices)
        self.extc_choice.Bind(wx.EVT_CHOICE, self.onChoiceUpdate)
        self.units_choice = wx.Choice(self, -1, choices = self.unit_choices)
        self.units_choice.Bind(wx.EVT_CHOICE, self.onChoiceUpdate)
        self.extc_choice.Select(0)
        self.units_choice.Select(0)

        choice_sizer = wx.BoxSizer(wx.HORIZONTAL)
        choice_sizer.Add(self.units_choice, 0, wx.EXPAND)
        choice_sizer.Add(self.extc_choice, 0, wx.EXPAND | wx.LEFT, border=self._FromDIP(5))

        file_sizer = wx.FlexGridSizer(cols=2, rows=2, vgap=self._FromDIP(4),
            hgap=self._FromDIP(4))
        bg_label = wx.StaticText(self, -1, 'Background : ')
        samp_label = wx.StaticText(self, -1, 'Sample : ')
        self.bg_txt = wx.StaticText(self, -1, 'Bgfile')
        self.sample_txt = wx.StaticText(self, -1, 'Sampfile')
        file_sizer.Add(bg_label, 0)
        file_sizer.Add(self.bg_txt, 0, wx.EXPAND)
        file_sizer.Add(samp_label, 0)
        file_sizer.Add(self.sample_txt, 0)
        layout_sizer.Add(file_sizer,0, wx.EXPAND | wx.ALL, border=self._FromDIP(10))

        spin_sizer = wx.FlexGridSizer(cols = 3, rows = len(self.all_spins),
            vgap=self._FromDIP(4), hgap=self._FromDIP(4))

        for key in self.all_spins:
            spin_id, button_id, label, val = self.spin_ctrl_ids[key]

            if key in self.double_spins:
                spin_ctrl = wx.SpinCtrlDouble(self, spin_id, value = '1.0',
                    min = 0, max = 16000, initial = 1)
                spin_ctrl.SetIncrement(0.1)
                spin_ctrl.SetDigits(3)
                spin_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.onSpinUpdate)
            else:
                spin_ctrl = wx.SpinCtrlDouble(self, spin_id, value = '1.0',
                    min = 0, max = 16000, initial = 1)
                spin_ctrl.SetIncrement(0.1)
                spin_ctrl.SetDigits(2)
                spin_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.onSpinUpdate)
            static_label = wx.StaticText(self, -1, label)

            #button = wx.Button(self, button_id, 'From Header')

            if key not in ['UVExtinctionCoeff']:
                spin_sizer.Add(static_label, 0, wx.ALIGN_CENTER_VERTICAL)
                spin_sizer.Add(spin_ctrl, 0, wx.EXPAND)
                spin_sizer.Add((10,10), 0)
            else:
                spin_sizer.Add(static_label, 0, wx.ALIGN_CENTER_VERTICAL)
                spin_sizer.Add(spin_ctrl, 0, wx.ALIGN_CENTER)

        spin_sizer.Add(choice_sizer, 0, wx.EXPAND)

        layout_sizer.Add(spin_sizer, 0, wx.EXPAND | wx.ALL, border=self._FromDIP(10))
        layout_sizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL),
            0, wx.EXPAND | wx.LEFT | wx.RIGHT, border=self._FromDIP(5))

        conc_sizer = wx.FlexGridSizer(rows=2, cols=3, vgap=self._FromDIP(4),
            hgap=self._FromDIP(4))
        absorb_label = wx.StaticText(self, -1, 'Absorbance')
        self.absorb_ctrl = wx.TextCtrl(self, -1, '0', style = wx.TE_RIGHT)

        conc_label = wx.StaticText(self, -1, 'Concentration')
        self.conc_ctrl = wx.TextCtrl(self, -1, '1', style = wx.TE_RIGHT)

        conc_sizer.Add(absorb_label, 0, wx.ALIGN_CENTRE_VERTICAL)
        conc_sizer.Add(self.absorb_ctrl, 0)
        conc_sizer.Add(wx.StaticText(self, -1, 'AU'), 0, wx.ALIGN_CENTRE_VERTICAL)
        conc_sizer.Add(conc_label, 0, wx.ALIGN_CENTRE_VERTICAL)
        conc_sizer.Add(self.conc_ctrl, 0)
        conc_sizer.Add(wx.StaticText(self, -1, 'mg/ml'), 0, wx.ALIGN_CENTRE_VERTICAL)

        layout_sizer.Add(conc_sizer, 0, wx.EXPAND | wx.ALL, self._FromDIP(10))

        self.SetSizerAndFit(layout_sizer)

    def processAndSaveAll(self):

        for each_sasm in self.selected_sasms:
            self.setSampleValues(each_sasm)

            a = self._calcAbsorbance()
            c = self._calcConcentration(a)

            print(each_sasm, a, c)
            each_sasm.setParameter('Conc', round(c, 3))
            each_sasm.setParameter('Absorbance', a)


class GuinierPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id):
        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.guinier_frame = parent.GetParent().GetParent()

        try:
            self.raw_settings = self.main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        SASUtils.update_mpl_style()

        self.fig = Figure((5,4), 75)

        self.data_line = None

        norm_residuals = self.raw_settings.get('normalizedResiduals')
        if norm_residuals:
            self.subplotLabels = [('Guinier', '$q^2$', '$\ln(I(q))$', .1),
            ('Normalized Residual', '$q^2$', '$\Delta \ln (I(q))/\sigma (q)$', 0.1)]
        else:
            self.subplotLabels = [('Guinier', '$q^2$', '$\ln(I(q))$', .1),
            ('Residual', '$q^2$', '$\Delta \ln (I(q))$', 0.1)]


        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(self.subplotLabels)):
            subplot = self.fig.add_subplot(len(self.subplotLabels),1,i+1,
                title = self.subplotLabels[i][0], label = self.subplotLabels[i][0])
            subplot.set_xlabel(self.subplotLabels[i][1])
            subplot.set_ylabel(self.subplotLabels[i][2])

            if self.subplotLabels[i][0] == 'Normalized Residual':
                label = 'Residual'
            else:
                label = self.subplotLabels[i][0]

            self.subplots[label] = subplot

        self.fig.subplots_adjust(left = 0.15, bottom = 0.08, right = 0.95, top = 0.95, hspace = 0.3)
        # self.fig.set_facecolor('white')

        self.subplots['Residual'].axhline(0, color='k', linewidth=1.0)

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)
        # self.canvas.SetBackgroundColour('white')

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

    def updateColors(self):
        color = SASUtils.update_mpl_style()

        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Guinier']
        b = self.subplots['Residual']

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def refresh_display(self):
        self.ax_redraw()
        self.toolbar.Refresh()

    def _calcFit(self, is_autorg=False):
        ''' calculate fit and statistics '''
        xmin, xmax = self.xlim

        x = self.x[xmin:xmax+1]
        y = self.y[xmin:xmax+1]
        yerr = self.yerr[xmin:xmax+1]

        #Remove NaN and Inf values:
        x = x[np.where(np.isfinite(y))]
        yerr = yerr[np.where(np.isfinite(y))]
        y = y[np.where(np.isfinite(y))]

        error_weight = self.raw_settings.get('errorWeight')
        norm_residuals = self.raw_settings.get('normalizedResiduals')

        Rg, I0, Rger, I0er, a, b = SASCalc.calcRg(x, y, yerr, transform=False,
            error_weight=error_weight)

        if is_autorg:
            est_rg_err = None
            est_i0_err = None
        else:
            est_rg_err, est_i0_err = self._estimateError(x, y, yerr)

        #Get fit statistics:
        y_fit = SASCalc.linear_func(x, a, b)
        error = y - y_fit
        r_sqr = 1 - np.square(error).sum()/np.square(y-y.mean()).sum()

        if norm_residuals:
            error = error/yerr

        newInfo = {'I0' : I0,
                   'Rg' : Rg,
                   'qRg_max': Rg*self.orig_q[xmax],
                   'qRg_min' : Rg*self.orig_q[xmin],
                   'qmin'   : self.orig_q[xmin],
                   'qmax'   : self.orig_q[xmax],
                   'rsq': r_sqr,
                   'err_fsigma_rg'  : Rger,
                   'err_fsigma_i0'  : I0er,
                   'err_est_rg'     : est_rg_err,
                   'err_est_i0'     : est_i0_err,
                   }

        return x, y_fit, a, error, newInfo

    def _estimateError(self, x, y, yerr):
        error_weight = self.raw_settings.get('errorWeight')

        est_rg_err, est_i0_err = SASCalc.estimate_guinier_error(x, y, yerr,
            transform=False, error_weight=error_weight)

        if est_rg_err is None:
            est_rg_err = -1

        if est_i0_err is None:
            est_i0_err = -1

        return est_rg_err, est_i0_err

    def plotExpObj(self, ExpObj):
        qmin, qmax = ExpObj.getQrange()

        self.orig_i = ExpObj.i[qmin:qmax]
        self.orig_q = ExpObj.q[qmin:qmax]
        self.orig_err = ExpObj.err[qmin:qmax]

        self.x = np.square(self.orig_q)
        self.y = np.log(self.orig_i)
        self.yerr = np.absolute(self.orig_err/self.orig_i) #I know it looks odd, but it's correct for a natural log

    def updateDataPlot(self, xlim, is_autorg=False):
        xmin, xmax = xlim
        self.xlim = xlim

        ## Plot the (at most) 3 first and last points after fit:
        if xmin < 20:
            min_offset = xmin
        else:
            min_offset = 20

        if xmax+1 > len(self.orig_q)-3:
            max_offset = len(self.orig_q) - (xmax+1)
        else:
            max_offset = 3

        xmin = xmin - min_offset
        xmax = xmax + 1 + max_offset

        #data containing the extra first and last points
        x = self.x[xmin:xmax]
        y = self.y[xmin:xmax]

        x = x[np.where(np.isfinite(y))]
        y = y[np.where(np.isfinite(y))]

        a = self.subplots['Guinier']
        b = self.subplots['Residual']

        try:
            x_fit, y_fit, I0, error, newInfo = self._calcFit(is_autorg)
        except TypeError as e:
            print(e)
            return

        wx.CallAfter(self.guinier_frame.controlPanel.updateInfo, newInfo)


        xg = [0, x_fit[0]]
        yg = [I0, y_fit[0]]

        if self.data_line is None:
            self.data_line, = a.plot(x, y, 'b.', animated = True)
            self.fit_line, = a.plot(x_fit, y_fit, 'r', animated = True)
            self.interp_line, = a.plot(xg, yg, 'g--', animated = True)

            self.error_line, = b.plot(x_fit, error, 'b', animated = True)

            self.lim_front_line = a.axvline(x=x_fit[0], color = 'r', linestyle = '--', animated = True)
            self.lim_back_line = a.axvline(x=x_fit[-1], color = 'r', linestyle = '--', animated = True)

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)
        else:
            self.data_line.set_ydata(y)
            self.data_line.set_xdata(x)

            self.fit_line.set_ydata(y_fit)
            self.fit_line.set_xdata(x_fit)

            self.interp_line.set_xdata(xg)
            self.interp_line.set_ydata(yg)

            self.lim_back_line.set_xdata(x_fit[-1])
            self.lim_front_line.set_xdata(x_fit[0])

            #Error lines:
            self.error_line.set_xdata(x_fit)
            self.error_line.set_ydata(error)

        self.autoscale_plot()

    def redrawLines(self):
        a = self.subplots['Guinier']
        b = self.subplots['Residual']

        if self.data_line is not None:

            self.canvas.restore_region(self.background)
            self.canvas.restore_region(self.err_background)

            a.draw_artist(self.data_line)
            a.draw_artist(self.fit_line)
            a.draw_artist(self.interp_line)
            a.draw_artist(self.lim_front_line)
            a.draw_artist(self.lim_back_line)

            b.draw_artist(self.error_line)

            self.canvas.blit(a.bbox)
            self.canvas.blit(b.bbox)

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplots['Guinier'], self.subplots['Residual']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()

    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''
        if event.button == 3:
            if float(matplotlib.__version__[:3]) >= 1.2:
                if self.toolbar.GetToolState(self.toolbar.wx_ids['Pan']) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu)
                    else:
                        self._showPopupMenu()

            else:
                if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu)
                    else:
                        self._showPopupMenu()

    def _showPopupMenu(self):
        menu = wx.Menu()
        menu.Append(1, 'Export Data As CSV')

        self.PopupMenu(menu)

        menu.Destroy()

    def _onPopupMenuChoice(self, evt):
        my_id = evt.GetId()

        if my_id == 1:
            self._exportData()

    def _exportData(self):
        data_list = []
        header = ''

        if self.data_line is not None:
            xmin, xmax = self.xlim
            ## Plot the (at most) 3 first and last points after fit:
            if xmin < 20:
                min_offset = xmin
            else:
                min_offset = 20

            if xmax+1 > len(self.orig_q)-3:
                max_offset = len(self.orig_q) - (xmax+1)
            else:
                max_offset = 3

            xmin = xmin - min_offset
            xmax = xmax + 1 + max_offset

            #data containing the extra first and last points
            x = self.x[xmin:xmax]
            y = self.y[xmin:xmax]
            yerr = self.yerr[xmin:xmax]

            x = x[np.where(np.isfinite(y))]
            y = y[np.where(np.isfinite(y))]
            yerr = yerr[np.where(np.isfinite(y))]

            data_list.append(x)
            data_list.append(y)
            data_list.append(yerr)

            header = header + '{},{},{},'.format('q**2_data', 'ln(I(q))_data', 'error_data')


            x_fit = self.fit_line.get_xdata()
            y_fit = self.fit_line.get_ydata()
            residual = self.error_line.get_ydata()

            data_list.append(x_fit)
            data_list.append(y_fit)
            data_list.append(residual)

            if self.subplotLabels[1][0] == 'Normalized Residual':
                label = 'normalized_residual'
            else:
                label = 'residual'

            header = header + '{},{},{},'.format('q**2_fit', 'ln(I(q))_fit', label)

        header.rstrip(',')

        if len(data_list) == 0:
            msg = 'Must have data shown on the plot to export it.'
            wx.CallAfter(wx.MessageBox, str(msg), "No Data Shown", style = wx.ICON_ERROR | wx.OK)
        else:
            dirctrl = wx.FindWindowByName('DirCtrlPanel')
            path = str(dirctrl.getDirLabel())

            filename = 'guinier_fit_plot_data.csv'

            dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = path, defaultFile = filename)

            if dialog.ShowModal() == wx.ID_OK:
                save_path = dialog.GetPath()
                name, ext = os.path.splitext(save_path)
                save_path = name + '.csv'
                dialog.Destroy()
            else:
                dialog.Destroy()
                return

            RAWGlobals.save_in_progress = True
            self.main_frame.setStatus('Saving Guinier data', 0)

            SASFileIO.saveUnevenCSVFile(save_path, data_list, header)

            RAWGlobals.save_in_progress = False
            self.main_frame.setStatus('', 0)


class GuinierControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, ExpObj, manip_item):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.ExpObj = ExpObj

        self.manip_item = manip_item
        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.guinier_frame = parent.GetParent().GetParent()

        self.old_analysis = {}

        if 'guinier' in self.ExpObj.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.ExpObj.getParameter('analysis')['guinier'])

        try:
            self.raw_settings = self.main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.spinctrlIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId()}

        self.staticTxtIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId()}

        self.infodata = {'I0' : ('I0 :', self.NewControlId(), self.NewControlId()),
                        'Rg' : ('Rg :', self.NewControlId(), self.NewControlId()),
                        'qRg_max': ('q_max*Rg', self.NewControlId()),
                        'qRg_min': ('q_min*Rg', self.NewControlId()),
                        'rsq': ('r^2 (fit) :', self.NewControlId()),
                         }

        self.error_data = {'fsigma_rg'  : self.NewControlId(),
                        'fsigma_i0'     : self.NewControlId(),
                        'autorg_rg'     : self.NewControlId(),
                        'autorg_i0'     : self.NewControlId(),
                        'est_rg'        : self.NewControlId(),
                        'est_i0'        : self.NewControlId(),
                        'sum_rg'        : self.NewControlId(),
                        'sum_i0'        : self.NewControlId(),
                        }

        self.button_ids = {'show'   : self.NewControlId(),
                            'info'  : self.NewControlId(),
                            }


        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)



        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(button, 1)

        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self.createInfoBox(box)
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND|wx.LEFT|wx.TOP,
            border=self._FromDIP(5))
        qrgsizer = self.createQRgInfo(box)
        boxSizer.Add(qrgsizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM,
            border=self._FromDIP(5))

        error_sizer = self.createErrorSizer()

        box2 = wx.StaticBox(self, -1, 'Control')
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)

        controlSizer = self.createControls(box2)

        line_sizer = wx.StaticLine(parent=box2, style=wx.LI_HORIZONTAL)

        autorg_button = wx.Button(box2, -1, 'Auto')
        autorg_button.Bind(wx.EVT_BUTTON, self.onAutoRg)

        boxSizer2.Add(controlSizer, 0, wx.EXPAND)
        boxSizer2.Add(line_sizer, 0, flag = wx.EXPAND | wx.ALL,
            border=self._FromDIP(10))
        boxSizer2.Add(autorg_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT,
            border=self._FromDIP(5))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.ALL,
            border=self._FromDIP(5))
        top_sizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=self._FromDIP(5))
        top_sizer.Add(error_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=self._FromDIP(5))
        top_sizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._FromDIP(5))
        top_sizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT| wx.TOP,
            border=self._FromDIP(5))

        self.SetSizer(top_sizer)

        self.setFilename(os.path.basename(ExpObj.getParameter('filename')))

        self.bi = None

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createQRgInfo(self, parent):

        sizer = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))

        txt1 = wx.StaticText(parent, -1, self.infodata['qRg_min'][0])
        txt2 = wx.StaticText(parent, -1, self.infodata['qRg_max'][0])
        ctrl1 = wx.TextCtrl(parent, self.infodata['qRg_min'][1])
        ctrl2 = wx.TextCtrl(parent, self.infodata['qRg_max'][1])

        sizer.Add(txt1, flag=wx.ALIGN_CENTER_HORIZONTAL)
        sizer.Add(txt2, flag=wx.ALIGN_CENTER_HORIZONTAL)
        sizer.Add(ctrl1)
        sizer.Add(ctrl2)

        return sizer

    def createInfoBox(self, parent):

        sizer = wx.FlexGridSizer(rows=len(self.infodata), cols=2,
            hgap=self._FromDIP(3), vgap=self._FromDIP(3))

        for key in self.infodata:

            if key == 'qRg_min' or key == 'qRg_max':
                continue

            if len(self.infodata[key]) == 2:
                txt = wx.StaticText(parent, -1, self.infodata[key][0])
                ctrl = wx.TextCtrl(parent, self.infodata[key][1], '0')
                sizer.Add(txt, 0)
                sizer.Add(ctrl,0)

            else:
                txt = wx.StaticText(parent, -1, self.infodata[key][0])
                ctrl1 = wx.TextCtrl(parent, self.infodata[key][1], '0')

                bsizer = wx.BoxSizer()
                bsizer.Add(ctrl1,0,wx.EXPAND)

                sizer.Add(txt,0)
                sizer.Add(bsizer,0)

        return sizer

    def createControls(self, parent):

        sizer = wx.FlexGridSizer(rows=2, cols=4, hgap=self._FromDIP(0),
            vgap=self._FromDIP(2))
        sizer.AddGrowableCol(0)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableCol(2)
        sizer.AddGrowableCol(3)

        sizer.Add(wx.StaticText(parent, -1,'q_min'),1, wx.LEFT, border=self._FromDIP(5))
        sizer.Add(wx.StaticText(parent, -1,'n_min'),1)
        sizer.Add(wx.StaticText(parent, -1,'q_max'),1)
        sizer.Add(wx.StaticText(parent, -1,'n_max'),1)

        self.startSpin = RAWCustomCtrl.IntSpinCtrl(parent, self.spinctrlIDs['qstart'],
            size=self._FromDIP((60,-1)))
        self.endSpin = RAWCustomCtrl.IntSpinCtrl(parent, self.spinctrlIDs['qend'],
            size =self._FromDIP((60,-1)))

        self.startSpin.SetValue(0)
        self.endSpin.SetValue(0)

        self.startSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.endSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)

        self.qstartTxt = wx.TextCtrl(parent, self.staticTxtIDs['qstart'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(parent, self.staticTxtIDs['qend'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_PROCESS_ENTER)

        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)

        sizer.Add(self.qstartTxt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._FromDIP(3))
        sizer.Add(self.startSpin, 0, wx.EXPAND | wx.RIGHT,
            border=self._FromDIP(3))
        sizer.Add(self.qendTxt, 0, wx.EXPAND | wx.RIGHT, border=self._FromDIP(3))
        sizer.Add(self.endSpin, 0, wx.EXPAND | wx.RIGHT, border=self._FromDIP(5))

        return sizer

    def createErrorSizer(self):
        parent = wx.StaticBox(self, wx.ID_ANY, 'Uncertainty')

        sum_sizer = wx.FlexGridSizer(rows=1, cols=4, hgap=self._FromDIP(3),
            vgap=self._FromDIP(3))
        sum_sizer.AddGrowableCol(1)
        sum_sizer.AddGrowableCol(3)
        rg_sum_lbl = wx.StaticText(parent, wx.ID_ANY, 'Rg : ')
        i0_sum_lbl = wx.StaticText(parent, wx.ID_ANY, 'I0 : ')
        rg_sum_txt = wx.TextCtrl(parent, self.error_data['sum_rg'], '',
            size = self._FromDIP((60, -1)))
        i0_sum_txt = wx.TextCtrl(parent, self.error_data['sum_i0'], '',
            size = self._FromDIP((60, -1)))

        sum_sizer.Add(rg_sum_lbl, flag=wx.ALIGN_CENTER_VERTICAL)
        sum_sizer.Add(rg_sum_txt, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        sum_sizer.Add(i0_sum_lbl, flag=wx.ALIGN_CENTER_VERTICAL)
        sum_sizer.Add(i0_sum_txt, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)

        self.err_sizer = wx.FlexGridSizer(rows=3, cols=4, hgap=self._FromDIP(3),
            vgap=self._FromDIP(3))
        self.err_sizer.AddGrowableCol(1)
        self.err_sizer.AddGrowableCol(2)
        self.err_sizer.AddGrowableCol(3)

        std_text = wx.StaticText(parent, wx.ID_ANY, 'Fit')
        auto_text = wx.StaticText(parent, wx.ID_ANY, 'Auto')
        est_text = wx.StaticText(parent, wx.ID_ANY, 'Est.')

        self.err_sizer.AddMany([(wx.StaticText(parent, wx.ID_ANY, ''), 0,),
            (std_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (auto_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (est_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            ])

        rg_text = wx.StaticText(parent, wx.ID_ANY, 'Rg :')
        rg_fit = wx.TextCtrl(parent, self.error_data['fsigma_rg'], '',
            size=self._FromDIP((60,-1)))
        rg_auto = wx.TextCtrl(parent, self.error_data['autorg_rg'], '',
            size=self._FromDIP((60,-1)))
        rg_est = wx.TextCtrl(parent, self.error_data['est_rg'], '',
            size=self._FromDIP((60,-1)))

        self.err_sizer.AddMany([(rg_text, 0, wx.ALIGN_CENTER_VERTICAL),
            (rg_fit, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND),
            (rg_auto, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND),
            (rg_est, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND),
            ])

        i0_text = wx.StaticText(parent, wx.ID_ANY, 'I0 :')
        i0_fit = wx.TextCtrl(parent, self.error_data['fsigma_i0'], '',
            size=self._FromDIP((60,-1)))
        i0_auto = wx.TextCtrl(parent, self.error_data['autorg_i0'], '',
            size=self._FromDIP((60,-1)))
        i0_est = wx.TextCtrl(parent, self.error_data['est_i0'], '',
            size=self._FromDIP((60,-1)))

        self.err_sizer.AddMany([(i0_text, 0, wx.ALIGN_CENTER_VERTICAL),
            (i0_fit, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND),
            (i0_auto, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND),
            (i0_est, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND),
            ])

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        show_btn = wx.Button(parent, self.button_ids['show'], 'Show Details')
        show_btn.Bind(wx.EVT_BUTTON, self._onShowButton)

        info_btn = wx.Button(parent, self.button_ids['info'], 'More Info')
        info_btn.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer.Add(show_btn, 0, wx.ALL, border=self._FromDIP(5))
        button_sizer.Add(info_btn, 0, wx.ALL, border=self._FromDIP(5))

        self.err_top_sizer = wx.StaticBoxSizer(parent, wx.VERTICAL)
        self.err_top_sizer.Add(sum_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        self.err_top_sizer.Add(self.err_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        self.err_top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL
            | wx.ALIGN_CENTER_VERTICAL, 5)

        self.err_top_sizer.Hide(self.err_sizer, recursive=True)

        return self.err_top_sizer

    def _initSettings(self):
        analysis = self.ExpObj.getParameter('analysis')

        if 'guinier' in analysis:
            spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

            old_start = spinstart.GetValue()
            old_end = spinend.GetValue()

            try:
                guinier = analysis['guinier']

                qmin = float(guinier['qStart'])
                qmax = float(guinier['qEnd'])

                findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
                closest_qmin = findClosest(qmin, self.ExpObj.q)
                closest_qmax = findClosest(qmax, self.ExpObj.q)

                idx_min = np.where(self.ExpObj.q == closest_qmin)[0][0]
                idx_max = np.where(self.ExpObj.q == closest_qmax)[0][0]

                minrange = spinstart.GetRange()
                maxrange = spinstart.GetRange()

                if idx_min < minrange[0]:
                    idx_min = minrange[0]
                elif idx_min > minrange[1]:
                    idx_min = minrange[1]

                if idx_max < maxrange[0]:
                    idx_max = maxrange[0]
                elif idx_max > maxrange[1]:
                    idx_max = maxrange[1]

                spinstart.SetValue(int(idx_min))
                spinend.SetValue(int(idx_max))

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(idx_min)],5)))

                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(idx_max)],5)))

                if 'Rg_autorg_err' in guinier and guinier['Rg_autorg_err'] != -1:
                    txt = wx.FindWindowById(self.error_data['autorg_rg'], self)
                    txt.SetValue(guinier['Rg_autorg_err'])

                    txt = wx.FindWindowById(self.error_data['autorg_i0'], self)
                    txt.SetValue(guinier['I0_autorg_err'])

                    self.updatePlot(is_autorg=True)
                else:
                    self.updatePlot()

            except Exception:
                spinstart.SetValue(old_start)
                spinend.SetValue(old_end)

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(old_start)],5)))

                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(old_end)],5)))

                self.runAutoRg()

        else:
            self.runAutoRg()

    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def createFileInfo(self):

        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(box, -1, '', style = wx.TE_READONLY)

        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND)

        return boxsizer

    def onSaveInfo(self, evt):
        gp = self.guinier_frame.plotPanel

        try:
            x_fit, y_fit, I0, error, newInfo = gp._calcFit()

            self.updateInfo(newInfo)

            info_dict = {}

            for key in newInfo:
                if key in self.infodata:
                    info_dict[key] = str(newInfo[key])

            nstart_val = wx.FindWindowById(self.spinctrlIDs['qstart'], self).GetValue()
            nend_val = wx.FindWindowById(self.spinctrlIDs['qend'], self).GetValue()

            qstart_val = wx.FindWindowById(self.staticTxtIDs['qstart'], self).GetValue()
            qend_val = wx.FindWindowById(self.staticTxtIDs['qend'], self).GetValue()

            info_dict['nStart'] = nstart_val
            info_dict['nEnd'] = nend_val
            info_dict['qStart'] = qstart_val
            info_dict['qEnd'] = qend_val

            info_dict['Rg_fit_err'] = newInfo['err_fsigma_rg']
            info_dict['I0_fit_err'] = newInfo['err_fsigma_i0']

            autorg_rg_err = wx.FindWindowById(self.error_data['autorg_rg'], self).GetValue()
            autorg_i0_err = wx.FindWindowById(self.error_data['autorg_i0'], self).GetValue()

            if autorg_rg_err != '':
                info_dict['Rg_autorg_err'] = autorg_rg_err
                info_dict['I0_autorg_err'] = autorg_i0_err
                info_dict['Rg_err'] = max(float(autorg_rg_err), float(newInfo['err_fsigma_rg']))
                info_dict['I0_err'] = max(float(autorg_i0_err), float(newInfo['err_fsigma_i0']))
                info_dict['Rg_est_err'] = -1
                info_dict['I0_est_err'] = -1
            else:
                info_dict['Rg_est_err'] = newInfo['err_est_rg']
                info_dict['I0_est_err'] = newInfo['err_est_i0']
                info_dict['Rg_err'] = max(float(newInfo['err_est_rg']), float(newInfo['err_fsigma_rg']))
                info_dict['I0_err'] = max(float(newInfo['err_est_i0']), float(newInfo['err_fsigma_i0']))
                info_dict['Rg_autorg_err'] = -1
                info_dict['I0_autorg_err'] = -1

            analysis_dict = self.ExpObj.getParameter('analysis')
            analysis_dict['guinier'] = info_dict

            if self.manip_item is not None:
                wx.CallAfter(self.manip_item.updateInfoTip, analysis_dict, fromGuinierDialog = True)
                if info_dict != self.old_analysis:
                    wx.CallAfter(self.manip_item.markAsModified)


            for mw_window in self.main_frame.mw_frames:
                if mw_window:
                    if mw_window.sasm == self.ExpObj:
                        mw_window.updateGuinierInfo()

        except TypeError:
            pass

        self.guinier_frame.OnClose()

    def onCloseButton(self, evt):
        self.guinier_frame.OnClose()

    def showBusy(self, show=True):
        if show:
            self.bi = wx.BusyInfo('Finding Rg, please wait.', self.guinier_frame)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass

    def onAutoRg(self, evt):
        self.runAutoRg()

    def runAutoRg(self):

        self.showBusy(True)
        thread = threading.Thread(target=self._do_autorg)
        thread.daemon = True
        thread.start()

    def _do_autorg(self):
        error_weight = self.raw_settings.get('errorWeight')
        rg, rger, i0, i0er, idx_min, idx_max = SASCalc.autoRg(self.ExpObj,
            error_weight=error_weight)

        wx.CallAfter(self._finish_autorg, rg, rger, i0, i0er, idx_min, idx_max)

    def _finish_autorg(self, rg, rger, i0, i0er, idx_min, idx_max):

        nmin_offset, _ = self.ExpObj.getQrange()

        try:
            spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

            old_start = spinstart.GetValue()
            old_end = spinend.GetValue()

        except Exception:
            # Window is closed before autorg finishes
            return

        if rg == -1:
            msg = ('Automatic determination of Rg failed.')
            dlg = wx.MessageDialog(self, msg, "Auto Rg Failed",
                style = wx.ICON_ERROR | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

            try:
                self.updatePlot()

            except Exception:
                pass

        else:
            try:
                spinstart.SetValue(int(idx_min)+nmin_offset)
                spinend.SetValue(int(idx_max)+nmin_offset)

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(idx_min)],5)))

                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(idx_max)],5)))

                txt = wx.FindWindowById(self.error_data['autorg_rg'], self)
                if abs(rger) > 1e3 or abs(rger) < 1e-2:
                    txt.SetValue('%.3E' %(rger))
                else:
                    txt.SetValue('%.4f' %(round(rger, 4)))

                txt = wx.FindWindowById(self.error_data['autorg_i0'], self)
                if abs(i0er) > 1e3 or abs(i0er) < 1e-2:
                    txt.SetValue('%.3E' %(i0er))
                else:
                    txt.SetValue('%.4f' %(round(i0er, 4)))

                self.updatePlot(is_autorg=True)

            except IndexError:

                try:
                    spinstart.SetValue(old_start)
                    spinend.SetValue(old_end)

                    txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                    txt.SetValue(str(round(self.ExpObj.q[int(old_start)],5)))

                    txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                    txt.SetValue(str(round(self.ExpObj.q[int(old_end)],5)))

                    txt = wx.FindWindowById(self.error_data['autorg_rg'], self)
                    txt.SetValue('')

                    txt = wx.FindWindowById(self.error_data['autorg_i0'], self)
                    txt.SetValue('')

                    self.updatePlot()

                except Exception:
                    # Most likely window has been closed before AutoRg finished
                    pass

            except Exception:
                # Most likely window has been closed before AutoRg finished
                pass

        try:
            self.showBusy(False)
        except Exception:
            pass

    def setCurrentExpObj(self, ExpObj):
        self.ExpObj = ExpObj

    def _onShowButton(self, evt):
        if self.err_top_sizer.IsShown(self.err_sizer):
            self.err_top_sizer.Hide(self.err_sizer, recursive=True)
            button = wx.FindWindowById(self.button_ids['show'], self)
            button.SetLabel('Show Details')
            self.Layout()
        else:
            self.err_top_sizer.Show(self.err_sizer, recursive=True)
            button = wx.FindWindowById(self.button_ids['show'], self)
            button.SetLabel('Hide Details')
            self.Layout()

    def _onInfoButton(self, evt):
        msg = ("RAW currently estimates the uncertainty in Rg and I0 as the largest "
        "of three possible sources.\n\n1) Fit - the standard deviation of the "
        "coefficients found by the fit (sqrt of the covariance matrix diagonal "
        "elements).\n\n2) Auto Rg - If the auto Rg position is used, RAW reports "
        "the standard deviation of the Rg and I0 values from all 'good' fitting "
        "regions found during the search.\n\n3) Est. - An estimated uncertainty similar "
        "to that reported from the auto Rg function. When manual limits are set, RAW "
        "reports the standard deviation in Rg and I0 obtained from the set of intervals "
        "where n_min is varied bewteen n_min to n_min+(n_max-n_min)*.1 and "
        "n_max varied between n_max-(n_max-n_min)*.1 to n_max.")

        dlg = wx.MessageDialog(self, msg, "Estimate Rg and I0 Uncertainty",
            style = wx.ICON_INFORMATION | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def onEnterInQlimits(self, evt):

        id = evt.GetId()

        lx = self.ExpObj.q

        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))

        txtctrl = wx.FindWindowById(id, self)

        #### If User inputs garbage: ####
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if id == self.staticTxtIDs['qstart']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return

            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'], self)
                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return
        #################################

        closest = findClosest(val,lx)

        i = np.where(lx == closest)[0][0]

        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)

        if id == self.staticTxtIDs['qstart']:

            max = endSpin.GetValue()

            if i > max-2:
                i = max - 2

            startSpin.SetValue(i)

        elif id == self.staticTxtIDs['qend']:
            minq = startSpin.GetValue()


            if i < minq+2:
                i = minq + 2

            endSpin.SetValue(i)

        txtctrl.SetValue(str(round(self.ExpObj.q[int(i)],5)))

        wx.CallAfter(self.updatePlot)

    def setSpinLimits(self, ExpObj):
        qmin, qmax = ExpObj.getQrange()

        self.startSpin.SetRange((qmin, qmax-1))
        self.endSpin.SetRange((qmin, qmax-1))

        self.startSpin.SetValue(qmin)
        self.endSpin.SetValue(qmax-1)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
        txt.SetValue(str(round(ExpObj.q[qmax-1],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
        txt.SetValue(str(round(ExpObj.q[qmin],4)))

    def onEnterOnSpinCtrl(self, evt):
        ''' Little workaround to make enter key in spinctrl work on Mac too '''
        spin = evt.GetEventObject()

        self.startSpin.SetFocus()
        self.endSpin.SetFocus()

        spin.SetFocus()

    def onSpinCtrl(self, evt):
        ctrl_id = evt.GetId()

        spin = wx.FindWindowById(ctrl_id, self)

        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        i = int(spin.GetValue())

        #Make sure the boundaries don't cross:
        if ctrl_id == self.spinctrlIDs['qstart']:
            max_val = int(endSpin.GetValue())
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)

            if i > max_val-2:
                i = max_val - 2
                spin.SetValue(i)

        elif ctrl_id == self.spinctrlIDs['qend']:
            min_val = int(startSpin.GetValue())
            txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)

            if i < min_val+2:
                i = min_val + 2
                spin.SetValue(i)

        txt.SetValue(str(round(self.ExpObj.q[int(i)],5)))

        #Important, since it's a slow function to update (could do it in a timer instead) otherwise this spin event might loop!
        wx.CallAfter(self.updatePlot)

    def updatePlot(self, is_autorg=False):
        if not is_autorg:
            txt = wx.FindWindowById(self.error_data['autorg_rg'], self)
            txt.SetValue('')
            txt = wx.FindWindowById(self.error_data['autorg_i0'], self)
            txt.SetValue('')

        plotpanel = self.guinier_frame.plotPanel

        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        i = int(spinstart.GetValue())
        i2 = int(spinend.GetValue())

        qmin, qmax = self.ExpObj.getQrange()

        xlim = [i-qmin,i2-qmin]

        plotpanel.updateDataPlot(xlim, is_autorg)

    def updateInfo(self, newInfo):
        for eachkey in newInfo:
            val = newInfo[eachkey]

            if eachkey.startswith('err'):
                key = '_'.join(eachkey.split('_')[1:])
                ctrl = wx.FindWindowById(self.error_data[key], self)
            elif eachkey in self.infodata:
                ctrl = wx.FindWindowById(self.infodata[eachkey][1], self)
            else:
                ctrl = None

            if ctrl is not None:
                if val is None:
                    ctrl.SetValue('')
                elif abs(val) > 1e3 or abs(val) < 1e-2:
                    ctrl.SetValue('%.3E' %(val))
                else:
                    ctrl.SetValue('%.4f' %(round(val, 4)))

        i0_list = []
        rg_list = []
        for key in self.error_data:
            if 'sum' not in key:
                ctrl = wx.FindWindowById(self.error_data[key])
                val = ctrl.GetValue()
                if 'i0' in key and val != '':
                    i0_list.append(float(val))
                if 'rg' in key and 'i0' not in key and val != '':
                    rg_list.append(float(val))

        ctrl = wx.FindWindowById(self.error_data['sum_rg'])
        ctrl.SetValue(str(max(rg_list)))

        ctrl = wx.FindWindowById(self.error_data['sum_i0'])
        ctrl.SetValue(str(max(i0_list)))

    def updateLimits(self, top = None, bottom = None):
        if bottom:
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)
            spinend.SetValue(bottom)
            txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
            txt.SetValue(str(round(self.ExpObj.q[int(bottom)],4)))

        if top:
            spinend = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
            spinend.SetValue(top)
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
            txt.SetValue(str(round(self.ExpObj.q[int(top)],4)))

    def getLimits(self):

        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        return [int(spinstart.GetValue()), int(spinend.GetValue())]

    def getInfo(self):

        guinierData = {}

        for eachKey in self.infodata:

            if len(self.infodata[eachKey]) == 2:
                ctrl = wx.FindWindowById(self.infodata[eachKey][1], self)
                val = ctrl.GetValue()
                guinierData[eachKey] = val
            else:
                ctrl1 = wx.FindWindowById(self.infodata[eachKey][1], self)

                val1 = ctrl1.GetValue()
                guinierData[eachKey] = val1

        return guinierData


class GuinierFrame(wx.Frame):

    def __init__(self, parent, title, ExpObj, manip_item):
        client_display = wx.GetClientDisplayRect()
        size = (min(800, client_display.Width), min(600, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        panel = wx.Panel(self)

        splitter1 = wx.SplitterWindow(panel, wx.ID_ANY)

        sizer = wx.BoxSizer()
        sizer.Add(splitter1, 1, flag=wx.EXPAND)

        panel.SetSizer(sizer)

        self.sasm = ExpObj


        self.plotPanel = GuinierPlotPanel(splitter1, wx.ID_ANY)
        self.controlPanel = GuinierControlPanel(splitter1, wx.ID_ANY, ExpObj, manip_item)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(300))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(self._FromDIP(290))    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(self._FromDIP(50))

        self.plotPanel.plotExpObj(ExpObj)


        self.controlPanel.setSpinLimits(ExpObj)
        self.controlPanel.setCurrentExpObj(ExpObj)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        self.Layout()

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.plotPanel.refresh_display()
        self.controlPanel._initSettings()

        self.CenterOnParent()
        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()

    def OnClose(self):
        self.controlPanel.showBusy(False)
        self.Destroy()


class MolWeightFrame(wx.Frame):

    def __init__(self, parent, title, sasm, manip_item):

        client_display = wx.GetClientDisplayRect()

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        opsys = platform.system()

        if opsys == 'Windows':
            if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'datmw.exe')):
                self.has_atsas = True
            else:
                self.has_atsas = False
        else:
            if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'datmw')):
                self.has_atsas = True
            else:
                self.has_atsas = False

        if not self.has_atsas:
            size = (min(525, client_display.Width), min(550, client_display.Height))
        else:
            size = (min(750, client_display.Width), min(550, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self.panel = wx.Panel(self, wx.ID_ANY, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.sasm = sasm
        self.manip_item = manip_item

        self.old_analysis = {}

        if 'molecularWeight' in self.sasm.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.sasm.getParameter('analysis')['molecularWeight'])

        self.infodata = {'I0' : ('I0 :', self.NewControlId(), self.NewControlId()),
                         'Rg' : ('Rg :', self.NewControlId(), self.NewControlId())}

        self.ids = {
            'VC': {
                'mol_type'      : self.NewControlId(),
                'calc_mw'       : self.NewControlId(),
                'info'          : self.NewControlId(),
                'more'          : self.NewControlId(),
                'sup_vc'        : self.NewControlId(),
                'sup_qr'        : self.NewControlId(),
                'sup_a'         : self.NewControlId(),
                'sup_b'         : self.NewControlId(),
                'sup_plot'      : self.NewControlId(),
                'sup_cutoff'    : self.NewControlId(),
                'sup_qmax'      : self.NewControlId(),
                },

            'conc': {
                'calc_mw'   : self.NewControlId(),
                'info'      : self.NewControlId(),
                'more'      : self.NewControlId(),
                'conc'      : self.NewControlId(),
                'sup_i0'    : self.NewControlId(),
                'sup_mw'    : self.NewControlId(),
                'sup_conc'  : self.NewControlId(),
                'sup_file'  : self.NewControlId(),
                },

            'VP': {
                'calc_mw'       : self.NewControlId(),
                'info'          : self.NewControlId(),
                'more'          : self.NewControlId(),
                'sup_vp'        : self.NewControlId(),
                'sup_vpc'       : self.NewControlId(),
                'sup_density'   : self.NewControlId(),
                'sup_cutoff'    : self.NewControlId(),
                'sup_qmax'      : self.NewControlId(),
                },

            'abs': {
                'calc_mw'   : self.NewControlId(),
                'info'      : self.NewControlId(),
                'more'      : self.NewControlId(),
                'calib'     : self.NewControlId(),
                'conc'      : self.NewControlId(),
                'sup_pm'    : self.NewControlId(),
                'sup_ps'    : self.NewControlId(),
                'sup_pv'    : self.NewControlId(),
                'sup_sc'    : self.NewControlId(),
                },

            'bayes': {
                'calc_mw'   : self.NewControlId(),
                'info'      : self.NewControlId(),
                'more'      : self.NewControlId(),
                'ci_start'  : self.NewControlId(),
                'ci_end'    : self.NewControlId(),
                'ci_prob'   : self.NewControlId(),
                'mw_prob'   : self.NewControlId(),
                },

            'datclass' : {
                'calc_mw'   : self.NewControlId(),
                'info'      : self.NewControlId(),
                'more'      : self.NewControlId(),
                'shape'     : self.NewControlId(),
                'dmax'      : self.NewControlId(),
            },

          }

        self.mws = {'conc'  : {},
                    'vc'    : {},
                    'vp'    : {},
                    'abs'   : {},
                    }

        if self.has_atsas:
            self.mws['bayes'] = {}
            self.mws['datclass'] = {}

        self.calc_mw_event = threading.Event()
        self.calc_mw_thread_running = threading.Event()
        self.calc_mw_thread = threading.Thread(target=self._calcMWThread)
        self.calc_mw_thread.daemon = True
        self.calc_mw_thread.start()

        topsizer = self._createLayout(self.panel)
        self._initSettings()

        self.panel.SetSizer(topsizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)

        self.SendSizeEvent()

        self.CenterOnParent()

        self.Raise()

    def _createLayout(self, parent):

        self.top_mw = wx.ScrolledWindow(parent, -1)
        self.top_mw.SetScrollRate(20,20)

        self.info_panel = self._createInfoLayout(parent)
        self.vc_panel = self._createVCLayout(self.top_mw)
        self.conc_panel = self._createConcLayout(self.top_mw)
        self.vp_panel = self._createVPLayout(self.top_mw)
        self.abs_panel = self._createAbsLayout(self.top_mw)
        self.button_panel = self._createButtonLayout(parent)

        if self.has_atsas:
            self.bayes_panel = self._createBayesLayout(self.top_mw)
            self.datclass_panel = self._createDatclassLayout(self.top_mw)

        if self.has_atsas:
            mw_sizer = wx.FlexGridSizer(cols=3, vgap=self._FromDIP(5),
                hgap=self._FromDIP(5))
            mw_sizer.AddGrowableCol(2)
        else:
            mw_sizer = wx.FlexGridSizer(cols=2, vgap=self._FromDIP(5),
                hgap=self._FromDIP(5))
        mw_sizer.AddGrowableCol(0)
        mw_sizer.AddGrowableCol(1)

        mw_sizer.Add(self.conc_panel, 0, wx.EXPAND)
        mw_sizer.Add(self.abs_panel, 0, wx.EXPAND)

        if self.has_atsas:
            mw_sizer.Add(self.bayes_panel, 0, wx.EXPAND)

        mw_sizer.Add(self.vc_panel, 0, wx.EXPAND)
        mw_sizer.Add(self.vp_panel, 0, wx.EXPAND)

        if self.has_atsas:
            mw_sizer.Add(self.datclass_panel, 0, wx.EXPAND)


        self.top_mw.SetSizer(mw_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.info_panel, 0, wx.EXPAND)
        top_sizer.Add(wx.StaticLine(parent = parent, style = wx.LI_HORIZONTAL),
            0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border=self._FromDIP(5))
        top_sizer.Add(self.top_mw, 10, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(wx.StaticLine(parent = parent, style = wx.LI_HORIZONTAL),
            0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = self._FromDIP(5))
        top_sizer.Add(self.button_panel, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.LEFT,
            border=self._FromDIP(5))

        return top_sizer

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        vc_plot = wx.FindWindowById(vc_ids['sup_plot'])
        vc_plot.updateColors()

    def _initSettings(self):

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:

            guinier = analysis['guinier']

            for each_key in self.infodata:
                window = wx.FindWindowById(self.infodata[each_key][1], self)
                if abs(float(guinier[each_key])) > 1e3 or abs(float(guinier[each_key])) < 1e-2:
                    window.ChangeValue('%.3E' %(float(guinier[each_key])))
                else:
                    window.ChangeValue('%.4f' %(round(float(guinier[each_key]), 4)))

        self.setFilename(os.path.basename(self.sasm.getParameter('filename')))

        if 'Conc' in self.sasm.getAllParameters():
            conc = str(self.sasm.getParameter('Conc'))
        else:
            conc = ''

        wx.FindWindowById(self.ids['conc']['conc'], self).ChangeValue(conc)

        wx.FindWindowById(self.ids['abs']['conc'], self).ChangeValue(conc)

        if self.raw_settings.get('NormAbsWater') or self.raw_settings.get('NormAbsCarbon'):
            wx.FindWindowById(self.ids['abs']['calib'], self).SetValue(True)


        ref_mw = self.raw_settings.get('MWStandardMW')
        ref_i0 = self.raw_settings.get('MWStandardI0')
        ref_conc = self.raw_settings.get('MWStandardConc')
        ref_file = self.raw_settings.get('MWStandardFile')

        if ref_mw > 0:
            wx.FindWindowById(self.ids['conc']['sup_mw'], self).ChangeValue(str(ref_mw))
        else:
            wx.FindWindowById(self.ids['conc']['sup_mw'], self).ChangeValue('')
        if ref_i0 > 0:
            wx.FindWindowById(self.ids['conc']['sup_i0'], self).ChangeValue(str(ref_i0))
        else:
            wx.FindWindowById(self.ids['conc']['sup_i0'], self).ChangeValue('')
        if ref_conc > 0:
            wx.FindWindowById(self.ids['conc']['sup_conc'], self).ChangeValue(str(ref_conc))
        else:
            wx.FindWindowById(self.ids['conc']['sup_conc'], self).ChangeValue('')
        wx.FindWindowById(self.ids['conc']['sup_file']).ChangeValue(ref_file)


        #Initialize VC MW settings
        aCtrl = wx.FindWindowById(self.ids['VC']['sup_a'], self)
        bCtrl = wx.FindWindowById(self.ids['VC']['sup_b'], self)
        molCtrl = wx.FindWindowById(self.ids['VC']['mol_type'], self)

        try:
            if 'molecularWeight' in analysis:
                molweight = analysis['molecularWeight']
                vc_type = molweight['VolumeOfCorrelation']['Type']
                vc_cutoff = molweight['VolumeOfCorrelation']['Cutoff']
                vc_qmax = molweight['VolumeOfCorrelation']['Q_max']
            else:
                vc_type = self.raw_settings.get('MWVcType')
                vc_cutoff = self.raw_settings.get('MWVcCutoff')
                vc_qmax = self.raw_settings.get('MWVcQmax')

        except Exception:
            vc_type = self.raw_settings.get('MWVcType')
            vc_cutoff = self.raw_settings.get('MWVcCutoff')
            vc_qmax = self.raw_settings.get('MWVcQmax')

        if vc_type == 'Protein':
            aval = self.raw_settings.get('MWVcAProtein')
            bval = self.raw_settings.get('MWVcBProtein')
        else:
            aval = self.raw_settings.get('MWVcARna')
            bval = self.raw_settings.get('MWVcBRna')

        aCtrl.ChangeValue(str(aval))
        bCtrl.ChangeValue(str(bval))
        molCtrl.SetStringSelection(vc_type)

        wx.FindWindowById(self.ids['VC']['sup_cutoff'], self).SetStringSelection(vc_cutoff)
        if vc_cutoff == 'Manual':
            wx.FindWindowById(self.ids['VC']['sup_qmax'], self).ChangeValue(str(vc_qmax))
        else:
            vc_qmax = self._calcVcqmax(vc_cutoff)

        wx.FindWindowById(self.ids['VC']['sup_plot'], self).plotSASM(self.sasm, vc_qmax)

        #Initialize Vp MW settings
        try:
            if 'molecularWeight' in analysis:
                molweight = analysis['molecularWeight']
                vp_cutoff = molweight['PorodVolume']['Cutoff']
                vp_rho = molweight['PorodVolume']['Density']
                vp_qmax = molweight['PorodVolume']['Q_max']

            else:
                vp_cutoff = self.raw_settings.get('MWVpCutoff')
                vp_rho = self.raw_settings.get('MWVpRho')
                vp_qmax = self.raw_settings.get('MWVpQmax')

        except Exception:
            vp_cutoff = self.raw_settings.get('MWVpCutoff')
            vp_rho = self.raw_settings.get('MWVpRho')
            vp_qmax = self.raw_settings.get('MWVpQmax')

        wx.FindWindowById(self.ids['VP']['sup_density'], self).ChangeValue(str(vp_rho))
        wx.FindWindowById(self.ids['VP']['sup_cutoff'], self).SetStringSelection(vp_cutoff)

        if vp_cutoff == 'Manual':
            wx.FindWindowById(self.ids['VP']['sup_qmax'], self).ChangeValue(str(vp_qmax))
        else:
            self._calcVpqmax(vp_cutoff)

        #Initialize Absolute scattering MW settings.

        try:
            if 'molecularWeight' in analysis:
                molweight = analysis['molecularWeight']
                rho_Mprot = float(molweight['Absolute']['Density_dry_protein'])
                rho_solv = float(molweight['Absolute']['Density_buffer'])
                nu_bar = float(molweight['Absolute']['Partial_specific_volume'])
            else:
                rho_Mprot = self.raw_settings.get('MWAbsRhoMprot') # electrons per dry mass of protein
                rho_solv = self.raw_settings.get('MWAbsRhoSolv') # electrons per volume of aqueous solvent
                nu_bar = self.raw_settings.get('MWAbsNuBar') # partial specific volume of the protein

        except Exception:
            rho_Mprot = self.raw_settings.get('MWAbsRhoMprot') # electrons per dry mass of protein
            rho_solv = self.raw_settings.get('MWAbsRhoSolv') # electrons per volume of aqueous solvent
            nu_bar = self.raw_settings.get('MWAbsNuBar') # partial specific volume of the protein

        r0 = self.raw_settings.get('MWAbsR0') #scattering lenght of an electron
        d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
        wx.FindWindowById(self.ids['abs']['sup_pm'], self).ChangeValue('%.2E' %(rho_Mprot))
        wx.FindWindowById(self.ids['abs']['sup_ps'], self).ChangeValue('%.2E' %(rho_solv))
        wx.FindWindowById(self.ids['abs']['sup_pv'], self).ChangeValue('%.4f' %(nu_bar))
        wx.FindWindowById(self.ids['abs']['sup_sc'], self).ChangeValue('%.2E' %(d_rho))

        self.standard_paths = wx.StandardPaths.Get()

        self.calcMW()

    def _createInfoLayout(self, parent):
        box = wx.StaticBox(parent, wx.ID_ANY, 'Info')
        top_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #Filename box
        box1 = wx.StaticBox(box, -1, 'Filename')
        boxSizer1 = wx.StaticBoxSizer(box1, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(box1, -1, '', style = wx.TE_READONLY)
        boxSizer1.Add(self.filenameTxtCtrl, 1)

        # Guinier parameters box
        box2 = wx.StaticBox(box, -1, 'Guinier Parameters')
        boxSizer2 = wx.StaticBoxSizer(box2, wx.HORIZONTAL)

        infoSizer = wx.BoxSizer(wx.HORIZONTAL)

        for key in self.infodata:
            txt = wx.StaticText(box2, -1, self.infodata[key][0])
            ctrl1 = wx.TextCtrl(box2, self.infodata[key][1], '0', style = wx.TE_READONLY)

            infoSizer.Add(txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                border=self._FromDIP(5))
            infoSizer.Add(ctrl1,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                border=self._FromDIP(5))
            infoSizer.AddSpacer(self._FromDIP(5))

        guinierfitbutton = wx.Button(box2, -1, 'Guinier Fit')
        guinierfitbutton.Bind(wx.EVT_BUTTON, self.onGuinierFit)

        boxSizer2.Add(infoSizer, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL ,
            border=self._FromDIP(5))
        boxSizer2.Add(guinierfitbutton, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            border=self._FromDIP(5))


        top_sizer.Add(boxSizer1, 1, wx.EXPAND | wx.ALL ,
            border=self._FromDIP(5))
        top_sizer.Add(boxSizer2, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))

        return top_sizer

    def _createConcLayout(self, parent):
        concbox = wx.StaticBox(parent, -1, 'I(0) Ref. MW')

        conc_ids = self.ids['conc']

        conc_info = wx.Button(concbox, id = conc_ids['info'], label = 'More Info')
        conc_info.Bind(wx.EVT_BUTTON, self._onInfo)

        conc_details = wx.Button(concbox, id = conc_ids['more'], label = 'Show Details')
        conc_details.Bind(wx.EVT_BUTTON, self._onMore)

        conc_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_buttonsizer.Add(conc_details, 0, wx.RIGHT, border=self._FromDIP(5))
        conc_buttonsizer.Add(conc_info, 0)


        concsizer = wx.BoxSizer(wx.HORIZONTAL)

        conc = wx.TextCtrl(concbox, conc_ids['conc'], '',
            size=self._FromDIP((60, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        conc_txt = wx.StaticText(concbox, -1,  'Concentration: ')
        conc_txt2 = wx.StaticText(concbox, -1,  'mg/ml')

        conc.Bind(wx.EVT_TEXT, self._onUpdateConc)

        concsizer.Add(conc_txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        concsizer.Add(conc, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        concsizer.Add(conc_txt2, 0, wx.ALIGN_CENTER_VERTICAL)


        mwsizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_mw = wx.TextCtrl(concbox, conc_ids['calc_mw'], '',
            size = self._FromDIP((80, -1)), style = wx.TE_READONLY)
        mw_txt = wx.StaticText(concbox, -1, 'MW:')
        mw_txt2 = wx.StaticText(concbox, -1,  'kDa')

        mwsizer.Add(mw_txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        mwsizer.Add(conc_mw, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        mwsizer.Add(mw_txt2, 0, wx.ALIGN_CENTER_VERTICAL)


        sup_txt1 = wx.StaticText(concbox, -1, 'Ref. I(0):')
        sup_txt2 = wx.StaticText(concbox, -1, 'Ref. MW:')
        sup_txt3 = wx.StaticText(concbox, -1, 'kDa')
        sup_txt4 = wx.StaticText(concbox, -1, 'Ref. Concentration:')
        sup_txt5 = wx.StaticText(concbox, -1, 'mg/ml')
        sup_txt6 = wx.StaticText(concbox, -1, 'File:')

        sup_i0 = wx.TextCtrl(concbox, conc_ids['sup_i0'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_mw = wx.TextCtrl(concbox, conc_ids['sup_mw'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_conc = wx.TextCtrl(concbox, conc_ids['sup_conc'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_file = wx.TextCtrl(concbox, conc_ids['sup_file'], '',
            size = self._FromDIP((200, -1)), style = wx.TE_READONLY)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer1.Add(sup_i0, 1, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt2, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer2.Add(sup_mw, 1,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer2.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt4, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer3.Add(sup_conc, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer3.Add(sup_txt5, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer4.Add(sup_txt6, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer4.Add(sup_file, 1, wx.ALIGN_CENTER_VERTICAL)

        self.conc_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.conc_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.conc_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.conc_sup_sizer.Add(sup_sizer3, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.conc_sup_sizer.Add(sup_sizer4, 0)


        self.conc_top_sizer = wx.StaticBoxSizer(concbox, wx.VERTICAL)
        self.conc_top_sizer.Add(concsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.conc_top_sizer.Add(mwsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.conc_top_sizer.Add(self.conc_sup_sizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.conc_top_sizer.Add(conc_buttonsizer, 0, wx.ALIGN_CENTER | wx.ALL,
            border=self._FromDIP(5))

        self.conc_top_sizer.Hide(self.conc_sup_sizer, recursive=True)

        return self.conc_top_sizer

    def _createVCLayout(self, parent):

        vcbox = wx.StaticBox(parent, -1, 'Vc MW')

        vc_ids = self.ids['VC']

        vc_info = wx.Button(vcbox, id = vc_ids['info'], label = 'More Info')
        vc_info.Bind(wx.EVT_BUTTON, self._onInfo)

        vc_details = wx.Button(vcbox, id = vc_ids['more'], label = 'Show Details')
        vc_details.Bind(wx.EVT_BUTTON, self._onMore)

        vc_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        vc_buttonsizer.Add(vc_details, 0, wx.RIGHT, border=self._FromDIP(5))
        vc_buttonsizer.Add(vc_info, 0)



        mol_type = wx.Choice(vcbox, vc_ids['mol_type'], choices = ['Protein', 'RNA'])
        mol_type.Bind(wx.EVT_CHOICE, self._onMoleculeChoice)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)

        VCmw = wx.TextCtrl(vcbox, vc_ids['calc_mw'], '',
            size = self._FromDIP((80, -1)), style = wx.TE_READONLY)
        txt = wx.StaticText(vcbox, -1, 'MW:')
        txt2 = wx.StaticText(vcbox, -1,  'kDa')

        mwsizer.Add(txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        mwsizer.Add(VCmw, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        mwsizer.Add(txt2, 0, wx.ALIGN_CENTER_VERTICAL)


        sup_txt1 = wx.StaticText(vcbox, -1, 'Vc:')
        sup_txt2 = wx.StaticText(vcbox, -1, 'A^2')
        sup_txt3 = wx.StaticText(vcbox, -1, 'Qr:')
        sup_txt4 = wx.StaticText(vcbox, -1, 'A^3')
        sup_txt5 = wx.StaticText(vcbox, -1, 'a:')
        sup_txt6 = wx.StaticText(vcbox, -1, 'b:')

        sup_vc = wx.TextCtrl(vcbox, vc_ids['sup_vc'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_qr = wx.TextCtrl(vcbox, vc_ids['sup_qr'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_a = wx.TextCtrl(vcbox, vc_ids['sup_a'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_b = wx.TextCtrl(vcbox, vc_ids['sup_b'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)
        sup_qmax = wx.TextCtrl(vcbox, vc_ids['sup_qmax'], '',
            size = self._FromDIP((80, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        sup_cutoff = wx.Choice(vcbox, vc_ids['sup_cutoff'], choices=['Default',
            '8/Rg', 'log(I0/I(q))', 'Manual'])

        sup_cutoff.Bind(wx.EVT_CHOICE, self._onVcCutoff)
        sup_qmax.Bind(wx.EVT_TEXT, self._updateVcmwParam)

        sup_sizer = wx.FlexGridSizer(rows=2, cols=5, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        sup_sizer.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_vc, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_txt2, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer.Add(sup_txt5, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(10))
        sup_sizer.Add(sup_a, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        sup_sizer.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_qr, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_txt4, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer.Add(sup_txt6, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(10))
        sup_sizer.Add(sup_b, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        sup_sizer2 = wx.FlexGridSizer(cols=3, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        sup_sizer2.Add(wx.StaticText(vcbox, label='q cutoff:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_cutoff, flag=wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.AddSpacer(self._FromDIP(1))
        sup_sizer2.Add(wx.StaticText(vcbox, label='q_max:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_qmax, flag=wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(wx.StaticText(vcbox, label='1/A'),
            flag=wx.ALIGN_CENTER_VERTICAL)

        vc_plot = MWPlotPanel(vcbox, vc_ids['sup_plot'], '')

        self.vc_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vc_sup_sizer.Add(sup_sizer, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.vc_sup_sizer.Add(sup_sizer2, border=5, flag=wx.BOTTOM)
        self.vc_sup_sizer.Add(vc_plot, 0, wx.EXPAND)


        self.vc_top_sizer = wx.StaticBoxSizer(vcbox, wx.VERTICAL)
        self.vc_top_sizer.Add(mol_type, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.vc_top_sizer.Add(mwsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.vc_top_sizer.Add(self.vc_sup_sizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.vc_top_sizer.Add(vc_buttonsizer, 0, wx.ALIGN_CENTER | wx.ALL,
            border=self._FromDIP(5))

        self.vc_top_sizer.Hide(self.vc_sup_sizer, recursive = True)

        return self.vc_top_sizer

    def _createVPLayout(self, parent):
        vpbox = wx.StaticBox(parent, -1, 'Vp MW')

        vp_ids = self.ids['VP']

        vp_info = wx.Button(vpbox, id = vp_ids['info'], label = 'More Info')
        vp_info.Bind(wx.EVT_BUTTON, self._onInfo)

        vp_details = wx.Button(vpbox, id = vp_ids['more'], label = 'Show Details')
        vp_details.Bind(wx.EVT_BUTTON, self._onMore)

        vp_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        vp_buttonsizer.Add(vp_details, 0, wx.RIGHT, border=self._FromDIP(5))
        vp_buttonsizer.Add(vp_info, 0)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)

        VpMW = wx.TextCtrl(vpbox, vp_ids['calc_mw'], '',
            size = self._FromDIP((80, -1)), style = wx.TE_READONLY)
        txt = wx.StaticText(vpbox, -1, 'MW:')
        txt2 = wx.StaticText(vpbox, -1,  'kDa')

        mwsizer.Add(txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        mwsizer.Add(VpMW, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        mwsizer.Add(txt2, 0, wx.ALIGN_CENTER_VERTICAL)

        mw_warning = RAWCustomCtrl.StaticText(vpbox, label=('Warning: final '
            'q point is outside\nthe extrapolation region\n(0.1 <= q <= 0.5 1/A), '
            'no\ncorrection has been applied!'))

        self.mw_warning_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mw_warning_sizer.Add(mw_warning, wx.EXPAND)


        sup_txt1 = wx.StaticText(vpbox, -1, 'Vp:')
        sup_txt2 = wx.StaticText(vpbox, -1, 'A^3')
        sup_txt3 = wx.StaticText(vpbox, -1, 'Corrected Vp:')
        sup_txt4 = wx.StaticText(vpbox, -1, 'A^3')
        sup_txt5 = wx.StaticText(vpbox, -1, 'Macromolecule Density:')
        sup_txt6 = wx.StaticText(vpbox, -1, 'kDa/A^3')
        sup_txt7 = wx.StaticText(vpbox, wx.ID_ANY, 'q cutoff:')
        sup_txt8 = wx.StaticText(vpbox, wx.ID_ANY, 'q_max:')
        sup_txt9 = wx.StaticText(vpbox, wx.ID_ANY, '1/A')

        sup_vp = wx.TextCtrl(vpbox, vp_ids['sup_vp'], '',
            size = self._FromDIP((80, -1)), style = wx.TE_READONLY)
        sup_vpc = wx.TextCtrl(vpbox, vp_ids['sup_vpc'], '',
            size = self._FromDIP((80, -1)), style = wx.TE_READONLY)
        sup_density = wx.TextCtrl(vpbox, vp_ids['sup_density'], '',
            size = self._FromDIP((80, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        sup_qmax = wx.TextCtrl(vpbox, vp_ids['sup_qmax'], '',
         size = self._FromDIP((80, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))

        sup_cutoff = wx.Choice(vpbox, vp_ids['sup_cutoff'], choices=['Default',
            '8/Rg', 'log(I0/I(q))', 'Manual'])

        sup_cutoff.Bind(wx.EVT_CHOICE, self._onVpCutoff)
        sup_density.Bind(wx.EVT_TEXT, self._updateVpmwParam)
        sup_qmax.Bind(wx.EVT_TEXT, self._updateVpmwParam)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer1.Add(sup_vp, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer1.Add(sup_txt2, 0, wx.ALIGN_CENTER_VERTICAL)

        vpc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        vpc_sizer.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        vpc_sizer.Add(sup_vpc, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        vpc_sizer.Add(sup_txt4, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt5, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer3.Add(sup_density, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer3.Add(sup_txt6, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer4.Add(sup_txt7, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer4.Add(sup_cutoff, 1, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer5 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer5.Add(sup_txt8, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer5.Add(sup_qmax, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer5.Add(sup_txt9, 0, wx.ALIGN_CENTER_VERTICAL)

        self.vp_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vp_sup_sizer.Add(sup_sizer4, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.vp_sup_sizer.Add(sup_sizer5, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.vp_sup_sizer.Add(sup_sizer3,0, wx.BOTTOM, border=self._FromDIP(5))
        self.vp_sup_sizer.Add(sup_sizer1, 0)

        self.vp_top_sizer = wx.StaticBoxSizer(vpbox, wx.VERTICAL)
        self.vp_top_sizer.Add(mwsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT, border=self._FromDIP(5))
        self.vp_top_sizer.Add(vpc_sizer, border=self._FromDIP(5), flag=wx.LEFT|
            wx.RIGHT|wx.TOP)
        self.vp_top_sizer.Add(self.mw_warning_sizer, 0, wx.TOP|wx.LEFT|
            wx.RIGHT|wx.EXPAND, border=self._FromDIP(5))
        self.vp_top_sizer.Add(self.vp_sup_sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        self.vp_top_sizer.Add(vp_buttonsizer, 0, wx.ALIGN_CENTER | wx.ALL,
            border=self._FromDIP(5))

        self.vp_top_sizer.Hide(self.vp_sup_sizer, recursive = True)
        self.vp_top_sizer.Hide(self.mw_warning_sizer, recursive = True)

        return self.vp_top_sizer

    def _createAbsLayout(self, parent):
        absbox = wx.StaticBox(parent, -1, 'Abs. MW')

        abs_ids = self.ids['abs']

        abs_checkbox = wx.CheckBox(absbox, id=abs_ids['calib'],
            label='Intensity on Absolute Scale')
        abs_checkbox.SetValue(False)
        abs_checkbox.Bind(wx.EVT_CHECKBOX, self._onAbsCheck)


        abs_info = wx.Button(absbox, id = abs_ids['info'], label = 'More Info')
        abs_info.Bind(wx.EVT_BUTTON, self._onInfo)

        abs_details = wx.Button(absbox, id = abs_ids['more'], label = 'Show Details')
        abs_details.Bind(wx.EVT_BUTTON, self._onMore)

        abs_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        abs_buttonsizer.Add(abs_details, 0, wx.RIGHT, border=self._FromDIP(5))
        abs_buttonsizer.Add(abs_info, 0)

        concsizer = wx.BoxSizer(wx.HORIZONTAL)

        conc = wx.TextCtrl(absbox, abs_ids['conc'], '', size=self._FromDIP((60, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        conc_txt = wx.StaticText(absbox, -1,  'Concentration:')
        conc_txt2 = wx.StaticText(absbox, -1,  'mg/ml')

        conc.Bind(wx.EVT_TEXT, self._onUpdateConc)

        concsizer.Add(conc_txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        concsizer.Add(conc, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        concsizer.Add(conc_txt2, 0,  wx.ALIGN_CENTER_VERTICAL)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)

        absMW = wx.TextCtrl(absbox, abs_ids['calc_mw'], '',
            size = self._FromDIP((80, -1)), style = wx.TE_READONLY)
        txt = wx.StaticText(absbox, -1, 'MW:')
        txt2 = wx.StaticText(absbox, -1,  'kDa')

        mwsizer.Add(txt,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        mwsizer.Add(absMW, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        mwsizer.Add(txt2, 0, wx.ALIGN_CENTER_VERTICAL)


        sup_txt1 = wx.StaticText(absbox, -1, '# electrons per mass dry macromolecule:')
        sup_txt2 = wx.StaticText(absbox, -1, 'e-/g')
        sup_txt3 = wx.StaticText(absbox, -1, '# electrons per volume of buffer:')
        sup_txt4 = wx.StaticText(absbox, -1, 'e-/cm^3')
        sup_txt5 = wx.StaticText(absbox, -1, 'Protein partial specific volume:')
        sup_txt6 = wx.StaticText(absbox, -1, 'cm^3/g')
        sup_txt9 = wx.StaticText(absbox, -1, 'Calc. Scattering contrast per mass:')
        sup_txt10 = wx.StaticText(absbox, -1, 'e- cm/g')

        sup_pm = wx.TextCtrl(absbox, abs_ids['sup_pm'], '',
            size = self._FromDIP((80, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        sup_ps = wx.TextCtrl(absbox, abs_ids['sup_ps'], '',
            size = self._FromDIP((80, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        sup_pv = wx.TextCtrl(absbox, abs_ids['sup_pv'], '',
            size = self._FromDIP((80, -1)),
            validator=RAWCustomCtrl.CharValidator('float'))
        sup_sc = wx.TextCtrl(absbox, abs_ids['sup_sc'], '',
            size = self._FromDIP((80, -1)), style=wx.TE_READONLY)

        sup_pm.Bind(wx.EVT_TEXT, self._updateAbsmwParams)
        sup_ps.Bind(wx.EVT_TEXT, self._updateAbsmwParams)
        sup_pv.Bind(wx.EVT_TEXT, self._updateAbsmwParams)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer1.Add(sup_pm, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer1.Add(sup_txt2, 0,wx.ALIGN_CENTER_VERTICAL)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer2.Add(sup_ps, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer2.Add(sup_txt4, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt5, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer3.Add(sup_pv, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer3.Add(sup_txt6, 0, wx.ALIGN_CENTER_VERTICAL)

        sup_sizer5 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer5.Add(sup_txt9, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer5.Add(sup_sc, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,
            border=self._FromDIP(5))
        sup_sizer5.Add(sup_txt10, 0, wx.ALIGN_CENTER_VERTICAL)

        self.abs_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.abs_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.abs_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.abs_sup_sizer.Add(sup_sizer3, 0, wx.BOTTOM, border=self._FromDIP(5))
        self.abs_sup_sizer.Add(sup_sizer5, 0)


        self.abs_top_sizer = wx.StaticBoxSizer(absbox, wx.VERTICAL)
        self.abs_top_sizer.Add(abs_checkbox, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.abs_top_sizer.Add(concsizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        self.abs_top_sizer.Add(mwsizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        self.abs_top_sizer.Add(self.abs_sup_sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        self.abs_top_sizer.Add(abs_buttonsizer, 0, wx.ALIGN_CENTER|wx.ALL,
            border=self._FromDIP(5))

        self.abs_top_sizer.Hide(self.abs_sup_sizer, recursive = True)

        return self.abs_top_sizer

    def _createBayesLayout(self, parent):
        bayes_ids = self.ids['bayes']

        self.bayes_top_sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, "datmw Bayes MW")
        ctrl_parent = self.bayes_top_sizer.GetStaticBox()

        mw = wx.TextCtrl(ctrl_parent, bayes_ids['calc_mw'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        ci_start = wx.TextCtrl(ctrl_parent, bayes_ids['ci_start'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        ci_end = wx.TextCtrl(ctrl_parent, bayes_ids['ci_end'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        ci_prob = wx.TextCtrl(ctrl_parent, bayes_ids['ci_prob'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        mw_prob = wx.TextCtrl(ctrl_parent, bayes_ids['mw_prob'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        info_button = wx.Button(ctrl_parent, bayes_ids['info'], label='More Info')
        details_button = wx.Button(ctrl_parent, bayes_ids['more'],
            label='Show Details')

        info_button.Bind(wx.EVT_BUTTON, self._onInfo)
        details_button.Bind(wx.EVT_BUTTON, self._onMore)

        mw_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mw_sizer.Add(wx.StaticText(ctrl_parent, label='MW (kDa):'),
            border=self._FromDIP(5), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
        mw_sizer.Add(mw, flag=wx.ALIGN_CENTER_VERTICAL)

        conf_sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
        conf_sub_sizer.Add(ci_start, border=self._FromDIP(5),
            flag=wx.ALIGN_CENTER_VERTICAL)
        conf_sub_sizer.Add(wx.StaticText(ctrl_parent, label='to'),
            border=self._FromDIP(5), flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        conf_sub_sizer.Add(ci_end, border=self._FromDIP(5),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)

        conf_sizer = wx.BoxSizer(wx.VERTICAL)
        conf_sizer.Add(wx.StaticText(ctrl_parent, label='Conf. Interval (kDa):'),
            flag=wx.ALIGN_CENTER)
        conf_sizer.Add(conf_sub_sizer, border=self._FromDIP(5), flag=wx.TOP)

        self.bayes_sup_sizer = wx.FlexGridSizer(cols=2, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        self.bayes_sup_sizer.Add(wx.StaticText(ctrl_parent,
            label='MW Probability:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.bayes_sup_sizer.Add(mw_prob, flag=wx.ALIGN_CENTER_VERTICAL)
        self.bayes_sup_sizer.Add(wx.StaticText(ctrl_parent,
            label='Conf. Interval Prob.:'))
        self.bayes_sup_sizer.Add(ci_prob, flag=wx.ALIGN_CENTER_VERTICAL)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(details_button, 0, wx.RIGHT, border=self._FromDIP(2))
        button_sizer.Add(info_button, 0, wx.LEFT, border=self._FromDIP(2))

        self.bayes_top_sizer.Add(mw_sizer, border=self._FromDIP(5),
            flag=wx.TOP|wx.LEFT|wx.RIGHT)
        self.bayes_top_sizer.Add(conf_sizer, border=self._FromDIP(5),
            flag=wx.TOP|wx.LEFT|wx.RIGHT)
        self.bayes_top_sizer.Add(self.bayes_sup_sizer, border=self._FromDIP(5),
            flag=wx.TOP|wx.LEFT|wx.RIGHT)
        self.bayes_top_sizer.Add(button_sizer, border=self._FromDIP(5),
            flag=wx.ALL|wx.ALIGN_CENTER_HORIZONTAL)

        self.bayes_top_sizer.Hide(self.bayes_sup_sizer, recursive = True)

        return self.bayes_top_sizer

    def _createDatclassLayout(self, parent):
        datclass_ids = self.ids['datclass']

        self.datclass_top_sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, "Shape&&Size MW")
        ctrl_parent = self.datclass_top_sizer.GetStaticBox()

        mw = wx.TextCtrl(ctrl_parent, datclass_ids['calc_mw'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        shape = wx.TextCtrl(ctrl_parent, datclass_ids['shape'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        dmax = wx.TextCtrl(ctrl_parent, datclass_ids['dmax'], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        info_button = wx.Button(ctrl_parent, datclass_ids['info'], label='More Info')
        details_button = wx.Button(ctrl_parent, datclass_ids['more'],
            label='Show Details')

        info_button.Bind(wx.EVT_BUTTON, self._onInfo)
        details_button.Bind(wx.EVT_BUTTON, self._onMore)

        mw_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mw_sizer.Add(wx.StaticText(ctrl_parent, label='MW (kDa):'),
            border=self._FromDIP(5), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
        mw_sizer.Add(mw, flag=wx.ALIGN_CENTER_VERTICAL)

        self.datclass_sup_sizer = wx.FlexGridSizer(cols=2, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        self.datclass_sup_sizer.Add(wx.StaticText(ctrl_parent,
            label='DATCLASS shape:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.datclass_sup_sizer.Add(shape, flag=wx.ALIGN_CENTER_VERTICAL)
        self.datclass_sup_sizer.Add(wx.StaticText(ctrl_parent,
            label='DATCLASS Dmax:'))
        self.datclass_sup_sizer.Add(dmax, flag=wx.ALIGN_CENTER_VERTICAL)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(details_button, 0, wx.RIGHT, self._FromDIP(2))
        button_sizer.Add(info_button, 0, wx.LEFT, self._FromDIP(2))

        self.datclass_top_sizer.Add(mw_sizer, border=self._FromDIP(5),
            flag=wx.TOP|wx.LEFT|wx.RIGHT)
        self.datclass_top_sizer.Add(self.datclass_sup_sizer,
            border=self._FromDIP(5), flag=wx.TOP|wx.LEFT|wx.RIGHT)
        self.datclass_top_sizer.Add(button_sizer, border=self._FromDIP(5),
            flag=wx.ALL|wx.ALIGN_CENTER_HORIZONTAL)

        self.datclass_top_sizer.Hide(self.datclass_sup_sizer, recursive = True)

        return self.datclass_top_sizer

    def _createButtonLayout(self, parent):
        button = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(parent, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        params_button = wx.Button(parent, -1, 'Change Advanced Parameters')
        params_button.Bind(wx.EVT_BUTTON, self.onChangeParams)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(params_button, 0, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(savebutton, 0, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(button, 0, wx.RIGHT, border=self._FromDIP(5))

        return buttonSizer

    def showBusy(self, show=True):
        if show:
            self.bi = wx.BusyInfo('Calculating Molecular weight, please wait.', self)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass

    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def onGuinierFit(self,evt):

        strconc = wx.FindWindowById(self.ids['conc']['conc'], self).GetValue()

        try:
            conc = float(strconc)
        except ValueError:
            conc = -1

        if strconc != '' and conc > 0:
            self.sasm.setParameter('Conc', conc)

        self.main_frame.showGuinierFitFrame(self.sasm, self.manip_item)

    def updateGuinierInfo(self):
        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:

            guinier = analysis['guinier']

            for each_key in self.infodata:
                if each_key in guinier:
                    window = wx.FindWindowById(self.infodata[each_key][1], self)
                    if abs(float(guinier[each_key])) > 1e3 or abs(float(guinier[each_key])) < 1e-2:
                        window.SetValue('%.3E' %(float(guinier[each_key])))
                    else:
                        window.SetValue('%.4f' %(round(float(guinier[each_key]), 4)))

        if 'Conc' in self.sasm.getAllParameters():
            conc = str(self.sasm.getParameter('Conc'))
            wx.FindWindowById(self.ids['conc']['conc'], self).ChangeValue(conc)
            wx.FindWindowById(self.ids['abs']['conc'], self).ChangeValue(conc)

        vp_cutoff = wx.FindWindowById(self.ids['VP']['sup_cutoff']).GetStringSelection()
        self._calcVpqmax(vp_cutoff)

        vc_cutoff = wx.FindWindowById(self.ids['VC']['sup_cutoff']).GetStringSelection()
        qmax = self._calcVcqmax(vc_cutoff)

        wx.FindWindowById(self.ids['VC']['sup_plot'], self).plotSASM(self.sasm, qmax)

        self.calcMW()

    def updateMWInfo(self):
        if self.raw_settings.get('NormAbsWater') or self.raw_settings.get('NormAbsCarbon'):
            wx.FindWindowById(self.ids['abs']['calib'], self).SetValue(True)

        ref_mw = self.raw_settings.get('MWStandardMW')
        ref_i0 = self.raw_settings.get('MWStandardI0')
        ref_conc = self.raw_settings.get('MWStandardConc')
        ref_file = self.raw_settings.get('MWStandardFile')

        if ref_mw > 0:
            wx.FindWindowById(self.ids['conc']['sup_mw'], self).ChangeValue(str(ref_mw))
        else:
            wx.FindWindowById(self.ids['conc']['sup_mw'], self).ChangeValue('')
        if ref_i0 > 0:
            wx.FindWindowById(self.ids['conc']['sup_i0'], self).ChangeValue(str(ref_i0))
        else:
            wx.FindWindowById(self.ids['conc']['sup_i0'], self).ChangeValue('')
        if ref_conc > 0:
            wx.FindWindowById(self.ids['conc']['sup_conc'], self).ChangeValue(str(ref_conc))
        else:
            wx.FindWindowById(self.ids['conc']['sup_conc'], self).ChangeValue('')
        wx.FindWindowById(self.ids['conc']['sup_file'], self).ChangeValue(ref_file)


        #Initialize VC MW settings
        aCtrl = wx.FindWindowById(self.ids['VC']['sup_a'], self)
        bCtrl = wx.FindWindowById(self.ids['VC']['sup_b'], self)
        molCtrl = wx.FindWindowById(self.ids['VC']['mol_type'], self)

        vc_type = molCtrl.GetStringSelection()

        if vc_type == 'Protein':
            aval = self.raw_settings.get('MWVcAProtein')
            bval = self.raw_settings.get('MWVcBProtein')
        else:
            aval = self.raw_settings.get('MWVcARna')
            bval = self.raw_settings.get('MWVcBRna')

        aCtrl.ChangeValue(str(aval))
        bCtrl.ChangeValue(str(bval))
        molCtrl.SetStringSelection(vc_type)

        vc_cutoff = self.raw_settings.get('MWVcCutoff')
        vc_qmax_manual = self.raw_settings.get('MWVcQmax')

        wx.FindWindowById(self.ids['VC']['sup_cutoff'], self).SetStringSelection(vc_cutoff)

        if vc_cutoff == 'Manual':
            wx.FindWindowById(self.ids['VC']['sup_qmax'], self).ChangeValue(str(vc_qmax_manual))

        self._calcVpqmax(vc_cutoff)

        #Initialize Vp MW settings
        vp_rho = self.raw_settings.get('MWVpRho')
        vp_cutoff = self.raw_settings.get('MWVpCutoff')
        vp_qmax_manual = self.raw_settings.get('MWVpQmax')

        wx.FindWindowById(self.ids['VP']['sup_density'], self).ChangeValue(str(vp_rho))
        wx.FindWindowById(self.ids['VP']['sup_cutoff'], self).SetStringSelection(vp_cutoff)

        if vp_cutoff == 'Manual':
            wx.FindWindowById(self.ids['VP']['sup_qmax'], self).ChangeValue(str(vp_qmax_manual))


        #Initialize Absolute scattering MW settings.
        rho_Mprot = self.raw_settings.get('MWAbsRhoMprot') # electrons per dry mass of protein
        rho_solv = self.raw_settings.get('MWAbsRhoSolv') # electrons per volume of aqueous solvent
        nu_bar = self.raw_settings.get('MWAbsNuBar') # partial specific volume of the protein
        r0 = self.raw_settings.get('MWAbsR0') #scattering lenght of an electron
        d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
        wx.FindWindowById(self.ids['abs']['sup_pm'], self).ChangeValue('%.2E' %(rho_Mprot))
        wx.FindWindowById(self.ids['abs']['sup_ps'], self).ChangeValue('%.2E' %(rho_solv))
        wx.FindWindowById(self.ids['abs']['sup_pv'], self).ChangeValue('%.4f' %(nu_bar))
        wx.FindWindowById(self.ids['abs']['sup_sc'], self).ChangeValue('%.2E' %(d_rho))

        self._calcVpqmax(vp_cutoff)

        self.calcMW()

    def _onInfo(self,evt):
        evt_id = evt.GetId()

        if evt_id == self.ids['conc']['info']:
            msg = ("The scattering at zero angle, I(0) is proportional "
                "to the molecular weight of the macromolecule, and the "
                "concentration and contrast of the macromolecule in solution. "
                "If a reference sample of known molecular weight and "
                "concentration is measured, it can be used to calibrate the "
                "molecular weight of any other scattering profile with known "
                "concentration (assuming constant contrast between reference "
                "and sample, and a monodisperse sample). Molecular weight is "
                "calculated as:\n\n"
                "MW_m = (I(0)_m / c_m) * (MM_st)/(I(0)_st / c_st)\n\n"
                "where MW is the molecular weight, c is the concentration, "
                "and '_m' and '_st' designates quantities from the "
                "macromolecule of interest and the standard respectively. "
                "For a reference see, among many, Mylonas, E. & Svergun, "
                "D. I. (2007). J. Appl. Crystallogr. 40, s245-s249.\n\n"
                "This method can yield inaccurate results if:\n"
                "- The reference is not properly calibrated (concentration, "
                "I(0) measurement).\n"
                "- I(0) is poorly determined.\n"
                "- Sample concentration is poorly determined.\n"
                "- The contrast between the macromolecule and buffer is "
                "significantly different between the reference and sample.")

        elif evt_id == self.ids['VC']['info']:
            msg = ("This method uses the approach described in: Rambo, R. "
                "P. & Tainer, J. A. (2013). Nature. 496, 477-481, please "
                "cite this paper in addition to the RAW paper if you use "
                "this method. This method should work for both compact and "
                "flexible macromolecules. The authors claim the error in "
                "MW determination is ~5-10%.\n\n"
                "This method can yield inaccurate results if:\n"
                "- The integral of q*I(q) doesn't converge (click 'Show "
                "Details' to see), which can indicate the scattering profile "
                "is not measured to high enough q or that there is a bad "
                "buffer match.\n"
                "- I(0) and/or Rg are poorly determined.\n"
                "- You have a protein-nucleic acid complex.\n"
                "- Your molecule is less than ~15-20 kDa.")

        elif evt_id == self.ids['VP']['info']:
            msg = ("This method uses the approach described in: Piiadov, "
                "V., Ares de Araujo, E., Neto, M. O., Craievich, A. F., "
                "& Polikarpov,  I. (2019). Prot. Sci. 28(2), 454-463,"
                "please cite this paper in addition to the RAW "
                "paper if you use this method. It applies a correction to "
                "the Porod volume, which has only been calculated for 0.1 "
                "< q_max < 0.5 1/A. A cutoff is automatically applied to q "
                "to keep it in this region, the cutoff also truncates based "
                "protein size. The authors report a median of 12% uncertainty "
                "for calculated molecular weight from globular proteins.\n\n"
                "This method can yield inaccurate results if:\n"
                "- The molecule is not globular (i.e. is flexible or extended).\n"
                "- I(0) is poorly determined.\n"
                "- The protein density used is inaccurate.\n"
                "- Your molecule is not a protein.\n\n"
                "This method is also available in an online calculator from "
                "the original authors: http://saxs.ifsc.usp.br/).")

        elif evt_id == self.ids['abs']['info']:
            msg = ("This uses the absolute calibration of the scattering profile to determine the molecular weight, "
                   "as described in Orthaber, D., Bergmann, A., & Glatter, O. (2000). J. Appl. Crystallogr. 33, "
                   "218-225. By determining the absolute scattering at I(0), if the sample concentration is also "
                   "known, the molecular weight is calculated as:\n\n"
                   "MW = (N_A * I(0) / c)/(drho_M^2)\n\n"
                   "where N_A is the Avagadro number, c is the concentration, and drho_M is the scattering contrast "
                   "per mass. The accuracy of this method was assessed in Mylonas, E. & Svergun, D. I. (2007). "
                   "J. Appl. Crystallogr. 40, s245-s249, and for most proteins is <~10%.\n\n"
                   "This method can yield inaccurate results if:\n"
                   "- The absolute calibration is not accurate.\n"
                   "- I(0) is poorly determined.\n"
                   "- Sample concentration is poorly determined.\n"
                   "- Scattering contrast is wrong, either from buffer changes or macromolecule type "
                   "(default settings are for protein).")

        elif evt_id == self.ids['bayes']['info']:
            msg = ("A method for calculating a molecular weight using Bayesian "
                "inference with the molecular weight calculations from the Porod "
                "volume, volume of correlation, and comparison to known structures "
                "methods as the evidence. This method was described in Hajizadeh, "
                "N. R., Franke, D., Jeffries, C. M. & Svergun, D. I. (2018), "
                "Sci. Rep. 8, 7204. Please cite this paper in addition to the "
                "RAW paper if you use this method. Essentially, it takes a large test "
                "dataset of theoretical scattering profiles, calculates the "
                "molecular weight for each using each method, then creates a "
                "probability distribution for each method that describes the "
                "probability of obtaining a particular calculated molecular "
                "weight given the true molecular weight. These probabilities "
                "are combined across all the methods, and the most likely molecular "
                "weight is thus estimated.\n\n"
                "The authors found that for the theoretical scattering profiles "
                "used, the median molecular weight from this method was "
                "accurate and the median absolute deviation was 4%. Overall, "
                "they reported that it was more accurate than any individual "
                "method. It may be that the uncertainty in this method is "
                "usually closer to ~5% than 10% for the other methods.\n\n"
                "This method can yield inaccurate results if:\n"
                "- Your molecule is not a protein.\n"
                "- There are significant subtraction errors.\n"
                "- The other methods it use all return poor MW estimates.")

        elif evt_id == self.ids['datclass']['info']:
            msg = ("A molecular weight estimation using a machine learning "
                "method that categories SAXS data into shape categories based "
                "on comparison with a catalog of known structures from the PDB. "
                "This method was described in Franke, D., Jeffries, C. M. & "
                "Svergun, D.I. (2018, Biophys. J. 114, 2485-2492. Please "
                "cite this paper in addition to the RAW paper if you use "
                "this method. By finding the nearest structures in shape and "
                "size (also the name of the method: Shape&Size), you can "
                "obtain estimates for the molecular weight of the sample.\n\n"
                "The authors found that, for the theoretical scattering profiles "
                "used for testing, the method calculated molecular weights "
                "within 10% of the expected value for 90% of the test data. "
                "Other work found that for the test dataset the median molecular "
                "weight was correct and the median absolute deviation was 4%. "
                "It is reasonable to say that the uncertainty in molecular "
                "weight from this method is ~10% for most systems, though there "
                "are outliers.\n\n"
                "This method can yield inaccurate results if:\n"
                "- The system is flexible.\n"
                "- Your molecule is not a protein.")
        if platform.system() == 'Windows':
            msg = '\n' + msg
        dlg = wx.MessageDialog(self, msg, "Calculating Molecular Weight",
            style = wx.ICON_INFORMATION | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def _onMore(self, evt):
        evt_id = evt.GetId()

        if evt_id == self.ids['conc']['more']:
            if self.conc_top_sizer.IsShown(self.conc_sup_sizer):
                self.conc_top_sizer.Hide(self.conc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['conc']['more'], self)
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.conc_top_sizer.Show(self.conc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['conc']['more'], self)
                button.SetLabel('Hide Details')
                self.panel.Layout()

        elif evt_id == self.ids['VC']['more']:
            if self.vc_top_sizer.IsShown(self.vc_sup_sizer):
                self.vc_top_sizer.Hide(self.vc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VC']['more'], self)
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.vc_top_sizer.Show(self.vc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VC']['more'], self)
                button.SetLabel('Hide Details')
                self.panel.Layout()

        elif evt_id == self.ids['VP']['more']:
            if self.vp_top_sizer.IsShown(self.vp_sup_sizer):
                self.vp_top_sizer.Hide(self.vp_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VP']['more'], self)
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.vp_top_sizer.Show(self.vp_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VP']['more'], self)
                button.SetLabel('Hide Details')
                self.panel.Layout()
        elif evt_id == self.ids['abs']['more']:
            if self.abs_top_sizer.IsShown(self.abs_sup_sizer):
                self.abs_top_sizer.Hide(self.abs_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['abs']['more'], self)
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.abs_top_sizer.Show(self.abs_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['abs']['more'], self)
                button.SetLabel('Hide Details')
                self.panel.Layout()

        elif evt_id == self.ids['bayes']['more']:
            if self.bayes_top_sizer.IsShown(self.bayes_sup_sizer):
                self.bayes_top_sizer.Hide(self.bayes_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['bayes']['more'], self)
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.bayes_top_sizer.Show(self.bayes_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['bayes']['more'], self)
                button.SetLabel('Hide Details')
                self.panel.Layout()

        elif evt_id == self.ids['datclass']['more']:
            if self.datclass_top_sizer.IsShown(self.datclass_sup_sizer):
                self.datclass_top_sizer.Hide(self.datclass_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['datclass']['more'], self)
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.datclass_top_sizer.Show(self.datclass_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['datclass']['more'], self)
                button.SetLabel('Hide Details')
                self.panel.Layout()


    def _onMoleculeChoice(self,evt):
        vc_ids = self.ids['VC']

        aCtrl = wx.FindWindowById(vc_ids['sup_a'], self)
        bCtrl = wx.FindWindowById(vc_ids['sup_b'], self)

        molCtrl = evt.GetEventObject()
        val = molCtrl.GetStringSelection()

        if val == 'Protein':
            aval = self.raw_settings.get('MWVcAProtein')
            bval = self.raw_settings.get('MWVcBProtein')
        else:
            aval = self.raw_settings.get('MWVcARna')
            bval = self.raw_settings.get('MWVcBRna')

        aCtrl.ChangeValue(str(aval))
        bCtrl.ChangeValue(str(bval))

        self.calcVcMW()

    def _onUpdateConc(self, evt):
        evt_id = evt.GetId()

        concCtrl = evt.GetEventObject()
        val = concCtrl.GetValue()

        if evt_id == self.ids['conc']['conc']:
            wx.FindWindowById(self.ids['abs']['conc'], self).ChangeValue(val)
        else:
            wx.FindWindowById(self.ids['conc']['conc'], self).ChangeValue(val)

        self.calcConcMW()
        self.calcAbsMW()

    def _onVpCutoff(self, evt):
        choice = evt.GetString()

        self._calcVpqmax(choice)

    def _calcVpqmax(self, choice):
        q_max_ctrl = wx.FindWindowById(self.ids['VP']['sup_qmax'], self)

        q = self.sasm.getQ()
        i = self.sasm.getI()

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            i0 = float(guinier['I0'])
            rg = float(guinier['Rg'])
        else:
            i0 = 0
            rg = 0

        if choice != 'Manual':
            q_max_ctrl.Disable()

        else:
            q_max_ctrl.Enable()

        try:
            qmax = float(q_max_ctrl.GetValue())
        except Exception:
            qmax = None

        qmax = SASCalc.calcVqmax(q, i, rg, i0, choice, qmax)

        q_max_ctrl.ChangeValue(str(qmax))

        self.calcVpMW()

    def _onVcCutoff(self, evt):
        choice = evt.GetString()

        qmax = self._calcVcqmax(choice)

        wx.FindWindowById(self.ids['VC']['sup_plot'], self).plotSASM(self.sasm, qmax)

    def _calcVcqmax(self, choice):
        q_max_ctrl = wx.FindWindowById(self.ids['VC']['sup_qmax'], self)

        q = self.sasm.getQ()
        i = self.sasm.getI()

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            i0 = float(guinier['I0'])
            rg = float(guinier['Rg'])
        else:
            i0 = 0
            rg = 0

        if choice != 'Manual':
            q_max_ctrl.Disable()

        else:
            q_max_ctrl.Enable()

        try:
            qmax = float(q_max_ctrl.GetValue())
        except Exception:
            qmax = None

        qmax = SASCalc.calcVqmax(q, i, rg, i0, choice, qmax)

        q_max_ctrl.ChangeValue(str(qmax))

        self.calcVcMW()

        return qmax

    def _updateVpmwParam(self, evt):

        try:
            float(evt.GetEventObject().GetValue())
            self.calcVpMW()
        except Exception:
            pass

    def _updateVcmwParam(self, evt):

        try:
            val = float(evt.GetEventObject().GetValue())
            self.calcVcMW()

            if evt.GetEventObject() == wx.FindWindowById(self.ids['VC']['sup_qmax'], self):
                wx.FindWindowById(self.ids['VC']['sup_plot'], self).plotSASM(self.sasm, val)
        except Exception:
            pass

    def _updateAbsmwParams(self, evt):
        try:
            float(evt.GetEventObject().GetValue())
            self.calcAbsMW()
        except Exception:
            pass

    def _onAbsCheck(self, evt):
        chkbox = evt.GetEventObject()

        if chkbox.GetValue():
            wx.FindWindowById(self.ids['abs']['conc'], self).Enable()
            self.calcAbsMW()
        else:
            wx.FindWindowById(self.ids['abs']['conc'], self).Disable()
            wx.FindWindowById(self.ids['abs']['calc_mw'], self).ChangeValue('')

    def _showVpMWWarning(self, show):

        if show:
            if not self.vp_top_sizer.IsShown(self.mw_warning_sizer):
                self.vp_top_sizer.Show(self.mw_warning_sizer,recursive=True)
                self.panel.Layout()

        else:
            if self.vp_top_sizer.IsShown(self.mw_warning_sizer):
                self.vp_top_sizer.Hide(self.mw_warning_sizer,recursive=True)
                self.panel.Layout()

    def onChangeParams(self, evt):

        self.main_frame.showOptionsDialog(focusHead='Molecular Weight')

    def onCloseButton(self, evt):
        self.OnClose()

    def onSaveInfo(self, evt):
        calcData = {'I(0)Concentration'  : {},
                    'VolumeOfCorrelation': {},
                    'PorodVolume'        : {},
                    'Absolute'           : {}}

        if self.has_atsas:
            calcData['DatmwBayes'] = {}
            calcData['ShapeAndSize'] = {}

        try:
            calcData['I(0)Concentration']['MW'] = self.mws['conc']['mw']
        except Exception:
            pass

        try:
            calcData['VolumeOfCorrelation']['MW'] = self.mws['vc']['mw']
            calcData['VolumeOfCorrelation']['Type'] = self.mws['vc']['type']
            calcData['VolumeOfCorrelation']['Vcor'] = self.mws['vc']['vc']
            calcData['VolumeOfCorrelation']['Cutoff'] = self.mws['vc']['cutoff']
            calcData['VolumeOfCorrelation']['Q_max'] = self.mws['vc']['q_max']
        except Exception:
            pass

        try:
            calcData['PorodVolume']['MW'] = self.mws['vp']['mw']
            calcData['PorodVolume']['VPorod'] = self.mws['vp']['pVolume']
            calcData['PorodVolume']['VPorod_Corrected'] = self.mws['vp']['pv_cor']
            calcData['PorodVolume']['Density'] = self.mws['vp']['pv_density']
            calcData['PorodVolume']['Cutoff'] = self.mws['vp']['cutoff']
            calcData['PorodVolume']['Q_max'] = self.mws['vp']['q_max']
        except Exception:
            pass

        try:
            calcData['Absolute']['MW'] = self.mws['abs']['mw']
            calcData['Absolute']['Density_dry_protein'] = self.mws['abs']['rho_Mprot']
            calcData['Absolute']['Density_buffer'] = self.mws['abs']['rho_solv']
            calcData['Absolute']['Partial_specific_volume'] = self.mws['abs']['nu_bar']
        except Exception:
            pass

        if self.has_atsas:
            try:
                calcData['DatmwBayes']['MW'] = self.mws['bayes']['mw']
                calcData['DatmwBayes']['ConfidenceIntervalLower'] = self.mws['bayes']['ci_start']
                calcData['DatmwBayes']['ConfidenceIntervalUpper'] = self.mws['bayes']['ci_end']
                calcData['DatmwBayes']['MWProbability'] = self.mws['bayes']['mw_prob']
                calcData['DatmwBayes']['ConfidenceIntervalProbability'] = self.mws['bayes']['ci_prob']
            except Exception:
                pass

            try:
                calcData['ShapeAndSize']['MW'] = self.mws['datclass']['mw']
                calcData['ShapeAndSize']['Shape'] = self.mws['datclass']['shape']
                calcData['ShapeAndSize']['Dmax'] = self.mws['datclass']['dmax']
            except Exception:
                pass

        analysis_dict = self.sasm.getParameter('analysis')
        analysis_dict['molecularWeight'] = calcData

        strconc = wx.FindWindowById(self.ids['conc']['conc'], self).GetValue()

        try:
            conc = float(strconc)
        except ValueError:
            conc = -1

        if strconc != '' and conc > 0:
            self.sasm.setParameter('Conc', conc)

        if self.manip_item is not None:
            wx.CallAfter(self.manip_item.updateInfoTip, analysis_dict, fromGuinierDialog = True)
            if self.old_analysis != calcData:
                wx.CallAfter(self.manip_item.markAsModified)

        self.OnClose()


    def calcMW(self):
        self.calc_mw_event.set()

    def _calcMWThread(self):
        while not self.calc_mw_thread_running.is_set():
            if self.calc_mw_event.is_set():
                if self.has_atsas:
                    wx.CallAfter(self.showBusy, True)

                self.calcConcMW()
                self.calcVcMW()
                self.calcVpMW()
                self.calcAbsMW()

                if self.has_atsas:
                    self.calcATSASMwFromFile()

                self.calc_mw_event.clear()

                if self.has_atsas:
                    wx.CallAfter(self.showBusy, False)
            else:
                time.sleep(0.1)

    def calcConcMW(self):
        conc_ids = self.ids['conc']
        try:
            conc = float(wx.FindWindowById(conc_ids['conc'], self).GetValue())
        except ValueError:
            conc = -1

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            i0 = float(guinier['I0'])
        else:
            i0 = 0

        try:
            ref_mw = float(wx.FindWindowById(self.ids['conc']['sup_mw'], self).GetValue())
            ref_i0 = float(wx.FindWindowById(self.ids['conc']['sup_i0'], self).GetValue())
            ref_conc = float(wx.FindWindowById(self.ids['conc']['sup_conc'], self).GetValue())
        except Exception:
            ref_mw = -1

        if ref_mw != -1:
            mw = SASCalc.calcRefMW(i0, conc, ref_i0, ref_conc, ref_mw)
        else:
            mw = -1

        if mw > 0:
            self.mws['conc']['mw'] = str(mw)

            val = round(mw,1)

            if val > 1e3 or val < 1e-2:
                mwstr = '%.2E' %(val)
            else:
                mwstr = '%.1f' %(val)

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(conc_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, mwstr)

        else:
            self.mws['conc']['mw'] = ''

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(conc_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, '')

    def calcVcMW(self):

        vc_ids = self.ids['VC']
        molecule = wx.FindWindowById(vc_ids['mol_type'], self).GetStringSelection()

        vc_cutoff = wx.FindWindowById(vc_ids['sup_cutoff'], self).GetStringSelection()

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            try:
                i0 = float(guinier['I0'])
                rg = float(guinier['Rg'])
            except Exception:
                i0 = 0
                rg = 0
        else:
            i0 = 0
            rg = 0

        q = self.sasm.getQ()

        q_max_ctrl = wx.FindWindowById(vc_ids['sup_qmax'], self)
        qmax = float(q_max_ctrl.GetValue())

        if qmax > q[-1]:
            qmax = q[-1]
        elif qmax < q[0]:
            qmax = q[0]

        if molecule == 'Protein':
            is_protein = True
        else:
            is_protein = False

        if rg > 0 and i0 > 0:
            mw, mw_error, vc, qr = SASCalc.calcVcMW(self.sasm, rg, i0, qmax,
                self.raw_settings.get('MWVcAProtein'),
                self.raw_settings.get('MWVcBProtein'),
                self.raw_settings.get('MWVcARna'),
                self.raw_settings.get('MWVcBRna'), is_protein)

            self.mws['vc']['mw'] = str(mw)
            self.mws['vc']['vc'] = str(vc)
            self.mws['vc']['qr'] = str(qr)
            self.mws['vc']['type'] = molecule
            self.mws['vc']['cutoff'] = vc_cutoff
            self.mws['vc']['q_max'] = str(float(q_max_ctrl.GetValue()))

            mw_val = round(mw,1)
            vc_val = round(vc,1)
            qr_val = round(qr,1)

            if mw_val > 1e3 or mw_val < 1e-2:
                mwstr = '%.2E' %(mw_val)
            else:
                mwstr = '%.1f' %(mw_val)

            if vc_val > 1e3 or vc_val < 1e-2:
                vcstr = '%.2E' %(vc_val)
            else:
                vcstr = '%.1f' %(vc_val)

            if qr_val > 1e3 or qr_val < 1e-2:
                qrstr = '%.2E' %(qr_val)
            else:
                qrstr = '%.1f' %(qr_val)

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(vc_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, mwstr)

                vc_win = wx.FindWindowById(vc_ids['sup_vc'], self)
                wx.CallAfter(vc_win.ChangeValue, vcstr)

                qr_win = wx.FindWindowById(vc_ids['sup_qr'], self)
                wx.CallAfter(qr_win.ChangeValue, qrstr)
        else:
            self.mws['vc']['mw'] = ''
            self.mws['vc']['vc'] = ''
            self.mws['vc']['qr'] = ''
            self.mws['vc']['type'] = molecule
            self.mws['vc']['cutoff'] = vc_cutoff
            self.mws['vc']['q_max'] = str(float(q_max_ctrl.GetValue()))

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(vc_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, '')

                vc_win = wx.FindWindowById(vc_ids['sup_vc'], self)
                wx.CallAfter(vc_win.ChangeValue, '')

                qr_win = wx.FindWindowById(vc_ids['sup_qr'], self)
                wx.CallAfter(qr_win.ChangeValue, '')

    def calcVpMW(self):
        #This is calculated using the method in Fischer et al. J. App. Crys. 2009

        vp_ids = self.ids['VP']
        vp_cutoff = wx.FindWindowById(vp_ids['sup_cutoff'], self).GetStringSelection()

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            try:
                i0 = float(guinier['I0'])
                rg = float(guinier['Rg'])
            except Exception:
                i0 = 0
                rg = 0
        else:
            i0 = 0
            rg = 0

        q = self.sasm.getQ()
        i = self.sasm.getI()
        err = self.sasm.getErr()

        density = float(wx.FindWindowById(vp_ids['sup_density'], self).GetValue())

        q_max_ctrl = wx.FindWindowById(vp_ids['sup_qmax'], self)
        qmax = float(q_max_ctrl.GetValue())

        if qmax > q[-1]:
            qmax = q[-1]
        elif qmax < q[0]:
            qmax = q[0]


        if qmax<=0.5 and qmax>=0.1:
            wx.CallAfter(self._showVpMWWarning, False)
        else:
            wx.CallAfter(self._showVpMWWarning, True)

        if i0 > 0:
            analysis = self.sasm.getParameter('analysis')
            guinier_analysis = analysis['guinier']
            qmin = float(guinier_analysis['qStart'])

            mw, pVolume, pv_cor = SASCalc.calcVpMW(q, i, err, rg, i0, qmin,
                density, qmax)

            self.mws['vp']['mw'] = str(mw)
            self.mws['vp']['pVolume'] = str(pVolume)
            self.mws['vp']['pv_cor'] = str(pv_cor)
            self.mws['vp']['pv_density'] = str(density)
            self.mws['vp']['cutoff'] = vp_cutoff
            self.mws['vp']['q_max'] = str(float(q_max_ctrl.GetValue()))

            mw_val = round(mw,1)
            pv_val = round(pVolume,1)
            pvc_val = round(pv_cor,1)

            if mw_val > 1e3 or mw_val < 1e-2:
                mwstr = '%.2E' %(mw_val)
            else:
                mwstr = '%.1f' %(mw_val)

            if pv_val > 1e3 or pv_val < 1e-2:
                pvstr = '%.2E' %(pv_val)
            else:
                pvstr = '%.1f' %(pv_val)

            if pvc_val > 1e3 or pvc_val < 1e-2:
                pvcstr = '%.2E' %(pvc_val)
            else:
                pvcstr = '%.1f' %(pvc_val)

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(vp_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, mwstr)

                vpCtrl = wx.FindWindowById(vp_ids['sup_vp'], self)
                wx.CallAfter(vpCtrl.ChangeValue, pvstr)

                pvcCtrl = wx.FindWindowById(vp_ids['sup_vpc'], self)
                wx.CallAfter(pvcCtrl.ChangeValue, pvcstr)

        else:
            self.mws['vp']['mw'] = ''
            self.mws['vp']['pVolume'] = ''
            self.mws['vp']['pv_cor'] = ''
            self.mws['vp']['pv_density'] = str(density)
            self.mws['vp']['cutoff'] = vp_cutoff
            self.mws['vp']['q_max'] = str(float(q_max_ctrl.GetValue()))

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(vp_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, '')

                vpCtrl = wx.FindWindowById(vp_ids['sup_vp'], self)
                wx.CallAfter(vpCtrl.ChangeValue, '')

                pvcCtrl = wx.FindWindowById(vp_ids['sup_vpc'], self)
                wx.CallAfter(pvcCtrl.ChangeValue, '')

    def calcAbsMW(self):
        abs_ids = self.ids['abs']

        try:
            conc = float(wx.FindWindowById(abs_ids['conc'], self).GetValue())
        except ValueError:
            conc = -1

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            i0 = float(guinier['I0'])
        else:
            i0 = 0

        rho_Mprot = float(wx.FindWindowById(self.ids['abs']['sup_pm'], self).GetValue()) #e-/g, # electrons per dry mass of protein
        rho_solv = float(wx.FindWindowById(self.ids['abs']['sup_ps'], self).GetValue()) #e-/cm^-3, # electrons per volume of aqueous solvent
        nu_bar = float(wx.FindWindowById(self.ids['abs']['sup_pv'], self).GetValue()) #cm^3/g, # partial specific volume of the protein
        r0 = self.raw_settings.get('MWAbsR0') #cm, scattering lenght of an electron

        if conc > 0 and i0 > 0 and wx.FindWindowById(abs_ids['calib'], self).GetValue():
            mw = SASCalc.calcAbsMW(i0, conc, rho_Mprot, rho_solv, nu_bar, r0)

            self.mws['abs']['mw'] = str(mw)
            self.mws['abs']['rho_Mprot'] = str(rho_Mprot)
            self.mws['abs']['rho_solv'] = str(rho_solv)
            self.mws['abs']['nu_bar'] = str(nu_bar)

            val = round(mw,1)

            if val > 1e3 or val < 1e-2:
                mwstr = '%.2E' %(val)
            else:
                mwstr = '%.1f' %(val)

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(abs_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, mwstr)

                d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
                sc_win = wx.FindWindowById(self.ids['abs']['sup_sc'], self)
                wx.CallAfter(sc_win.ChangeValue, '%.2E' %(d_rho))

        else:
            self.mws['abs']['mw'] = ''
            self.mws['abs']['rho_Mprot'] = str(rho_Mprot)
            self.mws['abs']['rho_solv'] = str(rho_solv)
            self.mws['abs']['nu_bar'] = str(nu_bar)

            if not self.calc_mw_thread_running.is_set():
                mwCtrl = wx.FindWindowById(abs_ids['calc_mw'], self)
                wx.CallAfter(mwCtrl.ChangeValue, '')

                d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
                sc_win = wx.FindWindowById(self.ids['abs']['sup_sc'], self)
                wx.CallAfter(sc_win.ChangeValue, '')

    def calcBayesMW(self, path, datname):
        # This calculates the Bayesian estimated MW using datmw from ATSAS

        try:
            rg = -1
            i0 = -1
            first = -1

            analysis = self.sasm.getParameter('analysis')
            if 'guinier' in analysis:
                try:
                    rg = float(analysis['guinier']['Rg'])
                except Exception:
                    pass

                try:
                    i0 = float(analysis['guinier']['I0'])
                except Exception:
                    pass

                try:
                    #Plus one offset is because datmw has 1 as first point, not 0
                    first = max(0, int(analysis['guinier']['nStart']) - profile.getQrange()[0])

                except Exception:
                    first = self.sasm.getQrange()[0]

            if i0 == -1 or rg == -1 or first == -1:
                raise SASExceptions.NoATSASError('Datmw requires rg and i0.')

            res = SASCalc.runDatmw(rg, i0, first, 'bayes',
                self.raw_settings.get('ATSASDir'), path, datname)
        except Exception:
            res = ()

        if len(res) > 0:
            mw, mw_score, ci_lower, ci_upper, ci_score = res

            mw_score = mw_score*100
            ci_score = ci_score*100

            self.mws['bayes']['mw'] = str(mw)
            self.mws['bayes']['ci_start'] = str(ci_lower)
            self.mws['bayes']['ci_end'] = str(ci_upper)
            self.mws['bayes']['mw_prob'] = str(mw_score)
            self.mws['bayes']['ci_prob'] = str(ci_score)

            mw = round(mw, 1)
            ci_lower = round(ci_lower, 1)
            ci_upper = round(ci_upper, 1)

            if not self.calc_mw_thread_running.is_set():
                mw_window = wx.FindWindowById(self.ids['bayes']['calc_mw'], self)
                wx.CallAfter(mw_window.ChangeValue, self.format_float(mw))

                ci_l_win = wx.FindWindowById(self.ids['bayes']['ci_start'], self)
                wx.CallAfter(ci_l_win.ChangeValue, self.format_float(ci_lower))

                ci_u_win = wx.FindWindowById(self.ids['bayes']['ci_end'], self)
                wx.CallAfter(ci_u_win.ChangeValue, self.format_float(ci_upper))

                mw_prob_win = wx.FindWindowById(self.ids['bayes']['mw_prob'], self)
                wx.CallAfter(mw_prob_win.ChangeValue, self.format_float(mw_score))

                ci_prob_win = wx.FindWindowById(self.ids['bayes']['ci_prob'], self)
                wx.CallAfter(ci_prob_win.ChangeValue, self.format_float(ci_score))

        else:
            self.mws['bayes']['mw'] = ''
            self.mws['bayes']['ci_start'] = ''
            self.mws['bayes']['ci_end'] = ''
            self.mws['bayes']['mw_prob'] = ''
            self.mws['bayes']['ci_prob'] = ''

            if not self.calc_mw_thread_running.is_set():
                mw_window = wx.FindWindowById(self.ids['bayes']['calc_mw'], self)
                wx.CallAfter(mw_window.ChangeValue, '')

                ci_l_win = wx.FindWindowById(self.ids['bayes']['ci_start'], self)
                wx.CallAfter(ci_l_win.ChangeValue, '')

                ci_u_win = wx.FindWindowById(self.ids['bayes']['ci_end'], self)
                wx.CallAfter(ci_u_win.ChangeValue, '')

                mw_prob_win = wx.FindWindowById(self.ids['bayes']['mw_prob'], self)
                wx.CallAfter(mw_prob_win.ChangeValue, '')

                ci_prob_win = wx.FindWindowById(self.ids['bayes']['ci_prob'], self)
                wx.CallAfter(ci_prob_win.ChangeValue, '')

    def calcDatclassMW(self, path, datname):
        # This calculates the Bayesian estimated MW using datmw from ATSAS

        try:
            analysis = self.sasm.getParameter('analysis')
            if 'guinier' in analysis:
                try:
                    rg = float(analysis['guinier']['Rg'])
                except Exception:
                    rg = -1
            else:
                rg = -1

            if 'guinier' in analysis:
                try:
                    i0 = float(analysis['guinier']['I0'])
                except Exception:
                    i0 = -1
            else:
                i0 = -1

            if i0 == -1 or rg == -1:
                raise SASExceptions.NoATSASError('Datclass requires rg and i0.')

            first = max(0, int(analysis['guinier']['nStart']) - self.sasm.getQrange()[0])

            res = SASCalc.runDatclass(rg, i0, first, self.raw_settings.get('ATSASDir'),
                path, datname)

        except Exception:
            res = ()

        if len(res) > 0:
            shape, mw, dmax = res

            self.mws['datclass']['mw'] = str(mw)
            self.mws['datclass']['shape'] = shape
            self.mws['datclass']['dmax'] = str(dmax)

            mw = round(mw, 1)
            dmax = round(dmax, 0)

            if not self.calc_mw_thread_running.is_set():
                mw_window = wx.FindWindowById(self.ids['datclass']['calc_mw'], self)
                wx.CallAfter(mw_window.ChangeValue, self.format_float(mw))

                shape_win = wx.FindWindowById(self.ids['datclass']['shape'], self)
                wx.CallAfter(shape_win.ChangeValue, shape)

                dmax_win = wx.FindWindowById(self.ids['datclass']['dmax'], self)
                wx.CallAfter(dmax_win.ChangeValue, str(dmax))

        else:
            self.mws['datclass']['mw'] = ''
            self.mws['datclass']['shape'] = ''
            self.mws['datclass']['dmax'] = ''

            if not self.calc_mw_thread_running.is_set():
                mw_window = wx.FindWindowById(self.ids['datclass']['calc_mw'], self)
                wx.CallAfter(mw_window.ChangeValue, '')

                shape_win = wx.FindWindowById(self.ids['datclass']['shape'], self)
                wx.CallAfter(shape_win.ChangeValue, '')

                dmax_win = wx.FindWindowById(self.ids['datclass']['dmax'], self)
                wx.CallAfter(dmax_win.ChangeValue, '')

    def calcATSASMwFromFile(self):
        """
        Calculates MW using methods that require a file written to disk,
        so that file writting is done only once.
        """
        tempdir = self.standard_paths.GetTempDir()

        datname = tempfile.NamedTemporaryFile(dir=os.path.abspath(tempdir)).name

        while os.path.isfile(datname):
            datname = tempfile.NamedTemporaryFile(dir=os.path.abspath(tempdir)).name

        datname = os.path.split(datname)[-1] + '.dat'

        SASFileIO.writeRadFile(self.sasm, os.path.abspath(os.path.join(tempdir, datname)),
            False)


        self.calcBayesMW(tempdir, datname)
        self.calcDatclassMW(tempdir, datname)

    def format_float(self, val):
        if val > 1e3 or val < 1e-2:
            ret = '%.2E' %(val)
        else:
            ret = '%.1f' %(val)

        return ret

    def OnClose(self):
        self.calc_mw_thread_running.set()
        self.calc_mw_thread.join()
        self.Destroy()


class MWPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name):

        wx.Panel.__init__(self, parent, panel_id, name = name,
            style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        SASUtils.update_mpl_style()

        # self.fig = Figure((5,4), 75)
        self.fig = Figure((3.25,2.5))
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)

        self.data_line = None

        subplotLabels = [('Integrated Area of q*I(q)', 'q [1/A]', '$\int q \cdot I(q) dq$', 'VC')]

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][3]] = subplot

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)

        self.SetSizer(sizer)
        # self.canvas.SetBackgroundColour('white')
        # self.fig.set_facecolor('white')
        self.fig.tight_layout()

        font_size = 10
        a = self.subplots['VC']

        a.locator_params(tight = True)
        a.locator_params(axis='x', nbins = 6)

        a.title.set_size(font_size)
        a.yaxis.get_label().set_size(font_size)
        a.xaxis.get_label().set_size(font_size)

        for tick in a.xaxis.get_major_ticks():
            tick.label.set_fontsize(font_size)

        for tick in a.yaxis.get_major_ticks():
            tick.label.set_fontsize(font_size)

        self.canvas.draw()

    def updateColors(self):
        color = SASUtils.update_mpl_style()

        self.canvas.draw()

    def _calcInt(self, sasm, qmax, interp=True):
        ''' calculate pointwise integral '''

        q = sasm.getQ()
        i = sasm.getI()
        err = sasm.getErr()

        qmax = float(qmax)

        if qmax not in q:
            idx = np.argmin(np.abs(q-qmax))
            qmax = q[idx]
        else:
            idx = np.argwhere(q == qmax)[0][0]

        q = q[:idx+1]
        i = i[:idx+1]
        err = err[:idx+1]

        analysis = sasm.getParameter('analysis')

        if interp and q[0] != 0 and 'guinier' in analysis:
            guinier_analysis = analysis['guinier']
            guinier_qmin = float(guinier_analysis['qStart'])
            i0 = float(guinier_analysis['I0'])
            rg = float(guinier_analysis['Rg'])

            findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
            closest_qmin = findClosest(guinier_qmin, q)

            idx_min = np.where(q == closest_qmin)[0][0]

            q = q[idx_min:]
            i = i[idx_min:]

            def guinier_interp(x):
                return i0*np.exp((-1./3.)*np.square(rg)*np.square(x))

            q_interp = np.arange(0,q[0],q[1]-q[0])
            i_interp = guinier_interp(q_interp)

            q = np.concatenate((q_interp, q))
            i = np.concatenate((i_interp, i))

        y = np.zeros_like(q, dtype = float)
        qi = q*i

        for a in range(2,len(q)+1):
            y[a-1] = integrate.trapz(qi[:a],q[:a])

        return q, y

    def plotSASM(self, sasm, qmax):
        try:
            q, intI = self._calcInt(sasm, qmax)
        except TypeError:
            return

        self.updateDataPlot(q, intI)


    def updateDataPlot(self, q, intI):
        a = self.subplots['VC']

        if self.data_line is None:
            self.data_line, = a.plot(q, intI, 'r.')
        else:
            self.data_line.set_xdata(q)
            self.data_line.set_ydata(intI)

        a.relim()
        a.autoscale_view()

        self.canvas.draw()


class GNOMFrame(wx.Frame):

    def __init__(self, parent, title, sasm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = (min(825, client_display.Width), min(700, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.main_frame = parent
        self.sasm = sasm

        panel = wx.Panel(self)

        splitter1 = wx.SplitterWindow(panel, wx.ID_ANY)

        sizer = wx.BoxSizer()
        sizer.Add(splitter1, 1, flag=wx.EXPAND)

        panel.SetSizer(sizer)

        self.plotPanel = IFTPlotPanel(splitter1, wx.ID_ANY)
        self.controlPanel = GNOMControlPanel(splitter1, wx.ID_ANY, sasm, manip_item)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(315))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(self._FromDIP(315))   #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(self._FromDIP(50))


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)

        self.SendSizeEvent()

        self.CenterOnParent()
        self.Raise()

        self.getGnomVersion()

        self.standard_paths = wx.StandardPaths.Get()

        self.showBusy()
        t = threading.Thread(target=self.initGNOM, args=(sasm,))
        t.daemon=True
        t.start()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()

    def initGNOM(self, sasm):

        self.saveGNOMProfile()

        analysis_dict = sasm.getParameter('analysis')
        if 'GNOM' in analysis_dict:
            wx.CallAfter(self.controlPanel.initGnomValues, sasm)
        else:
            wx.CallAfter(self.controlPanel.initAutoValues, sasm)

    def getGnomVersion(self):
        #Checks if we have gnom4 or gnom5
        version = SASCalc.getATSASVersion(self._raw_settings.get('ATSASDir'))

        if (int(version.split('.')[0]) > 2 or
            (int(version.split('.')[0]) == 2 and int(version.split('.')[1]) >=8)):
            self.new_gnom = True
        else:
            self.new_gnom = False

    def showBusy(self, show=True, msg=''):
        if show:
            if msg == '':
                msg = 'Initializing GNOM, please wait.'

            self.bi = wx.BusyInfo(msg, self)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass

    def updateGNOMSettings(self):
        self.controlPanel.updateGNOMSettings()

    def saveGNOMProfile(self):
        tempdir = self.standard_paths.GetTempDir()

        save_sasm = copy.deepcopy(self.sasm)

        savename = os.path.splitext(save_sasm.getParameter('filename'))[0] + '.dat'

        outname = tempfile.NamedTemporaryFile(dir=os.path.abspath(tempdir)).name
        while os.path.isfile(outname):
            outname = tempfile.NamedTemporaryFile(dir=os.path.abspath(tempdir)).name

        outname = os.path.split(outname)[1]
        outname = outname+'.out'

        if (self.main_frame.OnlineControl.isRunning()
            and tempdir == self.main_frame.OnlineControl.getTargetDir()):
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        try:
            SASFileIO.saveMeasurement(save_sasm, tempdir, self._raw_settings, filetype = '.dat')
        except SASExceptions.HeaderSaveError as e:
            self._showSaveError('header')

        self.tempdir = tempdir
        self.savename = savename
        self.outname = outname

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

    def cleanupGNOM(self):
        savefile = os.path.join(self.tempdir, self.savename)
        outfile = os.path.join(self.tempdir, self.outname)

        if self.savename != '':
            if os.path.isfile(savefile):
                try:
                    os.remove(savefile)
                except Exception as e:
                    print(e)
                    print('GNOM cleanup failed to remove the .dat file!')

        if self.outname != '':
            if os.path.isfile(outfile):
                try:
                    os.remove(outfile)
                except Exception as e:
                    print(e)
                    print('GNOM cleanup failed to remove the .out file!')

    def OnClose(self):
        self.cleanupGNOM()

        self.Destroy()



class IFTPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = main_frame.raw_settings

        SASUtils.update_mpl_style()

        self.fig = Figure((5,4), 75)

        self.ift = None

        self.norm_residuals = self.raw_settings.get('normalizedResiduals')

        subplotLabels = [('P(r)', 'r', 'P(r)', .1),
            ('Data/Fit', 'q', 'I(q)', 0.1)]

        if self.norm_residuals:
            subplotLabels.append(('Normalized Residual', '$q$',
                '$\Delta I(q)/\sigma (q)$', 0.1))
        else:
            subplotLabels.append(('Residual', '$q$', '$\Delta I(q)$', 0.1))

        gridspec = matplotlib.gridspec.GridSpec(3, 1, height_ratios=[1, 1, 0.3])
        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(gridspec[i],
                title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])

            if subplotLabels[i][0] == 'Normalized Residual':
                label = 'Residual'
            else:
                label = subplotLabels[i][0]

            self.subplots[label] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93,
            top = 0.93, hspace = 0.4)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        system_settings = wx.SystemSettings()

        try:
            system_appearance = system_settings.GetAppearance()
            is_dark = system_appearance.IsDark()
        except Exception:
            is_dark = False

        if is_dark:
            color = 'white'
        else:
            color = 'black'

        self.pr_hline = self.subplots['P(r)'].axhline(color = color, linewidth=1.0)
        self.res_hline = self.subplots['Residual'].axhline(color = color, linewidth=1.0)

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateColors(self):
        color = SASUtils.update_mpl_style()

        # self.pr_hline.set_color(color)
        # self.res_hline.set_color(color)

        self.canvas.draw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']
        c = self.subplots['Residual']

        self.canvas.mpl_disconnect(self.cid) #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)
        self.residual_background = self.canvas.copy_from_bbox(c.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw) #Reconnect draw_event

    def plotPr(self, iftm):
        r = iftm.r
        p = iftm.p
        perr = iftm.err

        i = iftm.i_orig
        q = iftm.q_orig
        err = iftm.err_orig

        qfit = q
        fit = iftm.i_fit #GNOM jreg

        self.updateDataPlot(q, i, err, r, p, perr, qfit, fit)

    def updateDataPlot(self, q, i, err, r, p, perr, qfit, fit):

        #Save for resizing:
        self.orig_q = q
        self.orig_i = i
        self.orig_err = err
        self.orig_r = r
        self.orig_p = p
        self.orig_perr = perr
        self.orig_qfit = qfit
        self.orig_fit = fit

        residual = i - fit
        if self.norm_residuals:
            residual = residual/err

        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']
        c = self.subplots['Residual']

        if self.ift is None:
            self.ift, = a.plot(r, p, 'r.-', animated = True)

            self.data_line, = b.semilogy(q, i, 'b.', animated = True)
            self.fit_line, = b.semilogy(qfit, fit, 'r', animated = True)

            self.residual_line, = c.plot(q, residual, 'b.', animated=True)

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)
            self.residual_background = self.canvas.copy_from_bbox(c.bbox)

        else:
            self.ift.set_ydata(p)
            self.ift.set_xdata(r)

            #Error lines:
            self.data_line.set_xdata(q)
            self.data_line.set_ydata(i)
            self.fit_line.set_xdata(qfit)
            self.fit_line.set_ydata(fit)

            self.residual_line.set_xdata(q)
            self.residual_line.set_ydata(residual)

            if not self.ift.get_visible():
                self.ift.set_visible(True)
                self.data_line.set_visible(True)
                self.fit_line.set_visible(True)
                self.residual_line.set_visible(True)

        self.autoscale_plot()

    def redrawLines(self):
        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']
        c = self.subplots['Residual']

        if self.ift is not None:
            self.canvas.restore_region(self.background)
            a.draw_artist(self.ift)

            self.canvas.restore_region(self.err_background)
            b.draw_artist(self.data_line)
            b.draw_artist(self.fit_line)

            self.canvas.restore_region(self.residual_background)
            c.draw_artist(self.residual_line)

            self.canvas.blit(a.bbox)
            self.canvas.blit(b.bbox)
            self.canvas.blit(c.bbox)

    def autoscale_plot(self):

        redraw = False

        plot_list = [self.subplots['P(r)'], self.subplots['Data/Fit'],
            self.subplots['Residual']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()

    def clearDataPlot(self):
        if self.ift is not None:
            self.ift.set_visible(False)
            self.data_line.set_visible(False)
            self.fit_line.set_visible(False)
            self.residual_line.set_visible(False)

            self.redrawLines()


class GNOMControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, sasm, manip_item):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.sasm = sasm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.gnom_frame = parent.GetParent().GetParent()

        self.raw_settings = self.main_frame.raw_settings

        self.old_analysis = {}
        self.old_dmax = -1

        if 'GNOM' in self.sasm.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.sasm.getParameter('analysis')['GNOM'])

        self.gnom_settings = {
            'rmin_zero'     : self.raw_settings.get('gnomForceRminZero'),
            'rmax_zero'     : self.raw_settings.get('gnomForceRmaxZero'),
            'npts'          : self.raw_settings.get('gnomNPoints'),
            'alpha'         : self.raw_settings.get('gnomInitialAlpha'),
            'first'         : 0,
            'last'          : len(self.sasm.q),
            'system'        : self.raw_settings.get('gnomSystem'),
            'radius56'      : self.raw_settings.get('gnomRadius56'),
            'rmin'          : self.raw_settings.get('gnomRmin'),
            }

        self.out_list = {}


        self.spinctrlIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId(),
                            'dmax'   : self.NewControlId(),
                            }

        self.staticTxtIDs = {'qstart'   : self.NewControlId(),
                            'qend'      : self.NewControlId(),
                            'alpha'     : self.NewControlId(),
                            }

        self.otherctrlIDs = {'force_dmax'   : self.NewControlId(),
                            }


        self.infodata = {'guinierI0' : ('I0 :', self.NewControlId()),
                         'guinierRg' : ('Rg :', self.NewControlId()),
                         'guinierRg_err'    :('Rg Err. :', self.NewControlId()),
                         'guinierI0_err'    :('I0 Err. :', self.NewControlId()),
                         'gnomRg_err'    :('Rg Err. :', self.NewControlId()),
                         'gnomI0_err'    :('I0 Err. :', self.NewControlId()),
                         'gnomI0'    : ('I0 :', self.NewControlId()),
                         'gnomRg'    : ('Rg :', self.NewControlId()),
                         'TE': ('Total Estimate :', self.NewControlId()),
                         'gnomQuality': ('GNOM says :', self.NewControlId()),
                         'chisq': ('Chi^2 (fit) :', self.NewControlId()),
                         'alpha':   ('Alpha :', self.NewControlId()),
                         }

        self.plotted_iftm = None

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):
        info_button = wx.Button(self, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)


        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,0, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(savebutton, 0, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(button)


        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self._createControls(box2)
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))


        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self._createInfoBox(box)
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND)


        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT
            | wx.TOP, self._FromDIP(5))
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            self._FromDIP(5))
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            self._FromDIP(5))
        bsizer.AddStretchSpacer(1)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, border=self._FromDIP(5))

        self.SetSizer(bsizer)

    def _createInfoBox(self, parent):

        sizer = wx.FlexGridSizer(5, 3, self._FromDIP(5), self._FromDIP(5))

        sizer.Add((0,0))

        rglabel = wx.StaticText(parent, -1, 'Rg (A)')
        i0label = wx.StaticText(parent, -1, 'I(0)')

        sizer.Add(rglabel, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer.Add(i0label, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)

        guinierlabel = wx.StaticText(parent, -1, 'Guinier:')
        self.guinierRg = wx.TextCtrl(parent, self.infodata['guinierRg'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)
        self.guinierI0 = wx.TextCtrl(parent, self.infodata['guinierI0'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)

        sizer.Add(guinierlabel, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierRg, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierI0, 0, wx.ALIGN_CENTER_VERTICAL)

        guinierlabel = wx.StaticText(parent, -1, 'Guinier Err.:')
        self.guinierRg = wx.TextCtrl(parent, self.infodata['guinierRg_err'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)
        self.guinierI0 = wx.TextCtrl(parent, self.infodata['guinierI0_err'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)

        sizer.Add(guinierlabel, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierRg, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierI0, 0, wx.ALIGN_CENTER_VERTICAL)

        gnomlabel = wx.StaticText(parent, -1, 'P(r):')
        self.gnomRg = wx.TextCtrl(parent, self.infodata['gnomRg'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)
        self.gnomI0 = wx.TextCtrl(parent, self.infodata['gnomI0'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)

        sizer.Add(gnomlabel, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.gnomRg, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.gnomI0, 0, wx.ALIGN_CENTER_VERTICAL)

        gnomlabel = wx.StaticText(parent, -1, 'P(r) Err.:')
        self.gnomRg = wx.TextCtrl(parent, self.infodata['gnomRg_err'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)
        self.gnomI0 = wx.TextCtrl(parent, self.infodata['gnomI0_err'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)

        sizer.Add(gnomlabel, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.gnomRg, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.gnomI0, 0, wx.ALIGN_CENTER_VERTICAL)

        self.alpha = wx.TextCtrl(parent, self.infodata['alpha'][1], ''
            , size=self._FromDIP((80,-1)), style=wx.TE_READONLY)

        teLabel = wx.StaticText(parent, -1, self.infodata['TE'][0])
        self.totalEstimate = wx.TextCtrl(parent, self.infodata['TE'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)

        chisqLabel = wx.StaticText(parent, -1, self.infodata['chisq'][0])
        self.chisq = wx.TextCtrl(parent, self.infodata['chisq'][1], '0',
            size = self._FromDIP((80,-1)), style = wx.TE_READONLY)

        qualityLabel = wx.StaticText(parent, -1, self.infodata['gnomQuality'][0])
        self.quality = wx.TextCtrl(parent, self.infodata['gnomQuality'][1], '', style = wx.TE_READONLY)

        res_sizer2 = wx.FlexGridSizer(rows=4, cols=2, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        res_sizer2.Add(teLabel)
        res_sizer2.Add(self.totalEstimate)
        res_sizer2.Add(chisqLabel)
        res_sizer2.Add(self.chisq)
        res_sizer2.Add(qualityLabel)
        res_sizer2.Add(self.quality, flag=wx.EXPAND)
        res_sizer2.Add(wx.StaticText(parent, label=self.infodata['alpha'][0]))
        res_sizer2.Add(self.alpha)
        res_sizer2.AddGrowableCol(1)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer, 0, wx.TOP|wx.LEFT|wx.RIGHT, self._FromDIP(5))
        top_sizer.Add(res_sizer2, flag=wx.ALL|wx.EXPAND, border=self._FromDIP(5))

        return top_sizer

    def _createControls(self, parent):

        sizer = wx.FlexGridSizer(rows=2, cols=4, hgap=self._FromDIP(5),
            vgap=self._FromDIP(2))
        sizer.AddGrowableCol(0)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableCol(2)
        sizer.AddGrowableCol(3)

        sizer.Add(wx.StaticText(parent, -1,'q_min'),1)
        sizer.Add(wx.StaticText(parent, -1,'n_min'),1)
        sizer.Add(wx.StaticText(parent, -1,'q_max'),1)
        sizer.Add(wx.StaticText(parent, -1,'n_max'),1)

        self.startSpin = RAWCustomCtrl.IntSpinCtrl(parent, self.spinctrlIDs['qstart'],
            size = self._FromDIP((60,-1)), min_val=0)
        self.endSpin = RAWCustomCtrl.IntSpinCtrl(parent, self.spinctrlIDs['qend'],
            size = self._FromDIP((60,-1)), min_val=0)

        self.startSpin.SetValue(0)
        self.endSpin.SetValue(0)

        self.startSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.endSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)

        self.qstartTxt = wx.TextCtrl(parent, self.staticTxtIDs['qstart'], 'q: ',
            size = self._FromDIP((55, 22)), style = wx.TE_PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(parent, self.staticTxtIDs['qend'], 'q: ',
            size = self._FromDIP((55, 22)), style = wx.TE_PROCESS_ENTER)

        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)

        sizer.Add(self.qstartTxt, 0, wx.EXPAND)
        sizer.Add(self.startSpin, 0, wx.EXPAND)
        sizer.Add(self.qendTxt, 0, wx.EXPAND)
        sizer.Add(self.endSpin, 0, wx.EXPAND)


        ctrl2_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.dmaxSpin = RAWCustomCtrl.IntSpinCtrl(parent, self.spinctrlIDs['dmax'],
            size = self._FromDIP((60,-1)), min_val = 1)
        self.dmaxSpin.SetValue(0)
        self.dmaxSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.dmaxSpin.Bind(wx.EVT_TEXT, self.onDmaxText)

        self.alpha_ctrl = wx.TextCtrl(parent, self.staticTxtIDs['alpha'],
            size=self._FromDIP((40,-1)), style=wx.TE_PROCESS_ENTER)
        self.alpha_ctrl.Bind(wx.EVT_TEXT_ENTER, self.onAlpha)

        self.cut_qrg = wx.CheckBox(parent, label='Truncate for DAMMIF/N')
        self.cut_qrg.SetValue(self.raw_settings.get('gnomCut8Rg'))
        self.cut_qrg.Bind(wx.EVT_CHECKBOX, self.onCutQRg)

        ctrl2_sizer.Add(wx.StaticText(parent, -1, 'Dmax: '), 0, wx.RIGHT
            |wx.ALIGN_CENTER_VERTICAL, self._FromDIP(2))
        ctrl2_sizer.Add(self.dmaxSpin, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            self._FromDIP(5))
        ctrl2_sizer.Add(wx.StaticText(parent, label='Alpha (0=auto):'),
            border=self._FromDIP(2), flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        ctrl2_sizer.Add(self.alpha_ctrl, border=self._FromDIP(5), proportion=1,
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)

        rmax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rmax_text = wx.StaticText(parent, -1, 'Force to 0 at Dmax: ')
        rmax_choice = wx.Choice(parent, self.otherctrlIDs['force_dmax'], choices = ['Y', 'N'])
        rmax_choice.SetStringSelection(self.gnom_settings['rmax_zero'])
        rmax_choice.Bind(wx.EVT_CHOICE, self.onSettingsChange)
        rmax_sizer.Add(rmax_text, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            self._FromDIP(3))
        rmax_sizer.Add(rmax_choice, 0, wx.ALIGN_CENTER_VERTICAL)


        advancedParams = wx.Button(parent, -1, 'Change Advanced Parameters')
        advancedParams.Bind(wx.EVT_BUTTON, self.onChangeParams)

        find_dmax = wx.Button(parent, -1, 'Auto Dmax')
        find_dmax.Bind(wx.EVT_BUTTON, self.onFindDmaxButton)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer, 0, wx.EXPAND|wx.BOTTOM, self._FromDIP(5))
        top_sizer.Add(ctrl2_sizer, 0, wx.EXPAND | wx.BOTTOM,
            self._FromDIP(5))
        top_sizer.Add(rmax_sizer, 0, wx.EXPAND | wx.BOTTOM, self._FromDIP(5))
        top_sizer.Add(self.cut_qrg, 0, wx.EXPAND | wx.BOTTOM, self._FromDIP(5))
        top_sizer.Add(advancedParams, 0, wx.CENTER | wx.BOTTOM, self._FromDIP(5))
        top_sizer.Add(find_dmax, 0, wx.CENTER)

        return top_sizer


    def initAutoValues(self, sasm):
        self.setGuinierInfo(sasm)

        if 'guinier' in sasm.getParameter('analysis'):
            guinier = sasm.getParameter('analysis')['guinier']

            try:
                nmin = guinier['nStart']
                nmax = sasm.getQrange()[1]
            except Exception:
                nmin, nmax = sasm.getQrange()
        else:
            nmin, nmax = sasm.getQrange()

        self.startSpin.SetRange((0, len(sasm.q)-1))
        self.endSpin.SetRange((0, len(sasm.q)-1))

        self.endSpin.SetValue(nmax-1)
        self.startSpin.SetValue(nmin)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
        txt.SetValue(str(round(sasm.q[nmax-1],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
        txt.SetValue(str(round(sasm.q[nmin],4)))

        self.old_nstart = nmin
        self.old_nend = nmax-1
        self.previous_qmax = sasm.q[nmax-1]

        self.cutQrg()

        self.setFilename(os.path.basename(sasm.getParameter('filename')))
        self.alpha_ctrl.SetValue(str(self.gnom_settings['alpha']))

        self._runFindDmax()

        # wx.CallAfter(self.gnom_frame.showBusy, False)

    def initGnomValues(self, sasm):
        self.setGuinierInfo(sasm)

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)

        gnom_analysis = sasm.getParameter('analysis')['GNOM']

        try:
            dmax = int(round(float(gnom_analysis['Dmax'])))
        except Exception:
            dmax = -1

        try:
            qmin = gnom_analysis['qStart']
            qmax = gnom_analysis['qEnd']

            findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
            closest_qmin = findClosest(qmin, sasm.q)
            closest_qmax = findClosest(qmax, sasm.q)

            new_nmin = np.where(sasm.q == closest_qmin)[0][0]
            new_nmax = np.where(sasm.q == closest_qmax)[0][0]

        except Exception:
            new_nmin, new_nmax = sasm.getQrange()

        self.startSpin.SetRange((0, len(sasm.q)-1))
        self.endSpin.SetRange((0, len(sasm.q)-1))

        self.endSpin.SetValue(new_nmax)
        self.startSpin.SetValue(new_nmin)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
        txt.SetValue(str(round(sasm.q[new_nmax],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
        txt.SetValue(str(round(sasm.q[new_nmin],4)))

        self.old_nstart = new_nmin
        self.old_nend = new_nmax
        self.previous_qmax = sasm.q[new_nmax]

        self.cutQrg()

        self.setFilename(os.path.basename(sasm.getParameter('filename')))

        try:
            alpha = gnom_analysis['Alpha']
        except Exception:
            alpha = self.gnom_settings['alpha']

        if alpha == self.gnom_settings['alpha']:
            self.alpha_ctrl.SetValue(str(self.gnom_settings['alpha']))
        else:
            self.alpha_ctrl.SetValue('0')

        self.updateGNOMSettings(update_plot=False)

        if dmax != -1:
            self.old_dmax = dmax

            self.calcGNOM(dmax)

            dmaxWindow.SetValue(dmax)

            if alpha != 0 and alpha != self.gnom_settings['alpha']:

                ift = self.out_list[str(dmax)]

                if float(ift.getParameter('alpha')) == float(alpha):
                    self.alpha_ctrl.SetValue('0')
                else:
                    self.alpha_ctrl.SetValue(str(alpha))
                    self.updateGNOMSettings(update_plot=False)
                    self.calcGNOM(dmax)

            self.updateGNOMInfo(self.out_list[str(dmax)])

            self.updatePlot()

            wx.CallAfter(self.gnom_frame.showBusy, False)

        else:
            self._runFindDmax()


    def setGuinierInfo(self, sasm):
        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1], self)
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1], self)
        guinierRgerrWindow = wx.FindWindowById(self.infodata['guinierRg_err'][1], self)
        guinierI0errWindow = wx.FindWindowById(self.infodata['guinierI0_err'][1], self)

        if 'guinier' in sasm.getParameter('analysis'):

            guinier = sasm.getParameter('analysis')['guinier']

            try:
                guinierRgWindow.SetValue(self.formatNumStr(guinier['Rg']))
            except Exception:
                guinierRgWindow.SetValue('')

            try:
                guinierI0Window.SetValue(self.formatNumStr(guinier['I0']))
            except Exception:
                guinierI0Window.SetValue('')

            try:
                guinierRgerrWindow.SetValue(self.formatNumStr(guinier['Rg_err']))
            except Exception:
                guinierRgerrWindow.SetValue('')

            try:
                guinierI0errWindow.SetValue(self.formatNumStr(guinier['I0_err']))
            except Exception:
                guinierI0errWindow.SetValue('')

    def formatNumStr(self, val):
        val = float(val)

        if abs(val) > 1e3 or abs(val) < 1e-2:
            my_str = '%.2E' %(val)
        else:
            my_str = '%.4f' %(round(val,4))

        return my_str

    def updateGNOMInfo(self, iftm):
        gnomRgWindow = wx.FindWindowById(self.infodata['gnomRg'][1], self)
        gnomI0Window = wx.FindWindowById(self.infodata['gnomI0'][1], self)
        gnomRgerrWindow = wx.FindWindowById(self.infodata['gnomRg_err'][1], self)
        gnomI0errWindow = wx.FindWindowById(self.infodata['gnomI0_err'][1], self)
        gnomTEWindow = wx.FindWindowById(self.infodata['TE'][1], self)
        gnomQualityWindow = wx.FindWindowById(self.infodata['gnomQuality'][1], self)
        gnomChisqWindow = wx.FindWindowById(self.infodata['chisq'][1], self)
        gnomAlphaWindow = wx.FindWindowById(self.infodata['alpha'][1], self)

        gnomRgWindow.SetValue(self.formatNumStr(iftm.getParameter('rg')))
        gnomI0Window.SetValue(self.formatNumStr(iftm.getParameter('i0')))
        gnomRgerrWindow.SetValue(self.formatNumStr(iftm.getParameter('rger')))
        gnomI0errWindow.SetValue(self.formatNumStr(iftm.getParameter('i0er')))
        gnomTEWindow.SetValue(str(iftm.getParameter('TE')))
        gnomChisqWindow.SetValue(self.formatNumStr(iftm.getParameter('chisq')))
        gnomQualityWindow.SetValue(str(iftm.getParameter('quality')))
        gnomAlphaWindow.SetValue(str(iftm.getParameter('alpha')))


    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def createFileInfo(self):

        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(box, -1, '', style = wx.TE_READONLY)

        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        return boxsizer

    def onSaveInfo(self, evt):
        gnom_results = {}

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        dmax = str(dmaxWindow.GetValue())

        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        start_idx = startSpin.GetValue()
        end_idx = endSpin.GetValue()

        if not self.out_list or dmax not in self.out_list:
            self.updateGNOMSettings(update_plot=False)
            self.calcGNOM(dmax)

        gnom_results['Dmax'] = dmax
        gnom_results['Total_Estimate'] = self.out_list[dmax].getParameter('TE')
        gnom_results['Real_Space_Rg'] = self.out_list[dmax].getParameter('rg')
        gnom_results['Real_Space_I0'] = self.out_list[dmax].getParameter('i0')
        gnom_results['Real_Space_Rg_Err'] = self.out_list[dmax].getParameter('rger')
        gnom_results['Real_Space_I0_Err'] = self.out_list[dmax].getParameter('i0er')
        gnom_results['Alpha'] = self.out_list[dmax].getParameter('alpha')
        gnom_results['qStart'] = self.sasm.q[start_idx]
        gnom_results['qEnd'] = self.sasm.q[end_idx]
        gnom_results['GNOM_ChiSquared'] = self.out_list[dmax].getParameter('chisq')
        gnom_results['GNOM_Quality_Assessment'] = self.out_list[dmax].getParameter('quality')

        analysis_dict = self.sasm.getParameter('analysis')
        analysis_dict['GNOM'] = gnom_results

        if self.manip_item is not None:
            if gnom_results != self.old_analysis:
                wx.CallAfter(self.manip_item.markAsModified)
                wx.CallAfter(self.manip_item.updateInfoPanel)

        iftm = self.out_list[dmax]
        iftm.setParameter('filename', os.path.splitext(self.sasm.getParameter('filename'))[0]+'.out')

        if self.raw_settings.get('AutoSaveOnGnom'):
            if os.path.isdir(self.raw_settings.get('GnomFilePath')):
                RAWGlobals.mainworker_cmd_queue.put(['save_iftm', [iftm, self.raw_settings.get('GnomFilePath')]])
            else:
                self.raw_settings.set('GnomFilePath', False)
                wx.CallAfter(wx.MessageBox, 'The folder:\n' +self.raw_settings.get('GNOMFilePath')+ '\ncould not be found. Autosave of GNOM files has been disabled. If you are using a config file from a different computer please go into Advanced Options/Autosave to change the save folders, or save you config file to avoid this message next time.', 'Autosave Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

        RAWGlobals.mainworker_cmd_queue.put(['to_plot_ift', [iftm, 'black', None, not self.raw_settings.get('AutoSaveOnGnom')]])


        self.gnom_frame.OnClose()

    def onCloseButton(self, evt):

        self.gnom_frame.OnClose()

    def _onInfoButton(self, evt):
        msg = ('If you use GNOM in your work, in addition to citing '
            'the RAW paper please cite the paper given here:'
            '\nhttps://www.embl-hamburg.de/biosaxs/gnom.html')
        wx.MessageBox(str(msg), "How to cite GNOM", style = wx.ICON_INFORMATION | wx.OK)

    def onFindDmaxButton(self, evt):
        self.gnom_frame.showBusy(True, 'Finding Dmax')
        self._runFindDmax()

    def _runFindDmax(self):
        t = threading.Thread(target=self.findDmax)
        t.daemon=True
        t.start()

    def onDmaxText(self,evt):
        self.dmaxSpin.Unbind(wx.EVT_TEXT) #Avoid infinite recursion


        dmax = str(self.dmaxSpin.GetValue())
        try:
            dmax = float(dmax.replace(',', '.'))
            self.dmaxSpin.SetValue(int(dmax))
        except ValueError:
            pass

        self.dmaxSpin.Bind(wx.EVT_TEXT, self.onDmaxText)

    def onAlpha(self, evt):
        alpha = str(self.alpha_ctrl.GetValue())

        try:
            alpha = float(alpha.replace(',', '.'))
            self.alpha_ctrl.ChangeValue(str(alpha))

            old_alpha = float(self.gnom_settings['alpha'])

            if old_alpha != alpha:
                self.onSettingsChange(None)

        except ValueError:
            pass

    def onCutQRg(self, evt):
        self.cutQrg()

    def cutQrg(self):
        is_checked = self.cut_qrg.IsChecked()

        guinier_rg = wx.FindWindowById(self.infodata['guinierRg'][1], self)
        gnom_rg = wx.FindWindowById(self.infodata['gnomRg'][1], self)

        try:
            rg = float(guinier_rg.GetValue())
        except Exception:
            rg = 0

        if rg == 0:
            try:
                rg = float(gnom_rg.GetValue())
            except Exception:
                rg = 0

        if is_checked:
            self.previous_qmax = float(wx.FindWindowById(self.staticTxtIDs['qend'], self).GetValue())

            if rg > 0:
                q_max = 8./rg
                q_max = min(0.3, q_max)

            else:
                q_max = 0.3

        else:
            q_max = self.previous_qmax

        self.setQVal(q_max, 'qend')

    def onEnterInQlimits(self, evt):

        id = evt.GetId()

        txtctrl = wx.FindWindowById(id, self)

        #### If User inputs garbage: ####
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if id == self.staticTxtIDs['qstart']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.sasm.q[idx],5)))
                return

            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'], self)
                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.sasm.q[idx],4)))
                return
        #################################

        if id == self.staticTxtIDs['qstart']:
            control_name = 'qstart'

        elif id == self.staticTxtIDs['qend']:
            control_name = 'qend'

        self.setQVal(val, control_name)

    def setQVal(self, val, control_name):
        lx = self.sasm.q

        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
        closest = findClosest(val,lx)

        i = np.where(lx == closest)[0][0]

        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)

        if control_name == 'qstart':

            n_max = endSpin.GetValue()

            if i > n_max-3:
                i = n_max - 3

            startSpin.SetValue(i)

        elif control_name == 'qend':
            n_min = startSpin.GetValue()


            if i < n_min+3:
                i = n_min + 3

            endSpin.SetValue(i)

        txtctrl = wx.FindWindowById(self.staticTxtIDs[control_name], self)
        txtctrl.SetValue(str(round(self.sasm.q[int(i)],4)))

        update_plot = False

        if control_name == 'qstart':
            if i != self.old_nstart:
                self.out_list = {}
                update_plot = True
            self.old_nstart = i
        elif control_name == 'qend':
            if i != self.old_nend:
                self.out_list = {}
                update_plot = True
            self.old_nend = i

        if update_plot:
            wx.CallAfter(self.updatePlot)


    def onSpinCtrl(self, evt):

        myid = evt.GetId()

        update_plot = False

        if myid != self.spinctrlIDs['dmax']:
            spin = wx.FindWindowById(myid, self)

            startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
            endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)

            i = spin.GetValue()

            #Make sure the boundaries don't cross:
            if myid == self.spinctrlIDs['qstart']:
                max_val = endSpin.GetValue()
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)

                if i > max_val-3:
                    i = max_val - 3
                    spin.SetValue(i)

            elif myid == self.spinctrlIDs['qend']:
                min_val = startSpin.GetValue()
                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)

                if i < min_val+3:
                    i = min_val + 3
                    spin.SetValue(i)

            txt.SetValue(str(round(self.sasm.q[int(i)],4)))

            if myid == self.spinctrlIDs['qstart']:
                if i != self.old_nstart:
                    self.out_list = {}
                    update_plot = True
                self.old_nstart = i
            elif myid == self.spinctrlIDs['qend']:
                if i != self.old_nend:
                    self.out_list = {}
                    update_plot = True
                self.old_nend = i

        else:
            dmax = float(wx.FindWindowById(self.spinctrlIDs['dmax'], self).GetValue())
            if self.old_dmax != dmax:
                update_plot = True
            self.old_dmax = dmax

        if update_plot:
            #Important, since it's a slow function to update (could do it in a
            #timer instead) otherwise this spin event might loop!
            wx.CallAfter(self.updatePlot)


    def updatePlot(self):
        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        dmax = dmaxWindow.GetValue()

        plotpanel = self.gnom_frame.plotPanel

        if str(dmax) not in self.out_list:
            self.updateGNOMSettings(update_plot=False)
            self.calcGNOM(dmax)

        if str(dmax) in self.out_list:
            self.updateGNOMInfo(self.out_list[str(dmax)])

            a = plotpanel.subplots['P(r)']
            b = plotpanel.subplots['Data/Fit']
            if not a.get_autoscale_on():
                a.set_autoscale_on(True)
            if not b.get_autoscale_on():
                b.set_autoscale_on(True)

            plotpanel.plotPr(self.out_list[str(dmax)])
        else:
            plotpanel.clearDataPlot()

    def findDmax(self):
        self.updateGNOMSettings(update_plot=False)

        start = self.gnom_settings['first']
        end = self.gnom_settings['last']

        save_sasm = copy.deepcopy(self.sasm)

        save_sasm.setQrange((start, end))

        # Calculate Rg if not available
        error_weight = self.raw_settings.get('errorWeight')

        analysis = save_sasm.getParameter('analysis')
        if 'guinier' not in analysis:
            RAWAPI.auto_guinier(save_sasm, error_weight)

        try:
            dmax = RAWAPI.auto_dmax(save_sasm, single_proc=True)
        except Exception as e:
            dmax = -1
            msg = ("Automatic Dmax determination failed with the following error:\n"
                "{}".format(e))
            wx.CallAfter(self.main_frame.showMessageDialog, self, msg, "Error finding Dmax",
                wx.ICON_WARNING|wx.OK)
            traceback.print_exc()

        if dmax == -1:
            try:
                analysis = save_sasm.getParameter('analysis')
                rg = float(analysis['guinier']['Rg'])
            except Exception:
                rg = 10

            dmax = int(round(rg*3))

        wx.CallAfter(self._finishFindDmax, dmax)

    def _finishFindDmax(self, dmax):

        if dmax != -1:
            dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)

            dmaxWindow.SetValue(dmax)
            self.old_dmax = dmax

            if str(dmax) in self.out_list.keys():
                self.updateGNOMInfo(self.out_list[str(dmax)])

            else:
                self.calcGNOM(dmax)
                self.updateGNOMInfo(self.out_list[str(dmax)])

            self.updatePlot()

        self.gnom_frame.showBusy(show=False)

    def calcGNOM(self, dmax):
        tempdir = self.gnom_frame.standard_paths.GetTempDir()

        save_sasm = copy.deepcopy(self.sasm)

        savename = os.path.splitext(save_sasm.getParameter('filename'))[0] + '.dat'

        outname = tempfile.NamedTemporaryFile(dir=os.path.abspath(tempdir)).name
        while os.path.isfile(outname):
            outname = tempfile.NamedTemporaryFile(dir=os.path.abspath(tempdir)).name

        outname = os.path.split(outname)[1]
        outname = outname+'.out'

        if not os.path.isfile(os.path.join(self.gnom_frame.tempdir, self.gnom_frame.savename)):
            self.gnom_frame.saveGNOMProfile()

        if (self.gnom_frame.main_frame.OnlineControl.isRunning()
            and tempdir == self.gnom_frame.main_frame.OnlineControl.getTargetDir()):
            self.gnom_frame.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        try:
            SASFileIO.saveMeasurement(save_sasm, tempdir, self.raw_settings, filetype = '.dat')
        except SASExceptions.HeaderSaveError as e:
            self._showSaveError('header')

        try:
            iftm = SASCalc.runGnom(self.gnom_frame.savename, False, dmax,
                self.gnom_settings, self.gnom_frame.tempdir,
                self.raw_settings.get('ATSASDir'), self.gnom_frame.outname,
                new_gnom=self.gnom_frame.new_gnom)

        except (SASExceptions.NoATSASError, SASExceptions.GNOMError) as e:
            wx.CallAfter(wx.MessageBox, str(e), 'Error running GNOM/DATGNOM', style = wx.ICON_ERROR | wx.OK)
            self.SetFocusIgnoringChildren()
            traceback.print_exc()
            return

        if restart_timer:
            wx.CallAfter(self.gnom_frame.main_frame.controlTimer, True)

        self.out_list[str(int(iftm.getParameter('dmax')))] = iftm

    def onSettingsChange(self, evt):
        self.updateGNOMSettings()

    def updateGNOMSettings(self, update_plot=True):
        self.old_settings = copy.deepcopy(self.gnom_settings)

        self.gnom_settings = {
            'rmin_zero' : self.raw_settings.get('gnomForceRminZero'),
            'rmax_zero' : wx.FindWindowById(self.otherctrlIDs['force_dmax']).GetStringSelection(),
            'npts'      : self.raw_settings.get('gnomNPoints'),
            'alpha'     : wx.FindWindowById(self.staticTxtIDs['alpha']).GetValue(),
            'first'     : int( wx.FindWindowById(self.spinctrlIDs['qstart'], self).GetValue()),
            'last'      : int( wx.FindWindowById(self.spinctrlIDs['qend'], self).GetValue()),
            'system'    : self.raw_settings.get('gnomSystem'),
            'radius56'  : self.raw_settings.get('gnomRadius56'),
            'rmin'      : self.raw_settings.get('gnomRmin'),
            }

        if self.old_settings != self.gnom_settings:
            self.out_list = {}

        if update_plot:
            self.updatePlot()


    def onChangeParams(self, evt):
        self.main_frame.showOptionsDialog(focusHead='GNOM')

class DammifFrame(wx.Frame):

    def __init__(self, parent, title, iftm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = (min(725, client_display.Width), min(900, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self.manip_item = manip_item
        self.iftm = iftm
        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self._getATSASVersion()

        self.panel = wx.Panel(self)
        self.notebook = wx.Notebook(self.panel, wx.ID_ANY)
        self.RunPanel = DammifRunPanel(self.notebook, self.iftm, self.manip_item)
        self.ResultsPanel = DammifResultsPanel(self.notebook, self.iftm, self.manip_item)
        self.ViewerPanel = DammifViewerPanel(self.notebook)

        self.notebook.AddPage(self.RunPanel, 'Run')
        self.notebook.AddPage(self.ResultsPanel, 'Results')
        self.notebook.AddPage(self.ViewerPanel, 'Viewer')

        sizer = self._createLayout(self.panel)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.notebook, 1, wx.EXPAND)
        panel_sizer.Add(sizer, 0, wx.ALIGN_CENTER | wx.ALL, border=self._FromDIP(5))

        self.panel.SetSizer(panel_sizer)

        self.panel.Layout()
        self.Layout()
        self.SendSizeEvent()
        self.panel.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.notebook.Fit()

            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + self._FromDIP(20)
                self.SetSize(self._FromDIP(size))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        self.CenterOnParent()

        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.ResultsPanel.updateColors()
        self.ViewerPanel.updateColors()

    def _createLayout(self, parent):
        close_button = wx.Button(parent, -1, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer =  wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(info_button, 0, wx.RIGHT, self._FromDIP(5))
        button_sizer.Add(close_button, 0)

        return button_sizer

    def updateDAMMIFSettings(self):
        self.RunPanel.updateDAMMIFSettings()

    def _getATSASVersion(self):
        version = SASCalc.getATSASVersion(self.raw_settings.get('ATSASDir'))

        if ((int(version.split('.')[0]) == 3 and int(version.split('.')[1]) >= 1)
            or int(version.split('.')[0]) > 3):
            self.model_ext = '.cif'
        else:
            self.model_ext = '.pdb'

    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = ('In addition to citing the RAW paper:\n If you use DAMMIF '
        'in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/dammif.html\n\nIf you use '
        'DAMMIN in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/dammin.html\n\nIIf you use '
        'DAMAVER in your work, please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/damaver.html\n\nIf you use '
        'DAMCLUST in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/manuals/damclust.html\n\n'
        'If you use AMBIMETER in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/manuals/ambimeter.html.\n\n'
        'If you use SASRES in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/manuals/sasres.html\n\n'
        'If you use SUPCOMB in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/supcomb.html')
        wx.MessageBox(str(msg), "How to cite AMBIMETER/DAMMIF/DAMMIN/DAMAVER/DAMCLUST/SASRES", style = wx.ICON_INFORMATION | wx.OK)


    def OnClose(self, event):
        self.RunPanel.Close(event)

        if event.GetVeto():
            return
        else:
            self.Destroy()


class DammifRunPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.parent = parent

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.dammif_frame = parent.GetParent().GetParent()

        self.raw_settings = self.main_frame.raw_settings

        self.infodata = {}

        self.ids = {'runs'          : self.NewControlId(),
                    'procs'         : self.NewControlId(),
                    'mode'          : self.NewControlId(),
                    'sym'           : self.NewControlId(),
                    'anisometry'    : self.NewControlId(),
                    'status'        : self.NewControlId(),
                    'damaver'       : self.NewControlId(),
                    'damclust'      : self.NewControlId(),
                    'save'          : self.NewControlId(),
                    'prefix'        : self.NewControlId(),
                    'logbook'       : self.NewControlId(),
                    'start'         : self.NewControlId(),
                    'abort'         : self.NewControlId(),
                    'changedir'     : self.NewControlId(),
                    'program'       : self.NewControlId(),
                    'refine'        : self.NewControlId(),
                    'fname'         : self.NewControlId(),
                    'align'         : self.NewControlId(),
                    'align_file'    : self.NewControlId(),
                    'align_file_btn': self.NewControlId(),
                    }

        self.threads = []

        topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(topsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.logbook.SetActiveTabColour(RAWGlobals.tab_color)

    def _createLayout(self, parent):

        file_box = wx.StaticBox(parent, -1, 'Filename')

        file_ctrl = wx.TextCtrl(file_box, self.ids['fname'], self.filename,
            size = self._FromDIP((150, -1)), style = wx.TE_READONLY)

        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        file_sizer.Add(file_ctrl, 2, wx.LEFT | wx.RIGHT | wx.EXPAND, self._FromDIP(5))
        file_sizer.AddStretchSpacer(1)


        settings_sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, 'Settings')
        settings_box = settings_sizer.GetStaticBox()

        savedir_text = wx.StaticText(settings_box, -1, 'Output directory :')
        savedir_ctrl = wx.TextCtrl(settings_box, self.ids['save'], '',
            size = self._FromDIP((350, -1)))

        try:
            savedir_ctrl.AutoCompleteDirectories() #compatability for older versions of wxpython
        except AttributeError as e:
            print(e)

        savedir_button = wx.Button(settings_box, self.ids['changedir'], 'Select')
        savedir_button.Bind(wx.EVT_BUTTON, self.onChangeDirectoryButton)

        dir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dir_sizer.Add(savedir_ctrl, proportion=1, border=self._FromDIP(2),
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        dir_sizer.Add(savedir_button, flag=wx.ALIGN_CENTER_VERTICAL)

        savedir_sizer = wx.BoxSizer(wx.VERTICAL)
        savedir_sizer.Add(savedir_text, 0, wx.LEFT | wx.RIGHT,
            border=self._FromDIP(2))
        savedir_sizer.Add(dir_sizer, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND,
            border=self._FromDIP(2))


        prefix_text = wx.StaticText(settings_box, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(settings_box, self.ids['prefix'], '',
            size = self._FromDIP((150, -1)))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.LEFT, border=self._FromDIP(5))
        prefix_sizer.Add(prefix_ctrl, 1, wx.LEFT | wx.RIGHT, border=self._FromDIP(5))
        prefix_sizer.AddStretchSpacer(1)


        nruns_text = wx.StaticText(settings_box, -1, 'Number of reconstructions :')
        nruns_ctrl = wx.TextCtrl(settings_box, self.ids['runs'], '',
            size = self._FromDIP((60, -1)))
        nruns_ctrl.Bind(wx.EVT_TEXT, self.onRunsText)

        nruns_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nruns_sizer.Add(nruns_text, 0, wx.LEFT, border=self._FromDIP(5))
        nruns_sizer.Add(nruns_ctrl, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(5))


        nprocs = multiprocessing.cpu_count()
        nprocs_choices = [str(i) for i in range(nprocs, 0, -1)]
        nprocs_text = wx.StaticText(settings_box, -1, 'Number of simultaneous runs :')
        nprocs_choice = wx.Choice(settings_box, self.ids['procs'], choices = nprocs_choices)

        nprocs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nprocs_sizer.Add(nprocs_text, 0, wx.LEFT, border=self._FromDIP(5))
        nprocs_sizer.Add(nprocs_choice, 0, wx.LEFT | wx.RIGHT,
            border=self._FromDIP(5))


        program_text = wx.StaticText(settings_box, -1, 'Use :')
        program_choice = wx.Choice(settings_box, self.ids['program'], choices = ['DAMMIF', 'DAMMIN'])


        mode_text = wx.StaticText(settings_box, -1, 'Mode :')
        mode_choice = wx.Choice(settings_box, self.ids['mode'], choices = ['Fast', 'Slow', 'Custom'])


        sym_choices = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 'P11',
                        'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18', 'P19', 'P22', 'P222',
                        'P32', 'P42', 'P52', 'P62', 'P72', 'P82', 'P92', 'P102', 'P112', 'P122']

        sym_text = wx.StaticText(settings_box, -1, 'Symmetry :')
        sym_choice = wx.Choice(settings_box, self.ids['sym'], choices = sym_choices)


        anisometry_choices = ['Unknown', 'Prolate', 'Oblate']
        aniso_text = wx.StaticText(settings_box, -1, 'Anisometry :')
        aniso_choice = wx.Choice(settings_box, self.ids['anisometry'], choices = anisometry_choices)


        choices_sizer = wx.FlexGridSizer(cols=4, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))
        choices_sizer.SetFlexibleDirection(wx.HORIZONTAL)
        choices_sizer.AddGrowableCol(0)
        choices_sizer.AddGrowableCol(1)
        choices_sizer.AddGrowableCol(2)
        choices_sizer.AddGrowableCol(3)

        choices_sizer.Add(program_text)
        choices_sizer.Add(mode_text)
        choices_sizer.Add(sym_text)
        choices_sizer.Add(aniso_text)

        choices_sizer.Add(program_choice)
        choices_sizer.Add(mode_choice)
        choices_sizer.Add(sym_choice)
        choices_sizer.Add(aniso_choice)

        damaver_chk = wx.CheckBox(settings_box, self.ids['damaver'], 'Align and average envelopes (damaver)')
        damaver_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        refine_chk = wx.CheckBox(settings_box, self.ids['refine'], 'Refine average with dammin')
        refine_sizer = wx.BoxSizer(wx.HORIZONTAL)
        refine_sizer.AddSpacer(self._FromDIP(20))
        refine_sizer.Add(refine_chk)

        damclust_chk = wx.CheckBox(settings_box, self.ids['damclust'], 'Align and cluster envelopes (damclust)')
        damclust_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        self.align_result = wx.CheckBox(settings_box, self.ids['align'],
            label='Align output to PDB:')
        self.align_result.SetValue(False)
        self.align_file_ctrl = wx.TextCtrl(settings_box, self.ids['align_file'],
            style=wx.TE_READONLY)
        align_button = wx.Button(settings_box, self.ids['align_file_btn'],
            label='Select')
        align_button.Bind(wx.EVT_BUTTON, self._selectAlignFile)

        align_sizer = wx.BoxSizer(wx.HORIZONTAL)
        align_sizer.Add(self.align_result, border=self._FromDIP(5), flag=wx.RIGHT)
        align_sizer.Add(self.align_file_ctrl, border=self._FromDIP(5), flag=wx.RIGHT,
            proportion=1)
        align_sizer.Add(align_button)

        advancedButton = wx.Button(settings_box, -1, 'Change Advanced Settings')
        advancedButton.Bind(wx.EVT_BUTTON, self._onAdvancedButton)


        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND | wx.TOP, self._FromDIP(2))
        settings_sizer.Add(nruns_sizer, 0, wx.TOP, self._FromDIP(2))
        settings_sizer.Add(nprocs_sizer, 0, wx.TOP, self._FromDIP(2))
        settings_sizer.Add(choices_sizer, 0, wx.LEFT | wx.RIGHT | wx.TOP
            |wx.EXPAND, self._FromDIP(2))
        settings_sizer.Add(damaver_chk, 0, wx.LEFT | wx.RIGHT | wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(refine_sizer, 0, wx.LEFT | wx.RIGHT | wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(damclust_chk, 0, wx.LEFT | wx.RIGHT | wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(align_sizer, border=2, flag=wx.LEFT|wx.RIGHT|wx.TOP
            |wx.EXPAND)
        settings_sizer.Add(advancedButton, 0, wx.LEFT | wx.RIGHT | wx.TOP
            |wx.ALIGN_CENTER, self._FromDIP(2))


        start_button = wx.Button(parent, self.ids['start'], 'Start')
        start_button.Bind(wx.EVT_BUTTON, self.onStartButton)

        abort_button = wx.Button(parent, self.ids['abort'], 'Abort')
        abort_button.Bind(wx.EVT_BUTTON, self.onAbortButton)

        button_box = wx.StaticBox(parent, -1, 'Controls')
        button_sizer = wx.StaticBoxSizer(button_box, wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_CENTER,
            border=self._FromDIP(2))
        button_sizer.Add(abort_button, 0, wx.ALL | wx.ALIGN_CENTER,
            border=self._FromDIP(2))
        button_sizer.AddStretchSpacer(1)

        control_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer.Add(file_sizer, 0, wx.EXPAND)
        control_sizer.Add(settings_sizer, 0, wx.EXPAND)
        control_sizer.Add(button_sizer, 0, wx.EXPAND)


        status_box = wx.StaticBox(parent, -1, 'Status')

        self.status = wx.TextCtrl(status_box, self.ids['status'], '',
            style = wx.TE_MULTILINE | wx.TE_READONLY, size = self._FromDIP((100,200)))

        status_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)
        status_sizer.Add(self.status, 1, wx.EXPAND | wx.ALL,
            border=self._FromDIP(2))


        half_sizer = wx.BoxSizer(wx.HORIZONTAL)
        half_sizer.Add(control_sizer, 2, wx.EXPAND)
        half_sizer.Add(status_sizer, 1, wx.EXPAND)

        log_box = wx.StaticBox(parent, -1, 'Log')

        try:
            self.logbook = flatNB.FlatNotebook(log_box, self.ids['logbook'],
                agwStyle = flatNB.FNB_NAV_BUTTONS_WHEN_NEEDED | flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)
        except AttributeError as e:
            print(e)
            self.logbook = flatNB.FlatNotebook(log_box, self.ids['logbook'])     #compatability for older versions of wxpython
            self.logbook.SetWindowStyleFlag(flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)

        self.logbook.SetActiveTabColour(RAWGlobals.tab_color)
        self.logbook.DeleteAllPages()

        log_sizer = wx.StaticBoxSizer(log_box, wx.HORIZONTAL)
        log_sizer.Add(self.logbook, 1, wx.ALL | wx.EXPAND, 2)

        if (int(wx.__version__.split('.')[1])<9
            and int(wx.__version__.split('.')[0]) == 2):     #compatability for older versions of wxpython
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            top_sizer.Add(half_sizer, 0, wx.EXPAND)
            top_sizer.Add(log_sizer, 1, wx.EXPAND)
        else:
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            top_sizer.Add(half_sizer, 1, wx.EXPAND)
            top_sizer.Add(log_sizer, 1, wx.EXPAND)

        self.dammif_timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self.onDammifTimer, self.dammif_timer)


        return top_sizer


    def _initSettings(self):
        self.dammif_settings = {'mode'              : self.raw_settings.get('dammifMode'),
                                'unit'              : self.raw_settings.get('dammifUnit'),
                                'sym'               : self.raw_settings.get('dammifSymmetry'),
                                'anisometry'        : self.raw_settings.get('dammifAnisometry'),
                                'omitSolvent'       : self.raw_settings.get('dammifOmitSolvent'),
                                'chained'           : self.raw_settings.get('dammifChained'),
                                'constant'          : self.raw_settings.get('dammifConstant'),
                                'maxBead'           : self.raw_settings.get('dammifMaxBeadCount'),
                                'radius'            : self.raw_settings.get('dammifDummyRadius'),
                                'harmonics'         : self.raw_settings.get('dammifSH'),
                                'propFit'           : self.raw_settings.get('dammifPropToFit'),
                                'curveWeight'       : self.raw_settings.get('dammifCurveWeight'),
                                'seed'              : self.raw_settings.get('dammifRandomSeed'),
                                'maxSteps'          : self.raw_settings.get('dammifMaxSteps'),
                                'maxIters'          : self.raw_settings.get('dammifMaxIters'),
                                'maxSuccess'        : self.raw_settings.get('dammifMaxStepSuccess'),
                                'minSuccess'        : self.raw_settings.get('dammifMinStepSuccess'),
                                'TFactor'           : self.raw_settings.get('dammifTFactor'),
                                'RgWeight'          : self.raw_settings.get('dammifRgPen'),
                                'cenWeight'         : self.raw_settings.get('dammifCenPen'),
                                'looseWeight'       : self.raw_settings.get('dammifLoosePen'),
                                'initialDAM'        : self.raw_settings.get('damminInitial'),
                                'knots'             : self.raw_settings.get('damminKnots'),
                                'damminConstant'    : self.raw_settings.get('damminConstant'),
                                'diameter'          : self.raw_settings.get('damminDiameter'),
                                'packing'           : self.raw_settings.get('damminPacking'),
                                'coordination'      : self.raw_settings.get('damminCoordination'),
                                'disconWeight'      : self.raw_settings.get('damminDisconPen'),
                                'periphWeight'      : self.raw_settings.get('damminPeriphPen'),
                                'damminCurveWeight' : self.raw_settings.get('damminCurveWeight'),
                                'annealSched'       : self.raw_settings.get('damminAnealSched'),
                                'shape'             : self.raw_settings.get('dammifExpectedShape')
                                }

        mode = wx.FindWindowById(self.ids['mode'], self)
        mode.SetStringSelection(self.dammif_settings['mode'])

        sym = wx.FindWindowById(self.ids['sym'], self)
        sym.SetStringSelection(self.dammif_settings['sym'])

        anisometry = wx.FindWindowById(self.ids['anisometry'], self)
        anisometry.SetStringSelection(self.dammif_settings['anisometry'])

        procs = wx.FindWindowById(self.ids['procs'], self)
        if procs.GetCount()>1:
            procs.SetSelection(1)
        else:
            procs.SetSelection(0)

        damaver = wx.FindWindowById(self.ids['damaver'], self)
        damaver.SetValue(self.raw_settings.get('dammifDamaver'))

        damclust = wx.FindWindowById(self.ids['damclust'], self)
        damclust.SetValue(self.raw_settings.get('dammifDamclust'))

        prefix = wx.FindWindowById(self.ids['prefix'], self)
        prefix.SetValue(os.path.splitext(self.filename)[0])

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        save = wx.FindWindowById(self.ids['save'], self)
        save.SetValue(path)

        nruns = wx.FindWindowById(self.ids['runs'], self)
        nruns.SetValue(str(self.raw_settings.get('dammifReconstruct')))

        refine = wx.FindWindowById(self.ids['refine'], self)

        if refine.IsEnabled:
            refine.SetValue(self.raw_settings.get('dammifRefine'))

        program = wx.FindWindowById(self.ids['program'], self)
        program.SetStringSelection(self.raw_settings.get('dammifProgram'))

        wx.FindWindowById(self.ids['abort'], self).Disable()

        self.logbook.DeleteAllPages()

        self.align_file_name = None

        self.model_ext = self.dammif_frame.model_ext

    def onStartButton(self, evt):
        #Set the dammif settings
        self.setArgs()

        #Get user settings on number of runs, save location, etc
        damaver_window = wx.FindWindowById(self.ids['damaver'], self)
        damaver = damaver_window.GetValue()

        damclust_window = wx.FindWindowById(self.ids['damclust'], self)
        damclust = damclust_window.GetValue()

        prefix_window = wx.FindWindowById(self.ids['prefix'], self)
        prefix = prefix_window.GetValue()
        prefix = prefix.replace(' ', '_')

        path_window = wx.FindWindowById(self.ids['save'], self)
        path = path_window.GetValue()

        procs_window = wx.FindWindowById(self.ids['procs'], self)
        procs = int(procs_window.GetStringSelection())

        nruns_window = wx.FindWindowById(self.ids['runs'], self)
        nruns = int(nruns_window.GetValue())

        program_window = wx.FindWindowById(self.ids['program'], self)
        program = program_window.GetStringSelection()

        refine_window = wx.FindWindowById(self.ids['refine'], self)
        refine = refine_window.GetValue()

        align = self.align_result.GetValue()

        if len(prefix)>30:
            msg = ("Warning: The file prefix '{}'' is too long (>30 characters). It "
                "will be truncated to '{}'. Proceed?".format(prefix, prefix[:30]))
            dlg = wx.MessageDialog(self.main_frame, msg, "Truncate filename?",
                style=wx.ICON_WARNING|wx.YES_NO)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            if proceed == wx.ID_YES:
                prefix = prefix[:30]
                prefix_window.SetValue(prefix)
            else:
                return

        outname = os.path.join(path, prefix+'.out')

        #Check to see if any files will be overwritten. Prompt use if that is the case. Write the .out file for dammif to use
        if os.path.exists(outname):
            existingOut = SASFileIO.loadOutFile(outname)[0].getParameter('out')
            if existingOut != self.ift:

                msg = ("Warning: the file %s already exists in the specified "
                    "directory, and is not identical to the P(r) dammif will "
                    "use. To continue, RAW must overwrite this file. Do you "
                    "wish to continue?" %(prefix+'.out'))
                dlg = wx.MessageDialog(self.main_frame, msg, "Overwrite existing file?", style = wx.ICON_WARNING | wx.YES_NO)
                proceed = dlg.ShowModal()
                dlg.Destroy()

                if proceed == wx.ID_YES:
                    with open(outname, 'w') as f:
                        for line in self.ift:
                            f.write(line)
                else:
                    return
        else:
            with open(outname, 'w') as f:
                for line in self.ift:
                    f.write(line)

        dammif_names = {key: value for (key, value) in [(str(i), prefix+'_%s' %(str(i).zfill(2))) for i in range(1, nruns+1)]}
        if refine:
            dammif_names['refine'] = 'refine_' + prefix

        yes_to_all = False
        for key in dammif_names:
            LogName = os.path.join(path, dammif_names[key]+'.log')
            InName = os.path.join(path, dammif_names[key]+'.in')
            FitName = os.path.join(path, dammif_names[key]+'.fit')
            FirName = os.path.join(path, dammif_names[key]+'.fir')
            EnvelopeName = os.path.join(path, dammif_names[key]+'-1' + self.model_ext)
            SolventName = os.path.join(path, dammif_names[key]+'-0' + self.model_ext)

            if ((os.path.exists(LogName) or os.path.exists(InName)
                or os.path.exists(FitName) or os.path.exists(FirName)
                or os.path.exists(EnvelopeName) or os.path.exists(SolventName))
                and not yes_to_all):
                button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                question = ('Warning: selected directory contains DAMMIF/N '
                    'output files with the prefix:\n"%s".\nRunning DAMMIF/N '
                    'will overwrite these files.\nDo you wish to continue?'
                    %(dammif_names[key]))
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                    question, button_list, label, icon,
                    style = wx.CAPTION | wx.RESIZE_BORDER)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True

        #Set up the various bits of information the threads will need. Set up the status windows.
        self.dammif_ids = {key: value for (key, value) in [(str(i), self.NewControlId()) for i in range(1, nruns+1)]}

        self.thread_nums = queue.Queue()

        self.logbook.DeleteAllPages()

        for i in range(1, nruns+1):
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids[str(i)], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, str(i))
            self.thread_nums.put(str(i))

        if nruns > 1 and damaver:

            damaver_names = [
                prefix+'_damfilt' + self.model_ext,
                prefix+'_damsel.log',
                prefix+'_damstart' + self.model_ext,
                prefix+'_damsup.log',
                prefix+'_damaver' + self.model_ext,
                'damfilt' + self.model_ext,
                'damsel.log',
                'damstart' + self.model_ext,
                'damsup.log',
                'damaver' + self.model_ext
                ]

            for item in damaver_names:

                if os.path.exists(os.path.join(path, item)) and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                    question = 'Warning: selected directory contains the DAMAVER output file\n"%s". Running DAMAVER will overwrite this file.\nDo you wish to continue?' %(item)
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                        question, button_list, label, icon,
                        style = wx.CAPTION | wx.RESIZE_BORDER)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['damaver'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['damaver'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Average')

        if nruns > 1 and refine:
            self.dammif_ids['refine'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['refine'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Refine')

        if nruns > 1 and damclust:

            damclust_names = [prefix+'_damclust.log']

            for item in damclust_names:

                if os.path.exists(os.path.join(path, item)) and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES),
                        ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                    question = ('Warning: selected directory contains the '
                        'DAMCLUST output file\n"%s". Running DAMCLUST will '
                        'overwrite this file.\nDo you wish to continue?' %(item))
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                        question, button_list, label, icon,
                        style = wx.CAPTION | wx.RESIZE_BORDER)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['damclust'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['damclust'], '',
                style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Cluster')

        if align and self.align_file_name != '':
            filenames = [os.path.split(self.align_file_name)[1]]

            filenames.extend(['{}-1_aligned{}'.format(key, self.model_ext)
                for key in dammif_names])

            if nruns > 1 and damaver:
                filenames.extend(['{}_damfilt_aligned{}'.format(prefix, self.model_ext),
                    '{}_damaver_aligned{}'.format(prefix, self.model_ext)])

            if nruns > 1 and refine:
                filenames.append('{}_refined-1{}'.format(prefix, self.model_ext))

            for item in filenames:
                if os.path.exists(os.path.join(path, item)) and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES),
                        ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]

                    question = ('Warning: selected directory contains an '
                        'alignment output file\n"%s". Running alignment will '
                        'overwrite this file.\nDo you wish to continue?' %(item))
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                        question, button_list, label, icon,
                        style=wx.CAPTION|wx.RESIZE_BORDER)

                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['align'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['align'], '',
                style=wx.TE_MULTILINE|wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Align')

        elif align and self.align_file_name == '':
            msg = ('You must select a file to align to or disable alignment.')
            dlg = wx.MessageDialog(self, msg, 'No alignment template file')
            dlg.ShowModal()
            dlg.Destroy()
            return


        self.status.SetValue('Starting processing\n')


        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                wx.FindWindowById(self.ids[key], self).Disable()
            elif key == 'abort':
                wx.FindWindowById(self.ids[key], self).Enable()


        self.threads = []

        self.my_semaphore = threading.BoundedSemaphore(procs)
        self.start_semaphore = threading.BoundedSemaphore(1)

        self.abort_event = threading.Event()
        self.abort_event.clear()

        self.rs = queue.Queue()

        for key in self.dammif_ids:
            if (key != 'damaver' and key != 'damclust' and key != 'refine'
                and key != 'align'):
                t = threading.Thread(target = self.runDammif,
                    args=(outname, prefix, path, program))
                t.daemon = True
                t.start()
                self.threads.append(t)

        self.dammif_timer.Start(1000)

        self.main_frame.sleep_inhibit.on()


    def onAbortButton(self, evt):
        self.abort_event.set()

        if self.dammif_timer.IsRunning():
            self.dammif_timer.Stop()

        aborted = False

        while not aborted:
            done_list = [False for i in range(len(self.threads))]
            for i in range(len(self.threads)):
                if not self.threads[i].is_alive():
                    done_list[i] = True
            if np.all(done_list):
                aborted = True
            time.sleep(.1)


        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                wx.FindWindowById(self.ids[key], self).Enable()
            elif key == 'abort':
                wx.FindWindowById(self.ids[key], self).Disable()


        self.status.AppendText('Processing Aborted!')

        self.main_frame.sleep_inhibit.off()


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save'], self).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)

        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save'], self).SetValue(new_path)

        dirdlg.Destroy()

    def _selectAlignFile(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        filters = 'PDB and CIF files (*.pdb;*.cif)|*.pdb;*.cif|All files (*.*)|*.*'

        dialog = wx.FileDialog(self, 'Select a file', load_path, style=wx.FD_OPEN,
            wildcard=filters)

        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        # Destroy the dialog
        dialog.Destroy()

        if file is not None:
            self.align_file_name = file
            self.align_file_ctrl.SetValue(os.path.split(file)[1])
            self.align_file_ctrl.SetToolTip(wx.ToolTip(file))


    def onRunsText(self, evt):
        nruns_ctrl = wx.FindWindowById(self.ids['runs'], self)


        nruns = nruns_ctrl.GetValue()
        if nruns != '' and not nruns.isdigit():

            try:
                nruns = float(nruns.replace(',', '.'))
            except ValueError as e:
                print (e)
                nruns = ''
            if nruns != '':
                nruns = str(int(nruns))

            nruns_ctrl.ChangeValue(nruns) #Use changevalue instead of setvalue to avoid having to unbind and rebind


    def setArgs(self):
        for key in self.dammif_settings:
            if key in self.ids:
                window = wx.FindWindowById(self.ids[key], self)

                self.dammif_settings[key] = window.GetStringSelection()


    def runDammif(self, outname, prefix, path, program, refine = False):
        def read_output(process):
            while process.poll() is None:
                if process.stdout is not None:
                    process.stdout.read(1)

        with self.my_semaphore:
            #Check to see if things have been aborted
            if not refine:
                my_num = self.thread_nums.get()
                damId = self.dammif_ids[my_num]
            else:
                damId = self.dammif_ids['refine']
            damWindow = wx.FindWindowById(damId, self)

            if self.abort_event.isSet():
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return


            #Make sure that you don't start two dammif processes with the same random seed
            with self.start_semaphore:
                if not self.rs.empty():
                    old_rs = self.rs.get()
                    while old_rs == int(time.time()):
                        time.sleep(0.01)
                self.rs.put(int(time.time()))

            if not refine:
                dam_prefix = prefix+'_%s' %(my_num.zfill(2))
            else:
                dam_prefix = 'refine_' + prefix

            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, dam_prefix+'.log'),
                os.path.join(path, dam_prefix+'.in'),
                os.path.join(path, dam_prefix+'.fit'),
                os.path.join(path, dam_prefix+'.fir'),
                os.path.join(path, dam_prefix+'-1'+self.model_ext),
                os.path.join(path, dam_prefix+'-1_aligned'+self.model_ext),
                os.path.join(path, dam_prefix+'-0'+self.model_ext),
                ]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            #Run DAMMIF
            dam_args = self.dammif_settings

            if refine:
                self.dammif_settings['mode'] = 'Refine'
                self.dammif_settings['initialDAM'] = prefix+'_damstart'+self.model_ext

            if refine:
                wx.CallAfter(self.status.AppendText, 'Starting Refinement\n')
            else:
                wx.CallAfter(self.status.AppendText, 'Starting %s run %s\n' %(program, my_num))

            if refine:
                program = 'DAMMIN'

            if program == 'DAMMIF':
                dammif_proc = SASCalc.runDammif(outname, dam_prefix, dam_args,
                    path, self.raw_settings.get('ATSASDir'))
            else:
                dammif_proc = SASCalc.runDammin(outname, dam_prefix, dam_args,
                    path, self.raw_settings.get('ATSASDir'))

            #Hackey, but necessary to prevent the process output buffer
            # from filling up and stalling the process
            if dammif_proc.stdout is not None:
                read_thread = threading.Thread(target=read_output, args=(dammif_proc,))
                read_thread.daemon = True
                read_thread.start()

            logname = os.path.join(path,dam_prefix)+'.log'

            while not os.path.exists(logname):
                time.sleep(0.01)

            pos = 0

            #Send the DAMMIF log output to the screen.
            while dammif_proc.poll() is None:
                if self.abort_event.isSet():
                    dammif_proc.terminate()
                    wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                    return

                with open(logname, 'rb') as logfile:
                    logfile.seek(pos)
                    newtext = logfile.read()
                    pos = logfile.tell()

                if newtext != '':
                    wx.CallAfter(damWindow.AppendText, newtext)

                time.sleep(.1)

            with open(logname, 'rb') as logfile:
                logfile.seek(pos)
                final_status = logfile.read()

            wx.CallAfter(damWindow.AppendText, final_status)

            if dammif_proc.stderr is not None:
                error = dammif_proc.stderr.read()

                if not isinstance(error, str):
                    error = str(error, encoding='UTF-8')

                if error != '':
                    wx.CallAfter(damWindow.AppendText, error)

            if refine:
                wx.CallAfter(self.status.AppendText, 'Finished Refinement\n')

                damclust_window = wx.FindWindowById(self.ids['damclust'])
                damclust = damclust_window.GetValue()

                if damclust:
                    t = threading.Thread(target = self.runDamclust, args = (prefix, path))
                    t.daemon = True
                    t.start()
                    self.threads.append(t)

                elif 'align' in self.dammif_ids:
                    t = threading.Thread(target = self.runSupcomb, args = (prefix, path))
                    t.daemon = True
                    t.start()
                    self.threads.append(t)

                else:
                    wx.CallAfter(self.finishedProcessing)
            else:
                wx.CallAfter(self.status.AppendText, 'Finished %s run %s\n' %(program, my_num))


    def runDamaver(self, prefix, path):
        read_semaphore = threading.BoundedSemaphore(1)

        with self.my_semaphore:
            #Check to see if things have been aborted
            damId = self.dammif_ids['damaver']
            damWindow = wx.FindWindowById(damId, self)

            if self.abort_event.isSet():
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return

            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, prefix+'_damfilt'+self.model_ext),
                os.path.join(path, prefix+'_damsel.log'),
                os.path.join(path, prefix+'_damstart'+self.model_ext),
                os.path.join(path, prefix+'_damsup.log'),
                os.path.join(path, prefix+'_damaver'+self.model_ext),
                os.path.join(path, prefix+'_damfilt_aligned'+self.model_ext),
                os.path.join(path, prefix+'_damaver_aligned'+self.model_ext),
                ]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            wx.CallAfter(self.status.AppendText, 'Starting DAMAVER\n')


            nruns_window = wx.FindWindowById(self.ids['runs'], self)
            nruns = int(nruns_window.GetValue())

            dam_filelist = [prefix+'_%s-1%s' %(str(i).zfill(2), self.model_ext)
                for i in range(1, nruns+1)]

            symmetry = self.dammif_settings['sym']

            damaver_proc = SASCalc.runDamaver(dam_filelist, path,
                self.raw_settings.get('ATSASDir'), symmetry)

            damaver_q = queue.Queue()
            readout_t = threading.Thread(target=self.enqueue_output,
                args=(damaver_proc, damaver_q, read_semaphore))
            readout_t.daemon = True
            readout_t.start()


            #Send the damaver output to the screen.
            while damaver_proc.poll() is None:
                if self.abort_event.isSet():
                    damaver_proc.terminate()
                    wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                    return

                try:
                    new_text = damaver_q.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(damWindow.AppendText, new_text)
                except queue.Empty:
                    pass
                time.sleep(0.001)

            time.sleep(2)
            with read_semaphore: #see if there's any last data that we missed
                while True:
                    try:
                        new_text = damaver_q.get_nowait()
                        new_text = new_text[0]

                        if new_text != '':
                            wx.CallAfter(damWindow.AppendText, new_text)

                    except queue.Empty:
                        break

                new_text = damaver_proc.stdout.read()

                if not isinstance(new_text, str):
                    new_text = str(new_text, encoding='UTF-8')

                if new_text != '':
                    wx.CallAfter(damWindow.AppendText, new_text)

            new_files = [
                (os.path.join(path, 'damfilt'+self.model_ext),
                    os.path.join(path, prefix+'_damfilt'+self.model_ext)),
                (os.path.join(path, 'damsel.log'),
                    os.path.join(path, prefix+'_damsel.log')),
                (os.path.join(path, 'damstart'+self.model_ext),
                    os.path.join(path, prefix+'_damstart'+self.model_ext)),
                (os.path.join(path, 'damsup.log'),
                    os.path.join(path, prefix+'_damsup.log')),
                (os.path.join(path, 'damaver'+self.model_ext),
                    os.path.join(path, prefix+'_damaver'+self.model_ext))]

            for item in new_files:
                os.rename(item[0], item[1])


            wx.CallAfter(self.status.AppendText, 'Finished DAMAVER\n')

            refine_window = wx.FindWindowById(self.ids['refine'], self)
            refine = refine_window.GetValue()

            damclust_window = wx.FindWindowById(self.ids['damclust'])
            damclust = damclust_window.GetValue()

            if refine:
                program_window = wx.FindWindowById(self.ids['program'], self)
                program = program_window.GetStringSelection()

                outname = os.path.join(path, prefix+'.out')

                t = threading.Thread(target = self.runDammif, args = (outname,
                    prefix, path, program, refine))
                t.daemon = True
                t.start()
                self.threads.append(t)
            elif damclust:
                t = threading.Thread(target = self.runDamclust, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            elif 'align' in self.dammif_ids:
                t = threading.Thread(target = self.runSupcomb, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            else:
                wx.CallAfter(self.finishedProcessing)


    def runDamclust(self, prefix, path):

        read_semaphore = threading.BoundedSemaphore(1)

        with self.my_semaphore:
            #Check to see if things have been aborted
            damId = self.dammif_ids['damclust']
            damWindow = wx.FindWindowById(damId, self)

            if self.abort_event.isSet():
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return

            nruns_window = wx.FindWindowById(self.ids['runs'], self)
            nruns = int(nruns_window.GetValue())

            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, prefix+'_damclust.log')]

            for i in range(1, nruns+1):
                old_files.append(os.path.join(path, '{}-1-avr{}'.format(prefix,
                    self.model_ext)))
                old_files.append(os.path.join(path, '{}-1-flt{}'.format(prefix,
                    self.model_ext)))

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            wx.CallAfter(self.status.AppendText, 'Starting DAMCLUST\n')


            dam_filelist = [prefix+'_%s-1%s' %(str(i).zfill(2), self.model_ext)
                for i in range(1, nruns+1)]

            symmetry = self.dammif_settings['sym']

            damclust_proc = SASCalc.runDamclust(dam_filelist, path,
                self.raw_settings.get('ATSASDir'), symmetry)


            damclust_q = queue.Queue()
            readout_t = threading.Thread(target=self.enqueue_output,
                args=(damclust_proc, damclust_q, read_semaphore))
            readout_t.daemon = True
            readout_t.start()


            #Send the damclust output to the screen.
            while damclust_proc.poll() is None:
                if self.abort_event.isSet():
                    damclust_proc.terminate()
                    wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                    return

                try:
                    new_text = damclust_q.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(damWindow.AppendText, new_text)
                except queue.Empty:
                    pass
                time.sleep(0.001)

            time.sleep(2)

            with read_semaphore: #see if there's any last data that we missed
                while True:
                    try:
                        new_text = damclust_q.get_nowait()
                        new_text = new_text[0]

                        if new_text != '':
                            wx.CallAfter(damWindow.AppendText, new_text)

                    except queue.Empty:
                        break

                new_text = damclust_proc.stdout.read()

                if not isinstance(new_text, str):
                    new_text = str(new_text, encoding='UTF-8')

                if new_text != '':
                    wx.CallAfter(damWindow.AppendText, new_text)


            new_files = [(os.path.join(path, 'damclust.log'), os.path.join(path, prefix+'_damclust.log'))]

            for item in new_files:
                os.rename(item[0], item[1])

            wx.CallAfter(self.status.AppendText, 'Finished DAMCLUST\n')

            if 'align' in self.dammif_ids:
                t = threading.Thread(target = self.runSupcomb, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            else:
                wx.CallAfter(self.finishedProcessing)


    def runSupcomb(self, prefix, path):

        if self.align_file_name != os.path.join(path, os.path.split(self.align_file_name)[-1]):
            shutil.copy(self.align_file_name, path)

        template = os.path.split(self.align_file_name)[-1]

        with self.my_semaphore:
            #Check to see if things have been aborted
            sup_id = self.dammif_ids['align']
            sup_window = wx.FindWindowById(sup_id, self)

            if self.abort_event.is_set():
                wx.CallAfter(sup_window.AppendText, 'Aborted!\n')
                return

            nruns = int(wx.FindWindowById(self.ids['runs'], self).GetValue())
            symmetry = self.dammif_settings['sym']

            if symmetry == 'P1':
                mode = 'fast'
            else:
                mode = 'slow'

            target_filenames = []
            if 'damaver' in self.dammif_ids:
                name = '{}_damsup.log'.format(prefix)
                filename = os.path.join(path, name)
                _, rep_model = SASFileIO.loadDamsupLogFile(filename)

                target_filenames.extend(['{}_damaver{}'.format(prefix, self.model_ext),
                    '{}_damfilt{}'.format(prefix, self.model_ext), rep_model])

            if 'refine' in self.dammif_ids:
                target_filenames.append('refine_{}-1{}'.format(prefix, self.model_ext))

            if 'damclust' in self.dammif_ids:
                name = '{}_damclust.log'.format(prefix)
                filename = os.path.join(path, name)
                cluster_list, distance_list = SASFileIO.loadDamclustLogFile(filename)

                for cluster in cluster_list:
                    if cluster.rep_model not in target_filenames:
                        name, ext = os.path.splitext(cluster.rep_model)
                        target_filenames.append(cluster.rep_model)
                        target_filenames.append('{}-avr{}'.format(name, self.model_ext))
                        target_filenames.append('{}-flt{}'.format(name, self.model_ext))

            if ('damaver' not in self.dammif_ids and 'refine' not in self.dammif_ids
                and 'damclust' not in self.dammif_ids):
                target_filenames.extend(['{}_{:02d}-1{}'.format(prefix, run, self.model_ext)
                    for run in range(1, nruns+1)])

            supcomb_q = queue.Queue()
            read_semaphore = threading.BoundedSemaphore(1)

            wx.CallAfter(self.status.AppendText, 'Starting Alignment\n')

            for target in target_filenames:
                if self.abort_event.is_set():
                    wx.CallAfter(self.sup_window.AppendText, 'Aborted!\n')
                    return

                msg = 'SUPCOMB started for {}\n\n'.format(target)
                wx.CallAfter(sup_window.AppendText, msg)

                sup_proc = SASCalc.runSupcomb(template, target, path,
                    self.raw_settings.get('ATSASDir'), symmetry=symmetry,
                    mode=mode)

                if sup_proc is None:
                    msg  = ('SUPCOMB failed to start for target file '
                        '{}'.format(target))
                    wx.CallAfter(sup_window.AppendText, msg)

                else:
                    readout_t = threading.Thread(target=self.enqueue_output,
                        args=(sup_proc, supcomb_q, read_semaphore))
                    readout_t.daemon = True
                    readout_t.start()


                    #Send the damaver output to the screen.
                    while sup_proc.poll() is None:
                        if self.abort_event.is_set():
                            sup_proc.terminate()
                            wx.CallAfter(sup_window.AppendText, '\nAborted!')
                        try:
                            new_text = supcomb_q.get_nowait()
                            new_text = new_text[0]

                            wx.CallAfter(sup_window.AppendText, new_text)

                        except queue.Empty:
                            pass
                        time.sleep(0.001)

                    if not self.abort_event.is_set():
                        time.sleep(2)
                        with read_semaphore: #see if there's any last data that we missed
                            while True:
                                try:
                                    new_text = supcomb_q.get_nowait()
                                    new_text = new_text[0]

                                    if new_text != '':
                                        wx.CallAfter(sup_window.AppendText, new_text)

                                except queue.Empty:
                                    break

                            new_text = sup_proc.stdout.read()

                            if not isinstance(new_text, str):
                                new_text = str(new_text, encoding='UTF-8')

                            if new_text != '':
                                wx.CallAfter(sup_window.AppendText, new_text)

                        name, ext = os.path.splitext(target)
                        sup_name = '{}_aligned{}'.format(name, ext)

                        if os.path.exists(os.path.join(path, sup_name)):
                            msg = '\nSUPCOMB finished for {}\n\n'.format(target)
                            wx.CallAfter(sup_window.AppendText, msg)
                        else:
                            msg = '\nSUPCOMB failed for {}\n\n'.format(target)
                            wx.CallAfter(sup_window.AppendText, msg)

            wx.CallAfter(self.status.AppendText, 'Finished Alignment\n')
            wx.CallAfter(self.finishedProcessing)

    def enqueue_output(self, proc, queue, read_semaphore):
        #Solution for non-blocking reads adapted from stack overflow
        #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python

        with read_semaphore:
            out = proc.stdout
            line = ''
            line2=''
            while proc.poll() is None:
                line = out.read(1)

                if not isinstance(line, str):
                    line = str(line, encoding='UTF-8')

                line2+=line
                if line == '\n':
                    queue.put_nowait([line2])
                    line2=''
                time.sleep(0.00001)

            line = out.read(1)

            if not isinstance(line, str):
                line = str(line, encoding='UTF-8')

            line2 += line
            queue.put_nowait([line2])

    def onDammifTimer(self, evt):
        dammif_finished = False

        done_list = [False for i in range(len(self.threads))]
        for i in range(len(self.threads)):
            if not self.threads[i].is_alive():
                done_list[i] = True
        if np.all(done_list):
            dammif_finished = True


        if dammif_finished:
            self.dammif_timer.Stop()

            if 'damaver' in self.dammif_ids:
                path_window = wx.FindWindowById(self.ids['save'], self)
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'], self)
                prefix = prefix_window.GetValue()
                prefix = prefix.replace(' ', '_')

                t = threading.Thread(target = self.runDamaver, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            elif 'damclust' in self.dammif_ids:
                path_window = wx.FindWindowById(self.ids['save'], self)
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'], self)
                prefix = prefix_window.GetValue()
                prefix = prefix.replace(' ', '_')

                t = threading.Thread(target = self.runDamclust, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            elif 'align' in self.dammif_ids:
                path_window = wx.FindWindowById(self.ids['save'], self)
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'], self)
                prefix = prefix_window.GetValue()
                prefix = prefix.replace(' ', '_')

                t = threading.Thread(target = self.runSupcomb, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            else:
                wx.CallAfter(self.finishedProcessing)


    def finishedProcessing(self):
        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                wx.FindWindowById(self.ids[key], self).Enable()
            elif key == 'abort':
                wx.FindWindowById(self.ids[key], self).Disable()

        wx.CallAfter(self.status.AppendText, 'Finished Processing')

        #Now tell the
        #Get user settings on number of runs, save location, etc
        damaver_window = wx.FindWindowById(self.ids['damaver'], self)
        damaver = damaver_window.GetValue()

        damclust_window = wx.FindWindowById(self.ids['damclust'], self)
        damclust = damclust_window.GetValue()

        prefix_window = wx.FindWindowById(self.ids['prefix'], self)
        prefix = prefix_window.GetValue()
        prefix = prefix.replace(' ', '_')

        path_window = wx.FindWindowById(self.ids['save'], self)
        path = path_window.GetValue()

        nruns_window = wx.FindWindowById(self.ids['runs'], self)
        nruns = int(nruns_window.GetValue())

        refine_window = wx.FindWindowById(self.ids['refine'], self)
        refine = refine_window.GetValue()

        settings = {'damaver'   : damaver,
                    'damclust'  : damclust,
                    'prefix'    : prefix,
                    'path'      : path,
                    'runs'      : nruns,
                    'refine'    : refine,
                    }

        if not damaver_window.GetValue():
           refine_window.Disable()

        self.main_frame.sleep_inhibit.off()

        wx.CallAfter(self.dammif_frame.ResultsPanel.updateResults, settings)

    def _onAdvancedButton(self, evt):
        self.main_frame.showOptionsDialog(focusHead='DAMMIF/N')

    def onCheckBox(self,evt):
        refine = wx.FindWindowById(self.ids['refine'], self)

        if evt.GetId() == self.ids['damaver'] and not evt.IsChecked():
            refine.Disable()
            refine.SetValue(False)

        elif evt.GetId() == self.ids['damaver'] and evt.IsChecked():
            refine.Enable()



    def updateDAMMIFSettings(self):
        self.dammif_settings = {'mode'              : self.raw_settings.get('dammifMode'),
                                'unit'              : self.raw_settings.get('dammifUnit'),
                                'sym'               : self.raw_settings.get('dammifSymmetry'),
                                'anisometry'        : self.raw_settings.get('dammifAnisometry'),
                                'omitSolvent'       : self.raw_settings.get('dammifOmitSolvent'),
                                'chained'           : self.raw_settings.get('dammifChained'),
                                'constant'          : self.raw_settings.get('dammifConstant'),
                                'maxBead'           : self.raw_settings.get('dammifMaxBeadCount'),
                                'radius'            : self.raw_settings.get('dammifDummyRadius'),
                                'harmonics'         : self.raw_settings.get('dammifSH'),
                                'propFit'           : self.raw_settings.get('dammifPropToFit'),
                                'curveWeight'       : self.raw_settings.get('dammifCurveWeight'),
                                'seed'              : self.raw_settings.get('dammifRandomSeed'),
                                'maxSteps'          : self.raw_settings.get('dammifMaxSteps'),
                                'maxIters'          : self.raw_settings.get('dammifMaxIters'),
                                'maxSuccess'        : self.raw_settings.get('dammifMaxStepSuccess'),
                                'minSuccess'        : self.raw_settings.get('dammifMinStepSuccess'),
                                'TFactor'           : self.raw_settings.get('dammifTFactor'),
                                'RgWeight'          : self.raw_settings.get('dammifRgPen'),
                                'cenWeight'         : self.raw_settings.get('dammifCenPen'),
                                'looseWeight'       : self.raw_settings.get('dammifLoosePen'),
                                'initialDAM'        : self.raw_settings.get('damminInitial'),
                                'knots'             : self.raw_settings.get('damminKnots'),
                                'damminConstant'    : self.raw_settings.get('damminConstant'),
                                'diameter'          : self.raw_settings.get('damminDiameter'),
                                'packing'           : self.raw_settings.get('damminPacking'),
                                'coordination'      : self.raw_settings.get('damminCoordination'),
                                'disconWeight'      : self.raw_settings.get('damminDisconPen'),
                                'periphWeight'      : self.raw_settings.get('damminPeriphPen'),
                                'damminCurveWeight' : self.raw_settings.get('damminCurveWeight'),
                                'annealSched'       : self.raw_settings.get('damminAnealSched'),
                                'shape'             : self.raw_settings.get('dammifExpectedShape'),
                                }

        mode = wx.FindWindowById(self.ids['mode'], self)
        mode.SetStringSelection(self.dammif_settings['mode'])

        sym = wx.FindWindowById(self.ids['sym'], self)
        sym.SetStringSelection(self.dammif_settings['sym'])

        anisometry = wx.FindWindowById(self.ids['anisometry'], self)
        anisometry.SetStringSelection(self.dammif_settings['anisometry'])

        procs = wx.FindWindowById(self.ids['procs'], self)
        procs.SetSelection(1)

        damaver = wx.FindWindowById(self.ids['damaver'], self)
        damaver.SetValue(self.raw_settings.get('dammifDamaver'))

        damclust = wx.FindWindowById(self.ids['damclust'], self)
        damclust.SetValue(self.raw_settings.get('dammifDamclust'))

        prefix = wx.FindWindowById(self.ids['prefix'], self)
        prefix.SetValue(os.path.splitext(self.filename)[0])

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        save = wx.FindWindowById(self.ids['save'], self)
        save.SetValue(path)

        nruns = wx.FindWindowById(self.ids['runs'], self)
        nruns.SetValue(str(self.raw_settings.get('dammifReconstruct')))

        refine = wx.FindWindowById(self.ids['refine'], self)

        if refine.IsEnabled:
            refine.SetValue(self.raw_settings.get('dammifRefine'))

        program = wx.FindWindowById(self.ids['program'], self)
        program.SetStringSelection(self.raw_settings.get('dammifProgram'))

    def Close(self, event):

        process_finished = True

        if self.dammif_timer.IsRunning():
            process_finished = False

        if process_finished:
            done_list = [False for i in range(len(self.threads))]

            if len(done_list) > 0:
                for i in range(len(self.threads)):
                    if not self.threads[i].is_alive():
                        done_list[i] = True
                if not np.all(done_list):
                    process_finished = False

        if not process_finished and event.CanVeto():
            msg = ("Warning: DAMMIF/N, DAMAVER, or DAMCLUST is still "
                "running. Closing this window will abort the currently "
                "running processes. Do you want to continue closing the "
                "window?")
            dlg = wx.MessageDialog(self.main_frame, msg, "Abort DAMMIF/DAMMIN/DAMAVER/DAMCLUST?",
                style = wx.ICON_WARNING | wx.YES_NO)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            if proceed == wx.ID_YES:
                self.abort_event.set()

                self.main_frame.sleep_inhibit.off()

                if self.dammif_timer.IsRunning():
                    self.dammif_timer.Stop()

                aborted = False

                while not aborted:
                    done_list = [False for i in range(len(self.threads))]
                    for i in range(len(self.threads)):
                        if not self.threads[i].is_alive():
                            done_list[i] = True
                    if np.all(done_list):
                        aborted = True
                    time.sleep(.1)

                for key in self.ids:
                    if key != 'logbook' and key != 'abort' and key != 'status':
                        wx.FindWindowById(self.ids[key], self).Enable()
                    elif key == 'abort':
                        wx.FindWindowById(self.ids[key], self).Disable()

                self.status.AppendText('Processing Aborted!')

            else:
                event.Veto()

        elif not process_finished:
            #Try to gracefully exit
            self.abort_event.set()

            self.main_frame.sleep_inhibit.off()

            if self.dammif_timer.IsRunning():
                self.dammif_timer.Stop()

            aborted = False

            while not aborted:
                done_list = [False for i in range(len(self.threads))]
                for i in range(len(self.threads)):
                    if not self.threads[i].is_alive():
                        done_list[i] = True
                if np.all(done_list):
                    aborted = True
                time.sleep(.1)

            for key in self.ids:
                if key != 'logbook' and key != 'abort' and key != 'status':
                    wx.FindWindowById(self.ids[key], self).Enable()
                elif key == 'abort':
                    wx.FindWindowById(self.ids[key], self).Disable()

            self.status.AppendText('Processing Aborted!')

class DammifResultsPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.parent = parent

        self.dammif_frame = parent.GetParent().GetParent()

        self.manip_item = manip_item

        self.iftm = iftm

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.ids = {'ambiCats'      : self.NewControlId(),
                    'ambiScore'     : self.NewControlId(),
                    'ambiEval'      : self.NewControlId(),
                    'nsdMean'       : self.NewControlId(),
                    'nsdStdev'      : self.NewControlId(),
                    'nsdInc'        : self.NewControlId(),
                    'nsdTot'        : self.NewControlId(),
                    'clustNum'      : self.NewControlId(),
                    'clustDescrip'  : self.NewControlId(),
                    'clustDist'     : self.NewControlId(),
                    'models'        : self.NewControlId(),
                    'model_sum'     : self.NewControlId(),
                    'res'           : self.NewControlId(),
                    'resErr'        : self.NewControlId(),
                    'resUnit'       : self.NewControlId(),
                    }

        self.topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(self.topsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        for i in range(self.models.GetPageCount()):
            page = self.models.GetPage(i)

            if isinstance(page, DammifPlotPanel):
                page.updateColors()

        self.models.SetActiveTabColour(RAWGlobals.tab_color)

    def _createLayout(self, parent):
        ambi_box = wx.StaticBox(parent, wx.ID_ANY, 'Ambimeter')
        self.ambi_sizer = wx.StaticBoxSizer(ambi_box, wx.VERTICAL)

        match_text = wx.StaticText(ambi_box, wx.ID_ANY, 'Compatible shape categories:')
        match_ctrl = wx.TextCtrl(ambi_box, self.ids['ambiCats'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        score_text = wx.StaticText(ambi_box, -1, 'Ambiguity score:')
        score_ctrl = wx.TextCtrl(ambi_box, self.ids['ambiScore'], '',
            size = self._FromDIP((60, -1)), style = wx.TE_READONLY)

        eval_text = wx.StaticText(ambi_box, -1, 'AMBIMETER says:')
        eval_ctrl = wx.TextCtrl(ambi_box, self.ids['ambiEval'], '',
            size = self._FromDIP((300, -1)), style = wx.TE_READONLY)

        ambi_subsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer1.Add(match_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer1.Add(match_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        ambi_subsizer1.Add(score_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(8))
        ambi_subsizer1.Add(score_ctrl, 0, wx.LEFT| wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))

        ambi_subsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer2.Add(eval_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer2.Add(eval_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))

        self.ambi_sizer.Add(ambi_subsizer1, 0)
        self.ambi_sizer.Add(ambi_subsizer2, 0, wx.TOP, border=self._FromDIP(5))


        nsd_box = wx.StaticBox(parent, wx.ID_ANY, 'Normalized Spatial Discrepancy')
        self.nsd_sizer = wx.StaticBoxSizer(nsd_box, wx.HORIZONTAL)

        mean_text = wx.StaticText(nsd_box, wx.ID_ANY, 'Mean NSD:')
        mean_ctrl = wx.TextCtrl(nsd_box, self.ids['nsdMean'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        stdev_text = wx.StaticText(nsd_box, wx.ID_ANY, 'Stdev. NSD:')
        stdev_ctrl = wx.TextCtrl(nsd_box, self.ids['nsdStdev'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        inc_text = wx.StaticText(nsd_box, wx.ID_ANY, 'DAMAVER included:')
        inc_ctrl = wx.TextCtrl(nsd_box, self.ids['nsdInc'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)
        inc_text2 = wx.StaticText(nsd_box, wx.ID_ANY, 'of')
        total_ctrl = wx.TextCtrl(nsd_box, self.ids['nsdTot'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        self.nsd_sizer.Add(mean_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.nsd_sizer.Add(mean_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.nsd_sizer.Add(stdev_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(8))
        self.nsd_sizer.Add(stdev_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.nsd_sizer.Add(inc_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(8))
        self.nsd_sizer.Add(inc_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.nsd_sizer.Add(inc_text2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.nsd_sizer.Add(total_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))


        res_box = wx.StaticBox(parent, wx.ID_ANY, 'Reconstruction Resolution (SASRES)')
        self.res_sizer = wx.StaticBoxSizer(res_box, wx.HORIZONTAL)

        res_text = wx.StaticText(res_box, wx.ID_ANY, 'Ensemble Resolution:')
        res_ctrl = wx.TextCtrl(res_box, self.ids['res'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        reserr_text = wx.StaticText(res_box, wx.ID_ANY, '+/-')
        reserr_ctrl = wx.TextCtrl(res_box, self.ids['resErr'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        resunit_ctrl = wx.TextCtrl(res_box, self.ids['resUnit'], '',
            size=self._FromDIP((100,-1)), style=wx.TE_READONLY)

        self.res_sizer.Add(res_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.res_sizer.Add(res_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.res_sizer.Add(reserr_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.res_sizer.Add(reserr_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.res_sizer.Add(resunit_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(4))


        clust_box = wx.StaticBox(parent, wx.ID_ANY, 'Clustering')
        self.clust_sizer = wx.StaticBoxSizer(clust_box, wx.VERTICAL)

        clust_num_text = wx.StaticText(clust_box, wx.ID_ANY, 'Number of clusters:')
        clust_num_ctrl = wx.TextCtrl(clust_box, self.ids['clustNum'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        clust_num_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clust_num_sizer.Add(clust_num_text, 0, wx.ALIGN_CENTER_VERTICAL)
        clust_num_sizer.Add(clust_num_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))

        clust_list1= wx.ListCtrl(clust_box, self.ids['clustDescrip'],
            size=self._FromDIP((-1,150)), style=wx.LC_REPORT)
        clust_list1.InsertColumn(0, 'Cluster')
        clust_list1.InsertColumn(1, 'Isolated')
        clust_list1.InsertColumn(2, 'Rep. Model')
        clust_list1.InsertColumn(3, 'Deviation')

        clust_list2= wx.ListCtrl(clust_box, self.ids['clustDist'],
            size=self._FromDIP((-1,150)), style=wx.LC_REPORT)
        clust_list2.InsertColumn(0, 'Cluster 1')
        clust_list2.InsertColumn(1, 'Cluster 2')
        clust_list2.InsertColumn(2, 'Distance')

        clust_list_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clust_list_sizer.Add(clust_list1, 5, wx.EXPAND)
        clust_list_sizer.Add(clust_list2, 3, wx.LEFT | wx.EXPAND,
            border=self._FromDIP(8))

        self.clust_sizer.Add(clust_num_sizer, 0)
        self.clust_sizer.Add(clust_list_sizer, 0, wx.EXPAND | wx.TOP,
            border=self._FromDIP(5))


        models_box = wx.StaticBox(parent, wx.ID_ANY, 'Models')

        try:
            self.models = flatNB.FlatNotebook(models_box, self.ids['models'],
                agwStyle=flatNB.FNB_NAV_BUTTONS_WHEN_NEEDED|flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)
        except AttributeError:
            self.models = flatNB.FlatNotebook(models_box, self.ids['models'])     #compatability for older versions of wxpython
            self.models.SetWindowStyleFlag(flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)

        self.models.SetActiveTabColour(RAWGlobals.tab_color)
        self.models.DeleteAllPages()

        summary_panel = wx.Panel(self.models)

        models_list = wx.ListCtrl(summary_panel, self.ids['model_sum'],
            size=self._FromDIP((-1,-1)), style=wx.LC_REPORT)
        models_list.InsertColumn(0, 'Model')
        models_list.InsertColumn(1, 'Chi^2')
        models_list.InsertColumn(2, 'Rg')
        models_list.InsertColumn(3, 'Dmax')
        models_list.InsertColumn(4, 'Excluded Vol.')
        models_list.InsertColumn(5, 'Est. Protein MW.')
        models_list.InsertColumn(6, 'Mean NSD')

        if platform.system() == 'Windows':
            models_list.SetColumnWidth(5, -2)
        else:
            models_list.SetColumnWidth(5, self._FromDIP(100))

        mp_sizer = wx.BoxSizer()
        mp_sizer.Add(models_list, 1, flag=wx.EXPAND)
        summary_panel.SetSizer(mp_sizer)

        self.models.AddPage(summary_panel, 'Summary')


        self.models_sizer = wx.StaticBoxSizer(models_box, wx.VERTICAL)
        self.models_sizer.Add(self.models, 1, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.ambi_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.nsd_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.res_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.clust_sizer,0, wx.EXPAND)
        top_sizer.Add(self.models_sizer,1,wx.EXPAND)

        return top_sizer


    def _initSettings(self):
        run_window = self.dammif_frame.RunPanel
        path_window = wx.FindWindowById(run_window.ids['save'], run_window)
        # path = path_window.GetValue()

        self.model_ext = self.dammif_frame.model_ext

        opsys = platform.system()
        if opsys == 'Windows':
            if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'ambimeter.exe')):
                run_ambi = True
            else:
                run_ambi = False
        else:
            if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'ambimeter')):
                run_ambi = True
            else:
                run_ambi = False

        if run_ambi:
            t = threading.Thread(target=self.runAmbimeter)
            t.daemon = True
            t.start()
        else:
            self.topsizer.Hide(self.ambi_sizer, recursive=True)

        self.topsizer.Hide(self.nsd_sizer, recursive=True)
        self.topsizer.Hide(self.clust_sizer, recursive=True)
        self.topsizer.Hide(self.res_sizer, recursive=True)
        # self.topsizer.Hide(self.models_sizer, recursive=True)

    def runAmbimeter(self):
        standard_paths = wx.StandardPaths.Get()
        tempdir = standard_paths.GetTempDir()

        outname = tempfile.NamedTemporaryFile(dir=tempdir).name

        while os.path.isfile(outname):
            outname = tempfile.NamedTemporaryFile(dir=tempdir).name

        outname = os.path.split(outname)[-1] + '.out'

        if self.main_frame.OnlineControl.isRunning() and tempdir == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        SASFileIO.writeOutFile(self.iftm, os.path.join(tempdir, outname))

        ambi_settings = {'sRg' :'4',
                        'files':'None'
                        }

        try:
            output = SASCalc.runAmbimeter(outname, 'temp', ambi_settings,
                tempdir, self.raw_settings.get('ATSASDir'))

        except SASExceptions.NoATSASError as e:
            wx.CallAfter(self.main_frame.showMessageDialog, self, str(e),
                "Error running Ambimeter", wx.ICON_ERROR|wx.OK)
            os.remove(os.path.join(tempdir, outname))
            return

        os.remove(os.path.join(tempdir, outname))

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        wx.CallAfter(cats_window.SetValue, output[0])
        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        wx.CallAfter(score_window.SetValue, output[1])
        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        wx.CallAfter(eval_window.SetValue, output[2])

    def getNSD(self, filename):
        mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err, res_unit = SASFileIO.loadDamselLogFile(filename)

        mean_window = wx.FindWindowById(self.ids['nsdMean'], self)
        mean_window.SetValue(mean_nsd)
        stdev_window = wx.FindWindowById(self.ids['nsdStdev'], self)
        stdev_window.SetValue(stdev_nsd)
        inc_window = wx.FindWindowById(self.ids['nsdInc'], self)
        inc_window.SetValue(str(len(include_list)))
        tot_window = wx.FindWindowById(self.ids['nsdTot'], self)
        tot_window.SetValue(str(len(result_dict)))

    def getResolution(self, filename):
        mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err, res_unit = SASFileIO.loadDamselLogFile(filename)

        res_window = wx.FindWindowById(self.ids['res'], self)
        res_window.SetValue(res)
        reserr_window = wx.FindWindowById(self.ids['resErr'], self)
        reserr_window.SetValue(res_err)
        unit_window = wx.FindWindowById(self.ids['resUnit'], self)
        unit_window.SetValue(res_unit)
        tot_window = wx.FindWindowById(self.ids['nsdTot'], self)
        tot_window.SetValue(str(len(result_dict)))

    def getClust(self, filename):
        cluster_list, distance_list = SASFileIO.loadDamclustLogFile(filename)

        num_window = wx.FindWindowById(self.ids['clustNum'], self)
        num_window.SetValue(str(len(cluster_list)))

        clist = wx.FindWindowById(self.ids['clustDescrip'])
        clist.DeleteAllItems()
        for cluster in cluster_list:
            if cluster.dev == -1:
                isolated = 'Y'
                dev = ''
            else:
                isolated = 'N'
                dev = str(cluster.dev)

            clist.Append((str(cluster.num), isolated, cluster.rep_model, dev))

        dlist = wx.FindWindowById(self.ids['clustDist'])
        dlist.DeleteAllItems()
        for dist_data in distance_list:
            dlist.Append(list(map(str, dist_data)))

    def getModels(self, settings):
        while self.models.GetPageCount() > 1:
            last_page = self.models.GetPageText(self.models.GetPageCount()-1)
            if last_page != 'Summary':
                self.models.DeletePage(self.models.GetPageCount()-1)
            else:
                self.models.DeletePage(self.models.GetPageCount()-2)

        models_window = wx.FindWindowById(self.ids['model_sum'])
        models_window.DeleteAllItems()

        path = settings['path']
        prefix = settings['prefix']

        model_list = []

        if settings['damaver'] and int(settings['runs']) > 1:
            name = prefix+'_damsel.log'
            filename = os.path.join(path, name)
            mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err, res_unit = SASFileIO.loadDamselLogFile(filename)

            name = prefix+'_damsup.log'
            filename = os.path.join(path, name)
            model_data, rep_model = SASFileIO.loadDamsupLogFile(filename)

        for num in range(1,int(settings['runs'])+1):
            fprefix = '%s_%s' %(prefix, str(num).zfill(2))
            dam_name = os.path.join(path, fprefix+'-1'+self.model_ext)
            fir_name = os.path.join(path, fprefix+'.fir')

            sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)

            chisq = sasm.getParameter('counters')['Chi_squared']

            atoms, header, model_data = self._loadModelFile(dam_name)
            model_data['chisq'] = chisq

            if settings['damaver'] and int(settings['runs']) > 1:
                model_data['nsd'] = result_dict[os.path.basename(dam_name)][-1]
                if result_dict[os.path.basename(dam_name)][0].lower() == 'include':
                    include = True
                else:
                    include = False

                model_data['include'] = include

            model_list.append([num, model_data, atoms])

            plot_panel = DammifPlotPanel(self.models, sasm, fit_sasm, chisq)
            self.models.AddPage(plot_panel, str(num))

        if settings['damaver'] and int(settings['runs']) > 1:
            damaver_name = os.path.join(path, prefix+'_damaver'+self.model_ext)
            damfilt_name = os.path.join(path, prefix+'_damfilt'+self.model_ext)

            atoms, header, model_data = self._loadModelFile(damaver_name)
            model_list.append(['damaver', model_data, atoms])

            atoms, header, model_data = self._loadModelFile(damfilt_name)
            model_list.append(['damfilt', model_data, atoms])

        if settings['refine'] and int(settings['runs']) > 1:
            dam_name = os.path.join(path, 'refine_'+prefix+'-1'+self.model_ext)
            fir_name = os.path.join(path, 'refine_'+prefix+'.fir')
            sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
            chisq = sasm.getParameter('counters')['Chi_squared']

            atoms, header, model_data = self._loadModelFile(dam_name)
            model_data['chisq'] = chisq

            model_list.append(['refine', model_data, atoms])

            plot_panel = DammifPlotPanel(self.models, sasm, fit_sasm, chisq)
            self.models.AddPage(plot_panel, 'Refined')

        for item in model_list:
            models_window.Append((item[0], item[1]['chisq'], item[1]['rg'],
                item[1]['dmax'], item[1]['excluded_volume'], item[1]['mw'],
                item[1]['nsd']))

            if settings['damaver'] and int(settings['runs']) > 1:
                if not item[1]['include'] and item[0]!='damaver' and item[0]!='damfilt' and item[0]!='refine':
                    index = models_window.GetItemCount()-1
                    models_window.SetItemTextColour(index, 'red')

                if item[0] == int('-'.join(rep_model.split('_')[-1].split('-')[:-1])):
                    index = models_window.GetItemCount()-1
                    models_window.SetItemTextColour(index, 'blue')

        return model_list

    def updateResults(self, settings):
        #In case we ran a different setting a second time, without closing the window
        self.topsizer.Hide(self.nsd_sizer, recursive=True)
        self.topsizer.Hide(self.res_sizer, recursive=True)
        self.topsizer.Hide(self.clust_sizer, recursive=True)

        if settings['damaver'] and int(settings['runs']) > 1:
            self.topsizer.Show(self.nsd_sizer, recursive=True)
            name = settings['prefix']+'_damsel.log'
            filename = os.path.join(settings['path'],name)
            self.getNSD(filename)
            self.getResolution(filename)

            if wx.FindWindowById(self.ids['res'], self).GetValue():
                self.topsizer.Show(self.res_sizer, recursive=True)

        if settings['damclust'] and int(settings['runs']) > 1:
            self.topsizer.Show(self.clust_sizer, recursive=True)
            name = settings['prefix']+'_damclust.log'
            filename = os.path.join(settings['path'],name)
            self.getClust(filename)

        model_list = self.getModels(settings)

        self.Layout()

        self.parent.SetSelection(1)

        self.dammif_frame.ViewerPanel.updateResults(model_list)

        self._saveResults()

    def _saveResults(self):
        nsd_data = []
        res_data = []
        clust_num = 0
        clist_data = []
        dlist_data = []
        ambi_data = []

        models_list = wx.FindWindowById(self.ids['model_sum'])
        cdb = wx.ColourDatabase()

        if self.topsizer.IsShown(self.nsd_sizer):
            nsd_mean = wx.FindWindowById(self.ids['nsdMean']).GetValue()
            nsd_stdev = wx.FindWindowById(self.ids['nsdStdev']).GetValue()
            nsd_inc = wx.FindWindowById(self.ids['nsdInc']).GetValue()
            nsd_tot = wx.FindWindowById(self.ids['nsdTot']).GetValue()

            rep_item = ''
            ex_items = []
            for i in range(models_list.GetItemCount()):
                if cdb.FindName(models_list.GetItemTextColour(i)).lower() == 'blue':
                    rep_item = models_list.GetItem(i, 0).GetText()
                if cdb.FindName(models_list.GetItemTextColour(i)).lower() == 'red':
                    ex_items.append(models_list.GetItem(i, 0).GetText())


            nsd_data = [('Mean NSD:', nsd_mean),
                ('Stdev. NSD:', nsd_stdev),
                ('DAMAVER Included:', nsd_inc, 'of', nsd_tot),
                ('Representative model:', rep_item),
                ]

            if ex_items:
                nsd_data.append(('Excluded Models:', ' ,'.join(ex_items)))

        if self.topsizer.IsShown(self.res_sizer):
            res = wx.FindWindowById(self.ids['res']).GetValue()
            res_err = wx.FindWindowById(self.ids['resErr']).GetValue()
            res_unit = wx.FindWindowById(self.ids['resUnit']).GetValue()
            res_data = [('Ensemble resolution:', res, '+/-', res_err, res_unit)]

        if self.topsizer.IsShown(self.clust_sizer):
            clust_num = ('Number of clusters:', wx.FindWindowById(self.ids['clustNum']).GetValue())
            clust_list = wx.FindWindowById(self.ids['clustDescrip'])
            dist_list = wx.FindWindowById(self.ids['clustDist'])


            clist_data = [[] for k in range(clust_list.GetItemCount())]
            for i in range(clust_list.GetItemCount()):
                item_data = [[] for k in range(clust_list.GetColumnCount())]
                for j in range(clust_list.GetColumnCount()):
                    item = clust_list.GetItem(i, j)
                    data = item.GetText()
                    item_data[j] = data

                clist_data[i] = item_data

            dlist_data = [[] for k in range(dist_list.GetItemCount())]
            for i in range(dist_list.GetItemCount()):
                item_data = [[] for k in range(dist_list.GetColumnCount())]
                for j in range(dist_list.GetColumnCount()):
                    item = dist_list.GetItem(i, j)
                    data = item.GetText()
                    item_data[j] = data

                dlist_data[i] = item_data

        model_data = [[] for k in range(models_list.GetItemCount())]
        for i in range(models_list.GetItemCount()):
            item_data = [[] for k in range(models_list.GetColumnCount())]
            for j in range(models_list.GetColumnCount()):
                item = models_list.GetItem(i, j)
                data = item.GetText()
                item_data[j] = data

            model_data[i] = item_data

        if self.topsizer.IsShown(self.ambi_sizer):
            ambi_cats = wx.FindWindowById(self.ids['ambiCats']).GetValue()
            ambi_score = wx.FindWindowById(self.ids['ambiScore']).GetValue()
            ambi_eval = wx.FindWindowById(self.ids['ambiEval']).GetValue()
            ambi_data = [('Compatible shape categories:', ambi_cats),
                        ('Ambiguity score:', ambi_score), ('AMBIMETER says:', ambi_eval)]

        input_file = wx.FindWindowById(self.dammif_frame.RunPanel.ids['fname']).GetValue()
        output_prefix = wx.FindWindowById(self.dammif_frame.RunPanel.ids['prefix']).GetValue()
        output_directory = wx.FindWindowById(self.dammif_frame.RunPanel.ids['save']).GetValue()
        reconst_prog = wx.FindWindowById(self.dammif_frame.RunPanel.ids['program']).GetStringSelection()
        mode = wx.FindWindowById(self.dammif_frame.RunPanel.ids['mode']).GetStringSelection()
        symmetry = wx.FindWindowById(self.dammif_frame.RunPanel.ids['sym']).GetStringSelection()
        anisometry = wx.FindWindowById(self.dammif_frame.RunPanel.ids['anisometry']).GetStringSelection()
        tot_recons = wx.FindWindowById(self.dammif_frame.RunPanel.ids['runs']).GetValue()
        damaver = wx.FindWindowById(self.dammif_frame.RunPanel.ids['damaver']).IsChecked()
        refine = wx.FindWindowById(self.dammif_frame.RunPanel.ids['refine']).IsChecked()
        damclust = wx.FindWindowById(self.dammif_frame.RunPanel.ids['damclust']).IsChecked()

        setup_data = [('Input file:', input_file), ('Output prefix:', output_prefix),
                    ('Output directory:', output_directory), ('Program used:', reconst_prog),
                    ('Mode:', mode), ('Symmetry:', symmetry), ('Anisometry:', anisometry),
                    ('Total number of reconstructions:', tot_recons),
                    ('Used DAMAVER:', damaver), ('Refined with DAMMIN:', refine),
                    ('Used DAMCLUST:', damclust),
                    ]

        models_nb = wx.FindWindowById(self.ids['models'], self)

        model_plots = []

        for i in range(models_nb.GetPageCount()):
            page = models_nb.GetPage(i)
            if models_nb.GetPageText(i) != 'Summary':
                figures = page.figures
                model = models_nb.GetPageText(i)
                model_plots.append((model, figures))

        name = output_prefix

        save_path = os.path.join(output_directory, name + '_dammif_results.csv')

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving DAMMIF/N data', 0)

        SASFileIO.saveDammixData(save_path, ambi_data, nsd_data, res_data, clust_num,
            clist_data, dlist_data, model_data, setup_data, model_plots)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)

    def _loadModelFile(self, filename):
        if self.model_ext == '.pdb':
            results = SASFileIO.loadPDBFile(filename)
        elif self.model_ext == '.cif':
            results = SASFileIO.loadmmCIFFile(filename)

        return results

class DammifPlotPanel(wx.Panel):

    def __init__(self, parent, sasm, fit_sasm, chisq):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BG_STYLE_SYSTEM
            |wx.RAISED_BORDER)

        self.sasm = sasm
        self.fit_sasm = fit_sasm
        self.chisq = chisq
        self.figures = []

        main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = main_frame.raw_settings
        self.norm_residuals = self.raw_settings.get('normalizedResiduals')

        self.canvas = self.createPlot()

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.canvas, 1, wx.GROW)

        self.SetSizer(sizer)

    def updateColors(self):
        color = SASUtils.update_mpl_style()
        # self.ax1_hline.set_color(color)
        self.canvas.draw()

    def createPlot(self):
        color = SASUtils.update_mpl_style()

        fig = Figure((5,4), 75)
        self.figures.append(fig)

        canvas = FigureCanvasWxAgg(self, -1, fig)

        gridspec = matplotlib.gridspec.GridSpec(2, 1, height_ratios=[1, 0.3])

        q = self.sasm.getQ()
        i = self.sasm.getI()
        i_fit = self.fit_sasm.getI()
        err = self.sasm.getErr()

        residual = i - i_fit
        if self.norm_residuals:
            residual = residual/err

        ax0 = fig.add_subplot(gridspec[0])
        ax0.semilogy(q, i, 'bo')
        ax0.semilogy(q, i_fit, 'r')
        ax0.set_xlabel('q')
        ax0.set_ylabel('I(q)')

        ax1 = fig.add_subplot(gridspec[1])
        self.ax1_hline = ax1.axhline(0, color=color, linewidth=1.0)
        ax1.plot(q, residual, 'bo')
        ax1.set_xlabel('q')
        if self.norm_residuals:
            ax1.set_ylabel('$\Delta I(q)/\sigma (q)$')
        else:
            ax1.set_ylabel('$\Delta I(q)$')

        # canvas.SetBackgroundColour('white')
        fig.subplots_adjust(left = 0.1, bottom = 0.12, right = 0.95, top = 0.95,
            hspace=0.25)
        # fig.set_facecolor('white')

        canvas.draw()

        return canvas


class DammifViewerPanel(wx.Panel):

    def __init__(self, parent):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY)
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY)

        self.parent = parent

        self.ids = {'models'    : self.NewControlId(),
                    }

        self.model_dict = None

        top_sizer = self._createLayout(self)

        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        color = SASUtils.update_mpl_style()
        self.canvas.draw()

    def _createLayout(self, parent):
        ctrls_box = wx.StaticBox(parent, wx.ID_ANY, 'Viewer Controls')

        model_text = wx.StaticText(ctrls_box, wx.ID_ANY, 'Model to display:')
        model_choice = wx.Choice(ctrls_box, self.ids['models'])
        model_choice.Bind(wx.EVT_CHOICE, self.onChangeModels)

        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_sizer.Add(model_text, 0)
        model_sizer.Add(model_choice, 0, wx.LEFT, border=self._FromDIP(3))

        ctrls_sizer = wx.StaticBoxSizer(ctrls_box, wx.VERTICAL)
        ctrls_sizer.Add(model_sizer, 0)


        self.fig = Figure(dpi=75, tight_layout=True)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.subplot = self.fig.add_subplot(1,1,1, projection='3d')
        self.subplot.grid(False)
        self.subplot.set_axis_off()

        # self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        # self.toolbar.Realize()

        layout_sizer = wx.BoxSizer(wx.VERTICAL)
        layout_sizer.Add(ctrls_sizer, 0, wx.BOTTOM | wx.EXPAND,
            border=self._FromDIP(5))
        layout_sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)
        # sizer.Add(self.toolbar, 0, wx.GROW)

        self.canvas.draw()

        return layout_sizer

    def _plotModel(self, atoms, radius):
        self.subplot.clear()
        self.subplot.grid(False)
        self.subplot.set_axis_off()

        scale = (float(radius)/1.25)**2

        self.subplot.scatter(atoms[:,0], atoms[:,1], atoms[:,2], s=20*scale,
            alpha=.9, edgecolors='k')

        self.canvas.draw()

    def onChangeModels(self, evt):
        model = evt.GetString()

        self._plotModel(self.model_dict[model][1], self.model_dict[model][0]['atom_radius'])


    def updateResults(self, model_list):
        self.model_dict = collections.OrderedDict()

        for item in model_list:
            self.model_dict[str(item[0])] = [item[1], item[2]]

        model_choice = wx.FindWindowById(self.ids['models'], self)
        model_choice.Set(list(self.model_dict.keys()))

        if 'refine' in self.model_dict:
            self._plotModel(self.model_dict['refine'][1], self.model_dict['refine'][0]['atom_radius'])
            model_choice.SetStringSelection('refine')
        elif 'damfilt' in self.model_dict:
            self._plotModel(self.model_dict['damfilt'][1], self.model_dict['damfilt'][0]['atom_radius'])
            model_choice.SetStringSelection('damfilt')
        elif 'damaver' in self.model_dict:
            self._plotModel(self.model_dict['damaver'][1], self.model_dict['damaver'][0]['atom_radius'])
            model_choice.SetStringSelection('damaver')
        else:
            self._plotModel(self.model_dict['1'][1], self.model_dict['1'][0]['atom_radius'])
            model_choice.SetStringSelection('1')


class DenssFrame(wx.Frame):

    def __init__(self, parent, title, iftm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = (min(750, client_display.Width), min(900, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self.manip_item = manip_item
        self.iftm = iftm
        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.panel = wx.Panel(self)
        self.notebook = wx.Notebook(self.panel, wx.ID_ANY)
        self.RunPanel = DenssRunPanel(self.notebook, self.iftm, self.manip_item)
        self.ResultsPanel = DenssResultsPanel(self.notebook, self.iftm, self.manip_item)
        # self.ViewerPanel = DenssViewerPanel(self.notebook)

        self.notebook.AddPage(self.RunPanel, 'Run')
        self.notebook.AddPage(self.ResultsPanel, 'Results')
        # self.notebook.AddPage(self.ViewerPanel, 'Viewer')

        sizer = self._createLayout(self.panel)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.notebook, 1, wx.EXPAND)
        top_sizer.Add(sizer, 0, wx.ALIGN_CENTER | wx.ALL, self._FromDIP(5))

        self.panel.SetSizer(top_sizer)

        self.panel.Layout()
        self.Layout()
        self.SendSizeEvent()
        self.panel.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.notebook.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + self._FromDIP(20)
                self.SetSize(self._FromDIP(size))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        self.CenterOnParent()

        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.ResultsPanel.updateColors()
        # self.ViewerPanel.updateColors()

    def _createLayout(self, parent):
        close_button = wx.Button(parent, -1, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer =  wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(info_button, 0, wx.RIGHT, self._FromDIP(5))
        button_sizer.Add(close_button, 0)

        return button_sizer

    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = ('In addition to citing the RAW paper:\n If you use Denss '
        'in your work please cite the paper given here:\n'
        'https://www.nature.com/articles/nmeth.4581\n\n'
        'For more information about DENSS see:\n'
        'https://www.tdgrant.com/denss/')
        wx.MessageBox(str(msg), "How to cite Denss", style = wx.ICON_INFORMATION | wx.OK)

    def updateDenssSettings(self):
        self.RunPanel.updateDenssSettings()

    def OnClose(self, event):
        self.RunPanel.Close(event)

        if event.GetVeto():
            return
        else:
            self.Destroy()


class DenssRunPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.parent = parent

        self.denss_frame = parent.GetParent().GetParent()

        self.manip_item = manip_item

        self.iftm = iftm

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.infodata = {}

        self.ids = {'runs'          : self.NewControlId(),
                    'procs'         : self.NewControlId(),
                    'status'        : self.NewControlId(),
                    'average'       : self.NewControlId(),
                    'save'          : self.NewControlId(),
                    'prefix'        : self.NewControlId(),
                    'logbook'       : self.NewControlId(),
                    'start'         : self.NewControlId(),
                    'abort'         : self.NewControlId(),
                    'changedir'     : self.NewControlId(),
                    'fname'         : self.NewControlId(),
                    'mode'          : self.NewControlId(),
                    'electrons'     : self.NewControlId(),
                    'refine'        : self.NewControlId(),
                    'sym_on'        : self.NewControlId(),
                    'ncs'           : self.NewControlId(),
                    'ncsAxis'       : self.NewControlId(),
                    'ncsType'       : self.NewControlId(),
                    'align'         : self.NewControlId(),
                    'align_file'    : self.NewControlId(),
                    'align_file_btn': self.NewControlId(),
                    }

        self.threads_finished = []

        if platform.system() == 'Darwin' and six.PY3:
            self.single_proc = True
        else:
            self.single_proc = False

        topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(topsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.logbook.SetActiveTabColour(RAWGlobals.tab_color)

    def _createLayout(self, parent):

        file_box = wx.StaticBox(parent, -1, 'Filename')

        file_ctrl = wx.TextCtrl(file_box, self.ids['fname'], self.filename,
            size=self._FromDIP((150, -1)), style=wx.TE_READONLY)

        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        file_sizer.Add(file_ctrl, 2, wx.LEFT | wx.RIGHT | wx.EXPAND,
            border=self._FromDIP(5))
        file_sizer.AddStretchSpacer(1)

        settings_box = wx.StaticBox(parent, -1, 'Settings')

        savedir_text = wx.StaticText(settings_box, -1, 'Output directory :')
        savedir_ctrl = wx.TextCtrl(settings_box, self.ids['save'], '',
            size=self._FromDIP((350, -1)))

        try:
            savedir_ctrl.AutoCompleteDirectories() #compatability for older versions of wxpython
        except AttributeError as e:
            print(e)

        savedir_button = wx.Button(settings_box, self.ids['changedir'], 'Select')
        savedir_button.Bind(wx.EVT_BUTTON, self.onChangeDirectoryButton)

        dir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dir_sizer.Add(savedir_ctrl, proportion=1, border=self._FromDIP(2),
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        dir_sizer.Add(savedir_button, flag=wx.ALIGN_CENTER_VERTICAL)

        savedir_sizer = wx.BoxSizer(wx.VERTICAL)
        savedir_sizer.Add(savedir_text, 0, wx.LEFT | wx.RIGHT,
            border=self._FromDIP(2))
        savedir_sizer.Add(dir_sizer, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND,
            border=self._FromDIP(2))


        prefix_text = wx.StaticText(settings_box, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(settings_box, self.ids['prefix'], '',
            size=self._FromDIP((150, -1)))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.LEFT, border=self._FromDIP(5))
        prefix_sizer.Add(prefix_ctrl, 1, wx.LEFT | wx.RIGHT,
            border=self._FromDIP(5))
        prefix_sizer.AddStretchSpacer(1)


        nruns_text = wx.StaticText(settings_box, -1, 'Number of reconstructions :')
        nruns_ctrl = wx.TextCtrl(settings_box, self.ids['runs'], '',
            size=self._FromDIP((60, -1)))
        nruns_ctrl.Bind(wx.EVT_TEXT, self.onRunsText)

        nruns_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nruns_sizer.Add(nruns_text, 0, wx.LEFT, border=self._FromDIP(5))
        nruns_sizer.Add(nruns_ctrl, 0, wx.LEFT | wx.RIGHT,
            border=self._FromDIP(5))


        if self.single_proc:
            nprocs = 1
        else:
            nprocs = multiprocessing.cpu_count()

        nprocs_choices = [str(i) for i in range(nprocs, 0, -1)]
        nprocs_text = wx.StaticText(settings_box, -1, 'Number of simultaneous runs :')
        nprocs_choice = wx.Choice(settings_box, self.ids['procs'], choices = nprocs_choices)

        nprocs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nprocs_sizer.Add(nprocs_text, 0, wx.LEFT, border=self._FromDIP(5))
        nprocs_sizer.Add(nprocs_choice, 0, wx.LEFT | wx.RIGHT,
            border=self._FromDIP(5))


        mode_text = wx.StaticText(settings_box, wx.ID_ANY, 'Mode :')
        mode_ctrl = wx.Choice(settings_box, self.ids['mode'], choices=['Fast', 'Slow', 'Membrane', 'Custom'])

        mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mode_sizer.Add(mode_text, 0, wx.LEFT, border=self._FromDIP(5))
        mode_sizer.Add(mode_ctrl, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(5))


        ne_text = wx.StaticText(settings_box, wx.ID_ANY, 'Total number of electrons (optional) :')
        ne_ctrl = wx.TextCtrl(settings_box, self.ids['electrons'], '',
            size=self._FromDIP((60,-1)))

        ne_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ne_sizer.Add(ne_text, 0, wx.LEFT, border=self._FromDIP(5))
        ne_sizer.Add(ne_ctrl, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(5))

        average_chk = wx.CheckBox(settings_box, self.ids['average'], 'Align and average densities')
        average_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        refine_chk = wx.CheckBox(settings_box, self.ids['refine'], 'Refine average')
        refine_sizer = wx.BoxSizer(wx.HORIZONTAL)
        refine_sizer.AddSpacer(self._FromDIP(20))
        refine_sizer.Add(refine_chk)

        sym_chk = wx.CheckBox(settings_box, self.ids['sym_on'], 'Apply symmetry constraint')
        sym_val = wx.TextCtrl(settings_box, self.ids['ncs'],
            size=self._FromDIP((40, -1)), value='2',
            validator=RAWCustomCtrl.CharValidator('int'))
        sym_axis = wx.Choice(settings_box, self.ids['ncsAxis'],
            choices=['X', 'Y', 'Z'])
        sym_axis.SetStringSelection('X')
        sym_type = wx.Choice(settings_box, self.ids['ncsType'],
            choices=['Cyclical', 'Dihedral'])

        sym_axis.SetSelection(0)
        sym_type.SetSelection(0)

        sym_chk.Bind(wx.EVT_CHECKBOX, self.onSymCheck)

        sym_sizer = wx.GridBagSizer(vgap=self._FromDIP(5),hgap=self._FromDIP(5))
        sym_sizer.Add(sym_chk, (0,0), span=(1,5))
        sym_sizer.Add(self._FromDIP(20), 0, (1, 0))
        sym_sizer.Add(wx.StaticText(settings_box, label='N-fold symmetry:'), (1,1),
            flag=wx.ALIGN_CENTER_VERTICAL)
        sym_sizer.Add(sym_val, (1,2), flag=wx.ALIGN_CENTER_VERTICAL)
        sym_sizer.Add(wx.StaticText(settings_box, label='Symmetry axis:'), (1,3),
            flag=wx.ALIGN_CENTER_VERTICAL)
        sym_sizer.Add(sym_axis, (1,4), flag=wx.ALIGN_CENTER_VERTICAL)
        sym_sizer.Add(wx.StaticText(settings_box, label='Symmetry type:'), (1,5),
            flag=wx.ALIGN_CENTER_VERTICAL)
        sym_sizer.Add(sym_type, (1,6), flag=wx.ALIGN_CENTER_VERTICAL)

        self.align_result = wx.CheckBox(settings_box, self.ids['align'],
            label='Align output to PDB/MRC:')
        self.align_result.SetValue(False)
        self.align_file_ctrl = wx.TextCtrl(settings_box, self.ids['align_file'],
            style=wx.TE_READONLY)
        align_button = wx.Button(settings_box, self.ids['align_file_btn'],
            label='Select')
        align_button.Bind(wx.EVT_BUTTON, self._selectAlignFile)

        align_sizer = wx.BoxSizer(wx.HORIZONTAL)
        align_sizer.Add(self.align_result, border=self._FromDIP(5),
            flag=wx.RIGHT)
        align_sizer.Add(self.align_file_ctrl, border=self._FromDIP(5),
            flag=wx.RIGHT, proportion=1)
        align_sizer.Add(align_button)

        advancedButton = wx.Button(settings_box, -1, 'Change Advanced Settings')
        advancedButton.Bind(wx.EVT_BUTTON, self._onAdvancedButton)


        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND | wx.TOP, self._FromDIP(2))
        settings_sizer.Add(nruns_sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(nprocs_sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(mode_sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(ne_sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP, self._FromDIP(2))
        settings_sizer.Add(average_chk, 0, wx.LEFT|wx.RIGHT|wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(refine_sizer, 0,wx.LEFT|wx.RIGHT|wx.TOP,
            self._FromDIP(2))
        settings_sizer.Add(sym_sizer, 0, flag=wx.TOP, border=self._FromDIP(2))
        settings_sizer.Add(align_sizer, border=self._FromDIP(2), flag=wx.LEFT
            |wx.RIGHT|wx.TOP|wx.EXPAND)
        settings_sizer.Add(advancedButton, 0, wx.LEFT|wx.RIGHT|wx.TOP
            |wx.ALIGN_CENTER, self._FromDIP(2))


        button_box = wx.StaticBox(parent, -1, 'Controls')

        start_button = wx.Button(button_box, self.ids['start'], 'Start')
        start_button.Bind(wx.EVT_BUTTON, self.onStartButton)

        abort_button = wx.Button(button_box, self.ids['abort'], 'Abort')
        abort_button.Bind(wx.EVT_BUTTON, self.onAbortButton)

        button_sizer = wx.StaticBoxSizer(button_box, wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_CENTER,
            border=self._FromDIP(2))
        button_sizer.Add(abort_button, 0, wx.ALL | wx.ALIGN_CENTER,
            border=self._FromDIP(2))
        button_sizer.AddStretchSpacer(1)

        control_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer.Add(file_sizer, 0, wx.EXPAND)
        control_sizer.Add(settings_sizer, 0, wx.EXPAND)
        control_sizer.Add(button_sizer, 0, wx.EXPAND)


        status_box = wx.StaticBox(parent, -1, 'Status')

        self.status = wx.TextCtrl(status_box, self.ids['status'], '',
            style=wx.TE_MULTILINE|wx.TE_READONLY, size=self._FromDIP((130,200)))

        status_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)
        status_sizer.Add(self.status, 1, wx.EXPAND | wx.ALL,
            border=self._FromDIP(2))


        half_sizer = wx.BoxSizer(wx.HORIZONTAL)
        half_sizer.Add(control_sizer, 2, wx.EXPAND)
        half_sizer.Add(status_sizer, 1, wx.EXPAND)

        log_box = wx.StaticBox(parent, -1, 'Log')

        try:
            self.logbook = flatNB.FlatNotebook(log_box, self.ids['logbook'],
                agwStyle=flatNB.FNB_NAV_BUTTONS_WHEN_NEEDED|flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)
        except AttributeError as e:
            print(e)
            self.logbook = flatNB.FlatNotebook(log_box, self.ids['logbook'])     #compatability for older versions of wxpython
            self.logbook.SetWindowStyleFlag(flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)

        self.logbook.SetActiveTabColour(RAWGlobals.tab_color)
        self.logbook.DeleteAllPages()

        log_sizer = wx.StaticBoxSizer(log_box, wx.HORIZONTAL)
        log_sizer.Add(self.logbook, 1, wx.ALL | wx.EXPAND, border=self._FromDIP(5))

        if (int(wx.__version__.split('.')[1])<9
            and int(wx.__version__.split('.')[0]) == 2):     #compatability for older versions of wxpython
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            top_sizer.Add(half_sizer, 0, wx.EXPAND)
            top_sizer.Add(log_sizer, 1, wx.EXPAND)
        else:
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            top_sizer.Add(half_sizer, 1, wx.EXPAND)
            top_sizer.Add(log_sizer, 1, wx.EXPAND)

        self.denss_timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self.onDenssTimer, self.denss_timer)

        self.msg_timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self.onMessageTimer, self.msg_timer)

        if not self.single_proc:
            self.my_manager = multiprocessing.Manager()
            self.wx_queue = self.my_manager.Queue()
        else:
            self.wx_queue = queue.Queue()

        return top_sizer


    def _initSettings(self):
        self.updateDenssSettings()

        aver = wx.FindWindowById(self.ids['average'], self)
        aver.SetValue(self.denss_settings['average'])

        refine = wx.FindWindowById(self.ids['refine'], self)
        refine.SetValue(self.denss_settings['refine'])

        if aver.GetValue():
            refine.Enable()
        else:
            refine.Disable()

        nruns = wx.FindWindowById(self.ids['runs'], self)
        nruns.SetValue(str(self.denss_settings['runs']))

        electrons = wx.FindWindowById(self.ids['electrons'], self)
        electrons.SetValue(str(self.denss_settings['electrons']))

        mode = wx.FindWindowById(self.ids['mode'], self)
        mode.SetStringSelection(str(self.denss_settings['mode']))

        procs = wx.FindWindowById(self.ids['procs'], self)
        if procs.GetCount()>1:
            procs.SetSelection(1)
        else:
            procs.SetSelection(0)

        prefix = wx.FindWindowById(self.ids['prefix'], self)
        prefix.SetValue(os.path.splitext(self.filename)[0])

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()
        save = wx.FindWindowById(self.ids['save'], self)
        save.SetValue(path)

        sym_on = wx.FindWindowById(self.ids['sym_on'])
        sym_val = wx.FindWindowById(self.ids['ncs'])
        sym_axis = wx.FindWindowById(self.ids['ncsAxis'])
        sym_type = wx.FindWindowById(self.ids['ncsType'])

        sym = self.denss_settings['ncs']
        sym_axis_val = self.denss_settings['ncsAxis']
        sym_type_val = self.denss_settings['ncsType']

        if int(sym) > 1:
            sym_on.SetValue(True)
            sym_val.SetValue(str(sym))
            sym_type.SetStringSelection(sym_type_val)

            sym_val.Enable()
            sym_axis.Enable()
            sym_type.Enable()
        else:
            sym_on.SetValue(False)

            sym_val.Disable()
            sym_axis.Disable()
            sym_type.Disable()

        if int(sym_axis_val) == 1:
            sym_axis.SetStringSelection('X')
        elif int(sym_axis_val) == 2:
            sym_axis.SetStringSelection('Y')
        elif int(sym_axis_val) == 3:
            sym_axis.SetStringSelection('Z')

        wx.FindWindowById(self.ids['abort'], self).Disable()

        self.align_file_name = None

        self.logbook.DeleteAllPages()


    def onStartButton(self, evt):
        #Set the denss settings
        self.setArgs()

        #Get user settings on number of runs, save location, etc
        average_window = wx.FindWindowById(self.ids['average'], self)
        average = average_window.GetValue()

        refine_window = wx.FindWindowById(self.ids['refine'], self)
        refine = refine_window.GetValue()

        prefix_window = wx.FindWindowById(self.ids['prefix'], self)
        prefix = prefix_window.GetValue()

        path_window = wx.FindWindowById(self.ids['save'], self)
        path = path_window.GetValue()

        procs_window = wx.FindWindowById(self.ids['procs'], self)
        procs = int(procs_window.GetStringSelection())

        nruns_window = wx.FindWindowById(self.ids['runs'], self)
        nruns = int(nruns_window.GetValue())

        align = self.align_result.GetValue()

        denss_names = collections.OrderedDict()
        for (key, value) in [(str(i), prefix+'_%s' %(str(i).zfill(2))) for i in range(1, nruns+1)]:
            denss_names[key] = value

        yes_to_all = False
        for key in denss_names:
            log_name = denss_names[key]+'.log'
            xplor_names = [denss_names[key]+'_current.xplor', denss_names[key]+'.xplor',
                denss_names[key]+'_original.xplor', denss_names[key]+'_precentered.xplor',
                denss_names[key]+'_support.xplor']
            fit_name = denss_names[key]+'_map.fit'
            stats_name = denss_names[key]+'_stats_by_step.txt'
            saxs_name = denss_names[key]+'_step0_saxs.dat'
            image_names = [denss_names[key]+'_chis.png', denss_names[key]+'_fit.png',
                denss_names[key]+'_rgs.png', denss_names[key]+'_supportV.png']
            mrc_name = [denss_names[key]+'.mrc', denss_names[key]+'_support.mrc']
            hdf_name = denss_names[key]+'_enant.hdf'

            names = [log_name, fit_name, stats_name, saxs_name, hdf_name] + mrc_name + xplor_names + image_names

            file_names = [os.path.join(path, name) for name in names]

            file_exists = False

            for f in file_names:
                if os.path.exists(f):
                    file_exists = True
                    break

            if file_exists and not yes_to_all:
                button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                question = ('Warning: selected directory contains Denss output '
                        'files with the prefix:\n"%s".\nRunning Denss will '
                        'overwrite these files.\nDo you wish to continue?'
                        %(denss_names[key])
                        )
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                    question, button_list, label, icon, style=wx.CAPTION|wx.RESIZE_BORDER)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True

            for f in file_names:
                if os.path.exists(f):
                    os.remove(f)

        #Set up the various bits of information the threads will need. Set up the status windows.
        self.denss_ids = collections.OrderedDict()
        for (key, value) in [(str(i), self.NewControlId()) for i in range(1, nruns+1)]:
            self.denss_ids[key] = value

        if not self.single_proc:
            self.thread_nums = self.my_manager.Queue()
        else:
            self.thread_nums = queue.Queue()

        self.logbook.DeleteAllPages()

        for i in range(1, nruns+1):
            text_ctrl = wx.TextCtrl(self.logbook, self.denss_ids[str(i)], '',
                style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, str(i))
            self.thread_nums.put_nowait(str(i))

        if nruns > 3 and average:
            average_names = [prefix+'_average.log', prefix+'_average.mrc',
                prefix+'_chis_by_step.fit', prefix+'_fsc.dat', prefix+'_map.fit',
                prefix+'_rg_by_step.fit', prefix+'_supportV_by_step.fit']

            average_names = average_names + [prefix+'_%i_aligned.mrc' %(i+1) for i in range(nruns)]

            file_names = [os.path.join(path, name) for name in average_names]

            file_exists = False

            for f in file_names:
                if os.path.exists(f):
                    file_exists = True
                    break

            if file_exists and not yes_to_all:
                button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                question = ('Warning: selected directory contains DENSS average '
                    'output files\n. Running the average will overwrite these '
                    'files.\nDo you wish to continue?')
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                    question, button_list, label, icon, style=wx.CAPTION | wx.RESIZE_BORDER)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True

            self.denss_ids['average'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.denss_ids['average'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Average')

            for f in file_names:
                if os.path.exists(f):
                    os.remove(f)


            if refine:
                refine_names = [prefix+'_refine.log', prefix+'_refine.mrc',
                    prefix+'_chis_by_step.fit', prefix+'_fsc.dat', prefix+'_map.fit',
                    prefix+'_rg_by_step.fit', prefix+'_supportV_by_step.fit']

                refine_names = refine_names + [prefix+'_%i_aligned.mrc' %(i+1) for i in range(nruns)]

                file_names = [os.path.join(path, name) for name in refine_names]

                file_exists = False

                for f in file_names:
                    if os.path.exists(f):
                        file_exists = True
                        break

                if file_exists and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                    question = ('Warning: selected directory contains DENSS refined '
                        'output files\n. Running the refinement will overwrite these '
                        'files.\nDo you wish to continue?')
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                        question, button_list, label, icon, style=wx.CAPTION | wx.RESIZE_BORDER)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

                self.denss_ids['refine'] = self.NewControlId()
                text_ctrl = wx.TextCtrl(self.logbook, self.denss_ids['refine'],
                    style=wx.TE_MULTILINE|wx.TE_READONLY)
                self.logbook.AddPage(text_ctrl, 'Refine')

                for f in file_names:
                    if os.path.exists(f):
                        os.remove(f)


        if align and self.align_file_name != '':
            filenames = [os.path.split(self.align_file_name)[1]]

            centered_align_file = '{}_centered{}'.format(*os.path.splitext(os.path.split(self.align_file_name)[1]))
            filenames.append(centered_align_file)

            filenames.extend(['{}-1_aligned.mrc'.format(key) for key in denss_names])

            if nruns > 1 and average:
                filenames.append('{}_average.mrc'.format(prefix))

            if nruns > 1 and refine:
                filenames.append('{}_refine.mrc'.format(prefix))

            for item in filenames:
                if os.path.exists(os.path.join(path, item)) and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES),
                        ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]

                    question = ('Warning: selected directory contains an '
                        'alignment output file\n"%s". Running alignment will '
                        'overwrite this file.\nDo you wish to continue?' %(item))
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self,
                        question, button_list, label, icon,
                        style=wx.CAPTION|wx.RESIZE_BORDER)

                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.denss_ids['align'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.denss_ids['align'], '',
                style=wx.TE_MULTILINE|wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Align')

        elif align and self.align_file_name == '':
            msg = ('You must select a file to align to or disable alignment.')
            dlg = wx.MessageDialog(self, msg, 'No alignment template file')
            dlg.ShowModal()
            dlg.Destroy()
            return

        self.status.SetValue('Starting processing\n')


        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                try:
                    wx.FindWindowById(self.ids[key], self).Disable()
                except AttributeError:
                    pass
            elif key == 'abort':
                wx.FindWindowById(self.ids[key], self).Enable()

        self.main_frame.sleep_inhibit.on()

        # Remove aligned filenames, because they don't automatically get overwritten if
        # align is off, and it could cause confusion
        align_names = ['{}_{:02d}_aligned.mrc'.format(prefix, i+1) for i in range(nruns)]
        if nruns > 1 and average:
            align_names.append('{}_average_aligned.mrc'.format(prefix))
        if nruns > 1 and refine:
            align_names.append('{}_refine_aligned.mrc'.format(prefix))

        for fname in align_names:
            if os.path.isfile(os.path.join(path, fname)):
                os.remove(os.path.join(path, fname))

        self.startDenss(path, prefix, procs)

    def onAbortButton(self, evt):
        self.abort_event.set()

        for stop_event in self.stop_events:
            stop_event.set()

        if self.denss_timer.IsRunning():
            self.denss_timer.Stop()

        abort_thread = threading.Thread(target=self.abort)
        abort_thread.daemon = True
        abort_thread.start()

    def abort(self):
        aborted = False

        self.main_frame.sleep_inhibit.off()

        while not aborted:
            self.my_lock.acquire()
            if np.all(self.threads_finished):
                aborted = True
            self.my_lock.release()
            time.sleep(.1)

        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                try:
                    wx.CallAfter(wx.FindWindowById(self.ids[key], self).Enable)
                except AttributeError:
                    pass
            elif key == 'abort':
                wx.CallAfter(wx.FindWindowById(self.ids[key], self).Disable)

        wx.CallAfter(self.status.AppendText, 'Processing Aborted!')

        wx.CallAfter(self.msg_timer.Stop)


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save'], self).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)

        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save'], self).SetValue(new_path)

        dirdlg.Destroy()

    def _selectAlignFile(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        filters = 'PDB files (*.pdb)|*.pdb|All files (*.*)|*.*'

        dialog = wx.FileDialog(self, 'Select a file', load_path, style=wx.FD_OPEN,
            wildcard=filters)

        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        # Destroy the dialog
        dialog.Destroy()

        if file is not None:
            self.align_file_name = file
            self.align_file_ctrl.SetValue(os.path.split(file)[1])
            self.align_file_ctrl.SetToolTip(wx.ToolTip(file))

    def onRunsText(self, evt):
        nruns_ctrl = wx.FindWindowById(self.ids['runs'], self)
        nruns = nruns_ctrl.GetValue()

        if nruns != '' and not nruns.isdigit():

            try:
                nruns = float(nruns.replace(',', '.'))
            except ValueError:
                nruns = ''
            if nruns != '':
                nruns = str(int(nruns))

            nruns_ctrl.ChangeValue(nruns) #Use changevalue instead of setvalue to avoid having to unbind and rebind


    def setArgs(self):
        for key in self.denss_settings:
            if key in self.ids:
                window = wx.FindWindowById(self.ids[key], self)
                if window is not None:
                    if key == 'runs' or key == 'mode' or key == 'ncsAxis' or key =='ncsType':
                        self.denss_settings[key] = window.GetStringSelection()
                    else:
                        self.denss_settings[key] = window.GetValue()

        sym = wx.FindWindowById(self.ids['sym_on'], self)

        dmax = float(self.iftm.getParameter('dmax'))

        if not sym.GetValue():
            self.denss_settings['ncs'] = 0

        if self.denss_settings['ncsAxis'] == 1:
            self.denss_settings['ncsAxis'] = 'X'
        elif self.denss_settings['ncsAxis'] == 2:
            self.denss_settings['ncsAxis'] = 'Y'
        elif self.denss_settings['ncsAxis'] == 3:
            self.denss_settings['ncsAxis'] = 'Z'

        if self.denss_settings['mode'] != 'Custom':
            #reset settings to default
            temp_settings = RAWSettings.RawGuiSettings()
            self.denss_settings['voxel'] = temp_settings.get('denssVoxel')
            self.denss_settings['oversample'] = temp_settings.get('denssOversampling')
            self.denss_settings['steps'] = temp_settings.get('denssSteps')
            # self.denss_settings['limitDmax'] = temp_settings.get('denssLimitDmax')
            # self.denss_settings['dmaxStep'] = temp_settings.get('denssLimitDmaxStep')
            self.denss_settings['recenter'] = temp_settings.get('denssRecenter')
            self.denss_settings['recenterStep'] = temp_settings.get('denssRecenterStep')
            self.denss_settings['positivity'] = temp_settings.get('denssPositivity')
            self.denss_settings['extrapolate'] = temp_settings.get('denssExtrapolate')
            self.denss_settings['shrinkwrap'] = temp_settings.get('denssShrinkwrap')
            self.denss_settings['swSigmaStart'] = temp_settings.get('denssShrinkwrapSigmaStart')
            self.denss_settings['swSigmaEnd'] = temp_settings.get('denssShrinkwrapSigmaEnd')
            self.denss_settings['swSigmaDecay'] = temp_settings.get('denssShrinkwrapSigmaDecay')
            self.denss_settings['swThresFrac'] = temp_settings.get('denssShrinkwrapThresFrac')
            self.denss_settings['swIter'] = temp_settings.get('denssShrinkwrapIter')
            self.denss_settings['swMinStep'] = temp_settings.get('denssShrinkwrapMinStep')
            self.denss_settings['connected'] = temp_settings.get('denssConnected')
            self.denss_settings['conSteps'] = temp_settings.get('denssConnectivitySteps')
            self.denss_settings['chiEndFrac'] = temp_settings.get('denssChiEndFrac')
            self.denss_settings['cutOutput'] = temp_settings.get('denssCutOut')
            self.denss_settings['writeXplor'] = temp_settings.get('denssWriteXplor')
            self.denss_settings['recenterMode'] = temp_settings.get('denssRecenterMode')
            # self.denss_settings['minDensity'] = temp_settings.get('denssMinDensity')
            # self.denss_settings['maxDensity'] = temp_settings.get('denssMaxDensity')
            # self.denss_settings['flattenLowDensity'] = temp_settings.get('denssFlattenLowDensity')
            self.denss_settings['ncsSteps'] = temp_settings.get('denssNCSSteps')
            self.denss_settings['denssGPU'] = temp_settings.get('denssGPU')

        shrinkwrap_sigma_start_in_A = (3.0 * dmax / 64.0) * 3.0
        shrinkwrap_sigma_end_in_A = (3.0 * dmax / 64.0) * 1.5

        if self.denss_settings['mode'] == 'Fast':
            self.denss_settings['swMinStep'] = 1000
            self.denss_settings['conSteps'] = '[2000]'
            self.denss_settings['recenterStep'] = '%s' %(list(range(501,2502,500)))
            self.denss_settings['steps'] = None

            self.denss_settings['voxel'] = dmax*self.denss_settings['oversample']/32.

        elif self.denss_settings['mode'] == 'Slow':
            self.denss_settings['swMinStep'] = 1000
            self.denss_settings['conSteps'] = '[2000]'
            self.denss_settings['recenterStep'] = '%s' %(list(range(501,8002,500)))
            self.denss_settings['steps'] = None
            self.denss_settings['voxel'] = dmax*self.denss_settings['oversample']/64.

        elif self.denss_settings['mode'] == 'Membrane':
            self.denss_settings['swMinStep'] = 0
            self.denss_settings['swThresFrac'] = 0.1
            self.denss_settings['conSteps'] = '[300, 500, 1000]'
            self.denss_settings['recenterStep'] = '%s' %(list(range(501,8002,500)))
            self.denss_settings['steps'] = None
            self.denss_settings['voxel'] = dmax*self.denss_settings['oversample']/64.
            self.denss_settings['positivity'] = False

            shrinkwrap_sigma_start_in_A *= 2.0
            shrinkwrap_sigma_end_in_A *= 2.0

        if self.denss_settings['swSigmaStart'] == 'None':
            shrinkwrap_sigma_start_in_vox = shrinkwrap_sigma_start_in_A / self.denss_settings['voxel']
            self.denss_settings['swSigmaStart'] = shrinkwrap_sigma_start_in_vox

        if self.denss_settings['swSigmaEnd'] == 'None':
            shrinkwrap_sigma_end_in_vox = shrinkwrap_sigma_end_in_A / self.denss_settings['voxel']
            self.denss_settings['swSigmaEnd'] = shrinkwrap_sigma_end_in_vox

    def get_multi_output(self, out_queue, den_window, stop_event, nmsg=100):
        num_msg = 0
        full_msg = ''
        while True:
            if stop_event.wait(0.001):
                try:
                    msg = out_queue.get_nowait()
                    full_msg = full_msg + msg
                except queue.Empty:
                    pass
                wx.CallAfter(den_window.AppendText, full_msg)
                break
            try:
                msg = out_queue.get_nowait()
                num_msg = num_msg + 1
                full_msg = full_msg + msg
            except queue.Empty:
                pass

            if num_msg == nmsg:
                wx.CallAfter(den_window.AppendText, full_msg)
                num_msg = 0
                full_msg = ''

    def startDenss(self, path, prefix, procs):
        self.stop_events = []
        self.threads_finished = []
        self.results = []

        comm_list = []

        q = self.iftm.q_extrap
        I = self.iftm.i_extrap

        ext_pts = len(I)-len(self.iftm.i_orig)

        if ext_pts > 0:
            sigq =np.empty_like(I)
            sigq[:ext_pts] = I[:ext_pts]*np.mean((self.iftm.err_orig[:10]/self.iftm.i_orig[:10]))
            sigq[ext_pts:] = I[ext_pts:]*(self.iftm.err_orig/self.iftm.i_orig)
        else:
            sigq = I*(self.iftm.err_orig/self.iftm.i_orig)

        sigq = np.abs(sigq)

        D = self.iftm.getParameter('dmax')

        for key in self.denss_ids:
            if key != 'average' and key != 'refine' and key!= 'align':
                if not self.single_proc:
                    den_queue = self.my_manager.Queue()
                    stop_event = self.my_manager.Event()
                else:
                    den_queue = queue.Queue()
                    stop_event = threading.Event()

                stop_event.clear()
                comm_list.append([den_queue, stop_event])

                den_window = wx.FindWindowById(self.denss_ids[key])

                comm_t = threading.Thread(target=self.get_multi_output,
                    args=(den_queue, den_window, stop_event))
                comm_t.daemon = True
                comm_t.start()

                self.stop_events.append(stop_event)
                self.threads_finished.append(False)

        if not self.single_proc:
            self.my_lock = self.my_manager.Lock()
            self.abort_event = self.my_manager.Event()
            my_pool = multiprocessing.Pool(procs)

            self.abort_event.clear()

            try:
                for key in self.denss_ids:
                    if key != 'average' and key != 'refine' and key!= 'align':
                        result = my_pool.apply_async(DENSS.runDenss, args=(q, I,
                            sigq, D, prefix, path, self.denss_settings),
                            kwds={'comm_list':comm_list, 'my_lock':self.my_lock,
                            'thread_num_q':self.thread_nums,
                            'wx_queue':self.wx_queue,
                            'abort_event':self.abort_event,
                            'log_id': self.denss_ids[key],})

                        self.results.append(result)

            except Exception:
                my_pool.close()
                raise

            my_pool.close()

        else:
            self.my_lock = threading.Lock()
            self.abort_event = threading.Event()

            self.abort_event.clear()

            run_t = threading.Thread(target=self.manage_denss, args=(q, I, sigq,
                D, prefix, path, comm_list))
            run_t.daemon = True
            run_t.start()

        self.denss_timer.Start(1000)
        self.msg_timer.Start(100)

    def manage_denss(self, q, I, sigq, D, prefix, path, comm_list):
        for key in self.denss_ids:
            if key != 'average' and key != 'refine' and key != 'align':
                data = DENSS.runDenss(q, I, sigq, D, prefix, path,
                    self.denss_settings, **{'comm_list':comm_list,
                    'my_lock':self.my_lock, 'thread_num_q':self.thread_nums,
                    'wx_queue':self.wx_queue, 'abort_event':self.abort_event,
                    'log_id': self.denss_ids[key],})

                self.results.append(data)

    def runAverage(self, prefix, path, nruns, procs):

        #Check to see if things have been aborted
        myId = self.denss_ids['average']
        averWindow = wx.FindWindowById(myId, self)

        if self.abort_event.is_set():
            wx.CallAfter(averWindow.AppendText, 'Aborted!\n')
            return

        wx.CallAfter(self.status.AppendText, 'Starting Average\n')

        if not self.single_proc:
            denss_outputs = [result.get() for result in self.results]
        else:
            denss_outputs = self.results

        if not self.single_proc:
            avg_q = self.my_manager.Queue()
            stop_event = self.my_manager.Event()
        else:
            avg_q = queue.Queue()
            stop_event = threading.Event()

        stop_event.clear()

        comm_t = threading.Thread(target=self.get_multi_output,
            args=(avg_q, averWindow, stop_event, 1))
        comm_t.daemon = True
        comm_t.start()

        #START CONTENTS OF denss.all.py from Tom Grant's code. Up to date
        #as of 5/21/19, commit 1967ae6, version 1.4.9
        #Has interjections of my code in a few places, mostly for outputs
        allrhos = np.array([denss_outputs[i][8] for i in np.arange(nruns)])
        sides = np.array([denss_outputs[i][9] for i in np.arange(nruns)])

        wx.CallAfter(averWindow.AppendText, 'Filtering enantiomers\n')

        allrhos, scores = DENSS.run_enantiomers(allrhos, procs, nruns,
            avg_q, self.my_lock, self.wx_queue, self.abort_event,
            self.single_proc)

        if self.abort_event.is_set():
            stop_event.set()
            return

        wx.CallAfter(averWindow.AppendText, 'Generating alignment reference\n')

        refrho = DENSS.binary_average(allrhos, procs, self.abort_event,
            self.single_proc)

        if self.abort_event.is_set():
            stop_event.set()
            self.threads_finished[-1] = True
            wx.CallAfter(averWindow.AppendText, 'Aborted!\n')
            return

        wx.CallAfter(averWindow.AppendText, 'Aligning and averaging models\n')

        aligned, scores = DENSS.align_multiple(refrho, allrhos, procs,
            self.abort_event, self.single_proc)

        if self.abort_event.is_set():
            stop_event.set()
            self.threads_finished[-1] = True
            wx.CallAfter(averWindow.AppendText, 'Aborted!\n')
            return

        #filter rhos with scores below the mean - 2*standard deviation.
        mean = np.mean(scores)
        std = np.std(scores)
        threshold = mean - 2*std
        filtered = np.empty(len(scores),dtype=str)

        for i in range(nruns):
            if scores[i] < threshold:
                filtered[i] = 'Filtered'
            else:
                filtered[i] = ' '
            # ioutput = prefix+"_"+str(i+1)+"_aligned"
            # DENSS.write_mrc(aligned[i], sides[0], os.path.join(path, ioutput+".mrc"))
            ioutput = prefix+"_"+str(i+1)
            # wx.CallAfter(averWindow.AppendText, "%s, Score = %0.3f %s\n" % (ioutput,scores[i],filtered[i]))
            wx.CallAfter(averWindow.AppendText,'Correlation score to reference: %s.mrc %.3f %s\n' %(ioutput, scores[i], filtered[i]))

        idx_keep = np.where(scores>threshold)
        kept_ids = np.arange(nruns)[idx_keep]
        aligned = aligned[idx_keep]
        average_rho = np.mean(aligned,axis=0)

        wx.CallAfter(averWindow.AppendText, "Mean of correlation scores: %.3f\n" % mean)
        wx.CallAfter(averWindow.AppendText, "Standard deviation of scores: %.3f\n" % std)
        wx.CallAfter(averWindow.AppendText,'Total number of input maps for alignment: %i\n' % allrhos.shape[0])
        wx.CallAfter(averWindow.AppendText,'Number of aligned maps accepted: %i\n' % aligned.shape[0])
        wx.CallAfter(averWindow.AppendText,'Correlation score between average and reference: %.3f\n' % (-DENSS.rho_overlap_score(average_rho, refrho)))
        DENSS.write_mrc(average_rho, sides[0], os.path.join(path, prefix+'_average.mrc'))


        #rather than compare two halves, average all fsc's to the reference
        fscs = []
        resns = []
        for calc_map in range(len(aligned)):
            fsc_map = DENSS.calc_fsc(aligned[calc_map],refrho,sides[0])
            fscs.append(fsc_map)
            resn_map = DENSS.fsc2res(fsc_map)
            resns.append(resn_map)

        fscs = np.array(fscs)

        #save a file containing all fsc curves
        fscs_header = ['res(1/A)']
        for i in kept_ids:
            ioutput = prefix+"_"+str(i)+"_aligned"
            fscs_header.append(ioutput)
        #add the resolution as the first column
        fscs_for_file = np.vstack((fscs[0,:,0],fscs[:,:,1])).T
        np.savetxt(os.path.join(path, prefix+'_allfscs.dat'), fscs_for_file,
            delimiter=" ", fmt="%.5e", header=",".join(fscs_header))

        resns = np.array(resns)
        fsc = np.mean(fscs,axis=0)
        resn, x, y, resx = DENSS.fsc2res(fsc, return_plot=True)
        resn_sd = np.std(resns)

        np.savetxt(os.path.join(path, prefix+'_fsc.dat'), fsc, delimiter=" ",
            fmt="%.5e", header="1/resolution, FSC; Resolution=%.1f +- %.1f A" % (resn,resn_sd))

        res_str = 'Resolution = %.1f +- %.1f A\n' % (resn,resn_sd)
        wx.CallAfter(averWindow.AppendText, res_str)
        wx.CallAfter(averWindow.AppendText,'END')

        #END CONTENTS OF denss.all.py

        wx.CallAfter(self.status.AppendText, 'Finished Average\n')

        log_text = averWindow.GetValue()

        with open(os.path.join(path, '{}_average.log'.format(prefix)), 'w') as f:
            f.write(log_text)

        self.threads_finished[-1] = True
        stop_event.set()

        self.average_results = {'mean': mean, 'std': std,'res': resn, 'res_sd': resn_sd,
            'scores': scores, 'fsc': fsc, 'total': allrhos.shape[0],
            'inc': aligned.shape[0], 'thresh': threshold, 'model': average_rho,
            'side': sides[0], 'fscs': fscs}

        if self.abort_event.is_set():
            return

        if 'refine' in self.denss_ids:
            t = threading.Thread(target=self.runRefine,
                args=(prefix, path, nruns, procs))
            t.daemon = True
            t.start()
            self.threads_finished.append(False)

        elif 'align' in self.denss_ids:
            self.refine_results = []

            t = threading.Thread(target=self.runAlign,
                    args=(prefix, path, nruns, procs))
            t.daemon = True
            t.start()
            self.threads_finished.append(False)

        else:
            self.msg_timer.Stop()
            self.refine_results = []
            wx.CallAfter(self.finishedProcessing)


    def runRefine(self, prefix, path, nruns, procs):
        #Check to see if things have been aborted
        myId = self.denss_ids['refine']
        refine_window = wx.FindWindowById(myId, self)

        if self.abort_event.is_set():
            wx.CallAfter(refine_window.AppendText, 'Aborted!\n')
            return

        wx.CallAfter(self.status.AppendText, 'Starting Refinement\n')

        self.thread_nums.put_nowait('-1')

        if not self.single_proc:
            refine_q = self.my_manager.Queue()
            stop_event = self.my_manager.Event()
        else:
            refine_q = queue.Queue()
            stop_event = threading.Event()

        stop_event.clear()
        self.stop_events.append(stop_event)

        comm_t = threading.Thread(target=self.get_multi_output,
            args=(refine_q, refine_window, stop_event))
        comm_t.daemon = True
        comm_t.start()

        comm_list = [[refine_q, stop_event],]

        q = self.iftm.q_extrap
        I = self.iftm.i_extrap

        ext_pts = len(I)-len(self.iftm.i_orig)

        if ext_pts > 0:
            sigq =np.empty_like(I)
            sigq[:ext_pts] = I[:ext_pts]*np.mean((self.iftm.err_orig[:10]/self.iftm.i_orig[:10]))
            sigq[ext_pts:] = I[ext_pts:]*(self.iftm.err_orig/self.iftm.i_orig)
        else:
            sigq = I*(self.iftm.err_orig/self.iftm.i_orig)

        D = self.iftm.getParameter('dmax')

        avg_model = self.average_results['model']

        if not self.single_proc:
            my_pool = multiprocessing.Pool(procs)

            result = my_pool.apply_async(DENSS.runDenss, args=(q, I, sigq,
                D, prefix, path, self.denss_settings, avg_model),
                kwds={'comm_list':comm_list, 'my_lock':self.my_lock,
                    'thread_num_q':self.thread_nums, 'wx_queue':self.wx_queue,
                    'abort_event':self.abort_event, 'log_id': myId,})

            my_pool.close()
            my_pool.join()
            self.refine_results = result.get()

        else:
            self.refine_results = DENSS.runDenss(q, I, sigq, D, prefix, path,
                self.denss_settings, avg_model, **{'comm_list':comm_list,
                'my_lock':self.my_lock, 'thread_num_q':self.thread_nums,
                'wx_queue':self.wx_queue, 'abort_event':self.abort_event,
                'log_id': myId,})

        wx.CallAfter(self.status.AppendText, 'Finished Refinement\n')

        self.threads_finished[-1] = True
        stop_event.set()

        if 'align' in self.denss_ids:
            t = threading.Thread(target=self.runAlign,
                    args=(prefix, path, nruns, procs))
            t.daemon = True
            t.start()
            self.threads_finished.append(False)
        else:
            self.msg_timer.Stop()
            wx.CallAfter(self.finishedProcessing)

    def runAlign(self, prefix, path, nruns, procs):

        myId = self.denss_ids['align']
        align_window = wx.FindWindowById(myId, self)

        wx.CallAfter(self.status.AppendText, 'Starting Alignment\n')

        items_to_align = collections.OrderedDict()

        if 'refine' in self.denss_ids:
            rho = self.refine_results[-2]
            side = self.refine_results[-1]

            rhos = np.array([rho])
            sides = np.array([side])

            items_to_align['Refined'] = (rhos, sides)

        elif 'average' in self.denss_ids:
            rho = self.average_results['model']
            side = self.average_results['side']

            rhos = np.array([rho])
            sides = np.array([side])

            items_to_align['Averaged'] = (rhos, sides)
        else:
            if not self.single_proc:
                denss_outputs = [result.get() for result in self.results]
            else:
                denss_outputs = self.results

            for i, key in enumerate(self.denss_ids):
                if key != 'average' and key != 'refine' and key != 'align':
                    rho = denss_outputs[i][-2]
                    side = denss_outputs[i][-1]
                    rhos = np.array([rho])
                    sides = np.array([side])

                    items_to_align['{:02d}'.format(i+1)] = (rhos, sides)

        if not self.single_proc:
            align_q = self.my_manager.Queue()
            stop_event = self.my_manager.Event()
        else:
            align_q = queue.Queue()
            stop_event = threading.Event()

        stop_event.clear()

        comm_t = threading.Thread(target=self.get_multi_output,
            args=(align_q, align_window, stop_event, 1))
        comm_t.daemon = True
        comm_t.start()

        settings = {'cores' : procs,
                'enantiomer' : True,
                'center' : True,
                'resolution' : 15.0,
                }

        if self.align_file_name != os.path.join(path, os.path.split(self.align_file_name)[1]):
            shutil.copy(self.align_file_name, path)

        align_file_name = os.path.join(path, os.path.split(self.align_file_name)[1])

        for i, key in enumerate(items_to_align):
            if self.abort_event.is_set():
                stop_event.set()
                wx.CallAfter(self.status.AppendText, 'Aborted!\n')

            align_q.put_nowait('Aligning model {}\n'.format(key))

            if i == 1:
                settings['center'] = False
                align_file_name = "{}_centered{}".format(*os.path.splitext(align_file_name))

            rhos, sides = items_to_align[key]

            if settings is not None and not self.abort_event.is_set():
                aligned, scores = DENSS.run_align(rhos, sides, align_file_name, align_q,
                    self.abort_event, single_proc=self.single_proc, **settings)
            else:
                aligned = None
                scores = None

            if self.abort_event.is_set():
                stop_event.set()
                wx.CallAfter(self.status.AppendText, 'Aborted!\n')

            elif aligned is not None:
                align_q.put_nowait('Correlation score to reference: {:.3f}\n'.format(scores[0]))

                if key == 'Refined':
                    outname = os.path.join(path, '{}_refine_aligned.mrc'.format(prefix))
                elif key == 'Averaged':
                    outname = os.path.join(path, '{}_average_aligned.mrc'.format(prefix))

                else:
                    outname = os.path.join(path, '{}_{:02d}_aligned.mrc'.format(prefix, i+1))

                DENSS.write_mrc(aligned[0], sides[0], outname)

        self.threads_finished[-1] = True
        stop_event.set()

        align_q.put_nowait('DENSS Alignment finished\n')

        wx.CallAfter(self.status.AppendText, 'Finished Alignment\n')

        self.msg_timer.Stop()
        wx.CallAfter(self.finishedProcessing)


    def onDenssTimer(self, evt):
        denss_finished = False

        if np.all(self.threads_finished):
            denss_finished = True

        if denss_finished:
            self.denss_timer.Stop()

            path_window = wx.FindWindowById(self.ids['save'], self)
            path = path_window.GetValue()

            prefix_window = wx.FindWindowById(self.ids['prefix'], self)
            prefix = prefix_window.GetValue()

            procs_window = wx.FindWindowById(self.ids['procs'], self)
            procs = int(procs_window.GetStringSelection())

            nruns_window = wx.FindWindowById(self.ids['runs'], self)
            nruns = int(nruns_window.GetValue())

            if not self.single_proc:
                denss_outputs = [result.get() for result in self.results]
            else:
                denss_outputs = self.results

            qdata = denss_outputs[0][0]
            Idata = denss_outputs[0][1]
            sigqdata = denss_outputs[0][2]
            qbinsc = denss_outputs[0][3]
            all_Imean = [denss_outputs[i][4] for i in np.arange(nruns)]
            header = ['q','I','error']
            fit = np.zeros(( len(qbinsc),nruns+3 ))
            fit[:len(qdata),0] = qdata
            fit[:len(Idata),1] = Idata
            fit[:len(sigqdata),2] = sigqdata

            for edmap in range(nruns):
                fit[:len(all_Imean[0]),edmap+3] = all_Imean[edmap]
                header.append("I_fit_"+str(edmap))

            np.savetxt(os.path.join(path, prefix+'_map.fit'), fit, delimiter=" ",
                fmt="%.5e".encode('ascii'), header=" ".join(header))
            chi_header, rg_header, supportV_header = list(zip(*[('chi_'+str(i),
                'rg_'+str(i),'supportV_'+str(i)) for i in range(nruns)]))
            all_chis = np.array([denss_outputs[i][5] for i in np.arange(nruns)])
            all_rg = np.array([denss_outputs[i][6] for i in np.arange(nruns)])
            all_supportV = np.array([denss_outputs[i][7] for i in np.arange(nruns)])

            np.savetxt(os.path.join(path, prefix+'_chis_by_step.fit'), all_chis.T,
                delimiter=" ", fmt="%.5e".encode('ascii'), header=",".join(chi_header))
            np.savetxt(os.path.join(path, prefix+'_rg_by_step.fit'), all_rg.T,
                delimiter=" ", fmt="%.5e".encode('ascii'), header=",".join(rg_header))
            np.savetxt(os.path.join(path, prefix+'_supportV_by_step.fit'),
                all_supportV.T, delimiter=" ", fmt="%.5e".encode('ascii'),
                header=",".join(supportV_header))

            chis = []
            rgs = []
            svs = []
            for i in range(nruns):
                last_index = max(np.where(denss_outputs[i][5] !=0)[0])
                chis.append(denss_outputs[i][5][last_index])
                rgs.append(denss_outputs[i][6][last_index+1])
                svs.append(denss_outputs[i][7][last_index+1])
                #Weird DENSS thing where last index of chi is 1 less than of Rg

            self.denss_stats = {'rg': rgs, 'chi': chis, 'sv': svs}

            if 'average' in self.denss_ids:
                t = threading.Thread(target=self.runAverage,
                    args=(prefix, path, nruns, procs))
                t.daemon = True
                t.start()
                self.threads_finished.append(False)

            elif 'align' in self.denss_ids:
                self.average_results = {}
                self.refine_results = []

                t = threading.Thread(target=self.runAlign,
                    args=(prefix, path, nruns, procs))
                t.daemon = True
                t.start()
                self.threads_finished.append(False)

            else:
                self.msg_timer.Stop()

                self.average_results = {}
                self.refine_results = []
                wx.CallAfter(self.finishedProcessing)

    def onMessageTimer(self, evt):
        for i in range(len(self.threads_finished)):
            try:
                self.my_lock.acquire()
                msg = self.wx_queue.get_nowait()
                if msg[0].startswith('status'):
                    wx.CallAfter(self.status.AppendText, msg[1])
                elif msg[0] == 'finished':
                    self.threads_finished[msg[1]] = True
                elif msg[0] == 'average':
                    averWindow = wx.FindWindowById(self.denss_ids['average'], self)
                    wx.CallAfter(averWindow.AppendText, msg[1])
                elif msg[0] == 'error':
                    wx.CallAfter(self.showError, msg[1], msg[2])
                elif msg[0] == 'refine':
                    refine_window = wx.FindWindowById(self.denss_ids['refine'], self)
                    wx.CallAfter(refine_window.AppendText, msg[1])
                else:
                    my_num = msg[0].split()[-1]
                    my_id = self.denss_ids[my_num]
                    denssWindow = wx.FindWindowById(my_id, self)
                    wx.CallAfter(denssWindow.AppendText, msg[1])
            except queue.Empty:
                pass
            finally:
                self.my_lock.release()

            try:
                if i<len(self.results):
                    if not self.single_proc:
                        if self.results[i].ready():
                            self.results[i].get()
            except Exception as e:
                self.abort_event.set()
                print(e)
                raise

    def showError(self, thread_num, error):
        if thread_num >=0:
            msg = ('The following error occured unexpectedly in run {}. Please '
                'inform the developers.\n\nError traceback:\n{}'.format(thread_num+1, error))
        else:
             msg = ('The following error occured unexpectedly in the refinement. Please '
                'inform the developers.\n\nError traceback:\n{}'.format(error))

        wx.MessageBox(msg, 'Unexpected error.', style=wx.ICON_ERROR|wx.OK)


    def finishedProcessing(self):
        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                try:
                    wx.FindWindowById(self.ids[key], self).Enable()
                except AttributeError:
                    pass
            elif key == 'abort':
                wx.FindWindowById(self.ids[key], self).Disable()

        wx.CallAfter(self.status.AppendText, 'Finished Processing')

        if not self.single_proc:
            denss_results = [result.get() for result in self.results]
        else:
            denss_results = self.results


        #Get user settings on number of runs, save location, etc
        average_window = wx.FindWindowById(self.ids['average'], self)
        average = average_window.GetValue()

        refine_window = wx.FindWindowById(self.ids['refine'], self)
        refine = refine_window.GetValue()

        prefix_window = wx.FindWindowById(self.ids['prefix'], self)
        prefix = prefix_window.GetValue()

        path_window = wx.FindWindowById(self.ids['save'], self)
        path = path_window.GetValue()

        nruns_window = wx.FindWindowById(self.ids['runs'], self)
        nruns = int(nruns_window.GetValue())

        sym_window = wx.FindWindowById(self.ids['sym_on'], self)
        use_sym = sym_window.GetValue()

        settings = {'average'   : average,
                    'prefix'    : prefix,
                    'path'      : path,
                    'runs'      : nruns,
                    'refine'    : refine,
                    'sym'       : use_sym,
                    }

        if not use_sym:
            wx.FindWindowById(self.ids['ncs']).Disable()
            wx.FindWindowById(self.ids['ncsAxis']).Disable()
            wx.FindWindowById(self.ids['ncsType']).Disable()

        if not average_window.GetValue():
           refine_window.Disable()

        self.main_frame.sleep_inhibit.off()

        wx.CallAfter(self.denss_frame.ResultsPanel.updateResults, settings,
            denss_results, self.denss_stats, self.average_results,
            self.refine_results)


    def _onAdvancedButton(self, evt):
        self.main_frame.showOptionsDialog(focusHead='DENSS')

    def onCheckBox(self,evt):
        refine = wx.FindWindowById(self.ids['refine'], self)

        if evt.GetId() == self.ids['average'] and not evt.IsChecked():
            refine.Disable()
            refine.SetValue(False)

        elif evt.GetId() == self.ids['average'] and evt.IsChecked():
            refine.Enable()

    def onSymCheck(self, evt):
        status = evt.IsChecked()

        wx.FindWindowById(self.ids['ncs'], self).Enable(status)
        wx.FindWindowById(self.ids['ncsAxis'], self).Enable(status)
        wx.FindWindowById(self.ids['ncsType'], self).Enable(status)

    def updateDenssSettings(self):
        self.denss_settings = {
            'voxel'             : self.raw_settings.get('denssVoxel'),
            'oversample'        : self.raw_settings.get('denssOversampling'),
            'electrons'         : self.raw_settings.get('denssNElectrons'),
            'steps'             : self.raw_settings.get('denssSteps'),
            # 'limitDmax'         : self.raw_settings.get('denssLimitDmax'),
            # 'dmaxStep'          : self.raw_settings.get('denssLimitDmaxStep'),
            'recenter'          : self.raw_settings.get('denssRecenter'),
            'recenterStep'      : self.raw_settings.get('denssRecenterStep'),
            'positivity'        : self.raw_settings.get('denssPositivity'),
            'extrapolate'       : self.raw_settings.get('denssExtrapolate'),
            'shrinkwrap'        : self.raw_settings.get('denssShrinkwrap'),
            'swSigmaStart'      : self.raw_settings.get('denssShrinkwrapSigmaStart'),
            'swSigmaEnd'        : self.raw_settings.get('denssShrinkwrapSigmaEnd'),
            'swSigmaDecay'      : self.raw_settings.get('denssShrinkwrapSigmaDecay'),
            'swThresFrac'       : self.raw_settings.get('denssShrinkwrapThresFrac'),
            'swIter'            : self.raw_settings.get('denssShrinkwrapIter'),
            'swMinStep'         : self.raw_settings.get('denssShrinkwrapMinStep'),
            'connected'         : self.raw_settings.get('denssConnected'),
            'conSteps'          : self.raw_settings.get('denssConnectivitySteps'),
            'chiEndFrac'        : self.raw_settings.get('denssChiEndFrac'),
            'average'           : self.raw_settings.get('denssAverage'),
            'runs'              : self.raw_settings.get('denssReconstruct'),
            'cutOutput'         : self.raw_settings.get('denssCutOut'),
            'writeXplor'        : self.raw_settings.get('denssWriteXplor'),
            'mode'              : self.raw_settings.get('denssMode'),
            'recenterMode'      : self.raw_settings.get('denssRecenterMode'),
            # 'minDensity'        : self.raw_settings.get('denssMinDensity'),
            # 'maxDensity'        : self.raw_settings.get('denssMaxDensity'),
            # 'flattenLowDensity' : self.raw_settings.get('denssFlattenLowDensity'),
            'ncs'               : self.raw_settings.get('denssNCS'),
            'ncsSteps'          : self.raw_settings.get('denssNCSSteps'),
            'ncsAxis'           : self.raw_settings.get('denssNCSAxis'),
            'ncsType'           : self.raw_settings.get('denssNCSType'),
            'refine'            : self.raw_settings.get('denssRefine'),
            'denssGPU'          : self.raw_settings.get('denssGPU'),
            }


    def Close(self, event):

        process_finished = True

        if self.denss_timer.IsRunning():
            process_finished = False

        if process_finished and len(self.threads_finished)>0:
            if not np.all(self.threads_finished):
                process_finished = False

        if not process_finished and event.CanVeto():
            msg = ("Warning: DENSS is still running. "
                "Closing this window will abort the currently running "
                "processes. Do you want to continue closing the window?")
            dlg = wx.MessageDialog(self.main_frame, msg, "Abort DENSS?",
                style = wx.ICON_WARNING | wx.YES_NO)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            if proceed == wx.ID_YES:
                self.abort_event.set()
                self.main_frame.sleep_inhibit.off()

                for stop_event in self.stop_events:
                    stop_event.set()

                if self.denss_timer.IsRunning():
                    self.denss_timer.Stop()

                if self.msg_timer.IsRunning():
                    self.msg_timer.Stop()

            else:
                event.Veto()

        elif not process_finished:
            #Try to gracefully exit
            self.abort_event.set()
            self.main_frame.sleep_inhibit.off()

            for stop_event in self.stop_events:
                stop_event.set()

            if self.denss_timer.IsRunning():
                self.denss_timer.Stop()

            if self.msg_timer.IsRunning():
                    self.msg_timer.Stop()


class DenssResultsPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.parent = parent

        self.run_panel = parent.GetParent().GetParent().RunPanel

        self.manip_item = manip_item

        self.iftm = iftm

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.ids = {'ambiCats'      : self.NewControlId(),
                    'ambiScore'     : self.NewControlId(),
                    'ambiEval'      : self.NewControlId(),
                    'res'           : self.NewControlId(),
                    'res_sd'        : self.NewControlId(),
                    'models'        : self.NewControlId(),
                    'rscorMean'     : self.NewControlId(),
                    'rscorStd'      : self.NewControlId(),
                    'rscorInc'      : self.NewControlId(),
                    'rscorTot'      : self.NewControlId(),
                    'model_sum'     : self.NewControlId(),
                    }

        self.topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(self.topsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        for i in range(self.models.GetPageCount()):
            page = self.models.GetPage(i)

            if isinstance(page, DenssPlotPanel) or isinstance(page, DenssAveragePlotPanel):
                page.updateColors()

        self.models.SetActiveTabColour(RAWGlobals.tab_color)

    def _createLayout(self, parent):
        ambi_box = wx.StaticBox(parent, wx.ID_ANY, 'Ambimeter')
        self.ambi_sizer = wx.StaticBoxSizer(ambi_box, wx.VERTICAL)

        match_text = wx.StaticText(ambi_box, wx.ID_ANY, 'Compatible shape categories:')
        match_ctrl = wx.TextCtrl(ambi_box, self.ids['ambiCats'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        score_text = wx.StaticText(ambi_box, -1, 'Ambiguity score:')
        score_ctrl = wx.TextCtrl(ambi_box, self.ids['ambiScore'], '',
            size=self._FromDIP((60, -1)), style = wx.TE_READONLY)

        eval_text = wx.StaticText(ambi_box, -1, 'AMBIMETER says:')
        eval_ctrl = wx.TextCtrl(ambi_box, self.ids['ambiEval'], '',
            size=self._FromDIP((300, -1)), style = wx.TE_READONLY)

        ambi_subsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer1.Add(match_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer1.Add(match_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        ambi_subsizer1.Add(score_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(8))
        ambi_subsizer1.Add(score_ctrl, 0, wx.LEFT| wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))

        ambi_subsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer2.Add(eval_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer2.Add(eval_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))

        self.ambi_sizer.Add(ambi_subsizer1, 0)
        self.ambi_sizer.Add(ambi_subsizer2, 0, wx.TOP, border=self._FromDIP(5))


        rscor_box = wx.StaticBox(parent, wx.ID_ANY, 'Real Space Correlation (RSC)')
        self.rscor_sizer = wx.StaticBoxSizer(rscor_box, wx.HORIZONTAL)

        corm_text = wx.StaticText(rscor_box, label='Mean RSC:')
        corm_ctrl = wx.TextCtrl(rscor_box, self.ids['rscorMean'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)
        cors_text = wx.StaticText(rscor_box, label='Stdev. RSC:')
        cors_ctrl = wx.TextCtrl(rscor_box, self.ids['rscorStd'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)
        cori1_text = wx.StaticText(rscor_box, label='Average included:')
        cori1_ctrl = wx.TextCtrl(rscor_box, self.ids['rscorInc'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)
        cori2_text = wx.StaticText(rscor_box, label='of')
        cori2_ctrl = wx.TextCtrl(rscor_box, self.ids['rscorTot'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        self.rscor_sizer.Add(corm_text, flag=wx.ALIGN_CENTER_VERTICAL)
        self.rscor_sizer.Add(corm_ctrl, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        self.rscor_sizer.Add(cors_text, border=self._FromDIP(4),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        self.rscor_sizer.Add(cors_ctrl, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        self.rscor_sizer.Add(cori1_text, border=self._FromDIP(4),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        self.rscor_sizer.Add(cori1_ctrl, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        self.rscor_sizer.Add(cori2_text, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
        self.rscor_sizer.Add(cori2_ctrl, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)

        res_box = wx.StaticBox(parent, wx.ID_ANY, 'Reconstruction Resolution (FSC)')
        self.res_sizer = wx.StaticBoxSizer(res_box, wx.HORIZONTAL)

        res_text = wx.StaticText(res_box, wx.ID_ANY, 'Fourier Shell Correlation Resolution:')
        res_ctrl = wx.TextCtrl(res_box, self.ids['res'], '',
            size=self._FromDIP((60,-1)), style=wx.TE_READONLY)

        res_sd_text = wx.StaticText(res_box, label='+/-')
        res_sd_ctrl = wx.TextCtrl(res_box, self.ids['res_sd'], '',
            size=self._FromDIP((60, -1)), style=wx.TE_READONLY)

        resunit_text = wx.StaticText(res_box, label='Angstrom')

        self.res_sizer.Add(res_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.res_sizer.Add(res_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.res_sizer.Add(res_sd_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.res_sizer.Add(res_sd_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        self.res_sizer.Add(resunit_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(4))

        model_box = wx.StaticBox(parent, -1, 'Models')

        try:
            self.models = flatNB.FlatNotebook(model_box, self.ids['models'],
                agwStyle=flatNB.FNB_NAV_BUTTONS_WHEN_NEEDED|flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)
        except AttributeError:
            self.models = flatNB.FlatNotebook(model_box, self.ids['models'])     #compatability for older versions of wxpython
            self.models.SetWindowStyleFlag(flatNB.FNB_NO_X_BUTTON|flatNB.FNB_NODRAG)

        self.models.SetActiveTabColour(RAWGlobals.tab_color)
        self.models.DeleteAllPages()

        summary_panel = wx.Panel(self.models)

        models_list = wx.ListCtrl(summary_panel, id=self.ids['model_sum'],
            size=(-1,-1), style=wx.LC_REPORT)
        models_list.InsertColumn(0, 'Model')
        models_list.InsertColumn(1, 'Chi^2')
        models_list.InsertColumn(2, 'Rg')
        models_list.InsertColumn(3, 'Support Vol.')
        models_list.InsertColumn(4, 'Mean RSC')

        mp_sizer = wx.BoxSizer()
        mp_sizer.Add(models_list, 1, flag=wx.EXPAND)
        summary_panel.SetSizer(mp_sizer)

        self.models.AddPage(summary_panel, 'Summary')

        self.model_sizer = wx.StaticBoxSizer(model_box, wx.HORIZONTAL)
        self.model_sizer.Add(self.models, 1, wx.ALL | wx.EXPAND,
            border=self._FromDIP(5))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.ambi_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.rscor_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.res_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.model_sizer, 1, wx.EXPAND)

        return top_sizer


    def _initSettings(self):
        if self.iftm.getParameter('algorithm') == 'GNOM':
            opsys = platform.system()
            if opsys == 'Windows':
                if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'ambimeter.exe')):
                    run_ambi = True
                else:
                    run_ambi = False
            else:
                if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'ambimeter')):
                    run_ambi = True
                else:
                    run_ambi = False

            if run_ambi:
                t = threading.Thread(target=self.runAmbimeter)
                t.daemon = True
                t.start()
            else:
                self.topsizer.Hide(self.ambi_sizer, recursive=True)

        else:
            self.topsizer.Hide(self.ambi_sizer, recursive=True)

        self.topsizer.Hide(self.rscor_sizer, recursive=True)
        self.topsizer.Hide(self.res_sizer, recursive=True)

    def runAmbimeter(self):
        standard_paths = wx.StandardPaths.Get()
        tempdir = standard_paths.GetTempDir()

        outname = tempfile.NamedTemporaryFile(dir=tempdir).name

        while os.path.isfile(outname):
            outname = tempfile.NamedTemporaryFile(dir=tempdir).name

        outname = os.path.split(outname)[-1] + '.out'

        if self.main_frame.OnlineControl.isRunning() and tempdir == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        SASFileIO.writeOutFile(self.iftm, os.path.join(tempdir, outname))

        ambi_settings = {'sRg' :'4',
                        'files':'None'
                        }

        try:
            output = SASCalc.runAmbimeter(outname, 'temp', ambi_settings,
                tempdir, self.raw_settings.get('ATSASDir'))

        except SASExceptions.NoATSASError as e:
            wx.CallAfter(self.main_frame.showMessageDialog, self, str(e),
                "Error running Ambimeter", wx.ICON_ERROR|wx.OK)
            os.remove(os.path.join(tempdir, outname))
            return

        os.remove(os.path.join(tempdir, outname))

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        wx.CallAfter(cats_window.SetValue, output[0])
        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        wx.CallAfter(score_window.SetValue, output[1])
        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        wx.CallAfter(eval_window.SetValue, output[2])

    def getResolution(self, resolution, resolution_sd):
        res_window = wx.FindWindowById(self.ids['res'], self)
        res_window.SetValue(str(resolution))

        res_sd_window = wx.FindWindowById(self.ids['res_sd'], self)
        res_sd_window.SetValue(str(resolution_sd))

    def getModels(self, settings, denss_results, denss_stats, average_results,
        refine_results):

        nruns = settings['runs']

        while self.models.GetPageCount() > 1:
            last_page = self.models.GetPageText(self.models.GetPageCount()-1)
            if last_page != 'Summary':
                self.models.DeletePage(self.models.GetPageCount()-1)
            else:
                self.models.DeletePage(self.models.GetPageCount()-2)

        self.modelSummary(settings, denss_results, denss_stats, average_results,
            refine_results)

        for i in range(1, nruns+1):
            plot_panel = DenssPlotPanel(self.models, denss_results[i-1], self.iftm)
            self.models.AddPage(plot_panel, str(i))

        if nruns >= 4 and settings['average']:
            plot_panel = DenssAveragePlotPanel(self.models, settings, average_results)
            self.models.AddPage(plot_panel, 'Average')

            if settings['refine']:
                plot_panel = DenssPlotPanel(self.models, refine_results, self.iftm)
                self.models.AddPage(plot_panel, 'Refine')

    def modelSummary(self, settings, denss_results, denss_stats, average_results,
        refine_results):
        nruns = settings['runs']
        models_list = wx.FindWindowById(self.ids['model_sum'], self)
        models_list.DeleteAllItems()

        for i in range(nruns):
            model = str(i+1)
            chisq = str(round(denss_stats['chi'][i], 5))
            rg = str(round(denss_stats['rg'][i],2))
            sv = str(round(denss_stats['sv'][i], 2))

            if average_results:
                mrsc = str(round(average_results['scores'][i],4))
            else:
                mrsc = ''

            models_list.Append((model, chisq, rg, sv, mrsc))

            if mrsc != '' and float(mrsc) < average_results['thresh']:
                models_list.SetItemTextColour(i, 'red') #Not working?!

        if settings['runs'] >= 4 and settings['average'] and settings['refine']:
            model = 'Refine'
            last_index = max(np.where(refine_results[5] !=0)[0])
            chisq = str(round(refine_results[5][last_index], 5))
            rg = str(round(refine_results[6][last_index], 2))
            sv = str(round(refine_results[7][last_index], 2))
            mrsc = ''

            models_list.Append((model, chisq, rg, sv, mrsc))



    def getAverage(self, avg_results):
        mean = str(round(avg_results['mean'],4))
        std = str(round(avg_results['std'],4))
        total = str(avg_results['total'])
        inc = str(avg_results['inc'])

        mean_window = wx.FindWindowById(self.ids['rscorMean'], self)
        mean_window.SetValue(mean)
        std_window = wx.FindWindowById(self.ids['rscorStd'], self)
        std_window.SetValue(std)
        inc_window = wx.FindWindowById(self.ids['rscorInc'], self)
        inc_window.SetValue(inc)
        total_window = wx.FindWindowById(self.ids['rscorTot'], self)
        total_window.SetValue(total)

    def updateResults(self, settings, denss_results, denss_stats, average_results,
        refine_results):
        #In case we ran a different setting a second time, without closing the window
        self.topsizer.Hide(self.res_sizer, recursive=True)
        self.topsizer.Hide(self.rscor_sizer, recursive=True)

        if settings['runs'] >= 4 and settings['average']:
            self.getResolution(average_results['res'], average_results['res_sd'])
            self.getAverage(average_results)

            self.topsizer.Show(self.rscor_sizer, recursive=True)
            self.topsizer.Show(self.res_sizer, recursive=True)

        self.getModels(settings, denss_results, denss_stats, average_results,
            refine_results)

        self.Layout()

        models_nb = wx.FindWindowById(self.ids['models'])
        models_nb.DoGetBestSize()
        for i in range(models_nb.GetPageCount()):
            models_nb.SetSelection(i)

        models_nb.SetSelection(0)

        self.parent.SetSelection(1)

        # viewer_window = wx.FindWindowByName('DammifViewerPanel')
        # viewer_window.updateResults(model_list)

        self._saveResults()

    def _saveResults(self):
        res_data = []
        ambi_data = []
        rsc_data = []

        models_list = wx.FindWindowById(self.ids['model_sum'], self)

        cdb = wx.ColourDatabase()

        if self.topsizer.IsShown(self.rscor_sizer):
            mean = wx.FindWindowById(self.ids['rscorMean'], self).GetValue()
            std = wx.FindWindowById(self.ids['rscorStd'], self).GetValue()
            inc = wx.FindWindowById(self.ids['rscorInc'], self).GetValue()
            total = wx.FindWindowById(self.ids['rscorTot'], self).GetValue()

            rsc_data.append(('Mean RSC:', mean))
            rsc_data.append(('Stdev. RSC:', std))
            rsc_data.append(('Number of models included:', inc))
            rsc_data.append(('Total number of models:', total))

            ex_items = []
            for i in range(models_list.GetItemCount()):
                if cdb.FindName(models_list.GetItemTextColour(i)).lower() == 'red':
                    ex_items.append(models_list.GetItem(i, 0).GetText())

            if ex_items:
                rsc_data.append(('Excluded Models:', ' ,'.join(ex_items)))

        if self.topsizer.IsShown(self.res_sizer):
            res = wx.FindWindowById(self.ids['res']).GetValue()
            res_sd = wx.FindWindowById(self.ids['res_sd']).GetValue()
            res_data = [('Fourier Shell Correlation Resolution (Angstrom): ', res,
                '+/-', res_sd)]

        models_nb = wx.FindWindowById(self.ids['models'], self)

        model_plots = []

        for i in range(models_nb.GetPageCount()):
            page = models_nb.GetPage(i)
            if models_nb.GetPageText(i) != 'Summary':
                figures = page.figures
                model = models_nb.GetPageText(i)
                model_plots.append((model, figures))

        model_data = [[] for k in range(models_list.GetItemCount())]

        for i in range(models_list.GetItemCount()):
            item_data = [[] for k in range(models_list.GetColumnCount())]
            for j in range(models_list.GetColumnCount()):
                item = models_list.GetItem(i, j)
                data = item.GetText()
                item_data[j] = data

            model_data[i] = item_data

        if self.topsizer.IsShown(self.ambi_sizer):
            ambi_cats = wx.FindWindowById(self.ids['ambiCats']).GetValue()
            ambi_score = wx.FindWindowById(self.ids['ambiScore']).GetValue()
            ambi_eval = wx.FindWindowById(self.ids['ambiEval']).GetValue()
            ambi_data = [('Compatible shape categories:', ambi_cats),
                        ('Ambiguity score:', ambi_score), ('AMBIMETER says:', ambi_eval)]

        input_file = wx.FindWindowById(self.run_panel.ids['fname']).GetValue()
        output_prefix = wx.FindWindowById(self.run_panel.ids['prefix']).GetValue()
        output_directory = wx.FindWindowById(self.run_panel.ids['save']).GetValue()
        mode = wx.FindWindowById(self.run_panel.ids['mode']).GetStringSelection()
        tot_recons = wx.FindWindowById(self.run_panel.ids['runs']).GetValue()
        electrons = wx.FindWindowById(self.run_panel.ids['electrons']).GetValue()
        average = wx.FindWindowById(self.run_panel.ids['average']).IsChecked()
        symmetry = wx.FindWindowById(self.run_panel.ids['sym_on']).IsChecked()
        refined = wx.FindWindowById(self.run_panel.ids['refine']).IsChecked()

        setup_data = [('Input file:', input_file), ('Output prefix:', output_prefix),
                    ('Output directory:', output_directory), ('Mode:', mode),
                    ('Total number of reconstructions:', tot_recons),
                    ('Number of electrons in molecule:', electrons),
                    ('Averaged:', average),
                    ('Refined:', refined),
                    ('Symmetry applied:', symmetry)
                    ]

        if symmetry:
            sym_val = wx.FindWindowById(self.run_panel.ids['ncs']).GetValue()
            sym_axis = wx.FindWindowById(self.run_panel.ids['ncsAxis']).GetStringSelection()
            sym_type = wx.FindWindowById(self.run_panel.ids['ncsType']).GetStringSelection()

            setup_data.append(('N-fold rotational symmetry:', sym_val))
            setup_data.append(('Symmetry axis:', sym_axis))
            setup_data.append(('Symmetry type:', sym_type))

        filename = output_prefix + '_denss_results.csv'
        save_path = os.path.join(output_directory, filename)

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving DENSS data', 0)

        SASFileIO.saveDenssData(save_path, ambi_data, res_data, model_plots,
            setup_data, rsc_data, model_data)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)

        self.Layout()


class DenssViewerPanel(wx.Panel):

    def __init__(self, parent):

        wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DenssViewerPanel')

        self.parent = parent

        self.ids = {'models'    : self.NewControlId(),
                    }

        self.model_dict = None

        top_sizer = self._createLayout(self)

        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self, parent):
        ctrls_box = wx.StaticBox(parent, wx.ID_ANY, 'Viewer Controls')

        model_text = wx.StaticText(ctrls_box, wx.ID_ANY, 'Model to display:')
        model_choice = wx.Choice(ctrls_box, self.ids['models'])
        model_choice.Bind(wx.EVT_CHOICE, self.onChangeModels)

        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_sizer.Add(model_text, 0)
        model_sizer.Add(model_choice, 0, wx.LEFT, border=self._FromDIP(3))


        ctrls_sizer = wx.StaticBoxSizer(ctrls_box, wx.VERTICAL)
        ctrls_sizer.Add(model_sizer, 0)


        self.fig = Figure(dpi=75, tight_layout=True)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.subplot = self.fig.add_subplot(1,1,1, projection='3d')
        self.subplot.grid(False)
        self.subplot.set_axis_off()

        # self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        # self.toolbar.Realize()

        layout_sizer = wx.BoxSizer(wx.VERTICAL)
        layout_sizer.Add(ctrls_sizer, 0, wx.BOTTOM | wx.EXPAND, self._FromDIP(5))
        layout_sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)
        # sizer.Add(self.toolbar, 0, wx.GROW)

        self.canvas.draw()

        return layout_sizer

    def _plotModel(self, atoms, radius):
        self.subplot.clear()
        self.subplot.grid(False)
        self.subplot.set_axis_off()

        scale = (float(radius)/1.25)**2

        self.subplot.scatter(atoms[:,0], atoms[:,1], atoms[:,2], s=250*scale, alpha=.95)

        self.canvas.draw()

    def onChangeModels(self, evt):
        model = evt.GetString()

        self._plotModel(self.model_dict[model][1], self.model_dict[model][0]['atom_radius'])


    def updateResults(self, model_list):
        self.model_dict = collections.OrderedDict()

        for item in model_list:
            self.model_dict[str(item[0])] = [item[1], item[2]]

        model_choice = wx.FindWindowById(self.ids['models'], self)
        model_choice.Set(list(self.model_dict.keys()))

        if 'refine' in self.model_dict:
            self._plotModel(self.model_dict['refine'][1], self.model_dict['refine'][0]['atom_radius'])
            model_choice.SetStringSelection('refine')
        elif 'damfilt' in self.model_dict:
            self._plotModel(self.model_dict['damfilt'][1], self.model_dict['damfilt'][0]['atom_radius'])
            model_choice.SetStringSelection('damfilt')
        elif 'damaver' in self.model_dict:
            self._plotModel(self.model_dict['damaver'][1], self.model_dict['damaver'][0]['atom_radius'])
            model_choice.SetStringSelection('damaver')
        else:
            self._plotModel(self.model_dict['1'][1], self.model_dict['1'][0]['atom_radius'])
            model_choice.SetStringSelection('1')


class DenssPlotPanel(wx.Panel):

    def __init__(self, parent, denss_results, iftm):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BG_STYLE_SYSTEM
            |wx.RAISED_BORDER)

        self.denss_results = denss_results
        self.iftm = iftm

        self.figures = []

        self.sc_canvas = self.createScatteringPlot()
        self.stats_canvas = self.createStatsPlot()

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.sc_canvas, 1, wx.GROW)
        sizer.Add(self.stats_canvas, 1, wx.GROW)

        self.SetSizer(sizer)

    def updateColors(self):
        color = SASUtils.update_mpl_style()

        # self.ax1_hline.set_color(color)

        # self.ax0_err[0].set_color(color)

        # for each in self.ax0_err[1]:
        #     each.set_color(color)

        # for each in self.ax0_err[2]:
        #     each.set_color(color)

        # self.ax0_smooth.set_color(color)
        self.sc_canvas.draw()
        self.stats_canvas.draw()

    def createScatteringPlot(self):
        color = SASUtils.update_mpl_style()

        if color == 'black':
            color_num = '0'
        else:
            color_num = '1'

        fig = Figure((3.25,2.5))
        canvas = FigureCanvasWxAgg(self, -1, fig)

        self.figures.append(fig)

        if self.iftm.getParameter('algorithm') == 'GNOM':
            q = self.iftm.q_extrap
            I = self.iftm.i_extrap

            ext_pts = len(I)-len(self.iftm.i_orig)
            sigq = np.empty_like(I)
            sigq[:ext_pts] = I[:ext_pts]*np.mean((self.iftm.err_orig[:10]/self.iftm.i_orig[:10]))
            sigq[ext_pts:] = I[ext_pts:]*(self.iftm.err_orig/self.iftm.i_orig)
        else:
            q = self.iftm.q_orig
            I = self.iftm.i_fit
            sigq = I*(self.iftm.err_orig/self.iftm.i_orig)
        #handle sigq values whose error bounds would go negative and be missing on the log scale
        sigq2 = np.copy(sigq)
        sigq2[sigq>I] = I[sigq>I]*.999

        qdata = self.denss_results[0]
        Idata = self.denss_results[1]
        qbinsc = self.denss_results[3]
        Imean = self.denss_results[4]

        gs = matplotlib.gridspec.GridSpec(2, 1, height_ratios=[3,1])

        ax0 = fig.add_subplot(gs[0])
        self.ax0_err = ax0.errorbar(self.iftm.q_orig, self.iftm.i_orig, color=color, marker='.',
            yerr=self.iftm.err_orig, mec='none', mew=0, ms=3, alpha=0.3,
            capsize=0, elinewidth=0.1, ecolor=cc.to_rgba(color_num,alpha=0.5),
            label='Exp. Data')
        self.ax0_smooth = ax0.plot(q, I, color=color, linestyle='--',alpha=0.7, lw=1,
            label='Smoothed Exp. Data')[0]
        ax0.plot(qdata[qdata<=q[-1]], Idata[qdata<=q[-1]], 'bo',alpha=0.5,
            label='Interpolated')
        ax0.plot(qbinsc[qdata<=q[-1]], Imean[qdata<=q[-1]],'r.',label='DENSS Map')
        handles,labels = ax0.get_legend_handles_labels()
        handles = [handles[3], handles[0], handles[1],handles[2]]
        labels = [labels[3], labels[0], labels[1], labels[2]]
        xmax = np.min([self.iftm.q_orig.max(),q.max(),qdata.max()])*1.1
        ymin = np.min([np.min(I[q<=xmax]),np.min(Idata[qdata<=xmax]),np.min(Imean[qdata<=xmax])])
        ymax = np.max([np.max(I[q<=xmax]),np.max(Idata[qdata<=xmax]),np.max(Imean[qdata<=xmax])])
        ax0.set_xlim([-xmax*.05,xmax])
        ax0.set_ylim([0.5*ymin,1.5*ymax])
        ax0.legend(handles,labels, fontsize='small')
        ax0.semilogy()
        ax0.set_ylabel('I(q)', fontsize='small')
        ax0.tick_params(labelbottom=False, labelsize='x-small')

        residuals = np.log10(Imean[np.in1d(qbinsc,qdata)])-np.log10(Idata)
        ax1 = fig.add_subplot(gs[1])
        self.ax1_hline = ax1.axhline(0, color=color, linewidth=1.0)
        ax1.plot(qdata[qdata<=q[-1]], residuals[qdata<=q[-1]], 'ro-')
        ylim = ax1.get_ylim()
        ymax = np.max(np.abs(ylim))
        n = int(.9*len(residuals[qdata<=q[-1]]))
        ymax = np.max(np.abs(residuals[qdata<=q[-1]][:-n]))
        ax1.set_ylim([-ymax,ymax])
        ax1.yaxis.major.locator.set_params(nbins=5)
        xlim = ax0.get_xlim()
        ax1.set_xlim(xlim)
        ax1.set_ylabel('Residuals', fontsize='small')
        ax1.set_xlabel(r'q ($\mathrm{\AA^{-1}}$)', fontsize='small')
        ax1.tick_params(labelsize='x-small')


        # canvas.SetBackgroundColour('white')
        fig.subplots_adjust(left = 0.2, bottom = 0.15, right = 0.95, top = 0.95)
        # fig.set_facecolor('white')

        canvas.draw()

        return canvas

    def createStatsPlot(self):
        color = SASUtils.update_mpl_style()

        fig = Figure((3.25,2.5))
        canvas = FigureCanvasWxAgg(self, -1, fig)

        self.figures.append(fig)

        chi = self.denss_results[5]
        rg = self.denss_results[6]
        vol = self.denss_results[7]

        ax0 = fig.add_subplot(311)
        ax0.plot(chi[chi>0])
        ax0.set_ylabel('$\chi^2$', fontsize='small')
        ax0.semilogy()
        ax0.tick_params(labelbottom=False, labelsize='x-small')

        ax1 = fig.add_subplot(312)
        ax1.plot(rg[rg!=0])
        ax1.set_ylabel('Rg', fontsize='small')
        ax1.tick_params(labelbottom=False, labelsize='x-small')

        ax2 = fig.add_subplot(313)
        ax2.plot(vol[vol>0])
        ax2.set_xlabel('Step', fontsize='small')
        ax2.set_ylabel('Support Volume ($\mathrm{\AA^{3}}$)', fontsize='small')
        ax2.semilogy()
        ax2.tick_params(labelsize='x-small')

        # canvas.SetBackgroundColour('white')
        fig.subplots_adjust(left = 0.2, bottom = 0.15, right = 0.95, top = 0.95)
        # fig.set_facecolor('white')

        canvas.draw()

        return canvas

class DenssAveragePlotPanel(wx.Panel):

    def __init__(self, parent, settings, average_results):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BG_STYLE_SYSTEM
            |wx.RAISED_BORDER)

        self.denss_settings = settings
        self.avg_results = average_results

        self.figures = []

        self.fsc_canvas = self.createFSCPlot()

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.fsc_canvas, 1, wx.GROW)

        self.SetSizer(sizer)

    def updateColors(self):
        color = SASUtils.update_mpl_style()
        # self.ax0_hline.set_color(color)
        # for plot in self.fsc_plots:
        #     plot.set_color(color)
        self.fsc_canvas.draw()

    def createFSCPlot(self):
        color = SASUtils.update_mpl_style()

        fig = Figure((3.25,2.5))
        canvas = FigureCanvasWxAgg(self, -1, fig)

        self.figures.append(fig)

        res = self.avg_results['fsc'][:, 0]
        fsc = self.avg_results['fsc'][:, 1]
        full_fsc = self.avg_results['fsc']
        fscs = self.avg_results['fscs']
        resn = self.avg_results['res']

        x = np.linspace(full_fsc[0,0],full_fsc[-1,0],100)
        y = np.interp(x, full_fsc[:,0], full_fsc[:,1])
        resi = np.argmin(y>=0.5)
        resx = np.interp(0.5,[y[resi+1],y[resi]],[x[resi+1],x[resi]])

        ax0 = fig.add_subplot(111)
        self.ax0_hline = ax0.axhline(0.5, color=color, linestyle='--')
        self.fsc_plots = []
        for i in range(fscs.shape[0]):
            new_plot = ax0.plot(fscs[i,:,0],fscs[i,:,1],color=color, linestyle='--',alpha=0.1)[0]
            self.fsc_plots.append(new_plot)

        ax0.plot(res, fsc, 'bo-')
        ax0.plot([resx],[0.5],'ro',label='Resolution = '+str(resn)+r'$\mathrm{\AA}$')
        ax0.set_xlabel('Resolution ($\\AA^{-1}$)', fontsize='small')
        ax0.set_ylabel('Fourier Shell Correlation', fontsize='small')
        ax0.tick_params(labelsize='x-small')
        ax0.legend(fontsize='small')

        # canvas.SetBackgroundColour('white')
        fig.subplots_adjust(left = 0.1, bottom = 0.12, right = 0.95, top = 0.95)
        # fig.set_facecolor('white')

        canvas.draw()

        return canvas


class DenssAlignFrame(wx.Frame):

    def __init__(self, parent, title):
        client_display = wx.GetClientDisplayRect()
        size = (min(450, client_display.Width), min(450, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.template_file_name = None
        self.target_file_name = None
        self.denss_thread = None
        self.abort_event = threading.Event()
        self.read_semaphore = threading.BoundedSemaphore(1)
        self.out_queue = queue.Queue()

        if platform.system() == 'Darwin' and six.PY3:
            self.single_proc = True
        else:
            self.single_proc = False

        self._createLayout()

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()

        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        panel = wx.Panel(self, wx.ID_ANY, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.template_file = wx.TextCtrl(panel)
        self.target_file = wx.TextCtrl(panel)

        self.template_select = wx.Button(panel, label='Select', style=wx.TE_READONLY)
        self.target_select = wx.Button(panel, label='Select', style=wx.TE_READONLY)

        self.template_select.Bind(wx.EVT_BUTTON, self._onSelectFile)
        self.target_select.Bind(wx.EVT_BUTTON, self._onSelectFile)

        file_sizer = wx.FlexGridSizer(cols=3, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        file_sizer.Add(wx.StaticText(panel, label='Reference (mrc or pdb):'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        file_sizer.Add(self.template_file, flag=wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        file_sizer.Add(self.template_select, flag=wx.ALIGN_CENTER_VERTICAL)
        file_sizer.Add(wx.StaticText(panel, label='Target (mrc):'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        file_sizer.Add(self.target_file, flag=wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        file_sizer.Add(self.target_select)
        file_sizer.AddGrowableCol(1)

        adv_pane = wx.CollapsiblePane(panel, label="Advanced Settings",
            style=wx.CP_NO_TLW_RESIZE)
        adv_pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        adv_win = adv_pane.GetPane()

        self.enantiomorphs = wx.Choice(adv_win, choices=['True', 'False'])
        self.enantiomorphs.SetSelection(0)

        if self.single_proc:
            nprocs = 1
        else:
            nprocs = multiprocessing.cpu_count()
            self.my_manager = multiprocessing.Manager()

        nprocs_choices = [str(i) for i in range(nprocs, 0, -1)]
        self.nprocs = wx.Choice(adv_win, choices = nprocs_choices)
        self.nprocs.SetSelection(len(nprocs_choices)-1)

        self.center = wx.Choice(adv_win, choices=['True', 'False'])
        self.center.SetSelection(0)

        self.resolution = wx.TextCtrl(adv_win, value='15.0',
            validator=RAWCustomCtrl.CharValidator('float'))

        adv_settings_sizer = wx.FlexGridSizer(cols=4, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))

        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Number of cores:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.nprocs, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Enantiomorphs:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.enantiomorphs, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Center reference:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.center, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='PDB calc resolution:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.resolution, flag=wx.ALIGN_CENTER_VERTICAL)

        adv_sizer = wx.BoxSizer(wx.HORIZONTAL)
        adv_sizer.Add(adv_settings_sizer, border=self._FromDIP(5), flag=wx.ALL)
        adv_sizer.AddStretchSpacer(1)

        adv_win.SetSizer(adv_sizer)

        self.start_button = wx.Button(panel, label='Start')
        self.abort_button = wx.Button(panel, label='Abort')

        self.start_button.Bind(wx.EVT_BUTTON, self.onStartButton)
        self.abort_button.Bind(wx.EVT_BUTTON, self.onAbortButton)
        self.abort_button.Disable()

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.start_button, flag=wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        button_sizer.Add(self.abort_button, flag=wx.RIGHT, border=self._FromDIP(5))

        self.status = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY)

        info_button = wx.Button(panel, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        savebutton = wx.Button(panel, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self._onCloseButton)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,1,wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(savebutton, 1, wx.RIGHT, border=self._FromDIP(5))

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(file_sizer, border=self._FromDIP(5), flag=wx.ALL
            |wx.EXPAND)
        panel_sizer.Add(adv_pane, border=self._FromDIP(5), flag=wx.ALL|wx.EXPAND)
        panel_sizer.Add(button_sizer, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.Add(self.status, proportion=1, border=self._FromDIP(5),
            flag=wx.ALL|wx.EXPAND)
        panel_sizer.Add(buttonSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))

        panel.SetSizer(panel_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        return top_sizer

    def onCollapse(self, event):
        self.Layout()
        self.Refresh()
        self.SendSizeEvent()

    def _getSettings(self):
        enantiomorphs = self.enantiomorphs.GetStringSelection()
        cores = int(self.nprocs.GetStringSelection())
        center = self.center.GetStringSelection()
        resolution = self.resolution.GetValue()

        if enantiomorphs == 'True':
            enantiomorphs = True
        else:
            enantiomorphs = False

        if center == 'True':
            center = True
        else:
            center = False

        error = False

        try:
            resolution = float(resolution)
        except Exception:
            resolution = None
            error = True
            msg = ('Resolution must be a number.')

        if not error:
            settings = {'cores' : cores,
                'enantiomer' : enantiomorphs,
                'center' : center,
                'resolution' : resolution,
                }
        else:
            dialog = wx.MessageDialog(self, msg, 'Error in DENSS Alignment parameters')
            dialog.ShowModal()
            settings = None
            dialog.Destroy()

        return settings

    def _onSelectFile(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        if evt.GetEventObject() == self.template_select:
            filters = 'PDB files (*.pdb)|*.pdb|MRC files (*.mrc)|*.mrc|All files (*.*)|*.*'
        else:
            filters = 'MRC files (*.mrc)|*.mrc|All files (*.*)|*.*'

        dialog = wx.FileDialog(self, 'Select a file', load_path, style=wx.FD_OPEN,
            wildcard=filters)

        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        # Destroy the dialog
        dialog.Destroy()

        if file is not None:
            if evt.GetEventObject() == self.template_select:
                self.template_file_name = file
                self.template_file.SetValue(os.path.split(file)[1])
                self.template_file.SetToolTip(wx.ToolTip(file))
            else:
                self.target_file_name = file
                self.target_file.SetValue(os.path.split(file)[1])
                self.target_file.SetToolTip(wx.ToolTip(file))

    def onStartButton(self, evt):
        self.abort_event.clear()
        run_denss = True

        refbasename, refext = os.path.splitext(self.template_file_name)
        refoutput = refbasename+"_centered.pdb"

        center = self.center.GetStringSelection()

        if center == 'True':
            center = True
        else:
            center = False

        if os.path.exists(refoutput) and center:
            msg = ('A file already exists in the template directory with the '
                'name {}. This will be replaced with the centered template file. '
                'Continue?'.format(os.path.split(refoutput)[1]))
            dialog = wx.MessageDialog(self, msg, "File will be overwritten",
                style=wx.YES_NO)

            result = dialog.ShowModal()

            if result == wx.ID_NO:
                run_denss = False

            dialog.Destroy()

        name, ext = os.path.splitext(self.target_file_name)
        outname = '{}_aligned{}'.format(name, ext)

        if os.path.exists(outname) and run_denss:
            msg = ('A file already exists in the target directory with the '
                'name {}. This will be replaced with the aligned file. '
                'Continue?'.format(os.path.split(outname)[1]))
            dialog = wx.MessageDialog(self, msg, "File will be overwritten",
                style=wx.YES_NO)

            result = dialog.ShowModal()

            if result == wx.ID_NO:
                run_denss = False

            dialog.Destroy()

        if run_denss:
            self.start_button.Disable()
            self.abort_button.Enable()
            self.status.SetValue('')

            self.denss_thread = threading.Thread(target=self.runAlign)
            self.denss_thread.daemon = True
            self.denss_thread.start()

    def get_multi_output(self, out_queue, den_window, stop_event, nmsg=1):
        num_msg = 0
        full_msg = ''
        while True:
            if stop_event.wait(0.001):
                try:
                    msg = out_queue.get_nowait()
                    full_msg = full_msg + msg
                except queue.Empty:
                    pass
                wx.CallAfter(den_window.AppendText, full_msg)
                break

            try:
                msg = out_queue.get_nowait()
                num_msg = num_msg + 1
                full_msg = full_msg + msg
            except queue.Empty:
                pass

            if num_msg == nmsg:
                wx.CallAfter(den_window.AppendText, full_msg)
                num_msg = 0
                full_msg = ''

    def runAlign(self):

        #Load target
        try:
            rho, side = DENSS.read_mrc(self.target_file_name)
        except Exception:
            msg = ("Couldn't load target file, please verify that it is a .mrc file.")
            wx.CallAfter(self.main_frame.showMessageDialog, self, msg,
                "Error running Alignment", wx.ICON_ERROR|wx.OK)

            self.abort_event.set()

            rho = None
            side = None

        if rho is not None:
            rhos = np.array([rho])
            sides = np.array([side])

        if not self.single_proc:
            avg_q = self.my_manager.Queue()
            stop_event = self.my_manager.Event()
        else:
            avg_q = queue.Queue()
            stop_event = threading.Event()

        stop_event.clear()

        comm_t = threading.Thread(target=self.get_multi_output,
            args=(avg_q, self.status, stop_event, 1))
        comm_t.daemon = True
        comm_t.start()

        settings = self._getSettings()

        if settings is not None and not self.abort_event.is_set():
            aligned, scores = DENSS.run_align(rhos, sides, self.template_file_name, avg_q,
                self.abort_event, single_proc=self.single_proc, **settings)
        else:
            aligned = None
            scores = None

        if self.abort_event.is_set():
            stop_event.set()
            wx.CallAfter(self.status.AppendText, 'Aborted!\n')

        elif aligned is not None:
            avg_q.put_nowait('Correlation score to reference: {:.3f}\n'.format(scores[0]))

            name, ext = os.path.splitext(self.target_file_name)
            outname = '{}_aligned{}'.format(name, ext)

            DENSS.write_mrc(aligned[0], sides[0], outname)

            avg_q.put_nowait('DENSS Alignment finished\n')

        else:
            avg_q.put_nowait('DENSS Alignment failed\n')

        stop_event.set()
        self.cleanupDENSS()

    def onAbortButton(self, evt):
        self.abort_event.set()

    def cleanupDENSS(self):
        self.start_button.Enable()
        self.abort_button.Disable()

    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = ('In addition to citing the RAW paper:\n If you use Denss '
        'in your work please cite the paper given here:\n'
        'https://www.nature.com/articles/nmeth.4581\n\n'
        'For more information about DENSS see:\n'
        'https://www.tdgrant.com/denss/')
        wx.MessageBox(str(msg), "How to cite Denss", style = wx.ICON_INFORMATION | wx.OK)

    def OnClose(self, event):

        self.Destroy()


class BIFTFrame(wx.Frame):

    def __init__(self, parent, title, sasm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = (min(800, client_display.Width), min(700, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.sasm = sasm

        panel = wx.Panel(self)

        splitter1 = wx.SplitterWindow(panel, wx.ID_ANY)

        sizer = wx.BoxSizer()
        sizer.Add(splitter1, 1, flag=wx.EXPAND)

        panel.SetSizer(sizer)

        self.plotPanel = IFTPlotPanel(splitter1, wx.ID_ANY)
        self.controlPanel = BIFTControlPanel(splitter1, wx.ID_ANY, sasm, manip_item)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(290))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(self._FromDIP(290))    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(self._FromDIP(50))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()
        self.Raise()

        self.Bind(wx.EVT_CLOSE, self._onClose)

        wx.CallLater(50, self.initBIFT)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()

    def initBIFT(self):
        self.controlPanel.runBIFT()

    def updateBIFTSettings(self):
        self.controlPanel.updateBIFTSettings()

    def _onClose(self, evt):
        self.close()

    def close(self):
        self.controlPanel.onClose()
        self.Destroy()

class BIFTControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, sasm, manip_item):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.bift_frame = parent.GetParent().GetParent()

        self.sasm = sasm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.bift_thread = None
        self.bift_abort = threading.Event()
        self.BIFT_queue = queue.Queue()

        self.old_analysis = {}

        # if platform.system() == 'Darwin' and six.PY3:
        #     self.single_proc = True
        # else:
        #     self.single_proc = False

        self.single_proc = True

        if 'BIFT' in self.sasm.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.sasm.getParameter('analysis')['BIFT'])

        self.bift_settings = {
            'npts'          : self.raw_settings.get('PrPoints'),
            'alpha_max'     : self.raw_settings.get('maxAlpha'),
            'alpha_min'     : self.raw_settings.get('minAlpha'),
            'alpha_n'       : self.raw_settings.get('AlphaPoints'),
            'dmax_min'      : self.raw_settings.get('maxDmax'),
            'dmax_max'      : self.raw_settings.get('minDmax'),
            'dmax_n'        : self.raw_settings.get('DmaxPoints'),
            'mc_runs'       : self.raw_settings.get('mcRuns'),
            'single_proc'   : self.single_proc,
            }


        self.infodata = {
            'dmax'         : ('Dmax :', self.NewControlId()),
            'dmax_err'     : ('Dmax :', self.NewControlId()),
            'alpha'        : ('Log(Alpha) :', self.NewControlId()),
            'alpha_err'    : ('Log(Alpha) :', self.NewControlId()),
            'guinierI0'    : ('I0 :', self.NewControlId()),
            'guinierRg'    : ('Rg :', self.NewControlId()),
            'guinierRg_err':('Rg Err. :', self.NewControlId()),
            'guinierI0_err':('I0 Err. :', self.NewControlId()),
            'biftI0'       : ('I0 :', self.NewControlId()),
            'biftRg'       : ('Rg :', self.NewControlId()),
            'biftI0_err'   : ('I0 Err. :', self.NewControlId()),
            'biftRg_err'   : ('Rg Err. :', self.NewControlId()),
            'chisq'        : ('Chi^2 (fit) :', self.NewControlId()),
            'evidence'     : ('Evidence :', self.NewControlId()),
            }

        self.statusIds = {  'status'      : self.NewControlId(),
            }

        self.buttonIds = {  'abort'     : self.NewControlId(),
                            'settings'  : self.NewControlId(),
                            'run'       : self.NewControlId()}


        self.iftm = None

        self.createLayout()

        self.initValues()

        self.BIFT_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onBIFTTimer, self.BIFT_timer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createLayout(self):
        info_button = wx.Button(self, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,0, wx.LEFT | wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(savebutton, 1, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(button, 1, wx.RIGHT, border=self._FromDIP(5))


        box2 = wx.StaticBox(self, -1, 'Control')
        ctrls = self.createControls(box2)
        ctrl_sizer = wx.StaticBoxSizer(box2, wx.VERTICAL)
        ctrl_sizer.Add(ctrls, 0, wx.EXPAND)


        box = wx.StaticBox(self, -1, 'Parameters')
        info = self.createInfoBox(box)
        info_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        info_sizer.Add(info, 0, wx.EXPAND)

        box3 = wx.StaticBox(self, -1, 'Status')
        status = self.createStatus(box3)
        status_sizer = wx.StaticBoxSizer(box3, wx.VERTICAL)
        status_sizer.Add(status, 0, wx.EXPAND)


        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self._FromDIP(5))
        bsizer.Add(ctrl_sizer, 0, wx.EXPAND, border=self._FromDIP(5))
        bsizer.Add(status_sizer, 0, wx.EXPAND | wx.TOP, border=self._FromDIP(5))
        bsizer.Add(info_sizer, 0, wx.EXPAND | wx.BOTTOM, border=self._FromDIP(5))
        bsizer.AddStretchSpacer(1)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL,
            border=self._FromDIP(5))

        self.SetSizer(bsizer)

    def createFileInfo(self):

        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(box, -1, '', style = wx.TE_READONLY)

        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND | wx.ALL,
            border=self._FromDIP(3))

        return boxsizer

    def createInfoBox(self, parent):

        rglabel = wx.StaticText(parent, -1, 'Rg (A)')
        i0label = wx.StaticText(parent, -1, 'I0')

        guinierlabel = wx.StaticText(parent, -1, 'Guinier :')
        self.guinierRg = wx.TextCtrl(parent, self.infodata['guinierRg'][1], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        self.guinierI0 = wx.TextCtrl(parent, self.infodata['guinierI0'][1], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)

        guinierlabel_err = wx.StaticText(parent, -1, 'Guinier Err. :')
        self.guinierRgErr = wx.TextCtrl(parent, self.infodata['guinierRg_err'][1],
            '', size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        self.guinierI0Err = wx.TextCtrl(parent, self.infodata['guinierI0_err'][1],
            '', size=self._FromDIP((80,-1)), style=wx.TE_READONLY)

        biftlabel = wx.StaticText(parent, -1, 'P(r) :')
        self.biftRg = wx.TextCtrl(parent, self.infodata['biftRg'][1], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        self.biftI0 = wx.TextCtrl(parent, self.infodata['biftI0'][1], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)

        biftlabel_err = wx.StaticText(parent, -1, 'P(r) Err. :')
        self.biftRgErr = wx.TextCtrl(parent, self.infodata['biftRg_err'][1], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)
        self.biftI0Err = wx.TextCtrl(parent, self.infodata['biftI0_err'][1], '',
            size=self._FromDIP((80,-1)), style=wx.TE_READONLY)

        sizer = wx.FlexGridSizer(rows=5, cols=3, hgap=self._FromDIP(5),
            vgap=self._FromDIP(2))
        sizer.Add((0,0))
        sizer.Add(rglabel, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))
        sizer.Add(i0label, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))
        sizer.Add(guinierlabel, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierRg, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierI0, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(guinierlabel_err, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierRgErr, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.guinierI0Err, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(biftlabel, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.biftRg, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.biftI0, 0,  wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(biftlabel_err, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.biftRgErr, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.biftI0Err, 0, wx.ALIGN_CENTER_VERTICAL)


        dmaxLabel = wx.StaticText(parent, -1, 'Dmax :')
        self.dmax = wx.TextCtrl(parent, self.infodata['dmax'][1], '',
            size=self._FromDIP((70,-1)), style=wx.TE_READONLY)
        self.dmax_err = wx.TextCtrl(parent, self.infodata['dmax_err'][1], '',
            size=self._FromDIP((70,-1)), style=wx.TE_READONLY)

        alphaLabel = wx.StaticText(parent, -1, 'Log(Alpha) :')
        self.alpha = wx.TextCtrl(parent, self.infodata['alpha'][1], '',
            size=self._FromDIP((70,-1)), style=wx.TE_READONLY)
        self.alpha_err = wx.TextCtrl(parent, self.infodata['alpha_err'][1], '',
            size=self._FromDIP((70,-1)), style=wx.TE_READONLY)

        chisqLabel = wx.StaticText(parent, -1, self.infodata['chisq'][0])
        self.chisq = wx.TextCtrl(parent, self.infodata['chisq'][1], '',
            size=self._FromDIP((70,-1)), style=wx.TE_READONLY)

        self.evidence = wx.TextCtrl(parent, self.infodata['evidence'][1], '',
            size=self._FromDIP((70,-1)), style=wx.TE_READONLY)

        sizer2 = wx.FlexGridSizer(rows=4, cols=4, hgap=self._FromDIP(5),
            vgap=self._FromDIP(2))
        sizer2.Add(dmaxLabel, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.dmax, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(wx.StaticText(parent, label='+/-'), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.dmax_err, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(alphaLabel, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.alpha, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(wx.StaticText(parent, label='+/-'), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.alpha_err, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(chisqLabel, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.chisq, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add((0,0))
        sizer2.Add((0,0))
        sizer2.Add(wx.StaticText(parent, label='Evidence :'), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.evidence, flag=wx.ALIGN_CENTER_VERTICAL)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer,0, wx.BOTTOM | wx.LEFT, self._FromDIP(5))
        top_sizer.Add(sizer2,0, wx.BOTTOM | wx.LEFT, self._FromDIP(5))

        return top_sizer

    def createControls(self, parent):

        sizer = wx.FlexGridSizer(rows=2, cols=4, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        sizer.AddGrowableCol(0)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableCol(2)
        sizer.AddGrowableCol(3)

        sizer.Add(wx.StaticText(parent,-1,'q_min'),1, wx.LEFT,
            border=self._FromDIP(3))
        sizer.Add(wx.StaticText(parent,-1,'n_min'),1)
        sizer.Add(wx.StaticText(parent,-1,'q_max'),1)
        sizer.Add(wx.StaticText(parent,-1,'n_max'),1)

        self.startSpin = RAWCustomCtrl.IntSpinCtrl(parent, size=self._FromDIP((60,-1)),
            min_val=0)
        self.endSpin = RAWCustomCtrl.IntSpinCtrl(parent, size=self._FromDIP((60,-1)),
            min_val=0)

        self.startSpin.SetValue(0)
        self.endSpin.SetValue(0)

        self.startSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.endSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)

        self.qstartTxt = wx.TextCtrl(parent, size=self._FromDIP((55, 22)),
            style=wx.TE_PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(parent, size=self._FromDIP((55, 22)),
            style=wx.TE_PROCESS_ENTER)

        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)

        sizer.Add(self.qstartTxt, 0, wx.EXPAND)
        sizer.Add(self.startSpin, 0, wx.EXPAND)
        sizer.Add(self.qendTxt, 0, wx.EXPAND)
        sizer.Add(self.endSpin, 0, wx.EXPAND)


        runButton = wx.Button(parent, self.buttonIds['run'], 'Run')
        runButton.Bind(wx.EVT_BUTTON, self.onRunButton)

        abortButton = wx.Button(parent, self.buttonIds['abort'], 'Abort')
        abortButton.Bind(wx.EVT_BUTTON, self.onAbortButton)

        advancedParams = wx.Button(parent, self.buttonIds['settings'], 'Settings')
        advancedParams.Bind(wx.EVT_BUTTON, self.onChangeParams)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(runButton, 0, wx.ALL, border=self._FromDIP(3))
        button_sizer.Add(abortButton, 0, wx.ALL, border=self._FromDIP(3))
        button_sizer.Add(advancedParams, 0, wx.ALL, border=self._FromDIP(3))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer, flag=wx.TOP, border=2)
        top_sizer.Add(button_sizer, flag=wx.TOP|wx.BOTTOM, border=self._FromDIP(2))

        return top_sizer

    def createStatus(self, parent):

        statusLabel = wx.StaticText(parent, -1, 'Status :')
        statusText = wx.StaticText(parent, self.statusIds['status'], '')
        statusText.SetForegroundColour('Red')

        statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        statusSizer.Add(statusLabel, 0, wx.RIGHT, border=self._FromDIP(3))
        statusSizer.Add(statusText, 0, wx.RIGHT, border=self._FromDIP(3))

        return statusSizer

    def initValues(self):
        analysis = self.sasm.getParameter('analysis')
        if 'guinier' in analysis:
            guinier = analysis['guinier']

            try:
                self.guinierRg.SetValue(self.formatNumStr(guinier['Rg']))
            except Exception:
                self.guinierRg.SetValue('')

            try:
                self.guinierRgErr.SetValue(self.formatNumStr(guinier['Rg_err']))
            except Exception:
                self.guinierRgErr.SetValue('')

            try:
                self.guinierI0.SetValue(self.formatNumStr(guinier['I0']))
            except Exception:
                self.guinierI0.SetValue('')

            try:
                self.guinierI0Err.SetValue(self.formatNumStr(guinier['I0_err']))
            except Exception:
                self.guinierI0Err.SetValue('')

        self.startSpin.SetRange((0, len(self.sasm.q)-2))
        self.endSpin.SetRange((1, len(self.sasm.q)-1))

        if 'BIFT' in analysis and 'qStart' in analysis['BIFT']:
            try:
                qmin = analysis['BIFT']['qStart']
                qmax = analysis['BIFT']['qEnd']

                findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
                closest_qmin = findClosest(qmin, self.sasm.q)
                closest_qmax = findClosest(qmax, self.sasm.q)

                nmin = np.where(self.sasm.q == closest_qmin)[0][0]
                nmax = np.where(self.sasm.q == closest_qmax)[0][0]+1
            except Exception:
                nmin, nmax = self.sasm.getQrange()

        elif 'guinier' in analysis:
            guinier = analysis['guinier']

            try:
                nmin = guinier['nStart']
                nmax = self.sasm.getQrange()[1]
            except Exception:
                nmin, nmax = self.sasm.getQrange()

        else:
            nmin, nmax = self.sasm.getQrange()

        i = self.sasm.i

        while i[nmin] == 0 and nmin < nmax-1:
            nmin = nmin + 1

        while i[nmax-1] == 0 and nmin + 1 < nmax-1:
            nmax = nmax - 1

        self.endSpin.SetValue(nmax-1)
        self.startSpin.SetValue(nmin)
        self.qendTxt.SetValue(str(round(self.sasm.q[nmax-1],4)))
        self.qstartTxt.SetValue(str(round(self.sasm.q[nmin],4)))

        self.old_nstart = nmin
        self.old_nend = nmax

        self.setFilename(os.path.basename(self.sasm.getParameter('filename')))

    def onSpinCtrl(self, evt):
        spin_ctrl = evt.GetEventObject()
        i = spin_ctrl.GetValue()

        #Make sure the boundaries don't cross:
        if spin_ctrl == self.startSpin:
            max_val = self.endSpin.GetValue()
            txt = self.qstartTxt

            if i > max_val-3:
                i = max_val - 3
                spin_ctrl.SetValue(i)

        elif spin_ctrl == self.endSpin:
            min_val = self.startSpin.GetValue()
            txt = self.qendTxt

            if i < min_val+3:
                i = min_val + 3
                spin_ctrl.SetValue(i)

        txt.SetValue(str(round(self.sasm.q[int(i)],4)))

        if spin_ctrl == self.startSpin:
            self.old_nstart = i
        elif spin_ctrl == self.endSpin:
            self.old_nend = i

    def onEnterInQlimits(self, evt):

        q = self.sasm.q

        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))

        txtctrl = evt.GetEventObject()

        #### If User inputs garbage: ####
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if txtctrl == self.qstartTxt:
                spinctrl = self.startSpin
            elif txtctrl == self.qendTxt:
                spinctrl = self.endSpin

            idx = int(spinctrl.GetValue())
            txtctrl.SetValue(str(round(self.sasm.q[idx],4)))
            return

        #################################

        closest = findClosest(val,q)

        i = np.where(q == closest)[0][0]

        if txtctrl == self.qstartTxt:

            n_max = self.endSpin.GetValue()

            if i > n_max-3:
                i = n_max - 3

            self.startSpin.SetValue(i)

        elif txtctrl == self.qendTxt:
            n_min = self.startSpin.GetValue()

            if i < n_min+3:
                i = n_min + 3

            self.endSpin.SetValue(i)

        txtctrl.SetValue(str(round(self.sasm.q[int(i)],4)))

        if txtctrl == self.qstartTxt:
            self.old_nstart = i
        elif txtctrl == self.qendTxt:
            self.old_nend = i

    def formatNumStr(self, val):
        val = float(val)

        if abs(val) > 1e3 or abs(val) < 1e-2:
            my_str = '%.2E' %(val)
        else:
            my_str = '%.4f' %(round(val,4))

        return my_str

    def onSaveInfo(self, evt):

        if self.iftm is not None:

            results_dict = {}

            start_idx = self.startSpin.GetValue()
            end_idx = self.endSpin.GetValue()

            results_dict['Dmax'] = str(self.iftm.getParameter('dmax'))
            results_dict['Dmax_Err'] = str(self.iftm.getParameter('dmaxer'))
            results_dict['Real_Space_Rg'] = str(self.iftm.getParameter('rg'))
            results_dict['Real_Space_Rg_Err'] = str(self.iftm.getParameter('rger'))
            results_dict['Real_Space_I0'] = str(self.iftm.getParameter('i0'))
            results_dict['Real_Space_I0_Err'] = str(self.iftm.getParameter('i0er'))
            results_dict['ChiSquared'] = str(self.iftm.getParameter('chisq'))
            results_dict['LogAlpha'] = str(self.iftm.getParameter('alpha'))
            results_dict['LogAlpha_Err'] = str(self.iftm.getParameter('alpha_er'))
            results_dict['Evidence'] = str(self.iftm.getParameter('evidence'))
            results_dict['Evidence_Err'] = str(self.iftm.getParameter('evidence_er'))
            results_dict['qStart'] = str(self.sasm.q[start_idx])
            results_dict['qEnd'] = str(self.sasm.q[end_idx])

            analysis_dict = self.sasm.getParameter('analysis')
            analysis_dict['BIFT'] = results_dict

            if self.manip_item is not None:
                if results_dict != self.old_analysis:
                    wx.CallAfter(self.manip_item.markAsModified)
                    wx.CallAfter(self.manip_item.updateInfoPanel)

        if self.BIFT_timer.IsRunning():
            self.BIFT_timer.Stop()
            self.bift_abort.set()

        if self.bift_thread is not None:
            self.bift_thread.join()

        if self.raw_settings.get('AutoSaveOnBift') and self.iftm is not None:
            if os.path.isdir(self.raw_settings.get('BiftFilePath')):
                RAWGlobals.mainworker_cmd_queue.put(['save_iftm', [self.iftm, self.raw_settings.get('BiftFilePath')]])
            else:
                self.raw_settings.set('AutoSaveOnBift', False)
                wx.CallAfter(wx.MessageBox, 'The folder:\n' +self.raw_settings.get('BiftFilePath')+ '\ncould not be found. Autosave of BIFT files has been disabled. If you are using a config file from a different computer please go into Advanced Options/Autosave to change the save folders, or save you config file to avoid this message next time.', 'Autosave Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

        if self.iftm is not None:
            RAWGlobals.mainworker_cmd_queue.put(['to_plot_ift', [self.iftm, 'blue', None, not self.raw_settings.get('AutoSaveOnBift')]])

        self.bift_frame.close()

    def onChangeParams(self, evt):
        self.main_frame.showOptionsDialog(focusHead='IFT')

    def onRunButton(self, evt):
        self.runBIFT()

    def onCloseButton(self, evt):
        self.onClose()
        self.bift_frame.close()

    def onClose(self):
        if self.BIFT_timer.IsRunning():
            self.BIFT_timer.Stop()
            self.bift_abort.set()

        if self.bift_thread is not None:
            self.bift_thread.join()

    def onAbortButton(self, evt):
        self.bift_abort.set()

    def _onInfoButton(self, evt):
        msg = ('If you use BIFT in your work, in addition to citing '
            'the RAW paper please cite:\nHansen, S. (2000). J. Appl. '
            'Cryst. 33, 1415-1421.')
        wx.MessageBox(str(msg), "How to cite BIFT", style = wx.ICON_INFORMATION | wx.OK)

    def updateBIFTInfo(self):
        if self.iftm is not None:
            rg = self.iftm.getParameter('rg')
            i0 = self.iftm.getParameter('i0')
            rger = self.iftm.getParameter('rger')
            i0er = self.iftm.getParameter('i0er')
            chisq = self.iftm.getParameter('chisq')
            dmax = self.iftm.getParameter('dmax')
            dmaxer = self.iftm.getParameter('dmaxer')
            alpha = self.iftm.getParameter('alpha')
            alphaer = self.iftm.getParameter('alpha_er')
            evidence = self.iftm.getParameter('evidence')

            self.biftRg.SetValue(self.formatNumStr(rg))
            self.biftRgErr.SetValue(self.formatNumStr(rger))
            self.biftI0.SetValue(self.formatNumStr(i0))
            self.biftI0Err.SetValue(self.formatNumStr(i0er))
            self.chisq.SetValue(self.formatNumStr(chisq))
            self.dmax.SetValue(self.formatNumStr(dmax))
            self.dmax_err.SetValue(self.formatNumStr(dmaxer))
            self.alpha.SetValue(self.formatNumStr(alpha))
            self.alpha_err.SetValue(self.formatNumStr(alphaer))
            self.evidence.SetValue(self.formatNumStr(evidence))

    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def updatePlot(self):

        self.bift_frame.plotPanel.plotPr(self.iftm)

    def updateBIFTSettings(self):
        self.old_settings = copy.deepcopy(self.bift_settings)

        self.bift_settings = {
            'npts'          : self.raw_settings.get('PrPoints'),
            'alpha_max'     : self.raw_settings.get('maxAlpha'),
            'alpha_min'     : self.raw_settings.get('minAlpha'),
            'alpha_n'       : self.raw_settings.get('AlphaPoints'),
            'dmax_min'      : self.raw_settings.get('maxDmax'),
            'dmax_max'      : self.raw_settings.get('minDmax'),
            'dmax_n'        : self.raw_settings.get('DmaxPoints'),
            'mc_runs'       : self.raw_settings.get('mcRuns'),
            'single_proc'   : self.single_proc,
            }

        if self.old_settings != self.bift_settings:
            self.runBIFT()

    def runBIFT(self):

        for key in self.buttonIds:
            if key not in ['abort']:
                wx.FindWindowById(self.buttonIds[key], self).Disable()
            else:
                wx.FindWindowById(self.buttonIds[key], self).Enable()

        self.bift_abort.clear()

        while not self.BIFT_queue.empty():
            self.BIFT_queue.get_nowait()

        self.BIFT_timer.Start(1)

        self.updateStatus({'status': 'Running grid search'})

        start = int(self.startSpin.GetValue())
        end = int(self.endSpin.GetValue())+1

        q = self.sasm.q[start:end]
        i = self.sasm.i[start:end]
        err = self.sasm.err[start:end]

        args = (q, i, err, self.sasm.getParameter('filename'))

        kwargs = copy.deepcopy(self.bift_settings)
        kwargs['queue'] = self.BIFT_queue
        kwargs['abort_check'] = self.bift_abort

        self.bift_thread = threading.Thread(target=self._runBIFT,
            args=(args, kwargs))
        self.bift_thread.daemon = True
        self.bift_thread.start()

    def _runBIFT(self, args, kwargs):
        iftm = BIFT.doBift(*args, **kwargs)

        if iftm is not None:
            self.iftm = iftm
            wx.CallAfter(self._onSuccess)

    def _onSuccess(self):
        self.updateStatus({'status' : 'BIFT done'})
        self.updatePlot()
        self.updateBIFTInfo()
        self.finishedProcessing()

        if self.BIFT_timer.IsRunning():
            self.BIFT_timer.Stop()


    def updateStatus(self, updates):
        for key in updates:
            if key in self.statusIds:
                if key == 'alpha':
                    wx.FindWindowById(self.statusIds[key], self).SetLabel(str(np.log(updates[key])))
                else:
                    wx.FindWindowById(self.statusIds[key], self).SetLabel(str(updates[key]))

    def clearStatus(self, exception_list):
        for key in self.statusIds:
            if key not in exception_list:
                wx.FindWindowById(self.statusIds[key], self).SetLabel('')

    def finishedProcessing(self):
        for key in self.buttonIds:
            if key not in ['abort']:
                wx.FindWindowById(self.buttonIds[key], self).Enable()
            else:
                wx.FindWindowById(self.buttonIds[key], self).Disable()

    def onBIFTTimer(self, evt):
        try:
            args = self.BIFT_queue.get_nowait()
            if 'update' in args:
                self.updateStatus(args['update'])

            elif 'failed' in args:
                self.updateStatus({'status' : 'BIFT failed'})
                self.clearStatus(['status'])
                self.finishedProcessing()

                if self.BIFT_timer.IsRunning():
                    self.BIFT_timer.Stop()

            elif 'canceled' in args:
                self.updateStatus({'status' : 'BIFT canceled'})
                self.clearStatus(['status'])
                self.finishedProcessing()

                if self.BIFT_timer.IsRunning():
                    self.BIFT_timer.Stop()


        except queue.Empty:
            pass


class AmbimeterFrame(wx.Frame):

    def __init__(self, parent, title, iftm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = (min(450, client_display.Width), min(450, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self.panel = wx.Panel(self, wx.ID_ANY, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.ids = {'input'         : self.NewControlId(),
                    'rg'            : self.NewControlId(),
                    'prefix'        : self.NewControlId(),
                    'files'         : self.NewControlId(),
                    'sRg'           : self.NewControlId(),
                    'save'          : self.NewControlId(),
                    'ambiCats'      : self.NewControlId(),
                    'ambiScore'     : self.NewControlId(),
                    'ambiEval'      : self.NewControlId()}


        self.ambi_settings = {}


        topsizer = self._createLayout(self.panel)
        self._initSettings()
        self._getSettings()


        self.panel.SetSizer(topsizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()

        self.Raise()

        self.showBusy()
        t = threading.Thread(target=self.runAmbimeter)
        t.daemon = True
        t.start()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        pass

    def _createLayout(self, parent):
        file_text = wx.StaticText(parent, -1, 'File :')
        file_ctrl = wx.TextCtrl(parent, self.ids['input'], '',
            size=self._FromDIP((150, -1)), style=wx.TE_READONLY)

        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        file_sizer.Add(file_text, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        file_sizer.Add(file_ctrl, 2, wx.ALL|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        file_sizer.AddStretchSpacer(1)

        rg_text = wx.StaticText(parent, -1, 'Rg :')
        rg_ctrl = wx.TextCtrl(parent, self.ids['rg'], '',
            size=self._FromDIP((60, -1)), style=wx.TE_READONLY)

        rg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rg_sizer.Add(rg_text, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        rg_sizer.Add(rg_ctrl, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        settings_box = wx.StaticBox(parent, -1, 'Controls')

        srg_text = wx.StaticText(settings_box, -1, 'Upper q*Rg limit (3 < q*Rg <7) :')
        srg_ctrl = wx.TextCtrl(settings_box, self.ids['sRg'], '4',
            size=self._FromDIP((60, -1)))
        srg_ctrl.Bind(wx.EVT_TEXT, self.onSrgText)

        srg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        srg_sizer.Add(srg_text, 0, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        srg_sizer.Add(srg_ctrl, 1, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))


        shape_text = wx.StaticText(settings_box, -1, 'Output shape(s) to save: ')
        shape_choice = wx.Choice(settings_box, self.ids['files'],
            choices=['None', 'Best', 'All'])
        shape_choice.SetSelection(0)

        shape_sizer = wx.BoxSizer(wx.HORIZONTAL)
        shape_sizer.Add(shape_text, 0, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        shape_sizer.Add(shape_choice, 0, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        savedir_text = wx.StaticText(settings_box, -1, 'Output directory :')
        savedir_ctrl = wx.TextCtrl(settings_box, self.ids['save'], '',
            size=self._FromDIP((350, -1)))

        try:
            savedir_ctrl.AutoCompleteDirectories() #compatability for older versions of wxpython
        except AttributeError as e:
            print(e)

        savedir_button = wx.Button(settings_box, -1, 'Select/Change Directory')
        savedir_button.Bind(wx.EVT_BUTTON, self.onChangeDirectoryButton)

        savedir_sizer = wx.BoxSizer(wx.VERTICAL)
        savedir_sizer.Add(savedir_text, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        savedir_sizer.Add(savedir_ctrl, 0, wx.TOP|wx.LEFT|wx.RIGHT| wx.EXPAND,
            border=self._FromDIP(5))
        savedir_sizer.Add(savedir_button, 0, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER,
            border=self._FromDIP(5))


        prefix_text = wx.StaticText(settings_box, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(settings_box, self.ids['prefix'], '',
            size=self._FromDIP((150, -1)))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        prefix_sizer.Add(prefix_ctrl, 2, wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        prefix_sizer.AddStretchSpacer(1)


        start_button = wx.Button(settings_box, -1, 'Run')
        start_button.Bind(wx.EVT_BUTTON, self.onStartButton)


        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        settings_sizer.Add(srg_sizer, 0)
        # settings_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER,
        #     border=self._FromDIP(5))
        settings_sizer.Add(shape_sizer, 0)
        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND)
        settings_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_CENTER,
            border=self._FromDIP(5))


        results_box = wx.StaticBox(parent, -1, 'Results')

        cats_text = wx.StaticText(results_box, -1, 'Number of compatible shape categories :')
        cats_ctrl = wx.TextCtrl(results_box, self.ids['ambiCats'], '',
            size=self._FromDIP((60, -1)), style=wx.TE_READONLY)

        cats_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cats_sizer.Add(cats_text, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        cats_sizer.Add(cats_ctrl, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))


        score_text = wx.StaticText(results_box, -1, 'Ambiguity score :')
        score_ctrl = wx.TextCtrl(results_box, self.ids['ambiScore'], '',
            size=self._FromDIP((60, -1)), style = wx.TE_READONLY)

        score_sizer = wx.BoxSizer(wx.HORIZONTAL)
        score_sizer.Add(score_text, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        score_sizer.Add(score_ctrl, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        eval_text = wx.StaticText(results_box, -1, 'AMBIMETER says :')
        eval_ctrl = wx.TextCtrl(results_box, self.ids['ambiEval'], '',
            size=self._FromDIP((250, -1)), style=wx.TE_READONLY)

        eval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        eval_sizer.Add(eval_text, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        eval_sizer.Add(eval_ctrl, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))


        results_sizer = wx.StaticBoxSizer(results_box, wx.VERTICAL)
        results_sizer.Add(cats_sizer, 0, flag=wx.TOP, border=self._FromDIP(5))
        # results_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER,
        #     border=self._FromDIP(5))
        results_sizer.Add(score_sizer, 0, flag=wx.TOP, border=self._FromDIP(5))
        results_sizer.Add(eval_sizer, 0, flag=wx.EXPAND|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(5))

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        savebutton = wx.Button(parent, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,1,wx.RIGHT,
            border=self._FromDIP(5))
        buttonSizer.Add(savebutton, 1, wx.RIGHT,
            border=self._FromDIP(5))
        buttonSizer.Add(button, 1)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(file_sizer, 0, wx.EXPAND)
        top_sizer.Add(rg_sizer, 0)
        top_sizer.Add(settings_sizer, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        top_sizer.Add(results_sizer, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        top_sizer.Add(buttonSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))


        return top_sizer

    def _initSettings(self):
        fname_window = wx.FindWindowById(self.ids['input'], self)
        fname_window.SetValue(self.iftm.getParameter('filename').replace(' ','_'))

        rg_window = wx.FindWindowById(self.ids['rg'], self)
        rg_window.SetValue(str(self.iftm.getParameter('rg')))

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        outdir_window = wx.FindWindowById(self.ids['save'], self)
        outdir_window.SetValue(path)

        outprefix_window = wx.FindWindowById(self.ids['prefix'], self)
        outprefix_window.SetValue(os.path.splitext(os.path.basename(self.iftm.getParameter('filename')))[0])

    def _getSettings(self):

        outdir_window = wx.FindWindowById(self.ids['save'], self)
        self.ambi_settings['path'] = outdir_window.GetValue()

        outprefix_window = wx.FindWindowById(self.ids['prefix'], self)
        self.ambi_settings['prefix'] = outprefix_window.GetValue()

        outsrg_window = wx.FindWindowById(self.ids['sRg'], self)
        self.ambi_settings['sRg'] = outsrg_window.GetValue()

        outfiles_window = wx.FindWindowById(self.ids['files'], self)
        self.ambi_settings['files'] = outfiles_window.GetStringSelection()


    def onStartButton(self, evt):
        self._getSettings()
        self.showBusy()
        t = threading.Thread(target=self.runAmbimeter)
        t.daemon = True
        t.start()


    def runAmbimeter(self):
        if self.ambi_settings['files'] == 'None':
            standard_paths = wx.StandardPaths.Get()
            path = standard_paths.GetTempDir()
        else:
            path = self.ambi_settings['path']

        outname = tempfile.NamedTemporaryFile(dir=path).name

        while os.path.isfile(outname):
            outname = tempfile.NamedTemporaryFile(dir=path).name

        outname = os.path.split(outname)[-1] + '.out'


        if self.main_frame.OnlineControl.isRunning() and path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False


        SASFileIO.writeOutFile(self.iftm, os.path.join(path, outname))

        try:
            output = SASCalc.runAmbimeter(outname,
                self.ambi_settings['prefix'].replace(' ','_'),
                self.ambi_settings, path, self.raw_settings.get('ATSASDir'))

        except SASExceptions.NoATSASError as e:
            wx.CallAfter(self.main_frame.showMessageDialog, self, str(e),
                "Error running Ambimeter", wx.ICON_ERROR|wx.OK)
            os.remove(os.path.join(path, outname))
            wx.CallAfter(self.showBusy, False)
            self.Close()
            return


        if os.path.isfile(os.path.join(path, outname)):
            try:
                os.remove(os.path.join(path, outname))
            except Exception:
                pass

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        wx.CallAfter(cats_window.SetValue, output[0])

        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        wx.CallAfter(score_window.SetValue, output[1])

        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        wx.CallAfter(eval_window.SetValue, output[2])

        wx.CallAfter(self.showBusy, False)

    def showBusy(self, show=True):
        if show:
            self.bi = wx.BusyInfo('Running AMBIMETER, please wait.', self)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save'], self).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)

        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save'], self).SetValue(new_path)

        dirdlg.Destroy()

    def onSrgText(self, evt):
        srg_ctrl = wx.FindWindowById(self.ids['sRg'], self)


        srg = srg_ctrl.GetValue()
        if srg != '' and not srg.isdigit():

            try:
                srg = float(srg.replace(',', '.'))
            except ValueError as e:
                print(e)
                srg = ''
            if srg != '':
                srg = str(float(srg))

            srg_ctrl.ChangeValue(srg)


    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = ('If you use AMBIMETER in your work, in addition '
            'to citing the RAW paper please cite:\nPetoukhov, '
            'M. V. & Svergun, D. I. (2015). Acta Cryst. D71, '
            '1051-1058.')
        wx.MessageBox(str(msg), "How to cite AMBIMETER", style = wx.ICON_INFORMATION | wx.OK)

    def onSaveInfo(self, evt):
        analysis_dict = {}

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        cats_val = cats_window.GetValue()

        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        score_val = score_window.GetValue()

        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        eval_val = eval_window.GetValue()

        try:
            cats_val = float(cats_val)
            score_val = float(score_val)

            analysis_dict['Shape_categories'] = cats_val
            analysis_dict['Ambiguity_score'] = score_val
            analysis_dict['Interp'] = eval_val

            self.iftm.setParameter('Ambimeter', analysis_dict)

            wx.CallAfter(self.manip_item.updateInfoPanel)

        except Exception:
            pass


        self.Close()


    def OnClose(self, event):

        self.Destroy()


class SupcombFrame(wx.Frame):

    def __init__(self, parent, title):
        client_display = wx.GetClientDisplayRect()
        size = (min(450, client_display.Width), min(450, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.template_file_name = None
        self.target_file_name = None
        self.supcomb_thread = None
        self.abort_event = threading.Event()
        self.read_semaphore = threading.BoundedSemaphore(1)
        self.out_queue = queue.Queue()

        self.standard_paths = wx.StandardPaths.Get()

        self._createLayout()

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()

        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        panel = wx.Panel(self, wx.ID_ANY, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.template_file = wx.TextCtrl(panel)
        self.target_file = wx.TextCtrl(panel)

        self.template_select = wx.Button(panel, label='Select', style=wx.TE_READONLY)
        self.target_select = wx.Button(panel, label='Select', style=wx.TE_READONLY)

        self.template_select.Bind(wx.EVT_BUTTON, self._onSelectFile)
        self.target_select.Bind(wx.EVT_BUTTON, self._onSelectFile)

        file_sizer = wx.FlexGridSizer(cols=3, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        file_sizer.Add(wx.StaticText(panel, label='Reference (pdb):'), flag=wx.ALIGN_CENTER_VERTICAL)
        file_sizer.Add(self.template_file, flag=wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        file_sizer.Add(self.template_select, flag=wx.ALIGN_CENTER_VERTICAL)
        file_sizer.Add(wx.StaticText(panel, label='Target (pdb):'), flag=wx.ALIGN_CENTER_VERTICAL)
        file_sizer.Add(self.target_file, flag=wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        file_sizer.Add(self.target_select)
        file_sizer.AddGrowableCol(1)

        adv_panel = wx.CollapsiblePane(panel, label="Advanced Settings",
            style=wx.CP_NO_TLW_RESIZE)
        adv_panel.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        adv_win = adv_panel.GetPane()

        self.mode = wx.Choice(adv_win, choices=['fast', 'slow'])
        self.mode.SetSelection(0)

        self.superposition = wx.Choice(adv_win, choices=['ALL', 'BACKBONE'])
        self.superposition.SetSelection(0)

        self.enantiomorphs = wx.Choice(adv_win, choices=['YES', 'NO'])
        self.enantiomorphs.SetSelection(0)

        self.proximity = wx.Choice(adv_win, choices=['NSD', 'VOL'])
        self.proximity.SetSelection(0)

        self.fraction = wx.TextCtrl(adv_win, validator=RAWCustomCtrl.CharValidator('float'))
        self.fraction.SetValue('1.0')

        sym_choices = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
            'P10', 'P11', 'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18',
            'P19', 'P22', 'P32', 'P42', 'P52', 'P62', 'P72', 'P82', 'P92',
            'P102', 'P112', 'P122', 'P23', 'P432', 'PICO']
        self.symmetry = wx.Choice(adv_win, choices=sym_choices)
        self.symmetry.SetSelection(0)

        adv_settings_sizer = wx.FlexGridSizer(cols=4, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Mode:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.mode, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Superposition:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.superposition, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Enantiomorphs:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.enantiomorphs, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Proximity:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.proximity, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Fraction:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.fraction, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(wx.StaticText(adv_win, label='Symmetry:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_settings_sizer.Add(self.symmetry, flag=wx.ALIGN_CENTER_VERTICAL)

        adv_sizer = wx.BoxSizer(wx.HORIZONTAL)
        adv_sizer.Add(adv_settings_sizer, border=self._FromDIP(5), flag=wx.ALL)
        adv_sizer.AddStretchSpacer(1)

        adv_win.SetSizer(adv_sizer)

        self.start_button = wx.Button(panel, label='Start')
        self.abort_button = wx.Button(panel, label='Abort')

        self.start_button.Bind(wx.EVT_BUTTON, self.onStartButton)
        self.abort_button.Bind(wx.EVT_BUTTON, self.onAbortButton)
        self.abort_button.Disable()

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.start_button, flag=wx.ALL)
        button_sizer.Add(self.abort_button, flag=wx.ALL)

        self.status = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY)

        info_button = wx.Button(panel, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        savebutton = wx.Button(panel, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self._onCloseButton)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,1,wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(savebutton, 1)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(file_sizer, border=self._FromDIP(5), flag=wx.ALL|wx.EXPAND)
        panel_sizer.Add(adv_panel, border=self._FromDIP(5), flag=wx.ALL|wx.EXPAND)
        panel_sizer.Add(button_sizer, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.Add(self.status, proportion=1, border=self._FromDIP(5),
            flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.EXPAND)
        panel_sizer.Add(buttonSizer, 0, wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT
            |wx.ALIGN_CENTER_HORIZONTAL, border=self._FromDIP(5))

        panel.SetSizer(panel_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        return top_sizer

    def onCollapse(self, event):
        self.Layout()
        self.Refresh()
        self.SendSizeEvent()

    def _getSettings(self):
        mode = self.mode.GetStringSelection()
        superposition = self.superposition.GetStringSelection()
        enantiomorphs = self.enantiomorphs.GetStringSelection()
        proximity = self.proximity.GetStringSelection()
        symmetry = self.symmetry.GetStringSelection()

        error = False
        try:
            fraction = float(self.fraction.GetValue())
        except Exception:
            fraction = None
            error = True
            msg = ('Fraction must be a number between 0 and 1.0.')

        if isinstance(fraction, float):
            if fraction < 0 or fraction > 1:
                error = True
                msg = ('Fraction must be a number between 0 and 1.0.')

        if symmetry != 'P1' and mode == 'fast':
            error = True
            msg = ('Slow mode must be used to aply symmetry constraints.')

        if not error:
            settings = {'mode'  : mode,
                'superposition' : superposition,
                'enantiomorphs' : enantiomorphs,
                'proximity'     : proximity,
                'symmetry'      : symmetry,
                'fraction'      : fraction,
                }
        else:
            dialog = wx.MessageDialog(self, msg, 'Error in SUPCOMB parameters')
            dialog.ShowModal()
            settings = None
            dialog.Destroy()

        return settings

    def _onSelectFile(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        filters = 'PDB and CIF files (*.pdb;*.cif)|*.pdb;*.cif|All files (*.*)|*.*'

        dialog = wx.FileDialog(self, 'Select a file', load_path, style=wx.FD_OPEN,
            wildcard=filters)

        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        # Destroy the dialog
        dialog.Destroy()

        if file is not None:
            if evt.GetEventObject() == self.template_select:
                self.template_file_name = file
                self.template_file.SetValue(os.path.split(file)[1])
                self.template_file.SetToolTip(wx.ToolTip(file))
            else:
                self.target_file_name = file
                self.target_file.SetValue(os.path.split(file)[1])
                self.target_file.SetToolTip(wx.ToolTip(file))

    def onStartButton(self, evt):
        self.abort_event.clear()

        name, ext = os.path.splitext(self.target_file_name)
        outname = '{}_aligned{}'.format(name, ext)

        run_supcomb = True

        if os.path.exists(outname):
            msg = ('A file already exists in the target directory with the '
                'name {}. This will be replaced with the aligned file. '
                'Continue?'.format(os.path.split(outname)[1]))
            dialog = wx.MessageDialog(self, msg, "File will be overwritten",
                style=wx.YES_NO)

            result = dialog.ShowModal()

            if result == wx.ID_NO:
                run_supcomb = False

            dialog.Destroy()

        if run_supcomb:
            self.start_button.Disable()
            self.abort_button.Enable()
            self.status.SetValue('')

            self.supcomb_thread = threading.Thread(target=self.runSupcomb)
            self.supcomb_thread.daemon = True
            self.supcomb_thread.start()

    def enqueue_output(self, out, queue):
        with self.read_semaphore:
            line = 'test'
            line2=''
            while line != '':
                line = out.read(1)

                if not isinstance(line, str):
                    line = str(line, encoding='UTF-8')

                line2 += line
                if line == '\n':
                    queue.put_nowait([line2])
                    line2=''
                time.sleep(0.00001)

            line = out.read()

            if not isinstance(line, str):
                line = str(line, encoding='UTF-8')

            line2 += line
            queue.put_nowait([line2])

    def runSupcomb(self):
        tempdir = self.standard_paths.GetTempDir()
        template_tempname = os.path.join(tempdir, os.path.split(self.template_file_name)[1])
        target_tempname = os.path.join(tempdir, os.path.split(self.target_file_name)[1])

        shutil.copy(self.template_file_name, template_tempname)
        shutil.copy(self.target_file_name, target_tempname)

        path, template = os.path.split(template_tempname)
        target = os.path.split(target_tempname)[1]

        settings = self._getSettings()

        if self.abort_event.is_set():
            wx.CallAfter(self.status.AppendText, 'Aborted!\n')

        if settings is not None and not self.abort_event.is_set():
            sup_proc = SASCalc.runSupcomb(template, target, path,
                self.raw_settings.get('ATSASDir'), **settings)
        else:
            sup_proc = None

        if sup_proc is None and not self.abort_event.is_set() and settings is not None:
            wx.CallAfter(self.status.AppendText, 'SUPCOMB failed to start')

        else:
            readout_t = threading.Thread(target=self.enqueue_output,
                args=(sup_proc.stdout, self.out_queue))
            readout_t.daemon = True
            readout_t.start()


            #Send the damaver output to the screen.
            while sup_proc.poll() is None:
                if self.abort_event.is_set():
                    sup_proc.terminate()
                    wx.CallAfter(self.status.AppendText, '\nAborted!')
                try:
                    new_text = self.out_queue.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(self.status.AppendText, new_text)
                except queue.Empty:
                    pass
                time.sleep(0.01)

            if not self.abort_event.is_set():
                time.sleep(2)
                with self.read_semaphore: #see if there's any last data that we missed
                    while True:
                        try:
                            new_text = self.out_queue.get_nowait()
                            new_text = new_text[0]

                            if new_text != '':
                                wx.CallAfter(self.status.AppendText, new_text)

                        except queue.Empty:
                            break

                    new_text = sup_proc.stdout.read()

                    if not isinstance(new_text, str):
                        new_text = str(new_text, encoding='UTF-8')

                    if new_text != '':
                        wx.CallAfter(self.status.AppendText, new_text)

                name, ext = os.path.splitext(target_tempname)
                temp_outname = '{}_aligned{}'.format(name, ext)

                name, ext = os.path.splitext(self.target_file_name)
                outname = '{}_aligned{}'.format(name, ext)

                if os.path.exists(temp_outname):
                    shutil.copy(temp_outname, outname)
                    wx.CallAfter(self.status.AppendText, '\nSUPCOMB finished')
                else:
                    wx.CallAfter(self.status.AppendText, '\nSUPCOMB failed')

                try:
                    os.remove(template_tempname)
                    os.remove(target_tempname)
                except Exception:
                    pass

        self.cleanupSupcomb()

    def onAbortButton(self, evt):
        self.abort_event.set()

    def cleanupSupcomb(self):
        self.start_button.Enable()
        self.abort_button.Disable()

    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = ('If you use SUPCOMB in your work, in addition '
            'to citing the RAW paper please cite:\nM.Kozin & D.Svergun (2001) '
            'Automated matching of high- and low-resolution structural models. '
            ' J Appl Cryst. 34, 33-41.')
        wx.MessageBox(str(msg), "How to cite SUPCOMB", style=wx.ICON_INFORMATION|wx.OK)

    def OnClose(self, event):

        self.Destroy()



class SVDFrame(wx.Frame):

    def __init__(self, parent, title, secm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = size = (min(950, client_display.Width), min(750, client_display.Height))

        self.secm = secm
        self.manip_item = manip_item

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self._Layout()

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()
        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()
        self.controlPanel.updateColors()

    def _Layout(self):
        panel = wx.Panel(self)
        splitter1 = wx.SplitterWindow(panel)

        copy_secm = copy.copy(self.secm)

        self.plotPanel = SVDResultsPlotPanel(splitter1, wx.ID_ANY)
        self.controlPanel = SVDControlPanel(splitter1, wx.ID_ANY, copy_secm,
            self.manip_item, self, 'SVD')

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(325))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(self._FromDIP(325))    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(self._FromDIP(50))

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + self._FromDIP(20)
                self.SetSize(self._FromDIP(size))

        splitter1.Layout()

        button = wx.Button(panel, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self._onCancelButton)

        savebutton = wx.Button(panel, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self._onOkButton)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, border=self._FromDIP(5))
        buttonSizer.Add(button, 1)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(splitter1, 1, flag=wx.EXPAND)
        panel_sizer.Add(buttonSizer, flag=wx.TOP|wx.BOTTOM|wx.LEFT,
            border=self._FromDIP(3))
        panel.SetSizer(panel_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

    def OnClose(self):

        self.Destroy()

    def _onCancelButton(self, evt):
        self.OnClose()

    def _onOkButton(self, evt):
        svd_dict = {}
        for key in self.controlPanel.control_ids:
            window = (wx.FindWindowById(self.controlPanel.control_ids[key],
                self.controlPanel))

            if window is not None:
                if key != 'profile':
                    svd_dict[key] = window.GetValue()
                else:
                    svd_dict[key] = window.GetStringSelection()


        analysis_dict = self.secm.getParameter('analysis')

        if 'svd' in analysis_dict:
            old_svd_dict = analysis_dict['svd']
        else:
            old_svd_dict = {}

        if old_svd_dict == svd_dict:
            modified = False
        else:
            modified = True

        analysis_dict['svd'] = svd_dict

        self.secm.setParameter('analysis', analysis_dict)

        if self.manip_item is not None:
            if modified:
                self.manip_item.markAsModified()

        self.OnClose()

    def plotSVD(self, svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor,
        svd_start,  svd_end):
        self.plotPanel.plotSVD( svd_U, svd_s, svd_V, svd_U_autocor,
            svd_V_autocor, svd_start,  svd_end)


class SVDResultsPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id):

        SASUtils.update_mpl_style()

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.svd = None

        subplotLabels = [('Singular Values', 'Index', 'Value', .1),
            ('AutoCorrelation', 'Index', 'Absolute Value', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1,
                title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93,
            top = 0.93, hspace = 0.26)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateColors(self):
        SASUtils.update_mpl_style()
        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Singular Values']
        b = self.subplots['AutoCorrelation']

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plotSVD(self, svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, svd_start, svd_end):
        index = np.arange(len(svd_s))

        self.updateDataPlot(index, svd_s, svd_U_autocor, svd_V_autocor, svd_start, svd_end)

    def updateDataPlot(self, index, svd_s, svd_U_autocor, svd_V_autocor, svd_start, svd_end):

        #Save for resizing:
        self.orig_index = index
        self.orig_svd_s = svd_s
        self.orig_svd_U_autocor = svd_U_autocor
        self.orig_svd_V_autocor = svd_V_autocor
        self.orig_svd_start = svd_start
        self.orig_svd_end = svd_end


        a = self.subplots['Singular Values']
        b = self.subplots['AutoCorrelation']

        xdata = index[svd_start:svd_end+1]
        ydata1 = svd_s[svd_start:svd_end+1]
        ydata2 = svd_U_autocor[svd_start:svd_end+1]
        ydata3 = svd_V_autocor[svd_start:svd_end+1]

        if self.svd is None:
            self.svd, = a.semilogy(xdata, ydata1, 'r.-', animated = True)

            self.u_autocor, = b.plot(xdata, ydata2, 'r.-', label = 'U (Left singular vectors)', animated = True)
            self.v_autocor, = b.plot(xdata, ydata3, 'b.-', label = 'V (Right singular vectors)', animated = True)
            b.legend(fontsize = 12)

            #self.lim_back_line, = a.plot([x_lim_back, x_lim_back], [y_lim_back-0.2, y_lim_back+0.2], transform=a.transAxes, animated = True)

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)
        else:
            self.svd.set_xdata(xdata)
            self.svd.set_ydata(ydata1)

            self.u_autocor.set_xdata(xdata)
            self.u_autocor.set_ydata(ydata2)

            self.v_autocor.set_xdata(xdata)
            self.v_autocor.set_ydata(ydata3)

        self.autoscale_plot()


    def redrawLines(self):
        a = self.subplots['Singular Values']
        b = self.subplots['AutoCorrelation']

        if self.svd is not None:
            self.canvas.restore_region(self.background)
            a.draw_artist(self.svd)

            #restore white background in error plot and draw new error:
            self.canvas.restore_region(self.err_background)
            b.draw_artist(self.u_autocor)
            b.draw_artist(self.v_autocor)

            self.canvas.blit(a.bbox)
            self.canvas.blit(b.bbox)

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplots['Singular Values'], self.subplots['AutoCorrelation']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()


class SVDSECPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, svd = False):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        SASUtils.update_mpl_style()

        if ((int(matplotlib.__version__.split('.')[0]) == 1
            and int(matplotlib.__version__.split('.')[1]) >= 5)
            or int(matplotlib.__version__.split('.')[0]) > 1):
            self.fig = Figure((4,4), 75)
        else:
            if not svd:
                self.fig = Figure((300./75,4), 75)
            else:
                self.fig = Figure((250./75,4), 75)

        self.secm = None

        subplotLabels = [('SECPlot', 'Index', 'Intensity', .1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1,
                label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.18, bottom = 0.13, right = 0.93,
            top = 0.93, hspace = 0.26)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateColors(self):
        SASUtils.update_mpl_style()
        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['SECPlot']

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plotSECM(self, secm, framei, framef, ydata_type):
        frame_list = secm.plot_frame_list

        if ydata_type == 'q_val':
            intensity = secm.I_of_q
        elif ydata_type == 'mean':
            intensity = secm.mean_i
        elif ydata_type == 'q_range':
            intensity = secm.qrange_I
        else:
            intensity = secm.total_i

        self.updateDataPlot(frame_list, intensity, framei, framef)

    def updateDataPlot(self, frame_list, intensity, framei, framef):

        #Save for resizing:
        self.orig_frame_list = frame_list
        self.orig_intensity = intensity
        self.orig_framei = framei
        self.orig_framef = framef

        a = self.subplots['SECPlot']

        if self.secm is None:
            self.secm, = a.plot(frame_list, intensity, 'r.-', animated = True)

            self.cut_line, = a.plot(frame_list[framei:framef+1],
                intensity[framei:framef+1], 'b.-', animated = True)

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.background = self.canvas.copy_from_bbox(a.bbox)
        else:
            self.secm.set_ydata(intensity)
            self.secm.set_xdata(frame_list)

            #Error lines:
            self.cut_line.set_ydata(intensity[framei:framef+1])
            self.cut_line.set_xdata(frame_list[framei:framef+1])

        self.autoscale_plot()

    def redrawLines(self):
        if self.secm is not None:
            a = self.subplots['SECPlot']

            self.canvas.restore_region(self.background)

            a.draw_artist(self.secm)
            a.draw_artist(self.cut_line)

            self.canvas.blit(a.bbox)

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplots['SECPlot']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()


class SVDControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, secm, manip_item, top_frame, ctrl_type):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.top_frame = top_frame
        self.ctrl_type = ctrl_type

        self.secm = secm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.control_ids = {'profile'   : self.NewControlId(),
                            'fstart'    : self.NewControlId(),
                            'fend'      : self.NewControlId(),
                            'svd_start' : self.NewControlId(),
                            'svd_end'   : self.NewControlId(),
                            'input'     : self.NewControlId(),
                            'norm_data' : self.NewControlId()}

        self.field_ids = {'fname'     : self.NewControlId()}

        self.button_ids = {'save_svd'   : self.NewControlId(),
                            'save_all'  : self.NewControlId()}

        self.ydata_type = 'total'

        self.svd_U = None
        self.svd_s = None
        self.svd_V = None

        control_sizer = self._createLayout()

        self.SetSizer(control_sizer)

        self.initValues()

        self.results = {
            'profile'        : '',
            'fstart'        : 0,
            'fend'          : 0,
            'svd_start'     : 0,
            'svd_end'       : 0,
            'input'         : 0,
            'int'           : [],
            'err'           : [],
            'svd_u'         : [],
            'svd_s'         : [],
            'svd_v'         : [],
            'svd_int_norm'  : [],
            'secm_choice'   : 'sub',
            'sub_secm'      : None,
            'bl_secm'       : None,
            'ydata_type'    : 'Total',
            'filename'      : '',
            'q'             : [],
            }

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.sec_plot.updateColors()

    def _createLayout(self):

        top_sizer =wx.BoxSizer(wx.VERTICAL)

        #filename sizer
        box = wx.StaticBox(self, -1, 'Filename')
        filesizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        filenameTxtCtrl = wx.TextCtrl(box, self.field_ids['fname'], '',
            style = wx.TE_READONLY)

        filesizer.Add(filenameTxtCtrl, 1, wx.ALL, border=self._FromDIP(3))


        #svd controls
        ctrl_box = wx.StaticBox(self, -1, 'Controls')
        control_sizer = wx.StaticBoxSizer(ctrl_box, wx.VERTICAL)

        #control if you're using unsubtracted or subtracted curves
        choices = ['Unsubtracted']
        if self.secm.subtracted_sasm_list:
            choices.append('Subtracted')
        if self.secm.baseline_subtracted_sasm_list:
            choices.append('Baseline Corrected')

        label = wx.StaticText(ctrl_box, -1, 'Use:')
        profile_type = wx.Choice(ctrl_box, self.control_ids['profile'], choices = choices)
        profile_type.Bind(wx.EVT_CHOICE, self._onProfileChoice)

        if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
            if 'Subtracted' in choices:
                profile_type.SetStringSelection('Subtracted')
            else:
                profile_type.SetStringSelection('Unsubtracted')
        else:
            profile_type.SetStringSelection('Unsubtracted')

        profile_sizer = wx.BoxSizer(wx.HORIZONTAL)
        profile_sizer.Add(label, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(3))
        profile_sizer.Add(profile_type, 1, wx.RIGHT, border=self._FromDIP(3))

        #control what the range of curves you're using is.
        label1 = wx.StaticText(ctrl_box, -1, 'Use Frames:')
        label2 = wx.StaticText(ctrl_box, -1, 'to')
        start_frame = RAWCustomCtrl.IntSpinCtrl(ctrl_box, self.control_ids['fstart'],
            size=self._FromDIP((60,-1)))
        end_frame = RAWCustomCtrl.IntSpinCtrl(ctrl_box, self.control_ids['fend'],
            size=self._FromDIP((60,-1)))

        start_frame.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeFrame)
        end_frame.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeFrame)

        frame_sizer = wx.BoxSizer(wx.HORIZONTAL)
        frame_sizer.Add(label1, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(3))
        frame_sizer.Add(start_frame, 0, wx.RIGHT, border=self._FromDIP(3))
        frame_sizer.Add(label2, 0, wx.RIGHT, border=self._FromDIP(3))
        frame_sizer.Add(end_frame, 0, wx.RIGHT, border=self._FromDIP(3))


        if self.ctrl_type == 'SVD':
            norm_data = wx.CheckBox(ctrl_box, self.control_ids['norm_data'],
                'Normalize by uncertainty')
            norm_data.SetValue(True)
            norm_data.Bind(wx.EVT_CHECKBOX, self._onNormChoice)

        #plot the sec data
        self.sec_plot = SVDSECPlotPanel(ctrl_box, wx.ID_ANY)


        #SVD control sizer
        control_sizer.Add(profile_sizer, 0,  wx.TOP | wx.EXPAND,
            border=self._FromDIP(3))
        control_sizer.Add(frame_sizer, 0, wx.TOP | wx.EXPAND,
            border=self._FromDIP(8))
        if self.ctrl_type == 'SVD':
            control_sizer.Add(norm_data, 0, wx.TOP | wx.EXPAND,
                border=self._FromDIP(8))
        control_sizer.Add(self.sec_plot, 0, wx.TOP | wx.EXPAND,
            border=self._FromDIP(8))

        if self.manip_item is None:
            control_sizer.Hide(profile_sizer, recursive = True)

        #svd results
        results_box = wx.StaticBox(self, -1, 'Results')
        results_sizer = wx.StaticBoxSizer(results_box, wx.VERTICAL)

        #Control plotted SVD range
        label1 = wx.StaticText(results_box, -1, 'Plot indexes:')
        label2 = wx.StaticText(results_box, -1, 'to')
        start_svd = RAWCustomCtrl.IntSpinCtrl(results_box, self.control_ids['svd_start'],
            size=self._FromDIP((60,-1)))
        end_svd = RAWCustomCtrl.IntSpinCtrl(results_box, self.control_ids['svd_end'],
            size=self._FromDIP((60,-1)))

        start_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)
        end_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)

        svdrange_sizer = wx.BoxSizer(wx.HORIZONTAL)
        svdrange_sizer.Add(label1, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(3))
        svdrange_sizer.Add(start_svd, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(3))
        svdrange_sizer.Add(label2, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(3))
        svdrange_sizer.Add(end_svd, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(3))


        if self.ctrl_type == 'SVD':
            #Save SVD info
            save_svd_auto = wx.Button(results_box, self.button_ids['save_svd'],
                'Save Plotted Values')
            save_svd_auto.Bind(wx.EVT_BUTTON, self._onSaveButton)

            save_svd_all = wx.Button(results_box, self.button_ids['save_all'], 'Save All')
            save_svd_all.Bind(wx.EVT_BUTTON, self._onSaveButton)

            svd_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            svd_button_sizer.Add(save_svd_auto, 1, wx.LEFT | wx.RIGHT,
                border=self._FromDIP(3))
            svd_button_sizer.Add(save_svd_all, 1, wx.RIGHT, border=self._FromDIP(3))


        results_sizer.Add(svdrange_sizer, 0,  wx.TOP | wx.EXPAND,
            border=self._FromDIP(3))

        if self.ctrl_type == 'SVD':
            results_sizer.Add(svd_button_sizer,0, wx.TOP | wx.EXPAND,
                border=self._FromDIP(3))

        if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
            #Input number of significant values to use for EFA or REGALS
            input_box = wx.StaticBox(self, -1, 'User Input')
            input_sizer = wx.StaticBoxSizer(input_box, wx.VERTICAL)

            sub_sizer = wx.BoxSizer(wx.HORIZONTAL)

            label1 = wx.StaticText(input_box, -1, '# Significant SVs:')
            user_input = RAWCustomCtrl.IntSpinCtrl(input_box, self.control_ids['input'],
                size=self._FromDIP((60,-1)))


            sub_sizer.Add(label1, 0, wx.LEFT|wx.TOP|wx.BOTTOM
                |wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(3))
            sub_sizer.Add(user_input, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL,
                border=self._FromDIP(3))
            sub_sizer.AddStretchSpacer(1)

            input_sizer.Add(sub_sizer, flag=wx.EXPAND)


            if self.ctrl_type == 'REGALS':
                sub_sizer2 = wx.BoxSizer(wx.HORIZONTAL)

                self.regals_exp_type = wx.Choice(input_box, choices=['IEC/SEC-SAXS',
                    'Titration', 'TR-SAXS', 'Other'])
                self.regals_exp_type.SetSelection(0)

                sub_sizer2.Add(wx.StaticText(input_box, label='Experiment type:'), 0,
                    wx.LEFT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL,
                    border=self._FromDIP(3))
                sub_sizer2.Add(self.regals_exp_type, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL,
                    border=self._FromDIP(3))
                sub_sizer2.AddStretchSpacer(1)


                sub_sizer3 = wx.BoxSizer(wx.HORIZONTAL)

                self.regals_use_efa = wx.CheckBox(input_box,
                    label='Use EFA to find component ranges')
                self.regals_use_efa.SetValue(True)

                sub_sizer3.Add(self.regals_use_efa, border=self._FromDIP(3),
                    flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL)

                input_sizer.Add(sub_sizer2, flag=wx.TOP|wx.EXPAND,
                    border=self._FromDIP(3))
                input_sizer.Add(sub_sizer3)


        top_sizer.Add(filesizer, 0, wx.EXPAND | wx.TOP, border=self._FromDIP(3))
        top_sizer.Add(control_sizer, 0, wx.EXPAND | wx.TOP, border=self._FromDIP(3))
        top_sizer.Add(results_sizer, 0, wx.EXPAND | wx.TOP, border=self._FromDIP(3))

        if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
            top_sizer.Add(input_sizer, 0, wx.TOP | wx.BOTTOM | wx.EXPAND,
                border=self._FromDIP(3))

        top_sizer.AddStretchSpacer(1)

        return top_sizer


    def initValues(self):

        filename = self.secm.getParameter('filename')

        filename_window = wx.FindWindowById(self.field_ids['fname'], self)
        filename_window.SetValue(filename)

        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window =wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

        if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
            user_input_window = wx.FindWindowById(self.control_ids['input'], self)


        framei = self.secm.plot_frame_list[0]
        framef = self.secm.plot_frame_list[-1]

        framei_window.SetRange((framei, framef))
        framef_window.SetRange((framei, framef))

        svd_start_window.SetRange((0, framef-framei-1))
        svd_end_window.SetRange((1, framef-framei))

        svd_start_window.SetValue(0)
        svd_end_window.SetValue(min(framef-framei, 10))

        if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
            user_input_window.SetValue(0)
            user_input_window.SetRange((0, framef-framei))

        analysis_dict = self.secm.getParameter('analysis')

        if self.ctrl_type == 'SVD':
            if 'svd' in analysis_dict:
                analysis = analysis_dict['svd']
            else:
                analysis = None

        if self.ctrl_type == 'EFA':
            if 'efa' in analysis_dict:
                analysis = analysis_dict['efa']
            else:
                analysis = None

        if self.ctrl_type == 'REGALS':
            if 'regals' in analysis_dict:
                analysis = analysis_dict['regals']
            else:
                analysis = None

        if analysis is None:
            if len(self.secm.subtracted_sasm_list)>0 and len(np.where(self.secm.use_subtracted_sasm)[0]) > 0:
                frame_start = max(np.where(self.secm.use_subtracted_sasm)[0][0]-100, framei)
                frame_end = min(np.where(self.secm.use_subtracted_sasm)[0][-1]+100, framef)

            else:
                frame_start = framei
                frame_end = framef

            framei_window.SetValue(frame_start)
            framef_window.SetValue(frame_end)

        else:
            for key in analysis:
                if key == 'profile':
                    wx.FindWindowById(self.control_ids[key], self).SetStringSelection(analysis[key])
                elif key == 'nsvs':
                    wx.FindWindowById(self.control_ids['input'], self).SetValue(analysis[key])
                elif key in self.control_ids:
                     wx.FindWindowById(self.control_ids[key], self).SetValue(analysis[key])
                elif key == 'exp_type':
                    self.regals_exp_type.SetStringSelection(analysis[key])
                elif key == 'use_efa':
                    self.regals_use_efa.SetValue(analysis[key])

        #make a subtracted profile SECM
        if len(self.secm.subtracted_sasm_list)>0:
            self.subtracted_secm = SECM.SECM(self.secm._file_list,
                self.secm.subtracted_sasm_list, self.secm.plot_frame_list,
                self.secm.getAllParameters(), self.raw_settings)
        else:
            self.subtracted_secm = SECM.SECM(self.secm._file_list,
                self.secm.subtracted_sasm_list, [],
                self.secm.getAllParameters(), self.raw_settings)

            profile_window = wx.FindWindowById(self.control_ids['profile'], self)
            profile_window.SetStringSelection('Unsubtracted')

        if self.secm.baseline_subtracted_sasm_list:
            self.bl_subtracted_secm = SECM.SECM(self.secm._file_list,
                self.secm.baseline_subtracted_sasm_list, self.secm.plot_frame_list,
                self.secm.getAllParameters(), self.raw_settings)
        else:
            self.bl_subtracted_secm = SECM.SECM(self.secm._file_list,
                self.secm.baseline_subtracted_sasm_list, [],
                self.secm.getAllParameters(), self.raw_settings)

        if self.manip_item is not None:
            sec_plot_panel = wx.FindWindowByName('SECPlotPanel')

            self.ydata_type = sec_plot_panel.plotparams['y_axis_display']

            if self.ydata_type == 'q_val':
                q=float(sec_plot_panel.plotparams['secm_plot_q'])
                self.subtracted_secm.I(q)
                self.bl_subtracted_secm.I(q)

            elif self.ydata_type == 'q_range':
                qrange = sec_plot_panel.plotparams['secm_plot_qrange']
                self.subtracted_secm.calc_qrange_I(qrange)
                self.bl_subtracted_secm.calc_qrange_I(qrange)

        self.updateSECPlot()

        self.runSVD()

        if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
            if self.svd_U is not None:
                #Attempts to figure out the significant number of singular values
                if user_input_window.GetValue() == 0:
                    svals = SASCalc.findSignificantSingularValues(self.svd_s,
                        self.svd_U_autocor, self.svd_V_autocor)

                    user_input_window.SetValue(svals)


    #This function is called when the profiles used are changed between subtracted and unsubtracted.
    def _onProfileChoice(self, evt):
        wx.CallAfter(self.updateSECPlot)
        self.runSVD()

    #This function is called when the start and end frame range spin controls are modified
    def _onChangeFrame(self, evt):
        my_id = evt.GetId()

        spin = wx.FindWindowById(my_id, self)

        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'], self)
        fend_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

        #Make sure the boundaries don't cross:
        if my_id == self.control_ids['fstart']:
            max_val = fend_window.GetValue()

            if new_val > max_val-1:
                new_val = max_val - 1
                spin.SetValue(new_val)

        elif my_id == self.control_ids['fend']:
            min_val = fstart_window.GetValue()

            if new_val < min_val+1:
                new_val = min_val + 1
                spin.SetValue(new_val)

        svd_min = svd_start_window.GetValue()
        svd_max = svd_end_window.GetValue()
        tot = fend_window.GetValue()-fstart_window.GetValue()

        if svd_max > tot:
            svd_end_window.SetValue(tot)

        if svd_min > tot:
            svd_start_window.SetValue(tot-1)

        wx.CallAfter(self.updateSECPlot)

        self.runSVD()

    def _onChangeSVD(self, evt):
        my_id = evt.GetId()

        spin = wx.FindWindowById(my_id, self)

        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'], self)
        fend_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        #Make sure the boundaries don't cross:
        if my_id == self.control_ids['svd_start']:
            max_val = svd_end_window.GetValue()

            tot = fend_window.GetValue()-fstart_window.GetValue()

            if new_val > tot - 1:
                new_val = tot - 1
                spin.SetValue(new_val)

            elif new_val > max_val-1:
                new_val = max_val - 1
                spin.SetValue(new_val)

        elif my_id == self.control_ids['svd_end']:
            min_val = svd_start_window.GetValue()

            tot = fend_window.GetValue()-fstart_window.GetValue()

            if new_val > tot:
                new_val = tot
                spin.SetValue(new_val)

            elif new_val < min_val+1:
                new_val = min_val + 1
                spin.SetValue(new_val)

        wx.CallAfter(self.updateSVDPlot)

    def _onNormChoice(self, evt):
        wx.CallAfter(self.runSVD)

    def runSVD(self):
        profile_window = wx.FindWindowById(self.control_ids['profile'], self)

        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        if self.ctrl_type == 'SVD':
            err_norm = wx.FindWindowById(self.control_ids['norm_data'], self).GetValue()
        else:
            err_norm = True

        if profile_window.GetStringSelection() == 'Unsubtracted':
            secm = self.secm
        elif profile_window.GetStringSelection() == 'Subtracted':
            secm = self.subtracted_secm
        elif profile_window.GetStringSelection() == 'Baseline Corrected':
            secm = self.bl_subtracted_secm

        try:
            sasm_list = secm.getSASMList(framei, framef)
        except SASExceptions.DataNotCompatible as e:
            msg = e.parameter
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)
            sasm_list = []

        (self.svd_U, self.svd_s, self.svd_V, self.svd_U_autocor,
            self.svd_V_autocor, self.i, self.err, self.svd_a,
            success) = SASCalc.SVDOnSASMs(sasm_list, err_norm)

        if not success:
            if self.ctrl_type == 'EFA' or self.ctrl_type == 'REGALS':
                msg = ('Initial SVD failed, so {} analysis cannot '
                    'continue.'.format(self.ctrl_type))
            else:
                msg = ('SVD failed.')

            wx.CallAfter(wx.MessageBox, msg, 'SVD Failed.', style = wx.ICON_ERROR | wx.OK)

        else:
            wx.CallAfter(self.updateSVDPlot)

    def updateSECPlot(self):
        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        profile_window = wx.FindWindowById(self.control_ids['profile'], self)

        if profile_window.GetStringSelection() == 'Unsubtracted':
            self.sec_plot.plotSECM(self.secm, framei, framef, self.ydata_type)
        elif profile_window.GetStringSelection() == 'Subtracted':
            self.sec_plot.plotSECM(self.subtracted_secm, framei, framef, self.ydata_type)
        elif profile_window.GetStringSelection() == 'Baseline Corrected':
            self.sec_plot.plotSECM(self.bl_subtracted_secm, framei, framef, self.ydata_type)

    def updateSVDPlot(self):

        if self.svd_s is not None and not np.any(np.isnan(self.svd_s)):
            svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
            svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

            svd_start = svd_start_window.GetValue()
            svd_end = svd_end_window.GetValue()

            self.top_frame.plotSVD(self.svd_U, self.svd_s, self.svd_V,
                self.svd_U_autocor, self.svd_V_autocor, svd_start, svd_end)


    def getSignificant(self):
        return wx.FindWindowById(self.control_ids['input'], self).GetValue()

    def setSignificant(self, nvals):
        wx.FindWindowById(self.control_ids['input'], self).SetValue(nvals)

    def _onSaveButton(self, evt):
        if evt.GetId() == self.button_ids['save_svd']:
            self.saveSV()
        elif evt.GetId() == self.button_ids['save_all']:
            self.saveAll()

    def saveSV(self):
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        path = str(dirctrl.getDirLabel())

        filename_window = wx.FindWindowById(self.field_ids['fname'], self)
        filename = filename_window.GetValue()

        name, ext = os.path.splitext(filename)

        filename = name + '_sv.csv'

        dialog = wx.FileDialog(self, message=("Please select save directory "
            "and enter save file name"), style=wx.FD_SAVE, defaultDir=path,
            defaultFile=filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name + '.csv'
            dialog.Destroy()
        else:
            dialog.Destroy()
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving SVD data', 0)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()

        data = np.column_stack((self.svd_s[svd_start:svd_end+1],
            self.svd_U_autocor[svd_start:svd_end+1],
            self.svd_V_autocor[svd_start:svd_end+1]))

        header = 'Singular_values,U_Autocorrelation,V_Autocorrelation'

        SASFileIO.saveCSVFile(save_path, data, header)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)

    def saveAll(self):
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        path = str(dirctrl.getDirLabel())

        filename_window = wx.FindWindowById(self.field_ids['fname'], self)
        filename = filename_window.GetValue()

        name, ext = os.path.splitext(filename)

        filename = name + '_svd_all.csv'

        dialog = wx.FileDialog(self, message=("Please select save directory "
            "and enter save file name"), style=wx.FD_SAVE, defaultDir=path,
            defaultFile=filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name + '.csv'
            dialog.Destroy()
        else:
            dialog.Destroy()
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving SVD data', 0)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()

        svd_data = np.column_stack((self.svd_s[svd_start:svd_end+1],
            self.svd_U_autocor[svd_start:svd_end+1],
            self.svd_V_autocor[svd_start:svd_end+1]))

        u_data = self.svd_U[:,svd_start:svd_end+1]
        v_data = self.svd_V[:,svd_start:svd_end+1]

        SASFileIO.saveSVDData(save_path, svd_data, u_data, v_data)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)

    def getResults(self):
        for key in self.results:
            if key in self.control_ids:
                window = wx.FindWindowById(self.control_ids[key], self)

                if key != 'profile':
                    value = window.GetValue()

                else:
                    value = window.GetStringSelection()

            elif key == 'int':
                value = self.i

            elif key == 'err':
                value = self.err

            elif key == 'svd_u':
                value = self.svd_U

            elif key == 'svd_s':
                value = self.svd_s

            elif key == 'svd_v':
                value = self.svd_V

            elif key == 'svd_int_norm':
                value = self.svd_a

            elif key =='secm_choice':
                profile_window = wx.FindWindowById(self.control_ids['profile'], self)
                profile_type = profile_window.GetStringSelection()

                if profile_type == 'Unsubtracted':
                    value = 'usub'
                elif profile_type == 'Subtracted':
                    value = 'sub'
                elif profile_type == 'Basline Corrected':
                    value = 'bl'

            elif key == 'sub_secm':
                value = self.subtracted_secm

            elif key == 'bl_secm':
                value = self.bl_subtracted_secm

            elif key == 'ydata_type':
                value = self.ydata_type

            elif key == 'filename':
                filename_window = wx.FindWindowById(self.field_ids['fname'], self)
                value = filename_window.GetValue()

            elif key == 'q':
                profile_window = wx.FindWindowById(self.control_ids['profile'], self)
                profile_type = profile_window.GetStringSelection()

                if profile_type == 'Unsubtracted':
                    value = self.secm.getSASM().getQ()
                elif profile_type == 'Subtracted':
                    value = self.subtracted_secm.getSASM().getQ()
                elif profile_type == 'Baseline Corrected':
                    value = self.bl_subtracted_secm.getSASM().getQ()

            self.results[key] = value

        if self.ctrl_type == 'REGALS':
            self.results['exp_type'] = self.regals_exp_type.GetStringSelection()
            self.results['use_efa'] = self.regals_use_efa.GetValue()

        return self.results



class EFAFrame(wx.Frame):

    def __init__(self, parent, title, secm, manip_item):

        client_display = wx.GetClientDisplayRect()
        size = (min(950, client_display.Width), min(800, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.orig_secm = secm

        self.secm = copy.deepcopy(secm)
        self.manip_item = manip_item

        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.splitter_ids = {1  : self.NewControlId(),
                            2   : self.NewControlId(),
                            3   : self.NewControlId()}

        self.old_svd_input = -1

        self.current_panel = 1

        self._createLayout(self.panel)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()
        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel1.updateColors()
        self.controlPanel1.updateColors()
        self.plotPanel2.updateColors()
        self.plotPanel3.updateColors()
        self.controlPanel3.updateColors()

    def _createLayout(self, parent):

        #Creating the first EFA analysis panel
        self.splitter1 = wx.SplitterWindow(parent, self.splitter_ids[1])

        self.plotPanel1 = SVDResultsPlotPanel(self.splitter1, wx.ID_ANY)
        self.controlPanel1 = SVDControlPanel(self.splitter1, wx.ID_ANY,
            self.secm, self.manip_item, self, 'EFA')

        self.splitter1.SplitVertically(self.controlPanel1, self.plotPanel1, self._FromDIP(325))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter1.SetMinimumPaneSize(self._FromDIP(325))    #Back compatability with older wxpython versions
        else:
            self.splitter1.SetMinimumPaneSize(self._FromDIP(50))

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + self._FromDIP(20)
                self.SetSize(self._FromDIP(size))


        self.splitter2 = wx.SplitterWindow(parent, self.splitter_ids[2])

        self.plotPanel2 = EFAResultsPlotPanel2(self.splitter2, -1)
        self.controlPanel2 = EFAControlPanel2(self.splitter2, -1, self.secm,
            self.manip_item, self, 'EFA')

        self.splitter2.SplitVertically(self.controlPanel2, self.plotPanel2, self._FromDIP(325))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter2.SetMinimumPaneSize(self._FromDIP(325))    #Back compatability with older wxpython versions
        else:
            self.splitter2.SetMinimumPaneSize(self._FromDIP(50))

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.splitter2.Fit()


        self.splitter3 = wx.SplitterWindow(parent, self.splitter_ids[3])

        self.plotPanel3 = EFAResultsPlotPanel3(self.splitter3, -1)
        self.controlPanel3 = EFAControlPanel3(self.splitter3, -1, self.secm, self.manip_item)

        self.splitter3.SplitVertically(self.controlPanel3, self.plotPanel3, self._FromDIP(325))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter3.SetMinimumPaneSize(self._FromDIP(325))    #Back compatability with older wxpython versions
        else:
            self.splitter3.SetMinimumPaneSize(self._FromDIP(50))

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.splitter3.Fit()


        #Creating the fixed buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.next_button = wx.Button(parent, -1, 'Next')
        self.next_button.Bind(wx.EVT_BUTTON, self._onNextButton)

        self.back_button = wx.Button(parent, -1, 'Back')
        self.back_button.Bind(wx.EVT_BUTTON, self._onBackButton)
        self.back_button.Disable()

        self.cancel_button = wx.Button(parent, -1, 'Cancel')
        self.cancel_button.Bind(wx.EVT_BUTTON, self._onCancelButton)

        self.done_button = wx.Button(parent, -1, 'Done')
        self.done_button.Bind(wx.EVT_BUTTON, self._onDoneButton)
        self.done_button.Disable()

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer.Add(self.cancel_button, 0 , wx.LEFT, border=self._FromDIP(3))
        button_sizer.Add(self.done_button, 0, wx.LEFT, border=self._FromDIP(3))
        button_sizer.Add(info_button, 0, wx.LEFT, border=self._FromDIP(3))
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.back_button, 0, wx.RIGHT, border=self._FromDIP(3))
        button_sizer.Add(self.next_button, 0, wx.RIGHT, border=self._FromDIP(3))

        sl = wx.StaticLine(parent, wx.ID_ANY, style=wx.LI_HORIZONTAL)

        self.top_sizer = wx.BoxSizer(wx.VERTICAL)
        self.top_sizer.Add(self.splitter1, 1, wx.EXPAND | wx.BOTTOM,
            border=self._FromDIP(3))
        self.top_sizer.Add(self.splitter2, 1, wx.EXPAND | wx.BOTTOM,
            border=self._FromDIP(3))
        self.top_sizer.Add(self.splitter3, 1, wx.EXPAND | wx.BOTTOM,
            border=self._FromDIP(3))
        self.top_sizer.Add(sl, 0, wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self._FromDIP(3))
        self.top_sizer.Add(button_sizer, 0, wx.TOP|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(3))


        self.top_sizer.Hide(self.splitter2, recursive = True)
        self.top_sizer.Hide(self.splitter3, recursive = True)

        self.panel.SetSizer(self.top_sizer)

        # self.panel.Layout()
        # self.SendSizeEvent()
        # self.panel.Layout()

    def _onNextButton(self, evt):

        if self.current_panel == 1:

            self.getPanel1Values()

            if self.panel1_results['input'] != 0:

                if (self.panel1_results['svd_u'] is not None
                    and not np.any(np.isnan(self.panel1_results['svd_u']))):

                    self.top_sizer.Hide(wx.FindWindowById(
                        self.splitter_ids[self.current_panel], self),
                        recursive = True)

                    self.top_sizer.Show(wx.FindWindowById(
                        self.splitter_ids[self.current_panel+1], self),
                        recursive = True)

                    self.current_panel = self.current_panel + 1

                    self.back_button.Enable()

                    self.plotPanel2.refresh_display()

                    if not self.controlPanel2.initialized:
                        self.controlPanel2.initialize(self.panel1_results)

                    elif (self.panel1_results['fstart'] != self.controlPanel2.panel1_results['fstart']
                        or self.panel1_results['fend'] != self.controlPanel2.panel1_results['fend']
                        or self.panel1_results['profile'] != self.controlPanel2.panel1_results['profile']):
                        self.controlPanel2.reinitialize(self.panel1_results, efa = True)

                    elif  self.panel1_results['input'] != self.controlPanel2.panel1_results['input']:
                        self.controlPanel2.reinitialize(self.panel1_results, efa = False)

                else:
                    msg = ('SVD not successful. Either change data range '
                        'or type, or select a new data set.')
                    dlg = wx.MessageDialog(self, msg, "No Singular Values Found",
                        style = wx.ICON_INFORMATION | wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()

            else:
                msg = ('Please enter the number of significant singular '
                    'values to use for the evolving factor analysis in '
                    'the User Input area.')
                dlg = wx.MessageDialog(self, msg, "No Singular Values Selected",
                    style = wx.ICON_INFORMATION | wx.OK)
                dlg.ShowModal()
                dlg.Destroy()

            if self.panel1_results['input'] != self.old_svd_input:
                self.old_svd_input = self.panel1_results['input']
                self.controlPanel3.converged = False
                self.controlPanel3.rotation_data = {}

        elif self.current_panel == 2:

            self.getPanel2Values()

            correct = np.all([point[0] < point[1] for point in self.panel2_results['points']])

            if correct:

                self.top_sizer.Hide(wx.FindWindowById(
                    self.splitter_ids[self.current_panel], self),
                recursive = True)

                self.top_sizer.Show(wx.FindWindowById(
                    self.splitter_ids[self.current_panel+1], self),
                     recursive = True)

                self.current_panel = self.current_panel + 1

                self.next_button.Disable()

                self.done_button.Enable()

                self.plotPanel3.refresh_display()

                if not self.controlPanel3.initialized:
                    self.controlPanel3.initialize(self.panel1_results,
                        self.panel2_results)

                elif (self.panel1_results['fstart'] != self.controlPanel3.panel1_results['fstart']
                    or self.panel1_results['fend'] != self.controlPanel3.panel1_results['fend']
                    or self.panel1_results['profile'] != self.controlPanel3.panel1_results['profile']
                    or self.panel1_results['input'] != self.controlPanel3.panel1_results['input']):
                    self.controlPanel3.reinitialize(self.panel1_results,
                        self.panel2_results, rebuild = True)

                elif  np.any(self.panel2_results['points'] != self.controlPanel3._getRanges()):
                    self.controlPanel3.reinitialize(self.panel1_results,
                        self.panel2_results, rebuild = False)

            else:
                msg = ('The smallest start value must be less than the smallest '
                    'end value, the second smallest start value must be less '
                    'than the second smallest end value, and so on. Please '
                    'change start and end values according (if necessary, you '
                    'can further adjust these ranges on the next page).')
                dlg = wx.MessageDialog(self, msg, "Start and End Values Incorrect",
                    style = wx.ICON_INFORMATION | wx.OK)
                dlg.ShowModal()
                dlg.Destroy()


        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

    def _onBackButton(self, evt):

        if self.current_panel == 2:
            self.top_sizer.Hide(wx.FindWindowById(
                self.splitter_ids[self.current_panel], self),
                recursive = True)

            self.top_sizer.Show(wx.FindWindowById(
                self.splitter_ids[self.current_panel-1], self),
                recursive = True)

            self.current_panel = self.current_panel - 1

            self.back_button.Disable()

        elif self.current_panel == 3:
            self.top_sizer.Hide(wx.FindWindowById(
                self.splitter_ids[self.current_panel], self),
            recursive = True)

            self.top_sizer.Show(wx.FindWindowById(
                self.splitter_ids[self.current_panel-1], self),
            recursive = True)

            self.current_panel = self.current_panel - 1

            self.next_button.Enable()

            self.done_button.Disable()

            points = self.controlPanel3._getRanges()

            if  np.any(self.panel2_results['points'] != points):
                forward_sv = points[:,0]
                backward_sv = points[:,1]

                if (np.all(np.sort(forward_sv) == forward_sv)
                    and np.all(np.sort(backward_sv) == backward_sv)):
                    self.controlPanel2.setSVs(points)


        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

    def _onCancelButton(self, evt):
        self.OnClose()

    def _onDoneButton(self, evt):
        self.getPanel3Values()

        if self.panel3_results['converged']:
            RAWGlobals.mainworker_cmd_queue.put(['to_plot_sasm', [self.panel3_results['profiles'], 'black', None, True, 2]])


        if self.manip_item is not None:
            analysis_dict = self.orig_secm.getParameter('analysis')

            efa_dict = {}

            efa_dict['fstart'] = self.panel1_results['fstart']
            efa_dict['fend'] = self.panel1_results['fend']
            efa_dict['profile'] = self.panel1_results['profile']
            efa_dict['nsvs'] = self.panel1_results['input']
            efa_dict['ranges'] = self.panel3_results['ranges']
            efa_dict['iter_limit'] = self.panel3_results['options']['niter']
            efa_dict['tolerance'] = self.panel3_results['options']['tol']
            efa_dict['method'] = self.panel3_results['options']['method']
            efa_dict['force_positive'] = self.panel3_results['force_positive']

            analysis_dict['efa'] = efa_dict

            self.manip_item.markAsModified()

        self.OnClose()

    def _onInfoButton(self, evt):
        msg = ('If you use evolving factor analysis (EFA) in your '
            'work, in addition to citing the RAW paper please cite:'
            '\nSteve P. Meisburger, Alexander B. Taylor, Crystal A. '
            'Khan, Shengnan Zhang, Paul F. Fitzpatrick, and Nozomi '
            'Ando. Journal of the American Chemical Society 2016 138 '
            '(20), 6506-6516.')
        wx.MessageBox(str(msg), "How to cite EFA", style = wx.ICON_INFORMATION | wx.OK)

    def plotSVD(self, svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor,
        svd_start,  svd_end):
        self.plotPanel1.plotSVD( svd_U, svd_s, svd_V, svd_U_autocor,
            svd_V_autocor, svd_start,  svd_end)

    def refreshEFAPlot(self):
        self.plotPanel2.refresh()

    def plotEFA(self, forward_data, backward_data):
        self.plotPanel2.plotEFA(forward_data, backward_data)

    def getPanel1Values(self):
        self.panel1_results = self.controlPanel1.getResults()

    def getPanel2Values(self):
        self.panel2_results = self.controlPanel2.getResults()

    def getPanel3Values(self):

        self.panel3_results = self.controlPanel3.getResults()

    def OnClose(self):

        self.Destroy()


class EFAControlPanel2(wx.Panel):

    def __init__(self, parent, panel_id, secm, manip_item, efa_frame, ctrl_type):

        wx.Panel.__init__(self, parent, panel_id, style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.efa_frame = efa_frame

        self.secm = secm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.ctrl_type = ctrl_type

        self.raw_settings = self.main_frame.raw_settings

        self.initialized = False

        control_sizer = self._createLayout()

        self.SetSizer(control_sizer)

        self.bkg_dialog = None

        self.results = {
            'start_points'   : [],
            'end_points'    : [],
            'points'        : [],
            'forward_efa'   : [],
            'backward_efa'  : [],
            }

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        if self.bkg_dialog is not None:
            self.bkg_dialog.updateColors()

    def _createLayout(self):

        self.top_efa = wx.ScrolledWindow(self, -1)
        self.top_efa.SetScrollRate(20,20)

        top_sizer =wx.BoxSizer(wx.VERTICAL)


        #svd controls
        self.top_box = wx.StaticBox(self.top_efa, -1, 'User Input')
        control_sizer = wx.StaticBoxSizer(self.top_box, wx.VERTICAL)

        self.forward_sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self.top_box, -1, 'Forward:')

        self.forward_sizer.Add(label, 0)


        self.backward_sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self.top_box, -1, 'Backward:')

        self.backward_sizer.Add(label, 0)


        control_sizer.Add(self.forward_sizer, 0, wx.EXPAND|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(3))
        control_sizer.Add(self.backward_sizer, 0, wx.EXPAND|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(3))

        if self.ctrl_type == 'REGALS':
            self.bkg_components = RAWCustomCtrl.IntSpinCtrl(self.top_box,
                size=self._FromDIP((60, -1)))
            self.bkg_components.SetRange((0, 10))
            self.bkg_components.SetValue(0)

            bkg_sizer = wx.BoxSizer(wx.HORIZONTAL)
            bkg_sizer.Add(wx.StaticText(self.top_box, label='# of background components:'),
                border=self._FromDIP(3), flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)
            bkg_sizer.Add(self.bkg_components, border=self._FromDIP(5),
                flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)

            bkg_button = wx.Button(self.top_box, label='Find background components')
            bkg_button.Bind(wx.EVT_BUTTON, self._on_find_regals_bkg)

            control_sizer.Add(bkg_sizer, border=self._FromDIP(20),
                flag=wx.TOP)
            control_sizer.Add(bkg_button, border=self._FromDIP(5), flag=wx.TOP)

        self.top_efa.SetSizer(control_sizer)

        top_sizer.Add(self.top_efa, 1, wx.EXPAND)
        # top_sizer.AddStretchSpacer(1)

        return top_sizer


    def initialize(self, svd_results):
        self.panel1_results = copy.copy(svd_results)

        nvals = svd_results['input']

        if self.ctrl_type == 'REGALS':
            self.bkg_components.SetRange((0, nvals))

            series_analysis_dict = self.secm.getParameter('analysis')

            if 'regals' in series_analysis_dict and self.ctrl_type == 'REGALS':
                analysis_dict = series_analysis_dict['regals']

                if 'background_components' in analysis_dict:
                    if analysis_dict['background_components'] <= nvals:
                        self.bkg_components.SetValue(analysis_dict['background_components'])

        self.forward_ids = [self.NewControlId() for i in range(nvals)]
        self.backward_ids = [self.NewControlId() for i in range(nvals)]

        self.fsizer = wx.FlexGridSizer(cols=2, rows=nvals, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))
        self.bsizer = wx.FlexGridSizer(cols=2, rows=nvals, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))

        start = svd_results['fstart']
        end = svd_results['fend']

        for i in range(nvals):

            flabel = wx.StaticText(self.top_box, -1, 'Value %i start :' %(i))
            fcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_box, self.forward_ids[i],
                size=self._FromDIP((60, -1)))
            fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onForwardControl)
            fcontrol.SetValue(start)
            fcontrol.SetRange((start,end))

            self.fsizer.Add(flabel, 0)
            self.fsizer.Add(fcontrol, 0)

            blabel = wx.StaticText(self.top_box, -1, 'Value %i start :' %(i))
            bcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_box, self.backward_ids[i],
                size=self._FromDIP((60, -1)))
            bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onBackwardControl)
            bcontrol.SetValue(start)
            bcontrol.SetRange((start,end))

            self.bsizer.Add(blabel, 0)
            self.bsizer.Add(bcontrol, 0)

        self.forward_sizer.Add(self.fsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(3))
        self.backward_sizer.Add(self.bsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(3))

        self.forward_sizer.Layout()
        self.backward_sizer.Layout()
        self.top_efa.Layout()
        self.Layout()
        self.efa_frame.Layout()
        self.efa_frame.SendSizeEvent()

        self.busy_dialog = wx.BusyInfo('Please wait, calculating . . . ',
            self.efa_frame)
        wx.Yield()

        efa_thread = threading.Thread(target=self._runEFA,
            args=(self.panel1_results['svd_int_norm'],))
        efa_thread.daemon = True
        wx.CallLater(100, efa_thread.start)

    def reinitialize(self, svd_results, efa, new_ranges=None):
        self.panel1_results = copy.copy(svd_results)

        nvals = svd_results['input']

        if self.ctrl_type == 'REGALS':
            self.bkg_components.SetRange((0, nvals))

        self.forward_ids = [self.NewControlId() for i in range(nvals)]
        self.backward_ids = [self.NewControlId() for i in range(nvals)]

        self.forward_sizer.Hide(self.fsizer)
        self.forward_sizer.Detach(self.fsizer)

        self.backward_sizer.Hide(self.bsizer)
        self.backward_sizer.Detach(self.bsizer)

        for child in self.fsizer.GetChildren():
            self.fsizer.Hide(child.Window)
            self.fsizer.Detach(child.Window)

        for child in self.bsizer.GetChildren():
            self.bsizer.Hide(child.Window)
            self.bsizer.Detach(child.Window)


        self.forward_sizer.Layout()
        self.backward_sizer.Layout()
        self.top_efa.Layout()
        self.Layout()

        start = svd_results['fstart']
        end = svd_results['fend']

        self.fsizer = wx.FlexGridSizer(cols=2, rows=nvals, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))
        self.bsizer = wx.FlexGridSizer(cols=2, rows=nvals, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))

        for i in range(nvals):

            flabel = wx.StaticText(self.top_box, -1, 'Value %i start :' %(i))
            fcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_box, self.forward_ids[i],
                size=self._FromDIP((60, -1)))
            fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onForwardControl)
            fcontrol.SetValue(start)
            fcontrol.SetRange((start,end))

            self.fsizer.Add(flabel, 0)
            self.fsizer.Add(fcontrol, 0)

            blabel = wx.StaticText(self.top_box, -1, 'Value %i end :' %(i))
            bcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_box, self.backward_ids[i],
                size=self._FromDIP((60, -1)))
            bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onBackwardControl)
            bcontrol.SetValue(start)
            bcontrol.SetRange((start,end))

            self.bsizer.Add(blabel, 0)
            self.bsizer.Add(bcontrol, 0)


        self.forward_sizer.Add(self.fsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(3))
        self.backward_sizer.Add(self.bsizer, 0, wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(3))

        self.forward_sizer.Layout()
        self.backward_sizer.Layout()
        self.top_efa.Layout()
        self.Layout()

        if efa:
            self.busy_dialog = wx.BusyInfo('Please wait, calculating . . . ', self.efa_frame)
            wx.Yield()

            efa_thread = threading.Thread(target=self._runEFA,
                args=(self.panel1_results['svd_int_norm'],))
            efa_thread.daemon = True
            wx.CallLater(100, efa_thread.start)

        elif new_ranges is None:
            self._findEFAPoints()
            self.efa_frame.refreshEFAPlot()
            wx.CallAfter(self.updateEFAPlot)

        else:
            if self.ctrl_type == 'REGALS':
                forward_sv = new_ranges[:,0]
                backward_sv = new_ranges[:,1]

                bkg_comp = self.bkg_components.GetValue()

                backward_sv = np.roll(backward_sv, -1*bkg_comp)

                new_ranges = np.column_stack((forward_sv, backward_sv))

            self.efa_frame.refreshEFAPlot()
            self.setSVs(new_ranges)

    def _onForwardControl(self, evt):
        self.updateEFAPlot()

    def _onBackwardControl(self, evt):
        self.updateEFAPlot()

    def setSVs(self, points):
        for i in range(len(points)):
            forward = wx.FindWindowById(self.forward_ids[i], self)
            backward = wx.FindWindowById(
                self.backward_ids[len(self.backward_ids)-1-i], self)

            forward.SetValue(points[i][0])
            backward.SetValue(points[i][1])

        wx.CallAfter(self.updateEFAPlot)

    def _runEFA(self, A):
        f_slist = SASCalc.runEFA(A)
        wx.Yield()
        b_slist = SASCalc.runEFA(A, False)

        wx.CallAfter(self._processEFAResults, f_slist, b_slist)

    def _processEFAResults(self, f_slist, b_slist):
        self.efa_forward = f_slist
        self.efa_backward = b_slist

        if not self.initialized:
            series_analysis_dict = self.secm.getParameter('analysis')
            nvals = self.panel1_results['input']

            if 'efa' in series_analysis_dict and self.ctrl_type == 'EFA':
                analysis_dict = series_analysis_dict['efa']
            elif 'regals' in series_analysis_dict and self.ctrl_type == 'REGALS':
                analysis_dict = series_analysis_dict['regals']
            else:
                analysis_dict = None


            if analysis_dict is not None:

                if (nvals == analysis_dict['nsvs']
                    and self.panel1_results['fstart'] == analysis_dict['fstart']
                    and self.panel1_results['fend'] == analysis_dict['fend']
                    and self.panel1_results['profile'] == analysis_dict['profile']
                    and nvals == len(analysis_dict['ranges'])):

                    if self.ctrl_type == 'REGALS':
                        points = np.array(analysis_dict['frame_ranges'])
                    else:
                        points = np.array(analysis_dict['ranges'])

                    forward_sv = points[:,0]
                    backward_sv = points[:,1]

                    if self.ctrl_type == 'REGALS':
                        bkg_comp = self.bkg_components.GetValue()
                        backward_sv = np.roll(backward_sv, -1*bkg_comp)
                        points = np.column_stack((forward_sv, backward_sv))

                        if int(self.bkg_components.GetValue()) == 0:

                            if ('exp_type' in self.panel1_results and
                                self.panel1_results['exp_type'] == 'IEC/SEC-SAXS'):
                                wx.CallAfter(self._find_regals_bkg)

                    if np.all(np.sort(forward_sv) == forward_sv) and np.all(np.sort(backward_sv) == backward_sv):
                        self.setSVs(points)
                    elif self.ctrl_type == 'REGALS':
                        self.setSVs(points)
                    else:
                        self._findEFAPoints()
                else:
                    self._findEFAPoints()
            else:
                self._findEFAPoints()

            self.initialized = True

            if self.ctrl_type == 'REGALS':
                if int(self.bkg_components.GetValue()) == 0:
                    if ('exp_type' in self.panel1_results and
                        self.panel1_results['exp_type'] == 'IEC/SEC-SAXS'):
                        wx.CallAfter(self._find_regals_bkg)

        else:
            self._findEFAPoints()

        del self.busy_dialog
        self.busy_dialog = None

        self.efa_frame.refreshEFAPlot()

        wx.CallAfter(self.updateEFAPlot)


    def _findEFAPoints(self):

        forward_windows = [wx.FindWindowById(my_id, self) for my_id in self.forward_ids]

        backward_windows = [wx.FindWindowById(my_id, self) for my_id in self.backward_ids]

        start_offset = self.panel1_results['fstart']

        old_value = start_offset

        for i in range(len(forward_windows)):
            if int(forward_windows[i].GetValue()) == int(start_offset):
                try:
                    d1 = np.gradient(self.efa_forward[i,i+1:])

                    val_list = np.where(d1/d1.max()>.03+.05*i)[0] + start_offset

                    start = val_list[0]
                    j = 1

                    while start < old_value and j < len(val_list):
                        start = val_list[j]
                        j = j+1

                    if j == len(val_list):
                        start = val_list[0]

                    forward_windows[i].SetValue(start)

                    old_value = start

                except Exception as e:
                    print(e)


        old_value = self.panel1_results['fend']

        backward = self.efa_backward[:, ::-1]

        for i in range(len(backward_windows)):
            if int(backward_windows[i].GetValue()) == int(start_offset):
                try:
                    d1 = np.gradient(backward[i,:len(backward[i])-1-i])

                    d1_norm = d1/d1.min()

                    val_list = np.where(d1_norm>.05+.15*i)[0] + start_offset

                    end = val_list[-1]
                    j = 2

                    while end > old_value and j < len(val_list):
                        end = val_list[-j]
                        j = j+1

                    if j == len(val_list):
                        end = val_list[-1]

                    backward_windows[i].SetValue(end)

                    old_value = end

                except Exception as e:
                    print(e)

    def updateEFAPlot(self):
        nvals = self.panel1_results['input']+1

        forward_points = [wx.FindWindowById(my_id, self).GetValue() for my_id in self.forward_ids]

        backward_points = [wx.FindWindowById(my_id, self).GetValue() for my_id in self.backward_ids]

        forward_data = {'slist' : self.efa_forward[:nvals, :],
                        'index' : np.arange(len(self.efa_forward[0]))+self.panel1_results['fstart'],
                        'points': forward_points}

        backward_data = {'slist': self.efa_backward[:nvals, ::-1],
                        'index' : np.arange(len(self.efa_backward[0]))+self.panel1_results['fstart'],
                        'points': backward_points}

        self.efa_frame.plotEFA(forward_data, backward_data)

    def getResults(self):

        forward_points = [wx.FindWindowById(my_id, self).GetValue() for my_id in self.forward_ids]
        self.results['forward_points'] = copy.copy(forward_points)

        backward_points = [wx.FindWindowById(my_id, self).GetValue() for my_id in self.backward_ids]
        self.results['backward_points'] = copy.copy(backward_points)

        forward_points.sort()

        if self.ctrl_type == 'EFA':
            backward_points.sort()

        elif self.ctrl_type == 'REGALS':
            # Unlike elution compoments, background components are assumed to be first in last out
            n_bkg = self.bkg_components.GetValue()

            if n_bkg == 0:
                backward_points.sort()
            else:
                backward_points = backward_points[::-1]

            for i in range(n_bkg):
                backward_points.insert(0, backward_points.pop())

            self.results['bkg_components'] = n_bkg

        points = np.column_stack((forward_points,backward_points))

        self.results['points'] = points

        self.results['forward_efa'] = self.efa_forward
        self.results['backward_efa'] = self.efa_backward

        return self.results

    def _on_find_regals_bkg(self, evt):
        wx.CallAfter(self._find_regals_bkg)

    def _find_regals_bkg(self):
        start = self.panel1_results['fstart']
        end = self.panel1_results['fend']
        secm_choice = self.panel1_results['secm_choice']

        if secm_choice == 'usub':
            series = self.secm
        elif secm_choice == 'sub':
            series = self.panel1_results['sub_secm']
        elif secm_choice == 'bl':
            series = self.panel1_results['bl_secm']

        svd_a = self.panel1_results['svd_int_norm']

        self.bkg_dialog = REGALSBackground(self.efa_frame, start, end, series,
            secm_choice, self.panel1_results['input'], int(self.bkg_components.GetValue()))

        ret = self.bkg_dialog.ShowModal()

        if ret == wx.ID_OK:
            bkg_comps = self.bkg_dialog.get_bkg_comps()

            self.bkg_components.SetValue(bkg_comps)

        self.bkg_dialog.Destroy()
        self.bkg_dialog = None


class EFAResultsPlotPanel2(wx.Panel):

    def __init__(self, parent, panel_id):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.f_lines = []
        self.b_lines = []

        self.f_markers = []
        self.b_markers = []

        subplotLabels = [('Forward EFA', 'Index', 'Singular Value', 0.1),
            ('Backward EFA', 'Index', 'Singular Value', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1,
                title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93,
            top = 0.93, hspace = 0.26)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateColors(self):
        SASUtils.update_mpl_style()

        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Forward EFA']
        b = self.subplots['Backward EFA']

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.f_background = self.canvas.copy_from_bbox(a.bbox)
        self.b_background = self.canvas.copy_from_bbox(b.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def refresh(self):
        a = self.subplots['Forward EFA']
        b = self.subplots['Backward EFA']

        self.f_lines = []
        self.b_lines = []

        self.f_markers = []
        self.b_markers = []

        while len(a.lines) != 0:
            a.lines.pop(0)

        while len(b.lines) != 0:
            b.lines.pop(0)

        if ((int(matplotlib.__version__.split('.')[0]) ==1
            and int(matplotlib.__version__.split('.')[1]) >=5)
            or int(matplotlib.__version__.split('.')[0]) > 1):
            a.set_prop_cycle(None)
            b.set_prop_cycle(None)
        else:
            a.set_color_cycle(None)
            b.set_color_cycle(None)

    def refresh_display(self):
        self.ax_redraw()
        self.toolbar.Refresh()

    def plotEFA(self, forward_data, backward_data):

        self.updateDataPlot(forward_data, backward_data)

    def updateDataPlot(self, forward_data, backward_data):
        #Save for resizing:
        self.orig_forward_data = forward_data
        self.orig_backward_data = backward_data

        index = forward_data['index']
        f_slist = forward_data['slist']
        f_points = forward_data['points']

        b_slist = backward_data['slist']
        b_points = backward_data['points']

        fp_index = [np.where(index == point)[0][0] for point in f_points]
        bp_index = [np.where(index == point)[0][0] for point in b_points]

        a = self.subplots['Forward EFA']
        b = self.subplots['Backward EFA']


        if len(self.f_lines) == 0:

            for j in range(f_slist.shape[0]):
                line, = a.semilogy(index, f_slist[j], label = 'SV %i' %(j),
                    animated=True)
                self.f_lines.append(line)

            for j in range(len(f_points)):
                point, = a.semilogy(f_points[j], f_slist[j][fp_index[j]], 'o',
                    markeredgewidth=2, markeredgecolor=self.f_lines[j].get_color(),
                    markerfacecolor='none', markersize=8, label='_nolegend_',
                    animated = True)
                self.f_markers.append(point)

            for k in range(b_slist.shape[0]):
                line, = b.semilogy(index, b_slist[k], label='SV %i' %(k),
                    animated=True)
                self.b_lines.append(line)

            for k in range(len(b_points)):
                point, = b.semilogy(b_points[k], b_slist[k][bp_index[k]], 'o',
                    markeredgewidth=2, markeredgecolor=self.b_lines[k].get_color(),
                    markerfacecolor='none', markersize=8, label='_nolegend_',
                    animated=True)
                self.b_markers.append(point)

            a.legend(fontsize = 12, loc = 'upper left')
            b.legend(fontsize = 12)

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.f_background = self.canvas.copy_from_bbox(a.bbox)
            self.b_background = self.canvas.copy_from_bbox(b.bbox)

        else:
            for j in range(len(self.f_lines)):
                line = self.f_lines[j]
                line.set_xdata(index)
                line.set_ydata(f_slist[j])

            for j in range(len(self.f_markers)):
                marker = self.f_markers[j]
                marker.set_xdata(f_points[j])
                marker.set_ydata(f_slist[j][fp_index[j]])

            for k in range(len(self.b_lines)):
                line = self.b_lines[k]
                line.set_xdata(index)
                line.set_ydata(b_slist[k])

            for k in range(len(self.b_markers)):
                marker = self.b_markers[k]
                marker.set_xdata(b_points[k])
                marker.set_ydata(b_slist[k][bp_index[k]])

        self.autoscale_plot()

    def redrawLines(self):
        if len(self.f_lines) != 0:
            a = self.subplots['Forward EFA']
            b = self.subplots['Backward EFA']

            self.canvas.restore_region(self.f_background)

            for line in self.f_lines:
                a.draw_artist(line)

            for marker in self.f_markers:
                a.draw_artist(marker)

            #restore white background in error plot and draw new error:
            self.canvas.restore_region(self.b_background)

            for line in self.b_lines:
                b.draw_artist(line)

            for marker in self.b_markers:
                b.draw_artist(marker)

            self.canvas.blit(a.bbox)
            self.canvas.blit(b.bbox)

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplots['Forward EFA'], self.subplots['Backward EFA']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()

class EFAControlPanel3(wx.Panel):

    def __init__(self, parent, panel_id, secm, manip_item):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.efa_frame = parent.GetParent().GetParent()

        self.secm = secm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.control_ids = {'n_iter'        : self.NewControlId(),
                            'tol'           : self.NewControlId(),
                            'method'        : self.NewControlId(),
                            'status'        : self.NewControlId(),
                            'save_results'  : self.NewControlId()}

        self.control_values = {'n_iter' : 1000,
                                'tol'   : 1e-12}

        self.fail_text = ''

        self.initialized = False
        self.converged = False
        self.rotation_data = {}

        control_sizer = self._createLayout()

        self.SetSizer(control_sizer)

        self.results = {
            'options'   : {},
            'steps'     : 0,
            'iterations': 0,
            'converged' : False,
            'ranges'    : [],
            'profiles'  : [],
            'conc'      : [],
            'chisq'     : [],
            'force_positive'    : [],
            }

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.sec_plot.updateColors()

    def _createLayout(self):

        self.top_efa = wx.ScrolledWindow(self, -1)
        self.top_efa.SetScrollRate(20,20)

        top_sizer =wx.BoxSizer(wx.VERTICAL)

        self.sec_plot = EFARangePlotPanel(self, wx.ID_ANY)

        #svd controls
        self.peak_ctrl_box = wx.StaticBox(self.top_efa, -1, 'Component Range Controls')
        self.peak_control_sizer = wx.StaticBoxSizer(self.peak_ctrl_box, wx.VERTICAL)

        self.top_efa.SetSizer(self.peak_control_sizer)


        rot_box = wx.StaticBox(self, -1, 'Rotation Controls')
        iter_control_sizer = wx.StaticBoxSizer(rot_box, wx.VERTICAL)

        grid_sizer = wx.FlexGridSizer(cols=2, rows=3, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))

        method_label = wx.StaticText(rot_box, -1, 'Method:')
        method_control = wx.Choice(rot_box, self.control_ids['method'],
            choices=['Hybrid', 'Iterative', 'Explicit'])
        method_control.SetStringSelection('Hybrid')
        method_control.Bind(wx.EVT_CHOICE, self._onIterControl)

        grid_sizer.Add(method_label)
        grid_sizer.Add(method_control)


        num_label = wx.StaticText(rot_box, -1, 'Number of iterations:')

        num_control = RAWCustomCtrl.IntSpinCtrl(rot_box, self.control_ids['n_iter'],
            size=self._FromDIP((60,-1)))
        num_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onIterControl)
        num_control.SetValue(str(self.control_values['n_iter']))
        num_control.SetRange((1, 1e12))

        grid_sizer.Add(num_label, 0)
        grid_sizer.Add(num_control, 1)


        tol_label = wx.StaticText(rot_box, -1, 'Convergence threshold:')

        tol_control = RAWCustomCtrl.FloatSpinCtrl(rot_box, self.control_ids['tol'],
            size=self._FromDIP((60,-1)), never_negative = True)
        tol_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onIterControl)
        tol_control.SetValue(str(self.control_values['tol']))

        grid_sizer.Add(tol_label, 0)
        grid_sizer.Add(tol_control, 1)

        iter_control_sizer.Add(grid_sizer, 1, wx.TOP | wx.BOTTOM | wx.EXPAND,
            border=self._FromDIP(3))


        status_box = wx.StaticBox(self, -1, 'Status')
        status_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)

        status_label = wx.StaticText(status_box, self.control_ids['status'], '')

        status_sizer.Add(status_label,0, wx.ALL, border=self._FromDIP(3))


        results_box = wx.StaticBox(self, -1, 'Results')
        results_sizer = wx.StaticBoxSizer(results_box, wx.VERTICAL)

        save_results = wx.Button(results_box, self.control_ids['save_results'],
            'Save EFA Data (not profiles)')
        save_results.Bind(wx.EVT_BUTTON, self._onSaveButton)

        # button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # button_sizer.Add(save_results, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 3)

        results_sizer.Add(save_results, 0, wx.ALIGN_CENTER_HORIZONTAL)


        top_sizer.Add(self.sec_plot, 0, wx.ALL | wx.EXPAND, border=self._FromDIP(3))
        top_sizer.Add(self.top_efa, 1, wx.EXPAND)
        top_sizer.Add(iter_control_sizer, 0, wx.EXPAND)
        top_sizer.Add(status_sizer, 0, wx.EXPAND)
        top_sizer.Add(results_sizer, 0, wx.EXPAND)
        # top_sizer.AddStretchSpacer(1)

        return top_sizer


    def initialize(self, svd_results, efa_results):
        self.panel1_results = copy.copy(svd_results)

        self.panel2_results = copy.copy(efa_results)

        analysis_dict = self.secm.getParameter('analysis')

        nvals = efa_results['points'].shape[0]

        self.range_ids = [(self.NewControlId(), self.NewControlId(),
            self.NewControlId()) for i in range(nvals)]

        self.range_sizer = wx.FlexGridSizer(cols=5, rows=nvals,
            vgap=self._FromDIP(3), hgap=self._FromDIP(3))

        start = svd_results['fstart']
        end = svd_results['fend']

        points = efa_results['points']

        for i in range(nvals):

            label1 = wx.StaticText(self.peak_ctrl_box, -1, 'Range %i :' %(i))
            fcontrol = RAWCustomCtrl.IntSpinCtrl(self.peak_ctrl_box, self.range_ids[i][0],
                size=self._FromDIP((60, -1)))
            fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
            fcontrol.SetValue(points[i][0])
            fcontrol.SetRange((start, end))

            self.range_sizer.Add(label1, 0, wx.LEFT, border=self._FromDIP(3))
            self.range_sizer.Add(fcontrol, 0)

            label2 = wx.StaticText(self.peak_ctrl_box, -1, 'to')
            bcontrol = RAWCustomCtrl.IntSpinCtrl(self.peak_ctrl_box, self.range_ids[i][1],
                size=self._FromDIP((60, -1)))
            bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
            bcontrol.SetValue(points[i][1])
            bcontrol.SetRange((start, end))

            self.range_sizer.Add(label2, 0)
            self.range_sizer.Add(bcontrol, 0)

            force_pos = wx.CheckBox(self.peak_ctrl_box, self.range_ids[i][2], 'C>=0')
            force_pos.Bind(wx.EVT_CHECKBOX, self._onRangeControl)
            force_pos.SetValue(True)

            self.range_sizer.Add(force_pos, 0)


        self.peak_control_sizer.Add(self.range_sizer, 0, wx.TOP,
            border=self._FromDIP(3))

        if 'efa' in analysis_dict:
            efa_dict = analysis_dict['efa']
            if (efa_dict['fstart'] == self.panel1_results['fstart']
                and efa_dict['fend'] == self.panel1_results['fend']
                and efa_dict['profile'] == self.panel1_results['profile']
                and efa_dict['nsvs'] == self.panel1_results['input']
                and np.all(efa_dict['ranges'] == self._getRanges())):

                keylist = ['n_iter', 'tol', 'method']

                for key in keylist:
                    if key in efa_dict and key in self.control_ids:
                        window = wx.FindWindowById(self.control_ids[key])

                        if key != 'method':
                            try:
                                window.SetValue(str(efa_dict[key]))
                            except Exception as e:
                                print(e)
                        else:
                            try:
                                window.SetStringSelection(str(efa_dict[key]))
                            except Exception as e:
                                print(e)

                if 'force_positive' in efa_dict:
                    force_positive = efa_dict['force_positive']
                    for i in range(len(self.range_ids)):
                        window = wx.FindWindowById(self.range_ids[i][2], self)
                        window.SetValue(force_positive[i])

        if nvals == 1:
            window = wx.FindWindowById(self.control_ids['method'], self)
            window.SetStringSelection('Iterative')

        self.initialized = True

        wx.CallAfter(self.runRotation)

        wx.CallAfter(self.updateRangePlot)

    def reinitialize(self, svd_results, efa_results, rebuild):
        self.panel1_results = copy.copy(svd_results)

        self.panel2_results = copy.copy(efa_results)

        nvals = efa_results['points'].shape[0]

        if rebuild:
            self.peak_control_sizer.Hide(self.range_sizer)
            self.peak_control_sizer.Detach(self.range_sizer)

            for child in self.range_sizer.GetChildren():
                self.range_sizer.Hide(child.Window)
                self.range_sizer.Detach(child.Window)

            self.peak_control_sizer.Layout()
            self.top_efa.Layout()
            self.Layout()

            self.range_ids = [(self.NewControlId(), self.NewControlId(),
                self.NewControlId()) for i in range(nvals)]

            self.range_sizer = wx.FlexGridSizer(cols=5, rows=nvals,
                vgap=self._FromDIP(3), hgap=self._FromDIP(3))

            start = svd_results['fstart']
            end = svd_results['fend']

            points = efa_results['points']

            for i in range(nvals):

                label1 = wx.StaticText(self.peak_ctrl_box, -1, 'Range %i :' %(i))
                fcontrol = RAWCustomCtrl.IntSpinCtrl(self.peak_ctrl_box, self.range_ids[i][0],
                    size=self._FromDIP((60, -1)))
                fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
                fcontrol.SetValue(points[i][0])
                fcontrol.SetRange((start,end))

                self.range_sizer.Add(label1, 0, wx.LEFT, border=self._FromDIP(3))
                self.range_sizer.Add(fcontrol, 0)

                label2 = wx.StaticText(self.peak_ctrl_box, -1, 'to')
                bcontrol = RAWCustomCtrl.IntSpinCtrl(self.peak_ctrl_box, self.range_ids[i][1],
                    size=self._FromDIP((60, -1)))
                bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
                bcontrol.SetValue(points[i][1])
                bcontrol.SetRange((start,end))

                self.range_sizer.Add(label2, 0)
                self.range_sizer.Add(bcontrol, 0)

                force_pos = wx.CheckBox(self.peak_ctrl_box, self.range_ids[i][2], 'C>=0')
                force_pos.Bind(wx.EVT_CHECKBOX, self._onRangeControl)
                force_pos.SetValue(True)

                self.range_sizer.Add(force_pos, 0)


            self.peak_control_sizer.Add(self.range_sizer, 0, wx.TOP,
                border=self._FromDIP(3))

            self.peak_control_sizer.Layout()
            self.top_efa.Layout()
            self.Layout()

        else:
            for i in range(nvals):
                my_ids = self.range_ids[i]
                points = efa_results['points'][i]

                start = wx.FindWindowById(my_ids[0], self)
                end = wx.FindWindowById(my_ids[1], self)

                start.SetValue(points[0])
                end.SetValue(points[1])

        self.efa_frame.plotPanel3.refresh()

        self.sec_plot.refresh()

        wx.CallAfter(self.runRotation)
        wx.CallAfter(self.updateRangePlot)


    def _onIterControl(self, evt):

        if evt.GetId() == self.control_ids['method']:
            window = wx.FindWindowById(self.control_ids['method'], self)
            method = window.GetStringSelection()

            if method == 'Explicit':
                enable = False

            else:
                enable = True

            for ids in self.range_ids:
                my_id = ids[2]
                window = wx.FindWindowById(my_id, self)
                window.Enable(enable)

            window = wx.FindWindowById(self.control_ids['n_iter'], self)
            window.Enable(enable)

            window = wx.FindWindowById(self.control_ids['tol'], self)
            window.Enable(enable)


        wx.CallAfter(self.runRotation)

    def _onRangeControl(self, evt):
        wx.CallAfter(self.updateRangePlot)
        wx.CallAfter(self.runRotation)

    def _onSaveButton(self, evt):
        self.efa_frame.getPanel3Values()

        panel3_results = self.efa_frame.panel3_results

        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        path = str(dirctrl.getDirLabel())

        filename = self.panel1_results['filename']

        name, ext = os.path.splitext(filename)

        filename = name + '_efa.csv'

        dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = path, defaultFile = filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name+'.csv'
            dialog.Destroy()
        else:
            dialog.Destroy()
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving EFA data', 0)

        SASFileIO.saveEFAData(save_path, self.panel1_results, self.panel2_results, panel3_results)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)

    def _updateStatus(self, in_progress = False):
        status_window = wx.FindWindowById(self.control_ids['status'], self)

        if not in_progress:
            if self.converged:
                status = 'Rotation Successful\n'
            else:
                status = self.fail_text
        else:
            status = 'Rotation in progress'

        status_window.SetLabel(status)

        self.Layout()

    def runRotation(self):
        #Get component ranges and iteration control values
        wx.CallAfter(self._updateStatus, True)

        ranges = self._getRanges()

        start = self.panel1_results['fstart']

        ranges = ranges - start

        niter = int(wx.FindWindowById(self.control_ids['n_iter'], self).GetValue())
        tol = float(wx.FindWindowById(self.control_ids['tol'], self).GetValue())
        method = wx.FindWindowById(self.control_ids['method'], self).GetStringSelection()

        force_positive = []
        for i in range(len(self.range_ids)):
            window = wx.FindWindowById(self.range_ids[i][2], self)
            force_positive.append(window.GetValue())

        D = self.panel1_results['svd_int_norm']
        intensity = self.panel1_results['int']
        err = self.panel1_results['err']

        svd_v = self.panel1_results['svd_v']

        converged, conv_data, rotation_data = SASCalc.runRotation(D, intensity,
            err, ranges, force_positive, svd_v, previous_results=(self.converged,
            self.rotation_data), method=method, niter=niter, tol=tol)

        self.converged = converged
        self.conv_data = conv_data
        self.rotation_data = rotation_data

        k = conv_data['iterations']
        final_step = conv_data['final_step']
        failed = conv_data['failed']

        if method != 'Explicit':
            if k == niter and final_step > tol:
                dc = conv_data['steps']
                self.fail_text = ('Rotation failed to converge after %i\n '
                    'iterations with final delta = %.2E.' %(k, dc[-1]))
            elif failed:
                self.fail_text = ('Rotation failed due to a numerical error\n '
                    'in the algorithm. Try adjusting ranges or changing method.')
        else:
            if failed:
                self.fail_text = ('Rotation failed due to a numerical error\n '
                    'in the algorithm. Try adjusting ranges or changing method.')

        if self.converged:
            self._makeSASMs()
            wx.CallAfter(self.updateResultsPlot)

        else:
            wx.CallAfter(self.clearResultsPlot)

        wx.CallAfter(self._updateStatus)

    def _getRanges(self):
        ranges = []

        for my_ids in self.range_ids:
            r = [wx.FindWindowById(my_ids[0], self).GetValue(),
                wx.FindWindowById(my_ids[1], self).GetValue()]
            r.sort()
            ranges.append(r)

        ranges = np.array(ranges, dtype = int)

        return ranges

    def _makeSASMs(self):
        nprofiles = len(self.range_ids)

        self.sasms = [None for i in range(nprofiles)]

        old_filename = self.secm.getParameter('filename').split('.')

        if len(old_filename) > 1:
            old_filename = '.'.join(old_filename[:-1])
        else:
            old_filename = old_filename[0]

        if self.panel1_results['profile'] == 'Unsubtracted':
            q = copy.deepcopy(self.secm.getSASM(int_type='unsub').getQ())
            q_err = copy.deepcopy(self.secm.getSASM(int_type='unsub').getQErr())
        elif self.panel1_results['profile'] == 'Subtracted':
            q = copy.deepcopy(self.secm.getSASM(int_type='sub').getQ())
            q_err = copy.deepcopy(self.secm.getSASM(int_type='sub').getQErr())
        elif self.panel1_results['profile'] == 'Baseline Corrected':
            q = copy.deepcopy(self.secm.getSASM(int_type='baseline').getQ())
            q_err = copy.deepcopy(self.secm.getSASM(int_type='baseline').getQErr())

        ranges = self._getRanges()

        for i in range(nprofiles):
            intensity = self.rotation_data['int'][:,i]

            err = self.rotation_data['err'][:,i]

            sasm = SASM.SASM(intensity, q, err, {}, q_err)

            sasm.setParameter('filename', old_filename+'_%i' %(i))

            history_dict = {}

            history_dict['input_filename'] = self.panel1_results['filename']
            history_dict['start_index'] = str(self.panel1_results['fstart'])
            history_dict['end_index'] = str(self.panel1_results['fend'])
            history_dict['component_number'] = str(i)

            points = ranges[i]
            history_dict['component_range'] = '[%i, %i]' %(points[0], points[1])

            history = sasm.getParameter('history')
            history['EFA'] = history_dict

            self.sasms[i] = sasm


    def updateRangePlot(self):
        ydata_type = self.panel1_results['ydata_type']

        if self.panel1_results['secm_choice'] == 'usub':
            plot_secm = self.secm
        elif self.panel1_results['secm_choice'] == 'sub':
            plot_secm = self.panel1_results['sub_secm']
        elif self.panel1_results['secm_choice'] == 'bl':
            plot_secm = self.panel1_results['bl_secm']

        framei = self.panel1_results['fstart']
        framef = self.panel1_results['fend']

        ranges = self._getRanges()

        self.sec_plot.plotRange(plot_secm, framei, framef, ydata_type, ranges)

    def updateResultsPlot(self):
        framei = self.panel1_results['fstart']
        framef = self.panel1_results['fend']

        rmsd_data = [self.rotation_data['chisq'], list(range(framei, framef+1))]

        conc_data = [self.rotation_data['C'], list(range(framei, framef+1))]

        self.efa_frame.plotPanel3.plotEFA(self.sasms, rmsd_data, conc_data)

    def clearResultsPlot(self):
        self.efa_frame.plotPanel3.refresh()
        self.efa_frame.plotPanel3.canvas.draw()

    def getResults(self):

        self.results['steps'] = self.conv_data['steps']
        self.results['iterations'] = self.conv_data['iterations']
        self.results['options'] = self.conv_data['options']
        self.results['steps'] = self.conv_data['steps']

        force_positive = []
        for i in range(len(self.range_ids)):
            window = wx.FindWindowById(self.range_ids[i][2], self)
            force_positive.append(window.GetValue())

        self.results['force_positive'] = force_positive

        self.results['converged'] = self.converged

        if self.results['converged']:
            self.results['ranges'] = self._getRanges()
            self.results['profiles'] = self.sasms
            self.results['conc'] = self.rotation_data['C']
            self.results['chisq'] = self.rotation_data['chisq']

        return self.results


class EFAResultsPlotPanel3(wx.Panel):

    def __init__(self, parent, panel_id):

        wx.Panel.__init__(self, parent, panel_id, style=wx.BG_STYLE_SYSTEM
            |wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        SASUtils.update_mpl_style()

        self.fig = Figure((5,4), 75)

        self.a_lines = []
        self.b_lines = []
        self.c_lines = []
        self.c_reg_lines = []
        self.d_lines = []

        subplotLabels = [('Scattering Profiles', 'q ($\AA^{-1}$)', 'I', 0.1),
            ('P(r)', 'r ($\AA$)', '', 0.1),
            ('Mean Error Weighted $\chi^2$', 'Index', '$\chi^2$', 0.1),
            ('Concentration', 'Index', 'Arb.', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot((len(subplotLabels)+1)//2,2,i+1,
                title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left=0.12, bottom=0.07, right=0.93, top=0.93,
            hspace=0.26, wspace=0.26)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

        self.show_pr = False
        self.update_layout()

    def updateColors(self):
        SASUtils.update_mpl_style()
        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']
        d = self.subplots['P(r)']

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.a_background = self.canvas.copy_from_bbox(a.bbox)
        self.b_background = self.canvas.copy_from_bbox(b.bbox)
        self.c_background = self.canvas.copy_from_bbox(c.bbox)
        self.d_background = self.canvas.copy_from_bbox(d.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def refresh(self):
        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']
        d = self.subplots['P(r)']

        self.a_lines = []
        self.b_lines = []
        self.c_lines = []
        self.c_reg_lines = []
        self.d_lines = []

        while len(a.lines) != 0:
            a.lines.pop(0)

        while len(b.lines) != 0:
            b.lines.pop(0)

        while len(c.lines) != 0:
            c.lines.pop(0)

        while len(d.lines) != 0:
            d.lines.pop(0)

        if ((int(matplotlib.__version__.split('.')[0])==1
            and int(matplotlib.__version__.split('.')[1]) >=5)
            or int(matplotlib.__version__.split('.')[0]) > 1):
            a.set_prop_cycle(None)
            b.set_prop_cycle(None)
            c.set_prop_cycle(None)
            d.set_prop_cycle(None)
        else:
            a.set_color_cycle(None)
            b.set_color_cycle(None)
            c.set_color_cycle(None)
            d.set_color_cycle(None)

    def refresh_display(self):
        self.ax_redraw()
        self.toolbar.Refresh()

    def update_layout(self):

        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']
        d = self.subplots['P(r)']

        gs = matplotlib.gridspec.GridSpec(2, 2)

        if self.show_pr:
            a.set_subplotspec(gs[0,0])
            a.update_params()
            a.set_position(a.figbox)
            b.set_subplotspec(gs[1,0])
            b.update_params()
            b.set_position(b.figbox)
            c.set_subplotspec(gs[1,1,])
            c.update_params()
            c.set_position(c.figbox)
            d.set_subplotspec(gs[0,1])
            d.update_params()
            d.set_position(d.figbox)

            d.set_visible(True)

        else:
            a.set_subplotspec(gs[0,:])
            a.update_params()
            a.set_position(a.figbox)
            b.set_subplotspec(gs[1,0])
            b.update_params()
            b.set_position(b.figbox)
            c.set_subplotspec(gs[1,1,])
            c.update_params()
            c.set_position(c.figbox)

            d.set_visible(False)

        self.ax_redraw()


    def plotEFA(self, profile_data, rmsd_data, conc_data, ift_data=[],
        reg_conc_data=[]):
        if (len(profile_data) != len(self.a_lines)
            or len(ift_data) != len(self.d_lines)):
            self.refresh()

        if len(ift_data) > 0:
            if not self.show_pr:
                self.show_pr = True
                self.update_layout()

        else:
            if self.show_pr:
                self.show_pr = False
                self.update_layout()

        self.updateDataPlot(profile_data, rmsd_data, conc_data, ift_data,
            reg_conc_data)

    def updateDataPlot(self, profile_data, rmsd_data, conc_data, ift_data,
        reg_conc_data):
        #Save for resizing:
        self.orig_profile_data = profile_data
        self.orig_rmsd_data = rmsd_data
        self.orig_conc_data = conc_data

        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']
        d = self.subplots['P(r)']


        if len(self.a_lines) == 0:

            for j in range(len(profile_data)):
                line, = a.semilogy(profile_data[j].getQ(), profile_data[j].getI(),
                    label = 'Range %i' %(j), animated = True)
                self.a_lines.append(line)

            line, = b.plot(rmsd_data[1], rmsd_data[0], animated = True)

            self.b_lines.append(line)

            if isinstance(conc_data[0], np.ndarray):
                for j in range(conc_data[0].shape[1]):
                    line, = c.plot(conc_data[1], conc_data[0][:,j], animated = True)
                    self.c_lines.append(line)
            else:
                for c_data in conc_data:
                    if len(c_data[0]) < 40 and len(reg_conc_data) > 0:
                        line, = c.plot(c_data[0], c_data[1], 'o', animated = True)
                    else:
                        line, = c.plot(c_data[0], c_data[1], animated = True)
                    self.c_lines.append(line)

                if len(c_data[1]) <= 40:
                    for j, reg_data in enumerate(reg_conc_data):
                        color = self.c_lines[j].get_color()

                        line, = c.plot(reg_data[0], reg_data[1], animated=True)
                        line.set_color(color)
                        self.c_reg_lines.append(line)

            for j in range(len(ift_data)):
                line, = d.plot(ift_data[j].r, ift_data[j].p/ift_data[j].getParameter('i0'),
                    animated=True)
                self.d_lines.append(line)

            a.legend(fontsize = 12)

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.a_background = self.canvas.copy_from_bbox(a.bbox)
            self.b_background = self.canvas.copy_from_bbox(b.bbox)
            self.c_background = self.canvas.copy_from_bbox(c.bbox)
            self.d_background = self.canvas.copy_from_bbox(d.bbox)

        else:
            for j in range(len(self.a_lines)):
                line = self.a_lines[j]
                line.set_xdata(profile_data[j].q)
                line.set_ydata(profile_data[j].i)

            line = self.b_lines[0]
            line.set_xdata(rmsd_data[1])
            line.set_ydata(rmsd_data[0])

            for j in range(len(self.c_lines)):
                line = self.c_lines[j]
                if isinstance(conc_data[0], np.ndarray):
                    line.set_xdata(conc_data[1])
                    line.set_ydata(conc_data[0][:,j])
                else:
                    line.set_xdata(conc_data[j][0])
                    line.set_ydata(conc_data[j][1])

            for j in range(len(self.c_reg_lines)):
                line = self.c_reg_lines[j]
                line.set_xdata(reg_conc_data[j][0])
                line.set_ydata(reg_conc_data[j][1])

            for j in range(len(self.d_lines)):
                line = self.d_lines[j]
                line.set_xdata(ift_data[j].r)
                line.set_ydata(ift_data[j].p/ift_data[j].getParameter('i0'))

        self.autoscale_plot()

    def redrawLines(self):
        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']
        d = self.subplots['P(r)']

        self.canvas.restore_region(self.a_background)

        for line in self.a_lines:
            a.draw_artist(line)

        self.canvas.restore_region(self.b_background)

        for line in self.b_lines:
            b.draw_artist(line)

        self.canvas.restore_region(self.c_background)

        for line in self.c_lines:
            c.draw_artist(line)

        for line in self.c_reg_lines:
            c.draw_artist(line)

        if self.show_pr:
            self.canvas.restore_region(self.d_background)

            for line in self.d_lines:
                d.draw_artist(line)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)
        self.canvas.blit(c.bbox)

        if self.show_pr:
            self.canvas.blit(d.bbox)

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplots['Scattering Profiles'],
            self.subplots['Mean Error Weighted $\chi^2$'],
            self.subplots['Concentration'],
            self.subplots['P(r)']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()


class EFARangePlotPanel(wx.Panel):

    def __init__(self, parent, panel_id):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)
        self.SetSize(self._FromDIP((275, 300)))

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        SASUtils.update_mpl_style()

        if ((int(matplotlib.__version__.split('.')[0]) ==1
            and int(matplotlib.__version__.split('.')[1]) >=5)
            or int(matplotlib.__version__.split('.')[0])) > 1:
            self.fig = Figure((4,4), 75)
        else:
            self.fig = Figure((275./75,4), dpi = 75)

        self.cut_line = None
        self.range_arrows = []
        self.range_lines = []

        subplotLabels = [('SECPlot', 'Index', 'Intensity', .1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1,
                label=subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.18, bottom = 0.13, right = 0.93,
            top = 0.93, hspace = 0.26)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        color = SASUtils.update_mpl_style()
        if self.cut_line is not None:
            self.cut_line.set_color(color)

        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['SECPlot']

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def refresh(self):
        a = self.subplots['SECPlot']

        self.range_lines = []
        self.range_arrows = []
        self.cut_line = None

        while len(a.lines) != 0:
            a.lines.pop(0)

        if ((int(matplotlib.__version__.split('.')[0]) ==1
                    and int(matplotlib.__version__.split('.')[1]) >=5)
                or int(matplotlib.__version__.split('.')[0]) > 1):
            a.set_prop_cycle(None)
        else:
            a.set_color_cycle(None)

    def plotRange(self, secm, framei, framef, ydata_type, ranges, xvals=None):
        frame_list = secm.plot_frame_list

        if ydata_type == 'q_val':
            intensity = secm.I_of_q
        elif ydata_type == 'mean':
            intensity = secm.mean_i
        elif ydata_type == 'q_range':
            intensity = secm.qrange_I
        else:
            intensity = secm.total_i

        if len(ranges) != len(self.range_lines):
            self.refresh()

        self.updateDataPlot(frame_list, intensity, framei, framef, ranges, xvals)

    def updateDataPlot(self, frame_list, intensity, framei, framef, ranges,
        xvals=None):
        sec_color = SASUtils.update_mpl_style()
        #Save for resizing:
        self.orig_frame_list = frame_list
        self.orig_intensity = intensity
        self.orig_framei = framei
        self.orig_framef = framef
        self.orig_ranges = ranges

        a = self.subplots['SECPlot']

        if xvals is None:
            xvals = frame_list[framei:framef+1]

        if self.cut_line is None:

            self.cut_line, = a.plot(xvals, intensity[framei:framef+1], color=sec_color,
                marker='.', linestyle='-', animated = True)

            if ((int(matplotlib.__version__.split('.')[0]) ==1 and
                int(matplotlib.__version__.split('.')[1]) >=5) or
                int(matplotlib.__version__.split('.')[0]) > 1):
                a.set_prop_cycle(None) #Resets the color cycler to the original state
            else:
                a.set_color_cycle(None)

            for i in range(ranges.shape[0]):
                if ((int(matplotlib.__version__.split('.')[0]) ==1 and
                    int(matplotlib.__version__.split('.')[1]) >=5) or
                    int(matplotlib.__version__.split('.')[0]) > 1):
                    color = next(a._get_lines.prop_cycler)['color']
                else:
                    color =next(a._get_lines.color_cycle)

                annotation = a.annotate('', xy=(ranges[i][0], 0.975-0.05*(i)),
                    xytext=(ranges[i][1], 0.975-0.05*(i)),
                    xycoords=('data', 'axes fraction'),
                    arrowprops = dict(arrowstyle = '<->', color = color),
                    animated = True)
                self.range_arrows.append(annotation)

                rline1 = a.axvline(ranges[i][0], 0, 0.975-0.05*(i),
                    linestyle='dashed', color=color, animated=True)
                rline2 = a.axvline(ranges[i][1], 0, 0.975-0.05*(i),
                    linestyle='dashed', color=color, animated=True)

                self.range_lines.append([rline1, rline2])

            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
            self.background = self.canvas.copy_from_bbox(a.bbox)

        else:
            self.cut_line.set_ydata(intensity[framei:framef+1])
            self.cut_line.set_xdata(xvals)

            for i in range(ranges.shape[0]):
                arr = self.range_arrows[i]

                arr.xy = (ranges[i][0], 0.975-0.05*(i))
                arr.xyann = (ranges[i][1], 0.975-0.05*(i))

                lines = self.range_lines[i]

                lines[0].set_xdata(ranges[i][0])
                lines[1].set_xdata(ranges[i][1])

        self.autoscale_plot()

    def redrawLines(self):
        if self.cut_line is not None:
            a = self.subplots['SECPlot']

            self.canvas.restore_region(self.background)

            a.draw_artist(self.cut_line)

            for anno in self.range_arrows:
                a.draw_artist(anno)

            for lines in self.range_lines:
                a.draw_artist(lines[0])
                a.draw_artist(lines[1])

            self.canvas.blit(a.bbox)

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplots['SECPlot']]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()


class REGALSFrame(wx.Frame):

    def __init__(self, parent, secm, manip_item):

        wx.Frame.__init__(self, parent, wx.ID_ANY, "REGALS")

        client_display = wx.GetClientDisplayRect()
        size = (min(1500, client_display.Width), min(875, client_display.Height))
        self.SetSize(self._FromDIP(size))

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.orig_secm = secm
        self.secm = copy.copy(secm)
        self.manip_item = manip_item

        self.current_panel = 0
        self.bi = None

        self._layout()

        self.panel_results = [None for panel in self.panels]

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()
        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.svd_panel.updateColors()
        self.efa_panel.updateColors()
        self.run_panel.updateColors()

    def _layout(self):

        parent = wx.Panel(self)

        # Create the individual panels
        self.svd_panel = REGALSSVDPanel(parent, self.secm, self.manip_item)
        self.efa_panel = REGALSEFAPanel(parent, self.secm, self.manip_item)
        self.run_panel = REGALSRunPanel(parent, self.secm, self)

        self.panels = [self.svd_panel, self.efa_panel, self.run_panel]

        #Creating the fixed buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.next_button = wx.Button(parent, -1, 'Next')
        self.next_button.Bind(wx.EVT_BUTTON, self._on_next_button)

        self.back_button = wx.Button(parent, -1, 'Back')
        self.back_button.Bind(wx.EVT_BUTTON, self._on_back_button)
        self.back_button.Disable()

        self.cancel_button = wx.Button(parent, -1, 'Cancel')
        self.cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel_button)

        self.done_button = wx.Button(parent, -1, 'Done')
        self.done_button.Bind(wx.EVT_BUTTON, self._on_done_button)
        self.done_button.Disable()

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._on_info_button)

        button_sizer.Add(self.cancel_button, 0 , wx.LEFT, border=self._FromDIP(3))
        button_sizer.Add(self.done_button, 0, wx.LEFT, border=self._FromDIP(3))
        button_sizer.Add(info_button, 0, wx.LEFT, border=self._FromDIP(3))
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.back_button, 0, wx.RIGHT, border=self._FromDIP(3))
        button_sizer.Add(self.next_button, 0, wx.RIGHT, border=self._FromDIP(3))


        self.top_sizer = wx.BoxSizer(wx.VERTICAL)
        self.top_sizer.Add(self.svd_panel, proportion=1, flag=wx.EXPAND)
        self.top_sizer.Add(self.efa_panel, proportion=1, flag=wx.EXPAND)
        self.top_sizer.Add(self.run_panel, proportion=1, flag=wx.EXPAND)
        self.top_sizer.Add(wx.StaticLine(parent, wx.ID_ANY, style=wx.LI_HORIZONTAL),
            flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=self._FromDIP(5))
        self.top_sizer.Add(button_sizer, flag=wx.TOP|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(3))

        self.top_sizer.Hide(self.efa_panel, recursive=True)
        self.top_sizer.Hide(self.run_panel, recursive=True)

        parent.SetSizer(self.top_sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(parent, flag=wx.EXPAND, proportion=1)

        self.SetSizer(frame_sizer)
        self.Layout()

    def _on_next_button(self, evt):
        self.panel_results[self.current_panel] = self.panels[self.current_panel].get_panel_results()

        self.top_sizer.Hide(self.panels[self.current_panel], recursive=True)

        if self.current_panel == 0 and not self.panel_results[0]['use_efa']:
            self.top_sizer.Show(self.panels[self.current_panel+2], recursive=True)
            self.current_panel += 2
        else:
            self.top_sizer.Show(self.panels[self.current_panel+1], recursive=True)
            self.current_panel += 1

        self.panels[self.current_panel].refresh_display()
        self.panels[self.current_panel].initialize(self.panel_results)

        if self.current_panel == len(self.panels) -1:
            self.next_button.Disable()
            self.done_button.Enable()

        if self.current_panel >= 1:
            self.back_button.Enable()

        self.SendSizeEvent()

    def _on_back_button(self, evt):
        self.panel_results[self.current_panel] = self.panels[self.current_panel].get_panel_results()

        self.top_sizer.Hide(self.panels[self.current_panel], recursive=True)

        next_panel = self.current_panel-1

        if next_panel == 1 and not self.panel_results[0]['use_efa']:
            self.top_sizer.Show(self.panels[self.current_panel-2], recursive=True)
            self.current_panel -= 2
        else:
            self.top_sizer.Show(self.panels[self.current_panel-1], recursive=True)
            self.current_panel -= 1

        self.panels[self.current_panel].update(self.panel_results)

        if self.current_panel == 0:
            self.back_button.Disable()

        if self.current_panel <= len(self.panels) - 2:
            self.next_button.Enable()
            self.done_button.Disable()

        self.SendSizeEvent()

    def _on_cancel_button(self, evt):
        if self.panels[-1].regals_running:
            msg = ('REGALS is currently running, are you sure you want to '
                'close the window and abort REGALS?')
            dlg = wx.MessageDialog(self, msg, 'REGALS Running',
                style=wx.ICON_INFORMATION|wx.YES_NO)
            result = dlg.ShowModal()
            dlg.Destroy()

            if result == wx.ID_YES:
                close = True
                self.panels[-1].abort_regals()

            else:
                close = False

        else:
            close = True

        if close:
            self.OnClose()

    def _on_done_button(self, evt):

        if self.panels[-1].regals_running:
            msg = ('REGALS is currently running, are you sure you want to '
                'close the window and abort REGALS?')
            dlg = wx.MessageDialog(self, msg, 'REGALS Running',
                style=wx.ICON_INFORMATION|wx.YES_NO)
            result = dlg.ShowModal()
            dlg.Destroy()

            if result == wx.ID_YES:
                close = True
                self.panels[-1].abort_regals()

            else:
                close = False

        else:
            close = True

        if close:
            self.panel_results[-1] = self.run_panel.get_panel_results()
            profiles = self.panel_results[-1]['profiles']

            if profiles is not None:
                regals_results = self.panel_results[-1]['regals_results']

                RAWGlobals.mainworker_cmd_queue.put(['to_plot_sasm', [profiles, 'black', None, True, 2]])

                if self.manip_item is not None:
                    analysis_dict = self.secm.getParameter('analysis')

                    regals_dict = {}

                    regals_dict['fstart'] = self.panel_results[0]['fstart']
                    regals_dict['fend'] = self.panel_results[0]['fend']
                    regals_dict['profile'] = self.panel_results[0]['profile']
                    regals_dict['nsvs'] = len(profiles)
                    regals_dict['ranges'] = regals_results['settings']['ranges']
                    regals_dict['frame_ranges'] = regals_results['settings']['frame_ranges']
                    regals_dict['component_settings'] = regals_results['settings']['comp_settings']
                    regals_dict['run_settings'] = regals_results['settings']['ctrl_settings']
                    regals_dict['exp_type'] = self.panel_results[0]['exp_type']
                    regals_dict['use_efa'] = self.panel_results[0]['use_efa']

                    if self.panel_results[1] is not None:
                        regals_dict['background_components'] = self.panel_results[1]['bkg_components']

                    if not np.array_equal(self.panel_results[-1]['x_calibration']['x'],
                        np.arange(self.panel_results[0]['fstart'],
                            self.panel_results[0]['fend']+1)):
                        regals_dict['x_calibration'] = self.panel_results[-1]['x_calibration']

                    analysis_dict['regals'] = regals_dict

                    self.manip_item.markAsModified()

            self.OnClose()

    def _on_info_button(self, evt):
        msg = ('If you use REGALS in your work, in addition to citing '
            'the RAW paper please cite:\n'
            'Steve P. Meisburger, Da Xu, and Nozomi Ando. IUCrJ 2021 8 '
            '(2), 225-237. DOI: 10.1107/S2052252521000555')
        wx.MessageBox(str(msg), "How to cite REGALS",
            style=wx.ICON_INFORMATION|wx.OK)

    def show_busy_dialog(self, show, msg=''):
        if show:
            if msg == '':
                msg = 'Please wait, calculating . . .'
            self.bi = wx.BusyInfo(msg, self)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass

    def save_data(self):
        self.panel_results[-1] = self.run_panel.get_panel_results()

        profiles = self.panel_results[-1]['profiles']

        if profiles is not None:
            dirctrl = wx.FindWindowByName('DirCtrlPanel')
            path = str(dirctrl.getDirLabel())

            filename = self.panel_results[0]['filename']

            name, ext = os.path.splitext(filename)

            filename = name + '_regals.csv'

            dialog = wx.FileDialog(self, message=("Please select save "
                "directory and enter save file name"), style=wx.FD_SAVE,
                defaultDir=path, defaultFile=filename)

            if dialog.ShowModal() == wx.ID_OK:
                save_path = dialog.GetPath()
                name, ext = os.path.splitext(save_path)
                save_path = name+'.csv'
                dialog.Destroy()
            else:
                dialog.Destroy()
                return

            RAWGlobals.save_in_progress = True
            self.main_frame.setStatus('Saving REGALS data', 0)

            SASFileIO.saveREGALSData(save_path, self.panel_results)

            RAWGlobals.save_in_progress = False
            self.main_frame.setStatus('', 0)

        else:
            msg = ("REGALS hasn't been run yet, so there are no results "
                "to save. Run REGALS then save the results.")
            dlg = wx.MessageDialog(self, msg, 'No REGALS Results',
                style=wx.ICON_ERROR|wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def OnClose(self):
        self.Destroy()

class REGALSSVDPanel(wx.Panel):
    def __init__(self, parent, secm, manip_item):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.secm = secm
        self.manip_item = manip_item

        self._layout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()
        self.controlPanel.updateColors()

    def _layout(self):
        self.splitter = wx.SplitterWindow(self)

        self.plotPanel = SVDResultsPlotPanel(self.splitter, wx.ID_ANY)
        self.controlPanel = SVDControlPanel(self.splitter, wx.ID_ANY,
            self.secm, self.manip_item, self, 'REGALS')

        self.splitter.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(325))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter.SetMinimumPaneSize(self._FromDIP(325))    #Back compatability with older wxpython versions
        else:
            self.splitter.SetMinimumPaneSize(self._FromDIP(50))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.splitter, proportion=1, flag=wx.EXPAND)

        self.SetSizer(top_sizer)


    def plotSVD(self, svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor,
        svd_start,  svd_end):
        self.plotPanel.plotSVD( svd_U, svd_s, svd_V, svd_U_autocor,
            svd_V_autocor, svd_start,  svd_end)

    def get_panel_results(self):
        return self.controlPanel.getResults()

    def update(self, all_previous_results):
        regals_results = all_previous_results[2]

        if regals_results is not None:
            if regals_results['profiles'] is not None:
                nvals = len(regals_results['profiles'])

                if nvals != self.controlPanel.getSignificant():
                    self.controlPanel.setSignificant(nvals)

    def refresh_display(self):
        pass

class REGALSEFAPanel(wx.Panel):
    def __init__(self, parent, secm, manip_item):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.secm = secm
        self.manip_item = manip_item

        self._layout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()

    def _layout(self):
        self.splitter = wx.SplitterWindow(self)

        self.plotPanel = EFAResultsPlotPanel2(self.splitter, wx.ID_ANY)
        self.controlPanel = EFAControlPanel2(self.splitter, wx.ID_ANY,
            self.secm, self.manip_item, self, 'REGALS')

        self.splitter.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(300))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter.SetMinimumPaneSize(self._FromDIP(300))    #Back compatability with older wxpython versions
        else:
            self.splitter.SetMinimumPaneSize(self._FromDIP(50))


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.splitter, proportion=1, flag=wx.EXPAND)

        self.SetSizer(top_sizer)

    def get_panel_results(self):
        return self.controlPanel.getResults()

    def initialize(self, all_previous_results):
        previous_results = all_previous_results[0]

        if not self.controlPanel.initialized:
            self.controlPanel.initialize(previous_results)

        elif (previous_results['fstart'] != self.controlPanel.panel1_results['fstart']
            or previous_results['fend'] != self.controlPanel.panel1_results['fend']
            or previous_results['profile'] != self.controlPanel.panel1_results['profile']):
            self.controlPanel.reinitialize(previous_results, efa = True)

        elif  previous_results['input'] != self.controlPanel.panel1_results['input']:
            self.controlPanel.reinitialize(previous_results, efa = False)

        self.Layout()

    def update(self, all_previous_results):
        regals_results = all_previous_results[-1]

        if regals_results is not None and regals_results['regals_results'] is not None:
            new_ranges = regals_results['regals_results']['settings']['frame_ranges']

            if len(new_ranges) == self.controlPanel.panel1_results['input']:
                points = np.array(new_ranges)

                forward_sv = points[:,0]
                backward_sv = points[:,1]

                bkg_comp = all_previous_results[1]['bkg_components']

                backward_sv = np.roll(backward_sv, -1*bkg_comp)
                points = np.column_stack((forward_sv, backward_sv))

                self.controlPanel.setSVs(points)

            else:
                svd_results = copy.deepcopy(all_previous_results[0])
                svd_results['input'] = len(new_ranges)
                self.controlPanel.reinitialize(svd_results, False, new_ranges)

    def refreshEFAPlot(self):
        self.plotPanel.refresh()

    def plotEFA(self, forward_data, backward_data):
        self.plotPanel.plotEFA(forward_data, backward_data)

    def refresh_display(self):
        self.plotPanel.refresh_display()

class REGALSRunPanel(wx.Panel):
    def __init__(self, parent, secm, regals_frame):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.comp_panels = []

        self.secm = secm

        self.regals_x = None

        self.regals_thread = None
        self.regals_results = None
        self.sasms = None
        self.ifts = None

        self.regals_running = False
        self.regals_already_done = False

        self.regals_frame = regals_frame

        self.regals_abort_event = threading.Event()

        self._create_layout()

        self.Layout()

        prof_settings = {
            'type': 'simple',
            'lambda': 0.0,
            'auto_lambda': True,
            'kwargs': {
                'Nw': 50,
                'dmax': 100,
                'is_zero_at_r0': True,
                'is_zero_at_dmax': True,
                }
            }

        conc_settings = {
            'type': 'smooth',
            'lambda': 1.0,
            'auto_lambda': True,
            'xrange': [0, 10],
            'kwargs' : {
                'Nw': 50,
                'is_zero_at_xmin': True,
                'is_zero_at_xmax': True,
                'xmin': 0,
                'xmax': 10,
                },
            'frame_xmin': 0,
            'frame_xmax': 10,
        }

        self._default_component_settings = (prof_settings, conc_settings)


    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.controls.updateColors()
        self.results.updateColors()

    def _create_layout(self):
        parent = self

        self.controls = REGALSControls(parent, self.regals_frame, self.secm,
            self.on_component_change, self.run_regals, self.abort_regals,
            self.change_x)

        self.comp_grid = REGALSComponentGrid(parent, self.on_range_change,
            self.on_update_regals, self.regals_frame)

        self.results = REGALSResults(parent, self.regals_frame)

        sub_sizer = wx.BoxSizer(wx.VERTICAL)
        sub_sizer.Add(self.controls, flag=wx.EXPAND)
        sub_sizer.Add(self.comp_grid, proportion=1,
            flag=wx.EXPAND|wx.TOP, border=self._FromDIP(5))

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(sub_sizer, flag=wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        top_sizer.Add(self.results, flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.RIGHT,
            border=self._FromDIP(5), proportion=1)

        self.SetSizer(top_sizer)

    def refresh_display(self):
        pass

    def on_component_change(self, num_comps):
        self.controls.set_component_number(num_comps)
        self.comp_grid.set_component_number(num_comps,
            self._default_component_settings)
        self.on_range_change()
        self.SendSizeEvent()

    def run_regals(self):
        if self.svd_results['secm_choice'] == 'usub':
            regals_secm = self.secm
        elif self.svd_results['secm_choice'] == 'sub':
            regals_secm = self.svd_results['sub_secm']
        elif self.svd_results['secm_choice'] == 'bl':
            regals_secm = self.svd_results['bl_secm']

        start = self.svd_results['fstart']
        end = self.svd_results['fend']

        ref_q = regals_secm.getSASMList(start, end)[0].getQ()

        ctrl_settings = self.controls.get_settings()
        comp_settings = self.comp_grid.get_all_component_settings()
        comp_ranges = self.comp_grid.get_component_ranges()
        comp_frame_ranges = self.comp_grid.get_component_frame_ranges()

        self.regals_running = True
        self.regals_frame.show_busy_dialog(True)

        self.regals_abort_event.clear()

        self.regals_settings = {
            'ctrl_settings': copy.deepcopy(ctrl_settings),
            'comp_settings': copy.deepcopy(comp_settings),
            'ranges': comp_ranges,
            'frame_ranges': comp_frame_ranges,
            }

        seed_previous = ctrl_settings.pop('seed_previous')
        ctrl_settings['callback'] = self.on_regals_finished_callback
        ctrl_settings['abort_event'] = self.regals_abort_event

        use_previous_results = (seed_previous and self.regals_results is not None
            and len(self.regals_results['mixture'].u_profile) == len(comp_settings))

        valid = self.validate_regals(regals_secm, start, end, ref_q,
            ctrl_settings, self.regals_settings['comp_settings'], comp_ranges,
            use_previous_results, warn=False)

        if valid:

            if use_previous_results:
                mixture, components = SASCalc.create_regals_mixture(comp_settings,
                    ref_q, self.regals_x['x'], self.intensity, self.sigma, seed_previous,
                    self.regals_results['mixture'])

            else:
                mixture, components = SASCalc.create_regals_mixture(comp_settings,
                    ref_q, self.regals_x['x'], self.intensity, self.sigma)

            self.set_lambdas(mixture.lambda_concentration, mixture.lambda_profile)

            for j, comp in enumerate(self.regals_settings['comp_settings']):
                    prof = comp[0]
                    conc = comp[1]

                    prof['lambda'] = mixture.lambda_profile[j]
                    conc['lambda'] = mixture.lambda_concentration[j]

            valid = self.validate_regals(regals_secm, start, end, ref_q,
            ctrl_settings, self.regals_settings['comp_settings'], comp_ranges,
            use_previous_results, validate=False)

            if valid:
                    self.regals_thread = threading.Thread(target=SASCalc.run_regals,
                        args=(mixture, self.intensity, self.sigma),
                        kwargs=ctrl_settings)
                    self.regals_thread.daemon = True
                    self.regals_thread.start()

            else:
                self.abort_regals()

        else:
            self.abort_regals()

    def abort_regals(self):
        self.regals_abort_event.set()

        self.controls.on_regals_finished()
        self.regals_frame.show_busy_dialog(False)
        self.regals_running = False

    def validate_regals(self, regals_secm, start, end, ref_q, ctrl_settings,
        comp_settings, regals_ranges, use_previous_results, warn=True,
        validate=True):

        if validate:
            try:
                q_valid = all([np.all(ref_q == sasm.getQ() for sasm in regals_secm.getSASMList(start, end))])
            except Exception:
                q_valid = False

            invalid_err = np.argwhere(np.array([sasm.getErr() for sasm in regals_secm.getSASMList(start, end)]) <= 0)

            if invalid_err.size > 0:
                err_valid = False
            else:
                err_valid = True

            range_valid = True

            regals_ranges = [np.array(rr) for rr in regals_ranges]

            for i in range(len(regals_ranges)):
                for j in range(i+1, len(regals_ranges)):
                    if (np.all(regals_ranges[i] == regals_ranges[j])
                        and not use_previous_results):
                        s1 = copy.deepcopy(comp_settings[i])
                        s2 = copy.deepcopy(comp_settings[j])

                        s1[0].pop('auto_lambda')
                        s1[1].pop('auto_lambda')
                        s2[0].pop('auto_lambda')
                        s2[1].pop('auto_lambda')

                        range_valid = not s1 == s2

                        if not range_valid:
                            break

            valid_settings = True

            settings_msg = ''

            for i, comp in enumerate(comp_settings):
                conc_comp = comp[1]

                if conc_comp['type'] != 'simple':
                    if conc_comp['lambda'] == 0 and not conc_comp['auto_lambda']:
                        nw = conc_comp['kwargs']['Nw']
                        xmin = conc_comp['kwargs']['xmin']
                        xmax = conc_comp['kwargs']['xmax']

                        frame_xmin = conc_comp['frame_xmin']
                        frame_xmax = conc_comp['frame_xmax']

                        if nw >= frame_xmax - frame_xmin:
                            valid_settings = False

                            msg = ('- Component {} grid points ({}) are more '
                                'than the number of measurements in the defined '
                                'range ({} to {}) and lambda is 0. Either set '
                                'lambda to a non-zero value, reduce the number '
                                'of grid points, or expand the concentration '
                                'range.\n'.format(i, nw, xmin, xmax))
                            settings_msg = settings_msg + msg


            valid = q_valid and err_valid and range_valid and valid_settings

            err_msg = ''
            if not q_valid:
                err_msg = err_msg+ ('- All q vectors must match to use REGALS. '
                    'One or more q vectors in the dataset does not match the '
                    'others.\n')

            if not err_valid:
                err_msg = err_msg + ('- All sigma (error) values need to be > 0. '
                    'One or more scattering profile in the dataset has one or '
                    'more sigma values <= 0.')

            if not range_valid:
                err_msg = err_msg+ ('- Components must be unique. Two or '
                    'more components are identical.\n')

            if not valid_settings:
                err_msg = err_msg + settings_msg

            if not valid:
                msg = ('The following errors must be fixed before REGALS can '
                    'be run:\n')
                msg = msg + err_msg
                dlg = wx.MessageDialog(self, msg, 'Invalid input/settings',
                    style=wx.ICON_ERROR|wx.OK)
                dlg.ShowModal()
                dlg.Destroy()

        else:
            valid = True


        if valid and warn:
            warn_settings = False

            warn_settings_msg = ''

            for i, comp in enumerate(comp_settings):
                prof_comp = comp[0]
                conc_comp = comp[1]

                if prof_comp['type'] == 'simple':
                    if prof_comp['lambda'] != 0:
                        warn_settings = True

                        msg = ('- Component {} concentration has a simple '
                            'regularizer but a non-zero lambda. This is '
                            'not recommended.\n'.format(i))
                        warn_settings_msg = warn_settings_msg + msg

                if conc_comp['type'] == 'simple':
                    if conc_comp['lambda'] != 0:
                        warn_settings = True

                        msg = ('- Component {} concentration has a simple '
                            'regularizer but a non-zero lambda. This is '
                            'not recommended.\n'.format(i))
                        warn_settings_msg = warn_settings_msg + msg


            warning = warn_settings

            if warning:
                msg = ('The following warnings were found for your REGALS '
                    'settings.\n')

                if warn_settings:
                    msg = msg + warn_settings_msg

                msg = msg + ('Do you want to run REGALS?')

                dlg = wx.MessageDialog(self, msg, 'REGALS Warnings',
                    style=wx.ICON_WARNING|wx.YES_NO)
                result = dlg.ShowModal()
                dlg.Destroy()

                if result == wx.ID_NO:
                    valid = False

        return valid

    def set_lambdas(self, conc_lambdas, prof_lambdas):
        self.comp_grid.set_lambdas(conc_lambdas, prof_lambdas)

    def on_update_regals(self):
        self.controls.set_regals_update()

    def on_range_change(self):
        new_ranges = self.comp_grid.get_component_ranges()
        self.controls.update_ranges(new_ranges, self.svd_results, self.secm)

    def initialize(self, all_previous_results):
        self.svd_results = all_previous_results[0]
        self.efa_results = all_previous_results[-2]

        nvals = self.svd_results['input']

        start = self.svd_results['fstart']
        end = self.svd_results['fend']

        run_regals_on_start = True

        self.regals_x = {'x': np.arange(start, end+1),
            'x_base': np.arange(start, end+1),
            'x_choice': 'X',
            }

        self._default_component_settings[1]['kwargs']['xmin'] = start
        self._default_component_settings[1]['kwargs']['xmax'] = end
        self._default_component_settings[1]['xrange'] = [start, end]
        self._default_component_settings[1]['frame_xmin'] = start
        self._default_component_settings[1]['frame_xmax'] = end

        if 'exp_type' in self.svd_results:
            if (self.svd_results['exp_type'] == 'Titration'
                or self.svd_results['exp_type'] == 'TR-SAXS'):
                self._default_component_settings[0]['type'] = 'realspace'
                self._default_component_settings[0]['kwargs']['Nw'] = 101

        self.on_component_change(nvals)

        analysis_dict = self.secm.getParameter('analysis')

        if ('regals' in analysis_dict and nvals == analysis_dict['regals']['nsvs']
            and start == analysis_dict['regals']['fstart']
            and end == analysis_dict['regals']['fend']
            and self.svd_results['profile'] == analysis_dict['regals']['profile']
            and nvals == len(analysis_dict['regals']['ranges'])):

            comp_settings = analysis_dict['regals']['component_settings']
            ctrl_settings = analysis_dict['regals']['run_settings']

            if nvals == len(comp_settings):
                self.comp_grid.set_all_component_settings(comp_settings)

            if self.efa_results is not None and self.svd_results['use_efa']:
                self.update_ranges_from_frames(self.efa_results['points'])
            else:
                self.update_ranges_from_frames(np.array(analysis_dict['regals']['frame_ranges']))

            self.controls.set_settings(ctrl_settings)

            if 'x_calibration' in analysis_dict['regals']:
                xdata = analysis_dict['regals']['x_calibration']
                old_start = analysis_dict['regals']['fstart']

                xdata['x'] = np.array(xdata['x'])
                xdata['x_base'] = np.array(xdata['x_base'])

                old_end = analysis_dict['regals']['fend']

                if len(xdata['x']) == len(self.regals_x['x']):
                    self.change_x(xdata['x'], xdata['x_base'], xdata['x_choice'])

                elif start >= old_start and end <= old_end:
                    self.change_x(xdata['x'][start-old_start:end-old_start+1],
                        xdata['x_base'][start-old_start:end-old_start+1],
                        xdata['x_choice'][start-old_start:end-old_start+1])

        else:
            if self.efa_results is not None and self.svd_results['use_efa']:
                self.update_ranges_from_frames(self.efa_results['points'])
            else:
                if not self.regals_already_done:
                    run_regals_on_start = False

            comp_settings = self.comp_grid.get_all_component_settings()

            for settings in comp_settings:
                if settings[1]['frame_xmin'] < start:
                    settings[1]['frame_xmin'] = start

                if settings[1]['frame_xmax'] > end:
                    settings[1]['frame_xmax'] = end

                if settings[1]['xrange'][0] < start:
                    settings[1]['xrange'][0] = start

                if settings[1]['xrange'][1] > end:
                    settings[1]['xrange'][1] = end

                if settings[1]['kwargs']['xmin'] < start:
                    settings[1]['kwargs']['xmin'] = start

                if settings[1]['kwargs']['xmax'] > end:
                    settings[1]['kwargs']['xmax'] = end

                if settings[1]['frame_xmin'] == start:
                    settings[1]['kwargs']['is_zero_at_xmin'] = False

                if settings[1]['frame_xmax'] == end:
                    settings[1]['kwargs']['is_zero_at_xmax'] = False

            self.comp_grid.set_all_component_settings(comp_settings)

            if all_previous_results[-1] is not None:
                xdata = all_previous_results[-1]['x_calibration']
                old_start = all_previous_results[-1]['fstart']
                old_end = all_previous_results[-1]['fend']

                if len(xdata['x']) == len(self.regals_x['x']):
                    self.change_x(xdata['x'], xdata['x_base'], xdata['x_choice'])

                elif start >= old_start and end <= old_end:
                    self.change_x(xdata['x'][start-old_start:end-old_start+1],
                        xdata['x_base'][start-old_start:end-old_start+1],
                        xdata['x_choice'][start-old_start:end-old_start+1])

            new_frame_ranges = self.comp_grid.get_component_frame_ranges()
            self.update_ranges_from_frames(new_frame_ranges)
            new_ranges = self.comp_grid.get_component_ranges()
            self.controls.update_ranges(new_ranges, self.svd_results, self.secm)

        if self.svd_results['secm_choice'] == 'usub':
            regals_secm = self.secm
        elif self.svd_results['secm_choice'] == 'sub':
            regals_secm = self.svd_results['sub_secm']
        elif self.svd_results['secm_choice'] == 'bl':
            regals_secm = self.svd_results['bl_secm']

        sasm_list = regals_secm.getSASMList(start, end)
        i = np.array([sasm.getI() for sasm in sasm_list])
        err = np.array([sasm.getErr() for sasm in sasm_list])

        self.intensity = i.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose
        self.sigma = err.T

        if run_regals_on_start:
            self.controls.clear_regals_update()
            self.controls.do_regals()

        else:
            self.refresh_results()

    def update_ranges_from_frames(self, new_frame_ranges):
        start = self.svd_results['fstart']
        end = self.svd_results['fend']
        self.comp_grid.update_component_frame_ranges(new_frame_ranges, start, end)

        new_ranges = self.comp_grid.get_component_ranges()
        self.controls.update_ranges(new_ranges, self.svd_results, self.secm)


    def on_regals_finished_callback(self, *args, **kwargs):
         wx.CallAfter(self.on_regals_finished, *args, **kwargs)

    def on_regals_finished(self, *args, **kwargs):
        mixture, params, resid = args

        intensity = self.svd_results['int']
        sigma = self.svd_results['err']

        self.regals_results = {
            'mixture'   : mixture,
            'params'    : params,
            'resid'     : resid,
            'chisq'     : np.mean(resid ** 2, 0),
            'settings'  : self.regals_settings,
            'x'         : mixture.components[0].concentration._regularizer.x,
            'conc'      : SASCalc.make_regals_concs(mixture, intensity, sigma),
            'reg_conc'  : SASCalc.make_regals_regularized_concs(mixture),
            }

        if self.svd_results['secm_choice'] == 'usub':
            regals_secm = self.secm
        elif self.svd_results['secm_choice'] == 'sub':
            regals_secm = self.svd_results['sub_secm']
        elif self.svd_results['secm_choice'] == 'bl':
            regals_secm = self.svd_results['bl_secm']

        start = self.svd_results['fstart']
        end = self.svd_results['fend']

        ref_q = regals_secm.getSASMList(start, end)[0].getQ()
        ref_q_err = regals_secm.getSASMList(start, end)[0].getQErr()

        self.sasms = SASCalc.make_regals_sasms(mixture, ref_q, intensity, sigma,
            self.secm, start, end, ref_q_err)

        self.ifts = SASCalc.make_regals_ifts(mixture, ref_q, intensity, sigma,
            self.secm, start, end)

        self.controls.on_regals_finished()

        self.update_results()

        self.regals_frame.show_busy_dialog(False)
        self.regals_running = False

        self.regals_already_done = True

    def update_results(self):

        conc_data = self.regals_results['conc']

        rmsd_data = [self.regals_results['chisq'], self.regals_results['x']]

        total_iter = self.regals_results['params']['total_iter']
        aver_chisq = self.regals_results['params']['x2']

        regularized_concs = self.regals_results['reg_conc']

        self.results.update_results(self.sasms, rmsd_data, conc_data, total_iter,
            aver_chisq, self.ifts, regularized_concs)

    def refresh_results(self):
        self.results.refresh_results()

    def change_x(self, x, x_base, x_choice):
        self.regals_x = {'x': x,
            'x_base': x_base,
            'x_choice': x_choice,
            }

        old_ranges = self.comp_grid.get_component_frame_ranges()
        self.comp_grid.update_component_frame_ranges(old_ranges)

        start = self.svd_results['fstart']
        end = self.svd_results['fend']

        if np.array_equal(x, np.arange(start, end+1)):
            self.comp_grid.show_all_float_ranges(False)
        else:
            self.comp_grid.show_all_float_ranges(True)

        new_ranges = self.comp_grid.get_component_ranges()
        self.controls.update_ranges(new_ranges, self.svd_results, self.secm)

    def get_panel_results(self):
        start = self.svd_results['fstart']
        end = self.svd_results['fend']

        results = {
            'profiles' : self.sasms,
            'ifts' : self.ifts,
            'regals_results': self.regals_results,
            'x_calibration' : self.regals_x,
            'fstart' : start,
            'fend' : end,
            }

        return results

class REGALSControls(wx.Panel):

    def __init__(self, parent, regals_frame, secm, component_callback=None,
        regals_callback=None, abort_regals_callback=None, x_callback=None):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.regals_frame = regals_frame
        self.secm = secm

        self.component_callback = component_callback
        self.regals_callback = regals_callback
        self.abort_regals_callback = abort_regals_callback
        self.x_callback = x_callback

        self._layout()

        self._initialize()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.range_plot.updateColors()

    def _initialize(self):
        self.conv_type.SetStringSelection('Chi^2')
        self.max_iter.SetValue(1000)
        self.min_iter.SetValue(25)
        self.tol.SetValue('0.0001')

        self.seed_previous.SetValue(False)

        self.abort_regals.Disable()

        self._on_conv_type(None)

    def _layout(self):

        top_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, 'Controls')
        top_box = top_sizer.GetStaticBox()


        general_sizer = wx.StaticBoxSizer(wx.VERTICAL, top_box, 'General')
        general_box = general_sizer.GetStaticBox()

        self.component_num_ctrl = RAWCustomCtrl.IntSpinCtrl(general_box, wx.ID_ANY,
            min_val=1, size=self._FromDIP((60,-1)))
        self.seed_previous = wx.CheckBox(general_box, label='Start with previous results')
        self.run_regals = wx.Button(general_box, label='Run REGALS')
        self.abort_regals = wx.Button(general_box, label='Abort REGALS')
        self.calibrate_x = wx.Button(general_box, label='Calibrate X axis')

        self.component_num_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_component_change)
        self.seed_previous.Bind(wx.EVT_CHECKBOX, self._on_seed_previous)
        self.run_regals.Bind(wx.EVT_BUTTON, self._on_run_regals)
        self.abort_regals.Bind(wx.EVT_BUTTON, self._on_abort_regals)
        self.calibrate_x.Bind(wx.EVT_BUTTON, self._on_calibrate_x)


        self.general_ctrls_sizer = wx.GridBagSizer(vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        self.general_ctrls_sizer.Add(wx.StaticText(general_box,
            label='# of components:'), (0,0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.general_ctrls_sizer.Add(self.component_num_ctrl, (0,1),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.general_ctrls_sizer.Add(self.seed_previous, (1, 0), (1, 2),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.general_ctrls_sizer.Add(self.calibrate_x, (2, 0), (1, 2),
            flag=wx.ALIGN_CENTER_VERTICAL)

        start_sizer = wx.BoxSizer(wx.HORIZONTAL)
        start_sizer.Add(self.run_regals)
        start_sizer.Add(self.abort_regals, border=self._FromDIP(5), flag=wx.LEFT)

        general_sizer.Add(self.general_ctrls_sizer, border=self._FromDIP(5),
            proportion=1, flag=wx.EXPAND|wx.ALL)
        general_sizer.Add(start_sizer, border=self._FromDIP(5),
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM)


        conv_sizer = wx.StaticBoxSizer(wx.VERTICAL, top_box, 'Convergence')
        conv_box = conv_sizer.GetStaticBox()

        self.conv_type = wx.Choice(conv_box, choices=['Iterations', 'Chi^2'])
        self.conv_type.Bind(wx.EVT_CHOICE, self._on_conv_type)

        self.max_iter_label = wx.StaticText(conv_box, label='Max. iterations:')
        self.min_iter_label = wx.StaticText(conv_box, label='Min. iterations:')
        self.max_iter = RAWCustomCtrl.IntSpinCtrl(conv_box, wx.ID_ANY,
            min_val=1, size=self._FromDIP((60,-1)))
        self.min_iter = RAWCustomCtrl.IntSpinCtrl(conv_box, wx.ID_ANY,
            min_val=1, size=self._FromDIP((60,-1)))

        self.max_iter.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_iter_change)
        self.min_iter.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_iter_change)

        self.tol_label = wx.StaticText(conv_box, label='Tolerance:')
        self.tol = wx.TextCtrl(conv_box, size=self._FromDIP((60, -1)))
        self.tol.Bind(wx.EVT_TEXT, self._on_update_regals)

        self.conv_grid_sizer = wx.FlexGridSizer(cols=2, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))
        self.conv_grid_sizer.Add(wx.StaticText(conv_box, label='Conv. critera:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.conv_grid_sizer.Add(self.conv_type, flag=wx.ALIGN_CENTER_VERTICAL)
        self.conv_grid_sizer.Add(self.max_iter_label, flag=wx.ALIGN_CENTER_VERTICAL)
        self.conv_grid_sizer.Add(self.max_iter, flag=wx.ALIGN_CENTER_VERTICAL)
        self.conv_grid_sizer.Add(self.min_iter_label,
            flag=wx.ALIGN_CENTER_VERTICAL|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.conv_grid_sizer.Add(self.min_iter,
            flag=wx.ALIGN_CENTER_VERTICAL|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.conv_grid_sizer.Add(self.tol_label,
            flag=wx.ALIGN_CENTER_VERTICAL|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.conv_grid_sizer.Add(self.tol,
            flag=wx.ALIGN_CENTER_VERTICAL|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)

        conv_sizer.Add(self.conv_grid_sizer, border=self._FromDIP(5),
            flag=wx.EXPAND|wx.ALL, proportion=1)


        self.range_plot = EFARangePlotPanel(top_box, wx.ID_ANY)

        sub_sizer = wx.BoxSizer(wx.VERTICAL)
        sub_sizer.Add(general_sizer, border=self._FromDIP(5), flag=wx.EXPAND|wx.ALL)
        sub_sizer.Add(conv_sizer, border=self._FromDIP(5),
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM)

        top_sizer.Add(sub_sizer, border=self._FromDIP(5), flag=wx.EXPAND|wx.ALL)
        top_sizer.Add(self.range_plot, border=self._FromDIP(5),
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, proportion=1)

        self.SetSizer(top_sizer)

    def _on_component_change(self, evt):
        num_comps = self.component_num_ctrl.GetValue()

        if self.component_callback is not None:
            self.component_callback(num_comps)

        self.set_regals_update()

    def _on_seed_previous(self, evt):
        self.set_regals_update()

    def _on_conv_type(self, evt):
        self.set_regals_update()

        self._update_conv_type_layout()

    def _update_conv_type_layout(self):
        if self.conv_type.GetStringSelection() == 'Iterations':
            self.conv_grid_sizer.Hide(self.min_iter_label)
            self.conv_grid_sizer.Hide(self.min_iter)
            self.conv_grid_sizer.Hide(self.tol_label)
            self.conv_grid_sizer.Hide(self.tol)
        else:
            self.conv_grid_sizer.Show(self.min_iter_label)
            self.conv_grid_sizer.Show(self.min_iter)
            self.conv_grid_sizer.Show(self.tol_label)
            self.conv_grid_sizer.Show(self.tol)

        self.Layout()

    def _on_iter_change(self, evt):
        self.set_regals_update()

        if evt.GetEventObject == self.max_iter:
            cmin, cmax = self.min_iter.GetRange()
            self.min_iter.SetRange((cmin, self.max_iter.GetValue()-1))
        elif evt.GetEventObject == self.min_iter:
            cmin, cmax = self.max_iter.GetRange()
            self.max_iter.SetRange((self.min_iter.GetValue()+1, cmax))

    def _on_calibrate_x(self, evt):
        start = self.regals_frame.run_panel.svd_results['fstart']
        end = self.regals_frame.run_panel.svd_results['fend']

        cal_dialog = REGALSXCalibration(self.regals_frame, self.secm,
            self.regals_frame, start, end)

        ret = cal_dialog.ShowModal()

        if ret == wx.ID_OK:
            x, x_base, x_choice = cal_dialog.get_X_val()

            if self.x_callback is not None:
                wx.CallAfter(self.x_callback, x, x_base, x_choice)

        cal_dialog.Destroy()

    def set_regals_update(self):
        self.run_regals.SetBackgroundColour('yellow')
        self.run_regals.Refresh()

    def clear_regals_update(self):
        self.run_regals.SetBackgroundColour(wx.NullColour)
        self.run_regals.Refresh()

    def _on_run_regals(self, evt):
        if self.regals_callback is not None:
            self.do_regals()

    def _on_abort_regals(self, evt):
        if self.abort_regals_callback is not None:
            self.abort_regals.Disable()
            self.run_regals.Enable()
            wx.CallAfter(self.abort_regals_callback)

    def do_regals(self):
        self.clear_regals_update()
        self.abort_regals.Enable()
        self.run_regals.Disable()
        wx.CallAfter(self.regals_callback)

    def on_regals_finished(self):
        self.abort_regals.Disable()
        self.run_regals.Enable()

    def get_settings(self):
        settings = {
            'seed_previous' : self.seed_previous.GetValue(),
            'conv_type'     : self.conv_type.GetStringSelection(),
            'max_iter'      : self.max_iter.GetValue(),
            'min_iter'      : self.min_iter.GetValue(),
            'tol'           : float(self.tol.GetValue()),
            }

        return settings

    def _on_update_regals(self, evt):
        self.set_regals_update()

    def update_ranges(self, new_ranges, svd_results, secm):
        ydata_type = svd_results['ydata_type']

        if svd_results['secm_choice'] == 'usub':
            plot_secm = secm
        elif svd_results['secm_choice'] == 'sub':
            plot_secm = svd_results['sub_secm']
        elif svd_results['secm_choice'] == 'bl':
            plot_secm = svd_results['bl_secm']

        framei = svd_results['fstart']
        framef = svd_results['fend']

        self.range_plot.plotRange(plot_secm, framei, framef, ydata_type,
            new_ranges, self.regals_frame.run_panel.regals_x['x'])

    def set_component_number(self, num_comps):
        self.component_num_ctrl.SetValue(num_comps)

    def set_settings(self, settings):
        self.seed_previous.SetValue(settings['seed_previous'])
        self.conv_type.SetStringSelection(settings['conv_type'])
        self.max_iter.SetValue(int(settings['max_iter']))
        self.min_iter.SetValue(int(settings['min_iter']))
        self.tol.SetValue(str(settings['tol']))

        self._update_conv_type_layout()



class REGALSComponentGrid(scrolled.ScrolledPanel):

    def __init__(self, parent, range_callback, update_callback, regals_frame,
        *args, **kwargs):
        scrolled.ScrolledPanel.__init__(self, parent, *args, **kwargs)

        self.SetMinSize((800, 425))

        self.component_panels = []
        self.range_callback = range_callback
        self.update_callback = update_callback
        self.regals_frame = regals_frame

        self._layout()

        self.SetupScrolling()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _layout(self):
        self.grid_sizer =wx.FlexGridSizer(cols = 3,vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))

        top_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, 'Components')
        self.top_box = top_sizer.GetStaticBox()

        top_sizer.Add(self.grid_sizer, border=self._FromDIP(5), flag=wx.ALL)

        self.SetSizer(top_sizer)

    def set_component_number(self, num_comps, comp_settings=None):
        if num_comps < len(self.component_panels):
            while num_comps < len(self.component_panels):
                self.remove_component()

        elif num_comps > len(self.component_panels):
            while num_comps > len(self.component_panels):
                self.add_component(comp_settings)

    def add_component(self, component_settings):

        new_comp = REGALSComponent(self.top_box, self.range_callback,
            self.update_callback, self.regals_frame, len(self.component_panels))
        new_comp.set_settings(component_settings)

        self.component_panels.append(new_comp)
        self.grid_sizer.Add(new_comp)
        self.Layout()

    def remove_component(self, component=-1):
        if (len(self.component_panels) > 0 and (component == -1
            or component<len(self.component_panels))):
            comp = self.component_panels.pop(component)
            self.grid_sizer.Detach(comp)
            comp.Destroy()
            self.Layout()

    def get_all_component_settings(self):
        comp_settings = [comp.get_settings() for comp in self.component_panels]
        return comp_settings

    def get_component_settings(self, comp_num):
        return self.component_panels[comp_num].get_settings()

    def get_component_ranges(self):
        comp_ranges = np.array([comp.get_range() for comp in self.component_panels])
        return comp_ranges

    # def update_component_ranges(self, new_ranges, cmin=None, cmax=None):
    #     for i, new_range in enumerate(new_ranges):
    #         self.component_panels[i].set_range(new_range, cmin, cmax)

    def update_component_frame_ranges(self, new_ranges, cmin=None, cmax=None):
        for i, new_range in enumerate(new_ranges):
            self.component_panels[i].set_frame_range(new_range, cmin, cmax)

    def get_component_frame_ranges(self):
        comp_ranges = np.array([comp.get_frame_range() for comp in self.component_panels])
        return comp_ranges

    def set_lambdas(self, conc_lambdas, prof_lambdas):
        for j, component in enumerate(self.component_panels):
            component.set_lambdas(conc_lambdas[j], prof_lambdas[j])

    def set_all_component_settings(self, settings):
        for j, comp_settings in enumerate(settings):
            self.component_panels[j].set_settings(comp_settings)

    def set_component_settings(self, settings, comp_num):
        self.component_panels[comp_num].set_settings(settings)

    def show_all_float_ranges(self, show):
        for comp in self.component_panels:
            comp.show_float_range(show)

class REGALSComponent(wx.Panel):

    def __init__(self, parent, range_callback, update_callback, regals_frame,
        comp_num=0, init_settings=None):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.range_callback = range_callback
        self.update_callback = update_callback
        self.comp_num = comp_num
        self.regals_frame = regals_frame

        self._create_layout()

        self._initialize(init_settings)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _initialize(self, init_settings):
        if init_settings is None:
            self.prof_comp_ctrl.SetStringSelection('simple')
            self.prof_auto_regularizer_ctrl.SetValue(True)
            self.prof_regularizer_ctrl.SetValue(0)
            self.prof_nw_ctrl.SetValue(50)
            self.dmax_ctrl.SetValue(100)
            self.zero_at_rmin_ctrl.SetValue(True)
            self.zero_at_dmax_ctrl.SetValue(True)

            self.conc_comp_ctrl.SetStringSelection('smooth')
            self.conc_auto_regularizer_ctrl.SetValue(True)
            self.conc_regularizer_ctrl.SetValue(0)
            self.conc_nw_ctrl.SetValue(50)
            self.zero_at_xmin_ctrl.SetValue(True)
            self.zero_at_xmax_ctrl.SetValue(True)

            self.conc_start.SetValue(0)
            self.conc_end.SetValue(1)
            self.conc_start.SetRange((0, 0))
            self.conc_end.SetRange((1, 1))

            self.float_conc_start.SetValue(0)
            self.float_conc_end.SetValue(1)
            self.float_conc_start.SetRange((0, 0))
            self.float_conc_end.SetRange((1, 1))

        else:
            self.set_settings(init_settings)

        self.current_prof_reg = self.prof_comp_ctrl.GetStringSelection()

        self._on_prof_comp_change(None)
        self._on_conc_comp_change(None)

        self._on_auto_prof_lambda(None)
        self._on_auto_conc_lambda(None)

    def _create_layout(self):
        top_sizer = wx.StaticBoxSizer(wx.VERTICAL, self,
            'Component {}'.format(self.comp_num))
        top_box = top_sizer.GetStaticBox()

        self.prof_sizer = wx.StaticBoxSizer(wx.VERTICAL, top_box, 'Profile')
        prof_box = self.prof_sizer.GetStaticBox()

        self.prof_comp_ctrl = wx.Choice(prof_box,
            choices=['simple', 'smooth', 'realspace'])

        self.prof_comp_ctrl.Bind(wx.EVT_CHOICE, self._on_prof_comp_change)

        self.prof_auto_regularizer_ctrl = wx.CheckBox(prof_box, label='Auto lambda')
        self.prof_auto_regularizer_ctrl.Bind(wx.EVT_CHECKBOX, self._on_auto_prof_lambda)

        self.prof_regularizer_ctrl = RAWCustomCtrl.MagnitudeSpinCtrl(prof_box,
            wx.ID_ANY, size=self._FromDIP((80, -1)))

        self.prof_regularizer_ctrl.Bind(wx.EVT_TEXT, self._on_update_regals)

        self.prof_nw_ctrl = RAWCustomCtrl.IntSpinCtrl(prof_box, wx.ID_ANY,
            min_val=2, size=self._FromDIP((60,-1)))
        self.prof_nw_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_regals)

        self.dmax_ctrl = RAWCustomCtrl.IntSpinCtrl(prof_box,
            wx.ID_ANY, min_val=1, size=self._FromDIP((60,-1)))

        self.dmax_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_regals)

        self.zero_at_rmin_ctrl = wx.CheckBox(prof_box, label='Zero at Rmin')
        self.zero_at_dmax_ctrl = wx.CheckBox(prof_box, label='Zero at Dmax')

        self.zero_at_rmin_ctrl.Bind(wx.EVT_CHECKBOX, self._on_update_regals)
        self.zero_at_dmax_ctrl.Bind(wx.EVT_CHECKBOX, self._on_update_regals)

        prof_comp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prof_comp_sizer.Add(wx.StaticText(prof_box, label='Regularizer:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        prof_comp_sizer.Add(self.prof_comp_ctrl, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        prof_auto_reg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prof_auto_reg_sizer.Add(self.prof_auto_regularizer_ctrl,
            flag=wx.ALIGN_CENTER_VERTICAL)

        prof_reg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prof_reg_sizer.Add(wx.StaticText(prof_box, label='Lambda:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        prof_reg_sizer.Add(self.prof_regularizer_ctrl, proportion=1,
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))

        self.prof_nw_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.prof_nw_sizer.Add(wx.StaticText(prof_box, label='Grid Points:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.prof_nw_sizer.Add(self.prof_nw_ctrl, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        self.dmax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.dmax_sizer.Add(wx.StaticText(prof_box, label='Dmax:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.dmax_sizer.Add(self.dmax_ctrl, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        self.pr_min_max_sizer = wx.BoxSizer(wx.VERTICAL)
        self.pr_min_max_sizer.Add(self.zero_at_rmin_ctrl)
        self.pr_min_max_sizer.Add(self.zero_at_dmax_ctrl, flag=wx.TOP, border=self._FromDIP(5))

        self.prof_sizer.Add(prof_comp_sizer, flag=wx.ALL, border=self._FromDIP(5))
        self.prof_sizer.Add(prof_auto_reg_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.prof_sizer.Add(prof_reg_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5))
        self.prof_sizer.Add(self.prof_nw_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.prof_sizer.Add(self.dmax_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.prof_sizer.Add(self.pr_min_max_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))


        self.conc_sizer = wx.StaticBoxSizer(wx.VERTICAL, top_box, 'Concentration')
        conc_box = self.conc_sizer.GetStaticBox()

        self.conc_comp_ctrl = wx.Choice(conc_box,
            choices=['simple', 'smooth'])
        self.conc_comp_ctrl.SetStringSelection('smooth')

        self.conc_comp_ctrl.Bind(wx.EVT_CHOICE, self._on_conc_comp_change)

        self.conc_auto_regularizer_ctrl = wx.CheckBox(conc_box, label='Auto lambda')
        self.conc_auto_regularizer_ctrl.Bind(wx.EVT_CHECKBOX, self._on_auto_conc_lambda)

        self.conc_regularizer_ctrl = RAWCustomCtrl.MagnitudeSpinCtrl(conc_box,
            wx.ID_ANY, size=self._FromDIP((80, -1)))

        self.conc_regularizer_ctrl.Bind(wx.EVT_TEXT, self._on_update_regals)

        self.conc_start = RAWCustomCtrl.IntSpinCtrl(conc_box, wx.ID_ANY)
        self.conc_end = RAWCustomCtrl.IntSpinCtrl(conc_box, wx.ID_ANY)

        self.conc_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_range)
        self.conc_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_range)

        self.float_conc_start = RAWCustomCtrl.FloatSpinCtrl(conc_box, wx.ID_ANY)
        self.float_conc_end = RAWCustomCtrl.FloatSpinCtrl(conc_box, wx.ID_ANY)

        self.float_conc_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_float_range)
        self.float_conc_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_float_range)

        self.conc_nw_ctrl = RAWCustomCtrl.IntSpinCtrl(conc_box, wx.ID_ANY,
            min_val=2, size=self._FromDIP((60,-1)))
        self.conc_nw_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_update_regals)

        self.zero_at_xmin_ctrl = wx.CheckBox(conc_box, label='Zero at Xmin')
        self.zero_at_xmax_ctrl = wx.CheckBox(conc_box, label='Zero at Xmax')

        self.zero_at_xmin_ctrl.Bind(wx.EVT_CHECKBOX, self._on_update_regals)
        self.zero_at_xmax_ctrl.Bind(wx.EVT_CHECKBOX, self._on_update_regals)

        conc_comp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_comp_sizer.Add(wx.StaticText(conc_box, label='Regularizer:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        conc_comp_sizer.Add(self.conc_comp_ctrl, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        conc_auto_reg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_auto_reg_sizer.Add(self.conc_auto_regularizer_ctrl,
            flag=wx.ALIGN_CENTER_VERTICAL)

        conc_reg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_reg_sizer.Add(wx.StaticText(conc_box, label='Lambda:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        conc_reg_sizer.Add(self.conc_regularizer_ctrl, proportion=1,
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))

        self.conc_range_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.conc_range_sizer.Add(wx.StaticText(conc_box, label='Range:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.conc_range_sizer.Add(self.conc_start, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=self._FromDIP(5))
        self.conc_range_sizer.Add(wx.StaticText(conc_box, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=self._FromDIP(5))
        self.conc_range_sizer.Add(self.conc_end, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=self._FromDIP(5))

        self.float_conc_range_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.float_conc_range_sizer.Add(wx.StaticText(conc_box, label='Range:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.float_conc_range_sizer.Add(self.float_conc_start, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=self._FromDIP(5))
        self.float_conc_range_sizer.Add(wx.StaticText(conc_box, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=self._FromDIP(5))
        self.float_conc_range_sizer.Add(self.float_conc_end, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=self._FromDIP(5))

        self.conc_nw_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.conc_nw_sizer.Add(wx.StaticText(conc_box, label='Grid Points:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.conc_nw_sizer.Add(self.conc_nw_ctrl, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))

        self.conc_zero_sizer = wx.BoxSizer(wx.VERTICAL)
        self.conc_zero_sizer.Add(self.zero_at_xmin_ctrl)
        self.conc_zero_sizer.Add(self.zero_at_xmax_ctrl, flag=wx.TOP,
            border=self._FromDIP(5))

        self.conc_sizer.Add(conc_comp_sizer, flag=wx.ALL, border=self._FromDIP(5))
        self.conc_sizer.Add(conc_auto_reg_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.conc_sizer.Add(conc_reg_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5))
        self.conc_sizer.Add(self.conc_range_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.conc_sizer.Add(self.float_conc_range_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.conc_sizer.Add(self.conc_nw_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        self.conc_sizer.Add(self.conc_zero_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))



        top_sizer.Add(self.prof_sizer, flag=wx.EXPAND)
        top_sizer.Add(self.conc_sizer, flag=wx.EXPAND)

        self.SetSizer(top_sizer)

        self.show_float_range(False)

    def _on_prof_comp_change(self, evt):

        if self.prof_comp_ctrl.GetStringSelection() == 'simple':
            self.prof_sizer.Hide(self.prof_nw_sizer, recursive=True)
            self.prof_sizer.Hide(self.dmax_sizer, recursive=True)
            self.prof_sizer.Hide(self.pr_min_max_sizer, recursive=True)

            if (self.current_prof_reg == 'realspace'
                and self.prof_nw_ctrl.GetValue() == 101):
                self.prof_nw_ctrl.SetValue(50)

        elif self.prof_comp_ctrl.GetStringSelection() == 'smooth':
            self.prof_sizer.Show(self.prof_nw_sizer, recursive=True)
            self.prof_sizer.Hide(self.dmax_sizer, recursive=True)
            self.prof_sizer.Hide(self.pr_min_max_sizer, recursive=True)

            if (self.current_prof_reg == 'realspace'
                and self.prof_nw_ctrl.GetValue() == 101):
                self.prof_nw_ctrl.SetValue(50)

        elif self.prof_comp_ctrl.GetStringSelection() == 'realspace':
            self.prof_sizer.Show(self.prof_nw_sizer, recursive=True)
            self.prof_sizer.Show(self.dmax_sizer, recursive=True)
            self.prof_sizer.Show(self.pr_min_max_sizer, recursive=True)

            if (self.current_prof_reg != 'realspace'
                and self.prof_nw_ctrl.GetValue() == 50):
                self.prof_nw_ctrl.SetValue(101)

        self.current_prof_reg = self.prof_comp_ctrl.GetStringSelection()

        self.Layout()
        self.regals_frame.Layout()

        self._update_regals()

    def _on_conc_comp_change(self, evt):

        if self.conc_comp_ctrl.GetStringSelection() == 'simple':
            self.conc_sizer.Hide(self.conc_nw_sizer, recursive=True)
            self.conc_sizer.Hide(self.conc_zero_sizer, recursive=True)

        elif self.conc_comp_ctrl.GetStringSelection() == 'smooth':
            self.conc_sizer.Show(self.conc_nw_sizer, recursive=True)
            self.conc_sizer.Show(self.conc_zero_sizer, recursive=True)

        self.Layout()
        self.regals_frame.Layout()

        self._update_regals()

    def get_settings(self):

        prof_settings = self._get_prof_settings()
        conc_settings = self._get_conc_settings()

        return prof_settings, conc_settings

    def _get_prof_settings(self):
        prof_settings = {
            'type'          : self.prof_comp_ctrl.GetStringSelection(),
            'lambda'        : float(self.prof_regularizer_ctrl.GetValue()),
            'auto_lambda'   : self.prof_auto_regularizer_ctrl.GetValue(),
        }

        if prof_settings['type'] == 'simple':
            prof_settings['kwargs'] = {}

        elif prof_settings['type'] == 'smooth':
            prof_settings['kwargs'] = {
                'Nw'    : self.prof_nw_ctrl.GetValue(),
                }

        elif prof_settings['type'] == 'realspace':
            prof_settings['kwargs'] = {
                'dmax'              : self.dmax_ctrl.GetValue(),
                'Nw'                : self.prof_nw_ctrl.GetValue(),
                'is_zero_at_r0'     : self.zero_at_rmin_ctrl.GetValue(),
                'is_zero_at_dmax'   : self.zero_at_dmax_ctrl.GetValue(),
                }

        return prof_settings

    def _get_conc_settings(self):
        xmin = float(self.float_conc_start.GetValue())
        xmax = float(self.float_conc_end.GetValue())

        regals_x = self.regals_frame.run_panel.regals_x

        min_val, min_arg = SASUtils.find_closest(xmin, regals_x['x'])

        if np.isclose(xmin, regals_x['x'][min_arg]):
            xmin = regals_x['x'][min_arg]

        max_val, max_arg = SASUtils.find_closest(xmax, regals_x['x'])

        if np.isclose(xmax, regals_x['x'][max_arg]):
            xmax = regals_x['x'][max_arg]

        conc_settings = {
            'type'          : self.conc_comp_ctrl.GetStringSelection(),
            'lambda'        : float(self.conc_regularizer_ctrl.GetValue()),
            'auto_lambda'   : self.conc_auto_regularizer_ctrl.GetValue(),
            'kwargs'    : {
                'xmin'  : xmin,
                'xmax'  : xmax,
                },
            'xrange'    : [self.conc_start.GetRange()[0], self.conc_end.GetRange()[1]],
            'frame_xmin': self.conc_start.GetValue(),
            'frame_xmax': self.conc_end.GetValue(),
            }

        if conc_settings['type'] == 'smooth':
            conc_settings['kwargs']['Nw'] = self.conc_nw_ctrl.GetValue()
            conc_settings['kwargs']['is_zero_at_xmin'] = self.zero_at_xmin_ctrl.GetValue()
            conc_settings['kwargs']['is_zero_at_xmax'] = self.zero_at_xmax_ctrl.GetValue()

        return conc_settings

    def set_settings(self, settings):
        if settings is not None:
            prof_settings, conc_settings = settings

            self.prof_comp_ctrl.SetStringSelection(prof_settings['type'])

            if prof_settings['lambda'] is not None:
                self.prof_regularizer_ctrl.ChangeValue(float(prof_settings['lambda']))
                self.prof_auto_regularizer_ctrl.SetValue(prof_settings['auto_lambda'])

            if prof_settings['type'] == 'smooth':
                self.prof_nw_ctrl.SetValue(int(prof_settings['kwargs']['Nw']))

            elif prof_settings['type'] == 'realspace':
                self.prof_nw_ctrl.SetValue(int(prof_settings['kwargs']['Nw']))
                self.dmax_ctrl.SetValue(int(prof_settings['kwargs']['dmax']))
                self.zero_at_rmin_ctrl.SetValue(prof_settings['kwargs']['is_zero_at_r0'])
                self.zero_at_dmax_ctrl.SetValue(prof_settings['kwargs']['is_zero_at_dmax'])


            self.conc_comp_ctrl.SetStringSelection(conc_settings['type'])

            if conc_settings['lambda'] is not None:
                self.conc_regularizer_ctrl.ChangeValue(float(conc_settings['lambda']))
                self.conc_auto_regularizer_ctrl.SetValue(conc_settings['auto_lambda'])

            self.set_frame_range((conc_settings['frame_xmin'], conc_settings['frame_xmax']),
                conc_settings['xrange'][0], conc_settings['xrange'][1])

            if conc_settings['type'] == 'smooth':
                self.conc_nw_ctrl.SetValue(int(conc_settings['kwargs']['Nw']))
                self.zero_at_xmin_ctrl.SetValue(conc_settings['kwargs']['is_zero_at_xmin'])
                self.zero_at_xmax_ctrl.SetValue(conc_settings['kwargs']['is_zero_at_xmax'])

        self._on_prof_comp_change(None)
        self._on_conc_comp_change(None)

        self._on_auto_prof_lambda(None)
        self._on_auto_conc_lambda(None)

    def _on_auto_prof_lambda(self, evt):
        if self.prof_auto_regularizer_ctrl.GetValue():
            self.prof_regularizer_ctrl.Disable()
        else:
            self.prof_regularizer_ctrl.Enable()

        self._update_regals()

    def _on_auto_conc_lambda(self, evt):
        if self.conc_auto_regularizer_ctrl.GetValue():
            self.conc_regularizer_ctrl.Disable()
        else:
            self.conc_regularizer_ctrl.Enable()

        self._update_regals()

    def _on_update_regals(self, evt):
        self._update_regals()

    def _update_regals(self):
        self.update_callback()

    def _on_update_float_range(self, evt):
        regals_x = self.regals_frame.run_panel.regals_x

        start = self.regals_frame.run_panel.svd_results['fstart']

        if evt.GetEventObject() == self.float_conc_end:
            cmin, cmax = self.float_conc_start.GetRange()
            self.float_conc_start.SetRange((cmin, float(self.float_conc_end.GetValue())))

            val = self.float_conc_end.GetValue()

            min_val, min_arg = SASUtils.find_closest(float(val), regals_x['x'])

            min_arg = min_arg + start

            if min_arg == self.conc_start.GetValue():
                min_arg = min_arg + 1

            self.conc_end.SetValue(min_arg)

            cmin, cmax = self.conc_start.GetRange()
            cmax = min_arg-1

            self.conc_start.SetRange((cmin, cmax))


        elif evt.GetEventObject() == self.float_conc_start:
            cmin, cmax = self.float_conc_end.GetRange()
            self.float_conc_end.SetRange((float(self.float_conc_start.GetValue()), cmax))

            val = self.float_conc_start.GetValue()

            min_val, min_arg = SASUtils.find_closest(float(val), regals_x['x'])

            min_arg = min_arg + start

            if min_arg == self.conc_end.GetValue():
                min_arg = min_arg - 1

            self.conc_start.SetValue(min_arg)

            cmin, cmax = self.conc_end.GetRange()
            cmin = min_arg+1

            self.conc_end.SetRange((cmin, cmax))

        self.range_callback()
        self._update_regals()

    def _on_update_range(self, evt):
        regals_x = self.regals_frame.run_panel.regals_x
        start = self.regals_frame.run_panel.svd_results['fstart']

        if evt.GetEventObject() == self.conc_end:
            cmin, cmax = self.conc_start.GetRange()
            cmax = self.conc_end.GetValue()-1
            self.conc_start.SetRange((cmin, cmax))

            self.float_conc_end.SetValue(regals_x['x'][int(self.conc_end.GetValue())-start])
            self.float_conc_start.SetRange((regals_x['x'][cmin-start], regals_x['x'][cmax+1-start]))

        elif evt.GetEventObject() == self.conc_start:
            cmin, cmax = self.conc_end.GetRange()
            cmin = self.conc_start.GetValue()+1
            self.conc_end.SetRange((cmin, cmax))

            self.float_conc_start.SetValue(regals_x['x'][int(self.conc_start.GetValue())-start])
            self.float_conc_end.SetRange((regals_x['x'][cmin-1-start], regals_x['x'][cmax-start]))

        self.range_callback()
        self._update_regals()

    def get_range(self):
        return (float(self.float_conc_start.GetValue()),
            float(self.float_conc_end.GetValue()))

    def get_frame_range(self):
        return (int(self.conc_start.GetValue()), int(self.conc_end.GetValue()))

    def set_frame_range(self, new_range, cmin=None, cmax=None):
        start = self.regals_frame.run_panel.svd_results['fstart']

        if cmin is None:
            cmin, _ = self.conc_start.GetRange()
        if cmax is None:
            _, cmax = self.conc_end.GetRange()

        if new_range[0] > new_range[1]:
            new_range = [new_range[1], new_range[0]]

        elif new_range[0] == new_range[1]:
            if new_range[0] > cmin:
                new_range[0] = new_range[0]-1
            elif new_range[1] < cmax:
                new_range[1] = new_range[1]+1

        self.conc_start.SetRange((cmin, new_range[1]-1))
        self.conc_end.SetRange((new_range[0]+1, cmax))

        self.conc_start.SetValue(new_range[0])
        self.conc_end.SetValue(new_range[1])

        regals_x = self.regals_frame.run_panel.regals_x

        self.float_conc_start.SetRange((regals_x['x'][cmin-start],
            regals_x['x'][new_range[1]-start]))
        self.float_conc_end.SetRange((regals_x['x'][new_range[0]-start],
            regals_x['x'][cmax-start]))

        self.float_conc_start.SetValue(regals_x['x'][new_range[0]-start])
        self.float_conc_end.SetValue(regals_x['x'][new_range[1]-start])

    def set_lambdas(self, conc_lambda, prof_lambda):
        if not np.isfinite(conc_lambda):
            conc_lambda = 0

        if not np.isfinite(prof_lambda):
            prof_lambda = 0

        if self.conc_auto_regularizer_ctrl.GetValue():
            self.conc_regularizer_ctrl.ChangeValue(conc_lambda)

        if self.prof_auto_regularizer_ctrl.GetValue():
            self.prof_regularizer_ctrl.ChangeValue(prof_lambda)

    def show_float_range(self, show):
        if show:
            self.conc_sizer.Show(self.float_conc_range_sizer, recursive=True)
            self.conc_sizer.Hide(self.conc_range_sizer, recursive=True)

        else:
            self.conc_sizer.Hide(self.float_conc_range_sizer, recursive=True)
            self.conc_sizer.Show(self.conc_range_sizer, recursive=True)

        self.Layout()
        self.regals_frame.Layout()

class REGALSResults(wx.Panel):

    def __init__(self, parent, regals_frame, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.regals_frame = regals_frame

        self.SetMinSize((600, 400))
        self._create_layout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.results_plot.updateColors()

    def _create_layout(self):

        results_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label='Results')
        results_box = results_sizer.GetStaticBox()

        self.chisq = wx.StaticText(results_box, size=self._FromDIP((60, -1)))
        self.iters = wx.StaticText(results_box, size=self._FromDIP((60, -1)))

        save_regals_data = wx.Button(results_box, label='Save REGALS data (not profiles)')
        save_regals_data.Bind(wx.EVT_BUTTON, self._on_save_data)

        sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sub_sizer.Add(wx.StaticText(results_box, label='Iterations:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        sub_sizer.Add(self.iters, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL,
            border=self._FromDIP(5))
        sub_sizer.Add(wx.StaticText(results_box, label='Average Chi^2:'),
            flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=self._FromDIP(10))
        sub_sizer.Add(self.chisq, flag=wx.ALIGN_CENTRE_VERTICAL)
        sub_sizer.AddStretchSpacer(1)
        sub_sizer.Add(save_regals_data, border=self._FromDIP(5), flag=wx.LEFT)

        self.results_plot = EFAResultsPlotPanel3(results_box, wx.ID_ANY)

        results_sizer.Add(self.results_plot, proportion=1, flag=wx.EXPAND|
            wx.LEFT|wx.RIGHT|wx.BOTTOM, border=self._FromDIP(5))
        results_sizer.Add(sub_sizer, flag=wx.ALL|wx.EXPAND, border=self._FromDIP(5))

        self.SetSizer(results_sizer)

    def update_results(self, sasms, rmsd_data, conc_data, total_iter,
        aver_chisq, ifts, reg_concs):
        self.iters.SetLabel('{}'.format(total_iter))
        self.chisq.SetLabel('{}'.format(round(aver_chisq,3)))

        self.results_plot.plotEFA(sasms, rmsd_data, conc_data, ifts, reg_concs)

    def refresh_results(self):
        self.iters.SetLabel('')
        self.chisq.SetLabel('')
        self.results_plot.refresh()
        self.results_plot.ax_redraw()

    def _on_save_data(self, evt):
        self.regals_frame.save_data()

class REGALSXCalibration(wx.Dialog):

    def __init__(self, parent, series, regals_frame, start, end, *args, **kwargs):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, 'REGALS X Data Calibration', *args,
            style = wx.RESIZE_BORDER|wx.CAPTION, **kwargs)

        self.series = series
        self.regals_frame = regals_frame
        self.start = start
        self.end = end

        self._create_layout()

        self._initialize()

        self.Fit()
        SASUtils.set_best_size(self)
        self.CenterOnParent()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _create_layout(self):
        parent = self

        self.use_x = wx.Choice(parent, choices=['X', 'Log10(X)', 'Ln(X)'])

        load_x = wx.Button(parent, label='Load X values from file')
        load_x.Bind(wx.EVT_BUTTON, self._on_load_x)

        reset_x = wx.Button(parent, label='Reset X values to default')
        reset_x.Bind(wx.EVT_BUTTON, self._on_reset_x)

        use_sizer = wx.BoxSizer(wx.HORIZONTAL)
        use_sizer.Add(wx.StaticText(self, label='Use for X axis:'))
        use_sizer.Add(self.use_x, flag=wx.LEFT, border=self._FromDIP(5))
        use_sizer.Add(load_x, flag=wx.LEFT, border=self._FromDIP(30))
        use_sizer.Add(reset_x, flag=wx.LEFT, border=self._FromDIP(30))



        self.data_grid = wx.grid.Grid(parent)
        self.data_grid.CreateGrid(len(self.series.plot_frame_list[self.start:self.end+1]), 5)
        self.data_grid.SetColLabelValue(0, 'File Name')
        self.data_grid.SetColLabelValue(1, 'Frame Number')
        self.data_grid.SetColLabelValue(2, 'X')
        self.data_grid.SetColLabelValue(3, 'Log10(X)')
        self.data_grid.SetColLabelValue(4, 'Ln(X)')

        self.data_grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self._on_cell_changed)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(use_sizer, flag=wx.ALL, border=self._FromDIP(5))
        top_sizer.Add(self.data_grid, proportion=1, border=self._FromDIP(5),
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM)
        top_sizer.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), flag=wx.ALL,
            border=self._FromDIP(5))

        self.Bind(wx.EVT_BUTTON, self._onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)

        self.SetSizer(top_sizer)

    def _initialize(self):

        regals_x = self.regals_frame.run_panel.regals_x

        self.use_x.SetStringSelection(regals_x['x_choice'])

        for j in range(len(self.series.plot_frame_list[self.start:self.end+1])):
            self.data_grid.SetCellValue(j, 0, os.path.split(self.series._file_list[j+self.start])[1])
            self.data_grid.SetCellValue(j, 1, '{}'.format(self.series.plot_frame_list[j+self.start]))
            self._set_x_val(regals_x['x_base'][j], j)

            self.data_grid.SetReadOnly(j, 0)
            self.data_grid.SetReadOnly(j, 1)
            self.data_grid.SetReadOnly(j, 3)
            self.data_grid.SetReadOnly(j, 4)

        self.data_grid.AutoSizeColumns()
        self.data_grid.SetColSize(2, max(60, self.data_grid.GetColSize(2)))

    def _on_cell_changed(self, evt):
        row = evt.GetRow()

        try:
            val = float(self.data_grid.GetCellValue(row, 2).strip())
            self._set_x_val(val, row, False)
            self.data_grid.SetCellValue(row, 3, '{}'.format(np.log10(val)))
            self.data_grid.SetCellValue(row, 4, '{}'.format(np.log(val)))
        except Exception:
            msg = ('X values must be numeric.')
            dlg = wx.MessageDialog(self, msg, "Invalid X Value",
                style=wx.ICON_ERROR|wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def _set_x_val(self, val, row, set_x=True):

        if row < self.data_grid.GetNumberRows():
            if set_x:
                self.data_grid.SetCellValue(row, 2, '{}'.format(val))

            self.data_grid.SetCellValue(row, 3, '{}'.format(np.log10(val)))
            self.data_grid.SetCellValue(row, 4, '{}'.format(np.log(val)))

    def get_X_val(self):
        x_choice = self.use_x.GetStringSelection()

        if x_choice == 'X':
            col = 2
        elif x_choice == 'Log10(X)':
            col = 3
        elif x_choice == 'Ln(X)':
            col = 4

        try:
            x = np.array([float(self.data_grid.GetCellValue(j, col)) for j in range(self.data_grid.GetNumberRows())])
            x_base = np.array([float(self.data_grid.GetCellValue(j, 2)) for j in range(self.data_grid.GetNumberRows())])
        except Exception:
            x = None
            x_base = None

        return x, x_base, x_choice

    def _on_load_x(self, evt):
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        path = str(dirctrl.getDirLabel())

        dialog = wx.FileDialog(self, message="Please select file with X values",
            style=wx.FD_OPEN, defaultDir=path)

        if dialog.ShowModal() == wx.ID_OK:
            load_path = dialog.GetPath()
        else:
            load_path = None

        dialog.Destroy()

        if load_path is not None:
            loaded_x = np.loadtxt(load_path)

            for j, val in enumerate(loaded_x):
                self._set_x_val(val, j)

    def _on_reset_x(self, evt):
        new_x = np.arange(self.start, self.end+1)

        for j, val in enumerate(new_x):
            self._set_x_val(val, j)

    def _onOK(self, evt):
        x, x_base, x_choice = self.get_X_val()

        if x is None or x_base is None:
            valid = False
        elif not np.all(np.isfinite(x)) or not np.all(np.isfinite(x_base)):
            valid = False
        else:
            valid = True

        if not valid:
            msg = ('All X values must be finite numbers.')
            dlg = wx.MessageDialog(self, msg, "Invalid X Value",
                style=wx.ICON_ERROR|wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

        else:
            if self.IsModal():
                self.EndModal(wx.ID_OK)
            else:
                self.Close()

    def _onCancel(self, evt):
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Close()


class REGALSBackground(wx.Dialog):

    def __init__(self, parent, start, end, series, plot_type, max_comps, bkg_comps,
        *args, **kwargs):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, 'REGALS Background Components', *args,
            style = wx.RESIZE_BORDER|wx.CAPTION, **kwargs)

        self.series = series
        self.start = start
        self.end = end
        self.plot_type = plot_type

        if self.plot_type == 'usub':
            self.plot_type = 'unsub'
        elif self.plot_type == 'bl':
            self.plot_type = 'baseline'

        self.svd_results = {}

        self.prop_cycle = matplotlib.rcParams['axes.prop_cycle']()

        self._create_layout()

        self._initialize(max_comps, bkg_comps)

        self.Fit()
        SASUtils.set_best_size(self)
        self.CenterOnParent()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.svd_plot.updateColors()
        self.series_plot.updateColors()

    def _create_layout(self):
        parent = self

        ctrl_sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, label='Controls')
        ctrl_box = ctrl_sizer.GetStaticBox()

        self.series_plot = SeriesPlotPanel(ctrl_box, self.plot_type, 'REGALS')


        self.bkg_region_list = SeriesRangeItemList(self, 'buffer', ctrl_box,
            list_type='REGALS')
        self.bkg_region_list.SetMinSize(self._FromDIP((-1,130)))


        buffer_add_btn = wx.Button(ctrl_box, label='Add region')
        buffer_add_btn.Bind(wx.EVT_BUTTON, self._onSeriesAdd)

        buffer_remove_btn = wx.Button(ctrl_box, label='Remove region')
        buffer_remove_btn.Bind(wx.EVT_BUTTON, self._onSeriesRemove)

        buf_btn_sizer = wx.BoxSizer(wx.VERTICAL)
        buf_btn_sizer.Add(buffer_add_btn, flag=wx.BOTTOM, border=self._FromDIP(5))
        buf_btn_sizer.Add(buffer_remove_btn)

        buffer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        buffer_sizer.Add(self.bkg_region_list, proportion=1, flag=wx.EXPAND|wx.RIGHT,
            border=self._FromDIP(5))
        buffer_sizer.Add(buf_btn_sizer, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))


        self.start_svd = RAWCustomCtrl.IntSpinCtrl(ctrl_box, size=self._FromDIP((60,-1)))
        self.end_svd = RAWCustomCtrl.IntSpinCtrl(ctrl_box, size=self._FromDIP((60,-1)))

        self.start_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)
        self.end_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)

        plotted_svs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        plotted_svs_sizer.Add(wx.StaticText(ctrl_box, label='Plot indexes:'),
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))
        plotted_svs_sizer.Add(self.start_svd,
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))
        plotted_svs_sizer.Add(wx.StaticText(ctrl_box, label='to'),
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))
        plotted_svs_sizer.Add(self.end_svd, flag=wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))


        self.num_svs = RAWCustomCtrl.IntSpinCtrl(ctrl_box, size=self._FromDIP((60,-1)))

        num_svs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        num_svs_sizer.Add(wx.StaticText(ctrl_box, label='# Significant SVs:'),
            flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))
        num_svs_sizer.Add(self.num_svs, flag=wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))


        ctrl_sizer.Add(self.series_plot, proportion=1, flag=wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        ctrl_sizer.Add(buffer_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5))
        ctrl_sizer.Add(plotted_svs_sizer, flag=wx.ALL, border=self._FromDIP(5))
        ctrl_sizer.Add(num_svs_sizer, flag=wx.ALL, border=self._FromDIP(5))


        plot_sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, label='Results')
        plot_box = plot_sizer.GetStaticBox()

        self.svd_plot = REGALSBackgroundSVDPlot(plot_box)

        plot_sizer.Add(self.svd_plot, proportion=1, flag=wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sub_sizer.Add(ctrl_sizer, flag=wx.ALL|wx.EXPAND, proportion=1,
            border=self._FromDIP(5))
        sub_sizer.Add(plot_sizer, flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.EXPAND,
            proportion=1, border=self._FromDIP(5))


        cancel_button = wx.Button(parent, label='Cancel')
        cancel_button.Bind(wx.EVT_BUTTON, self._onCancel)
        done_button = wx.Button(parent, label='Done')
        done_button.Bind(wx.EVT_BUTTON, self._onOK)

        button_sizer = wx.BoxSizer()
        button_sizer.Add(cancel_button, flag=wx.ALL, border=self._FromDIP(5))
        button_sizer.Add(done_button, flag=wx.ALL, border=self._FromDIP(5))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sub_sizer, flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.EXPAND,
            proportion=1, border=self._FromDIP(5))
        top_sizer.Add(button_sizer, flag=wx.ALL,
            border=self._FromDIP(5))

        self.Bind(wx.EVT_BUTTON, self._onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)

        self.SetSizer(top_sizer)

    def _initialize(self, max_comps, bkg_comps):
        frames = self.series.getFrames()
        intensity = self.series.getIntI()

        frames = frames[self.start:self.end+1]
        intensity = intensity[self.start:self.end+1]

        self.update_plot_data(frames, intensity, 'intensity', 'left')
        if self.plot_type != 'unsub':
            self.update_plot_label('', 'right')

        self.start_svd.SetValue(0)
        self.end_svd.SetValue(10)

        self.start_svd.SetRange((0, 9))
        self.end_svd.SetRange((1,len(frames)))

        self.num_svs.SetValue(bkg_comps)
        self.num_svs.SetRange((0, max_comps))

    def update_plot_data(self, xdata, ydata, label, axis):
        self.series_plot.plot_data(xdata, ydata, label, axis)

    def update_plot_range(self, start, end, index, color):
        self.series_plot.plot_range(start, end, index, color)

        self.do_svd(start, end, index)

    def update_plot_label(self, label, axis):
        self.series_plot.plot_label(label, axis)

    def remove_plot_range(self, index):
        self.series_plot.remove_range(index)

        self.svd_plot.remove_data(index)

    def remove_plot_data(self, index):
        self.series_plot.remove_data(index)

    def pick_plot_range(self, start_item, end_item, index):
        self.series_plot.pick_range(start_item, end_item, index)

    def show_plot_range(self, index, show):
        self.series_plot.show_range(index, show)

    def _onSeriesAdd(self, evt):
        """Called when the Add control buttion is used."""
        index, start, end, color = self._addSeriesRange(self.bkg_region_list)
        self.update_plot_range(start, end, index, color)

    def _addSeriesRange(self, parent_list):
        range_item = parent_list.create_items()

        start, end = range_item.get_range()
        index = range_item.GetId()

        range_item.color = next(self.prop_cycle)['color']

        self.Layout()
        self.SendSizeEvent()

        return index, start, end, range_item.color

    def _onSeriesRemove(self, evt):
        """Called by the Remove control button, removes a control."""
        selected = self.bkg_region_list.get_selected_items()

        while len(selected) > 0:
            item = selected[0]
            idx = item.GetId()

            self.remove_plot_range(idx)

            if len(selected) > 1:
                self.bkg_region_list.remove_item(item, resize=False)
            else:
                self.bkg_region_list.remove_item(item, resize=True)

            del self.svd_results[idx]

        self.Layout()
        self.SendSizeEvent()

    def onSeriesPick(self, event):
        event_object = event.GetEventObject()
        event_item = event_object.GetParent()

        index = event_item.GetId()

        start_item = event_item.start_ctrl
        end_item = event_item.end_ctrl

        wx.CallAfter(self.pick_plot_range, start_item, end_item, index)

    def setPickRange(self, index, pick_range, plot_type):
        pick_range.sort()

        item = wx.FindWindowById(index)

        current_start_range = item.start_ctrl.GetRange()
        current_end_range = item.end_ctrl.GetRange()

        new_start = max(pick_range[0], current_start_range[0])
        new_end = min(pick_range[1], current_end_range[1])

        item.start_ctrl.SetValue(new_start)
        item.end_ctrl.SetValue(new_end)

        item.start_ctrl.SetRange((current_start_range[0], new_end))

        current_end_range = item.end_ctrl.GetRange()
        item.end_ctrl.SetRange((new_start, current_end_range[1]))

        self.update_plot_range(new_start, new_end, index, item.color)

    def updateSeriesRange(self, event):
        event_object = event.GetEventObject()
        event_item = event_object.GetParent()
        value = event_object.GetValue()

        start, end = event_item.get_range()
        index = event_item.GetId()

        if event_object is event_item.start_ctrl:
            current_range = event_item.end_ctrl.GetRange()
            event_item.end_ctrl.SetRange((value, current_range[-1]))
        else:
            current_range = event_item.start_ctrl.GetRange()
            event_item.start_ctrl.SetRange((current_range[0], value))

        self.update_plot_range(start, end, index, event_item.color)

    def _onChangeSVD(self, evt):
        for index in self.svd_results:
            self.plot_svd_results(index)

        start_svd = int(self.start_svd.GetValue())
        end_svd = int(self.end_svd.GetValue())

        start_range = self.start_svd.GetRange()
        end_range = self.end_svd.GetRange()

        self.start_svd.SetRange((start_range[0], end_svd-1))
        self.end_svd.SetRange((start_svd+1, end_range[1]))

    def do_svd(self, start, end, index):
        sasm_list = self.series.getSASMList(start, end)

        (svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, i, err, svd_a,
            success) = SASCalc.SVDOnSASMs(sasm_list, True)

        if index not in self.svd_results:
            self.svd_results[index] = {}

        self.svd_results[index]['svd_U_autocor'] = svd_U_autocor
        self.svd_results[index]['svd_V_autocor'] = svd_V_autocor
        self.svd_results[index]['svd_s'] = svd_s

        self.plot_svd_results(index)

    def plot_svd_results(self, index):
        svd_U_autocor = self.svd_results[index]['svd_U_autocor']
        svd_V_autocor = self.svd_results[index]['svd_V_autocor']
        svd_s = self.svd_results[index]['svd_s']

        xdata = np.arange(len(svd_s))

        svd_start = int(self.start_svd.GetValue())
        svd_end = int(self.end_svd.GetValue())

        item = wx.FindWindowById(index)

        plt_end = min(svd_end, len(svd_s)-1)
        self.svd_plot.plot_data(xdata[svd_start:plt_end+1],
            svd_s[svd_start:plt_end+1], index, 'sv', item.color)
        self.svd_plot.plot_data(xdata[svd_start:plt_end+1],
            svd_U_autocor[svd_start:plt_end+1], index, 'left_ac', item.color)
        self.svd_plot.plot_data(xdata[svd_start:plt_end+1],
            svd_V_autocor[svd_start:plt_end+1], index, 'right_ac', item.color)

    def get_bkg_comps(self):
        return int(self.num_svs.GetValue())

    def _onOK(self, evt):
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Close()

    def _onCancel(self, evt):
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Close()

class REGALSBackgroundSVDPlot(wx.Panel):

    def __init__(self, parent):

        wx.Panel.__init__(self, parent)


        self.sv_plot_lines = {}
        self.left_ac_plot_lines = {}
        self.right_ac_plot_lines = {}

        self.create_layout()

        self.fig.tight_layout()
        self.canvas.draw()

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateColors(self):
        SASUtils.update_mpl_style()
        self.canvas.ax_redraw()

    def create_layout(self):
        SASUtils.update_mpl_style()

        self.fig = Figure((5,4), 75)

        self.sv_subplot = self.fig.add_subplot(2,1,1, title='Singular Values')
        self.sv_subplot.set_xlabel('Value')
        self.sv_subplot.set_ylabel('Index')

        self.ac_subplot = self.fig.add_subplot(2,1,2, title='AutoCorrelation')
        self.ac_subplot.set_xlabel('Absolute Value')
        self.ac_subplot.set_ylabel('Index')


        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.EXPAND)

        self.SetSizer(sizer)

    def plot_data(self, xdata, ydata, label, axis, color=None):
        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)

        if axis == 'sv':
            try:
                line = self.sv_plot_lines[label]
            except Exception:
                line = None

        elif axis == 'left_ac':
            try:
                line = self.left_ac_plot_lines[label]
            except Exception:
                line = None

        else:
            try:
                line = self.right_ac_plot_lines[label]
            except Exception:
                line = None

        if color is None:
            if axis == 'sv':
                color = next(self.sv_subplot._get_lines.prop_cycler)['color']
            else:
                color = next(self.ac_subplot._get_lines.prop_cycler)['color']

        if line is None:
            if axis == 'sv':
                line, = self.sv_subplot.semilogy(xdata, ydata, '.-', color=color)
                self.sv_plot_lines[label] = line

            elif axis == 'left_ac':
                line, = self.ac_subplot.plot(xdata, ydata, '.-', color=color)
                self.left_ac_plot_lines[label] = line

            else:
                line, = self.ac_subplot.plot(xdata, ydata, '.--', color=color)
                self.right_ac_plot_lines[label] = line
        else:
            line.set_xdata(xdata)
            line.set_ydata(ydata)

        self.updatePlot()

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def remove_data(self, index):
        if index in self.sv_plot_lines:
            line = self.sv_plot_lines[index]
            line.remove()

            del self.sv_plot_lines[index]

        if index in self.left_ac_plot_lines:
            line = self.left_ac_plot_lines[index]
            line.remove()

            del self.left_ac_plot_lines[index]

        if index in self.right_ac_plot_lines:
            line = self.right_ac_plot_lines[index]
            line.remove()

            del self.right_ac_plot_lines[index]

        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''
        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def autoscale_plot(self):
        self.sv_subplot.set_autoscale_on(True)

        self.sv_subplot.relim()
        self.sv_subplot.autoscale_view()

        self.ac_subplot.set_autoscale_on(True)

        self.ac_subplot.relim()
        self.ac_subplot.autoscale_view()

        self.ax_redraw()

    def updatePlot(self):
        self.autoscale_plot()

class SimilarityFrame(wx.Frame):

    def __init__(self, parent, title, sasm_list):

        client_display = wx.GetClientDisplayRect()
        size = (min(600, client_display.Width), min(400, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))


        self.panel = wx.Panel(self, wx.ID_ANY, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.sasm_list = sasm_list

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        self.ids = {
                    'method'        : self.NewControlId(),
                    'correction'    : self.NewControlId(),
                    'hl_diff_chk'   : self.NewControlId(),
                    'hl_diff_val'   : self.NewControlId(),
                    'hl_same_chk'   : self.NewControlId(),
                    'hl_same_val'   : self.NewControlId(),
                    }

        self.pvals = None
        self.item_data = None
        self.corrected_pvals = None

        sizer = self._createLayout(self.panel)
        self._initSettings()

        self.panel.SetSizer(sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()

        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self._highlight()

    def _createLayout(self, parent):
        method_text = wx.StaticText(parent, -1, 'Method:')
        method_choice = wx.Choice(parent, self.ids['method'], choices = ['CorMap'])
        method_choice.Bind(wx.EVT_CHOICE, self._onMethodChange)
        correction_text = wx.StaticText(parent, -1, 'Multiple testing correction:')
        correction_choice = wx.Choice(parent, self.ids['correction'],
            choices=['None', 'Bonferroni'])
        correction_choice.SetStringSelection('Bonferroni')
        correction_choice.Bind(wx.EVT_CHOICE, self._onMethodChange)

        method_sizer = wx.BoxSizer(wx.HORIZONTAL)
        method_sizer.Add(method_text, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(3))
        method_sizer.Add(method_choice, 0, wx.RIGHT, border=self._FromDIP(6))
        method_sizer.Add(correction_text, 0, wx.RIGHT, border=self._FromDIP(3))
        method_sizer.Add(correction_choice, 0, wx.RIGHT, border=self._FromDIP(3))

        highlight_diff_chkbx = wx.CheckBox(parent, self.ids['hl_diff_chk'],
            'Highlight with p-value <')
        highlight_diff_chkbx.Bind(wx.EVT_CHECKBOX, self._onHighlightChange)
        highlight_diff_pval = wx.TextCtrl(parent, self.ids['hl_diff_val'], '0.01',
            size=self._FromDIP((65, -1)))
        highlight_diff_pval.SetBackgroundColour(wx.Colour(255,128,96))
        highlight_diff_pval.Bind(wx.EVT_TEXT, self._onTextEntry)

        highlight_same_chkbx = wx.CheckBox(parent, self.ids['hl_same_chk'],
            'Highlight with p-value >')
        highlight_same_chkbx.Bind(wx.EVT_CHECKBOX, self._onHighlightChange)
        highlight_same_pval = wx.TextCtrl(parent, self.ids['hl_same_val'], '0.01',
            size=self._FromDIP((65, -1)))
        highlight_same_pval.SetBackgroundColour('LIGHT BLUE')
        highlight_same_pval.Bind(wx.EVT_TEXT, self._onTextEntry)

        highlight_diff_sizer = wx.BoxSizer(wx.HORIZONTAL)
        highlight_diff_sizer.Add(highlight_diff_chkbx,0, wx.LEFT,
            border=self._FromDIP(3))
        highlight_diff_sizer.Add(highlight_diff_pval, 0, wx.RIGHT,
            border=self._FromDIP(3))
        highlight_diff_sizer.Add(highlight_same_chkbx,0, wx.LEFT,
            border=self._FromDIP(12))
        highlight_diff_sizer.Add(highlight_same_pval, 0, wx.RIGHT,
            border=self._FromDIP(3))

        self.listPanel = similiarityListPanel(parent, (-1, 300))

        #Creating the fixed buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.done_button = wx.Button(parent, -1, 'Done')
        self.done_button.Bind(wx.EVT_BUTTON, self._onDoneButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        save_button = wx.Button(parent, -1, 'Save')
        save_button.Bind(wx.EVT_BUTTON, self._onSaveButton)

        button_sizer.Add(self.done_button, 0, wx.RIGHT | wx.LEFT,
            border=self._FromDIP(3))
        button_sizer.Add(info_button, 0, wx.RIGHT, border=self._FromDIP(3))
        button_sizer.Add(save_button, 0, wx.RIGHT, border=self._FromDIP(3))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(method_sizer, 0, wx.TOP | wx.BOTTOM,
            border=self._FromDIP(5))
        top_sizer.Add(highlight_diff_sizer, 0, wx.TOP | wx.BOTTOM,
            border=self._FromDIP(5))
        top_sizer.Add(self.listPanel, 1, wx.EXPAND)
        top_sizer.Add(button_sizer, 0, wx.BOTTOM, border=self._FromDIP(5))

        return top_sizer

    def _initSettings(self):
        method = self.raw_settings.get('similarityTest')
        correction = self.raw_settings.get('similarityCorrection')
        threshold = self.raw_settings.get('similarityThreshold')

        wx.FindWindowById(self.ids['method'], self).SetStringSelection(method)
        wx.FindWindowById(self.ids['correction'], self).SetStringSelection(correction)
        wx.FindWindowById(self.ids['hl_diff_val'], self).ChangeValue(str(threshold))
        wx.FindWindowById(self.ids['hl_same_val'], self).ChangeValue(str(threshold))

        self._runSimilarityTest()

    def _runSimilarityTest(self):
        method_window = wx.FindWindowById(self.ids['method'])
        method = method_window.GetStringSelection()

        if method == 'CorMap':
            self._calcCorMapPval()

    def _onMethodChange(self, evt):
        self._runSimilarityTest()

    def _onTextEntry(self, evt):
        ctrl = evt.GetEventObject()
        pval = ctrl.GetValue()
        if pval != '' and pval !='-' and pval !='.' and not pval.isdigit():
            try:
                pval = float(pval.replace(',', '.'))
            except ValueError:
                pval = ''
                ctrl.ChangeValue(pval)
            if pval != '':
                self._highlight()
        elif pval.isdigit():
            self._highlight()

    def _onHighlightChange(self, evt):
        self._highlight()

    def _highlight(self):
        hl_diff = wx.FindWindowById(self.ids['hl_diff_chk']).GetValue()
        hl_diff_pval = wx.FindWindowById(self.ids['hl_diff_val']).GetValue()
        hl_same = wx.FindWindowById(self.ids['hl_same_chk']).GetValue()
        hl_same_pval = wx.FindWindowById(self.ids['hl_same_val']).GetValue()
        correction = wx.FindWindowById(self.ids['correction']).GetStringSelection()

        def_color = RAWGlobals.list_item_bkg_color

        if (hl_diff and hl_diff_pval != '') or (hl_same and hl_same_pval != ''):
            if hl_diff_pval != '':
                try:
                    hl_diff_pval = float(hl_diff_pval)
                except ValueError:
                    hl_diff_pval =''
            if hl_same_pval != '':
                try:
                    hl_same_pval = float(hl_same_pval)
                except ValueError:
                    hl_diff_pval =''

            for index in range(self.listPanel.GetItemCount()):
                if correction == 'None':
                    pval = float(self.listPanel.GetItemText(index,5))
                else:
                    pval = float(self.listPanel.GetItemText(index,6))

                if (hl_diff and hl_diff_pval != '') and (hl_same and hl_same_pval != ''):
                    if pval < hl_diff_pval and pval <= hl_same_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, wx.Colour(255,128,96))
                    elif pval >= hl_diff_pval and pval > hl_same_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, 'LIGHT BLUE')
                    elif pval < hl_diff_pval and pval > hl_same_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, wx.Colour(248,124,255))
                    elif pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                    else:
                        self.listPanel.SetItemBackgroundColour(index, def_color)

                elif hl_diff and hl_diff_pval != '':
                    if pval < hl_diff_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, wx.Colour(255,128,96))
                    elif pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                    else:
                        self.listPanel.SetItemBackgroundColour(index, def_color)

                elif hl_same and hl_same_pval != '':
                    if pval > hl_same_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, 'LIGHT BLUE')
                    elif pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                    else:
                        self.listPanel.SetItemBackgroundColour(index, def_color)
        else:
            for index in range(self.listPanel.GetItemCount()):
                pval = float(self.listPanel.GetItemText(index,5))
                if pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                else:
                    self.listPanel.SetItemBackgroundColour(index, def_color)

    def _calcCorMapPval(self):
        correction_window = wx.FindWindowById(self.ids['correction'])
        correction = correction_window.GetStringSelection()

        self.item_data, self.pvals, self.corrected_pvals, failed_comparisons = SASProc.run_cormap_all(self.sasm_list, correction)

        self.listPanel.DeleteAllItems()
        for item in self.item_data:
            self.listPanel.addItem(*item, correction=correction)

        self._highlight()

        if failed_comparisons:
            self._showComparisonError(failed_comparisons)

    def _onDoneButton(self, evt):
        self._onClose()

    def _onInfoButton(self, evt):
        msg = ('If you use CorMap in your work, in addition to citing the '
            'RAW paper please cite this paper:\n'
            'https://www.nature.com/nmeth/journal/v12/n5/abs/nmeth.3358.html')
        wx.MessageBox(str(msg), "How to cite Similarity Testing", style = wx.ICON_INFORMATION | wx.OK)

    def _onSaveButton(self, evt):
        self._save()

    def _showComparisonError(self, failed_comparisons):
        msg = 'The following comparisons failed due to differences in q vector:\n'
        for each_pair in failed_comparisons:
            msg=msg+'%s to %s\n' %(each_pair[0], each_pair[1])
        wx.MessageBox(str(msg), "Similarity Testing Error", style = wx.ICON_INFORMATION | wx.OK)

    def _save(self):
        """Saves the data shown in the list as a csv file.
        """
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        path = str(dirctrl.getDirLabel())

        filename = 'similarity_test.csv'

        dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = path, defaultFile = filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name + '.csv'
            dialog.Destroy()
        else:
            dialog.Destroy()
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving similarity data', 0)

        correction_window = wx.FindWindowById(self.ids['correction'])
        correction = correction_window.GetStringSelection()

        save_data = copy.copy(self.item_data)
        if correction == 'None':
            for item in save_data:
                item[-1]=''

        header = ('File# 1,File# 2,Filename 1,Filename 2,Longest Edge (C),Prob. '
            'Same (Pr(>C-1)),Corrected Prob. Same')

        SASFileIO.saveCSVFile(save_path, save_data, header)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)

    def _onClose(self):
        self.OnClose(1)

    def OnClose(self, event):
        self.Destroy()

class similiarityListPanel(wx.Panel, wx.lib.mixins.listctrl.ColumnSorterMixin,
    wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin):
    """Makes a sortable list panel for the similarity data. Right now,
    only has columns for the CorMap test.
    This is based on:
    https://www.blog.pythonlibrary.org/2011/01/04/wxpython-wx-listctrl-tips-and-tricks/
    """
    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT,
            size=self._FromDIP(size))

        self.list_ctrl.InsertColumn(0, 'File# 1')
        self.list_ctrl.InsertColumn(1, 'File# 2')
        self.list_ctrl.InsertColumn(2, 'Filename 1')
        self.list_ctrl.InsertColumn(3, 'Filename 2')
        self.list_ctrl.InsertColumn(4, 'Longest Edge (C)')
        self.list_ctrl.InsertColumn(5, 'Prob. Same (Pr(>C-1))')
        self.list_ctrl.InsertColumn(6, 'Corrected Prob. Same')

        self.itemDataMap = {}
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, 7)
        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, border=self._FromDIP(5))
        self.SetSizer(sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def GetListCtrl(self):
        """Used by the ColumnSorterMixin
        """
        return self.list_ctrl

    def GetColumnCount(self):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetColumnCount()

    def GetColumnWidth(self, col):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetColumnWidth(col)

    def GetItemCount(self):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetItemCount()

    def GetCountPerPage(self):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetCountPerPage()

    def SetColumnWidth(self, col, width):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.SetColumnWidth(col, width)

    def DeleteAllItems(self):
        """Makes this call accessible to the main panel
        """
        self.list_ctrl.DeleteAllItems()

    def GetItem(self, index):
        """Makes this call accessible to the main panel1_results
        """
        return self.list_ctrl.GetItem(index)

    def GetItemText(self, index, col):
        """Makes this call accessible to the main panel1_results
        """
        return self.list_ctrl.GetItemText(index, col)

    def SetItemBackgroundColour(self, index, color):
        self.list_ctrl.SetItemBackgroundColour(index, color)

    def addItem(self, fnum1, fnum2, fname1, fname2, c, pval, cor_pval, correction= 'None'):
        if correction == 'None':
            cor_pval = ''
        items = self.list_ctrl.GetItemCount()
        self.list_ctrl.Append((fnum1, fnum2, fname1, fname2, c, pval, cor_pval))
        self.itemDataMap[items] = (fnum1, fnum2, fname1, fname2, c, pval, cor_pval)

        self.list_ctrl.SetItemData(items, items)


class NormKratkyFrame(wx.Frame):

    def __init__(self, parent, title, sasm_list):

        client_display = wx.GetClientDisplayRect()
        size = (min(800, client_display.Width), min(600, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.main_frame = parent

        self.sasm_list = sasm_list

        self.panel = wx.Panel(self, wx.ID_ANY)

        splitter1 = wx.SplitterWindow(self.panel, wx.ID_ANY)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(splitter1, 1, flag=wx.EXPAND)
        self.panel.SetSizer(sizer)

        self.plotPanel = NormKratkyPlotPanel(splitter1, wx.ID_ANY)
        self.controlPanel = NormKratkyControlPanel(splitter1, wx.ID_ANY, sasm_list)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(290))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(self._FromDIP(290))    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(self._FromDIP(50))

        splitter1.Layout()

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.CenterOnParent()
        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()

    def OnClose(self):

        self.Destroy()



class NormKratkyPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        color = SASUtils.update_mpl_style()

        self.fig = Figure((5,4), 75)

        self.line_dict = {}

        self.DataTuple = collections.namedtuple('PlotItem', ['sasm', 'rg', 'i0', 'vc', 'line', 'label'])

        self.plot_labels = {'Normalized'            : ('Normalized Kratky', 'q', 'q^2*I(q)/I(0)'),
                            'Dimensionless (Rg)'    : ('Dimensionless Kratky (Rg)', 'qRg', '(qRg)^2*I(q)/I(0)'),
                            'Dimensionless (Vc)'    : ('Dimensionless Kratky (Vc)', 'q(Vc)^(1/2)', '(q)^2*Vc*I(q)/I(0)'),
                            }

        self.plot_type = 'Dimensionless (Rg)'

        self.subplot = self.fig.add_subplot(1,1,1,
            title=self.plot_labels[self.plot_type][0],
            label=self.plot_labels[self.plot_type][0])
        self.subplot.set_xlabel(self.plot_labels[self.plot_type][1])
        self.subplot.set_ylabel(self.plot_labels[self.plot_type][2])
        self.hline = self.subplot.axhline(0, color=color, linewidth=1.0)

        self.v_line = None
        self.h_line = None

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93,
            top = 0.93, hspace = 0.26)
        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

    def updateColors(self):
        color = SASUtils.update_mpl_style()

        # self.hline.set_color(color)

        self.ax_redraw()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def addSASMToPlot(self, sasm):

        analysis_dict = sasm.getParameter('analysis')

        rg = float(analysis_dict['guinier']['Rg'])
        i0 = float(analysis_dict['guinier']['I0'])
        vc = float(analysis_dict['molecularWeight']['VolumeOfCorrelation']['Vcor'])
        name = sasm.getParameter('filename')

        qmin, qmax = sasm.getQrange()
        q = sasm.q[qmin:qmax]
        i = sasm.i[qmin:qmax]

        if self.plot_type == 'Normalized':
            xdata = q
            ydata = q**2*i/i0
        elif self.plot_type == 'Dimensionless (Rg)':
            xdata = q*rg
            ydata = (q*rg)**2*i/i0

            if len(self.line_dict) == 0:
                self.v_line = self.subplot.axvline(np.sqrt(3), 0, 1,
                    linestyle='dashed', color='0.6')
                self.h_line = self.subplot.axhline(3./np.e, 0, 1,
                    linestyle = 'dashed', color='0.6')

        elif self.plot_type == 'Dimensionless (Vc)':
            xdata = q*np.sqrt(vc)
            ydata = (q)**2*vc*i/i0

        data_line, = self.subplot.plot(xdata, ydata, animated=True, label=name)

        self.line_dict[data_line] = self.DataTuple(sasm, rg, i0, vc, data_line, name)

        if len(self.line_dict) == 1:
            self.canvas.mpl_disconnect(self.cid)
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

        self.autoscale_plot()

        return data_line

    def autoscale_plot(self):
        redraw = False

        plot_list = [self.subplot]

        for plot in plot_list:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim(True)
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

            if newx != oldx or newy != oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()

    def redrawLines(self):

        if len(self.line_dict) > 0:
            self.canvas.restore_region(self.background)

        for line in self.line_dict:
            self.subplot.draw_artist(line)

            legend = self.subplot.get_legend()
            if legend is not None:
                if legend.get_visible():
                    self.subplot.draw_artist(legend)

        if len(self.line_dict) > 0:
            self.canvas.blit(self.subplot.bbox)

    def updatePlot(self, plot_type):
        self.plot_type = plot_type

        self.subplot.set_title(self.plot_labels[self.plot_type][0])
        self.subplot.set_xlabel(self.plot_labels[self.plot_type][1])
        self.subplot.set_ylabel(self.plot_labels[self.plot_type][2])

        if self.plot_type == 'Normalized' and self.v_line is not None:
            self.v_line.remove()
            self.h_line.remove()
            self.v_line = None
            self.h_line = None
        elif self.plot_type == 'Dimensionless (Rg)' and self.v_line is None:
            self.v_line = self.subplot.axvline(np.sqrt(3), 0, 1, linestyle = 'dashed', color='0.6')
            self.h_line = self.subplot.axhline(3./np.e, 0, 1, linestyle = 'dashed', color='0.6')
        elif self.plot_type == 'Dimensionless (Vc)' and self.v_line is not None:
            self.v_line.remove()
            self.h_line.remove()
            self.v_line = None
            self.h_line = None

        for line, data in self.line_dict.items():
            sasm = data.sasm
            qmin, qmax = sasm.getQrange()
            q = sasm.q[qmin:qmax]
            i = sasm.i[qmin:qmax]

            rg = data.rg
            i0 = data.i0
            vc = data.vc

            if self.plot_type == 'Normalized':
                xdata = q
                ydata = q**2*i/i0
            elif self.plot_type == 'Dimensionless (Rg)':
                xdata = q*rg
                ydata = (q*rg)**2*i/i0
            elif self.plot_type == 'Dimensionless (Vc)':
                xdata = q*np.sqrt(vc)
                ydata = (q)**2*vc*i/i0

            line.set_xdata(xdata)
            line.set_ydata(ydata)

        self.autoscale_plot()

    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''
        if event.button == 3:
            if float(matplotlib.__version__[:3]) >= 1.2:
                if self.toolbar.GetToolState(self.toolbar.wx_ids['Pan']) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu)
                    else:
                        self._showPopupMenu()

            else:
                if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu)
                    else:
                        self._showPopupMenu()

    def _showPopupMenu(self):
        menu = wx.Menu()

        menu.AppendCheckItem(1, 'Legend')
        menu.Append(2, 'Export Data As CSV')

        legend = self.subplot.get_legend()

        if legend is not None and legend.get_visible():
            menu.Check(1, True)

        self.PopupMenu(menu)

        menu.Destroy()

    def _onPopupMenuChoice(self, evt):
        my_id = evt.GetId()

        if my_id == 1:
            legend = self.subplot.get_legend()

            if evt.IsChecked():
                self._updateLegend()
            else:
                if legend is not None:
                    legend.set_visible(False)

        elif my_id == 2:
            self._exportData(self)

        self.redrawLines()

    def _updateLegend(self):
        leg_lines = []
        leg_labels = []
        self.subplot.legend_ = None
        for line in self.line_dict:
            if line.get_visible():
                leg_lines.append(line)
                leg_labels.append(line.get_label())

        self.subplot.legend(leg_lines, leg_labels)
        self.subplot.get_legend().set_animated(True)

    def _exportData(self, evt):
        title, xlabel, ylabel = self.plot_labels[self.plot_type]
        data_list = []
        header = ''

        for line, data in self.line_dict.items():
            if line.get_visible():
                xdata = line.get_xdata()
                ydata = line.get_ydata()

                qmin, qmax = data.sasm.getQrange()
                errdata = ydata*(data.sasm.err[qmin:qmax]/data.sasm.i[qmin:qmax])

                data_list.append(xdata)
                data_list.append(ydata)
                data_list.append(errdata)

                data_xlabel = data.label+'_'+xlabel
                data_ylabel = data.label+'_'+ylabel
                data_errlabel = data.label+'_'+ylabel+'_err'

                header = header + '%s,%s,%s,' %(data_xlabel, data_ylabel, data_errlabel)

        header.rstrip(',')

        if len(data_list) == 0:
            msg = 'Must have data shown on the plot to export it.'
            wx.CallAfter(wx.MessageBox, str(msg), "No Data Shown", style = wx.ICON_ERROR | wx.OK)
        else:
            dirctrl = wx.FindWindowByName('DirCtrlPanel')
            path = str(dirctrl.getDirLabel())

            filename = title.replace(' ', '_') + '.csv'

            dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = path, defaultFile = filename)

            if dialog.ShowModal() == wx.ID_OK:
                save_path = dialog.GetPath()
                name, ext = os.path.splitext(save_path)
                save_path = name + '.csv'
                dialog.Destroy()
            else:
                dialog.Destroy()
                return

            RAWGlobals.save_in_progress = True
            self.main_frame.setStatus('Saving Kratky data', 0)

            SASFileIO.saveUnevenCSVFile(save_path, data_list, header)

            RAWGlobals.save_in_progress = False
            self.main_frame.setStatus('', 0)


class NormKratkyControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, sasm_list):

        wx.Panel.__init__(self, parent, panel_id,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.parent = parent

        self.norm_kratky_frame = parent.GetParent().GetParent()

        self.sasm_list = sasm_list

        self.control_ids = {'plot'  : self.NewControlId(),
                            }

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        sizer = self._createLayout()

        self.SetSizer(sizer)

        self._initialize()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def onCloseButton(self, evt):
        self.norm_kratky_frame.OnClose()

    def _createLayout(self):

        close_button = wx.Button(self, wx.ID_OK, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(close_button, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER,
            border=self._FromDIP(5))


        ctrl_box = wx.StaticBox(self, -1, 'Control')
        control_sizer = wx.StaticBoxSizer(ctrl_box, wx.VERTICAL)

        plt_text = wx.StaticText(ctrl_box, -1, 'Plot:')
        plt_ctrl = wx.Choice(ctrl_box, self.control_ids['plot'], choices=['Normalized', 'Dimensionless (Rg)', 'Dimensionless (Vc)'])
        plt_ctrl.SetStringSelection('Dimensionless (Rg)')
        plt_ctrl.Bind(wx.EVT_CHOICE, self._onPlotChoice)

        plt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        plt_sizer.Add(plt_text, 0, wx.LEFT | wx.RIGHT, border=self._FromDIP(5))
        plt_sizer.Add(plt_ctrl, 0, wx.RIGHT, border=self._FromDIP(5))

        self.list = normKratkyListPanel(ctrl_box)


        control_sizer.Add(plt_sizer, 0)
        control_sizer.Add(self.list, 1, wx.EXPAND | wx.TOP, border=self._FromDIP(5))


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(control_sizer,0, wx.TOP | wx.EXPAND, border=self._FromDIP(5))
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(button_sizer,0, wx.BOTTOM|wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))

        return top_sizer

    def _initialize(self):
        plotpanel = self.norm_kratky_frame.plotPanel

        for sasm in self.sasm_list:
            analysis_dict = sasm.getParameter('analysis')
            i0 = float(analysis_dict['guinier']['I0'])

            qmin, qmax = sasm.getQrange()
            q = sasm.q[qmin:qmax]
            i = sasm.i[qmin:qmax]

            vc = SASCalc.volumeOfCorrelation(q, i, i0)
            if 'molecularWeight' in analysis_dict:
                analysis_dict['molecularWeight']['VolumeOfCorrelation']['Vcor'] = str(vc)
            else:
                analysis_dict['molecularWeight'] = {'VolumeOfCorrelation' :{'Vcor' :vc}}

            line = plotpanel.addSASMToPlot(sasm)

            self.list.addItem(sasm, line)


    def _onPlotChoice(self, evt):
        self.updatePlot()


    def updatePlot(self):
        plotWindow = wx.FindWindowById(self.control_ids['plot'], self)
        plot_type = plotWindow.GetStringSelection()

        plotpanel = self.norm_kratky_frame.plotPanel

        plotpanel.updatePlot(plot_type)


class normKratkyListPanel(wx.Panel, wx.lib.mixins.listctrl.ColumnSorterMixin,
    wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin):
    """Makes a sortable list panel for the normalized kratky data.
    This is based on:
    https://www.blog.pythonlibrary.org/2011/01/04/wxpython-wx-listctrl-tips-and-tricks/
    https://www.blog.pythonlibrary.org/2011/11/02/wxpython-an-intro-to-the-ultimatelistctrl/
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.list_ctrl = ULC.UltimateListCtrl(self, agwStyle=ULC.ULC_REPORT
            | ULC.ULC_SORT_ASCENDING|ULC.ULC_NO_HIGHLIGHT,
            size=self._FromDIP((-1,450)))

        self.norm_kratky_frame = parent.GetParent().norm_kratky_frame

        self.list_ctrl.InsertColumn(0, 'Show')
        self.list_ctrl.InsertColumn(1, 'Filename')
        self.list_ctrl.InsertColumn(2, 'Color')
        self.list_ctrl.InsertColumn(3, 'Rg')
        self.list_ctrl.InsertColumn(4, 'I(0)')
        self.list_ctrl.InsertColumn(5, 'Vc')

        self.list_ctrl.Bind(ULC.EVT_LIST_ITEM_CHECKED, self._onItemChecked)

        self.itemDataMap = {}
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, 6)
        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, border=self._FromDIP(5))
        self.SetSizer(sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def GetListCtrl(self):
        """Used by the ColumnSorterMixin
        """
        return self.list_ctrl

    def GetColumnCount(self):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetColumnCount()

    def GetColumnWidth(self, col):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetColumnWidth(col)

    def GetItemCount(self):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetItemCount()

    def GetCountPerPage(self):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.GetCountPerPage()

    def SetColumnWidth(self, col, width):
        """Used by the AutoWidthMixin
        """
        return self.list_ctrl.SetColumnWidth(col, width)

    def DeleteAllItems(self):
        """Makes this call accessible to the main panel
        """
        self.list_ctrl.DeleteAllItems()

    def GetItem(self, index):
        """Makes this call accessible to the main panel
        """
        return self.list_ctrl.GetItem(index)

    def GetItemText(self, index, col):
        """Makes this call accessible to the main panel
        """
        return self.list_ctrl.GetItemText(index, col)

    def SetItemBackgroundColour(self, index, color):
        self.list_ctrl.SetItemBackgroundColour(index, color)

    def addItem(self, sasm, line):
        analysis_dict = sasm.getParameter('analysis')
        rg = float(analysis_dict['guinier']['Rg'])
        i0 = float(analysis_dict['guinier']['I0'])
        vc = float(analysis_dict['molecularWeight']['VolumeOfCorrelation']['Vcor'])
        name = sasm.getParameter('filename')

        conv = mplcol.ColorConverter()
        color = conv.to_rgb(line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        try:
            index = self.list_ctrl.InsertStringItem(sys.maxsize, '', it_kind=1)
        except Exception:
            index = self.list_ctrl.InsertStringItem(sys.maxint, '', it_kind=1)
        self.list_ctrl.SetStringItem(index, 1, name)
        self.list_ctrl.SetStringItem(index, 2, '')
        self.list_ctrl.SetStringItem(index, 3, str(rg))
        self.list_ctrl.SetStringItem(index, 4, str(i0))
        self.list_ctrl.SetStringItem(index, 5, str(vc))

        self.itemDataMap[index] = ('', name, '', rg, i0, vc)

        self.list_ctrl.SetItemData(index, index)

        item = self.list_ctrl.GetItem(index, 0)
        item.Check(True)
        self.list_ctrl.SetItem(item)

        colour_indicator = RAWCustomCtrl.ColourIndicator(self.list_ctrl, index,
            color, size = self._FromDIP((30,15)))
        colour_indicator.Bind(wx.EVT_LEFT_DOWN, self._onColorButton)

        item = self.list_ctrl.GetItem(index, 2)
        item.SetWindow(colour_indicator)
        item.SetAlign(ULC.ULC_FORMAT_LEFT)
        self.list_ctrl.SetItem(item)

        item = self.list_ctrl.GetItem(index, 0)
        item.SetAlign(ULC.ULC_FORMAT_CENTER)
        self.list_ctrl.SetItem(item)

        item = self.list_ctrl.GetItem(index)
        itemData = [sasm, line]
        item.SetPyData(itemData)
        self.list_ctrl.SetItem(item)

        self.list_ctrl.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.list_ctrl.SetColumnWidth(1, self._FromDIP(130))
        self.list_ctrl.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

    def _onItemChecked(self, evt):
        item = evt.GetItem()

        itemData = item.GetPyData()
        line = itemData[1]

        state = item.IsChecked()
        line.set_visible(state)

        plotpanel = self.norm_kratky_frame.plotPanel

        legend =plotpanel.subplot.get_legend()
        if legend is not None and legend.get_visible():
            plotpanel._updateLegend()
        plotpanel.redrawLines()

    def _onColorButton(self, evt):
        index = evt.GetId()
        item = self.list_ctrl.GetItem(index)
        itemData = item.GetPyData()
        line = itemData[1]

        plotpanel = self.norm_kratky_frame.plotPanel

        dlg = RAWCustomDialogs.ColourChangeDialog(self, None, 'NormKratky',
            line, plotpanel)
        dlg.ShowModal()
        dlg.Destroy()

        conv = mplcol.ColorConverter()
        color = line.get_color()
        color = conv.to_rgb(color)
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        item = self.list_ctrl.GetItem(index, 2)
        color_control = item.GetWindow()
        color_control.updateColour(color)
        self.list_ctrl.SetItem(item)

        legend =plotpanel.subplot.get_legend()
        if legend is not None and legend.get_visible():
            plotpanel._updateLegend()
            plotpanel.redrawLines()


class LCSeriesFrame(wx.Frame):

    def __init__(self, parent, title, secm, manip_item, raw_settings):

        client_display = wx.GetClientDisplayRect()
        size = (min(1000, client_display.Width), min(900, client_display.Height))

        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        self.SetSize(self._FromDIP(size))

        panel = wx.Panel(self)

        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE|wx.SP_3D)

        sizer = wx.BoxSizer()
        sizer.Add(splitter, 1, flag=wx.EXPAND)

        panel.SetSizer(sizer)

        secm.acquireSemaphore()

        self.original_secm = secm
        self.manip_item = manip_item
        self._raw_settings = raw_settings

        self.plotPanel = LCSeriesPlotPage(splitter, self.original_secm.getSASM().getQ())
        self.controlPanel = LCSeriesControlPanel(splitter, self.original_secm)


        splitter.SplitVertically(self.controlPanel, self.plotPanel, self._FromDIP(325))

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter.SetMinimumPaneSizeself._FromDIP((290))    #Back compatability with older wxpython versions
        else:
            splitter.SetMinimumPaneSize(self._FromDIP(50))

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.Bind(wx.EVT_CLOSE, self.OnCloseEvt)

        self.CenterOnParent()
        self.Raise()

        self.showBusy(msg='Initializing...')
        t = threading.Thread(target=self.initialize)
        t.daemon = True
        t.start()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.plotPanel.updateColors()
        self.controlPanel.updateColors()

    def initialize(self):
        self.secm = copy.deepcopy(self.original_secm)
        self.original_secm.releaseSemaphore()

        wx.CallAfter(self.plotPanel.initialize, self.secm)
        wx.CallAfter(self.controlPanel.initialize, self.secm)

        wx.CallAfter(self.showBusy, False)

    def showBusy(self, show=True, msg=''):
        if show:
            self.bi = wx.BusyInfo(msg, self)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass

    def OnCloseEvt(self, evt):
        self.OnClose()

    def OnClose(self):
        self.showBusy(show=False)

        for t in self.controlPanel.threads:
            if t.is_alive():
                t.join()

        self.Destroy()


class SeriesPlotPanel(wx.Panel):

    def __init__(self, parent, plot_type, ctrl_type='LC'):

        wx.Panel.__init__(self, parent)

        self.ctrl_type = ctrl_type

        if self.ctrl_type == 'LC':
            self.series_frame = parent.GetParent().series_frame
        elif self.ctrl_type == 'REGALS':
            self.series_frame = parent.GetParent()

        self.all_plot_types = {'unsub'  : {'left': 'Total Intensity', 'right' : '',
                        'title': 'Unsubtracted Series', 'bottom': 'Frame #'},
            'sub'       : {'left': 'Total Intensity', 'right': 'Rg',
                        'title': 'Subtracted Series', 'bottom': 'Frame #'},
            'baseline'  : {'left': 'Total Intensity', 'right': 'Rg',
                        'title': 'Baseline Corrected Series', 'bottom': 'Frame #'},
            'uv'        : {'left': 'Total Intensity', 'right': 'UV',
                        'title': 'SAXS and UV', 'bottom': 'Frame #'},
            }

        self.plot_type = plot_type

        self.plot_lines = {}
        self.r_plot_lines = {}
        self.plot_ranges = {}

        self.range_pick = False

        self.subplot = None
        self.ryaxis = None

        self.create_layout()

        if self.ctrl_type == 'REGALS':
            self.fig.tight_layout()

        # Connect the callback for the draw_event so that window resizing works:
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        self.canvas.mpl_connect('motion_notify_event', self._onMouseMotionEvent)
        self.canvas.mpl_connect('button_press_event', self._onMousePressEvent)

    def updateColors(self):
        color = SASUtils.update_mpl_style()

        # if self.plot_type != 'unsub':
        #     self.axhline.set_color(color)

        self.ax_redraw()

    def create_layout(self):
        color = SASUtils.update_mpl_style()

        self.fig = Figure((5,4), 75)

        self.subplot = self.fig.add_subplot(1,1,1,
            title=self.all_plot_types[self.plot_type]['title'])
        self.subplot.set_xlabel(self.all_plot_types[self.plot_type]['bottom'])
        self.subplot.set_ylabel(self.all_plot_types[self.plot_type]['left'])

        if self.plot_type != 'unsub':
            self.ryaxis = self.subplot.twinx()
            self.ryaxis.set_ylabel(self.all_plot_types[self.plot_type]['right'])
            self.axhline = self.subplot.axhline(0, color=color, linewidth=1.0)

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93,
            top = 0.93, hspace = 0.26)

        # self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # self.canvas.SetBackgroundColour('white')

        self.toolbar = RAWCustomCtrl.CustomPlotToolbar(self, self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.EXPAND)

        self.SetSizer(sizer)

    def plot_data(self, xdata, ydata, label, axis):
        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)

        if axis == 'left':
            try:
                line = self.plot_lines[label]
            except Exception:
                line = None
        else:
            try:
                line = self.r_plot_lines[label]
            except Exception:
                line = None

        if line is None:
            if axis == 'left':

                if isinstance(label, str) and label.startswith('base'):
                    color = '#ff7f0e'
                else:
                    color = '#1f77b4'
                line, = self.subplot.plot(xdata, ydata, animated=True,
                    color=color)
                self.canvas.draw()
                self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
                self.plot_lines[label] = line
            else:
                if self.plot_type != 'uv':
                    line, = self.ryaxis.plot(xdata, ydata, animated=True,
                        linestyle='', marker='o', color='#d62728')
                else:
                    line, = self.ryaxis.plot(xdata, ydata, animated=True,
                        linestyle='-', color='#d62728')
                self.canvas.draw()
                self.r_background = self.canvas.copy_from_bbox(self.ryaxis.bbox)
                self.r_plot_lines[label] = line
        else:
            line.set_xdata(xdata)
            line.set_ydata(ydata)

        self.updatePlot()

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plot_range(self, start, end, index, color=None):

        if index in self.plot_ranges:
            line = self.plot_ranges[index]
        else:
            line = None

        if line is None:
            self.canvas.mpl_disconnect(self.cid)
            if color is None:
                if isinstance(index, str) and index.startswith('bl'):
                    color = '#17becf'
                else:
                    color = '#2ca02c'

            if start<end:
                line = self.subplot.axvspan(start, end, animated=True, facecolor=color,
                    alpha=0.5)
            else:
                line = self.subplot.axvspan(start-0.5, end+0.5, animated=True, facecolor=color,
                    alpha=0.5)
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
            self.plot_ranges[index] = line
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        else:
            if start<end:
                pts = line.get_xy()
                pts[:,0] = [start, start, end, end, start]
                line.set_xy(pts)
            else:
                pts = line.get_xy()
                pts[:,0] = [start-0.5, start-0.5, end+0.5, end+0.5, start-0.5]
                line.set_xy(pts)

        self.redrawLines()

    def plot_label(self, label, axis):
        if axis == 'left':
            self.subplot.set_ylabel(label)
        else:
            self.ryaxis.set_ylabel(label)

        self.ax_redraw()

    def remove_range(self, index):
        if index in self.plot_ranges:
            line = self.plot_ranges[index]
            line.remove()

            del self.plot_ranges[index]

            self.redrawLines()

    def remove_data(self, index):
        if index in self.plot_lines:
            line = self.plot_lines[index]
            line.remove()

            del self.plot_lines[index]

            self.redrawLines()

        elif index in self.r_plot_lines:
            line = self.r_plot_lines[index]
            line.remove()

            del self.r_plot_lines[index]

            self.redrawLines()

    def pick_range(self, start, end, index):
        self.start_range = -1
        self.end_range = -1
        self.range_pick = True
        self.range_index = index

        low_x, high_x = self.subplot.get_xlim()

        if isinstance(index, str) and index.startswith('bl'):
            color = '#17becf'
        else:
            color = '#2ca02c'

        self.canvas.mpl_disconnect(self.cid)
        self.range_line = self.subplot.axvline(low_x, color=color, alpha=0.5, animated=True)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

        self.plot_ranges[index].set_visible(False)
        self.range_line.set_visible(False)

        self.redrawLines()

        self.range_line.set_visible(True)

    def show_range(self, index, show):
        line = self.plot_ranges[index]
        line.set_visible(show)

        self.redrawLines()

    def _onMouseMotionEvent(self, event):

        if event.inaxes:
            x, y = event.xdata, event.ydata
            xlabel = self.subplot.xaxis.get_label().get_text()
            ylabel = self.subplot.yaxis.get_label().get_text()
            if self.ryaxis is not None:
                y2label = self.ryaxis.yaxis.get_label().get_text()

            if self.ryaxis is not None:
                if event.inaxes == self.ryaxis:
                    trans1 = self.ryaxis.transData
                    trans2 = self.subplot.transData.inverted()
                    x2, y2 = x, y
                    x, y = trans2.transform(trans1.transform((x,y)))
                else:
                    trans1 = self.subplot.transData
                    trans2 = self.ryaxis.transData.inverted()
                    x2, y2 = trans2.transform(trans1.transform((x,y)))

            if abs(y) > 0.001 and abs(y) < 1000:
                y_val = '{:.3f}'.format(round(y, 3))
            else:
                y_val = '{:.3E}'.format(y)

            if self.ryaxis is not None:
                if abs(y2) > 0.001 and abs(y2) < 1000:
                    y2_val = '{:.3f}'.format(round(y2, 3))
                else:
                    y2_val = '{:.3E}'.format(y2)

            if 'Frame' in xlabel:
                x_val = int(x)
            else:
                x_val = x

            if self.ryaxis is not None:
                self.toolbar.set_status('{} = {}, {} = {}, {} = {}'.format(xlabel,
                    x_val, ylabel, y_val, y2label, y2_val))
            else:
                self.toolbar.set_status('{} = {}, {} = {}'.format(xlabel, x_val, ylabel, y_val))

            if self.range_pick:
                if self.start_range == -1:
                    x = int(round(x))
                    self.range_line.set_xdata([x, x])
                else:
                    x = int(round(x))
                    pts = self.plot_ranges[self.range_index].get_xy()
                    pts[:,0] = [self.start_range, self.start_range, x, x, self.start_range]
                    self.plot_ranges[self.range_index].set_xy(pts)

                self.redrawLines()
        else:
            self.toolbar.set_status('')

    def _onMousePressEvent(self, event):
        if self.range_pick and event.inaxes and event.button == 1:
            x = event.xdata

            if self.start_range == -1:
                self.start_range = int(round(x))
                pts = self.plot_ranges[self.range_index].get_xy()
                pts[:,0] = [self.start_range, self.start_range, self.start_range+1,
                    self.start_range+1, self.start_range]
                self.plot_ranges[self.range_index].set_xy(pts)

                self.range_line.set_visible(False)
                self.plot_ranges[self.range_index].set_visible(True)

            else:
                self.end_range = int(round(x))
                pts = self.plot_ranges[self.range_index].get_xy()
                pts[:,0] = [self.start_range, self.start_range, self.end_range,
                    self.end_range, self.start_range]
                self.plot_ranges[self.range_index].set_xy(pts)

                self.range_pick = False
                self.range_line.remove()
                del self.range_line

                if self.ctrl_type == 'LC':
                    control_page = self.series_frame.controlPanel
                elif self.ctrl_type == 'REGALS':
                    control_page = self.series_frame

                control_page.setPickRange(self.range_index, [self.start_range, self.end_range],
                    self.plot_type)

            self.redrawLines()

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''
        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
        self.redrawLines()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def autoscale_plot(self):
        self.subplot.set_autoscale_on(True)

        oldx = self.subplot.get_xlim()
        oldy = self.subplot.get_ylim()

        self.subplot.relim()
        self.subplot.autoscale_view()

        newx = self.subplot.get_xlim()
        newy = self.subplot.get_ylim()

        if newx != oldx or newy != oldy:
            redraw = True
        else:
            redraw = False

        if self.ryaxis is not None:
            self.ryaxis.set_autoscale_on(True)

            r_oldx = self.ryaxis.get_xlim()
            r_oldy = self.ryaxis.get_ylim()

            self.ryaxis.relim()
            self.ryaxis.autoscale_view()

            r_newx = self.ryaxis.get_xlim()
            r_newy = self.ryaxis.get_ylim()

            if r_newx != r_oldx or r_newy != r_oldy:
                redraw = True

        if redraw:
            self.ax_redraw()
        else:
            self.redrawLines()

    def redrawLines(self):
        self.canvas.restore_region(self.background)

        for line in self.plot_lines.values():
            self.subplot.draw_artist(line)

        for line in self.plot_ranges.values():
            self.subplot.draw_artist(line)

        if self.range_pick:
            self.subplot.draw_artist(self.range_line)

        if self.ryaxis is not None:
            for line in self.r_plot_lines.values():
                self.ryaxis.draw_artist(line)

        self.canvas.blit(self.subplot.bbox)

    def updatePlot(self):
        self.autoscale_plot()


class LCSeriesPlotPage(wx.Panel):

    def __init__(self, parent, secm_q_list):

        wx.Panel.__init__(self, parent, wx.ID_ANY,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER)

        self.series_frame = parent.GetParent().GetParent()

        self.intensity = 'total'
        self.calc = 'Rg'

        self.create_layout(secm_q_list)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.unsub_panel.updateColors()
        self.sub_panel.updateColors()
        self.baseline_panel.updateColors()

    def create_layout(self, secm_q_list):

        control_box = wx.StaticBox(self, -1, 'Plot Controls')

        self.intensity_type = wx.Choice(control_box, choices=['Total Intensity',
            'Mean Intensity', 'Intensity at specific q', 'Intensity in q range'])
        self.intensity_type.Bind(wx.EVT_CHOICE, self._on_intensity_change)

        self.calc_type = wx.Choice(control_box, choices=['Rg', 'MW (Vc)', 'MW (Vp)',
            'I0'])
        self.calc_type.Bind(wx.EVT_CHOICE, self._on_calc_change)

        self.q_val = RAWCustomCtrl.FloatSpinCtrlList(control_box, TextLength=60,
            value_list=secm_q_list)
        self.q_val.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_qval_change)

        self.q_range_start = RAWCustomCtrl.FloatSpinCtrlList(control_box, TextLength=60,
            value_list=secm_q_list,
            max_idx=len(secm_q_list)-2)
        self.q_range_end = RAWCustomCtrl.FloatSpinCtrlList(control_box, TextLength=60,
            value_list=secm_q_list, initIndex=-1, min_idx=1)
        self.q_range_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_qrange_change)
        self.q_range_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_qrange_change)

        self.qval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.qval_sizer.Add(wx.StaticText(control_box, label='q ='),
            flag=wx.ALIGN_CENTER_VERTICAL)
        self.qval_sizer.Add(self.q_val, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT)

        self.qrange_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.qrange_sizer.Add(wx.StaticText(control_box, label='q ='),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.qrange_sizer.Add(self.q_range_start, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.qrange_sizer.Add(wx.StaticText(control_box, label='to'), border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.qrange_sizer.Add(self.q_range_end, border=self._FromDIP(2),
            flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)

        self.q_point_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.q_point_sizer.Add(self.qval_sizer)
        self.q_point_sizer.Add(self.qrange_sizer, flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
        self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        controls = wx.FlexGridSizer(cols=3, rows=2, vgap=2, hgap=2)
        controls.Add(wx.StaticText(control_box, label='Intensity:'))
        controls.Add(self.intensity_type)
        controls.Add(self.q_point_sizer)
        controls.Add(wx.StaticText(control_box, label='Calculated value:'))
        controls.Add(self.calc_type)


        control_sizer = wx.StaticBoxSizer(control_box, wx.HORIZONTAL)
        control_sizer.Add(controls, border=self._FromDIP(2), flag=wx.BOTTOM
            |wx.LEFT|wx.TOP)
        control_sizer.AddStretchSpacer(1)

        self.notebook = wx.Notebook(self)

        self.unsub_panel = SeriesPlotPanel(self.notebook, 'unsub')
        self.sub_panel = SeriesPlotPanel(self.notebook, 'sub')
        self.baseline_panel = SeriesPlotPanel(self.notebook, 'baseline')
        # self.uv_panel = SeriesPlotPanel(self.notebook, 'uv')

        self.notebook.AddPage(self.unsub_panel, 'Unsubtracted')
        self.notebook.AddPage(self.sub_panel, 'Subtracted')
        self.notebook.AddPage(self.baseline_panel, 'Baseline Corrected')
        # self.notebook.AddPage(self.uv_panel, 'UV')

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(control_sizer, flag=wx.EXPAND)
        top_sizer.Add(self.notebook, 1, flag=wx.EXPAND|wx.TOP,
            border=self._FromDIP(5))
        self.SetSizer(top_sizer)

    def initialize(self, secm):

        self.secm = secm

        if self.secm.qref != 0:
            self.q_val.SetValue(self.secm.qref)

        if self.secm.qrange[0] !=0 and self.secm.qrange[1] !=0:
            self.q_range_start.SetValue(self.secm.qrange[0])
            self.q_range_end.SetValue(self.secm.qrange[1])

        sec_plot_panel = wx.FindWindowByName('SECPlotPanel')
        data_type = sec_plot_panel.plotparams['y_axis_display']
        calc_type = sec_plot_panel.plotparams['secm_plot_calc']

        if data_type == 'total':
            self.intensity = 'total'
            self.intensity_type.SetStringSelection('Total Intensity')
            label = 'Total Intensity'
            self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        elif data_type == 'mean':
            self.intensity = 'mean'
            self.intensity_type.SetStringSelection('Mean Intensity')
            label = 'Mean Intensity'
            self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        elif data_type == 'q_val':
            self.intensity = 'q_val'
            self.intensity_type.SetStringSelection('Intensity at specific q')

            qref = float(self.q_val.GetValue())
            label = 'Intensity at q={:.5f}'.format(qref)

            self.q_point_sizer.Show(self.qval_sizer, show=True, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        elif data_type == 'q_range':
            self.intensity = 'q_range'
            self.intensity_type.SetStringSelection('Intensity in q range')

            q1 = float(self.q_range_start.GetValue())
            q2 = float(self.q_range_end.GetValue())
            label = 'Intensity from q={:.5f} to {:.5f}'.format(q1, q2)

            self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=True, recursive=True)

        self.Layout()

        self.update_plot_label(label, 'left', 'unsub')
        self.update_plot_label(label, 'left', 'sub')
        self.update_plot_label(label, 'left', 'baseline')
        # self.update_plot_label(label, 'left', 'uv')

        if calc_type == 'RG':
            self.calc = 'Rg'
        elif calc_type == 'MW (Vc)':
            self.calc = 'MW (Vc)'
        elif calc_type == 'MW (Vp)':
            self.calc = 'MW (Vp)'
        elif calc_type == 'I0':
            self.calc = 'I0'

        self.calc_type.SetStringSelection(self.calc)

        self.update_plot_label(self.calc, 'right', 'sub')
        self.update_plot_label(self.calc, 'right', 'baseline')


    def update_plot_data(self, xdata, ydata, label, axis, plot):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.plot_data(xdata, ydata, label, axis)
        elif plot == 'sub':
            self.sub_panel.plot_data(xdata, ydata, label, axis)
        elif plot == 'baseline':
            self.baseline_panel.plot_data(xdata, ydata, label, axis)
        elif plot == 'uv':
            self.uv_panel.plot_data(xdata, ydata, label, axis)

    def update_plot_range(self, start, end, index, plot):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.plot_range(start, end, index)
        elif plot == 'sub':
            self.sub_panel.plot_range(start, end, index)
        elif plot == 'baseline':
            self.baseline_panel.plot_range(start, end, index)
        elif plot == 'uv':
            self.uv_panel.plot_range(start, end, index)

    def update_plot_label(self, label, axis, plot):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.plot_label(label, axis)
        elif plot == 'sub':
            self.sub_panel.plot_label(label, axis)
        elif plot == 'baseline':
            self.baseline_panel.plot_label(label, axis)
        elif plot == 'uv':
            self.uv_panel.plot_label(label, axis)

    def remove_plot_range(self, index, plot):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.remove_range(index)
        elif plot == 'sub':
            self.sub_panel.remove_range(index)
        elif plot == 'baseline':
            self.baseline_panel.remove_range(index)
        elif plot == 'uv':
            self.uv_panel.remove_range(index)

    def remove_plot_data(self, index, plot):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.remove_data(index)
        elif plot == 'sub':
            self.sub_panel.remove_data(index)
        elif plot == 'baseline':
            self.baseline_panel.remove_data(index)
        elif plot == 'uv':
            self.uv_panel.remove_data(index)

    def pick_plot_range(self, start_item, end_item, index, plot):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.pick_range(start_item, end_item, index)
        elif plot == 'sub':
            self.sub_panel.pick_range(start_item, end_item, index)
        elif plot == 'baseline':
            self.baseline_panel.pick_range(start_item, end_item, index)
        elif plot == 'uv':
            self.uv_panel.pick_range(start_item, end_item, index)

    def show_plot_range(self, index, plot, show):
        if plot == 'gen_sub':
            control_page = self.series_frame.controlPanel
            if control_page.processing_done['baseline']:
                plot = 'baseline'
            else:
                plot = 'sub'

        if plot == 'unsub':
            self.unsub_panel.show_range(index, show)
        elif plot == 'sub':
            self.sub_panel.show_range(index, show)
        elif plot == 'baseline':
            self.baseline_panel.show_range(index, show)
        elif plot == 'uv':
            self.uv_panel.show_range(index, show)

    def show_plot(self, plot):
        for i in range(self.notebook.GetPageCount()):
            if self.notebook.GetPageText(i) == plot:
                self.notebook.ChangeSelection(i)
                break

    def get_plot(self):
        return self.notebook.GetPageText(self.notebook.GetSelection())

    def _on_intensity_change(self, event):
        int_type = event.GetString()

        if int_type == 'Total Intensity':
            self.intensity = 'total'
            label = int_type
            self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        elif int_type == 'Mean Intensity':
            self.intensity = 'mean'
            label = int_type
            self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        elif int_type == 'Intensity at specific q':
            self.intensity = 'q_val'

            qref = float(self.q_val.GetValue())
            label = 'Intensity at q={:.5f}'.format(qref)

            self.q_point_sizer.Show(self.qval_sizer, show=True, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=False, recursive=True)

        elif int_type == 'Intensity in q range':
            self.intensity = 'q_range'

            q1 = float(self.q_range_start.GetValue())
            q2 = float(self.q_range_end.GetValue())
            label = 'Intensity from q={:.5f} to {:.5f}'.format(q1, q2)

            self.q_point_sizer.Show(self.qval_sizer, show=False, recursive=True)
            self.q_point_sizer.Show(self.qrange_sizer, show=True, recursive=True)

        self.Layout()

        self.update_plot_label(label, 'left', 'unsub')
        self.update_plot_label(label, 'left', 'sub')
        self.update_plot_label(label, 'left', 'baseline')
        # self.update_plot_label(label, 'left', 'uv')

        control_page = self.series_frame.controlPanel

        frames = self.secm.getFrames()

        intensity = control_page._getIntensity('unsub')
        self.update_plot_data(frames, intensity, 'intensity', 'left', 'unsub')

        if control_page.processing_done['buffer']:
            control_page.plotSubtracted()

        if control_page.processing_done['baseline']:
            control_page.plotBaseline()

        control_page.secm.intensity_change = True

    def _on_calc_change(self, event):
        calc_type = event.GetString()

        self.calc = calc_type

        control_page = self.series_frame.controlPanel

        frames = self.secm.getFrames()

        self.update_plot_label(self.calc, 'right', 'sub')
        self.update_plot_label(self.calc, 'right', 'baseline')

        if control_page.processing_done['buffer'] and not control_page.processing_done['baseline']:

            if self.calc == 'Rg':
                data = control_page.results['calc']['rg']
            elif self.calc == 'MW (Vc)':
                data = control_page.results['calc']['vcmw']
            elif self.calc == 'MW (Vp)':
                data = control_page.results['calc']['vpmw']
            elif self.calc == 'I0':
                data = control_page.results['calc']['i0']

            frames = frames[data>0]
            data = data[data>0]

            self.update_plot_data(frames, data, 'calc', 'right', 'sub')

        elif control_page.processing_done['baseline']:

            if self.calc == 'Rg':
                data = control_page.results['calc']['rg']
            elif self.calc == 'MW (Vc)':
                data = control_page.results['calc']['vcmw']
            elif self.calc == 'MW (Vp)':
                data = control_page.results['calc']['vpmw']
            elif self.calc == 'I0':
                data = control_page.results['calc']['i0']

            frames = frames[data>0]
            data = data[data>0]

            self.update_plot_data(frames, data, 'calc', 'right', 'baseline')

            if 'calc' in control_page.results['buffer']:
                if self.calc == 'Rg':
                    sub_data = control_page.results['buffer']['calc']['rg']
                elif self.calc == 'MW (Vc)':
                    sub_data = control_page.results['buffer']['calc']['vcmw']
                elif self.calc == 'MW (Vp)':
                    sub_data = control_page.results['buffer']['calc']['vpmw']
                elif self.calc == 'I0':
                    sub_data = control_page.results['buffer']['calc']['i0']

                sub_frames = self.secm.getFrames()
                sub_frames = sub_frames[sub_data>0]
                sub_data = sub_data[sub_data>0]

                self.update_plot_data(sub_frames, sub_data, 'calc', 'right', 'sub')

    def _on_qval_change(self, event):
        control_page = self.series_frame.controlPanel

        frames = self.secm.getFrames()

        try:
            qref = float(self.q_val.GetValue())
        except ValueError:
            return

        intensity = np.array([sasm.getIofQ(qref) for sasm in self.secm.getAllSASMs()])
        self.update_plot_data(frames, intensity, 'intensity', 'left', 'unsub')

        label = 'Intensity at q={:.5f}'.format(qref)

        self.update_plot_label(label, 'left', 'unsub')
        self.update_plot_label(label, 'left', 'sub')
        self.update_plot_label(label, 'left', 'baseline')
        # self.update_plot_label(label, 'left', 'uv')

        if control_page.processing_done['buffer']:
            control_page.plotSubtracted()

        if control_page.processing_done['baseline']:
            control_page.plotBaseline()

        control_page.secm.intensity_change = True

        return

    def _on_qrange_change(self, event):
        control_page = self.series_frame.controlPanel

        frames = self.secm.getFrames()

        try:
            q1 = float(self.q_range_start.GetValue())
            q2 = float(self.q_range_end.GetValue())
        except ValueError:
            return

        label = 'Intensity from q={:.5f} to {:.5f}'.format(q1, q2)

        self.update_plot_label(label, 'left', 'unsub')
        self.update_plot_label(label, 'left', 'sub')
        self.update_plot_label(label, 'left', 'baseline')
        # self.update_plot_label(label, 'left', 'uv')

        _, end = self.q_range_end.GetRange()
        self.q_range_start.SetRange((0, self.q_range_end.GetIndex()-1))
        self.q_range_end.SetRange((self.q_range_start.GetIndex()+1, end))

        intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in self.secm.getAllSASMs()])
        self.update_plot_data(frames, intensity, 'intensity', 'left', 'unsub')

        if control_page.processing_done['buffer']:
            control_page.plotSubtracted()

        if control_page.processing_done['baseline']:
            control_page.plotBaseline()

        control_page.secm.intensity_change = True

        return

class LCSeriesControlPanel(wx.ScrolledWindow):

    def __init__(self, parent, original_secm):

        wx.ScrolledWindow.__init__(self, parent,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER|wx.VSCROLL)
        self.SetScrollRate(20,20)

        self.original_secm = original_secm

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        self.series_frame = parent.GetParent().GetParent()
        self.plot_page = self.series_frame.plotPanel

        self.question_thread_wait_event = threading.Event()
        self.question_return_queue = queue.Queue()

        self.proc_lock = threading.Lock()
        self.threads = []

        self._createLayout()

        self.processing_order = ['buffer', 'baseline', 'uv', 'calc']

        self.process = {'buffer': self.processBuffer,
            'baseline'  : self.processBaseline,
            'uv'        : self.processUV,
            'calc'      : self.processCalcs,
            }

        self.processing_done = {'buffer':   False,
            'baseline'  : False,
            'uv'        : False,
            'calc'      : False,
            'sample'    : False,
            }

        self.should_process = {'buffer':   True,
            'baseline'  : False,
            'uv'        : False,
            'calc'      : True,
            }

        self.continue_processing = True

        self.results = {}

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def updateColors(self):
        self.buffer_range_list.updateColors()
        self.sample_range_list.updateColors()

    def _createLayout(self):

        frames = self.original_secm.getFrames()

        close_button = wx.Button(self, wx.ID_OK, 'OK')
        close_button.Bind(wx.EVT_BUTTON, self.onOkButton)

        cancel_button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        cancel_button.Bind(wx.EVT_BUTTON, self.onCancelButton)

        cite_button = wx.Button(self, label='How to Cite')
        cite_button.Bind(wx.EVT_BUTTON, self.onCiteButton)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(cancel_button, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER,
            border=self._FromDIP(5))
        button_sizer.Add(close_button, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER,
            border=self._FromDIP(5))
        button_sizer.Add(cite_button, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER,
            border=self._FromDIP(5))

        control_box = wx.StaticBox(self, -1, 'Control')
        control_sizer = wx.StaticBoxSizer(control_box, wx.VERTICAL)

        name_label = wx.StaticText(control_box, label="Series:")
        self.series_name = wx.StaticText(control_box)

        series_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        series_name_sizer.Add(name_label, border=self._FromDIP(2),
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        series_name_sizer.Add(self.series_name, border=self._FromDIP(2),
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)


        info_pane = wx.CollapsiblePane(control_box, label="Series Info",
            style=wx.CP_NO_TLW_RESIZE)
        info_pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        info_win = info_pane.GetPane()

        self.series_type = wx.Choice(info_win, choices=['SEC-SAXS'])
        self.series_type.SetStringSelection('SEC-SAXS')
        self.series_type.Bind(wx.EVT_CHOICE, self.onUpdateProc)

        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_sizer.Add(wx.StaticText(info_win, label='Series type:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        type_sizer.Add(self.series_type, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(2))
        type_sizer.AddStretchSpacer(1)

        vp_density = self.raw_settings.get('MWVpRho')
        self.vc_mol_type = wx.Choice(info_win, choices=['Protein', 'RNA'])
        self.vc_mol_type.SetStringSelection('Protein')
        self.vc_mol_type.Bind(wx.EVT_CHOICE, self.onUpdateProc)

        self.vp_density = wx.TextCtrl(info_win, value=str(vp_density),
            size=self._FromDIP((60,-1)), style=wx.TE_PROCESS_ENTER)
        self.avg_window = wx.TextCtrl(info_win, value='5',
            size=self._FromDIP((60,-1)), style=wx.TE_PROCESS_ENTER)
        self.vp_density.Bind(wx.EVT_TEXT_ENTER, self.onUpdateProc)
        self.avg_window.Bind(wx.EVT_TEXT_ENTER, self.onUpdateProc)

        settings_sizer = wx.FlexGridSizer(rows=3, cols=2, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))
        settings_sizer.Add(wx.StaticText(info_win, label='Vc Mol. type:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        settings_sizer.Add(self.vc_mol_type, flag=wx.ALIGN_CENTER_VERTICAL)
        settings_sizer.Add(wx.StaticText(info_win, label='Vp density (kDa/A^3):'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        settings_sizer.Add(self.vp_density, flag=wx.ALIGN_CENTER_VERTICAL)
        settings_sizer.Add(wx.StaticText(info_win, label='Averaging window size:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        settings_sizer.Add(self.avg_window, flag=wx.ALIGN_CENTER_VERTICAL)

        info_sizer = wx.BoxSizer(wx.VERTICAL)
        info_sizer.Add(type_sizer, border=self._FromDIP(2), flag=wx.LEFT
            |wx.RIGHT|wx.TOP|wx.EXPAND)
        info_sizer.Add(settings_sizer, border=self._FromDIP(5), flag=wx.ALL)
        info_win.SetSizer(info_sizer)

        info_pane.Expand()


        buffer_pane = wx.CollapsiblePane(control_box, label="Buffer",
            style=wx.CP_NO_TLW_RESIZE)
        buffer_pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        buffer_win = buffer_pane.GetPane()

        self.subtracted = wx.CheckBox(buffer_win,
            label='Series is already subtracted')
        self.subtracted.SetValue(False)
        self.subtracted.Bind(wx.EVT_CHECKBOX, self._onSubtracted)

        self.buffer_range_list = SeriesRangeItemList(self, 'buffer', buffer_win)
        self.buffer_range_list.SetMinSize(self._FromDIP((-1,115)))

        self.buffer_auto_btn = wx.Button(buffer_win, label='Auto')
        self.buffer_auto_btn.Bind(wx.EVT_BUTTON, self._onBufferAuto)

        self.buffer_add_btn = wx.Button(buffer_win, label='Add region')
        self.buffer_add_btn.Bind(wx.EVT_BUTTON, self._onSeriesAdd)

        self.buffer_remove_btn = wx.Button(buffer_win, label='Remove region')
        self.buffer_remove_btn.Bind(wx.EVT_BUTTON, self._onSeriesRemove)

        self.buffer_calc = wx.Button(buffer_win, label='Set buffer')
        self.buffer_calc.Bind(wx.EVT_BUTTON, self.onUpdateProc)

        buffer_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        buffer_button_sizer.Add(self.buffer_auto_btn)
        buffer_button_sizer.Add(self.buffer_add_btn, flag=wx.LEFT,
            border=self._FromDIP(2))
        buffer_button_sizer.Add(self.buffer_remove_btn, flag=wx.LEFT,
            border=self._FromDIP(2))

        buffer_sizer = wx.BoxSizer(wx.VERTICAL)
        buffer_sizer.Add(self.subtracted, flag=wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(2))
        buffer_sizer.Add(self.buffer_range_list, flag=wx.LEFT|wx.RIGHT|wx.TOP
            |wx.EXPAND, border=self._FromDIP(2))
        buffer_sizer.Add(buffer_button_sizer, flag=wx.LEFT|wx.RIGHT|wx.TOP
            |wx.ALIGN_CENTER, border=self._FromDIP(2))
        buffer_sizer.Add(self.buffer_calc, flag=wx.ALL, border=self._FromDIP(5))
        buffer_win.SetSizer(buffer_sizer)

        buffer_pane.Expand()


        baseline_pane = wx.CollapsiblePane(control_box, label="Baseline Correction",
            style=wx.CP_NO_TLW_RESIZE)
        baseline_pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        baseline_win = baseline_pane.GetPane()

        self.baseline_cor = wx.Choice(baseline_win,
            choices=['None', 'Linear', 'Integral'])
        self.baseline_cor.SetStringSelection('None')
        self.baseline_cor.Bind(wx.EVT_CHOICE, self.onBaselineChange)

        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_sizer.Add(wx.StaticText(baseline_win, label='Baseline correction:'),
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(2))
        type_sizer.Add(self.baseline_cor, border=self._FromDIP(2),
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        type_sizer.AddStretchSpacer(1)

        r1_0 = frames[0]
        r2_0 = frames[0]

        if len(frames) < 22:
            r1_1 = frames[len(frames)//2]
            r2_1 = frames[min(len(frames)//2+1, len(frames)-1)]
        else:
            r1_1 = frames[10]
            r2_1 = frames[-11]

        self.bl_r1_start = RAWCustomCtrl.IntSpinCtrl(baseline_win,
            wx.ID_ANY, min_val=r1_0, max_val=r1_1, size=self._FromDIP((60,-1)))
        self.bl_r1_end = RAWCustomCtrl.IntSpinCtrl(baseline_win,
            wx.ID_ANY, min_val=r1_0, max_val=frames[-1], size=self._FromDIP((60,-1)))
        self.bl_r1_start.SetValue(r1_0)
        self.bl_r1_end.SetValue(r1_1)
        self.bl_r1_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)
        self.bl_r1_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)

        self.bl_r2_start = RAWCustomCtrl.IntSpinCtrl(baseline_win,
            wx.ID_ANY, min_val=r2_0, max_val=frames[-1], size=self._FromDIP((60,-1)))
        self.bl_r2_end = RAWCustomCtrl.IntSpinCtrl(baseline_win,
            wx.ID_ANY, min_val=r2_1, max_val=frames[-1], size=self._FromDIP((60,-1)))
        self.bl_r2_start.SetValue(r2_1)
        self.bl_r2_end.SetValue(frames[-1])
        self.bl_r2_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)
        self.bl_r2_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)

        self.bl_r1_pick = wx.Button(baseline_win, label='Pick')
        self.bl_r2_pick = wx.Button(baseline_win, label='Pick')
        self.bl_r1_pick.Bind(wx.EVT_BUTTON, self.onBaselinePick)
        self.bl_r2_pick.Bind(wx.EVT_BUTTON, self.onBaselinePick)

        baseline_ctrl_sizer = wx.FlexGridSizer(rows=2, cols=5, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_win, label='Start:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r1_start, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_win, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r1_end, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r1_pick, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_win, label='End:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r2_start, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_win, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r2_end, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r2_pick, flag=wx.ALIGN_CENTER_VERTICAL)

        self.baseline_auto = wx.Button(baseline_win, label='Auto')
        self.baseline_auto.Bind(wx.EVT_BUTTON, self._onBaselineAuto)

        self.baseline_extrap = wx.CheckBox(baseline_win,
            label='Extrapolate to all frames')
        self.baseline_extrap.SetValue(True)

        self.baseline_options_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.baseline_options_sizer.Add(self.baseline_extrap, flag=wx.RIGHT,
            border=self._FromDIP(2))
        self.baseline_options_sizer.Add(self.baseline_auto,
            flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN)

        self.baseline_calc = wx.Button(baseline_win,
            label='Set baseline and calculate')
        self.baseline_calc.Bind(wx.EVT_BUTTON, self.onUpdateProc)

        baseline_sizer = wx.BoxSizer(wx.VERTICAL)
        baseline_sizer.Add(type_sizer, border=self._FromDIP(2), flag=wx.EXPAND
            |wx.ALL)
        baseline_sizer.Add(baseline_ctrl_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(2))
        baseline_sizer.Add(self.baseline_options_sizer,
            flag=wx.LEFT|wx.RIGHT|wx.BOTTOM, border=self._FromDIP(2))
        baseline_sizer.Add(self.baseline_calc, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        baseline_win.SetSizer(baseline_sizer)


        # uv_pane = wx.CollapsiblePane(self, label="UV",
            # style=wx.CP_NO_TLW_RESIZE)
        # uv_pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        # uv_win = uv_pane.GetPane()

        # uv_sizer = wx.BoxSizer(wx.VERTICAL)
        # uv_win.SetSizer(uv_sizer)


        sample_pane = wx.CollapsiblePane(control_box, label="Sample",
            style=wx.CP_NO_TLW_RESIZE)
        sample_pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCollapse)
        sample_win = sample_pane.GetPane()

        self.sample_range_list = SeriesRangeItemList(self, 'sample', sample_win)
        self.sample_range_list.SetMinSize(self._FromDIP((-1,85)))

        self.sample_auto_btn = wx.Button(sample_win, label='Auto')
        self.sample_auto_btn.Bind(wx.EVT_BUTTON, self._onSampleAuto)

        self.sample_add_btn = wx.Button(sample_win, label='Add region')
        self.sample_add_btn.Bind(wx.EVT_BUTTON, self._onSeriesAdd)

        self.sample_remove_btn = wx.Button(sample_win, label='Remove region')
        self.sample_remove_btn.Bind(wx.EVT_BUTTON, self._onSeriesRemove)

        to_mainplot = wx.Button(sample_win, label='To Profiles Plot')
        to_mainplot.Bind(wx.EVT_BUTTON, self._onToMainPlot)

        sample_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sample_button_sizer.Add(self.sample_auto_btn)
        sample_button_sizer.Add(self.sample_add_btn, flag=wx.LEFT,
            border=self._FromDIP(2))
        sample_button_sizer.Add(self.sample_remove_btn, flag=wx.LEFT,
            border=self._FromDIP(2))

        sample_sizer = wx.BoxSizer(wx.VERTICAL)
        sample_sizer.Add(self.sample_range_list, flag=wx.LEFT|wx.RIGHT|wx.TOP
            |wx.EXPAND, border=self._FromDIP(2))
        sample_sizer.Add(sample_button_sizer, flag=wx.LEFT|wx.RIGHT|wx.TOP
            |wx.ALIGN_CENTER_HORIZONTAL, border=self._FromDIP(2))
        sample_sizer.Add(to_mainplot, flag=wx.ALL, border=self._FromDIP(5))
        sample_win.SetSizer(sample_sizer)

        sample_pane.Expand()


        control_sizer.Add(series_name_sizer, flag=wx.ALL, border=self._FromDIP(2))
        control_sizer.Add(info_pane, flag=wx.ALL|wx.EXPAND,
            border=self._FromDIP(2))
        control_sizer.Add(buffer_pane, flag=wx.EXPAND|wx.ALL,
            border=self._FromDIP(2))
        control_sizer.Add(baseline_pane, flag=wx.ALL|wx.EXPAND,
            border=self._FromDIP(2))
        # control_sizer.Add(uv_pane, flag=wx.TOP, border=self._FromDIP(5))
        control_sizer.Add(sample_pane, flag=wx.EXPAND|wx.ALL,
            border=self._FromDIP(2))
        control_sizer.AddStretchSpacer(1)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(control_sizer, 1, flag=wx.ALL|wx.EXPAND,
            border=self._FromDIP(2))
        top_sizer.Add(button_sizer, 0, flag=wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))

        self.SetSizer(top_sizer)

    def initialize(self, secm):
        self.secm = secm

        self.series_name.SetLabel(self.secm.getParameter('filename'))

        if self.secm.series_type == 'SEC':
            self.series_type.SetStringSelection('SEC-SAXS')

        frames = self.secm.getFrames()

        if self.plot_page.intensity == 'total':
            intensity = self.secm.getIntI()
        elif self.plot_page.intensity == 'mean':
            intensity = self.secm.getMeanI()
        elif self.plot_page.intensity == 'q_val':
            intensity = self.secm.getIofQ()
        elif self.plot_page.intensity == 'q_range':
            intensity = self.secm.getIofQRange()

        self.plot_page.update_plot_data(frames, intensity, 'intensity', 'left', 'unsub')

        if self.secm.mol_type != '':
            self.vc_mol_type.SetStringSelection(self.secm.mol_type)

        if self.secm.window_size != -1:
            self.avg_window.ChangeValue(str(self.secm.window_size))

        if self.secm.mol_density != -1:
            self.vp_density.ChangeValue(str(self.secm.mol_density))

        if self.secm.already_subtracted:
            self.subtracted.SetValue(True)

        if self.secm.buffer_range:
            for region in self.secm.buffer_range:
                self._addAutoBufferRange(region[0], region[1])

        if self.secm.subtracted_sasm_list:
            sim_threshold = self.raw_settings.get('similarityThreshold')
            sim_test = self.raw_settings.get('similarityTest')
            correction = self.raw_settings.get('similarityCorrection')
            calc_threshold = self.raw_settings.get('secCalcThreshold')

            results = {'buffer_range': self.secm.buffer_range,
                'sub_sasms':            self.secm.subtracted_sasm_list,
                'use_sub_sasms':        self.secm.use_subtracted_sasm,
                'similarity_test':      sim_test,
                'similarity_corr':      correction,
                'similarity_thresh':    sim_threshold,
                'calc_thresh':          calc_threshold,
                'already_subtracted':   self.subtracted.IsChecked(),
                'sub_mean_i':           self.secm.mean_i_sub,
                'sub_total_i':          self.secm.total_i_sub,
                'buffer_sasm':          self.secm.average_buffer_sasm,
                }

            self.results['buffer'] = results
            self.processing_done['buffer'] = True
            self.plotSubtracted()


        if self.secm.baseline_subtracted_sasm_list:
            self.baseline_cor.SetStringSelection(self.secm.baseline_type)

            self.bl_r1_start.SetValue(self.secm.baseline_start_range[0])
            self.bl_r1_end.SetValue(self.secm.baseline_start_range[1])
            self.bl_r2_start.SetValue(self.secm.baseline_end_range[0])
            self.bl_r2_end.SetValue(self.secm.baseline_end_range[1])

            self.baseline_extrap.SetValue(self.secm.baseline_extrap)

            if self.secm.baseline_type != 'Integral':
                self.baseline_auto.Disable()
                self.baseline_options_sizer.Hide(self.baseline_auto)

            if self.secm.baseline_type != 'Linear':
                self.baseline_extrap.Disable()
                self.baseline_options_sizer.Hide(self.baseline_extrap)

            self.plot_page.update_plot_range(self.secm.baseline_start_range[0],
                self.secm.baseline_start_range[1], 'bl_start', 'sub')
            self.plot_page.update_plot_range(self.secm.baseline_end_range[0],
                self.secm.baseline_end_range[1], 'bl_end', 'sub')

            bl_sub_mean_i = np.array([sasm.getMeanI() for sasm in self.secm.baseline_corr])
            bl_sub_total_i = np.array([sasm.getTotalI() for sasm in self.secm.baseline_corr])

            results = {'baseline_start_range'   : self.secm.baseline_start_range,
                'baseline_end_range'            : self.secm.baseline_end_range,
                'sub_sasms'                     : self.secm.baseline_subtracted_sasm_list,
                'use_sub_sasms'                 : self.secm.use_baseline_subtracted_sasm,
                'baseline_corr'                 : self.secm.baseline_corr,
                'similarity_test'               : sim_test,
                'similarity_thresh'             : sim_threshold,
                'calc_thresh'                   : calc_threshold,
                'sub_mean_i'                    : self.secm.mean_i_bcsub,
                'sub_total_i'                   : self.secm.total_i_bcsub,
                'bl_sub_mean_i'                 : bl_sub_mean_i,
                'bl_sub_total_i'                : bl_sub_total_i,
                'baseline_extrap'               : self.secm.baseline_extrap,
                'fit_results'                   : self.secm.baseline_fit_results,
                'baseline_type'                 : self.secm.baseline_type,
                }

            self.results['baseline'] = results
            self.processing_done['baseline'] = True
            self.should_process['baseline'] = True

            self.plotBaseline()

        else:
            self.bl_r1_start.Disable()
            self.bl_r1_end.Disable()
            self.bl_r2_start.Disable()
            self.bl_r2_end.Disable()
            self.bl_r1_pick.Disable()
            self.bl_r2_pick.Disable()
            self.baseline_calc.Disable()
            self.baseline_auto.Disable()
            self.baseline_extrap.Disable()
            self.baseline_options_sizer.Hide(self.baseline_auto)
            self.baseline_options_sizer.Hide(self.baseline_extrap)


        array_test = (isinstance(self.secm.vpmw_list, np.ndarray)
            and (not np.all(self.secm.vpmw_list == -1)
            or np.all(self.secm.rg_list == -1))
            and self.secm.vpmw_list.size > 0)
        list_test = isinstance(self.secm.vpmw_list, list) and self.secm.vpmw_list

        if array_test or list_test:
            if self.secm.mol_type == 'Protein':
                is_protein = True
            else:
                is_protein = False

            results = {'rg':    self.secm.rg_list,
                'rger':         self.secm.rger_list,
                'i0':           self.secm.i0_list,
                'i0er':         self.secm.i0er_list,
                'vcmw':         self.secm.vcmw_list,
                'vcmwer':       self.secm.vcmwer_list,
                'vpmw':         self.secm.vpmw_list,
                'window_size':  self.secm.window_size,
                'is_protein':   is_protein,
                'vp_density':   self.secm.mol_density,
                }

            self.results['calc'] = results
            self.processing_done['calc'] = True
            self.plotCalc()

        else:
            if self.processing_done['buffer']:
                t = threading.Thread(target=self.updateProcessing, args=('calc',))
                t.daemon = True
                t.start()
                self.threads.append(t)


        if self.secm.sample_range:
            for region in self.secm.sample_range:
                self._addAutoSampleRange(region[0], region[1])


        if self.processing_done['baseline']:
            self.plot_page.show_plot('Baseline Corrected')
        elif self.processing_done['buffer']:
            self.plot_page.show_plot('Subtracted')

    def onOkButton(self, evt):
        series_control_panel = wx.FindWindowByName('SeriesControlPanel')
        restart_online = False

        if series_control_panel.seriesIsOnline:
            series_control_panel.seriesPanelGoOffline()
            restart_online = True

        t = threading.Thread(target=self.saveResults, args=(restart_online,))
        t.daemon = True
        t.start()
        self.threads.append(t)

    def saveResults(self, restart_online):
        self.proc_lock.acquire()

        self.original_secm.acquireSemaphore()

        if self.series_type.GetStringSelection() == 'SEC-SAXS':
            self.original_secm.series_type = 'SEC'

        if self.processing_done['buffer']:
            buffer_sasm = self.results['buffer']['buffer_sasm']
            buffer_range = self.results['buffer']['buffer_range']
            already_subtracted = self.results['buffer']['already_subtracted']

            self.original_secm.buffer_range = buffer_range
            self.original_secm.already_subtracted = already_subtracted
            self.original_secm.average_buffer_sasm = buffer_sasm

            if len(self.secm.getAllSASMs()) == len(self.original_secm.getAllSASMs()):
                sub_sasms = self.results['buffer']['sub_sasms']
                use_sub_sasms = self.results['buffer']['use_sub_sasms']

            else:
                calc_threshold = self.raw_settings.get('secCalcThreshold')
                qref = None
                qrange = None
                if self.plot_page.intensity == 'q_val':
                    qref = float(self.plot_page.q_val.GetValue())
                elif self.plot_page.intensity == 'q_range':
                    q1 = float(self.plot_page.q_range_start.GetValue())
                    q2 = float(self.plot_page.q_range_end.GetValue())

                    qrange = (q1, q2)

                new_sasms = self.original_secm.getAllSASMs()[len(self.secm.getAllSASMs()):]

                new_sub_sasms, new_use_sub_sasms = self.original_secm.subtractSASMs(buffer_sasm,
                    new_sasms, self.plot_page.intensity, calc_threshold, qref, qrange)

                sub_sasms = self.results['buffer']['sub_sasms'] + new_sub_sasms
                use_sub_sasms = self.results['buffer']['use_sub_sasms'] + new_use_sub_sasms

            self.original_secm.setSubtractedSASMs(sub_sasms, use_sub_sasms)


        if self.processing_done['baseline']:
            if len(self.secm.getAllSASMs()) == len(self.original_secm.getAllSASMs()):
                baseline_sub_sasms = self.results['baseline']['sub_sasms']
                baseline_use_sub_sasms = self.results['baseline']['use_sub_sasms']
                baselines = self.results['baseline']['baseline_corr']

            else:
                calc_threshold = self.raw_settings.get('secCalcThreshold')
                qref = None
                qrange = None
                if self.plot_page.intensity == 'q_val':
                    qref = float(self.plot_page.q_val.GetValue())
                elif self.plot_page.intensity == 'q_range':
                    q1 = float(self.plot_page.q_range_start.GetValue())
                    q2 = float(self.plot_page.q_range_end.GetValue())

                    qrange = (q1, q2)

                r1_start = self.results['baseline']['baseline_start_range'][0]
                r1_end = self.results['baseline']['baseline_start_range'][1]
                r2_start = self.results['baseline']['baseline_end_range'][0]
                r2_end = self.results['baseline']['baseline_end_range'][1]

                bl_type = self.results['baseline']['baseline_type']
                bl_extrap = self.results['baseline']['baseline_extrap']

                new_sasms = self.original_secm.subtracted_sasm_list[len(self.secm.getAllSASMs()):]

                bl_sasms = []

                baselines = self.results['baseline']['baseline_corr']
                fit_results = self.results['baseline']['fit_results']

                bl_q = copy.deepcopy(new_sasms[0].getQ())
                bl_err = np.zeros_like(new_sasms[0].getQ())

                for j, sasm in enumerate(new_sasms):
                    idx = j + len(self.secm.getAllSASMs())
                    q = copy.deepcopy(sasm.getQ())

                    if bl_type == 'Integral':
                        if idx < r1_start:
                            baseline = baselines[0].getI()
                            i = copy.deepcopy(sasm.getI())
                            err = copy.deepcopy(sasm.getErr())
                        elif idx >= r1_end and idx < r2_start:
                            baseline = baselines[idx-r1_end].getI()
                            i = sasm.getI() - baseline
                            err = sasm.getErr() * i/sasm.getI()
                        else:
                            baseline = baselines[-1].getI()
                            i = sasm.getI() - baseline
                            err = sasm.getErr() * i/sasm.getI()

                    elif bl_type == 'Linear':

                        if bl_extrap:
                            baseline = np.array([SASCalc.linear_func(idx, fit[0], fit[1]) for fit in fit_results])
                            i = sasm.getI() - baseline
                            err = sasm.getErr() * i/sasm.getI()

                            bl_newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                            baselines.append(bl_newSASM)

                        else:
                            if idx >= r1_start and idx <= r2_end:
                                baseline = np.array([SASCalc.linear_func(idx, fit[0], fit[1]) for fit in fit_results])
                                i = sasm.getI() - baseline
                                err = sasm.getErr() * i/sasm.getI()

                                bl_newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                                baselines.append(bl_newSASM)
                            else:
                                i = copy.deepcopy(sasm.getI())
                                err = copy.deepcopy(sasm.getErr())
                                baseline = np.zeros_like(i)


                    parameters = copy.deepcopy(sasm.getAllParameters())
                    newSASM = SASM.SASM(i, q, err, {}, copy.deepcopy(sasm.getQErr()))
                    newSASM.setParameter('filename', parameters['filename'])

                    history = newSASM.getParameter('history')

                    history = {}

                    history1 = []
                    history1.append(copy.deepcopy(sasm.getParameter('filename')))
                    for key in sasm.getParameter('history'):
                        history1.append({ key : copy.deepcopy(sasm.getParameter('history')[key])})

                    history['baseline_correction'] = {'initial_file':history1, 'type':bl_type}

                    newSASM.setParameter('history', history)

                    bl_sasms.append(newSASM)

                use_subtracted_sasms = []

                buffer_sub_sasms = self.results['buffer']['sub_sasms']
                start_sasms = [buffer_sub_sasms[k] for k in range(r1_start, r1_end+1)]

                start_avg_sasm = SASProc.average(start_sasms, forced=True)
                int_type = self.plot_page.intensity
                if  int_type == 'total':
                    ref_intensity = start_avg_sasm.getTotalI()
                elif int_type == 'mean':
                    ref_intensity = start_avg_sasm.getMeanI()
                elif int_type == 'q_val':
                    qref = float(self.plot_page.q_val.GetValue())
                    ref_intensity = start_avg_sasm.getIofQ(qref)
                elif int_type == 'q_range':
                    q1 = float(self.plot_page.q_range_start.GetValue())
                    q2 = float(self.plot_page.q_range_end.GetValue())
                    ref_intensity = start_avg_sasm.getIofQRange(q1, q2)

                for sasm in bl_sasms:
                    if int_type == 'total':
                        sasm_intensity = sasm.getTotalI()
                    elif int_type == 'mean':
                        sasm_intensity = sasm.getMeanI()
                    elif int_type == 'q_val':
                        sasm_intensity = sasm.getIofQ(qref)
                    elif int_type == 'q_range':
                        sasm_intensity = sasm.getIofQRange(q1, q2)

                    if abs(sasm_intensity/ref_intensity) > calc_threshold:
                        use_subtracted_sasms.append(True)
                    else:
                        use_subtracted_sasms.append(False)

                baseline_sub_sasms = self.results['baseline']['sub_sasms'] + bl_sasms
                baseline_use_sub_sasms = self.results['baseline']['use_sub_sasms'] + use_subtracted_sasms

            self.original_secm.setBCSubtractedSASMs(baseline_sub_sasms, baseline_use_sub_sasms)

            self.original_secm.baseline_start_range = self.results['baseline']['baseline_start_range']
            self.original_secm.baseline_end_range = self.results['baseline']['baseline_end_range']
            self.original_secm.baseline_corr = baselines
            self.original_secm.baseline_type = self.results['baseline']['baseline_type']
            self.original_secm.baseline_extrap = self.results['baseline']['baseline_extrap']
            self.original_secm.baseline_fit_results = self.results['baseline']['fit_results']

        else:
            self.original_secm.baseline_start_range = (-1, -1)
            self.original_secm.baseline_end_range = (-1, -1)
            self.original_secm.baseline_corr = []
            self.original_secm.baseline_type = ''
            self.original_secm.baseline_extrap = True
            self.original_secm.baseline_fit_results = []

            self.original_secm.baseline_subtracted_sasm_list = []
            self.original_secm.use_baseline_subtracted_sasm = []
            self.original_secm.mean_i_bcsub = np.zeros_like(self.original_secm.mean_i)
            self.original_secm.total_i_bcsub = np.zeros_like(self.original_secm.total_i)
            self.original_secm.I_of_q_bcsub = np.zeros_like(self.original_secm.I_of_q)
            self.original_secm.qrange_I_bcsub = np.zeros_like(self.original_secm.qrange_I)


        if self.processing_done['calc']:
            if self.results['calc']['is_protein']:
                mol_type = 'Protein'
            else:
                mol_type = 'RNA'

            self.original_secm.window_size = self.results['calc']['window_size']
            self.original_secm.mol_type = mol_type
            self.original_secm.mol_density = self.results['calc']['vp_density']

            if len(self.secm.getAllSASMs()) == len(self.original_secm.getAllSASMs()):
                rg = self.results['calc']['rg']
                rger = self.results['calc']['rger']
                i0 = self.results['calc']['i0']
                i0er = self.results['calc']['i0er']
                vcmw = self.results['calc']['vcmw']
                vcmwer = self.results['calc']['vcmwer']
                vpmw = self.results['calc']['vpmw']
            else:
                mol_type = self.vc_mol_type.GetStringSelection()

                if mol_type == 'Protein':
                    is_protein = True
                else:
                    is_protein = False

                error_weight = self.raw_settings.get('errorWeight')
                window_size = int(self.avg_window.GetValue())
                vp_density = float(self.vp_density.GetValue())
                vp_cutoff = self.raw_settings.get('MWVpCutoff')
                vp_qmax = self.raw_settings.get('MWVpQmax')
                vc_cutoff = self.raw_settings.get('MWVcCutoff')
                vc_qmax = self.raw_settings.get('MWVcQmax')
                vc_a_prot = self.raw_settings.get('MWVcAProtein')
                vc_b_prot = self.raw_settings.get('MWVcBProtein')
                vc_a_rna = self.raw_settings.get('MWVcARna')
                vc_b_rna = self.raw_settings.get('MWVcBRna')

                first_update_frame = int(self.original_secm.plot_frame_list[len(self.secm.getAllSASMs())])
                last_frame = int(self.original_secm.plot_frame_list[-1])

                first_frame = first_update_frame - window_size

                if first_frame <0:
                    first_frame = 0

                if self.processing_done['baseline']:
                    sub_sasms = self.original_secm.baseline_subtracted_sasm_list[first_frame:last_frame+1]
                    use_sub_sasms = self.original_secm.use_baseline_subtracted_sasm[first_frame:last_frame+1]
                else:
                    sub_sasms = self.original_secm.subtracted_sasm_list[first_frame:last_frame+1]
                    use_sub_sasms = self.original_secm.use_subtracted_sasm[first_frame:last_frame+1]

                success, results = SASCalc.run_secm_calcs(sub_sasms,
                    use_sub_sasms, window_size, is_protein, error_weight,
                    vp_density, vp_cutoff, vp_qmax, vc_cutoff, vc_qmax,
                    vc_a_prot, vc_b_prot, vc_a_rna, vc_b_rna)

                if success:
                    new_rg = results['rg']
                    new_rger = results['rger']
                    new_i0 = results['i0']
                    new_i0er = results['i0er']
                    new_vcmw = results['vcmw']
                    new_vcmwer = results['vcmwer']
                    new_vpmw = results['vpmw']

                    rg = self.results['calc']['rg']
                    rger = self.results['calc']['rger']
                    i0 = self.results['calc']['i0']
                    i0er = self.results['calc']['i0er']
                    vcmw = self.results['calc']['vcmw']
                    vcmwer = self.results['calc']['vcmwer']
                    vpmw = self.results['calc']['vpmw']

                    index1 = first_frame+(window_size-1)//2
                    index2 = (window_size-1)//2

                    rg = np.concatenate((rg[:index1], new_rg[index2:]))
                    rger = np.concatenate((rger[:index1], new_rger[index2:]))
                    i0 = np.concatenate((i0[:index1], new_i0[index2:]))
                    i0er = np.concatenate((i0er[:index1], new_i0er[index2:]))
                    vcmw = np.concatenate((vcmw[:index1], new_vcmw[index2:]))
                    vcmwer = np.concatenate((vcmwer[:index1], new_vcmwer[index2:]))
                    vpmw = np.concatenate((vpmw[:index1], new_vpmw[index2:]))

            if rg.size>0:
                self.original_secm.setCalcValues(rg, rger, i0, i0er, vcmw, vcmwer, vpmw)
                self.original_secm.calc_has_data = True

        if self.processing_done['sample']:
            self.original_secm.sample_range = self.results['sample']['sample_range']

        self.original_secm.intensity_change = False

        self.original_secm.releaseSemaphore()

        if restart_online:
            series_control_panel = wx.FindWindowByName('SeriesControlPanel')
            wx.CallAfter(series_control_panel.seriesPanelGoOnline)

        RAWGlobals.mainworker_cmd_queue.put(['update_secm_plot', self.original_secm])

        wx.CallAfter(self.series_frame.manip_item.updateInfoTip)
        wx.CallAfter(self.series_frame.manip_item.markAsModified)
        wx.CallAfter(self.series_frame.manip_item.updateInfoPanel)
        wx.CallAfter(self.series_frame.OnClose)

        self.proc_lock.release()

    def onCancelButton(self, evt):
        self.series_frame.OnClose()

    def onUpdateProc(self, event):
        event_object = event.GetEventObject()

        if event_object is self.buffer_calc:
            start = 'buffer'
            if self.baseline_cor.GetStringSelection() == 'None':
                self.should_process['baseline'] = False
        elif event_object is self.baseline_calc:
            start = 'baseline'
            if self.processing_done['buffer'] and self.baseline_cor.GetStringSelection() != 'None':
                self.should_process['baseline'] = True
            else:
                self.should_process['baseline'] = False
        elif (event_object is self.vc_mol_type or event_object is self.vp_density
            or event_object is self.avg_window):
            start = 'calc'
            if self.baseline_cor.GetStringSelection() == 'None':
                self.should_process['baseline'] = False

        t = threading.Thread(target=self.updateProcessing, args=(start,))
        t.daemon = True
        t.start()
        self.threads.append(t)

    def updateProcessing(self, start):
        self.proc_lock.acquire()

        self.continue_processing = True

        start_idx = self.processing_order.index(start)
        processing_steps = self.processing_order[start_idx:]

        for step in self.processing_order[:start_idx]:
            if self.should_process[step] and not self.processing_done[step]:
                self.continue_processing = False

        if self.continue_processing:
            wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

        for step in processing_steps:
            if not self.continue_processing:
                break

            elif self.should_process[step]:
                if step == 'calc':
                    self.process[step](start)
                else:
                    self.process[step]()

        wx.CallAfter(self.series_frame.showBusy, False)

        self.proc_lock.release()

    def updateSeriesRange(self, event):
        event_object = event.GetEventObject()
        event_item = event_object.GetParent()
        value = event_object.GetValue()

        start, end = event_item.get_range()
        index = event_item.GetId()

        if event_object is event_item.start_ctrl:
            current_range = event_item.end_ctrl.GetRange()
            event_item.end_ctrl.SetRange((value, current_range[-1]))
        else:
            current_range = event_item.start_ctrl.GetRange()
            event_item.start_ctrl.SetRange((current_range[0], value))

        if event_item.item_type == 'buffer':
            self.plot_page.update_plot_range(start, end, index, 'unsub')
        else:
            self.plot_page.update_plot_range(start, end, index, 'gen_sub')

    def onBaselineChange(self, event):
        baseline = self.baseline_cor.GetStringSelection()

        if baseline == 'None':
            self.bl_r1_start.Disable()
            self.bl_r1_end.Disable()
            self.bl_r2_start.Disable()
            self.bl_r2_end.Disable()
            self.bl_r1_pick.Disable()
            self.bl_r2_pick.Disable()
            self.baseline_calc.Disable()
            self.baseline_auto.Disable()
            self.baseline_extrap.Disable()
            self.baseline_options_sizer.Hide(self.baseline_auto)
            self.baseline_options_sizer.Hide(self.baseline_extrap)

            try:
                self.plot_page.remove_plot_range('bl_start', 'sub')
            except KeyError:
                pass
            try:
                self.plot_page.remove_plot_range('bl_end', 'sub')
            except KeyError:
                pass

            try:
                self.plot_page.remove_plot_data('baseline', 'sub')
            except KeyError:
                pass

            try:
                self.plot_page.remove_plot_data('intensity', 'baseline')
            except KeyError:
                pass

            try:
                self.plot_page.remove_plot_data('calc', 'baseline')
            except KeyError:
                pass

            self.processing_done['baseline'] = False
            self.should_process['baseline'] = False

            self.switchSampleRange('baseline', 'sub')

            if self.processing_done['buffer']:
                if 'calc' in self.results['buffer']:
                    self.results['calc']['rg'] = self.results['buffer']['calc']['rg']
                    self.results['calc']['rger'] = self.results['buffer']['calc']['rger']
                    self.results['calc']['i0'] = self.results['buffer']['calc']['i0']
                    self.results['calc']['i0er'] = self.results['buffer']['calc']['i0er']
                    self.results['calc']['vcmw'] = self.results['buffer']['calc']['vcmw']
                    self.results['calc']['vcmwer'] = self.results['buffer']['calc']['vcmwer']
                    self.results['calc']['vpmw'] = self.results['buffer']['calc']['vpmw']
                else:
                    t = threading.Thread(target=self.updateProcessing, args=('calc',))
                    t.daemon = True
                    t.start()
                    self.threads.append(t)

                wx.CallAfter(self.plot_page.show_plot, 'Subtracted')

        else:
            self.bl_r1_start.Enable()
            self.bl_r1_end.Enable()
            self.bl_r2_start.Enable()
            self.bl_r2_end.Enable()
            self.bl_r1_pick.Enable()
            self.bl_r2_pick.Enable()
            self.baseline_calc.Enable()

            if baseline == 'Integral':
                self.baseline_auto.Enable()
                self.baseline_options_sizer.Show(self.baseline_auto)
            else:
                self.baseline_auto.Disable()
                self.baseline_options_sizer.Hide(self.baseline_auto)

            if baseline == 'Linear':
                self.baseline_extrap.Enable()
                self.baseline_options_sizer.Show(self.baseline_extrap)
            else:
                self.baseline_extrap.Disable()
                self.baseline_options_sizer.Hide(self.baseline_extrap)

            r1_start = self.bl_r1_start.GetValue()
            r1_end = self.bl_r1_end.GetValue()

            r2_start = self.bl_r2_start.GetValue()
            r2_end = self.bl_r2_end.GetValue()

            self.Layout()

            self.plot_page.update_plot_range(r1_start, r1_end, 'bl_start', 'sub')
            self.plot_page.update_plot_range(r2_start, r2_end, 'bl_end', 'sub')

            if self.processing_done['buffer']:
                wx.CallAfter(self.plot_page.show_plot, 'Subtracted')


    def updateBaselineRange(self, event):
        event_object = event.GetEventObject()
        value = event_object.GetValue()

        if event_object is self.bl_r1_start:
            current_range = self.bl_r1_end.GetRange()
            self.bl_r1_end.SetRange((value, current_range[-1]))

        elif event_object is self.bl_r1_end:
            current_range = self.bl_r1_start.GetRange()
            self.bl_r1_start.SetRange((current_range[0], value))

        elif event_object is self.bl_r2_start:
            current_range = self.bl_r2_end.GetRange()
            self.bl_r2_end.SetRange((value, current_range[-1]))

        elif event_object is self.bl_r2_end:
            current_range = self.bl_r2_start.GetRange()
            self.bl_r2_start.SetRange((current_range[0], value))

        if event_object is self.bl_r1_start or event_object is self.bl_r1_end:
            start = self.bl_r1_start.GetValue()
            end = self.bl_r1_end.GetValue()
            index = 'bl_start'

        elif event_object is self.bl_r2_start or event_object is self.bl_r2_end:
            start = self.bl_r2_start.GetValue()
            end = self.bl_r2_end.GetValue()
            index = 'bl_end'

        self.plot_page.update_plot_range(start, end, index, 'sub')

    def onCollapse(self, event):
        self.Layout()
        self.Refresh()
        self.SendSizeEvent()

    def _onSubtracted(self, event):
        is_not_sub = not event.IsChecked()
        self.buffer_range_list.Enable(is_not_sub)
        self.buffer_add_btn.Enable(is_not_sub)
        self.buffer_remove_btn.Enable(is_not_sub)
        self.buffer_auto_btn.Enable(is_not_sub)

        for item in self.buffer_range_list.get_items():
            self.plot_page.show_plot_range(item.GetId(), 'unsub', is_not_sub)

    def _onSeriesAdd(self, evt):
        """Called when the Add control buttion is used."""
        ctrl = evt.GetEventObject()
        if ctrl is self.buffer_add_btn:
            parent_list = self.buffer_range_list
        elif ctrl is self.sample_add_btn:
            parent_list = self.sample_range_list

        index, start, end = self._addSeriesRange(parent_list)

        if parent_list is self.buffer_range_list:
            self.plot_page.update_plot_range(start, end, index, 'unsub')
            self.plot_page.show_plot('Unsubtracted')
        else:
            self.plot_page.update_plot_range(start, end, index, 'gen_sub')
            if self.processing_done['baseline']:
                self.plot_page.show_plot('Baseline Corrected')
            elif self.processing_done['buffer']:
                self.plot_page.show_plot('Subtracted')

    def _addSeriesRange(self, parent_list):
        range_item = parent_list.create_items()

        start, end = range_item.get_range()
        index = range_item.GetId()

        self.Layout()

        return index, start, end

    def _onSeriesRemove(self, evt):
        """Called by the Remove control button, removes a control."""

        ctrl = evt.GetEventObject()
        if ctrl is self.buffer_remove_btn:
            parent_list = self.buffer_range_list
        elif ctrl is self.sample_remove_btn:
            parent_list = self.sample_range_list

        selected = parent_list.get_selected_items()

        while len(selected) > 0:
            item = selected[0]
            idx = item.GetId()

            if parent_list is self.buffer_range_list:
                self.plot_page.remove_plot_range(idx, 'unsub')
            else:
                self.plot_page.remove_plot_range(idx, 'gen_sub')

            if len(selected) > 1:
                parent_list.remove_item(item, resize=False)
            else:
                parent_list.remove_item(item, resize=True)

    def switchSampleRange(self, plot1, plot2):
        items = self.sample_range_list.get_items()

        for item in items:
            idx = item.GetId()

            self.plot_page.remove_plot_range(idx, plot1)

            start, end = item.get_range()
            self.plot_page.update_plot_range(start, end, idx, plot2)

    def onSeriesPick(self, event):
        event_object = event.GetEventObject()
        event_item = event_object.GetParent()
        parent_list = event_item.item_list

        index = event_item.GetId()

        start_item = event_item.start_ctrl
        end_item = event_item.end_ctrl

        if parent_list is self.buffer_range_list:
            wx.CallAfter(self.plot_page.pick_plot_range, start_item, end_item, index, 'unsub')
            wx.CallAfter(self.plot_page.show_plot, 'Unsubtracted')
        else:
            wx.CallAfter(self.plot_page.pick_plot_range, start_item, end_item, index, 'gen_sub')
            if self.processing_done['baseline']:
                wx.CallAfter(self.plot_page.show_plot, 'Baseline Corrected')
            elif self.processing_done['buffer']:
                wx.CallAfter(self.plot_page.show_plot, 'Subtracted')

    def onBaselinePick(self, event):
        event_object = event.GetEventObject()

        if event_object is self.bl_r1_pick:
            start_item = self.bl_r1_start
            end_item = self.bl_r1_end
            index = 'bl_start'

        elif event_object is self.bl_r2_pick:
            start_item = self.bl_r2_start
            end_item = self.bl_r2_end
            index = 'bl_end'

        wx.CallAfter(self.plot_page.pick_plot_range, start_item, end_item, index, 'sub')
        wx.CallAfter(self.plot_page.show_plot, 'Subtracted')


    def setPickRange(self, index, pick_range, plot_type):
        pick_range.sort()

        if index == 'bl_start' or index == 'bl_end':
            if index == 'bl_start':
                start_ctrl = self.bl_r1_start
                end_ctrl = self.bl_r1_end
            elif index == 'bl_end':
                start_ctrl = self.bl_r2_start
                end_ctrl = self.bl_r2_end

            current_start_range = start_ctrl.GetRange()
            current_end_range = end_ctrl.GetRange()

            new_start = max(pick_range[0], current_start_range[0])
            new_end = min(pick_range[1], current_end_range[1])

            start_ctrl.SetValue(new_start)
            end_ctrl.SetValue(new_end)

            start_ctrl.SetRange((current_start_range[0], new_end))

            current_end_range = end_ctrl.GetRange()
            end_ctrl.SetRange((new_start, current_end_range[1]))

            self.plot_page.update_plot_range(new_start, new_end, index, 'sub')

        else:
            item = wx.FindWindowById(index)

            current_start_range = item.start_ctrl.GetRange()
            current_end_range = item.end_ctrl.GetRange()

            new_start = max(pick_range[0], current_start_range[0])
            new_end = min(pick_range[1], current_end_range[1])

            item.start_ctrl.SetValue(new_start)
            item.end_ctrl.SetValue(new_end)

            item.start_ctrl.SetRange((current_start_range[0], new_end))

            current_end_range = item.end_ctrl.GetRange()
            item.end_ctrl.SetRange((new_start, current_end_range[1]))

            if item.item_type == 'buffer':
                self.plot_page.update_plot_range(new_start, new_end, index, 'unsub')
            else:
                self.plot_page.update_plot_range(new_start, new_end, index, 'gen_sub')

    def _validateBufferRange(self):
        valid = True

        if not self.subtracted.IsChecked():
            buffer_items = self.buffer_range_list.get_items()

            if len(buffer_items) == 0:
                valid = False
                msg = ("You must specify at least one buffer range.")
            else:
                buffer_range_list = [item.get_range() for item in buffer_items]

                for i in range(len(buffer_range_list)):
                    start, end = buffer_range_list[i]

                    for j in range(len(buffer_range_list)):
                        if j != i:
                            jstart, jend = buffer_range_list[j]
                            if jstart < start and start < jend:
                                valid = False
                            elif jstart < end and end < jend:
                                valid = False
                            elif jstart == start and jend == end:
                                valid = False

                        if not valid:
                            break

                    if not valid:
                        break

                msg = ("Buffer ranges should be non-overlapping.")

        if not valid:
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Buffer range invalid", wx.ICON_ERROR|wx.OK)

        return valid

    def _validateBuffer(self, sasms, frame_idx, fast=False):
        """
        Note: Test order is by time it takes for large data point frames
        (>2000). Put the fastest ones first, and if you're doing the automated
        test it makes it much faster.
        """

        intensity = self._getRegionIntensity(sasms)
        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        sim_cor = self.raw_settings.get('similarityCorrection')

        (valid, similarity_results, svd_results,
            intI_results) = SASCalc.validateBuffer(sasms, frame_idx, intensity,
            sim_test, sim_cor, sim_thresh, fast)

        return valid, similarity_results, svd_results, intI_results

    def _getBufferInvalidMsg(self, similarity_results, svd_results,
        intI_results, sim_test, sim_threshold, frame_idx, buffer_sasms):
        msg = ''

        if (not similarity_results['all_similar'] or not similarity_results['low_q_similar']
            or not similarity_results['high_q_similar']):

            msg = msg + ('\nStatistical tests were performed using the {} test '
                'and a p-value\nthreshold of {}. Frame {} was chosen as the '
                'reference frame.\n'.format(sim_test, sim_threshold, frame_idx[similarity_results['max_idx']]))

            all_outlier_set = set(frame_idx[similarity_results['all_outliers']])
            low_outlier_set = set(frame_idx[similarity_results['low_q_outliers']])
            high_outlier_set = set(frame_idx[similarity_results['high_q_outliers']])

            if not similarity_results['all_similar']:
                msg = msg + ('\nUsing the whole q range, the following frames\n'
                    'were found to be different:\n')
                msg = msg + ', '.join(map(str, frame_idx[similarity_results['all_outliers']]))
                msg = msg + '\n'

            if (not similarity_results['low_q_similar'] and
                all_outlier_set != low_outlier_set and
                not all_outlier_set.issuperset(low_outlier_set)):
                qi, qf = buffer_sasms[0].getQrange()
                q = buffer_sasms[0].getQ()

                if abs(q[0]) > 0.0001 and abs(q[0]) < 10:
                    qi_val = '{:.4f}'.format(round(q[0], 4))
                else:
                    qi_val = '{:.3E}'.format(q[0])

                if abs(q[100]) > 0.0001 and abs(q[100]) < 10:
                    qf_val = '{:.4f}'.format(round(q[100], 4))
                else:
                    qf_val = '{:.3E}'.format(q[100])

                msg = msg + ('\nUsing a low q range of q={} to {}, the following frames\n'
                    'were found to be different:\n'.format(qi_val, qf_val))
                msg = msg + ', '.join(map(str, frame_idx[similarity_results['low_q_outliers']]))
                msg = msg + '\n'

            if (not similarity_results['high_q_similar'] and
                all_outlier_set != high_outlier_set and
                not all_outlier_set.issuperset(high_outlier_set)):
                qi, qf = buffer_sasms[0].getQrange()
                q = buffer_sasms[0].getQ()

                if abs(q[-100]) > 0.0001 and abs(q[-100]) < 10:
                    qi_val = '{:.4f}'.format(round(q[-100], 4))
                else:
                    qi_val = '{:.3E}'.format(q[-100])

                if abs(q[-1]) > 0.0001 and abs(q[-1]) < 10:
                    qf_val = '{:.4f}'.format(round(q[-1], 4))
                else:
                    qf_val = '{:.3E}'.format(q[-1])

                msg = msg + ('\nUsing a high q range of q={} to {}, the following frames\n'
                    'were found to be different:\n'.format(qi_val, qf_val))
                msg = msg + ', '.join(map(str, frame_idx[similarity_results['high_q_outliers']]))
                msg = msg + '\n'

        if not intI_results['intI_valid'] or not intI_results['smoothed_intI_valid']:
            msg = msg+('\nPossible correlations between intensity and frame '
                'number were detected\n(no correlation is expected for '
                'buffer regions)\n')

        if svd_results['svals'] != 1:
            msg = msg+('\nAutomated singular value decomposition found {} '
                'significant\nsingular values in the selected region.\n'.format(svd_results['svals']))

        return msg

    def processBuffer(self):

        sim_threshold = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        correction = self.raw_settings.get('similarityCorrection')
        calc_threshold = self.raw_settings.get('secCalcThreshold')

        valid = self._validateBufferRange()

        if not valid:
            self.continue_processing = False
            return

        if not self.subtracted.IsChecked():

            buffer_items = self.buffer_range_list.get_items()
            buffer_range_list = [item.get_range() for item in buffer_items]

            if 'buffer' in self.results:
                if self.results['buffer']['buffer_range']:
                    cur_br = set(buffer_range_list)
                    old_br = set(self.results['buffer']['buffer_range'])
                    if cur_br == old_br and not self.secm.intensity_change:
                        self.continue_processing = False
                        msg = ("This buffer range is already set.")
                        wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame,
                            msg, "Buffer already set", wx.ICON_INFORMATION|wx.OK)
                        return #No change in buffer range, no need to do anything

            frame_idx = []
            for item in buffer_range_list:
                frame_idx = frame_idx + list(range(item[0], item[1]+1))

            frame_idx = sorted(set(frame_idx))
            frame_idx = np.array(frame_idx)

            buffer_sasms = [self.secm.getSASM(idx) for idx in frame_idx]

            valid, similarity_results, svd_results, intI_results = self._validateBuffer(buffer_sasms,
                frame_idx)

            if not valid:
                msg = self._getBufferInvalidMsg(similarity_results, svd_results,
                    intI_results, sim_test, sim_threshold, frame_idx, buffer_sasms)

                msg = ('RAW found potential differences between selected '
                    'buffer frames.\n') + msg

                wx.CallAfter(self.series_frame.showBusy, False)
                answer = self._displayQuestionDialog(msg,
                    'Warning: Selected buffer frames are different',
                [('Cancel', wx.ID_CANCEL), ('Continue', wx.ID_YES)],
                wx.ART_WARNING)

                wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

                if answer[0] != wx.ID_YES:
                    self.continue_processing = False
                    return

            avg_sasm, success, err = self.secm.averageFrames(buffer_range_list,
                'unsub', sim_test, sim_threshold, correction, True)

            if not success:
                if err[0] == 'q_vector':
                    msg = 'The selected items must have the same q vectors to be averaged.'
                    wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame,
                            msg, "Average Error", wx.ICON_INFORMATION|wx.OK)
                    self.continue_processing = False
                    return

            qref = None
            qrange = None
            if self.plot_page.intensity == 'q_val':
                qref = float(self.plot_page.q_val.GetValue())
            elif self.plot_page.intensity == 'q_range':
                q1 = float(self.plot_page.q_range_start.GetValue())
                q2 = float(self.plot_page.q_range_end.GetValue())

                qrange = (q1, q2)

            subtracted_sasms, use_subtracted_sasm = self.secm.subtractAllSASMs(avg_sasm,
                self.plot_page.intensity, calc_threshold, qref, qrange)

        else:
            subtracted_sasms = self.secm.getAllSASMs()
            use_subtracted_sasm = [True for i in range(len(subtracted_sasms))]
            buffer_range_list = []
            avg_sasm = None

        sub_mean_i = np.array([sasm.getMeanI() for sasm in subtracted_sasms])
        sub_total_i = np.array([sasm.getTotalI() for sasm in subtracted_sasms])

        results = {'buffer_range':  buffer_range_list,
            'sub_sasms':            subtracted_sasms,
            'use_sub_sasms':        use_subtracted_sasm,
            'similarity_test':      sim_test,
            'similarity_corr':      correction,
            'similarity_thresh':    sim_threshold,
            'calc_thresh':          calc_threshold,
            'already_subtracted':   self.subtracted.IsChecked(),
            'sub_mean_i':           sub_mean_i,
            'sub_total_i':          sub_total_i,
            'buffer_sasm':          avg_sasm,
            }

        self.results['buffer'] = results

        self.processing_done['buffer'] = True

        self.secm.intensity_change = False

        if self.plot_page.get_plot() == 'Unsubtracted':
            if not self.should_process['baseline']:
                wx.CallAfter(self.plot_page.show_plot, 'Subtracted')
            else:
                wx.CallAfter(self.plot_page.show_plot, 'Baseline Corrected')

        wx.CallAfter(self.plotSubtracted)
        return

    def plotSubtracted(self):
        frames = self.secm.getFrames()

        intensity = self._getIntensity('buffer')

        self.plot_page.update_plot_data(frames, intensity, 'intensity', 'left', 'sub')

    def _getIntensity(self, int_type):

        if int_type == 'unsub':
            if self.plot_page.intensity == 'total':
                intensity = self.secm.getIntI()
            elif self.plot_page.intensity == 'mean':
                intensity = self.secm.getMeanI()
            elif self.plot_page.intensity == 'q_val':
                qref = float(self.plot_page.q_val.GetValue())
                sasms = self.secm.getAllSASMs()
                intensity = np.array([sasm.getIofQ(qref) for sasm in sasms])
            elif self.plot_page.intensity == 'q_range':
                q1 = float(self.plot_page.q_range_start.GetValue())
                q2 = float(self.plot_page.q_range_end.GetValue())
                sasms = self.secm.getAllSASMs()
                intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in sasms])

        else:
            if self.plot_page.intensity == 'total':
                intensity = self.results[int_type]['sub_total_i']
            elif self.plot_page.intensity == 'mean':
                intensity = self.results[int_type]['sub_mean_i']
            elif self.plot_page.intensity == 'q_val':
                qref = float(self.plot_page.q_val.GetValue())
                sasms = self.results[int_type]['sub_sasms']
                intensity = np.array([sasm.getIofQ(qref) for sasm in sasms])
            elif self.plot_page.intensity == 'q_range':
                q1 = float(self.plot_page.q_range_start.GetValue())
                q2 = float(self.plot_page.q_range_end.GetValue())
                sasms = self.results[int_type]['sub_sasms']
                intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in sasms])

        return intensity

    def _getRegionIntensity(self, sasms):
        if self.plot_page.intensity == 'total':
            intensity = np.array([sasm.getTotalI() for sasm in sasms])
        elif self.plot_page.intensity == 'mean':
            intensity = np.array([sasm.getMeanI() for sasm in sasms])
        elif self.plot_page.intensity == 'q_val':
            qref = float(self.plot_page.q_val.GetValue())
            intensity = np.array([sasm.getIofQ(qref) for sasm in sasms])
        elif self.plot_page.intensity == 'q_range':
            q1 = float(self.plot_page.q_range_start.GetValue())
            q2 = float(self.plot_page.q_range_end.GetValue())
            intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in sasms])

        return intensity

    def _validateBaselineRange(self):
        valid = True

        r1 = (self.bl_r1_start.GetValue(), self.bl_r1_end.GetValue())
        r2 = (self.bl_r2_start.GetValue(), self.bl_r2_end.GetValue())

        if r1[1] >= r2[0]:
            valid = False
            msg = ('The end of the start region must be before the start of '
                'the end region.')

        if self.baseline_cor.GetStringSelection() == 'Integral':
            if r1[1]-r1[0] < 10 or r2[1]-r2[0] < 10:
                valid = False
                msg = ('For the integral method both regions must be at least '
                    '10 frames long.')

        if not valid:
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame,
                msg, "Baseline start/end range invalid", wx.ICON_ERROR|wx.OK)


        return valid

    def _validateBaseline(self, sasms, frames, ref_sasms, all_sasms, bl_type, start, fast=False):
        intensity = self._getRegionIntensity(sasms)
        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        sim_cor = self.raw_settings.get('similarityCorrection')

        (valid, similarity_results, svd_results, intI_results,
            other_results) = SASCalc.validateBaseline(sasms, frames,
            intensity, bl_type, ref_sasms, start, sim_test, sim_cor, sim_thresh,
            fast)

        return valid, similarity_results, svd_results, intI_results, other_results

    def _getBaselineInvalidMsg(self, similarity_results, svd_results, intI_results,
        other_results, bl_type, start, sim_test, sim_threshold, frame_idx, buffer_sasms):

        msg = self._getBufferInvalidMsg(similarity_results, svd_results,
                    intI_results, sim_test, sim_threshold, frame_idx, buffer_sasms)

        if bl_type == 'Integral':
            # if not other_results['range_valid']:
            #     if start:
            #         msg = msg+('\nProfiles prior to the selected start region were '
            #             'found to be different from those in the\nselected start '
            #             'region. This may indicate that the baseline is already '
            #             'changing in\nthe selected start region.\n')
            #     else:
            #         msg = msg+('\nProfiles after to the selected end region were '
            #             'found to be different from those in the\nselected end '
            #             'region. This may indicate that the baseline is still '
            #             'changing in\nthe selected end region.\n')

            if not start:
                if not other_results['zero_valid']:
                    msg = msg+('\nIn the selected end region, some q values are '
                        'less than those in the selected start\nregion. The '
                        'integral baseline correction method will not work for '
                        'those q values.\n')

        return msg

    def processBaseline(self):
        valid = self._validateBaselineRange()

        if not valid:
            self.continue_processing = False
            return

        bl_type = self.baseline_cor.GetStringSelection()
        bl_extrap = self.baseline_extrap.IsChecked()

        sim_threshold = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        calc_threshold = self.raw_settings.get('secCalcThreshold')
        max_iter = self.raw_settings.get('IBaselineMaxIter')
        min_iter = self.raw_settings.get('IBaselineMinIter')

        int_type = self.plot_page.intensity
        qref = float(self.plot_page.q_val.GetValue())
        q1 = float(self.plot_page.q_range_start.GetValue())
        q2 = float(self.plot_page.q_range_end.GetValue())
        qrange = (q1, q2)

        r1 = (self.bl_r1_start.GetValue(), self.bl_r1_end.GetValue())
        r2 = (self.bl_r2_start.GetValue(), self.bl_r2_end.GetValue())

        sub_sasms = self.results['buffer']['sub_sasms']
        unsub_sasms = self.secm.getAllSASMs()

        start_frames = list(range(r1[0], r1[1]+1))
        end_frames = list(range(r2[0], r2[1]+1))

        start_sasms = [sub_sasms[i] for i in start_frames]
        end_sasms = [sub_sasms[i] for i in end_frames]

        if bl_type == 'Integral':
            (s_valid,
            s_similarity_results,
            s_svd_results,
            s_intI_results,
            s_other_results) = self._validateBaseline(start_sasms, start_frames,
                start_sasms, sub_sasms, bl_type, True)

            if not s_valid:
                s_msg = self._getBaselineInvalidMsg(s_similarity_results,
                    s_svd_results, s_intI_results, s_other_results, bl_type,
                    True, sim_test, sim_threshold, np.array(start_frames), sub_sasms)

            (e_valid,
            e_similarity_results,
            e_svd_results,
            e_intI_results,
            e_other_results) = self._validateBaseline(end_sasms, end_frames,
                start_sasms, sub_sasms, bl_type, False)

            if not e_valid:
                e_msg = self._getBaselineInvalidMsg(e_similarity_results,
                    e_svd_results, e_intI_results, e_other_results, bl_type,
                    False, sim_test, sim_threshold, np.array(end_frames), sub_sasms)

            if not s_valid or not e_valid:
                msg = ('RAW found potential issues with the selected baseline '
                    'start/end regions(s).\n')

                if not s_valid:
                    msg = msg + ('\nThe start region may not be suitable for '
                        'baseline correction for the following reason(s):\n')

                    msg = msg + s_msg

                if not e_valid:
                    msg = msg + ('\nThe end region may not be suitable for '
                        'baseline correction for the following reason(s):\n')

                    msg = msg + e_msg

                wx.CallAfter(self.series_frame.showBusy, False)

                answer = self._displayQuestionDialog(msg,
                    'Warning: Selected baseline ranges may be invalid',
                [('Cancel', wx.ID_CANCEL), ('Continue', wx.ID_YES)],
                wx.ART_WARNING)

                wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

                if answer[0] != wx.ID_YES:
                    self.continue_processing = False
                    return

        elif bl_type == 'Linear':
            (valid,
            similarity_results,
            svd_results,
            intI_results,
            other_results) = self._validateBaseline(end_sasms, end_frames,
                start_sasms, sub_sasms, bl_type, False)

            if not valid:
                msg = ('RAW found potential issues with the selected baseline '
                    'start/end regions(s).\n')

                if not other_results['fit_valid']:
                    msg = msg + ('\nThe linear fit of the selected start region '
                        'does not match the linear fit of the\nselected end region '
                        'at all q values. This may indicate that a linear baseline\n'
                        'is not an appropriate correction over the selected '
                        'ranges.')

                wx.CallAfter(self.series_frame.showBusy, False)

                answer = self._displayQuestionDialog(msg,
                    'Warning: Selected baseline ranges may be invalid',
                [('Cancel', wx.ID_CANCEL), ('Continue', wx.ID_YES)],
                wx.ART_WARNING)

                wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

                if answer[0] != wx.ID_YES:
                    self.continue_processing = False
                    return

        (bl_sasms, use_subtracted_sasms, bl_corr, fit_results, sub_mean_i,
            sub_total_i, bl_sub_mean_i, bl_sub_total_i) = SASCalc.processBaseline(
            unsub_sasms, sub_sasms, r1, r2, bl_type, min_iter, max_iter,
            bl_extrap, int_type, qref, qrange, calc_threshold)

        results = {'baseline_start_range'   : r1,
            'baseline_end_range'            : r2,
            'sub_sasms'                     : bl_sasms,
            'use_sub_sasms'                 : use_subtracted_sasms,
            'baseline_corr'                 : bl_corr,
            'similarity_test'               : sim_test,
            'similarity_thresh'             : sim_threshold,
            'calc_thresh'                   : calc_threshold,
            'sub_mean_i'                    : sub_mean_i,
            'sub_total_i'                   : sub_total_i,
            'bl_sub_mean_i'                 : bl_sub_mean_i,
            'bl_sub_total_i'                : bl_sub_total_i,
            'baseline_extrap'               : bl_extrap,
            'fit_results'                   : fit_results,
            'baseline_type'                 : bl_type,
            }

        self.results['baseline'] = results

        self.processing_done['baseline'] = True

        if self.plot_page.get_plot() == 'Subtracted':
            wx.CallAfter(self.plot_page.show_plot, 'Baseline Corrected')

        wx.CallAfter(self.plotBaseline)
        wx.CallAfter(self.switchSampleRange, 'sub', 'baseline')

        return

    def plotBaseline(self):
        frames = self.secm.getFrames()
        intensity = self._getIntensity('baseline')

        bl_type = self.results['baseline']['baseline_type']
        bl_extrap = self.results['baseline']['baseline_extrap']

        r1 = self.results['baseline']['baseline_start_range']
        r2 = self.results['baseline']['baseline_end_range']
        bl_corr = self.results['baseline']['baseline_corr']

        if bl_type == 'Integral':
            bl_region = np.arange(r1[-1], r2[0]+1)
        elif bl_type == 'Linear' and not bl_extrap:
            bl_region = np.arange(r1[0], r2[1]+1)
        elif bl_type == 'Linear' and bl_extrap:
            bl_region = frames

        bl_intensity = self._getRegionIntensity(bl_corr)

        self.plot_page.update_plot_data(bl_region, bl_intensity, 'baseline', 'left', 'sub')
        self.plot_page.update_plot_data(frames, intensity, 'intensity', 'left', 'baseline')

    def processUV(self):
        pass

    def _validateCalc(self):
        valid = True

        window_size = self.avg_window.GetValue()
        vp_density = self.vp_density.GetValue()

        try:
            window_size = int(window_size)
        except Exception:
            msg = ("The averaging window size must be an integer.")
            valid = False
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Averaging window size invalid", wx.ICON_ERROR|wx.OK)
            return valid

        if window_size <= 0:
            msg = ("The window size must be larger than 0.")
            valid = False
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Averaging window size invalid", wx.ICON_ERROR|wx.OK)
            return valid

        try:
            vp_density = float(vp_density)
        except Exception:
            msg = ("The density for the Vp MW estimate must be a number.")
            valid = False
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Vp MW density invalid", wx.ICON_ERROR|wx.OK)
            return valid

        if vp_density < 0:
            msg = ("The density for the Vp MW estimate must be greater than 0.")
            valid = False
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Vp MW density invalid", wx.ICON_ERROR|wx.OK)
            return valid

        return valid

    def processCalcs(self, start):
        valid = self._validateCalc()

        if not valid:
            self.continue_processing = False
            return

        mol_type = self.vc_mol_type.GetStringSelection()

        if mol_type == 'Protein':
            is_protein = True
        else:
            is_protein = False

        error_weight = self.raw_settings.get('errorWeight')
        window_size = int(self.avg_window.GetValue())
        vp_density = float(self.vp_density.GetValue())
        vp_cutoff = self.raw_settings.get('MWVpCutoff')
        vp_qmax = self.raw_settings.get('MWVpQmax')
        vc_cutoff = self.raw_settings.get('MWVcCutoff')
        vc_qmax = self.raw_settings.get('MWVcQmax')
        vc_a_prot = self.raw_settings.get('MWVcAProtein')
        vc_b_prot = self.raw_settings.get('MWVcBProtein')
        vc_a_rna = self.raw_settings.get('MWVcARna')
        vc_b_rna = self.raw_settings.get('MWVcBRna')


        if self.secm.intensity_change:
            calc_threshold = self.raw_settings.get('secCalcThreshold')

            intensity = self._getIntensity('unsub')
            ref_sub = self._getRegionIntensity([self.results['buffer']['buffer_sasm']])

            self.results['buffer']['use_sub_sasms'] = abs(intensity/ref_sub[0])>calc_threshold

            if self.processing_done['baseline']:
                bl_type = self.results['baseline']['baseline_type']
                bl_corr = self.results['baseline']['baseline_corr']
                bl_extrap = self.results['baseline']['baseline_extrap']
                r1 = self.results['baseline']['baseline_start_range']
                r2 = self.results['baseline']['baseline_end_range']
                sub_sasms = self.results['buffer']['sub_sasms']

                use_subtracted_sasms = []
                zeroSASM = SASM.SASM(np.zeros_like(sub_sasms[0].getQ()),
                    sub_sasms[0].getQ(), sub_sasms[0].getErr(), {})
                unsub_sasms = self.secm.getAllSASMs()
                bl_unsub_sasms = []

                for j in range(len(unsub_sasms)):
                    if bl_type == 'Integral':
                        if j < r1[1]:
                            bkg_sasm = zeroSASM
                        elif j >= r1[1] and j <= r2[0]:
                            bkg_sasm = bl_corr[j-r1[1]]
                        else:
                            bkg_sasm = bl_corr[-1]

                    elif bl_type == 'Linear':
                        if bl_extrap:
                            bkg_sasm = bl_corr[j]
                        else:
                            if j >= r1[0] or j <= r2[1]:
                                bkg_sasm = bl_corr[j-r1[0]]
                            else:
                                bkg_sasm = zeroSASM

                    bl_unsub_sasms.append(SASProc.subtract(unsub_sasms[j], bkg_sasm, forced = True))

                bl_unsub_ref_sasm = SASProc.average([bl_unsub_sasms[j] for j in range(r1[0], r1[1]+1)], forced=True)

                int_type = self.plot_page.intensity
                if  int_type == 'total':
                    ref_intensity = bl_unsub_ref_sasm.getTotalI()
                elif int_type == 'mean':
                    ref_intensity = bl_unsub_ref_sasm.getMeanI()
                elif int_type == 'q_val':
                    qref = float(self.plot_page.q_val.GetValue())
                    ref_intensity = bl_unsub_ref_sasm.getIofQ(qref)
                elif int_type == 'q_range':
                    q1 = float(self.plot_page.q_range_start.GetValue())
                    q2 = float(self.plot_page.q_range_end.GetValue())
                    ref_intensity = bl_unsub_ref_sasm.getIofQRange(q1, q2)

                for sasm in bl_unsub_sasms:
                    if int_type == 'total':
                        sasm_intensity = sasm.getTotalI()
                    elif int_type == 'mean':
                        sasm_intensity = sasm.getMeanI()
                    elif int_type == 'q_val':
                        sasm_intensity = sasm.getIofQ(qref)
                    elif int_type == 'q_range':
                        sasm_intensity = sasm.getIofQRange(q1, q2)

                    if abs(sasm_intensity/ref_intensity) > calc_threshold:
                        use_subtracted_sasms.append(True)
                    else:
                        use_subtracted_sasms.append(False)

                self.results['baseline']['use_sub_sasms'] = use_subtracted_sasms

            self.secm.intensity_change = False

        if self.processing_done['baseline']:
            sub_sasms = self.results['baseline']['sub_sasms']
            use_sub_sasms = self.results['baseline']['use_sub_sasms']
        else:
            sub_sasms = self.results['buffer']['sub_sasms']
            use_sub_sasms = self.results['buffer']['use_sub_sasms']

        success, results = SASCalc.run_secm_calcs(sub_sasms, use_sub_sasms,
            window_size, is_protein, error_weight, vp_density, vp_cutoff,
            vp_qmax, vc_cutoff, vc_qmax, vc_a_prot, vc_b_prot, vc_a_rna,
            vc_b_rna)

        if success:
            self.results['calc'] = results
            self.processing_done['calc'] = True

        if not self.processing_done['baseline']:
            self.results['buffer']['calc'] = results

        elif self.processing_done['baseline'] and (start == 'calc' or start == 'buffer'):
            sub_sasms = self.results['buffer']['sub_sasms']
            use_sub_sasms = self.results['buffer']['use_sub_sasms']

            success, results = SASCalc.run_secm_calcs(sub_sasms, use_sub_sasms,
                window_size, is_protein, error_weight, vp_density, vp_cutoff,
                vp_qmax, vc_cutoff, vc_qmax, vc_a_prot, vc_b_prot, vc_a_rna,
                vc_b_rna)

            if success:
                self.results['buffer']['calc'] = results

        if success:
            wx.CallAfter(self.plotCalc)

    def plotCalc(self):
        frames = self.secm.getFrames()

        if self.plot_page.calc == 'Rg':
            data = self.results['calc']['rg']
        elif self.plot_page.calc == 'MW (Vc)':
            data = self.results['calc']['vcmw']
        elif self.plot_page.calc == 'MW (Vp)':
            data = self.results['calc']['vpmw']
        elif self.plot_page.calc == 'I0':
            data = self.results['calc']['i0']

        frames = frames[data>0]
        data = data[data>0]

        self.plot_page.update_plot_data(frames, data, 'calc', 'right', 'gen_sub')

        if 'calc' in self.results['buffer']:
            frames = self.secm.getFrames()

            if self.plot_page.calc == 'Rg':
                data = self.results['buffer']['calc']['rg']
            elif self.plot_page.calc == 'MW (Vc)':
                data = self.results['buffer']['calc']['vcmw']
            elif self.plot_page.calc == 'MW (Vp)':
                data = self.results['buffer']['calc']['vpmw']
            elif self.plot_page.calc == 'I0':
                data = self.results['buffer']['calc']['i0']

            frames = frames[data>0]
            data = data[data>0]

            self.plot_page.update_plot_data(frames, data, 'calc', 'right', 'sub')


    def _validateSampleRange(self):
        valid = True

        sample_items = self.sample_range_list.get_items()

        if not self.processing_done['calc']:
            valid = False
            msg = ("You must first specify a buffer range.")
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Specify buffer range", wx.ICON_ERROR|wx.OK)
        else:
            if len(sample_items) == 0:
                valid = False
                msg = ("You must specify at least one sample range.")
            else:
                sample_range_list = [item.get_range() for item in sample_items]

                for i in range(len(sample_range_list)):
                    start, end = sample_range_list[i]

                    for j in range(len(sample_range_list)):
                        if j != i:
                            jstart, jend = sample_range_list[j]
                            if jstart < start and start < jend:
                                valid = False
                            elif jstart < end and end < jend:
                                valid = False
                            elif jstart == start and jend == end:
                                valid = False

                        if not valid:
                            break

                    if not valid:
                        break

                msg = ("Sample ranges should be non-overlapping.")

            if not valid:
                wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                    "Sample range invalid", wx.ICON_ERROR|wx.OK)

        return valid

    def _validateSample(self, sub_sasms, frame_idx, fast=False):
        intensity = self._getRegionIntensity(sub_sasms)

        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        sim_cor = self.raw_settings.get('similarityCorrection')

        rg = self.results['calc']['rg'][frame_idx]
        vcmw = self.results['calc']['vcmw'][frame_idx]
        vpmw = self.results['calc']['vpmw'][frame_idx]

        (valid, similarity_results, param_results, svd_results,
            sn_results) = SASCalc.validateSample(sub_sasms, frame_idx,
            intensity, rg, vcmw, vpmw, sim_test, sim_cor, sim_thresh, fast)

        return valid, similarity_results, param_results, svd_results, sn_results

    def _onToMainPlot(self, evt):
        t = threading.Thread(target=self._toMainPlot)
        t.daemon = True
        t.start()
        self.threads.append(t)

    def _toMainPlot(self):
        self.proc_lock.acquire()

        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')

        valid = self._validateSampleRange()

        if not valid:
            self.proc_lock.release()
            return

        wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

        sample_items = self.sample_range_list.get_items()
        sample_range_list = [item.get_range() for item in sample_items]

        if self.processing_done['baseline']:
            sub_sasms = self.results['baseline']['sub_sasms']
        else:
            sub_sasms = self.results['buffer']['sub_sasms']
            buffer_sasm = self.results['buffer']['buffer_sasm']

        frame_idx = []
        for item in sample_range_list:
            frame_idx = frame_idx + list(range(item[0], item[1]+1))

        frame_idx = sorted(set(frame_idx))
        frame_idx = np.array(frame_idx)

        valid, similarity_results, param_results, svd_results, sn_results = self._validateSample(
            [sub_sasms[idx] for idx in frame_idx], frame_idx)

        if not valid:
            msg = ('RAW found potential problems with the selected sample frames.\n')

            if (not similarity_results['all_similar'] or not similarity_results['low_q_similar']
                or not similarity_results['high_q_similar']):
                msg = msg + ('\nStatistical tests were performed using the {} test '
                    'and a p-value\nthreshold of {}. Frame {} was chosen as the '
                    'reference frame.\n'.format(sim_test, sim_thresh, frame_idx[similarity_results['max_idx']]))

                all_outlier_set = set(frame_idx[similarity_results['all_outliers']])
                low_outlier_set = set(frame_idx[similarity_results['low_q_outliers']])
                high_outlier_set = set(frame_idx[similarity_results['high_q_outliers']])

                if not similarity_results['all_similar']:
                    msg = msg + ('\nUsing the whole q range, the following frames\n'
                        'were found to be different:\n')
                    msg = msg + ', '.join(map(str, frame_idx[similarity_results['all_outliers']]))
                    msg = msg + '\n'

                if (not similarity_results['low_q_similar'] and
                    all_outlier_set != low_outlier_set and
                    not all_outlier_set.issuperset(low_outlier_set)):
                    qi, qf = sub_sasms[0].getQrange()
                    q = sub_sasms[0].getQ()

                    if abs(q[0]) > 0.0001 and abs(q[0]) < 10:
                        qi_val = '{:.4f}'.format(round(q[0], 4))
                    else:
                        qi_val = '{:.3E}'.format(q[0])

                    if abs(q[100]) > 0.0001 and abs(q[100]) < 10:
                        qf_val = '{:.4f}'.format(round(q[100], 4))
                    else:
                        qf_val = '{:.3E}'.format(q[100])

                    msg = msg + ('\nUsing a low q range of q={} to {}, the following frames\n'
                        'were found to be different:\n'.format(qi_val, qf_val))
                    msg = msg + ', '.join(map(str, frame_idx[similarity_results['low_q_outliers']]))
                    msg = msg + '\n'

                if (not similarity_results['high_q_similar'] and
                    all_outlier_set != high_outlier_set and
                    not all_outlier_set.issuperset(high_outlier_set)):
                    qi, qf = sub_sasms[0].getQrange()
                    q = sub_sasms[0].getQ()

                    if abs(q[-100]) > 0.0001 and abs(q[-100]) < 10:
                        qi_val = '{:.4f}'.format(round(q[-100], 4))
                    else:
                        qi_val = '{:.3E}'.format(q[-100])

                    if abs(q[-1]) > 0.0001 and abs(q[-1]) < 10:
                        qf_val = '{:.4f}'.format(round(q[-1], 4))
                    else:
                        qf_val = '{:.3E}'.format(q[-1])

                    msg = msg + ('\nUsing a high q range of q={} to {}, the following frames\n'
                        'were found to be different:\n'.format(qi_val, qf_val))
                    msg = msg + ', '.join(map(str, frame_idx[similarity_results['high_q_outliers']]))
                    msg = msg + '\n'

            if not param_results['param_valid']:
                if param_results['param_range_valid']:
                    msg = msg+('\nPossible correlations with frame number were detected '
                        'in the\nfollowing parameters (no correlation is expected for '
                        'well-subtracted\nsingle-species data):\n')

                    if param_results['rg_pval'] <= 0.05:
                        msg = msg + ('- Radius of gyration\n')
                    if param_results['vcmw_pval'] <= 0.05:
                        msg = msg + ('- Mol. weight from volume of correlation method\n')
                    if param_results['vpmw_pval'] <= 0.05:
                        msg = msg + ('- Mol. weight from adjusted Porod volume method\n')
                else:
                    msg = msg+('\nAuto Rg was unable to determine Rg values for the '
                        'following frames:\n')
                    msg = msg + ', '.join(map(str, frame_idx[param_results['param_bad_frames']]))
                    msg = msg + '\n'

            if svd_results['svals'] != 1:
                msg = msg+('\nAutomated singular value decomposition found {} '
                    'significant\nsingular values in the selected region.\n'.format(svd_results['svals']))

            if not sn_results['sn_valid']:
                msg = msg + ("\nAveraging some of the selected frames decreases signal to "
                "noise in the\nfinal profile. For the best overall signal to noise the "
                "following frames should not\nbe included:\n")
                msg = msg + ', '.join(map(str, frame_idx[sn_results['low_sn']]))
                msg = msg + '\n'

            wx.CallAfter(self.series_frame.showBusy, False)
            answer = self._displayQuestionDialog(msg,
                'Warning: Selected sample frames are different',
            [('Cancel', wx.ID_CANCEL), ('Continue', wx.ID_YES)],
            wx.ART_WARNING)

            if answer[0] != wx.ID_YES:
                self.proc_lock.release()
                return
            else:
                wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

        secm_prefix = os.path.splitext(os.path.split(self.secm.getParameter('filename'))[1])[0]

        if (not self.processing_done['baseline'] and
            not self.results['buffer']['already_subtracted']):

            sasms = self.secm.getAllSASMs()
            sasm_list = [sasms[idx] for idx in frame_idx]

            average_sasm = SASProc.average(sasm_list, forced=True)
            average_sasm.setParameter('filename', 'A_{}'.format(average_sasm.getParameter('filename')))

            final_sasm = SASProc.subtract(average_sasm, buffer_sasm, forced=True)
            final_sasm.setParameter('filename', 'S_A_{}'.format(secm_prefix))
            color = 'red'

        else:
            sasm_list = [sub_sasms[idx] for idx in frame_idx]

            final_sasm = SASProc.average(sasm_list, forced=True)
            final_sasm.setParameter('filename', 'A_S_{}'.format(secm_prefix))
            color = 'forest green'

        RAWGlobals.mainworker_cmd_queue.put(['to_plot_sasm', [[final_sasm], color, None, True, 2]])

        self.processing_done['sample'] = True
        self.results['sample'] = {'sample_range'    : sample_range_list,
            }

        wx.CallAfter(self.series_frame.showBusy, False)
        self.proc_lock.release()

        return

    def _onBufferAuto(self, event):
        t = threading.Thread(target=self._findBufferRange)
        t.daemon = True
        t.start()
        self.threads.append(t)

    def _findBufferRange(self):
        self.proc_lock.acquire()

        wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

        intensity = self._getIntensity('unsub')
        buffer_sasms = self.secm.getAllSASMs()

        avg_window = int(self.avg_window.GetValue())
        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        sim_cor = self.raw_settings.get('similarityCorrection')

        success, region_start, region_end = SASCalc.findBufferRange(buffer_sasms,
            intensity, avg_window, sim_test,  sim_cor, sim_thresh)

        if success:
            wx.CallAfter(self._addAutoBufferRange, region_start, region_end)
        else:
            msg = ("Failed to find a valid buffer range.")
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Buffer range not found", wx.ICON_ERROR|wx.OK)

        wx.CallAfter(self.series_frame.showBusy, False)

        self.proc_lock.release()

    def _onSampleAuto(self, event):

        if self.processing_done['calc']:
            t = threading.Thread(target=self._findSampleRange)
            t.daemon = True
            t.start()
            self.threads.append(t)
        else:
            msg = ("You must first set a buffer range before you can run the "
                "automated determination of the sample range.")
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Requires buffer range", wx.ICON_ERROR|wx.OK)

    def _findSampleRange(self):
        self.proc_lock.acquire()

        wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

        if self.processing_done['baseline']:
            sub_sasms = self.results['baseline']['sub_sasms']
            intensity = self._getIntensity('baseline')
        else:
            sub_sasms = self.results['buffer']['sub_sasms']
            intensity = self._getIntensity('buffer')

        avg_window = int(self.avg_window.GetValue())
        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        sim_cor = self.raw_settings.get('similarityCorrection')


        rg = self.results['calc']['rg']
        vcmw = self.results['calc']['vcmw']
        vpmw = self.results['calc']['vpmw']

        success, region_start, region_end = SASCalc.findSampleRange(sub_sasms,
            intensity, rg, vcmw, vpmw, avg_window, sim_test, sim_cor,
            sim_thresh)

        if success:
            wx.CallAfter(self._addAutoSampleRange, region_start, region_end)
        else:
            msg = ("Failed to find a valid sample range.")
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Sample range not found", wx.ICON_ERROR|wx.OK)

        wx.CallAfter(self.series_frame.showBusy, False)

        self.proc_lock.release()

        return

    def _onBaselineAuto(self, event):
        if self.processing_done['buffer']:
            t = threading.Thread(target=self._findBaselineRange)
            t.daemon = True
            t.start()
            self.threads.append(t)
        else:
            msg = ("You must first set a buffer range before you can run the "
                "automated determination of the baseline region.")
            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Requires buffer range", wx.ICON_ERROR|wx.OK)

    def _findBaselineRange(self):
        self.proc_lock.acquire()

        wx.CallAfter(self.series_frame.showBusy, True, 'Please wait, processing.')

        sub_sasms = self.results['buffer']['sub_sasms']
        intensity = self._getIntensity('buffer')

        bl_type = self.baseline_cor.GetStringSelection()

        sim_thresh = self.raw_settings.get('similarityThreshold')
        sim_test = self.raw_settings.get('similarityTest')
        sim_cor = self.raw_settings.get('similarityCorrection')

        avg_window = int(self.avg_window.GetValue())

        if (not self.results['buffer']['already_subtracted']
            and len(self.results['buffer']['buffer_range'])==1):
            region1_start = self.results['buffer']['buffer_range'][0][0]
            region1_end = self.results['buffer']['buffer_range'][0][1]
            start_region = (region1_start, region1_end)
        else:
            start_region = None

        (start_failed, end_failed, region1_start, region1_end, region2_start,
            region2_end) = SASCalc.findBaselineRange(sub_sasms, intensity,
            bl_type, avg_window, start_region, sim_test, sim_cor, sim_thresh)

        if not start_failed and not end_failed:
            wx.CallAfter(self._updateAutoBaselineRange, region1_start, region1_end,
                region2_start, region2_end)
        else:
            if not start_failed:
                wx.CallAfter(self._updateAutoBaselineRange, region1_start, region1_end,
                    -1, -1)
                msg = ("Failed to find a valid baseline end region.")

            elif not end_failed:
                wx.CallAfter(self._updateAutoBaselineRange, -1, -1, region2_start,
                    region2_end)
                msg = ("Failed to find a valid baseline start region.")

            else:
                msg = ("Failed to find valid baseline start and end regions.")

            wx.CallAfter(self.main_frame.showMessageDialog, self.series_frame, msg,
                "Baseline range not found", wx.ICON_ERROR|wx.OK)

        wx.CallAfter(self.series_frame.showBusy, False)

        self.proc_lock.release()

    def _addAutoSampleRange(self, region_start, region_end):
        index, j1, j2 = self._addSeriesRange(self.sample_range_list)

        item = wx.FindWindowById(index)

        current_start_range = item.start_ctrl.GetRange()
        current_end_range = item.end_ctrl.GetRange()

        item.start_ctrl.SetValue(region_start)
        item.end_ctrl.SetValue(region_end)

        item.start_ctrl.SetRange((current_start_range[0], region_end))
        item.end_ctrl.SetRange((region_start, current_end_range[1]))

        self.plot_page.update_plot_range(region_start, region_end, index, 'gen_sub')

        if self.processing_done['baseline']:
            self.plot_page.show_plot('Baseline Corrected')
        else:
            self.plot_page.show_plot('Subtracted')

    def _addAutoBufferRange(self, region_start, region_end):
        index, j1, j2 = self._addSeriesRange(self.buffer_range_list)

        item = wx.FindWindowById(index)

        current_start_range = item.start_ctrl.GetRange()
        current_end_range = item.end_ctrl.GetRange()

        item.start_ctrl.SetValue(region_start)
        item.end_ctrl.SetValue(region_end)

        item.start_ctrl.SetRange((current_start_range[0], region_end))
        item.end_ctrl.SetRange((region_start, current_end_range[1]))

        self.plot_page.update_plot_range(region_start, region_end, index, 'unsub')

        self.plot_page.show_plot('Unsubtracted')

    def _updateAutoBaselineRange(self, r1_start, r1_end, r2_start, r2_end):

        if r1_start != -1:
            self.bl_r1_start.SetValue(r1_start)
            self.bl_r1_end.SetValue(r1_end)

            current_range = self.bl_r1_start.GetRange()
            self.bl_r1_start.SetRange((current_range[0], r1_end))

            current_range = self.bl_r1_end.GetRange()
            self.bl_r1_end.SetRange((r1_start, current_range[-1]))

            self.plot_page.update_plot_range(r1_start, r1_end, 'bl_start', 'sub')

        if r2_start != -1:
            self.bl_r2_start.SetValue(r2_start)
            self.bl_r2_end.SetValue(r2_end)

            current_range = self.bl_r2_start.GetRange()
            self.bl_r2_start.SetRange((current_range[0], r2_end))

            current_range = self.bl_r2_end.GetRange()
            self.bl_r2_end.SetRange((r2_start, current_range[-1]))

            self.plot_page.update_plot_range(r2_start, r2_end, 'bl_end', 'sub')

        self.plot_page.show_plot('Subtracted')

    def _displayQuestionDialog(self, question, label, button_list, icon=None,
        filename=None, save_path=None):

        wx.CallAfter(self._showQuestionDialogFromThread, question, label,
            button_list, icon, filename, save_path)

        self.question_thread_wait_event.wait()
        self.question_thread_wait_event.clear()

        answer = self.question_return_queue.get()
        self.question_return_queue.task_done()

        return answer

    def _showQuestionDialogFromThread(self, question, label, button_list, icon=None,
        filename=None, save_path=None):
        ''' Function to show a question dialog from the thread '''

        question_dialog = RAWCustomDialogs.CustomQuestionDialog(self, question,
            button_list, label, icon, filename, save_path, style=wx.CAPTION|wx.RESIZE_BORDER)
        result = question_dialog.ShowModal()
        path = question_dialog.getPath()
        question_dialog.Destroy()

        if path:
            self.question_return_queue.put([result, path])
        else:
            self.question_return_queue.put([result])  # put answer in thread safe queue

        self.question_thread_wait_event.set()                 # Release thread from its waiting state

    def onCiteButton(self, event):
        msg = ('In addition to citing the RAW paper:\nIf you use the '
            'integral baseline correction in your work please cite the '
            'following paper:\nhttps://doi.org/10.1107/S1600576716011201\n'
            'Brookes et al. (2016). J. Appl. Cryst. 49, 1827-1841.\n\n'
            )
        wx.MessageBox(str(msg), "How to cite integral baseline correction", style = wx.ICON_INFORMATION | wx.OK)

class SeriesRangeItemList(RAWCustomCtrl.ItemList):

    def __init__(self, series_panel, item_type, *args, list_type='LC', **kwargs):
        self.series_panel = series_panel
        self.item_type = item_type
        self.list_type = list_type

        RAWCustomCtrl.ItemList.__init__(self, *args, **kwargs)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _create_toolbar(self):
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        toolbar_sizer.Add(wx.StaticText(self, label='Start'),
            border=self._FromDIP(3), flag=wx.LEFT)
        toolbar_sizer.Add(wx.StaticText(self, label='End'),
            border=self._FromDIP(35), flag=wx.LEFT)

        toolbar_sizer.AddStretchSpacer(1)

        return toolbar_sizer

    def create_items(self):
        item = SeriesRangeItem(self.series_panel, self.item_type, self,
            self.list_panel, list_type=self.list_type, id=self.NewControlId())
        self.add_items([item])

        return item

class SeriesRangeItem(RAWCustomCtrl.ListItem):

    def __init__(self, series_panel, item_type, *args, list_type='LC', **kwargs):
        self.series_panel = series_panel
        self.item_type = item_type
        self.list_type = list_type

        RAWCustomCtrl.ListItem.__init__(self, *args, **kwargs)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _create_layout(self):
        if self.list_type == 'LC':
            frames = self.series_panel.secm.getFrames()
        elif self.list_type == 'REGALS':
            frames = np.arange(self.series_panel.start, self.series_panel.end+1)

        self.start_ctrl = RAWCustomCtrl.IntSpinCtrl(self, wx.ID_ANY,
            min_val=frames[0], max_val=frames[-1], size=self._FromDIP((60,-1)))
        self.end_ctrl = RAWCustomCtrl.IntSpinCtrl(self, wx.ID_ANY,
            min_val=frames[0], max_val=frames[-1], size=self._FromDIP((60,-1)))

        self.start_ctrl.SetValue(frames[0])
        self.end_ctrl.SetValue(frames[-1])

        self.start_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.series_panel.updateSeriesRange)
        self.end_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.series_panel.updateSeriesRange)

        pick = wx.Button(self, label='Pick')
        pick.Bind(wx.EVT_BUTTON, self.series_panel.onSeriesPick)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.start_ctrl, border=self._FromDIP(5), flag=wx.LEFT
            |wx.ALIGN_CENTER_VERTICAL)
        top_sizer.Add(self.end_ctrl, border=self._FromDIP(5), flag=wx.LEFT
            |wx.ALIGN_CENTER_VERTICAL)
        top_sizer.Add(pick, border=self._FromDIP(5), flag=wx.LEFT|wx.RIGHT
            |wx.ALIGN_CENTER_VERTICAL)
        top_sizer.AddStretchSpacer(1)

        self.SetSizer(top_sizer)

    def get_range(self):
        return self.start_ctrl.GetValue(), self.end_ctrl.GetValue()


class GuinierTestApp(wx.App):

    def OnInit(self, filename = None):

        #ExpObj, ImgDummy = fileIO.loadFile('/home/specuser/Downloads/BSUB_MVMi7_5_FULL_001_c_plot.rad')

        tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'lyzexp.dat')

        #tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'Lys12_1_001_plot.rad')

        print(tst_file)
        raw_settings = RAWSettings.RawGuiSettings()

        ExpObj, ImgDummy = SASFileIO.loadFile(tst_file, raw_settings)

        if isinstance(ExpObj, list):
            ExpObj = ExpObj[0]

        frame = GuinierFrame(self, 'Guinier Fit', ExpObj, None)
        self.SetTopWindow(frame)
        frame.SetSize(self._FromDIP((800,600)))
        frame.CenterOnScreen()
        frame.Show(True)
        return True

if __name__ == "__main__":

    #This GUI can be run from a commandline: python guinierGUI.py <filename>
    args = sys.argv

    if len(args) > 1:
        filename = args[1]
    else:
        filename = None

    app = GuinierTestApp(0, filename)   #MyApp(redirect = True)
    app.MainLoop()

    #app = PorodTestApp(0, filename)   #MyApp(redirect = True)
    #app.MainLoop()
