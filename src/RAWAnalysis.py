'''
Created on Mar 23, 2010

@author: specuser
'''
import matplotlib
#matplotlib.use('WXAgg')
matplotlib.rc('image', origin = 'lower')        # turn image upside down.. x,y, starting from lower left

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg#,Toolbar, FigureCanvasWx
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.patches import Circle, Rectangle, Polygon
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor#, Slider, Button
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, Rectangle, Polygon
import numpy as np
import wx, math
import sys, os
from scipy import linspace, polyval, polyfit, sqrt, randn
import RAW, RAWSettings, RAWCustomCtrl

class GuinierPlotPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, wxEmbedded = False):
        
        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
        
        main_frame = wx.FindWindowByName('MainFrame')
        
        try:
            self.raw_settings = main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()
        
        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
                    
        self.data_line = None
    
        subplotLabels = [('Guinier', 'q^2', 'ln(I(q)', .1), ('Error', 'q', 'I(q)', 0.1)]
        
        self.fig.subplots_adjust(hspace = 0.26)
        
        self.subplots = {}
        
        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot 
      
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)
        self.canvas.SetBackgroundColour('white')
        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')
        
        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw) 

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''
        
        a = self.subplots['Guinier']
        b = self.subplots['Error']

        self.background = self.canvas.copy_from_bbox(a.bbox)
        self.err_background = self.canvas.copy_from_bbox(b.bbox)
        
        self.updateDataPlot(self.orig_i, self.orig_q, self.xlim)
        
    def _calcFit(self):
        ''' calculate fit and statistics '''
 
        q_roi = self.q
        i_roi = self.i
        
        x = np.power(q_roi, 2)
        y = np.log(i_roi)
        
        #Remove NaN and Inf values:
        x = x[np.where(np.isnan(y) == False)]
        y = y[np.where(np.isnan(y) == False)]
        x = x[np.where(np.isinf(y) == False)]
        y = y[np.where(np.isinf(y) == False)]
        
        #Get 1.st order fit:
        ar, br = polyfit(x, y, 1)
        
        #Obtain fit values:
        y_fit = polyval([ar, br], x)
        
        #Get fit statistics:
        error = y - y_fit
        SS_tot = np.sum(np.power(y-np.mean(y),2))
        SS_err = np.sum(np.power(error, 2))
        rsq = 1 - SS_err / SS_tot
        
        I0 = br
        Rg = np.sqrt(-3*ar)
                
        if np.isnan(Rg):
            Rg = 0  
        
        ######## CALCULATE ERROR ON PARAMETERS ###############
        
        N = len(error)
        stde = SS_err / (N-2)
        std_slope = stde * np.sqrt( (1/N) +  (np.power(np.mean(x),2)/np.sum(np.power(x-np.mean(x),2))))
        std_interc = stde * np.sqrt(  1 / np.sum(np.power(x-np.mean(x),2)))
        
        ######################################################
        
        if np.isnan(std_slope):
            std_slope = -1
        if np.isnan(std_interc):
            std_interc = -1
        
        newInfo = {'I0' : (np.exp(I0), std_interc),
                   'Rg' : (Rg, std_slope),
                   'qRg_max': Rg * np.sqrt(x[-1]),
                   'qRg_min' : Rg * np.sqrt(x[0]),
                   'rsq': rsq}
        
        
        mw = self.raw_settings.get('MWStandardMW') 
        mwI0 = self.raw_settings.get('MWStandardI0')
        mwConc = self.raw_settings.get('MWStandardConc')
        
        conc = wx.FindWindowByName('GuinierControlPanel').getConcentration()
        
        if mw != 0 and mw > 0 and mwI0 !=0 and mwI0 > 0 and conc != 0 and conc > 0 and mwConc > 0:
            newInfo['MM'] = (newInfo['I0'][0] * (mw/(mwI0/mwConc))) / conc
                        
        
        return x, y_fit, br, error, newInfo
        
    def plotExpObj(self, ExpObj):
        xlim = [0, len(ExpObj.i)]
        
        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(ExpObj.i, ExpObj.q, xlim)
        
        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, i, q, xlim):
            
        xmin, xmax = xlim
        
        #Save for resizing:
        self.orig_i = i
        self.orig_q = q
        self.xlim = xlim
        
        #Cut out region of interest
        self.i = i[xmin:xmax]
        self.q = q[xmin:xmax]
        
        ## Plot the (at most) 3 first and last points after fit:
        if xmin < 3:
            min_offset = xmin
        else:
            min_offset = 3
        
        if xmax > len(q)-3:
            max_offset = len(q) - xmax
        else:
            max_offset = 3

        xmin = xmin - min_offset
        xmax = xmax + max_offset
        
        #data containing the 3 first and last points
        q_offset = q[xmin:xmax]
        i_offset = i[xmin:xmax]
            
        x = np.power(q_offset, 2)
        y = np.log(i_offset)
         
        x = x[np.where(np.isnan(y)==False)]
        y = y[np.where(np.isnan(y)==False)]
        x = x[np.where(np.isinf(y)==False)]
        y = y[np.where(np.isinf(y)==False)]
            
        a = self.subplots['Guinier']
        b = self.subplots['Error']
        
        try:
            x_fit, y_fit, I0, error, newInfo = self._calcFit()
        except TypeError:
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
            
            #self.lim_back_line, = a.plot([x_lim_back, x_lim_back], [y_lim_back-0.2, y_lim_back+0.2], transform=a.transAxes, animated = True)
            
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)
            self.err_background = self.canvas.copy_from_bbox(b.bbox)
        else:
            self.canvas.restore_region(self.background)
            
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
        
        a.relim()
        a.autoscale_view()
        
        a.draw_artist(self.data_line)
        a.draw_artist(self.fit_line)
        a.draw_artist(self.interp_line)
        a.draw_artist(self.lim_front_line)
        a.draw_artist(self.lim_back_line)

        b.set_xlim((x_fit[0], x_fit[-1]))
        b.set_ylim((error.min(), error.max()))
  
        #restore white background in error plot and draw new error:
        self.canvas.restore_region(self.err_background)
        b.draw_artist(self.error_line)
        b.draw_artist(self.zero_line)

        self.canvas.blit(a.bbox)
        self.canvas.blit(b.bbox)
        
           
#class GuinierPlotPanel(wx.Panel):
#    
#    def __init__(self, parent, panel_id, name, wxEmbedded = False):
#        
#        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
#        
#        self.i = None
#        self.q = None
#        
#        self.fig = Figure((5,4), 75)
#        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
#                
#        self.canvas.mpl_connect('motion_notify_event', self.onMotionEvent)
##        self.canvas.mpl_connect('button_press_event', self.onMouseButtonPressEvent)
#        self.canvas.mpl_connect('button_release_event', self.onMouseReleaseEvent)
#        self.canvas.mpl_connect('pick_event', self.onPick)
##        self.canvas.mpl_connect('key_press_event', self.onKeyPressEvent)
#        
#        #self.toolbar = MaskingPanelToolbar(self, self.canvas)
#        subplotLabels = [('Guinier', 'q^2', 'ln(I(q)'), ('Error', 'q', 'I(q)')]
#        
#        self.fig.subplots_adjust(hspace = 0.26)
#        
#        self.subplots = {}
#        
#        for i in range(0, len(subplotLabels)):
#            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
#            subplot.set_xlabel(subplotLabels[i][1])
#            subplot.set_ylabel(subplotLabels[i][2])
#            self.subplots[subplotLabels[i][0]] = subplot 
#        
#        sizer = wx.BoxSizer(wx.VERTICAL)
#        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
#        
#        self.toolbar = NavigationToolbar2Wx(self.canvas)
#        self.toolbar.Realize()
#        sizer.Add(self.toolbar, 0, wx.GROW)
#
#        self.SetSizer(sizer)
#        self.Fit()
#        
#        self.ltop = None
#        self.lbottom = None
#        self.pickedArtist = None
#        
#        self.lfitbottom = None
#        self.lfittop = None
#        self.limits = None
#        
#        #Figure Limits
#        self.bottomlimit = None
#        self.toplimit = None
#        
#        #self.figlim = None
#        
#        #Interpolation to I(0) line and linear fitting line
#        self.interpline = None
#        self.fitline = None
#        
#        self.SetColor()
#
#    def onMotionEvent(self, evt):
#        
#        if self.pickedArtist:
#            a = evt.xdata
#            
#            if a != None:
#                findClosest=lambda a,l:min(l,key=lambda x:abs(x-a))
#            
#                lx = np.power(self.q,2)
#                ly = self.i
#            
#                closest = findClosest(a,lx)
#            
#                idx = np.where(lx == closest)
#            
#                idx = idx[0][0]
#            
#                controlPanel = wx.FindWindowByName('GuinierControlPanel')
#            
#                if self.pickedArtist.get_label() == 'top':
#                    controlPanel.updateLimits(top = idx)
#                    self.drawTopLimit(lx[idx], ly[idx])
#                    self.drawBottomLimit(lx[self.bottomlimit], ly[self.bottomlimit])
#                    self.toplimit = idx
#                    self.updateFigureLimits()
#            
#                elif self.pickedArtist.get_label() == 'bottom': 
#                    self.drawBottomLimit(lx[idx], ly[idx])
#                    self.drawTopLimit(lx[self.toplimit], ly[self.toplimit])
#                    controlPanel.updateLimits(bottom = idx)
#                    self.bottomlimit = idx
#                    self.updateFigureLimits()
#        
#
#    def onMouseReleaseEvent(self, evt):
#                
#        if self.pickedArtist:
#            self.pickedArtist = None
#            controlPanel = wx.FindWindowByName('GuinierControlPanel')
#            self.setLimits(controlPanel.getLimits())
#            
#            a = self.subplots['Guinier']
#            
#           
#            lims = a.get_xlim()
#            #self.updateGuinierPlot()
#            #if self.fitline:
#            #    self.fitline.remove()
#            
#            self.drawFit()
#            a.set_xlim(lims)
#
#    def onPick(self, evt):
#        
#        self.pickedArtist = evt.artist
#        
#        self.canvas.draw()
#        
#    def updateFigureLimits(self):
#    
#        a = self.subplots['Guinier']
#            
#        x = np.power(self.q,2)
#        y = np.log(self.i)
#        
#        dist = len(self.q[0:self.toplimit])
#        dist2 = len(self.q[self.bottomlimit:])-1
#        
#        if dist > 5:
#            toplim = self.toplimit-5
#        else:
#            toplim = self.toplimit-dist
#            
#        if dist2 > 5:
#            botlim = self.bottomlimit+5
#        else:
#            botlim = self.bottomlimit+dist2
#             
#        #self.figlim = (x[toplim], x[botlim])
#        
#        self.toplimit = toplim
#        self.bottomlimit = botlim
#        
#        a.set_xlim((0, x[botlim]))
#            
#        oldylim = a.get_ylim()
#
#        if not np.isnan(y[botlim]) and not np.isinf(y[botlim]):
#            a.set_ylim((y[botlim], oldylim[1]))
# 
#        self.canvas.draw()
#               
#    def _plotGuinier(self, i, q):
#        
#        self.i = i
#        self.q = q
#        
#        controlPanel = wx.FindWindowByName('GuinierControlPanel')
#        
#        self.setLimits(controlPanel.getLimits())
#        
#        x = np.power(self.q,2)
#        y = np.log(self.i)
#        
#        x = x[np.where(np.isnan(y)==False)]
#        y = y[np.where(np.isnan(y)==False)]
#        
#        x = x[np.where(np.isinf(y)==False)]
#        y = y[np.where(np.isinf(y)==False)]
#        
#        self.maxmin = (min(y), max(y))
#        
#        self.subplots['Guinier'].plot(x, y, 'b.')
#        
#        self.canvas.draw()
#        
#    def updateGuinierPlot(self):
#        
#        tlim = self.limits[0]
#        blim = self.limits[1]
#        
#        if self.interpline:
#            self.interpline.remove()
#            
#        #self.subplots['Guinier'].plot(guinier_q[tlim:blim], np.log(i)[tlim:blim], '.')
#        self.drawFit()
##        self.updateFigureLimits()
#        self.canvas.draw()
#             
#    def plotExpObj(self, ExpObj):        
#        self._plotGuinier(ExpObj.i, ExpObj.q)
#        
#        #self._plotData(ExpObj.i, ExpObj.q)
#        
#        controlPanel = wx.FindWindowByName('GuinierControlPanel')
#        self.limits = controlPanel.getLimits()
#                
#        self.toplimit = 0
#        self.bottomlimit = len(ExpObj.q)-1
#        
#        #self.drawFit()
#        #self.drawLimits()
#    
#    def drawLimits(self, x,y):
#        
#        self.drawTopLimit(x,y)
#        self.drawBottomLimit(x, y)
#    
#    def drawTopLimit(self, x, y):
#        
#        a = self.subplots['Guinier']
#        
#        if self.ltop:
#            self.ltop.remove()
#
#        y = np.log(y)
#        
#        if np.isnan(y) or np.isinf(y):
#            y = 0
#        
#        x,y = a.transLimits.transform((x,y))
#                
#        self.ltop = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
#                                             color = 'r', picker = 6, alpha = 1, label = 'top', linestyle = '--')
#
#        a.add_artist(self.ltop)
#        self.canvas.draw()
#
#    def drawBottomLimit(self, x, y): 
#        
#        a = self.subplots['Guinier']
#        
#        if self.lbottom:
#            self.lbottom.remove()
#                      
#        y = np.log(y)
#        
#        if np.isnan(y) or np.isinf(y):
#            y = 0
#         
#        x,y = a.transLimits.transform((x,y))
#
#        self.lbottom = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
#                                                color = 'r', picker = 6, alpha = 1, label = 'bottom', linestyle = '--')
#        
#        a.add_artist(self.lbottom)
#        self.canvas.draw()
#        
#    def drawFitLimits(self, xall, yall):
#        
#        a = self.subplots['Guinier']
#        
#        if self.lfitbottom:
#            self.lfitbottom.remove()
#            self.lfittop.remove()
#
#        x,y = a.transLimits.transform((xall[1],yall[1]))
#
#        self.lfitbottom = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
#                                                color = 'r', picker = 6, alpha = 1, label = 'bottom')
#        
#        x,y = a.transLimits.transform((xall[0],yall[0]))
#
#        self.lfittop = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
#                                                color = 'r', picker = 6, alpha = 1, label = 'top')
#        
#        a.add_artist(self.lfitbottom)
#        a.add_artist(self.lfittop)
#        
#        self.canvas.draw()
#    
#    def drawError(self, x, error):
#                
#        a = self.subplots['Error']
#        
#        for each in a.get_lines():
#            each.remove()
#        
#        a.plot(x, error, 'b')
#        
#        zeroline = np.zeros((1,len(x)))
#    
#        a.plot(x, zeroline[0], 'r')
#        
#        a.set_xlim((x[0], x[-1]))
#        a.set_ylim((error.min(), error.max()))
#    
#    def drawFit(self):
#    
#        #fitfunc = lambda p, x: p[0] + p[1] * x
#        #errfunc = lambda p, x, y, err: (y - fitfunc(p, x)) / err
#        
#        #pinit = [1.0, -1.0]
#        #out = optimize.leastsq(errfunc, pinit, args=(logx, logy, logyerr), full_output=1)
#
#        tlim = self.limits[0]
#        blim = self.limits[1]
#
#        #x = self.subplots['Guinier'].get_lines()[0].get_xdata()
#        #y = self.subplots['Guinier'].get_lines()[0].get_ydata()
#        
#        x = np.power(self.q[tlim:blim+1],2)
#        y = np.log(self.i[tlim:blim+1])
#        
#        x = x[np.where(np.isnan(y)==False)]
#        y = y[np.where(np.isnan(y)==False)]
#        
#        x = x[np.where(np.isinf(y)==False)]
#        y = y[np.where(np.isinf(y)==False)]
#               
#        (ar,br) = polyfit(x,y, 1)
#
#        yr = polyval([ar , br], x)
#        
#        error = y-yr
#        
#        SS_tot = np.sum(np.power(y-np.mean(y),2))
#        SS_err = np.sum(np.power(error,2))
#        rsq = 1 - SS_err / SS_tot
#         
#        a = self.subplots['Guinier']
#        
#        #################### CALC Rg #########################
#        
#        self.I0 = br
#        self.Rg = np.sqrt(-3*ar)
#        if np.isnan(self.Rg):
#            self.Rg = 0
#        
#        ######## CALCULATE ERROR ON PARAMETERS ###############
#        
#        N = len(error)
#        stde = SS_err / (N-2)
#        std_slope = stde * np.sqrt( (1/N) +  (np.power(np.mean(x),2)/np.sum(np.power(x-np.mean(x),2))))
#        std_interc = stde * np.sqrt(  1 / np.sum(np.power(x-np.mean(x),2)))
#        
#        ######################################################
#        
#        if np.isnan(std_slope):
#            std_slope = -1
#        if np.isnan(std_interc):
#            std_interc = -1
#        
#        newInfo = {'I0' : (np.exp(self.I0), std_interc),
#                   'Rg' : (self.Rg, std_slope),
#                   'qRg': self.Rg * np.sqrt(x[-1]),
#                   'rsq': rsq}
#                                                      
#        controlPanel = wx.FindWindowByName('GuinierControlPanel')
#        controlPanel.updateInfo(newInfo)
#                
#        xg = [0, x[0]]
#        yg = [self.I0, yr[0]]
#        
#        xfull = np.power(self.q,2)
#        yfull = np.log(self.i)
#        
#        xf = xfull[np.where(np.isnan(yfull)==False)]
#        yf = yfull[np.where(np.isnan(yfull)==False)]
#        
#        if self.fitline != None:
#            self.fitline.remove()
#
#        self.fitline = matplotlib.lines.Line2D(x, yr, linewidth = 1, color = 'r', alpha = 1, label = 'fitline')
#        a.add_artist(self.fitline)
#        
#        self.interpline = matplotlib.lines.Line2D(xg, yg, linewidth = 1, color = 'g', linestyle = '--', alpha = 1, label = 'interpline')
#        a.add_artist(self.interpline)              
#        
#        self.maxmin = (np.min([yr.min(), y.min()]), np.max([y.max(), self.I0]))
#                
#        self.drawError(x, error)
#        
#        self.canvas.draw_idle()
#    
#    def SetColor(self, rgbtuple = None):
#        """ Set figure and canvas colours to be the same """
#        if not rgbtuple:
#             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
#       
#        col = [c/255.0 for c in rgbtuple]
#        self.fig.set_facecolor(col)
#        self.fig.set_edgecolor(col)
#        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))
#
#    def setLimits(self, limits):
#        self.limits = limits
#        
#        self.bottomlimit = limits[1]
#        self.toplimit = limits[0]       
             
class GuinierControlPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, ExpObj, manip_item):
        
        self.ExpObj = ExpObj
        
        self.manip_item = manip_item
        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        
        try:
            self.raw_settings = self.main_frame.raw_settings
        except AttributeError:
            self.raw_settings = RAWSettings.RawGuiSettings()

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
          
        self.spinctrlIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.staticTxtIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.infodata = {'I0' : ('I0 :', wx.NewId(), wx.NewId()),
                         'Rg' : ('Rg :', wx.NewId(), wx.NewId()),
                         'qRg_max': ('qRg_max :', wx.NewId()),
                         'qRg_min': ('qRg :', wx.NewId()),
                         'rsq': ('r^2 (fit) :', wx.NewId()),
                         'MM': ('MM :', wx.NewId())}
        

        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)
        
        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)
        
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1)
        
        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self.createInfoBox()
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP ,5)
        qrgsizer = self.createQRgInfo()
        boxSizer.Add(qrgsizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        
        
        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self.createControls()
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND)
        
        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        bsizer.Add(self.createConcInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT| wx.TOP, 5)
         
        self.SetSizer(bsizer)
        
        self.setFilename(os.path.basename(ExpObj.getParameter('filename')))
        
        #self._initSettings()
                
                
    def _initSettings(self):
        
        analysis = self.ExpObj.getParameter('analysis')
        
        if 'guinier' in analysis:
            
            guinier = analysis['guinier']
            
            start_idx = guinier['nStart']
            end_idx = guinier['nEnd']
            
            spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
            
            old_start = spinstart.GetValue()
            old_end = spinend.GetValue()
            
            try:
                spinstart.SetValue(int(start_idx))
                spinend.SetValue(int(end_idx))
                self.updatePlot()
            
            except IndexError:
                spinstart.SetValue(old_start)
                spinend.SetValue(old_end)
                print 'FAILED initSetting! resetting controls'
            
        
    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))
        
    def createFileInfo(self):
        
        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        
        #txt = wx.StaticText(self, -1, 'Filename :')
        self.filenameTxtCtrl = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY)
        
        #boxsizer.Add((5,5),0)
        #boxsizer.Add(txt,0,wx.EXPAND | wx.TOP , 4)
        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND)
        
        return boxsizer
    
    def getConcentration(self):
        
        try:
            val = float(self.concCtrl.GetValue())
            return val
        except Exception:
            return 0
    
    def createConcInfo(self):
        box = wx.StaticBox(self, -1, 'Sample Concentration')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        
        
        if self.ExpObj.getAllParameters().has_key('Conc'):
            val = self.ExpObj.getParameter('Conc')
        else:
            val = ''
        
        self.concCtrl = wx.TextCtrl(self, -1, str(val), size = (60, -1))
        txt = wx.StaticText(self, -1,  'mg/ml')

        boxsizer.Add(self.concCtrl, 0, wx.EXPAND)
        boxsizer.Add(txt, 0, wx.LEFT, 5)
        
        return boxsizer
        
    def onSaveInfo(self, evt):
        gp = wx.FindWindowByName('GuinierPlotPanel')
        x_fit, y_fit, I0, error, newInfo = gp._calcFit()
        self.updateInfo(newInfo)
        
        info_dict = {}
        
        for key in self.infodata.keys():
            id = self.infodata[key][1]
            widget = wx.FindWindowById(id)
            val = widget.GetValue()
            
            info_dict[key] = val
        
        info_dict['Conc'] = self.getConcentration()
        
        nstart_val = wx.FindWindowById(self.spinctrlIDs['qstart']).GetValue()
        nend_val = wx.FindWindowById(self.spinctrlIDs['qend']).GetValue()
        
        qstart_val = wx.FindWindowById(self.staticTxtIDs['qstart']).GetValue()
        qend_val = wx.FindWindowById(self.staticTxtIDs['qend']).GetValue()
                
        info_dict['nStart'] = nstart_val
        info_dict['nEnd'] = nend_val
        info_dict['qStart'] = qstart_val
        info_dict['qEnd'] = qend_val
        
        if self.getConcentration() > 0:
            self.ExpObj.setParameter('Conc', self.getConcentration())
            
        if self.getConcentration() > 0:
            self.ExpObj.setParameter('MW', info_dict['MM'])
        
        analysis_dict = self.ExpObj.getParameter('analysis')
        analysis_dict['guinier'] = info_dict
        
        if self.manip_item != None:
            wx.CallAfter(self.manip_item.updateInfoTip, analysis_dict, fromGuinierDialog = True)
        
        #wx.MessageBox('The parameters have now been stored in memory', 'Parameters Saved')
        
        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()
        
    def onCloseButton(self, evt):
        
        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()
        
        
    def setCurrentExpObj(self, ExpObj):
        
        self.ExpObj = ExpObj
        #self.onSpinCtrl(self.startSpin)
    
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
                #ctrl2 = wx.TextCtrl(self, self.infodata[key][2], '0', size = (60,21))
                #txtpm = wx.StaticText(self, -1, u"\u00B1")
                
                bsizer = wx.BoxSizer()
                bsizer.Add(ctrl1,0,wx.EXPAND)
                #bsizer.Add(txtpm,0, wx.LEFT | wx.TOP, 3)
                #bsizer.Add(ctrl2,0,wx.EXPAND | wx.LEFT, 3)
                
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
        
#        if sys.platform == 'darwin':
#             # For getting Mac to process ENTER events:
#            self.startSpin.GetChildren()[0].SetWindowStyle(wx.PROCESS_ENTER)
#            self.startSpin.GetChildren()[0].Bind(wx.EVT_TEXT_ENTER, self.onEnterOnSpinCtrl)                           
#                                                         
#            self.endSpin.GetChildren()[0].SetWindowStyle(wx.PROCESS_ENTER)
#            self.endSpin.GetChildren()[0].Bind(wx.EVT_TEXT_ENTER, self.onEnterOnSpinCtrl) 
#        
        
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
        sizer.Add(self.endSpin, 0, wx.EXPAND | wx.RIGHT, 5)
        
        return sizer
    
    def onEnterInQlimits(self, evt):
        
        id = evt.GetId()
        
        lx = self.ExpObj.q
        ly = self.ExpObj.i
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))

        txtctrl = wx.FindWindowById(id)
        
        #### If User inputs garbage: ####
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if id == self.staticTxtIDs['qstart']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qstart'])
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return
            
            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'])
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return
        #################################
            
        closest = findClosest(val,lx)
            
        i = np.where(lx == closest)[0][0]
        
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'])
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'])
        
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
                
        txtctrl.SetValue(str(round(self.ExpObj.q[int(i)],5)))
        
        wx.CallAfter(self.updatePlot)
        
    def setSpinLimits(self, ExpObj):
        self.startSpin.SetRange((0, len(ExpObj.q)-1))
        self.endSpin.SetRange((0, len(ExpObj.q)-1))
        
        self.endSpin.SetValue(len(ExpObj.q)-1)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'])
        txt.SetValue(str(round(ExpObj.q[int(len(ExpObj.q)-1)],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
        txt.SetValue(str(round(ExpObj.q[0],4)))
        
        self._initSettings()
        
    def onEnterOnSpinCtrl(self, evt):
        ''' Little workaround to make enter key in spinctrl work on Mac too '''
        spin = evt.GetEventObject()
        
        self.startSpin.SetFocus()
        self.endSpin.SetFocus()
        
        spin.SetFocus()
        
    def onSpinCtrl(self, evt):
        
        id = evt.GetId()
        
        spin = wx.FindWindowById(id)
             
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'])
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'])
            
        i = spin.GetValue()
        
        #Make sure the boundaries don't cross:
        if id == self.spinctrlIDs['qstart']:
            max = endSpin.GetValue()
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
            
            if i > max-3:
                i = max - 3
                spin.SetValue(i)
            
        elif id == self.spinctrlIDs['qend']:
            min = startSpin.GetValue()
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            
            if i < min+3:
                i = min + 3
                spin.SetValue(i)
                
        txt.SetValue(str(round(self.ExpObj.q[int(i)],5)))
        
        #Important, since it's a slow function to update (could do it in a timer instead) otherwise this spin event might loop!
        wx.CallAfter(self.updatePlot)
        
    def updatePlot(self):
        plotpanel = wx.FindWindowByName('GuinierPlotPanel')
        a = plotpanel.subplots['Guinier']
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i = int(spinstart.GetValue())
        
        x = self.ExpObj.q
        y = self.ExpObj.i
        
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i2 = int(spinend.GetValue())
        
        xlim = [i,i2]
        plotpanel.updateDataPlot(y, x, xlim)
        
        #plotpanel.canvas.draw()
        
    def updateInfo(self, newInfo):
        
        for eachkey in newInfo.iterkeys():
            
            if len(self.infodata[eachkey]) == 2: 
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey],5)))
            else:
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey][0],5)))
                
                #ctrlerr = wx.FindWindowById(self.infodata[eachkey][2])
                #ctrlerr.SetValue(str(round(newInfo[eachkey][1],5)))
             
    def updateLimits(self, top = None, bottom = None):
  
        if bottom:
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
            spinend.SetValue(bottom)
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            txt.SetValue(str(round(self.ExpObj.q[int(bottom)],4)))
            
        if top:
            spinend = wx.FindWindowById(self.spinctrlIDs['qstart'])
            spinend.SetValue(top)
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
            txt.SetValue(str(round(self.ExpObj.q[int(top)],4)))
            
    def getLimits(self):
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        return [int(spinstart.GetValue()), int(spinend.GetValue())]
    
    def getInfo(self):
        
        guinierData = {}
        
        for eachKey in self.infodata.iterkeys():
            
            if len(self.infodata[eachKey]) == 2:
                ctrl = wx.FindWindowById(self.infodata[eachKey][1])
                val = ctrl.GetValue()
                guinierData[eachKey] = val
            else:
                ctrl1 = wx.FindWindowById(self.infodata[eachKey][1])
                ctrl2 = wx.FindWindowById(self.infodata[eachKey][2])
                val1 = ctrl1.GetValue()
                val2 = ctrl2.GetValue()
                
                guinierData[eachKey] = (val1, val2) 
                
        return guinierData
    
#---- **** Main Dialog ****
    
class GuinierFitDialog(wx.Dialog):

    def __init__(self, parent, ExpObj):
        wx.Dialog.__init__(self, parent, -1, 'Guinier Fit', name = 'GuinierDialog', size = (800,600))
    
        splitter1 = wx.SplitterWindow(self, -1)
     
        self.controlPanel = GuinierControlPanel(splitter1, -1, 'GuinierControlPanel')
        plotPanel = GuinierPlotPanel(splitter1, -1, 'GuinierPlotPanel')
  
        splitter1.SplitVertically(controlPanel, plotPanel, 270)
        splitter1.SetMinimumPaneSize(50)
    
        plotPanel.plotExpObj(ExpObj)
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)
        
    def getConcentration(self):
        return self.controlPanel.getConcentration()
        
    def OnClose(self):
        self.Destroy()


#---- **** Porod plotting ****

class PorodDialog(wx.Dialog):

    def __init__(self, parent, ExpObj):
        wx.Dialog.__init__(self, parent, -1, 'Porod', name = 'PorodDialog', size = (800,600))
    
        splitter1 = wx.SplitterWindow(self, -1)
     
        controlPanel = PorodControlPanel(splitter1, -1, 'PorodControlPanel')
        plotPanel = PorodPlotPanel(splitter1, -1, 'PorodPlotPanel')
  
        splitter1.SplitVertically(controlPanel, plotPanel, 270)
        splitter1.SetMinimumPaneSize(50)
    
        plotPanel.plotExpObj(ExpObj)
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)

    def OnClose(self):
        self.Destroy()


class PorodPlotPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, wxEmbedded = False):
        
        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
        
        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
                    
        self.data_line = None
    
        subplotLabels = [('Porod', 'q', 'I(q)q^4', .1)]
        
        self.fig.subplots_adjust(hspace = 0.26)
        
        self.subplots = {}
        
        for i in range(0, len(subplotLabels)):
            subplot = self.fig.add_subplot(len(subplotLabels),1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot 
      
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)
        self.canvas.SetBackgroundColour('white')
        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')
        
        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw) 

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''
        
        a = self.subplots['Porod']
    
        self.background = self.canvas.copy_from_bbox(a.bbox)
        
        self.updateDataPlot()
        
    def _calcFit(self):
        ''' calculate fit and statistics '''
 
        q_roi = self.q
        i_roi = self.i
        
        x = np.power(q_roi, 2)
        y = np.log(i_roi)
        
        #Remove NaN and Inf values:
        x = x[np.where(np.isnan(y) == False)]
        y = y[np.where(np.isnan(y) == False)]
        x = x[np.where(np.isinf(y) == False)]
        y = y[np.where(np.isinf(y) == False)]
        
        #Get 1.st order fit:
        ar, br = polyfit(x, y, 1)
        
        #Obtain fit values:
        y_fit = polyval([ar, br], x)
        
        #Get fit statistics:
        error = y - y_fit
        SS_tot = np.sum(np.power(y-np.mean(y),2))
        SS_err = np.sum(np.power(error, 2))
        rsq = 1 - SS_err / SS_tot
        
        I0 = br
        Rg = np.sqrt(-3*ar)
                
        if np.isnan(Rg):
            Rg = 0  
        
        ######## CALCULATE ERROR ON PARAMETERS ###############
        
        N = len(error)
        stde = SS_err / (N-2)
        std_slope = stde * np.sqrt( (1/N) +  (np.power(np.mean(x),2)/np.sum(np.power(x-np.mean(x),2))))
        std_interc = stde * np.sqrt(  1 / np.sum(np.power(x-np.mean(x),2)))
        
        ######################################################
        
        if np.isnan(std_slope):
            std_slope = -1
        if np.isnan(std_interc):
            std_interc = -1
        
        newInfo = {'I0' : (np.exp(I0), std_interc),
                   'Rg' : (Rg, std_slope),
                   'qRg': Rg * np.sqrt(x[-1]),
                   'rsq': rsq}
        
        
        
        
        return x, y_fit, br, error, newInfo
        
    def plotExpObj(self, ExpObj):
        xlim = [0, len(ExpObj.i)]
        
        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        #self.updateDataPlot(ExpObj.i, ExpObj.q, xlim)
        
        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self):
        
        pass
            
#        xmin, xmax = xlim
#        
#        #Save for resizing:
#        self.orig_i = i
#        self.orig_q = q
#        self.xlim = xlim
#        
#        #Cut out region of interest
#        self.i = i[xmin:xmax]
#        self.q = q[xmin:xmax]
#        
#        ## Plot the (at most) 3 first and last points after fit:
#        if xmin < 3:
#            min_offset = xmin
#        else:
#            min_offset = 3
#        
#        if xmax > len(q)-3:
#            max_offset = len(q) - xmax
#        else:
#            max_offset = 3
#
#        xmin = xmin - min_offset
#        xmax = xmax + max_offset
#        
#        #data containing the 3 first and last points
#        q_offset = q[xmin:xmax]
#        i_offset = i[xmin:xmax]
#            
#        x = np.power(q_offset, 2)
#        y = np.log(i_offset)
#         
#        x = x[np.where(np.isnan(y)==False)]
#        y = y[np.where(np.isnan(y)==False)]
#        x = x[np.where(np.isinf(y)==False)]
#        y = y[np.where(np.isinf(y)==False)]
#            
#        a = self.subplots['Porod']
#        
#        
#        try:
#            x_fit, y_fit, I0, error, newInfo = self._calcFit()
#        except TypeError:
#            return
#                                                      
#        controlPanel = wx.FindWindowByName('PorodControlPanel')
#        wx.CallAfter(controlPanel.updateInfo, newInfo)
#        
#        xg = [0, x_fit[0]]
#        yg = [I0, y_fit[0]]
#        
#        zeros = np.zeros((1,len(x_fit)))[0]
#        
#        x_lim_front = x[0]
#        x_lim_back = x[-1]
#        
#        if not self.data_line:
#            self.data_line, = a.plot(x, y, 'b.', animated = True)
#            self.fit_line, = a.plot(x_fit, y_fit, 'r', animated = True)
#            self.interp_line, = a.plot(xg, yg, 'g--', animated = True)
#
#            self.error_line, = b.plot(x_fit, error, 'b', animated = True)
#            self.zero_line, = b.plot(x_fit, zeros, 'r', animated = True)
#            
#            self.lim_front_line = a.axvline(x=x_lim_front, color = 'r', linestyle = '--', animated = True)
#            self.lim_back_line = a.axvline(x=x_lim_back, color = 'r', linestyle = '--', animated = True)
#            
#            #self.lim_back_line, = a.plot([x_lim_back, x_lim_back], [y_lim_back-0.2, y_lim_back+0.2], transform=a.transAxes, animated = True)
#            
#            self.canvas.draw()
#            self.background = self.canvas.copy_from_bbox(a.bbox)
#            self.err_background = self.canvas.copy_from_bbox(b.bbox)
#        else:
#            self.canvas.restore_region(self.background)
#            
#            self.data_line.set_ydata(y)
#            self.data_line.set_xdata(x)
#            
#            self.fit_line.set_ydata(y_fit)
#            self.fit_line.set_xdata(x_fit)
#            
#            self.interp_line.set_xdata(xg)
#            self.interp_line.set_ydata(yg)
#            
#            self.lim_back_line.set_xdata(x_fit[-1])
#            self.lim_front_line.set_xdata(x_fit[0])
#  
#            #Error lines:          
#            self.error_line.set_xdata(x_fit)
#            self.error_line.set_ydata(error)
#            self.zero_line.set_xdata(x_fit)
#            self.zero_line.set_ydata(zeros)
#        
#        a.relim()
#        a.autoscale_view()
#        
#        a.draw_artist(self.data_line)
#        a.draw_artist(self.fit_line)
#        a.draw_artist(self.interp_line)
#        a.draw_artist(self.lim_front_line)
#        a.draw_artist(self.lim_back_line)
#
#        b.set_xlim((x_fit[0], x_fit[-1]))
#        b.set_ylim((error.min(), error.max()))
#  
#        #restore white background in error plot and draw new error:
#        self.canvas.restore_region(self.err_background)
#        b.draw_artist(self.error_line)
#        b.draw_artist(self.zero_line)
#
#        self.canvas.blit(a.bbox)
#        self.canvas.blit(b.bbox)


class PorodControlPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, ExpObj, manip_item):
        
        self.ExpObj = ExpObj
        
        self.manip_item = manip_item

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
          
        self.spinctrlIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.staticTxtIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.infodata = {'I0' : ('I0 :', wx.NewId(), wx.NewId()),
                         'Rg' : ('Rg :', wx.NewId(), wx.NewId()),
                         'Volume': ('Volume :', wx.NewId()),
                         'Weight': ('Weight :', wx.NewId())}
        

        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)
        
        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)
        
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(savebutton, 1, wx.RIGHT, 5)
        buttonSizer.Add(button, 1)
        
        
        box = wx.StaticBox(self, -1, 'Parameters')
        infoSizer = self.createInfoBox()
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        
        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self.createControls()
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND)
        
        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT| wx.TOP, 5)
         
        self.SetSizer(bsizer)
        
        self.setFilename(os.path.basename(ExpObj.getParameter('filename')))
        
        #self._initSettings()
                
                
    def _initSettings(self):
        
        analysis = self.ExpObj.getParameter('analysis')
        
        if 'porod' in analysis:
            
            porod = analysis['porod']
            
            start_idx = porod['nStart']
            end_idx = porod['nEnd']
            
            spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
            
            old_start = spinstart.GetValue()
            old_end = spinend.GetValue()
            
            try:
                spinstart.SetValue(int(start_idx))
                spinend.SetValue(int(end_idx))
                self.updatePlot()
            
            except IndexError:
                spinstart.SetValue(old_start)
                spinend.SetValue(old_end)
                print 'FAILED initSetting! resetting controls'
            
        
    def setFilename(self, filename):
        self.filenameTxtCtrl.SetValue(str(filename))
        
    def createFileInfo(self):
        
        box = wx.StaticBox(self, -1, 'Filename')
        boxsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        
        #txt = wx.StaticText(self, -1, 'Filename :')
        self.filenameTxtCtrl = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY)
        
        #boxsizer.Add((5,5),0)
        #boxsizer.Add(txt,0,wx.EXPAND | wx.TOP , 4)
        boxsizer.Add(self.filenameTxtCtrl, 1, wx.EXPAND)
        
        return boxsizer
        
        
    def onSaveInfo(self, evt):
        
        info_dict = {}
        
        for key in self.infodata.keys():
            id = self.infodata[key][1]
            widget = wx.FindWindowById(id)
            val = widget.GetValue()
            
            info_dict[key] = val
        
        nstart_val = wx.FindWindowById(self.spinctrlIDs['qstart']).GetValue()
        nend_val = wx.FindWindowById(self.spinctrlIDs['qend']).GetValue()
        
        qstart_val = wx.FindWindowById(self.staticTxtIDs['qstart']).GetValue()
        qend_val = wx.FindWindowById(self.staticTxtIDs['qend']).GetValue()
                
        info_dict['nStart'] = nstart_val
        info_dict['nEnd'] = nend_val
        info_dict['qStart'] = qstart_val
        info_dict['qEnd'] = qend_val
        
        analysis_dict = self.ExpObj.getParameter('analysis')
        analysis_dict['porod'] = info_dict
        
        if self.manip_item != None:
            wx.CallAfter(self.manip_item.updateInfoTip, analysis_dict)
        
        wx.MessageBox('The parameters have now been stored in memory', 'Parameters Saved')
        
        diag = wx.FindWindowByName('PorodFrame')
        diag.OnClose()
        
    def onCloseButton(self, evt):
        
        diag = wx.FindWindowByName('PorodFrame')
        diag.OnClose()
        
        
    def setCurrentExpObj(self, ExpObj):
        
        self.ExpObj = ExpObj
        #self.onSpinCtrl(self.startSpin)
        
    def createInfoBox(self):
        
        sizer = wx.FlexGridSizer(rows = len(self.infodata), cols = 2)
        
        for key in self.infodata.iterkeys():
            
            if len(self.infodata[key]) == 2:
                txt = wx.StaticText(self, -1, self.infodata[key][0])
                ctrl = wx.TextCtrl(self, self.infodata[key][1], '0')
                sizer.Add(txt, 0)
                sizer.Add(ctrl,0)
            else:
                txt = wx.StaticText(self, -1, self.infodata[key][0])
                ctrl1 = wx.TextCtrl(self, self.infodata[key][1], '0')      
                #ctrl2 = wx.TextCtrl(self, self.infodata[key][2], '0', size = (60,21))
                #txtpm = wx.StaticText(self, -1, u"\u00B1")
                
                bsizer = wx.BoxSizer()
                bsizer.Add(ctrl1,0,wx.EXPAND)
                #bsizer.Add(txtpm,0, wx.LEFT | wx.TOP, 3)
                #bsizer.Add(ctrl2,0,wx.EXPAND | wx.LEFT, 3)
                
                sizer.Add(txt,0)
                sizer.Add(bsizer,0)
             
        return sizer
        
    def createControls(self):
        
        sizer = wx.FlexGridSizer(rows = 1, cols = 4)
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
        
#        if sys.platform == 'darwin':
#             # For getting Mac to process ENTER events:
#            self.startSpin.GetChildren()[0].SetWindowStyle(wx.PROCESS_ENTER)
#            self.startSpin.GetChildren()[0].Bind(wx.EVT_TEXT_ENTER, self.onEnterOnSpinCtrl)                           
#                                                         
#            self.endSpin.GetChildren()[0].SetWindowStyle(wx.PROCESS_ENTER)
#            self.endSpin.GetChildren()[0].Bind(wx.EVT_TEXT_ENTER, self.onEnterOnSpinCtrl) 
#        
        
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
        sizer.Add(self.endSpin, 0, wx.EXPAND | wx.RIGHT, 5)
        
        return sizer
    
    def onEnterInQlimits(self, evt):
        
        id = evt.GetId()
        
        lx = self.ExpObj.q
        ly = self.ExpObj.i
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))

        txtctrl = wx.FindWindowById(id)
        
        #### If User inputs garbage: ####
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if id == self.staticTxtIDs['qstart']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qstart'])
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return
            
            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'])
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return
        #################################
            
        closest = findClosest(val,lx)
            
        i = np.where(lx == closest)[0][0]
        
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'])
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'])
        
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
                
        txtctrl.SetValue(str(round(self.ExpObj.q[int(i)],5)))
        
        wx.CallAfter(self.updatePlot)
        
    def setSpinLimits(self, ExpObj):
        self.startSpin.SetRange((0, len(ExpObj.q)-1))
        self.endSpin.SetRange((0, len(ExpObj.q)-1))
        
        self.endSpin.SetValue(len(ExpObj.q)-1)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'])
        txt.SetValue(str(round(ExpObj.q[int(len(ExpObj.q)-1)],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
        txt.SetValue(str(round(ExpObj.q[0],4)))
        
        self._initSettings()
        
    def onEnterOnSpinCtrl(self, evt):
        ''' Little workaround to make enter key in spinctrl work on Mac too '''
        spin = evt.GetEventObject()
        
        self.startSpin.SetFocus()
        self.endSpin.SetFocus()
        
        spin.SetFocus()
        
    def onSpinCtrl(self, evt):
        
        id = evt.GetId()
        
        spin = wx.FindWindowById(id)
             
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'])
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'])
            
        i = spin.GetValue()
        
        #Make sure the boundaries don't cross:
        if id == self.spinctrlIDs['qstart']:
            max = endSpin.GetValue()
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
            
            if i > max-3:
                i = max - 3
                spin.SetValue(i)
            
        elif id == self.spinctrlIDs['qend']:
            min = startSpin.GetValue()
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            
            if i < min+3:
                i = min + 3
                spin.SetValue(i)
                
        txt.SetValue(str(round(self.ExpObj.q[int(i)],5)))
        
        #Important, since it's a slow function to update (could do it in a timer instead) otherwise this spin event might loop!
        wx.CallAfter(self.updatePlot)
        
    def updatePlot(self):
        plotpanel = wx.FindWindowByName('PorodPlotPanel')
        a = plotpanel.subplots['Porod']
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i = int(spinstart.GetValue())
        
        x = self.ExpObj.q
        y = self.ExpObj.i
        
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i2 = int(spinend.GetValue())
        
        xlim = [i,i2]
        plotpanel.updateDataPlot(y, x, xlim)
        
    def updateInfo(self, newInfo):
        
        for eachkey in newInfo.iterkeys():
            
            if len(self.infodata[eachkey]) == 2: 
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey],5)))
            else:
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey][0],5)))
                
                #ctrlerr = wx.FindWindowById(self.infodata[eachkey][2])
                #ctrlerr.SetValue(str(round(newInfo[eachkey][1],5)))
             
    def updateLimits(self, top = None, bottom = None):
  
        if bottom:
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
            spinend.SetValue(bottom)
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            txt.SetValue(str(round(self.ExpObj.q[int(bottom)],4)))
            
        if top:
            spinend = wx.FindWindowById(self.spinctrlIDs['qstart'])
            spinend.SetValue(top)
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
            txt.SetValue(str(round(self.ExpObj.q[int(top)],4)))
            
    def getLimits(self):
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        return [int(spinstart.GetValue()), int(spinend.GetValue())]
    
    def getInfo(self):
        
        porodData = {}
        
        for eachKey in self.infodata.iterkeys():
            
            if len(self.infodata[eachKey]) == 2:
                ctrl = wx.FindWindowById(self.infodata[eachKey][1])
                val = ctrl.GetValue()
                porodData[eachKey] = val
            else:
                ctrl1 = wx.FindWindowById(self.infodata[eachKey][1])
                ctrl2 = wx.FindWindowById(self.infodata[eachKey][2])
                val1 = ctrl1.GetValue()
                val2 = ctrl2.GetValue()
                
                porodData[eachKey] = (val1, val2) 
                
        return porodData

#---- **** FOR TESTING ****


class PorodTestFrame(wx.Frame):
    
    def __init__(self, parent, title, ExpObj, manip_item):
        
        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'PorodFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'PorodFrame', size = (800,600))
        
        splitter1 = wx.SplitterWindow(self, -1)   
        
        plotPanel = PorodPlotPanel(splitter1, -1, 'PorodPlotPanel')
        controlPanel = PorodControlPanel(splitter1, -1, 'PorodControlPanel', ExpObj, manip_item)
          
        splitter1.SplitVertically(controlPanel, plotPanel, 290)
        splitter1.SetMinimumPaneSize(50)
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(1)
        #self.statusbar.SetStatusWidths([-3, -2])

        plotPanel.plotExpObj(ExpObj)
        
        
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)
        
        self.CenterOnParent()
    
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)
        
    def OnClose(self):
        
        self.Destroy()
        
class PorodTestApp(wx.App):
    
    def OnInit(self, filename = None):
        
        #ExpObj, ImgDummy = fileIO.loadFile('/home/specuser/Downloads/BSUB_MVMi7_5_FULL_001_c_plot.rad')
        
        tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'lyzexp.dat')
        
        #tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'Lys12_1_001_plot.rad')
        
        print tst_file
        raw_settings = RAWSettings.RawGuiSettings()

        ExpObj, ImgDummy = SASFileIO.loadFile(tst_file, raw_settings)
        
        frame = PorodTestFrame(self, 'Porod', ExpObj, None)
        self.SetTopWindow(frame)
        frame.SetSize((800,600))
        frame.CenterOnScreen()
        frame.Show(True)
        return True

              
class GuinierTestFrame(wx.Frame):
    
    def __init__(self, parent, title, ExpObj, manip_item):
        
        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'GuinierFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'GuinierFrame', size = (800,600))
        
        splitter1 = wx.SplitterWindow(self, -1)
                
        
        plotPanel = GuinierPlotPanel(splitter1, -1, 'GuinierPlotPanel')
        controlPanel = GuinierControlPanel(splitter1, -1, 'GuinierControlPanel', ExpObj, manip_item)
  
        splitter1.SplitVertically(controlPanel, plotPanel, 290)
        splitter1.SetMinimumPaneSize(50)
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(1)
        #self.statusbar.SetStatusWidths([-3, -2])

        plotPanel.plotExpObj(ExpObj)
        
        
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)
        
        self.CenterOnParent()
    
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)
        
    def OnClose(self):
        
        self.Destroy()
        
class GuinierTestApp(wx.App):
    
    def OnInit(self, filename = None):
        
        #ExpObj, ImgDummy = fileIO.loadFile('/home/specuser/Downloads/BSUB_MVMi7_5_FULL_001_c_plot.rad')
        
        tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'lyzexp.dat')
        
        #tst_file = os.path.join(os.getcwd(), 'Tests', 'TestData', 'Lys12_1_001_plot.rad')
        
        print tst_file
        raw_settings = RAWSettings.RawGuiSettings()

        ExpObj, ImgDummy = SASFileIO.loadFile(tst_file, raw_settings)
        
        frame = GuinierTestFrame(self, 'Guinier Fit', ExpObj, None)
        self.SetTopWindow(frame)
        frame.SetSize((800,600))
        frame.CenterOnScreen()
        frame.Show(True)
        return True
        
if __name__ == "__main__":
    import SASFileIO

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


