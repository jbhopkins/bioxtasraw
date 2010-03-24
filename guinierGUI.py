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
import wx
import fileIO

class GuinierPlotPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, wxEmbedded = False):
        
        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM)
        
        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        
        self.canvas.mpl_connect('motion_notify_event', self.onMotionEvent)
#        self.canvas.mpl_connect('button_press_event', self.onMouseButtonPressEvent)
        self.canvas.mpl_connect('button_release_event', self.onMouseReleaseEvent)
        self.canvas.mpl_connect('pick_event', self.onPick)
#        self.canvas.mpl_connect('key_press_event', self.onKeyPressEvent)
        
        #self.toolbar = MaskingPanelToolbar(self, self.canvas)
        subplotLabels = [('Data', 'q', 'I(q)'), ('Guinier', 'q^2', 'ln(I(q)')]
        
        self.subplots = {}
        NoOfSubplots = 2

        for i in range(0,NoOfSubplots):
            subplot = self.fig.add_subplot(2,1,i+1, title = subplotLabels[i][0], label = subplotLabels[i][0])
            subplot.set_xlabel(subplotLabels[i][1])
            subplot.set_ylabel(subplotLabels[i][2])
            self.subplots[subplotLabels[i][0]] = subplot 
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)

    
        self.SetSizer(sizer)
        self.Fit()
        
        
        self.ltop = None
        self.lbottom = None
        self.pickedArtist = None
        self.lbottomRect1 = None
        self.lbottomRect2 = None
        self.ltopRect1 = None
        self.ltopRect2 = None
        #color = parent.GetThemeBackgroundColour()
        #self.SetColor(color)
        
#        tst = range(0,100)
#        tst2 = range(0,100)
#        self._plotGuinier(tst, tst2)
#        self._plotData(tst, tst2)

    def onMotionEvent(self, evt):
        
        if self.pickedArtist:
            a = evt.xdata
            
            if a != None:
                findClosest=lambda a,l:min(l,key=lambda x:abs(x-a))
            
                
                lx = self.subplots['Data'].get_lines()[0].get_xdata()
                ly = self.subplots['Data'].get_lines()[0].get_ydata()
            
                closest = findClosest(a,lx)
            
                idx = np.where(lx == closest)
            
                controlPanel = wx.FindWindowByName('GuinierControlPanel')
            
                if self.pickedArtist.get_label() == 'top':
                    self.drawTopLimit(lx[idx][0], ly[idx][0])
                    controlPanel.updateLimits(top = idx)
            
                elif self.pickedArtist.get_label() == 'bottom': 
                    self.drawBottomLimit(lx[idx][0], ly[idx][0])
                    controlPanel.updateLimits(bottom = idx)
        

    def onMouseReleaseEvent(self, evt):
                
        if self.pickedArtist:
            self.pickedArtist = None

    def onPick(self, evt):
        
        self.pickedArtist = evt.artist
        
        self.canvas.draw()
        
        
    def _plotGuinier(self, i, q):
        
        guinier_q = np.power(q,2)
        guinier_q[np.where(guinier_q<=0)]=1
        self.subplots['Guinier'].semilogy(guinier_q, i, '.')
        
        self.canvas.draw()
        
    def _plotData(self, i, q):
        
        self.subplots['Data'].plot(q, i, 'g.')
        
        self.canvas.draw()
        
    def plotExpObj(self, ExpObj):
        self._plotGuinier(ExpObj.i, ExpObj.q)
        self._plotData(ExpObj.i, ExpObj.q)
        
        #self.drawLimits()
    
    def drawLimits(self):
        
        self.drawTopLimit()
    
    def drawTopLimit(self, x, y):
        
        a = self.subplots['Data']
        
        if self.ltop:
            self.ltop.remove()
            self.ltopRect1.remove()
            self.ltopRect2.remove()
            
        x,y = a.transLimits.transform((x,y))
                
        #cir = Circle( (0.5, 0.5), 0.25, alpha = 0.5, picker = True, transform=a.transAxes)
        #a.axvspan(x[30]-0.01*x[30], x[30]+0.01*x[30], facecolor='r', alpha=0.5, picker = True)

        self.ltop = matplotlib.lines.Line2D([x,x], [y-0.1,y+0.1], transform=a.transAxes, linewidth = 2,
                                             color = 'r', picker = True, alpha = 0.8, label = 'top')
        
        self.ltopRect1 = Rectangle((x-0.0125, y+0.1), 0.025, 0.05, transform=a.transAxes, label = 'top', picker = True)
        self.ltopRect1.set_facecolor('red')
        self.ltopRect2 = Rectangle((x-0.0125, y-0.1), 0.025, 0.05, transform=a.transAxes, label = 'top', picker = True)
        self.ltopRect2.set_facecolor('red')
        
        a.add_artist(self.ltop)
        a.add_patch(self.ltopRect1)
        a.add_patch(self.ltopRect2)
        
        self.canvas.draw()

    def drawBottomLimit(self, x, y): 
        
        a = self.subplots['Data']
        
        if self.lbottom:
            self.lbottom.remove()
            self.lbottomRect1.remove()
            self.lbottomRect2.remove()
            
        x,y = a.transLimits.transform((x,y))

        #cir = Circle( (0.5, 0.5), 0.25, alpha = 0.5, picker = True, transform=a.transAxes)
        #a.axvspan(x[30]-0.01*x[30], x[30]+0.01*x[30], facecolor='r', alpha=0.5, picker = True)

        self.lbottom = matplotlib.lines.Line2D([x,x], [y-0.1,y+0.1], transform=a.transAxes, linewidth = 2,
                                                color = 'r', picker = True, alpha = 0.8, label = 'bottom')
        
        self.lbottomRect1 = Rectangle((x-0.0125, y+0.1), 0.025, 0.05, transform=a.transAxes, label = 'bottom', picker = True)
        self.lbottomRect1.set_facecolor('red')
        self.lbottomRect2 = Rectangle((x-0.0125, y-0.1), 0.025, 0.05, transform=a.transAxes, label = 'bottom', picker = True)
        self.lbottomRect2.set_facecolor('red')
        
        a.add_artist(self.lbottom)
        a.add_patch(self.lbottomRect1)
        a.add_patch(self.lbottomRect2)
        
        self.canvas.draw()
        
        
    def drawFit(self):
        
        
        fitfunc = lambda p, x: p[0] + p[1] * x
        errfunc = lambda p, x, y, err: (y - fitfunc(p, x)) / err
        
        pinit = [1.0, -1.0]
        out = optimize.leastsq(errfunc, pinit, args=(logx, logy, logyerr), full_output=1)


    
    def SetColor(self, rgbtuple = None):
        """ Set figure and canvas colours to be the same """
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
       
        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

class GuinierControlPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM)
         
         
        self.spinctrlIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.staticTxtIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
         
        controlSizer = self.createControls()
         
        self.SetSizer(controlSizer)
        
        self.ExpObj = None
        
    def setCurrentExpObj(self, ExpObj):
        
        self.ExpObj = ExpObj
 
    def createControls(self):
        
        sizer = wx.FlexGridSizer(rows = 1, cols = 4)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableCol(2)
        sizer.AddGrowableCol(3)
        
        sizer.Add(wx.StaticText(self,-1,'q_min'),1)
        sizer.Add(wx.StaticText(self,-1,'n_min'),1)
        sizer.Add(wx.StaticText(self,-1,'q_max'),1)
        sizer.Add(wx.StaticText(self,-1,'n_max'),1)
        
        self.startSpin = wx.SpinCtrl(self, self.spinctrlIDs['qstart'], size = (60,-1))
        self.endSpin = wx.SpinCtrl(self, self.spinctrlIDs['qend'], size = (60,-1))
        
        self.startSpin.Bind(wx.EVT_SPINCTRL, self.onSpinCtrl)
        self.endSpin.Bind(wx.EVT_SPINCTRL, self.onSpinCtrl)
        
        self.qstartTxt = wx.TextCtrl(self, self.staticTxtIDs['qstart'], 'q: ', size = (50, 10), style = wx.PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(self, self.staticTxtIDs['qend'], 'q: ', size = (50, 10), style = wx.PROCESS_ENTER)
        
        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        
        sizer.Add(self.qstartTxt, 1, wx.EXPAND)
        sizer.Add(self.startSpin, 1, wx.EXPAND)
        sizer.Add(self.qendTxt, 1, wx.EXPAND)
        sizer.Add(self.endSpin, 1, wx.EXPAND)
        
        return sizer
    
    def onEnterInQlimits(self, evt):
        
        id = evt.GetId()
        
        lx = self.ExpObj.q
        ly = self.ExpObj.i
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))

        txtctrl = wx.FindWindowById(id)
        
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if id == self.staticTxtIDs['qstart']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qstart'])
                txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],4)))
                return
            
            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'])
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],4)))
                return
            
        
        plotpanel = wx.FindWindowByName('GuinierPlotPanel')
            
        closest = findClosest(val,lx)
            
        idx = np.where(lx == closest)[0][0]
        
        if id == self.staticTxtIDs['qstart']:
            spinctrl = wx.FindWindowById(self.spinctrlIDs['qstart'])
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
            plotpanel.drawTopLimit(lx[idx],ly[idx])

        elif id == self.staticTxtIDs['qend']:
            spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'])
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            plotpanel.drawBottomLimit(lx[idx],ly[idx])
            
        spinctrl.SetValue(idx)
        txt.SetValue(str(round(self.ExpObj.q[idx],4)))
        
    def setSpinLimits(self, ExpObj):
        self.startSpin.SetRange(0, len(ExpObj.q)-1)
        self.endSpin.SetRange(0, len(ExpObj.q)-1)
        
        self.endSpin.SetValue(len(ExpObj.q)-1)
        txt = wx.FindWindowById(self.staticTxtIDs['qend'])
        txt.SetValue(str(round(ExpObj.q[int(len(ExpObj.q)-1)],4)))
        txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
        txt.SetValue(str(round(ExpObj.q[0],4)))
        
        
        
    def onSpinCtrl(self, evt):
        
        id = evt.GetId()
        
        spin = wx.FindWindowById(id)
         
        if id == self.spinctrlIDs['qstart']:
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
        elif id == self.spinctrlIDs['qend']:
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            
        i = spin.GetValue()
        txt.SetValue(str(round(self.ExpObj.q[int(i)],4)))
        
        plotpanel = wx.FindWindowByName('GuinierPlotPanel')
        a = plotpanel.subplots['Data']
        
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i = int(spinstart.GetValue())
        
        x = a.get_lines()[0].get_xdata()
        y = a.get_lines()[0].get_ydata()
        
        plotpanel.drawTopLimit(x[i],y[i])
        
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i = int(spinend.GetValue())
        
        plotpanel.drawBottomLimit(x[i],y[i])
    
    def updateLimits(self, top = None, bottom = None):
  
        if bottom:
            bottom = bottom[0][0]
            spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
            spinend.SetValue(bottom)
            txt = wx.FindWindowById(self.staticTxtIDs['qend'])
            txt.SetValue(str(round(self.ExpObj.q[int(bottom)],4)))
            
        if top:
            top = top[0][0]
            spinend = wx.FindWindowById(self.spinctrlIDs['qstart'])
            spinend.SetValue(top)
            txt = wx.FindWindowById(self.staticTxtIDs['qstart'])
            txt.SetValue(str(round(self.ExpObj.q[int(top)],4)))
                         
class GuinierTestFrame(wx.Frame):
    
    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title, name = 'TestFrame')
        
        splitter1 = wx.SplitterWindow(self, -1)
                
        plotPanel = GuinierPlotPanel(splitter1, -1, 'GuinierPlotPanel')
        controlPanel = GuinierControlPanel(splitter1, -1, 'GuinierControlPanel')
  
        splitter1.SplitVertically(controlPanel, plotPanel, 270)
        splitter1.SetMinimumPaneSize(50)
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(1)
        #self.statusbar.SetStatusWidths([-3, -2])
                
        expParams = {
             'NormalizeConst'    : 1.0,
             'NormalizeConstChk' : False,
             'NormalizeM2'       : False,
             'NormalizeTime'     : False,
             'NormalizeM1'       : False, 
             'NormalizeAbs'      : False,
             'NormalizeTrans'    : False,
             'Calibrate'         : False,         # Calibrate AgBe
             'CalibrateMan'      : False,        # Calibrate manual (wavelength / distance)
             'AutoBgSubtract'    : False,
             'AutoBIFT'          : False,
             
             #CENTER / BINNING
             'Binsize'    : 2,
             'Xcenter'    : 556.0,
             'Ycenter'    : 544.0,
             'QrangeLow'  : 25,
             'QrangeHigh' : 9999,
             'PixelCalX'  : 200,
             'PixelCalY'  : 200,
             
             #MASKING
             'SampleFile'              : None,
             'BackgroundFile'          : None,
             'BeamStopMask'            : None,
             'BeamStopMaskFilename'    : None,
             'BeamStopMaskParams'      : None,
             'ReadOutNoiseMask'        : None,
             'ReadOutNoiseMaskFilename': None,
             'ReadOutNoiseMaskParams'  : None,
             'WaterFile'               : None,
             'EmptyFile'               : None,
             'FlatFieldFile'           : None,
             
             #Q-CALIBRATION
             'WaveLength'          : 0.0,
             'SampleDistance'      : 0.0,
             'SampleThickness'     : 0.0,
             'BgPatternType'       : 'contain',
             'BgPatternValue'      : '',
             'ReferenceQ'          : 0.0,
             'ReferenceDistPixel'  : 0,
             'ReferenceDistMm'     : 0.0,
             'DetectorPixelSize'   : 0.0,
             'SmpDetectOffsetDist' : 0.0,
             'WaterAvgMinPoint'    : 30,
             'WaterAvgMaxPoint'    : 500,
             
             #DEFAULT BIFT PARAMETERS
             'maxDmax'     : 400.0,
             'minDmax'     : 10.0,
             'DmaxPoints'  : 10,
             'maxAlpha'    : 1e10,
             'minAlpha'    : 150.0,
             'AlphaPoints' : 16,
             'PrPoints'    : 50,
             
             #ARTIFACT REMOVAL:
             'ZingerRemoval'     : False,
             'ZingerRemoveSTD'   : 4,
             'ZingerRemoveWinLen': 10,
             'ZingerRemoveIdx'   : 10,
             
             'ZingerRemovalAvgStd'  : 8,
             'ZingerRemovalAvg'     : False,
             
             #SAVE DIRECTORIES
             'ReducedFilePath'      : ' ',
             'AutoSaveOnImageFiles' : False,
             'AutoSaveOnAvgFiles'   : False,
             
             #IMAGE FORMATS
             #See advancedOptionsGUI ['Quantum 210, CHESS', 'MarCCD 165, MaxLab', 'Medoptics, CHESS', 'FLICAM, CHESS']
             'ImageFormat'          : 'Quantum 210, CHESS',
                 
             'CurveOffsetVal'        : 0.0,
             'OffsetCurve'           : False,
             'CurveScaleVal'         : 1.0,
             'ScaleCurve'            : False
             }
    
        ExpObj, ImgDummy = fileIO.loadFile('lyzexp.dat')
        
        plotPanel.plotExpObj(ExpObj)
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)
  
    
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)

class OverviewTestApp(wx.App):
    
    def OnInit(self):
        
        frame = GuinierTestFrame('Guinier Fit', -1)
        self.SetTopWindow(frame)
        frame.SetSize((800,600))
        frame.CenterOnScreen()
        frame.Show(True)
        
        return True
        
if __name__ == "__main__":
    app = OverviewTestApp(0)   #MyApp(redirect = True)
    app.MainLoop()
