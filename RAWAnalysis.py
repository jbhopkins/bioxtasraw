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
import matplotlib
import numpy as np
import sys
import os
import copy
import multiprocessing
import threading
import Queue
import wx
import time
import re
import platform
import subprocess
import collections
import shutil
matplotlib.rcParams['backend'] = 'WxAgg'
matplotlib.rc('image', origin = 'lower')        # turn image upside down.. x,y, starting from lower left

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg#,Toolbar, FigureCanvasWx
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
from matplotlib.figure import Figure
import matplotlib.colors as mplcol
from mpl_toolkits.mplot3d import Axes3D

# These are for the AutoWrapStaticText class
from wx.lib.wordwrap import wordwrap
from wx.lib.stattext import GenStaticText as StaticText
import wx.lib.agw.flatnotebook as flatNB
from wx.lib.agw import ultimatelistctrl as ULC

from scipy import integrate
import scipy.stats as stats

import RAWSettings
import RAWCustomCtrl
import SASCalc
import SASFileIO
import SASM
import SASExceptions
import RAWGlobals
import RAWCustomDialogs

class GuinierPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.data_line = None

        subplotLabels = [('Guinier', '$q^2$', '$\ln(I(q))$', .1), ('Residual', '$q^2$', '$\Delta \ln (I(q))$', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])

            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.15, bottom = 0.08, right = 0.95, top = 0.95, hspace = 0.3)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)
        # self.canvas.SetBackgroundColour('white')

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Guinier']
        b = self.subplots['Residual']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)

        self.canvas.mpl_disconnect(self.cid)

        self.updateDataPlot(self.xlim, is_autorg=True)

        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def _calcFit(self, is_autorg=False):
        ''' calculate fit and statistics '''
        xmin, xmax = self.xlim

        x = self.x[xmin:xmax+1]
        y = self.y[xmin:xmax+1]
        yerr = self.yerr[xmin:xmax+1]

        #Remove NaN and Inf values:
        x = x[np.where(np.isnan(y) == False)]
        yerr = yerr[np.where(np.isnan(y) == False)]
        y = y[np.where(np.isnan(y) == False)]

        x = x[np.where(np.isinf(y) == False)]
        yerr = yerr[np.where(np.isinf(y) == False)]
        y = y[np.where(np.isinf(y) == False)]

        Rg, I0, Rger, I0er, opt, cov = SASCalc.calcRg(x, y, yerr, transform=False)

        if is_autorg:
            est_rg_err = None
            est_i0_err = None
        else:
            est_rg_err, est_i0_err = self._estimateError(x, y, yerr)

        #Get fit statistics:
        a = opt[0]
        b = opt[1]
        y_fit = SASCalc.linear_func(x, a, b)
        error = y - y_fit
        r_sqr = 1 - np.square(error).sum()/np.square(y-y.mean()).sum()

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
        win_size = len(x)

        if win_size < 10:
            est_rg_err = None
            est_i0_err = None
        else:
            var = win_size/10
            rg_list = np.empty((var+1)**2, dtype=np.float64)
            i0_list = np.empty((var+1)**2, dtype=np.float64)
            index = 0

            for li in range(0, var+1):
                for ri in range(0,var+1):
                    if ri == 0:
                        Rg, I0, Rger, I0er, opt, cov = SASCalc.calcRg(x[li:], y[li:], yerr[li:], transform=False)
                    else:
                        Rg, I0, Rger, I0er, opt, cov = SASCalc.calcRg(x[li:-ri], y[li:-ri], yerr[li:-ri], transform=False)
                    rg_list[index] = Rg
                    i0_list[index] = I0
                    index = index+1

            est_rg_err = rg_list.std()
            est_i0_err = i0_list.std()


        return est_rg_err, est_i0_err

    def plotExpObj(self, ExpObj):
        qmin, qmax = ExpObj.getQrange()

        self.orig_i = ExpObj.i[qmin:qmax]
        self.orig_q = ExpObj.q[qmin:qmax]
        self.orig_err = ExpObj.err[qmin:qmax]

        self.x = np.square(self.orig_q)
        self.y = np.log(self.orig_i)
        self.yerr = np.absolute(self.orig_err/self.orig_i)

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

        x = x[np.where(np.isnan(y)==False)]
        y = y[np.where(np.isnan(y)==False)]
        x = x[np.where(np.isinf(y)==False)]
        y = y[np.where(np.isinf(y)==False)]

        a = self.subplots['Guinier']
        b = self.subplots['Residual']

        try:
            x_fit, y_fit, I0, error, newInfo = self._calcFit(is_autorg)
        except TypeError as e:
            print e
            return

        controlPanel = wx.FindWindowByName('GuinierControlPanel')
        wx.CallAfter(controlPanel.updateInfo, newInfo)


        xg = [0, x_fit[0]]
        yg = [I0, y_fit[0]]

        zeros = np.zeros((1,len(x_fit)))[0]

        x_lim_front = x[0]
        x_lim_back = x[-1]

        if not self.data_line:
            self.data_line, = a.plot(x, y, 'b.', animated = True)
            self.fit_line, = a.plot(x_fit, y_fit, 'r', animated = True)
            self.interp_line, = a.plot(xg, yg, 'g--', animated = True)

            self.error_line, = b.plot(x_fit, error, 'b', animated = True)
            self.zero_line, = b.plot(x_fit, zeros, 'r', animated = True)

            self.lim_front_line = a.axvline(x=x_lim_front, color = 'r', linestyle = '--', animated = True)
            self.lim_back_line = a.axvline(x=x_lim_back, color = 'r', linestyle = '--', animated = True)

            self.canvas.draw()
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

            self.zero_line.set_xdata(x_fit)
            self.zero_line.set_ydata(zeros)

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()
        b_oldx = b.get_xlim()
        b_oldy = b.get_ylim()

        a.relim()
        a.autoscale_view()

        b.relim()
        b.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()
        b_newx = b.get_xlim()
        b_newy = b.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy or b_newx != b_oldx or b_newy != b_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.background)
        self.canvas.restore_region(self.err_background)

        a.draw_artist(self.data_line)
        a.draw_artist(self.fit_line)
        a.draw_artist(self.interp_line)
        a.draw_artist(self.lim_front_line)
        a.draw_artist(self.lim_back_line)

        b.draw_artist(self.error_line)
        b.draw_artist(self.zero_line)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)


class GuinierControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, ExpObj, manip_item):

        self.parent = parent

        self.ExpObj = ExpObj

        self.manip_item = manip_item
        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.guinier_frame = wx.FindWindowByName('GuinierFrame')

        self.old_analysis = {}

        if 'guinier' in self.ExpObj.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.ExpObj.getParameter('analysis')['guinier'])

        try:
            self.raw_settings = self.main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.spinctrlIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId()}

        self.staticTxtIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId()}

        self.infodata = {'I0' : ('I0 :', self.NewControlId(), self.NewControlId()),
                        'Rg' : ('Rg :', self.NewControlId(), self.NewControlId()),
                        'qRg_max': ('qRg_max :', self.NewControlId()),
                        'qRg_min': ('qRg :', self.NewControlId()),
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

        autorg_button = wx.Button(self, -1, 'AutoRG')
        autorg_button.Bind(wx.EVT_BUTTON, self.onAutoRg)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1)

        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self.createInfoBox()
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP ,5)
        qrgsizer = self.createQRgInfo()
        boxSizer.Add(qrgsizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 5)

        error_sizer = self.createErrorSizer()

        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self.createControls()
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND)
        line_sizer = wx.StaticLine(parent = self, style = wx.LI_HORIZONTAL)
        boxSizer2.Add(line_sizer, 0, flag = wx.EXPAND | wx.ALL, border = 10)
        boxSizer2.Add(autorg_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        # top_sizer.Add(self.createConcInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        top_sizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        top_sizer.Add(error_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        top_sizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        top_sizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT| wx.TOP, 5)

        self.SetSizer(top_sizer)

        self.setFilename(os.path.basename(ExpObj.getParameter('filename')))

    def createQRgInfo(self):

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        txt = wx.StaticText(self, -1, self.infodata['qRg_min'][0])
        ctrl1 = wx.TextCtrl(self, self.infodata['qRg_min'][1], '0')
        ctrl2 = wx.TextCtrl(self, self.infodata['qRg_max'][1], '0')

        sizer.Add(txt, 0, wx.RIGHT, 7)
        sizer.Add(ctrl1,0, wx.RIGHT, 5)
        sizer.Add(ctrl2,0)

        return sizer

    def createInfoBox(self):

        sizer = wx.FlexGridSizer(rows = len(self.infodata), cols = 2)

        for key in self.infodata.iterkeys():


            if key == 'qRg_min' or key == 'qRg_max':
                continue

            if len(self.infodata[key]) == 2:
                txt = wx.StaticText(self, -1, self.infodata[key][0])
                ctrl = wx.TextCtrl(self, self.infodata[key][1], '0')
                sizer.Add(txt, 0)
                sizer.Add(ctrl,0)

            else:
                txt = wx.StaticText(self, -1, self.infodata[key][0])
                ctrl1 = wx.TextCtrl(self, self.infodata[key][1], '0')

                bsizer = wx.BoxSizer()
                bsizer.Add(ctrl1,0,wx.EXPAND)

                sizer.Add(txt,0)
                sizer.Add(bsizer,0)

        return sizer

    def createControls(self):

        sizer = wx.FlexGridSizer(rows = 2, cols = 4)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableCol(2)
        sizer.AddGrowableCol(3)

        sizer.Add(wx.StaticText(self,-1,'q_min'),1, wx.LEFT, 5)
        sizer.Add(wx.StaticText(self,-1,'n_min'),1)
        sizer.Add(wx.StaticText(self,-1,'q_max'),1)
        sizer.Add(wx.StaticText(self,-1,'n_max'),1)

        self.startSpin = RAWCustomCtrl.IntSpinCtrl(self, self.spinctrlIDs['qstart'], size = (60,-1))
        self.endSpin = RAWCustomCtrl.IntSpinCtrl(self, self.spinctrlIDs['qend'], size = (60,-1))

        self.startSpin.SetValue(0)
        self.endSpin.SetValue(0)

        self.startSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.endSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)

        self.qstartTxt = wx.TextCtrl(self, self.staticTxtIDs['qstart'], 'q: ', size = (60, -1), style = wx.PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(self, self.staticTxtIDs['qend'], 'q: ', size = (60, -1), style = wx.PROCESS_ENTER)

        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)

        sizer.Add(self.qstartTxt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 3)
        sizer.Add(self.startSpin, 0, wx.EXPAND | wx.RIGHT, 3)
        sizer.Add(self.qendTxt, 0, wx.EXPAND | wx.RIGHT, 3)
        sizer.Add(self.endSpin, 0, wx.EXPAND | wx.RIGHT, 5)

        return sizer

    def createErrorSizer(self):
        box = wx.StaticBox(self, wx.ID_ANY, 'Uncertainty')

        sum_sizer = wx.FlexGridSizer(1, 4, 3, 3)
        sum_sizer.AddGrowableCol(1)
        sum_sizer.AddGrowableCol(3)
        rg_sum_lbl = wx.StaticText(self, wx.ID_ANY, 'Rg : ')
        i0_sum_lbl = wx.StaticText(self, wx.ID_ANY, 'I0 : ')
        rg_sum_txt = wx.TextCtrl(self, self.error_data['sum_rg'], '', size = (60, -1))
        i0_sum_txt = wx.TextCtrl(self, self.error_data['sum_i0'], '', size = (60, -1))

        sum_sizer.AddMany([(rg_sum_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (rg_sum_txt, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            (i0_sum_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (i0_sum_txt, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            ])

        self.err_sizer = wx.FlexGridSizer(3, 4, 3, 3)
        self.err_sizer.AddGrowableCol(1)
        self.err_sizer.AddGrowableCol(2)
        self.err_sizer.AddGrowableCol(3)

        std_text = wx.StaticText(self, wx.ID_ANY, 'Fit')
        auto_text = wx.StaticText(self, wx.ID_ANY, 'AutoRg')
        est_text = wx.StaticText(self, wx.ID_ANY, 'Est.')

        self.err_sizer.AddMany([(wx.StaticText(self, wx.ID_ANY, ''), 0,),
            (std_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (auto_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (est_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            ])

        rg_text = wx.StaticText(self, wx.ID_ANY, 'Rg :')
        rg_fit = wx.TextCtrl(self, self.error_data['fsigma_rg'], '', size=(60,-1))
        rg_auto = wx.TextCtrl(self, self.error_data['autorg_rg'], '', size=(60,-1))
        rg_est = wx.TextCtrl(self, self.error_data['est_rg'], '', size=(60,-1))

        self.err_sizer.AddMany([(rg_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (rg_fit, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            (rg_auto, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            (rg_est, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            ])

        i0_text = wx.StaticText(self, wx.ID_ANY, 'I0 :')
        i0_fit = wx.TextCtrl(self, self.error_data['fsigma_i0'], '', size=(60,-1))
        i0_auto = wx.TextCtrl(self, self.error_data['autorg_i0'], '', size=(60,-1))
        i0_est = wx.TextCtrl(self, self.error_data['est_i0'], '', size=(60,-1))

        self.err_sizer.AddMany([(i0_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL),
            (i0_fit, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            (i0_auto, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            (i0_est, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND),
            ])

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        show_btn = wx.Button(self, self.button_ids['show'], 'Show Details')
        show_btn.Bind(wx.EVT_BUTTON, self._onShowButton)

        info_btn = wx.Button(self, self.button_ids['info'], 'More Info')
        info_btn.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer.Add(show_btn, 0, wx.ALL, 5)
        button_sizer.Add(info_btn, 0, wx.ALL, 5)

        self.err_top_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.err_top_sizer.Add(sum_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        self.err_top_sizer.Add(self.err_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        self.err_top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.err_top_sizer.Hide(self.err_sizer, recursive=True)

        return self.err_top_sizer

    def _initSettings(self):
        analysis = self.ExpObj.getParameter('analysis')

        if 'guinier' in analysis:

            guinier = analysis['guinier']

            qmin = float(guinier['qStart'])
            qmax = float(guinier['qEnd'])

            findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
            closest_qmin = findClosest(qmin, self.ExpObj.q)
            closest_qmax = findClosest(qmax, self.ExpObj.q)

            idx_min = np.where(self.ExpObj.q == closest_qmin)[0][0]
            idx_max = np.where(self.ExpObj.q == closest_qmax)[0][0]

            spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

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

            old_start = spinstart.GetValue()
            old_end = spinend.GetValue()

            try:
                spinstart.SetValue(int(idx_min))
                spinend.SetValue(int(idx_max))

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(idx_min)],5)))

                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(idx_max)],5)))

                if 'Rg_autorg_err' in guinier:
                    txt = wx.FindWindowById(self.error_data['autorg_rg'], self)
                    txt.SetValue(guinier['Rg_autorg_err'])

                    txt = wx.FindWindowById(self.error_data['autorg_i0'], self)
                    txt.SetValue(guinier['I0_autorg_err'])

                    self.updatePlot(is_autorg=True)
                else:
                    self.updatePlot()

            except IndexError:
                spinstart.SetValue(old_start)
                spinend.SetValue(old_end)

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(old_start)],5)))

                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                txt.SetValue(str(round(self.ExpObj.q[int(old_end)],5)))

                self.updatePlot()

        else:
            self.runAutoRg()



    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def createFileInfo(self):

        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY)

        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND)

        return boxsizer

    def onSaveInfo(self, evt):
        gp = wx.FindWindowByName('GuinierPlotPanel')
        try:
            x_fit, y_fit, I0, error, newInfo = gp._calcFit()

            self.updateInfo(newInfo)

            info_dict = {}

            for key in newInfo.keys():
                if key in self.infodata.keys():
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
            else:
                info_dict['Rg_est_err'] = newInfo['err_est_rg']
                info_dict['I0_est_err'] = newInfo['err_est_i0']
                info_dict['Rg_err'] = max(float(newInfo['err_est_rg']), float(newInfo['err_fsigma_rg']))
                info_dict['I0_err'] = max(float(newInfo['err_est_i0']), float(newInfo['err_fsigma_i0']))

            analysis_dict = self.ExpObj.getParameter('analysis')
            analysis_dict['guinier'] = info_dict

            if self.manip_item is not None:
                wx.CallAfter(self.manip_item.updateInfoTip, analysis_dict, fromGuinierDialog = True)
                if info_dict != self.old_analysis:
                    wx.CallAfter(self.manip_item.markAsModified)

            mw_window = wx.FindWindowByName('MolWeightFrame')

            if mw_window:
                mw_window.updateGuinierInfo()
        except TypeError:
            pass

        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()

    def onCloseButton(self, evt):

        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()

    def onAutoRg(self, evt):
        self.runAutoRg()

    def runAutoRg(self):

        rg, rger, i0, i0er, idx_min, idx_max = SASCalc.autoRg(self.ExpObj)

        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        old_start = spinstart.GetValue()
        old_end = spinend.GetValue()

        if rg == -1:
            msg = 'AutoRG could not find a suitable interval to calculate Rg.'
            wx.CallAfter(wx.MessageBox, str(msg), "AutoRG Failed", style = wx.ICON_ERROR | wx.OK)

        else:
            try:
                spinstart.SetValue(int(idx_min))
                spinend.SetValue(int(idx_max))

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

            except IndexError:
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

                msg = 'AutoRG did not produce a useable result. Please report this to the developers.'
                wx.MessageBox(str(msg), "AutoRG Failed", style = wx.ICON_ERROR | wx.OK)

        self.updatePlot(is_autorg=True)

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
        "elements).\n\n2) Autorg - If the autorg position is used, RAW reports "
        "the standard deviation of the Rg and I0 values from all 'good' fitting "
        "regions found during the search.\n\n3) Est. - An estimated uncertainty similar "
        "to that reported from the autorg function. When manual limits are set, RAW "
        "reports the standard deviation in Rg and I0 obtained from the set of intervals "
        "where n_min is varied bewteen n_min to n_min+(n_max-n_min)*.1 and "
        "n_max varied between n_max-(n_max-n_min)*.1 to n_max.")

        dlg = wx.MessageDialog(self, msg, "Estimate Rg and I0 Uncertainty", style = wx.ICON_INFORMATION | wx.OK)
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
        id = evt.GetId()

        spin = wx.FindWindowById(id, self)

        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        i = spin.GetValue()

        #Make sure the boundaries don't cross:
        if id == self.spinctrlIDs['qstart']:
            max = endSpin.GetValue()
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)

            if i > max-2:
                i = max - 2
                spin.SetValue(i)

        elif id == self.spinctrlIDs['qend']:
            min = startSpin.GetValue()
            txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)

            if i < min+2:
                i = min + 2
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

        plotpanel = wx.FindWindowByName('GuinierPlotPanel')

        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        i = int(spinstart.GetValue())
        i2 = int(spinend.GetValue())

        qmin, qmax = self.ExpObj.getQrange()

        xlim = [i-qmin,i2-qmin]

        plotpanel.canvas.mpl_disconnect(plotpanel.cid) #disconnect draw event to avoid recursions

        #Deals with problems of the zoom, pan, and home button and autoscaling the axes when we change the data range
        a = plotpanel.subplots['Guinier']
        b = plotpanel.subplots['Residual']
        if not a.get_autoscale_on():
            a.set_autoscale_on(True)
        if not b.get_autoscale_on():
            b.set_autoscale_on(True)

        plotpanel.updateDataPlot(xlim, is_autorg)
        plotpanel.cid = plotpanel.canvas.mpl_connect('draw_event', plotpanel.ax_redraw) #Reconnect draw_event


    def updateInfo(self, newInfo):
        for eachkey in newInfo.iterkeys():
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

        for eachKey in self.infodata.iterkeys():

            if len(self.infodata[eachKey]) == 2:
                ctrl = wx.FindWindowById(self.infodata[eachKey][1], self)
                val = ctrl.GetValue()
                guinierData[eachKey] = val
            else:
                ctrl1 = wx.FindWindowById(self.infodata[eachKey][1], self)

                val1 = ctrl1.GetValue()
                guinierData[eachKey] = val1

        return guinierData

### Main Guinier Frame!!! ###
class GuinierFrame(wx.Frame):

    def __init__(self, parent, title, ExpObj, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'GuinierFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'GuinierFrame', size = (800,600))

        splitter1 = wx.SplitterWindow(self, -1)


        plotPanel = GuinierPlotPanel(splitter1, -1, 'GuinierPlotPanel')
        self.controlPanel = GuinierControlPanel(splitter1, -1, 'GuinierControlPanel', ExpObj, manip_item)

        splitter1.SplitVertically(self.controlPanel, plotPanel, 300)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(290)    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(50)

        plotPanel.plotExpObj(ExpObj)


        self.controlPanel.setSpinLimits(ExpObj)
        self.controlPanel.setCurrentExpObj(ExpObj)

        splitter1.Layout()
        self.Layout()
        self.SendSizeEvent()
        splitter1.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)

        self.controlPanel._initSettings()

        self.CenterOnParent()
        self.Raise()


    def OnClose(self):

        self.Destroy()


class MolWeightFrame(wx.Frame):

    def __init__(self, parent, title, sasm, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'MolWeightFrame', size = (475,525))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'MolWeightFrame', size = (475,525))

        self.panel = wx.Panel(self, -1, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.sasm = sasm
        self.manip_item = manip_item

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.old_analysis = {}

        if 'molecularWeight' in self.sasm.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.sasm.getParameter('analysis')['molecularWeight'])

        try:
            self.raw_settings = self.main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.infodata = {'I0' : ('I0 :', self.NewControlId(), self.NewControlId()),
                         'Rg' : ('Rg :', self.NewControlId(), self.NewControlId())}

        self.ids = {'VC': {'mol_type' : self.NewControlId(),
                           'calc_mw' : self.NewControlId(),
                           'info': self.NewControlId(),
                           'more': self.NewControlId(),
                           'sup_vc': self.NewControlId(),
                           'sup_qr': self.NewControlId(),
                           'sup_a': self.NewControlId(),
                           'sup_b': self.NewControlId(),
                           'sup_plot': self.NewControlId()},
                    'conc': {'calc_mw' : self.NewControlId(),
                             'info': self.NewControlId(),
                             'more': self.NewControlId(),
                             'conc': self.NewControlId(),
                             'sup_i0': self.NewControlId(),
                             'sup_mw': self.NewControlId(),
                             'sup_conc': self.NewControlId(),
                             'sup_file': self.NewControlId()},
                    'VP': {'calc_mw' : self.NewControlId(),
                           'info': self.NewControlId(),
                           'more': self.NewControlId(),
                           'sup_vp': self.NewControlId(),
                           'sup_vpc': self.NewControlId(),
                           'sup_density': self.NewControlId()},
                    'abs': {'calc_mw' : self.NewControlId(),
                              'info': self.NewControlId(),
                              'more': self.NewControlId(),
                              'calib': self.NewControlId(),
                              'conc': self.NewControlId(),
                              'sup_pm': self.NewControlId(),
                              'sup_ps': self.NewControlId(),
                              'sup_pv': self.NewControlId(),
                              'sup_sc': self.NewControlId()}
                              }

        self.mws = {'conc'  : {},
                    'vc'    : {},
                    'vp'    : {},
                    'abs'   : {},
                    }

        topsizer = self._createLayout(self.panel)
        self._initSettings()

        self.panel.SetSizer(topsizer)
        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.panel.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)


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


        mw_sizer = wx.FlexGridSizer(2, 2, 5, 5)
        mw_sizer.AddGrowableCol(0)
        mw_sizer.AddGrowableCol(1)

        mw_sizer.Add(self.conc_panel, 0, wx.EXPAND)
        mw_sizer.Add(self.abs_panel, 0, wx.EXPAND)
        mw_sizer.Add(self.vc_panel, 0, wx.EXPAND)
        mw_sizer.Add(self.vp_panel, 0, wx.EXPAND)

        self.top_mw.SetSizer(mw_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.info_panel, 0, wx.EXPAND)
        top_sizer.Add(wx.StaticLine(parent = parent, style = wx.LI_HORIZONTAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        top_sizer.Add(self.top_mw, 10, wx.EXPAND)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(wx.StaticLine(parent = parent, style = wx.LI_HORIZONTAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        top_sizer.Add(self.button_panel, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.LEFT, 5)

        return top_sizer

    def _initSettings(self):

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:

            guinier = analysis['guinier']

            for each_key in self.infodata.iterkeys():
                window = wx.FindWindowById(self.infodata[each_key][1], self)
                if abs(float(guinier[each_key])) > 1e3 or abs(float(guinier[each_key])) < 1e-2:
                    window.ChangeValue('%.3E' %(guinier[each_key]))
                else:
                    window.ChangeValue('%.4f' %(round(float(guinier[each_key]), 4)))

        self.setFilename(os.path.basename(self.sasm.getParameter('filename')))

        if self.sasm.getAllParameters().has_key('Conc'):
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
            else:
                vc_type = self.raw_settings.get('MWVcType')
        except Exception, e:
            print e
            vc_type = self.raw_settings.get('MWVcType')

        if vc_type == 'Protein':
            aval = self.raw_settings.get('MWVcAProtein')
            bval = self.raw_settings.get('MWVcBProtein')
        else:
            aval = self.raw_settings.get('MWVcARna')
            bval = self.raw_settings.get('MWVcBRna')

        aCtrl.ChangeValue(str(aval))
        bCtrl.ChangeValue(str(bval))
        molCtrl.SetStringSelection(vc_type)

        wx.FindWindowById(self.ids['VC']['sup_plot'], self).plotSASM(self.sasm)

        #Initialize Vp MW settings
        vp_rho = self.raw_settings.get('MWVpRho')

        wx.FindWindowById(self.ids['VP']['sup_density'], self).ChangeValue(str(vp_rho))


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


        self.calcMW()


    def _createInfoLayout(self, parent):
        #Filename box
        box1 = wx.StaticBox(parent, -1, 'Filename')
        boxSizer1 = wx.StaticBoxSizer(box1, wx.HORIZONTAL)
        self.filenameTxtCtrl = wx.TextCtrl(parent, -1, '', style = wx.TE_READONLY)
        boxSizer1.Add(self.filenameTxtCtrl, 1)

        # Guinier parameters box
        infoSizer = wx.BoxSizer(wx.HORIZONTAL)

        for key in self.infodata.iterkeys():
            txt = wx.StaticText(parent, -1, self.infodata[key][0])
            ctrl1 = wx.TextCtrl(parent, self.infodata[key][1], '0', style = wx.TE_READONLY)

            infoSizer.Add(txt,0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
            infoSizer.Add(ctrl1,0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
            infoSizer.AddSpacer(5)

        guinierfitbutton = wx.Button(parent, -1, 'Guinier Fit')
        guinierfitbutton.Bind(wx.EVT_BUTTON, self.onGuinierFit)

        box2 = wx.StaticBox(parent, -1, 'Guinier Parameters')
        boxSizer2 = wx.StaticBoxSizer(box2, wx.HORIZONTAL)
        boxSizer2.Add(infoSizer, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL ,5)
        boxSizer2.Add(guinierfitbutton, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT| wx.TOP, 5)

        box = wx.StaticBox(parent, wx.ID_ANY, 'Info')
        top_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        top_sizer.Add(boxSizer1, 1, wx.EXPAND | wx.TOP | wx.BOTTOM , 5)
        top_sizer.Add(boxSizer2, 0, wx.TOP | wx.BOTTOM , 5)

        return top_sizer

    def _createConcLayout(self, parent):
        concbox = wx.StaticBox(parent, -1, 'I(0) Ref. MW')

        conc_ids = self.ids['conc']

        conc_info = wx.Button(parent, id = conc_ids['info'], label = 'More Info')
        conc_info.Bind(wx.EVT_BUTTON, self._onInfo)

        conc_details = wx.Button(parent, id = conc_ids['more'], label = 'Show Details')
        conc_details.Bind(wx.EVT_BUTTON, self._onMore)

        conc_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_buttonsizer.Add(conc_details, 0, wx.RIGHT, 2)
        conc_buttonsizer.Add(conc_info, 0, wx.LEFT, 2)


        concsizer = wx.BoxSizer(wx.HORIZONTAL)

        conc = wx.TextCtrl(parent, conc_ids['conc'], '', size = (60, -1))
        conc_txt = wx.StaticText(parent, -1,  'Concentration: ')
        conc_txt2 = wx.StaticText(parent, -1,  'mg/ml')

        conc.Bind(wx.EVT_TEXT, self._onUpdateConc)

        concsizer.Add(conc_txt,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        concsizer.Add(conc, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        concsizer.Add(conc_txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)


        mwsizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_mw = wx.TextCtrl(parent, conc_ids['calc_mw'], '', size = (80, -1), style = wx.TE_READONLY)
        mw_txt = wx.StaticText(parent, -1, 'MW :')
        mw_txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(mw_txt,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        mwsizer.Add(conc_mw, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        mwsizer.Add(mw_txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)


        sup_txt1 = wx.StaticText(parent, -1, 'Ref. I(0) :')
        sup_txt2 = wx.StaticText(parent, -1, 'Ref. MW :')
        sup_txt3 = wx.StaticText(parent, -1, 'kDa')
        sup_txt4 = wx.StaticText(parent, -1, 'Ref. Concentration :')
        sup_txt5 = wx.StaticText(parent, -1, 'mg/ml')
        sup_txt6 = wx.StaticText(parent, -1, 'File :')

        sup_i0 = wx.TextCtrl(parent, conc_ids['sup_i0'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_mw = wx.TextCtrl(parent, conc_ids['sup_mw'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_conc = wx.TextCtrl(parent, conc_ids['sup_conc'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_file = wx.TextCtrl(parent, conc_ids['sup_file'], '', size = (200, -1), style = wx.TE_READONLY)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer1.Add(sup_i0, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt2,0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_mw,1,wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_txt3,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt4,0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer3.Add(sup_conc,1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer3.Add(sup_txt5,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer4.Add(sup_txt6, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer4.Add(sup_file, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        self.conc_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.conc_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, 5)
        self.conc_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, 5)
        self.conc_sup_sizer.Add(sup_sizer3, 0, wx.BOTTOM, 5)
        self.conc_sup_sizer.Add(sup_sizer4, 0)


        self.conc_top_sizer = wx.StaticBoxSizer(concbox, wx.VERTICAL)
        self.conc_top_sizer.Add(concsizer, 0, wx.BOTTOM, 5)
        self.conc_top_sizer.Add(mwsizer, 0, wx.BOTTOM, 5)
        self.conc_top_sizer.Add(self.conc_sup_sizer, 0, wx.BOTTOM, 5)
        self.conc_top_sizer.Add(conc_buttonsizer, 0, wx.ALIGN_CENTER | wx.TOP, 2)

        self.conc_top_sizer.Hide(self.conc_sup_sizer,recursive = True)

        return self.conc_top_sizer

    def _createVCLayout(self, parent):

        vcbox = wx.StaticBox(parent, -1, 'Vc MW')

        vc_ids = self.ids['VC']

        vc_info = wx.Button(parent, id = vc_ids['info'], label = 'More Info')
        vc_info.Bind(wx.EVT_BUTTON, self._onInfo)

        vc_details = wx.Button(parent, id = vc_ids['more'], label = 'Show Details')
        vc_details.Bind(wx.EVT_BUTTON, self._onMore)

        vc_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        vc_buttonsizer.Add(vc_details, 0, wx.RIGHT, 2)
        vc_buttonsizer.Add(vc_info, 0, wx.LEFT, 2)



        mol_type = wx.Choice(parent, vc_ids['mol_type'], choices = ['Protein', 'RNA'])
        mol_type.Bind(wx.EVT_CHOICE, self._onMoleculeChoice)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)

        VCmw = wx.TextCtrl(parent, vc_ids['calc_mw'], '', size = (80, -1), style = wx.TE_READONLY)
        txt = wx.StaticText(parent, -1, 'MW :')
        txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(txt,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        mwsizer.Add(VCmw, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        mwsizer.Add(txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)


        sup_txt1 = wx.StaticText(parent, -1, 'Vc :')
        sup_txt2 = wx.StaticText(parent, -1, 'A^2')
        sup_txt3 = wx.StaticText(parent, -1, 'Qr :')
        sup_txt4 = wx.StaticText(parent, -1, 'A^3')
        sup_txt5 = wx.StaticText(parent, -1, 'a :')
        sup_txt6 = wx.StaticText(parent, -1, 'b :')

        sup_vc = wx.TextCtrl(parent, vc_ids['sup_vc'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_qr = wx.TextCtrl(parent, vc_ids['sup_qr'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_a = wx.TextCtrl(parent, vc_ids['sup_a'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_b = wx.TextCtrl(parent, vc_ids['sup_b'], '', size = (60, -1), style = wx.TE_READONLY)

        sup_sizer = wx.FlexGridSizer(rows = 2, cols = 5, hgap =0, vgap=5)
        sup_sizer.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_vc, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer.Add(sup_txt5, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 10)
        sup_sizer.Add(sup_a, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        sup_sizer.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_qr, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer.Add(sup_txt4, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer.Add(sup_txt6, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 10)
        sup_sizer.Add(sup_b, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        vc_plot = MWPlotPanel(parent, vc_ids['sup_plot'], '')

        self.vc_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vc_sup_sizer.Add(sup_sizer, 0, wx.BOTTOM, 5)
        self.vc_sup_sizer.Add(vc_plot, 0, wx.EXPAND)


        self.vc_top_sizer = wx.StaticBoxSizer(vcbox, wx.VERTICAL)
        self.vc_top_sizer.Add(mol_type, 0, wx.BOTTOM, 5)
        self.vc_top_sizer.Add(mwsizer, 0, wx.BOTTOM, 5)
        self.vc_top_sizer.Add(self.vc_sup_sizer, 0, wx.BOTTOM, 5)
        self.vc_top_sizer.Add(vc_buttonsizer, 0, wx.ALIGN_CENTER | wx.TOP, 2)

        self.vc_top_sizer.Hide(self.vc_sup_sizer, recursive = True)

        return self.vc_top_sizer

    def _createVPLayout(self, parent):
        vpbox = wx.StaticBox(parent, -1, 'Vp MW')

        vp_ids = self.ids['VP']

        vp_info = wx.Button(parent, id = vp_ids['info'], label = 'More Info')
        vp_info.Bind(wx.EVT_BUTTON, self._onInfo)

        vp_details = wx.Button(parent, id = vp_ids['more'], label = 'Show Details')
        vp_details.Bind(wx.EVT_BUTTON, self._onMore)

        vp_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        vp_buttonsizer.Add(vp_details, 0, wx.RIGHT, 2)
        vp_buttonsizer.Add(vp_info, 0, wx.RIGHT, 2)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)

        VpMW = wx.TextCtrl(parent, vp_ids['calc_mw'], '', size = (80, -1), style = wx.TE_READONLY)
        txt = wx.StaticText(parent, -1, 'MW :')
        txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(txt,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        mwsizer.Add(VpMW, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        mwsizer.Add(txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        mw_warning = AutoWrapStaticText(parent, 'Warning: final q point is outside the extrapolation region (0.15 < q < 0.45 1/A), no correction has been applied!')

        self.mw_warning_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mw_warning_sizer.Add(mw_warning, wx.EXPAND)


        sup_txt1 = wx.StaticText(parent, -1, 'Vp :')
        sup_txt2 = wx.StaticText(parent, -1, 'A^3')
        sup_txt3 = wx.StaticText(parent, -1, 'Corrected Vp :')
        sup_txt4 = wx.StaticText(parent, -1, 'A^3')
        sup_txt5 = wx.StaticText(parent, -1, 'Macromolecule Density :')
        sup_txt6 = wx.StaticText(parent, -1, 'kDa/A^3')

        sup_vp = wx.TextCtrl(parent, vp_ids['sup_vp'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_vpc = wx.TextCtrl(parent, vp_ids['sup_vpc'], '', size = (60, -1), style = wx.TE_READONLY)
        sup_density = wx.TextCtrl(parent, vp_ids['sup_density'], '', size = (60, -1), style = wx.TE_READONLY)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer1.Add(sup_vp, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer1.Add(sup_txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_vpc, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_txt4, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt5,0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer3.Add(sup_density,1,wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer3.Add(sup_txt6,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        self.vp_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vp_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, 5)
        self.vp_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, 5)
        self.vp_sup_sizer.Add(sup_sizer3,0)


        self.vp_top_sizer = wx.StaticBoxSizer(vpbox, wx.VERTICAL)
        self.vp_top_sizer.Add(mwsizer, 0, wx.BOTTOM, 5)
        self.vp_top_sizer.Add(self.mw_warning_sizer, 0, wx.BOTTOM | wx.EXPAND, 5)
        self.vp_top_sizer.Add(self.vp_sup_sizer, 0, wx.BOTTOM, 5)
        self.vp_top_sizer.Add(vp_buttonsizer, 0, wx.ALIGN_CENTER | wx.TOP, 2)

        self.vp_top_sizer.Hide(self.vp_sup_sizer, recursive = True)
        self.vp_top_sizer.Hide(self.mw_warning_sizer, recursive = True)

        return self.vp_top_sizer

    def _createAbsLayout(self, parent):
        absbox = wx.StaticBox(parent, -1, 'Abs. MW')

        abs_ids = self.ids['abs']

        abs_checkbox = wx.CheckBox(parent, id = abs_ids['calib'], label = 'Intensity on Absolute Scale', style = wx.ALIGN_RIGHT)
        abs_checkbox.SetValue(False)
        abs_checkbox.Bind(wx.EVT_CHECKBOX, self._onAbsCheck)


        abs_info = wx.Button(parent, id = abs_ids['info'], label = 'More Info')
        abs_info.Bind(wx.EVT_BUTTON, self._onInfo)

        abs_details = wx.Button(parent, id = abs_ids['more'], label = 'Show Details')
        abs_details.Bind(wx.EVT_BUTTON, self._onMore)

        abs_buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        abs_buttonsizer.Add(abs_details, 0, wx.RIGHT, 2)
        abs_buttonsizer.Add(abs_info, 0, wx.LEFT, 2)

        concsizer = wx.BoxSizer(wx.HORIZONTAL)

        conc = wx.TextCtrl(parent, abs_ids['conc'], '', size = (60, -1))
        conc_txt = wx.StaticText(parent, -1,  'Concentration: ')
        conc_txt2 = wx.StaticText(parent, -1,  'mg/ml')

        conc.Bind(wx.EVT_TEXT, self._onUpdateConc)

        concsizer.Add(conc_txt,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        concsizer.Add(conc, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        concsizer.Add(conc_txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)

        absMW = wx.TextCtrl(parent, abs_ids['calc_mw'], '', size = (80, -1), style = wx.TE_READONLY)
        txt = wx.StaticText(parent, -1, 'MW :')
        txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(txt,0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        mwsizer.Add(absMW, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        mwsizer.Add(txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)


        sup_txt1 = wx.StaticText(parent, -1, '# electrons per mass dry macromolecule :')
        sup_txt2 = wx.StaticText(parent, -1, 'e-/g')
        sup_txt3 = wx.StaticText(parent, -1, '# electrons per volume of buffer :')
        sup_txt4 = wx.StaticText(parent, -1, 'e-/cm^3')
        sup_txt5 = wx.StaticText(parent, -1, 'Protein partial specific volume :')
        sup_txt6 = wx.StaticText(parent, -1, 'cm^3/g')
        sup_txt9 = wx.StaticText(parent, -1, 'Calc. Scattering contrast per mass :')
        sup_txt10 = wx.StaticText(parent, -1, 'e- cm/g')

        sup_pm = wx.TextCtrl(parent, abs_ids['sup_pm'], '', size = (70, -1), style = wx.TE_READONLY)
        sup_ps = wx.TextCtrl(parent, abs_ids['sup_ps'], '', size = (70, -1), style = wx.TE_READONLY)
        sup_pv = wx.TextCtrl(parent, abs_ids['sup_pv'], '', size = (70, -1), style = wx.TE_READONLY)
        sup_sc = wx.TextCtrl(parent, abs_ids['sup_sc'], '', size = (70, -1), style = wx.TE_READONLY)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer1.Add(sup_pm, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer1.Add(sup_txt2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt3, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_ps, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer2.Add(sup_txt4, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt5, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer3.Add(sup_pv, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer3.Add(sup_txt6, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        sup_sizer5 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer5.Add(sup_txt9, 0, wx.ALIGN_CENTER_VERTICAL)
        sup_sizer5.Add(sup_sc, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sup_sizer5.Add(sup_txt10, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 1)

        self.abs_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.abs_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, 5)
        self.abs_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, 5)
        self.abs_sup_sizer.Add(sup_sizer3, 0, wx.BOTTOM, 5)
        self.abs_sup_sizer.Add(sup_sizer5,0)


        self.abs_top_sizer = wx.StaticBoxSizer(absbox, wx.VERTICAL)
        self.abs_top_sizer.Add(abs_checkbox, 0, wx.BOTTOM, 5)
        self.abs_top_sizer.Add(concsizer, 0, wx.BOTTOM, 5)
        self.abs_top_sizer.Add(mwsizer, 0, wx.BOTTOM, 5)
        self.abs_top_sizer.Add(self.abs_sup_sizer, 0, wx.BOTTOM, 5)
        self.abs_top_sizer.Add(abs_buttonsizer, 0, wx.ALIGN_CENTER | wx.TOP, 2)

        self.abs_top_sizer.Hide(self.abs_sup_sizer, recursive = True)

        return self.abs_top_sizer

    def _createButtonLayout(self, parent):
        button = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(parent, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        params_button = wx.Button(parent, -1, 'Change Advanced Parameters')
        params_button.Bind(wx.EVT_BUTTON, self.onChangeParams)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(params_button, 0, wx.ALIGN_LEFT | wx.RIGHT, 5)
        buttonSizer.Add(savebutton, 0, wx.RIGHT | wx.ALIGN_RIGHT, 5)
        buttonSizer.Add(button, 0, wx.RIGHT | wx.ALIGN_RIGHT, 5)

        return buttonSizer

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

            for each_key in self.infodata.iterkeys():
                window = wx.FindWindowById(self.infodata[each_key][1], self)
                if abs(float(guinier[each_key])) > 1e3 or abs(float(guinier[each_key])) < 1e-2:
                    window.SetValue('%.3E' %(guinier[each_key]))
                else:
                    window.SetValue('%.4f' %(round(float(guinier[each_key]), 4)))

        if self.sasm.getAllParameters().has_key('Conc'):
            conc = str(self.sasm.getParameter('Conc'))
            wx.FindWindowById(self.ids['conc']['conc'], self).ChangeValue(conc)
            wx.FindWindowById(self.ids['abs']['conc'], self).ChangeValue(conc)

        wx.FindWindowById(self.ids['VC']['sup_plot'], self).plotSASM(self.sasm)

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

        #Initialize Vp MW settings
        vp_rho = self.raw_settings.get('MWVpRho')

        wx.FindWindowById(self.ids['VP']['sup_density'], self).ChangeValue(str(vp_rho))


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


        self.calcMW()

    def _onInfo(self,evt):
        evt_id = evt.GetId()

        if evt_id == self.ids['conc']['info']:
            msg = ("The scattering at zero angle, I(0) is proportional to the molecular weight of the "
                  "macromolecule, and the concentration and contrast of the macromolecule in solution. If a reference "
                  "sample of known molecular weight and concentration is measured, it can be used to calibrate the "
                  "molecular weight of any other scattering profile with known concentration (assuming constant "
                  "contrast between reference and sample, and a monodisperse sample). Molecular weight is calculated "
                  "as:\n\n"
                  "MW_m = (I(0)_m / c_m) * (MM_st)/(I(0)_st / c_st)\n\n"
                  "where MW is the molecular weight, c is the concentration, and '_m' and '_st' designates quantities "
                  "from the macromolecule of interest and the standard respectively. For a reference see, among many, "
                  "Mylonas, E. & Svergun, D. I. (2007). J. Appl. Crystallogr. 40, s245-s249.\n\n"
                  "This method can yield inaccurate results if:\n"
                  "- The reference is not properly calibrated (concentration, I(0) measurement).\n"
                  "- I(0) is poorly determined.\n"
                  "- Sample concentration is poorly determined.\n"
                  "- The contrast between the macromolecule and buffer is significantly different between the reference and sample.")
        elif evt_id == self.ids['VC']['info']:
            msg = ("This method uses the approach described in: Rambo, R. P. & Tainer, J. A. (2013). Nature. "
                   "496, 477-481, please cite this paper in addition to the RAW paper if you use this method. "
                   "This method should work for both compact and flexible macromolecules. "
                   "The authors claim the error in MW determination is ~5-10%.\n\n"
                   "This method can yield inaccurate results if:\n"
                   "- The integral of q*I(q) doesn't converge (click 'Show Details' to see), which can indicate "
                   "the scattering profile is not measured to high enough q or that there is a bad buffer match.\n"
                   "- I(0) and/or Rg are poorly determined.\n"
                   "- You have a protein-nucleic acid complex.")
        elif evt_id == self.ids['VP']['info']:
            msg = ("This method uses the approach described in: Fischer, H., de Oliveira Neto, M., Napolitano, "
                  "H. B., Polikarpov, I., & Craievich, A. F. (2010). J. Appl. Crystallogr. 43, 101-109, "
                  "please cite this paper in addition to the RAW paper if you use this method.  It applies "
                  "a correction to the Porod volume, which has only been calculated for 0.15 < q_max < 0.45 1/A. "
                  "For scattering profiles with a maximum q outside this range, no correction is applied by RAW. "
                  "The authors report a maximum of 10% uncertainty for calculated molecular weight from globular proteins.\n\n"
                  "This method can yield inaccurate results if:\n"
                  "- The molecule is not globular (i.e. is flexible or extended).\n"
                  "- I(0) is poorly determined.\n"
                  "- The protein density used is inaccurate (can be changed in advanced settings).\n"
                  "- Your molecule is not a protein.\n\n"
                  "Note: To do the integration, RAW extrapolates the scattering profile to I(0) using the Guinier fit (if necessary). "
                  "The authors of the original paper used smoothed and extrapolated scattering profiles generated by "
                  "GNOM. This extrapolation method is currently used in their online calculator: http://saxs.ifsc.usp.br/).")
        else:
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
                   "- I(0) is poorly determined."
                   "- Sample concentration is poorly determined."
                   "- Scattering contrast is wrong, either from buffer changes or macromolecule type "
                   "(default settings are for protein).")

        dlg = wx.MessageDialog(self, msg, "Calculating Molecular Weight", style = wx.ICON_INFORMATION | wx.OK)
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
        else:
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

        self.calcVCMW()

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

    def _onUpdateDensity(self, evt):
        self.calcVpMW()

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

        # for eachKey in self.ids.iterkeys():
        #     mw = wx.FindWindowById(self.ids[eachKey]['calc_mw'], self).GetValue()

        #     if eachKey == 'conc':
        #         calcData['I(0)Concentration']['MW'] = mw
        #         self.sasm.setParameter('MW', mw)

        #     elif eachKey == 'VC':
        #         mol_type = wx.FindWindowById(self.ids[eachKey]['mol_type'], self).GetStringSelection()
        #         vcor = wx.FindWindowById(self.ids[eachKey]['sup_vc'], self).GetValue()

        #         calcData['VolumeOfCorrelation']['MW'] = mw
        #         calcData['VolumeOfCorrelation']['Type'] = mol_type
        #         calcData['VolumeOfCorrelation']['Vcor'] = vcor

        #     elif eachKey == 'VP':
        #         vporod = wx.FindWindowById(self.ids[eachKey]['sup_vp'], self).GetValue()
        #         vpcor = wx.FindWindowById(self.ids[eachKey]['sup_vpc'], self).GetValue()

        #         calcData['PorodVolume']['MW'] = mw
        #         calcData['PorodVolume']['VPorod'] = vporod
        #         calcData['PorodVolume']['VPorod_Corrected'] = vpcor

        #     elif eachKey == 'abs':
        #         calcData['Absolute']['MW'] = mw

        calcData['I(0)Concentration']['MW'] = self.mws['conc']['mw']
        self.sasm.setParameter('MW', self.mws['conc']['mw'])

        calcData['VolumeOfCorrelation']['MW'] = self.mws['vc']['mw']
        calcData['VolumeOfCorrelation']['Type'] = self.mws['vc']['type']
        calcData['VolumeOfCorrelation']['Vcor'] = self.mws['vc']['vc']

        calcData['PorodVolume']['MW'] = self.mws['vp']['mw']
        calcData['PorodVolume']['VPorod'] = self.mws['vp']['pVolume']
        calcData['PorodVolume']['VPorod_Corrected'] = self.mws['vp']['pv_cor']

        calcData['Absolute']['MW'] = self.mws['abs']['mw']

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
        self.calcConcMW()

        self.calcVCMW()

        self.calcVpMW()

        self.calcAbsMW()

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

        mw = SASCalc.calcRefMW(i0, conc)

        if mw > 0:
            self.mws['conc']['mw'] = str(mw)

            val = round(mw,1)

            if val > 1e3 or val < 1e-2:
                mwstr = '%.2E' %(val)
            else:
                mwstr = '%.1f' %(val)

            mwCtrl = wx.FindWindowById(conc_ids['calc_mw'], self)
            mwCtrl.ChangeValue(mwstr)
        else:
            self.mws['conc']['mw'] = ''

    def calcVCMW(self):

        vc_ids = self.ids['VC']
        molecule = wx.FindWindowById(vc_ids['mol_type'], self).GetStringSelection()

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            i0 = float(guinier['I0'])
            rg = float(guinier['Rg'])
        else:
            i0 = 0
            rg = 0

        if molecule == 'Protein':
            is_protein = True
        else:
            is_protein = False

        if rg > 0 and i0 > 0:
            mw, mw_error, vc, qr = SASCalc.calcVcMW(self.sasm, rg, i0, is_protein)

            self.mws['vc']['mw'] = str(mw)
            self.mws['vc']['vc'] = str(vc)
            self.mws['vc']['qr'] = str(qr)
            self.mws['vc']['type'] = molecule

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

            mwCtrl = wx.FindWindowById(vc_ids['calc_mw'], self)
            mwCtrl.ChangeValue(mwstr)

            wx.FindWindowById(vc_ids['sup_vc'], self).ChangeValue(vcstr)

            wx.FindWindowById(vc_ids['sup_qr'], self).ChangeValue(qrstr)
        else:
            self.mws['vc']['mw'] = ''
            self.mws['vc']['vc'] = ''
            self.mws['vc']['qr'] = ''
            self.mws['vc']['type'] = molecule

    def calcVpMW(self):
        #This is calculated using the method in Fischer et al. J. App. Crys. 2009

        vp_ids = self.ids['VP']

        analysis = self.sasm.getParameter('analysis')

        if 'guinier' in analysis:
            guinier = analysis['guinier']
            i0 = float(guinier['I0'])
            rg = float(guinier['Rg'])
        else:
            i0 = 0
            rg = 0

        q = self.sasm.q
        i = self.sasm.i
        err = self.sasm.err
        qmin, qmax = self.sasm.getQrange()

        q = q[qmin:qmax]
        i = i[qmin:qmax]
        err = err[qmin:qmax]

        if q[-1]<0.45 and q[-1]>0.15:
            self._showVpMWWarning(False)
        else:
            self._showVpMWWarning(True)

        if i0 > 0:
            analysis = self.sasm.getParameter('analysis')
            guinier_analysis = analysis['guinier']
            qmin = float(guinier_analysis['qStart'])

            mw, pVolume, pv_cor = SASCalc.calcVpMW(q, i, err, rg, i0, qmin)

            self.mws['vp']['mw'] = str(mw)
            self.mws['vp']['pVolume'] = str(pVolume)
            self.mws['vp']['pv_cor'] = str(pv_cor)

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

            mwCtrl = wx.FindWindowById(vp_ids['calc_mw'], self)
            mwCtrl.SetValue(mwstr)

            vpCtrl = wx.FindWindowById(vp_ids['sup_vp'], self)
            vpCtrl.SetValue(pvstr)

            pvcCtrl = wx.FindWindowById(vp_ids['sup_vpc'], self)
            pvcCtrl.SetValue(pvcstr)

        else:
            self.mws['vp']['mw'] = ''
            self.mws['vp']['pVolume'] = ''
            self.mws['vp']['pv_cor'] = ''

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

        if conc > 0 and i0 > 0 and wx.FindWindowById(abs_ids['calib'], self).GetValue():
            mw = SASCalc.calcAbsMW(i0, conc)

            self.mws['abs']['mw'] = str(mw)

            val = round(mw,1)

            if val > 1e3 or val < 1e-2:
                mwstr = '%.2E' %(val)
            else:
                mwstr = '%.1f' %(val)

            mwCtrl = wx.FindWindowById(abs_ids['calc_mw'], self)
            mwCtrl.SetValue(mwstr)

        else:
            self.mws['abs']['mw'] = ''

    def OnClose(self):

        self.Destroy()


class MWPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

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
        self.canvas.SetBackgroundColour('white')
        self.fig.subplots_adjust(left = 0.35, bottom = 0.16, right = 0.95, top = 0.91)
        self.fig.set_facecolor('white')

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

    def _calcInt(self, sasm, interp=True):
        ''' calculate pointwise integral '''

        q = sasm.q
        i = sasm.i
        qmin, qmax = sasm.getQrange()

        q = q[qmin:qmax]
        i = i[qmin:qmax]

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

    def plotSASM(self, sasm):
        try:
            q, intI = self._calcInt(sasm)
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

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'GNOMFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'GNOMFrame', size = (800,600))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.main_frame = parent

        splitter1 = wx.SplitterWindow(self, -1)

        self.plotPanel = GNOMPlotPanel(splitter1, -1, 'GNOMPlotPanel')
        self.controlPanel = GNOMControlPanel(splitter1, -1, 'GNOMControlPanel', sasm, manip_item)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, 290)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(290)    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(50)

        splitter1.Layout()
        self.Layout()
        self.SendSizeEvent()
        splitter1.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)

        self.initGNOM(self.plotPanel, self.controlPanel, sasm)

        self.CenterOnParent()
        self.Raise()

    def initGNOM(self, plotPanel, controlPanel, sasm):

        self.getGnomVersion()

        analysis_dict = sasm.getParameter('analysis')
        if 'GNOM' in analysis_dict:
            iftm = self.controlPanel.initGnomValues(sasm)

        else:
            dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
            path = dirctrl_panel.getDirLabel()

            cwd = os.getcwd()

            savename = 't_dat.dat'

            while os.path.isfile(os.path.join(path, savename)):
                savename = 't'+savename

            save_sasm = SASM.SASM(copy.deepcopy(sasm.i), copy.deepcopy(sasm.q), copy.deepcopy(sasm.err), copy.deepcopy(sasm.getAllParameters()))

            save_sasm.setParameter('filename', savename)

            save_sasm.setQrange(sasm.getQrange())

            if self.main_frame.OnlineControl.isRunning() and path == self.main_frame.OnlineControl.getTargetDir():
                self.main_frame.controlTimer(False)
                restart_timer = True
            else:
                restart_timer = False

            try:
                SASFileIO.saveMeasurement(save_sasm, path, self._raw_settings, filetype = '.dat')
            except SASExceptions.HeaderSaveError as e:
                self._showSaveError('header')

            os.chdir(path)

            try:
                init_iftm = SASCalc.runDatgnom(savename, sasm)
            except SASExceptions.NoATSASError as e:
                wx.CallAfter(wx.MessageBox, str(e), 'Error running GNOM/DATGNOM', style = wx.ICON_ERROR | wx.OK)
                self.cleanupGNOM(path, savename = savename)
                os.chdir(cwd)
                self.onClose()
                return

            os.chdir(cwd)


            if init_iftm == None:
                outname = 't_datgnom.out'
                while os.path.isfile(outname):
                    outname = 't'+outname

                if 'Guinier' in analysis_dict:
                    rg = float(analysis_dict['Guinier']['Rg'])
                    dmax = int(rg*3.) #Mostly arbitrary guess at Dmax

                else:
                    dmax = 80 #Completely arbitrary default setting for Dmax

                os.chdir(path)

                try:
                    init_iftm = SASCalc.runGnom(savename, outname, dmax, self.controlPanel.gnom_settings, new_gnom = self.new_gnom)
                except (SASExceptions.NoATSASError, SASExceptions.GNOMError) as e:
                    wx.CallAfter(wx.MessageBox, str(e), 'Error running GNOM/DATGNOM', style = wx.ICON_ERROR | wx.OK)
                    self.cleanupGNOM(path, savename = savename, outname = outname)
                    self.onClose()
                    os.chdir(cwd)
                    return

                os.chdir(cwd)

                self.cleanupGNOM(path, outname = outname)

            self.cleanupGNOM(path, savename = savename)

            if restart_timer:
                wx.CallAfter(self.main_frame.controlTimer, True)


            iftm = controlPanel.initDatgnomValues(sasm, init_iftm)

        plotPanel.plotPr(iftm)

    def updateGNOMSettings(self):
        self.controlPanel.updateGNOMSettings()

    def cleanupGNOM(self, path, savename = '', outname = ''):
        savefile = os.path.join(path, savename)
        outfile = os.path.join(path, outname)

        if savename != '':
            if os.path.isfile(savefile):
                try:
                    os.remove(savefile)
                except Exception, e:
                    print e
                    print 'GNOM cleanup failed to remove the .dat file!'

        if outname != '':
            if os.path.isfile(outfile):
                try:
                    os.remove(outfile)
                except Exception, e:
                    print e
                    print 'GNOM cleanup failed to remove the .out file!'

    def getGnomVersion(self):
        #Checks if we have gnom4 or gnom5
        raw_settings = wx.FindWindowByName('MainFrame').raw_settings
        atsasDir = raw_settings.get('ATSASDir')

        opsys = platform.system()

        if opsys == 'Windows':
            dammifDir = os.path.join(atsasDir, 'dammif.exe')
        else:
            dammifDir = os.path.join(atsasDir, 'dammif')

        if os.path.exists(dammifDir):
            process=subprocess.Popen('%s -v' %(dammifDir), stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True) #gnom4 doesn't do a proper -v!!! So use something else
            output, error = process.communicate()
            output = output.strip()
            error = error.strip()

            dammif_re = 'ATSAS\s*\d+[.]\d+[.]\d*'
            version_match = re.search(dammif_re, output)
            version = version_match.group().split()[-1]

            if int(version.split('.')[0]) > 2 or (int(version.split('.')[0]) == 2 and int(version.split('.')[1]) >=8):
                self.new_gnom = True
            else:
                self.new_gnom = False

    def OnClose(self):

        self.Destroy()



class GNOMPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.ift = None

        subplotLabels = [('P(r)', 'r', 'P(r)', .1), ('Data/Fit', 'q', 'I(q)', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)

        if self.ift is not None:
            self.canvas.mpl_disconnect(self.cid) #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
            self.updateDataPlot(self.orig_q, self.orig_i, self.orig_err, self.orig_r, self.orig_p, self.orig_perr, self.orig_qexp, self.orig_jreg)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw) #Reconnect draw_event

    def plotPr(self, iftm):
        # xlim = [0, len(sasm.i)]

        # xlim = iftm.getQrange()

        r = iftm.r
        p = iftm.p
        perr = iftm.err

        i = iftm.i_orig
        q = iftm.q_orig
        err = iftm.err_orig

        qexp = q
        jreg = iftm.i_fit

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(q, i, err, r, p, perr, qexp, jreg)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, q, i, err, r, p, perr, qexp, jreg):

        #Save for resizing:
        self.orig_q = q
        self.orig_i = i
        self.orig_err = err
        self.orig_r = r
        self.orig_p = p
        self.orig_perr = perr
        self.orig_qexp = qexp
        self.orig_jreg = jreg

        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']

        if not self.ift:
            self.ift, = a.plot(r, p, 'r.-', animated = True)

            self.zero_line  = a.axhline(color = 'k', animated = True)

            self.data_line, = b.plot(q, i, 'b.', animated = True)
            self.gnom_line, = b.plot(qexp, jreg, 'r', animated = True)

            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)


        else:
            self.ift.set_ydata(p)
            self.ift.set_xdata(r)

            #Error lines:
            self.data_line.set_xdata(q)
            self.data_line.set_ydata(i)
            self.gnom_line.set_xdata(qexp)
            self.gnom_line.set_ydata(jreg)

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()
        b_oldx = b.get_xlim()
        b_oldy = b.get_ylim()

        a.relim()
        a.autoscale_view()

        b.relim()
        b.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()
        b_newx = b.get_xlim()
        b_newy = b.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy or b_newx != b_oldx or b_newy != b_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.background)
        a.draw_artist(self.ift)
        a.draw_artist(self.zero_line)

        #restore white background in error plot and draw new error:
        self.canvas.restore_region(self.err_background)
        b.draw_artist(self.data_line)
        b.draw_artist(self.gnom_line)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)


class GNOMControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, sasm, manip_item):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.sasm = sasm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.old_analysis = {}

        if 'GNOM' in self.sasm.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.sasm.getParameter('analysis')['GNOM'])

        self.gnom_settings = {  'expert'        : self.raw_settings.get('gnomExpertFile'),
                                'rmin_zero'     : self.raw_settings.get('gnomForceRminZero'),
                                'rmax_zero'     : self.raw_settings.get('gnomForceRmaxZero'),
                                'npts'          : self.raw_settings.get('gnomNPoints'),
                                'alpha'         : self.raw_settings.get('gnomInitialAlpha'),
                                'angular'       : self.raw_settings.get('gnomAngularScale'),
                                'system'        : self.raw_settings.get('gnomSystem'),
                                'form'          : self.raw_settings.get('gnomFormFactor'),
                                'radius56'      : self.raw_settings.get('gnomRadius56'),
                                'rmin'          : self.raw_settings.get('gnomRmin'),
                                'fwhm'          : self.raw_settings.get('gnomFWHM'),
                                'ah'            : self.raw_settings.get('gnomAH'),
                                'lh'            : self.raw_settings.get('gnomLH'),
                                'aw'            : self.raw_settings.get('gnomAW'),
                                'lw'            : self.raw_settings.get('gnomLW'),
                                'spot'          : self.raw_settings.get('gnomSpot'),
                                'expt'          : self.raw_settings.get('gnomExpt')
                                }

        self.out_list = {}


        self.spinctrlIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId(),
                            'dmax'   : self.NewControlId()}

        self.staticTxtIDs = {'qstart' : self.NewControlId(),
                            'qend'   : self.NewControlId()}

        self.otherctrlIDs = {'force_dmax'   : self.NewControlId(),
                            }


        self.infodata = {'guinierI0' : ('I0 :', self.NewControlId(), self.NewControlId()),
                         'guinierRg' : ('Rg :', self.NewControlId(), self.NewControlId()),
                         'gnomI0'    : ('I0 :', self.NewControlId(), self.NewControlId()),
                         'gnomRg'    : ('Rg :', self.NewControlId(), self.NewControlId()),
                         'TE': ('Total Estimate :', self.NewControlId()),
                         'gnomQuality': ('GNOM says :', self.NewControlId()),
                         'chisq': ('chi^2 (fit) :', self.NewControlId())
                         }

        self.plotted_iftm = None

        info_button = wx.Button(self, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)


        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,0, wx.LEFT | wx.RIGHT, 5)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1, wx.RIGHT, 5)


        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self.createControls()
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND)


        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self.createInfoBox()
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND)


        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 3)
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 3)
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 3)
        bsizer.AddStretchSpacer(1)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(bsizer)


    def initDatgnomValues(self, sasm, iftm):
        self.setSpinLimits(sasm)

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1], self)
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1], self)

        dmax = int(round(iftm.getParameter('dmax')))

        if dmax != iftm.getParameter('dmax'):
            self.calcGNOM(dmax)
        else:
            self.out_list[str(dmax)] = iftm

        dmaxWindow.SetValue(dmax)

        self.updateGNOMInfo(self.out_list[str(dmax)])

        if 'guinier' in sasm.getParameter('analysis'):

            guinier = sasm.getParameter('analysis')['guinier']

            try:
                guinierRgWindow.SetValue(str(guinier['Rg']))
            except Exception as e:
                print e
                guinierRgWindow.SetValue('')

            try:
                guinierI0Window.SetValue(str(guinier['I0']))
            except Exception as e:
                print e
                guinierI0Window.SetValue('')

        self.setFilename(os.path.basename(sasm.getParameter('filename')))

        return self.out_list[str(dmax)]

    def initGnomValues(self, sasm):

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1], self)
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1], self)

        dmax = sasm.getParameter('analysis')['GNOM']['Dmax']
        qmin = sasm.getParameter('analysis')['GNOM']['qStart']
        qmax = sasm.getParameter('analysis')['GNOM']['qEnd']

        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
        closest_qmin = findClosest(qmin, sasm.q)
        closest_qmax = findClosest(qmax, sasm.q)

        new_nmin = np.where(sasm.q == closest_qmin)[0][0]
        new_nmax = np.where(sasm.q == closest_qmax)[0][0]

        self.startSpin.SetRange((0, len(sasm.q)-1))
        self.endSpin.SetRange((0, len(sasm.q)-1))

        self.endSpin.SetValue(new_nmax)
        self.startSpin.SetValue(new_nmin)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
        txt.SetValue(str(round(sasm.q[new_nmax],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
        txt.SetValue(str(round(sasm.q[new_nmin],4)))

        self.calcGNOM(dmax)

        dmaxWindow.SetValue(dmax)

        self.updateGNOMInfo(self.out_list[str(dmax)])

        if 'guinier' in sasm.getParameter('analysis'):

            guinier = sasm.getParameter('analysis')['guinier']

            try:
                guinierRgWindow.SetValue(str(guinier['Rg']))
            except Exception as e:
                print e
                guinierRgWindow.SetValue('')

            try:
                guinierI0Window.SetValue(str(guinier['I0']))
            except Exception as e:
                print e
                guinierI0Window.SetValue('')

        self.setFilename(os.path.basename(sasm.getParameter('filename')))

        return self.out_list[str(dmax)]



    def updateGNOMInfo(self, iftm):
        gnomRgWindow = wx.FindWindowById(self.infodata['gnomRg'][1], self)
        gnomI0Window = wx.FindWindowById(self.infodata['gnomI0'][1], self)
        gnomTEWindow = wx.FindWindowById(self.infodata['TE'][1], self)
        gnomQualityWindow = wx.FindWindowById(self.infodata['gnomQuality'][1], self)
        gnomChisqWindow = wx.FindWindowById(self.infodata['chisq'][1], self)

        gnomRgWindow.SetValue(str(iftm.getParameter('rg')))
        gnomI0Window.SetValue(str(iftm.getParameter('i0')))
        gnomTEWindow.SetValue(str(iftm.getParameter('TE')))
        gnomChisqWindow.SetValue(str(iftm.getParameter('chisq')))
        gnomQualityWindow.SetValue(str(iftm.getParameter('quality')))


    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def createFileInfo(self):

        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY)

        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND)

        return boxsizer

    def onSaveInfo(self, evt):

        gnom_results = {}

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        dmax = str(dmaxWindow.GetValue())

        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        start_idx = startSpin.GetValue()
        end_idx = endSpin.GetValue()

        gnom_results['Dmax'] = dmax
        gnom_results['Total_Estimate'] = self.out_list[dmax].getParameter('TE')
        gnom_results['Real_Space_Rg'] = self.out_list[dmax].getParameter('rg')
        gnom_results['Real_Space_I0'] = self.out_list[dmax].getParameter('i0')
        gnom_results['qStart'] = self.sasm.q[start_idx]
        gnom_results['qEnd'] = self.sasm.q[end_idx]
        # gnom_results['GNOM_ChiSquared'] = self.out_list[dmax]['chisq']
        # gnom_results['GNOM_Quality_Assessment'] = self.out_list[dmax]['gnomQuality']

        analysis_dict = self.sasm.getParameter('analysis')
        analysis_dict['GNOM'] = gnom_results

        if self.manip_item is not None:
            if gnom_results != self.old_analysis:
                wx.CallAfter(self.manip_item.markAsModified)

        iftm = self.out_list[dmax]
        iftm.setParameter('filename', os.path.splitext(self.sasm.getParameter('filename'))[0]+'.out')

        if self.raw_settings.get('AutoSaveOnGnom'):
            if os.path.isdir(self.raw_settings.get('GnomFilePath')):
                RAWGlobals.mainworker_cmd_queue.put(['save_iftm', [iftm, self.raw_settings.get('GnomFilePath')]])
            else:
                self.raw_settings.set('GnomFilePath', False)
                wx.CallAfter(wx.MessageBox, 'The folder:\n' +self.raw_settings.get('GNOMFilePath')+ '\ncould not be found. Autosave of GNOM files has been disabled. If you are using a config file from a different computer please go into Advanced Options/Autosave to change the save folders, or save you config file to avoid this message next time.', 'Autosave Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

        RAWGlobals.mainworker_cmd_queue.put(['to_plot_ift', [iftm, 'black', None, not self.raw_settings.get('AutoSaveOnGnom')]])


        diag = wx.FindWindowByName('GNOMFrame')
        diag.OnClose()

    def onCloseButton(self, evt):

        diag = wx.FindWindowByName('GNOMFrame')
        diag.OnClose()

    def _onInfoButton(self, evt):
        msg = 'If you use GNOM in your work, in addition to citing the RAW paper please cite the paper given here:\nhttps://www.embl-hamburg.de/biosaxs/gnom.html'
        wx.MessageBox(str(msg), "How to cite GNOM", style = wx.ICON_INFORMATION | wx.OK)

    def onDatgnomButton(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        cwd = os.getcwd()

        savename = 't_dat.dat'

        while os.path.isfile(os.path.join(path, savename)):
            savename = 't'+savename

        save_sasm = SASM.SASM(copy.deepcopy(self.sasm.i), copy.deepcopy(self.sasm.q), copy.deepcopy(self.sasm.err), copy.deepcopy(self.sasm.getAllParameters()))

        save_sasm.setParameter('filename', savename)

        save_sasm.setQrange(self.sasm.getQrange())

        top = wx.FindWindowByName('GNOMFrame')

        if top.main_frame.OnlineControl.isRunning() and path == top.main_frame.OnlineControl.getTargetDir():
            top.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        try:
            SASFileIO.saveMeasurement(save_sasm, path, self.raw_settings, filetype = '.dat')
        except SASExceptions.HeaderSaveError as e:
            self._showSaveError('header')

        os.chdir(path)

        try:
            datgnom = SASCalc.runDatgnom(savename, self.sasm)
        except SASExceptions.NoATSASError as e:
            wx.CallAfter(wx.MessageBox, str(e), 'Error running GNOM/DATGNOM', style = wx.ICON_ERROR | wx.OK)
            top = wx.FindWindowByName('GNOMFrame')
            top.cleanupGNOM(path, savename = savename)
            os.chdir(cwd)
            top.OnClose()
            return

        os.chdir(cwd)

        top.cleanupGNOM(path, savename = savename)

        if restart_timer:
            wx.CallAfter(top.main_frame.controlTimer, True)

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)

        dmax = int(round(datgnom.getParameter('dmax')))

        if dmax != datgnom.getParameter('dmax') and dmax not in self.out_list:
            self.calcGNOM(dmax)
        elif dmax == datgnom.getParameter('dmax') and dmax not in self.out_list:
            self.out_list[str(dmax)] = datgnom

        dmaxWindow.SetValue(dmax)

        self.updateGNOMInfo(self.out_list[str(dmax)])

        self.updatePlot()

    def createInfoBox(self):

        sizer = wx.FlexGridSizer(rows = 3, cols = 3)

        sizer.Add((0,0))

        rglabel = wx.StaticText(self, -1, 'Rg (A)')
        i0label = wx.StaticText(self, -1, 'I0')

        sizer.Add(rglabel, 0, wx.ALL, 5)
        sizer.Add(i0label, 0, wx.ALL, 5)

        guinierlabel = wx.StaticText(self, -1, 'Guinier :')
        self.guinierRg = wx.TextCtrl(self, self.infodata['guinierRg'][1], '0', size = (60,-1), style = wx.TE_READONLY)
        self.guinierI0 = wx.TextCtrl(self, self.infodata['guinierI0'][1], '0', size = (60,-1), style = wx.TE_READONLY)

        sizer.Add(guinierlabel, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.guinierRg, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        sizer.Add(self.guinierI0, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        gnomlabel = wx.StaticText(self, -1, 'P(r) :')
        self.gnomRg = wx.TextCtrl(self, self.infodata['gnomRg'][1], '0', size = (60,-1), style = wx.TE_READONLY)
        self.gnomI0 = wx.TextCtrl(self, self.infodata['gnomI0'][1], '0', size = (60,-1), style = wx.TE_READONLY)

        sizer.Add(gnomlabel, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.gnomRg, 0, wx.ALL, 5)
        sizer.Add(self.gnomI0, 0, wx.ALL, 5)


        teLabel = wx.StaticText(self, -1, self.infodata['TE'][0])
        self.totalEstimate = wx.TextCtrl(self, self.infodata['TE'][1], '0', size = (60,-1), style = wx.TE_READONLY)

        teSizer = wx.BoxSizer(wx.HORIZONTAL)
        teSizer.Add(teLabel, 0, wx.RIGHT, 5)
        teSizer.Add(self.totalEstimate, 0, wx.RIGHT, 5)

        chisqLabel = wx.StaticText(self, -1, self.infodata['chisq'][0])
        self.chisq = wx.TextCtrl(self, self.infodata['chisq'][1], '0', size = (60,-1), style = wx.TE_READONLY)

        chisqSizer = wx.BoxSizer(wx.HORIZONTAL)
        chisqSizer.Add(chisqLabel, 0, wx.RIGHT, 5)
        chisqSizer.Add(self.chisq, 0, wx.RIGHT, 5)

        qualityLabel = wx.StaticText(self, -1, self.infodata['gnomQuality'][0])
        self.quality = wx.TextCtrl(self, self.infodata['gnomQuality'][1], '', style = wx.TE_READONLY)

        qualitySizer = wx.BoxSizer(wx.HORIZONTAL)
        qualitySizer.Add(qualityLabel, 0, wx.RIGHT, 5)
        qualitySizer.Add(self.quality, 1)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer,0)
        top_sizer.Add(teSizer,0, wx.BOTTOM, 5)
        top_sizer.Add(chisqSizer,0, wx.BOTTOM, 5)
        top_sizer.Add(qualitySizer,0, wx.BOTTOM | wx.EXPAND, 5)

        return top_sizer

    def createControls(self):

        sizer = wx.FlexGridSizer(rows = 2, cols = 4)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableCol(2)
        sizer.AddGrowableCol(3)

        sizer.Add(wx.StaticText(self,-1,'q_min'),1, wx.LEFT, 3)
        sizer.Add(wx.StaticText(self,-1,'n_min'),1)
        sizer.Add(wx.StaticText(self,-1,'q_max'),1)
        sizer.Add(wx.StaticText(self,-1,'n_max'),1)

        self.startSpin = RAWCustomCtrl.IntSpinCtrl(self, self.spinctrlIDs['qstart'], size = (60,-1), min =0)
        self.endSpin = RAWCustomCtrl.IntSpinCtrl(self, self.spinctrlIDs['qend'], size = (60,-1), min = 0)

        self.startSpin.SetValue(0)
        self.endSpin.SetValue(0)

        self.startSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.endSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)

        self.qstartTxt = wx.TextCtrl(self, self.staticTxtIDs['qstart'], 'q: ', size = (55, 22), style = wx.PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(self, self.staticTxtIDs['qend'], 'q: ', size = (55, 22), style = wx.PROCESS_ENTER)

        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)

        sizer.Add(self.qstartTxt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 3)
        sizer.Add(self.startSpin, 0, wx.EXPAND | wx.RIGHT, 3)
        sizer.Add(self.qendTxt, 0, wx.EXPAND | wx.RIGHT, 3)
        sizer.Add(self.endSpin, 0, wx.EXPAND | wx.RIGHT, 3)


        dmax_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.dmaxSpin = RAWCustomCtrl.IntSpinCtrl(self, self.spinctrlIDs['dmax'], size = (60,-1), min = 1)

        self.dmaxSpin.SetValue(0)
        self.dmaxSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.dmaxSpin.Bind(wx.EVT_TEXT, self.onDmaxText)

        dmax_sizer.Add(wx.StaticText(self, -1, 'Dmax: '), 0, wx.LEFT, 3)
        dmax_sizer.Add(self.dmaxSpin, 0, wx.EXPAND | wx.RIGHT, 3)

        rmax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rmax_text = wx.StaticText(self, -1, 'Force to 0 at Dmax: ')
        rmax_choice = wx.Choice(self, self.otherctrlIDs['force_dmax'], choices = ['Y', 'N'])
        rmax_choice.SetStringSelection(self.gnom_settings['rmax_zero'])
        rmax_choice.Bind(wx.EVT_CHOICE, self.onSettingsChange)
        rmax_sizer.Add(rmax_text, 0, wx.LEFT, 3)
        rmax_sizer.Add(rmax_choice, 0, wx.RIGHT, 3)


        advancedParams = wx.Button(self, -1, 'Change Advanced Parameters')
        advancedParams.Bind(wx.EVT_BUTTON, self.onChangeParams)

        datgnom = wx.Button(self, -1, 'DATGNOM')
        datgnom.Bind(wx.EVT_BUTTON, self.onDatgnomButton)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer, 0, wx.EXPAND)
        top_sizer.Add(dmax_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM , 5)
        top_sizer.Add(rmax_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        top_sizer.Add(advancedParams, 0, wx.CENTER | wx.BOTTOM, 10)
        top_sizer.Add(datgnom, 0, wx.CENTER)


        return top_sizer

    def onDmaxText(self,evt):
        self.dmaxSpin.Unbind(wx.EVT_TEXT) #Avoid infinite recursion

        dmax = str(self.dmaxSpin.GetValue())
        dmax = float(dmax.replace(',', '.'))
        self.dmaxSpin.SetValue(int(dmax))

        self.dmaxSpin.Bind(wx.EVT_TEXT, self.onDmaxText)

    def onEnterInQlimits(self, evt):

        id = evt.GetId()

        lx = self.sasm.q

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
                txt.SetValue(str(round(self.sasm.q[idx],5)))
                return

            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'], self)
                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.sasm.q[idx],5)))
                return
        #################################

        closest = findClosest(val,lx)

        i = np.where(lx == closest)[0][0]

        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)

        if id == self.staticTxtIDs['qstart']:

            max = endSpin.GetValue()

            if i > max-3:
                i = max - 3

            startSpin.SetValue(i)

        elif id == self.staticTxtIDs['qend']:
            minq = startSpin.GetValue()


            if i < minq+3:
                i = minq + 3

            endSpin.SetValue(i)

        txtctrl.SetValue(str(round(self.sasm.q[int(i)],5)))


        self.out_list = {}

        wx.CallAfter(self.updatePlot)

    def setSpinLimits(self, sasm):
        self.startSpin.SetRange((0, len(sasm.q)-1))
        self.endSpin.SetRange((0, len(sasm.q)-1))

        self.endSpin.SetValue(len(sasm.q)-1)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)
        txt.SetValue(str(round(sasm.q[int(len(sasm.q)-1)],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)
        txt.SetValue(str(round(sasm.q[0],4)))


    def onSpinCtrl(self, evt):

        id = evt.GetId()

        if id != self.spinctrlIDs['dmax']:
            spin = wx.FindWindowById(id, self)

            startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
            endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)

            i = spin.GetValue()

            #Make sure the boundaries don't cross:
            if id == self.spinctrlIDs['qstart']:
                max = endSpin.GetValue()
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'], self)

                if i > max-3:
                    i = max - 3
                    spin.SetValue(i)

            elif id == self.spinctrlIDs['qend']:
                min = startSpin.GetValue()
                txt = wx.FindWindowById(self.staticTxtIDs['qend'], self)

                if i < min+3:
                    i = min + 3
                    spin.SetValue(i)

            txt.SetValue(str(round(self.sasm.q[int(i)],5)))

            self.out_list = {}

        #Important, since it's a slow function to update (could do it in a timer instead) otherwise this spin event might loop!
        wx.CallAfter(self.updatePlot)


    def updatePlot(self):
        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        dmax = dmaxWindow.GetValue()

        if dmax not in self.out_list:
            self.calcGNOM(dmax)

        self.updateGNOMInfo(self.out_list[str(dmax)])

        plotpanel = wx.FindWindowByName('GNOMPlotPanel')

        dmax_window = wx.FindWindowById(self.spinctrlIDs['dmax'], self)
        dmax = str(dmax_window.GetValue())

        a = plotpanel.subplots['P(r)']
        b = plotpanel.subplots['Data/Fit']
        if not a.get_autoscale_on():
            a.set_autoscale_on(True)
        if not b.get_autoscale_on():
            b.set_autoscale_on(True)

        plotpanel.plotPr(self.out_list[dmax])


    def calcGNOM(self, dmax):
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'], self)
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'], self)

        start = int(startSpin.GetValue())
        end = int(endSpin.GetValue())

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        cwd = os.getcwd()

        savename = 't_dat.dat'

        while os.path.isfile(os.path.join(path, savename)):
            savename = 't'+savename

        outname = 't_out.out'
        while os.path.isfile(os.path.join(path, outname)):
            outname = 't'+outname

        save_sasm = SASM.SASM(copy.deepcopy(self.sasm.i), copy.deepcopy(self.sasm.q), copy.deepcopy(self.sasm.err), copy.deepcopy(self.sasm.getAllParameters()))

        save_sasm.setParameter('filename', savename)
        save_sasm.setQrange((start, end))


        top = wx.FindWindowByName('GNOMFrame')

        if top.main_frame.OnlineControl.isRunning() and path == top.main_frame.OnlineControl.getTargetDir():
            top.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        try:
            SASFileIO.saveMeasurement(save_sasm, path, self.raw_settings, filetype = '.dat')
        except SASExceptions.HeaderSaveError as e:
            self._showSaveError('header')


        os.chdir(path)
        try:
            iftm = SASCalc.runGnom(savename, outname, dmax, self.gnom_settings, new_gnom = top.new_gnom)
        except (SASExceptions.NoATSASError, SASExceptions.GNOMError) as e:
            wx.CallAfter(wx.MessageBox, str(e), 'Error running GNOM/DATGNOM', style = wx.ICON_ERROR | wx.OK)
            top = wx.FindWindowByName('GNOMFrame')
            top.cleanupGNOM(path, savename, outname)
            os.chdir(cwd)
            top.OnClose()
            return

        os.chdir(cwd)

        top.cleanupGNOM(path, savename, outname)

        if restart_timer:
            wx.CallAfter(top.main_frame.controlTimer, True)

        self.out_list[str(int(iftm.getParameter('dmax')))] = iftm


    def onSettingsChange(self, evt):
        self.updateGNOMSettings()


    def updateGNOMSettings(self):
        self.old_settings = copy.deepcopy(self.gnom_settings)

        self.gnom_settings = {  'expert'        : self.raw_settings.get('gnomExpertFile'),
                                'rmin_zero'     : self.raw_settings.get('gnomForceRminZero'),
                                'rmax_zero'     : wx.FindWindowById(self.otherctrlIDs['force_dmax']).GetStringSelection(),
                                'npts'          : self.raw_settings.get('gnomNPoints'),
                                'alpha'         : self.raw_settings.get('gnomInitialAlpha'),
                                'angular'       : self.raw_settings.get('gnomAngularScale'),
                                'system'        : self.raw_settings.get('gnomSystem'),
                                'form'          : self.raw_settings.get('gnomFormFactor'),
                                'radius56'      : self.raw_settings.get('gnomRadius56'),
                                'rmin'          : self.raw_settings.get('gnomRmin'),
                                'fwhm'          : self.raw_settings.get('gnomFWHM'),
                                'ah'            : self.raw_settings.get('gnomAH'),
                                'lh'            : self.raw_settings.get('gnomLH'),
                                'aw'            : self.raw_settings.get('gnomAW'),
                                'lw'            : self.raw_settings.get('gnomLW'),
                                'spot'          : self.raw_settings.get('gnomSpot'),
                                'expt'          : self.raw_settings.get('gnomExpt')
                                }

        if self.old_settings != self.gnom_settings:
            self.out_list = {}

        self.updatePlot()


    def onChangeParams(self, evt):
        self.main_frame.showOptionsDialog(focusHead='GNOM')


class DammifFrame(wx.Frame):

    def __init__(self, parent, title, iftm, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'DammifFrame', size = (675,750))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'DammifFrame', size = (675,750))

        self.manip_item = manip_item
        self.iftm = iftm
        self.ift = iftm.getParameter('out')
        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.panel = wx.Panel(self)
        self.notebook = wx.Notebook(self.panel, wx.ID_ANY)
        self.RunPanel = DammifRunPanel(self.notebook, self.iftm, self.manip_item)
        self.ResultsPanel = DammifResultsPanel(self.notebook, self.iftm, self.manip_item)
        self.ViewerPanel = DammifViewerPanel(self.notebook)

        self.notebook.AddPage(self.RunPanel, 'Run')
        self.notebook.AddPage(self.ResultsPanel, 'Results')
        self.notebook.AddPage(self.ViewerPanel, 'Viewer')

        sizer = self._createLayout(self.panel)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.notebook, 1, wx.EXPAND)
        top_sizer.Add(sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

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
                size[1] = size[1] + 20
                self.SetSize(size)

        self.CenterOnParent()

        self.Raise()

    def _createLayout(self, parent):
        close_button = wx.Button(parent, -1, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer =  wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(info_button, 0, wx.RIGHT, 5)
        button_sizer.Add(close_button, 0)

        return button_sizer

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
        'If you use AMBIMETER in your work please cite:\n'
        'Petoukhov, M. V. & Svergun, D. I. (2015). Acta Cryst. D71, 1051-1058.\n\n'
        'If you use SASRES in your work please cite the paper given here:\n'
        'https://www.embl-hamburg.de/biosaxs/manuals/sasres.html')
        wx.MessageBox(str(msg), "How to cite AMBIMETER/DAMMIF/DAMMIN/DAMAVER/DAMCLUST/SASRES", style = wx.ICON_INFORMATION | wx.OK)


    def OnClose(self, event):
        dammifrun = wx.FindWindowByName('DammifRunPanel')
        dammifrun.Close(event)

        if event.GetVeto():
            return
        else:
            self.Destroy()


class DammifRunPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DammifRunPanel')
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY, name = 'DammifRunPanel')

        self.parent = parent

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')

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
                    }

        self.threads = []

        topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(topsizer)

    def _createLayout(self, parent):

        file_ctrl = wx.TextCtrl(parent, self.ids['fname'], self.filename, size = (150, -1), style = wx.TE_READONLY)

        file_box = wx.StaticBox(parent, -1, 'Filename')
        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        file_sizer.Add(file_ctrl, 2, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        file_sizer.AddStretchSpacer(1)

        savedir_text = wx.StaticText(parent, -1, 'Output directory :')
        savedir_ctrl = wx.TextCtrl(parent, self.ids['save'], '', size = (350, -1))

        try:
            savedir_ctrl.AutoCompleteDirectories() #compatability for older versions of wxpython
        except AttributeError as e:
            print e

        savedir_button = wx.Button(parent, self.ids['changedir'], 'Select/Change Directory')
        savedir_button.Bind(wx.EVT_BUTTON, self.onChangeDirectoryButton)

        savedir_sizer = wx.BoxSizer(wx.VERTICAL)
        savedir_sizer.Add(savedir_text, 0, wx.LEFT | wx.RIGHT, 5)
        savedir_sizer.Add(savedir_ctrl, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND, 5)
        savedir_sizer.Add(savedir_button, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 5)


        prefix_text = wx.StaticText(parent, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(parent, self.ids['prefix'], '', size = (150, -1))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.LEFT, 5)
        prefix_sizer.Add(prefix_ctrl, 1, wx.LEFT | wx.RIGHT, 5)
        prefix_sizer.AddStretchSpacer(1)


        nruns_text = wx.StaticText(parent, -1, 'Number of reconstructions :')
        nruns_ctrl = wx.TextCtrl(parent, self.ids['runs'], '', size = (60, -1))
        nruns_ctrl.Bind(wx.EVT_TEXT, self.onRunsText)

        nruns_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nruns_sizer.Add(nruns_text, 0, wx.LEFT, 5)
        nruns_sizer.Add(nruns_ctrl, 0, wx.LEFT | wx.RIGHT, 5)


        nprocs = multiprocessing.cpu_count()
        nprocs_choices = [str(i) for i in range(nprocs, 0, -1)]
        nprocs_text = wx.StaticText(parent, -1, 'Number of simultaneous runs :')
        nprocs_choice = wx.Choice(parent, self.ids['procs'], choices = nprocs_choices)

        nprocs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nprocs_sizer.Add(nprocs_text, 0, wx.LEFT, 5)
        nprocs_sizer.Add(nprocs_choice, 0, wx.LEFT | wx.RIGHT, 5)


        program_text = wx.StaticText(parent, -1, 'Use :')
        program_choice = wx.Choice(parent, self.ids['program'], choices = ['DAMMIF', 'DAMMIN'])


        mode_text = wx.StaticText(parent, -1, 'Mode :')
        mode_choice = wx.Choice(parent, self.ids['mode'], choices = ['Fast', 'Slow', 'Custom'])


        sym_choices = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 'P11',
                        'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18', 'P19', 'P22', 'P222',
                        'P32', 'P42', 'P52', 'P62', 'P72', 'P82', 'P92', 'P102', 'P112', 'P122']

        sym_text = wx.StaticText(parent, -1, 'Symmetry :')
        sym_choice = wx.Choice(parent, self.ids['sym'], choices = sym_choices)


        anisometry_choices = ['Unknown', 'Prolate', 'Oblate']
        aniso_text = wx.StaticText(parent, -1, 'Anisometry :')
        aniso_choice = wx.Choice(parent, self.ids['anisometry'], choices = anisometry_choices)


        choices_sizer = wx.FlexGridSizer(2, 4, 5, 5)
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

        damaver_chk = wx.CheckBox(parent, self.ids['damaver'], 'Align and average envelopes (damaver)')
        damaver_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        refine_chk = wx.CheckBox(parent, self.ids['refine'], 'Refine average with dammin')
        refine_sizer = wx.BoxSizer(wx.HORIZONTAL)
        refine_sizer.AddSpacer(20)
        refine_sizer.Add(refine_chk)

        damclust_chk = wx.CheckBox(parent, self.ids['damclust'], 'Align and cluster envelopes (damclust)')
        damclust_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        advancedButton = wx.Button(parent, -1, 'Change Advanced Settings')
        advancedButton.Bind(wx.EVT_BUTTON, self._onAdvancedButton)


        settings_box = wx.StaticBox(parent, -1, 'Settings')
        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        # settings_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND | wx.TOP, 5)
        settings_sizer.Add(nruns_sizer, 0, wx.TOP, 5)
        settings_sizer.Add(nprocs_sizer, 0, wx.TOP, 5)
        # settings_sizer.Add(mode_sizer, 0)
        # settings_sizer.Add(sym_sizer, 0)
        # settings_sizer.Add(aniso_sizer, 0)
        settings_sizer.Add(choices_sizer, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 5)
        settings_sizer.Add(damaver_chk, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        settings_sizer.Add(refine_sizer, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        settings_sizer.Add(damclust_chk, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        settings_sizer.Add(advancedButton, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 5)


        start_button = wx.Button(parent, self.ids['start'], 'Start')
        start_button.Bind(wx.EVT_BUTTON, self.onStartButton)

        abort_button = wx.Button(parent, self.ids['abort'], 'Abort')
        abort_button.Bind(wx.EVT_BUTTON, self.onAbortButton)

        button_box = wx.StaticBox(parent, -1, 'Controls')
        button_sizer = wx.StaticBoxSizer(button_box, wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        button_sizer.Add(abort_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        button_sizer.AddStretchSpacer(1)

        control_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer.Add(file_sizer, 0, wx.EXPAND)
        control_sizer.Add(settings_sizer, 0, wx.EXPAND)
        control_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.EXPAND)


        self.status = wx.TextCtrl(parent, self.ids['status'], '', style = wx.TE_MULTILINE | wx.TE_READONLY, size = (100,200))
        status_box = wx.StaticBox(parent, -1, 'Status')
        status_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)
        status_sizer.Add(self.status, 1, wx.EXPAND | wx.ALL, 5)


        half_sizer = wx.BoxSizer(wx.HORIZONTAL)
        half_sizer.Add(control_sizer, 2, wx.EXPAND)
        half_sizer.Add(status_sizer, 1, wx.EXPAND)


        try:
            self.logbook = flatNB.FlatNotebook(parent, self.ids['logbook'], agwStyle = flatNB.FNB_NAV_BUTTONS_WHEN_NEEDED | flatNB.FNB_NO_X_BUTTON)
        except AttributeError as e:
            print e
            self.logbook = flatNB.FlatNotebook(parent, self.ids['logbook'])     #compatability for older versions of wxpython
            self.logbook.SetWindowStyleFlag(flatNB.FNB_NO_X_BUTTON)

        self.logbook.DeleteAllPages()

        log_box = wx.StaticBox(parent, -1, 'Log')
        log_sizer = wx.StaticBoxSizer(log_box, wx.HORIZONTAL)
        log_sizer.Add(self.logbook, 1, wx.ALL | wx.EXPAND, 5)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:     #compatability for older versions of wxpython
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
                                'annealSched'       : self.raw_settings.get('damminAnealSched')
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

        outname = os.path.join(path, prefix+'.out')


        #Check to see if any files will be overwritten. Prompt use if that is the case. Write the .out file for dammif to use
        if os.path.exists(outname):
            existingOut = SASFileIO.loadOutFile(outname)[0].getParameter('out')
            if existingOut != self.ift:

                msg = "Warning: the file %s already exists in the specified directory, and is not identical to the P(r) dammif will use. To continue, RAW must overwrite this file. Do you wish to continue?" %(prefix+'.out')
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
            EnvelopeName = os.path.join(path, dammif_names[key]+'-1.pdb')
            SolventName = os.path.join(path, dammif_names[key]+'-0.pdb')

            if (os.path.exists(LogName) or os.path.exists(InName) or os.path.exists(FitName) or os.path.exists(FirName) or os.path.exists(EnvelopeName) or os.path.exists(SolventName)) and not yes_to_all:
                button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                question = 'Warning: selected directory contains DAMMIF/N output files with the prefix:\n"%s".\nRunning DAMMIF/N will overwrite these files.\nDo you wish to continue?' %(dammif_names[key])
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, style = wx.CAPTION | wx.RESIZE_BORDER)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True

        #Set up the various bits of information the threads will need. Set up the status windows.
        self.dammif_ids = {key: value for (key, value) in [(str(i), self.NewControlId()) for i in range(1, nruns+1)]}

        self.thread_nums = Queue.Queue()

        self.logbook.DeleteAllPages()

        for i in range(1, nruns+1):
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids[str(i)], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, str(i))
            self.thread_nums.put(str(i))

        if nruns > 1 and damaver:

            damaver_names = [prefix+'_damfilt.pdb', prefix+'_damsel.log', prefix+'_damstart.pdb', prefix+'_damsup.log',
                        prefix+'_damaver.pdb', 'damfilt.pdb', 'damsel.log', 'damstart.pdb', 'damsup.log', 'damaver.pdb']

            for item in damaver_names:

                if os.path.exists(os.path.join(path, item)) and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                    question = 'Warning: selected directory contains the DAMAVER output file\n"%s". Running DAMAVER will overwrite this file.\nDo you wish to continue?' %(item)
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, style = wx.CAPTION | wx.RESIZE_BORDER)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['damaver'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['damaver'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Damaver')


        elif nruns > 1 and damclust:

            damclust_names = [prefix+'_damclust.log']

            for item in damclust_names:

                if os.path.exists(os.path.join(path, item)) and not yes_to_all:
                    button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                    question = 'Warning: selected directory contains the DAMCLUST output file\n"%s". Running DAMCLUST will overwrite this file.\nDo you wish to continue?' %(item)
                    label = 'Overwrite existing files?'
                    icon = wx.ART_WARNING

                    question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, style = wx.CAPTION | wx.RESIZE_BORDER)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['damclust'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['damclust'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Damclust')

        if nruns > 1 and refine:
            self.dammif_ids['refine'] = self.NewControlId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['refine'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Refine')


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

        self.rs = Queue.Queue()

        for key in self.dammif_ids:
            if key != 'damaver' and key != 'damclust' and key != 'refine':
                t = threading.Thread(target = self.runDammif, args = (outname, prefix, path, program))
                t.daemon = True
                t.start()
                self.threads.append(t)

        self.dammif_timer.Start(1000)


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


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save'], self).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)

        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save'], self).SetValue(new_path)


    def onRunsText(self, evt):
        nruns_ctrl = wx.FindWindowById(self.ids['runs'], self)


        nruns = nruns_ctrl.GetValue()
        if nruns != '' and not nruns.isdigit():

            try:
                nruns = float(nruns.replace(',', '.'))
            except ValueError as e:
                print e
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
            old_files = [os.path.join(path, dam_prefix+'.log'), os.path.join(path, dam_prefix+'.in'),
                        os.path.join(path, dam_prefix+'.fit'), os.path.join(path, dam_prefix+'.fir'),
                        os.path.join(path, dam_prefix+'-1.pdb'), os.path.join(path, dam_prefix+'-0.pdb')]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            #Run DAMMIF
            dam_args = self.dammif_settings

            if refine:
                self.dammif_settings['mode'] = 'Refine'
                self.dammif_settings['initialDAM'] = prefix+'_damstart.pdb'

            if refine:
                wx.CallAfter(self.status.AppendText, 'Starting Refinement\n')
            else:
                wx.CallAfter(self.status.AppendText, 'Starting %s run %s\n' %(program, my_num))

            cwd = os.getcwd()
            os.chdir(path)

            if refine:
                program = 'DAMMIN'

            if program == 'DAMMIF':
                dammif_proc = SASCalc.runDammif(outname, dam_prefix, dam_args)
            else:
                dammif_proc = SASCalc.runDammin(outname, dam_prefix, dam_args)

            os.chdir(cwd)

            logname = os.path.join(path,dam_prefix)+'.log'

            while not os.path.exists(logname):
                time.sleep(0.01)

            pos = 0

            #Send the DAMMIF log output to the screen.
            while dammif_proc.poll() == None:
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

            if refine:
                wx.CallAfter(self.status.AppendText, 'Finished Refinement\n')
                self.finishedProcessing()
            else:
                wx.CallAfter(self.status.AppendText, 'Finished %s run %s\n' %(program, my_num))


    def runDamaver(self, prefix, path):

        read_semaphore = threading.BoundedSemaphore(1)
        #Solution for non-blocking reads adapted from stack overflow
        #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
        def enqueue_output(out, queue):
            with read_semaphore:
                line = 'test'
                line2=''
                while line != '':
                    line = out.read(1)
                    line2+=line
                    if line == '\n':
                        queue.put_nowait([line2])
                        line2=''
                    time.sleep(0.00001)


        with self.my_semaphore:
            #Check to see if things have been aborted
            damId = self.dammif_ids['damaver']
            damWindow = wx.FindWindowById(damId, self)

            if self.abort_event.isSet():
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return

            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, prefix+'_damfilt.pdb'), os.path.join(path, prefix+'_damsel.log'),
                        os.path.join(path, prefix+'_damstart.pdb'), os.path.join(path, prefix+'_damsup.log'),
                        os.path.join(path, prefix+'_damaver.pdb'), os.path.join(path, 'damfilt.pdb'),
                        os.path.join(path, 'damsel.log'), os.path.join(path, 'damstart.pdb'),
                        os.path.join(path, 'damsup.log'), os.path.join(path, 'damaver.pdb')]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            wx.CallAfter(self.status.AppendText, 'Starting DAMAVER\n')


            nruns_window = wx.FindWindowById(self.ids['runs'], self)
            nruns = int(nruns_window.GetValue())

            dam_filelist = [prefix+'_%s-1.pdb' %(str(i).zfill(2)) for i in range(1, nruns+1)]


            cwd = os.getcwd()
            os.chdir(path)

            damaver_proc = SASCalc.runDamaver(dam_filelist)

            os.chdir(cwd)


            damaver_q = Queue.Queue()
            readout_t = threading.Thread(target=enqueue_output, args=(damaver_proc.stdout, damaver_q))
            readout_t.daemon = True
            readout_t.start()


            #Send the damaver output to the screen.
            while damaver_proc.poll() == None:
                if self.abort_event.isSet():
                    damaver_proc.terminate()
                    wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                    return

                try:
                    new_text = damaver_q.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(damWindow.AppendText, new_text)
                except Queue.Empty:
                    pass
                time.sleep(0.001)

            time.sleep(2)
            with read_semaphore: #see if there's any last data that we missed
                try:
                    new_text = damaver_q.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(damWindow.AppendText, new_text)
                except Queue.Empty:
                    pass


            new_files = [(os.path.join(path, 'damfilt.pdb'), os.path.join(path, prefix+'_damfilt.pdb')),
                        (os.path.join(path, 'damsel.log'), os.path.join(path, prefix+'_damsel.log')),
                        (os.path.join(path, 'damstart.pdb'), os.path.join(path, prefix+'_damstart.pdb')),
                        (os.path.join(path, 'damsup.log'), os.path.join(path, prefix+'_damsup.log')),
                        (os.path.join(path, 'damaver.pdb'), os.path.join(path, prefix+'_damaver.pdb'))]

            for item in new_files:
                os.rename(item[0], item[1])


            wx.CallAfter(self.status.AppendText, 'Finished DAMAVER\n')

            refine_window = wx.FindWindowById(self.ids['refine'], self)
            refine = refine_window.GetValue()

            if refine:
                program_window = wx.FindWindowById(self.ids['program'], self)
                program = program_window.GetStringSelection()

                outname = os.path.join(path, prefix+'.out')

                t = threading.Thread(target = self.runDammif, args = (outname, prefix, path, program, refine))
                t.daemon = True
                t.start()
                self.threads.append(t)
            else:
                self.finishedProcessing()


    def runDamclust(self, prefix, path):

        read_semaphore = threading.BoundedSemaphore(1)
        #Solution for non-blocking reads adapted from stack overflow
        #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
        def enqueue_output(out, queue):
            with read_semaphore:
                line = 'test'
                line2=''
                while line != '':
                    line = out.read(1)
                    line2+=line
                    if line == '\n':
                        queue.put_nowait([line2])
                        line2=''
                    time.sleep(0.00001)


        with self.my_semaphore:
            #Check to see if things have been aborted
            damId = self.dammif_ids['damclust']
            damWindow = wx.FindWindowById(damId, self)

            if self.abort_event.isSet():
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return

            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, prefix+'_damclust.log')]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            wx.CallAfter(self.status.AppendText, 'Starting DAMCLUST\n')


            nruns_window = wx.FindWindowById(self.ids['runs'], self)
            nruns = int(nruns_window.GetValue())

            dam_filelist = [prefix+'_%s-1.pdb' %(str(i).zfill(2)) for i in range(1, nruns+1)]


            cwd = os.getcwd()
            os.chdir(path)

            damclust_proc = SASCalc.runDamclust(dam_filelist)

            os.chdir(cwd)


            damclust_q = Queue.Queue()
            readout_t = threading.Thread(target=enqueue_output, args=(damclust_proc.stdout, damclust_q))
            readout_t.daemon = True
            readout_t.start()


            #Send the damclust output to the screen.
            while damclust_proc.poll() == None:
                if self.abort_event.isSet():
                    damclust_proc.terminate()
                    wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                    return

                try:
                    new_text = damclust_q.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(damWindow.AppendText, new_text)
                except Queue.Empty:
                    pass
                time.sleep(0.001)

            time.sleep(2)
            with read_semaphore: #see if there's any last data that we missed
                try:
                    new_text = damclust_q.get_nowait()
                    new_text = new_text[0]

                    wx.CallAfter(damWindow.AppendText, new_text)
                except Queue.Empty:
                    pass


            new_files = [(os.path.join(path, 'damclust.log'), os.path.join(path, prefix+'_damclust.log'))]

            for item in new_files:
                os.rename(item[0], item[1])

            wx.CallAfter(self.status.AppendText, 'Finished DAMCLUST\n')

            self.finishedProcessing()


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


                t = threading.Thread(target = self.runDamaver, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            elif 'damclust' in self.dammif_ids:
                path_window = wx.FindWindowById(self.ids['save'], self)
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'], self)
                prefix = prefix_window.GetValue()


                t = threading.Thread(target = self.runDamclust, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            else:
                self.finishedProcessing()


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

        results_window = wx.FindWindowByName('DammifResultsPanel')
        wx.CallAfter(results_window.updateResults, settings)

        self.parent.SetSelection(1)

    def _onAdvancedButton(self, evt):
        self.main_frame.showOptionsDialog(focusHead='DAMMIF/N')

    def onCheckBox(self,evt):
        refine = wx.FindWindowById(self.ids['refine'], self)

        if evt.GetId() == self.ids['damaver'] and evt.IsChecked():
            damclust = wx.FindWindowById(self.ids['damclust'], self)
            damclust.SetValue(False)

            if not refine.IsEnabled():
                refine.Enable()
                refine.SetValue(self.raw_settings.get('dammifRefine'))

        elif evt.GetId() == self.ids['damaver'] and not evt.IsChecked():
            if refine.IsEnabled():
                refine.Disable()
                refine.SetValue(False)

        elif evt.GetId() == self.ids['damclust'] and evt.IsChecked():
            damaver = wx.FindWindowById(self.ids['damaver'], self)
            damaver.SetValue(False)

            if refine.IsEnabled():
                refine.Disable()
                refine.SetValue(False)


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
                                'annealSched'       : self.raw_settings.get('damminAnealSched')
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
            msg = "Warning: DAMMIF/N, DAMAVER, or DAMCLUST is still running. Closing this window will abort the currently running processes. Do you want to continue closing the window?"
            dlg = wx.MessageDialog(self.main_frame, msg, "Abort DAMMIF/DAMMIN/DAMAVER/DAMCLUST?", style = wx.ICON_WARNING | wx.YES_NO)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            if proceed == wx.ID_YES:
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

            else:
                event.Veto()

        elif not process_finished:
            #Try to gracefully exit
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

class DammifResultsPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DammifResultsPanel')
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY, name = 'DammifResultsPanel')

        self.parent = parent

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

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
                    'res'           : self.NewControlId(),
                    'resErr'        : self.NewControlId(),
                    'resUnit'       : self.NewControlId(),
                    }

        self.topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(self.topsizer)

    def _createLayout(self, parent):
        ambi_box = wx.StaticBox(parent, wx.ID_ANY, 'Ambimeter')
        self.ambi_sizer = wx.StaticBoxSizer(ambi_box, wx.VERTICAL)

        match_text = wx.StaticText(parent, wx.ID_ANY, 'Compatible shape categories:')
        match_ctrl = wx.TextCtrl(parent, self.ids['ambiCats'], '', size=(60,-1), style=wx.TE_READONLY)

        score_text = wx.StaticText(parent, -1, 'Ambiguity score:')
        score_ctrl = wx.TextCtrl(parent, self.ids['ambiScore'], '', size = (60, -1), style = wx.TE_READONLY)

        eval_text = wx.StaticText(parent, -1, 'AMBIMETER says:')
        eval_ctrl = wx.TextCtrl(parent, self.ids['ambiEval'], '', size = (300, -1), style = wx.TE_READONLY)

        ambi_subsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer1.Add(match_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer1.Add(match_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        ambi_subsizer1.Add(score_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        ambi_subsizer1.Add(score_ctrl, 0, wx.LEFT| wx.ALIGN_CENTER_VERTICAL, 2)

        ambi_subsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer2.Add(eval_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer2.Add(eval_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.ambi_sizer.Add(ambi_subsizer1, 0)
        self.ambi_sizer.Add(ambi_subsizer2, 0, wx.TOP, 5)


        nsd_box = wx.StaticBox(parent, wx.ID_ANY, 'Normalized Spatial Discrepancy')
        self.nsd_sizer = wx.StaticBoxSizer(nsd_box, wx.HORIZONTAL)

        mean_text = wx.StaticText(parent, wx.ID_ANY, 'Mean NSD:')
        mean_ctrl = wx.TextCtrl(parent, self.ids['nsdMean'], '', size=(60,-1), style=wx.TE_READONLY)

        stdev_text = wx.StaticText(parent, wx.ID_ANY, 'Stdev. NSD:')
        stdev_ctrl = wx.TextCtrl(parent, self.ids['nsdStdev'], '', size=(60,-1), style=wx.TE_READONLY)

        inc_text = wx.StaticText(parent, wx.ID_ANY, 'DAMAVER included:')
        inc_ctrl = wx.TextCtrl(parent, self.ids['nsdInc'], '', size=(60,-1), style=wx.TE_READONLY)
        inc_text2 = wx.StaticText(parent, wx.ID_ANY, 'of')
        total_ctrl = wx.TextCtrl(parent, self.ids['nsdTot'], '', size=(60,-1), style=wx.TE_READONLY)

        self.nsd_sizer.Add(mean_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.nsd_sizer.Add(mean_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(stdev_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        self.nsd_sizer.Add(stdev_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(inc_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        self.nsd_sizer.Add(inc_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(inc_text2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(total_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)


        res_box = wx.StaticBox(parent, wx.ID_ANY, 'Reconstruction Resolution (SASRES)')
        self.res_sizer = wx.StaticBoxSizer(res_box, wx.HORIZONTAL)

        res_text = wx.StaticText(parent, wx.ID_ANY, 'Ensemble Resolution:')
        res_ctrl = wx.TextCtrl(parent, self.ids['res'], '', size=(60,-1), style=wx.TE_READONLY)

        reserr_text = wx.StaticText(parent, wx.ID_ANY, '+/-')
        reserr_ctrl = wx.TextCtrl(parent, self.ids['resErr'], '', size=(60,-1), style=wx.TE_READONLY)

        resunit_ctrl = wx.TextCtrl(parent, self.ids['resUnit'], '', size=(100,-1), style=wx.TE_READONLY)

        self.res_sizer.Add(res_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.res_sizer.Add(res_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,2)
        self.res_sizer.Add(reserr_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.res_sizer.Add(reserr_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.res_sizer.Add(resunit_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 4)


        clust_box = wx.StaticBox(parent, wx.ID_ANY, 'Clustering')
        self.clust_sizer = wx.StaticBoxSizer(clust_box, wx.VERTICAL)

        clust_num_text = wx.StaticText(parent, wx.ID_ANY, 'Number of clusters:')
        clust_num_ctrl = wx.TextCtrl(parent, self.ids['clustNum'], '', size=(60,-1), style=wx.TE_READONLY)

        clust_num_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clust_num_sizer.Add(clust_num_text, 0, wx.ALIGN_CENTER_VERTICAL)
        clust_num_sizer.Add(clust_num_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)

        clust_list1= wx.ListCtrl(parent, self.ids['clustDescrip'], size=(-1,150), style=wx.LC_REPORT)
        clust_list1.InsertColumn(0, 'Cluster')
        clust_list1.InsertColumn(1, 'Isolated')
        clust_list1.InsertColumn(2, 'Rep. Model')
        clust_list1.InsertColumn(3, 'Deviation')

        clust_list2= wx.ListCtrl(parent, self.ids['clustDist'], size=(-1,150), style=wx.LC_REPORT)
        clust_list2.InsertColumn(0, 'Cluster 1')
        clust_list2.InsertColumn(1, 'Cluster 2')
        clust_list2.InsertColumn(2, 'Distance')

        clust_list_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clust_list_sizer.Add(clust_list1, 5, wx.EXPAND)
        clust_list_sizer.Add(clust_list2, 3, wx.LEFT | wx.EXPAND, 8)

        self.clust_sizer.Add(clust_num_sizer, 0)
        self.clust_sizer.Add(clust_list_sizer, 0, wx.EXPAND | wx.TOP, 5)


        models_box = wx.StaticBox(parent, wx.ID_ANY, 'Models')
        self.models_sizer = wx.StaticBoxSizer(models_box, wx.VERTICAL)

        models_list = wx.ListCtrl(parent, self.ids['models'], size = (-1,-1), style=wx.LC_REPORT)
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
            models_list.SetColumnWidth(5, 100)

        self.models_sizer.Add(models_list, 1, wx.EXPAND)


        save_button = wx.Button(parent, wx.ID_ANY, 'Save Results Summary')
        save_button.Bind(wx.EVT_BUTTON, self._saveResults)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.ambi_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.nsd_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.res_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.clust_sizer,0, wx.EXPAND)
        top_sizer.Add(self.models_sizer,1,wx.EXPAND)
        top_sizer.Add(save_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        return top_sizer


    def _initSettings(self):
        wx.CallAfter(self.runAmbimeter)

        self.topsizer.Hide(self.nsd_sizer, recursive=True)
        self.topsizer.Hide(self.clust_sizer, recursive=True)
        self.topsizer.Hide(self.res_sizer, recursive=True)
        # self.topsizer.Hide(self.models_sizer, recursive=True)

    def runAmbimeter(self):
        cwd = os.getcwd()
        run_window = wx.FindWindowByName('DammifRunPanel')
        path_window = wx.FindWindowById(run_window.ids['save'], run_window)
        path = path_window.GetValue()
        os.chdir(path)

        outname = 't_ambimeter.out'
        while os.path.isfile(outname):
            outname = 't'+outname

        if self.main_frame.OnlineControl.isRunning() and path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        SASFileIO.writeOutFile(self.iftm, os.path.join(path, outname))

        ambi_settings = {'sRg' :'4',
                        'files':'None'
                        }

        try:
            output = SASCalc.runAmbimeter(outname, 'temp', ambi_settings)

        except SASExceptions.NoATSASError as e:
            wx.CallAfter(wx.MessageBox, str(e), 'Error running Ambimeter', style = wx.ICON_ERROR | wx.OK)
            os.remove(outname)
            os.chdir(cwd)
            return

        os.remove(outname)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

        os.chdir(cwd)

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        cats_window.SetValue(output[0])
        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        score_window.SetValue(output[1])
        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        eval_window.SetValue(output[2])

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
            dlist.Append(map(str, dist_data))

    def getModels(self, settings):
        models_window = wx.FindWindowById(self.ids['models'])
        models_window.DeleteAllItems()

        file_nums = range(1,int(settings['runs'])+1)
        path = settings['path']
        prefix = settings['prefix']

        model_list = []

        if settings['damaver']:
            name = prefix+'_damsel.log'
            filename = os.path.join(path, name)
            mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err, res_unit = SASFileIO.loadDamselLogFile(filename)

        for num in file_nums:
            fprefix = '%s_%s' %(prefix, str(num).zfill(2))
            dam_name = os.path.join(path, fprefix+'-1.pdb')
            fir_name = os.path.join(path, fprefix+'.fir')

            sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)

            chisq = sasm.getParameter('counters')['Chi_squared']

            atoms, header, model_data = SASFileIO.loadPDBFile(dam_name)
            model_data['chisq'] = chisq

            if settings['damaver'] and int(settings['runs']) > 1:
                model_data['nsd'] = result_dict[os.path.basename(dam_name)][-1]
                if result_dict[os.path.basename(dam_name)][0].lower() == 'include':
                    include = True
                else:
                    include = False

                model_data['include'] = include

            model_list.append([num, model_data, atoms])

        if settings['damaver'] and int(settings['runs']) > 1:
            damaver_name = os.path.join(path, prefix+'_damaver.pdb')
            damfilt_name = os.path.join(path, prefix+'_damfilt.pdb')

            atoms, header, model_data = SASFileIO.loadPDBFile(damaver_name)
            model_list.append(['damaver', model_data, atoms])

            atoms, header, model_data = SASFileIO.loadPDBFile(damfilt_name)
            model_list.append(['damfilt', model_data, atoms])

        if settings['refine']and int(settings['runs']) > 1:
            dam_name = os.path.join(path, 'refine_'+prefix+'-1.pdb')
            fir_name = os.path.join(path, 'refine_'+prefix+'.fir')
            sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
            chisq = sasm.getParameter('counters')['Chi_squared']

            atoms, header, model_data = SASFileIO.loadPDBFile(dam_name)
            model_data['chisq'] = chisq

            model_list.append(['refine', model_data, atoms])

        for item in model_list:
            models_window.Append((item[0], item[1]['chisq'], item[1]['rg'],
                item[1]['dmax'], item[1]['excluded_volume'], item[1]['mw'],
                item[1]['nsd']))

            if settings['damaver']:
                if not item[1]['include'] and item[0]!='damaver' and item[0]!='damfilt' and item[0]!='refine':
                    index = models_window.GetItemCount()-1
                    models_window.SetItemTextColour(index, 'red')

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

        viewer_window = wx.FindWindowByName('DammifViewerPanel')
        viewer_window.updateResults(model_list)

    def _saveResults(self, evt):
        nsd_data = []
        res_data = []
        clust_num = 0
        clist_data = []
        dlist_data = []

        if self.topsizer.IsShown(self.nsd_sizer):
            nsd_mean = wx.FindWindowById(self.ids['nsdMean']).GetValue()
            nsd_stdev = wx.FindWindowById(self.ids['nsdStdev']).GetValue()
            nsd_inc = wx.FindWindowById(self.ids['nsdInc']).GetValue()
            nsd_tot = wx.FindWindowById(self.ids['nsdTot']).GetValue()
            nsd_data = [('Mean NSD:', nsd_mean), ('Stdev. NSD', nsd_stdev),
                        ('DAMAVER Included:', nsd_inc, 'of', nsd_tot)]

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


        models_list = wx.FindWindowById(self.ids['models'])

        model_data = [[] for k in range(models_list.GetItemCount())]
        for i in range(models_list.GetItemCount()):
            item_data = [[] for k in range(models_list.GetColumnCount())]
            for j in range(models_list.GetColumnCount()):
                item = models_list.GetItem(i, j)
                data = item.GetText()
                item_data[j] = data

            model_data[i] = item_data

        ambi_cats = wx.FindWindowById(self.ids['ambiCats']).GetValue()
        ambi_score = wx.FindWindowById(self.ids['ambiScore']).GetValue()
        ambi_eval = wx.FindWindowById(self.ids['ambiEval']).GetValue()
        ambi_data = [('Compatible shape categories:', ambi_cats),
                    ('Ambiguity score:', ambi_score), ('AMBIMETER says:', ambi_eval)]

        input_file = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['fname']).GetValue()
        output_prefix = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['prefix']).GetValue()
        output_directory = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['save']).GetValue()
        reconst_prog = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['program']).GetStringSelection()
        mode = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['mode']).GetStringSelection()
        symmetry = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['sym']).GetStringSelection()
        anisometry = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['anisometry']).GetStringSelection()
        tot_recons = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['runs']).GetValue()
        damaver = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['damaver']).IsChecked()
        refine = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['refine']).IsChecked()
        damclust = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['damclust']).IsChecked()

        setup_data = [('Input file:', input_file), ('Output prefix:', output_prefix),
                    ('Output directory:', output_directory), ('Program used:', reconst_prog),
                    ('Mode:', mode), ('Symmetry:', symmetry), ('Anisometry:', anisometry),
                    ('Total number of reconstructions:', tot_recons),
                    ('Used DAMAVER:', damaver), ('Refined with DAMMIN:', refine),
                    ('Used DAMCLUST:', damclust),
                    ]

        name = output_prefix

        filename = name + '_dammif_results.csv'

        dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = output_directory, defaultFile = filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name+'.csv'
        else:
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving DAMMIF/N data', 0)

        SASFileIO.saveDammixData(save_path, ambi_data, nsd_data, res_data, clust_num,
                                clist_data, dlist_data, model_data, setup_data)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)


class DammifViewerPanel(wx.Panel):

    def __init__(self, parent):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DammifViewerPanel')
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY, name = 'DammifViewerPanel')

        self.parent = parent

        self.ids = {'models'    : self.NewControlId(),
                    }

        self.model_dict = None

        top_sizer = self._createLayout(self)

        self.SetSizer(top_sizer)

    def _createLayout(self, parent):
        model_text = wx.StaticText(parent, wx.ID_ANY, 'Model to display:')
        model_choice = wx.Choice(parent, self.ids['models'])
        model_choice.Bind(wx.EVT_CHOICE, self.onChangeModels)

        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_sizer.Add(model_text, 0)
        model_sizer.Add(model_choice, 0, wx.LEFT, 3)

        ctrls_box = wx.StaticBox(parent, wx.ID_ANY, 'Viewer Controls')
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
        layout_sizer.Add(ctrls_sizer, 0, wx.BOTTOM | wx.EXPAND, 5)
        layout_sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)
        # sizer.Add(self.toolbar, 0, wx.GROW)

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
        model_choice.Set(self.model_dict.keys())

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

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'DenssFrame', size = (675,750))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'DenssFrame', size = (675,750))

        self.manip_item = manip_item
        self.iftm = iftm
        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.panel = wx.Panel(self)
        self.notebook = wx.Notebook(self.panel, wx.ID_ANY)
        self.RunPanel = DenssRunPanel(self.notebook, self.iftm, self.manip_item)
        # self.ResultsPanel = DenssResultsPanel(self.notebook, self.iftm, self.manip_item)
        # self.ViewerPanel = DenssViewerPanel(self.notebook)

        self.notebook.AddPage(self.RunPanel, 'Run')
        # self.notebook.AddPage(self.ResultsPanel, 'Results')
        # self.notebook.AddPage(self.ViewerPanel, 'Viewer')

        sizer = self._createLayout(self.panel)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.notebook, 1, wx.EXPAND)
        top_sizer.Add(sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

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
                size[1] = size[1] + 20
                self.SetSize(size)

        self.CenterOnParent()

        self.Raise()

    def _createLayout(self, parent):
        close_button = wx.Button(parent, -1, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer =  wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(info_button, 0, wx.RIGHT, 5)
        button_sizer.Add(close_button, 0)

        return button_sizer

    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = ('In addition to citing the RAW paper:\n If you use Denss '
        'in your work please cite the paper given here:\n'
        'https://www.nature.com/articles/nmeth.4581\n\n'
        'For more information about DENSS see:\n'
        'https://www.tdgrant.com/denss/\n\n'
        'If you use EMAN2 (density alignment) in your work, please cite '
        'both the main EMAN2 and the single particle tomography paper given '
        'here:\n'
        'http://blake.bcm.edu/emanwiki/EMAN2/'
        )
        wx.MessageBox(str(msg), "How to cite Denss and EMAN2", style = wx.ICON_INFORMATION | wx.OK)

    def updateDenssSettings(self):
        self.RunPanel.updateDenssSettings()

    def OnClose(self, event):
        dammifrun = wx.FindWindowByName('DenssRunPanel')
        dammifrun.Close(event)

        if event.GetVeto():
            return
        else:
            self.Destroy()


class DenssRunPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DenssRunPanel')
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY, name = 'DenssRunPanel')

        self.parent = parent

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

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
                    'electrons'            : self.NewControlId(),
                    }

        if self.raw_settings.get('EMAN2Dir') != '':
            self.eman_present = True
        else:
            self.eman_present = False

        self.threads_finished = []

        topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(topsizer)

    def _createLayout(self, parent):

        file_ctrl = wx.TextCtrl(parent, self.ids['fname'], self.filename, size = (150, -1), style = wx.TE_READONLY)

        file_box = wx.StaticBox(parent, -1, 'Filename')
        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        file_sizer.Add(file_ctrl, 2, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        file_sizer.AddStretchSpacer(1)

        savedir_text = wx.StaticText(parent, -1, 'Output directory :')
        savedir_ctrl = wx.TextCtrl(parent, self.ids['save'], '', size = (350, -1))

        try:
            savedir_ctrl.AutoCompleteDirectories() #compatability for older versions of wxpython
        except AttributeError:
            pass

        savedir_button = wx.Button(parent, self.ids['changedir'], 'Select/Change Directory')
        savedir_button.Bind(wx.EVT_BUTTON, self.onChangeDirectoryButton)

        savedir_sizer = wx.BoxSizer(wx.VERTICAL)
        savedir_sizer.Add(savedir_text, 0, wx.LEFT | wx.RIGHT, 5)
        savedir_sizer.Add(savedir_ctrl, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND, 5)
        savedir_sizer.Add(savedir_button, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 5)


        prefix_text = wx.StaticText(parent, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(parent, self.ids['prefix'], '', size = (150, -1))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.LEFT, 5)
        prefix_sizer.Add(prefix_ctrl, 1, wx.LEFT | wx.RIGHT, 5)
        prefix_sizer.AddStretchSpacer(1)


        nruns_text = wx.StaticText(parent, -1, 'Number of reconstructions :')
        nruns_ctrl = wx.TextCtrl(parent, self.ids['runs'], '', size = (60, -1))
        nruns_ctrl.Bind(wx.EVT_TEXT, self.onRunsText)

        nruns_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nruns_sizer.Add(nruns_text, 0, wx.LEFT, 5)
        nruns_sizer.Add(nruns_ctrl, 0, wx.LEFT | wx.RIGHT, 5)


        nprocs = multiprocessing.cpu_count()
        nprocs_choices = [str(i) for i in range(nprocs, 0, -1)]
        nprocs_text = wx.StaticText(parent, -1, 'Number of simultaneous runs :')
        nprocs_choice = wx.Choice(parent, self.ids['procs'], choices = nprocs_choices)

        nprocs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nprocs_sizer.Add(nprocs_text, 0, wx.LEFT, 5)
        nprocs_sizer.Add(nprocs_choice, 0, wx.LEFT | wx.RIGHT, 5)


        mode_text = wx.StaticText(parent, wx.ID_ANY, 'Mode :')
        mode_ctrl = wx.Choice(parent, self.ids['mode'], choices=['Fast', 'Slow', 'Custom'])

        mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mode_sizer.Add(mode_text, 0, wx.LEFT, 5)
        mode_sizer.Add(mode_ctrl, 0, wx.LEFT | wx.RIGHT, 5)


        ne_text = wx.StaticText(parent, wx.ID_ANY, 'Total number of electrons :')
        ne_ctrl = wx.TextCtrl(parent, self.ids['electrons'], '', size=(60,-1))

        ne_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ne_sizer.Add(ne_text, 0, wx.LEFT, 5)
        ne_sizer.Add(ne_ctrl, 0, wx.LEFT | wx.RIGHT, 5)

        if self.eman_present:
            average_chk = wx.CheckBox(parent, self.ids['average'], 'Align and average densities (EMAN2)')

        advancedButton = wx.Button(parent, -1, 'Change Advanced Settings')
        advancedButton.Bind(wx.EVT_BUTTON, self._onAdvancedButton)


        settings_box = wx.StaticBox(parent, -1, 'Settings')
        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND | wx.TOP, 5)
        settings_sizer.Add(nruns_sizer, 0, wx.TOP, 5)
        settings_sizer.Add(nprocs_sizer, 0, wx.TOP, 5)
        settings_sizer.Add(mode_sizer, 0, wx.TOP, 5)
        settings_sizer.Add(ne_sizer, 0, wx.TOP, 5)
        if self.eman_present:
            settings_sizer.Add(average_chk, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        settings_sizer.Add(advancedButton, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 5)


        start_button = wx.Button(parent, self.ids['start'], 'Start')
        start_button.Bind(wx.EVT_BUTTON, self.onStartButton)

        abort_button = wx.Button(parent, self.ids['abort'], 'Abort')
        abort_button.Bind(wx.EVT_BUTTON, self.onAbortButton)

        button_box = wx.StaticBox(parent, -1, 'Controls')
        button_sizer = wx.StaticBoxSizer(button_box, wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        button_sizer.Add(abort_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        button_sizer.AddStretchSpacer(1)

        control_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer.Add(file_sizer, 0, wx.EXPAND)
        control_sizer.Add(settings_sizer, 0, wx.EXPAND)
        control_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.EXPAND)


        self.status = wx.TextCtrl(parent, self.ids['status'], '', style = wx.TE_MULTILINE | wx.TE_READONLY, size = (100,200))
        status_box = wx.StaticBox(parent, -1, 'Status')
        status_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)
        status_sizer.Add(self.status, 1, wx.EXPAND | wx.ALL, 5)


        half_sizer = wx.BoxSizer(wx.HORIZONTAL)
        half_sizer.Add(control_sizer, 2, wx.EXPAND)
        half_sizer.Add(status_sizer, 1, wx.EXPAND)


        try:
            self.logbook = flatNB.FlatNotebook(parent, self.ids['logbook'], agwStyle = flatNB.FNB_NAV_BUTTONS_WHEN_NEEDED | flatNB.FNB_NO_X_BUTTON)
        except AttributeError as e:
            print e
            self.logbook = flatNB.FlatNotebook(parent, self.ids['logbook'])     #compatability for older versions of wxpython
            self.logbook.SetWindowStyleFlag(flatNB.FNB_NO_X_BUTTON)

        self.logbook.DeleteAllPages()

        log_box = wx.StaticBox(parent, -1, 'Log')
        log_sizer = wx.StaticBoxSizer(log_box, wx.HORIZONTAL)
        log_sizer.Add(self.logbook, 1, wx.ALL | wx.EXPAND, 5)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:     #compatability for older versions of wxpython
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

        self.my_manager = multiprocessing.Manager()
        self.wx_queue = self.my_manager.Queue()

        return top_sizer


    def _initSettings(self):
        self.updateDenssSettings()

        if self.eman_present:
            aver = wx.FindWindowById(self.ids['average'], self)
            aver.SetValue(self.denss_settings['average'])

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

        wx.FindWindowById(self.ids['abort'], self).Disable()

        self.logbook.DeleteAllPages()


    def onStartButton(self, evt):
        #Set the denss settings
        self.setArgs()

        #Get user settings on number of runs, save location, etc
        if self.eman_present:
            average_window = wx.FindWindowById(self.ids['average'], self)
            average = average_window.GetValue()
        else:
            average = False

        prefix_window = wx.FindWindowById(self.ids['prefix'], self)
        prefix = prefix_window.GetValue()

        path_window = wx.FindWindowById(self.ids['save'], self)
        path = path_window.GetValue()

        procs_window = wx.FindWindowById(self.ids['procs'], self)
        procs = int(procs_window.GetStringSelection())

        nruns_window = wx.FindWindowById(self.ids['runs'], self)
        nruns = int(nruns_window.GetValue())

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
            mrc_name = denss_names[key]+'.mrc'

            names = [log_name, fit_name, stats_name, saxs_name, mrc_name] + xplor_names + image_names

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

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame,
                    question, button_list, label, icon, style=wx.CAPTION|wx.RESIZE_BORDER)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True

        #Set up the various bits of information the threads will need. Set up the status windows.
        self.denss_ids = collections.OrderedDict()
        for (key, value) in [(str(i), self.NewControlId()) for i in range(1, nruns+1)]:
            self.denss_ids[key] = value

        self.thread_nums = self.my_manager.Queue()

        self.logbook.DeleteAllPages()

        for i in range(1, nruns+1):
            text_ctrl = wx.TextCtrl(self.logbook, self.denss_ids[str(i)], '',
                style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, str(i))
            self.thread_nums.put_nowait(str(i))

        if nruns > 1 and average:

            average_names = [prefix+'_stack.hdf', prefix+'_stack_resized.hdf']
            names = average_names
            file_names = [os.path.join(path, name) for name in names]
            aver_folder = os.path.join(path, prefix+'_aver')

            file_exists = False

            for f in file_names:
                if os.path.exists(f):
                    file_exists = True
                    break

            if file_exists and not yes_to_all:
                button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                question = ('Warning: selected directory contains an EMAN2 average '
                    'output file(\n. Running the average will overwrite this '
                    'file.\nDo you wish to continue?')
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame,
                    question, button_list, label, icon, style=wx.CAPTION | wx.RESIZE_BORDER)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True
            if os.path.exists(aver_folder) and os.path.isdir(aver_folder) and not yes_to_all:
                button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO)]
                question = ('Warning: selected directory contains EMAN2 average '
                    'output folder\n. Running the average will remove all '
                    'contents in this folder.\nDo you wish to continue?')
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame,
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


        self.status.SetValue('Starting processing\n')


        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                try:
                    wx.FindWindowById(self.ids[key], self).Disable()
                except AttributeError:
                    pass
            elif key == 'abort':
                wx.FindWindowById(self.ids[key], self).Enable()

        self.stop_events = []
        self.threads_finished = []
        self.results = []

        self.my_lock = self.my_manager.Lock()

        self.abort_event = self.my_manager.Event()
        self.abort_event.clear()

        comm_list = []

        my_pool = multiprocessing.Pool(procs)

        q = self.iftm.q_extrap
        I = self.iftm.i_extrap
        sigq = np.sqrt(I) #Artificially generate noise for the data assuming poisson. Should be a better way
        D = self.iftm.getParameter('dmax')

        for key in self.denss_ids:
            if key != 'average':
                den_queue = self.my_manager.Queue()
                stop_event = self.my_manager.Event()
                stop_event.clear()
                comm_list.append([den_queue, stop_event])

                den_window = wx.FindWindowById(self.denss_ids[key])

                comm_t = threading.Thread(target=self.get_multi_output,
                    args=(den_queue, den_window, stop_event))
                comm_t.daemon = True
                comm_t.start()

                result = my_pool.apply_async(SASCalc.runDenss, args=(q, I, sigq,
                    D, prefix, path, comm_list, self.my_lock, self.thread_nums,
                    self.wx_queue, self.abort_event, self.denss_settings))

                self.stop_events.append(stop_event)
                self.threads_finished.append(False)
                self.results.append(result)

        my_pool.close()

        self.denss_timer.Start(1000)
        self.msg_timer.Start(100)

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
                    if key == 'runs' or key == 'mode':
                        self.denss_settings[key] = window.GetStringSelection()
                    else:
                        self.denss_settings[key] = window.GetValue()

        if self.denss_settings['mode'] != 'Custom':
            #reset settings to default
            temp_settings = RAWSettings.RawGuiSettings()
            self.denss_settings['voxel'] = temp_settings.get('denssVoxel')
            self.denss_settings['oversample'] = temp_settings.get('denssOversampling')
            self.denss_settings['steps'] = temp_settings.get('denssSteps')
            self.denss_settings['limitDmax'] = temp_settings.get('denssLimitDmax')
            self.denss_settings['dmaxStep'] = temp_settings.get('denssDmaxStartStep')
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

        if self.denss_settings['mode'] == 'Fast':
            self.denss_settings['swMinStep'] = 1000
            self.denss_settings['conSteps'] = '[2000]'
            self.denss_settings['recenterStep'] = '[501,1001,1501,2001,2501]'
            self.denss_settings['steps'] = 5000
            D = float(self.iftm.getParameter('dmax'))
            self.denss_settings['voxel'] = D*self.denss_settings['oversample']/32.

        elif self.denss_settings['mode'] == 'Slow':
            self.denss_settings['swMinStep'] = 5000
            self.denss_settings['conSteps'] = '[7500]'
            self.denss_settings['recenterStep'] = '[1001,1501,3001,7501,8501]'
            self.denss_settings['steps'] = 10000
            D = float(self.iftm.getParameter('dmax'))
            self.denss_settings['voxel'] = D*self.denss_settings['oversample']/64.

    def get_multi_output(self, queue, den_window, stop_event):
        num_msg = 0
        full_msg = ''
        while True:
            if stop_event.wait(0.001):
                wx.CallAfter(den_window.AppendText, full_msg)
                break
            try:
                msg = queue.get_nowait()
                num_msg = num_msg + 1
                full_msg = full_msg + msg
            except Queue.Empty:
                pass

            if num_msg == 100:
                wx.CallAfter(den_window.AppendText, full_msg)
                num_msg = 0
                full_msg = ''

    def runAverage(self, prefix, path, nruns, procs):

        read_semaphore = threading.BoundedSemaphore(1)
        #Solution for non-blocking reads adapted from stack overflow
        #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
        def enqueue_output(out, queue):
            with read_semaphore:
                line = 'test'
                line2=''
                while line != '':
                    line = out.read(1)
                    line2+=line
                    if line == '\n':
                        queue.put_nowait([line2])
                        line2=''
                    time.sleep(0.0001)

        #Check to see if things have been aborted
        myId = self.denss_ids['average']
        averWindow = wx.FindWindowById(myId, self)

        if self.abort_event.is_set():
            wx.CallAfter(averWindow.AppendText, 'Aborted!\n')
            return

        #Remove old files, so they don't mess up the program
        old_folder = os.path.join(path, prefix+'_aver')

        if os.path.exists(old_folder) and os.path.isdir(old_folder):
            shutil.rmtree(old_folder)

        wx.CallAfter(self.status.AppendText, 'Starting Average\n')

        den_filelist = [prefix+'_%s.mrc' %(str(i).zfill(2)) for i in range(1, nruns+1)]

        cwd = os.getcwd()
        os.chdir(path)

        eman_proc, out1 = SASCalc.runEman2Aver(den_filelist, procs, prefix)

        os.chdir(cwd)

        wx.CallAfter(averWindow.AppendText, out1)

        eman_q = Queue.Queue()
        readout_t = threading.Thread(target=enqueue_output, args=(eman_proc.stdout, eman_q))
        readout_t.daemon = True
        readout_t.start()

        #Send the eman2 output to the screen.
        while eman_proc.poll() is None:
            if self.abort_event.is_set():
                eman_proc.terminate()
                wx.CallAfter(averWindow.AppendText, 'Aborted!\n')
                return

            try:
                new_text = eman_q.get_nowait()
                new_text = new_text[0]
                wx.CallAfter(averWindow.AppendText, new_text)
            except Queue.Empty:
                pass
            time.sleep(0.001)

        time.sleep(2)
        with read_semaphore: #see if there's any last data that we missed
            try:
                new_text = eman_q.get_nowait()
                new_text = new_text[0]

                wx.CallAfter(averWindow.AppendText, new_text)
            except Queue.Empty:
                pass

        wx.CallAfter(self.status.AppendText, 'Finished Average\n')

        self.threads_finished[-1] = True

        self.finishedProcessing()


    def onDenssTimer(self, evt):
        denss_finished = False

        if np.all(self.threads_finished):
            denss_finished = True

        if denss_finished:
            self.denss_timer.Stop()
            self.msg_timer.Stop()

            if 'average' in self.denss_ids:
                path_window = wx.FindWindowById(self.ids['save'], self)
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'], self)
                prefix = prefix_window.GetValue()

                procs_window = wx.FindWindowById(self.ids['procs'], self)
                procs = int(procs_window.GetStringSelection())

                nruns_window = wx.FindWindowById(self.ids['runs'], self)
                nruns = int(nruns_window.GetValue())

                t = threading.Thread(target = self.runAverage, args = (prefix, path, nruns, procs))
                t.daemon = True
                t.start()
                self.threads_finished.append(False)

            else:
                self.finishedProcessing()

    def onMessageTimer(self, evt):
        for i in range(len(self.threads_finished)):
            try:
                self.my_lock.acquire()
                msg = self.wx_queue.get_nowait()
                if msg[0].startswith('status'):
                    wx.CallAfter(self.status.AppendText, msg[1])
                elif msg[0] == 'finished':
                    self.threads_finished[msg[1]] = True
                else:
                    my_num = msg[0].split()[-1]
                    my_id = self.denss_ids[my_num]
                    denssWindow = wx.FindWindowById(my_id, self)
                    wx.CallAfter(denssWindow.AppendText, msg[1])
            except Queue.Empty:
                pass
            finally:
                self.my_lock.release()

            try:
                if self.results[i].ready():
                    self.results[i].get()
            except Exception as e:
                self.abort_event.set()
                print e
                raise


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

        # #Get user settings on number of runs, save location, etc
        # damaver_window = wx.FindWindowById(self.ids['damaver'], self)
        # damaver = damaver_window.GetValue()

        # damclust_window = wx.FindWindowById(self.ids['damclust'], self)
        # damclust = damclust_window.GetValue()

        # prefix_window = wx.FindWindowById(self.ids['prefix'], self)
        # prefix = prefix_window.GetValue()

        # path_window = wx.FindWindowById(self.ids['save'], self)
        # path = path_window.GetValue()

        # nruns_window = wx.FindWindowById(self.ids['runs'], self)
        # nruns = int(nruns_window.GetValue())

        # refine_window = wx.FindWindowById(self.ids['refine'], self)
        # refine = refine_window.GetValue()

        # settings = {'damaver'   : damaver,
        #             'damclust'  : damclust,
        #             'prefix'    : prefix,
        #             'path'      : path,
        #             'runs'      : nruns,
        #             'refine'    : refine,
        #             }

        # results_window = wx.FindWindowByName('DammifResultsPanel')
        # wx.CallAfter(results_window.updateResults, settings)

        # self.parent.SetSelection(1)

    def _onAdvancedButton(self, evt):
        self.main_frame.showOptionsDialog(focusHead='DENSS')

    def updateDenssSettings(self):
        self.denss_settings = {'voxel'      : self.raw_settings.get('denssVoxel'),
                            'oversample'    : self.raw_settings.get('denssOversampling'),
                            'electrons'     : self.raw_settings.get('denssNElectrons'),
                            'steps'         : self.raw_settings.get('denssSteps'),
                            'limitDmax'     : self.raw_settings.get('denssLimitDmax'),
                            'dmaxStep'      : self.raw_settings.get('denssDmaxStartStep'),
                            'recenter'      : self.raw_settings.get('denssRecenter'),
                            'recenterStep'  : self.raw_settings.get('denssRecenterStep'),
                            'positivity'    : self.raw_settings.get('denssPositivity'),
                            'extrapolate'   : self.raw_settings.get('denssExtrapolate'),
                            'shrinkwrap'    : self.raw_settings.get('denssShrinkwrap'),
                            'swSigmaStart'  : self.raw_settings.get('denssShrinkwrapSigmaStart'),
                            'swSigmaEnd'    : self.raw_settings.get('denssShrinkwrapSigmaEnd'),
                            'swSigmaDecay'  : self.raw_settings.get('denssShrinkwrapSigmaDecay'),
                            'swThresFrac'   : self.raw_settings.get('denssShrinkwrapThresFrac'),
                            'swIter'        : self.raw_settings.get('denssShrinkwrapIter'),
                            'swMinStep'     : self.raw_settings.get('denssShrinkwrapMinStep'),
                            'connected'     : self.raw_settings.get('denssConnected'),
                            'conSteps'      : self.raw_settings.get('denssConnectivitySteps'),
                            'chiEndFrac'    : self.raw_settings.get('denssChiEndFrac'),
                            'plotOutput'    : self.raw_settings.get('denssPlotOutput'),
                            'average'       : self.raw_settings.get('denssEman2Average'),
                            'runs'          : self.raw_settings.get('denssReconstruct'),
                            'cutOutput'     : self.raw_settings.get('denssCutOut'),
                            'writeXplor'    : self.raw_settings.get('denssWriteXplor'),
                            'mode'          : self.raw_settings.get('denssMode'),
                            }


    def Close(self, event):

        process_finished = True

        if self.denss_timer.IsRunning():
            process_finished = False

        if process_finished and len(self.threads_finished)>0:
            if not np.all(self.threads_finished):
                process_finished = False

        if not process_finished and event.CanVeto():
            msg = "Warning: DENSS or EMAN2 is still running. Closing this window will abort the currently running processes. Do you want to continue closing the window?"
            dlg = wx.MessageDialog(self.main_frame, msg, "Abort DENSS/EMAN2?", style = wx.ICON_WARNING | wx.YES_NO)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            if proceed == wx.ID_YES:
                self.abort_event.set()

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

            for stop_event in self.stop_events:
                stop_event.set()

            if self.denss_timer.IsRunning():
                self.denss_timer.Stop()

            if self.msg_timer.IsRunning():
                    self.msg_timer.Stop()



class DenssResultsPanel(wx.Panel):

    def __init__(self, parent, iftm, manip_item):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DenssResultsPanel')
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY, name = 'DenssResultsPanel')

        self.parent = parent

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

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
                    'res'           : self.NewControlId(),
                    'resErr'        : self.NewControlId(),
                    'resUnit'       : self.NewControlId(),
                    }

        self.topsizer = self._createLayout(self)
        self._initSettings()

        self.SetSizer(self.topsizer)

    def _createLayout(self, parent):
        ambi_box = wx.StaticBox(parent, wx.ID_ANY, 'Ambimeter')
        self.ambi_sizer = wx.StaticBoxSizer(ambi_box, wx.VERTICAL)

        match_text = wx.StaticText(parent, wx.ID_ANY, 'Compatible shape categories:')
        match_ctrl = wx.TextCtrl(parent, self.ids['ambiCats'], '', size=(60,-1), style=wx.TE_READONLY)

        score_text = wx.StaticText(parent, -1, 'Ambiguity score:')
        score_ctrl = wx.TextCtrl(parent, self.ids['ambiScore'], '', size = (60, -1), style = wx.TE_READONLY)

        eval_text = wx.StaticText(parent, -1, 'AMBIMETER says:')
        eval_ctrl = wx.TextCtrl(parent, self.ids['ambiEval'], '', size = (300, -1), style = wx.TE_READONLY)

        ambi_subsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer1.Add(match_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer1.Add(match_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        ambi_subsizer1.Add(score_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        ambi_subsizer1.Add(score_ctrl, 0, wx.LEFT| wx.ALIGN_CENTER_VERTICAL, 2)

        ambi_subsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        ambi_subsizer2.Add(eval_text, 0, wx.ALIGN_CENTER_VERTICAL)
        ambi_subsizer2.Add(eval_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.ambi_sizer.Add(ambi_subsizer1, 0)
        self.ambi_sizer.Add(ambi_subsizer2, 0, wx.TOP, 5)


        nsd_box = wx.StaticBox(parent, wx.ID_ANY, 'Normalized Spatial Discrepancy')
        self.nsd_sizer = wx.StaticBoxSizer(nsd_box, wx.HORIZONTAL)

        mean_text = wx.StaticText(parent, wx.ID_ANY, 'Mean NSD:')
        mean_ctrl = wx.TextCtrl(parent, self.ids['nsdMean'], '', size=(60,-1), style=wx.TE_READONLY)

        stdev_text = wx.StaticText(parent, wx.ID_ANY, 'Stdev. NSD:')
        stdev_ctrl = wx.TextCtrl(parent, self.ids['nsdStdev'], '', size=(60,-1), style=wx.TE_READONLY)

        inc_text = wx.StaticText(parent, wx.ID_ANY, 'DAMAVER included:')
        inc_ctrl = wx.TextCtrl(parent, self.ids['nsdInc'], '', size=(60,-1), style=wx.TE_READONLY)
        inc_text2 = wx.StaticText(parent, wx.ID_ANY, 'of')
        total_ctrl = wx.TextCtrl(parent, self.ids['nsdTot'], '', size=(60,-1), style=wx.TE_READONLY)

        self.nsd_sizer.Add(mean_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.nsd_sizer.Add(mean_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(stdev_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        self.nsd_sizer.Add(stdev_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(inc_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        self.nsd_sizer.Add(inc_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(inc_text2, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.nsd_sizer.Add(total_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)


        res_box = wx.StaticBox(parent, wx.ID_ANY, 'Reconstruction Resolution (SASRES)')
        self.res_sizer = wx.StaticBoxSizer(res_box, wx.HORIZONTAL)

        res_text = wx.StaticText(parent, wx.ID_ANY, 'Ensemble Resolution:')
        res_ctrl = wx.TextCtrl(parent, self.ids['res'], '', size=(60,-1), style=wx.TE_READONLY)

        reserr_text = wx.StaticText(parent, wx.ID_ANY, '+/-')
        reserr_ctrl = wx.TextCtrl(parent, self.ids['resErr'], '', size=(60,-1), style=wx.TE_READONLY)

        resunit_ctrl = wx.TextCtrl(parent, self.ids['resUnit'], '', size=(100,-1), style=wx.TE_READONLY)

        self.res_sizer.Add(res_text, 0, wx.ALIGN_CENTER_VERTICAL)
        self.res_sizer.Add(res_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL,2)
        self.res_sizer.Add(reserr_text, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.res_sizer.Add(reserr_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.res_sizer.Add(resunit_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 4)


        clust_box = wx.StaticBox(parent, wx.ID_ANY, 'Clustering')
        self.clust_sizer = wx.StaticBoxSizer(clust_box, wx.VERTICAL)

        clust_num_text = wx.StaticText(parent, wx.ID_ANY, 'Number of clusters:')
        clust_num_ctrl = wx.TextCtrl(parent, self.ids['clustNum'], '', size=(60,-1), style=wx.TE_READONLY)

        clust_num_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clust_num_sizer.Add(clust_num_text, 0, wx.ALIGN_CENTER_VERTICAL)
        clust_num_sizer.Add(clust_num_ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)

        clust_list1= wx.ListCtrl(parent, self.ids['clustDescrip'], size=(-1,150), style=wx.LC_REPORT)
        clust_list1.InsertColumn(0, 'Cluster')
        clust_list1.InsertColumn(1, 'Isolated')
        clust_list1.InsertColumn(2, 'Rep. Model')
        clust_list1.InsertColumn(3, 'Deviation')

        clust_list2= wx.ListCtrl(parent, self.ids['clustDist'], size=(-1,150), style=wx.LC_REPORT)
        clust_list2.InsertColumn(0, 'Cluster 1')
        clust_list2.InsertColumn(1, 'Cluster 2')
        clust_list2.InsertColumn(2, 'Distance')

        clust_list_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clust_list_sizer.Add(clust_list1, 5, wx.EXPAND)
        clust_list_sizer.Add(clust_list2, 3, wx.LEFT | wx.EXPAND, 8)

        self.clust_sizer.Add(clust_num_sizer, 0)
        self.clust_sizer.Add(clust_list_sizer, 0, wx.EXPAND | wx.TOP, 5)


        models_box = wx.StaticBox(parent, wx.ID_ANY, 'Models')
        self.models_sizer = wx.StaticBoxSizer(models_box, wx.VERTICAL)

        models_list = wx.ListCtrl(parent, self.ids['models'], size = (-1,-1), style=wx.LC_REPORT)
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
            models_list.SetColumnWidth(5, 100)

        self.models_sizer.Add(models_list, 1, wx.EXPAND)


        save_button = wx.Button(parent, wx.ID_ANY, 'Save Results Summary')
        save_button.Bind(wx.EVT_BUTTON, self._saveResults)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.ambi_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.nsd_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.res_sizer, 0, wx.EXPAND)
        top_sizer.Add(self.clust_sizer,0, wx.EXPAND)
        top_sizer.Add(self.models_sizer,1,wx.EXPAND)
        top_sizer.Add(save_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        return top_sizer


    def _initSettings(self):
        wx.CallAfter(self.runAmbimeter)

        self.topsizer.Hide(self.nsd_sizer, recursive=True)
        self.topsizer.Hide(self.clust_sizer, recursive=True)
        self.topsizer.Hide(self.res_sizer, recursive=True)
        # self.topsizer.Hide(self.models_sizer, recursive=True)

    def runAmbimeter(self):
        cwd = os.getcwd()
        run_window = wx.FindWindowByName('DammifRunPanel')
        path_window = wx.FindWindowById(run_window.ids['save'], run_window)
        path = path_window.GetValue()
        os.chdir(path)

        outname = 't_ambimeter.out'
        while os.path.isfile(outname):
            outname = 't'+outname

        if self.main_frame.OnlineControl.isRunning() and path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        SASFileIO.writeOutFile(self.iftm, os.path.join(path, outname))

        ambi_settings = {'sRg' :'4',
                        'files':'None'
                        }

        try:
            output = SASCalc.runAmbimeter(outname, 'temp', ambi_settings)

        except SASExceptions.NoATSASError as e:
            wx.CallAfter(wx.MessageBox, str(e), 'Error running Ambimeter', style = wx.ICON_ERROR | wx.OK)
            os.remove(outname)
            os.chdir(cwd)
            return

        os.remove(outname)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

        os.chdir(cwd)

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        cats_window.SetValue(output[0])
        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        score_window.SetValue(output[1])
        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        eval_window.SetValue(output[2])

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
            dlist.Append(map(str, dist_data))

    def getModels(self, settings):
        models_window = wx.FindWindowById(self.ids['models'])
        models_window.DeleteAllItems()

        file_nums = range(1,int(settings['runs'])+1)
        path = settings['path']
        prefix = settings['prefix']

        model_list = []

        if settings['damaver']:
            name = prefix+'_damsel.log'
            filename = os.path.join(path, name)
            mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err, res_unit = SASFileIO.loadDamselLogFile(filename)

        for num in file_nums:
            fprefix = '%s_%s' %(prefix, str(num).zfill(2))
            dam_name = os.path.join(path, fprefix+'-1.pdb')
            fir_name = os.path.join(path, fprefix+'.fir')

            sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)

            chisq = sasm.getParameter('counters')['Chi_squared']

            atoms, header, model_data = SASFileIO.loadPDBFile(dam_name)
            model_data['chisq'] = chisq

            if settings['damaver'] and int(settings['runs']) > 1:
                model_data['nsd'] = result_dict[os.path.basename(dam_name)][-1]
                if result_dict[os.path.basename(dam_name)][0].lower() == 'include':
                    include = True
                else:
                    include = False

                model_data['include'] = include

            model_list.append([num, model_data, atoms])

        if settings['damaver'] and int(settings['runs']) > 1:
            damaver_name = os.path.join(path, prefix+'_damaver.pdb')
            damfilt_name = os.path.join(path, prefix+'_damfilt.pdb')

            atoms, header, model_data = SASFileIO.loadPDBFile(damaver_name)
            model_list.append(['damaver', model_data, atoms])

            atoms, header, model_data = SASFileIO.loadPDBFile(damfilt_name)
            model_list.append(['damfilt', model_data, atoms])

        if settings['refine']and int(settings['runs']) > 1:
            dam_name = os.path.join(path, 'refine_'+prefix+'-1.pdb')
            fir_name = os.path.join(path, 'refine_'+prefix+'.fir')
            sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
            chisq = sasm.getParameter('counters')['Chi_squared']

            atoms, header, model_data = SASFileIO.loadPDBFile(dam_name)
            model_data['chisq'] = chisq

            model_list.append(['refine', model_data, atoms])

        for item in model_list:
            models_window.Append((item[0], item[1]['chisq'], item[1]['rg'],
                item[1]['dmax'], item[1]['excluded_volume'], item[1]['mw'],
                item[1]['nsd']))

            if settings['damaver']:
                if not item[1]['include'] and item[0]!='damaver' and item[0]!='damfilt' and item[0]!='refine':
                    index = models_window.GetItemCount()-1
                    models_window.SetItemTextColour(index, 'red')

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

        viewer_window = wx.FindWindowByName('DammifViewerPanel')
        viewer_window.updateResults(model_list)

    def _saveResults(self, evt):
        nsd_data = []
        res_data = []
        clust_num = 0
        clist_data = []
        dlist_data = []

        if self.topsizer.IsShown(self.nsd_sizer):
            nsd_mean = wx.FindWindowById(self.ids['nsdMean']).GetValue()
            nsd_stdev = wx.FindWindowById(self.ids['nsdStdev']).GetValue()
            nsd_inc = wx.FindWindowById(self.ids['nsdInc']).GetValue()
            nsd_tot = wx.FindWindowById(self.ids['nsdTot']).GetValue()
            nsd_data = [('Mean NSD:', nsd_mean), ('Stdev. NSD', nsd_stdev),
                        ('DAMAVER Included:', nsd_inc, 'of', nsd_tot)]

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


        models_list = wx.FindWindowById(self.ids['models'])

        model_data = [[] for k in range(models_list.GetItemCount())]
        for i in range(models_list.GetItemCount()):
            item_data = [[] for k in range(models_list.GetColumnCount())]
            for j in range(models_list.GetColumnCount()):
                item = models_list.GetItem(i, j)
                data = item.GetText()
                item_data[j] = data

            model_data[i] = item_data

        ambi_cats = wx.FindWindowById(self.ids['ambiCats']).GetValue()
        ambi_score = wx.FindWindowById(self.ids['ambiScore']).GetValue()
        ambi_eval = wx.FindWindowById(self.ids['ambiEval']).GetValue()
        ambi_data = [('Compatible shape categories:', ambi_cats),
                    ('Ambiguity score:', ambi_score), ('AMBIMETER says:', ambi_eval)]

        input_file = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['fname']).GetValue()
        output_prefix = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['prefix']).GetValue()
        output_directory = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['save']).GetValue()
        reconst_prog = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['program']).GetStringSelection()
        mode = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['mode']).GetStringSelection()
        symmetry = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['sym']).GetStringSelection()
        anisometry = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['anisometry']).GetStringSelection()
        tot_recons = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['runs']).GetValue()
        damaver = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['damaver']).IsChecked()
        refine = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['refine']).IsChecked()
        damclust = wx.FindWindowById(wx.FindWindowByName('DammifRunPanel').ids['damclust']).IsChecked()

        setup_data = [('Input file:', input_file), ('Output prefix:', output_prefix),
                    ('Output directory:', output_directory), ('Program used:', reconst_prog),
                    ('Mode:', mode), ('Symmetry:', symmetry), ('Anisometry:', anisometry),
                    ('Total number of reconstructions:', tot_recons),
                    ('Used DAMAVER:', damaver), ('Refined with DAMMIN:', refine),
                    ('Used DAMCLUST:', damclust),
                    ]

        name = output_prefix

        filename = name + '_dammif_results.csv'

        dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = output_directory, defaultFile = filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name+'.csv'
        else:
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving DAMMIF/N data', 0)

        SASFileIO.saveDammixData(save_path, ambi_data, nsd_data, res_data, clust_num,
                                clist_data, dlist_data, model_data, setup_data)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)


class DenssViewerPanel(wx.Panel):

    def __init__(self, parent):

        try:
            wx.Panel.__init__(self, parent, wx.ID_ANY, name = 'DenssViewerPanel')
        except:
            wx.Panel.__init__(self, None, wx.ID_ANY, name = 'DenssViewerPanel')

        self.parent = parent

        self.ids = {'models'    : self.NewControlId(),
                    }

        self.model_dict = None

        top_sizer = self._createLayout(self)

        self.SetSizer(top_sizer)

    def _createLayout(self, parent):
        model_text = wx.StaticText(parent, wx.ID_ANY, 'Model to display:')
        model_choice = wx.Choice(parent, self.ids['models'])
        model_choice.Bind(wx.EVT_CHOICE, self.onChangeModels)

        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_sizer.Add(model_text, 0)
        model_sizer.Add(model_choice, 0, wx.LEFT, 3)

        ctrls_box = wx.StaticBox(parent, wx.ID_ANY, 'Viewer Controls')
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
        layout_sizer.Add(ctrls_sizer, 0, wx.BOTTOM | wx.EXPAND, 5)
        layout_sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.EXPAND)
        # sizer.Add(self.toolbar, 0, wx.GROW)

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
        model_choice.Set(self.model_dict.keys())

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


class BIFTFrame(wx.Frame):

    def __init__(self, parent, title, sasm, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'BIFTFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'BIFTFrame', size = (800,600))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        splitter1 = wx.SplitterWindow(self, -1)

        self.plotPanel = BIFTPlotPanel(splitter1, -1, 'BIFTPlotPanel')
        self.controlPanel = BIFTControlPanel(splitter1, -1, 'BIFTControlPanel', sasm, manip_item)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, 290)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(290)    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(50)

        splitter1.Layout()
        self.Layout()
        self.SendSizeEvent()
        splitter1.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)

        self.CenterOnParent()
        self.Raise()

        wx.FutureCall(50, self.initBIFT)

    def initBIFT(self):
        self.controlPanel.runBIFT()

    def OnClose(self):

        self.Destroy()


class BIFTPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.ift = None

        subplotLabels = [('P(r)', 'r', 'P(r)', .1), ('Data/Fit', 'q', 'I(q)', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)

        if self.ift is not None:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_q, self.orig_i, self.orig_err, self.orig_r, self.orig_p, self.orig_perr, self.orig_qexp, self.orig_jreg, self.xlim)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plotPr(self, iftm):

        xlim = iftm.getQrange()

        r = iftm.r
        p = iftm.p
        perr = iftm.err

        i = iftm.i_orig
        q = iftm.q_orig
        err = iftm.err_orig

        qexp = q
        jreg = iftm.i_fit

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(q, i, err, r, p, perr, qexp, jreg, xlim)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, q, i, err, r, p, perr, qexp, jreg, xlim):

        xmin, xmax = xlim

        #Save for resizing:
        self.orig_q = q
        self.orig_i = i
        self.orig_err = err
        self.orig_r = r
        self.orig_p = p
        self.orig_perr = perr
        self.orig_qexp = qexp
        self.orig_jreg = jreg

        self.xlim = xlim

        # #Cut out region of interest
        self.i = i[xmin:xmax]
        self.q = q[xmin:xmax]

        a = self.subplots['P(r)']
        b = self.subplots['Data/Fit']

        if not self.ift:
            self.ift, = a.plot(r, p, 'r.-', animated = True)

            self.zero_line = a.axhline(color = 'k', animated = True)

            self.data_line, = b.plot(self.q, self.i, 'b.', animated = True)
            self.gnom_line, = b.plot(qexp, jreg, 'r', animated = True)

            #self.lim_back_line, = a.plot([x_lim_back, x_lim_back], [y_lim_back-0.2, y_lim_back+0.2], transform=a.transAxes, animated = True)

            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)
        else:
            self.ift.set_ydata(p)
            self.ift.set_xdata(r)

            #Error lines:
            self.data_line.set_xdata(self.q)
            self.data_line.set_ydata(self.i)
            self.gnom_line.set_xdata(qexp)
            self.gnom_line.set_ydata(jreg)

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()
        b_oldx = b.get_xlim()
        b_oldy = b.get_ylim()

        a.relim()
        a.autoscale_view()

        b.relim()
        b.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()
        b_newx = b.get_xlim()
        b_newy = b.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy or b_newx != b_oldx or b_newy != b_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.background)

        a.draw_artist(self.ift)
        a.draw_artist(self.zero_line)

        #restore white background in error plot and draw new error:
        self.canvas.restore_region(self.err_background)
        b.draw_artist(self.data_line)
        b.draw_artist(self.gnom_line)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)


class BIFTControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, sasm, manip_item):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.sasm = sasm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.old_analysis = {}

        if 'BIFT' in self.sasm.getParameter('analysis'):
            self.old_analysis = copy.deepcopy(self.sasm.getParameter('analysis')['BIFT'])

        self.bift_settings = (self.raw_settings.get('PrPoints'),
                                  self.raw_settings.get('maxAlpha'),
                                  self.raw_settings.get('minAlpha'),
                                  self.raw_settings.get('AlphaPoints'),
                                  self.raw_settings.get('maxDmax'),
                                  self.raw_settings.get('minDmax'),
                                  self.raw_settings.get('DmaxPoints'))


        self.infodata = {'dmax'         : ('Dmax :', self.NewControlId()),
                         'alpha'        : ('Log(Alpha) :', self.NewControlId()),
                         'guinierI0'    : ('I0 :', self.NewControlId()),
                         'guinierRg'    : ('Rg :', self.NewControlId()),
                         'biftI0'       : ('I0 :', self.NewControlId()),
                         'biftRg'       : ('Rg :', self.NewControlId()),
                         'chisq'        : ('Reduced chi^2 :', self.NewControlId())
                         }

        self.statusIds = {  'status'      : self.NewControlId(),
                            'evidence'  : self.NewControlId(),
                            'chi'       : self.NewControlId(),
                            'alpha'     : self.NewControlId(),
                            'dmax'      : self.NewControlId(),
                            'spoint'    : self.NewControlId(),
                            'tpoint'    : self.NewControlId()}

        self.buttonIds = {  'abort'     : self.NewControlId(),
                            'settings'  : self.NewControlId(),
                            'run'       : self.NewControlId()}


        self.iftm = None

        info_button = wx.Button(self, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,0, wx.LEFT | wx.RIGHT, 5)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1, wx.RIGHT, 5)


        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self.createControls()
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND | wx.ALIGN_CENTER)


        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self.createInfoBox()
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND)

        box3 = wx.StaticBox(self, -1, 'Status')
        statusSizer = self.createStatus()
        boxSizer3 = wx.StaticBoxSizer(box3, wx.VERTICAL)
        boxSizer3.Add(statusSizer, 0, wx.EXPAND)


        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        bsizer.Add(boxSizer2, 0, wx.EXPAND, 5)
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.BOTTOM, 5)
        bsizer.Add(boxSizer3, 0, wx.EXPAND | wx.TOP, 5)
        bsizer.AddStretchSpacer(1)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(bsizer)

        self.initValues()

        self.BIFT_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onBIFTTimer, self.BIFT_timer)

        self.BIFT_queue = Queue.Queue()

    def createFileInfo(self):

        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.filenameTxtCtrl = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY)

        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND | wx.ALL, 3)

        return boxsizer

    def createInfoBox(self):

        dmaxLabel = wx.StaticText(self, -1, 'Dmax :')
        self.dmaxWindow = wx.TextCtrl(self, self.infodata['dmax'][1], '', size = (60,-1), style = wx.TE_READONLY)

        dmaxSizer = wx.BoxSizer(wx.HORIZONTAL)
        dmaxSizer.Add(dmaxLabel, 0, wx.RIGHT, 5)
        dmaxSizer.Add(self.dmaxWindow, 0, wx.RIGHT, 5)

        alphaLabel = wx.StaticText(self, -1, 'Log(Alpha) :')
        self.alphaWindow = wx.TextCtrl(self, self.infodata['alpha'][1], '', size = (60,-1), style = wx.TE_READONLY)

        alphaSizer = wx.BoxSizer(wx.HORIZONTAL)
        alphaSizer.Add(alphaLabel, 0, wx.RIGHT, 5)
        alphaSizer.Add(self.alphaWindow, 0, wx.RIGHT, 5)


        sizer = wx.FlexGridSizer(rows = 3, cols = 3)

        sizer.Add((0,0))

        rglabel = wx.StaticText(self, -1, 'Rg (A)')
        i0label = wx.StaticText(self, -1, 'I0')

        sizer.Add(rglabel, 0, wx.ALL, 5)
        sizer.Add(i0label, 0, wx.ALL, 5)

        guinierlabel = wx.StaticText(self, -1, 'Guinier :')
        self.guinierRg = wx.TextCtrl(self, self.infodata['guinierRg'][1], '', size = (60,-1), style = wx.TE_READONLY)
        self.guinierI0 = wx.TextCtrl(self, self.infodata['guinierI0'][1], '', size = (60,-1), style = wx.TE_READONLY)

        sizer.Add(guinierlabel, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.guinierRg, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        sizer.Add(self.guinierI0, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        biftlabel = wx.StaticText(self, -1, 'P(r) :')
        self.biftRg = wx.TextCtrl(self, self.infodata['biftRg'][1], '', size = (60,-1), style = wx.TE_READONLY)
        self.biftI0 = wx.TextCtrl(self, self.infodata['biftI0'][1], '', size = (60,-1), style = wx.TE_READONLY)

        sizer.Add(biftlabel, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.biftRg, 0, wx.ALL, 5)
        sizer.Add(self.biftI0, 0, wx.ALL, 5)


        chisqLabel = wx.StaticText(self, -1, self.infodata['chisq'][0])
        self.chisq = wx.TextCtrl(self, self.infodata['chisq'][1], '', size = (60,-1), style = wx.TE_READONLY)

        chisqSizer = wx.BoxSizer(wx.HORIZONTAL)
        chisqSizer.Add(chisqLabel, 0, wx.RIGHT, 5)
        chisqSizer.Add(self.chisq, 0, wx.RIGHT, 5)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(dmaxSizer, 0, wx.BOTTOM | wx.LEFT, 5)
        top_sizer.Add(alphaSizer, 0, wx.BOTTOM | wx.LEFT, 5)
        top_sizer.Add(sizer,0, wx.BOTTOM | wx.LEFT, 5)
        top_sizer.Add(chisqSizer,0, wx.BOTTOM | wx.LEFT, 5)

        return top_sizer

    def createControls(self):

        runButton = wx.Button(self, self.buttonIds['run'], 'Run')
        runButton.Bind(wx.EVT_BUTTON, self.onRunButton)

        abortButton = wx.Button(self, self.buttonIds['abort'], 'Abort')
        abortButton.Bind(wx.EVT_BUTTON, self.onAbortButton)

        advancedParams = wx.Button(self, self.buttonIds['settings'], 'Settings')
        advancedParams.Bind(wx.EVT_BUTTON, self.onChangeParams)


        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(runButton, 0, wx.ALL, 3)
        top_sizer.Add(abortButton, 0, wx.ALL, 3)
        top_sizer.Add(advancedParams, 0, wx.ALL, 3)


        return top_sizer

    def createStatus(self):

        statusLabel = wx.StaticText(self, -1, 'Status :')
        statusText = wx.StaticText(self, self.statusIds['status'], '')

        statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        statusSizer.Add(statusLabel, 0, wx.RIGHT, 3)
        statusSizer.Add(statusText, 0, wx.RIGHT, 3)


        evidenceLabel = wx.StaticText(self, -1, 'Evidence :')
        evidenceText = wx.StaticText(self, self.statusIds['evidence'], '')

        evidenceSizer = wx.BoxSizer(wx.HORIZONTAL)
        evidenceSizer.Add(evidenceLabel, 0, wx.RIGHT, 3)
        evidenceSizer.Add(evidenceText, 0, wx.RIGHT, 3)


        chiLabel = wx.StaticText(self, -1, 'Reduced chi^2 :')
        chiText = wx.StaticText(self, self.statusIds['chi'], '')

        chiSizer = wx.BoxSizer(wx.HORIZONTAL)
        chiSizer.Add(chiLabel, 0, wx.RIGHT, 3)
        chiSizer.Add(chiText, 0, wx.RIGHT, 3)


        alphaLabel = wx.StaticText(self, -1, 'Log(Alpha) :')
        alphaText = wx.StaticText(self, self.statusIds['alpha'], '')

        alphaSizer = wx.BoxSizer(wx.HORIZONTAL)
        alphaSizer.Add(alphaLabel, 0, wx.RIGHT, 3)
        alphaSizer.Add(alphaText, 0, wx.RIGHT, 3)


        dmaxLabel = wx.StaticText(self, -1, 'Dmax :')
        dmaxText = wx.StaticText(self, self.statusIds['dmax'], '')

        dmaxSizer = wx.BoxSizer(wx.HORIZONTAL)
        dmaxSizer.Add(dmaxLabel, 0, wx.RIGHT, 3)
        dmaxSizer.Add(dmaxText, 0, wx.RIGHT, 3)

        spointLabel = wx.StaticText(self, -1, 'Current Search Point :')
        spointText = wx.StaticText(self, self.statusIds['spoint'], '')

        spointSizer = wx.BoxSizer(wx.HORIZONTAL)
        spointSizer.Add(spointLabel, 0, wx.RIGHT, 3)
        spointSizer.Add(spointText, 0, wx.RIGHT, 3)


        tpointLabel = wx.StaticText(self, -1, 'Total Search Points :')
        tpointText = wx.StaticText(self, self.statusIds['tpoint'], '')

        tpointSizer = wx.BoxSizer(wx.HORIZONTAL)
        tpointSizer.Add(tpointLabel, 0, wx.RIGHT, 3)
        tpointSizer.Add(tpointText, 0, wx.RIGHT, 3)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(statusSizer, 0, wx.ALL, 3)
        top_sizer.Add(evidenceSizer, 0, wx.ALL, 3)
        top_sizer.Add(chiSizer, 0, wx.ALL, 3)
        top_sizer.Add(alphaSizer, 0, wx.ALL, 3)
        top_sizer.Add(dmaxSizer, 0, wx.ALL, 3)
        top_sizer.Add(spointSizer, 0, wx.ALL, 3)
        top_sizer.Add(tpointSizer, 0, wx.ALL, 3)

        return top_sizer

    def initValues(self):

        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1], self)
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1], self)

        if 'guinier' in self.sasm.getParameter('analysis'):

            guinier = self.sasm.getParameter('analysis')['guinier']

            try:
                guinierRgWindow.SetValue(str(guinier['Rg']))
            except Exception as e:
                print e
                guinierRgWindow.SetValue('')

            try:
                guinierI0Window.SetValue(str(guinier['I0']))
            except Exception as e:
                print e
                guinierI0Window.SetValue('')

        self.setFilename(os.path.basename(self.sasm.getParameter('filename')))

    def onSaveInfo(self, evt):

        if self.iftm is not None:

            results_dict = {}

            results_dict['Dmax'] = str(self.iftm.getParameter('dmax'))
            results_dict['Real_Space_Rg'] = str(self.iftm.getParameter('Rg'))
            results_dict['Real_Space_I0'] = str(self.iftm.getParameter('I0'))
            results_dict['ChiSquared'] = str(self.iftm.getParameter('ChiSquared'))
            results_dict['LogAlpha'] = str(self.iftm.getParameter('alpha'))


            analysis_dict = self.sasm.getParameter('analysis')
            analysis_dict['BIFT'] = results_dict

            if self.manip_item is not None:
                if results_dict != self.old_analysis:
                    wx.CallAfter(self.manip_item.markAsModified)

        if self.BIFT_timer.IsRunning():
            self.BIFT_timer.Stop()
            RAWGlobals.cancel_bift = True

        if self.raw_settings.get('AutoSaveOnBift') and self.iftm is not None:
            if os.path.isdir(self.raw_settings.get('BiftFilePath')):
                RAWGlobals.mainworker_cmd_queue.put(['save_iftm', [self.iftm, self.raw_settings.get('BiftFilePath')]])
            else:
                self.raw_settings.set('AutoSaveOnBift', False)
                wx.CallAfter(wx.MessageBox, 'The folder:\n' +self.raw_settings.get('BiftFilePath')+ '\ncould not be found. Autosave of BIFT files has been disabled. If you are using a config file from a different computer please go into Advanced Options/Autosave to change the save folders, or save you config file to avoid this message next time.', 'Autosave Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

        if self.iftm is not None:
            RAWGlobals.mainworker_cmd_queue.put(['to_plot_ift', [self.iftm, 'blue', None, not self.raw_settings.get('AutoSaveOnBift')]])

        diag = wx.FindWindowByName('BIFTFrame')
        diag.OnClose()

    def onChangeParams(self, evt):
        self.main_frame.showOptionsDialog(focusHead='IFT')

    def onRunButton(self, evt):
        self.runBIFT()

    def onCloseButton(self, evt):

        if self.BIFT_timer.IsRunning():
            self.BIFT_timer.Stop()
            RAWGlobals.cancel_bift = True

        diag = wx.FindWindowByName('BIFTFrame')
        diag.OnClose()

    def onAbortButton(self, evt):
        RAWGlobals.cancel_bift = True

    def _onInfoButton(self, evt):
        msg = 'If you use BIFT in your work, in addition to citing the RAW paper please cite:\nHansen, S. (2000). J. Appl. Cryst. 33, 1415-1421.'
        wx.MessageBox(str(msg), "How to cite BIFT", style = wx.ICON_INFORMATION | wx.OK)

    def updateBIFTInfo(self):
        biftRgWindow = wx.FindWindowById(self.infodata['biftRg'][1], self)
        biftI0Window = wx.FindWindowById(self.infodata['biftI0'][1], self)
        biftChisqWindow = wx.FindWindowById(self.infodata['chisq'][1], self)
        biftDmaxWindow = wx.FindWindowById(self.infodata['dmax'][1], self)
        biftAlphaWindow = wx.FindWindowById(self.infodata['alpha'][1], self)

        if self.iftm is not None:

            biftRgWindow.SetValue(str(self.iftm.getParameter('Rg')))
            biftI0Window.SetValue(str(self.iftm.getParameter('I0')))
            biftChisqWindow.SetValue(str(self.iftm.getParameter('ChiSquared')))
            biftDmaxWindow.SetValue(str(self.iftm.getParameter('dmax')))
            biftAlphaWindow.SetValue(str(np.log(self.iftm.getParameter('alpha'))))

    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))

    def updatePlot(self):

        # xlim = self.iftm.getQrange()

        # r = self.iftm.r
        # p = self.iftm.p
        # perr = self.iftm.err

        # i = self.iftm.i_orig
        # q = self.iftm.q_orig
        # err = self.iftm.err_orig

        # qexp = q
        # jreg = self.iftm.i_fit

        plotpanel = wx.FindWindowByName('BIFTPlotPanel')

        # plotpanel.updateDataPlot(q, i, err, r, p, perr, qexp, jreg, xlim)
        plotpanel.plotPr(self.iftm)

    def updateBIFTSettings(self):
        self.old_settings = copy.deepcopy(self.bift_settings)

        self.bift_settings = (self.raw_settings.get('PrPoints'),
                          self.raw_settings.get('maxAlpha'),
                          self.raw_settings.get('minAlpha'),
                          self.raw_settings.get('AlphaPoints'),
                          self.raw_settings.get('maxDmax'),
                          self.raw_settings.get('minDmax'),
                          self.raw_settings.get('DmaxPoints'))

        if self.old_settings != self.bift_settings:
            pass

        self.updatePlot()

    def runBIFT(self):

        for key in self.buttonIds:
            if key not in ['abort']:
                wx.FindWindowById(self.buttonIds[key], self).Disable()
            else:
                wx.FindWindowById(self.buttonIds[key], self).Enable()

        RAWGlobals.cancel_bift = False

        while not self.BIFT_queue.empty():
            self.BIFT_queue.get_nowait()

        self.BIFT_timer.Start(1)

        self.updateStatus({'status': 'Performing search grid'})

        RAWGlobals.mainworker_cmd_queue.put(['ift', ['BIFT', self.sasm, self.BIFT_queue, self.bift_settings]])

    def updateStatus(self, updates):
        for key in updates:
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

            elif 'success' in args:
                self.iftm = args['results']
                self.updateStatus({'status' : 'BIFT done'})
                self.updatePlot()
                self.updateBIFTInfo()
                self.finishedProcessing()

                if self.BIFT_timer.IsRunning():
                    self.BIFT_timer.Stop()

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


        except Queue.Empty:
            pass


class AmbimeterFrame(wx.Frame):

    def __init__(self, parent, title, iftm, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'AmbimeterFrame', size = (450,525))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'AmbimeterFrame', size = (450,525))

        self.panel = wx.Panel(self, -1, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

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
        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

        self.Layout()


        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.panel.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)


        self.CenterOnParent()

        self.Raise()

        wx.FutureCall(50,self.runAmbimeter)


    def _createLayout(self, parent):

        file_text = wx.StaticText(parent, -1, 'File :')
        file_ctrl = wx.TextCtrl(parent, self.ids['input'], '', size = (150, -1), style = wx.TE_READONLY)

        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        file_sizer.Add(file_text, 0, wx.ALL, 5)
        file_sizer.Add(file_ctrl, 2, wx.ALL | wx.EXPAND, 5)
        file_sizer.AddStretchSpacer(1)

        rg_text = wx.StaticText(parent, -1, 'Rg :')
        rg_ctrl = wx.TextCtrl(parent, self.ids['rg'], '', size = (60, -1), style = wx.TE_READONLY)

        rg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rg_sizer.Add(rg_text, 0, wx.ALL, 5)
        rg_sizer.Add(rg_ctrl, 1, wx.ALL | wx.EXPAND, 5)


        srg_text = wx.StaticText(parent, -1, 'Upper q*Rg limit (3 < q*Rg <7) :')
        srg_ctrl = wx.TextCtrl(parent, self.ids['sRg'], '4', size = (60, -1))
        srg_ctrl.Bind(wx.EVT_TEXT, self.onSrgText)

        srg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        srg_sizer.Add(srg_text, 0, wx.ALL, 5)
        srg_sizer.Add(srg_ctrl, 1, wx.ALL, 5)


        shape_text = wx.StaticText(parent, -1, 'Output shape(s) to save: ')
        shape_choice = wx.Choice(parent, self.ids['files'], choices = ['None', 'Best', 'All'])
        shape_choice.SetSelection(0)

        shape_sizer = wx.BoxSizer(wx.HORIZONTAL)
        shape_sizer.Add(shape_text, 0, wx.ALL, 5)
        shape_sizer.Add(shape_choice, 0, wx.ALL, 5)

        savedir_text = wx.StaticText(parent, -1, 'Output directory :')
        savedir_ctrl = wx.TextCtrl(parent, self.ids['save'], '', size = (350, -1))

        try:
            savedir_ctrl.AutoCompleteDirectories() #compatability for older versions of wxpython
        except AttributeError as e:
            print e

        savedir_button = wx.Button(parent, -1, 'Select/Change Directory')
        savedir_button.Bind(wx.EVT_BUTTON, self.onChangeDirectoryButton)

        savedir_sizer = wx.BoxSizer(wx.VERTICAL)
        savedir_sizer.Add(savedir_text, 0, wx.ALL, 5)
        savedir_sizer.Add(savedir_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        savedir_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)


        prefix_text = wx.StaticText(parent, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(parent, self.ids['prefix'], '', size = (150, -1))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.ALL, 5)
        prefix_sizer.Add(prefix_ctrl, 2, wx.ALL, 5)
        prefix_sizer.AddStretchSpacer(1)


        start_button = wx.Button(parent, -1, 'Run')
        start_button.Bind(wx.EVT_BUTTON, self.onStartButton)


        settings_box = wx.StaticBox(parent, -1, 'Controls')
        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        settings_sizer.Add(srg_sizer, 0)
        # settings_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        settings_sizer.Add(shape_sizer, 0)
        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND)
        settings_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)


        cats_text = wx.StaticText(parent, -1, 'Number of compatible shape categories :')
        cats_ctrl = wx.TextCtrl(parent, self.ids['ambiCats'], '', size = (60, -1), style = wx.TE_READONLY)

        cats_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cats_sizer.Add(cats_text, 0, wx.ALL, 5)
        cats_sizer.Add(cats_ctrl, 0, wx.ALL, 5)


        score_text = wx.StaticText(parent, -1, 'Ambiguity score :')
        score_ctrl = wx.TextCtrl(parent, self.ids['ambiScore'], '', size = (60, -1), style = wx.TE_READONLY)

        score_sizer = wx.BoxSizer(wx.HORIZONTAL)
        score_sizer.Add(score_text, 0, wx.ALL, 5)
        score_sizer.Add(score_ctrl, 0, wx.ALL, 5)

        eval_text = wx.StaticText(parent, -1, 'AMBIMETER says :')
        eval_ctrl = wx.TextCtrl(parent, self.ids['ambiEval'], '', size = (250, -1), style = wx.TE_READONLY)

        eval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        eval_sizer.Add(eval_text, 0, wx.ALL, 5)
        eval_sizer.Add(eval_ctrl, 1, wx.ALL, 5)


        results_box = wx.StaticBox(parent, -1, 'Results')
        results_sizer = wx.StaticBoxSizer(results_box, wx.VERTICAL)
        results_sizer.Add(cats_sizer, 0)
        # results_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        results_sizer.Add(score_sizer, 0)
        results_sizer.Add(eval_sizer, 0, wx.EXPAND)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        savebutton = wx.Button(parent, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(info_button,1,wx.RIGHT, 5)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(file_sizer, 0, wx.EXPAND)
        top_sizer.Add(rg_sizer, 0)
        top_sizer.Add(settings_sizer, 0, wx.EXPAND)
        top_sizer.Add(results_sizer, 0, wx.EXPAND)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(buttonSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_RIGHT, 5)


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
        self.runAmbimeter()


    def runAmbimeter(self):
        bi = wx.BusyInfo('Running AMBIMETER, pleae wait.', self)

        cwd = os.getcwd()
        os.chdir(self.ambi_settings['path'])

        outname = 't_ambimeter.out'
        while os.path.isfile(outname):
            outname = 't'+outname


        if self.main_frame.OnlineControl.isRunning() and self.ambi_settings['path'] == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False


        SASFileIO.writeOutFile(self.iftm, os.path.join(self.ambi_settings['path'], outname))

        try:
            output = SASCalc.runAmbimeter(outname, self.ambi_settings['prefix'].replace(' ','_'), self.ambi_settings)

        except SASExceptions.NoATSASError as e:
            wx.CallAfter(wx.MessageBox, str(e), 'Error running Ambimeter', style = wx.ICON_ERROR | wx.OK)
            os.remove(outname)
            os.chdir(cwd)
            bi.Destroy()
            self.Close()
            return


        os.remove(outname)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)


        os.chdir(cwd)

        cats_window = wx.FindWindowById(self.ids['ambiCats'], self)
        cats_window.SetValue(output[0])

        score_window = wx.FindWindowById(self.ids['ambiScore'], self)
        score_window.SetValue(output[1])

        eval_window = wx.FindWindowById(self.ids['ambiEval'], self)
        eval_window.SetValue(output[2])

        bi.Destroy()


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save'], self).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)

        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save'], self).SetValue(new_path)


    def onSrgText(self, evt):
        srg_ctrl = wx.FindWindowById(self.ids['sRg'], self)


        srg = srg_ctrl.GetValue()
        if srg != '' and not srg.isdigit():

            try:
                srg = float(srg.replace(',', '.'))
            except ValueError as e:
                print e
                srg = ''
            if srg != '':
                srg = str(float(srg))

            srg_ctrl.ChangeValue(srg)


    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = 'If you use AMBIMETER in your work, in addition to citing the RAW paper please cite:\nPetoukhov, M. V. & Svergun, D. I. (2015). Acta Cryst. D71, 1051-1058.'
        wx.MessageBox(str(msg), "How to cite AMBIMETER", style = wx.ICON_INFORMATION | wx.OK)

    def onSaveInfo(self, evt):

        self.Close()


    def OnClose(self, event):

        self.Destroy()



class SVDFrame(wx.Frame):

    def __init__(self, parent, title, secm, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'SVDFrame', size = (800,680))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'SVDFrame', size = (800,680))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        splitter1 = wx.SplitterWindow(self, -1)

        copy_secm = copy.copy(secm)

        self.plotPanel = SVDResultsPlotPanel(splitter1, -1, 'SVDResultsPlotPanel')
        self.controlPanel = SVDControlPanel(splitter1, -1, 'SVDControlPanel', copy_secm, manip_item)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, 290)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(290)    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(50)

        splitter1.Layout()
        self.Layout()
        self.SendSizeEvent()
        splitter1.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)

        self.CenterOnParent()
        self.Raise()

    def OnClose(self):

        self.Destroy()



class SVDResultsPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.svd = None

        subplotLabels = [('Singular Values', 'Index', 'Value', .1), ('AutoCorrelation', 'Index', 'Absolute Value', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Singular Values']
        b = self.subplots['AutoCorrelation']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)

        if self.svd is not None:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_index, self.orig_svd_s, self.orig_svd_U_autocor, self.orig_svd_V_autocor, self.orig_svd_start, self.orig_svd_end)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plotSVD(self, svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, svd_start, svd_end):
        index = np.arange(len(svd_s))

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(index, svd_s, svd_U_autocor, svd_V_autocor, svd_start, svd_end)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

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

        if not self.svd:
            self.svd, = a.semilogy(xdata, ydata1, 'r.-', animated = True)

            self.u_autocor, = b.plot(xdata, ydata2, 'r.-', label = 'U (Left singular vectors)', animated = True)
            self.v_autocor, = b.plot(xdata, ydata3, 'b.-', label = 'V (Right singular vectors)', animated = True)
            b.legend(fontsize = 12)

            #self.lim_back_line, = a.plot([x_lim_back, x_lim_back], [y_lim_back-0.2, y_lim_back+0.2], transform=a.transAxes, animated = True)

            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)
        else:
            self.svd.set_xdata(xdata)
            self.svd.set_ydata(ydata1)

            self.u_autocor.set_xdata(xdata)
            self.u_autocor.set_ydata(ydata2)

            self.v_autocor.set_xdata(xdata)
            self.v_autocor.set_ydata(ydata3)

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()
        b_oldx = b.get_xlim()
        b_oldy = b.get_ylim()

        a.relim()
        a.autoscale_view()

        b.relim()
        b.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()
        b_newx = b.get_xlim()
        b_newy = b.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy or b_newx != b_oldx or b_newy != b_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.background)

        a.draw_artist(self.svd)

        #restore white background in error plot and draw new error:
        self.canvas.restore_region(self.err_background)
        b.draw_artist(self.u_autocor)
        b.draw_artist(self.v_autocor)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)


class SVDSECPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, svd = False, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        if (int(matplotlib.__version__.split('.')[0]) == 1 and int(matplotlib.__version__.split('.')[1]) >= 5) or int(matplotlib.__version__.split('.')[0]) > 1:
            self.fig = Figure((4,4), 75)
        else:
            if not svd:
                self.fig = Figure((300./75,4), 75)
            else:
                self.fig = Figure((250./75,4), 75)

        self.secm = None

        subplotLabels = [('SECPlot', 'Frame #', 'Intensity', .1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.18, bottom = 0.13, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['SECPlot']
        # b = self.subplots['Data/Fit']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        # self.err_background = self.canvas.copy_from_bbox(b.bbox)

        if self.secm is not None:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_frame_list, self.orig_intensity, self.orig_framei, self.orig_framef)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plotSECM(self, secm, framei, framef, ydata_type):
        frame_list = secm.frame_list

        if ydata_type == 'qspec':
            intensity = secm.I_of_q
        elif ydata_type == 'mean':
            intensity = secm.mean_i
        else:
            intensity = secm.total_i

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(frame_list, intensity, framei, framef)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, frame_list, intensity, framei, framef):

        #Save for resizing:
        self.orig_frame_list = frame_list
        self.orig_intensity = intensity
        self.orig_framei = framei
        self.orig_framef = framef

        a = self.subplots['SECPlot']

        if not self.secm:
            self.secm, = a.plot(frame_list, intensity, 'r.-', animated = True)

            self.cut_line, = a.plot(frame_list[framei:framef+1], intensity[framei:framef+1], 'b.-', animated = True)

            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)
        else:
            self.secm.set_ydata(intensity)
            self.secm.set_xdata(frame_list)

            #Error lines:
            self.cut_line.set_ydata(intensity[framei:framef+1])
            self.cut_line.set_xdata(frame_list[framei:framef+1])


        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()

        a.relim()
        a.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.background)

        a.draw_artist(self.secm)
        a.draw_artist(self.cut_line)

        self.canvas.blit(a.bbox)


class SVDControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, secm, manip_item):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.svd_frame = wx.FindWindowByName('SVDFrame')

        self.secm = secm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.control_ids = {'profile'   : self.NewControlId(),
                            'fstart'    : self.NewControlId(),
                            'fend'      : self.NewControlId(),
                            'svd_start' : self.NewControlId(),
                            'svd_end'   : self.NewControlId(),
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


    def _createLayout(self):

        top_sizer =wx.BoxSizer(wx.VERTICAL)

        #filename sizer
        box = wx.StaticBox(self, -1, 'Filename')
        filesizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        filenameTxtCtrl = wx.TextCtrl(self, self.field_ids['fname'], '', style = wx.TE_READONLY)

        filesizer.Add(filenameTxtCtrl, 1, wx.ALL, 3)


        #svd controls
        box = wx.StaticBox(self, -1, 'Controls')
        control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #control if you're using unsubtracted or subtracted curves
        label = wx.StaticText(self, -1, 'Use :')
        profile_type = wx.Choice(self, self.control_ids['profile'], choices = ['Unsubtracted', 'Subtracted'])
        profile_type.SetStringSelection('Unsubtracted')
        profile_type.Bind(wx.EVT_CHOICE, self._onProfileChoice)

        profile_sizer = wx.BoxSizer(wx.HORIZONTAL)
        profile_sizer.Add(label, 0, wx.LEFT | wx.RIGHT, 3)
        profile_sizer.Add(profile_type, 1, wx.RIGHT, 3)

        #control what the range of curves you're using is.
        label1 = wx.StaticText(self, -1, 'Use Frames :')
        label2 = wx.StaticText(self, -1, 'to')
        start_frame = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['fstart'], size = (60,-1))
        end_frame = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['fend'], size = (60,-1))

        start_frame.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeFrame)
        end_frame.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeFrame)

        frame_sizer = wx.BoxSizer(wx.HORIZONTAL)
        frame_sizer.Add(label1, 0, wx.LEFT | wx.RIGHT, 3)
        frame_sizer.Add(start_frame, 0, wx.RIGHT, 3)
        frame_sizer.Add(label2, 0, wx.RIGHT, 3)
        frame_sizer.Add(end_frame, 0, wx.RIGHT, 3)

        norm_data = wx.CheckBox(self, self.control_ids['norm_data'], 'Normalize by uncertainty')
        norm_data.SetValue(True)
        norm_data.Bind(wx.EVT_CHECKBOX, self._onNormChoice)


        #plot the sec data
        sec_plot = SVDSECPlotPanel(self, -1, 'SVDSECPlotPanel', svd = True)


        #SVD control sizer
        control_sizer.Add(profile_sizer, 0,  wx.TOP | wx.EXPAND, 3)
        control_sizer.Add(frame_sizer, 0, wx.TOP | wx.EXPAND, 8)
        control_sizer.Add(norm_data, 0, wx.TOP | wx.EXPAND, 8)
        control_sizer.Add(sec_plot, 0, wx.TOP | wx.EXPAND, 8)

        if self.manip_item == None:
            control_sizer.Hide(profile_sizer, recursive = True)


        #svd results
        box = wx.StaticBox(self, -1, 'Results')
        results_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #Control plotted SVD range
        label1 = wx.StaticText(self, -1, 'Plot indexes :')
        label2 = wx.StaticText(self, -1, 'to')
        start_svd = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['svd_start'], size = (60,-1))
        end_svd = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['svd_end'], size = (60,-1))

        start_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)
        end_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)

        svdrange_sizer = wx.BoxSizer(wx.HORIZONTAL)
        svdrange_sizer.Add(label1, 0, wx.LEFT | wx.RIGHT, 3)
        svdrange_sizer.Add(start_svd, 0, wx.RIGHT, 3)
        svdrange_sizer.Add(label2, 0, wx.RIGHT, 3)
        svdrange_sizer.Add(end_svd, 0, wx.RIGHT, 3)


        #Save SVD info
        save_svd_auto = wx.Button(self, self.button_ids['save_svd'], 'Save Plotted Values')
        save_svd_auto.Bind(wx.EVT_BUTTON, self._onSaveButton)

        save_svd_all = wx.Button(self, self.button_ids['save_all'], 'Save All')
        save_svd_all.Bind(wx.EVT_BUTTON, self._onSaveButton)

        svd_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        svd_button_sizer.Add(save_svd_auto, 1, wx.LEFT | wx.RIGHT, 3)
        svd_button_sizer.Add(save_svd_all, 1, wx.RIGHT, 3)


        results_sizer.Add(svdrange_sizer, 0,  wx.TOP | wx.EXPAND, 3)
        results_sizer.Add(svd_button_sizer,0, wx.TOP | wx.EXPAND, 3)


        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self._onCancelButton)

        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self._onOkButton)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1)


        top_sizer.Add(filesizer, 0, wx.EXPAND | wx.TOP, 3)
        top_sizer.Add(control_sizer, 0, wx.EXPAND | wx.TOP, 3)
        top_sizer.Add(results_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        return top_sizer

    def initValues(self):

        filename = self.secm.getParameter('filename')

        filename_window = wx.FindWindowById(self.field_ids['fname'], self)
        filename_window.SetValue(filename)

        analysis_dict = self.secm.getParameter('analysis')

        if 'svd' not in analysis_dict:

            framei = self.secm.frame_list[0]
            framef = self.secm.frame_list[-1]


            framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
            framef_window = wx.FindWindowById(self.control_ids['fend'], self)

            if len(self.secm.subtracted_sasm_list)>0:
                if not np.all(self.secm.use_subtracted_sasm):
                    frame_start = max(np.where(self.secm.use_subtracted_sasm)[0][0], framei)
                    frame_end = min(np.where(self.secm.use_subtracted_sasm)[0][-1], framef)

            else:
                frame_start = framei
                frame_end = framef

            framei_window.SetValue(frame_start)
            framef_window.SetValue(frame_end)

            framei_window.SetRange((framei, framef))
            framef_window.SetRange((framei, framef))


            svd_start_window =wx.FindWindowById(self.control_ids['svd_start'], self)
            svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

            svd_start_window.SetValue(0)
            svd_end_window.SetValue(min(framef-framei,10))

            svd_start_window.SetRange((0, framef-framei-1))
            svd_end_window.SetRange((1, framef-framei))

        else:
            framei = self.secm.frame_list[0]
            framef = self.secm.frame_list[-1]

            framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
            framef_window = wx.FindWindowById(self.control_ids['fend'], self)

            svd_start_window =wx.FindWindowById(self.control_ids['svd_start'], self)
            svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

            framei_window.SetRange((framei, framef))
            framef_window.SetRange((framei, framef))

            svd_start_window.SetRange((0, framef-framei-1))
            svd_end_window.SetRange((1, framef-framei))

            for key in analysis_dict['svd']:
                if key != 'profile':
                    wx.FindWindowById(self.control_ids[key], self).SetValue(analysis_dict['svd'][key])
                else:
                    wx.FindWindowById(self.control_ids[key], self).SetStringSelection(analysis_dict['svd'][key])


        #make a subtracted profile SECM
        if len(self.secm.subtracted_sasm_list)>0:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, self.secm.frame_list, self.secm.getAllParameters())
        else:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, [], self.secm.getAllParameters())


        if self.manip_item is not None:
            sec_plot_panel = wx.FindWindowByName('SECPlotPanel')

            self.ydata_type = sec_plot_panel.plotparams['y_axis_display']

            if self.ydata_type == 'qspec':
                q=float(sec_plot_panel.plotparams['secm_plot_q'])
                self.subtracted_secm.I(q)

        self.updateSECPlot()

        wx.CallAfter(self.runSVD)


    #This function is called when the profiles used are changed between subtracted and unsubtracted.
    def _onProfileChoice(self, evt):
        if len(self.subtracted_secm.getAllSASMs()) > 0:
            wx.CallAfter(self.updateSECPlot)
            wx.CallAfter(self.runSVD)
        else:
            msg = 'No subtracted files are available for this series curve. You can create subtracted curves by setting a buffer range in the Series Control Panel and calculating the parameter values. You will have to reopen the SVD window after doing this.'
            dlg = wx.MessageDialog(self, msg, "No subtracted files", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

            profile_window = wx.FindWindowById(evt.GetId(), self)
            profile_window.SetStringSelection('Unsubtracted')


    #This function is called when the start and end frame range spin controls are modified
    def _onChangeFrame(self, evt):
        id = evt.GetId()

        spin = wx.FindWindowById(id, self)

        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'], self)
        fend_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

        #Make sure the boundaries don't cross:
        if id == self.control_ids['fstart']:
            max_val = fend_window.GetValue()

            if new_val > max_val-1:
                new_val = max_val - 1
                spin.SetValue(new_val)

        elif id == self.control_ids['fend']:
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

        wx.CallAfter(self.runSVD)

    def _onNormChoice(self, evt):
        wx.CallAfter(self.runSVD)

    def _onChangeSVD(self, evt):
        id = evt.GetId()

        spin = wx.FindWindowById(id, self)

        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'], self)
        fend_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        #Make sure the boundaries don't cross:
        if id == self.control_ids['svd_start']:
            max_val = svd_end_window.GetValue()

            tot = fend_window.GetValue()-fstart_window.GetValue()

            if new_val > tot - 1:
                new_val = tot - 1
                spin.SetValue(new_val)

            elif new_val > max_val-1:
                new_val = max_val - 1
                spin.SetValue(new_val)

        elif id == self.control_ids['svd_end']:
            min_val = svd_start_window.GetValue()

            tot = fend_window.GetValue()-fstart_window.GetValue()

            if new_val > tot:
                new_val = tot
                spin.SetValue(new_val)

            elif new_val < min_val+1:
                new_val = min_val + 1
                spin.SetValue(new_val)

        wx.CallAfter(self.updateSVDPlot)


    def onSaveInfo(self, evt):

        diag = wx.FindWindowByName('SVDFrame')
        diag.OnClose()


    def runSVD(self):
        profile_window = wx.FindWindowById(self.control_ids['profile'], self)

        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        if profile_window.GetStringSelection() == 'Unsubtracted':
            secm = self.secm
        else:
            secm = self.subtracted_secm

        norm_data_window = wx.FindWindowById(self.control_ids['norm_data'], self)
        norm_data = norm_data_window.GetValue()

        sasm_list = secm.getSASMList(framei, framef)

        svd_a = np.array([sasm.i for sasm in sasm_list])
        svd_a = svd_a.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose svd_a

        if norm_data:
            err = np.array([sasm.err for sasm in sasm_list])
            err = err.T

            err_mean = np.mean(err, axis = 1)
            if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
                err_avg = np.broadcast_to(err_mean.reshape(err_mean.size,1), err.shape)
            else:
                err_avg = np.array([err_mean for i in range(err.shape[1])]).T

            svd_a = svd_a/err_avg


        self.svd_U, self.svd_s, svd_Vt = np.linalg.svd(svd_a, full_matrices = True)
        self.svd_V = svd_Vt.T
        self.svd_U_autocor = np.abs(np.array([np.correlate(self.svd_U[:,i], self.svd_U[:,i], mode = 'full')[-self.svd_U.shape[0]+1] for i in range(self.svd_U.shape[1])]))
        self.svd_V_autocor = np.abs(np.array([np.correlate(self.svd_V[:,i], self.svd_V[:,i], mode = 'full')[-self.svd_V.shape[0]+1] for i in range(self.svd_V.shape[1])]))

        wx.CallAfter(self.updateSVDPlot)

    def updateSECPlot(self):

        plotpanel = wx.FindWindowByName('SVDSECPlotPanel')
        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        profile_window = wx.FindWindowById(self.control_ids['profile'],self )

        if profile_window.GetStringSelection() == 'Unsubtracted':
            plotpanel.plotSECM(self.secm, framei, framef, self.ydata_type)
        else:
            plotpanel.plotSECM(self.subtracted_secm, framei, framef, self.ydata_type)

    def updateSVDPlot(self):
        plotpanel = wx.FindWindowByName('SVDResultsPlotPanel')

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()

        plotpanel.plotSVD(self.svd_U, self.svd_s, self.svd_V, self.svd_U_autocor, self.svd_V_autocor, svd_start, svd_end)

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

        dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = path, defaultFile = filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name + '.csv'
        else:
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving SVD data', 0)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()

        data = np.column_stack((self.svd_s[svd_start:svd_end+1], self.svd_U_autocor[svd_start:svd_end+1], self.svd_V_autocor[svd_start:svd_end+1]))

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

        dialog = wx.FileDialog(self, message = "Please select save directory and enter save file name", style = wx.FD_SAVE, defaultDir = path, defaultFile = filename)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            name, ext = os.path.splitext(save_path)
            save_path = name + '.csv'
        else:
            return

        RAWGlobals.save_in_progress = True
        self.main_frame.setStatus('Saving SVD data', 0)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()

        svd_data = np.column_stack((self.svd_s[svd_start:svd_end+1], self.svd_U_autocor[svd_start:svd_end+1], self.svd_V_autocor[svd_start:svd_end+1]))

        u_data = self.svd_U[:,svd_start:svd_end+1]
        v_data = self.svd_V[:,svd_start:svd_end+1]

        SASFileIO.saveSVDData(save_path, svd_data, u_data, v_data)

        RAWGlobals.save_in_progress = False
        self.main_frame.setStatus('', 0)


    def _onCancelButton(self, evt):
        self.svd_frame.OnClose()


    def _onOkButton(self, evt):
        svd_dict = {}
        for key in self.control_ids:
            if key != 'profile':
                svd_dict[key] = wx.FindWindowById(self.control_ids[key], self).GetValue()
            else:
                svd_dict[key] = wx.FindWindowById(self.control_ids[key], self).GetStringSelection()


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

        self.svd_frame.OnClose()



class EFAFrame(wx.Frame):

    def __init__(self, parent, title, secm, manip_item):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'EFAFrame', size = (950,750))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'EFAFrame', size = (950,750))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.secm = copy.copy(secm)
        self.manip_item = manip_item

        self.panel = wx.Panel(self, -1, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.splitter_ids = {1  : self.NewControlId(),
                            2   : self.NewControlId(),
                            3   : self.NewControlId()}


        self.panel1_results = {'profile'        : '',
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
                                'use_sub'       : True,
                                'sub_secm'      : None,
                                'ydata_type'    : 'Total',
                                'filename'      : '',
                                'q'             : []}

        self.panel2_results = {'start_points'   : [],
                                'end_points'    : [],
                                'points'        : [],
                                'forward_efa'   : [],
                                'backward_efa'  : []}

        self.panel3_results = {'options'    : {},
                                'steps'     : 0,
                                'iterations': 0,
                                'converged' : False,
                                'ranges'    : [],
                                'profiles'  : [],
                                'conc'      : [],
                                'chisq'     : []}

        self.current_panel = 1


        self._createLayout(self.panel)

        self.CenterOnParent()
        self.Raise()

    def _createLayout(self, parent):

        #Creating the first EFA analysis panel
        self.splitter1 = wx.SplitterWindow(parent, self.splitter_ids[1])

        self.plotPanel1 = SVDResultsPlotPanel(self.splitter1, -1, 'EFAResultsPlotPanel1')
        self.controlPanel1 = EFAControlPanel1(self.splitter1, -1, 'EFAControlPanel1', self.secm, self.manip_item)

        self.splitter1.SplitVertically(self.controlPanel1, self.plotPanel1, 325)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter1.SetMinimumPaneSize(325)    #Back compatability with older wxpython versions
        else:
            self.splitter1.SetMinimumPaneSize(50)

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)


        self.splitter2 = wx.SplitterWindow(parent, self.splitter_ids[2])

        self.plotPanel2 = EFAResultsPlotPanel2(self.splitter2, -1, 'EFAResultsPlotPanel2')
        self.controlPanel2 = EFAControlPanel2(self.splitter2, -1, 'EFAControlPanel2', self.secm, self.manip_item)

        self.splitter2.SplitVertically(self.controlPanel2, self.plotPanel2, 300)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter2.SetMinimumPaneSize(300)    #Back compatability with older wxpython versions
        else:
            self.splitter2.SetMinimumPaneSize(50)

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.splitter2.Fit()


        self.splitter3 = wx.SplitterWindow(parent, self.splitter_ids[3])

        self.plotPanel3 = EFAResultsPlotPanel3(self.splitter3, -1, 'EFAResultsPlotPanel3')
        self.controlPanel3 = EFAControlPanel3(self.splitter3, -1, 'EFAControlPanel3', self.secm, self.manip_item)

        self.splitter3.SplitVertically(self.controlPanel3, self.plotPanel3, 300)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            self.splitter3.SetMinimumPaneSize(300)    #Back compatability with older wxpython versions
        else:
            self.splitter3.SetMinimumPaneSize(50)

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

        button_sizer.Add(self.cancel_button, 0 , wx.LEFT | wx.ALIGN_LEFT,3)
        button_sizer.Add(self.done_button, 0, wx.LEFT | wx.ALIGN_LEFT, 3)
        button_sizer.Add(info_button, 0, wx.LEFT | wx.ALIGN_LEFT, 3)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.back_button, 0, wx.RIGHT | wx.ALIGN_RIGHT, 3)
        button_sizer.Add(self.next_button, 0, wx.RIGHT | wx.ALIGN_RIGHT, 3)

        sl = wx.StaticLine(parent, wx.ID_ANY, style=wx.LI_HORIZONTAL)

        self.top_sizer = wx.BoxSizer(wx.VERTICAL)
        self.top_sizer.Add(self.splitter1, 1, wx.EXPAND | wx.BOTTOM, 3)
        self.top_sizer.Add(self.splitter2, 1, wx.EXPAND | wx.BOTTOM, 3)
        self.top_sizer.Add(self.splitter3, 1, wx.EXPAND | wx.BOTTOM, 3)
        self.top_sizer.Add(sl, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3)
        self.top_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.EXPAND, 3)


        self.top_sizer.Hide(self.splitter2, recursive = True)
        self.top_sizer.Hide(self.splitter3, recursive = True)

        self.panel.SetSizer(self.top_sizer)

        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()


    def _onNextButton(self, evt):

        if self.current_panel == 1:

            self.getPanel1Values()

            if self.panel1_results['input'] != 0:

                if type(self.panel1_results['svd_u']) is not None and not np.any(np.isnan(self.panel1_results['svd_u'])):

                    self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel], self), recursive = True)

                    self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel+1], self), recursive = True)

                    self.current_panel = self.current_panel + 1

                    self.back_button.Enable()

                    efa_panel2 =  wx.FindWindowByName('EFAControlPanel2')

                    if not efa_panel2.initialized:
                        efa_panel2.initialize(self.panel1_results)

                    elif self.panel1_results['fstart'] != efa_panel2.panel1_results['fstart'] or self.panel1_results['fend'] != efa_panel2.panel1_results['fend'] or self.panel1_results['profile'] != efa_panel2.panel1_results['profile']:
                        efa_panel2.reinitialize(self.panel1_results, efa = True)

                    elif  self.panel1_results['input'] != efa_panel2.panel1_results['input']:
                        efa_panel2.reinitialize(self.panel1_results, efa = False)

                else:
                    msg = 'SVD not successful. Either change data range or type, or select a new data set.'
                    dlg = wx.MessageDialog(self, msg, "No Singular Values Found", style = wx.ICON_INFORMATION | wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()

            else:
                msg = 'Please enter the number of significant singular values to use for the evolving factor analysis in the User Input area.'
                dlg = wx.MessageDialog(self, msg, "No Singular Values Selected", style = wx.ICON_INFORMATION | wx.OK)
                dlg.ShowModal()
                dlg.Destroy()

        elif self.current_panel == 2:

            self.getPanel2Values()

            correct = np.all([point[0] < point[1] for point in self.panel2_results['points']])

            if correct:

                self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel], self), recursive = True)

                self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel+1], self), recursive = True)

                self.current_panel = self.current_panel + 1

                self.next_button.Disable()

                self.done_button.Enable()

                efa_panel3 =  wx.FindWindowByName('EFAControlPanel3')

                if not efa_panel3.initialized:
                    efa_panel3.initialize(self.panel1_results, self.panel2_results)

                elif self.panel1_results['fstart'] != efa_panel3.panel1_results['fstart'] or self.panel1_results['fend'] != efa_panel3.panel1_results['fend'] or self.panel1_results['profile'] != efa_panel3.panel1_results['profile'] or self.panel1_results['input'] != efa_panel3.panel1_results['input']:
                    efa_panel3.reinitialize(self.panel1_results, self.panel2_results, rebuild = True)

                elif  np.any(self.panel2_results['points'] != efa_panel3._getRanges()):
                    efa_panel3.reinitialize(self.panel1_results, self.panel2_results, rebuild = False)

            else:
                msg = 'The smallest start value must be less than the smallest end value, the second smallest start value must be less than the second smallest end value, and so on. Please change start and end values according (if necessary, you can further adjust these ranges on the next page).'
                dlg = wx.MessageDialog(self, msg, "Start and End Values Incorrect", style = wx.ICON_INFORMATION | wx.OK)
                dlg.ShowModal()
                dlg.Destroy()


        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

    def _onBackButton(self, evt):

        if self.current_panel == 2:
            self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel], self), recursive = True)

            self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel-1], self), recursive = True)

            self.current_panel = self.current_panel - 1

            self.back_button.Disable()

        elif self.current_panel == 3:
            self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel], self), recursive = True)

            self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel-1], self), recursive = True)

            self.current_panel = self.current_panel - 1

            self.next_button.Enable()

            self.done_button.Disable()

            efa_panel3 =  wx.FindWindowByName('EFAControlPanel3')

            efa_panel2 =  wx.FindWindowByName('EFAControlPanel2')

            points = efa_panel3._getRanges()

            if  np.any(self.panel2_results['points'] != points):
                forward_sv = points[:,0]
                backward_sv = points[:,1]

                if np.all(np.sort(forward_sv) == forward_sv) and np.all(np.sort(backward_sv) == backward_sv):
                    efa_panel2.setSVs(points)


        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

    def _onCancelButton(self, evt):
        self.OnClose()

    def _onDoneButton(self, evt):
        self.getPanel3Values()

        if self.panel3_results['converged']:
            RAWGlobals.mainworker_cmd_queue.put(['to_plot_sasm', [self.panel3_results['profiles'], 'black', None, True]])


        if self.manip_item is not None:
            analysis_dict = self.secm.getParameter('analysis')

            efa_dict = {}

            efa_dict['fstart'] = self.panel1_results['fstart']
            efa_dict['fend'] = self.panel1_results['fend']
            efa_dict['profile'] = self.panel1_results['profile']
            efa_dict['nsvs'] = self.panel1_results['input']
            efa_dict['ranges'] = self.panel3_results['ranges']
            efa_dict['iter_limit'] = self.panel3_results['options']['niter']
            efa_dict['tolerance'] = self.panel3_results['options']['tol']
            efa_dict['method'] = self.panel3_results['options']['method']

            analysis_dict['efa'] = efa_dict

        self.OnClose()

    def _onInfoButton(self, evt):
        msg = 'If you use evolving factor analysis (EFA) in your work, in addition to citing the RAW paper please cite:\nSteve P. Meisburger, Alexander B. Taylor, Crystal A. Khan, Shengnan Zhang, Paul F. Fitzpatrick, and Nozomi Ando. Journal of the American Chemical Society 2016 138 (20), 6506-6516.'
        wx.MessageBox(str(msg), "How to cite EFA", style = wx.ICON_INFORMATION | wx.OK)

    def getPanel1Values(self):
        for key in self.panel1_results:
            if key in self.controlPanel1.control_ids:
                window = wx.FindWindowById(self.controlPanel1.control_ids[key], self.controlPanel1)

                if key != 'profile':
                    value = window.GetValue()

                else:
                    value = window.GetStringSelection()

            elif key == 'int':
                value = self.controlPanel1.i

            elif key == 'err':
                value = self.controlPanel1.err

            elif key == 'svd_u':
                value = self.controlPanel1.svd_U

            elif key == 'svd_s':
                value = self.controlPanel1.svd_s

            elif key == 'svd_v':
                value = self.controlPanel1.svd_V

            elif key == 'svd_int_norm':
                value = self.controlPanel1.svd_a

            elif key =='use_sub':
                profile_window = wx.FindWindowById(self.controlPanel1.control_ids['profile'], self.controlPanel1)

                if profile_window.GetStringSelection() == 'Unsubtracted':
                    value = False
                else:
                    value = True

            elif key == 'sub_secm':
                value = self.controlPanel1.subtracted_secm

            elif key == 'ydata_type':
                value = self.controlPanel1.ydata_type

            elif key == 'filename':
                filename_window = wx.FindWindowById(self.controlPanel1.field_ids['fname'], self.controlPanel1)
                value = filename_window.GetValue()

            elif key == 'q':
                profile_window = wx.FindWindowById(self.controlPanel1.control_ids['profile'], self.controlPanel1)

                if profile_window.GetStringSelection() == 'Unsubtracted':
                    qmin, qmax = self.secm.getSASM().getQrange()
                    value = self.secm.getSASM().q[qmin:qmax]
                else:
                    qmin, qmax = self.secm.getSASM().getQrange()
                    value = self.controlPanel1.subtracted_secm.getSASM().q[qmin:qmax]


            self.panel1_results[key] = value

    def getPanel2Values(self):
        window = wx.FindWindowByName('EFAControlPanel2')

        forward_points = [wx.FindWindowById(my_id, window).GetValue() for my_id in window.forward_ids]
        self.panel2_results['forward_points'] = copy.copy(forward_points)

        backward_points = [wx.FindWindowById(my_id, window).GetValue() for my_id in window.backward_ids]
        self.panel2_results['backward_points'] = copy.copy(backward_points)

        forward_points.sort()
        backward_points.sort()

        points = np.column_stack((forward_points,backward_points))

        self.panel2_results['points'] = points

        self.panel2_results['forward_efa'] = window.efa_forward
        self.panel2_results['backward_efa'] = window.efa_backward


    def getPanel3Values(self):
        window = wx.FindWindowByName('EFAControlPanel3')

        self.panel3_results['steps'] = window.conv_data['steps']
        self.panel3_results['iterations'] = window.conv_data['iterations']
        self.panel3_results['options'] = window.conv_data['options']
        self.panel3_results['steps'] = window.conv_data['steps']

        self.panel3_results['converged'] = window.converged

        if self.panel3_results['converged']:
            self.panel3_results['ranges'] = window._getRanges()
            self.panel3_results['profiles'] = window.sasms
            self.panel3_results['conc'] = window.rotation_data['C']
            self.panel3_results['chisq'] = window.rotation_data['chisq']

    def OnClose(self):

        self.Destroy()

class EFAControlPanel1(wx.Panel):

    def __init__(self, parent, panel_id, name, secm, manip_item):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.svd_frame = wx.FindWindowByName('EFAFrame')

        self.secm = secm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.control_ids = {'profile'   : self.NewControlId(),
                            'fstart'    : self.NewControlId(),
                            'fend'      : self.NewControlId(),
                            'svd_start' : self.NewControlId(),
                            'svd_end'   : self.NewControlId(),
                            'input'     : self.NewControlId()}

        self.field_ids = {'fname'     : self.NewControlId()}

        self.ydata_type = 'total'

        self.svd_U = None
        self.svd_s = None
        self.svd_V = None

        control_sizer = self._createLayout()

        self.SetSizer(control_sizer)

        self.initValues()


    def _createLayout(self):

        top_sizer =wx.BoxSizer(wx.VERTICAL)

        #filename sizer
        box = wx.StaticBox(self, -1, 'Filename')
        filesizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        filenameTxtCtrl = wx.TextCtrl(self, self.field_ids['fname'], '', style = wx.TE_READONLY)

        filesizer.Add(filenameTxtCtrl, 1, wx.ALL, 3)


        #svd controls
        box = wx.StaticBox(self, -1, 'Controls')
        control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #control if you're using unsubtracted or subtracted curves
        label = wx.StaticText(self, -1, 'Use :')
        profile_type = wx.Choice(self, self.control_ids['profile'], choices = ['Unsubtracted', 'Subtracted'])
        profile_type.Bind(wx.EVT_CHOICE, self._onProfileChoice)
        profile_type.SetStringSelection('Subtracted')

        profile_sizer = wx.BoxSizer(wx.HORIZONTAL)
        profile_sizer.Add(label, 0, wx.LEFT | wx.RIGHT, 3)
        profile_sizer.Add(profile_type, 1, wx.RIGHT, 3)

        #control what the range of curves you're using is.
        label1 = wx.StaticText(self, -1, 'Use Frames :')
        label2 = wx.StaticText(self, -1, 'to')
        start_frame = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['fstart'], size = (60,-1))
        end_frame = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['fend'], size = (60,-1))

        start_frame.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeFrame)
        end_frame.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeFrame)

        frame_sizer = wx.BoxSizer(wx.HORIZONTAL)
        frame_sizer.Add(label1, 0, wx.LEFT | wx.RIGHT, 3)
        frame_sizer.Add(start_frame, 0, wx.RIGHT, 3)
        frame_sizer.Add(label2, 0, wx.RIGHT, 3)
        frame_sizer.Add(end_frame, 0, wx.RIGHT, 3)


        #plot the sec data
        sec_plot = SVDSECPlotPanel(self, -1, 'EFASECPlotPanel')


        #SVD control sizer
        control_sizer.Add(profile_sizer, 0,  wx.TOP | wx.EXPAND, 3)
        control_sizer.Add(frame_sizer, 0, wx.TOP | wx.EXPAND, 8)
        control_sizer.Add(sec_plot, 0, wx.TOP | wx.EXPAND, 8)

        if self.manip_item == None:
            control_sizer.Hide(profile_sizer, recursive = True)


        #svd results
        box = wx.StaticBox(self, -1, 'Results')
        results_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #Control plotted SVD range
        label1 = wx.StaticText(self, -1, 'Plot indexes :')
        label2 = wx.StaticText(self, -1, 'to')
        start_svd = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['svd_start'], size = (60,-1))
        end_svd = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['svd_end'], size = (60,-1))

        start_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)
        end_svd.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onChangeSVD)

        svdrange_sizer = wx.BoxSizer(wx.HORIZONTAL)
        svdrange_sizer.Add(label1, 0, wx.LEFT | wx.RIGHT, 3)
        svdrange_sizer.Add(start_svd, 0, wx.RIGHT, 3)
        svdrange_sizer.Add(label2, 0, wx.RIGHT, 3)
        svdrange_sizer.Add(end_svd, 0, wx.RIGHT, 3)

        results_sizer.Add(svdrange_sizer, 0,  wx.TOP | wx.EXPAND, 3)


        #Input number of significant values to use for EFA
        box = wx.StaticBox(self, -1, 'User Input')
        input_sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        label1 = wx.StaticText(self, -1, '# Significant SVs :')
        user_input = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['input'], size = (60,-1))


        input_sizer.Add(label1, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 3)
        input_sizer.Add(user_input, 0, wx.ALL, 3)
        input_sizer.AddStretchSpacer(1)


        top_sizer.Add(filesizer, 0, wx.EXPAND | wx.TOP, 3)
        top_sizer.Add(control_sizer, 0, wx.EXPAND | wx.TOP, 3)
        top_sizer.Add(results_sizer, 0, wx.EXPAND | wx.TOP, 3)
        top_sizer.Add(input_sizer, 0, wx.TOP | wx.BOTTOM | wx.EXPAND, 3)
        top_sizer.AddStretchSpacer(1)

        return top_sizer


    def initValues(self):

        filename = self.secm.getParameter('filename')

        filename_window = wx.FindWindowById(self.field_ids['fname'], self)
        filename_window.SetValue(filename)

        analysis_dict = self.secm.getParameter('analysis')

        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window =wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

        user_input_window = wx.FindWindowById(self.control_ids['input'], self)


        framei = self.secm.frame_list[0]
        framef = self.secm.frame_list[-1]

        framei_window.SetRange((framei, framef))
        framef_window.SetRange((framei, framef))

        svd_start_window.SetRange((0, framef-framei-1))
        svd_end_window.SetRange((1, framef-framei))

        user_input_window.SetValue(0)
        user_input_window.SetRange((0, framef-framei))

        if 'efa' not in analysis_dict:

            if len(self.secm.subtracted_sasm_list)>0:
                frame_start = max(np.where(self.secm.use_subtracted_sasm)[0][0]-100, framei)
                frame_end = min(np.where(self.secm.use_subtracted_sasm)[0][-1]+100, framef)

            else:
                frame_start = framei
                frame_end = framef

            framei_window.SetValue(frame_start)
            framef_window.SetValue(frame_end)

            svd_start_window.SetValue(0)
            svd_end_window.SetValue(min(framef-framei,10))

        else:
            for key in analysis_dict['efa']:
                if key == 'profile':
                    wx.FindWindowById(self.control_ids[key], self).SetStringSelection(analysis_dict['efa'][key])
                elif key == 'nsvs':
                    wx.FindWindowById(self.control_ids['input'], self).SetValue(analysis_dict['efa'][key])
                elif key in self.control_ids:
                     wx.FindWindowById(self.control_ids[key], self).SetValue(analysis_dict['efa'][key])

            svd_start_window.SetValue(0)
            svd_end_window.SetValue(min(framef-framei,10))


        #make a subtracted profile SECM
        if len(self.secm.subtracted_sasm_list)>0:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, self.secm.frame_list, self.secm.getAllParameters())
        else:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, [], self.secm.getAllParameters())

            profile_window = wx.FindWindowById(self.control_ids['profile'], self)
            profile_window.SetStringSelection('Unsubtracted')

        if self.manip_item is not None:
            sec_plot_panel = wx.FindWindowByName('SECPlotPanel')

            self.ydata_type = sec_plot_panel.plotparams['y_axis_display']

            if self.ydata_type == 'qspec':
                q=float(sec_plot_panel.plotparams['secm_plot_q'])
                self.subtracted_secm.I(q)

        self.updateSECPlot()

        self.runSVD()

        if self.svd_U is not None:
            #Attempts to figure out the significant number of singular values
            if user_input_window.GetValue() == 0:
                point1 = 0
                point2 = 0
                point3 = 0

                i = 0
                ratio_found = False

                while i < self.svd_s.shape[0]-1 and not ratio_found:
                    ratio = self.svd_s/self.svd_s[i]

                    if ratio[i+1] > 0.75:
                        point1 = i
                        ratio_found = True

                    i = i +1

                if not ratio_found:
                    point1 = self.svd_s.shape[0]

                u_points = np.where(self.svd_U_autocor > 0.6)[0]
                index_list = []

                if len(u_points) > 0:

                    for i in range(1,len(u_points)):
                        if u_points[i-1] +1 == u_points[i]:
                            index_list.append(i)

                    point2 = len(index_list)

                    if point2 == 0:
                        if u_points[0] == 0:
                            point2 =1
                    else:
                        point2 = point2 + 1


                v_points = np.where(self.svd_V_autocor > 0.6)[0]
                index_list = []

                if len(v_points) > 0:

                    for i in range(1,len(v_points)):
                        if v_points[i-1] +1 == v_points[i]:
                            index_list.append(i)

                    point3 = len(index_list)

                    if point3 == 0:
                        if v_points[0] == 0:
                            point3 =1
                    else:
                        point3 = point3 + 1

                plist = [point1, point2, point3]

                mode, count = stats.mode(plist)

                mode = mode[0]
                count = count[0]

                if count > 1:
                    user_input_window.SetValue(mode)

                elif np.mean(plist) > np.std(plist):
                    user_input_window.SetValue(int(np.mean(plist)))


    #This function is called when the profiles used are changed between subtracted and unsubtracted.
    def _onProfileChoice(self, evt):
        if len(self.subtracted_secm.getAllSASMs()) > 0:
            wx.CallAfter(self.updateSECPlot)
            self.runSVD()

        else:
            msg = 'No subtracted files are available for this series curve. You can create subtracted curves by setting a buffer range in the Sries Control Panel and calculating the parameter values. You will have to reopen the EFA window after doing this.'
            dlg = wx.MessageDialog(self, msg, "No subtracted files", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

            profile_window = wx.FindWindowById(evt.GetId(), self)
            profile_window.SetStringSelection('Unsubtracted')


    #This function is called when the start and end frame range spin controls are modified
    def _onChangeFrame(self, evt):
        id = evt.GetId()

        spin = wx.FindWindowById(id, self)

        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'], self)
        fend_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'], self)

        #Make sure the boundaries don't cross:
        if id == self.control_ids['fstart']:
            max_val = fend_window.GetValue()

            if new_val > max_val-1:
                new_val = max_val - 1
                spin.SetValue(new_val)

        elif id == self.control_ids['fend']:
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
        id = evt.GetId()

        spin = wx.FindWindowById(id, self)

        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'], self)
        fend_window = wx.FindWindowById(self.control_ids['fend'], self)

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

        #Make sure the boundaries don't cross:
        if id == self.control_ids['svd_start']:
            max_val = svd_end_window.GetValue()

            tot = fend_window.GetValue()-fstart_window.GetValue()

            if new_val > tot - 1:
                new_val = tot - 1
                spin.SetValue(new_val)

            elif new_val > max_val-1:
                new_val = max_val - 1
                spin.SetValue(new_val)

        elif id == self.control_ids['svd_end']:
            min_val = svd_start_window.GetValue()

            tot = fend_window.GetValue()-fstart_window.GetValue()

            if new_val > tot:
                new_val = tot
                spin.SetValue(new_val)

            elif new_val < min_val+1:
                new_val = min_val + 1
                spin.SetValue(new_val)

        wx.CallAfter(self.updateSVDPlot)

    def runSVD(self):
        profile_window = wx.FindWindowById(self.control_ids['profile'], self)

        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        if profile_window.GetStringSelection() == 'Unsubtracted':
            secm = self.secm
        else:
            secm = self.subtracted_secm

        sasm_list = secm.getSASMList(framei, framef)

        i = np.array([sasm.i[sasm.getQrange()[0]:sasm.getQrange()[1]] for sasm in sasm_list])
        err = np.array([sasm.err[sasm.getQrange()[0]:sasm.getQrange()[1]] for sasm in sasm_list])

        self.i = i.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose
        self.err = err.T

        err_mean = np.mean(self.err, axis = 1)
        if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
            self.err_avg = np.broadcast_to(err_mean.reshape(err_mean.size,1), self.err.shape)
        else:
            self.err_avg = np.array([err_mean for k in range(self.i.shape[1])]).T

        self.svd_a = self.i/self.err_avg

        try:
            self.svd_U, self.svd_s, svd_Vt = np.linalg.svd(self.svd_a, full_matrices = True)
        except:
            wx.CallAfter(wx.MessageBox, 'Initial SVD did not converge, so EFA cannot proceed.', 'SVD Failed', style = wx.ICON_ERROR | wx.OK)
            return

        self.svd_V = svd_Vt.T
        self.svd_U_autocor = np.abs(np.array([np.correlate(self.svd_U[:,k], self.svd_U[:,k], mode = 'full')[-self.svd_U.shape[0]+1] for k in range(self.svd_U.shape[1])]))
        self.svd_V_autocor = np.abs(np.array([np.correlate(self.svd_V[:,k], self.svd_V[:,k], mode = 'full')[-self.svd_V.shape[0]+1] for k in range(self.svd_V.shape[1])]))

        wx.CallAfter(self.updateSVDPlot)

    def updateSECPlot(self):

        plotpanel = wx.FindWindowByName('EFASECPlotPanel')
        framei_window = wx.FindWindowById(self.control_ids['fstart'], self)
        framef_window = wx.FindWindowById(self.control_ids['fend'], self)

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        profile_window = wx.FindWindowById(self.control_ids['profile'], self)

        if profile_window.GetStringSelection() == 'Unsubtracted':
            plotpanel.plotSECM(self.secm, framei, framef, self.ydata_type)
        else:
            plotpanel.plotSECM(self.subtracted_secm, framei, framef, self.ydata_type)

    def updateSVDPlot(self):

        if self.svd_s is not None and not np.any(np.isnan(self.svd_s)):
            plotpanel = wx.FindWindowByName('EFAResultsPlotPanel1')

            svd_start_window = wx.FindWindowById(self.control_ids['svd_start'], self)
            svd_end_window = wx.FindWindowById(self.control_ids['svd_end'], self)

            svd_start = svd_start_window.GetValue()
            svd_end = svd_end_window.GetValue()

            plotpanel.plotSVD(self.svd_U, self.svd_s, self.svd_V, self.svd_U_autocor, self.svd_V_autocor, svd_start, svd_end)


class EFAControlPanel2(wx.Panel):

    def __init__(self, parent, panel_id, name, secm, manip_item):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.efa_frame = wx.FindWindowByName('EFAFrame')

        self.secm = secm

        self.manip_item = manip_item
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.initialized = False

        control_sizer = self._createLayout()

        self.SetSizer(control_sizer)


    def _createLayout(self):

        self.top_efa = wx.ScrolledWindow(self, -1)
        self.top_efa.SetScrollRate(20,20)

        top_sizer =wx.BoxSizer(wx.VERTICAL)


        #svd controls
        box = wx.StaticBox(self.top_efa, -1, 'User Input')
        control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        self.forward_sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self.top_efa, -1, 'Forward ')

        self.forward_sizer.Add(label, 0)


        self.backward_sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self.top_efa, -1, 'Backward :')

        self.backward_sizer.Add(label, 0)


        control_sizer.Add(self.forward_sizer, 0, wx.EXPAND | wx.TOP, 3)
        control_sizer.Add(self.backward_sizer, 0, wx.EXPAND | wx.TOP, 3)

        self.top_efa.SetSizer(control_sizer)

        top_sizer.Add(self.top_efa, 1, wx.EXPAND)
        # top_sizer.AddStretchSpacer(1)

        return top_sizer


    def initialize(self, svd_results):
        self.panel1_results = copy.copy(svd_results)

        analysis_dict = self.secm.getParameter('analysis')

        nvals = svd_results['input']

        self.forward_ids = [self.NewControlId() for i in range(nvals)]
        self.backward_ids = [self.NewControlId() for i in range(nvals)]

        self.fsizer = wx.FlexGridSizer(cols = 2, rows = nvals, vgap = 3, hgap = 3)
        self.bsizer = wx.FlexGridSizer(cols = 2, rows = nvals, vgap = 3, hgap = 3)

        start = svd_results['fstart']
        end = svd_results['fend']

        for i in range(nvals):

            flabel = wx.StaticText(self.top_efa, -1, 'Value %i start :' %(i))
            fcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.forward_ids[i], size = (60, -1))
            fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onForwardControl)
            fcontrol.SetValue(start+i)
            fcontrol.SetRange((start+i,end))

            self.fsizer.Add(flabel, 0)
            self.fsizer.Add(fcontrol, 0)

            blabel = wx.StaticText(self.top_efa, -1, 'Value %i start :' %(i))
            bcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.backward_ids[i], size = (60, -1))
            bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onBackwardControl)
            bcontrol.SetValue(start)
            bcontrol.SetRange((start,end-i))

            self.bsizer.Add(blabel, 0)
            self.bsizer.Add(bcontrol, 0)


        self.forward_sizer.Add(self.fsizer, 0, wx.TOP, 3)
        self.backward_sizer.Add(self.bsizer, 0, wx.TOP, 3)

        busy_dialog = wx.BusyInfo('Running EFA', self.efa_frame)

        self.efa_forward = self.runEFA('forward')
        self.efa_backward = self.runEFA('backward')

        busy_dialog.Destroy()
        busy_dialog = None

        if 'efa' in analysis_dict:
            if nvals == analysis_dict['efa']['nsvs'] and self.panel1_results['fstart'] == analysis_dict['efa']['fstart'] and self.panel1_results['fend'] == analysis_dict['efa']['fend'] and self.panel1_results['profile'] == analysis_dict['efa']['profile']:
                points = analysis_dict['efa']['ranges']

                forward_sv = points[:,0]
                backward_sv = points[:,1]

                if np.all(np.sort(forward_sv) == forward_sv) and np.all(np.sort(backward_sv) == backward_sv):
                    self.setSVs(points)
                else:
                    self._findEFAPoints()
            else:
                self._findEFAPoints()
        else:
            self._findEFAPoints()

        self.initialized = True

        wx.CallAfter(self.updateEFAPlot)

    def reinitialize(self, svd_results, efa):
        self.panel1_results = copy.copy(svd_results)

        nvals = svd_results['input']

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

        self.fsizer = wx.FlexGridSizer(cols = 2, rows = nvals, vgap = 3, hgap = 3)
        self.bsizer = wx.FlexGridSizer(cols = 2, rows = nvals, vgap = 3, hgap = 3)

        for i in range(nvals):

            flabel = wx.StaticText(self.top_efa, -1, 'Value %i start :' %(i))
            fcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.forward_ids[i], size = (60, -1))
            fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onForwardControl)
            fcontrol.SetValue(start+i)
            fcontrol.SetRange((start+i,end))

            self.fsizer.Add(flabel, 0)
            self.fsizer.Add(fcontrol, 0)

            blabel = wx.StaticText(self.top_efa, -1, 'Value %i end :' %(i))
            bcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.backward_ids[i], size = (60, -1))
            bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onBackwardControl)
            bcontrol.SetValue(start)
            bcontrol.SetRange((start,end-i))

            self.bsizer.Add(blabel, 0)
            self.bsizer.Add(bcontrol, 0)


        self.forward_sizer.Add(self.fsizer, 0, wx.TOP, 3)
        self.backward_sizer.Add(self.bsizer, 0, wx.TOP, 3)

        self.forward_sizer.Layout()
        self.backward_sizer.Layout()
        self.top_efa.Layout()
        self.Layout()

        if efa:
            busy_dialog = wx.BusyInfo('Running EFA', self.efa_frame)

            self.efa_forward = self.runEFA('forward')
            self.efa_backward = self.runEFA('backward')

            busy_dialog.Destroy()
            busy_dialog = None

        self._findEFAPoints()

        plotpanel = wx.FindWindowByName('EFAResultsPlotPanel2')
        plotpanel.refresh()

        wx.CallAfter(self.updateEFAPlot)

    def _onForwardControl(self, evt):
        self.updateEFAPlot()

    def _onBackwardControl(self, evt):
        self.updateEFAPlot()

    def setSVs(self, points):
        for i in range(len(points)):
            forward = wx.FindWindowById(self.forward_ids[i], self)
            backward = wx.FindWindowById(self.backward_ids[len(self.backward_ids)-1-i], self)

            forward.SetValue(points[i][0])
            backward.SetValue(points[i][1])

        wx.CallAfter(self.updateEFAPlot)

    def _findEFAPoints(self):

        forward_windows = [wx.FindWindowById(my_id, self) for my_id in self.forward_ids]

        backward_windows = [wx.FindWindowById(my_id, self) for my_id in self.backward_ids]

        start_offset = self.panel1_results['fstart']

        old_value = start_offset

        for i in range(len(forward_windows)):
            if int(forward_windows[i].GetValue()) == int( start_offset+i):
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
                    print e


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
                    print e



    def runEFA(self, mode):
        A = self.panel1_results['svd_int_norm']

        slist = np.zeros_like(A)

        jmax = A.shape[1]

        if mode.lower() == 'backward':
            A = A[:,::-1]

        for j in range(jmax):
            s = np.linalg.svd(A[:, :j+1], full_matrices = False, compute_uv = False)
            slist[:s.size, j] = s

        return slist

    def updateEFAPlot(self):
        plotpanel = wx.FindWindowByName('EFAResultsPlotPanel2')

        nvals = self.panel1_results['input']+1

        forward_points = [wx.FindWindowById(my_id, self).GetValue() for my_id in self.forward_ids]

        backward_points = [wx.FindWindowById(my_id, self).GetValue() for my_id in self.backward_ids]

        forward_data = {'slist' : self.efa_forward[:nvals, :],
                        'index' : np.arange(len(self.efa_forward[0]))+self.panel1_results['fstart'],
                        'points': forward_points}

        backward_data = {'slist': self.efa_backward[:nvals, ::-1],
                        'index' : np.arange(len(self.efa_backward[0]))+self.panel1_results['fstart'],
                        'points': backward_points}

        plotpanel.plotEFA(forward_data, backward_data)


class EFAResultsPlotPanel2(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

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

        subplotLabels = [('Forward EFA', 'Index', 'Singular Value', 0.1), ('Backward EFA', 'Index', 'Singular Value', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Forward EFA']
        b = self.subplots['Backward EFA']

        self.f_background = self.canvas.copy_from_bbox(a.bbox)
        self.b_background = self.canvas.copy_from_bbox(b.bbox)

        if len(self.f_lines)>0:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_forward_data, self.orig_backward_data)
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

        if (int(matplotlib.__version__.split('.')[0]) ==1 and int(matplotlib.__version__.split('.')[1]) >=5) or int(matplotlib.__version__.split('.')[0]) > 1:
            a.set_prop_cycle(None)
            b.set_prop_cycle(None)
        else:
            a.set_color_cycle(None)
            b.set_color_cycle(None)

    def plotEFA(self, forward_data, backward_data):

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(forward_data, backward_data)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

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
                line, = a.semilogy(index, f_slist[j], label = 'SV %i' %(j), animated = True)
                self.f_lines.append(line)

            for j in range(len(f_points)):
                point, = a.semilogy(f_points[j], f_slist[j][fp_index[j]], 'o', markeredgewidth = 2, markeredgecolor = self.f_lines[j].get_color(), markerfacecolor='none', markersize = 8, label = '_nolegend_', animated = True)
                self.f_markers.append(point)

            for k in range(b_slist.shape[0]):
                line, = b.semilogy(index, b_slist[k], label = 'SV %i' %(k), animated = True)
                self.b_lines.append(line)

            for k in range(len(b_points)):
                point, = b.semilogy(b_points[k], b_slist[k][bp_index[k]], 'o', markeredgewidth = 2, markeredgecolor = self.b_lines[k].get_color(), markerfacecolor='none', markersize = 8, label = '_nolegend_', animated = True)
                self.b_markers.append(point)

            a.legend(fontsize = 12, loc = 'upper left')
            b.legend(fontsize = 12)

            self.canvas.draw()
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

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()
        b_oldx = b.get_xlim()
        b_oldy = b.get_ylim()

        a.relim()
        a.autoscale_view()

        b.relim()
        b.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()
        b_newx = b.get_xlim()
        b_newy = b.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy or b_newx != b_oldx or b_newy != b_oldy:
            self.canvas.draw()

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



class EFAControlPanel3(wx.Panel):

    def __init__(self, parent, panel_id, name, secm, manip_item):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.efa_frame = wx.FindWindowByName('EFAFrame')

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

        control_sizer = self._createLayout()

        self.SetSizer(control_sizer)


    def _createLayout(self):

        self.top_efa = wx.ScrolledWindow(self, -1)
        self.top_efa.SetScrollRate(20,20)

        top_sizer =wx.BoxSizer(wx.VERTICAL)

        sec_plot = EFARangePlotPanel(self, -1, 'EFARangePlotPanel')

        #svd controls
        box = wx.StaticBox(self.top_efa, -1, 'Component Range Controls')
        self.peak_control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        self.top_efa.SetSizer(self.peak_control_sizer)


        box = wx.StaticBox(self, -1, 'Rotation Controls')
        iter_control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        grid_sizer = wx.FlexGridSizer(cols = 2, rows = 3, vgap =3, hgap =3)

        method_label = wx.StaticText(self, -1, 'Method :')
        method_control = wx.Choice(self, self.control_ids['method'], choices = ['Hybrid', 'Iterative', 'Explicit'])
        method_control.SetStringSelection('Hybrid')
        method_control.Bind(wx.EVT_CHOICE, self._onIterControl)

        grid_sizer.Add(method_label)
        grid_sizer.Add(method_control)


        num_label = wx.StaticText(self, -1, 'Number of iterations :')

        num_control = RAWCustomCtrl.IntSpinCtrl(self, self.control_ids['n_iter'], size = (60,-1))
        num_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onIterControl)
        num_control.SetValue(str(self.control_values['n_iter']))
        num_control.SetRange((1, 1e12))

        grid_sizer.Add(num_label, 0)
        grid_sizer.Add(num_control, 1)


        tol_label = wx.StaticText(self, -1, 'Convergence threshold :')

        tol_control = RAWCustomCtrl.FloatSpinCtrl(self, self.control_ids['tol'], size = (60,-1), never_negative = True)
        tol_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onIterControl)
        tol_control.SetValue(str(self.control_values['tol']))

        grid_sizer.Add(tol_label, 0)
        grid_sizer.Add(tol_control, 1)

        iter_control_sizer.Add(grid_sizer, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 3)


        box = wx.StaticBox(self, -1, 'Status')
        status_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        status_label = wx.StaticText(self, self.control_ids['status'], '')

        status_sizer.Add(status_label,0, wx.ALL, 3)


        box = wx.StaticBox(self, -1, 'Results')
        results_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        save_results = wx.Button(self, self.control_ids['save_results'], 'Save EFA Data (not profiles)')
        save_results.Bind(wx.EVT_BUTTON, self._onSaveButton)

        # button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # button_sizer.Add(save_results, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 3)

        results_sizer.Add(save_results, 0, wx.ALIGN_CENTER_HORIZONTAL)


        top_sizer.Add(sec_plot, 0, wx.ALL | wx.EXPAND, 3)
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

        self.range_ids = [(self.NewControlId(), self.NewControlId(), self.NewControlId()) for i in range(nvals)]

        self.range_sizer = wx.FlexGridSizer(cols = 5, rows = nvals, vgap = 3, hgap = 3)

        start = svd_results['fstart']
        end = svd_results['fend']

        points = efa_results['points']

        for i in range(nvals):

            label1 = wx.StaticText(self.top_efa, -1, 'Range %i :' %(i))
            fcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.range_ids[i][0], size = (60, -1))
            fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
            fcontrol.SetValue(points[i][0])
            fcontrol.SetRange((start+i,points[i][1]-1))

            self.range_sizer.Add(label1, 0, wx.LEFT, 3)
            self.range_sizer.Add(fcontrol, 0)

            label2 = wx.StaticText(self.top_efa, -1, 'to')
            bcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.range_ids[i][1], size = (60, -1))
            bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
            bcontrol.SetValue(points[i][1])
            bcontrol.SetRange((points[i][0]+1,end-(nvals-1-i)))

            self.range_sizer.Add(label2, 0)
            self.range_sizer.Add(bcontrol, 0)

            force_pos = wx.CheckBox(self.top_efa, self.range_ids[i][2], 'C>=0')
            force_pos.Bind(wx.EVT_CHECKBOX, self._onRangeControl)
            force_pos.SetValue(True)

            self.range_sizer.Add(force_pos, 0)


        self.peak_control_sizer.Add(self.range_sizer, 0, wx.TOP, 3)

        if 'efa' in analysis_dict:
            efa_dict = analysis_dict['efa']
            if efa_dict['fstart'] == self.panel1_results['fstart'] and efa_dict['fend'] == self.panel1_results['fend'] and efa_dict['profile'] == self.panel1_results['profile'] and efa_dict['nsvs'] == self.panel1_results['input'] and np.all(efa_dict['ranges'] == self._getRanges()):

                keylist = ['n_iter', 'tol', 'method']

                for key in keylist:
                    if key in efa_dict and key in self.control_ids:
                        window = wx.FindWindowById(self.control_ids[key])

                        if key != 'method':
                            try:
                                window.SetValue(str(efa_dict[key]))
                            except Exception as e:
                                print e
                        else:
                            try:
                                window.SetStringSelection(str(efa_dict[key]))
                            except Exception as e:
                                print e

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

            self.range_ids = [(self.NewControlId(), self.NewControlId(), self.NewControlId()) for i in range(nvals)]

            self.range_sizer = wx.FlexGridSizer(cols = 5, rows = nvals, vgap = 3, hgap = 3)

            start = svd_results['fstart']
            end = svd_results['fend']

            points = efa_results['points']

            for i in range(nvals):

                label1 = wx.StaticText(self.top_efa, -1, 'Range %i :' %(i))
                fcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.range_ids[i][0], size = (60, -1))
                fcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
                fcontrol.SetValue(points[i][0])
                fcontrol.SetRange((start+i,points[i][1]-1))

                self.range_sizer.Add(label1, 0, wx.LEFT, 3)
                self.range_sizer.Add(fcontrol, 0)

                label2 = wx.StaticText(self.top_efa, -1, 'to')
                bcontrol = RAWCustomCtrl.IntSpinCtrl(self.top_efa, self.range_ids[i][1], size = (60, -1))
                bcontrol.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onRangeControl)
                bcontrol.SetValue(points[i][1])
                bcontrol.SetRange((points[i][0]+1,end-i))

                self.range_sizer.Add(label2, 0)
                self.range_sizer.Add(bcontrol, 0)

                force_pos = wx.CheckBox(self.top_efa, self.range_ids[i][2], 'C>=0')
                force_pos.Bind(wx.EVT_CHECKBOX, self._onRangeControl)
                force_pos.SetValue(True)

                self.range_sizer.Add(force_pos, 0)


            self.peak_control_sizer.Add(self.range_sizer, 0, wx.TOP, 3)

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

        plotpanel = wx.FindWindowByName('EFAResultsPlotPanel3')
        plotpanel.refresh()

        plotpanel = wx.FindWindowByName('EFARangePlotPanel')
        plotpanel.refresh()

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

        myId = evt.GetId()

        for ids in self.range_ids:
            if myId in ids:

                if myId == ids[0]:
                    spinctrl = wx.FindWindowById(ids[1], self)

                    current_range = spinctrl.GetRange()

                    new_range = (int(evt.GetValue())+1, current_range[1])

                    spinctrl.SetRange(new_range)

                    wx.CallAfter(self.updateRangePlot)

                elif myId == ids[1]:
                    spinctrl = wx.FindWindowById(ids[0], self)

                    current_range = spinctrl.GetRange()

                    new_range = (current_range[0],int(evt.GetValue())-1)

                    spinctrl.SetRange(new_range)

                    wx.CallAfter(self.updateRangePlot)

                break

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
        else:
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


    def updateRotation(self, M,C,D):
        S = np.dot(D, np.linalg.pinv(np.transpose(M*C)))

        Cnew = np.transpose(np.dot(np.linalg.pinv(S), D))

        for i in range(len(self.range_ids)):
            window = wx.FindWindowById(self.range_ids[i][2], self)
            if window.GetValue():
                Cnew[Cnew[:,i] < 0,i] = 0

        csum = np.sum(M*Cnew, axis = 0)
        if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
            Cnew = Cnew/np.broadcast_to(csum, Cnew.shape) #normalizes by the sum of each column
        else:
            norm = np.array([csum for i in range(Cnew.shape[0])])

            Cnew = Cnew/norm #normalizes by the sum of each column

        return Cnew

    def firstRotation(self, M,C,D):
        #Have to run an initial rotation without forcing C>=0 or things typically fail to converge (usually the SVD fails)
        S = np.dot(D, np.linalg.pinv(np.transpose(M*C)))

        Cnew = np.transpose(np.dot(np.linalg.pinv(S), D))

        csum = np.sum(M*Cnew, axis = 0)
        if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
            Cnew = Cnew/np.broadcast_to(csum, Cnew.shape) #normalizes by the sum of each column
        else:
            norm = np.array([csum for i in range(Cnew.shape[0])])

            Cnew = Cnew/norm #normalizes by the sum of each column

        return Cnew

    def _initIterative(self, M, num_sv, D):

        #Set a variable to test whether the rotation fails for a numerical reason
        failed = False

        if not self.converged:
            C = self.panel1_results['svd_v'][:,:num_sv]
        else:
            C = self.rotation_data['C']

        #Do an initial rotation
        try:
            C = self.firstRotation(M, C, D)
        except np.linalg.linalg.LinAlgError:
            failed = True

        return failed, C, None, None

    def _initExplicit(self, M, num_sv, D):
        V_bar = self.panel1_results['svd_v'][:,:num_sv]

        T = np.ones((num_sv, num_sv))

        failed = False

        return failed, None, V_bar, T

    def _initHybrid(self, M, num_sv, D):

        if not self.converged:
            failed, temp, V_bar, T = self._initExplicit(M, num_sv, D)
            C, failed, temp1, temp2, temp3 = self._runExplicit(M, None, None, None, V_bar, T)
        else:
            C = self.rotation_data['C']
            failed = False

        return failed, C, None, None

    def _runIterative(self, *args):
        M = args[0]
        D = args[1]
        failed = args[2]
        C = args[3]

        niter = int(wx.FindWindowById(self.control_ids['n_iter'], self).GetValue())
        tol = float(wx.FindWindowById(self.control_ids['tol'], self).GetValue())

        #Carry out the calculation to convergence
        k = 0
        converged = False

        dc = []

        while k < niter and not converged and not failed:
            k = k+1
            try:
                Cnew = self.updateRotation(M, C, D)
            except np.linalg.linalg.LinAlgError:
               failed = True

            dck = np.sum(np.abs(Cnew - C))

            dc.append(dck)

            C = Cnew

            if dck < tol:
                converged = True

        return C, failed, converged, dc, k

    def _runExplicit(self, *args):
        M = args[0]
        # D = args[1]
        failed = args[2]
        V_bar = args[4]
        T = args[5]

        num_sv = M.shape[1]

        for i in range(num_sv):
            V_i_0 = V_bar[np.logical_not(M[:,i]),:]

            T[i,1:num_sv] = -np.dot(V_i_0[:,0].T, np.linalg.pinv(V_i_0[:,1:num_sv].T))

        C = np.dot(T, V_bar.T)

        C = C.T

        if -1*C.min() > C.max():
            C = C*-1

        converged = True

        csum = np.sum(M*C, axis = 0)
        if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
            C = C/np.broadcast_to(csum, C.shape) #normalizes by the sum of each column
        else:
            norm = np.array([csum for i in range(C.shape[0])])

            C = C/norm #normalizes by the sum of each column

        return C, failed, converged, None, None


    def runRotation(self):
        #Get component ranges and iteration control values
        self._updateStatus(True)

        ranges = self._getRanges()

        start = self.panel1_results['fstart']

        ranges = ranges - start

        niter = int(wx.FindWindowById(self.control_ids['n_iter'], self).GetValue())
        tol = float(wx.FindWindowById(self.control_ids['tol'], self).GetValue())
        method = wx.FindWindowById(self.control_ids['method'], self).GetStringSelection()

        init_dict = {'Hybrid'       : self._initHybrid,
                    'Iterative'     : self._initIterative,
                    'Explicit'      : self._initExplicit}

        run_dict = {'Hybrid'        : self._runIterative,
                    'Iterative'     : self._runIterative,
                    'Explicit'      : self._runExplicit}

        #Calculate the initial matrices
        num_sv = ranges.shape[0]

        D = self.panel1_results['svd_int_norm']

        M = np.zeros_like(self.panel1_results['svd_v'][:,:num_sv])

        for j in range(num_sv):
            M[ranges[j][0]:ranges[j][1]+1, j] = 1

        if self.converged and M.shape[0] != self.rotation_data['C'].shape[0]:
            self.converged = False
            self.rotation_data = {}

        init_results = init_dict[method](M, num_sv, D) #Init takes M, num_sv, and D, and returns failed, C, V_bar, T in that order. If a method doesn't use a particular variable, then it should return None for that result

        C, failed, converged, dc, k = run_dict[method](M, D, init_results[0], init_results[1], init_results[2], init_results[3]) #Takes M, D, failed, C, V_bar, T in that order. If a method doesn't use a particular variable, then it should be passed None for that variable.


        if not failed:
            if method != 'Explicit':
                self.conv_data = {'steps'   : dc,
                                'iterations': k,
                                'final_step': dc[-1],
                                'options'   : {'niter': niter, 'tol': tol, 'method': method}}
            else:
                self.conv_data = {'steps'   : None,
                                'iterations': None,
                                'final_step': None,
                                'options'   : {'niter': niter, 'tol': tol, 'method': method}}

        #Check whether the calculation converged

        if method != 'Explicit':
            if k == niter and dc[-1] > tol:
                self.converged = False
                self.fail_text = 'Rotataion failed to converge after %i\n iterations with final delta = %.2E.' %(k, dc[-1])
            elif failed:
                self.converged = False
                self.fail_text = 'Rotataion failed due to a numerical error\n in the algorithm. Try adjusting ranges or changing method.'
            else:
                self.converged = True

        else:
            if failed:
                self.converged = False
                self.fail_text = 'Rotataion failed due to a numerical error\n in the algorithm. Try adjusting ranges or changing method.'
            else:
                self.converged = True

        if self.converged:
            #Calculate SAXS basis vectors
            mult = np.linalg.pinv(np.transpose(M*C))
            intensity = np.dot(self.panel1_results['int'], mult)
            err = np.sqrt(np.dot(np.square(self.panel1_results['err']), np.square(mult)))

            int_norm = np.dot(D, mult)
            resid = D - np.dot(int_norm, np.transpose(M*C))

            chisq = np.mean(np.square(resid),0)

            #Save the results
            self.rotation_data = {'M'   : M,
                                'C'     : C,
                                'int'   : intensity,
                                'err'   : err,
                                'chisq' : chisq}


            wx.CallAfter(self.updateResultsPlot)

            self._makeSASMs()

        else:
            wx.CallAfter(self.clearResultsPlot)

        wx.CallAfter(self._updateStatus)

    def _getRanges(self):
        ranges = []

        for my_ids in self.range_ids:
            ranges.append([wx.FindWindowById(my_ids[0], self).GetValue(), wx.FindWindowById(my_ids[1], self).GetValue()])

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

        for i in range(nprofiles):
            old_sasm = self.secm.getSASM()
            q = old_sasm.q

            qmin, qmax = old_sasm.getQrange()

            q = q[qmin:qmax]

            intensity = self.rotation_data['int'][:,i]

            err = self.rotation_data['err'][:,i]

            sasm = SASM.SASM(intensity, q, err, {})

            sasm.setParameter('filename', old_filename+'_%i' %(i))

            history_dict = {}

            history_dict['input_filename'] = self.panel1_results['filename']
            history_dict['start_index'] = str(self.panel1_results['fstart'])
            history_dict['end_index'] = str(self.panel1_results['fend'])
            history_dict['component_number'] = str(i)

            points = self._getRanges()[i]
            history_dict['component_range'] = '[%i, %i]' %(points[0], points[1])

            history = sasm.getParameter('history')
            history['EFA'] = history_dict

            self.sasms[i] = sasm


    def updateRangePlot(self):
        plotpanel = wx.FindWindowByName('EFARangePlotPanel')

        ydata_type = self.panel1_results['ydata_type']

        if self.panel1_results['use_sub']:
            plot_secm = self.panel1_results['sub_secm']
        else:
            plot_secm = self.secm

        framei = self.panel1_results['fstart']
        framef = self.panel1_results['fend']

        ranges = self._getRanges()

        plotpanel.plotRange(plot_secm, framei, framef, ydata_type, ranges)

    def updateResultsPlot(self):
        plotpanel = wx.FindWindowByName('EFAResultsPlotPanel3')

        framei = self.panel1_results['fstart']
        framef = self.panel1_results['fend']

        rmsd_data = [self.rotation_data['chisq'], range(framei, framef+1)]

        conc_data = [self.rotation_data['C'], range(framei, framef+1)]

        plotpanel.plotEFA(self.sasms, rmsd_data, conc_data)

    def clearResultsPlot(self):
        plotpanel = wx.FindWindowByName('EFAResultsPlotPanel3')

        plotpanel.refresh()

        plotpanel.canvas.draw()


class EFAResultsPlotPanel3(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        self.fig = Figure((5,4), 75)

        self.a_lines = []
        self.b_lines = []
        self.c_lines = []

        subplotLabels = [('Scattering Profiles', 'q ($\AA^{-1}$)', 'I', 0.1), ('Mean Error Weighted $\chi^2$', 'Index', '$\chi^2$', 0.1), ('Concentration', 'Index', 'Arb.', 0.1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        subplot = self.fig.add_subplot(2, 2, (1,2), title = subplotLabels[0][0], label = subplotLabels[0][0])
        subplot.set_xlabel(subplotLabels[0][1])
        subplot.set_ylabel(subplotLabels[0][2])
        self.subplots[subplotLabels[0][0]] = subplot

        subplot = self.fig.add_subplot(2, 2, 3, title = subplotLabels[1][0], label = subplotLabels[1][0])
        subplot.set_xlabel(subplotLabels[1][1])
        subplot.set_ylabel(subplotLabels[1][2])
        self.subplots[subplotLabels[1][0]] = subplot

        subplot = self.fig.add_subplot(2, 2, 4, title = subplotLabels[2][0], label = subplotLabels[2][0])
        subplot.set_xlabel(subplotLabels[2][1])
        subplot.set_ylabel(subplotLabels[2][2])
        self.subplots[subplotLabels[2][0]] = subplot

        # for i in range(0, len(subplotLabels)):
        #     subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
        #     subplot.set_xlabel(subplotLabels[i][1])
        #     subplot.set_ylabel(subplotLabels[i][2])
        #     self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26, wspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']

        self.a_background = self.canvas.copy_from_bbox(a.bbox)
        self.b_background = self.canvas.copy_from_bbox(b.bbox)
        self.c_background = self.canvas.copy_from_bbox(c.bbox)

        if len(self.a_lines)>0:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_profile_data, self.orig_rmsd_data, self.orig_conc_data)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def refresh(self):
        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']

        self.a_lines = []
        self.b_lines = []
        self.c_lines = []

        while len(a.lines) != 0:
            a.lines.pop(0)

        while len(b.lines) != 0:
            b.lines.pop(0)

        while len(c.lines) != 0:
            c.lines.pop(0)

        if (int(matplotlib.__version__.split('.')[0]) ==1 and int(matplotlib.__version__.split('.')[1]) >=5) or int(matplotlib.__version__.split('.')[0]) > 1:
            a.set_prop_cycle(None)
            b.set_prop_cycle(None)
            c.set_prop_cycle(None)
        else:
            a.set_color_cycle(None)
            b.set_color_cycle(None)
            c.set_color_cycle(None)

    def plotEFA(self, profile_data, rmsd_data, conc_data):

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(profile_data, rmsd_data, conc_data)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, profile_data, rmsd_data, conc_data):
        #Save for resizing:
        self.orig_profile_data = profile_data
        self.orig_rmsd_data = rmsd_data
        self.orig_conc_data = conc_data

        a = self.subplots['Scattering Profiles']
        b = self.subplots['Mean Error Weighted $\chi^2$']
        c = self.subplots['Concentration']


        if len(self.a_lines) == 0:

            for j in range(len(profile_data)):
                line, = a.semilogy(profile_data[j].q, profile_data[j].i, label = 'Range %i' %(j), animated = True)
                self.a_lines.append(line)

            line, = b.plot(rmsd_data[1], rmsd_data[0], animated = True)

            self.b_lines.append(line)

            for j in range(conc_data[0].shape[1]):
                line, = c.plot(conc_data[1], conc_data[0][:,j], animated = True)
                self.c_lines.append(line)


            a.legend(fontsize = 12)

            self.canvas.draw()
            self.a_background = self.canvas.copy_from_bbox(a.bbox)
            self.b_background = self.canvas.copy_from_bbox(b.bbox)
            self.c_background = self.canvas.copy_from_bbox(c.bbox)

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
                line.set_xdata(conc_data[1])
                line.set_ydata(conc_data[0][:,j])

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()
        b_oldx = b.get_xlim()
        b_oldy = b.get_ylim()
        c_oldx = c.get_xlim()
        c_oldy = c.get_ylim()

        a.relim()
        a.autoscale_view()

        b.relim()
        b.autoscale_view()

        c.relim()
        c.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()
        b_newx = b.get_xlim()
        b_newy = b.get_ylim()
        c_newx = c.get_xlim()
        c_newy = c.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy or b_newx != b_oldx or b_newy != b_oldy or c_newx != c_oldx or c_newy != c_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.a_background)

        for line in self.a_lines:
            a.draw_artist(line)


        self.canvas.restore_region(self.b_background)

        for line in self.b_lines:
            b.draw_artist(line)


        self.canvas.restore_region(self.c_background)

        for line in self.c_lines:
            c.draw_artist(line)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)
        self.canvas.blit(c.bbox)


class EFARangePlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER, size = (275,300))

        main_frame = wx.FindWindowByName('MainFrame')

        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        if (int(matplotlib.__version__.split('.')[0]) ==1 and int(matplotlib.__version__.split('.')[1]) >=5) or int(matplotlib.__version__.split('.')[0]) > 1:
            self.fig = Figure((4,4), 75)
        else:
            self.fig = Figure((275./75,4), dpi = 75)

        self.cut_line = None
        self.range_arrows = []
        self.range_lines = []

        subplotLabels = [('SECPlot', 'Frame #', 'Intensity', .1)]

        self.fig.subplots_adjust(hspace = 0.26)

        self.subplots = {}

        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot

        self.fig.subplots_adjust(left = 0.18, bottom = 0.13, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        a = self.subplots['SECPlot']
        # b = self.subplots['Data/Fit']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        # self.err_background = self.canvas.copy_from_bbox(b.bbox)

        if self.cut_line is not None:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_frame_list, self.orig_intensity, self.orig_framei, self.orig_framef, self.orig_ranges)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def refresh(self):
        a = self.subplots['SECPlot']

        self.range_lines = []
        self.range_arrows = []
        self.cut_line = None

        while len(a.lines) != 0:
            a.lines.pop(0)

        if (int(matplotlib.__version__.split('.')[0]) ==1 and int(matplotlib.__version__.split('.')[1]) >=5) or int(matplotlib.__version__.split('.')[0]) > 1:
            a.set_prop_cycle(None)
        else:
            a.set_color_cycle(None)

    def plotRange(self, secm, framei, framef, ydata_type, ranges):
        frame_list = secm.frame_list

        if ydata_type == 'qspec':
            intensity = secm.I_of_q
        elif ydata_type == 'mean':
            intensity = secm.mean_i
        else:
            intensity = secm.total_i

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(frame_list, intensity, framei, framef, ranges)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, frame_list, intensity, framei, framef, ranges):
        #Save for resizing:
        self.orig_frame_list = frame_list
        self.orig_intensity = intensity
        self.orig_framei = framei
        self.orig_framef = framef
        self.orig_ranges = ranges

        a = self.subplots['SECPlot']

        if self.cut_line is None:

            self.cut_line, = a.plot(frame_list[framei:framef+1], intensity[framei:framef+1], 'k.-', animated = True)

            if (int(matplotlib.__version__.split('.')[0]) ==1 and int(matplotlib.__version__.split('.')[1]) >=5) or int(matplotlib.__version__.split('.')[0]) > 1:
                a.set_prop_cycle(None) #Resets the color cycler to the original state
            else:
                a.set_color_cycle(None)

            for i in range(ranges.shape[0]):
                if (int(matplotlib.__version__.split('.')[0]) ==1 and int(matplotlib.__version__.split('.')[1]) >=5) or int(matplotlib.__version__.split('.')[0]) > 1:
                    color = a._get_lines.prop_cycler.next()['color']
                else:
                    color = a._get_lines.color_cycle.next()

                annotation = a.annotate('', xy = (ranges[i][0], 0.975-0.05*(i)), xytext = (ranges[i][1], 0.975-0.05*(i)), xycoords = ('data', 'axes fraction'), arrowprops = dict(arrowstyle = '<->', color = color), animated = True)
                self.range_arrows.append(annotation)

                rline1 = a.axvline(ranges[i][0], 0, 0.975-0.05*(i), linestyle = 'dashed', color = color, animated = True)
                rline2 = a.axvline(ranges[i][1], 0, 0.975-0.05*(i), linestyle = 'dashed', color = color, animated = True)

                self.range_lines.append([rline1, rline2])

            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)


        else:
            self.cut_line.set_ydata(intensity[framei:framef+1])
            self.cut_line.set_xdata(frame_list[framei:framef+1])

            for i in range(ranges.shape[0]):
                arr = self.range_arrows[i]

                arr.xy = (ranges[i][0], 0.975-0.05*(i))
                arr.xyann = (ranges[i][1], 0.975-0.05*(i))

                lines = self.range_lines[i]

                lines[0].set_xdata(ranges[i][0])
                lines[1].set_xdata(ranges[i][1])


        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()

        a.relim()
        a.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()

        if a_newx != a_oldx or a_newy != a_oldy:
            self.canvas.draw()

        self.canvas.restore_region(self.background)

        a.draw_artist(self.cut_line)

        for anno in self.range_arrows:
            a.draw_artist(anno)

        for lines in self.range_lines:
            a.draw_artist(lines[0])
            a.draw_artist(lines[1])

        self.canvas.blit(a.bbox)


class SimilarityFrame(wx.Frame):

    def __init__(self, parent, title, sasm_list):

        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'SimilarityFrame', size = (600,400))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'SimilarityFrame', size = (600,400))

        self.panel = wx.Panel(self, -1, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

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
        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            self.panel.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)

        self.CenterOnParent()

        self.Raise()

    def _createLayout(self, parent):
        method_text = wx.StaticText(parent, -1, 'Method:')
        method_choice = wx.Choice(parent, self.ids['method'], choices = ['CorMap'])
        method_choice.Bind(wx.EVT_CHOICE, self._onMethodChange)
        correction_text = wx.StaticText(parent, -1, 'Multiple testing correction:')
        correction_choice = wx.Choice(parent, self.ids['correction'], choices=['None', 'Bonferroni'])
        correction_choice.SetStringSelection('Bonferroni')
        correction_choice.Bind(wx.EVT_CHOICE, self._onMethodChange)

        method_sizer = wx.BoxSizer(wx.HORIZONTAL)
        method_sizer.Add(method_text, 0, wx.LEFT | wx.RIGHT, 3)
        method_sizer.Add(method_choice, 0, wx.RIGHT, 6)
        method_sizer.Add(correction_text, 0, wx.RIGHT, 3)
        method_sizer.Add(correction_choice, 0, wx.RIGHT, 3)

        highlight_diff_chkbx = wx.CheckBox(parent, self.ids['hl_diff_chk'], 'Highlight with p-value <')
        highlight_diff_chkbx.Bind(wx.EVT_CHECKBOX, self._onHighlightChange)
        highlight_diff_pval = wx.TextCtrl(parent, self.ids['hl_diff_val'], '0.01', size = (65, -1))
        highlight_diff_pval.SetBackgroundColour(wx.Colour(255,128,96))
        highlight_diff_pval.Bind(wx.EVT_TEXT, self._onTextEntry)

        highlight_same_chkbx = wx.CheckBox(parent, self.ids['hl_same_chk'], 'Highlight with p-value >')
        highlight_same_chkbx.Bind(wx.EVT_CHECKBOX, self._onHighlightChange)
        highlight_same_pval = wx.TextCtrl(parent, self.ids['hl_same_val'], '0.01', size = (65, -1))
        highlight_same_pval.SetBackgroundColour('LIGHT BLUE')
        highlight_same_pval.Bind(wx.EVT_TEXT, self._onTextEntry)

        highlight_diff_sizer = wx.BoxSizer(wx.HORIZONTAL)
        highlight_diff_sizer.Add(highlight_diff_chkbx,0, wx.LEFT, 3)
        highlight_diff_sizer.Add(highlight_diff_pval, 0, wx.RIGHT, 3)
        highlight_diff_sizer.Add(highlight_same_chkbx,0, wx.LEFT, 12)
        highlight_diff_sizer.Add(highlight_same_pval, 0, wx.RIGHT, 3)

        self.listPanel = similiarityListPanel(parent, (-1, 300))

        #Creating the fixed buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.done_button = wx.Button(parent, -1, 'Done')
        self.done_button.Bind(wx.EVT_BUTTON, self._onDoneButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        save_button = wx.Button(parent, -1, 'Save')
        save_button.Bind(wx.EVT_BUTTON, self._onSaveButton)

        button_sizer.Add(self.done_button, 0, wx.RIGHT | wx.LEFT, 3)
        button_sizer.Add(info_button, 0, wx.RIGHT, 3)
        button_sizer.Add(save_button, 0, wx.RIGHT, 3)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(method_sizer, 0, wx.TOP | wx.BOTTOM, 5)
        top_sizer.Add(highlight_diff_sizer, 0, wx.TOP | wx.BOTTOM, 5)
        top_sizer.Add(self.listPanel, 1, wx.EXPAND, 0)
        top_sizer.Add(button_sizer, 0, wx.BOTTOM, 5)

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
                        self.listPanel.SetItemBackgroundColour(index, 'WHITE')

                elif hl_diff and hl_diff_pval != '':
                    if pval < hl_diff_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, wx.Colour(255,128,96))
                    elif pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                    else:
                        self.listPanel.SetItemBackgroundColour(index, 'WHITE')

                elif hl_same and hl_same_pval != '':
                    if pval > hl_same_pval and pval != -1:
                        self.listPanel.SetItemBackgroundColour(index, 'LIGHT BLUE')
                    elif pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                    else:
                        self.listPanel.SetItemBackgroundColour(index, 'WHITE')
        else:
            for index in range(self.listPanel.GetItemCount()):
                pval = float(self.listPanel.GetItemText(index,5))
                if pval == -1:
                        self.listPanel.SetItemBackgroundColour(index, 'YELLOW')
                else:
                    self.listPanel.SetItemBackgroundColour(index, 'WHITE')

    def _calcCorMapPval(self):
        correction_window = wx.FindWindowById(self.ids['correction'])
        correction = correction_window.GetStringSelection()

        self.item_data, self.pvals, self.corrected_pvals, failed_comparisons = SASCalc.run_cormap(self.sasm_list, correction)

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
        else:
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

        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT, size=size
                        )

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
        sizer.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

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

        try:
            wx.Frame.__init__(self, parent, wx.ID_ANY, title, name = 'NormKratkyFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, wx.ID_ANY, title, name = 'NormKratkyFrame', size = (800,600))

        self._raw_settings = wx.FindWindowByName('MainFrame').raw_settings

        self.main_frame = parent

        splitter1 = wx.SplitterWindow(self, wx.ID_ANY)

        self.plotPanel = NormKratkyPlotPanel(splitter1, wx.ID_ANY, 'NormKratkyPlotPanel')
        self.controlPanel = NormKratkyControlPanel(splitter1, wx.ID_ANY, 'NormKratkyControlPanel', sasm_list)

        splitter1.SplitVertically(self.controlPanel, self.plotPanel, 290)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(290)    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(50)

        splitter1.Layout()
        self.Layout()
        self.SendSizeEvent()
        splitter1.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)

        self.CenterOnParent()
        self.Raise()

    def OnClose(self):

        self.Destroy()



class NormKratkyPlotPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, wxEmbedded = False):

        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.fig = Figure((5,4), 75)

        self.line_dict = {}

        self.DataTuple = collections.namedtuple('PlotItem', ['sasm', 'rg', 'i0', 'vc', 'line', 'label'])

        self.plot_labels = {'Normalized'            : ('Normalized Kratky', 'q', 'q^2*I(q)/I(0)'),
                            'Dimensionless (Rg)'    : ('Dimensionless Kratky (Rg)', 'qRg', '(qRg)^2*I(q)/I(0)'),
                            'Dimensionless (Vc)'    : ('Dimensionless Kratky (Vc)', 'q(Vc)^(1/2)', '(q)^2*Vc*I(q)/I(0)'),
                            }

        self.plot_type = 'Dimensionless (Rg)'

        self.subplot = self.fig.add_subplot(1,1,1, title = self.plot_labels[self.plot_type][0], label = self.plot_labels[self.plot_type][0])
        self.subplot.set_xlabel(self.plot_labels[self.plot_type][1])
        self.subplot.set_ylabel(self.plot_labels[self.plot_type][2])

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        self.background = self.canvas.copy_from_bbox(self.subplot.bbox)

        if len(self.line_dict) > 0:
            self.canvas.mpl_disconnect(self.cid) #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
            self.redrawLines()
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw) #Reconnect draw_event

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
        elif self.plot_type == 'Dimensionless (Vc)':
            xdata = q*np.sqrt(vc)
            ydata = (q)**2*vc*i/i0

        data_line, = self.subplot.plot(xdata, ydata, animated=True, label=name)

        self.line_dict[data_line] = self.DataTuple(sasm, rg, i0, vc, data_line, name)

        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)

        if len(self.line_dict) == 1:
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.subplot.bbox)

        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

        return data_line

    def relimPlot(self):
        oldx = self.subplot.get_xlim()
        oldy = self.subplot.get_ylim()

        self.subplot.relim()
        self.subplot.autoscale_view()

        newx = self.subplot.get_xlim()
        newy = self.subplot.get_ylim()

        if newx != oldx or newy != oldy:
            self.canvas.draw()

        self.redrawLines()

    def redrawLines(self):

        self.canvas.restore_region(self.background)

        for line in self.line_dict.keys():
            self.subplot.draw_artist(line)

        legend = self.subplot.get_legend()
        if legend is not None:
            if legend.get_visible():
                self.subplot.draw_artist(legend)

        self.canvas.blit(self.subplot.bbox)

    def updatePlot(self, plot_type):
        self.plot_type = plot_type

        self.subplot.set_title(self.plot_labels[self.plot_type][0])
        self.subplot.set_xlabel(self.plot_labels[self.plot_type][1])
        self.subplot.set_ylabel(self.plot_labels[self.plot_type][2])

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

        self.relimPlot()

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
        for line in self.line_dict.keys():
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
            else:
                return

            RAWGlobals.save_in_progress = True
            self.main_frame.setStatus('Saving Kratky data', 0)

            SASFileIO.saveNormKratkyData(save_path, data_list, header)

            RAWGlobals.save_in_progress = False
            self.main_frame.setStatus('', 0)


class NormKratkyControlPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, sasm_list):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.parent = parent

        self.sasm_list = sasm_list

        self.control_ids = {'plot'  : self.NewControlId(),
                            }

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        sizer = self._createLayout()

        self.SetSizer(sizer)

        self._initialize()

    def onCloseButton(self, evt):
        diag = wx.FindWindowByName('NormKratkyFrame')
        diag.OnClose()

    def _createLayout(self):

        close_button = wx.Button(self, wx.ID_OK, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(close_button, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL, 5)


        box = wx.StaticBox(self, -1, 'Control')
        control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        plt_text = wx.StaticText(self, -1, 'Plot:')
        plt_ctrl = wx.Choice(self, self.control_ids['plot'], choices=['Normalized', 'Dimensionless (Rg)', 'Dimensionless (Vc)'])
        plt_ctrl.SetStringSelection('Dimensionless (Rg)')
        plt_ctrl.Bind(wx.EVT_CHOICE, self._onPlotChoice)

        plt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        plt_sizer.Add(plt_text, 0, wx.LEFT | wx.RIGHT, 5)
        plt_sizer.Add(plt_ctrl, 0, wx.RIGHT, 5)

        self.list = normKratkyListPanel(self)


        control_sizer.Add(plt_sizer, 0)
        control_sizer.Add(self.list, 1, wx.EXPAND | wx.TOP, 5)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(control_sizer,0, wx.TOP | wx.EXPAND, 5)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(button_sizer,0, wx.BOTTOM|wx.ALIGN_CENTER_HORIZONTAL, 5)

        return top_sizer

    def _initialize(self):
        plotpanel = wx.FindWindowByName('NormKratkyPlotPanel')

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

        plotpanel = wx.FindWindowByName('NormKratkyPlotPanel')

        subplot = plotpanel.subplot
        if not subplot.get_autoscale_on():
            subplot.set_autoscale_on(True)

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
                        | ULC.ULC_SORT_ASCENDING, size=(-1,450)
                        )

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
        sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

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

        colour_indicator = RAWCustomCtrl.ColourIndicator(self.list_ctrl, index, color, size = (30,15))
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
        self.list_ctrl.SetColumnWidth(1, 130)
        self.list_ctrl.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

    def _onItemChecked(self, evt):
        item = evt.GetItem()

        itemData = item.GetPyData()
        line = itemData[1]

        state = item.IsChecked()
        line.set_visible(state)

        plotpanel = wx.FindWindowByName('NormKratkyPlotPanel')

        legend =plotpanel.subplot.get_legend()
        if legend is not None and legend.get_visible():
            plotpanel._updateLegend()
        plotpanel.redrawLines()

    def _onColorButton(self, evt):
        index = evt.GetId()
        item = self.list_ctrl.GetItem(index)
        itemData = item.GetPyData()
        line = itemData[1]

        plotpanel = wx.FindWindowByName('NormKratkyPlotPanel')

        dlg = RAWCustomDialogs.ColourChangeDialog(self, None, 'NormKratky', line, plotpanel)
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


# ----------------------------------------------------------------------------
# Auto-wrapping static text class
# ----------------------------------------------------------------------------
class AutoWrapStaticText(StaticText):
    """
    A simple class derived from :mod:`lib.stattext` that implements auto-wrapping
    behaviour depending on the parent size.
    .. versionadded:: 0.9.5
    Code from: https://github.com/wxWidgets/Phoenix/blob/master/wx/lib/agw/infobar.py
    Original author: Andrea Gavana
    """
    def __init__(self, parent, label):
        """
        Defsult class constructor.
        :param Window parent: a subclass of :class:`Window`, must not be ``None``;
        :param string `label`: the :class:`AutoWrapStaticText` text label.
        """
        StaticText.__init__(self, parent, wx.ID_ANY, label, style=wx.ST_NO_AUTORESIZE)
        self.label = label
        # colBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK)
        # self.SetBackgroundColour(colBg)
        # self.SetOwnForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT))

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSize)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.OnSize)

    def OnSize(self, event):
        """
        Handles the ``wx.EVT_SIZE`` event for :class:`AutoWrapStaticText`.
        :param `event`: a :class:`SizeEvent` event to be processed.
        """
        event.Skip()
        self.Wrap(event.GetSize().width)

    def Wrap(self, width):
        """
        This functions wraps the controls label so that each of its lines becomes at
        most `width` pixels wide if possible (the lines are broken at words boundaries
        so it might not be the case if words are too long).
        If `width` is negative, no wrapping is done.
        :param integer `width`: the maximum available width for the text, in pixels.
        :note: Note that this `width` is not necessarily the total width of the control,
        since a few pixels for the border (depending on the controls border style) may be added.
        """
        if width < 0:
           return
        self.Freeze()

        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        text = wordwrap(self.label, width, dc)
        self.SetLabel(text, wrapped=True)

        self.Thaw()

    def SetLabel(self, label, wrapped=False):
        """
        Sets the :class:`AutoWrapStaticText` label.
        All "&" characters in the label are special and indicate that the following character is
        a mnemonic for this control and can be used to activate it from the keyboard (typically
        by using ``Alt`` key in combination with it). To insert a literal ampersand character, you
        need to double it, i.e. use "&&". If this behaviour is undesirable, use `SetLabelText` instead.
        :param string `label`: the new :class:`AutoWrapStaticText` text label;
        :param bool `wrapped`: ``True`` if this method was called by the developer using :meth:`~AutoWrapStaticText.SetLabel`,
        ``False`` if it comes from the :meth:`~AutoWrapStaticText.OnSize` event handler.
        :note: Reimplemented from :class:`PyControl`.
        """

        if not wrapped:
            self.label = label

        StaticText.SetLabel(self, label)


class GuinierTestApp(wx.App):

    def OnInit(self, filename = None):

        #ExpObj, ImgDummy = fileIO.loadFile('/home/specuser/Downloads/BSUB_MVMi7_5_FULL_001_c_plot.rad')

        tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'lyzexp.dat')

        #tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'Lys12_1_001_plot.rad')

        print tst_file
        raw_settings = RAWSettings.RawGuiSettings()

        ExpObj, ImgDummy = SASFileIO.loadFile(tst_file, raw_settings)

        if type(ExpObj) == list:
            ExpObj = ExpObj[0]

        frame = GuinierFrame(self, 'Guinier Fit', ExpObj, None)
        self.SetTopWindow(frame)
        frame.SetSize((800,600))
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
