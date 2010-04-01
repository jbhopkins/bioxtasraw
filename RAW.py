#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BioXTAS RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BioXTAS RAW.  If not, see <http://www.gnu.org/licenses200/>.
#
#******************************************************************************
from __future__ import division
import sys, os, cPickle, threading, re, math#, gc, time
import matplotlib
matplotlib.rc('image', origin='lower')           # This turns the image upside down!!
                                                #  but x and y will start from zero in the lower left corner 

from pylab import setp

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg #,Toolbar 
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

from matplotlib.font_manager import FontProperties
import matplotlib.cbook as cbook

from numpy import power, zeros, shape, transpose, array

import wx.lib.scrolledpanel as scrolled
import wx.animate
import wx.html
from wx.lib.wordwrap import wordwrap

#Needs to be imported for cPickle to load mask files
#... Strange... :
from masking import CircleMask, RectangleMask, PolygonMask
# comment
import copy
import fileIO
import masking
import cartToPol
import AutoAnalysisGUI
import advancedOptionsGUI
import Queue
import overview
import guinierGUI
import cProfile


global MAINFRAME_ID

BGFILENAME_ID = wx.NewId()

global expParams

#DEFAULT PARAMETERS:
expParams = {
             'NormalizeConst'    : 1.0,
             'NormalizeConstChk' : False,
             'NormalizeM2'       : False,
             'NormalizeTime'     : False,
             'NormalizeM1'       : False, 
             'NormalizeAbs'      : False,
             'NormalizeTrans'    : False,
             'Calibrate'         : False,        # Calibrate AgBe
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
             
             #DEFAULT GNOM PARAMETERS
             'gnomMaxAlpha'    : 60,
             'gnomMinAlpha'    : 0.01,
             'gnomAlphaPoints' : 100,
             'gnomPrPoints'    : 50,
             'gnomFixInitZero' : True,
             
             'OSCILLweight'    : 3.0,
             'VALCENweight'    : 1.0,
             'POSITVweight'    : 1.0,
             'SYSDEVweight'    : 3.0,
             'STABILweight'    : 3.0,
             'DISCRPweight'    : 1.0,
             
             #DEFAULT IFT PARAMETERS:
             'IFTAlgoList'        : ['BIFT', 'GNOM'],
             'IFTAlgoChoice'      : 'BIFT',
             
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

#File extensions that are ignored when in OnlineMode
generalParams = {'OnlineExcludedFileTypes' : ['.rad', '.hdr', '.dat', '.cts']}

plotParams = {'LegendLocation' : (1,0)}

plotQueue = Queue.Queue(0)
bgSubPlotQueue = Queue.Queue(0)
autoBgSubQueue = Queue.Queue(0)
#loadMaskQueue = Queue.Queue(0)

def getGeneralParameters():
    return generalParams

def getTreatmentParameters():
    
    P = []
    
    if expParams['NormalizeConstChk']:
        P.append('NormalizeConstChk')
    if expParams['NormalizeM2']:
        P.append('NormalizeM2')
    if expParams['NormalizeTime']:
        P.append('NormalizeTime')
    if expParams['NormalizeM1']:
        P.append('NormalizeM1')
    if expParams['Calibrate']:
        P.append('Calibrate')
    if expParams['OffsetCurve']:
        P.append('OffsetCurve')
    if expParams['ScaleCurve']:
        P.append('ScaleCurve')
        
    # For backwards compatibility:
    try:
        if expParams['CalibrateMan']:
            P.append('CalibrateMan')
    except KeyError:
        expParams['CalibrateMan'] = False
    
    try:
        if expParams['NormalizeAbs']:
            P.append('NormalizeAbs')
    except KeyError:
        expParams['NormalizeAbs'] = False
        
    try:
        if expParams['NormalizeTrans']:
            P.append('NormalizeTrans')
    except KeyError:
        expParams['NormalizeTrans'] = False
       
    return P

class ManipItemEvent(wx.PyCommandEvent):
    
    def __init__(self, evtType, id, value = None):
        
        wx.PyCommandEvent.__init__(self, evtType, id)
        
        self.value = value
        
    def GetValue(self):
        return self.value
    
    def SetValue(self, value):
        self.value = value
        
myEVT_MANIP_ITEM = wx.NewEventType()
EVT_MANIP_ITEM = wx.PyEventBinder(myEVT_MANIP_ITEM, 1)


# QUEUING Call from threads:
#import Queue
#
#q = Queue.Queue()
#
#def _process():
#    fcn, args, kwargs = q.get()
#    fcn(*args, **kwargs)
#
#def CallAfter(fcn, *args, **kwargs):
#    q.put((fcn, args, kwargs))
#    wx.CallAfter(_process)


#---- *** Worker Threads ***

class PlotWorkerThread(threading.Thread):
    
    def __init__(self, parent, pgthread, setBackground = False):
        
        threading.Thread.__init__(self)
        
        self._parent = parent
        self._pgthread = pgthread
        self._setBackground = setBackground

    def run(self):
        
        while True:
            
            selectedFiles = plotQueue.get() # Blocks until a new item is available in the queue
        
            dirCtrlPanel = wx.FindWindowByName('DirCtrlPanel')
            plotpanel = wx.FindWindowByName('PlotPanel')
            biftplotpanel = wx.FindWindowByName('BIFTPlotPanel')
            mainframe_window = wx.FindWindowByName('MainFrame')
        
            selectedFiles = dirCtrlPanel.GetSelectedFile()
        
            for eachSelectedFile in selectedFiles:
                
#                cProfile.runctx("ExpObj, FullImage = fileIO.loadFile(eachSelectedFile, expParams)", globals(), locals())
                ExpObj, FullImage = fileIO.loadFile(eachSelectedFile, expParams)
                                                
                checkedTreatments = getTreatmentParameters()
                
                if ExpObj != None:
                    if ExpObj.i != []:
                    
                        cartToPol.applyDataManipulations(ExpObj, expParams, checkedTreatments)    # Only does something for images
            
                        if self._setBackground == True:
                            expParams['BackgroundFile'] = ExpObj
                            wx.CallAfter(dirCtrlPanel.SetBackgroundFile,eachSelectedFile)
                    
                        if ExpObj.type == 'bift':
                            biftplotpanel.PlotLoadedBift(ExpObj)
                        else:    
                            wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, ExpObj, axes = self._parent.subplot1)   
                            wx.CallAfter(plotpanel._setLabels, ExpObj, axes = self._parent.subplot1)
        
                        # For some unknown F*ing reason showing the image can make the program hang!
                        if FullImage and len(selectedFiles) == 1:
                            rawplot = wx.FindWindowByName('RawPlotPanel')
                            wx.CallAfter(rawplot.showImage, FullImage, ExpObj)
                            #rawplot.showImage( FullImage, ExpObj)
                        
                        if ExpObj.type != 'bift':
                            manipulationPage = wx.FindWindowByName('ManipulationPage')
                            evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObj)
                            wx.PostEvent(manipulationPage, evt)
        
                        wx.CallAfter(mainframe_window.SetStatusText,'Loading: ' + eachSelectedFile + '...Done!')    
                    
                        autoSave = expParams['AutoSaveOnImageFiles']
                    
                        if ExpObj.getFileType() == 'image' and autoSave:
                            dirctrlpanel = wx.FindWindowByName('DirCtrlPanel')                        
                            wx.CallAfter(dirctrlpanel.SaveSingleRadFile, ExpObj)

                    else:
                        wx.CallAfter(wx.MessageBox, 'Filename: ' + eachSelectedFile + '\nDoes not contain any recognisable data.\n\nIf you are trying to load an image,\nset the correct image format in Options.', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                else:
                    wx.CallAfter(wx.MessageBox, 'Filename: ' + eachSelectedFile + '\nDoes not contain any recognisable data.\n\nIf you are trying to load an image,\nset the correct image format in Options.', 'Load Failed!', wx.OK | wx.ICON_ERROR)
        
            wx.CallAfter(plotpanel._insertLegend, axes = self._parent.subplot1)
            
            plotQueue.task_done()
        
class BgSubPlotWorkerThread(threading.Thread):
    
    def __init__(self, parent, pgthread):
        
        threading.Thread.__init__(self)
        
        self._parent = parent
        self._pgthread = pgthread

    def run(self):
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        mainframe = wx.FindWindowByName('MainFrame')
        
        while True:
            
            selectedFiles, bgfilename = bgSubPlotQueue.get()

            #selectedFiles = wx.FindWindowByName('DirCtrlPanel').GetSelectedFile()
            #bgfilename = wx.FindWindowByName('DirCtrlPanel').GetBackgroundPath()
        
            ExpObjBackgrnd, FullImage = fileIO.loadFile(bgfilename, expParams)
        
            checkedTreatments = getTreatmentParameters()
            cartToPol.applyDataManipulations(ExpObjBackgrnd, expParams, checkedTreatments)
        
            for eachSelectedFile in selectedFiles:
            
                wx.CallAfter(mainframe.SetStatusText, 'Loading file..')    
                #self._pgthread.SetStatus('Loading file..')
            
                ExpObjSample, FullImage = fileIO.loadFile(eachSelectedFile, expParams)
            
                cartToPol.applyDataManipulations(ExpObjSample, expParams, checkedTreatments)
            
                ExpObjSample.param['filename'] = eachSelectedFile    
            
                ###################### Sample File Label Update: ###############
                #sampleFilenameTxt = wx.FindWindowById(SAMPLEFILENAME_ID)
                noPathSampleFilename = os.path.split(eachSelectedFile)[1]
                fullPathSample = os.path.split(eachSelectedFile)[0]
                #sampleFilenameTxt.SetLabel(noPathSampleFilename) 
                ################################################################
                noPathBackgrndFilename = os.path.split(bgfilename)[1]
                        
                wx.CallAfter(mainframe.SetStatusText, 'Subtracting and Plotting')    
            
                if len(ExpObjSample.i) == len(ExpObjBackgrnd.i):
#                    ExpObjSample = ExpObjSample.subtract(ExpObjBackgrnd)
                    ExpObjSample = cartToPol.subtractMeasurement(ExpObjSample, ExpObjBackgrnd)
                    
                    
                    ExpObjSample.param['filename'] = os.path.join(fullPathSample, 'BSUB_' + noPathSampleFilename)
                    
                    
                    wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, ExpObjSample, axes = self._parent.subplot2)
                    wx.CallAfter(plotpanel._setLabels, ExpObjSample, title = 'Background Subtracted Data', axes = self._parent.subplot2)
                    wx.CallAfter(plotpanel._insertLegend, eachSelectedFile, axes = self._parent.subplot2)
                
                    #plotpanel._PlotOnSelectedAxesScale(ExpObjSample, axes = self._parent.subplot2)
                    #plotpanel._setLabels(ExpObjSample, title = 'Background Subtracted Data', axes = self._parent.subplot2)
                    #plotpanel._insertLegend(eachSelectedFile, axes = self._parent.subplot2)
        
                    #Update figure:
                    wx.CallAfter(plotpanel.canvas.draw)
                
                    manipulationPage = wx.FindWindowByName('ManipulationPage')
                    evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObjSample)
                    wx.PostEvent(manipulationPage, evt)
        
                    wx.CallAfter(mainframe.SetStatusText, 'Loading: ' + eachSelectedFile + '...Done!')    
            
                else:
                    wx.MessageBox(noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
            
            bgSubPlotQueue.task_done()
        #Close progress dialog
        #self._pgthread.stop()
        
class AutoBgSubWorkerThread(threading.Thread):
    
    def __init__(self, parent, listOfFilePaths):
        
        threading.Thread.__init__(self)
        
        self._parent = parent
        #self._pgthread = pgthread
        self._listOfFilePaths = listOfFilePaths
        
        #self._pgthread = MyProgressBar(self._parent)
        
        self._plotOriginal = True
        
        global expParams
        self.expParams = expParams
        
    def run(self):
        
        #self._pgthread.run()
        while True:
        
            self._listOfFilePaths = autoBgSubQueue.get()
        
            manipulationPage = wx.FindWindowByName('ManipulationPage')
            plotpanel = wx.FindWindowByName('PlotPanel')
            ExpObjBackgrnd = expParams['BackgroundFile']
            mainframe = wx.FindWindowByName('MainFrame')
        
            if plotpanel.noOfPlots != 2:
                plotpanel.subplot2 = plotpanel.subplot1
            
            if ExpObjBackgrnd != None:
            
                for eachFile in self._listOfFilePaths:
        
                    #self._pgthread.SetStatus('Loading file..')
                
                    ExpObjSample, FullImage = fileIO.loadFile(eachFile, expParams)
                    checkedTreatments = getTreatmentParameters()
                    cartToPol.applyDataManipulations(ExpObjSample, expParams, checkedTreatments)
            
                    ExpObjSample.param['filename'] = eachFile
                
                #self._pgthread.SetStatus('Subtracting and Plotting')
                
                    if self._plotOriginal:
                        if len(ExpObjSample.i > 1):
                        
                            wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, ExpObjSample, plotpanel.subplot1)
                            wx.CallAfter(plotpanel._insertLegend, eachFile, axes = plotpanel.subplot1)
                        
                            evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObjSample)
                            wx.PostEvent(manipulationPage, evt)
                
                    #Check if they are of equal length before subtracting
                    if len(ExpObjSample.i) == len(ExpObjBackgrnd.i):
                    
                        ExpObjSample = ExpObjSample.subtract(ExpObjBackgrnd)
                        wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, ExpObjSample, plotpanel.subplot2)
                        wx.CallAfter(plotpanel._setLabels, ExpObjSample)
                        wx.CallAfter(plotpanel._insertLegend, eachFile, axes = plotpanel.subplot2)
                    
                        #Add plot to manipulation list
                        evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObjSample)
                        wx.PostEvent(manipulationPage, evt)
        
                        #Update status bar
                        wx.CallAfter(mainframe.SetStatusText, 'Loading: ' + eachFile + '...Done!')    
                    
                        if expParams['AutoBIFT'] == True:
                            #self._pgthread.stop()
                            biftThread = AutoAnalysisGUI.BiftCalculationThread(self, ExpObjSample)
                            biftThread.start()
            
                    else:
                        noPathSampleFilename = os.path.split(eachFile)[1]
                        noPathBackgrndFilename = ExpObjBackgrnd.param['filename']
                    
                        wx.CallAfter(wx.MessageBox, noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)

                #self._pgthread.SetStatus('Done')
       
            else:
                wx.CallAfter(wx.MessageBox, 'No background loaded!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
       
            autoBgSubQueue.task_done()
        #Close progress dialog
        
        #self._pgthread.stop()

#class LoadMaskThread(threading.Thread):
#    
#    def __init__(self, parent):
#        
#        threading.Thread.__init__(self)
#        
#        #self._masktype = masktype
#        #self._mask_fullpath = mask_fullpath
#        self._parent = parent
#        #self._pgthread = pgthread
#        #self._maskInExpParams = maskInExpParams
#        #self.expParams = expParams
#        #self.type = type
#        
#    def run(self):
#        
#        while True:
#        
#            self._mask_fullpath, self._masktype, self.expParams, self.type = loadMaskQueue.get()
#        
#            mainframe = wx.FindWindowByName('MainFrame')
#        
#            #self._pgthread.SetStatus('Loading Mask...')
#            wx.CallAfter(mainframe.SetStatusText, 'Loading mask...')    
#        
#            if self.type == None:
#                if self.expParams['BeamStopMaskParams'] != None:
#                    self.expParams['BeamStopMask'] = masking.createMaskFromRAWFormat(self.expParams['BeamStopMaskParams'])
#            
#                if expParams['ReadOutNoiseMaskParams'] != None:
#                    self.expParams['ReadOutNoiseMask'] = masking.createMaskFromRAWFormat(self.expParams['ReadOutNoiseMaskParams'])
#            else:
#                if self._masktype == 'readout':
#                    expParams['ReadOutNoiseMask'], expParams['ReadOutNoiseMaskParams'] = masking.loadMask(self._mask_fullpath)
#                    expParams['ReadOutNoiseMaskFilename'] = os.path.split(self._mask_fullpath)[1]
#                elif self._masktype == 'beamstop':
#                    expParams['BeamStopMask'], expParams['BeamStopMaskParams'] = masking.loadMask(self._mask_fullpath)
#                    expParams['BeamStopMaskFilename'] = os.path.split(self._mask_fullpath)[1]    
#        
#            wx.CallAfter(mainframe.SetStatusText, 'Loading mask... Done!')
#            
#            loadMaskQueue.task_done()    
#        
#        #self._pgthread.SetStatus('Done')
#        #self._pgthread.stop()
        
#---- *** My Progressbar ***               

class MyProgressBar:
    
    def __init__(self, parent):
        
        self.parent = parent
        self.progressDialog = MyProgressDialog()
        
    def run(self):
        self.progressDialog.Show()
    
    def stop(self):
        self.progressDialog.Close()
    
    def SetStatus(self, status):
        self.progressDialog.SetStatus(str(status))

class MyProgressDialog(wx.Dialog):
    
    def __init__(self):
        
        wx.Dialog.__init__(self, None, -1, size = (300,120))
        
        mainframe = wx.FindWindowByName('MainFrame')
        os.path.join(a)
        ag_fname = os.path.join(mainframe.RAWWorkDir, 'ressources', 'Bob2.gif')
        ag = wx.animate.GIFAnimationCtrl(self, -1, ag_fname)

        waitLabel = wx.StaticText(self, -1, 'Please Wait!')
        self.statusLabel = wx.StaticText(self, -1, 'Status')
        
        font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        self.statusLabel.SetFont(font)
        
        font = wx.Font(15, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        waitLabel.SetFont(font)
        
        self.statusSizer = wx.BoxSizer(wx.VERTICAL)
        self.statusSizer.Add(waitLabel, 0, wx.ALIGN_CENTER)
        self.statusSizer.Add(self.statusLabel, 0, wx.TOP | wx.ALIGN_CENTER, 10)
        
        sizer = wx.BoxSizer()
        sizer.Add(ag, 0, wx.CENTER | wx.LEFT, 25)
        sizer.Add(self.statusSizer, 0, wx.CENTER | wx.LEFT, 45)
        
        self.SetSizer(sizer)
        
        ag.GetPlayer().UseBackgroundColour(True)
        ag.Play()
        
    def SetStatus(self, status):
        self.statusLabel.SetLabel(status)
        self.statusSizer.Layout()
        
class MyCustomToolbar(NavigationToolbar2Wx):
    def __init__(self, parent, canvas):

        self.fig_axes = parent.fig.gca()
        self.parent = parent

        self.parent = parent
        
        #self._MTB_LOGLIN = wx.NewId()
        #self._MTB_LOGLOG = wx.NewId()
        #self._MTB_LINLIN = wx.NewId()
        self._MTB_ERRBARS = wx.NewId()
        self._MTB_LEGEND = wx.NewId()
        self._MTB_SHOWBOTH = wx.NewId()
        self._MTB_SHOWTOP = wx.NewId()
        
        self._MTB_CLR1 = wx.NewId()
        self._MTB_CLR2 = wx.NewId()
        
#        self.parent.subplot1.relim()
#        self.parent.subplot1.autoscale_view()
#        self.parent.subplot2.relim()
#        self.parent.subplot2.autoscale_view()
        self.parent.canvas.draw()
        self._MTB_SHOWBOTTOM = wx.NewId()
        
        NavigationToolbar2Wx.__init__(self, canvas)
        
        mainframe = wx.FindWindowByName('MainFrame')
        workdir = mainframe.RAWWorkDir

        #fitaxisIconFilename = os.path.join(workdir, "ressources","loglin.png")
        #loglinIconFilename = os.path.join(workdir, "ressources", "loglin.png")
        #loglogIconFilename = os.path.join(workdir, "ressources", "loglog.png")
        #linlinIconFilename = os.path.join(workdir, "ressources", "linlin.png")
        clear1IconFilename = os.path.join(workdir, "ressources" ,"clear1white.png")
        clear2IconFilename = os.path.join(workdir, "ressources" ,"clear2white.png")
        errbarsIconFilename = os.path.join(workdir, "ressources" ,"errbars.png")
        legendIconFilename = os.path.join(workdir, "ressources", "legend.png")
        showbothIconFilename = os.path.join(workdir, "ressources", "showboth.png")
        showtopIconFilename = os.path.join(workdir, "ressources", "showtop.png")
        showbottomIconFilename = os.path.join(workdir, "ressources", "showbottom.png")
        
        #fitaxis_icon = wx.Bitmap(fitaxisIconFilename, wx.BITMAP_TYPE_PNG)
        #loglin_icon = wx.Bitmap(loglinIconFilename, wx.BITMAP_TYPE_PNG)
        #loglog_icon = wx.Bitmap(loglogIconFilename, wx.BITMAP_TYPE_PNG)
        #linlin_icon = wx.Bitmap(linlinIconFilename, wx.BITMAP_TYPE_PNG)
        
        clear1_icon = wx.Bitmap(clear1IconFilename, wx.BITMAP_TYPE_PNG)
        clear2_icon = wx.Bitmap(clear2IconFilename, wx.BITMAP_TYPE_PNG)
        errbars_icon = wx.Bitmap(errbarsIconFilename, wx.BITMAP_TYPE_PNG)
        legend_icon = wx.Bitmap(legendIconFilename, wx.BITMAP_TYPE_PNG)
        showboth_icon = wx.Bitmap(showbothIconFilename, wx.BITMAP_TYPE_PNG)
        showtop_icon = wx.Bitmap(showtopIconFilename, wx.BITMAP_TYPE_PNG)
        showbottom_icon = wx.Bitmap(showbottomIconFilename, wx.BITMAP_TYPE_PNG)
        
#        self.parent.subplot1.relim()
#        self.parent.subplot1.autoscale_view()
#        self.parent.subplot2.relim()
#        self.parent.subplot2.autoscale_view()
        #self.parent.canvas.draw()ilename, wx.BITMAP_TYPE_PNG)

#        self.AddSeparator()
#        self.AddCheckTool(self._MTB_LOGLIN, loglin_icon)
#        self.AddCheckTool(self._MTB_LOGLOG, loglog_icon)
#        self.AddCheckTool(self._MTB_LINLIN, linlin_icon)
        self.AddSeparator()
        self.AddCheckTool(self._MTB_ERRBARS, errbars_icon, shortHelp='Show Errorbars')
        self.AddSimpleTool(self._MTB_LEGEND, legend_icon, 'Adjust Legend')
        self.AddSeparator()
        self.AddCheckTool(self._MTB_SHOWBOTH, showboth_icon, shortHelp='Show Both Plots')
        self.AddCheckTool(self._MTB_SHOWTOP, showtop_icon,  shortHelp='Show Top Plot')
        self.AddCheckTool(self._MTB_SHOWBOTTOM, showbottom_icon, shortHelp='Show Bottom Plot')
        self.AddSeparator()
        self.AddSimpleTool(self._MTB_CLR1, clear1_icon, 'Clear Top Plot')
        self.AddSimpleTool(self._MTB_CLR2, clear2_icon, 'Clear Bottom Plot')
        
#        self.Bind(wx.EVT_TOOL, self.loglin, id = self._MTB_LOGLIN)
#        self.Bind(wx.EVT_TOOL, self.loglog, id = self._MTB_LOGLOG)
#        self.Bind(wx.EVT_TOOL, self.linlin, id = self._MTB_LINLIN)
        self.Bind(wx.EVT_TOOL, self.clear1, id = self._MTB_CLR1)
        self.Bind(wx.EVT_TOOL, self.clear2, id = self._MTB_CLR2)
        self.Bind(wx.EVT_TOOL, self.errbars, id = self._MTB_ERRBARS)
        self.Bind(wx.EVT_TOOL, self.legend, id = self._MTB_LEGEND)
        self.Bind(wx.EVT_TOOL, self.showboth, id = self._MTB_SHOWBOTH)
        self.Bind(wx.EVT_TOOL, self.showtop, id = self._MTB_SHOWTOP)
        self.Bind(wx.EVT_TOOL, self.showbottom, id = self._MTB_SHOWBOTTOM)
        
        
        self.Realize()
        
        self.ErrorbarIsOn = False
        
        self.ToggleTool(self._MTB_SHOWBOTH, True)
    
    #Overriding the default home button commands:
    
#    def pan(self, *args):
#        self.ToggleTool(self._NTB2_ZOOM, False)
#        NavigationToolbar2.pan(self, *args)
#    
#    def zoom(self, *args):
#        self.ToggleTool(self._NTB2_PAN, False)
#        NavigationToolbar2.zoom(self, *args)
    
    def home(self, *args):
#        'restore the original view'
#        self._views.home()
#        self._positions.home()
#        self.set_history_buttons()
#        self._update_view()
#        
#        self.parent.subplot1.relim()
#        self.parent.subplot1.autoscale_view()
#        
#        self.parent.subplot2.relim()
#        self.parent.subplot2.autoscale_view()
        
        self.parent.fitAxis()
        
        self.parent.canvas.draw()
             
    def showboth(self, evt):
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, False)
        self.ToggleTool(self._MTB_SHOWBOTH, True)
        
        self.parent.subplot1.set_visible(True)
        self.parent.subplot2.set_visible(True)
        
        self.parent.subplot1.change_geometry(2,1,1)
        self.parent.subplot2.change_geometry(2,1,2)
        self.parent.canvas.draw()

    def showtop(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, False)
        self.ToggleTool(self._MTB_SHOWTOP, True)
        
        self.parent.subplot1.set_visible(True)
        self.parent.subplot2.set_visible(False)
        
        self.parent.subplot1.change_geometry(1,1,1)
        self.parent.canvas.draw()

    def showbottom(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, True)
        
        self.parent.subplot1.set_visible(False)
        self.parent.subplot2.set_visible(True)
        
        self.parent.subplot2.change_geometry(1,1,1)
        self.parent.canvas.draw()
        
    def legend(self, evt):   
        canvas = self.parent.canvas
        plots = (self.parent.subplot1, self.parent.subplot2)
        dialog = LegendDialog(self.parent, plots, canvas)
        dialog.ShowModal()
        
    def clear1(self, evt):
        self.parent.ClearSubplot(self.parent.subplot1)
    def clear2(self, evt):
        
        print 'CHECK!'
        self.parent.ClearSubplot(self.parent.subplot2)
    
    def errbars(self, evt):
        
        if not(self.ErrorbarIsOn):
            self.parent.plotparams['errorbars_on'] = True
            self.ErrorbarIsOn = True
            self.parent.ShowErrorbars()
        else:
            self.parent.plotparams['errorbars_on'] = False
            self.ErrorbarIsOn = False
            self.parent.HideErrorbars()
            
#    def loglog(self,evt):
#        self.ToggleTool(self._MTB_LOGLOG, False)
#                
#        self.parent.plotparams['axesscale'] = 'loglog'
#        self.parent.UpdatePlotAxesScaling()
#                
#        self.parent.canvas.draw()
#
#    def loglin(self,evt):
#        self.ToggleTool(self._MTB_LOGLIN, False)
#        
#        self.parent.plotparams['axesscale'] = 'loglin'
#        self.parent.UpdatePlotAxesScaling()
#        
##        self.parent.subplot1.relim()
##        self.parent.subplot1.autoscale_view()
##        self.parent.subplot2.relim()
##        self.parent.subplot2.autoscale_view()
#        self.parent.canvas.draw()
#
#    def linlin(self,evt):
#        self.ToggleTool(self._MTB_LINLIN, False)
#        
#        self.parent.plotparams['axesscale'] = 'linlin'
#        self.parent.UpdatePlotAxesScaling()


        
#---- *** Legend Dialog ***

class LegendDialog(wx.Dialog):
    
    def __init__(self, parent, subplots, canvas):
        
        wx.Dialog.__init__(self, parent, -1, 'Legend Options', size=(200, 120), name = 'LegendDialog')
        
        self.canvas = canvas
        self.topradioId = wx.NewId()
        self.bottomradioId = wx.NewId()
        self.subplots = subplots
        self.parent = parent
        
        self.chosenPlot = self.subplots[0]
        self.chosenLegend = self.chosenPlot.get_legend()
    
        self.currentLegendPosition = (0.0, 0.0)
        
        sizer = self.createLegendParameters()
        self.SetSizer(sizer)
        
        self.initControls()
        
    def initControls(self):
        
        if self.parent.subplot1LegendPos == None or self.parent.subplot1.get_legend() == None:
            self.autoCheck1.SetValue(True)
            self.radio_top.Enable(False)
        else:
            self.autoCheck1.SetValue(False)
            self.radio_top.Enable(True) 
                    
        if self.parent.subplot2LegendPos == None or self.parent.subplot2.get_legend() == None:
            self.autoCheck2.SetValue(True)
            self.radio_bottom.Enable(False)
        else:
            self.autoCheck2.SetValue(False)
            self.radio_bottom.Enable(True) 
        
        if not self.autoCheck1.IsChecked() or not self.autoCheck2.IsChecked():
            self.up_down_spinner.Enable(True)
            self.left_right_spinner.Enable(True)
        else:
            self.up_down_spinner.Enable(False)
            self.left_right_spinner.Enable(False)
            
        if self.autoCheck1.IsChecked() and not self.autoCheck2.IsChecked():
            self.radio_bottom.SetValue(True)
            self.chosenPlot = self.subplots[1]
            self.chosenLegend = self.chosenPlot.get_legend()
            self.currentLegendPosition = self.chosenLegend._loc
            
            self.up_down_spinner.SetValue(str(round(self.currentLegendPosition[0], 2)))
            self.left_right_spinner.SetValue(str(round(self.currentLegendPosition[1], 2)))
    
    def createLegendParameters(self):
        
        sizer = wx.BoxSizer(wx.VERTICAL)
            
        self.radio_top = wx.RadioButton(self, self.topradioId, 'Top Plot')
        self.radio_bottom = wx.RadioButton(self, self.bottomradioId, 'Bottom Plot')
        
        self.radio_top.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radio_bottom.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        
        spinSizer = wx.BoxSizer(wx.HORIZONTAL)
        radioSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.up_down_spinner = FloatSpinCtrl(self, -1, initValue = str(round(self.currentLegendPosition[0], 2)),button_style = wx.SP_HORIZONTAL)
        self.left_right_spinner = FloatSpinCtrl(self, -1, initValue = str(round(self.currentLegendPosition[1], 2)))
        
        self.up_down_spinner.Bind(EVT_MY_SPIN, self.OnSpinChange)
        self.left_right_spinner.Bind(EVT_MY_SPIN, self.OnSpinChange)
        
        self.autoCheck1 = wx.CheckBox(self, -1, 'Auto')
        self.autoCheck2 = wx.CheckBox(self, -1, 'Auto')
        self.autoCheck1.Bind(wx.EVT_CHECKBOX, self.OnCheckBox1)
        self.autoCheck2.Bind(wx.EVT_CHECKBOX, self.OnCheckBox2)
        
        autoSizer = wx.BoxSizer(wx.HORIZONTAL)
        autoSizer.Add(self.autoCheck1, 1, wx.RIGHT, 20)
        autoSizer.Add(self.autoCheck2, 1, wx.LEFT, 20)
        
        radioSizer.Add(self.radio_top, 1)
        radioSizer.Add(self.radio_bottom, 1, wx.LEFT, 5)
        
        spinSizer.Add(self.up_down_spinner, 1)
        spinSizer.Add(self.left_right_spinner, 1, wx.LEFT, 5)
        
        sizer.Add(autoSizer, 1, wx.CENTRE | wx.TOP, 10)
        sizer.Add(radioSizer, 1, wx.CENTRE | wx.TOP, 5)
        sizer.Add(spinSizer, 1, wx.CENTRE)
        
        return sizer
    
    def OnCheckBox1(self, evt):
        
        if evt.IsChecked() == True:
            self.parent.autoLegendPos = True

            self.parent.subplot1LegendPos = None
            self.radio_top.Enable(False)
            
            self.chosenPlot = self.subplots[0]
            self.chosenLegend = self.chosenPlot.get_legend()
        
            self.chosenLegend._loc = 1            
            d = self.canvas.get_renderer()
            self.chosenLegend.draw(d)
                
            if self.autoCheck2.IsChecked():
                self.up_down_spinner.Enable(False)
                self.left_right_spinner.Enable(False)
            else:
                self.radio_bottom.SetValue(True)
                self.chosenPlot = self.subplots[1]
                self.chosenLegend = self.chosenPlot.get_legend()
                bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
                x,y = bbox.x0, bbox.y0
                self.currentLegendPosition = (x,y)
                self.up_down_spinner.SetValue(str(round(self.currentLegendPosition[0], 2)))
                self.left_right_spinner.SetValue(str(round(self.currentLegendPosition[1], 2)))
                        
           
            self.canvas.draw()
        else:
            
            self.chosenPlot = self.subplots[0]
            self.chosenLegend = self.chosenPlot.get_legend()
            
            if self.chosenLegend != None:
                self.radio_top.SetValue(True)
                self.parent.autoLegendPos = False
                self.radio_top.Enable(True)
                self.up_down_spinner.Enable(True)
                self.left_right_spinner.Enable(True)
            
                bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
                x,y = bbox.x0, bbox.y0
                self.currentLegendPosition = (x,y)
                self.up_down_spinner.SetValue(str(round(self.currentLegendPosition[0], 2)))
                self.left_right_spinner.SetValue(str(round(self.currentLegendPosition[1], 2)))
            else:
                self.chosenPlot = self.subplots[1]
                self.chosenLegend = self.chosenPlot.get_legend()
                self.autoCheck1.SetValue(True)
            
            
    def OnCheckBox2(self, evt):
        
        if evt.IsChecked() == True:
            self.parent.autoLegendPos = True
            
            self.parent.subplot2LegendPos = None
            self.radio_bottom.Enable(False)
            
            self.chosenPlot = self.subplots[1]
            self.chosenLegend = self.chosenPlot.get_legend()
            self.chosenLegend._loc = 1            
            d = self.canvas.get_renderer()
            self.chosenLegend.draw(d)
            
            if self.autoCheck1.IsChecked():
                self.up_down_spinner.Enable(False)
                self.left_right_spinner.Enable(False)
            else:
                self.radio_top.SetValue(True)
                self.chosenPlot = self.subplots[0]
                self.chosenLegend = self.chosenPlot.get_legend()
                bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
                x,y = bbox.x0, bbox.y0
                self.currentLegendPosition = (x,y)
                self.up_down_spinner.SetValue(str(round(self.currentLegendPosition[0], 2)))
                self.left_right_spinner.SetValue(str(round(self.currentLegendPosition[1], 2)))
            
            self.canvas.draw()
        else:
            self.chosenPlot = self.subplots[1]
            self.chosenLegend = self.chosenPlot.get_legend()
            
            if self.chosenLegend != None:
                self.radio_bottom.SetValue(True)
                self.parent.autoLegendPos = False
                self.radio_bottom.Enable(True)
                self.up_down_spinner.Enable(True)
                self.left_right_spinner.Enable(True)
                bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
                x,y = bbox.x0, bbox.y0
                self.currentLegendPosition = (x,y)
                self.up_down_spinner.SetValue(str(round(self.currentLegendPosition[0], 2)))
                self.left_right_spinner.SetValue(str(round(self.currentLegendPosition[1], 2)))
            else:
                self.autoCheck2.SetValue(True)
                self.chosenPlot = self.subplots[0]
                self.chosenLegend = self.chosenPlot.get_legend()
                
    def OnRadioButton(self, evt):
        
        if evt.GetId() == self.topradioId:
            self.chosenPlot = self.subplots[0]        
        else:
            self.chosenPlot = self.subplots[1]
    
        self.chosenLegend = self.chosenPlot.get_legend()
    
        if self.chosenLegend != None:
            bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
            x,y = bbox.x0, bbox.y0
            #print bbox.width
            
            if self.chosenLegend._loc == 1:
                self.chosenLegend._loc = (x,y)
            
            self.currentLegendPosition = self.chosenLegend._loc
            
        else:
            self.currentLegendPosition = (0.0, 0.0)
    
        self.up_down_spinner.SetValue(str(round(self.currentLegendPosition[0],2)))
        self.left_right_spinner.SetValue(str(round(self.currentLegendPosition[1],2)))
    
    def OnSpinChange(self, evt):
        
        x = self.up_down_spinner.GetValue()
        y = self.left_right_spinner.GetValue()
        
        if self.chosenLegend != None:
            self.chosenLegend._loc = (float(x),float(y))
            
            if self.chosenPlot == self.parent.subplot1:
                bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
                bbox.height
                
                self.parent.subplot1LegendPos = ( (float(x),float(y)), bbox.height)
            else:
                bbox = self.chosenLegend.legendPatch.get_bbox().inverse_transformed(self.chosenPlot.transAxes) #
                bbox.height
                
                self.parent.subplot2LegendPos = ( (float(x),float(y)), bbox.height)
        
            d = self.canvas.get_renderer()
            self.chosenLegend.draw(d)
            self.canvas.draw()
        
#---- *** Plot Panels *** 
class PlotPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, noOfPlots = 1):
        
        wx.Panel.__init__(self, parent, panel_id, name = name)

        self.name = name
        self.fig = Figure((5,4), 75)
        self.noOfPlots = noOfPlots
        
        self.plotWorkerThread = None
        self.bgPlotWorkerThread = None
        
        ############## SETUP PLOT AXES ###############
        if noOfPlots == 1:
            self.subplot1 = self.fig.add_subplot(111)
        else:
            self.subplot1 = self.fig.add_subplot(211)
            self.subplot2 = self.fig.add_subplot(212)
        
        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        
        self.subplot1LegendPos = None
        self.subplot2LegendPos = None
        self.autoLegendPos = True
        
        self.fitplot = None
            
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        
        self.toolbar = MyCustomToolbar(self, self.canvas)
        self.toolbar.Realize()

        # Now put all into a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # This way of adding to sizer allows resizing
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        
        # Best to allow the toolbar to resize!
        sizer.Add(self.toolbar, 0, wx.GROW)
        
        color = parent.GetThemeBackgroundColour()
        self.SetColor(color)
        self.SetSizer(sizer)
        self.Fit()
        
        # Variables for the plotted experiments:
        self.legendnames = []
        self.plottedExps = []
        self.selectedLine = None
        
        self.plotparams = {'axesscale1': 'linlin',
                           'axesscale2': 'linlin',
                           'plot1type' : 'normal',
                           'plot2type' : 'subtracted',
                           'errorbars_on': False}
        
        self.legendPicked = False
        self.pickLocation = (0,0)
        self.legendPosition = (0.5,0.5)
        
        self.canvas.callbacks.connect('pick_event', self.OnPick)
        self.canvas.callbacks.connect('key_press_event', self.OnKeyPress)
        #self.canvas.callbacks.connect('button_press_event', self.OnMouseButton)
        self.canvas.callbacks.connect('motion_notify_event', self.onMotionEvent)
                
        self.MenuItemIds = {'Kratky' : wx.NewId(),
                            'Guinier': wx.NewId()}
        
        subplotLabels = { 'subtracted'  : ('Subtracted', 'q', 'I(q)'),
                          'PDDF'        : ('PDDF', 'r', 'p(r)'),
                          'kratky'      : ('Kratky', 'q', 'I(q)q^2'),
                          'guinier'     : ('Guinier', 'q^2', 'ln(I(q)')}
        
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
        
    def onMotionEvent(self, event):
        
        if event.inaxes:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('x = ' +  str(x) + ', y = ' + str(y), 1) 
            
#    def setCursor(self, a, state):
#                
#        if state == 'off':
#            if self.cursor:
#                self.cursor.clear(0)
#            
#        elif state == 'on':
#            self.cursor = Cursor(a, useblit = True, color='red')
    
    def OnMouseButton(self, evt):

        print evt.button
        if evt.button == 3:
            self.ShowPopupMenu()
            
    def ShowPopupMenu(self):

        menu = wx.Menu()
        
        plot1SubMenu = wx.Menu()
        plot1SubMenu.AppendRadioItem(self.MenuItemIds['Guinier'], 'Guinier')
        plot1SubMenu.AppendRadioItem(self.MenuItemIds['Kratky'], 'Kratky')
        plot1SubMenu.AppendRadioItem(3, 'Subtracted')
        
        plot2SubMenu = wx.Menu()
        plot2SubMenu.AppendRadioItem(3, 'Normal')
        plot2SubMenu.AppendRadioItem(self.MenuItemIds['Guinier'], 'Guinier')
        plot2SubMenu.AppendRadioItem(self.MenuItemIds['Kratky'], 'Kratky')
        plot2SubMenu.AppendRadioItem(3, 'Subtracted')
            
        menu.AppendSubMenu(plot1SubMenu, 'Plot 1')
        menu.AppendSubMenu(plot2SubMenu, 'Plot 2')
        
        menu.Append(6, 'Average selected item(s)' )
        menu.AppendSeparator()
        menu.Append(5, 'Remove selected item(s)' )
        menu.Append(3, 'Indirect Fourier Transform')
        menu.AppendSeparator()
        menu.Append(8, 'Move curve to top plot')
        menu.Append(9, 'Move curve to bottom plot')
        menu.AppendSeparator()
        menu.Append(7, 'Save selected file(s)')
        
        self.Bind(wx.EVT_MENU, self._OnPopupMenuChoice) 
        
        self.PopupMenu(menu)
        
    def _OnPopupMenuChoice(self, evt):
        print evt.GetId()
    
    def InitLabels(self):
        
        if self.GetName() == 'BIFTPlotPanel':
            self._setLabels(None, title = 'Indirect Fourier Transform', xlabel = 'r [A]', ylabel = 'p(r)', axes = self.subplot1)
            self._setLabels(None, title = 'Fit', xlabel = 'q [1/A]', ylabel = 'I(q)', axes = self.subplot2)
        elif self.GetName() == 'PlotPanel':
            self._setLabels(None, title = 'Plot', xlabel = 'q [1/A]', ylabel = 'I(q)', axes = self.subplot1)
            self._setLabels(None, title = 'Subtracted', xlabel = 'q [1/A]', ylabel = 'I(q)', axes = self.subplot2)
    
    def DeleteLinePlot(self, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        linePoppedOk = self.PopLine(self.subplot1)
        
        if not(linePoppedOk):
            self.PopLine(self.subplot2)
        
    def PopLine(self, a):     
        
        try:
            
            theidx = -1
            for idx in range(0, len(self.plottedExps)):
                if self.plottedExps[idx].line == self.selectedLine:
                   ManipulationPage = wx.FindWindowByName('ManipulationPage')
                   ManipulationPage.RemoveItem(self.plottedExps[idx])
                   self.plottedExps[idx].line.remove()
                   theidx = idx
                   break
            
            
            if self.plottedExps[theidx].errLine and theidx != -1:
                errline1 = self.plottedExps[theidx].errLine[0]
                self.plottedExps[theidx].errLine[1][0].remove()
                
                for each in errline1:
                    each.remove()
            else:
                return True
            
            self.plottedExps.pop(theidx)
            self._insertLegend(axes = a)
            self.canvas.draw()
            
            return True
            
        except ValueError, e:
            print 'Error in PlotPanel.DeleteLinePlot()\n' + str(e)
            return False
            
    def DeleteSingleLine(self, line, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
            
        lines = a.get_lines()
        
        idx = lines.index(line)

        a.lines.pop(idx)
        
        # GRR slow!!
        for i in range(0,len(self.plottedExps)):
            if self.plottedExps[i].line == line:
                self.plottedExps.pop(i)
                break
        
        if self.selectedLine == line:
             self.selectedLine = None
        
        self._insertLegend(axes = axes)
                    
        self.canvas.draw()
        
    def OnKeyPress(self, evt):
             
        if evt.key == 'delete' and self.selectedLine != None:
            self.DeleteLinePlot()
    
    def OnPick(self, evt):
        
        try:
            if evt.artist.type == 'legend':
                print 'LEGEND PICK!'
                
                a = self.subplot1
                legend = a.get_legend()
                self.legendPosition = legend._loc
                self.legendPicked = True
                return
        except:
            pass
        
        if self.selectedLine == evt.artist:
            
            for each in self.plottedExps:
                each.line.set_linewidth(1)
            self.selectedLine = None
            
        else:
            self.selectedLine = evt.artist
            
            for each in self.plottedExps:
                each.line.set_linewidth(1)
            
            self.selectedLine.set_linewidth(3)
            
            manipulationPage = wx.FindWindowByName('ManipulationPage')
            manipulationPage.DeselectAllExceptOne(None, self.selectedLine)
        
        self.canvas.draw()
    
    def SelectLine(self, line):
        
        self.selectedLine = line
        self.selectedLine.set_linewidth(3)
        
        self.canvas.draw()
            
    def DeselectLine(self, line):
        
        line.set_linewidth(1)
        
        self.canvas.draw()
                
    def _ClearFigure(self, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        a.clear()
        a.set_xscale('linear')       # Reset to default values
        a.set_yscale('linear')
        a.set_xlim(0,1.0)
        a.set_ylim(0,1.0)
        
    def UpdatePlotAxesScaling(self):
        
        if self.noOfPlots == 2:
            
            if self.GetName() == 'BIFTPlotPanel':
                axes = [self.subplot2]
            else:
                axes = [self.subplot1, self.subplot2]
        else:
            axes = [self.fig.gca()]
            
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
                a.set_yscale('log')
    
            if self.plotparams.get('axesscale'+ str(c)) == 'loglog':
                a.set_xscale('log')
                a.set_yscale('log')
                
            if self.plotparams.get('axesscale'+ str(c)) == 'linlog':
                a.set_xscale('log')
                a.set_yscale('linear')
        
        self.fitAxis()         

        self.canvas.draw()
         
    def init_plot_data(self):
        a = self.fig.add_subplot(111)
        #self.toolbar.update() # Not sure why this is needed - ADS

    def GetToolBar(self):
        # You will need to override GetToolBar if you are using an 
        # unmanaged toolbar in your frame
        return self.toolbar
    
    def SetColor(self, rgbtuple):
        """Set figure and canvas colours to be the same"""
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
       
        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))
    
    def _getExperimentParameters(self):
        
        q_range = (expParams['QrangeLow'], expParams['QrangeHigh'])
        pixelcal = [expParams['PixelCalX'], expParams['PixelCalY']]
        x_center, y_center = expParams['Xcenter'], expParams['Ycenter']
        binsize = expParams['Binsize']
        mask = expParams['BeamStopMask']      
        rdmask = expParams['ReadOutNoiseMask'] 
        
        return mask, rdmask, q_range, pixelcal, x_center, y_center, binsize
    
    def togglePlot(self, ExpObj):
        
        if ExpObj.isPlotted == True:
            ExpObj.line.set_visible(False)
            ExpObj.isPlotted = False
        else:
            ExpObj.line.set_visible(True)
            ExpObj.isPlotted = True

        self._insertLegend(axes = self.subplot1)
        
        if self.GetName() != 'BIFTPlotPanel':
            self._insertLegend(axes = self.subplot2)
        
        self.canvas.draw()       
    
    def updatePlotAfterScaling(self, ExpObj):
        
        ExpObj.line.set_data(ExpObj.q, ExpObj.i)
        
        self.canvas.draw()
            
    def _removeLine(self, idx = -1):
        
        a = self.fig.gca()
        a.lines.pop(idx)
        
        #thats a tricky one when its not the last one!
        a._get_lines.count = a._get_lines.count - 1    # This is a no-no, but the hack is nessecary to fix colors  
    
    def onPlotButton(self, evt):
        
        #progressBar = MyProgressBar(self)
        progressBar = None
        
        dirCtrlPanel = wx.FindWindowByName('DirCtrlPanel')
            
        selectedFiles = dirCtrlPanel.GetSelectedFile()
                
        if evt == 'onlineBackground':
            
            if self.plotWorkerThread == None:
                self.plotWorkerThread = PlotWorkerThread(self, progressBar, setBackground = True)
                self.plotWorkerThread.setDaemon(True)
                self.plotWorkerThread.start()
                plotQueue.put(selectedFiles)
            else:
                plotQueue.put(selectedFiles)
            
        else:
            
            if self.plotWorkerThread == None:
                self.plotWorkerThread = PlotWorkerThread(self, progressBar)
                self.plotWorkerThread.setDaemon(True)
                self.plotWorkerThread.start()
                plotQueue.put(selectedFiles)
            else:
                plotQueue.put(selectedFiles)
        
        #progressBar.run()
        
    def PlotExperimentObject(self, ExpObj, name = None, axes = None, addToPlottedExps = True):
        
        self._PlotOnSelectedAxesScale(ExpObj, axes, addToPlottedExps)
        #self._setLabels(ExpObj, axes = plotaxes)
        
        if name != None:
            self._insertLegend('Average', axes = axes)
        else:
            self._insertLegend(os.path.split(ExpObj.param['filename'])[1], axes = axes)    # filename without path
        
        #Update figure:
        self.canvas.draw()
        
        if addToPlottedExps:
            manipulationPage = wx.FindWindowByName('ManipulationPage')
            manipulationPage.AddItem(ExpObj)
        
    def PlotBIFTExperimentObject(self, ExpObj, name = None):
        
        # Until we get errorbars on!
        ExpObj.errorbars = zeros((len(ExpObj.q)))
        
        print 'Q',shape(ExpObj.q)
        print 'I',shape(transpose(ExpObj.i)[0])
        print 'E',shape(ExpObj.errorbars)
        
        if shape(ExpObj.i) == (50,1):
            ExpObj.i = transpose(ExpObj.i)[0]
        
        self._PlotOnSelectedAxesScale(ExpObj, self.subplot1)
        self._setLabels(ExpObj, 'Indirect Fourier Transform', 'r (A)', 'P(r)', self.subplot1)
        
        if name != None:
            self._insertLegend('IFT', self.subplot1)
        else:
            self._insertLegend(os.path.split(ExpObj.param['filename'])[1], self.subplot1)    # filename without path
        
        manipulationPage = wx.FindWindowByName('ManipulationPage')
        evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObj)
        wx.PostEvent(manipulationPage, evt)
        
        self._ClearFigure(self.subplot2)
        
        q = ExpObj.allData['orig_q']
        i = ExpObj.allData['orig_i']
        err = ExpObj.allData['orig_err']
        
        FitExp = cartToPol.RadFileMeasurement(i, q, err, None)
        
        self._PlotArrayOnSelectedAxesScale([q, ExpObj.fit], self.subplot2, True)
        self._PlotOnSelectedAxesDontSave(FitExp, self.subplot2, True)
        
        #self._insertLegend(os.path.split(ExpObj.param['filename'])[1], self.subplot2)
        self._setLabels(ExpObj, 'Fit', 'q (1/A)', 'I', self.subplot2)
        
        
        self.fitAxis()
        #Update figure:
        self.canvas.draw()
     
    def SubtractAndPlot(self, ExpObjList):
        
        ExpObjBackgrnd = expParams['BackgroundFile']
        
        if ExpObjBackgrnd != None:
            
            noPathBackgrndFilename = os.path.split(ExpObjBackgrnd.param['filename'])[1]
            dialog = wx.ProgressDialog('Subtracting..', 'Subtracting Background', 7, self, wx.PD_APP_MODAL | wx.PD_AUTO_HIDE)
            
            for eachExpObjSample in ExpObjList:
                fullpath = os.path.split(eachExpObjSample.param['filename'])[0]
                noPathSampleFilename = os.path.split(eachExpObjSample.param['filename'])[1]
                
                if len(eachExpObjSample.i) == len(ExpObjBackgrnd.i):
                    
                    ExpObjSubbed = cartToPol.subtractMeasurement(eachExpObjSample, ExpObjBackgrnd)
                    
                    ExpObjSubbed.param['filename'] = os.path.join(fullpath, 'BSUB_' + noPathSampleFilename) 
                    
                    dialog.Update(1)
            
                    self._PlotOnSelectedAxesScale(ExpObjSubbed, self.subplot2)
                    #overviewpanel = wx.FindWindowByName('OverviewPanel')
                    #overviewpanel.plotExpObj(ExpObjSubbed)
                
                    dialog.Update(3)
            
                    #Update figure:
                    self.canvas.draw()
        
                    manipulationPage = wx.FindWindowByName('ManipulationPage')
                    manipulationPage.AddItem(ExpObjSubbed)
        
                    dialog.Update(7)
            
                else:
                    wx.MessageBox(noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
                    dialog.Update(7)
        
            #self._setLabels(ExpObjSample)           
            self._insertLegend(axes = self.subplot2)
        
    def OnSubnPlot(self, evt):
                
        dirCtrlPanel = wx.FindWindowByName('DirCtrlPanel')
        selectedFiles = dirCtrlPanel.GetSelectedFile()
        bgfilename = dirCtrlPanel.GetBackgroundPath()
        
        progressThread = None
        
        if bgfilename != None:
            #progressThread = MyProgressBar(self)
            progressThread = None
            
            if self.bgPlotWorkerThread == None:
                self.bgPlotWorkerThread = BgSubPlotWorkerThread(self, progressThread)
                self.bgPlotWorkerThread.setDaemon(True)
                self.bgPlotWorkerThread.start()
                bgSubPlotQueue.put([selectedFiles, bgfilename])
            else:
                bgSubPlotQueue.put([selectedFiles, bgfilename])
        
            #progressThread.run()
        
    def ShowErrorbars(self):
        
        for each in self.plottedExps:
            setp(each.errLine[0], visible=True)
            setp(each.errLine[1], visible=True)
        
        if self.fitplot != None and self.name == 'BIFTPlotPanel':
            setp(self.fitplot.errLine[0], visible=True)
            setp(self.fitplot.errLine[1], visible=True)
            
        self.canvas.draw()

    def HideErrorbars(self):
        
        for each in self.plottedExps:
            setp(each.errLine[0], visible=False)
            setp(each.errLine[1], visible=False)
        
        
        if self.fitplot != None and self.name == 'BIFTPlotPanel':
            setp(self.fitplot.errLine[0], visible=False)
            setp(self.fitplot.errLine[1], visible=False)
            
        self.canvas.draw()
        
    def _PlotOnSelectedAxesDontSave(self, ExpObj, axes = None, forceScale = None):

        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        line, ec, el = a.errorbar(ExpObj.q, ExpObj.i, ExpObj.errorbars, picker = 3)
        
        #Hide errorbars:
        if self.plotparams['errorbars_on'] == False:
            setp(ec, visible=False)
            setp(el, visible=False)
            
        ExpObj.line = line
        ExpObj.errLine = (ec, el)
        ExpObj.axes = a
        ExpObj.canvas = self.canvas
        ExpObj.plotPanel = self
        ExpObj.isPlotted = True
        
        self.fitplot = ExpObj        # Insert the plot into plotted experiments list
    
    
    def _PlotOnSelectedAxesScale(self, ExpObj, axes = None, addToPlottedExps = True):
    
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        #plot with errorbars
        
        if a == self.subplot1:
            type = self.plotparams.get('plot1type')
        elif a == self.subplot2:  
            type = self.plotparams.get('plot2type')
          
            
        if type == 'normal' or type == 'subtracted':
            line, ec, el = a.errorbar(ExpObj.q, ExpObj.i, ExpObj.errorbars, picker = 3)
        elif type == 'kratky':
            line, ec, el = a.errorbar(ExpObj.q, ExpObj.i*power(ExpObj.q,2), ExpObj.errorbars, picker = 3)
        elif type == 'guinier':
            line, ec, el = a.errorbar(power(ExpObj.q,2), ExpObj.i, ExpObj.errorbars, picker = 3)
        elif type == 'porod':
            line, ec, el = a.errorbar(ExpObj.q, power(ExpObj.q,4)*ExpObj.i, ExpObj.errorbars, picker = 3)
           
        mainframe = wx.FindWindowByName('MainFrame')
        
        if self.name == 'BIFTPlotPanel':
            mainframe.plotNB.SetSelection(1)
        else:
            mainframe.plotNB.SetSelection(0)
        
        #Hide errorbars:
        if self.plotparams['errorbars_on'] == False:
            setp(ec, visible=False)
            setp(el, visible=False)
            
        ExpObj.line = line
        ExpObj.errLine = (ec, el)
        ExpObj.axes = a
        ExpObj.canvas = self.canvas
        ExpObj.plotPanel = self
        ExpObj.isPlotted = True
        
        #self.toolbar._views = cbook.Stack()
        #self.toolbar._positions = cbook.Stack()
        #self.toolbar._update_view()
        if addToPlottedExps:
            self.plottedExps.append(ExpObj)        # Insert the plot into plotted experiments list
    
        self.fitAxis()
    
    def _PlotArrayOnSelectedAxesScale(self, array, axes = None, forceScale = None):
        
        x = transpose(array[0])
        y = transpose(array[1])
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        if forceScale == None:
            if self.plotparams['axesscale'] == 'loglog':
                line = a.loglog(x, y, picker = 3)
            if self.plotparams['axesscale'] == 'loglin':
                line = a.semilogy(x, y, picker = 3)
            if self.plotparams['axesscale'] == 'linlin':
                line = a.plot(x, y, picker = 3)
                
        else:
            a.loglog(x, y, picker = 3)
        
        self.fitAxis()
            
        #ExpObj.line = line[0]
        #ExpObj.isPlotted = True
        #self.plottedExps.append(ExpObj)        # Insert the plot into plotted experiments array
    
    def _setLabels(self, ExpObj = None, title = None, xlabel = None, ylabel = None, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        # Set TITLE 
        if title == None:
              
            if self.name == 'BIFTPlotPanel':
                
                if a == self.subplot1:
                    a.set_title('Indirect Fourier Transform')
                    a.set_ylabel('P(r)')
                    a.set_xlabel('r [A]')
                elif a == self.subplot2:
                    a.set_title('Fit')
                    a.set_ylabel('I(q)')
                    a.set_xlabel('q [1/A]')
            else:
                    
                if a == self.subplot1:
                    if self.plotparams['plot1type'] == 'normal':
                        a.set_title('Main plot')
                        a.set_ylabel('I(q)')
                        a.set_xlabel('q [1/A]')
                        
                    elif self.plotparams['plot1type'] == 'kratky':
                        a.set_title('Kratky plot')
                        a.set_ylabel('I(q)q^2')
                        a.set_xlabel('q [1/A]')
                        
                    elif self.plotparams['plot1type'] == 'guinier':
                        a.set_title('Guinier plot')
                        a.set_ylabel('I(q)')
                        a.set_xlabel('q^2 [1/A^2]')
                    
                    elif self.plotparams['plot1type'] == 'porod':
                        a.set_title('Porod plot')
                        a.set_ylabel('I(q)q^4')
                        a.set_xlabel('q [1/A]')
                            
                elif a == self.subplot2:
                    if self.plotparams['plot2type'] == 'subtracted':
                        a.set_title('Subtracted plot')
                        a.set_ylabel('I(q)')
                        a.set_xlabel('q [1/A]')
                    elif self.plotparams['plot2type'] == 'kratky':
                        a.set_title('Kratky plot')
                        a.set_ylabel('I(q)q^2')
                        a.set_xlabel('q [1/A]')
                    elif self.plotparams['plot2type'] == 'guinier':
                        a.set_title('Guinier plot')
                        a.set_ylabel('I(q)')
                        a.set_xlabel('q^2 [1/A^2]')
                    elif self.plotparams['plot2type'] == 'porod':
                        a.set_title('Porod plot')
                        a.set_ylabel('I(q)q^4')
                        a.set_xlabel('q [1/A]')
        else:
            a.set_title(title)
                
    def fitAxis(self):
        
        plots = [self.subplot1, self.subplot2]
        
        for eachsubplot in plots:
            if eachsubplot.lines:
                
                maxq = None
                maxi = None
            
                minq = None
                mini = None
                        
                for each in eachsubplot.lines:
                    if each._label != '_nolegend_':
                        
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
                
        self.canvas.draw()
    
    def _insertLegend(self, selected_sample_file = None, axes = None):
        ####################################################################
        # NB!! LEGEND IS THE BIG SPEED HOG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ###################################################################
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        legendnames = []
        legendlines = []

        for each in self.plottedExps:
            if each.axes == axes:
                filename = os.path.split(each.param['filename'])[1]
                legendnames.append(filename)
                legendlines.append(each.line)
        
        legendnames = tuple(legendnames)
        legendlines = tuple(legendlines)

        if len(legendnames) > 0:
            
            if a == self.subplot1 and self.subplot1LegendPos != None:            
                leg = a.legend(legendlines, legendnames, prop = FontProperties(size = 10), borderpad = 0.2, loc = self.subplot1LegendPos[0], fancybox = True, shadow=True)
                leg.get_frame().set_alpha(0.3)

            elif a == self.subplot2 and self.subplot2LegendPos != None:
                leg = a.legend(legendlines, legendnames, prop = FontProperties(size = 10), borderpad = 0.2, loc = self.subplot2LegendPos[0], fancybox = True, shadow=True)
                leg.get_frame().set_alpha(0.3)                                    
            else:
                leg = a.legend(legendlines, legendnames, prop = FontProperties(size = 10), borderpad = 0.2, loc = 1, fancybox = True, shadow=True)
                leg.get_frame().set_alpha(0.3)
                    
        else:
            a.legend_ = None
        
        self.canvas.draw()
        
    def UpdatePlotsAfterTypeChange(self, axes):
        
        plotsInAxes = []
        
        for each in self.plottedExps:
            if each.axes == axes:
                plotsInAxes.append(each)
        
        for each in plotsInAxes:
            
            if axes == self.subplot1:
                
                if self.plotparams['plot1type'] == 'kratky':
                    each.line.set_ydata(each.i * power(each.q,2))
                    each.line.set_xdata(each.q)
                elif self.plotparams['plot1type'] == 'guinier':
                    each.line.set_ydata(each.i)
                    each.line.set_xdata(power(each.q,2))
                elif self.plotparams['plot1type'] == 'porod':
                    each.line.set_ydata(power(each.q,4)*each.i)
                    each.line.set_xdata(each.q)
                elif self.plotparams['plot1type'] == 'normal' or self.plotparams['plot1type'] == 'subtracted':
                    each.line.set_ydata(each.i)
                    each.line.set_xdata(each.q)
                                
                #each.line.pchanged()
          
            elif axes == self.subplot2:
                
                if self.plotparams['plot2type'] == 'kratky':
                    each.line.set_ydata(each.i * power(each.q,2))
                    each.line.set_xdata(each.q) 
                elif self.plotparams['plot2type'] == 'guinier':
                    each.line.set_ydata(each.i)
                    each.line.set_xdata(power(each.q,2))
                elif self.plotparams['plot2type'] == 'porod':
                    each.line.set_ydata(power(each.q,4)*each.i)
                    each.line.set_xdata(each.q)
                elif self.plotparams['plot2type'] == 'normal' or self.plotparams['plot2type'] == 'subtracted':
                    each.line.set_ydata(each.i)
                    each.line.set_xdata(each.q)
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
            
        self.fitAxis()
        
        self.canvas.draw()
        
    def UpdateSinglePlot(self, ExpObj):
        
        if ExpObj.plotPanel.GetName() == 'PlotPanel':
            if ExpObj.axes == self.subplot1:
                if self.plotparams['plot1type'] == 'kratky':
                    ExpObj.line.set_ydata(ExpObj.i * power(ExpObj.q,2))
                    ExpObj.line.set_xdata(ExpObj.q)
                elif self.plotparams['plot1type'] == 'guinier':
                    ExpObj.line.set_ydata(ExpObj.i)
                    ExpObj.line.set_xdata(power(ExpObj.q,2))
                elif self.plotparams['plot1type'] == 'porod':
                    ExpObj.line.set_ydata(power(ExpObj.q,4)*ExpObj.i)
                    ExpObj.line.set_xdata(ExpObj.q)
                elif self.plotparams['plot1type'] == 'normal' or self.plotparams['plot1type'] == 'subtracted':
                    ExpObj.line.set_ydata(ExpObj.i)
                    ExpObj.line.set_xdata(ExpObj.q)
            
            elif ExpObj.axes == self.subplot2:
                if self.plotparams['plot2type'] == 'kratky':
                    ExpObj.line.set_ydata(ExpObj.i * power(ExpObj.q,2))
                    ExpObj.line.set_xdata(ExpObj.q) 
                elif self.plotparams['plot2type'] == 'guinier':
                    ExpObj.line.set_ydata(ExpObj.i)
                    ExpObj.line.set_xdata(power(ExpObj.q,2))
                elif self.plotparams['plot2type'] == 'porod':
                    ExpObj.line.set_ydata(power(ExpObj.q,4)*ExpObj.i)
                    ExpObj.line.set_xdata(ExpObj.q)
                elif self.plotparams['plot2type'] == 'normal' or self.plotparams['plot2type'] == 'subtracted':
                    ExpObj.line.set_ydata(ExpObj.i)
                    ExpObj.line.set_xdata(ExpObj.q)
            
            self.canvas.draw()
        
    def PlotLoadedBift(self, BiftObj):
        
        i = BiftObj.allData['orig_i']
        q = BiftObj.allData['orig_q']
        err = BiftObj.allData['orig_err']
        
        ExpObj = cartToPol.RadFileMeasurement(array(i), array(q), array(err), BiftObj.param)
        
        self.PlotBIFTExperimentObject(BiftObj)
        biftPage = wx.FindWindowByName('AutoAnalysisPage')
        biftPage.addBiftObjToList(ExpObj, BiftObj)
    
    def OnUndo(self, evt):
        ''' This removes the last plotted line, and fixes legend and line color issues of new plots '''
           
        #a = self.fig.gca()
        a = self.subplot1
#        if a.lines:
#            self.plottedExps.pop(-1)                    
#            a.lines.pop(-1)
#            if self.fig.legends:
#                self.fig.legends.pop(-1)
#            self.legendnames.pop(-1)
#            a._get_lines.count = a._get_lines.count - 1    # This is a no-no, but the hack is nessecary to fix colors                                                     
    
        d = self.canvas.get_renderer()
        
        legend = a.get_legend()
        
        for each in legend.get_lines():
            each.set_picker(True)
            
        for each in legend.get_texts():
            each.type = 'legend'
            each.set_picker(True)
    
        frame = legend.get_frame()    
        frame.set_alpha(0.5)
        legend._loc = (0.5,0.5)
        legend.draw(d)
        
        bbox = legend.legendPatch.get_bbox().inverse_transformed(a.transAxes) #
        #bbox in axes coordinate:
        x = bbox.x0 #+bbox.width/2. # center
        
        print x
        
        self.canvas.draw()
    
    def ClearSubplot(self, subplot):
        
        expsToBeRemoved = []
        
        for i in range(0, len(self.plottedExps)):
            if self.plottedExps[i].axes == subplot:
                expsToBeRemoved.append(self.plottedExps[i])
        
        for each in expsToBeRemoved:
            self.plottedExps.remove(each)

        manipulationPage = wx.FindWindowByName('ManipulationPage')
        manipulationPage.ClearList(expsToBeRemoved)
        
        subplot.cla()
        
        self._setLabels(axes = subplot)
        self.canvas.draw_idle()
        
            
    def OnClearAll(self, event, clearManipItems = None):
        
        global expParams
        
        if self.name == 'PlotPanel':
            dial = wx.MessageDialog(None, 'Are you sure you want to clear everything?', 'Question', 
                                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            answer = dial.ShowModal()
        
            if answer == wx.ID_NO:
                return
        
        a = self.fig.gca()
        
        if clearManipItems == None:
            manipulationPage = wx.FindWindowByName('ManipulationPage')
            manipulationPage.ClearList(self.plottedExps)
        
        self.fig.legends = []        # Remove legends from figure
        self.legendnames = []
        self.plottedExps = []
        
        self.fitplot = []
        
        if self.noOfPlots == 2:
            self._ClearFigure(self.subplot1)
            self._ClearFigure(self.subplot2)
            
            #Reset stacks in toolbar mem
            self.toolbar._views = cbook.Stack()
            self.toolbar._positions = cbook.Stack()
        else:
            self._ClearFigure()
        
        self.plotparams['axesscale'] = 'linlin'
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
        
        #Update canvas:
        self.canvas.draw()
        
        #Clear statusbar:
        wx.FindWindowByName('MainFrame').SetStatusText('')
        
        if self.name == 'PlotPanel':
            biftpanel = wx.FindWindowByName('BIFTPlotPanel')
            biftpanel.OnClearAll(0)
            
            autoanalysis = wx.FindWindowByName('AutoAnalysisPage')
            autoanalysis.ClearList()
            
            maskpanel = wx.FindWindowByName('RawPlotPanel')
            maskpanel.clearFigure()
        
        expParams['BackgroundFile'] = None
        
    def onEraseBackground(self, evt):
        # this is supposed to prevent redraw flicker on some X servers...
        pass



#### Rewrite DirCtrlPanel to a listbox and a label with a dir browser.
#**************************************************************************
#
# Make function to, average over selected data and save to a file
#
# Connect indirect fourier to GUI... 
#

class FileExistsDialog(wx.Dialog):
    
    def __init__(self, filename, ExpObj):
        
        wx.Dialog.__init__(self, None, -1, 'File Exists!', size = (200,250))
        
        #filename = os.path.split(fileIO.filenameWithoutExtension(ExpObj))[1] + '.rad'
        
        self.ExpObj = ExpObj
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        filenameLabel = wx.StaticText(self, -1, filename + '\n already exists!')
        chooseLabel = wx.StaticText(self, -1, 'Please choose:')
        
        renameButton = wx.Button(self, 1, 'Rename', size = (100,25))
        overwriteButton = wx.Button(self, 2, 'Overwrite', size = (100,25))
        skipButton = wx.Button(self, 3, 'Skip', size = (100,25))
        overwriteAllButton = wx.Button(self, 4, 'Overwrite All', size = (100,25))
        skipAllButton = wx.Button(self, 5, 'Skip All', size = (100,25))
        
        
        renameButton.Bind(wx.EVT_BUTTON, self.onButton)
        overwriteButton.Bind(wx.EVT_BUTTON, self.onButton)
        skipButton.Bind(wx.EVT_BUTTON, self.onButton)
        overwriteAllButton.Bind(wx.EVT_BUTTON, self.onButton)
        skipAllButton.Bind(wx.EVT_BUTTON, self.onButton)
        
        sizer.Add((10,10),0)
        sizer.Add(filenameLabel, 0.5, wx.ALIGN_CENTER)
        sizer.Add((5,5),0)
        sizer.Add(chooseLabel, 0.5,wx.ALIGN_CENTER)
        sizer.Add((10,10),0)
        sizer.Add(renameButton, 1,wx.ALIGN_CENTER)
        sizer.Add(overwriteButton, 1,wx.ALIGN_CENTER)
        sizer.Add(skipButton, 1,wx.ALIGN_CENTER)
        sizer.Add(overwriteAllButton, 1,wx.ALIGN_CENTER)
        sizer.Add(skipAllButton, 1,wx.ALIGN_CENTER)
        sizer.Add((10,10),0)
        
        self.SetSizer(sizer)
        
    def onButton(self, evt):
        
        answer = evt.GetId()
        
        RENAME = 1
        OVERWRITE = 2
        SKIP = 3
        OVERWRITE_ALL = 4
        SKIP_ALL_EXISTING = 5
        
        if answer is OVERWRITE:
           filename = fileIO.saveMeasurement(self.ExpObj)
           wx.FindWindowByName('MainFrame').SetStatusText(filename + ' Saved!')
           self.EndModal(answer)
                    
        elif answer is RENAME:
                        
           filters = 'Rad files (*.rad)|*.rad'
           dialog = wx.FileDialog( self, style = wx.SAVE | wx.OVERWRITE_PROMPT, wildcard = filters)
           resultID = dialog.ShowModal()
                        
           if resultID == wx.ID_OK:
                            
               newFileName = dialog.GetPath()
                        
               oldFileName = self.ExpObj.param['filename']
               self.ExpObj.param['filename'] = newFileName
               filename = fileIO.saveMeasurement(self.ExpObj)
               self.ExpObj.param['filename'] = oldFileName
               wx.FindWindowByName('MainFrame').SetStatusText(filename + ' Saved!')
               self.EndModal(answer)             
                        
        elif answer is SKIP:
           self.EndModal(answer)

        elif answer is SKIP_ALL_EXISTING:
           self.EndModal(answer)
                          
        elif answer is OVERWRITE_ALL:
           overwriteAll = True
           filename = fileIO.saveMeasurement(self.ExpObj)
           wx.FindWindowByName('MainFrame').SetStatusText(filename + ' Saved!')
           self.EndModal(answer)
                    
                    
class DirCtrlPanel_2(wx.Panel):

    def __init__(self, parent, id):
        
        self.parent = parent
        
        wx.Panel.__init__(self, parent, id, name = 'DirCtrlPanel')
        
        self.fileExtensionList = ['All files (*.*)',
                                  'No Extension files (*.)',
                                  'TIFF files (*.tiff)',
                                  'TIF files (*.tif)',
                                  'RAD Files (*.rad)',
                                  'DAT files (*.dat)',
                                  'TXT files (*.txt)']
        
        DirCtrlPanel_Sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.CreateDirCtrl(DirCtrlPanel_Sizer)            #Listbox containing filenames
        self.CreateExtentionBox(DirCtrlPanel_Sizer)       #File extention filter
        
        self.SetSizer(DirCtrlPanel_Sizer, wx.EXPAND)
        
        self.bgFilename = None
        self.selected_file = None
        self.path = '/'
        
        self.FileList = []
        self.InitFileList()
        
    def InitFileList(self):
        
            self.FileList = os.listdir(self.path)
    
            FilesOnlyList = []
            
            for filename in self.FileList:
                if os.path.isfile(os.path.join(self.path, filename)):
                    FilesOnlyList.append(filename)
        
            self.FileList = FilesOnlyList
    
            self.UpdateDirLabel(self.path)
            self.UpdateFileListBox(self.FileList)
            self.FilterFileListAndUpdateListBox()
        
    def CreateExtentionBox(self, DirCtrlPanel_Sizer):
        
        self.dropdown = wx.Choice(self)
        DirCtrlPanel_Sizer.Add(self.dropdown, 0, wx.EXPAND | wx.TOP, 2)
        
        self.dropdown.AppendItems(strings = self.fileExtensionList)
        self.dropdown.Select(n=0)
        self.dropdown.Bind(wx.EVT_CHOICE, self.OnChoice)
        #wx.EVT_CHOICE(self, dropdown.GetId(), self.OnChoice)
    
    def OnChoice(self, event):
         self.FilterFileListAndUpdateListBox()
         
    def FilterFileListAndUpdateListBox(self):    
        
         choice = self.dropdown.GetStringSelection()
         pattern = re.compile('[.][*a-zA-Z0-9_]*[)]')
         extension = pattern.search(choice).group()[:-1]
         
         if extension == '.*':
             self.UpdateFileListBox(self.FileList)
             
         elif extension == '.':

             filteredFileList = []
             
             for each in self.FileList:
                 if len(each) > 4:
                     if each[-5:].find('.') == -1:
                         filteredFileList.append(each)
                 else:
                     filteredFileList.append(each)
             
             self.UpdateFileListBox(filteredFileList)
             
         else:
             filterdFileList = []
             
             for i in range(0,len(self.FileList)):
                 if self.FileList[i].endswith(extension):
                     filterdFileList.append(self.FileList[i])

             self.UpdateFileListBox(filterdFileList)            
        
    def CreateDirCtrl(self, DirCtrlPanel_Sizer):
        # create list box
        
        Dirlabelsizer = wx.BoxSizer()
        
        #mainframe = wx.FindWindowByName('MainFrame')
        #workdir = 
        
        self.DirLabel = wx.TextCtrl(self, -1, "/" , size = (30,16), style = wx.TE_PROCESS_ENTER)
        self.DirLabel.Bind(wx.EVT_KILL_FOCUS, self._OnDirLabelChange)
        self.DirLabel.Bind(wx.EVT_TEXT_ENTER, self._OnDirLabelChange)
        dirBitmap = wx.Bitmap(os.path.join("ressources", "wi0009-16.png"))
        

        self.DirButton = wx.BitmapButton(self, -1, dirBitmap)
        self.DirButton.Bind(wx.EVT_BUTTON, self._OnSetDirButton)
        
        Dirlabelsizer.Add(self.DirLabel, 1, wx.EXPAND | wx.RIGHT, 2)
        Dirlabelsizer.Add(self.DirButton,0)
        
        self.fileListBox = wx.ListBox(self, -1, style = wx.LB_EXTENDED)
        self.fileListBox.Bind(wx.EVT_KEY_DOWN, self._OnUpdateKey)
        self.fileListBox.Bind(wx.EVT_LEFT_DCLICK, self._OnDoubleClick)
        self.fileListBox.Bind(wx.EVT_LISTBOX, self._OnLeftClick)
        self.fileListBox.Bind(wx.EVT_RIGHT_DOWN, self._OnRightClick)
        
        DirCtrlPanel_Sizer.Add(Dirlabelsizer, 0, wx.EXPAND | wx.BOTTOM, 2)
        DirCtrlPanel_Sizer.Add(self.fileListBox, 1, wx.EXPAND)
        
        self.selectedFiles = []
        self.bgFilename = []
        
    def _OnDirLabelChange(self, evt):
        
        #print "change!"
        pathtxt = self.DirLabel.GetValue()
        if pathtxt != self.path:
            if os.path.isdir(pathtxt):
                self.path = pathtxt
                FileList = self.GetListOfFiles()
                self.UpdateFileListBox(FileList)
            else:
                self.DirLabel.SetValue(str(self.path))


    def _OnRightClick(self, evt):
        
        files = self.GetSelectedFile()
        
        if files:
            menu = wx.Menu()
            
            if len(files) == 1:
                menu.Append(1, 'Set as Background file')
                menu.AppendSeparator()
                menu.Append(2, 'Set as Empty cell file')
                menu.Append(3, 'Set as Water sample file')
            
            elif len(files) > 1:
                #menu.AppendSeparator()
                menu.Append(4, 'Average Selected Files')
                menu.Append(6, 'Substract Bg. and Plot')
            
            menu.AppendSeparator()
            menu.Append(5, 'Plot file(s)')
                        
            self.Bind(wx.EVT_MENU, self._OnPopupMenuChoice)
        
            self.PopupMenu(menu)
    
    def _OnPopupMenuChoice(self, evt):
        
        if evt.GetId() == 1:
            self.OnSetBackgroundFile(0)
            
        if evt.GetId() == 2:
            filename = self.GetSelectedFile()[0]
            
            plotPanel = wx.FindWindowByName('PlotPanel')
            ExpObj, FullImage = fileIO.loadFile(filename, expParams)
            
            if ExpObj.filetype == 'image':
                checkedTreatments = getTreatmentParameters()
                cartToPol.applyDataManipulations(ExpObj, expParams, checkedTreatments)
            
            expParams['EmptyFile'] = ExpObj
            
            infobox = wx.FindWindowByName('InfoPanel')
            infobox.WriteText(os.path.split(filename)[1] + ' is the empty cell file.\n')
            
        if evt.GetId() == 3:
            filename = self.GetSelectedFile()[0]
            plotPanel = wx.FindWindowByName('PlotPanel')
            ExpObj, FullImage = fileIO.loadFile(filename, expParams)
            
            if ExpObj.filetype == 'image':
                checkedTreatments = getTreatmentParameters()
                cartToPol.applyDataManipulations(ExpObj, expParams, checkedTreatments)
            
            expParams['WaterFile'] = ExpObj
            
            infobox = wx.FindWindowByName('InfoPanel')
            infobox.WriteText(os.path.split(filename)[1] + ' is the water sampe file.\n')
            
        if evt.GetId() == 4: #Average
            
            self.OnAverage()
            
        if evt.GetId() == 5:
            plotpanel = wx.FindWindowByName('PlotPanel')
            plotpanel.onPlotButton(0)
   
    def OnAverage(self, evt = None):
        filenames = self.GetSelectedFile()
            
        if len(filenames) > 1:
           ExpList = []
            
           for eachFilename in filenames:
               ExpObj, FullImage = fileIO.loadFile(eachFilename, expParams)
               ExpList.append(ExpObj)
                
           AvgExpObj = cartToPol.averageMeasurements(ExpList, expParams)
             
           plotpanel = wx.FindWindowByName('PlotPanel')
               
           path_file = os.path.split(AvgExpObj.param['filename'])
               
           AvgExpObj.param['filename'] = path_file[0] + 'AVG_' + path_file[1]
              
           plotpanel.PlotExperimentObject(AvgExpObj, axes = plotpanel.subplot1)

    def _OnLeftClick(self, evt):
        ''' When you leftclick an element in the list '''
#        state = wx.GetMouseState()
#        
#        if state.ShiftDown():
#            print 'SHIFT!'

        self.selectedFiles = []
        for eachFileIdx in self.fileListBox.GetSelections():
            self.selectedFiles.append(self.fileListBox.GetString(eachFileIdx))
        
    def _OnUpdateKey(self, evt):
        
        if evt.GetKeyCode() == 344:        # 344 = F5
            self.GetListOfFiles()
            self.FilterFileListAndUpdateListBox()
    
    def _OnDoubleClick(self, evt):
        
        selectedId = self.fileListBox.GetSelections()
        filename = self.fileListBox.GetString(selectedId[0])
        self.selected_file = os.path.join(self.path, filename)
    
        wx.FindWindowByName('PlotPanel').onPlotButton(0)
    
    def GetSelectedFile(self):
        ''' Returns a list of files with full path '''
        
        #print self.selectedFiles
        
        for each in range(0, len(self.selectedFiles)):
            self.selectedFiles[each] = os.path.join(self.path, self.selectedFiles[each])
        
        return self.selectedFiles
    
    def SetSelectedFile(self, filepath):
        
        self.selectedFiles = [filepath]
    
    def OnSetBackgroundFile(self, evt):
        
        if self.GetSelectedFile() == [] or self.GetSelectedFile() == None:
            return
        
        bgFilenameTxt = wx.FindWindowById(BGFILENAME_ID)
        self.bgFilename = self.GetSelectedFile()[0]                # Saves the filename with full path
        noPathfilename = os.path.split(self.bgFilename)[1]
        bgFilenameTxt.SetLabel(noPathfilename)
        
    def SetBackgroundFile(self, filename):
        
        bgFilenameTxt = wx.FindWindowById(BGFILENAME_ID)
        self.bgFilename = filename                # Saves the filename with full path
        noPathFilename = os.path.split(filename)[1]
        bgFilenameTxt.SetLabel(noPathFilename)
        
        infoPanel = wx.FindWindowByName('InfoPanel')
        infoPanel.WriteText(noPathFilename + ' is the background file.\n')
    
    def GetBackgroundPath(self):
        return self.bgFilename
    
    def OnSaveRad(self, evt):
        
        plottedExps = wx.FindWindowByName('PlotPanel').plottedExps

        OVERWRITE_ALL = 4
        SKIP_ALL_EXISITING = 5
        
        overwriteAll = False
        skipAllExisting = False

        if plottedExps:
            for each in plottedExps:
                
                fullPathFilename = each.param['filename']
                
                radFilename = fileIO.filenameWithoutExtension(each) + '.rad'

                if each.isBgSubbed == True:
                    radFilename = 'BSUB_' + radFilename

                #print each.isBgSubbed
                #print radFilename
                
                full_path_filename = each.param['filename']
                filePath = os.path.split(full_path_filename)[0]

                checkFilename = os.path.join(filePath, radFilename)
                
                fileExists = os.path.isfile(checkFilename)
                
                if fileExists and overwriteAll is False:

                    if skipAllExisting == False:
                        fileExistDialog = FileExistsDialog(radFilename, each)
                        answer = fileExistDialog.ShowModal()
                    
                        if answer == OVERWRITE_ALL:
                            overwriteAll = True
                        if answer == SKIP_ALL_EXISITING:
                            skipAllExisting = True
                    
                else:
                    filename = fileIO.saveMeasurement(each)    
                    wx.FindWindowByName('MainFrame').SetStatusText(filename + ' Saved!')
            
            self.GetListOfFiles()
            self.FilterFileListAndUpdateListBox()
            
#    def SaveSingleRadFileAs(self, ExpObj):
#        
#        fullPathFilename = ExpObj.param['filename']
#        radFilename = fileIO.filenameWithoutExtension(ExpObj) + '.rad'
#        
##        if ExpObj.isBifted == True:
##                radFilename = 'BIFT_' + radFilename
##        elif ExpObj.isBgSubbed == True:
##                radFilename = 'BSUB_' + radFilename
#        
#        dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.OVERWRITE_PROMPT)  
#        dialog.SetFilename(radFilename)
#            
#        if dialog.ShowModal() == wx.ID_OK:
#            file = dialog.GetPath()
#            ExpObj.param['filename'] = file
#                
#            fileIO.saveMeasurement(ExpObj, NoChange = True) 
#            # Destroy the dialog
#            
#        dialog.Destroy()
        
    def SaveSingleRadFile(self, ExpObj):
        
        OVERWRITE_ALL = 4
        SKIP_ALL_EXISITING = 5
        
        overwriteAll = False
        skipAllExisting = False

        if ExpObj != None:
                
            fullPathFilename = ExpObj.param['filename']
                
            radFilename = fileIO.filenameWithoutExtension(ExpObj) + '.rad'
#
#            if ExpObj.isBifted == True:
#                radFilename = 'BIFT_' + radFilename
#            elif ExpObj.isBgSubbed == True:
#                radFilename = 'BSUB_' + radFilename
                
            full_path_filename = ExpObj.param['filename']
            filePath = os.path.split(full_path_filename)[0]

            checkFilename = os.path.join(filePath, radFilename)
                
            fileExists = os.path.isfile(checkFilename)
            
            
            dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.OVERWRITE_PROMPT)  
            dialog.SetFilename(radFilename)
            
            if dialog.ShowModal() == wx.ID_OK:
                file = dialog.GetPath()
                ExpObj.param['filename'] = file
                
                fileIO.saveMeasurement(ExpObj, NoChange = True) 
            # Destroy the dialog
            dialog.Destroy()

#            if fileExists and overwriteAll is False:
#
#                if skipAllExisting == False:
#                    fileExistDialog = FileExistsDialog(radFilename, ExpObj)
#                    answer = fileExistDialog.ShowModal()
#                    
#                    if answer == OVERWRITE_ALL:
#                        overwriteAll = True
#                    if answer == SKIP_ALL_EXISITING:
#                        skipAllExisting = True
#                    
#            else:
#                filename = fileIO.saveMeasurement(ExpObj)    
#                wx.FindWindowByName('MainFrame').SetStatusText(filename + ' Saved!')
    
            self.GetListOfFiles()
            self.FilterFileListAndUpdateListBox()
    
    def _OnSetDirButton(self, evt):
        #onlineled = wx.FindWindowById(ONLINELED_ID)
        dirdlg = wx.DirDialog(self, "Please select directory:", '')
            
        if dirdlg.ShowModal() == wx.ID_OK:               
            self.path = dirdlg.GetPath()
            self.GetListOfFiles()
            self.UpdateDirLabel(self.path)
            self.UpdateFileListBox(self.FileList)
            self.FilterFileListAndUpdateListBox()       
            
    def UpdateDirLabel(self, path):
        self.DirLabel.SetValue(path)
        
    def GetListOfFiles(self):
        self.FileList = os.listdir(self.path)
        
        FilesOnlyList = []    
        for filename in self.FileList:
            if os.path.isfile(os.path.join(self.path, filename)):
                FilesOnlyList.append(filename)
        self.FileList = FilesOnlyList
        
        return self.FileList
        
    def UpdateFileListBox(self, FileList):
        
        self.fileListBox.Clear()
        
        for each in range(0, len(FileList)):
            FileList[each] = str(FileList[each])
         
        FileList.sort(key = str.lower)
        
        for each in FileList:
            self.fileListBox.Append(each)
                          
    def UpdateFileListBox_Online(self):
        
        self.fileListBox.Clear()
        
        self.FileList = self.GetListOfFiles()
        self.UpdateFileListBox(self.FileList)
        self.FilterFileListAndUpdateListBox()
                            
class InfoPanel(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent, name = 'InfoPanel')
        
        infoSizer = wx.BoxSizer()
        
        self.infoTextBox = wx.TextCtrl(self, -1, 'Welcome to BioXTAS RAW!\n--------------------------------\n\n', style = wx.TE_MULTILINE)
        
        self.infoTextBox.SetBackgroundColour('BLACK')
        self.infoTextBox.SetForegroundColour('YELLOW')
        
        infoSizer.Add(self.infoTextBox, 1, wx.EXPAND)
        
        self.SetSizer(infoSizer)
        
    def WriteText(self, text):
        
        self.infoTextBox.AppendText(text)
        
    def Clear(self):
        
        self.infoTextBox.Clear()
         
class OnlineController:                                   
    def __init__(self, parent):
        
        self.parent = parent
        
        # Setup the online file checker timer
        self.onlineTimer = wx.Timer()
        
        self.onlineTimer.Bind(wx.EVT_TIMER, self.OnOnlineTimer, self.onlineTimer)

        self.Old_DirList = []
        self.isOnline = False
        self.seekDir = []
        self.bgFilename = None
        
        self.autoBgSubThread = None
    
        
    def OnOnlineButton(self, state):
        
        #onlineled = wx.FindWindowById(ONLINELED_ID)
        dirdlg = wx.DirDialog(self.parent, "Please select directory to survey:", '')
        
        if state == 'Online':
            
            if dirdlg.ShowModal() == wx.ID_OK:                
                path = dirdlg.GetPath()
                self.Old_DirList = os.listdir(path)
                self.seekDir = path
                self.UpdateOnlineStatus('Online')
        else:
            self.UpdateOnlineStatus('Offline')
            
    def UpdateOnlineStatus(self, status):
        
        #onlineled = wx.FindWindowById(ONLINELED_ID)
        #onlinebutton = wx.FindWindowById(ONLINEBUTTON_ID)
        
        if status == 'Online':
#            size = onlineled.GetSize()
#            onlineled.SetLabel('Online')
#            onlineled.SetSize(size)
#            onlineled.SetBackgroundColour((0,255,0))
#            onlinebutton.SetLabel('Go Offline')
            self.parent.SetStatusText('Mode: ONLINE', 2)
            self.OnOnline('Online')
            
        elif status == 'Offline':
#            size = onlineled.GetSize()
#            onlineled.SetLabel('Offline')
#            onlineled.SetSize(size)
#            onlineled.SetBackgroundColour((0,100,0))
#            onlinebutton.SetLabel('Go Online..')
            self.parent.SetStatusText('Mode: OFFLINE', 2)
            self.OnOnline('Offline')
            
    def SetPath(self, filepath):
        
        DirCtrl = wx.FindWindowByName('DirCtrlPanel')
        DirCtrl.SetSelectedFile(filepath)
        
    def UpdateFileList(self):
        
        DirCtrl = wx.FindWindowByName('DirCtrlPanel')
        DirCtrl.UpdateFileListBox_Online()
        
    def OnOnlineTimer(self, evt):
        ''' This function checks for new files and processes them as they come in '''

        print "Shields up, checker online!"
        
        infopanel = wx.FindWindowByName('InfoPanel')
        DirList = os.listdir(self.seekDir)
        
        if DirList != self.Old_DirList:
            for idx in range(0, len(DirList)):

                try:
                    chk = self.Old_DirList.index(DirList[idx])
                
                except ValueError:
                    
                    self.UpdateFileList()
                    self.Old_DirList.append(DirList[idx])
                                    
                    print DirList[idx]
                    infopanel.WriteText('Incomming file:\n' + str(DirList[idx] + '\n\n') )
                    filepath = os.path.join(self.seekDir, str(DirList[idx]))

                    if not(self._FileTypeIsExcluded(filepath)):
                        self.ProcessIncommingFile(filepath)
                        
    def ProcessIncommingFile(self, filepath):
        
        plotPanel = wx.FindWindowByName('PlotPanel')
        dirCtrlPanel = wx.FindWindowByName('DirCtrlPanel')

        self.SetPath(filepath)    #Plot thread gets the filepath from there
        
        autoSubtractEnabled = expParams['AutoBgSubtract']
        
        if autoSubtractEnabled:
            filenameIsBackground = self.CheckIfFilenameIsBackground(filepath)
            
            if filenameIsBackground:
                plotPanel.onPlotButton('onlineBackground') 
                
            else:
                
                if self.autoBgSubThread == None:
                    self.autoBgSubThread = AutoBgSubWorkerThread(self)
                    self.autoBgSubThread.start()
                    autoBgSubQueue.put([filepath])
                else:
                    autoBgSubQueue.put([filepath])
            
        else:
           plotPanel.onPlotButton(0) 
            
    def CheckIfFilenameIsBackground(self, filepath):
        
        filename = os.path.split(filepath)[1]
        
        bgPatternType = expParams['BgPatternType']
        bgPattern = expParams['BgPatternValue']
        
        if bgPatternType == 'contain':
            result = filename.find(bgPattern)
            
            print "result:", str(result)
            
            if result < 0:
                return False
            else:
                return True
            
        elif bgPatternType == 'start':
            
            return filename.startswith(bgPattern)   # A python string function
            
        elif bgPatternType == 'end':
            
            return filename.endswith(bgPattern)    # A python string function
    
    def _FileTypeIsExcluded(self, filename):
        
        if len(filename) > 4:
            
            extension = filename[-4:]
            
            for eachExcludedExtension in getGeneralParameters()['OnlineExcludedFileTypes']:
                
                if extension == eachExcludedExtension:
                    return True
            
        return False
                               
    def OnOnline(self, state):
        
        if state == 'Offline':
            self.onlineTimer.Stop()
            self.isOnline = False
        else:
            self.onlineTimer.Start(3000)
            self.isOnline = True

#------------- *** My Custom SpinCtrl's ****

class FloatSpinEvent(wx.PyCommandEvent):
    
    def __init__(self, evtType, id):
        
        wx.PyCommandEvent.__init__(self, evtType, id)
        
        self.value = 0
        
    def GetValue(self):
        return self.value
    
    def SetValue(self, value):
        self.value = value
        
myEVT_MY_SPIN = wx.NewEventType()
EVT_MY_SPIN = wx.PyEventBinder(myEVT_MY_SPIN, 1)

class FloatSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, initValue = None, button_style = wx.SP_VERTICAL, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        if initValue == None:
            initValue = '1.00'
        
        self.defaultScaleDivider = 100
        self.ScaleDivider = 100
        
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = button_style)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999) #Needed for proper function of button on Linux
                
        self.Scale = wx.TextCtrl(self, -1, initValue, size = (40,22), style = wx.TE_PROCESS_ENTER)
        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)
        
        sizer = wx.BoxSizer()
        
        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)
        
        self.oldValue = 0
        
        self.SetSizer(sizer)
                
    def CastFloatSpinEvent(self):
        
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)
        
        #print str(self.ScalerButton.GetValue())
    
    def OnScaleChange(self, event):
        
        val = self.Scale.GetValue()
        
        try:
            num_of_digits = len(val.split('.')[1])
            
            if num_of_digits == 0:
                self.ScaleDivider = self.defaultScaleDivider
            else:
                self.ScaleDivider = power(10, num_of_digits)
        except IndexError:
            self.ScaleDivider = self.defaultScaleDivider
            
        if val != self.oldValue:
            self.oldValue = val
            self.CastFloatSpinEvent()

    def OnSpinUpScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        newval = float(val) + (1/self.ScaleDivider)
        self.Scale.SetValue(str(newval))
        
        if newval != self.oldValue:            
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def OnSpinDownScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        newval = float(val) - (1/self.ScaleDivider)
        self.Scale.SetValue(str(newval))  
        
        if newval != self.oldValue:
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def GetValue(self): 
        value = self.Scale.GetValue()
        return value
    
    def SetValue(self, value):
        self.Scale.SetValue(value)
        
    
    
class IntSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, min = None, max = None, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = wx.SP_VERTICAL)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999)
        self.max = max
        self.min = min
        
        #if self.min:
            #print "min at: ", str(self.min)
        #    self.ScalerButton.SetMin(self.min)
        #    self.ScalerButton.SetMax(self.max)
        #else:
        #self.ScalerButton.SetMin(-9999)
        #self.ScalerButton.SetMax(99999)
        
        self.Scale = wx.TextCtrl(self, -1, str(min), size = (40,22), style = wx.TE_PROCESS_ENTER)
        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)
        
        sizer = wx.BoxSizer()
        
        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)
        
        self.oldValue = 0
        
        self.SetSizer(sizer)
                
    def CastFloatSpinEvent(self):
        
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)
        
        #print str(self.ScalerButton.GetValue())
    
    def OnScaleChange(self, event):
        
        self.ScalerButton.SetValue(0) # Resit spinbutton position for button to work in linux
        
        #print str(self.ScalerButton.GetValue())
        
        val = self.Scale.GetValue()
                
        if self.max != None:
            if float(val) > self.max:
                self.Scale.SetValue(str(self.max))
        if self.min != None:
            if float(val) < self.min:
                self.Scale.SetValue(str(self.min))
        
        if val != self.oldValue:
            self.oldValue = val
            self.CastFloatSpinEvent()

    def OnSpinUpScale(self, event):
        #self.ScalerButton.SetValue(80)

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        
        newval = int(val) + 1
        
        if self.max != None:
            if newval > self.max:
                self.Scale.SetValue(str(self.max))
            else:
                self.Scale.SetValue(str(newval))
        else:        
            self.Scale.SetValue(str(newval))
        
        if newval != self.oldValue:            
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def OnSpinDownScale(self, event):
        #self.ScalerButton.SetValue(80)

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        newval = int(val) - 1
        
        if self.min != None:
            if newval < self.min:
                self.Scale.SetValue(str(self.min))
            else:
                self.Scale.SetValue(str(newval))
        else:
            self.Scale.SetValue(str(newval))  
        
        if newval != self.oldValue:
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def GetValue(self): 
        value = self.Scale.GetValue()
        return value
    
    def SetValue(self, value):
        self.Scale.SetValue(str(value))
        #print int(value)
        #self.ScalerButton.SetValue(int(str(value)))
        
    def SetRange(self, minmax):
        
        self.max = minmax[1]
        self.min = minmax[0]

class ListSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, scrollList, minIdx = None, maxIdx = None, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        self.scrollList = scrollList
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = wx.SP_VERTICAL)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        
        self.Scale = wx.TextCtrl(self, -1, str(scrollList[0]), size = (40,22), style = wx.TE_PROCESS_ENTER)
        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)
        
        sizer = wx.BoxSizer()
        
        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)
   
        self.idx = 0
        
        if maxIdx == None:
            self.maxIdx = len(scrollList)-1
        else:
            self.maxIdx = maxIdx
            
        if minIdx == None:
            self.minIdx = 0
        else:
            self.minIdx = minIdx
        
        self.oldValue = 0
        
        self.SetSizer(sizer)
                
    def CastFloatSpinEvent(self):
        
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)
    
    def OnScaleChange(self, event):
        
        val = self.Scale.GetValue()
        
        if float(val) >= self.scrollList[self.maxIdx]:
            self.idx = self.maxIdx
            self.Scale.SetValue(str(self.scrollList[self.idx]))
            self.CastFloatSpinEvent()
            return
        
        if float(val) <= self.scrollList[self.minIdx]:
            self.idx = self.minIdx
            self.Scale.SetValue(str(self.scrollList[self.idx]))
            self.CastFloatSpinEvent()
            return
                
        currentmin = self.scrollList[0]
        currentidx = 0
        changed = False
        for i in range(0,len(self.scrollList)):
            chk = abs(self.scrollList[i]-float(val))
            
            if chk < currentmin:
                currentmin = chk
                currentidx = i
                changed = True
        
        if changed == True:
            self.idx = currentidx
            self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        self.CastFloatSpinEvent()
                
#        if self.max != None:
#            if float(val) > self.max:
#                self.Scale.SetValue(str(self.max))
#        if self.min != None:
#            if float(val) < self.min:
#                self.Scale.SetValue(str(self.min))
#        
#        if val != self.oldValue:
#            self.oldValue = val

    def OnSpinUpScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        
        self.idx = self.idx + 1
        
        if self.idx > self.maxIdx:
            self.idx = self.maxIdx
            
        self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        self.CastFloatSpinEvent()
        
    def OnSpinDownScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        self.idx = self.idx - 1
        
        if self.idx < self.minIdx:
            self.idx = self.minIdx
        
        self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        self.CastFloatSpinEvent()
        
    def GetValue(self): 
        value = self.Scale.GetValue()
        return value
    
    def SetValue(self, value):
        self.Scale.SetValue(str(value))
        
    def SetRange(self, minmax):
        self.max = minmax[1]
        self.min = minmax[0]
    
    def SetIdx(self, idx):
        self.idx = idx
        self.Scale.SetValue(str(self.scrollList[self.idx]))
    
    def GetIdx(self):
        return self.idx
        
    def SetList(self, scrollList):
        self.idx = 0
        self.scrollList = scrollList
        self.maxIdx = len(scrollList)-1
        self.minIdx = 0
        self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        
#----------- **** The Notebook Pages ****
                    
class PlotPage(wx.Panel):
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        # *************** buttons ****************************

        DirPanel = DirCtrlPanel_2(self, wx.NewId())    # not really a panel.. its a widget. too lazy to change the name
        
        self.buttonData = (("Average", DirPanel.OnAverage),
                           ("Plot", plotpanel.onPlotButton),
                           ("Clear All", plotpanel.OnClearAll),
                           ("Set Bg", DirPanel.OnSetBackgroundFile),
                           ("Save Data", DirPanel.OnSaveRad),
                           ("Sub'n'Plot", plotpanel.OnSubnPlot))

        self.NO_OF_BUTTONS_IN_EACH_ROW = 3
        
        bgLabelSizer = self.CreateBackgroundFileLabels()
        buttonSizer = self.CreateButtons()
        
        # *************** Directory Control ***********************
        b2sizer = wx.BoxSizer(wx.VERTICAL) 
        b2sizer.Add((10,10), 0)
        b2sizer.Add(bgLabelSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE, 10) 
        b2sizer.Add((5,5))
        b2sizer.Add(DirPanel, 1, wx.EXPAND| wx.LEFT | wx.RIGHT, 10)
        b2sizer.Add(buttonSizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)                      

        self.SetSizer(b2sizer)
        
    def CreateBackgroundFileLabels(self):
        
        #BgFileLabel = wx.StaticText(self, -1, 'Background File:')
        box = wx.StaticBox(self, -1, 'Background File:')
        bgLabelSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        BgFilename = wx.StaticText(self, BGFILENAME_ID, 'None')
        BgFilename.SetMinSize((230,20))
        
        bgLabelSizer.Add(BgFilename, 1, wx.EXPAND)
        
        return bgLabelSizer
        
    def CreateButtons(self):
        
        noOfButtons = len(self.buttonData)
        noOfRows = int(math.ceil(noOfButtons / self.NO_OF_BUTTONS_IN_EACH_ROW))
        
        buttonSizer = wx.GridSizer( cols = self.NO_OF_BUTTONS_IN_EACH_ROW, rows = noOfRows)
        
        for buttonTxt, bindfunc in self.buttonData:
            button = wx.Button(self, -1, buttonTxt)
            button.Bind(wx.EVT_BUTTON, bindfunc)
            
            buttonSizer.Add(button, 1, wx.ALIGN_CENTER | wx.EXPAND)
        
            if buttonTxt == 'Undo':
                button.Enable(False)
                
        return buttonSizer    
            

#class OptionsPage(wx.Panel):
#    def __init__(self, parent, id):
#        wx.Panel.__init__(self, parent, id, name = 'OptionsPage')
#        
#        self.expParamsInGUI = {'NormalizeConst'    : (wx.NewId(), 'value', 'float'),
#                               'NormalizeConstChk' : (wx.NewId(), 'bool'),
#                               'NormalizeM2'  : (wx.NewId(), 'bool'),
#                               'NormalizeM1'  : (wx.NewId(), 'bool'),
#                               
#                               'NormalizeTime': (wx.NewId(), 'bool'),
#                               'NormalizeTrans':(wx.NewId(), 'bool')}
#                               
#                               
##                               'NormalizeAbs' : (wx.NewId(), 'bool'),
##                               'Calibrate'    : (wx.NewId(), 'bool'),
##                               'CalibrateMan' : (wx.NewId(), 'bool')}
##                               'Binsize'      : (wx.NewId(), 'value', 'int'),
##
##                               'Xcenter'      : (wx.NewId(), 'value', 'float'),
##                               'Ycenter'      : (wx.NewId(), 'value', 'float'),
##
##                               'QrangeLow'    : (wx.NewId(), 'value', 'int'),
##                               'QrangeHigh'   : (wx.NewId(), 'value', 'int'),
##                  
##                               'PixelCalX'    : (wx.NewId(), 'value', 'int')}
#             
#        self.maskIds = { 'BeamStopMask' : wx.NewId(),
#                         'ReadoutMask'  : wx.NewId()}
#                
#        #self.maskdata = (("Beamstop Mask:", self.maskIds['BeamStopMask'], "Set..", self.OnSetMask),
#        #                 ("Readout Mask:", self.maskIds['ReadoutMask'], "Set..", self.OnSetReadoutMask))
#
##        self.expsettingsdata = (("X center:", self.expParamsInGUI['Xcenter'][0]),
##                                ("Y center:", self.expParamsInGUI['Ycenter'][0]),
##                                ("AgBe Calib. Pixels:", self.expParamsInGUI['PixelCalX'][0]))
##                            
##        
##        self.expsettings_spin = (("Binning Size:", (self.expParamsInGUI['Binsize'][0], wx.NewId())),
##                                 ("Q-Low (pixels):", (self.expParamsInGUI['QrangeLow'][0], wx.NewId())),
##                                 ("Q-High (pixels):", (self.expParamsInGUI['QrangeHigh'][0], wx.NewId())))
#        
#        self.treatmentdata = (("Normalize by Monitor 2", self.expParamsInGUI['NormalizeM2'][0], 'normM2'),
#                              ("Normalize by Monitor 1", self.expParamsInGUI['NormalizeM1'][0], 'normM1'),
#                              ("Normalize by M2/M1 Factor", self.expParamsInGUI['NormalizeTrans'][0], 'normTrans'),
#                              ("Normalize by Exposure Time", self.expParamsInGUI['NormalizeTime'][0], 'normExposure'))
#                    #          ("Absolute Scale Calibration", self.expParamsInGUI['NormalizeAbs'][0], 'normAbs'),
#                    #          ("Calibrate Q-range (AgBe)", self.expParamsInGUI['Calibrate'][0], 'calibQrange'),
#                    #          ("Calibrate Q-range (Distance)", self.expParamsInGUI['CalibrateMan'][0], 'calibQmanual'))
#        
#        
#        self.buttondata = (("Load", self.OnLoadSettings),
#                           ("Save", self.OnSaveSettings),
#                           ("Advanced..", self.OnAdvancedButton))
#        
#        self.NO_OF_BUTTONS_IN_EACH_ROW = 3
#
#        panelsizer = wx.BoxSizer(wx.VERTICAL)
#        #self.CreateMaskSettings(panelsizer)
#        
#        #panelsizer.Add(wx.StaticLine(self,-1),0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
#        
#        self.CreateTreatmentData(panelsizer)
#                
#        #self.CreateExpSettings(panelsizer)
#    
#        self.CreateButtons(panelsizer)
#        
#        self.SetSizer(panelsizer)
#        
#        self._UpdateFromExpParams()
#        
#        self.selectedTreatments = [1,2,'hello']
#        
#        self.maskLoadingThread = None
#        
#    def CreateNormByConstant(self):
#        
#        id = self.expParamsInGUI['NormalizeConst'][0]
#        chkid = self.expParamsInGUI['NormalizeConstChk'][0]
#        
#        sizer = wx.BoxSizer(wx.HORIZONTAL)
#    
#        chkBox = wx.CheckBox(self, chkid, 'Normalize by Constant :')
#        chkBox.Bind(wx.EVT_CHECKBOX, self.OnChkBox)
#        
#        ctrl = FloatSpinCtrl(self, id)
#        ctrl.Bind(EVT_MY_SPIN, self.OnTxtCtrlChange)
#        
#        sizer.Add(chkBox, 1, wx.EXPAND)
#        sizer.Add(ctrl, 0)
#        
#        return sizer
#        
#        
#    def OnAdvancedButton(self, event):
#        
#        self.ShowOptionsDialog()
#        
#    def GetParameter(self, parameter):
#        global expParams
#        return expParams[parameter]
#    
#    def ChangeParameter(self, parameter, value):
#        global expParams
#        expParams[parameter] = value
#        self._UpdateFromExpParams()
#    
#    def ReplaceExpParams(self, newExpParams):
#        
#        global expParams
#        expParams = newExpParams
#        
#    def OnChkBox(self, event):
#        
#        chkboxID = event.GetId()
#        
#        self._CorrectConflictingSettings(chkboxID)
#        self._UpdateToExpParams()
#        
#    def _CorrectConflictingSettings(self, chkboxID):
#    
#        norm1ID = self.expParamsInGUI['NormalizeM1'][0]
#        norm2ID = self.expParamsInGUI['NormalizeM2'][0]
#        norm3ID = self.expParamsInGUI['NormalizeTime'][0]
#        norm4ID = self.expParamsInGUI['NormalizeTrans'][0]
#        
#        normM1box = wx.FindWindowById(norm1ID)
#        normM2box = wx.FindWindowById(norm2ID)
#        normTimebox = wx.FindWindowById(norm3ID)
#        normTransbox = wx.FindWindowById(norm4ID)
#        
#        if chkboxID == self.expParamsInGUI['CalibrateMan'][0]:
#            calibChkBox = wx.FindWindowById(self.expParamsInGUI['Calibrate'][0])
#            calibChkBox.SetValue(False)
#        elif chkboxID == self.expParamsInGUI['Calibrate'][0]:
#            calibChkBox = wx.FindWindowById(self.expParamsInGUI['CalibrateMan'][0])
#            calibChkBox.SetValue(False)
#            
#        #################################################
#        #### IF Absolute Calibration Checkbox is pressed:
#        #################################################
#        
#        if chkboxID == self.expParamsInGUI['NormalizeAbs'][0]:
#            absChkBox = wx.FindWindowById(self.expParamsInGUI['NormalizeAbs'][0])
#            
#            if absChkBox.GetValue() == True:
#            
#                if expParams['WaterFile'] == None or expParams['EmptyFile'] == None:
#                    absChkBox.SetValue(False)
#                    wx.MessageBox('Please enter an Empty cell sample file and a Water sample file under advanced options.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)
#                else:
#                    pass
#                    #normM1box.SetValue(False)
#                    #normM2box.SetValue(False)
#                    #normTimebox.SetValue(False)
#                    #normTransbox.SetValue(False)
#                    
#                    #normTransbox.Enable(False)
#                    #normTimebox.Enable(False)
#                    
#            else:
#                normTransbox.Enable(True)
#                normTimebox.Enable(True)
#                
#        #################################################
#        #### IF AgBe Calibration Checkbox is pressed:
#        #################################################
#                
#        if chkboxID == self.expParamsInGUI['Calibrate'][0]:
#            calibChkBox = wx.FindWindowById(self.expParamsInGUI['Calibrate'][0])
#            wavelength  = expParams['WaveLength']
#            pixelsize   = expParams['DetectorPixelSize']
#            
#            if wavelength != 0 and pixelsize != 0:
#                pass
#            else:
#                calibChkBox.SetValue(False)
#                wx.MessageBox('Please enter a valid Wavelength and Detector Pixelsize in advanced options.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)                
#        
#        if chkboxID == self.expParamsInGUI['CalibrateMan'][0]:
#            calibChkBox = wx.FindWindowById(self.expParamsInGUI['CalibrateMan'][0])
#            wavelength  = expParams['WaveLength']
#            pixelsize   = expParams['DetectorPixelSize']            
#            smpDist     = expParams['SampleDistance']
#        
#            if wavelength != 0 and pixelsize != 0 and smpDist !=0:
#                pass
#            else:
#                calibChkBox.SetValue(False)
#                wx.MessageBox('Please enter a valid Wavelength, Detector Pixelsize and Sample-Detector\n' +
#                              'distance in advanced options/calibration.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)                    
#            
#    def CreateButtons(self, panelsizer):
#        
#        noOfButtons = len(self.buttondata)
#        noOfRows = int(math.ceil(noOfButtons / self.NO_OF_BUTTONS_IN_EACH_ROW))
#        
#        buttonSizer = wx.GridSizer( cols = self.NO_OF_BUTTONS_IN_EACH_ROW, rows = noOfRows)
#        
#        for name, bindfunc in self.buttondata:
#            button = wx.Button(self, -1, name)
#            button.Bind(wx.EVT_BUTTON, bindfunc, button, button.GetId())
#            buttonSizer.Add(button, 1, wx.ALIGN_CENTER | wx.EXPAND)
#                        
#        panelsizer.Add(buttonSizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_CENTER, 10)
#        
#    def CreateTreatmentData(self, panelsizer):
#        
#        box = wx.StaticBox(self, -1, 'Normalization / Calibration')
#        staticBoxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
#        staticBoxSizer.Add((5,5), 0)
#        
#        staticBoxSizer.Add(self.CreateNormByConstant(), 0, wx.LEFT | wx.EXPAND, 5)
#        staticBoxSizer.Add((5,5),0)
#        
#        treatmentSizer = wx.BoxSizer(wx.VERTICAL)
#        
#        for each, id, name in self.treatmentdata:
#            chkBox = wx.CheckBox(self, id, each)
#            chkBox.Bind(wx.EVT_CHECKBOX, self.OnChkBox)
#            treatmentSizer.Add(chkBox, 0, wx.BOTTOM, 10)
#        
#        staticBoxSizer.Add(treatmentSizer, 0, wx.BOTTOM | wx.LEFT, 5)
#        
#        panelsizer.Add(staticBoxSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
#        
#    def CreateMaskSettings(self, panelsizer):
#        
#        noOfRows = int(len(self.maskdata))
#        hSizer = wx.FlexGridSizer(cols = 3, rows = noOfRows, vgap = 3, hgap = 3)
#        
#        for labtxt, labl_ID, buttxt, bindfunc in self.maskdata:
#            
#            button = wx.Button(self, -1, buttxt, size = (45,22))
#            wx.EVT_BUTTON(button, button.GetId(), bindfunc)
#            label = wx.StaticText(self, -1, labtxt)
#            
#            filenameLabel = wx.TextCtrl(self, labl_ID, "None")
#            filenameLabel.SetEditable(False)
#        
#            hSizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
#            hSizer.Add(filenameLabel, 1, wx.EXPAND)
#            hSizer.Add(button, 1)
#            
#        hSizer.AddGrowableCol(1)
#        panelsizer.Add(hSizer, 0.1, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
#    
#    def CreateExpSettings(self, panelsizer):       
#        
#        box = wx.StaticBox(self, -1, '2D Reduction Parameters')
#        staticBoxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
#        staticBoxSizer.Add((5,5), 0)
#        
#        for eachText, id in self.expsettingsdata:
#            txt = wx.StaticText(self, -1, eachText)
#            
#            if id == self.expParamsInGUI['Xcenter'][0] or id == self.expParamsInGUI['Ycenter'][0]:
#                ctrl = FloatSpinCtrl(self, id)
#            else:    
#                ctrl = IntSpinCtrl(self, id, min = 0)
#                
#            ctrl.Bind(EVT_MY_SPIN, self.OnTxtCtrlChange)
#            
#            sizer = wx.BoxSizer(wx.HORIZONTAL)
#            sizer.Add(txt, 1, wx.EXPAND)
#            sizer.Add(ctrl, 0)
#            
#            staticBoxSizer.Add(sizer, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT, 5)
#            
#        for eachEntry in self.expsettings_spin:
#            
#            label = wx.StaticText(self, -1, eachEntry[0])
#            
#            spinSizer = wx.BoxSizer(wx.HORIZONTAL)
#            spinSizer.Add(label, 1, wx.EXPAND)
#            
#            for eachSpinCtrl in eachEntry[1:]:
#                txtctrl_id = eachSpinCtrl[0]
#                spin_id = eachSpinCtrl[1]
#                      
#                txtCtrl = IntSpinCtrl(self, txtctrl_id)
#                txtCtrl.Bind(EVT_MY_SPIN, self.OnTxtCtrlChange)
#                
#                spinSizer.Add(txtCtrl, 0)
#        
#            staticBoxSizer.Add(spinSizer, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT, 5)   
#        
#        panelsizer.Add(staticBoxSizer, 0.1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
#        
#    def OnTxtCtrlChange(self, evt):
#        
#        self._UpdateToExpParams()
#            
##    def OnSetMask(self, evt):
##        
##        mask_filename, mask_dir, mask_fullpath = self._GetMaskFile("Please choose the Beamstop mask file.")
##        
##        if mask_filename != None:
##            self.LoadBeamStopMask(mask_fullpath)
##            
##        return mask_filename
#            
##    def LoadBeamStopMask(self, mask_fullpath):
##        
##        global expParams
##        
##        #mask_filename = os.path.split(mask_fullpath)[1]
##        
##        if mask_fullpath:
##            #filename_label = wx.FindWindowById(self.maskIds['BeamStopMask'])
##            #filename_label.SetLabel(mask_filename)
##            
##            #progressThread = MyProgressBar(self)
##            #progressThread = None
##            
##            if self.maskLoadingThread == None:
##                self.maskLoadingThread = LoadMaskThread(self)
##                self.maskLoadingThread.start()
##                loadMaskQueue.put([mask_fullpath, 'beamstop', expParams, 'param'])
##            else:
##                loadMaskQueue.put([mask_fullpath, 'beamstop', expParams, 'param'])
##            
##            #progressThread.run()
##            
##    def LoadReadoutNoiseMask(self, mask_fullpath):
##        
##        global expParams
##        
##        #mask_filename = os.path.split(mask_fullpath)[1]
##        
##        if mask_fullpath:
##            
##            #filename_label = wx.FindWindowById(self.maskIds['ReadoutMask'])
##            #filename_label.SetLabel(mask_filename)
##                       
##            #progressThread = MyProgressBar(self)
##            #progressThread= None
##            
##            if self.maskLoadingThread == None:
##                self.maskLoadingThread = LoadMaskThread(self)
##                self.maskLoadingThread.start()
##                loadMaskQueue.put([mask_fullpath, 'readout', expParams, 'param'])
##            else:
##                loadMaskQueue.put([mask_fullpath, 'readout', expParams, 'param'])
##            
##        
##            #progressThread.run()
#            
#    def OnSetReadoutMask(self, evt):
#        (mask_filename, mask_dir, mask_fullpath) = self._GetMaskFile("Please choose the Readout mask file.")
#        
#        if mask_filename != None:
#            self.LoadReadoutNoiseMask(mask_fullpath)
#            
#        return mask_filename
#            
#    def OnLoadSettings(self, evt):
#        
#        #global expParams
#        
#        file = self._CreateFileDialog(wx.OPEN)
#        
#        if file:
#            
#            try:
#                FileObj = open(file, 'r')
#            except:
#                print >> sys.stderr, 'Error opening file!'
#            
#            try:
#                newExpParams = cPickle.load(FileObj)
#            except:
#                print >> sys.stderr, 'That was not a valid config file!.. dumbass..'
#                
#            FileObj.close()
#                        
#            self._UpdateFromExtExpParams(newExpParams)
#            self.UpdateMasks(newExpParams)
#
#    def UpdateMasks(self, newExpParams):
#        global expParams
#        
#        if newExpParams.has_key('BeamStopMaskParams'):    # To make it backwards compatible with older cfg files..
#            
#            expParams['BeamStopMaskParams'] = newExpParams['BeamStopMaskParams']
#            expParams['BeamStopMaskFilename'] = newExpParams['BeamStopMaskFilename']
#            
#            expParams['ReadOutNoiseMaskParams'] = newExpParams['ReadOutNoiseMaskParams']
#            expParams['ReadOutNoiseMaskFilename'] = newExpParams['ReadOutNoiseMaskFilename']
#                       
#            progressThread = MyProgressBar(self)
#        
#            workerThread = LoadMaskThread(self, progressThread, None, 'beamstop', expParams)
#            workerThread.start()
#            progressThread.run()
#
#            #filename_label = wx.FindWindowById(self.maskIds['BeamStopMask'])
#            #filename_label.SetLabel(str(expParams['BeamStopMaskFilename']))
#
#            #filename_label = wx.FindWindowById(self.maskIds['ReadoutMask'])
#            #filename_label.SetLabel(str(expParams['ReadOutNoiseMaskFilename']))
#                    
#        else:
#                expParams['BeamStopMask'] = None
#                expParams['BeamStopMaskFilename'] = None
#                expParams['BeamStopMaskParams'] = None
#                expParams['ReadOutNoiseMask'] = None
#                expParams['ReadOutNoiseMaskFilename'] = None
#                expParams['ReadOutNoiseMaskParams'] = None
#                
#                filename_label = wx.FindWindowById(self.maskIds['BeamStopMask'])
#                filename_label.SetLabel('None')
#                
#                filename_label = wx.FindWindowById(self.maskIds['ReadoutMask'])
#                filename_label.SetLabel('None')
#                
#    def UpdateSettings(self):
#        self._UpdateFromExpParams()
#    
#    def OnSaveSettings(self, evt):
#        ############################ KILLS BEAMSTOP MASK !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#        global expParams
#        
#        self._UpdateToExpParams()
#        
#        expParamsToSave = expParams
#    
#        file = self._CreateFileDialog(wx.SAVE)
#        
#        beamback = None
#        readback = None
#        
#        if file:
#            
#            if expParamsToSave['BeamStopMask'] != None:
#                beamback = expParamsToSave['BeamStopMask'].__copy__()
#            if expParamsToSave['ReadOutNoiseMask'] != None:
#                readback = expParamsToSave['ReadOutNoiseMask'].__copy__()
#        
#            expParamsToSave['BackgroundFile'] = None
#            expParamsToSave['BeamStopMask'] = None
#            expParamsToSave['ReadOutNoiseMask'] = None
#            
#            FileObj = open(file, 'w')
#            cPickle.dump(expParamsToSave, FileObj)
#            FileObj.close()
#            
#            expParamsToSave['BeamStopMask'] = beamback
#            expParamsToSave['ReadOutNoiseMask'] = readback
#        
#    def getCheckedDataTreatments(self):            
#        return getTreatmentParameters()
#    
#    def _CreateFileDialog(self, mode):
#        
#        file = None
#        
#        if mode == wx.OPEN:
#            filters = 'Config files (*.cfg)|*.cfg|All files (*.*)|*.*'
#            dialog = wx.FileDialog( None, style = mode, wildcard = filters)
#        if mode == wx.SAVE:
#            filters = 'Config files (*.cfg)|*.cfg'
#            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters)        
#        
#        # Show the dialog and get user input
#        if dialog.ShowModal() == wx.ID_OK:
#            file = dialog.GetPath()
#            
#        # Destroy the dialog
#        dialog.Destroy()
#        
#        return file
#        
#    def _UpdateToExpParams(self):
#        
#        for eachKey in self.expParamsInGUI:
#            
#            id = self.expParamsInGUI.get(eachKey)[0]
#            type = self.expParamsInGUI.get(eachKey)[1]
#            value = wx.FindWindowById(id).GetValue()
#            
#            if type == 'bool':
#                expParams[eachKey] = value
#            
#            if type == 'value':
#                
#                valtype = self.expParamsInGUI.get(eachKey)[2]
#                
#                if valtype == 'int':
#                    expParams[eachKey] = int(value)
#                else:
#                    expParams[eachKey] = float(value)
#    
#    def _UpdateFromExpParams(self):
#        
#        for eachKey in self.expParamsInGUI:
#            
#            id = self.expParamsInGUI.get(eachKey)[0]
#            type = self.expParamsInGUI.get(eachKey)[1]
#            value = expParams.get(eachKey)
#            
#            if type == 'bool':
#                chkbox = wx.FindWindowById(id)
#                
#                if value:
#                    chkbox.SetValue(True)
#                elif not(value):
#                    chkbox.SetValue(False)
#                    
#            if type == 'value':
#                ctrl = wx.FindWindowById(id)
#                ctrl.SetValue(str(value))
#                
#                # Set the spin buttons to the value in expparams
##                for each in self.expsettings_spin:
##                    
##                    param_id = each[1][0]
##                    spin_id = each[1][1]
#                    
#                    #if id == param_id:
#                        #spinbutton = wx.FindWindowById(spin_id)
#                        #spinbutton.SetValue(int(value))
#       
#    def _UpdateFromExtExpParams(self, newExpParams):
#        
#         global expParams
#         
#         for key in newExpParams.iterkeys():
#             expParams[key] = newExpParams[key]
#        
#         for eachKey in self.expParamsInGUI:
#            
#            id = self.expParamsInGUI.get(eachKey)[0]
#            type = self.expParamsInGUI.get(eachKey)[1]
#            value = newExpParams.get(eachKey)
#            
#            if value != None:
#                if type == 'bool':
#                    chkbox = wx.FindWindowById(id)
#                
#                    if value:
#                        chkbox.SetValue(True)
#                    elif not(value):
#                        chkbox.SetValue(False)
#                        
#                    expParams[eachKey] = value
#                    
#                if type == 'value':
#                    ctrl = wx.FindWindowById(id)
#                    ctrl.SetValue(str(value))
#                    
#                    expParams[eachKey] = value
#                
#                # Set the spin buttons to the value in expparams
#                    for each in self.expsettings_spin:
#                        param_id = each[1][0]
#                        spin_id = each[1][1]
#        
#        
#           
#    def _GetMaskFile(self, Text):
#        
#        
#        #filedlg = wx.FileDialog(self, Text, '', '', '*.msk', wx.OPEN)
#        
#        filters = 'Mask files (*.msk)|*.msk|All files (*.*)|*.*'
#        filedlg = wx.FileDialog( None, style = wx.OPEN, wildcard = filters)
#        
#        if filedlg.ShowModal() == wx.ID_OK:
#            mask_filename = filedlg.GetFilename()
#            mask_dir = filedlg.GetDirectory()
#            mask_fullpath = filedlg.GetPath()
#            filedlg.Destroy()
#            
#            return (mask_filename, mask_dir, mask_fullpath)
#        else:
#            filedlg.Destroy()
#            return (None, None, None)

class ManipFilePanel(wx.Panel):
    def __init__(self, parent, ExpObj):
        
        self.ExpObj = ExpObj
        filename = os.path.split(ExpObj.param['filename'])[1]
        
        self.ExpObj.itempanel = self

#        if ExpObj.isBifted == True:
#            filename = 'BIFT_' + filename
#        elif ExpObj.isBgSubbed == True:
#            filename = 'BSUB_' + filename

        #font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        #self.statusLabel.SetFont(font)  
        
        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)
        
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseClick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightMouseClick)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        #self.Bind(wx.EVT_CHAR, self.OnKeyPress)
        
                                       #Label, TextCtrl_ID, SPIN_ID
        self.qmax = len(ExpObj.i_raw)
                             
        self.spinControls = (("nBegin:", wx.NewId(), (1, self.qmax-1), 'nlow'),        
                             ("nEnd:", wx.NewId(), (2, self.qmax), 'nhigh'))
        
        self.floatSpinControls = (("Scale:", wx.NewId(), 'scale', str(ExpObj.scaleval), self.OnFloatSpinCtrlChange),
                                  ("Offset:", wx.NewId(), 'offset', str(ExpObj.offsetval), self.OnFloatSpinCtrlChange))
    
        filenameLabel = wx.StaticText(self, -1, filename)
        #filenameLabel = wx.TextCtrl(self, -1, filename)
        
        filenameLabel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseClick)
        filenameLabel.Bind(wx.EVT_RIGHT_DOWN, self.OnRightMouseClick)
        filenameLabel.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)

        if ExpObj.type == 'bift':
            filenameLabel.SetForegroundColour(wx.Colour(0,200,0))

        elif ExpObj.isBgSubbed == True:
            filenameLabel.SetForegroundColour(wx.Colour(255,0,0))
            
        self.SelectedForPlot = wx.CheckBox(self, -1)
        self.SelectedForPlot.SetValue(True)
        self.SelectedForPlot.Bind(wx.EVT_CHECKBOX, self.OnChkBox)

        self.bglabel = wx.StaticText(self,-1, '    ')
        self.bglabel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseClick)
        self.bglabel.Bind(wx.EVT_RIGHT_DOWN, self.OnRightMouseClick)
        self.bglabel.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        

        panelsizer = wx.BoxSizer()
        panelsizer.Add(self.SelectedForPlot, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 3)
        panelsizer.Add(filenameLabel, 1, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 3)
        panelsizer.Add(self.bglabel, 0, wx.TOP | wx.RIGHT, 2)
        
        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(panelsizer, 1, wx.EXPAND)
        
        controlSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 3, hgap = 7)
        
        self.CreateSimpleSpinCtrls(controlSizer)
        self.CreateFloatSpinCtrls(controlSizer)
        
        self.topsizer.Add((5,5),0)
        self.topsizer.Add(controlSizer, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 3)
        
        self.SetSizer(self.topsizer)
       
        self.Selected = False     
    
    def OnKeyPress(self, evt):
        
        key = evt.GetKeyCode()
        
        if key == wx.WXK_DELETE and self.Selected == True:
            self.RemoveSelf()
            
    def OnChkBox(self, evt):
        
        if self.ExpObj.type == 'bift':
            plotpanel = wx.FindWindowByName('BIFTPlotPanel')
            plotpanel.togglePlot(self.ExpObj)
        else:
            plotpanel = wx.FindWindowByName('PlotPanel')
            plotpanel.togglePlot(self.ExpObj)
        
    def OnFloatSpinCtrlChange(self, evt):
        
        id = evt.GetId()
        value = evt.GetValue()
        
        for eachLabel, eachId, eachName, eachInitValue, eachBindfunc in self.floatSpinControls:
            
            if id == eachId:
                
                if eachName == 'scale':
                    self.ExpObj.scale(value)
                elif eachName == 'offset':
                    self.ExpObj.offset(value)
        
        self.ExpObj.plotPanel.UpdateSinglePlot(self.ExpObj)
        self.ExpObj.plotPanel.canvas.draw()
        
        
                
    def OnQrangeSpinCtrlChange(self, evt):
        
        qminID = self.spinControls[0][1]
        qmaxID = self.spinControls[1][1]
        
        qminCtrl = wx.FindWindowById(qminID)
        qmaxCtrl = wx.FindWindowById(qmaxID)
        
        qmin = int(qminCtrl.GetValue())
        qmax = int(qmaxCtrl.GetValue())

        if qmin < qmax:        
            self.ExpObj.setQrange((qmin-1, qmax))  
        
            self.ExpObj.plotPanel.UpdateSinglePlot(self.ExpObj)
            self.ExpObj.plotPanel.canvas.draw()
        
    def OnLeftMouseClick(self, evt):
        ctrlIsDown = evt.ControlDown()
        shiftIsDown = evt.ShiftDown()
        
        manipulationPage = wx.FindWindowByName('ManipulationPage')
        
        if shiftIsDown:
            try:
                
                firstMarkedItemIdx = manipulationPage.allManipulationItems.index(manipulationPage.GetSelectedItems()[0])
                lastMarkedItem = manipulationPage.GetSelectedItems()[-1]
                lastMarkedItemIdx = manipulationPage.allManipulationItems.index(lastMarkedItem)
                
                thisItemIdx = manipulationPage.allManipulationItems.index(self)
            
                if lastMarkedItemIdx > thisItemIdx:
                    adj = 0
                    idxs = [firstMarkedItemIdx, thisItemIdx]
                else:
                    idxs = [lastMarkedItemIdx, thisItemIdx]
                    adj = 1
                
                
                topItem = max(idxs)
                bottomItem = min(idxs)
            
                for each in manipulationPage.allManipulationItems[bottomItem+adj:topItem+adj]:
                    each.ToggleSelect()
            except IndexError:
                pass
            
        elif ctrlIsDown:
            self.ToggleSelect()
        else:
            manipulationPage.DeselectAllExceptOne(self)
            self.ToggleSelect()

        
    def OnRightMouseClick(self, evt):
        manipulationPage = wx.FindWindowByName('ManipulationPage')
        
        if not self.Selected:
            self.ToggleSelect()
            manipulationPage.DeselectAllExceptOne(self)
                    
        self.ShowPopupMenu()

    def ToggleSelect(self):
        
        if self.Selected:
            self.Selected = False
            self.SetBackgroundColour(wx.Color(250,250,250))
        else:
            self.Selected = True
            self.SetBackgroundColour(wx.Color(200,200,200))
            self.SetFocusIgnoringChildren()
        
        self.Refresh()

    def ShowPopupMenu(self):

        menu = wx.Menu()
        ManipulationPage = wx.FindWindowByName('ManipulationPage')
        selectedExpObjs = ManipulationPage.GetSelectedExpObjs()
        
        iftmenu = wx.Menu()
        iftmenu.Append(10, 'Run BIFT')
        iftmenu.Append(11, 'Run GNOM using current Dmax')
        iftmenu.AppendSeparator()
        iftmenu.Append(12, 'Add to IFT list')
        
        if len(selectedExpObjs) <= 1:
            menu.Append(1, 'Set as Background file')
            #menu.AppendSeparator()
        
        if expParams['BackgroundFile'] != None:
            menu.Append(4, 'Substract Background')
        
        if len(selectedExpObjs) > 1:
            menu.Append(6, 'Average selected item(s)' )
            
        menu.AppendSeparator()
        menu.Append(5, 'Remove selected item(s)' )
        menu.AppendSeparator()
        menu.Append(13, 'Guinier fit...')
        menu.AppendMenu(3, 'Indirect Fourier Transform', iftmenu)
        menu.AppendSeparator()
        menu.Append(8, 'Move curve to top plot')
        menu.Append(9, 'Move curve to bottom plot')
        menu.AppendSeparator()
        menu.Append(7, 'Save selected file(s)')
        
        self.Bind(wx.EVT_MENU, self._OnPopupMenuChoice) 
        
        self.PopupMenu(menu)
        
    def setAsBackground(self):
        
        global expParams
        
        dirCtrlPanel = wx.FindWindowByName('DirCtrlPanel')
        dirCtrlPanel.SetBackgroundFile(self.ExpObj.param['filename'])
            
        if expParams['BackgroundFile'] != None:
            try:
                # Exception is thrown if expParams[backgroundgile] holds a deleted ExpObj
                expParams['BackgroundFile'].itempanel.bglabel.SetLabel('')
            except:
                pass
            
        expParams['BackgroundFile'] = self.ExpObj

        self.bglabel.SetLabel('BG')
            
        self.topsizer.Layout()
        self.SetVirtualSize(self.GetBestVirtualSize())
        self.Refresh()    
    
    def _OnPopupMenuChoice(self, evt):
                
        ManipulationPage = wx.FindWindowByName('ManipulationPage')
        analysisPage = wx.FindWindowByName('AutoAnalysisPage')
        plotpanel = wx.FindWindowByName('PlotPanel')
        dirctrlpanel = wx.FindWindowByName('DirCtrlPanel')
        
        if evt.GetId() == 1:
            #Set background
            self.setAsBackground()
            
        if evt.GetId() == 3:
            #IFT
            analysisPage.runBiftOnExperimentObject(self.ExpObj, expParams)
        
        if evt.GetId() == 4:
            #Subtract and plot
            selectedExpObjsList = ManipulationPage.GetSelectedExpObjs()
            plotpanel.SubtractAndPlot(selectedExpObjsList)
        
        if evt.GetId() == 5:
            #Delete
            self.RemoveSelf()
        
        if evt.GetId() == 6:
            #check boundaries, Average and plot 
            selectedExpObjsList = ManipulationPage.GetSelectedExpObjs()
            AvgExpObj = cartToPol.averageMeasurements(selectedExpObjsList, expParams)
            plotpanel.PlotExperimentObject(AvgExpObj, axes = plotpanel.subplot1)
            
        if evt.GetId() == 7:
            #Save file
            selectedExpObjsList = ManipulationPage.GetSelectedExpObjs()
            
            for each in selectedExpObjsList:
                dirctrlpanel.SaveSingleRadFile(each)
                
        if evt.GetId() == 8:
            #Move to top plot
            selectedExpObjsList = ManipulationPage.GetSelectedExpObjs()
            ManipulationPage.MovePlots(selectedExpObjsList, plotpanel.subplot1)
                
        if evt.GetId() == 9:
            #Move to bottom plot
            selectedExpObjsList = ManipulationPage.GetSelectedExpObjs()
            ManipulationPage.MovePlots(selectedExpObjsList, plotpanel.subplot2)
            
        if evt.GetId() == 13:
            #Guinier fit
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedExpObjsList = ManipulationPage.GetSelectedExpObjs()
            
            ExpObj = selectedExpObjsList[0]
            Mainframe.ShowGuinierFitFrame(ExpObj)
            
        if evt.GetId() == 10:
            #BIFT
            analysisPage = wx.FindWindowByName('AutoAnalysisPage')
            analysisPage.runBiftOnExperimentObject(self.ExpObj, expParams)
            
        if evt.GetId() == 12:
            #Add to IFT List
            autoanalysis = wx.FindWindowByName('AutoAnalysisPage')
            
            for ExpObj in ManipulationPage.GetSelectedExpObjs(): 
                autoanalysis.addExpObjToList(ExpObj)
            
            wx.CallAfter(wx.MessageBox, 'Finished adding file(s) to the IFT list', 'Finished')
            
        if evt.GetId() == 11:
            #GNOM
            analysisPage.runBiftOnExperimentObject(self.ExpObj, expParams)
            
    def RemoveSelf(self):
        manipulationPage = wx.FindWindowByName('ManipulationPage')
        
        #Has to be callafter under Linux.. or it'll crash
        wx.CallAfter(manipulationPage.RemoveSelectedItems)
    
    def CreateFloatSpinCtrls(self, controlSizer):
        
        for label, id, name, initValue, bindfunc in self.floatSpinControls:
            
            label = wx.StaticText(self, -1, label)
            
            label.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseClick)
            label.Bind(wx.EVT_RIGHT_DOWN, self.OnRightMouseClick)
            label.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
            
            
            spinCtrl = FloatSpinCtrl(self, id, initValue)
            spinCtrl.Bind(EVT_MY_SPIN, bindfunc)
            
            controlSizer.Add(label, 1)
            controlSizer.Add(spinCtrl, 1)
        
    def CreateSimpleSpinCtrls(self, controlSizer):
        
        for eachSpinCtrl in self.spinControls:
                spin_id = eachSpinCtrl[1]
                spinLabelText = eachSpinCtrl[0]
                spinRange = eachSpinCtrl[2]
                spinName = eachSpinCtrl[3]
                
                spinMin = spinRange[0]
                spinMax = spinRange[1]
    
                if spinName == 'nhigh':
                    
                    if self.ExpObj.filetype == 'image':
                        init = self.ExpObj.getQrange()[1] 
                    else:
                        init = spinMax
                else:
                    if self.ExpObj.filetype == 'image':
                        init = self.ExpObj.getQrange()[0] + 1   # WHY +1 ???? 
                    else:
                        init = spinMin
                    
                SpinLabel = wx.StaticText(self, -1, spinLabelText)
                SpinLabel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseClick)
                SpinLabel.Bind(wx.EVT_RIGHT_DOWN, self.OnRightMouseClick)
                SpinLabel.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
                        
                SpinControl = IntSpinCtrl(self, spin_id, min = spinMin, max = spinMax)
                SpinControl.SetValue(init)  
                SpinControl.Bind(EVT_MY_SPIN, self.OnQrangeSpinCtrlChange)
                
                spinSizer = wx.BoxSizer()
                spinSizer.Add(SpinControl, 0)
                
                controlSizer.Add(SpinLabel, 1)        
                controlSizer.Add(spinSizer, 1)                    
        
class ManipulationPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, name = 'ManipulationPage')
        
        self.buttonData = ( ('IFT', self.OnBift),
                            ('Average', self.OnAverage),
                            ('Delete', self.OnDelete),
                            ('Save', self.OnSave),
                            ('Set Bg', self.OnSetBg),
                            ('Sub Bg', self.OnSubBg))

        self.panelsizer = wx.BoxSizer(wx.VERTICAL)

        self.underpanel = scrolled.ScrolledPanel(self, -1, style = wx.BORDER_SUNKEN)
      
        self.underpanel.SetVirtualSize((200, 200))
        self.underpanel.SetScrollRate(20,20)
      
        self.allManipulationItems = []

        self.underpanel_sizer = wx.BoxSizer(wx.VERTICAL)    
        self.underpanel.SetSizer(self.underpanel_sizer)
        
        #self.tstbutton = wx.Button(self, -1, "Test")
        #self.clrbutton = wx.Button(self, -1, "Clear")
        
        self.topLabel = wx.StaticText(self, -1, '- Plot List -')
        
        self.buttonSizer = self.createButtons()
        #self.tstbutton.Bind(wx.EVT_BUTTON, self.OnTest)
        #self.clrbutton.Bind(wx.EVT_BUTTON, self.ClearList)
        
        self.panelsizer.Add(self.topLabel, 0, wx.ALIGN_CENTER | wx.TOP, 5)
        self.panelsizer.Add(self.underpanel, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 3)
        self.panelsizer.Add(self.buttonSizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.TOP |wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        #self.panelsizer.Add((5,5),0)
        #self.panelsizer.Add(self.tstbutton, 0, wx.BOTTOM, 3)
        #self.panelsizer.Add(self.clrbutton, 0, wx.BOTTOM, 3)
        
        self.SetSizer(self.panelsizer)
        
        self.Bind(EVT_MANIP_ITEM, self.OnNewItem)
        
    def createButtons(self):
        
        cols = 3
        rows = round(len(self.buttonData)/cols)
        
        sizer = wx.GridSizer(cols = cols, rows = rows)
        
        for each in self.buttonData:
            label = each[0]
            func = each[1]
            
            button = wx.Button(self, -1, label)
            button.Bind(wx.EVT_BUTTON, func)
            
            sizer.Add(button, 1, wx.ALIGN_CENTER | wx.EXPAND)
        
        return sizer

    def OnBift(self, evt):
        
        analysisPage = wx.FindWindowByName('AutoAnalysisPage')
        ExpList = self.GetSelectedExpObjs()
        
        if ExpList == [] or ExpList == None:
            return
        
        analysisPage.runBiftOnExperimentObject(ExpList[0], expParams)
    
    def OnDelete(self, evt):
        selectedExpObjsList = self.GetSelectedItems()
        
        for each in selectedExpObjsList:
            try:
                each.RemoveSelf()
            except:
                pass
    
    def OnAverage(self, evt):
        #check boundaries, Average and plot 
        global expParams
        
        selectedExpObjsList = self.GetSelectedExpObjs()

        if selectedExpObjsList == [] or selectedExpObjsList == None or len(selectedExpObjsList) < 2:
            wx.MessageBox("Please select at least two items for averaging.")
            return
        
        AvgExpObj = cartToPol.averageMeasurements(selectedExpObjsList, expParams)
        
        if AvgExpObj == None:
            return
        
        path_file = os.path.split(AvgExpObj.param['filename'])
                
        AvgExpObj.param['filename'] = path_file[0] + 'AVG_' + path_file[1]
                
        plotpanel = wx.FindWindowByName('PlotPanel')
        plotpanel.PlotExperimentObject(AvgExpObj, axes = plotpanel.subplot1)
            
    def OnSave(self, evt):
        dirctrlpanel = wx.FindWindowByName('DirCtrlPanel')
            
        selectedExpObjsList = self.GetSelectedExpObjs()
        
        if selectedExpObjsList == [] or selectedExpObjsList == None:
            return
            
        for each in selectedExpObjsList:
            dirctrlpanel.SaveSingleRadFile(each)
                
    def OnSetBg(self, evt):
        ExpList = self.GetSelectedExpObjs()
        
        if ExpList == [] or ExpList == None:
            return
        
        ExpList[0].itempanel.setAsBackground()
        
    def OnSubBg(self, evt):
        plotpanel = wx.FindWindowByName('PlotPanel')            
        selectedExpObjsList = self.GetSelectedExpObjs()

        if selectedExpObjsList == [] or selectedExpObjsList == None:
            return

        plotpanel.SubtractAndPlot(selectedExpObjsList)
    
    def OnNewItem(self, evt):
        
        ExpObj = evt.GetValue()
        self.AddItem(ExpObj)
    
    def GetSelectedExpObjs(self):
        
        self.selectedExpObjList = []
        
        for each in self.allManipulationItems:
            if each.Selected == True:
                self.selectedExpObjList.append(each.ExpObj)
            
        return self.selectedExpObjList
    
    def GetSelectedItems(self):
        
        self.selectedItemList = []
        
        for each in self.allManipulationItems:
            if each.Selected == True:
                self.selectedItemList.append(each)
            
        return self.selectedItemList
    
    def MovePlots(self, ExpObjList, toAxes):
        
        axesThatNeedsUpdatedLegend = []
        
        for each in ExpObjList:
            if each.axes != toAxes:
                plotpanel = each.plotPanel
      
                each.line.remove()
                each.errLine[0][0].remove()
                each.errLine[0][1].remove()
                each.errLine[1][0].remove()
                
                if not each.axes in axesThatNeedsUpdatedLegend:
                    axesThatNeedsUpdatedLegend.append(each.axes)
                
                plotpanel.PlotExperimentObject(each, axes = toAxes, addToPlottedExps = False)
                
        for eachaxes in axesThatNeedsUpdatedLegend:
            plotpanel._insertLegend(axes = eachaxes)                
        
        if axesThatNeedsUpdatedLegend:
            plotpanel.canvas.draw()

                
    def RemoveSelectedItems(self):
        global expParams
        
        self.Freeze()
        
        axesThatNeedsUpdatedLegend = []
        
        for each in self.GetSelectedItems():
                     
            plotpanel = each.ExpObj.plotPanel
            
            each.ExpObj.line.remove()
            each.ExpObj.errLine[0][0].remove()
            each.ExpObj.errLine[0][1].remove()
            each.ExpObj.errLine[1][0].remove()
            
            i = plotpanel.plottedExps.index(each.ExpObj)
            plotpanel.plottedExps.pop(i)
            
            if not each.ExpObj.axes in axesThatNeedsUpdatedLegend:
                axesThatNeedsUpdatedLegend.append(each.ExpObj.axes)
            
            idx = self.allManipulationItems.index(each)
            self.allManipulationItems[idx].Destroy()
            self.allManipulationItems.pop(idx)
        
        for eachaxes in axesThatNeedsUpdatedLegend:
            plotpanel._insertLegend(axes = eachaxes)
            
        plotpanel.canvas.draw()
        
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Refresh()    
        
        self.Thaw()
        
    def DeselectAllExceptOne(self, item, line = None):
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        if line == None:
            
            for each in self.allManipulationItems:
                if each != item:
                    each.Selected = True
                    each.ToggleSelect()
        else:
            
            for each in self.allManipulationItems:
                if each.ExpObj.getLine() == line:
                    each.Selected = False
                    each.ToggleSelect()
                else:
                    each.Selected = True
                    each.ToggleSelect()
            
    def RemoveItem(self, ExpObj):
        
        self.Freeze()
        
        for i in range(0,len(self.allManipulationItems)):
            
            if self.allManipulationItems[i].ExpObj == ExpObj:
                self.allManipulationItems[i].Destroy()
                self.allManipulationItems.pop(i)                
                self.underpanel_sizer.Layout()
                self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
                self.underpanel.Refresh()
                break
            
        self.Thaw()
    
    def OnTest(self, evt):
        pass
        
    def AddItem(self, ExpObj):
        
        newItem = ManipFilePanel(self.underpanel, ExpObj)
        self.Freeze()
        self.underpanel_sizer.Add(newItem, 0, wx.GROW)
        self.underpanel_sizer.Layout()
        
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.Thaw()
        
        # Keeping track of all items in our list:
        self.allManipulationItems.append(newItem)
    
    def Update(self):
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Refresh()
        
    def ClearList(self, plottedExps):
        
        self.Freeze()    # Otherwise.. it looks strange
        
        #for each in self.underpanel.GetChildren():
        restOfItems = []
        for each in self.allManipulationItems:
            
            try:
                plottedExps.index(each.ExpObj)
                each.Destroy()
                self.underpanel_sizer.Layout()
            except ValueError:
                restOfItems.append(each)
        
        self.allManipulationItems = restOfItems
              
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        
        self.Thaw()
        
class MainFrame(wx.Frame):
    
    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title, name = 'MainFrame')
        
        splitter1 = wx.SplitterWindow(self, -1)
        splitter2 = wx.SplitterWindow(splitter1, -1)
        
        self.RAWWorkDir = os.getcwd()
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -2, -1])
        self.statusbar.SetStatusText('Mode: OFFLINE', 2)
        
        #self.InitToolBar()
        
        self.OnlineControl = OnlineController(self)
        
        # *************** Set minimum frame size ***************
        self.SetMinSize((800,600))
        
        # ************** The button panel *********************
        
        self.button_panel = wx.Panel(splitter1,-1)
        self.plot_panel = wx.Panel(splitter1,-1)
        
        # /* CREATE PLOT NOTEBOOK */
        self.plotNB = wx.Notebook(self.plot_panel)
        
        plotpage1 = PlotPanel(self.plotNB, -1, 'PlotPanel', 2) 
        plotpage2 = masking.MaskingPanel(self.plotNB, -1, 'RawPlotPanel', wxEmbedded = True)
        plotpage3 = PlotPanel(self.plotNB, wx.NewId(), 'BIFTPlotPanel', 2)
        #plotpage4 = overview.OverviewPanel(self.plotNB, -1, 'OverviewPanel')

        self.plotNB.AddPage(plotpage1, "1D Plots")
        self.plotNB.AddPage(plotpage3, "IFT Plot")
        self.plotNB.AddPage(plotpage2, "2D Image")
        #self.plotNB.AddPage(plotpage4, "Overview")
        
        plotNBsizer = wx.BoxSizer(wx.VERTICAL)
        plotNBsizer.Add(self.plotNB, 1, wx.EXPAND | wx.TOP, 5)

        self.plot_panel.SetSizer(plotNBsizer)

        nbsplitter = wx.SplitterWindow(self.button_panel, -1)
        
        # /* CREATE CONTROL NOTEBOOK */
        nb = wx.Notebook(nbsplitter)
        page1 = PlotPage(nb)
        #page2 = OptionsPage(nb, -1)
        page3 = AutoAnalysisGUI.AutoAnalysisPage(nb, expParams)
        page4 = ManipulationPage(nb)
        
        nb.AddPage(page1, "Files")
        nb.AddPage(page4, "Manipulation")
        #nb.AddPage(page2, "2D Options")
        nb.AddPage(page3, "IFT")

        self.infoPan = InfoPanel(nbsplitter)
                
        nbsplitter.SplitHorizontally(self.infoPan, nb, 150)
        nbsplitter.SetMinimumPaneSize(20)
        
        nbsizer = wx.BoxSizer(wx.VERTICAL)
        nbsizer.Add((5,5), 0, wx.EXPAND)
        nbsizer.Add(nbsplitter, 1, wx.EXPAND | wx.LEFT, 2)
        
        self.button_panel.SetSizer(nbsizer)
                
        splitter1.SplitVertically(self.button_panel, self.plot_panel, 270)
        splitter1.SetMinimumPaneSize(50)
        
        #Load workdir from rawcfg.dat:
        self.LoadCfg()
        
        self.MenuIDs = {'exit'              : wx.NewId(),
                        'advancedOptions'   : wx.NewId(),
                        'loadSettings'      : wx.NewId(),
                        'saveSettings'      : wx.NewId(),
                        'centering'         : wx.NewId(),
                        'goOnline'          : wx.NewId(),
                        'goOffline'         : wx.NewId(),
                        'plot1tynormal'       : wx.NewId(),
                        'plot1tyguinier'      : wx.NewId(),
                        'plot1tykratky'       : wx.NewId(),
                        'plot1typorod'        : wx.NewId(),
                        'plot1tysubtracted'   : wx.NewId(),
                        'plot2tynormal'       : wx.NewId(),
                        'plot2tyguinier'      : wx.NewId(),
                        'plot2tykratky'       : wx.NewId(),
                        'plot2tysubtracted'   : wx.NewId(),
                        'plot2typorod'        : wx.NewId(),
                        'plot1sclinlin'       : wx.NewId(),
                        'plot1scloglog'       : wx.NewId(),
                        'plot1scloglin'       : wx.NewId(),
                        'plot1sclinlog'       : wx.NewId(),
                        'plot2sclinlin'       : wx.NewId(),
                        'plot2scloglog'       : wx.NewId(),
                        'plot2scloglin'       : wx.NewId(),
                        'plot2sclinlog'       : wx.NewId(),
                        'help'              : wx.NewId(),
                        'about'             : wx.NewId(),
                        'guinierfit'        : wx.NewId()}
        
        self.CreateMenuBar()
        
        self.guinierframe = None
        
    def LoadCfg(self):
        
        try:
            file = 'rawcfg.dat'
            FileObj = open(file, 'r')
            savedInfo = cPickle.load(FileObj)
            FileObj.close()
            dirctrl = wx.FindWindowByName('DirCtrlPanel')
            dirctrl.path = savedInfo['workdir']
            self.ChangeParameter('ImageFormat', savedInfo['ImageFormat'])
            dirctrl.InitFileList()
        except:
            pass
        
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)

    def CreateMenuBar(self):
        
        MenuFile = wx.Menu()
        MenuFile.Append(self.MenuIDs['exit'], 'E&xit')
        
        self.Bind(wx.EVT_MENU, self.OnFileMenu, id = self.MenuIDs['exit'])
        
        MenuOptions = wx.Menu()
        MenuOptions.Append(self.MenuIDs['advancedOptions'], '&Advanced options...')
        MenuOptions.AppendSeparator()
        MenuOptions.Append(self.MenuIDs['loadSettings'], '&Load Settings')
        MenuOptions.Append(self.MenuIDs['saveSettings'], '&Save Settings')
        
        self.Bind(wx.EVT_MENU, self.OnOptionsMenu, id = self.MenuIDs['advancedOptions'])
        self.Bind(wx.EVT_MENU, self.OnLoadMenu, id = self.MenuIDs['loadSettings'])
        self.Bind(wx.EVT_MENU, self.OnSaveMenu, id = self.MenuIDs['saveSettings'])
       
         
        MenuOnline = wx.Menu()
        MenuOnline.Append(self.MenuIDs['goOnline'], '&Go Online')
        MenuOnline.Append(self.MenuIDs['goOffline'], 'Go &Offline')
        
        MenuFunction = wx.Menu()
        MenuFunction.Append(self.MenuIDs['guinierfit'], '&Guinier fit...')
        MenuFunction.Append(self.MenuIDs['centering'], '&Centering...')
        MenuFunction.AppendSeparator()
        MenuFunction.AppendSubMenu(MenuOnline, 'Online Mode')
        
        self.Bind(wx.EVT_MENU, self.OnFunctionMenu, id = self.MenuIDs['centering'])
        self.Bind(wx.EVT_MENU, self.OnFunctionMenu, id = self.MenuIDs['guinierfit'])
        self.Bind(wx.EVT_MENU, self.OnOnlineMenu, id = self.MenuIDs['goOnline'])
        self.Bind(wx.EVT_MENU, self.OnOnlineMenu, id = self.MenuIDs['goOffline'])
        
        MenuView = wx.Menu()
        self.MenuViewPlot1SubMenu = wx.Menu()
        self.MenuViewPlot1SubMenu.AppendRadioItem(self.MenuIDs['plot1tynormal'], 'Normal')
        self.MenuViewPlot1SubMenu.AppendRadioItem(self.MenuIDs['plot1tyguinier'], 'Guinier')
        self.MenuViewPlot1SubMenu.AppendRadioItem(self.MenuIDs['plot1tykratky'], 'Kratky')
        self.MenuViewPlot1SubMenu.AppendRadioItem(self.MenuIDs['plot1typorod'], 'Porod')
        
        self.MenuViewPlot2SubMenu = wx.Menu()
        self.MenuViewPlot2SubMenu.AppendRadioItem(self.MenuIDs['plot2tysubtracted'], 'Subtracted')
        self.MenuViewPlot2SubMenu.AppendRadioItem(self.MenuIDs['plot2tyguinier'], 'Guinier')
        self.MenuViewPlot2SubMenu.AppendRadioItem(self.MenuIDs['plot2tykratky'], 'Kratky')
        self.MenuViewPlot2SubMenu.AppendRadioItem(self.MenuIDs['plot2typorod'], 'Porod')
        
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1tynormal'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1tyguinier'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1tykratky'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1typorod'])
        
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2tynormal'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2tyguinier'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2tykratky'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2typorod'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2tysubtracted'])
        
        MenuViewPlot1ScaleSubMenu = wx.Menu()
        MenuViewPlot1ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot1sclinlin'], 'Lin-Lin')
        MenuViewPlot1ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot1scloglin'], 'Log-Lin')
        MenuViewPlot1ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot1scloglog'], 'Log-Log')
        MenuViewPlot1ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot1sclinlog'], 'Lin-Log')
        
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1sclinlin'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1scloglin'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1scloglog'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot1sclinlog'])
            
        MenuViewPlot2ScaleSubMenu = wx.Menu()
        MenuViewPlot2ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot2sclinlin'], 'Lin-Lin')
        MenuViewPlot2ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot2scloglin'], 'Log-Lin')
        MenuViewPlot2ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot2scloglog'], 'Log-Log')
        MenuViewPlot2ScaleSubMenu.AppendRadioItem(self.MenuIDs['plot2sclinlog'], 'Lin-Log')
        
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2sclinlin'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2scloglin'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2scloglog'])
        self.Bind(wx.EVT_MENU, self.OnViewMenu, id = self.MenuIDs['plot2sclinlog'])
        
        MenuView.AppendSubMenu(self.MenuViewPlot1SubMenu, '1D Plot (top) Type')
        MenuView.AppendSubMenu(self.MenuViewPlot2SubMenu, '1D Plot (bottom) Type')
        MenuView.AppendSeparator()
        MenuView.AppendSubMenu(MenuViewPlot1ScaleSubMenu, '1D Plot (top) Scale')
        MenuView.AppendSubMenu(MenuViewPlot2ScaleSubMenu, '1D Plot (bottom) Scale')
        
        
        MenuHelp = wx.Menu()
        MenuHelp.Append(self.MenuIDs['help'], '&Help!')
        MenuHelp.AppendSeparator()
        MenuHelp.Append(self.MenuIDs['about'], 'About')
        self.Bind(wx.EVT_MENU, self.OnAboutDlg, id = self.MenuIDs['about'])
        self.Bind(wx.EVT_MENU, self.OnHelp, id = self.MenuIDs['help'])
          
        menubar = wx.MenuBar()
        menubar.Append(MenuFile, '&File')
        menubar.Append(MenuOptions, '&Options')
        menubar.Append(MenuView, '&View')
        menubar.Append(MenuFunction, 'F&unction')
        menubar.Append(MenuHelp, '&Help')
        
        self.SetMenuBar(menubar)
    
    def OnCentering(self, evt):
        
        wx.MessageBox('Comming soon!', 'Info')
    
    def ShowOptionsDialog(self, focusIdx = None):
        
        if focusIdx != None:
            dialog = advancedOptionsGUI.OptionsDialog(self, expParams, focusIndex = focusIdx)
        else:
            dialog = advancedOptionsGUI.OptionsDialog(self, expParams)
        
        dialog.ShowModal()
    
    def OnLoadSettings(self, evt):   
        #global expParams
        
        file = self._CreateFileDialog(wx.OPEN)
        
        if file:
            
            try:
                FileObj = open(file, 'r')
            except:
                print >> sys.stderr, 'Error opening file!'
            
            try:
                newExpParams = cPickle.load(FileObj)
            except:
                print >> sys.stderr, 'That was not a valid config file!..'
                
            FileObj.close()
            
            self.InsertNewExpParams(newExpParams)
            #self._UpdateFromExtExpParams(newExpParams)
            self.UpdateMasks(newExpParams)
            
    def InsertIntoPlotQueue(self):
        
        plotQueue.put(selectedFiles)

    def InsertNewExpParams(self, newExpParams):    
        global expParams
        
        for each in newExpParams.iterkeys():
            expParams[each] = newExpParams[each]
    
    def UpdateMasks(self, newExpParams):
        global expParams
        
        if newExpParams.has_key('BeamStopMaskParams'):    # To make it backwards compatible with older cfg files..
            
            expParams['BeamStopMaskParams'] = newExpParams['BeamStopMaskParams']
            expParams['BeamStopMaskFilename'] = newExpParams['BeamStopMaskFilename']
            
            expParams['ReadOutNoiseMaskParams'] = newExpParams['ReadOutNoiseMaskParams']
            expParams['ReadOutNoiseMaskFilename'] = newExpParams['ReadOutNoiseMaskFilename']
            
            if expParams['BeamStopMaskFilename']:
                masking.LoadBeamStopMask(expParams['BeamStopMaskFilename']) # Load beamstop mask uses BeamStopMaskParams to generate mask and only tried to load the file if no params are found
            elif expParams['ReadOutNoiseMaskFilename']:      
                masking.LoadBeamStopMask(expParams['ReadOutNoiseMaskFilename'])
                
        else:
                expParams['BeamStopMask'] = None
                expParams['BeamStopMaskFilename'] = None
                expParams['BeamStopMaskParams'] = None
                expParams['ReadOutNoiseMask'] = None
                expParams['ReadOutNoiseMaskFilename'] = None
                expParams['ReadOutNoiseMaskParams'] = None
            
    def OnSaveSettings(self, evt):
        ############################ KILLS BEAMSTOP MASK !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        global expParams
        
        expParamsToSave = expParams
    
        file = self._CreateFileDialog(wx.SAVE)
        
        beamback = None
        readback = None
        
        if file:
            
            if expParamsToSave['BeamStopMask'] != None:
                beamback = expParamsToSave['BeamStopMask'].__copy__()
            if expParamsToSave['ReadOutNoiseMask'] != None:
                readback = expParamsToSave['ReadOutNoiseMask'].__copy__()
        
            expParamsToSave['BackgroundFile'] = None
            expParamsToSave['BeamStopMask'] = None
            expParamsToSave['ReadOutNoiseMask'] = None
            
            FileObj = open(file, 'w')
            cPickle.dump(expParamsToSave, FileObj)
            FileObj.close()
            
            expParamsToSave['BeamStopMask'] = beamback
            expParamsToSave['ReadOutNoiseMask'] = readback
        
    def getCheckedDataTreatments(self):            
        return getTreatmentParameters()
    
    def _CreateFileDialog(self, mode):
        
        file = None
        
        if mode == wx.OPEN:
            filters = 'Config files (*.cfg)|*.cfg|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters)
        if mode == wx.SAVE:
            filters = 'Config files (*.cfg)|*.cfg'
            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters)        
        
        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            
        # Destroy the dialog
        dialog.Destroy()
        
        return file
        
    def ReplaceExpParams(self, newExpParams):
        
        global expParams
        expParams = newExpParams
    
    def ChangeParameter(self, parameter, value):
        global expParams
        expParams[parameter] = value
        #self._UpdateFromExpParams()
    
    def GetParameter(self, parameter):
        global expParams
        return expParams[parameter]

    def GetAllParameters(self):
        global expParams
        return expParams
    
    def GetTreatments(self):
        return getTreatmentParameters()
    
    def ShowGuinierFitFrame(self, ExpObj):
        
        if not self.guinierframe:
            self.guinierframe = guinierGUI.GuinierTestFrame(self, 'Guinier Fit', ExpObj)
            self.guinierframe.SetIcon(self.GetIcon())
            self.guinierframe.Show(True)
        else:
            self.guinierframe.SetFocus()
            self.guinierframe.Raise()
            self.guinierframe.RequestUserAttention()
        
    def OnFunctionMenu(self, evt):
        
        id = evt.GetId()
        
        if id == self.MenuIDs['guinierfit']:
            
            manippage = wx.FindWindowByName('ManipulationPage')
            ExpObj = manippage.GetSelectedExpObjs()[0]
            
            self.ShowGuinierFitFrame(ExpObj)
            
            #dialog = guinierGUI.GuinierFitDialog(self, ExpObj)
            #dialog.ShowModal()  
            #dialog.Destroy()
            

    def OnViewMenu(self, evt):
        
        val = evt.GetId()
        
        key = [k for k, v in self.MenuIDs.iteritems() if v == val][0]
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        if key[0:7] == 'plot2sc':
            plotpanel.plotparams['axesscale2'] = key[-6:]
            plotpanel.UpdatePlotAxesScaling()
         
        elif key[0:7] == 'plot1sc':
            plotpanel.plotparams['axesscale1'] = key[-6:]
            plotpanel.UpdatePlotAxesScaling()
            
        elif key[0:7] == 'plot1ty':
            plotpanel.plotparams['plot1type'] = key[7:]
            plotpanel.UpdatePlotsAfterTypeChange(plotpanel.subplot1)
            
            if key[7:] == 'guinier':
                plotpanel.plotparams['axesscale1'] = 'loglin'
                plotpanel.UpdatePlotAxesScaling()
                self.MenuBar.FindItemById(self.MenuIDs['plot1scloglin']).Check(True)
            
            elif key[7:] == 'kratky' or key[7:] == 'porod':
                plotpanel.plotparams['axesscale1'] = 'linlin'
                plotpanel.UpdatePlotAxesScaling()
                self.MenuBar.FindItemById(self.MenuIDs['plot1sclinlin']).Check(True)
            
    
        elif key[0:7] == 'plot2ty':
            plotpanel.plotparams['plot2type'] = key[7:]
            plotpanel.UpdatePlotsAfterTypeChange(plotpanel.subplot2)
            
            if key[7:] == 'guinier':
                plotpanel.plotparams['axesscale2'] = 'loglin'
                plotpanel.UpdatePlotAxesScaling()
                self.MenuBar.FindItemById(self.MenuIDs['plot2scloglin']).Check(True)
                
            elif key[7:] == 'kratky' or key[7:] == 'porod':
                plotpanel.plotparams['axesscale2'] = 'linlin'
                plotpanel.UpdatePlotAxesScaling()
                self.MenuBar.FindItemById(self.MenuIDs['plot2sclinlin']).Check(True)

    
    def OnOptionsMenu(self, event):
        
        if event.GetId() == self.MenuIDs['advancedOptions']:
            self.ShowOptionsDialog()
    
    def OnFileMenu(self, event):
        
        if event.GetId() == self.MenuIDs['exit']:
            self.OnCloseWindow(0)
            
    def OnLoadMenu(self, event):
        self.OnLoadSettings(None)
    
    def OnAboutDlg(self, event):
        info = wx.AboutDialogInfo()
        info.Name = "BioXTAS RAW"
        info.Version = "0.99.7 Beta"
        info.Copyright = "Copyright(C) 2009 BioXTAS"
        info.Description = wordwrap(
            "BioXTAS RAW is a software package primarily for SAXS "
            "2D data reduction and 1D data analysis. It provides "
            "an easy GUI for handling multiple files fast, and "
            "a good alternative to commercial or protected "
            "software packages for finding the Pair Distance "
            "Distribution Function",
            400, wx.ClientDC(self))
        info.WebSite = ("http://www.bioxtas.org", "The Bioxtas Project")
        info.Developers = [u"Soren S. Nielsen"]
        info.License = wordwrap(
            "This program is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published by "
            "the Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.\n\n"

            "This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
            "GNU General Public License for more details.\n\n"

            "You should have received a copy of the GNU General Public License "
            "along with this program.  If not, see http://www.gnu.org/licenses/",
            400, wx.ClientDC(self))
        
        # Show the wx.AboutBox
        wx.AboutBox(info)
        
    
    def OnHelp(self, event):
#        frm = MyHtmlFrame(None, "BioXTAS RAW - Help -", )
#        icon = wx.Icon(name='raw.ico', type = wx.BITMAP_TYPE_ICO)
#        frm.SetIcon(icon)
#        frm.Show()
        #os.startfile(self.RAWWorkDir + '//RAW.chm')
        #os.path.join(self.RAWWorkDir, 'ressources', 'RAW.chm')
        os.execl('xchm')
        
    def OnSaveMenu(self, event):
        self.OnSaveSettings(None)
        
    def OnOnlineMenu(self, event):
        
        id = event.GetId()
        
        if id == self.MenuIDs['goOnline']:
            state = 'Online'
        else:
            state = 'Offline'
        
        self.OnlineControl.OnOnlineButton(state)
        
    def OnCloseWindow(self, event):
        self.Destroy()
        
        #Save current dir
        file = 'rawcfg.dat'
        
        try:
            FileObj = open(file, 'w')
        
            path = wx.FindWindowByName('DirCtrlPanel').path
            saveInfo = {'workdir' : path,
                        'ImageFormat' : self.GetParameter('ImageFormat')}
        
            cPickle.dump(saveInfo, FileObj)
            FileObj.close()
        except:
            pass
        
        
        os._exit(1)        ## Brutally kills running threads!
    
    def InitToolBar(self):
        toolbar = self.CreateToolBar()   
        toolbar.SetToolBitmapSize((48,48))
        toolbar.AddSimpleTool(wx.NewId(), wx.Image('ressources\\folder-find-48x48.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Help', 'Long help for New')
        #toolbar.SetBackgroundColour('LIGHT_GRAY')
        toolbar.Realize()
    
    def GetExperimentParameters(self):
        
        return expParams

class MyHtmlFrame(wx.Frame):

    def __init__(self, parent, title):

        wx.Frame.__init__(self, parent, -1, title)

        html = wx.html.HtmlWindow(self, style=wx.html.HW_SCROLLBAR_AUTO)

        html.SetStandardFonts()

        html.SetPage("test") 
        
#----------           
class MyApp(wx.App):
    
    def OnInit(self):
     
        # main frame and panel ---------
#        self.frame = MainFrame('BioXtas RAW 0.3b', MAINFRAME_ID)
#  
#        self.SetTopWindow(self.frame)
#  #      self.TopWindow.CenterOnScreen()
#        self.frame.SetSize((1024,768))
#        self.frame.CenterOnScreen()
#        self.frame.Show(1)
        
        MySplash = MySplashScreen()
        MySplash.Show()
        
        return True
    
    
class MySplashScreen(wx.SplashScreen):
    """
        Create a splash screen widget.
    """
    
    def __init__(self, parent = None):
        # This is a recipe to a the screen.
        # Modify the following variables as necessary.
        
        aBitmap = wx.Image(name = os.path.join("ressources","logo_atom.gif")).ConvertToBitmap()
        splashStyle = wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_TIMEOUT
        splashDuration = 2000 # milliseconds
        
        # Call the constructor with the above arguments in exactly the
        # following order.
        wx.SplashScreen.__init__(self, aBitmap, splashStyle,
                                 splashDuration, parent)
        
        self.Bind(wx.EVT_CLOSE, self.OnExit)

        wx.Yield()

    def OnExit(self, evt):
        self.Hide()
    
        frame = MainFrame('BioXTAS RAW 0.99.7b', -1)
        icon = wx.Icon(name= os.path.join("ressources","raw.ico"), type = wx.BITMAP_TYPE_ICO)
        frame.SetIcon(icon)
        app.SetTopWindow(frame)
  #      self.TopWindow.CenterOnScreen()
        frame.SetSize((1024,768))
        frame.CenterOnScreen()
        frame.Show(True)

        # The program will freeze without this line.
        evt.Skip()  # Make sure the default handler runs too...
       
if __name__ == '__main__':
    app = MyApp(0)   #MyApp(redirect = True)
    app.MainLoop()
    
