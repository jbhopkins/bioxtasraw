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
import fileIO, sys
from scipy import linspace, polyval, polyfit, sqrt, stats, randn


class GuinierPlotPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, wxEmbedded = False):
        
        wx.Panel.__init__(self, parent, panel_id, name = name, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
        
        self.i = None
        self.q = None
        
        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
                
        self.canvas.mpl_connect('motion_notify_event', self.onMotionEvent)
#        self.canvas.mpl_connect('button_press_event', self.onMouseButtonPressEvent)
        self.canvas.mpl_connect('button_release_event', self.onMouseReleaseEvent)
        self.canvas.mpl_connect('pick_event', self.onPick)
#        self.canvas.mpl_connect('key_press_event', self.onKeyPressEvent)
        
        #self.toolbar = MaskingPanelToolbar(self, self.canvas)
        subplotLabels = [('Guinier', 'q^2', 'ln(I(q)'), ('Error', 'q', 'I(q)')]
        
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
        self.Fit()
        
        self.ltop = None
        self.lbottom = None
        self.pickedArtist = None
        self.lbottomRect1 = None
        self.lbottomRect2 = None
        self.ltopRect1 = None
        self.ltopRect2 = None
        
        self.lfitbottom = None
        self.lfittop = None
        self.limits = None
        
        self.bottomlimit = None
        self.toplimit = None
        
        self.figlim = None
        self.interpline = None
        self.fitline = None
        
        self.SetColor()

    def onMotionEvent(self, evt):
        
        if self.pickedArtist:
            a = evt.xdata
            
            if a != None:
                findClosest=lambda a,l:min(l,key=lambda x:abs(x-a))
            
                lx = np.power(self.q,2)
                ly = self.i
            
                closest = findClosest(a,lx)
            
                idx = np.where(lx == closest)
            
                idx = idx[0][0]
            
                controlPanel = wx.FindWindowByName('GuinierControlPanel')
            
                if self.pickedArtist.get_label() == 'top':
                    controlPanel.updateLimits(top = idx)
                    self.drawTopLimit(lx[idx], ly[idx])
                    self.drawBottomLimit(lx[self.bottomlimit], ly[self.bottomlimit])
                    self.toplimit = idx
                    self.updateFigureLimits()
            
                elif self.pickedArtist.get_label() == 'bottom': 
                    self.drawBottomLimit(lx[idx], ly[idx])
                    self.drawTopLimit(lx[self.toplimit], ly[self.toplimit])
                    controlPanel.updateLimits(bottom = idx)
                    self.bottomlimit = idx
                    self.updateFigureLimits()
        

    def onMouseReleaseEvent(self, evt):
                
        if self.pickedArtist:
            self.pickedArtist = None
            controlPanel = wx.FindWindowByName('GuinierControlPanel')
            self.setLimits(controlPanel.getLimits())
            
            a = self.subplots['Guinier']
            
           
            lims = a.get_xlim()
            #self.updateGuinierPlot()
            #if self.fitline:
            #    self.fitline.remove()
            
            self.drawFit()
            a.set_xlim(lims)

    def onPick(self, evt):
        
        self.pickedArtist = evt.artist
        
        self.canvas.draw()
        
    def updateFigureLimits(self):
    
        a = self.subplots['Guinier']
            
        x = np.power(self.q,2)
         
        dist = len(self.q[0:self.toplimit])
        dist2 = len(self.q[self.bottomlimit:])-1
        
        if dist > 5:
            toplim = self.toplimit-5
        else:
            toplim = self.toplimit-dist
            
        if dist2 > 5:
            botlim = self.bottomlimit+5
        else:
            botlim = self.bottomlimit+dist2
             
        self.figlim = (x[toplim], x[botlim])
        
        self.toplimit = toplim
        self.bottomlimit = botlim
        
        a.set_xlim((x[toplim], x[botlim]))
        
        self.canvas.draw()
            
#            try:
#                pre = len(self.q[0:tlim])
#                post = len(self.q[blim:])
#
#            if pre >= 5 and post >=5:
#                xp = np.power(self.q[tlim-5:blim+5],2)
#                yp = np.log(self.i[tlim-5:blim+5])
#            else:
#                xp = np.power(self.q[tlim-pre:blim],2)
#                yp = np.log(self.i[tlim-pre:blim])
#        except:
#            xp = x
#            yp = y
            
        
    def _plotGuinier(self, i, q):
        
        self.i = i
        self.q = q
        
        controlPanel = wx.FindWindowByName('GuinierControlPanel')
        
        self.setLimits(controlPanel.getLimits())
        
        
        x = np.power(self.q,2)
        y = np.log(self.i)
        
        x = x[np.where(np.isnan(y)==False)]
        y = y[np.where(np.isnan(y)==False)]
        
        x = x[np.where(np.isinf(y)==False)]
        y = y[np.where(np.isinf(y)==False)]
        
        self.subplots['Guinier'].plot(x, y, 'b.')
        
        self.canvas.draw()
        
    def updateGuinierPlot(self):
        
        tlim = self.limits[0]
        blim = self.limits[1]
        
        if self.interpline:
            self.interpline.remove()
            
   
        
        #self.subplots['Guinier'].plot(guinier_q[tlim:blim], np.log(i)[tlim:blim], '.')
        self.drawFit()
#        self.updateFigureLimits()
        self.canvas.draw()
        
#    def _plotData(self, i, q):
#        
#        self.subplots['Data'].plot(np.power(q,2), np.log(i), 'g.')
#        self.canvas.draw()
#        
    def plotExpObj(self, ExpObj):        
        self._plotGuinier(ExpObj.i, ExpObj.q)
        
        #self._plotData(ExpObj.i, ExpObj.q)
        
        controlPanel = wx.FindWindowByName('GuinierControlPanel')
        self.limits = controlPanel.getLimits()
                
        self.toplimit = 0
        self.bottomlimit = len(ExpObj.q)-1
        
        #self.drawFit()
        
        #self.drawLimits()
    
    def drawLimits(self, x,y):
        
        self.drawTopLimit(x,y)
        self.drawBottomLimit(x, y)
    
    def drawTopLimit(self, x, y):
        
        a = self.subplots['Guinier']
        
        if self.ltop:
            self.ltop.remove()

        y = np.log(y)
        
        if np.isnan(y) or np.isinf(y):
            y = 0
        
        x,y = a.transLimits.transform((x,y))
                
        self.ltop = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
                                             color = 'r', picker = 6, alpha = 1, label = 'top', linestyle = '--')

        a.add_artist(self.ltop)

        self.canvas.draw()

    def drawBottomLimit(self, x, y): 
        
        a = self.subplots['Guinier']
        
        if self.lbottom:
            self.lbottom.remove()
                      
        y = np.log(y)
        
        if np.isnan(y) or np.isinf(y):
            y = 0
         
        x,y = a.transLimits.transform((x,y))

        self.lbottom = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
                                                color = 'r', picker = 6, alpha = 1, label = 'bottom', linestyle = '--')
        
        a.add_artist(self.lbottom)

        self.canvas.draw()
        
    def drawFitLimits(self, xall, yall):
        
        a = self.subplots['Guinier']
        
        if self.lfitbottom:
            self.lfitbottom.remove()
            self.lfittop.remove()

        x,y = a.transLimits.transform((xall[1],yall[1]))

        self.lfitbottom = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
                                                color = 'r', picker = 6, alpha = 1, label = 'bottom')
        
        x,y = a.transLimits.transform((xall[0],yall[0]))

        self.lfittop = matplotlib.lines.Line2D([x,x], [y-0.2,y+0.2], transform=a.transAxes, linewidth = 1,
                                                color = 'r', picker = 6, alpha = 1, label = 'top')
        
        
        a.add_artist(self.lfitbottom)
        a.add_artist(self.lfittop)
        
        self.canvas.draw()
    
    def drawError(self, x, error):
                
        a = self.subplots['Error']
        
        for each in a.get_lines():
            each.remove()
        
        a.plot(x, error, 'b')
        
        zeroline = np.zeros((1,len(x)))
    
        a.plot(x, zeroline[0], 'r')
        
        a.set_xlim((x[0], x[-1]))
        a.set_ylim((error.min(), error.max()))
    
    def drawFit(self):
    
        #fitfunc = lambda p, x: p[0] + p[1] * x
        #errfunc = lambda p, x, y, err: (y - fitfunc(p, x)) / err
        
        #pinit = [1.0, -1.0]
        #out = optimize.leastsq(errfunc, pinit, args=(logx, logy, logyerr), full_output=1)

        tlim = self.limits[0]
        blim = self.limits[1]

        #x = self.subplots['Guinier'].get_lines()[0].get_xdata()
        #y = self.subplots['Guinier'].get_lines()[0].get_ydata()
        
        x = np.power(self.q[tlim:blim+1],2)
        y = np.log(self.i[tlim:blim+1])
        
        x = x[np.where(np.isnan(y)==False)]
        y = y[np.where(np.isnan(y)==False)]
        
        x = x[np.where(np.isinf(y)==False)]
        y = y[np.where(np.isinf(y)==False)]
               
        (ar,br) = polyfit(x,y, 1)

        yr = polyval([ar , br], x)
        
        error = y-yr
        
        SS_tot = np.sum(np.power(y-np.mean(y),2))
        SS_err = np.sum(np.power(error,2))
        rsq = 1 - SS_err / SS_tot
        
        a = self.subplots['Guinier']
        
        self.I0 = br
        self.Rg = np.sqrt(-3*ar)
        if np.isnan(self.Rg):
            self.Rg = 0
        
        N = len(error)
        stde = SS_err / (N-2)
        std_slope = stde * np.sqrt( (1/N) +  (np.power(np.mean(x),2)/np.sum(np.power(x-np.mean(x),2))))
        std_interc = stde * np.sqrt(  1 / np.sum(np.power(x-np.mean(x),2)))
        
        if np.isnan(std_slope):
            std_slope = -1
        if np.isnan(std_interc):
            std_interc = -1
        
        newInfo = {'I0' : (np.exp(self.I0), std_interc),
                   'Rg' : (self.Rg, std_slope),
                   'qRg': self.Rg * np.sqrt(x[-1]),
                   'rsq': rsq}
                                                      
        controlPanel = wx.FindWindowByName('GuinierControlPanel')
        controlPanel.updateInfo(newInfo)
        
        #print 'qRg: ', self.Rg * np.sqrt(x[-1])
        #print 'I0: ', np.exp(self.I0)
        #print 'Rg: ', self.Rg
        
        xg = [0, x[0]]
        yg = [self.I0, yr[0]]
        
        xfull = np.power(self.q,2)
        yfull = np.log(self.i)
        
        xf = xfull[np.where(np.isnan(yfull)==False)]
        yf = yfull[np.where(np.isnan(yfull)==False)]
        
        #self.interpline = a.plot(xg, yg, 'r--')
        #self.fitline = a.plot(x, yr, 'r')
        
        #self.updateFigureLimits()
        
        if self.fitline != None:
            self.fitline.remove()

        self.fitline = matplotlib.lines.Line2D(x, yr, linewidth = 1, color = 'r', alpha = 1)
        a.add_artist(self.fitline)
        
        self.interpline = matplotlib.lines.Line2D(xg, yg, linewidth = 1, color = 'g', linestyle = '--', alpha = 1)
        a.add_artist(self.interpline)
               
        #a.set_xlim((0, xp[-1]))
        #a.set_ylim(np.min([yr.min(), yp.min()]), np.max([y.max(), self.I0]))
                
        self.drawError(x, error)
        
        self.canvas.draw_idle()
    
    def SetColor(self, rgbtuple = None):
        """ Set figure and canvas colours to be the same """
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
       
        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

    def setLimits(self, limits):
        self.limits = limits
        
        self.bottomlimit = limits[1]
        self.toplimit = limits[0]
        
class GuinierControlPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name):

        wx.Panel.__init__(self, parent, panel_id, name = name,style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)
          
        self.spinctrlIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.staticTxtIDs = {'qstart' : wx.NewId(),
                            'qend'   : wx.NewId()}
        
        self.infodata = {'I0' : ('I0 :', wx.NewId(), wx.NewId()),
                         'Rg' : ('Rg :', wx.NewId(), wx.NewId()),
                         'qRg': ('qRg :', wx.NewId()),
                         'rsq': ('r^2 (fit) :', wx.NewId())}
        
 
        controlSizer = self.createControls()
        infoSizer = self.createInfoBox()
        
        bsizer = wx.BoxSizer(wx.VERTICAL)
        
        button = wx.Button(self, -1, 'Close')
        button.Bind(wx.EVT_BUTTON, self.onCloseButton)
        
        savebutton = wx.Button(self, -1, 'Save info')
        savebutton.Bind(wx.EVT_BUTTON, self.onSaveInfo)
        
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(button, 1, wx.EXPAND)
        buttonSizer.Add(savebutton, 1, wx.EXPAND)
        
        box = wx.StaticBox(self, -1, 'Parameters')
        boxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        boxSizer.Add(infoSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        
        box2 = wx.StaticBox(self, -1, 'Control')
        boxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        boxSizer2.Add(controlSizer, 0, wx.EXPAND)
        
        bsizer.Add(boxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        bsizer.Add(boxSizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        bsizer.Add(buttonSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT| wx.TOP, 5)
         
        self.SetSizer(bsizer)
        
        self.ExpObj = None
        
    def onSaveInfo(self, evt):
        
        wx.MessageBox('The parameters has now been saved into the file header', 'Info')
        
        
        
        
    def onCloseButton(self, evt):
        
        diag = wx.FindWindowByName('GuinierFrame')
        diag.OnClose()
        
        
    def setCurrentExpObj(self, ExpObj):
        
        self.ExpObj = ExpObj
        self.onSpinCtrl(self.startSpin)
        
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
                ctrl2 = wx.TextCtrl(self, self.infodata[key][2], '0', size = (60,21))
                txtpm = wx.StaticText(self, -1, u"\u00B1")
                
                
                bsizer = wx.BoxSizer()
                bsizer.Add(ctrl1,0,wx.EXPAND)
                bsizer.Add(txtpm,0, wx.LEFT | wx.TOP, 3)
                bsizer.Add(ctrl2,0,wx.EXPAND | wx.LEFT, 3)
                
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
        
        self.startSpin = wx.SpinCtrl(self, self.spinctrlIDs['qstart'], size = (60,-1))
        self.endSpin = wx.SpinCtrl(self, self.spinctrlIDs['qend'], size = (60,-1))
        
        self.startSpin.Bind(wx.EVT_SPINCTRL, self.onSpinCtrl)
        self.endSpin.Bind(wx.EVT_SPINCTRL, self.onSpinCtrl)
        
        self.qstartTxt = wx.TextCtrl(self, self.staticTxtIDs['qstart'], 'q: ', size = (50, 10), style = wx.PROCESS_ENTER)
        self.qendTxt = wx.TextCtrl(self, self.staticTxtIDs['qend'], 'q: ', size = (50, 10), style = wx.PROCESS_ENTER)
        
        self.qstartTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        self.qendTxt.Bind(wx.EVT_TEXT_ENTER, self.onEnterInQlimits)
        
        sizer.Add(self.qstartTxt, 1, wx.EXPAND | wx.LEFT, 5)
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
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
                return
            
            if id == self.staticTxtIDs['qend']:
                spinctrl = wx.FindWindowById(self.spinctrlIDs['qend'])
                txt = wx.FindWindowById(self.staticTxtIDs['qend'])
                idx = int(spinctrl.GetValue())
                txt.SetValue(str(round(self.ExpObj.q[idx],5)))
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
        
        self.updatePlot()
        
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
        
        self.updatePlot()
        
    def updatePlot(self):
        plotpanel = wx.FindWindowByName('GuinierPlotPanel')
        a = plotpanel.subplots['Guinier']
        
        spinstart = wx.FindWindowById(self.spinctrlIDs['qstart'])
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i = int(spinstart.GetValue())
        
        x = np.power(self.ExpObj.q,2)
        y = self.ExpObj.i
        
        plotpanel.drawTopLimit(x[i],y[i])
        
        spinend = wx.FindWindowById(self.spinctrlIDs['qend'])
        
        i2 = int(spinend.GetValue())
        
        plotpanel.drawBottomLimit(x[i2],y[i2])        
        plotpanel.setLimits([i,i2])
        
        plotpanel.updateGuinierPlot()
        
        #self.updatePlot()
        plotpanel.updateFigureLimits()
        
        plotpanel.drawBottomLimit(x[i2],y[i2])
        plotpanel.drawTopLimit(x[i],y[i])
        
    def updateInfo(self, newInfo):
        
        for eachkey in newInfo.iterkeys():
            
            if len(self.infodata[eachkey]) == 2: 
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey],5)))
            else:
                ctrl = wx.FindWindowById(self.infodata[eachkey][1])
                ctrl.SetValue(str(round(newInfo[eachkey][0],5)))
                
                ctrlerr = wx.FindWindowById(self.infodata[eachkey][2])
                ctrlerr.SetValue(str(round(newInfo[eachkey][1],5)))
             
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
        
class GuinierFitDialog(wx.Dialog):

    def __init__(self, parent, ExpObj):
        wx.Dialog.__init__(self, parent, -1, 'Guinier Fit', name = 'GuinierDialog', size = (800,600))
    
        splitter1 = wx.SplitterWindow(self, -1)
     
        controlPanel = GuinierControlPanel(splitter1, -1, 'GuinierControlPanel')
        plotPanel = GuinierPlotPanel(splitter1, -1, 'GuinierPlotPanel')
  
        splitter1.SplitVertically(controlPanel, plotPanel, 270)
        splitter1.SetMinimumPaneSize(50)
    
        plotPanel.plotExpObj(ExpObj)
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)

    def OnClose(self):
        
        self.Destroy()
        
                         
class GuinierTestFrame(wx.Frame):
    
    def __init__(self, parent, title, ExpObj):
        
        try:
            wx.Frame.__init__(self, parent, -1, title, name = 'GuinierFrame', size = (800,600))
        except:
            wx.Frame.__init__(self, None, -1, title, name = 'GuinierFrame', size = (800,600))
        
        splitter1 = wx.SplitterWindow(self, -1)
                
        controlPanel = GuinierControlPanel(splitter1, -1, 'GuinierControlPanel')
        plotPanel = GuinierPlotPanel(splitter1, -1, 'GuinierPlotPanel')
  
        splitter1.SplitVertically(controlPanel, plotPanel, 270)
        splitter1.SetMinimumPaneSize(50)
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(1)
        #self.statusbar.SetStatusWidths([-3, -2])

        plotPanel.plotExpObj(ExpObj)
        controlPanel.setSpinLimits(ExpObj)
        controlPanel.setCurrentExpObj(ExpObj)
        
        self.CenterOnScreen()
    
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)
        
    def OnClose(self):
        
        self.Destroy()
        
class OverviewTestApp(wx.App):
    
    def OnInit(self, filename = None):
        
        #ExpObj, ImgDummy = fileIO.loadFile('/home/specuser/Downloads/BSUB_MVMi7_5_FULL_001_c_plot.rad')
        
        if filename:
            ExpObj, ImgDummy = fileIO.loadFile(filename)
        else:
            ExpObj, ImgDummy = fileIO.loadFile('lyzexp.dat')
        
        
        frame = GuinierTestFrame(self, 'Guinier Fit', ExpObj)
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
    
    app = OverviewTestApp(0, filename)   #MyApp(redirect = True)
    app.MainLoop()
