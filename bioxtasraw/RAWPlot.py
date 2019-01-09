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

import wx
import os
import sys
import platform
import itertools
import copy
import matplotlib
import numpy as np
import traceback

matplotlib.rcParams['backend'] = 'WxAgg'
matplotlib.rc('mathtext', default='regular')
if int(matplotlib.__version__.split('.')[0]) >= 2:
    matplotlib.rcParams['errorbar.capsize'] = 3


from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import matplotlib.font_manager as fm

import RAWCustomCtrl
import RAWGlobals
import RAWCustomDialogs

class MyFigureCanvasWxAgg(FigureCanvasWxAgg):

    def __init__(self, *args, **kwargs):
        FigureCanvasWxAgg.__init__(self, *args, **kwargs)

    def _onMotion(self, evt):
        """Start measuring on an axis."""

        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()
        evt.Skip()

        try:
            FigureCanvasWxAgg.motion_notify_event(self, x, y, guiEvent=evt)
        except:
            print 'Log fail! Switch to Lin-Lin plot in the menu'
            print "Unexpected error:", sys.exc_info()[0]
            print "Unexpected error:", sys.exc_info()[1]

            plotpanel = wx.FindWindowByName('PlotPanel')

            i=0
            for a in self.figure.get_axes():
               i = i + 1
               if a.get_yscale() == 'log':
                   a.set_yscale('linear')
                   a.set_xscale('linear')

                   plotpanel.setParameter('axesscale' + str(i), 'linlin')

                   wx.MessageBox('Data contains too many illegal/negative values for a log plot', 'Error!' )

            try:
                plotpanel.fitAxis()
            except ValueError, e:
                print 'MyFigureCanvasWxAgg: ' + str(e)


    #These don't do anything at the moment, but were giving me some strange errors on the sec plot
    def _onLeftButtonUp(self, evt):
        """End measuring on an axis."""
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()

        evt.Skip()
        if self.HasCapture():
            self.ReleaseMouse()

        try:
            FigureCanvasWxAgg.button_release_event(self, x, y, 1, guiEvent=evt)
        except Exception as e:
            print e
            print 'Log fail! Switch to Lin-Lin plot in the menu'


    def _onLeftButtonDown(self, evt):
        """Start measuring on an axis."""
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()

        evt.Skip()
        self.CaptureMouse()

        try:
            FigureCanvasWxAgg.button_press_event(self, x, y, 1, guiEvent=evt)
        except Exception as e:
            print e
            print 'Log fail! Switch to Lin-Lin plot in the menu'




class CustomPlotToolbar(NavigationToolbar2WxAgg):
    def __init__(self, parent, canvas):

        self.fig_axes = parent.fig.gca()
        self.parent = parent

        self.saved_artists = None

        self._MTB_ERRBARS = self.NewControlId()
        self._MTB_LEGEND = self.NewControlId()
        self._MTB_SHOWBOTH = self.NewControlId()
        self._MTB_SHOWTOP = self.NewControlId()
        self._MTB_CLR1 = self.NewControlId()
        self._MTB_CLR2 = self.NewControlId()
        self._MTB_SHOWBOTTOM = self.NewControlId()

        NavigationToolbar2WxAgg.__init__(self, canvas)

        self.workdir = RAWGlobals.RAWWorkDir

        #Icon made by Freepik from www.flaticon.com
        errbars = os.path.join(RAWGlobals.RAWResourcesDir, 'box-plot-graphic-24.png')

        showboth = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-showboth-24.png')
        showtop = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-1-24.png')
        showbottom = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-two-24.png')

        errbars_icon = wx.Bitmap(errbars, wx.BITMAP_TYPE_PNG)
        showboth_icon = wx.Bitmap(showboth, wx.BITMAP_TYPE_PNG)
        showtop_icon = wx.Bitmap(showtop, wx.BITMAP_TYPE_PNG)
        showbottom_icon = wx.Bitmap(showbottom, wx.BITMAP_TYPE_PNG)

        if wx.version().split()[0].strip()[0] == '4':
            self.AddSeparator()
            self.AddCheckTool(self._MTB_ERRBARS, '', errbars_icon, shortHelp='Show Errorbars')
            self.AddSeparator()
            self.AddCheckTool(self._MTB_SHOWBOTH, '', showboth_icon, shortHelp='Show Both Plots')
            self.AddCheckTool(self._MTB_SHOWTOP, '', showtop_icon,  shortHelp='Show Top Plot')
            self.AddCheckTool(self._MTB_SHOWBOTTOM, '', showbottom_icon, shortHelp='Show Bottom Plot')
        else:
            self.AddSeparator()
            self.AddCheckTool(self._MTB_ERRBARS, errbars_icon, shortHelp='Show Errorbars')
            self.AddSeparator()
            self.AddCheckTool(self._MTB_SHOWBOTH, showboth_icon, shortHelp='Show Both Plots')
            self.AddCheckTool(self._MTB_SHOWTOP, showtop_icon,  shortHelp='Show Top Plot')
            self.AddCheckTool(self._MTB_SHOWBOTTOM, showbottom_icon, shortHelp='Show Bottom Plot')

        self.Bind(wx.EVT_TOOL, self.errbars, id = self._MTB_ERRBARS)
        self.Bind(wx.EVT_TOOL, self.showboth, id = self._MTB_SHOWBOTH)
        self.Bind(wx.EVT_TOOL, self.showtop, id = self._MTB_SHOWTOP)
        self.Bind(wx.EVT_TOOL, self.showbottom, id = self._MTB_SHOWBOTTOM)

        self.Realize()

        self.ErrorbarIsOn = False

        self.ToggleTool(self._MTB_SHOWBOTH, True)

    def home(self, *args, **kwargs):
        self.parent.fitAxis(forced = True)

    def save(self,  *args, **kwargs):
        dia = FigureSaveDialog(self.parent, self.parent.fig, self.parent.save_parameters)
        dia.ShowModal()
        dia.Destroy()

    def showboth(self, evt):
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, False)
        self.ToggleTool(self._MTB_SHOWBOTH, True)

        self.parent.subplot1.set_visible(True)
        self.parent.subplot2.set_visible(True)

        self.parent.subplot1.change_geometry(2,1,1)
        self.parent.subplot2.change_geometry(2,1,2)
        self.parent._plot_shown = 0
        self.parent.canvas.draw()

    def showtop(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, False)
        self.ToggleTool(self._MTB_SHOWTOP, True)

        self.parent.subplot1.set_visible(True)
        self.parent.subplot2.set_visible(False)

        self.parent.subplot1.change_geometry(1,1,1)

        self.parent.subplot1.set_zorder(2)
        self.parent.subplot2.set_zorder(1)

        self.parent._plot_shown = 1
        self.parent.canvas.draw()

    def showbottom(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, True)

        self.parent.subplot1.set_visible(False)
        self.parent.subplot2.set_visible(True)

        self.parent.subplot1.set_zorder(1)
        self.parent.subplot2.set_zorder(2)

        self.parent.subplot2.change_geometry(1,1,1)
        self.parent._plot_shown = 2
        self.parent.canvas.draw()

    def errbars(self, evt):

        if not(self.ErrorbarIsOn):
            self.parent.plotparams['errorbars_on'] = True
            self.ErrorbarIsOn = True
            self.parent.showErrorbars(True)
        else:
            self.parent.plotparams['errorbars_on'] = False
            self.ErrorbarIsOn = False
            self.parent.showErrorbars(False)

class PlotPanel(wx.Panel):

    def __init__(self, parent, id, name, *args, **kwargs):

        wx.Panel.__init__(self, parent, id, *args, name = name, **kwargs)

        file_drop_target = RAWCustomCtrl.RawPlotFileDropTarget(self, 'main')
        self.SetDropTarget(file_drop_target)

        self._initFigure()

        self.toolbar = CustomPlotToolbar(self, self.canvas)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        #color = parent.GetThemeBackgroundColour()
        self.SetSizer(sizer)
        #self._setColor(color)

        # Variables for the plotted experiments:
        self.legend_names = []
        self.plotted_sasms = []

        self.selected_line = None
        self.selected_line_orig_width = 1
        self._plot_shown = 0

        #Timer to automatically restore line width after selection
        self.blink_timer = wx.Timer()
        self.blink_timer.Bind(wx.EVT_TIMER, self._onBlinkTimer)

        #Find the plot font, which is strangely hard!
        font_list = fm.get_fontconfig_fonts()

        fonts=[]

        for item in font_list:
            try:
                font_name = fm.FontProperties(fname=item).get_name()

                if font_name != 'System Font' and not font_name.startswith('.'):
                    fonts.append(font_name)
            except:
                pass

        mpl_font_dir = os.path.join(matplotlib.rcParams['datapath'],'fonts/ttf')
        font_list2 = fm.list_fonts(mpl_font_dir, '*.ttf')

        for item in font_list2:
            fp = fm.FontProperties()
            try:
                fp.set_file(item)
                font_name = fp.get_name()
                if font_name != 'System Font' and not font_name.startswith('.'):
                    fonts.append(font_name)
            except:
                pass

        fonts = list(set(fonts))
        fonts.sort()

        possible_fonts = matplotlib.rcParams['font.'+matplotlib.rcParams['font.family'][0]]

        found_font = False
        i = 0
        self.default_plot_font = None
        while not found_font and i in range(len(possible_fonts)):
            test_font = possible_fonts[i]

            if test_font in fonts:
                self.default_plot_font = test_font
                found_font = True

            i = i + 1

        if self.default_plot_font is None:
            self.default_plot_font = 'Arial'

        self.plotparams = {         'axesscale1'            : 'loglin',
                                    'axesscale2'            : 'loglin',
                                    'plot1type'             : 'normal',
                                    'plot2type'             : 'subtracted',
                                    'errorbars_on'          : False,

                                    'legend_pos1'           : None,
                                    'legend_pos2'           : None,
                                    'legend_visible1'       : False,
                                    'legend_visible2'       : False,
                                    'legend_fontsize1'      : 10,
                                    'legend_border1'        : False,
                                    'legend_fontsize2'      : 10,
                                    'legend_border2'        : False,
                                    'legend_alpha1'         : 0.7,
                                    'legend_alpha2'         : 0.7,
                                    'legend_shadow1'        : False,
                                    'legend_shadow2'        : False,

                                    'legtit_fontsize1'      : 12,
                                    'legtit_fontsize2'      : 12,

                                    'legtit_font1'          : self.default_plot_font,
                                    'legtit_font2'          : self.default_plot_font,

                                    'auto_fitaxes1'         : True,
                                    'auto_fitaxes2'         : True,
                                    'framestyle1'           : 'lb',
                                    'framestyle2'           : 'lb',

                                    'title_fontsize1'       : 16,
                                    'xlabel_fontsize1'      : 15,
                                    'ylabel_fontsize1'      : 15,

                                    'title_fontsize2'       : 16,
                                    'xlabel_fontsize2'      : 15,
                                    'ylabel_fontsize2'      : 15,

                                    'title_font1'           : self.default_plot_font,
                                    'xlabel_font1'          : self.default_plot_font,
                                    'ylabel_font1'          : self.default_plot_font,

                                    'title_font2'           : self.default_plot_font,
                                    'xlabel_font2'          : self.default_plot_font,
                                    'ylabel_font2'          : self.default_plot_font,

                                    'legend_font1'          : self.default_plot_font,
                                    'legend_font2'          : self.default_plot_font,

                                    'zero_line1'            : False,
                                    'zero_line2'            : False}

        self.frame_styles = ['Full', 'XY', 'X', 'Y', 'None']

        self.default_subplot_labels = { 'subtracted'  : ['Subtracted', '$q$', '$I(q)$'],
                                'kratky'      : ['Kratky', '$q$', '$I(q)q^{2}$'],
                                'guinier'     : ['Guinier', '$q^{2}$', '$ln(I(q))$'],
                                'porod'       : ['Porod', '$q$', '$I(q)q^{4}$'],
                                'normal'      : ['Main Plot', '$q$', '$I(q)$']}

        self.subplot_labels = copy.copy(self.default_subplot_labels)

        self.save_parameters ={'dpi' : 100,
                               'format' : 'png'}

        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)

        self._updateFrameStylesForAllPlots()
        self.updatePlotType(self.subplot1)
        self.updatePlotAxes()

        self.canvas.callbacks.connect('pick_event', self._onPickEvent)
        self.canvas.callbacks.connect('key_press_event', self._onKeyPressEvent)
        self.canvas.callbacks.connect('motion_notify_event', self._onMouseMotionEvent)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        self.canvas.callbacks.connect('scroll_event', self._onMouseScrollEvent)

        # self._canvas_cursor = Cursor(self.subplot1, useblit=True, color='red', linewidth=1, linestyle ='--', label = '_cursor_')
        # self._canvas_cursor.horizOn = False

    def _initFigure(self):
        self.fig = matplotlib.figure.Figure((5,4), 75)
        self.subplot1 = self.fig.add_subplot(211)
        self.subplot2 = self.fig.add_subplot(212)

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = MyFigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

    def setParameter(self, param, value):
        self.plotparams[param] = value

    def getParameter(self, param):
        return self.plotparams[param]

    def _updateFrameStylesForAllPlots(self):
        try:
            self.updateFrameStyle(axes = self.subplot1)
            self.updateFrameStyle(axes = self.subplot2)
        except Exception, e:
            print 'Possibly too old matplotlib version: ' + str(e)
            pass

    def updateFrameStyle(self, axes):
        if axes == self.subplot1:
            plotnum = '1'
        else:
            plotnum = '2'

        style = self.plotparams['framestyle' + plotnum]

        self.setFrameStyle(axes, style)

    def setFrameStyle(self, axes, style):

        if style.find('l')>-1:
            axes.spines['left'].set_color('black')
            axes.tick_params(left=True, which = 'both')
        else:
            axes.spines['left'].set_color('none')
            axes.tick_params(left=False, which = 'both')
        if style.find('r')>-1:
            axes.spines['right'].set_color('black')
            axes.tick_params(right=True, which = 'both')
        else:
            axes.spines['right'].set_color('none')
            axes.tick_params(right=False, which = 'both')
        if style.find('t')>-1:
            axes.spines['top'].set_color('black')
            axes.tick_params(top=True, which = 'both')
        else:
            axes.spines['top'].set_color('none')
            axes.tick_params(top=False, which = 'both')
        if style.find('b')>-1:
            axes.spines['bottom'].set_color('black')
            axes.tick_params(bottom=True, which = 'both')
        else:
            axes.spines['bottom'].set_color('none')
            axes.tick_params(bottom=False, which = 'both')

    def fitAxis(self, axes = None, forced = False):

        if axes is not None:
            if not isinstance(axes, list):
                plots = [axes]
            else:
                plots = axes
        else:
            plots = [self.subplot1, self.subplot2]

        for eachsubplot in plots:
            if eachsubplot.lines:

                if eachsubplot == self.subplot1:
                    plotnum = '1'
                else:
                    plotnum = '2'

                maxq = None
                maxi = None

                minq = None
                mini = None

                is_logy = False
                is_logx = False

                if (self.plotparams['plot' + plotnum + 'type'] == 'normal'
                        or self.plotparams['plot' + plotnum + 'type'] ==
                        'subtracted'):
                    if (self.plotparams['axesscale' + plotnum + ''] ==
                            'loglog' or self.plotparams['axesscale' + plotnum
                            + ''] == 'loglin'):
                        is_logy = True

                if (self.plotparams['plot' + plotnum + 'type'] == 'normal'
                        or self.plotparams['plot' + plotnum + 'type'] ==
                        'subtracted'):
                    if (self.plotparams['axesscale' + plotnum + ''] ==
                            'loglog' or self.plotparams['axesscale' + plotnum
                            + ''] == 'linlog'):
                        is_logx = True

                if self.plotparams['auto_fitaxes' + plotnum] == False and forced == False:
                    print 'Not fitting axes due to plot settings'
                    try:
                        self.canvas.draw()
                    except ValueError, e:
                        print 'ValueError in fitaxis() : ' + str(e)
                    return

                for each in eachsubplot.lines:
                    if each._label != '_nolegend_' and each._label != '_zero_' and each._label != '_cursor_' and each.get_visible() == True:

                        if not is_logx:
                            xdata = each.get_xdata()
                        else:
                            xdata = each.get_xdata()
                            xdata = xdata[xdata>0]

                        if not is_logy:
                            ydata = each.get_ydata()
                        else:
                            ydata = each.get_ydata()
                            ydata = ydata[ydata>0]

                        if len(xdata)>0:
                            if maxq is None:
                                maxq = max(xdata)
                                minq = min(xdata)

                            xmax = max(xdata)
                            xmin = min(xdata)

                            if xmax > maxq:
                                maxq = xmax
                            if xmin < minq:
                                minq = xmin

                        if len(ydata)>0:
                            if maxi is None:
                                maxi = max(ydata)
                                mini = min(ydata)

                            ymax = max(ydata)
                            ymin = min(ydata)

                            if ymax > maxi:
                                maxi = ymax
                            if ymin < mini:
                                mini = ymin

                if mini is not None and maxi is not None:
                    eachsubplot.set_ylim(mini, maxi)
                else:
                    eachsubplot.set_ylim(0.1, 1)

                if minq is not None and maxq is not None:
                    eachsubplot.set_xlim(minq, maxq)
                else:
                    eachsubplot.set_xlim(0.1, 1)

                #This is supposed to fix the value error bug
                #But it doesn't seem to. See, for example:
                #http://www.cloudypoint.com/Tutorials/discussion/python-solved-python-matplotlib-valueerror-for-logit-scale-axis-label/
                eachsubplot.spines['left']._adjust_location()
                eachsubplot.spines['bottom']._adjust_location()
                eachsubplot.spines['right']._adjust_location()
                eachsubplot.spines['top']._adjust_location()

        try:
            self.canvas.draw()
        except ValueError, e:
            print 'ValueError in fitaxis() : ' + str(e)
            traceback.print_exc()


    def _onBlinkTimer(self, event):

        try:
            self.selected_line.set_linewidth(self.selected_line_orig_width)
            self.canvas.draw()
        except:
            pass

        self.selected_line = None
        self.blink_timer.Stop()

    def _onPickEvent(self, event):

        mouseevent = event.mouseevent

        if mouseevent.button == 'up' or mouseevent.button == 'down' or mouseevent.button == 3:
            return

        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')

        if self.selected_line != None:
            self.selected_line.set_linewidth(self.selected_line_orig_width)

        self.selected_line = event.artist

        try:
            self.selected_line_orig_width = self.selected_line.get_linewidth()
            self.selected_line.set_linewidth(self.selected_line_orig_width + 2)
        except AttributeError:
            self.selected_line = None
            return

        wx.CallAfter(self.manipulation_panel.deselectAllExceptOne, None, self.selected_line)
        self.canvas.draw()

        self.blink_timer.Start(500)

        return

    def _onKeyPressEvent(self, event):
        pass

    def _onMouseScrollEvent(self, event):
        pass

    def _onMouseMotionEvent(self, event):

        if event.inaxes:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('q = ' +  str(round(x,5)) + ', I = ' + str(round(y,5)), 1)

    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''

        x_size,y_size = self.canvas.get_width_height()
        half_y = y_size / 2

        if self._plot_shown == 1:
            selected_plot = 1
        elif self._plot_shown == 2:
            selected_plot = 2
        elif event.y <= half_y:
            selected_plot = 2
        else:
            selected_plot = 1

        if event.button == 3:

            if float(matplotlib.__version__[:3]) >= 1.2:
                if self.toolbar.GetToolState(self.toolbar.wx_ids['Pan']) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, selected_plot)
                    else:
                        self._showPopupMenu(selected_plot)

            else:
                if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, selected_plot)
                    else:
                        self._showPopupMenu(selected_plot)

#--- ** Popup Menu ***

    def plotSASM(self, sasm_list, axes_no = 1, color = None, legend_label_in = None,
        line_data = None, *args, **kwargs):
        if axes_no == 1:
            a = self.subplot1
        elif axes_no == 2:
            a = self.subplot2
        else:
            a = axes_no

        if not isinstance(sasm_list, list):
            sasm_list = [sasm_list]

        #plot with errorbars
        if a == self.subplot1:
            plottype= self.plotparams.get('plot1type')
        elif a == self.subplot2:
            plottype= self.plotparams.get('plot2type')

        for sasm in sasm_list:

            q_min, q_max = sasm.getQrange()

            if legend_label_in == None:
                legend_label = sasm.getParameter('filename')
            else:
                legend_label = legend_label_in

            if plottype== 'normal' or plottype== 'subtracted':
                line, ec, el = a.errorbar(sasm.q[q_min:q_max], sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label, **kwargs)
            elif plottype== 'kratky':
                line, ec, el = a.errorbar(sasm.q[q_min:q_max], sasm.i[q_min:q_max] * np.power(sasm.q[q_min:q_max],2), sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
            elif plottype== 'guinier':
                line, ec, el = a.errorbar(np.power(sasm.q[q_min:q_max],2), sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
            elif plottype== 'porod':
                line, ec, el = a.errorbar(sasm.q[q_min:q_max], np.power(sasm.q[q_min:q_max],4)*sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)

            line.set_label(legend_label)

            #Hide errorbars:

            for each in ec:
                if self.plotparams['errorbars_on'] == False:
                    each.set_visible(False)
                if color != None:
                    each.set_color(color)
            for each in el:
                if self.plotparams['errorbars_on'] == False:
                    each.set_visible(False)
                if color != None:
                    each.set_color(color)

            if color != None:
                line.set_color(color)

            sasm.line = line
            sasm.err_line = (ec, el)
            sasm.axes = a
            sasm.canvas = self.canvas
            sasm.plot_panel = self
            sasm.is_plotted = True

            self.updateErrorBars(sasm)

            self.plotted_sasms.append(sasm)        # Insert the plot into plotted experiments list

            if line_data != None:
                line.set_linewidth(line_data['line_width'])
                line.set_linestyle(line_data['line_style'])
                line.set_color(line_data['line_color'])
                line.set_marker(line_data['line_marker'])
                line.set_visible(line_data['line_visible'])

                try:
                    line.set_markerfacecolor(line_data['line_marker_face_color'])
                    line.set_markeredgecolor(line_data['line_marker_edge_color'])

                    for each in sasm.err_line:
                        for line in each:
                            line.set_color(line_data['line_errorbar_color'])

                except KeyError:
                    pass #Version <1.3.0 doesn't have these keys


    def showErrorbars(self, state):

        for each in self.plotted_sasms:

            if each.line.get_visible():
                for each_err_line in each.err_line[0]:
                    each_err_line.set_visible(state)

                for each_err_line in each.err_line[1]:
                    each_err_line.set_visible(state)


                if state == True:
                    #Update errorbar positions

                    self.updateErrorBars(each)

        self.canvas.draw()

    def _showPopupMenu(self, selected_plot):

        self.selected_plot = selected_plot

        menu = wx.Menu()

        plot1SubMenu = self._createPopupAxesMenu('1')
        plot2SubMenu = self._createPopupAxesMenu('2')

        if selected_plot == 1:
            menu.AppendSubMenu(plot1SubMenu, 'Axes')
        else:
            menu.AppendSubMenu(plot2SubMenu, 'Axes')

        menu.AppendSeparator()
        plot_options = menu.Append(wx.ID_ANY, 'Plot Options...')


        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

        self.Bind(wx.EVT_MENU, self._onPlotOptions, plot_options)


        self.PopupMenu(menu)

        menu.Destroy()

    def _onPlotOptions(self, evt):
        if self.selected_plot == 1:
            axes = self.subplot1
        else:
            axes = self.subplot2

        dlg = RAWCustomDialogs.PlotOptionsDialog(self, self.plotparams, axes)
        dlg.ShowModal()
        dlg.Destroy()


    def _onPopupMenuChoice(self, evt):
        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        id = evt.GetId()

        for key in MenuIDs.iterkeys():
            if MenuIDs[key] == id:

                if key[4] == '1':

                    if key[5:7] == 'ty':
                        self.plotparams['plot1type'] = key[7:]
                        self.plotparams['axesscale1'] = 'linlin'

                        self.updatePlotType(self.subplot1)
                        self.updatePlotAxes(self.subplot1)

                    else:
                        self.plotparams['axesscale1'] = key[7:]
                        self.plotparams['plot1type'] = 'normal'

                        self.updatePlotType(self.subplot1)
                        self.updatePlotAxes(self.subplot1)

                else:
                    if key[5:7] == 'ty':
                        self.plotparams['plot2type'] = key[7:]
                        self.plotparams['axesscale2'] = 'linlin'

                        self.updatePlotType(self.subplot2)
                        self.updatePlotAxes(self.subplot2)

                    else:
                        self.plotparams['axesscale2'] = key[7:]
                        self.plotparams['plot2type'] = 'subtracted'

                        self.updatePlotType(self.subplot2)
                        self.updatePlotAxes(self.subplot2)


        #Update plot settings in menu bar:
        mainframe.setViewMenuScale(id)
        #evt.Skip()


    def _createPopupAxesMenu(self, plot_number):

        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        item_list = []
        pop_menu = wx.Menu()

        axes_list = [('sclinlin',    'Lin-Lin'),
                         ('scloglin',    'Log-Lin'),
                         ('scloglog',   'Log-Log'),
                         ('sclinlog',    'Lin-Log'),
                         ('tyguinier',  'Guinier'),
                         ('tykratky',   'Kratky'),
                         ('typorod',   'Porod') ]

        for key, label in axes_list:
            item = pop_menu.AppendRadioItem(MenuIDs['plot' + plot_number + key], label)
            item_list.append(item)

        self._markCurrentAxesSelection(item_list, plot_number)

        return pop_menu

    def _markCurrentAxesSelection(self, item_list, plot_number):
        ''' Set the current axes selection on the newly created
           popup menu '''

        if self.plotparams['plot' + plot_number + 'type'] == 'normal' or self.plotparams['plot' + plot_number + 'type'] == 'subtracted':

            if self.plotparams['axesscale' + plot_number + ''] == 'loglog':
                item_list[2].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'linlog':
                item_list[3].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'loglin':
                item_list[1].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'linlin':
                item_list[0].Check(True)

        else:
            if self.plotparams['plot' + plot_number + 'type'] == 'guinier':
                item_list[4].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'kratky':
                item_list[5].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'porod':
                item_list[6].Check(True)

    def updatePlotType(self, axes):
        if axes == self.subplot1:
            c = '1'
        else:
            c = '2'

        for each in self.plotted_sasms:
            if each is not None and each.line is not None and each.axes == axes:
                q_min, q_max = each.getQrange()

                if self.plotparams['plot' + c + 'type'] == 'kratky':
                    each.line.set_ydata(each.i[q_min:q_max] * np.power(each.q[q_min:q_max],2))
                    each.line.set_xdata(each.q[q_min:q_max])
                elif self.plotparams['plot' + c + 'type'] == 'guinier':
                    each.line.set_ydata(np.log(each.i[q_min:q_max]))
                    each.line.set_xdata(np.power(each.q[q_min:q_max],2))
                elif self.plotparams['plot' + c + 'type'] == 'porod':
                    each.line.set_ydata(np.power(each.q[q_min:q_max],4)*each.i[q_min:q_max])
                    each.line.set_xdata(each.q[q_min:q_max])
                elif self.plotparams['plot' + c + 'type'] == 'normal' or self.plotparams['plot' + c+ 'type'] == 'subtracted':
                    each.line.set_ydata(each.i[q_min:q_max])
                    each.line.set_xdata(each.q[q_min:q_max])

                self.updateErrorBars(each)

        self._setLabels(axes=axes)

    def updatePlotAxes(self, axes=None):

        if axes is None:
            axes = [self.subplot1, self.subplot2]
        elif not isinstance(axes, list):
            axes = [axes]

        for a in axes:

            if a == self.subplot1:
                c = 1
            elif a == self.subplot2:
                c = 2

            if self.plotparams.get('axesscale' + str(c)) == 'linlin':
                a.set_xscale('linear')
                a.set_yscale('linear')

            if self.plotparams.get('axesscale'+ str(c)) == 'loglin':
                a.set_xscale('linear')

                a.set_ylim(1, 99999)
                a.set_yscale('log')

            if self.plotparams.get('axesscale'+ str(c)) == 'loglog':
                a.set_xlim(1, 99999)
                a.set_xscale('log')

                a.set_ylim(1, 99999)
                a.set_yscale('log')

            if self.plotparams.get('axesscale'+ str(c)) == 'linlog':
                a.set_xlim(1, 99999)
                a.set_xscale('log')

                a.set_yscale('linear')

        self.fitAxis(axes)

    def updatePlotAfterManipulation(self, sasm_list, draw = True):

        for sasm in sasm_list:
            a = sasm.axes

            if a == self.subplot1:
                plottype= self.plotparams.get('plot1type')
            elif a == self.subplot2:
                plottype= self.plotparams.get('plot2type')

            q_min, q_max = sasm.getQrange()
            q = sasm.q[q_min:q_max]
            i = sasm.i[q_min:q_max]

            if plottype== 'normal' or plottype== 'subtracted':
                sasm.line.set_data(q, i)
            elif plottype== 'kratky':
                sasm.line.set_data(q, i*np.power(q,2))
            elif plottype== 'porod':
                sasm.line.set_data(q, np.power(q,4)*i)
            elif plottype == 'guinier':
                sasm.line.set_data(np.power(q,2), np.log(i))

            self.updateErrorBars(sasm)

        if draw:
            self.fitAxis()

    def updateErrorBars(self, sasm):
        a = sasm.axes

        if a == self.subplot1:
            plottype= self.plotparams.get('plot1type')
        elif a == self.subplot2:
            plottype= self.plotparams.get('plot2type')

        if sasm.err_line is not None:
            #Update errorbar positions
            caplines = sasm.err_line[0]
            barlinecols = sasm.err_line[1]

            yerr = sasm.err
            x = sasm.q
            y = sasm.i

            # Find the ending points of the errorbars
            if plottype== 'normal' or plottype== 'subtracted':
                error_positions = (x, y-yerr), (x, y+yerr)
            elif plottype== 'kratky':
                error_positions = (x, (y-yerr)*np.power(x,2)), (x, (y+yerr)*np.power(x,2))
            elif plottype== 'porod':
                error_positions = (x, (y-yerr)*np.power(x,4)), (x, (y+yerr)*np.power(x,4))
            elif plottype == 'guinier':
                error_positions = (np.power(x,2), np.log((y-yerr))), (np.power(x,2), np.log((y+yerr)))
            # Update the caplines
            for i,pos in enumerate(error_positions):
                caplines[i].set_data(pos)

            # Update the error bars
            barlinecols[0].set_segments(zip(zip(*error_positions[0]), zip(*error_positions[1])))

    def clearAllPlots(self):

        self.subplot_labels = copy.copy(self.default_subplot_labels)

        self.subplot1.cla()
        self.subplot2.cla()

        self.plotted_sasms = []

        self._updateFrameStylesForAllPlots()

        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)

        is_zline1 = self.plotparams['zero_line1']
        is_zline2 = self.plotparams['zero_line2']

        if is_zline1:
            axes = self.subplot1
            zero = axes.axhline(color='k')
            zero.set_label('_zero_')

        if is_zline2:
            axes = self.subplot2
            zero = axes.axhline(color='k')
            zero.set_label('_zero_')

        self.updatePlotAxes()

    def _setLabels(self, sasm = None, title = None, xlabel = None, ylabel = None, axes = None):

        if axes == None:
            a = self.fig.gca()
        else:
            a = axes

        # Set labels
        if title == None:
            if a == self.subplot1:
                plottype = self.plotparams['plot1type']
                a.title.set_text(self.subplot_labels[plottype][0])
                a.title.set_size(self.plotparams['title_fontsize1'])
                a.title.set_fontname(self.plotparams['title_font1'])
                a.yaxis.get_label().set_text(self.subplot_labels[plottype][2])
                a.yaxis.get_label().set_fontname(self.plotparams['ylabel_font1'])
                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize1'])
                a.xaxis.get_label().set_text(self.subplot_labels[plottype][1])
                a.xaxis.get_label().set_fontname(self.plotparams['xlabel_font1'])
                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize1'])

            elif a == self.subplot2:
                plottype = self.plotparams['plot2type']
                a.title.set_text(self.subplot_labels[plottype][0])
                a.title.set_size(self.plotparams['title_fontsize2'])
                a.title.set_fontname(self.plotparams['title_font2'])
                a.yaxis.get_label().set_text(self.subplot_labels[plottype][2])
                a.yaxis.get_label().set_fontname(self.plotparams['ylabel_font2'])
                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize2'])
                a.xaxis.get_label().set_text(self.subplot_labels[plottype][1])
                a.xaxis.get_label().set_fontname(self.plotparams['xlabel_font2'])
                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize2'])
        else:
            a.title.set_text(title)
            if a == self.subplot1:
                a.title.set_fontname(self.plotparams['title_font1'])
                a.title.set_size(self.plotparams['title_fontsize1'])

            elif a == self.subplot2:
                a.title.set_fontname(self.plotparams['title_font2'])
                a.title.set_size(self.plotparams['title_fontsize2'])

    def updateLegend(self, plotnum, draw = True):
        axes = plotnum

        print plotnum

        if plotnum == 1:
            axes = self.subplot1
        elif plotnum == 2:
            axes = self.subplot2
        elif plotnum == self.subplot1:
            plotnum = 1
        elif plotnum == self.subplot2:
            plotnum = 2

        self._insertLegend(axes, draw)

    def _insertLegend(self, axes, draw = True):
        ####################################################################
        # NB!! LEGEND IS THE BIG SPEED HOG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ###################################################################
        a = axes

        if a == self.subplot1:
            plotnum = 1
        elif a == self.subplot2:
            plotnum = 2

        if axes.lines:
            legend_lines = []
            legend_labels = []

            old_legend = axes.get_legend()

            if  old_legend is not None:
                self.plotparams['legend_pos%s' %(plotnum)] = old_legend._loc

                old_title = old_legend.get_title()
                old_title_text = old_title.get_text()
                old_title_weight = old_title.get_weight()
                old_title_style = old_title.get_style()

                axes.legend_ = None

            for each_line in axes.lines:
                if each_line.get_visible() == True and each_line.get_label() != '_zero_' and each_line.get_label() != '_nolegend_' and each_line.get_label() != '_line1':
                    legend_lines.append(each_line)
                    legend_labels.append(each_line.get_label())

            if not legend_lines:
                return

            if axes == self.subplot1:
                fontsize = self.plotparams['legend_fontsize1']
                fontname = self.plotparams['legend_font1']
                enable_border = self.plotparams['legend_border1']
                alpha = self.plotparams['legend_alpha1']
                leg_visible = self.plotparams['legend_visible1']
                shadow = self.plotparams['legend_shadow1']

                legtit_size = self.plotparams['legtit_fontsize1']
                legtit_font = self.plotparams['legtit_font1']

            else:
                fontsize = self.plotparams['legend_fontsize2']
                fontname = self.plotparams['legend_font2']
                enable_border =  self.plotparams['legend_border2']
                alpha = self.plotparams['legend_alpha2']
                leg_visible = self.plotparams['legend_visible2']
                shadow = self.plotparams['legend_shadow1']

                legtit_size = self.plotparams['legtit_fontsize2']
                legtit_font = self.plotparams['legtit_font2']


            leg = a.legend(legend_lines, legend_labels, prop = fm.FontProperties(size = fontsize, family = fontname), fancybox = True)
            leg.get_frame().set_alpha(alpha)
            leg.shadow = shadow

            #Set up the title correctly
            if old_legend is not None:
                title = leg.get_title()
                title.set_style(old_title_style)
                title.set_weight(old_title_weight)
                title.set_fontname(legtit_font)
                title.set_size(legtit_size)
                title.set_text(old_title_text)

                leg.set_title(title.get_text())

            else:
                leg.set_title('')

                title = leg.get_title()
                title.set_fontname(legtit_font)
                title.set_size(legtit_size)


            if leg_visible:
                leg.set_visible(True)
            else:
                leg.set_visible(False)

            if not enable_border:
                leg.get_frame().set_linewidth(0)
            else:
                leg.get_frame().set_linewidth(1)

            try:
                leg.draggable()   #Interferes with the scroll zoom!
                if self.plotparams['legend_pos%s' %(plotnum)] is not None:
                    leg._loc = self.plotparams['legend_pos%s' %(plotnum)]
            except AttributeError:
                print "WARNING: Old matplotlib version, legend not draggable"

        if draw:
            self.canvas.draw()

    def _setColor(self, rgbtuple):
        """Set figure and canvas colours to be the same"""
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()

        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))


class IftPlotPanel(PlotPanel):

    def __init__(self, parent, id, name, *args, **kwargs):

        wx.Panel.__init__(self, parent, id, *args, name = name, **kwargs)

        file_drop_target = RAWCustomCtrl.RawPlotFileDropTarget(self, 'ift')
        self.SetDropTarget(file_drop_target)

        self._initFigure()

        self.toolbar = CustomPlotToolbar(self, self.canvas)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        #color = parent.GetThemeBackgroundColour()
        self.SetSizer(sizer)
        #self._setColor(color)

        # Variables for the plotted experiments:
        self.legend_names = []
        self.plotted_iftms = []

        self.selected_line = None
        self.selected_line_orig_width = 1
        self._plot_shown = 0

        #Timer to automatically restore line width after selection
        self.blink_timer = wx.Timer()
        self.blink_timer.Bind(wx.EVT_TIMER, self._onBlinkTimer)

        #Find the plot font, which is strangely hard!
        font_list = fm.get_fontconfig_fonts()

        fonts=[]

        for item in font_list:
            try:
                font_name = fm.FontProperties(fname=item).get_name()

                if font_name != 'System Font' and not font_name.startswith('.'):
                    fonts.append(font_name)
            except:
                pass

        mpl_font_dir = os.path.join(matplotlib.rcParams['datapath'],'fonts/ttf')
        font_list2 = fm.list_fonts(mpl_font_dir, '*.ttf')

        for item in font_list2:
            fp = fm.FontProperties()
            try:
                fp.set_file(item)
                font_name = fp.get_name()
                if font_name != 'System Font' and not font_name.startswith('.'):
                    fonts.append(font_name)
            except:
                pass

        fonts = list(set(fonts))
        fonts.sort()

        possible_fonts = matplotlib.rcParams['font.'+matplotlib.rcParams['font.family'][0]]

        found_font = False
        i = 0
        self.default_plot_font = None
        while not found_font and i in range(len(possible_fonts)):
            test_font = possible_fonts[i]

            if test_font in fonts:
                self.default_plot_font = test_font
                found_font = True

            i = i + 1

        if self.default_plot_font is None:
            self.default_plot_font = 'Arial'

        self.plotparams = {         'axesscale1'            : 'linlin',
                                    'axesscale2'            : 'loglin',
                                    'plot1type'             : 'normal',
                                    'plot2type'             : 'subtracted',
                                    'errorbars_on'          : False,

                                    'legend_pos1'           : None,
                                    'legend_pos2'           : None,
                                    'legend_visible1'       : False,
                                    'legend_visible2'       : False,
                                    'legend_fontsize1'      : 10,
                                    'legend_fontsize2'      : 10,
                                    'legend_border1'        : False,
                                    'legend_border2'        : False,
                                    'legend_alpha1'         : 0.7,
                                    'legend_alpha2'         : 0.7,
                                    'legend_shadow1'        : False,
                                    'legend_shadow2'        : False,
                                    'legend_font1'          : self.default_plot_font,
                                    'legend_font2'          : self.default_plot_font,

                                    'legtit_fontsize1'      : 12,
                                    'legtit_fontsize2'      : 12,
                                    'legtit_font1'          : self.default_plot_font,
                                    'legtit_font2'          : self.default_plot_font,

                                    'auto_fitaxes1'         : True,
                                    'auto_fitaxes2'         : True,
                                    'framestyle1'           : 'lb',
                                    'framestyle2'           : 'lb',

                                    'title_fontsize1'       : 16,
                                    'xlabel_fontsize1'      : 15,
                                    'ylabel_fontsize1'      : 15,

                                    'title_fontsize2'       : 16,
                                    'xlabel_fontsize2'      : 15,
                                    'ylabel_fontsize2'      : 15,

                                    'title_font1'           : self.default_plot_font,
                                    'xlabel_font1'          : self.default_plot_font,
                                    'ylabel_font1'          : self.default_plot_font,

                                    'title_font2'           : self.default_plot_font,
                                    'xlabel_font2'          : self.default_plot_font,
                                    'ylabel_font2'          : self.default_plot_font,

                                    'zero_line1'            : False,
                                    'zero_line2'            : False}

        self.frame_styles = ['Full', 'XY', 'X', 'Y', 'None']

        self.default_subplot_labels = { 'subtracted'  : ('Data/Fit', '$q$', '$I(q)$'),
                                        'kratky'      : ('Kratky', '$q$ [1/A]', '$I(q)q^2$'),
                                        'porod'       : ('Porod', '$q$ [1/A]', '$I(q)q^4$'),
                                        'guinier'     : ('Guinier', '$q^2$ [1/A^2]', '$\ln(I(q)$'),
                                        'normal'      : ('Pair Distance Distribution Function', '$r$', '$P(r)$')}

        self.subplot_labels = copy.copy(self.default_subplot_labels)

        self.save_parameters ={'dpi' : 100,
                               'format' : 'png'}

        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)

        self._updateFrameStylesForAllPlots()
        self.updatePlotType(self.subplot1)
        self.updatePlotAxes()

        self.canvas.callbacks.connect('pick_event', self._onPickEvent)
        self.canvas.callbacks.connect('key_press_event', self._onKeyPressEvent)
        self.canvas.callbacks.connect('motion_notify_event', self._onMouseMotionEvent)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        self.canvas.callbacks.connect('scroll_event', self._onMouseScrollEvent)

        # self._canvas_cursor = Cursor(self.subplot1, useblit=True, color='red', linewidth=1, linestyle ='--' )
        # self._canvas_cursor.horizOn = False


    def _initFigure(self):
        self.fig = matplotlib.figure.Figure((5,4), 75)
        self.subplot1 = self.fig.add_subplot(211)
        self.subplot2 = self.fig.add_subplot(212)

        self.fig.subplots_adjust(left = 0.14, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = MyFigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

    def setParameter(self, param, value):
        self.plotparams[param] = value

    def getParameter(self, param):
        return self.plotparams[param]


    def _updateFrameStylesForAllPlots(self):
        try:
            self.updateFrameStyle(axes = self.subplot1)
            self.updateFrameStyle(axes = self.subplot2)
        except Exception, e:
            print 'Possibly too old matplotlib version: ' + str(e)
            pass

    def updateFrameStyle(self, axes):
        if axes == self.subplot1:
            plotnum = '1'
        else:
            plotnum = '2'

        style = self.plotparams['framestyle' + plotnum]

        self.setFrameStyle(axes, style)

    def setFrameStyle(self, axes, style):

        if style.find('l')>-1:
            axes.spines['left'].set_color('black')
            axes.tick_params(left=True, which = 'both')
        else:
            axes.spines['left'].set_color('none')
            axes.tick_params(left=False, which = 'both')
        if style.find('r')>-1:
            axes.spines['right'].set_color('black')
            axes.tick_params(right=True, which = 'both')
        else:
            axes.spines['right'].set_color('none')
            axes.tick_params(right=False, which = 'both')
        if style.find('t')>-1:
            axes.spines['top'].set_color('black')
            axes.tick_params(top=True, which = 'both')
        else:
            axes.spines['top'].set_color('none')
            axes.tick_params(top=False, which = 'both')
        if style.find('b')>-1:
            axes.spines['bottom'].set_color('black')
            axes.tick_params(bottom=True, which = 'both')
        else:
            axes.spines['bottom'].set_color('none')
            axes.tick_params(bottom=False, which = 'both')


    def fitAxis(self, axes = None, forced = False):

        if axes:
            plots = axes
        else:
            plots = [self.subplot1, self.subplot2]

        for eachsubplot in plots:
            if eachsubplot.lines:

                maxq = None
                maxi = None

                minq = None
                mini = None

                if eachsubplot == self.subplot1:
                    plotnum = '1'
                else:
                    plotnum = '2'

                if self.plotparams['auto_fitaxes' + plotnum] == False and forced == False:
                    print 'Not fitting axes due to plot settings'
                    try:
                        self.canvas.draw()
                    except ValueError, e:
                        print 'ValueError in fitaxis() : ' + str(e)
                    return

                for each in eachsubplot.lines:
                    if each._label != '_nolegend_' and each._label != '_zero_' and each.get_visible() == True:

                        if maxq == None:
                            maxq = max(each.get_xdata())
                            maxi = max(each.get_ydata())

                            minq = min(each.get_xdata())
                            mini = min(each.get_ydata())

                        xmax = max(each.get_xdata())
                        ymax = max(each.get_ydata())

                        xmin = min(each.get_xdata())
                        ymin = min(each.get_ydata())

                        if xmax > maxq:
                            maxq = xmax
                        if xmin < minq:
                            minq = xmin
                        if ymax > maxi:
                            maxi = ymax
                        if ymin < mini:
                            mini = ymin

                eachsubplot.set_ylim(mini, maxi)
                eachsubplot.set_xlim(minq, maxq)

                # self.updateFrameStyle(eachsubplot)

        try:
            self.canvas.draw()
        except ValueError, e:
            print 'ValueError in fitaxis() : ' + str(e)


    def _onBlinkTimer(self, event):

        try:
            self.selected_line.set_linewidth(self.selected_line_orig_width)
            self.canvas.draw()
        except:
            pass

        self.selected_line = None
        self.blink_timer.Stop()

    def _onPickEvent(self, event):

        mouseevent = event.mouseevent
        if mouseevent.button == 'up' or mouseevent.button == 'down':
            return


        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')

        if self.selected_line != None:
            self.selected_line.set_linewidth(self.selected_line_orig_width)

        self.selected_line = event.artist

        try:
            self.selected_line_orig_width = self.selected_line.get_linewidth()
            self.selected_line.set_linewidth(self.selected_line_orig_width + 2)
        except AttributeError:
            self.selected_line = None
            return

        wx.CallAfter(self.manipulation_panel.deselectAllExceptOne, None, self.selected_line)
        self.canvas.draw()

        self.blink_timer.Start(500)

    def _onKeyPressEvent(self, event):
        pass


    def _onMouseScrollEvent(self, event):

        return

        x_size,y_size = self.canvas.get_width_height()
        half_y = y_size / 2

        if self._plot_shown == 1:
            selected_plot = 1
        elif self._plot_shown == 2:
            selected_plot = 2
        elif event.y <= half_y:
            selected_plot = 2
        else:
            selected_plot = 1

        if selected_plot == 1:
            ax = self.subplot1
        else:
            ax = self.subplot2

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        cur_xrange = (cur_xlim[1] - cur_xlim[0])
        cur_yrange = (cur_ylim[1] - cur_ylim[0])

        xdata = event.xdata # get event x location
        ydata = event.ydata # get event y location

        if event.button == 'up':
            # zoom in
            scale_factor = 1.15
        elif event.button == 'down':
            # zoom out
            scale_factor = 0.85
        else:
            # deal with something that should never happen
            scale_factor = 1
            print event.button

        # MOVE AXIS
        zx_pix, zy_pix = ax.transAxes.transform((0,0))
        cx_pix, cy_pix = ax.transAxes.transform((0.5,0.5))


        xy = np.array([(xdata,ydata), (xdata, ydata)])

        mx_pix, my_pix = ax.transData.transform(xy)
        mx_pix = mx_pix[0]
        my_pix = my_pix[1]


        dx = cx_pix - mx_pix
        dy = cy_pix - my_pix

        dist = np.sqrt(np.power(abs(dx),2)+np.power(abs(dy),2))

        step = 0.15
        new_dist = dist * step   #step = 0..1

        tanA = abs(dy) / abs(dx)
        A = np.arctan(tanA)

        new_dx = np.cos(A) * new_dist
        new_dy = tanA * new_dx

        zdx = zx_pix + new_dx
        zdy = zy_pix + new_dy

        inv = ax.transData.inverted()


        zxdata, zydata = inv.transform((zx_pix, zy_pix))


        zstpx, zstpy = inv.transform((zdx, zdy))


        dx_move = zstpx - zxdata
        dy_move = zstpy - zydata


        if dx >= 0:
            newxmin = cur_xlim[0] - dx_move
            newxmax = cur_xlim[1] - dx_move
        if dx < 0:
            newxmin = cur_xlim[0] + dx_move
            newxmax = cur_xlim[1] + dx_move

        try:
            newxlim = (newxmin, newxmax)
        except UnboundLocalError:
            return

        if dy >= 0:
            newymin = cur_ylim[0] - dy_move
            newymax = cur_ylim[1] - dy_move
        if dy < 0:
            newymin = cur_ylim[0] + dy_move
            newymax = cur_ylim[1] + dy_move

        newylim = (newymin, newymax)


        #ZOOM
        cur_xrange = (cur_xlim[1] - cur_xlim[0])
        cur_yrange = (cur_ylim[1] - cur_ylim[0])

        new_xrange = scale_factor * cur_xrange
        new_yrange = scale_factor * cur_yrange

        dxrange = cur_xrange - new_xrange
        dyrange = cur_yrange - new_yrange

        xmin, xmax = newxlim
        newxlim_zoom = (xmin - (dxrange/2.0), xmax + (dxrange/2.0))

        ymin,ymax = newylim
        newylim_zoom = (ymin - (dyrange/2.0), ymax + (dyrange/2.0))

        ax.set_xlim(newxlim_zoom)
        ax.set_ylim(newylim_zoom)

        self.canvas.draw() # force re-draw


    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''

        x_size,y_size = self.canvas.get_width_height()
        half_y = y_size / 2

        if self._plot_shown == 1:
            selected_plot = 1
        elif self._plot_shown == 2:
            selected_plot = 2
        elif event.y <= half_y:
            selected_plot = 2
        else:
            selected_plot = 1

        if event.button == 3:

            if float(matplotlib.__version__[:3]) >= 1.2:
                if self.toolbar.GetToolState(self.toolbar.wx_ids['Pan']) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, selected_plot)
                    else:
                        self._showPopupMenu(selected_plot)
            else:
                if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, selected_plot)
                    else:
                        self._showPopupMenu(selected_plot)

#--- ** Popup Menu ***

    def showErrorbars(self, state):

        for each in self.plotted_iftms:

            if each.r_line.get_visible():
                for each_err_line in each.r_err_line[0]:
                    each_err_line.set_visible(state)

                for each_err_line in each.r_err_line[1]:
                    each_err_line.set_visible(state)


            if each.qo_line.get_visible():
                for each_err_line in each.qo_err_line[0]:
                    each_err_line.set_visible(state)

                for each_err_line in each.qo_err_line[1]:
                    each_err_line.set_visible(state)

            if state:
                self.updateErrorBars(each)

        self.canvas.draw()

    def _showPopupMenu(self, selected_plot):

        self.selected_plot = selected_plot

        menu = wx.Menu()

        plot2SubMenu = self._createPopupAxesMenu('2')

        if selected_plot == 2:
            menu.AppendSubMenu(plot2SubMenu, 'Axes')

            menu.AppendSeparator()

        plot_options = menu.Append(wx.ID_ANY, 'Plot Options...')

        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

        self.Bind(wx.EVT_MENU, self._onPlotOptions, plot_options)


        self.PopupMenu(menu)

        menu.Destroy()

    def _onPlotOptions(self, evt):
        if self.selected_plot == 1:
            axes = self.subplot1
        else:
            axes = self.subplot2

        dlg = RAWCustomDialogs.PlotOptionsDialog(self, self.plotparams, axes)
        dlg.ShowModal()
        dlg.Destroy()

    def _onPopupMenuChoice(self, evt):
        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        id = evt.GetId()

        for key in MenuIDs.iterkeys():
            if MenuIDs[key] == id:

                if key[4] == '1':

                    if key[5:7] == 'ty':
                        self.plotparams['plot1type'] = key[7:]
                        self.updatePlotType(self.subplot1)

                        self.plotparams['axesscale1'] = 'linlin'

                        self.updatePlotAxes()
                        print '1'
                    else:
                        self.plotparams['axesscale1'] = key[7:]
                        self.plotparams['plot1type'] = 'normal'
                        self.updatePlotType(self.subplot1)
                        self.updatePlotAxes()
                        print '2'
                else:
                    if key[5:7] == 'ty':
                        self.plotparams['plot2type'] = key[7:]
                        self.updatePlotType(self.subplot2)

                        self.plotparams['axesscale2'] = 'linlin'
                        self.updatePlotAxes()

                        print '3'

                    else:
                        self.plotparams['axesscale2'] = key[7:]
                        self.plotparams['plot2type'] = 'subtracted'
                        self.updatePlotType(self.subplot2)
                        try:
                            self.updatePlotAxes()
                        except ValueError, e:
                            print e
                        print '4'

        #Update plot settings in menu bar:
        mainframe.setViewMenuScale(id)
        #evt.Skip()


    def _createPopupAxesMenu(self, plot_number):

        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        item_list = []
        pop_menu = wx.Menu()

        axes_list = [('sclinlin',    'Lin-Lin'),
                         ('scloglin',    'Log-Lin'),
                         ('scloglog',   'Log-Log'),
                         ('sclinlog',    'Lin-Log'),
                         ('tyguinier',  'Guinier'),
                         ('tykratky',   'Kratky'),
                         ('typorod',   'Porod') ]

        for key, label in axes_list:
            item = pop_menu.AppendRadioItem(MenuIDs['plot' + plot_number + key], label)
            item_list.append(item)

        self._markCurrentAxesSelection(item_list, plot_number)

        return pop_menu

    def _markCurrentAxesSelection(self, item_list, plot_number):
        ''' Set the current axes selection on the newly created
           popup menu '''

        if self.plotparams['plot' + plot_number + 'type'] == 'normal' or self.plotparams['plot' + plot_number + 'type'] == 'subtracted':

            if self.plotparams['axesscale' + plot_number + ''] == 'loglog':
                item_list[2].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'linlog':
                item_list[3].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'loglin':
                item_list[1].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'linlin':
                item_list[0].Check(True)

        else:
            if self.plotparams['plot' + plot_number + 'type'] == 'guinier':
                item_list[4].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'kratky':
                item_list[5].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'porod':
                item_list[6].Check(True)

    def updatePlotType(self, axes):

        for each in self.plotted_iftms:
            if each is not None and each.qo_line is not None and each.qf_line is not None:
                q_min, q_max = each.getQrange()

                c = '2'

                if self.plotparams['plot' + c + 'type'] == 'kratky':
                    each.qo_line.set_ydata(each.i_orig[q_min:q_max] * np.power(each.q_orig[q_min:q_max],2))
                    each.qo_line.set_xdata(each.q_orig[q_min:q_max])

                    each.qf_line.set_ydata(each.i_fit[q_min:q_max] * np.power(each.q_orig[q_min:q_max],2))
                    each.qf_line.set_xdata(each.q_orig[q_min:q_max])

                elif self.plotparams['plot' + c + 'type'] == 'guinier':
                    each.qo_line.set_ydata(np.log(each.i_orig[q_min:q_max]))
                    each.qo_line.set_xdata(np.power(each.q_orig[q_min:q_max],2))

                    each.qf_line.set_ydata(np.log(each.i_fit[q_min:q_max]))
                    each.qf_line.set_xdata(np.power(each.q_orig[q_min:q_max],2))

                elif self.plotparams['plot' + c + 'type'] == 'porod':
                    each.qo_line.set_ydata(np.power(each.q_orig[q_min:q_max],4)*each.i_orig[q_min:q_max])
                    each.qo_line.set_xdata(each.q_orig[q_min:q_max])

                    each.qf_line.set_ydata(np.power(each.q_orig[q_min:q_max],4)*each.i_fit[q_min:q_max])
                    each.qf_line.set_xdata(each.q_orig[q_min:q_max])

                elif self.plotparams['plot' + c + 'type'] == 'normal' or self.plotparams['plot' + c+ 'type'] == 'subtracted':
                    each.qo_line.set_ydata(each.i_orig[q_min:q_max])
                    each.qo_line.set_xdata(each.q_orig[q_min:q_max])

                    each.qf_line.set_ydata(each.i_fit[q_min:q_max])
                    each.qf_line.set_xdata(each.q_orig[q_min:q_max])

                self.updateErrorBars(each)

        self._setLabels(axes = self.subplot2)

        self.fitAxis()

    def updatePlotAxes(self):

        axes = [self.subplot1, self.subplot2]

        for a in axes:

            if a == self.subplot1:
                c = 1
            elif a == self.subplot2:
                c = 2

            if self.plotparams.get('axesscale' + str(c)) == 'linlin':
                a.set_xscale('linear')
                a.set_yscale('linear')

            if self.plotparams.get('axesscale'+ str(c)) == 'loglin':
                a.set_xscale('linear')

                a.set_ylim(1, 99999)
                a.set_yscale('log')
                a.set_ylim(1, 99999)
                #a.limit_range_for_scale(1, 99999)

            if self.plotparams.get('axesscale'+ str(c)) == 'loglog':
                a.set_xscale('log')
                a.set_yscale('log')

            if self.plotparams.get('axesscale'+ str(c)) == 'linlog':
                a.set_xscale('log')
                a.set_yscale('linear')

        self.fitAxis()

    def updatePlotAfterManipulation(self, sasm_list, draw = True):

        for sasm in sasm_list:
            a = sasm.axes

            if a == self.subplot1:
                type = self.plotparams.get('plot1type')
            elif a == self.subplot2:
                type = self.plotparams.get('plot2type')

            q_min, q_max = sasm.getQrange()
            q = sasm.q[q_min:q_max]
            i = sasm.i[q_min:q_max]

            if type == 'normal' or type == 'subtracted':
                sasm.line.set_data(q, i)

            elif type == 'kratky':
                sasm.line.set_data(q, i*np.power(q,2))
            elif type == 'guinier':
                sasm.line.set_data(np.power(q,2), np.log(i))
            elif type == 'porod':
                sasm.line.set_data(q, np.power(q,4)*i)

            self.updateErrorBars(sasm)

        if draw:
            self.fitAxis()

    def updateErrorBars(self, iftm):

        if iftm.r_err_line is not None:
            a = iftm.r_axes

            if a == self.subplot1:
                plottype= self.plotparams.get('plot1type')
            elif a == self.subplot2:
                plottype= self.plotparams.get('plot2type')
            #Update errorbar positions
            caplines = iftm.r_err_line[0]
            barlinecols = iftm.r_err_line[1]

            yerr = iftm.err
            x = iftm.r
            y = iftm.p

            # Find the ending points of the errorbars
            if plottype== 'normal' or plottype== 'subtracted':
                error_positions = (x, y-yerr), (x, y+yerr)
            elif plottype== 'kratky':
                error_positions = (x, (y-yerr)*np.power(x,2)), (x, (y+yerr)*np.power(x,2))
            elif plottype== 'porod':
                error_positions = (x, (y-yerr)*np.power(x,4)), (x, (y+yerr)*np.power(x,4))
            elif plottype == 'guinier':
                error_positions = (np.power(x,2), np.log((y-yerr))), (np.power(x,2), np.log((y+yerr)))
            # Update the caplines
            for i,pos in enumerate(error_positions):
                caplines[i].set_data(pos)

            # Update the error bars
            barlinecols[0].set_segments(zip(zip(*error_positions[0]), zip(*error_positions[1])))


        if iftm.qo_err_line is not None:
            a = iftm.qo_axes

            if a == self.subplot1:
                plottype= self.plotparams.get('plot1type')
            elif a == self.subplot2:
                plottype= self.plotparams.get('plot2type')
            #Update errorbar positions
            caplines = iftm.qo_err_line[0]
            barlinecols = iftm.qo_err_line[1]

            yerr = iftm.err_orig
            x = iftm.q_orig
            y = iftm.i_orig

            # Find the ending points of the errorbars
            if plottype== 'normal' or plottype== 'subtracted':
                error_positions = (x, y-yerr), (x, y+yerr)
            elif plottype== 'kratky':
                error_positions = (x, (y-yerr)*np.power(x,2)), (x, (y+yerr)*np.power(x,2))
            elif plottype== 'porod':
                error_positions = (x, (y-yerr)*np.power(x,4)), (x, (y+yerr)*np.power(x,4))
            elif plottype == 'guinier':
                error_positions = (np.power(x,2), np.log((y-yerr))), (np.power(x,2), np.log((y+yerr)))
            # Update the caplines
            for i,pos in enumerate(error_positions):
                caplines[i].set_data(pos)

            # Update the error bars
            barlinecols[0].set_segments(zip(zip(*error_positions[0]), zip(*error_positions[1])))

    def clearAllPlots(self):

        self.subplot_labels = copy.copy(self.default_subplot_labels)

        self.subplot1.cla()
        self.subplot2.cla()

        self.plotted_iftms = []

        self._updateFrameStylesForAllPlots()

        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)

        is_zline1 = self.plotparams['zero_line1']
        is_zline2 = self.plotparams['zero_line2']

        if is_zline1:
            axes = self.subplot1
            zero = axes.axhline(color='k')
            zero.set_label('_zero_')

        if is_zline2:
            axes = self.subplot2
            zero = axes.axhline(color='k')
            zero.set_label('_zero_')

        self.updatePlotAxes()

    def _setLabels(self, sasm = None, title = None, xlabel = None, ylabel = None, axes = None):

        if axes == None:
            a = self.fig.gca()
        else:
            a = axes

        # Set labels
        if title == None:
            if a == self.subplot1:
                plottype = self.plotparams['plot1type']
                a.title.set_text(self.subplot_labels[plottype][0])
                a.title.set_size(self.plotparams['title_fontsize1'])
                a.title.set_fontname(self.plotparams['title_font1'])
                a.yaxis.get_label().set_text(self.subplot_labels[plottype][2])
                a.yaxis.get_label().set_fontname(self.plotparams['ylabel_font1'])
                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize1'])
                a.xaxis.get_label().set_text(self.subplot_labels[plottype][1])
                a.xaxis.get_label().set_fontname(self.plotparams['xlabel_font1'])
                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize1'])

            elif a == self.subplot2:
                plottype = self.plotparams['plot2type']
                a.title.set_text(self.subplot_labels[plottype][0])
                a.title.set_size(self.plotparams['title_fontsize2'])
                a.title.set_fontname(self.plotparams['title_font2'])
                a.yaxis.get_label().set_text(self.subplot_labels[plottype][2])
                a.yaxis.get_label().set_fontname(self.plotparams['ylabel_font2'])
                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize2'])
                a.xaxis.get_label().set_text(self.subplot_labels[plottype][1])
                a.xaxis.get_label().set_fontname(self.plotparams['xlabel_font2'])
                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize2'])
        else:
            a.title.set_text(title)
            if a == self.subplot1:
                a.title.set_fontname(self.plotparams['title_font1'])
                a.title.set_size(self.plotparams['title_fontsize1'])

            elif a == self.subplot2:
                a.title.set_fontname(self.plotparams['title_font2'])
                a.title.set_size(self.plotparams['title_fontsize2'])

    def updateLegend(self, plotnum, draw = True):
        axes = plotnum

        print plotnum

        if plotnum == 1:
            axes = self.subplot1
        if plotnum == 2:
            axes = self.subplot2
        if plotnum == self.subplot1:
            plotnum = 1
        if plotnum == self.subplot2:
            plotnum = 2

        self._insertLegend(axes, draw)

    def _insertLegend(self, axes, draw = True):
        ####################################################################
        # NB!! LEGEND IS THE BIG SPEED HOG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ###################################################################
        if axes == self.subplot1:
            plotnum = 1
        elif axes == self.subplot2:
            plotnum = 2

        if axes.lines:
            legend_lines = []
            legend_labels = []

            old_legend = axes.get_legend()

            if  old_legend != None:
                self.plotparams['legend_pos%s' %(plotnum)] = old_legend._loc

                old_title = old_legend.get_title()
                old_title_text = old_title.get_text()
                old_title_weight = old_title.get_weight()
                old_title_style = old_title.get_style()

                axes.legend_ = None

            for each_line in axes.lines:
                if each_line.get_visible() == True and each_line.get_label() != '_zero_' and each_line.get_label() != '_nolegend_' and each_line.get_label() != '_line1':
                    legend_lines.append(each_line)
                    legend_labels.append(each_line.get_label())

            if not legend_lines:
                return

            if axes == self.subplot1:
                fontsize = self.plotparams['legend_fontsize1']
                fontname = self.plotparams['legend_font1']
                enable_border = self.plotparams['legend_border1']
                alpha = self.plotparams['legend_alpha1']
                leg_visible = self.plotparams['legend_visible1']
                shadow = self.plotparams['legend_shadow1']

                legtit_size = self.plotparams['legtit_fontsize1']
                legtit_font = self.plotparams['legtit_font1']
            else:
                fontsize = self.plotparams['legend_fontsize2']
                fontname = self.plotparams['legend_font2']
                enable_border =  self.plotparams['legend_border2']
                alpha = self.plotparams['legend_alpha2']
                leg_visible = self.plotparams['legend_visible2']
                shadow = self.plotparams['legend_shadow2']

                legtit_size = self.plotparams['legtit_fontsize2']
                legtit_font = self.plotparams['legtit_font2']

            leg = axes.legend(legend_lines, legend_labels, prop = fm.FontProperties(size = fontsize, family = fontname), fancybox = True)
            leg.get_frame().set_alpha(alpha)
            leg.shadow = shadow

            #Set up the title correctly
            if old_legend is not None:
                title = leg.get_title()
                title.set_style(old_title_style)
                title.set_weight(old_title_weight)
                title.set_fontname(legtit_font)
                title.set_size(legtit_size)
                title.set_text(old_title_text)

                leg.set_title(title.get_text())

            else:
                leg.set_title('')

                title = leg.get_title()
                title.set_fontname(legtit_font)
                title.set_size(legtit_size)

            if leg_visible:
                leg.set_visible(True)
            else:
                leg.set_visible(False)

            if not enable_border:
                leg.get_frame().set_linewidth(0)
            else:
                leg.get_frame().set_linewidth(1)

            try:
                leg.draggable()   #Interferes with the scroll zoom!
                if self.plotparams['legend_pos%s' %(plotnum)] is not None:
                    leg._loc = self.plotparams['legend_pos%s' %(plotnum)]

            except AttributeError:
                print "WARNING: Old matplotlib version, legend not draggable"
        if draw:
            self.canvas.draw()

    def _setColor(self, rgbtuple):
        """Set figure and canvas colours to be the same"""
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()

        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))


    def plotIFTM(self, iftm_list, legend_label_in = None, line_data = None, *args, **kwargs):

        a1 = self.subplot1
        a2 = self.subplot2

        type1 = self.plotparams.get('plot1type')
        type2 = self.plotparams.get('plot2type')

        if type(iftm_list) != list:
            iftm_list = [iftm_list]

        for iftm in iftm_list:

            q_min, q_max = iftm.getQrange()

            if legend_label_in == None:
                legend_label = iftm.getParameter('filename')
            else:
                legend_label = legend_label_in

            if type1 == 'normal' or type1 == 'subtracted':
                pr_line, pr_ec, pr_el = a1.errorbar(iftm.r, iftm.p, iftm.err, picker = 3, label = legend_label+'_P(r)', **kwargs)

            pr_line.set_label(legend_label)

            if type2 == 'normal' or type2 == 'subtracted':
                orig_line, orig_ec, orig_el = a2.errorbar(iftm.q_orig[q_min:q_max], iftm.i_orig[q_min:q_max], iftm.err_orig[q_min:q_max], picker = 3, label = legend_label+'_Exp', **kwargs)
            elif type2 == 'kratky':
                orig_line, orig_ec, orig_el = a2.errorbar(iftm.q_orig[q_min:q_max], iftm.i_orig[q_min:q_max] * np.power(iftm.q_orig[q_min:q_max],2), iftm.err_orig[q_min:q_max], picker = 3, label = legend_label+'_Exp',**kwargs)
            elif type2 == 'guinier':
                orig_line, orig_ec, orig_el = a2.errorbar(np.power(iftm.q_orig[q_min:q_max],2), iftm.i_orig[q_min:q_max], iftm.err_orig[q_min:q_max], picker = 3, label = legend_label+'_Exp',**kwargs)
            elif type2 == 'porod':
                orig_line, orig_ec, orig_el = a2.errorbar(iftm.q_orig[q_min:q_max], np.power(iftm.q_orig[q_min:q_max],4)*iftm.i_orig[q_min:q_max], iftm.err_orig[q_min:q_max], picker = 3, label = legend_label+'_Exp',**kwargs)

            orig_line.set_label(legend_label+'_Exp')


            if type2 == 'normal' or type2 == 'subtracted':
                fit_line = a2.plot(iftm.q_orig[q_min:q_max], iftm.i_fit[q_min:q_max], picker = 3, label = legend_label+'_Fit', **kwargs)
            elif type2 == 'kratky':
                fit_line = a2.plot(iftm.q_orig[q_min:q_max], iftm.i_fit[q_min:q_max] * np.power(iftm.q_orig[q_min:q_max],2), picker = 3, label = legend_label+'_Fit',**kwargs)
            elif type2 == 'guinier':
                fit_line = a2.plot(np.power(iftm.q_orig[q_min:q_max],2), iftm.i_fit[q_min:q_max], picker = 3, label = legend_label+'_Fit',**kwargs)
            elif type2 == 'porod':
                fit_line = a2.plot(iftm.q_orig[q_min:q_max], np.power(iftm.q_orig[q_min:q_max],4)*iftm.i_fit[q_min:q_max], picker = 3, label = legend_label+'_Fit',**kwargs)

            #Hide errorbars:
            if self.plotparams['errorbars_on'] == False:
                for each in pr_ec:
                    each.set_visible(False)

                for each in pr_el:
                    each.set_visible(False)

                for each in orig_ec:
                    each.set_visible(False)

                for each in orig_el:
                    each.set_visible(False)

            iftm.r_line = pr_line
            iftm.qo_line = orig_line
            iftm.qf_line = fit_line[0]

            iftm.r_err_line = (pr_ec, pr_el)
            iftm.qo_err_line = (orig_ec, orig_el)

            iftm.r_axes = a1
            iftm.qo_axes = a2
            iftm.qf_axes = a2

            iftm.plot_panel = self

            iftm.canvas = self.canvas

            iftm.is_plotted = True

            self.plotted_iftms.append(iftm)        # Insert the plot into plotted experiments list

            if line_data != None:
                iftm.r_line.set_linewidth(line_data['r_line_width'])
                iftm.r_line.set_linestyle(line_data['r_line_style'])
                iftm.r_line.set_color(line_data['r_line_color'])
                iftm.r_line.set_marker(line_data['r_line_marker'])
                iftm.r_line.set_visible(line_data['r_line_visible'])

                iftm.qo_line.set_linewidth(line_data['qo_line_width'])
                iftm.qo_line.set_linestyle(line_data['qo_line_style'])
                iftm.qo_line.set_color(line_data['qo_line_color'])
                iftm.qo_line.set_marker(line_data['qo_line_marker'])
                iftm.qo_line.set_visible(line_data['qo_line_visible'])

                iftm.qf_line.set_linewidth(line_data['qf_line_width'])
                iftm.qf_line.set_linestyle(line_data['qf_line_style'])
                iftm.qf_line.set_color(line_data['qf_line_color'])
                iftm.qf_line.set_marker(line_data['qf_line_marker'])
                iftm.qf_line.set_visible(line_data['qf_line_visible'])

                try:
                    iftm.r_line.set_markerfacecolor(line_data['r_line_marker_face_color'])
                    iftm.r_line.set_markeredgecolor(line_data['r_line_marker_edge_color'])

                    for each in iftm.r_err_line:
                        for line in each:
                            line.set_color(line_data['r_line_errorbar_color'])

                    iftm.qo_line.set_markerfacecolor(line_data['qo_line_marker_face_color'])
                    iftm.qo_line.set_markeredgecolor(line_data['qo_line_marker_edge_color'])

                    for each in iftm.qo_err_line:
                        for line in each:
                            line.set_color(line_data['qo_line_errorbar_color'])

                    iftm.qf_line.set_markerfacecolor(line_data['qf_line_marker_face_color'])
                    iftm.qf_line.set_markeredgecolor(line_data['qf_line_marker_edge_color'])

                except KeyError:
                    pass #Version <1.3.0 doesn't have these keys


    def _onMouseMotionEvent(self, event):

        if event.inaxes == self.subplot1:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('r = ' +  str(round(x,5)) + ', P(r) = ' + str(round(y,5)), 1)
        elif event.inaxes == self.subplot2:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('q = ' +  str(round(x,5)) + ', I(q) = ' + str(round(y,5)), 1)

class FigureSavePanel(wx.Panel):
    #def __init__(self, parent, plotparams, axes, *args, **kwargs):
    def __init__(self, parent,figure, save_parameters, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.figure = figure
        self.old_unit = 'inches'
        self.save_parameters = save_parameters

        box = wx.StaticBox(self, -1, 'Settings')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        imgsize_sizer = self.createImageSizeSettings()

        sizer.Add(imgsize_sizer, 0, wx.ALL, 5)

        self.tight_border = wx.CheckBox(self, -1, 'Cut border padding')
        self.tight_border.SetValue(False)

        sizer.Add(self.tight_border, 0, wx.ALL, 5)


        self.updateSettings()

        self.SetSizer(sizer)
        self.Fit()
        self.CenterOnParent()

    def updateSettings(self):
        dpi = wx.FindWindowByName('Dpi')
        width = wx.FindWindowByName('Width')
        height = wx.FindWindowByName('Height')

        #dpi_val = self.figure.get_dpi()
        dpi_val = self.save_parameters['dpi']

        size = self.figure.get_size_inches()

        width.SetValue(str(size[0]))
        height.SetValue(str(size[1]))

        dpi.SetValue(str(dpi_val))

    def createImageSizeSettings(self):
        grid_sizer = wx.FlexGridSizer(cols = 3, rows = 4, vgap = 5, hgap = 5)

        format_list = ['png', 'eps', 'ps', 'pdf', 'tif', 'jpg', 'raw', 'svg']

        self.format_label= wx.StaticText(self, -1, 'Format:')
        self.format_choice = wx.Choice(self, -1, choices = format_list)
        self.format_choice.Select(format_list.index(self.save_parameters['format']))

        grid_sizer.Add(self.format_label, 0)
        grid_sizer.Add(self.format_choice, 0)
        grid_sizer.Add((1,1) ,0)

        data = ['Dpi', 'Width', 'Height']
        unit_list = ['inches', 'milimeters', 'pixels']

        for each in data:
            label = wx.StaticText(self, -1, each + ' :')

            if each == 'Dpi':
                ctrl = RAWCustomCtrl.IntSpinCtrl(self, -1, name = each, TextLength = 60)
            else:
                ctrl = RAWCustomCtrl.FloatSpinCtrl(self, -1, name = each, TextLength = 60)

            grid_sizer.Add(label, 0, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 5)
            grid_sizer.Add(ctrl, 0, wx.ALIGN_CENTRE_VERTICAL)

            if each == 'Height':
                self.unit_choice = wx.Choice(self, -1, choices = unit_list)
                self.unit_choice.Bind(wx.EVT_CHOICE, self.onUnitChoice)
                self.unit_choice.Select(0)
                grid_sizer.Add(self.unit_choice, 0, wx.ALIGN_CENTRE_VERTICAL)
            else:
                grid_sizer.Add((1,1), 0)

        return grid_sizer

    def onUnitChoice(self, event):

        width = wx.FindWindowByName('Width')
        height = wx.FindWindowByName('Height')
        dpi = wx.FindWindowByName('Dpi')

        height_val = float(height.GetValue())
        width_val = float(width.GetValue())
        dpi_val = int(dpi.GetValue())

        new_unit = self.unit_choice.GetStringSelection()

        new_height = height_val
        new_width = width_val

        if self.old_unit == 'inches':
            if new_unit == 'milimeters':
                new_height = round(height_val / 0.0393700787, 2)
                new_width = round(width_val / 0.0393700787, 2)

            elif new_unit == 'pixels':
                new_height = round(height_val * dpi_val,0)
                new_width = round(width_val * dpi_val, 0)

        elif self.old_unit == 'milimeters':
             if new_unit == 'inches':
                new_height = round(height_val * 0.0393700787, 3)
                new_width = round(width_val * 0.0393700787, 3)

             elif new_unit == 'pixels':
                new_height = round((height_val * 0.0393700787) * dpi_val,0)
                new_width = round((width_val * 0.0393700787) * dpi_val, 0)

        elif self.old_unit == 'pixels':
            if new_unit == 'inches':
                new_height = round(height_val / float(dpi_val), 3)
                new_width = round(width_val / float(dpi_val), 3)

            elif new_unit == 'milimeters':
                new_height = round((height_val / float(dpi_val)) / 0.0393700787, 2)
                new_width = round((width_val / float(dpi_val)) / 0.0393700787, 2)

        height.SetValue(str(new_height))
        width.SetValue(str(new_width))

        self.old_unit = new_unit

    def getSaveParameters(self):

        dpi = wx.FindWindowByName('Dpi')
        width = wx.FindWindowByName('Width')
        height = wx.FindWindowByName('Height')

        dpi_val = int(dpi.GetValue())
        width_val = float(width.GetValue())
        height_val = float(height.GetValue())

        fmt = self.format_choice.GetStringSelection()

        if self.unit_choice.GetStringSelection() == 'pixels':
            height_val = round(height_val / float(dpi_val), 5)
            width_val = round(width_val / float(dpi_val), 5)
        elif self.unit_choice.GetStringSelection() == 'milimeters':
            height_val = round(height_val * 0.0393700787, 5)
            width_val = round(width_val * 0.0393700787, 5)

        par_dict = {'height' : height_val,
                    'width' : width_val,
                    'dpi' : dpi_val,
                    'fmt' : fmt,
                    'cut' : self.tight_border.GetValue()}

        return par_dict

class FigureSaveDialog(wx.Dialog):

    def __init__(self, parent, figure, save_parameters, *args, **kwargs):
        wx.Dialog.__init__(self, parent, -1, 'Save figure', *args, **kwargs)

        self.figure = figure
        self.parent = parent
        self.save_parameters = save_parameters

        dpi_val = str(self.figure.get_dpi())
        size_val = self.figure.get_size_inches()

        self.old_fig_val = {'dpi' : dpi_val,
                            'x' : size_val[0],
                            'y' : size_val[1]}

        self.save_panel = FigureSavePanel(self, figure, save_parameters)

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind(wx.EVT_BUTTON, self._onOk, id = wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id = wx.ID_CANCEL)

        top_sizer.Add(self.save_panel, 1, wx.ALL, 10)

        top_sizer.Add(buttons, 0, wx.BOTTOM | wx.ALIGN_CENTRE_HORIZONTAL, 10)

        self.SetSizer(top_sizer)
        self.Fit()
        self.CenterOnParent()

    def restoreFigureSize(self):

        self.figure.set_dpi(int(self.old_fig_val['dpi']))

        x = self.old_fig_val['x']
        y = self.old_fig_val['y']

        self.figure.set_size_inches(float(x),float(y))

        self.parent.canvas.draw()

    def _onCancel(self, event):
        self.restoreFigureSize()
        self.EndModal(wx.CANCEL)

    def _onOk(self, event):

        try:
            par = self.save_panel.getSaveParameters()
        except ValueError:
            wx.MessageBox('You have provided invalid values.', 'Input error', style = wx.ICON_ERROR)
            return

        self.figure.set_dpi(par['dpi'])
        self.figure.set_size_inches(par['width'], par['height'])

        default_file = "image." + par['fmt']

        filters = '(*.' +  par['fmt'] + ')|*.' + par['fmt']

        dlg = wx.FileDialog(self.parent, "Save to file", "", default_file,
                            wildcard = filters,
                            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            dirname  = dlg.GetDirectory()
            filename = dlg.GetFilename()

            basename, ext = os.path.splitext(filename)

            filename = os.path.join(dirname, filename)

            if par['cut']:
                self.figure.savefig(filename, dpi = par['dpi'], bbox_inches='tight', format = par['fmt'])#, pad_inches=0)
            else:
                self.figure.savefig(filename, dpi = par['dpi'], format = par['fmt'])

            self.save_parameters['dpi'] = int(par['dpi'])
            self.save_parameters['format'] = par['fmt']
        else:
            return

        self.restoreFigureSize()

        self.EndModal(wx.OK)


class CustomSeriesPlotToolbar(NavigationToolbar2WxAgg):
    def __init__(self, parent, canvas):

        self.fig_axes = parent.fig.gca()
        self.parent = parent

        self.saved_artists = None

        self._MTB_CLR1 = self.NewControlId()

        NavigationToolbar2WxAgg.__init__(self, canvas)

        self.workdir = RAWGlobals.RAWWorkDir

        self.Bind(wx.EVT_TOOL, self.clear1, id = self._MTB_CLR1)

        self.Realize()

    def home(self, *args, **kwargs):
        self.parent.fitAxis(forced = True)

    def save(self,  *args, **kwargs):
        dia = FigureSaveDialog(self.parent, self.parent.fig, self.parent.save_parameters)
        dia.ShowModal()
        dia.Destroy()

    def clear1(self, evt):
        self.parent.clearSubplot(self.parent.subplot1)


class SeriesPlotPanel(wx.Panel):

    def __init__(self, parent, id, name, *args, **kwargs):

        wx.Panel.__init__(self, parent, id, *args, name = name, **kwargs)

        file_drop_target = RAWCustomCtrl.RawPlotFileDropTarget(self, 'sec')
        self.SetDropTarget(file_drop_target)

        #Find the plot font, which is strangely hard!
        font_list = fm.get_fontconfig_fonts()

        fonts=[]

        for item in font_list:
            try:
                font_name = fm.FontProperties(fname=item).get_name()

                if font_name != 'System Font' and not font_name.startswith('.'):
                    fonts.append(font_name)
            except:
                pass

        mpl_font_dir = os.path.join(matplotlib.rcParams['datapath'],'fonts/ttf')
        font_list2 = fm.list_fonts(mpl_font_dir, '*.ttf')

        for item in font_list2:
            fp = fm.FontProperties()
            try:
                fp.set_file(item)
                font_name = fp.get_name()
                if font_name != 'System Font' and not font_name.startswith('.'):
                    fonts.append(font_name)
            except:
                pass

        fonts = list(set(fonts))
        fonts.sort()

        possible_fonts = matplotlib.rcParams['font.'+matplotlib.rcParams['font.family'][0]]

        found_font = False
        i = 0
        self.default_plot_font = None
        while not found_font and i in range(len(possible_fonts)):
            test_font = possible_fonts[i]

            if test_font in fonts:
                self.default_plot_font = test_font
                found_font = True

            i = i + 1

        if self.default_plot_font is None:
            self.default_plot_font = 'Arial'

        self.plotparams = {         'axesscale1'            : 'linlin',
                                    'axesscale2'            : 'linlin',
                                    'plot1type'             : 'normal',
                                    'plot2type'             : 'subtracted',
                                    'errorbars_on'          : False,

                                    'legend_pos1'           : None,
                                    'legend_visible1'       : False,
                                    'legend_fontsize1'      : 10,
                                    'legend_border1'        : False,
                                    'legend_alpha1'         : 0.7,
                                    'legend_shadow1'        : False,
                                    'legend_showcalc1'      : False,

                                    'legtit_fontsize1'      : 12,

                                    'legtit_font1'          : self.default_plot_font,

                                    'auto_fitaxes1'         : True,
                                    'auto_fitaxes2'         : True,
                                    'framestyle1'           : 'lb',
                                    'framestyle2'           : 'r',

                                    'title_fontsize1'       : 16,
                                    'xlabel_fontsize1'      : 15,
                                    'ylabel_fontsize1'      : 15,
                                    'y2label_fontsize1'     : 15,

                                    'title_font1'           : self.default_plot_font,
                                    'xlabel_font1'          : self.default_plot_font,
                                    'ylabel_font1'          : self.default_plot_font,
                                    'y2label_font1'         : self.default_plot_font,
                                    'legend_font1'          : self.default_plot_font,

                                    'zero_line1'            : False,

                                    'y_axis_display'        : 'total',
                                    'x_axis_display'        : 'frame',
                                    'intensity_q'           : '0',
                                    'secm_plot_q'           : '0',
                                    'secm_plot_calc'        : 'RG',
                                    'plot_intensity'        : 'unsub',
                                    }

        self.frame_styles = ['Full', 'XY', 'X', 'Y', 'None']

        self.default_subplot_labels = { 'total'      : ['Frame #', 'Integrated Intensity'],
                                        'mean'       : ['Frame #', 'Mean Intensity'],
                                        'q_val'      : ['Frame #', 'Intensity at q = '],
                                        'q_range'    : ['Frame #', 'Intensity from q = '],
                                        'frame'      : ['Frame #', 'Integrated Intensity'],
                                        'time'       : ['Time (s)', 'Integrated Intensity']}

        self.default_subplot_titles = {'unsub'      : 'Series Plot',
                                        'sub'       : 'Subtracted Series Plot',
                                        'baseline'  : 'Baseline Corrected Series Plot',
                                        }


        self.subplot_labels = copy.copy(self.default_subplot_labels)
        self.subplot_titles = copy.copy(self.default_subplot_titles)

        self.save_parameters ={'dpi' : 100,
                               'format' : 'png'}

        self._initFigure()

        self.toolbar = CustomSeriesPlotToolbar(self, self.canvas)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)

        # Variables for the plotted experiments:
        self.legend_names = []
        self.plotted_secms = []

        self.selected_line = None
        self.selected_line_orig_width = 1
        self._plot_shown = 1

        self.markers = itertools.cycle(('o', 'v', 's', 'p', 'h', 'D', '^', '<', '>',))

        #Timer to automatically restore line width after selection
        self.blink_timer = wx.Timer()
        self.blink_timer.Bind(wx.EVT_TIMER, self._onBlinkTimer)

        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.ryaxis)

        self._updateFrameStylesForAllPlots()

        self.canvas.callbacks.connect('pick_event', self._onPickEvent)
        self.canvas.callbacks.connect('key_press_event', self._onKeyPressEvent)
        self.canvas.callbacks.connect('motion_notify_event', self._onMouseMotionEvent)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        self.canvas.callbacks.connect('scroll_event', self._onMouseScrollEvent)

    def _initFigure(self):
        self.fig = matplotlib.figure.Figure((5,4), 75)
        self.subplot1 = self.fig.add_subplot(111)

        self.ryaxis = self.subplot1.twinx()
        if self.plotparams['secm_plot_calc'] == 'None':
            self.ryaxis.axis('off')

        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = .9, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')

        self.canvas = MyFigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')

    def setParameter(self, param, value):
        self.plotparams[param] = value

    def getParameter(self, param):
        return self.plotparams[param]


    def _updateFrameStylesForAllPlots(self):
        try:
            self.updateFrameStyle(axes = self.subplot1)
            self.updateFrameStyle(axes=self.ryaxis)
        except Exception, e:
            print 'Possibly too old matplotlib version: ' + str(e)
            pass

    def updateFrameStyle(self, axes):
        if axes == self.subplot1:
            plotnum = '1'
        else:
            plotnum = '2'

        style = self.plotparams['framestyle' + plotnum]

        self.setFrameStyle(axes, style)

    def setFrameStyle(self, axes, style):

        if axes == self.subplot1:
            if style.find('l')>-1:
                axes.spines['left'].set_color('black')
                axes.tick_params(left=True, which = 'both')
            else:
                axes.spines['left'].set_color('none')
                axes.tick_params(left=False, which = 'both')
            if style.find('r')>-1:
                axes.spines['right'].set_color('black')
                axes.tick_params(right=True, which = 'both')
            else:
                axes.spines['right'].set_color('none')
                axes.tick_params(right=False, which = 'both')
            if style.find('t')>-1:
                axes.spines['top'].set_color('black')
                axes.tick_params(top=True, which = 'both')
            else:
                axes.spines['top'].set_color('none')
                axes.tick_params(top=False, which = 'both')
            if style.find('b')>-1:
                axes.spines['bottom'].set_color('black')
                axes.tick_params(bottom=True, which = 'both')
            else:
                axes.spines['bottom'].set_color('none')
                axes.tick_params(bottom=False, which = 'both')

        elif axes == self.ryaxis:
            axes.spines['left'].set_color('none')
            axes.tick_params(left=False, which = 'both')

            axes.spines['top'].set_color('none')
            axes.tick_params(top=False, which = 'both')

            axes.spines['bottom'].set_color('none')
            axes.tick_params(bottom=False, which = 'both')

            if style.find('r')>-1:
                axes.spines['right'].set_color('black')
                axes.tick_params(right=True, which = 'both')
            else:
                axes.spines['right'].set_color('none')
                axes.tick_params(right=False, which = 'both')


    def fitAxis(self, axes = None, forced = False):

        if axes:
            plots = axes
        else:
            plots = [self.subplot1, self.ryaxis]

        maxq1 = None
        maxi1 = None

        minq1 = None
        mini1 = None

        maxq2 = None
        maxi2 = None

        minq2 = None
        mini2 = None

        for eachsubplot in plots:
            if eachsubplot.lines:

                if eachsubplot == self.subplot1:
                    plotnum = '1'
                else:
                    plotnum = '2'

                if self.plotparams['auto_fitaxes' + plotnum] == False and forced == False:
                    print 'Not fitting axes due to plot settings'
                    try:
                        self.canvas.draw()
                    except ValueError, e:
                        print 'ValueError in fitaxis() : ' + str(e)
                    return

                for each in eachsubplot.lines:
                    if each._label != '_nolegend_' and each._label != '_zero_' and each._label != '_line1' and each.get_visible() == True:

                        if plotnum == '1':
                            if maxq1 == None:
                                maxq1 = max(each.get_xdata())
                                maxi1 = max(each.get_ydata())

                                minq1 = min(each.get_xdata())
                                mini1 = min(each.get_ydata())
                        elif plotnum =='2':
                            if maxq2 == None:
                                maxq2 = max(each.get_xdata())
                                maxi2 = max(each.get_ydata())

                                minq2 = min(each.get_xdata())
                                mini2 = min(each.get_ydata())

                        xmax = max(each.get_xdata())
                        ymax = max(each.get_ydata())

                        xmin = min(each.get_xdata())
                        ymin = min(each.get_ydata())

                        if plotnum =='1':
                            if xmax > maxq1:
                                maxq1 = xmax
                            if xmin < minq1:
                                minq1 = xmin
                            if ymax > maxi1:
                                maxi1 = ymax
                            if ymin < mini1:
                                mini1 = ymin
                        elif plotnum == '2':
                            if xmax > maxq2:
                                maxq2 = xmax
                            if xmin < minq2:
                                minq2 = xmin
                            if ymax > maxi2:
                                maxi2 = ymax
                            if ymin < mini2:
                                mini2 = ymin

        if maxq1 == None:
            if maxq2 != None:
                maxq1 = maxq2
            else:
                maxq1 = 1

        elif maxq2 == None:
            if maxq1 != None:
                maxq2 = maxq1
            else:
                maxq1 = 1

        if minq1 == None:
            if minq2 != None:
                minq1 = minq2
            else:
                minq1 = 0

        elif minq2 == None:
            if minq1 != None:
                minq2 = minq1
            else:
                minq1 = 0


        if maxq1 > maxq2:
            maxq = maxq1
        else:
            maxq = maxq2
        if minq1 < minq2:
            minq = minq1
        else:
            minq = minq2


        for eachsubplot in plots:
                if eachsubplot == self.subplot1:
                    eachsubplot.set_ylim(mini1, maxi1)
                else:
                    eachsubplot.set_ylim(mini2, maxi2)
                eachsubplot.set_xlim(minq, maxq)

        try:
            self.canvas.draw()
        except ValueError, e:
            print 'ValueError in fitaxis() : ' + str(e)


    def _onBlinkTimer(self, event):

        try:
            self.selected_line.set_linewidth(self.selected_line_orig_width)
            self.canvas.draw()
        except:
            pass

        self.selected_line = None
        self.blink_timer.Stop()

    def _onPickEvent(self, event):
        mouseevent = event.mouseevent
        if mouseevent.button == 'up' or mouseevent.button == 'down':
            return


        self.manipulation_panel = wx.FindWindowByName('SECPanel')

        if self.selected_line != None:
            self.selected_line.set_linewidth(self.selected_line_orig_width)

        self.selected_line = event.artist

        try:
            self.selected_line_orig_width = self.selected_line.get_linewidth()
            self.selected_line.set_linewidth(self.selected_line_orig_width + 2)
        except AttributeError:
            self.selected_line = None
            return

        wx.CallAfter(self.manipulation_panel.deselectAllExceptOne, None, self.selected_line)
        self.canvas.draw()

        self.blink_timer.Start(500)

    def _onKeyPressEvent(self, event):
        pass


    def _onMouseScrollEvent(self, event):

        return

        x_size,y_size = self.canvas.get_width_height()
        half_y = y_size / 2

        if self._plot_shown == 1:
            selected_plot = 1
        elif self._plot_shown == 2:
            selected_plot = 2
        elif event.y <= half_y:
            selected_plot = 2
        else:
            selected_plot = 1

        if selected_plot == 1:
            ax = self.subplot1
        else:
            ax = self.subplot2

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        cur_xrange = (cur_xlim[1] - cur_xlim[0])
        cur_yrange = (cur_ylim[1] - cur_ylim[0])

        xdata = event.xdata # get event x location
        ydata = event.ydata # get event y location

        if event.button == 'up':
            # zoom in
            scale_factor = 1.15
        elif event.button == 'down':
            # zoom out
            scale_factor = 0.85
        else:
            # deal with something that should never happen
            scale_factor = 1
            print event.button

        # MOVE AXIS
        zx_pix, zy_pix = ax.transAxes.transform((0,0))
        cx_pix, cy_pix = ax.transAxes.transform((0.5,0.5))

        xy = np.array([(xdata,ydata), (xdata, ydata)])

        mx_pix, my_pix = ax.transData.transform(xy)
        mx_pix = mx_pix[0]
        my_pix = my_pix[1]


        dx = cx_pix - mx_pix
        dy = cy_pix - my_pix

        dist = np.sqrt(np.power(abs(dx),2)+np.power(abs(dy),2))

        step = 0.15
        new_dist = dist * step   #step = 0..1

        tanA = abs(dy) / abs(dx)
        A = np.arctan(tanA)

        new_dx = np.cos(A) * new_dist
        new_dy = tanA * new_dx

        zdx = zx_pix + new_dx
        zdy = zy_pix + new_dy

        inv = ax.transData.inverted()


        zxdata, zydata = inv.transform((zx_pix, zy_pix))


        zstpx, zstpy = inv.transform((zdx, zdy))


        dx_move = zstpx - zxdata
        dy_move = zstpy - zydata


        if dx >= 0:
            newxmin = cur_xlim[0] - dx_move
            newxmax = cur_xlim[1] - dx_move
        if dx < 0:
            newxmin = cur_xlim[0] + dx_move
            newxmax = cur_xlim[1] + dx_move

        try:
            newxlim = (newxmin, newxmax)
        except UnboundLocalError:
            return

        if dy >= 0:
            newymin = cur_ylim[0] - dy_move
            newymax = cur_ylim[1] - dy_move
        if dy < 0:
            newymin = cur_ylim[0] + dy_move
            newymax = cur_ylim[1] + dy_move

        newylim = (newymin, newymax)


        #ZOOM
        cur_xrange = (cur_xlim[1] - cur_xlim[0])
        cur_yrange = (cur_ylim[1] - cur_ylim[0])

        new_xrange = scale_factor * cur_xrange
        new_yrange = scale_factor * cur_yrange

        dxrange = cur_xrange - new_xrange
        dyrange = cur_yrange - new_yrange

        xmin, xmax = newxlim
        newxlim_zoom = (xmin - (dxrange/2.0), xmax + (dxrange/2.0))

        ymin,ymax = newylim
        newylim_zoom = (ymin - (dyrange/2.0), ymax + (dyrange/2.0))

        ax.set_xlim(newxlim_zoom)
        ax.set_ylim(newylim_zoom)

        self.canvas.draw() # force re-draw


    def _onMouseMotionEvent(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata

            calced = self.plotparams['secm_plot_calc']

            xaxis = self.plotparams['x_axis_display'].capitalize()

            if event.inaxes == self.ryaxis:
                trans1 = self.ryaxis.transData
                trans2 = self.subplot1.transData.inverted()
                x2, y2 = x, y
                x, y = trans2.transform(trans1.transform((x,y)))
            else:
                trans1 = self.subplot1.transData
                trans2 = self.ryaxis.transData.inverted()
                x2, y2 = trans2.transform(trans1.transform((x,y)))

            if abs(y) > 0.001 and abs(y) < 1000:
                y_val = '{}'.format(round(y, 3))
            else:
                y_val = '{:.3E}'.format(y)

            if abs(y2) > 0.001 and abs(y2) < 1000:
                y2_val = '{}'.format(round(y2, 3))
            else:
                y2_val = '{:.3E}'.format(y2)

            if calced != 'None':
                wx.FindWindowByName('MainFrame').SetStatusText('%s = %i, I = %s, %s = %s' %(xaxis, x, y_val, calced, y2_val), 1)

            else:
                wx.FindWindowByName('MainFrame').SetStatusText('%s = %i, I = %s' %(xaxis, x, y_val), 1)

    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''
        selected_plot=1

        if event.button == 3:

            if float(matplotlib.__version__[:3]) >= 1.2:
                if self.toolbar.GetToolState(self.toolbar.wx_ids['Pan']) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, selected_plot)
                    else:
                        self._showPopupMenu(selected_plot)
            else:
                if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, selected_plot)
                    else:
                        self._showPopupMenu(selected_plot)

    def plotSECM(self, secm_list, color=None, legend_label_in=None,
        line_data=None, calc_line_data=None, *args, **kwargs):

        if not isinstance(secm_list, list):
            secm_list = [secm_list]

        for secm in secm_list:
            self._validatePlotSettings(secm)

        for secm in secm_list:
            if legend_label_in == None:
                legend_label = secm.getParameter('filename')
            else:
                legend_label = legend_label_in

            ydata = self._getIntensityData(secm)
            xdata = self._getXData(secm)

            if xdata is None or ydata is None:
                return

            line = self.subplot1.plot(xdata, ydata, picker=3, label=legend_label, **kwargs)[0]
            line.set_label(legend_label)

            secm.line = line
            secm.axes = self.subplot1
            secm.canvas = self.canvas
            secm.plot_panel = self
            secm.is_plotted = True

            #######If the secm object has calculated structural parameters, plot those
            if secm.calc_has_data:
                calc_data = self._getCalcData(secm)
            else:
                calc_data = None

            if calc_data is None:
                calc_data = np.zeros_like(xdata)-1

            calc_line = self.ryaxis.plot(xdata, calc_data,
                marker=self.markers.next(), linestyle ='', picker=3,
                label=self.plotparams['secm_plot_calc'], **kwargs)[0]
            calc_line.set_label(self.plotparams['secm_plot_calc'])

            secm.calc_line = calc_line
            secm.cacl_axes = self.ryaxis
            secm.calc_is_plotted = True

            plot_calc = self.plotparams['secm_plot_calc']

            if not secm.calc_has_data  or plot_calc == 'None' or not secm.is_visible:
                secm.calc_line.set_visible(False)
                secm.calc_line.set_picker(False)
            else:
                secm.calc_line.set_visible(True)
                secm.calc_line.set_picker(True)


            if color != None:
                secm.line.set_color(color)
                secm.calc_line.set_color(color)


            #Back to the main show
            self.plotted_secms.append(secm)        # Insert the plot into plotted experiments list

            if line_data != None:
                secm.line.set_linewidth(line_data['line_width'])
                secm.line.set_linestyle(line_data['line_style'])
                secm.line.set_color(line_data['line_color'])
                secm.line.set_marker(line_data['line_marker'])
                secm.line.set_visible(line_data['line_visible'])

                try:
                    secm.line.set_markerfacecolor(line_data['line_marker_face_color'])
                    secm.line.set_markeredgecolor(line_data['line_marker_edge_color'])
                except KeyError:
                    pass #Version <1.3.0 doesn't have these keys

            if calc_line_data != None:
                secm.calc_line.set_linewidth(calc_line_data['line_width'])
                secm.calc_line.set_linestyle(calc_line_data['line_style'])
                secm.calc_line.set_color(calc_line_data['line_color'])
                secm.calc_line.set_marker(calc_line_data['line_marker'])
                secm.calc_line.set_visible(calc_line_data['line_visible'])

                try:
                    secm.calc_line.set_markerfacecolor(calc_line_data['line_marker_face_color'])
                    secm.calc_line.set_markeredgecolor(calc_line_data['line_marker_edge_color'])
                except KeyError:
                    pass #Version <1.3.0 doesn't have these key

            self.updatePlotData()


    def _showPopupMenu(self, selected_plot):

        self.selected_plot = selected_plot

        menu = wx.Menu()

        # plot1SubMenu = self._createPopupAxesMenu('1')
        plotSubMenu2 = self._createPopupYdataMenu('1')
        plotSubMenu3 = self._createPopupYdataMenu('2')
        plotSubMenu4 = self._createPopupIntensityMenu('1')
        plotSubMenu5 = self._createPopupXdataMenu('1')

        # menu.AppendSubMenu(plot1SubMenu, 'Axes')
        menu.AppendSubMenu(plotSubMenu2, 'Y Data (Left Axis)')
        menu.AppendSubMenu(plotSubMenu3, 'Y Data (Right Axis)')
        menu.AppendSubMenu(plotSubMenu4, 'Intensity Type')
        menu.AppendSubMenu(plotSubMenu5, 'X Data')

        menu.AppendSeparator()

        plot_options = menu.Append(wx.ID_ANY, 'Plot Options...')

        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

        self.Bind(wx.EVT_MENU, self._onPlotOptions, plot_options)


        self.PopupMenu(menu)

        menu.Destroy()

    def _onPlotOptions(self, evt):
        axes = self.subplot1

        dlg = RAWCustomDialogs.PlotOptionsDialog(self, self.plotparams, axes)
        dlg.ShowModal()
        dlg.Destroy()

    def _onPopupMenuChoice(self, evt):
        mainframe = wx.FindWindowByName('MainFrame')
        seccontrol = wx.FindWindowByName('SECControlPanel')
        MenuIDs = mainframe.getMenuIds()
        choice_id = evt.GetId()

        if seccontrol._is_online:
            mainframe.OnlineSECControl.goOffline()

        for key in MenuIDs.iterkeys():
            if MenuIDs[key] == choice_id:

                if key[4] == '1':

                    self.plotparams['axesscale1'] = key[7:]
                    self.plotparams['plot1type'] = 'normal'
                    self.updatePlotAxes()

                elif key.startswith('sec'):
                    if key == 'secplottotal':
                        self.plotparams['y_axis_display'] = 'total'

                    elif key == 'secplotmean':
                        self.plotparams['y_axis_display'] = 'mean'

                    elif key == 'secplotq':
                        self.plotparams['y_axis_display'] = 'q_val'
                        self._getQValue()

                    elif key == 'secplotqr':
                        self.plotparams['y_axis_display'] = 'q_range'
                        self._getQRange()

                    elif key == 'secplotframe':
                        self.plotparams['x_axis_display'] = 'frame'
                    elif key == 'secplottime':
                        self.plotparams['x_axis_display'] = 'time'

                    elif key == 'secplotrg':
                        self.plotparams['secm_plot_calc'] = 'RG'
                        raxis_on = self.plotparams['framestyle1'].find('r')
                        if raxis_on>-1:
                            self.plotparams['framestyle1'] = self.plotparams['framestyle1'].replace('r','')
                            self.plotparams['framestyle2'] = self.plotparams['framestyle2']+'r'
                            self._updateFrameStylesForAllPlots()

                    elif key == 'secplotvcmw':
                        self.plotparams['secm_plot_calc'] = 'MW (Vc)'
                        raxis_on = self.plotparams['framestyle1'].find('r')
                        if raxis_on>-1:
                            self.plotparams['framestyle1'] = self.plotparams['framestyle1'].replace('r','')
                            self.plotparams['framestyle2'] = self.plotparams['framestyle2']+'r'
                            self._updateFrameStylesForAllPlots()

                    elif key == 'secplotvpmw':
                        self.plotparams['secm_plot_calc'] = 'MW (Vp)'
                        raxis_on = self.plotparams['framestyle1'].find('r')
                        if raxis_on>-1:
                            self.plotparams['framestyle1'] = self.plotparams['framestyle1'].replace('r','')
                            self.plotparams['framestyle2'] = self.plotparams['framestyle2']+'r'
                            self._updateFrameStylesForAllPlots()

                    elif key == 'secploti0':
                        self.plotparams['secm_plot_calc'] = 'I0'
                        raxis_on = self.plotparams['framestyle1'].find('r')
                        if raxis_on>-1:
                            self.plotparams['framestyle1'] = self.plotparams['framestyle1'].replace('r','')
                            self.plotparams['framestyle2'] = self.plotparams['framestyle2']+'r'
                            self._updateFrameStylesForAllPlots()

                    elif key == 'secplotnone':
                        self.plotparams['secm_plot_calc'] = 'None'

                    elif key == 'secplotunsub':
                        self.plotparams['plot_intensity'] = 'unsub'

                    elif key == 'secplotsub':
                        self.plotparams['plot_intensity'] = 'sub'

                    elif key == 'secplotbaseline':
                        self.plotparams['plot_intensity'] = 'baseline'

                if (key == 'secplotrg' or key == 'secplotvcmw' or 
                    key == 'secplotvpmw' or key == 'secploti0'):
                    intensity_flag = False
                else:
                    intensity_flag = True

                for secm in self.plotted_secms:
                    secm.intensity_change = secm.intensity_change or intensity_flag

                #Update plot settings in menu bar:
                mainframe.setViewMenuScale(choice_id)

                self.updatePlotData()


                #evt.Skip()

        if seccontrol._is_online:
            mainframe.OnlineSECControl.goOnline()


    def _createPopupAxesMenu(self, plot_number):

        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        item_list = []

        pop_menu = wx.Menu()

        left_y_axes_list = [('lylin',    'Lin'),
                         ('lylog',    'Log')]

        right_y_axes_list = [('rylin',    'Lin'),
                         ('rylog',    'Log')]

        x_axes_list = [('xlin',    'Lin'),
                         ('xlog',    'Log')]

        submenu1 = wx.Menu()
        submenu2 = wx.Menu()
        submenu3 = wx.Menu()

        for key, label in left_y_axes_list:
            item = submenu1.AppendRadioItem(MenuIDs['secplot' + key], label)
            item_list.append(item)

        for key, label in right_y_axes_list:
            item = submenu2.AppendRadioItem(MenuIDs['secplot' + key], label)
            item_list.append(item)

        for key, label in x_axes_list:
            item = submenu3.AppendRadioItem(MenuIDs['secplot' + key], label)
            item_list.append(item)

        self._markCurrentAxesSelection(item_list, plot_number)

        pop_menu.AppendSubMenu(submenu1, 'Left Y Axis')
        pop_menu.AppendSubMenu(submenu2, 'Right Y Axis')
        pop_menu.AppendSubMenu(submenu3, 'X Axis')

        return pop_menu

    def _createPopupYdataMenu(self, plot_number):
        if plot_number == '1':
            mainframe = wx.FindWindowByName('MainFrame')
            MenuIDs = mainframe.getMenuIds()
            item_list = []
            pop_menu = wx.Menu()

            axes_list = [('secplottotal',    'Integrated Intensity'),
                             ('secplotmean',    'Mean Intensity'),
                             ('secplotq',   'Intensity at specific q'),
                             ('secplotqr',  'Intensity in q range')
                             ]

            for key, label in axes_list:
                item = pop_menu.AppendRadioItem(MenuIDs[key], label)
                item_list.append(item)

            self._markCurrentYSelection(item_list, plot_number)

        elif plot_number == '2':
            mainframe = wx.FindWindowByName('MainFrame')
            MenuIDs = mainframe.getMenuIds()
            item_list = []
            pop_menu = wx.Menu()

            axes_list = [('secplotrg',    'RG'),
                             ('secplotvcmw',    'MW (Vc)'),
                             ('secplotvpmw',    'MW (Vp)'),
                             ('secploti0',   'I0'),
                             ('secplotnone', 'None'),
                             ]

            for key, label in axes_list:
                item = pop_menu.AppendRadioItem(MenuIDs[key], label)
                item_list.append(item)

            self._markCurrentYSelection(item_list, plot_number)

        return pop_menu

    def _createPopupXdataMenu(self, plot_number):

        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        item_list = []
        pop_menu = wx.Menu()

        axes_list = [('secplotframe',    'Frame Number'),
                         ('secplottime',    'Time'),
                         ]

        for key, label in axes_list:
            item = pop_menu.AppendRadioItem(MenuIDs[key], label)
            item_list.append(item)

        self._markCurrentXSelection(item_list, plot_number)

        return pop_menu

    def _createPopupIntensityMenu(self, plot_number):

        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        item_list = []
        pop_menu = wx.Menu()

        axes_list = [('secplotunsub',       'Unsubtracted'),
                        ('secplotsub',      'Subtracted'),
                        ('secplotbaseline', 'Baseline Corrected'),
                        ]

        for key, label in axes_list:
            item = pop_menu.AppendRadioItem(MenuIDs[key], label)
            item_list.append(item)

        if self.plotparams['plot_intensity'] == 'unsub':
            item_list[0].Check(True)
        elif self.plotparams['plot_intensity'] == 'sub':
            item_list[1].Check(True)
        elif self.plotparams['plot_intensity'] == 'baseline':
            item_list[2].Check(True)

        return pop_menu


    def _markCurrentAxesSelection(self, item_list, plot_number):
        ''' Set the current axes selection on the newly created
           popup menu '''

        if self.plotparams['plot' + plot_number + 'type'] == 'normal' or self.plotparams['plot' + plot_number + 'type'] == 'subtracted':

            if self.plotparams['axesscale1'] == 'loglog':
                item_list[1].Check(True)
                item_list[5].Check(True)
            elif self.plotparams['axesscale1'] == 'linlog':
                item_list[0].Check(True)
                item_list[5].Check(True)
            elif self.plotparams['axesscale1'] == 'loglin':
                item_list[1].Check(True)
                item_list[4].Check(True)
            elif self.plotparams['axesscale1'] == 'linlin':
                item_list[0].Check(True)
                item_list[4].Check(True)

            if self.plotparams['axesscale2'] == 'loglog':
                item_list[3].Check(True)
            elif self.plotparams['axesscale2'] == 'linlog':
                item_list[3].Check(True)
            elif self.plotparams['axesscale2'] == 'loglin':
                item_list[2].Check(True)
            elif self.plotparams['axesscale2'] == 'linlin':
                item_list[2].Check(True)

        else:
            if self.plotparams['plot' + plot_number + 'type'] == 'guinier':
                item_list[4].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'kratky':
                item_list[5].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'porod':
                item_list[6].Check(True)


    def _markCurrentYSelection(self, item_list, plot_number):
        ''' Set the current axes selection on the newly created
           popup menu '''
        if plot_number == '1':
            if self.plotparams['y_axis_display'] == 'total':
                item_list[0].Check(True)
            elif self.plotparams['y_axis_display'] == 'mean':
                item_list[1].Check(True)
            elif self.plotparams['y_axis_display'] == 'q_val':
                item_list[2].Check(True)
            elif self.plotparams['y_axis_display'] == 'q_range':
                item_list[3].Check(True)

        elif plot_number == '2':
            if self.plotparams['secm_plot_calc'] == 'RG':
                item_list[0].Check(True)
            elif self.plotparams['secm_plot_calc'] == 'MW (Vc)':
                item_list[1].Check(True)
            elif self.plotparams['secm_plot_calc'] == 'MW (Vp)':
                item_list[2].Check(True)
            elif self.plotparams['secm_plot_calc'] == 'I0':
                item_list[3].Check(True)
            elif self.plotparams['secm_plot_calc'] == 'None':
                item_list[4].Check(True)

    def _markCurrentXSelection(self, item_list, plot_number):
        ''' Set the current axes selection on the newly created
           popup menu '''

        if self.plotparams['x_axis_display'] == 'frame':
            item_list[0].Check(True)
        elif self.plotparams['x_axis_display'] == 'time':
            item_list[1].Check(True)

    def _validatePlotSettings(self, secm):
        mainframe = wx.FindWindowByName('MainFrame')
        menu_ids = mainframe.getMenuIds()

        if self.plotparams['y_axis_display'] == 'q_val':
            q=float(self.plotparams['secm_plot_q'])
            sasm = secm.getSASM()
            qrange = sasm.getQrange()
            qmin = sasm.q[qrange[0]]
            qmax = sasm.q[qrange[-1]-1]

            if q > qmax or q < qmin:
                wx.MessageBox("Specified q value outside of q range! Reverting to total intensity.", style=wx.ICON_ERROR | wx.OK)
                self.plotparams['y_axis_display'] = 'total'
                mainframe.setViewMenuScale(menu_ids['secplottotal'])

        elif self.plotparams['y_axis_display'] == 'q_range':
            qrange = self.plotparams['secm_plot_qrange']
            sasm = secm.getSASM()
            q = sasm.getQ()
            qmin = q[0]
            qmax = q[-1]

            if qrange[1] > qmax or qrange[0] < qmin:
                wx.MessageBox("Specified q value outside of q range! Reverting to total intensity.", style=wx.ICON_ERROR | wx.OK)
                self.plotparams['y_axis_display'] = 'total'
                mainframe.setViewMenuScale(menu_ids['secplottotal'])


        if self.plotparams['x_axis_display'] == 'time':
            time= secm.getTime()

            ydata = secm.line.get_ydata()

            if len(time) == 0:
                wx.CallAfter(wx.MessageBox, "Time data not available for this data set. Reverting to frame number.", style=wx.ICON_ERROR | wx.OK)
                self.plotparams['x_axis_display'] = 'frame'
                mainframe.setViewMenuScale(menu_ids['secplotframe'])
            elif time[0] == -1:
                wx.CallAfter(wx.MessageBox, "Time data not available for this data set. Reverting to frame number.", style=wx.ICON_ERROR | wx.OK)
                self.plotparams['x_axis_display'] = 'frame'
                mainframe.setViewMenuScale(menu_ids['secplotframe'])
            elif len(time) != len(ydata):
                wx.CallAfter(wx.MessageBox, "Time data not available for every frame in this data set. Reverting to frame number.", style=wx.ICON_ERROR | wx.OK)
                self.plotparams['x_axis_display'] = 'frame'
                mainframe.setViewMenuScale(menu_ids['secplotframe'])

        if self.plotparams['plot_intensity'] == 'sub':
            if not secm.subtracted_sasm_list:
                msg = ('Not all Series items have subtracted intensity '
                    'profiles. Reverting to unsubtracted intensity.')
                wx.CallAfter(wx.MessageBox, msg, style=wx.ICON_ERROR|wx.OK)
                self.plotparams['plot_intensity'] = 'unsub'
                mainframe.setViewMenuScale(menu_ids['secplotunsub'])

        if self.plotparams['plot_intensity'] == 'baseline':
            if not secm.baseline_subtracted_sasm_list:
                msg = ('Not all Series items have baseline corrected intensity '
                    'profiles. Reverting to unsubtracted intensity.')
                wx.CallAfter(wx.MessageBox, msg, style=wx.ICON_ERROR|wx.OK)
                self.plotparams['plot_intensity'] = 'unsub'
                mainframe.setViewMenuScale(menu_ids['secplotunsub'])

    def _getIntensityData(self, secm):
        if self.plotparams['y_axis_display'] == 'total':
            if self.plotparams['plot_intensity'] == 'unsub':
                intensity = secm.total_i
            elif self.plotparams['plot_intensity'] == 'sub':
                intensity = secm.total_i_sub
            elif self.plotparams['plot_intensity'] == 'baseline':
                intensity = secm.total_i_bcsub

        elif self.plotparams['y_axis_display'] == 'mean':
            if self.plotparams['plot_intensity'] == 'unsub':
                intensity = secm.mean_i
            elif self.plotparams['plot_intensity'] == 'sub':
                intensity = secm.mean_i_sub
            elif self.plotparams['plot_intensity'] == 'baseline':
                intensity = secm.mean_i_bcsub

        elif self.plotparams['y_axis_display'] == 'q_val':
            q = float(self.plotparams['secm_plot_q'])
            if secm.qref != q:
                secm.I(q)

            if self.plotparams['plot_intensity'] == 'unsub':
                intensity = secm.I_of_q
            elif self.plotparams['plot_intensity'] == 'sub':
                intensity = secm.I_of_q_sub
            elif self.plotparams['plot_intensity'] == 'baseline':
                intensity = secm.I_of_q_bcsub

        elif self.plotparams['y_axis_display'] == 'q_range':
            qrange = self.plotparams['secm_plot_qrange']
            if secm.qrange != qrange:
                secm.calc_qrange_I(qrange)

            if self.plotparams['plot_intensity'] == 'unsub':
                intensity = secm.qrange_I
            elif self.plotparams['plot_intensity'] == 'sub':
                intensity = secm.qrange_I_sub
            elif self.plotparams['plot_intensity'] == 'baseline':
                intensity = secm.qrange_I_bcsub

        else:
            intensity = None #Should never happen

        return intensity

    def _getCalcData(self, secm):
        if self.plotparams['secm_plot_calc'] =='RG':
            calc_data, err = secm.getRg()

        elif self.plotparams['secm_plot_calc'] == 'MW (Vc)':
            calc_data, err =  secm.getVcMW()

        elif self.plotparams['secm_plot_calc'] == 'MW (Vp)':
            calc_data, err =  secm.getVpMW()

        elif self.plotparams['secm_plot_calc'] == 'I0':
            calc_data, err =  secm.getI0()

        else:
            calc_data = None

        return calc_data

    def _getXData(self, secm):
        if self.plotparams['x_axis_display'] == 'frame':
           xdata = secm.plot_frame_list
        elif self.plotparams['x_axis_display'] == 'time':
            xdata = secm.getTime()
        else:
            xdata = None

        return xdata

    def updatePlotData(self, secm_list=[], draw=True):
        if not secm_list:
            secm_list = self.plotted_secms

        for each in secm_list:
            self._validatePlotSettings(each)

        for each in secm_list:
            each.acquireSemaphore()

            intensity = self._getIntensityData(each)

            each.line.set_ydata(intensity)

            if each.calc_has_data:

                calc_data = self._getCalcData(each)

                each.calc_line.set_ydata(calc_data)

                if (each.calc_line.get_label() == 'RG' or
                    each.calc_line.get_label() == 'MW (Vc)' or
                    each.calc_line.get_label() == 'MW (Vp)' or
                    each.calc_line.get_label() == 'I0'):
                    each.calc_line.set_label(self.plotparams['secm_plot_calc'])

            xdata = self._getXData(each)

            each.line.set_xdata(xdata)
            if each.calc_is_plotted:
                each.calc_line.set_xdata(xdata)

            if each.calc_has_data and each.is_visible:
                if self.plotparams['secm_plot_calc'] == 'None':
                    each.calc_line.set_visible(False)
                    each.calc_line.set_picker(False)
                else:
                    each.calc_line.set_visible(True)
                    each.calc_line.set_picker(True)
            each.releaseSemaphore()

        if self.plotparams['secm_plot_calc'] == 'None':
            self.ryaxis.axis('off')
        else:
            self.ryaxis.axis('on')

        if self.plotparams['legend_visible1'] == True:
            self.updateLegend(1, draw=False)

        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.ryaxis)

        if draw:
            self.fitAxis()

    def updatePlotAxes(self):

        axes = [self.subplot1, self.ryaxis]

        for a in axes:
            if a == self.subplot1:
                c = 1
            else:
                c = 2

            if self.plotparams.get('axesscale' + str(c)) == 'linlin':
                a.set_xscale('linear')
                a.set_yscale('linear')

            if self.plotparams.get('axesscale'+ str(c)) == 'loglin':
                a.set_xscale('linear')

                a.set_ylim(1, 99999)
                a.set_yscale('log')
                a.set_ylim(1, 99999)
                #a.limit_range_for_scale(1, 99999)

            if self.plotparams.get('axesscale'+ str(c)) == 'loglog':
                a.set_xscale('log')
                a.set_ylim(1, 99999)
                a.set_yscale('log')
                a.set_ylim(1, 99999)


            if self.plotparams.get('axesscale'+ str(c)) == 'linlog':
                a.set_xscale('log')
                a.set_yscale('linear')


        self.fitAxis()

    def clearAllPlots(self):

        self.subplot_labels = copy.copy(self.default_subplot_labels)
        self.subplot_titles = copy.copy(self.default_subplot_titles)

        self.subplot1.cla()
        self._setLabels(axes = self.subplot1)
        self.ryaxis.cla()
        self._setLabels(axes=self.ryaxis)

        self.plotted_secms = []

        self._updateFrameStylesForAllPlots()

        is_zline1 = self.plotparams['zero_line1']

        if is_zline1:
            axes = self.subplot1
            zero = axes.axhline(color='k')
            zero.set_label('_zero_')

        self.updatePlotAxes()

    def _getQValue(self):
        dlg = wx.TextEntryDialog(self,message = 'Enter q value at which to plot I(q) vs. frame', caption = 'Pick q Value')
        dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()

        try:
            float(result)
            self.plotparams['secm_plot_q'] = result
        except:
            wx.MessageBox("Specified q value is not a number! Reverting to total intensity.", style=wx.ICON_ERROR | wx.OK)
            self.plotparams['y_axis_display'] = 'total'

    def _getQRange(self):
        msg = 'Enter q range at which to plot I(q) vs. frame as q1, q2 (e.g. 0.1, 0.25).'
        dlg = wx.TextEntryDialog(self, message=msg, caption = 'Pick q Value')
        dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()

        try:
            q1, q2 = result.split(',')
            q1 = float(q1)
            q2 = float(q2)
            self.plotparams['secm_plot_qrange'] = (q1, q2)
        except:
            wx.MessageBox("Specified q value is not a number! Reverting to total intensity.", style=wx.ICON_ERROR | wx.OK)
            self.plotparams['y_axis_display'] = 'total'

    def _setLabels(self, sasm = None, title = None, xlabel = None, ylabel = None, axes = None):
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes

        # Set labels
        if title == None:
            if a ==self.subplot1:
                plottype = self.plotparams['y_axis_display']
                plot_intensity = self.plotparams['plot_intensity']

                a.title.set_text(self.subplot_titles[plot_intensity])
                a.title.set_size(self.plotparams['title_fontsize1'])
                a.title.set_fontname(self.plotparams['title_font1'])

                if plottype == 'total' or plottype == 'mean':
                    a.yaxis.get_label().set_text(self.subplot_labels[plottype][1])
                elif plottype == 'q_val':
                    a.yaxis.get_label().set_text(self.subplot_labels[plottype][1]+self.plotparams['secm_plot_q'])
                elif plottype == 'q_range':
                    qrange = self.plotparams['secm_plot_qrange']
                    a.yaxis.get_label().set_text(self.subplot_labels[plottype][1]+'{} to {}'.format(qrange[0], qrange[1]))
                else:
                    a.yaxis.get_label().set_text(self.subplot_labels('Y'))

                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize1'])
                a.yaxis.get_label().set_fontname(self.plotparams['ylabel_font1'])


                xaxistype = self.plotparams['x_axis_display']

                if xaxistype == 'frame' or xaxistype == 'time':
                    a.xaxis.get_label().set_text(self.subplot_labels[xaxistype][0])
                else:
                    a.xaxis.get_label().set_text('X')

                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize1'])
                a.xaxis.get_label().set_fontname(self.plotparams['xlabel_font1'])

            if a == self.ryaxis:
                calctype = self.plotparams['secm_plot_calc']
                if calctype == 'RG':
                    a.set_ylabel('Rg')
                elif calctype == 'MW (Vc)':
                    a.set_ylabel('Molecular Weight, Vc (kDa)')
                elif calctype == 'MW (Vp)':
                    a.set_ylabel('Molecular Weight, Vp (kDa)')
                elif calctype == 'I0':
                    a.set_ylabel('I0')

                a.yaxis.get_label().set_size(self.plotparams['y2label_fontsize1'])
                a.yaxis.get_label().set_fontname(self.plotparams['y2label_font1'])


        else:
            a.title.set_text(title)
            a.title.set_fontname(self.plotparams['title_font1'])
            a.title.set_size(self.plotparams['title_fontsize1'])

    def updateLegend(self, plotnum, draw=True):
        #Takes the plotnum argument for historical reasons: i.e. I'm too
        #lazy to change the inputs everywhere
        self._insertLegend(draw)

    def _insertLegend(self, draw=True):
        ####################################################################
        # NB!! LEGEND IS THE BIG SPEED HOG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ###################################################################
        a = self.subplot1

        if self.plotparams['legend_showcalc1']:
            axes_list = [self.subplot1, self.ryaxis]
        else:
            axes_list = [self.subplot1]

        legend_lines = []
        legend_labels = []

        for axes in axes_list:
            for each_line in axes.lines:
                if each_line.get_visible() == True and each_line.get_label() != '_zero_' and each_line.get_label() != '_nolegend_' and each_line.get_label() != '_line1':
                    legend_lines.append(each_line)
                    legend_labels.append(each_line.get_label())

        old_legend = a.get_legend()

        if  old_legend is not None:
            self.plotparams['legend_pos1'] = old_legend._loc

            old_title = old_legend.get_title()
            old_title_text = old_title.get_text()
            old_title_weight = old_title.get_weight()
            old_title_style = old_title.get_style()

            a.legend_ = None

        if not legend_lines:
            return
        else:
            fontsize = self.plotparams['legend_fontsize1']
            fontname = self.plotparams['legend_font1']
            enable_border = self.plotparams['legend_border1']
            alpha = self.plotparams['legend_alpha1']
            leg_visible = self.plotparams['legend_visible1']
            shadow = self.plotparams['legend_shadow1']

            legtit_size = self.plotparams['legtit_fontsize1']
            legtit_font = self.plotparams['legtit_font1']

            leg = a.legend(legend_lines, legend_labels, prop = fm.FontProperties(size = fontsize, family = fontname), fancybox = True)
            leg.get_frame().set_alpha(alpha)
            leg.shadow = shadow

            #Set up the title correctly
            if old_legend is not None:
                title = leg.get_title()
                title.set_style(old_title_style)
                title.set_weight(old_title_weight)
                title.set_fontname(legtit_font)
                title.set_size(legtit_size)
                title.set_text(old_title_text)

                leg.set_title(title.get_text())

            else:
                leg.set_title('')

                title = leg.get_title()
                title.set_fontname(legtit_font)
                title.set_size(legtit_size)

            if leg_visible:
                leg.set_visible(True)
            else:
                leg.set_visible(False)

            if not enable_border:
                leg.get_frame().set_linewidth(0)
            else:
                leg.get_frame().set_linewidth(1)

            try:
                leg.draggable()   #Interferes with the scroll zoom!
                if self.plotparams['legend_pos1'] is not None:
                    leg._loc = self.plotparams['legend_pos1']
            except AttributeError:
                print "WARNING: Old matplotlib version, legend not draggable"

        if draw:
            self.canvas.draw()

    def _setColor(self, rgbtuple):
        """Set figure and canvas colours to be the same"""
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()

        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))
