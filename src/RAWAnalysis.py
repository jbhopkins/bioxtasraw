'''
Created on Mar 23, 2010

@author: specuser
'''
import matplotlib
#matplotlib.use('WXAgg')
matplotlib.rc('image', origin = 'lower')        # turn image upside down.. x,y, starting from lower left

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg#,Toolbar, FigureCanvasWx
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
import numpy as np
import sys, os, copy, multiprocessing, threading, Queue, wx, time

from scipy import polyval, polyfit, sqrt, integrate
import scipy.interpolate as interp
from scipy.constants import Avogadro
import scipy.stats as stats

import RAW, RAWSettings, RAWCustomCtrl, SASCalc, RAWPlot, SASFileIO, SASM, SASExceptions, BIFT, RAWGlobals

# These are for the AutoWrapStaticText class
from wx.lib.wordwrap import wordwrap
from wx.lib.stattext import GenStaticText as StaticText
import wx.lib.agw.flatnotebook as flatNB

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        # self.toolbar = RAWPlot.CustomSECPlotToolbar(self, self.canvas)

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
        
        self.updateDataPlot(self.orig_i, self.orig_q, self.xlim)

        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        
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
        if xmin < 20:
            min_offset = xmin
        else:
            min_offset = 20
        
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
        b = self.subplots['Residual']
        
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

        # b.set_xlim((x_fit[0], x_fit[-1]))
        # b.set_ylim((error.min(), error.max()))

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
          
        self.spinctrlIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.staticTxtIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.infodata = {'I0' : ('I0 :', wx.NewId(), wx.NewId()),
                         'Rg' : ('Rg :', wx.NewId(), wx.NewId()),
                         'qRg_max': ('qRg_max :', wx.NewId()),
                         'qRg_min': ('qRg :', wx.NewId()),
                         'rsq': ('r^2 (fit) :', wx.NewId())}
        

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
        
        
        box2 = wx.StaticBox(self, -1, 'Control')
        controlSizer = self.createControls()
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND)
        line_sizer = wx.StaticLine(parent = self, style = wx.LI_HORIZONTAL)
        boxSizer2.Add(line_sizer, 0, flag = wx.EXPAND | wx.ALL, border = 10)
        boxSizer2.Add(autorg_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
        
        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        # bsizer.Add(self.createConcInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT| wx.TOP, 5)
         
        self.SetSizer(bsizer)
        
        self.setFilename(os.path.basename(ExpObj.getParameter('filename')))
                
                
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

            spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
            
            old_start = spinstart.GetValue()
            old_end = spinend.GetValue()

            try:
                spinstart.SetValue(int(idx_min))
                spinend.SetValue(int(idx_max))

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                txt.SetValue(str(round(self.ExpObj.q[int(idx_min)],5)))
            
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                txt.SetValue(str(round(self.ExpObj.q[int(idx_max)],5)))
                    
                self.updatePlot()
            except IndexError:
                spinstart.SetValue(old_start)
                spinend.SetValue(old_end)

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                txt.SetValue(str(round(self.ExpObj.q[int(old_start)],5)))
            
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                txt.SetValue(str(round(self.ExpObj.q[int(old_end)],5)))

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
            analysis_dict['guinier'] = info_dict
            
            if self.manip_item != None:
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

        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        old_start = spinstart.GetValue()
        old_end = spinend.GetValue()

        if rg == -1:
            msg = 'AutoRG could not find a suitable interval to calculate Rg.'
            wx.CallAfter(wx.MessageBox, str(msg), "AutoRG Failed", style = wx.ICON_ERROR | wx.OK)
            
        else:
            try:
                spinstart.SetValue(int(idx_min))
                spinend.SetValue(int(idx_max))

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                txt.SetValue(str(round(self.ExpObj.q[int(idx_min)],5)))
            
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                txt.SetValue(str(round(self.ExpObj.q[int(idx_max)],5)))
                    
                self.updatePlot()
            except IndexError:
                spinstart.SetValue(old_start)
                spinend.SetValue(old_end)

                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                txt.SetValue(str(round(self.ExpObj.q[int(old_start)],5)))
            
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                txt.SetValue(str(round(self.ExpObj.q[int(old_end)],5)))

                print 'FAILED AutoRG! resetting controls'
                msg = 'AutoRG did not produce a useable result. Please report this to the developers.'
                response = wx.MessageBox(str(msg), "AutoRG Failed", style = wx.ICON_ERROR | wx.OK)
        
    def setCurrentExpObj(self, ExpObj):
        
        self.ExpObj = ExpObj
    
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

        plotpanel.canvas.mpl_disconnect(plotpanel.cid) #disconnect draw event to avoid recursions
        plotpanel.updateDataPlot(y, x, xlim)
        plotpanel.cid = plotpanel.canvas.mpl_connect('draw_event', plotpanel.ax_redraw) #Reconnect draw_event

        
    def updateInfo(self, newInfo):
        
        for eachkey in newInfo.iterkeys():
            
            if len(self.infodata[eachkey]) == 2: 
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey],5)))
            else:
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey][0],5)))
             
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
  
        splitter1.SplitVertically(self.controlPanel, plotPanel, 290)

        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:
            splitter1.SetMinimumPaneSize(290)    #Back compatability with older wxpython versions
        else:
            splitter1.SetMinimumPaneSize(50)

        plotPanel.plotExpObj(ExpObj)
        
        
        self.controlPanel.setSpinLimits(ExpObj)
        self.controlPanel.setCurrentExpObj(ExpObj)
        self.controlPanel._initSettings()
        
        splitter1.Layout()
        self.Layout()
        self.SendSizeEvent()
        splitter1.Layout()
        self.Layout()

        if self.GetBestSize()[0] > self.GetSize()[0] or self.GetBestSize()[1] > self.GetSize()[1]:
            print 'fitting the guinier window size'
            splitter1.Fit()
            if platform.system() == 'Linux' and int(wx.__version__.split('.')[0]) >= 3:
                size = self.GetSize()
                size[1] = size[1] + 20
                self.SetSize(size)


        self.CenterOnParent()
        self.Raise()

        
    def OnClose(self):
        
        self.Destroy()


class MolWeightFrame(wx.Frame):
    
    def __init__(self, parent, title, sasm, manip_item):
        
        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'MolWeightFrame', size = (960,630))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'MolWeightFrame', size = (960,630))

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

        self.infodata = {'I0' : ('I0 :', wx.NewId(), wx.NewId()),
                         'Rg' : ('Rg :', wx.NewId(), wx.NewId())}

        self.ids = {'VC': {'mol_type' : wx.NewId(), 
                           'calc_mw' : wx.NewId(), 
                           'info': wx.NewId(),
                           'more': wx.NewId(),
                           'sup_vc': wx.NewId(),
                           'sup_qr': wx.NewId(),
                           'sup_a': wx.NewId(),
                           'sup_b': wx.NewId(),
                           'sup_plot': wx.NewId()},
                    'conc': {'calc_mw' : wx.NewId(), 
                             'info': wx.NewId(),
                             'more': wx.NewId(),
                             'conc': wx.NewId(),
                             'sup_i0': wx.NewId(),
                             'sup_mw': wx.NewId(),
                             'sup_conc': wx.NewId(),
                             'sup_file': wx.NewId()},
                    'VP': {'calc_mw' : wx.NewId(), 
                           'info': wx.NewId(),
                           'more': wx.NewId(),
                           'sup_vp': wx.NewId(),
                           'sup_vpc': wx.NewId(),
                           'sup_density': wx.NewId()},
                    'abs': {'calc_mw' : wx.NewId(), 
                              'info': wx.NewId(),
                              'more': wx.NewId(),
                              'calib': wx.NewId(),
                              'conc': wx.NewId(),
                              'sup_pm': wx.NewId(),
                              'sup_ps': wx.NewId(),
                              'sup_pv': wx.NewId(),
                              'sup_r0': wx.NewId(),
                              'sup_sc': wx.NewId()}}


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

        
        mw_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mw_sizer.Add(self.conc_panel, 0, wx.EXPAND)
        mw_sizer.AddStretchSpacer(1)
        mw_sizer.Add(wx.StaticLine(parent = self.top_mw, style = wx.LI_VERTICAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        mw_sizer.AddStretchSpacer(1)
        mw_sizer.Add(self.vc_panel, 0, wx.EXPAND)
        mw_sizer.AddStretchSpacer(1)
        mw_sizer.Add(wx.StaticLine(parent = self.top_mw, style = wx.LI_VERTICAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        mw_sizer.AddStretchSpacer(1)
        mw_sizer.Add(self.vp_panel, 0, wx.EXPAND)
        mw_sizer.AddStretchSpacer(1)
        mw_sizer.Add(wx.StaticLine(parent = self.top_mw, style = wx.LI_VERTICAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        mw_sizer.AddStretchSpacer(1)
        mw_sizer.Add(self.abs_panel, 0, wx.EXPAND)
        mw_sizer.AddStretchSpacer(1)

        self.top_mw.SetSizer(mw_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.info_panel, 0, wx.EXPAND)
        top_sizer.Add(wx.StaticLine(parent = parent, style = wx.LI_HORIZONTAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        top_sizer.Add(self.top_mw, 10, wx.EXPAND)
        top_sizer.Add(wx.StaticLine(parent = parent, style = wx.LI_HORIZONTAL), 0, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 5)
        top_sizer.Add(self.button_panel, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.LEFT, 5)

        return top_sizer

    def _initSettings(self):
        
        analysis = self.sasm.getParameter('analysis')
        
        if 'guinier' in analysis:
            
            guinier = analysis['guinier']

            for each_key in self.infodata.iterkeys():
                window = wx.FindWindowById(self.infodata[each_key][1])
                window.SetValue(guinier[each_key])


        self.setFilename(os.path.basename(self.sasm.getParameter('filename')))

        if self.sasm.getAllParameters().has_key('Conc'):
            conc = str(self.sasm.getParameter('Conc'))
        else:
            conc = ''

        wx.FindWindowById(self.ids['conc']['conc']).ChangeValue(conc)

        wx.FindWindowById(self.ids['abs']['conc']).ChangeValue(conc)

        if self.raw_settings.get('NormAbsWater'):
            wx.FindWindowById(self.ids['abs']['calib']).SetValue(True)


        ref_mw = self.raw_settings.get('MWStandardMW') 
        ref_i0 = self.raw_settings.get('MWStandardI0')
        ref_conc = self.raw_settings.get('MWStandardConc')
        ref_file = self.raw_settings.get('MWStandardFile')

        if ref_mw > 0:
            wx.FindWindowById(self.ids['conc']['sup_mw']).ChangeValue(str(ref_mw))
        else:
            wx.FindWindowById(self.ids['conc']['sup_mw']).ChangeValue('')
        if ref_i0 > 0:
            wx.FindWindowById(self.ids['conc']['sup_i0']).ChangeValue(str(ref_i0))
        else:
            wx.FindWindowById(self.ids['conc']['sup_i0']).ChangeValue('')
        if ref_conc > 0:
            wx.FindWindowById(self.ids['conc']['sup_conc']).ChangeValue(str(ref_conc))
        else:
            wx.FindWindowById(self.ids['conc']['sup_conc']).ChangeValue('')
        wx.FindWindowById(self.ids['conc']['sup_file']).ChangeValue(ref_file)


        #Initialize VC MW settings
        aCtrl = wx.FindWindowById(self.ids['VC']['sup_a'])
        bCtrl = wx.FindWindowById(self.ids['VC']['sup_b'])
        molCtrl = wx.FindWindowById(self.ids['VC']['mol_type'])

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

        aCtrl.SetValue(str(aval))
        bCtrl.SetValue(str(bval))
        molCtrl.SetStringSelection(vc_type)

        wx.FindWindowById(self.ids['VC']['sup_plot']).plotSASM(self.sasm)


        #Initialize Vp MW settings
        vp_rho = self.raw_settings.get('MWVpRho')

        wx.FindWindowById(self.ids['VP']['sup_density']).ChangeValue(str(vp_rho))


        #Initialize Absolute scattering MW settings.
        rho_Mprot = self.raw_settings.get('MWAbsRhoMprot') # electrons per dry mass of protein
        rho_solv = self.raw_settings.get('MWAbsRhoSolv') # electrons per volume of aqueous solvent
        nu_bar = self.raw_settings.get('MWAbsNuBar') # partial specific volume of the protein
        r0 = self.raw_settings.get('MWAbsR0') #scattering lenght of an electron
        d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
        wx.FindWindowById(self.ids['abs']['sup_pm']).ChangeValue('%.2E' %(rho_Mprot))
        wx.FindWindowById(self.ids['abs']['sup_ps']).ChangeValue('%.2E' %(rho_solv))
        wx.FindWindowById(self.ids['abs']['sup_pv']).ChangeValue('%.4f' %(nu_bar))
        wx.FindWindowById(self.ids['abs']['sup_r0']).ChangeValue('%.2E' %(r0))
        wx.FindWindowById(self.ids['abs']['sup_sc']).ChangeValue('%.2E' %(d_rho))


        self.calcMW()
            

    def _createInfoLayout(self, parent):
        #Filename box
        box1 = wx.StaticBox(parent, -1, 'Filename')
        boxSizer1 = wx.StaticBoxSizer(box1, wx.HORIZONTAL)
        self.filenameTxtCtrl = wx.TextCtrl(parent, -1, '', style = wx.TE_READONLY)
        boxSizer1.Add(self.filenameTxtCtrl, 1, wx.EXPAND)

        intro_text = ("This panel has four different methods for determining molecular weight from a scattering "
                        "profile. All of them rely on the I(0) and/or Rg determined by the Guinier fit.\n"
                        "The methods used (panels from left to right):\n"
                        "1) Compare I(0) to a known standard (must have MW standard set).\n"
                        "2) Using the volume of correlation (Vc).\n"
                        "3) Using the Porod volume (Vp).\n"
                        "4) Using absolute calibrated intensity (If your data is calibrated, but absolute "
                        "scale is not enabled in the RAW settings use the checkbox to manually enable).\n"
                        "'Show Details' provides calculation details and advanced options. 'More Info' "
                        "gives a brief description of each method.")

        intro = AutoWrapStaticText(parent, label = intro_text)

        # Guinier parameters box
        infoSizer = wx.FlexGridSizer(rows = len(self.infodata), cols = 2)
        
        for key in self.infodata.iterkeys():
            
            if len(self.infodata[key]) == 2:
                txt = wx.StaticText(parent, -1, self.infodata[key][0])
                ctrl = wx.TextCtrl(parent, self.infodata[key][1], '0', style = wx.TE_READONLY)
                infoSizer.Add(txt, 0)
                infoSizer.Add(ctrl,0)
                
            else:
                txt = wx.StaticText(parent, -1, self.infodata[key][0])
                ctrl1 = wx.TextCtrl(parent, self.infodata[key][1], '0', style = wx.TE_READONLY)      
                
                bsizer = wx.BoxSizer()
                bsizer.Add(ctrl1,0,wx.EXPAND)
                
                infoSizer.Add(txt,0)
                infoSizer.Add(bsizer,0)

        guinierfitbutton = wx.Button(parent, -1, 'Guinier Fit')
        guinierfitbutton.Bind(wx.EVT_BUTTON, self.onGuinierFit)
        
        box2 = wx.StaticBox(parent, -1, 'Guinier Parameters')
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(infoSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP ,5)
        boxSizer2.Add(guinierfitbutton, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT| wx.TOP, 5)

        fileSizer = wx.BoxSizer(wx.VERTICAL)
        fileSizer.Add(boxSizer1, 0, wx.EXPAND | wx.ALL, 2)
        fileSizer.AddStretchSpacer(1)
        fileSizer.Add(boxSizer2, 0, wx.EXPAND | wx.ALL, 2)

        
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(intro, 12, wx.EXPAND | wx.ALL, 5)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(fileSizer, 6, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        top_sizer.AddStretchSpacer(1)

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

        concsizer.Add(conc_txt,0, wx.LEFT, 2)
        concsizer.Add(conc, 1, wx.EXPAND)
        concsizer.Add(conc_txt2, 0, wx.LEFT, 1)


        mwsizer = wx.BoxSizer(wx.HORIZONTAL)
        conc_mw = wx.TextCtrl(parent, conc_ids['calc_mw'], '', size = (60, -1), style = wx.TE_READONLY)
        mw_txt = wx.StaticText(parent, -1, 'MW :')
        mw_txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(mw_txt,0, wx.LEFT, 2)
        mwsizer.Add(conc_mw, 1, wx.EXPAND)
        mwsizer.Add(mw_txt2, 0, wx.LEFT, 1)


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
        sup_sizer1.Add(sup_txt1, 0)
        sup_sizer1.Add(sup_i0, 1, wx.EXPAND)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt2,0)
        sup_sizer2.Add(sup_mw,1,wx.EXPAND)
        sup_sizer2.Add(sup_txt3,0, wx.LEFT, 1)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt4,0)
        sup_sizer3.Add(sup_conc,1, wx.EXPAND)
        sup_sizer3.Add(sup_txt5,0, wx.LEFT, 1)

        sup_sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer4.Add(sup_txt6, 0)
        sup_sizer4.Add(sup_file, 1, wx.EXPAND)

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
        
        VCmw = wx.TextCtrl(parent, vc_ids['calc_mw'], '', size = (60, -1), style = wx.TE_READONLY)
        txt = wx.StaticText(parent, -1, 'MW :')
        txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(txt,0, wx.LEFT, 2)
        mwsizer.Add(VCmw, 1, wx.EXPAND)
        mwsizer.Add(txt2, 0, wx.LEFT, 1)


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
        sup_sizer.Add(sup_txt1, 0)
        sup_sizer.Add(sup_vc, 1, wx.EXPAND)
        sup_sizer.Add(sup_txt2, 0, wx.LEFT, 1)

        sup_sizer.Add(sup_txt5, 0, wx.LEFT, 10)
        sup_sizer.Add(sup_a, 1, wx.EXPAND)

        sup_sizer.Add(sup_txt3, 0)
        sup_sizer.Add(sup_qr, 1, wx.EXPAND)
        sup_sizer.Add(sup_txt4, 0, wx.LEFT, 1)

        sup_sizer.Add(sup_txt6, 0, wx.LEFT, 10)
        sup_sizer.Add(sup_b, 1, wx.EXPAND)

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
        
        VpMW = wx.TextCtrl(parent, vp_ids['calc_mw'], '', size = (60, -1), style = wx.TE_READONLY)
        txt = wx.StaticText(parent, -1, 'MW :')
        txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(txt,0, wx.LEFT, 2)
        mwsizer.Add(VpMW, 1, wx.EXPAND)
        mwsizer.Add(txt2, 0, wx.LEFT, 1)


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
        sup_sizer1.Add(sup_txt1, 0)
        sup_sizer1.Add(sup_vp, 1, wx.EXPAND)
        sup_sizer1.Add(sup_txt2, 0, wx.LEFT, 1)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt3, 0)
        sup_sizer2.Add(sup_vpc, 1, wx.EXPAND)
        sup_sizer2.Add(sup_txt4, 0, wx.LEFT, 1)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt5,0)
        sup_sizer3.Add(sup_density,1,wx.EXPAND)
        sup_sizer3.Add(sup_txt6,0, wx.LEFT, 1)

        self.vp_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vp_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, 5)
        self.vp_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, 5)
        self.vp_sup_sizer.Add(sup_sizer3,0)

        
        self.vp_top_sizer = wx.StaticBoxSizer(vpbox, wx.VERTICAL)
        self.vp_top_sizer.Add(mwsizer, 0, wx.BOTTOM, 5)
        self.vp_top_sizer.Add(self.vp_sup_sizer, 0, wx.BOTTOM, 5)
        self.vp_top_sizer.Add(vp_buttonsizer, 0, wx.ALIGN_CENTER | wx.TOP, 2)

        self.vp_top_sizer.Hide(self.vp_sup_sizer, recursive = True)

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

        concsizer.Add(conc_txt,0, wx.LEFT, 2)
        concsizer.Add(conc, 1, wx.EXPAND)
        concsizer.Add(conc_txt2, 0, wx.LEFT, 1)

        mwsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        absMW = wx.TextCtrl(parent, abs_ids['calc_mw'], '', size = (65, -1), style = wx.TE_READONLY)
        txt = wx.StaticText(parent, -1, 'MW :')
        txt2 = wx.StaticText(parent, -1,  'kDa')

        mwsizer.Add(txt,0, wx.LEFT, 2)
        mwsizer.Add(absMW, 1, wx.EXPAND)
        mwsizer.Add(txt2, 0, wx.LEFT, 1)


        sup_txt1 = wx.StaticText(parent, -1, '# electrons per mass dry macromolecule :')
        sup_txt2 = wx.StaticText(parent, -1, 'e-/g')
        sup_txt3 = wx.StaticText(parent, -1, '# electrons per volume of buffer :')
        sup_txt4 = wx.StaticText(parent, -1, 'e-/cm^3')
        sup_txt5 = wx.StaticText(parent, -1, 'Protein partial specific volume :')
        sup_txt6 = wx.StaticText(parent, -1, 'cm^3/g')
        sup_txt7 = wx.StaticText(parent, -1, 'Scattering length of an electron :')
        sup_txt8 = wx.StaticText(parent, -1, 'cm')
        sup_txt9 = wx.StaticText(parent, -1, 'Scattering contrast per mass :')
        sup_txt10 = wx.StaticText(parent, -1, 'e- cm/g')

        sup_pm = wx.TextCtrl(parent, abs_ids['sup_pm'], '', size = (65, -1), style = wx.TE_READONLY)
        sup_ps = wx.TextCtrl(parent, abs_ids['sup_ps'], '', size = (65, -1), style = wx.TE_READONLY)
        sup_pv = wx.TextCtrl(parent, abs_ids['sup_pv'], '', size = (65, -1), style = wx.TE_READONLY)
        sup_r0 = wx.TextCtrl(parent, abs_ids['sup_r0'], '', size = (65, -1), style = wx.TE_READONLY)
        sup_sc = wx.TextCtrl(parent, abs_ids['sup_sc'], '', size = (65, -1), style = wx.TE_READONLY)

        sup_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer1.Add(sup_txt1, 0)
        sup_sizer1.Add(sup_pm, 1, wx.EXPAND)
        sup_sizer1.Add(sup_txt2, 0, wx.LEFT, 1)

        sup_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer2.Add(sup_txt3, 0)
        sup_sizer2.Add(sup_ps, 1, wx.EXPAND)
        sup_sizer2.Add(sup_txt4, 0, wx.LEFT, 1)

        sup_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer3.Add(sup_txt5, 0)
        sup_sizer3.Add(sup_pv, 1, wx.EXPAND)
        sup_sizer3.Add(sup_txt6, 0, wx.LEFT, 1)

        sup_sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer4.Add(sup_txt7, 0)
        sup_sizer4.Add(sup_r0, 1, wx.EXPAND)
        sup_sizer4.Add(sup_txt8, 0, wx.LEFT, 1)

        sup_sizer5 = wx.BoxSizer(wx.HORIZONTAL)
        sup_sizer5.Add(sup_txt9, 0)
        sup_sizer5.Add(sup_sc, 1, wx.EXPAND)
        sup_sizer5.Add(sup_txt10, 0, wx.LEFT, 1)

        self.abs_sup_sizer = wx.BoxSizer(wx.VERTICAL)
        self.abs_sup_sizer.Add(sup_sizer1, 0, wx.BOTTOM, 5)
        self.abs_sup_sizer.Add(sup_sizer2, 0, wx.BOTTOM, 5)
        self.abs_sup_sizer.Add(sup_sizer3, 0, wx.BOTTOM, 5)
        self.abs_sup_sizer.Add(sup_sizer4, 0, wx.BOTTOM, 5)
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

        strconc = wx.FindWindowById(self.ids['conc']['conc']).GetValue()

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
                window = wx.FindWindowById(self.infodata[each_key][1])
                window.SetValue(guinier[each_key])

        if self.sasm.getAllParameters().has_key('Conc'):
            conc = str(self.sasm.getParameter('Conc'))
            wx.FindWindowById(self.ids['conc']['conc']).ChangeValue(conc)
            wx.FindWindowById(self.ids['abs']['conc']).ChangeValue(conc)
        
        self.calcMW()

    def updateMWInfo(self):
        analysis = self.sasm.getParameter('analysis')

        if self.raw_settings.get('NormAbsWater'):
            wx.FindWindowById(self.ids['abs']['calib']).SetValue(True)

        ref_mw = self.raw_settings.get('MWStandardMW') 
        ref_i0 = self.raw_settings.get('MWStandardI0')
        ref_conc = self.raw_settings.get('MWStandardConc')
        ref_file = self.raw_settings.get('MWStandardFile')

        if ref_mw > 0:
            wx.FindWindowById(self.ids['conc']['sup_mw']).ChangeValue(str(ref_mw))
        else:
            wx.FindWindowById(self.ids['conc']['sup_mw']).ChangeValue('')
        if ref_i0 > 0:
            wx.FindWindowById(self.ids['conc']['sup_i0']).ChangeValue(str(ref_i0))
        else:
            wx.FindWindowById(self.ids['conc']['sup_i0']).ChangeValue('')
        if ref_conc > 0:
            wx.FindWindowById(self.ids['conc']['sup_conc']).ChangeValue(str(ref_conc))
        else:
            wx.FindWindowById(self.ids['conc']['sup_conc']).ChangeValue('')
        wx.FindWindowById(self.ids['conc']['sup_file']).ChangeValue(ref_file)


        #Initialize VC MW settings
        aCtrl = wx.FindWindowById(self.ids['VC']['sup_a'])
        bCtrl = wx.FindWindowById(self.ids['VC']['sup_b'])
        molCtrl = wx.FindWindowById(self.ids['VC']['mol_type'])

        vc_type = molCtrl.GetStringSelection()

        if vc_type == 'Protein':
            aval = self.raw_settings.get('MWVcAProtein')
            bval = self.raw_settings.get('MWVcBProtein')
        else:
            aval = self.raw_settings.get('MWVcARna')
            bval = self.raw_settings.get('MWVcBRna')

        aCtrl.SetValue(str(aval))
        bCtrl.SetValue(str(bval))
        molCtrl.SetStringSelection(vc_type)

        #Initialize Vp MW settings
        vp_rho = self.raw_settings.get('MWVpRho')

        wx.FindWindowById(self.ids['VP']['sup_density']).ChangeValue(str(vp_rho))


        #Initialize Absolute scattering MW settings.
        rho_Mprot = self.raw_settings.get('MWAbsRhoMprot') # electrons per dry mass of protein
        rho_solv = self.raw_settings.get('MWAbsRhoSolv') # electrons per volume of aqueous solvent
        nu_bar = self.raw_settings.get('MWAbsNuBar') # partial specific volume of the protein
        r0 = self.raw_settings.get('MWAbsR0') #scattering lenght of an electron
        d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
        wx.FindWindowById(self.ids['abs']['sup_pm']).ChangeValue('%.2E' %(rho_Mprot))
        wx.FindWindowById(self.ids['abs']['sup_ps']).ChangeValue('%.2E' %(rho_solv))
        wx.FindWindowById(self.ids['abs']['sup_pv']).ChangeValue('%.4f' %(nu_bar))
        wx.FindWindowById(self.ids['abs']['sup_r0']).ChangeValue('%.2E' %(r0))
        wx.FindWindowById(self.ids['abs']['sup_sc']).ChangeValue('%.2E' %(d_rho))


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
                  "This method can yield inaccurate results if the reference is not properly calibrated, I(0) is not "
                  "well estimated from the Guinier fit, or the contrast between the macromolecule and buffer is "
                  "significantly different between the reference and sample.")
        elif evt_id == self.ids['VC']['info']:
            msg = ("This method uses the approach described in: Rambo, R. P. & Tainer, J. A. (2013). Nature. "
                   "496, 477-481. First, the volume of correlation, Vc, is calculated. Unlike the Porod volume, "
                   "Vc is expected to converge for both compact and flexible macromolecules. Physically, Vc can "
                   "be interpreted as the particle volume per self-correlation length, and has units of A^2. "
                   "Vc and the radius of gyration, Rg, are then used to calculate a parameter Qr = Vc^2/Rg. "
                   "The molecular weight is then calculated as:\n\n"
                   "MW = (Qr/b)^(a)\n\n"
                   "where a and b are empirically determined constants that depend upon the type of macromolecule. "
                   "More details on the calculation are in the reference. The authors claim the error in MW "
                   "determination is ~5-10%\n\n"
                   "This method can yield inaccurate results if the integral of q*I(q) doesn't converge, which "
                   "may indicate the scattering profile is not measured to high enough q or that there is a bad "
                   "buffer match. It also requires accurate determination of I(0) and Rg. It doesn't work for "
                   "protein-nucleic acid complexes.")
        elif evt_id == self.ids['VP']['info']:
            msg = ("This method uses the approach described in: Fischer, H., de Oliveira Neto, M., Napolitano, "
                  "H. B., Polikarpov, I., & Craievich, A. F. (2009). J. Appl. Crystallogr. 43, 101-109. First, "
                  "the Porod volume, Vp, is determined. True determination of the Porod volume requires the "
                  "scattering profile measured to infinite q. A correction is applied to Vp to account "
                  "for the limited range of the measurement. The authors report a maximum of 10% uncertainty "
                  "for calculated molecular weight from globular proteins.\n\n"
                  "This method can yield inaccurate results if the molecule is not globular. It requires accurate "
                  "determination of I(0). It also requires an accurate protein density. It only works for "
                  "proteins.\n\n"
                  "Note: To do the integration, RAW extrapolates the scattering profile to I(0) using the Guinier fit. "
                  "The authors of the original paper used smoothed and extrapolated scattering profiles generated by "
                  "GNOM. This may cause discrepancy. To use this method on GNOM profiles, use the online SAXS MoW "
                  "calculator located at: http://www.if.sc.usp.br/~saxs/")
        else:
            msg = ("This uses the absolute calibration of the scattering profile to determine the molecular weight, "
                   "as described in Orthaber, D., Bergmann, A., & Glatter, O. (2000). J. Appl. Crystallogr. 33, "
                   "218-225. By determining the absolute scattering at I(0), if the sample concentration is also "
                   "known, the molecular weight is calculated as:\n\n"
                   "MW = (N_A * I(0) / c)/(drho_M^2)\n\n"
                   "where N_A is the Avagadro number, c is the concentration, and drho_M is the scattering contrast "
                   "per mass. The accuracy of this method was assessed in Mylonas, E. & Svergun, D. I. (2007). "
                   "J. Appl. Crystallogr. 40, s245-s249, and for most proteins is <~10%.\n\n"
                   "This method can yield inaccurate results if the absolute calibration is off, or if the "
                   "partial specific volume of the macromolecule in solution is incorrect. I(0) and the concentration "
                   "in solution must be well determined. Unless the scattering contrast is adjusted, this method "
                   "will only work for proteins.")

        dlg = wx.MessageDialog(self, msg, "Calculating Molecular Weight", style = wx.ICON_INFORMATION | wx.OK)
        proceed = dlg.ShowModal()
        dlg.Destroy()

    def _onMore(self, evt):
        evt_id = evt.GetId()

        if evt_id == self.ids['conc']['more']:
            if self.conc_top_sizer.IsShown(self.conc_sup_sizer):
                self.conc_top_sizer.Hide(self.conc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['conc']['more'])
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.conc_top_sizer.Show(self.conc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['conc']['more'])
                button.SetLabel('Hide Details')
                self.panel.Layout()
           
        elif evt_id == self.ids['VC']['more']:
            if self.vc_top_sizer.IsShown(self.vc_sup_sizer):
                self.vc_top_sizer.Hide(self.vc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VC']['more'])
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.vc_top_sizer.Show(self.vc_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VC']['more'])
                button.SetLabel('Hide Details')
                self.panel.Layout()

        elif evt_id == self.ids['VP']['more']:
            if self.vp_top_sizer.IsShown(self.vp_sup_sizer):
                self.vp_top_sizer.Hide(self.vp_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VP']['more'])
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.vp_top_sizer.Show(self.vp_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['VP']['more'])
                button.SetLabel('Hide Details')
                self.panel.Layout()
        else:
            if self.abs_top_sizer.IsShown(self.abs_sup_sizer):
                self.abs_top_sizer.Hide(self.abs_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['abs']['more'])
                button.SetLabel('Show Details')
                self.panel.Layout()
            else:
                self.abs_top_sizer.Show(self.abs_sup_sizer,recursive=True)
                button = wx.FindWindowById(self.ids['abs']['more'])
                button.SetLabel('Hide Details')
                self.panel.Layout()


    def _onMoleculeChoice(self,evt):
        vc_ids = self.ids['VC']

        aCtrl = wx.FindWindowById(vc_ids['sup_a'])
        bCtrl = wx.FindWindowById(vc_ids['sup_b'])

        molCtrl = evt.GetEventObject()
        val = molCtrl.GetStringSelection()

        if val == 'Protein':
            aval = self.raw_settings.get('MWVcAProtein')
            bval = self.raw_settings.get('MWVcBProtein')
        else:
            aval = self.raw_settings.get('MWVcARna')
            bval = self.raw_settings.get('MWVcBRna')

        aCtrl.SetValue(str(aval))
        bCtrl.SetValue(str(bval))

        self.calcVCMW()

    def _onUpdateConc(self, evt):
        evt_id = evt.GetId()

        concCtrl = evt.GetEventObject()
        val = concCtrl.GetValue()

        if evt_id == self.ids['conc']['conc']:
            wx.FindWindowById(self.ids['abs']['conc']).ChangeValue(val)
        else:
            wx.FindWindowById(self.ids['conc']['conc']).ChangeValue(val)

        self.calcConcMW()
        self.calcAbsMW()

    def _onUpdateDensity(self, evt):
        self.calcVpMW()

    def _onAbsCheck(self, evt):
        chkbox = evt.GetEventObject()

        if chkbox.GetValue():
            wx.FindWindowById(self.ids['abs']['conc']).Enable()
            self.calcAbsMW()
        else:
            wx.FindWindowById(self.ids['abs']['conc']).Disable()
            wx.FindWindowById(self.ids['abs']['calc_mw']).ChangeValue('')

    def onChangeParams(self, evt):

        self.main_frame.showOptionsDialog(focusHead='Molecular Weight')

    def onCloseButton(self, evt):
        self.OnClose()

    def onSaveInfo(self, evt):
        calcData = {'I(0)Concentration'  : {},
                    'VolumeOfCorrelation': {},
                    'PorodVolume'        : {},
                    'Absolute'           : {}}

        for eachKey in self.ids.iterkeys():
            mw = wx.FindWindowById(self.ids[eachKey]['calc_mw']).GetValue()

            if eachKey == 'conc':
                calcData['I(0)Concentration']['MW'] = mw
                self.sasm.setParameter('MW', mw)

            elif eachKey == 'VC':
                mol_type = wx.FindWindowById(self.ids[eachKey]['mol_type']).GetStringSelection()
                vcor = wx.FindWindowById(self.ids[eachKey]['sup_vc']).GetValue()

                calcData['VolumeOfCorrelation']['MW'] = mw
                calcData['VolumeOfCorrelation']['Type'] = mol_type
                calcData['VolumeOfCorrelation']['Vcor'] = vcor

            elif eachKey == 'VP':
                vporod = wx.FindWindowById(self.ids[eachKey]['sup_vp']).GetValue()
                vpcor = wx.FindWindowById(self.ids[eachKey]['sup_vpc']).GetValue()

                calcData['PorodVolume']['MW'] = mw
                calcData['PorodVolume']['VPorod'] = vporod
                calcData['PorodVolume']['VPorod_Corrected'] = vpcor

            elif eachKey == 'abs':
                calcData['Absolute']['MW'] = mw

        analysis_dict = self.sasm.getParameter('analysis')
        analysis_dict['molecularWeight'] = calcData

        strconc = wx.FindWindowById(self.ids['conc']['conc']).GetValue()

        try:
            conc = float(strconc)
        except ValueError:
            conc = -1

        if strconc != '' and conc > 0:
            self.sasm.setParameter('Conc', conc)

        if self.manip_item != None:
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
        i0 = float(wx.FindWindowById(self.infodata['I0'][1]).GetValue())

        ref_mw = self.raw_settings.get('MWStandardMW') 
        ref_I0 = self.raw_settings.get('MWStandardI0')
        ref_conc = self.raw_settings.get('MWStandardConc')
        
        try:
            conc = float(wx.FindWindowById(conc_ids['conc']).GetValue())
        except ValueError:
            conc = -1
        
        if ref_mw > 0 and ref_I0 > 0 and ref_conc > 0 and conc > 0 and i0 > 0:
            mw = (i0 * (ref_mw/(ref_I0/ref_conc))) / conc

            mwstr = str(np.around(mw,1))

            if len(mwstr.split('.')[1])>1:
                mwstr = '%.1E' %(mw)

            mwCtrl = wx.FindWindowById(conc_ids['calc_mw'])
            mwCtrl.SetValue(mwstr)

    def calcVCMW(self):

        vc_ids = self.ids['VC']
        rg = float(wx.FindWindowById(self.infodata['Rg'][1]).GetValue())
        i0 = float(wx.FindWindowById(self.infodata['I0'][1]).GetValue())

        molecule = wx.FindWindowById(vc_ids['mol_type']).GetStringSelection()

        if molecule == 'Protein':
            is_protein = True
        else:
            is_protein = False

        if rg > 0 and i0 > 0:
            mw, mw_error, tot, vc, qr = SASCalc.autoMW(self.sasm, rg, i0, is_protein)

            mwstr = str(np.around(mw,1))

            if len(mwstr.split('.')[1])>1:
                mwstr = '%.1E' %(mw)

            mwCtrl = wx.FindWindowById(vc_ids['calc_mw'])
            mwCtrl.SetValue(mwstr)


            vcstr = str(np.around(vc,1))

            if len(vcstr.split('.')[1])>1:
                vcstr = '%.1E' %(vc)

            wx.FindWindowById(vc_ids['sup_vc']).SetValue(vcstr)


            qrstr = str(np.around(qr,1))

            if len(qrstr.split('.')[1])>1:
                qrstr = '%.1E' %(qr)

            wx.FindWindowById(vc_ids['sup_qr']).SetValue(qrstr)
    
    def calcVpMW(self):
        #This is calculated using the method in Fischer et al. J. App. Crys. 2009

        vp_ids = self.ids['VP']

        rg = float(wx.FindWindowById(self.infodata['Rg'][1]).GetValue())
        i0 = float(wx.FindWindowById(self.infodata['I0'][1]).GetValue())

        q = self.sasm.q
        i = self.sasm.i
        # print q[-1]
        
        #These functions are used to correct the porod volume for the length of the q vector
        qA=[0.15, 0.19954, 0.25092, 0.30046, 0.40046, 0.45092]
        AA=[ -9921.6416, -7597.0151, -6865.6719, -5951.4927, -4645.5225, -3783.582]
        qB=[0.14908, 0.19969, 0.24939, 0.3, 0.40031, 0.45]
        BB=[0.57561, 0.61341, 0.65, 0.68415, 0.77073, 0.8561]

        fA=interp.interp1d(qA,AA)
        fB=interp.interp1d(qB,BB)

        if q[-1] < 0.45092:
            A=fA(q[-1])
            B=fB(q[-1])
        
        if i0 > 0:
            #Calculate the Porod Volume
            pVolume = SASCalc.porodVolume(self.sasm, rg, i0, True)

            #Correct for the length of the q vector
            if q[-1]<0.45092:
                pv_cor=(A+B*pVolume)
            else:
                pv_cor = pVolume

            #Get the input average protein density in solution (to be implimented in the show more)
            #0.83*10**(-3) is the average density of protein in solution in kDa/A^3
            density = self.raw_settings.get('MWVpRho')

            mw = pv_cor*density

            mwstr = str(np.around(mw,1))

            if len(mwstr.split('.')[1])>1:
                mwstr = '%.1E' %(mw)

            mwCtrl = wx.FindWindowById(vp_ids['calc_mw'])
            mwCtrl.SetValue(mwstr)

            vpstr = str(np.around(pVolume,1))

            if len(vpstr.split('.')[1])>1:
                vpstr = '%.1E' %(pVolume)

            vpCtrl = wx.FindWindowById(vp_ids['sup_vp'])
            vpCtrl.SetValue(vpstr)

            vpcstr = str(np.around(pv_cor,1))

            if len(vpcstr.split('.')[1])>1:
                vpcstr = '%.1E' %(pv_cor)

            pvcCtrl = wx.FindWindowById(vp_ids['sup_vpc'])
            pvcCtrl.SetValue(vpcstr)



    def calcAbsMW(self):
        try:
            abs_ids = self.ids['abs']
            i0 = float(wx.FindWindowById(self.infodata['I0'][1]).GetValue())

            #Default values from Mylonas & Svergun, J. App. Crys. 2007.
            rho_Mprot = self.raw_settings.get('MWAbsRhoMprot') #e-/g, # electrons per dry mass of protein
            rho_solv = self.raw_settings.get('MWAbsRhoSolv') #e-/cm^-3, # electrons per volume of aqueous solvent
            nu_bar = self.raw_settings.get('MWAbsNuBar') #cm^3/g, # partial specific volume of the protein
            r0 = self.raw_settings.get('MWAbsR0') #cm, scattering lenght of an electron
            
            try:
                conc = float(wx.FindWindowById(abs_ids['conc']).GetValue())
            except ValueError:
                conc = -1
            
            if conc > 0 and i0 > 0 and wx.FindWindowById(abs_ids['calib']).GetValue():
                d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
                mw = (Avogadro*i0/conc)/np.square(d_rho)

                mwstr = str(np.around(mw,1))

                if len(mwstr.split('.')[1])>1 or len(mwstr.split('.')[0])>4:
                    mwstr = '%.2E' %(mw)

                mwCtrl = wx.FindWindowById(abs_ids['calc_mw'])
                mwCtrl.SetValue(mwstr)
        except Exception, e:
            print e

        
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
        
        # Connect the callback for the draw_event so that window resizing works:
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw) 

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''
        
        a = self.subplots['VC']
       
        self.background = self.canvas.copy_from_bbox(a.bbox)
        
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(self.orig_i, self.orig_q)
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        
    def _calcInt(self):
        ''' calculate pointwise integral '''
 
        q_roi = self.orig_q
        i_roi = self.orig_i

        y = np.zeros_like(q_roi, dtype = float)

        for a in range(2,len(q_roi)+1):
            y[a-1] = integrate.simps(q_roi[:a]*i_roi[:a],q_roi[:a])
        
        return q_roi, y
        
    def plotSASM(self, sasm):
        #Disconnect draw_event to avoid ax_redraw on self.canvas.draw()
        self.canvas.mpl_disconnect(self.cid)
        self.updateDataPlot(sasm.i, sasm.q)
        
        #Reconnect draw_event
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def updateDataPlot(self, i, q):
        #Save for resizing:
        self.orig_i = i
        self.orig_q = q
            
        a = self.subplots['VC']
        
        try:
            x, y = self._calcInt()
        except TypeError:
            return
                                                      
        if not self.data_line:
            self.data_line, = a.plot(x, y, 'r.')
            
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(a.bbox)
        else:          
            self.data_line.set_ydata(y)
            self.data_line.set_xdata(x)

        a_oldx = a.get_xlim()
        a_oldy = a.get_ylim()

        a.relim()
        a.autoscale_view()

        a_newx = a.get_xlim()
        a_newy = a.get_ylim()

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

            SASFileIO.saveMeasurement(save_sasm, path, self._raw_settings, filetype = '.dat')
            
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
                    init_iftm = SASCalc.runGnom(savename, outname, dmax, self.controlPanel.gnom_settings)
                except SASExceptions.NoATSASError as e:
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

        qrange = sasm.getQrange()

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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
        
        if self.ift != None:
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
                                                      
        controlPanel = wx.FindWindowByName('GNOMControlPanel')
        
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

        # if  np.all(p>=0):
        #     a.set_ylim(bottom = p.min())

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
                                'rmin'          : self.raw_settings.get('gnomRmin')
                                }

        self.out_list = {}


        self.spinctrlIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId(),
                            'dmax'   : wx.NewId()}
        
        self.staticTxtIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}


        self.infodata = {'guinierI0' : ('I0 :', wx.NewId(), wx.NewId()),
                         'guinierRg' : ('Rg :', wx.NewId(), wx.NewId()),
                         'gnomI0'    : ('I0 :', wx.NewId(), wx.NewId()),
                         'gnomRg'    : ('Rg :', wx.NewId(), wx.NewId()),
                         'TE': ('Total Estimate :', wx.NewId()),
                         'gnomQuality': ('GNOM says :', wx.NewId()),
                         'chisq': ('chi^2 (fit) :', wx.NewId())
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
        boxSizer.Add(infoSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP ,5)
        
        
        bsizer = wx.BoxSizer(wx.VERTICAL)
        bsizer.Add(self.createFileInfo(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bsizer.AddStretchSpacer(1)
        bsizer.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
         
        self.SetSizer(bsizer)
        

    def initDatgnomValues(self, sasm, iftm):
        self.setSpinLimits(sasm)

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'])
        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1])
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1])

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

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'])
        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1])
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1])
        
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
        txt = wx.FindWindowById(self.staticTxtIDs['qend'])
        txt.SetValue(str(round(sasm.q[new_nmax],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
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
        gnomRgWindow = wx.FindWindowById(self.infodata['gnomRg'][1])
        gnomI0Window = wx.FindWindowById(self.infodata['gnomI0'][1])
        gnomTEWindow = wx.FindWindowById(self.infodata['TE'][1])
        gnomQualityWindow = wx.FindWindowById(self.infodata['gnomQuality'][1])
        gnomChisqWindow = wx.FindWindowById(self.infodata['chisq'][1])

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

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'])
        dmax = str(dmaxWindow.GetValue())

        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'])
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'])
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

        if self.manip_item != None:
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

        SASFileIO.saveMeasurement(save_sasm, path, self.raw_settings, filetype = '.dat')
        
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

        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'])

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
        
        sizer.Add(wx.StaticText(self,-1,'q_min'),1, wx.LEFT, 5)
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
        sizer.Add(self.endSpin, 0, wx.EXPAND | wx.RIGHT, 5)


        dmax_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.dmaxSpin = RAWCustomCtrl.IntSpinCtrl(self, self.spinctrlIDs['dmax'], size = (60,-1), min = 1)

        self.dmaxSpin.SetValue(0)
        self.dmaxSpin.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.onSpinCtrl)
        self.dmaxSpin.Bind(wx.EVT_TEXT, self.onDmaxText)

        dmax_sizer.Add(wx.StaticText(self, -1, 'Dmax :'), 0, wx.TOP | wx.BOTTOM | wx.RIGHT, 5)
        dmax_sizer.Add(self.dmaxSpin, 0, wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT, 5)


        advancedParams = wx.Button(self, -1, 'Change Advanced Parameters')
        advancedParams.Bind(wx.EVT_BUTTON, self.onChangeParams)

        datgnom = wx.Button(self, -1, 'DATGNOM')
        datgnom.Bind(wx.EVT_BUTTON, self.onDatgnomButton)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(sizer, 0, wx.EXPAND)
        top_sizer.Add(dmax_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        top_sizer.Add(advancedParams, 0, wx.CENTER | wx.BOTTOM, 10)
        top_sizer.Add(datgnom, 0, wx.CENTER | wx.BOTTOM, 10)

        
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
        ly = self.sasm.i
        
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
                txt.SetValue(str(round(self.sasm.q[idx],5)))
                return
            
            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'])
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.sasm.q[idx],5)))
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
                
        txtctrl.SetValue(str(round(self.sasm.q[int(i)],5)))


        self.out_list = {}
        
        wx.CallAfter(self.updatePlot)
        
    def setSpinLimits(self, sasm):
        self.startSpin.SetRange((0, len(sasm.q)-1))
        self.endSpin.SetRange((0, len(sasm.q)-1))
        
        self.endSpin.SetValue(len(sasm.q)-1)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'])
        txt.SetValue(str(round(sasm.q[int(len(sasm.q)-1)],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
        txt.SetValue(str(round(sasm.q[0],4)))

        
    def onSpinCtrl(self, evt):

        id = evt.GetId()

        if id != self.spinctrlIDs['dmax']:
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
                    
            txt.SetValue(str(round(self.sasm.q[int(i)],5)))

            self.out_list = {}

        #Important, since it's a slow function to update (could do it in a timer instead) otherwise this spin event might loop!
        wx.CallAfter(self.updatePlot)

        
    def updatePlot(self):
        dmaxWindow = wx.FindWindowById(self.spinctrlIDs['dmax'])
        dmax = dmaxWindow.GetValue()

        if dmax not in self.out_list:
            self.calcGNOM(dmax)

        self.updateGNOMInfo(self.out_list[str(dmax)])

        plotpanel = wx.FindWindowByName('GNOMPlotPanel')

        dmax_window = wx.FindWindowById(self.spinctrlIDs['dmax'])
        dmax = str(dmax_window.GetValue())
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i = int(spinstart.GetValue())
        
        i2 = int(spinend.GetValue())
        
        xlim = [i,i2]

        q = self.sasm.q
        i = self.sasm.i
        err = self.sasm.err
        
        r = self.out_list[dmax].r
        p = self.out_list[dmax].p
        perr = self.out_list[dmax].err
        qexp = self.out_list[dmax].q_orig
        jreg = self.out_list[dmax].i_fit


        # plotpanel.updateDataPlot(q, i, err, r, p, perr, qexp, jreg, xlim)
        plotpanel.plotPr(self.out_list[dmax])


    def calcGNOM(self, dmax):
        startSpin = wx.FindWindowById(self.spinctrlIDs['qstart'])
        endSpin = wx.FindWindowById(self.spinctrlIDs['qend'])

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


        SASFileIO.saveMeasurement(save_sasm, path, self.raw_settings, filetype = '.dat')
        

        os.chdir(path)
        try:
            iftm = SASCalc.runGnom(savename, outname, dmax, self.gnom_settings)
        except SASExceptions.NoATSASError as e:
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


    def updateGNOMSettings(self):
        self.old_settings = copy.deepcopy(self.gnom_settings)

        self.gnom_settings = {  'expert'        : self.raw_settings.get('gnomExpertFile'),
                                'rmin_zero'     : self.raw_settings.get('gnomForceRminZero'),
                                'rmax_zero'     : self.raw_settings.get('gnomForceRmaxZero'),
                                'npts'          : self.raw_settings.get('gnomNPoints'),
                                'alpha'         : self.raw_settings.get('gnomInitialAlpha'),
                                'angular'       : self.raw_settings.get('gnomAngularScale'),
                                'system'        : self.raw_settings.get('gnomSystem'),
                                'form'          : self.raw_settings.get('gnomFormFactor'),
                                'radius56'      : self.raw_settings.get('gnomRadius56'),
                                'rmin'          : self.raw_settings.get('gnomRmin')
                                }

        if self.old_settings != self.gnom_settings:
            self.out_list = {}

        self.updatePlot()


    def onChangeParams(self, evt):
        self.main_frame.showOptionsDialog(focusHead='GNOM')


class DammifFrame(wx.Frame):
    
    def __init__(self, parent, title, iftm, manip_item):
        
        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'DammifFrame', size = (675,700))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'DammifFrame', size = (675,700))

        self.panel = wx.Panel(self, -1, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.manip_item = manip_item

        self.iftm = iftm

        self.ift = iftm.getParameter('out')

        self.filename = iftm.getParameter('filename')

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.infodata = {}

        self.ids = {'runs'          : wx.NewId(),
                    'procs'         : wx.NewId(),
                    'mode'          : wx.NewId(),
                    'sym'           : wx.NewId(),
                    'anisometry'    : wx.NewId(),
                    'status'        : wx.NewId(),
                    'damaver'       : wx.NewId(),
                    'damclust'      : wx.NewId(),
                    'save'          : wx.NewId(),
                    'prefix'        : wx.NewId(),
                    'logbook'       : wx.NewId(),
                    'start'         : wx.NewId(),
                    'abort'         : wx.NewId(),
                    'changedir'     : wx.NewId()
                    }

        self.threads = []


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

        # file_text = wx.StaticText(parent, -1, 'File :')
        # file_ctrl = wx.TextCtrl(parent, -1, self.filename, size = (150, -1), style = wx.TE_READONLY)

        # file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # file_sizer.Add(file_text, 0, wx.ALL, 5)
        # file_sizer.Add(file_ctrl, 2, wx.ALL | wx.EXPAND, 5)
        # file_sizer.AddStretchSpacer(1)

        
        
        file_ctrl = wx.TextCtrl(parent, -1, self.filename, size = (150, -1), style = wx.TE_READONLY)
        
        file_box = wx.StaticBox(parent, -1, 'Filename')
        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        file_sizer.Add(file_ctrl, 2, wx.ALL | wx.EXPAND, 5)
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
        savedir_sizer.Add(savedir_text, 0, wx.ALL, 5)
        savedir_sizer.Add(savedir_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        savedir_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)


        prefix_text = wx.StaticText(parent, -1, 'Output prefix :')
        prefix_ctrl = wx.TextCtrl(parent, self.ids['prefix'], '', size = (150, -1))

        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(prefix_text, 0, wx.ALL, 5)
        prefix_sizer.Add(prefix_ctrl, 1, wx.ALL, 5)
        prefix_sizer.AddStretchSpacer(1)
        

        nruns_text = wx.StaticText(parent, -1, 'Number of reconstructions :')
        nruns_ctrl = wx.TextCtrl(parent, self.ids['runs'], '', size = (60, -1))
        nruns_ctrl.Bind(wx.EVT_TEXT, self.onRunsText)

        nruns_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nruns_sizer.Add(nruns_text, 0, wx.ALL, 5)
        nruns_sizer.Add(nruns_ctrl, 0, wx.ALL, 5)


        nprocs = multiprocessing.cpu_count()
        nprocs_choices = [str(i) for i in range(nprocs, 0, -1)]
        nprocs_text = wx.StaticText(parent, -1, 'Number of simultaneous runs :')
        nprocs_choice = wx.Choice(parent, self.ids['procs'], choices = nprocs_choices)

        nprocs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        nprocs_sizer.Add(nprocs_text, 0, wx.ALL, 5)
        nprocs_sizer.Add(nprocs_choice, 0, wx.ALL, 5)


        mode_text = wx.StaticText(parent, -1, 'Mode :')
        mode_choice = wx.Choice(parent, self.ids['mode'], choices = ['Fast', 'Slow', 'Custom'])

        # mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # mode_sizer.Add(mode_text, 0, wx.ALL, 5)
        # mode_sizer.Add(mode_choice, 0, wx.ALL, 5)


        sym_choices = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 'P11',
                        'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18', 'P19', 'P22', 'P222',
                        'P32', 'P42', 'P52', 'P62', 'P72', 'P82', 'P92', 'P102', 'P112', 'P122']

        sym_text = wx.StaticText(parent, -1, 'Symmetry :')
        sym_choice = wx.Choice(parent, self.ids['sym'], choices = sym_choices)

        # sym_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # sym_sizer.Add(sym_text, 0, wx.ALL, 5)
        # sym_sizer.Add(sym_choice, 0, wx.ALL, 5)


        anisometry_choices = ['Unknown', 'Prolate', 'Oblate']
        aniso_text = wx.StaticText(parent, -1, 'Anisometry :')
        aniso_choice = wx.Choice(parent, self.ids['anisometry'], choices = anisometry_choices)

        # aniso_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # aniso_sizer.Add(aniso_text, 0, wx.ALL, 5)
        # aniso_sizer.Add(aniso_choice, 0, wx.ALL, 5)


        choices_sizer = wx.FlexGridSizer(2, 3, 5, 10)
        choices_sizer.SetFlexibleDirection(wx.HORIZONTAL)
        choices_sizer.AddGrowableCol(0)
        choices_sizer.AddGrowableCol(1)
        choices_sizer.AddGrowableCol(2)

        choices_sizer.Add(mode_text)
        choices_sizer.Add(sym_text)
        choices_sizer.Add(aniso_text)

        choices_sizer.Add(mode_choice)
        choices_sizer.Add(sym_choice)
        choices_sizer.Add(aniso_choice)

        damaver_chk = wx.CheckBox(parent, self.ids['damaver'], 'Align and average envelopes (damaver)')
        damaver_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        damclust_chk = wx.CheckBox(parent, self.ids['damclust'], 'Align and cluster envelopes (damclust)')
        damclust_chk.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

        advancedButton = wx.Button(parent, -1, 'Change Advanced Settings')
        advancedButton.Bind(wx.EVT_BUTTON, self._onAdvancedButton)


        settings_box = wx.StaticBox(parent, -1, 'Settings')
        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        settings_sizer.Add(savedir_sizer, 0, wx.EXPAND)
        # settings_sizer.Add(savedir_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        settings_sizer.Add(prefix_sizer, 0, wx.EXPAND)
        settings_sizer.Add(nruns_sizer, 0)
        settings_sizer.Add(nprocs_sizer, 0)
        # settings_sizer.Add(mode_sizer, 0)
        # settings_sizer.Add(sym_sizer, 0)
        # settings_sizer.Add(aniso_sizer, 0)
        settings_sizer.Add(choices_sizer, 0, wx.ALL | wx.EXPAND, 5)
        settings_sizer.Add(damaver_chk, 0, wx.ALL, 5)
        settings_sizer.Add(damclust_chk, 0, wx.ALL, 5)
        settings_sizer.Add(advancedButton, 0, wx.ALL | wx.ALIGN_CENTER, 5)


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


        close_button = wx.Button(parent, -1, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self._onCloseButton)

        info_button = wx.Button(parent, -1, 'How To Cite')
        info_button.Bind(wx.EVT_BUTTON, self._onInfoButton)

        button_sizer =  wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(info_button, 0, wx.RIGHT, 5)
        button_sizer.Add(close_button, 0)


        if int(wx.__version__.split('.')[1])<9 and int(wx.__version__.split('.')[0]) == 2:     #compatability for older versions of wxpython
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            top_sizer.Add(half_sizer, 0, wx.EXPAND)
            top_sizer.Add(log_sizer, 1, wx.EXPAND)
            top_sizer.Add(close_button, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        else:
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            top_sizer.Add(half_sizer, 1, wx.EXPAND)
            top_sizer.Add(log_sizer, 1, wx.EXPAND)
            top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 5)


        self.dammif_timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self.onDammifTimer, self.dammif_timer)


        return top_sizer


    def _initSettings(self):
        self.dammif_settings = {'mode'          : self.raw_settings.get('dammifMode'),
                                'unit'          : self.raw_settings.get('dammifUnit'),
                                'sym'           : self.raw_settings.get('dammifSymmetry'),
                                'anisometry'    : self.raw_settings.get('dammifAnisometry'),
                                'omitSolvent'   : self.raw_settings.get('dammifOmitSolvent'),
                                'chained'       : self.raw_settings.get('dammifChained'),
                                'constant'      : self.raw_settings.get('dammifConstant'),
                                'maxBead'       : self.raw_settings.get('dammifMaxBeadCount'),
                                'radius'        : self.raw_settings.get('dammifDummyRadius'),
                                'harmonics'     : self.raw_settings.get('dammifSH'),
                                'propFit'       : self.raw_settings.get('dammifPropToFit'),
                                'curveWeight'   : self.raw_settings.get('dammifCurveWeight'),
                                'seed'          : self.raw_settings.get('dammifRandomSeed'),
                                'maxSteps'      : self.raw_settings.get('dammifMaxSteps'),
                                'maxIters'      : self.raw_settings.get('dammifMaxIters'),
                                'maxSuccess'    : self.raw_settings.get('dammifMaxStepSuccess'),
                                'minSuccess'    : self.raw_settings.get('dammifMinStepSuccess'),
                                'TFactor'       : self.raw_settings.get('dammifTFactor'),
                                'RgWeight'      : self.raw_settings.get('dammifRgPen'),
                                'cenWeight'     : self.raw_settings.get('dammifCenPen'),
                                'looseWeight'   : self.raw_settings.get('dammifLoosePen')
                                }

        mode = wx.FindWindowById(self.ids['mode'])
        mode.SetStringSelection(self.dammif_settings['mode'])

        sym = wx.FindWindowById(self.ids['sym'])
        sym.SetStringSelection(self.dammif_settings['sym'])

        anisometry = wx.FindWindowById(self.ids['anisometry'])
        anisometry.SetStringSelection(self.dammif_settings['anisometry'])

        procs = wx.FindWindowById(self.ids['procs'])
        if multiprocessing.cpu_count() > 1:
            procs.SetSelection(1)
        else:
            procs.SetSelection(0)

        damaver = wx.FindWindowById(self.ids['damaver'])
        damaver.SetValue(self.raw_settings.get('dammifDamaver'))

        damclust = wx.FindWindowById(self.ids['damclust'])
        damclust.SetValue(self.raw_settings.get('dammifDamclust'))

        prefix = wx.FindWindowById(self.ids['prefix'])
        prefix.SetValue(os.path.splitext(self.filename)[0])

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        save = wx.FindWindowById(self.ids['save'])
        save.SetValue(path)

        nruns = wx.FindWindowById(self.ids['runs'])
        nruns.SetValue(str(self.raw_settings.get('dammifReconstruct')))

        abort_button = wx.FindWindowById(self.ids['abort']).Disable()


    def onStartButton(self, evt):
        #Set the dammif settings
        self.setArgs()

        #Get user settings on number of runs, save location, etc
        damaver_window = wx.FindWindowById(self.ids['damaver'])
        damaver = damaver_window.GetValue()

        damclust_window = wx.FindWindowById(self.ids['damclust'])
        damclust = damclust_window.GetValue()

        prefix_window = wx.FindWindowById(self.ids['prefix'])
        prefix = prefix_window.GetValue()

        path_window = wx.FindWindowById(self.ids['save'])
        path = path_window.GetValue()

        procs_window = wx.FindWindowById(self.ids['procs'])
        procs = int(procs_window.GetStringSelection())

        nruns_window = wx.FindWindowById(self.ids['runs'])
        nruns = int(nruns_window.GetValue())

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
                    f = open(outname, 'w')

                    for line in self.ift:
                        f.write(line)

                    f.close()
                else:
                    return
        else:
            f = open(outname, 'w')

            for line in self.ift:
                f.write(line)

            f.close()

        dammif_names = {key: value for (key, value) in [(str(i), prefix+'_%s' %(str(i).zfill(2))) for i in range(1, nruns+1)]}

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
                question = 'Warning: selected directory contains DAMMIF output files with the prefix\n"%s". Running DAMMIF will overwrite these files.\nDo you wish to continue?' %(dammif_names[key])
                label = 'Overwrite existing files?'
                icon = wx.ART_WARNING

                question_dialog = RAWCustomCtrl.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, style = wx.CAPTION)
                result = question_dialog.ShowModal()
                question_dialog.Destroy()

                if result == wx.ID_NO:
                    return
                elif result == wx.ID_YESTOALL:
                    yes_to_all = True

        #Set up the various bits of information the threads will need. Set up the status windows.
        self.dammif_ids = {key: value for (key, value) in [(str(i), wx.NewId()) for i in range(1, nruns+1)]}

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

                    question_dialog = RAWCustomCtrl.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, style = wx.CAPTION)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['damaver'] = wx.NewId()
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

                    question_dialog = RAWCustomCtrl.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, style = wx.CAPTION)
                    result = question_dialog.ShowModal()
                    question_dialog.Destroy()

                    if result == wx.ID_NO:
                        return
                    elif result == wx.ID_YESTOALL:
                        yes_to_all = True

            self.dammif_ids['damclust'] = wx.NewId()
            text_ctrl = wx.TextCtrl(self.logbook, self.dammif_ids['damclust'], '', style = wx.TE_MULTILINE | wx.TE_READONLY)
            self.logbook.AddPage(text_ctrl, 'Damclust')


        self.status.SetValue('Starting processing\n')


        for key in self.ids:
            if key != 'logbook' and key != 'abort' and key != 'status':
                wx.FindWindowById(self.ids[key]).Disable()
            elif key == 'abort':
                wx.FindWindowById(self.ids[key]).Enable()


        self.threads = []
        
        self.my_semaphore = threading.BoundedSemaphore(procs)
        self.start_semaphore = threading.BoundedSemaphore(1)

        self.abort_event = threading.Event()
        self.abort_event.clear()

        self.rs = Queue.Queue()

        for key in self.dammif_ids:
            if key != 'damaver' and key != 'damclust':
                t = threading.Thread(target = self.runDammif, args = (outname, prefix, path))
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
                wx.FindWindowById(self.ids[key]).Enable()
            elif key == 'abort':
                wx.FindWindowById(self.ids[key]).Disable()


        self.status.AppendText('Processing Aborted!')


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save']).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)
            
        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save']).SetValue(new_path)


    def onRunsText(self, evt):
        nruns_ctrl = wx.FindWindowById(self.ids['runs'])
        

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
                window = wx.FindWindowById(self.ids[key])

                self.dammif_settings[key] = window.GetStringSelection()


    def runDammif(self, outname, prefix, path):

        with self.my_semaphore:
            #Check to see if things have been aborted
            if self.abort_event.isSet():
                my_num = self.thread_nums.get()
                damId = self.dammif_ids[my_num]
                damWindow = wx.FindWindowById(damId)
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return


            #Make sure that you don't start two dammif processes with the same random seed
            with self.start_semaphore:
                if not self.rs.empty():
                    old_rs = self.rs.get()
                    while old_rs == int(time.time()):
                        time.sleep(0.01)
                self.rs.put(int(time.time()))

            my_num = self.thread_nums.get()
            damId = self.dammif_ids[my_num]
            damWindow = wx.FindWindowById(damId)

            dam_prefix = prefix+'_%s' %(my_num.zfill(2))


            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, dam_prefix+'.log'), os.path.join(path, dam_prefix+'.in'),
                        os.path.join(path, dam_prefix+'.fit'), os.path.join(path, dam_prefix+'.fir'),
                        os.path.join(path, dam_prefix+'-1.pdb'), os.path.join(path, dam_prefix+'-0.pdb')]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)


            #Run DAMMIF
            dam_args = self.dammif_settings

            wx.CallAfter(self.status.AppendText, 'Starting DAMMIF run %s\n' %(my_num))

            cwd = os.getcwd()
            os.chdir(path)

            dammif_proc = SASCalc.runDammif(outname, dam_prefix, dam_args)

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

                logfile = open(logname, 'rb')
                logfile.seek(pos)

                newtext = logfile.read()

                if newtext != '':
                    wx.CallAfter(damWindow.AppendText, newtext)

                pos = logfile.tell()
                logfile.close()

                time.sleep(.1)

            logfile = open(os.path.join(path,dam_prefix)+'.log', 'rb')
            logfile.seek(pos)
            final_status = logfile.read()
            logfile.close()

            wx.CallAfter(damWindow.AppendText, final_status)


            wx.CallAfter(self.status.AppendText, 'Finished DAMMIF run %s\n' %(my_num))


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
            if self.abort_event.isSet():
                my_num = self.thread_nums.get()
                damId = self.dammif_ids[my_num]
                damWindow = wx.FindWindowById(damId)
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return

            damId = self.dammif_ids['damaver']
            damWindow = wx.FindWindowById(damId)

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


            nruns_window = wx.FindWindowById(self.ids['runs'])
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

            with read_semaphore: #see if there's any last data that we missed
                try:
                    new_text = damaver_q.get_nowait()
                    print new_text
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
            if self.abort_event.isSet():
                my_num = self.thread_nums.get()
                damId = self.dammif_ids[my_num]
                damWindow = wx.FindWindowById(damId)
                wx.CallAfter(damWindow.AppendText, 'Aborted!\n')
                return

            damId = self.dammif_ids['damclust']
            damWindow = wx.FindWindowById(damId)

            #Remove old files, so they don't mess up the program
            old_files = [os.path.join(path, prefix+'_damclust.log')]

            for item in old_files:
                if os.path.exists(item):
                    os.remove(item)

            wx.CallAfter(self.status.AppendText, 'Starting DAMCLUST\n')


            nruns_window = wx.FindWindowById(self.ids['runs'])
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

            with read_semaphore: #see if there's any last data that we missed
                try:
                    new_text = damclust_q.get_nowait()
                    print new_text
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
                path_window = wx.FindWindowById(self.ids['save'])
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'])
                prefix = prefix_window.GetValue()


                t = threading.Thread(target = self.runDamaver, args = (prefix, path))
                t.daemon = True
                t.start()
                self.threads.append(t)

            elif 'damclust' in self.dammif_ids:
                path_window = wx.FindWindowById(self.ids['save'])
                path = path_window.GetValue()

                prefix_window = wx.FindWindowById(self.ids['prefix'])
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
                wx.FindWindowById(self.ids[key]).Enable()
            elif key == 'abort':
                wx.FindWindowById(self.ids[key]).Disable()

        self.status.AppendText('Finished Processing')


    def _onAdvancedButton(self, evt):
        self.main_frame.showOptionsDialog(focusHead='DAMMIF')

    def onCheckBox(self,evt):
        if evt.GetId() == self.ids['damaver'] and evt.IsChecked():
            damclust = wx.FindWindowById(self.ids['damclust'])
            damclust.SetValue(False)

        elif evt.GetId() == self.ids['damclust'] and evt.IsChecked():
            damaver = wx.FindWindowById(self.ids['damaver'])
            damaver.SetValue(False)


    def updateDAMMIFSettings(self):
        self.dammif_settings = {'mode'          : self.raw_settings.get('dammifMode'),
                                'unit'          : self.raw_settings.get('dammifUnit'),
                                'sym'           : self.raw_settings.get('dammifSymmetry'),
                                'anisometry'    : self.raw_settings.get('dammifAnisometry'),
                                'omitSolvent'   : self.raw_settings.get('dammifOmitSolvent'),
                                'chained'       : self.raw_settings.get('dammifChained'),
                                'constant'      : self.raw_settings.get('dammifConstant'),
                                'maxBead'       : self.raw_settings.get('dammifMaxBeadCount'),
                                'radius'        : self.raw_settings.get('dammifDummyRadius'),
                                'harmonics'     : self.raw_settings.get('dammifSH'),
                                'propFit'       : self.raw_settings.get('dammifPropToFit'),
                                'curveWeight'   : self.raw_settings.get('dammifCurveWeight'),
                                'seed'          : self.raw_settings.get('dammifRandomSeed'),
                                'maxSteps'      : self.raw_settings.get('dammifMaxSteps'),
                                'maxIters'      : self.raw_settings.get('dammifMaxIters'),
                                'maxSuccess'    : self.raw_settings.get('dammifMaxStepSuccess'),
                                'minSuccess'    : self.raw_settings.get('dammifMinStepSuccess'),
                                'TFactor'       : self.raw_settings.get('dammifTFactor'),
                                'RgWeight'      : self.raw_settings.get('dammifRgPen'),
                                'cenWeight'     : self.raw_settings.get('dammifCenPen'),
                                'looseWeight'   : self.raw_settings.get('dammifLoosePen')
                                }

        mode = wx.FindWindowById(self.ids['mode'])
        mode.SetStringSelection(self.dammif_settings['mode'])

        sym = wx.FindWindowById(self.ids['sym'])
        sym.SetStringSelection(self.dammif_settings['sym'])

        anisometry = wx.FindWindowById(self.ids['anisometry'])
        anisometry.SetStringSelection(self.dammif_settings['anisometry'])

        procs = wx.FindWindowById(self.ids['procs'])
        procs.SetSelection(1)

        damaver = wx.FindWindowById(self.ids['damaver'])
        damaver.SetValue(self.raw_settings.get('dammifDamaver'))

        damclust = wx.FindWindowById(self.ids['damclust'])
        damclust.SetValue(self.raw_settings.get('dammifDamclust'))

        prefix = wx.FindWindowById(self.ids['prefix'])
        prefix.SetValue(os.path.splitext(self.filename)[0])

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        save = wx.FindWindowById(self.ids['save'])
        save.SetValue(path)

        nruns = wx.FindWindowById(self.ids['runs'])
        nruns.SetValue(str(self.raw_settings.get('dammifReconstruct')))


    def _onCloseButton(self, evt):
        self.Close()

    def _onInfoButton(self, evt):
        msg = 'In addition to citing the RAW paper:\n If you use DAMMIF in your work please cite the paper given here:\nhttps://www.embl-hamburg.de/biosaxs/dammif.html\n\nIf you use DAMAVER in your work, please cite the paper given here:\nhttps://www.embl-hamburg.de/biosaxs/damaver.html\n\nIf you use DAMCLUST in your work please cite the paper given here:\nhttps://www.embl-hamburg.de/biosaxs/manuals/damclust.html'
        wx.MessageBox(str(msg), "How to cite DAMMIF/DAMAVER/DAMCLUST", style = wx.ICON_INFORMATION | wx.OK)

    def OnClose(self, event):

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
                    process_finished = True

        if not process_finished and event.CanVeto():
            msg = "Warning: DAMMIF or DAMAVER is still running. Closing this window will abort the currently running processes. Do you want to continue closing the window?"
            dlg = wx.MessageDialog(self.main_frame, msg, "Abort DAMMIF/DAMAVER?", style = wx.ICON_WARNING | wx.YES_NO)
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
                        wx.FindWindowById(self.ids[key]).Enable()
                    elif key == 'abort':
                        wx.FindWindowById(self.ids[key]).Disable()

                self.status.AppendText('Processing Aborted!')

            else:
                event.Veto()
                return

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
                    wx.FindWindowById(self.ids[key]).Enable()
                elif key == 'abort':
                    wx.FindWindowById(self.ids[key]).Disable()

            self.status.AppendText('Processing Aborted!')

        self.Destroy()

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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
        
        if self.ift != None:
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
                                                      
        controlPanel = wx.FindWindowByName('BIFTControlPanel')

        
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


        self.infodata = {'dmax'         : ('Dmax :', wx.NewId()),
                         'alpha'        : ('Alpha :', wx.NewId()),
                         'guinierI0'    : ('I0 :', wx.NewId()),
                         'guinierRg'    : ('Rg :', wx.NewId()),
                         'biftI0'       : ('I0 :', wx.NewId()),
                         'biftRg'       : ('Rg :', wx.NewId()),
                         'chisq'        : ('chi^2 (fit) :', wx.NewId())
                         }

        self.statusIds = {  'status'      : wx.NewId(),
                            'evidence'  : wx.NewId(),
                            'chi'       : wx.NewId(),
                            'alpha'     : wx.NewId(),
                            'dmax'      : wx.NewId(),
                            'spoint'    : wx.NewId(),
                            'tpoint'    : wx.NewId()}

        self.buttonIds = {  'abort'     : wx.NewId(),
                            'settings'  : wx.NewId(),
                            'run'       : wx.NewId()}


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
        self.dmaxWindow = wx.TextCtrl(self, self.infodata['dmax'][1], '-1', size = (60,-1), style = wx.TE_READONLY)

        dmaxSizer = wx.BoxSizer(wx.HORIZONTAL)
        dmaxSizer.Add(dmaxLabel, 0, wx.RIGHT, 5)
        dmaxSizer.Add(self.dmaxWindow, 0, wx.RIGHT, 5)

        alphaLabel = wx.StaticText(self, -1, 'Log(Alpha) :')
        self.alphaWindow = wx.TextCtrl(self, self.infodata['alpha'][1], '-1', size = (60,-1), style = wx.TE_READONLY)

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
        self.guinierRg = wx.TextCtrl(self, self.infodata['guinierRg'][1], '0', size = (60,-1), style = wx.TE_READONLY)
        self.guinierI0 = wx.TextCtrl(self, self.infodata['guinierI0'][1], '0', size = (60,-1), style = wx.TE_READONLY)

        sizer.Add(guinierlabel, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.guinierRg, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        sizer.Add(self.guinierI0, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        biftlabel = wx.StaticText(self, -1, 'P(r) :')
        self.biftRg = wx.TextCtrl(self, self.infodata['biftRg'][1], '0', size = (60,-1), style = wx.TE_READONLY)
        self.biftI0 = wx.TextCtrl(self, self.infodata['biftI0'][1], '0', size = (60,-1), style = wx.TE_READONLY)

        sizer.Add(biftlabel, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.biftRg, 0, wx.ALL, 5)
        sizer.Add(self.biftI0, 0, wx.ALL, 5)


        chisqLabel = wx.StaticText(self, -1, self.infodata['chisq'][0])
        self.chisq = wx.TextCtrl(self, self.infodata['chisq'][1], '0', size = (60,-1), style = wx.TE_READONLY)

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


        chiLabel = wx.StaticText(self, -1, 'Chi :')
        chiText = wx.StaticText(self, self.statusIds['chi'], '')

        chiSizer = wx.BoxSizer(wx.HORIZONTAL)
        chiSizer.Add(chiLabel, 0, wx.RIGHT, 3)
        chiSizer.Add(chiText, 0, wx.RIGHT, 3)


        alphaLabel = wx.StaticText(self, -1, 'Alpha :')
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

        guinierRgWindow = wx.FindWindowById(self.infodata['guinierRg'][1])
        guinierI0Window = wx.FindWindowById(self.infodata['guinierI0'][1])

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

        if self.iftm != None:

            results_dict = {}

            results_dict['Dmax'] = str(self.iftm.getParameter('dmax'))
            results_dict['Real_Space_Rg'] = str(self.iftm.getParameter('Rg'))
            results_dict['Real_Space_I0'] = str(self.iftm.getParameter('I0'))
            results_dict['ChiSquared'] = str(self.iftm.getParameter('ChiSquared'))
            results_dict['LogAlpha'] = str(self.iftm.getParameter('alpha'))


            analysis_dict = self.sasm.getParameter('analysis')
            analysis_dict['BIFT'] = results_dict

            if self.manip_item != None:
                if results_dict != self.old_analysis:
                    wx.CallAfter(self.manip_item.markAsModified)

        if self.BIFT_timer.IsRunning():
            self.BIFT_timer.Stop()
            RAWGlobals.cancel_bift = True

        if self.raw_settings.get('AutoSaveOnBift') and self.iftm != None:
            if os.path.isdir(self.raw_settings.get('BiftFilePath')):
                RAWGlobals.mainworker_cmd_queue.put(['save_iftm', [self.iftm, self.raw_settings.get('BiftFilePath')]])
            else:
                self.raw_settings.set('AutoSaveOnBift', False)
                wx.CallAfter(wx.MessageBox, 'The folder:\n' +self.raw_settings.get('BiftFilePath')+ '\ncould not be found. Autosave of BIFT files has been disabled. If you are using a config file from a different computer please go into Advanced Options/Autosave to change the save folders, or save you config file to avoid this message next time.', 'Autosave Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

        if self.iftm != None:
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
        biftRgWindow = wx.FindWindowById(self.infodata['biftRg'][1])
        biftI0Window = wx.FindWindowById(self.infodata['biftI0'][1])
        biftChisqWindow = wx.FindWindowById(self.infodata['chisq'][1])
        biftDmaxWindow = wx.FindWindowById(self.infodata['dmax'][1])
        biftAlphaWindow = wx.FindWindowById(self.infodata['alpha'][1])

        if self.iftm != None:

            biftRgWindow.SetValue(str(self.iftm.getParameter('Rg')))
            biftI0Window.SetValue(str(self.iftm.getParameter('I0')))
            biftChisqWindow.SetValue(str(self.iftm.getParameter('ChiSquared')))
            biftDmaxWindow.SetValue(str(self.iftm.getParameter('dmax')))
            biftAlphaWindow.SetValue(str(self.iftm.getParameter('alpha')))
            
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
                wx.FindWindowById(self.buttonIds[key]).Disable()
            else:
                wx.FindWindowById(self.buttonIds[key]).Enable()

        RAWGlobals.cancel_bift = False

        while not self.BIFT_queue.empty():
            self.BIFT_queue.get_nowait()

        self.BIFT_timer.Start(1)

        self.updateStatus({'status': 'Performing search grid'})

        RAWGlobals.mainworker_cmd_queue.put(['ift', ['BIFT', self.sasm, self.BIFT_queue, self.bift_settings]])

    def updateStatus(self, updates):
        for key in updates:
            wx.FindWindowById(self.statusIds[key]).SetLabel(str(updates[key]))

    def clearStatus(self, exception_list):
        for key in self.statusIds:
            if key not in exception_list:
                wx.FindWindowById(self.statusIds[key]).SetLabel('')

    def finishedProcessing(self):
        for key in self.buttonIds:
            if key not in ['abort']:
                wx.FindWindowById(self.buttonIds[key]).Enable()
            else:
                wx.FindWindowById(self.buttonIds[key]).Disable()

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

        self.ids = {'input'         : wx.NewId(),
                    'rg'            : wx.NewId(),
                    'prefix'        : wx.NewId(),
                    'files'         : wx.NewId(),
                    'sRg'           : wx.NewId(),
                    'save'          : wx.NewId(),
                    'ambiCats'      : wx.NewId(),
                    'ambiScore'     : wx.NewId(),
                    'ambiEval'      : wx.NewId()}


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
        fname_window = wx.FindWindowById(self.ids['input'])
        fname_window.SetValue(self.iftm.getParameter('filename'))

        rg_window = wx.FindWindowById(self.ids['rg'])
        rg_window.SetValue(str(self.iftm.getParameter('rg')))

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        outdir_window = wx.FindWindowById(self.ids['save'])
        outdir_window.SetValue(path)

        outprefix_window = wx.FindWindowById(self.ids['prefix'])
        outprefix_window.SetValue(os.path.splitext(os.path.basename(self.iftm.getParameter('filename')))[0])

    def _getSettings(self):

        outdir_window = wx.FindWindowById(self.ids['save'])
        self.ambi_settings['path'] = outdir_window.GetValue()

        outprefix_window = wx.FindWindowById(self.ids['prefix'])
        self.ambi_settings['prefix'] = outprefix_window.GetValue()

        outsrg_window = wx.FindWindowById(self.ids['sRg'])
        self.ambi_settings['sRg'] = outsrg_window.GetValue()

        outfiles_window = wx.FindWindowById(self.ids['files'])
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
            output = SASCalc.runAmbimeter(outname, self.ambi_settings['prefix'], self.ambi_settings)

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
        
        cats_window = wx.FindWindowById(self.ids['ambiCats'])
        cats_window.SetValue(output[0])

        score_window = wx.FindWindowById(self.ids['ambiScore'])
        score_window.SetValue(output[1])

        eval_window = wx.FindWindowById(self.ids['ambiEval'])
        eval_window.SetValue(output[2])

        bi.Destroy()


    def onChangeDirectoryButton(self, evt):
        path = wx.FindWindowById(self.ids['save']).GetValue()

        dirdlg = wx.DirDialog(self, "Please select save directory:", defaultPath = path)
            
        if dirdlg.ShowModal() == wx.ID_OK:
            new_path = dirdlg.GetPath()
            wx.FindWindowById(self.ids['save']).SetValue(new_path)


    def onSrgText(self, evt):
        srg_ctrl = wx.FindWindowById(self.ids['sRg'])
        

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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
        
        if self.svd != None:
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

        # print ydata2
        # print ydata3

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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
        
        if self.secm != None:
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
            
        xmin, xmax = frame_list[0], frame_list[-1]
        
        #Save for resizing:
        self.orig_frame_list = frame_list
        self.orig_intensity = intensity
        self.orig_framei = framei
        self.orig_framef = framef
        
        # #Cut out region of interest
        # self.i = i[xmin:xmax]
        # self.q = q[xmin:xmax]
            
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

        self.control_ids = {'profile'   : wx.NewId(),
                            'fstart'    : wx.NewId(),
                            'fend'      : wx.NewId(),
                            'svd_start' : wx.NewId(),
                            'svd_end'   : wx.NewId(),
                            'norm_data' : wx.NewId()}

        self.field_ids = {'fname'     : wx.NewId()}
                            

        self.button_ids = {'save_svd'   : wx.NewId(),
                            'save_all'  : wx.NewId()}

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

        filename_window = wx.FindWindowById(self.field_ids['fname'])
        filename_window.SetValue(filename)

        analysis_dict = self.secm.getParameter('analysis')

        if 'svd' not in analysis_dict:

            framei = self.secm.frame_list[0]
            framef = self.secm.frame_list[-1]


            framei_window = wx.FindWindowById(self.control_ids['fstart'])
            framef_window = wx.FindWindowById(self.control_ids['fend'])

            if len(self.secm.subtracted_sasm_list)>0:
                frame_start = max(np.where(self.secm.use_subtracted_sasm)[0][0], framei)
                frame_end = min(np.where(self.secm.use_subtracted_sasm)[0][-1], framef)

            else:
                frame_start = framei
                frame_end = framef

            framei_window.SetValue(frame_start)
            framef_window.SetValue(frame_end)

            framei_window.SetRange((framei, framef))
            framef_window.SetRange((framei, framef))


            svd_start_window =wx.FindWindowById(self.control_ids['svd_start'])
            svd_end_window =wx.FindWindowById(self.control_ids['svd_end'])

            svd_start_window.SetValue(0)
            svd_end_window.SetValue(min(framef-framei,10))

            svd_start_window.SetRange((0, framef-framei-1))
            svd_end_window.SetRange((1, framef-framei))

        else:
            framei = self.secm.frame_list[0]
            framef = self.secm.frame_list[-1]

            framei_window = wx.FindWindowById(self.control_ids['fstart'])
            framef_window = wx.FindWindowById(self.control_ids['fend'])

            svd_start_window =wx.FindWindowById(self.control_ids['svd_start'])
            svd_end_window =wx.FindWindowById(self.control_ids['svd_end'])

            framei_window.SetRange((framei, framef))
            framef_window.SetRange((framei, framef))

            svd_start_window.SetRange((0, framef-framei-1))
            svd_end_window.SetRange((1, framef-framei))

            for key in analysis_dict['svd']:
                if key != 'profile':
                    wx.FindWindowById(self.control_ids[key]).SetValue(analysis_dict['svd'][key])
                else:
                    wx.FindWindowById(self.control_ids[key]).SetStringSelection(analysis_dict['svd'][key])


        #make a subtracted profile SECM
        if len(self.secm.subtracted_sasm_list)>0:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, self.secm.frame_list, self.secm.getAllParameters())
        else:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, [], self.secm.getAllParameters())


        if self.manip_item != None:
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
            msg = 'No subtracted files are available for this SEC curve. You can create subtracted curves by setting a buffer range in the SEC Control Panel and calculating the parameter values. You will have to reopen the SVD window after doing this.'
            dlg = wx.MessageDialog(self, msg, "No subtracted files", style = wx.ICON_INFORMATION | wx.OK)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            profile_window = wx.FindWindowById(evt.GetId())
            profile_window.SetStringSelection('Unsubtracted')


    #This function is called when the start and end frame range spin controls are modified
    def _onChangeFrame(self, evt):
        id = evt.GetId()

        spin = wx.FindWindowById(id)
            
        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'])
        fend_window = wx.FindWindowById(self.control_ids['fend'])

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'])

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

        spin = wx.FindWindowById(id)
            
        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'])
        fend_window = wx.FindWindowById(self.control_ids['fend'])

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'])

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
        profile_window = wx.FindWindowById(self.control_ids['profile'])

        framei_window = wx.FindWindowById(self.control_ids['fstart'])
        framef_window = wx.FindWindowById(self.control_ids['fend'])

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        if profile_window.GetStringSelection() == 'Unsubtracted':
            secm = self.secm
        else:
            secm = self.subtracted_secm

        norm_data_window = wx.FindWindowById(self.control_ids['norm_data'])
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
        framei_window = wx.FindWindowById(self.control_ids['fstart'])
        framef_window = wx.FindWindowById(self.control_ids['fend'])

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        profile_window = wx.FindWindowById(self.control_ids['profile'])

        if profile_window.GetStringSelection() == 'Unsubtracted':
            plotpanel.plotSECM(self.secm, framei, framef, self.ydata_type)
        else:
            plotpanel.plotSECM(self.subtracted_secm, framei, framef, self.ydata_type)

    def updateSVDPlot(self):
        plotpanel = wx.FindWindowByName('SVDResultsPlotPanel')

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'])

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

        filename_window = wx.FindWindowById(self.field_ids['fname'])
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

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'])

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()
        
        data = np.column_stack((self.svd_s[svd_start:svd_end+1], self.svd_U_autocor[svd_start:svd_end+1], self.svd_V_autocor[svd_start:svd_end+1]))

        header = 'Singular_values,U_Autocorrelation,V_Autocorrelation'

        SASFileIO.saveCSVFile(save_path, data, header)

    def saveAll(self):
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        path = str(dirctrl.getDirLabel())

        filename_window = wx.FindWindowById(self.field_ids['fname'])
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

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'])

        svd_start = svd_start_window.GetValue()
        svd_end = svd_end_window.GetValue()
        
        svd_data = np.column_stack((self.svd_s[svd_start:svd_end+1], self.svd_U_autocor[svd_start:svd_end+1], self.svd_V_autocor[svd_start:svd_end+1]))

        u_data = self.svd_U[:,svd_start:svd_end+1]
        v_data = self.svd_V[:,svd_start:svd_end+1]

        SASFileIO.saveSVDData(save_path, svd_data, u_data, v_data)


    def _onCancelButton(self, evt):
        self.svd_frame.OnClose()


    def _onOkButton(self, evt):
        svd_dict = {}
        for key in self.control_ids:
            if key != 'profile':
                svd_dict[key] = wx.FindWindowById(self.control_ids[key]).GetValue()
            else:
                svd_dict[key] = wx.FindWindowById(self.control_ids[key]).GetStringSelection()


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

        if self.manip_item != None:
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

        self.splitter_ids = {1  : wx.NewId(),
                            2   : wx.NewId(),
                            3   : wx.NewId()}


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

                if type(self.panel1_results['svd_u']) != None and not np.any(np.isnan(self.panel1_results['svd_u'])):

                    self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel]), recursive = True)

                    self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel+1]), recursive = True)

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
                    proceed = dlg.ShowModal()
                    dlg.Destroy()   

            else:
                msg = 'Please enter the number of significant singular values to use for the evolving factor analysis in the User Input area.'
                dlg = wx.MessageDialog(self, msg, "No Singular Values Selected", style = wx.ICON_INFORMATION | wx.OK)
                proceed = dlg.ShowModal()
                dlg.Destroy()     

        elif self.current_panel == 2:

            self.getPanel2Values()

            correct = np.all([point[0] < point[1] for point in self.panel2_results['points']])

            if correct:

                self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel]), recursive = True)

                self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel+1]), recursive = True)

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
                proceed = dlg.ShowModal()
                dlg.Destroy() 


        self.panel.Layout()
        self.SendSizeEvent()
        self.panel.Layout()

    def _onBackButton(self, evt):

        if self.current_panel == 2:
            self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel]), recursive = True)

            self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel-1]), recursive = True)

            self.current_panel = self.current_panel - 1

            self.back_button.Disable()

        elif self.current_panel == 3:
            self.top_sizer.Hide(wx.FindWindowById(self.splitter_ids[self.current_panel]), recursive = True)

            self.top_sizer.Show(wx.FindWindowById(self.splitter_ids[self.current_panel-1]), recursive = True)

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

            analysis_dict['efa'] = efa_dict

        self.OnClose()

    def _onInfoButton(self, evt):
        msg = 'If you use evolving factor analysis (EFA) in your work, in addition to citing the RAW paper please cite:\nSteve P. Meisburger, Alexander B. Taylor, Crystal A. Khan, Shengnan Zhang, Paul F. Fitzpatrick, and Nozomi Ando. Journal of the American Chemical Society 2016 138 (20), 6506-6516.'
        wx.MessageBox(str(msg), "How to cite EFA", style = wx.ICON_INFORMATION | wx.OK)

    def getPanel1Values(self):
        for key in self.panel1_results:
            if key in self.controlPanel1.control_ids:
                window = wx.FindWindowById(self.controlPanel1.control_ids[key])

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
                profile_window = wx.FindWindowById(self.controlPanel1.control_ids['profile'])

                if profile_window.GetStringSelection() == 'Unsubtracted':
                    value = False
                else:
                    value = True

            elif key == 'sub_secm':
                value = self.controlPanel1.subtracted_secm

            elif key == 'ydata_type':
                value = self.controlPanel1.ydata_type

            elif key == 'filename':
                filename_window = wx.FindWindowById(self.controlPanel1.field_ids['fname'])
                value = filename_window.GetValue()

            elif key == 'q':
                value = self.secm.getSASM().q

            self.panel1_results[key] = value

    def getPanel2Values(self):
        window = wx.FindWindowByName('EFAControlPanel2')

        forward_points = [wx.FindWindowById(my_id).GetValue() for my_id in window.forward_ids]
        self.panel2_results['forward_points'] = copy.copy(forward_points)

        backward_points = [wx.FindWindowById(my_id).GetValue() for my_id in window.backward_ids]
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

        self.control_ids = {'profile'   : wx.NewId(),
                            'fstart'    : wx.NewId(),
                            'fend'      : wx.NewId(),
                            'svd_start' : wx.NewId(),
                            'svd_end'   : wx.NewId(),
                            'input'     : wx.NewId()}

        self.field_ids = {'fname'     : wx.NewId()}

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

        filename_window = wx.FindWindowById(self.field_ids['fname'])
        filename_window.SetValue(filename)

        analysis_dict = self.secm.getParameter('analysis')

        framei_window = wx.FindWindowById(self.control_ids['fstart'])
        framef_window = wx.FindWindowById(self.control_ids['fend'])

        svd_start_window =wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'])

        user_input_window = wx.FindWindowById(self.control_ids['input'])


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
                frame_start = max(np.where(self.secm.use_subtracted_sasm)[0][0]-50, framei)
                frame_end = min(np.where(self.secm.use_subtracted_sasm)[0][-1]+50, framef)

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
                    wx.FindWindowById(self.control_ids[key]).SetStringSelection(analysis_dict['efa'][key])
                elif key == 'nsvs':
                    wx.FindWindowById(self.control_ids['input']).SetValue(analysis_dict['efa'][key])
                elif key in self.control_ids:
                     wx.FindWindowById(self.control_ids[key]).SetValue(analysis_dict['efa'][key])

            svd_start_window.SetValue(0)
            svd_end_window.SetValue(min(framef-framei,10))


        #make a subtracted profile SECM
        if len(self.secm.subtracted_sasm_list)>0:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, self.secm.frame_list, self.secm.getAllParameters())
        else:
            self.subtracted_secm = SASM.SECM(self.secm._file_list, self.secm.subtracted_sasm_list, [], self.secm.getAllParameters())
            
            profile_window = wx.FindWindowById(self.control_ids['profile'])
            profile_window.SetStringSelection('Unsubtracted')

        if self.manip_item != None:
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
            msg = 'No subtracted files are available for this SEC curve. You can create subtracted curves by setting a buffer range in the SEC Control Panel and calculating the parameter values. You will have to reopen the EFA window after doing this.'
            dlg = wx.MessageDialog(self, msg, "No subtracted files", style = wx.ICON_INFORMATION | wx.OK)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            profile_window = wx.FindWindowById(evt.GetId())
            profile_window.SetStringSelection('Unsubtracted')


    #This function is called when the start and end frame range spin controls are modified
    def _onChangeFrame(self, evt):
        id = evt.GetId()

        spin = wx.FindWindowById(id)
            
        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'])
        fend_window = wx.FindWindowById(self.control_ids['fend'])

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window =wx.FindWindowById(self.control_ids['svd_end'])

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

        spin = wx.FindWindowById(id)
            
        new_val = spin.GetValue()

        fstart_window = wx.FindWindowById(self.control_ids['fstart'])
        fend_window = wx.FindWindowById(self.control_ids['fend'])

        svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
        svd_end_window = wx.FindWindowById(self.control_ids['svd_end'])

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
        profile_window = wx.FindWindowById(self.control_ids['profile'])

        framei_window = wx.FindWindowById(self.control_ids['fstart'])
        framef_window = wx.FindWindowById(self.control_ids['fend'])

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        if profile_window.GetStringSelection() == 'Unsubtracted':
            secm = self.secm
        else:
            secm = self.subtracted_secm

        sasm_list = secm.getSASMList(framei, framef)

        i = np.array([sasm.i for sasm in sasm_list])
        err = np.array([sasm.err for sasm in sasm_list])

        self.i = i.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose
        self.err = err.T

        err_mean = np.mean(self.err, axis = 1)
        if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
            self.err_avg = np.broadcast_to(err_mean.reshape(err_mean.size,1), self.err.shape)
        else:
            self.err_avg = np.array([err_mean for i in range(self.i.shape[1])]).T

        self.svd_a = self.i/self.err_avg

        try:
            self.svd_U, self.svd_s, svd_Vt = np.linalg.svd(self.svd_a, full_matrices = True)
        except:
            wx.CallAfter(wx.MessageBox, 'Initial SVD did not converge, so EFA cannot proceed.', 'SVD Failed', style = wx.ICON_ERROR | wx.OK)
            return

        self.svd_V = svd_Vt.T
        self.svd_U_autocor = np.abs(np.array([np.correlate(self.svd_U[:,i], self.svd_U[:,i], mode = 'full')[-self.svd_U.shape[0]+1] for i in range(self.svd_U.shape[1])]))
        self.svd_V_autocor = np.abs(np.array([np.correlate(self.svd_V[:,i], self.svd_V[:,i], mode = 'full')[-self.svd_V.shape[0]+1] for i in range(self.svd_V.shape[1])]))

        wx.CallAfter(self.updateSVDPlot)

    def updateSECPlot(self):

        plotpanel = wx.FindWindowByName('EFASECPlotPanel')
        framei_window = wx.FindWindowById(self.control_ids['fstart'])
        framef_window = wx.FindWindowById(self.control_ids['fend'])

        framei = framei_window.GetValue()
        framef = framef_window.GetValue()

        profile_window = wx.FindWindowById(self.control_ids['profile'])

        if profile_window.GetStringSelection() == 'Unsubtracted':
            plotpanel.plotSECM(self.secm, framei, framef, self.ydata_type)
        else:
            plotpanel.plotSECM(self.subtracted_secm, framei, framef, self.ydata_type)

    def updateSVDPlot(self):

        if self.svd_s is not None and not np.any(np.isnan(self.svd_s)):
            plotpanel = wx.FindWindowByName('EFAResultsPlotPanel1')

            svd_start_window = wx.FindWindowById(self.control_ids['svd_start'])
            svd_end_window = wx.FindWindowById(self.control_ids['svd_end'])

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

        self.forward_ids = [wx.NewId() for i in range(nvals)]
        self.backward_ids = [wx.NewId() for i in range(nvals)]

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

        self.forward_ids = [wx.NewId() for i in range(nvals)]
        self.backward_ids = [wx.NewId() for i in range(nvals)]

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
            forward = wx.FindWindowById(self.forward_ids[i])
            backward = wx.FindWindowById(self.backward_ids[len(self.backward_ids)-1-i])

            forward.SetValue(points[i][0])
            backward.SetValue(points[i][1])

        wx.CallAfter(self.updateEFAPlot)

    def _findEFAPoints(self):

        forward_windows = [wx.FindWindowById(my_id) for my_id in self.forward_ids]

        backward_windows = [wx.FindWindowById(my_id) for my_id in self.backward_ids]

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

        forward_points = [wx.FindWindowById(my_id).GetValue() for my_id in self.forward_ids]

        backward_points = [wx.FindWindowById(my_id).GetValue() for my_id in self.backward_ids]

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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

        self.control_ids = {'n_iter'        : wx.NewId(),
                            'tol'           : wx.NewId(),
                            'status'        : wx.NewId(),
                            'save_results'  : wx.NewId()}

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


        box = wx.StaticBox(self, -1, 'Iteration Controls')
        iter_control_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        grid_sizer = wx.FlexGridSizer(cols = 2, rows = 2, vgap =3, hgap =3)
        
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

        self.range_ids = [(wx.NewId(), wx.NewId(), wx.NewId()) for i in range(nvals)]

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
                iter_window = wx.FindWindowById(self.control_ids['n_iter'])
                tol_window = wx.FindWindowById(self.control_ids['tol'])

                iter_window.SetValue(str(efa_dict['iter_limit']))
                tol_window.SetValue(str(efa_dict['tolerance']))

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

            self.range_ids = [(wx.NewId(), wx.NewId(), wx.NewId()) for i in range(nvals)]

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

            plotpanel = wx.FindWindowByName('EFAResultsPlotPanel3')
            plotpanel.refresh()

        else:
            for i in range(nvals):
                my_ids = self.range_ids[i]
                points = efa_results['points'][i]

                start = wx.FindWindowById(my_ids[0])
                end = wx.FindWindowById(my_ids[1])

                start.SetValue(points[0])
                end.SetValue(points[1])

            plotpanel = wx.FindWindowByName('EFAResultsPlotPanel3')
            plotpanel.refresh()

        wx.CallAfter(self.runRotation)
        wx.CallAfter(self.updateRangePlot)


    def _onIterControl(self, evt):
        wx.CallAfter(self.runRotation)

    def _onRangeControl(self, evt):

        myId = evt.GetId()

        for ids in self.range_ids:
            if myId in ids:

                if myId == ids[0]:
                    spinctrl = wx.FindWindowById(ids[1])

                    current_range = spinctrl.GetRange()

                    new_range = (int(evt.GetValue())+1, current_range[1])

                    spinctrl.SetRange(new_range)

                    wx.CallAfter(self.updateRangePlot)

                elif myId == ids[1]:
                    spinctrl = wx.FindWindowById(ids[0])

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

        SASFileIO.saveEFAData(save_path, self.panel1_results, self.panel2_results, panel3_results)


    def _updateStatus(self, in_progress = False):
        status_window = wx.FindWindowById(self.control_ids['status'])

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
            window = wx.FindWindowById(self.range_ids[i][2])
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

    def runRotation(self):
        #Get component ranges and iteration control values
        self._updateStatus(True)

        ranges = self._getRanges()

        start = self.panel1_results['fstart']

        ranges = ranges - start

        niter = int(wx.FindWindowById(self.control_ids['n_iter']).GetValue())
        tol = float(wx.FindWindowById(self.control_ids['tol']).GetValue())

        #Calculate the initial matrices
        num_sv = ranges.shape[0]

        D = self.panel1_results['svd_int_norm']

        if not self.converged:
            C = self.panel1_results['svd_v'][:,:num_sv]
        else:
            C = self.rotation_data['C']


        M = np.zeros_like(C)

        for j in range(num_sv):
            M[ranges[j][0]:ranges[j][1]+1, j] = 1

        #Set a variable to test whether the rotation fails for a numerical reason
        failed = False


        #Do an initial rotation
        try:
            C = self.firstRotation(M, C, D) 
        except np.linalg.linalg.LinAlgError as e:
            failed = True


        #Carry out the calculation to convergence
        k = 0
        converged = False

        dc = []

        while k < niter and not converged and not failed:
            k = k+1
            try:
                Cnew = self.updateRotation(M, C, D)
            except np.linalg.linalg.LinAlgError as e:
               failed = True

            dck = np.sum(np.abs(Cnew - C))

            dc.append(dck)

            C = Cnew

            if dck < tol:
                converged = True


        if not failed:
            self.conv_data = {'steps'   : dc,
                            'iterations': k,
                            'final_step': dc[-1],
                            'options'   : {'niter': niter, 'tol': tol}}

        #Check whether the calculation converged
        if k == niter and dck > tol:
            self.converged = False
            self.fail_text = 'Rotataion failed to converge after %i\n iterations with final delta = %.2E.' %(k, dc[-1])
        elif failed:
            self.converged = False
            self.fail_text = 'Rotataion failed due to a numerical error\n in the algorithm. Try adjusting ranges.'
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
            ranges.append([wx.FindWindowById(my_ids[0]).GetValue(), wx.FindWindowById(my_ids[1]).GetValue()])

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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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
      
        self.toolbar = NavigationToolbar2Wx(self.canvas)
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
        
        if self.cut_line != None:
            self.canvas.mpl_disconnect(self.cid)
            self.updateDataPlot(self.orig_frame_list, self.orig_intensity, self.orig_framei, self.orig_framef, self.orig_ranges)
            self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)
        
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
            
        xmin, xmax = frame_list[0], frame_list[-1]
        
        #Save for resizing:
        self.orig_frame_list = frame_list
        self.orig_intensity = intensity
        self.orig_framei = framei
        self.orig_framef = framef
        self.orig_ranges = ranges
            
        a = self.subplots['SECPlot']
        
        if self.cut_line == None:

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
        StaticText.__init__(self, parent, -1, label, style=wx.ST_NO_AUTORESIZE)
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