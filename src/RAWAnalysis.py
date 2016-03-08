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
import sys, os, copy
from scipy import linspace, polyval, polyfit, sqrt, randn
import scipy.interpolate as interp
from scipy import integrate as integrate
from scipy.constants import Avogadro
import RAW, RAWSettings, RAWCustomCtrl, SASCalc, RAWPlot
from wx.lib.splitter import MultiSplitterWindow
# These are for the AutoWrapStaticText class
from wx.lib.wordwrap import wordwrap
from wx.lib.stattext import GenStaticText as StaticText

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
    
        subplotLabels = [('Guinier', 'q^2', 'ln(I(q)', .1), ('Error', 'q', 'I(q)', 0.1)]
        
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

        I0 = float(newInfo['I0'][0])
        
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
        
             
class GuinierControlPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, ExpObj, manip_item):
        
        self.ExpObj = ExpObj
        
        self.manip_item = manip_item
        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')

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
                         'rsq': ('r^2 (fit) :', wx.NewId()),
                         'MM': ('MM :', wx.NewId())}
        

        button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)
        
        savebutton = wx.Button(self, wx.ID_OK, 'OK')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)

        autorg_button = wx.Button(self, -1, 'AutoRG')
        autorg_button.Bind(wx.EVT_BUTTON, self.onAutoRG)
        
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
            
            idx_min = guinier['nStart']
            idx_max = guinier['nEnd']

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

                print 'FAILED AutoRG! resetting controls'

            
        
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

        self.concCtrl.Bind(wx.EVT_TEXT, self._onUpdateConc)

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
        
        if float(info_dict['Conc']) > 0:
            self.ExpObj.setParameter('Conc', self.getConcentration())
            
        if float(info_dict['MM']) > 0:
            self.ExpObj.setParameter('MW', info_dict['MM'])
        
        analysis_dict = self.ExpObj.getParameter('analysis')
        analysis_dict['guinier'] = info_dict
        
        if self.manip_item != None:
            wx.CallAfter(self.manip_item.updateInfoTip, analysis_dict, fromGuinierDialog = True)
            if info_dict != self.old_analysis:
                wx.CallAfter(self.manip_item.markAsModified)

        mw_window = wx.FindWindowByName('MolWeightFrame')

        if mw_window:
            mw_window.updateGuinierInfo()
        
        #wx.MessageBox('The parameters have now been stored in memory', 'Parameters Saved')
        
        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()
        
    def onCloseButton(self, evt):
        
        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()

    def onAutoRG(self, evt):
        rg, rger, i0, i0er, idx_min, idx_max = SASCalc.autoRg(self.ExpObj)

        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        old_start = spinstart.GetValue()
        old_end = spinend.GetValue()

        if rg == -1:
            msg = 'AutoRG could not find a suitable interval to calculate Rg. Values are not updated.'
            wx.CallAfter(wx.MessageBox, str(msg), "AutoRG Failed", style = wx.ICON_ERROR | wx.OK)
            return
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
                wx.CallAfter(wx.MessageBox, str(msg), "AutoRG Failed", style = wx.ICON_ERROR | wx.OK)
        
        
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

    def _onUpdateConc(self,evt):
        mw = self.raw_settings.get('MWStandardMW') 
        mwI0 = self.raw_settings.get('MWStandardI0')
        mwConc = self.raw_settings.get('MWStandardConc')
        
        conc = self.getConcentration()

        info = self.getInfo()
        I0 = float(info['I0'])
        
        if mw != 0 and mw > 0 and mwI0 !=0 and mwI0 > 0 and conc != 0 and conc > 0 and mwConc > 0:
            newInfo = {'MM': (I0 * (mw/(mwI0/mwConc)) / conc)}
            self.updateInfo(newInfo)
        
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
                # ctrl2 = wx.FindWindowById(self.infodata[eachKey][2])
                val1 = ctrl1.GetValue()
                # val2 = ctrl2.GetValue()
                
                # guinierData[eachKey] = (val1, val2) 
                guinierData[eachKey] = val1

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
        
        
        self.CenterOnParent()

    def _createLayout(self, parent):

        # parent = self.panel
        
        self.top_mw = wx.ScrolledWindow(parent, -1)

        self.top_mw.SetScrollbars(20,20,50,50)

        # self.top_mw = self

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
        # top_sizer.Add(mw_sizer, 10, wx.EXPAND)
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

        # intro = wx.TextCtrl(self, value=intro_text, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_NO_VSCROLL|wx.BORDER_NONE|wx.TE_RICH2) 
        # color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        # intro.SetBackgroundColour(color)

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

        # top_sizer.Layout()

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
        buttonSizer.Add(params_button, 0, wx.ALIGN_LEFT | wx.LEFT, 5)
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

        A=fA(q[-1])
        B=fB(q[-1])
        
        if i0 > 0:
            #Calculate the Porod Volume
            pVolume = SASCalc.porodVolume(self.sasm, rg, i0, True)

            #Correct for the length of the q vector
            if q[-1]<0.45:
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
        
        # self.toolbar = NavigationToolbar2Wx(self.canvas)
        # self.toolbar.Realize()
        # sizer.Add(self.toolbar, 0, wx.GROW)

        self.SetSizer(sizer)
        self.canvas.SetBackgroundColour('white')
        self.fig.subplots_adjust(left = 0.26, bottom = 0.16, right = 0.95, top = 0.91)
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
        
        self.updateDataPlot(self.orig_i, self.orig_q)
        
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
            self.canvas.restore_region(self.background)
            
            self.data_line.set_ydata(y)
            self.data_line.set_xdata(x)
            
        
        a.relim()
        a.autoscale_view()
        
        a.draw_artist(self.data_line)

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