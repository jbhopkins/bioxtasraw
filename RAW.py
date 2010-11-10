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
import sys, os, cPickle, threading, re, math     #, gc, time
import matplotlib, time, subprocess
matplotlib.rc('image', origin='lower')           # This turns the image upside down!!
                                                 #  but x and y will start from zero in the lower left corner 

from pylab import setp

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg #,Toolbar 
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import cursors
from matplotlib.figure import Figure

from matplotlib.font_manager import FontProperties
import matplotlib.cbook as cbook

from numpy import power, zeros, shape, transpose, array, where, isnan, isinf

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
             'CountNormalize'    : 1.0,
             
             'AutoBIFT'          : False,
             'AutoAvg'           : False,
             'AutoAvgRemovePlots': False,
             
             'AutoAvgRegExp'     : '',
             'AutoAvgNameRegExp' : '',
             'AutoAvgNoOfFrames' : 1,
             'AutoBgSubRegExp'   : '',
             
             'UseOnlineFilter' : False,
             'OnlineFilterExt' : '',
             
             
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
             #'BgPatternType'       : 'contain',
             #'BgPatternValue'      : '',
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
             'ProcessedFilePath'    : None,
             'AveragedFilePath'     : None,
             'SubtractedFilePath'   : None,
             'AutoSaveOnImageFiles' : False,
             'AutoSaveOnAvgFiles'   : False,    
             'AutoSaveOnSub'        : False,
             
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

PlotReadyEvent = wx.NewEventType()
EVT_PLOT_READY = wx.PyEventBinder(PlotReadyEvent, 1)


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
        self.savepath = None
        self.currentAutoAvgName = None
        self.avgList = []

    def run(self):
        
        while True:
            
            selectedFiles = plotQueue.get()    # Blocks until a new item is available in the queue
            
            if len(selectedFiles) == 2:
                if selectedFiles[1] == True :
                    selectedFiles = selectedFiles[0]
                    FromOnlineMode = True
                else:
                    FromOnlineMode = False
            else:
                FromOnlineMode = False

            print selectedFiles
 
            if expParams['AutoSaveOnImageFiles'] == True and FromOnlineMode:
                self.savepath = expParams['ProcessedFilePath']
            else:
                self.savepath = None
 
            dirCtrlPanel = wx.FindWindowByName('DirCtrlPanel')
            plotpanel = wx.FindWindowByName('PlotPanel')
            biftplotpanel = wx.FindWindowByName('BIFTPlotPanel')
            mainframe_window = wx.FindWindowByName('MainFrame')
        
            #wx.PostEvent(mainframe_window.GetEventHandler(), PlotReadyEvent)
          
            for eachSelectedFile in selectedFiles:
                
#               cProfile.runctx("ExpObj, FullImage = fileIO.loadFile(eachSelectedFile, expParams)", globals(), locals())     
                try:      
                    ExpObj, FullImage = fileIO.loadFile(eachSelectedFile, expParams)
                except (IndexError, ValueError, RuntimeError):
                    #wx.CallAfter(wx.MessageBox(eachSelectedFile + ' does not match the current image format.\n\nSee advanced options to change the current image format', 'Wrong image format')
                    #WARNING - ValueERROR happen on flicam file when no counter file is found!
                    print 'Wrong image format (plotWorkerThread)'
                    ExpObj = None
                    FullImage = None
                    
                                                
                checkedTreatments = getTreatmentParameters()
                
                if ExpObj != None:
                    if ExpObj.i != []:
                    
                        cartToPol.applyDataManipulations(ExpObj, expParams, checkedTreatments)    # Only does something for images
                                             
                        if expParams['AutoBgSubtract'] and FromOnlineMode:
                            self._setBackground = self.CheckIfFilenameIsBackground(eachSelectedFile)
                        
                        AvgExpObj = None  
                        if expParams['AutoAvg'] and FromOnlineMode:
                            AvgExpObj = self.processAutoAveraging(ExpObj, eachSelectedFile)
                            
                            if self._setBackground == True and AvgExpObj != None:
                                expParams['BackgroundFile'] = AvgExpObj
                                wx.CallAfter(dirCtrlPanel.SetBackgroundFile, AvgExpObj.param['filename'])
                                
                            # If filename doesnt match autoavg pattern treat it as a normal file and set background if needed:
                            elif self._setBackground == True and len(self.avgList) == 0:
                                expParams['BackgroundFile'] = ExpObj
                                wx.CallAfter(dirCtrlPanel.SetBackgroundFile, eachSelectedFile)
                        else:
                            
                            if self._setBackground == True:
                                expParams['BackgroundFile'] = ExpObj
                                wx.CallAfter(dirCtrlPanel.SetBackgroundFile, eachSelectedFile)
                                                              
                        if self.savepath:
                            self.saveMeasurement(ExpObj, self.savepath)
       
                        if ExpObj.type == 'bift':
                            biftplotpanel.PlotLoadedBift(ExpObj)
                        else:    
                            wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, ExpObj, axes = self._parent.subplot1)   
                            wx.CallAfter(plotpanel._setLabels, ExpObj, axes = self._parent.subplot1)
            
                        # For some unknown reason showing the image can make the program hang!
                        if FullImage and len(selectedFiles) == 1:
                            rawplot = wx.FindWindowByName('RawPlotPanel')
                            wx.CallAfter(rawplot.showImage, FullImage, ExpObj)
                        
                        if ExpObj.type != 'bift':
                            manipulationPage = wx.FindWindowByName('ManipulationPage')
                            
                            wx.CallAfter(manipulationPage.AddItem, ExpObj)
                            
                            #evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObj)
                            #wx.PostEvent(manipulationPage, evt)
                            
                        
                        #If autoaverage is on and an averaged data has been created:
                        if expParams['AutoAvg'] and AvgExpObj != None and FromOnlineMode:    
                            wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, AvgExpObj, axes = self._parent.subplot1)   
                            wx.CallAfter(plotpanel._setLabels, AvgExpObj, axes = self._parent.subplot1)
                            
                            manipulationPage = wx.FindWindowByName('ManipulationPage')
                            #evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, AvgExpObj)
                            
                            #wx.PostEvent(manipulationPage, evt)
                            
                            wx.CallAfter(manipulationPage.AddItem, AvgExpObj)
                            
                            
                            if expParams['AutoBgSubtract'] and FromOnlineMode and self._setBackground == False:
                                self.subtractAndPlot(AvgExpObj)
                        
                        # If filename does not match autoavg pattern then treat it like a normal file and subtract background if needed
                        elif expParams['AutoAvg'] and len(self.avgList) == 0 and self._setBackground == False and expParams['AutoBgSubtract'] and FromOnlineMode:
                            autoBgSubQueue.put(([eachSelectedFile], False))
                        
                        elif expParams['AutoBgSubtract'] and not expParams['AutoAvg'] and self._setBackground == False and FromOnlineMode:
                            autoBgSubQueue.put(([eachSelectedFile], False))
  
        
                        wx.CallAfter(mainframe_window.SetStatusText,'Loading: ' + eachSelectedFile + '...Done!')    
                    
                    else:
                        wx.CallAfter(wx.MessageBox, 'Filename: ' + eachSelectedFile + '\nDoes not contain any recognisable data.\n\nIf you are trying to load an image,\nset the correct image format in Options.\n** Also check that your mask fits the image **', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                else:
                    wx.CallAfter(wx.MessageBox, 'Filename: ' + eachSelectedFile + '\nDoes not contain any recognisable data.\n\nIf you are trying to load an image,\nset the correct image format in Options.\n\n** Also check that your mask fits the image **', 'Load Failed!', wx.OK | wx.ICON_ERROR)
        
            wx.CallAfter(plotpanel._insertLegend, axes = self._parent.subplot1)
            
            plotQueue.task_done()
            
    def subtractAndPlot(self, ExpObjSample):
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        ExpObjBackgrnd = expParams['BackgroundFile']
        
        if not ExpObjBackgrnd:
            return
        
        if len(ExpObjSample.i) == len(ExpObjBackgrnd.i):
                    
            wx.CallAfter(plotpanel.SubtractAndPlot, [ExpObjSample])
        
        else:
            noPathSampleFilename = os.path.split(eachFile)[1]
            noPathBackgrndFilename = ExpObjBackgrnd.param['filename']
                    
            wx.CallAfter(wx.MessageBox, noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
    
    def cleanAvgList(self):
        self.avgList = []
            
    def CheckIfFilenameIsBackground(self, filepath):
        
        filename = os.path.split(filepath)[1]
        
        regexp = expParams['AutoBgSubRegExp']
        
        try:
            pattern = re.compile(regexp)
        except:
            return False
    
        m = pattern.match(filename)
    
        if m:
            return True
        else:
            return False
            
            
    def processAutoAveraging(self,ExpObj, eachSelectedFile):
        
        AvgExpObj = None
        
        if self.FilenameMatchesCurrentAvgName(eachSelectedFile):    
            self.avgList.append(ExpObj)
        else:
            self.avgList = []
            name, frame = self.ExtractFilenameAndFrameNumber(eachSelectedFile,  expParams['AutoAvgRegExp'], expParams['AutoAvgNameRegExp'])
                                
            if name and frame:
                self.currentAutoAvgName = name
                self.avgList.append(ExpObj)
            else:
                self.currentAutoAvgName = None
                                  
        print 'FilesInList : ', len(self.avgList)
        
        if len(self.avgList) == expParams['AutoAvgNoOfFrames']:
            AvgExpObj = self.averageFilesInAvgList()
            self.avgList = []  
            
            if expParams['AutoSaveOnAvgFiles']:
                self.saveMeasurement(AvgExpObj, expParams['AveragedFilePath'])
                
        return AvgExpObj
            
    def averageFilesInAvgList(self):
            
        AvgExpObj = cartToPol.averageMeasurements(self.avgList, expParams)
        
        if AvgExpObj == None:
            return None
        
#        path_file = os.path.split(AvgExpObj.param['filename'])          
#        AvgExpObj.param['filename'] = path_file[0] + 'AVG_' + path_file[1]
        
        return AvgExpObj
    
    def saveMeasurement(self, ExpObj, savepath): 
        filename = os.path.split(ExpObj.param['filename'])[1]
        fullsavePath = os.path.join(savepath, filename)
        ExpObj.param['filename'] = fullsavePath
        fileIO.saveMeasurement(ExpObj)
        print fullsavePath +'...SAVED'
        self.savepath = None
        wx.CallAfter(dirCtrlPanel.FilterFileListAndUpdateListBox)
        
    def ExtractFilenameAndFrameNumber(self, filepath, frameregexp, nameregexp):
        
        filename = os.path.split(filepath)[1]
    
        frame = False
        name = False
    
        # EXTRACT FRAME NUMBER
        try:
            pattern = re.compile(frameregexp)
            m = pattern.findall(filename)
        
            if len(m) > 0:
                found = ''
                for each in m:
                    found = found + each
                    print m
        
                non_decimal = re.compile(r'[^\d.]+')
                frame = non_decimal.sub('', found)
    
                if frame == '':
                    frame = False
        except:
            pass

        # EXTRACT FILENAME
        try:
            namepattern = re.compile(nameregexp) 
            n = namepattern.findall(filename)
   
            if len(n) > 0:
                found = ''
                for each in n:
                    found = found + each
                    print n
        
                if found != '':
                    name = found
                else:
                    name = False
        except:
            pass
        
        return name, frame
     
    def FilenameMatchesCurrentAvgName(self, filepath):
        
        frameNumberRegExp = expParams['AutoAvgRegExp']
        nameRegExp = expParams['AutoAvgNameRegExp']
        
        name, frame = self.ExtractFilenameAndFrameNumber(filepath, frameNumberRegExp, nameRegExp)
        
        if name and frame:
            if self.currentAutoAvgName == name:
                return True
            else:
                self.currentAutoAvgName = name
                return False 
        else:
            return False
    
        
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
    
            ExpObjBackgrnd, FullImage = fileIO.loadFile(bgfilename, expParams)
        
            checkedTreatments = getTreatmentParameters()
            cartToPol.applyDataManipulations(ExpObjBackgrnd, expParams, checkedTreatments)
        
            for eachSelectedFile in selectedFiles:
            
                wx.CallAfter(mainframe.SetStatusText, 'Loading file..')
            
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
                  
                    #Update figure:
                    wx.CallAfter(plotpanel.canvas.draw)
                
                    manipulationPage = wx.FindWindowByName('ManipulationPage')
                    #evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObjSample)
                    #wx.PostEvent(manipulationPage, evt)
                    wx.CallAfter(manipulationPage.AddItem, ExpObjSample)
        
                    wx.CallAfter(mainframe.SetStatusText, 'Loading: ' + eachSelectedFile + '...Done!')    
            
                else:
                    wx.MessageBox(noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
            
            bgSubPlotQueue.task_done()
      
class AutoBgSubWorkerThread(threading.Thread):
    
    def __init__(self, parent):
        
        threading.Thread.__init__(self)
        
        self._parent = parent
        self._listOfFilePaths = None
        self._plotOriginal = True
        
        global expParams
        self.expParams = expParams
        
    def run(self):
        
        while True:
        
            self._listOfFilePaths = autoBgSubQueue.get()
            
            #Nasty Hack:
            if len(self._listOfFilePaths) == 2:
                if self._listOfFilePaths[1] == False:
                    self._plotOriginal = False
                    self._listOfFilePaths = self._listOfFilePaths[0]
                elif self._listOfFilePaths[1] == True:
                    self._plotOriginal = True
                    self._listOfFilePaths = self._listOfFilePaths[0]
            else:
                self._plotOriginal = False
        
            manipulationPage = wx.FindWindowByName('ManipulationPage')
            plotpanel = wx.FindWindowByName('PlotPanel')
            ExpObjBackgrnd = expParams['BackgroundFile']
            mainframe = wx.FindWindowByName('MainFrame')
         
            if ExpObjBackgrnd != None:
            
                for eachFile in self._listOfFilePaths:
                    
                    
                    print eachFile
                    ExpObjSample, FullImage = fileIO.loadFile(eachFile, expParams)
                    
                    checkedTreatments = getTreatmentParameters()
                    cartToPol.applyDataManipulations(ExpObjSample, expParams, checkedTreatments)
            
                    ExpObjSample.param['filename'] = eachFile                    
                        
                    if self._plotOriginal:
                        if len(ExpObjSample.i > 1):
                            
                            ExpObjSamp = ExpObjSample.copy()
                            
                            wx.CallAfter(plotpanel._PlotOnSelectedAxesScale, ExpObjSamp, plotpanel.subplot1)
                            wx.CallAfter(plotpanel._insertLegend, eachFile, axes = plotpanel.subplot1)
                        
                            #evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObjSamp)
                            #wx.PostEvent(manipulationPage, evt)
                            wx.CallAfter(manipulationPage.AddItem, ExpObjSamp)
                
                    #Check if they are of equal length before subtracting
                    if len(ExpObjSample.i) == len(ExpObjBackgrnd.i):
                    
                        wx.CallAfter(plotpanel.SubtractAndPlot, [ExpObjSample])
        
                        #Update status bar
                        wx.CallAfter(mainframe.SetStatusText, 'Loading: ' + eachFile + '...Done!')    
                    
                        if expParams['AutoBIFT'] == True:
                            print >> sys.stderr, 'AUTOBIFT THROUGH AutoBgSubThread NOT IMPLEMENTED'
                            #biftThread = AutoAnalysisGUI.BiftCalculationThread(self, ExpObjSample)
                            #biftThread.start()
            
                    else:
                        noPathSampleFilename = os.path.split(eachFile)[1]
                        noPathBackgrndFilename = ExpObjBackgrnd.param['filename']
                    
                        wx.CallAfter(wx.MessageBox, noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)

            else:
                wx.CallAfter(wx.MessageBox, 'No background loaded!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
       
            autoBgSubQueue.task_done()
   
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
        
        self._MTB_ERRBARS = wx.NewId()
        self._MTB_LEGEND = wx.NewId()
        self._MTB_SHOWBOTH = wx.NewId()
        self._MTB_SHOWTOP = wx.NewId()
        
        self._MTB_CLR1 = wx.NewId()
        self._MTB_CLR2 = wx.NewId()
        
        self.parent.canvas.draw()
        self._MTB_SHOWBOTTOM = wx.NewId()
        
        NavigationToolbar2Wx.__init__(self, canvas)
        
        mainframe = wx.FindWindowByName('MainFrame')
        self.workdir = mainframe.RAWWorkDir

        clear1IconFilename = os.path.join(self.workdir, "ressources" ,"clear1white.png")
        clear2IconFilename = os.path.join(self.workdir, "ressources" ,"clear2white.png")
        errbarsIconFilename = os.path.join(self.workdir, "ressources" ,"errbars.png")
        legendIconFilename = os.path.join(self.workdir, "ressources", "legend.png")
        showbothIconFilename = os.path.join(self.workdir, "ressources", "showboth.png")
        showtopIconFilename = os.path.join(self.workdir, "ressources", "showtop.png")
        showbottomIconFilename = os.path.join(self.workdir, "ressources", "showbottom.png")
        
        clear1_icon = wx.Bitmap(clear1IconFilename, wx.BITMAP_TYPE_PNG)
        clear2_icon = wx.Bitmap(clear2IconFilename, wx.BITMAP_TYPE_PNG)
        errbars_icon = wx.Bitmap(errbarsIconFilename, wx.BITMAP_TYPE_PNG)
        legend_icon = wx.Bitmap(legendIconFilename, wx.BITMAP_TYPE_PNG)
        showboth_icon = wx.Bitmap(showbothIconFilename, wx.BITMAP_TYPE_PNG)
        showtop_icon = wx.Bitmap(showtopIconFilename, wx.BITMAP_TYPE_PNG)
        showbottom_icon = wx.Bitmap(showbottomIconFilename, wx.BITMAP_TYPE_PNG)
        
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
    

#    def zoom(self, *args):
        #self.ToggleTool(self._NTB2_PAN, False)
        
#        if self.GetToolEnabled(self._NTB2_PAN):
#            self.set_cursor(4)
#        else:
        
#        NavigationToolbar2Wx.zoom(self, *args)
        
        
#        
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
        self.parent.ClearSubplot(self.parent.subplot2)
    
    def set_cursor(self, cursor):
        ''' overriding this method from parent '''
        
        cursord = {
                   cursors.MOVE : wx.Cursor(os.path.join(self.workdir, "ressources" ,"SmoothMove.cur"), wx.BITMAP_TYPE_CUR),
                   cursors.HAND : wx.Cursor(os.path.join(self.workdir, "ressources" ,"SmoothMove.cur"), wx.BITMAP_TYPE_CUR),
                   cursors.POINTER : wx.StockCursor(wx.CURSOR_ARROW),
                   cursors.SELECT_REGION : wx.Cursor(os.path.join(self.workdir, "ressources" ,"zoom-in.cur"), wx.BITMAP_TYPE_CUR),            #wx.CURSOR_CROSS,
                   }
        
        cursor = cursord[cursor]
        self.parent.canvas.SetCursor( cursor )
       
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
        
        
class myPlotScaleMenu(wx.Menu):
    
    def __init__(self, parent, plotnumber, **kwargs):
        
        wx.Menu.__init__(self)
        
        self._plot_number = plotnumber
        
        self.parent = parent
        self._itemslist = []
        
        self.Bind(wx.EVT_MENU, self.onSelection)
        
        self._addItems()
        self._updateSelection()
        
        #EVT_CUSTOM_MENU_SELECTED = wx.PyEventBinder(wx.wxEVT_COMMAND_MENU_SELECTED, 2) 
        #self.Bind(EVT_CUSTOM_MENU_SELECTED, self.onSelection)
        
    def _updateSelection(self):
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        if plotpanel.plotparams['plot' + self._plot_number + 'type'] == 'normal' or plotpanel.plotparams['plot' + self._plot_number + 'type'] == 'subtracted':
        
            if plotpanel.plotparams['axesscale' + self._plot_number + ''] == 'loglog':
                self._itemslist[2].Check(True)
            elif plotpanel.plotparams['axesscale' + self._plot_number + ''] == 'linlog':
                self._itemslist[3].Check(True)
            elif plotpanel.plotparams['axesscale' + self._plot_number + ''] == 'loglin':
                self._itemslist[1].Check(True)
            elif plotpanel.plotparams['axesscale' + self._plot_number + ''] == 'linlin':
                self._itemslist[0].Check(True)
        
        else:
            if plotpanel.plotparams['plot' + self._plot_number + 'type'] == 'guinier':
                self._itemslist[4].Check(True)
            elif plotpanel.plotparams['plot' + self._plot_number + 'type'] == 'kratky':
                self._itemslist[5].Check(True)
            elif plotpanel.plotparams['plot' + self._plot_number + 'type'] == 'porod':
                self._itemslist[6].Check(True)
        
    def _addItems(self):
        
        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.MenuIDs
        
        it1 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'sclinlin'], 'Lin-Lin')
        it2 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'scloglin'], 'Log-Lin')
        it3 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'scloglog'], 'Log-Log')
        it4 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'sclinlog'], 'Lin-Log')
        #it9 = self.AppendSeparator()
        it10 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'tyguinier'], 'Guinier')
        it11 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'tykratky'], 'Kratky')
        it12 = self.AppendRadioItem(MenuIDs['plot' + self._plot_number + 'typorod'], 'Porod')
        
    def onSelection(self, event):        
        print event.GetId()
        
        for eachItem in self._itemslist:
            if event.GetId() == eachItem.GetId():
                eachItem.Check(True)
    
        self.parent._OnPopupMenuChoice(event)
        
    
    def AppendRadioItem(self, id, label):
        
        item = super(myPlotScaleMenu, self).AppendRadioItem(id, label)
        self._itemslist.append(item)
        
        return item
    
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
                           'plot1state' : 'linlin',
                           'errorbars_on': False}
        
        self.legendPicked = False
        self.pickLocation = (0,0)
        self.legendPosition = (0.5,0.5)
        
        self.canvas.callbacks.connect('pick_event', self.OnPick)
        self.canvas.callbacks.connect('key_press_event', self.OnKeyPress)
        self.canvas.callbacks.connect('button_release_event', self.OnMouseButton)
        
        self.Bind(EVT_PLOT_READY, self.OnReadyPlot)
        
        
        self.canvas.callbacks.connect('motion_notify_event', self.onMotionEvent)
                        
        subplotLabels = { 'subtracted'  : ('Subtracted', 'q', 'I(q)'),
                          'PDDF'        : ('PDDF', 'r', 'p(r)'),
                          'kratky'      : ('Kratky', 'q', 'I(q)q^2'),
                          'guinier'     : ('Guinier', 'q^2', 'ln(I(q)')}
        
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
        
    def OnReadyPlot(self, evt):
        
        print 'PLOT IS READY!'
        
    def onMotionEvent(self, event):
        
        if event.inaxes:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('x = ' +  str(x) + ', y = ' + str(y), 1) 
            
    def OnMouseButton(self, evt):

        x_size,y_size = self.canvas.get_width_height()
        half_y = y_size / 2
        
        selected_plot = 1
        if evt.y <= half_y:
            selected_plot = 2
            
        if evt.button == 3:
            if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                self.ShowPopupMenu(selected_plot)
            
    def ShowPopupMenu(self, selected_plot):
        
        mainframe = wx.FindWindowByName('MainFrame')
    
        MenuIDs = mainframe.MenuIDs
       
        menu = wx.Menu()
        
        plot1SubMenu = myPlotScaleMenu(self, '1')
        
        plot2SubMenu = myPlotScaleMenu(self, '2')
            
        if selected_plot == 1:
            menu.AppendSubMenu(plot1SubMenu, 'Axes')
        else:
            menu.AppendSubMenu(plot2SubMenu, 'Axes')
          
        self.Bind(wx.EVT_MENU, self._OnPopupMenuChoice) 
        
        self.PopupMenu(menu)
        
    def _OnPopupMenuChoice(self, evt):
        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.MenuIDs
        id = evt.GetId()
        
        for key in MenuIDs.iterkeys():
            if MenuIDs[key] == id:
                
                print key
                
                if key[4] == '1':
                    
                    if key[5:7] == 'ty':
                        self.plotparams['plot1type'] = key[7:]
                        self.UpdatePlotsAfterTypeChange(self.subplot1)
                        
                        if key[7:] == 'guinier':
                            self.plotparams['axesscale1'] = 'loglin'
                        else:
                            self.plotparams['axesscale1'] = 'linlin'
                        self.UpdatePlotAxesScaling()
                            
                    else:
                        self.plotparams['axesscale1'] = key[7:]
                        self.plotparams['plot1type'] = 'normal'
                        self.UpdatePlotsAfterTypeChange(self.subplot1)
                        self.UpdatePlotAxesScaling()
                else:
                    if key[5:7] == 'ty':
                        self.plotparams['plot2type'] = key[7:]
                        self.UpdatePlotsAfterTypeChange(self.subplot2)
                        
                        if key[7:] == 'guinier':
                            self.plotparams['axesscale2'] = 'loglin'
                        else:
                            self.plotparams['axesscale2'] = 'linlin'
                        self.UpdatePlotAxesScaling()
     
                    else:
                        self.plotparams['axesscale2'] = key[7:]
                        self.plotparams['plot2type'] = 'subtracted'
                        self.UpdatePlotsAfterTypeChange(self.subplot2)
                        self.UpdatePlotAxesScaling()
                        
        mainframe.SetViewMenuScale(id)
  
    
    def InitLabels(self):
        
#        if self.GetName() == 'BIFTPlotPanel':
#            self._setLabels(None, title = 'Indirect Fourier Transform', xlabel = 'r [A]', ylabel = 'p(r)', axes = self.subplot1)
#            self._setLabels(None, title = 'Fit', xlabel = 'q [1/A]', ylabel = 'I(q)', axes = self.subplot2)
#        elif self.GetName() == 'PlotPanel':
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
        
        mouseevent = evt.mouseevent
        
        #Disable selecting using right mouse button:
        if mouseevent.button == 3:
            return
        
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
        
    def UpdatePlotAxesScaling(self):
        
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
        self._insertLegend(axes = self.subplot2)
        
        self.canvas.draw()       
    
    def updatePlotAfterScaling(self, ExpObj):
        
        a = ExpObj.axes
        
        if a == self.subplot1:
            type = self.plotparams.get('plot1type')
        elif a == self.subplot2:  
            type = self.plotparams.get('plot2type')
              
        if type == 'normal' or type == 'subtracted':
            #line, ec, el = a.errorbar(ExpObj.q, ExpObj.i, ExpObj.errorbars, picker = 3)
            ExpObj.line.set_data(ExpObj.q, ExpObj.i)
        elif type == 'kratky':
            #line, ec, el = a.errorbar(ExpObj.q, ExpObj.i*power(ExpObj.q,2), ExpObj.errorbars, picker = 3)
            ExpObj.line.set_data(ExpObj.q, ExpObj.i*power(ExpObj.q,2))
        elif type == 'guinier':
            #line, ec, el = a.errorbar(power(ExpObj.q,2), ExpObj.i, ExpObj.errorbars, picker = 3)
            ExpObj.line.set_data(power(ExpObj.q,2), ExpObj.i)
        elif type == 'porod':
            #line, ec, el = a.errorbar(ExpObj.q, power(ExpObj.q,4)*ExpObj.i, ExpObj.errorbars, picker = 3)
            ExpObj.line.set_data(ExpObj.q, power(ExpObj.q,4)*ExpObj.i)
        
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
        #evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObj)
        #wx.PostEvent(manipulationPage, evt)
        wx.CallAfter(manipulationPage.AddItem, ExpObj)
        
        self.subplot2.cla()
        
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
                
                    dialog.Update(3)
            
                    #Update figure:
                    self.canvas.draw()
        
                    manipulationPage = wx.FindWindowByName('ManipulationPage')
                    manipulationPage.AddItem(ExpObjSubbed)
        
                    dialog.Update(7)
                    
                    #Arrhh.. this should not be here.. SubtractAndPlot should be cleaned up
                    if expParams['AutoSaveOnSub']:
                        savepath = expParams['SubtractedFilePath']
                        filename = os.path.split(ExpObjSubbed.param['filename'])[1]
                        fullsavePath = os.path.join(savepath, filename)
                        ExpObjSubbed.param['filename'] = fullsavePath
                        fileIO.saveMeasurement(ExpObjSubbed, NoChange = True)
                        print fullsavePath +'...SAVED'
            
                else:
                    wx.MessageBox(noPathSampleFilename + ' and ' + noPathBackgrndFilename + '\ndoes not have the same q-range!', 'Subtraction Failed!', wx.OK | wx.ICON_ERROR)
                    dialog.Update(7)
        
            #self._setLabels(ExpObjSample)           
            self._insertLegend(axes = self.subplot2)
        
    def ShowErrorbars(self):
        
        for each in self.plottedExps:
            setp(each.errLine[0], visible=True)
            setp(each.errLine[1], visible=True)
        
#        if self.fitplot != None and self.name == 'BIFTPlotPanel':
#            setp(self.fitplot.errLine[0], visible=True)
#            setp(self.fitplot.errLine[1], visible=True)
            
        self.canvas.draw()

    def HideErrorbars(self):
        
        for each in self.plottedExps:
            setp(each.errLine[0], visible=False)
            setp(each.errLine[1], visible=False)
        
        
#        if self.fitplot != None and self.name == 'BIFTPlotPanel':
#            setp(self.fitplot.errLine[0], visible=False)
#            setp(self.fitplot.errLine[1], visible=False)
            
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
    
    
    def SwitchToNoteBookPage(self):
        mainframe = wx.FindWindowByName('MainFrame')
        mainframe.plotNB.SetSelection(0)
    
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
        
        self.SwitchToNoteBookPage()
        
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
    
    def _setLabels(self, ExpObj = None, title = None, xlabel = None, ylabel = None, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        # Set TITLE 
        if title == None:
            
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
    
    def ontest(self):
        print 'hello!'
           
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
        
#    def PlotLoadedBift(self, BiftObj):
#        
#        i = BiftObj.allData['orig_i']
#        q = BiftObj.allData['orig_q']
#        err = BiftObj.allData['orig_err']
#        
#        ExpObj = cartToPol.RadFileMeasurement(array(i), array(q), array(err), BiftObj.param)
#        
#        self.PlotBIFTExperimentObject(BiftObj)
#        biftPage = wx.FindWindowByName('AutoAnalysisPage')
#        biftPage.addBiftObjToList(ExpObj, BiftObj)
    
 
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
        self.UpdatePlotAxesScaling()
        
        self._setLabels(axes = subplot)
        self.canvas.draw()
    
        
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
   
    def OnClearAll(self, event, clearManipItems = None):
        
        global expParams
        
        if self.name == 'PlotPanel':
            dial = wx.MessageDialog(self, 'Are you sure you want to clear everything?', 'Question', 
                                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            answer = dial.ShowModal()
            dial.Destroy()
        
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
            
            #also sets correct axes scale:
            self.ClearSubplot(self.subplot1)
            self.ClearSubplot(self.subplot2)
            
            #Reset stacks in toolbar mem
            self.toolbar._views = cbook.Stack()
            self.toolbar._positions = cbook.Stack()
        else:
            self.subplot1.cla()

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


class IftPanel(PlotPanel):
    
    def __init__(self, parent, panel_id, name, noOfPlots = 1):
        
        PlotPanel.__init__(self, parent, panel_id, name, noOfPlots = noOfPlots)
 
 
    def InitLabels(self):
        self._setLabels(None, title = 'Indirect Fourier Transform', xlabel = 'r [A]', ylabel = 'p(r)', axes = self.subplot1)
        self._setLabels(None, title = 'Fit', xlabel = 'q [1/A]', ylabel = 'I(q)', axes = self.subplot2)
        
    def PlotExperimentObject(self, ExpObj, name = None):
        
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
        #evt = ManipItemEvent(myEVT_MANIP_ITEM, -1, ExpObj)
        #wx.PostEvent(manipulationPage, evt)
        wx.CallAfter(manipulationPage.AddItem, ExpObj)
        
        self.subplot2.cla()
        
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
        
    def ShowErrorbars(self):
        
        for each in self.plottedExps:
            setp(each.errLine[0], visible=True)
            setp(each.errLine[1], visible=True)
        
        if self.fitplot != None:
            setp(self.fitplot.errLine[0], visible=True)
            setp(self.fitplot.errLine[1], visible=True)
            
        self.canvas.draw()
        
    def HideErrorbars(self):
        
        for each in self.plottedExps:
            setp(each.errLine[0], visible=False)
            setp(each.errLine[1], visible=False)
        
        if self.fitplot != None:
            setp(self.fitplot.errLine[0], visible=False)
            setp(self.fitplot.errLine[1], visible=False)
            
        self.canvas.draw()
        
    def SwitchToNoteBookPage(self):
        mainframe = wx.FindWindowByName('MainFrame')
        mainframe.plotNB.SetSelection(1)
        
    def _setLabels(self, ExpObj = None, title = None, xlabel = None, ylabel = None, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        # Set TITLE 
        if title == None:
        
            if a == self.subplot1:
                a.set_title('Indirect Fourier Transform')
                a.set_ylabel('P(r)')
                a.set_xlabel('r [A]')
            elif a == self.subplot2:
                a.set_title('Fit')
                a.set_ylabel('I(q)')
                a.set_xlabel('q [1/A]')
            
        else:
            a.set_title(title)
        
    def PlotLoadedBift(self, BiftObj):
        
        i = BiftObj.allData['orig_i']
        q = BiftObj.allData['orig_q']
        err = BiftObj.allData['orig_err']
        
        ExpObj = cartToPol.RadFileMeasurement(array(i), array(q), array(err), BiftObj.param)
        
        self.PlotBIFTExperimentObject(BiftObj)
        biftPage = wx.FindWindowByName('AutoAnalysisPage')
        biftPage.addBiftObjToList(ExpObj, BiftObj)

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
                    
class CustomListCtrl(wx.ListCtrl):

    def __init__(self, parent, id):
        wx.ListCtrl.__init__(self, parent, id, style = wx.LC_REPORT)
        
        self.dir = '.'
        self.files = []
        
        self.filteredFilesList = []
        self.dirsList = []
        
        images = ['Up.png', 'Folder.png', 'document.png']
        
        self.InsertColumn(0, 'Name')
        self.InsertColumn(1, 'Ext')
        self.InsertColumn(2, 'Size', wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(3, 'Modified')

        self.SetColumnWidth(0, 160)
        self.SetColumnWidth(1, 40)
        self.SetColumnWidth(2, 70)
        self.SetColumnWidth(3, 115)
        
        self.il = wx.ImageList(16, 16)
        
        mainframe = wx.FindWindowByName('MainFrame')
        
        for each in images:
            self.il.Add(wx.Bitmap(os.path.join(mainframe.RAWWorkDir, 'ressources',each)))
            
        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        
        self.ReadFileList()
        self.RefreshFileList()
        
    def ReadFileList(self):
        try:
            self.files = os.listdir(self.dir)
        except OSError, msg:
            print msg
            
    def GetFilteredFileList(self):
        
        selIdx = self.GetParent().dropdown.GetCurrentSelection()
        sel = self.GetParent().fileExtensionList[selIdx]
        
        extIdx = sel.find('*.')
        
        extension = sel[extIdx+1:-1]
        
        if extension == '.':
            extension = ''
        
        if extension != '.*':
            filteredFiles = []
            for each in self.files:
                name, ext = os.path.splitext(each)
                
                if ext.lower() == extension:
                    filteredFiles.append(name+ext)
        else:
            filteredFiles = self.files
    
        # Filelist doesnt take Unicode! convert to normal strings:
        for i in range(0, len(filteredFiles)):
            filteredFiles[i] = str(filteredFiles[i])
            
        filteredFiles.sort(key = str.lower)
        
        return filteredFiles
    
    def RefreshFileList(self):
        
        self.DeleteAllItems()
        
        self.dirsList = []
        
        ### Take out the directories and sort them:
        for each in self.files:
            if os.path.isdir(os.path.join(self.dir, each)):
                self.dirsList.append(each)
        
        for i in range(0, len(self.dirsList)):
            self.dirsList[i] = str(self.dirsList[i])
        
        self.dirsList.sort(key = str.lower)
        
        ## Remove directories fromt the file list:
        for each in self.dirsList:
            self.files.remove(each)
        
        filteredFiles = self.GetFilteredFileList()        
    
        if len(self.dir) > 1:
            self.InsertStringItem(0, '..')
            self.SetItemImage(0,0)
            j = 1
        else:
            j = 0
        
        for i in self.dirsList:
            (name, ext) = os.path.splitext(i)
            ex = ext[1:]
            size = os.path.getsize(os.path.join(self.dir, i))
            sec = os.path.getmtime(os.path.join(self.dir, i))
            
            self.InsertStringItem(j, name)
            self.SetStringItem(j, 1, ex)
            self.SetStringItem(j, 2, '')
            self.SetStringItem(j, 3, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)))

            if os.path.isdir(os.path.join(self.dir,i)):
                self.SetItemImage(j, 1)
            
            if not (j % 2) == 0:
                self.SetItemBackgroundColour(j, '#e6f1f5')
            j += 1
                
        for i in filteredFiles:
            (name, ext) = os.path.splitext(i)
            ex = ext[1:]
            size = os.path.getsize(os.path.join(self.dir, i))
            sec = os.path.getmtime(os.path.join(self.dir, i))
            
            self.InsertStringItem(j, name)
            self.SetStringItem(j, 1, ex)
            self.SetStringItem(j, 2, str(round(size/1000,1)) + ' KB')
            self.SetStringItem(j, 3, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)))

            
            if os.path.isdir(os.path.join(self.dir,i)):
                self.SetItemImage(j, 1)
            else:
                self.SetItemImage(j, 2)
            #self.SetStringItem(j, 2, str(size) + ' B')
            #self.SetStringItem(j, 3, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)))

            if not (j % 2) == 0:
                self.SetItemBackgroundColour(j, '#e6f1f5')
            j += 1
        
    def GetSelectedFilenames(self):
         
        if self.GetSelectedItemCount() == 0:
             return []
        
        selected = []
        selIdx = self.GetFirstSelected()
        
        filename = self.GetItemText(selIdx)
        ext_item = self.GetItem(selIdx,1).GetText()
        
        if ext_item:
            fullfilename = filename + '.' + ext_item
        else:
            fullfilename = filename
        
        selected.append(fullfilename)
        
        for i in range(1, self.GetSelectedItemCount()):
            newSelIdx = self.GetNextSelected(selIdx)
            selIdx = newSelIdx
            
            filename = self.GetItemText(selIdx)
            ext_item = self.GetItem(selIdx,1).GetText()
        
            if ext_item:
                fullfilename = filename + '.' + ext_item
            else:
                fullfilename = filename
            
            selected.append(fullfilename)
    
        return selected
    
    def SetDir(self, dir):
        self.dir = dir
        
        self.ReadFileList()
        self.RefreshFileList()
                    
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
                                  'TXT files (*.txt)',
                                  'IMG files (*.img)']
        
        DirCtrlPanel_Sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.extChoice = self.CreateExtentionBox(DirCtrlPanel_Sizer)       #File extention filter
        
        self.CreateDirCtrl(DirCtrlPanel_Sizer)            #Listbox containing filenames
        
        DirCtrlPanel_Sizer.Add(self.extChoice, 0, wx.EXPAND | wx.TOP, 2)
        
        self.SetSizer(DirCtrlPanel_Sizer, wx.EXPAND)
        
        self.bgFilename = None
        self.selected_file = None
        self.path = '.'
        
        self.FileList = []
        #self.InitFileList()
        print self.path
        
    def SetPath(self, dir):
        
        self.path = dir
        self.fileListBox.SetDir(dir)
        self.UpdateDirLabel(self.path)
                
    def CreateExtentionBox(self, DirCtrlPanel_Sizer):
        
        self.dropdown = wx.Choice(self)        
        self.dropdown.AppendItems(strings = self.fileExtensionList)
        self.dropdown.Select(n=0)
        self.dropdown.Bind(wx.EVT_CHOICE, self.OnChoice)
        
        return self.dropdown
    
    def OnChoice(self, event):
         self.FilterFileListAndUpdateListBox()
         
    def FilterFileListAndUpdateListBox(self):    
         self.fileListBox.ReadFileList()
         self.fileListBox.RefreshFileList()
             
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
        
        #self.fileListBox = wx.ListBox(self, -1, style = wx.LB_EXTENDED)
        self.fileListBox = CustomListCtrl(self, -1)
        
        self.fileListBox.Bind(wx.EVT_KEY_DOWN, self._OnUpdateKey)
        self.fileListBox.Bind(wx.EVT_LEFT_DCLICK, self._OnDoubleClick)
        
        
        self.fileListBox.Bind(wx.EVT_LIST_ITEM_SELECTED, self._OnLeftClick)
        self.fileListBox.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._OnRightClick)
        
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
                
                self.fileListBox.SetDir(self.path)
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
                menu.AppendSeparator()
                menu.Append(7, 'Open in External Viewer')
            
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
            
        if evt.GetId() == 7:
            filename = self.GetSelectedFile()[0]
            
            platform = sys.platform
            
            if platform.find('linux') != -1: 
                pid = subprocess.Popen(['gedit', filename]).pid
                
   
    def OnAverage(self, evt = None):
        filenames = self.GetSelectedFile()
        
        checkedTreatments = getTreatmentParameters()
            
        if len(filenames) > 1:
           ExpList = []
        
           for eachFilename in filenames:
               try:
                   ExpObj, FullImage = fileIO.loadFile(eachFilename, expParams) 
                   cartToPol.applyDataManipulations(ExpObj, expParams, checkedTreatments) 
                   ExpList.append(ExpObj)
               except IndexError:
                    wx.CallAfter(wx.MessageBox, 'Filename: ' + eachFilename + '\nDoes not contain any recognisable data.\n\nIf you are trying to load an image,\nset the correct image format in Options.', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                    return
               
                
           AvgExpObj = cartToPol.averageMeasurements(ExpList, expParams)
             
           plotpanel = wx.FindWindowByName('PlotPanel')
               
           plotpanel.PlotExperimentObject(AvgExpObj, axes = plotpanel.subplot1)

    def _OnLeftClick(self, evt):
        ''' When you leftclick an element in the list '''
        pass
        
    def _OnUpdateKey(self, evt):
        
        if evt.GetKeyCode() == 344:        # 344 = F5
            self.fileListBox.ReadFileList()
            self.fileListBox.RefreshFileList()
            
    def _OnDoubleClick(self, evt):
        
        if self.fileListBox.GetSelectedFilenames() != []:
            fullfilename = self.fileListBox.GetSelectedFilenames()[0]
        else:
            return
        
        if fullfilename == '..':
            self.path = os.path.split(self.path)[0]  
            self.fileListBox.SetDir(self.path)
            self.UpdateDirLabel(self.path)
            
        elif os.path.isdir(os.path.join(self.path, fullfilename)):
            self.path = os.path.join(self.path, fullfilename)
            self.fileListBox.SetDir(self.path)
            self.UpdateDirLabel(self.path)
        
        else:
            wx.FindWindowByName('PlotPanel').onPlotButton(0)
    
    def GetSelectedFile(self):
        ''' Returns a list of files with full path '''
        
        #print self.selectedFiles
        self.selectedFiles = self.fileListBox.GetSelectedFilenames()
        
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
    
            #self.GetListOfFiles()
            self.FilterFileListAndUpdateListBox()
    
    def _OnSetDirButton(self, evt):
        dirdlg = wx.DirDialog(self, "Please select directory:", '')
            
        if dirdlg.ShowModal() == wx.ID_OK:               
            self.path = dirdlg.GetPath()
            
            self.fileListBox.SetDir(self.path)
            self.UpdateDirLabel(self.path)
  
    def UpdateDirLabel(self, path):
        self.DirLabel.SetValue(path)
                                  
    def UpdateFileListBox_Online(self):
        self.fileListBox.ReadFileList()
        self.fileListBox.RefreshFileList()

                            
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
        
    def OnOnlineButton(self, state):
        
        #onlineled = wx.FindWindowById(ONLINELED_ID)
        dirdlg = wx.DirDialog(self.parent, "Please select directory to survey:", '')
        mainframe = wx.FindWindowByName('MainFrame')
        
        if state == 'Online':
            
            if dirdlg.ShowModal() == wx.ID_OK:                
                path = dirdlg.GetPath()
                self.Old_DirList = os.listdir(path)
                self.seekDir = path
                self.UpdateOnlineStatus('Online')
                wx.CallAfter(mainframe.infoPan.WriteText,'Online mode enabled on:\n' + str(path) + '\n')    
                
        else:
            self.UpdateOnlineStatus('Offline')
            wx.CallAfter(mainframe.infoPan.WriteText,'Online mode disabled\n')
            
            plotpanel = wx.FindWindowByName('PlotPanel')
            plotpanel.plotWorkerThread.cleanAvgList()
            
    def UpdateOnlineStatus(self, status):
        
        if status == 'Online':

            self.parent.SetStatusText('Mode: ONLINE', 2)
            self.OnOnline('Online')
            
        elif status == 'Offline':

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

        print "Checker online!"
        
        infopanel = wx.FindWindowByName('InfoPanel')
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        DirList = os.listdir(self.seekDir)
                
        if DirList != self.Old_DirList:

            for idx in range(0, len(DirList)):

                try:
                    chk = self.Old_DirList.index(DirList[idx])
                
                except ValueError:
                    
                    self.Old_DirList.append(DirList[idx])
                    dirctrl.FilterFileListAndUpdateListBox()
                                    
                    infopanel.WriteText('Incomming file:\n' + str(DirList[idx] + '\n\n'))
                    filepath = os.path.join(self.seekDir, str(DirList[idx]))

                    if not(self._FileTypeIsExcluded(filepath)):
                        self.ProcessIncommingFile(filepath)
    
    def ProcessIncommingFile(self, filepath):
        
        print filepath
        
        filename = os.path.split(filepath)[1]
        
        name, extension = os.path.splitext(filename)
        print extension
        if expParams['UseOnlineFilter']:
            if extension == '.' + expParams['OnlineFilterExt'] or extension == expParams['OnlineFilterExt']:
                plotQueue.put(([filepath], True))
            else:
                print 'Extension doesnt match'
        else:
            plotQueue.put(([filepath], True))
            
    def CheckIfFilenameIsBackground(self, filepath):
        
        filename = os.path.split(filepath)[1]
        
        #bgPatternType = expParams['AutBgPatternType']
        #bgPattern = expParams['BgPatternValue']
        
        regexp = expParams['AutoBgSubRegExp']
        
        try:
            pattern = re.compile(regexp)
        except:
            return False
    
        m = pattern.match(filename)
    
        if m:
            return True
        else:
            return False
        
#        if bgPatternType == 'contain':
#            result = filename.find(bgPattern)
#            
#            print "result:", str(result)
#            
#            if result < 0:
#                return False
#            else:
#                return True
#            
#        elif bgPatternType == 'start':
#            
#            return filename.startswith(bgPattern)   # A python string function
#            
#        elif bgPatternType == 'end':
#            
#            return filename.endswith(bgPattern)    # A python string function
    
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
        
        return

#----- **** Custom Events ****

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

#----- **** Custom SpinCtrls ****

class FloatSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, initValue = None, button_style = wx.SP_VERTICAL, TextLength = 40, **kwargs):
        
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
                
        self.Scale = wx.TextCtrl(self, -1, initValue, size = (TextLength,22), style = wx.TE_PROCESS_ENTER)
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
    
    def __init__(self, parent, id, min = None, max = None, TextLength = 40, **kwargs):
        
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
        
        self.Scale = wx.TextCtrl(self, -1, str(min), size = (TextLength,22), style = wx.TE_PROCESS_ENTER)
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
        
        #if val != self.oldValue:
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
                    
        self.oldValue = newval
        wx.CallAfter(self.CastFloatSpinEvent)
        
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
        
        self.oldValue = newval
        wx.CallAfter(self.CastFloatSpinEvent)
        
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
    
    def __init__(self, parent, id, scrollList, minIdx = None, maxIdx = None, TextLength = 40, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        self.scrollList = scrollList
        
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = wx.SP_VERTICAL)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999)
        
        self.Scale = wx.TextCtrl(self, -1, str(scrollList[0]), size = (TextLength,22), style = wx.TE_PROCESS_ENTER)
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
        
        self.ScalerButton.SetValue(0)
        
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
            

class ManipFilePanel(wx.Panel):
    def __init__(self, parent, ExpObj):
        
        self.ExpObj = ExpObj
        filename = os.path.split(ExpObj.param['filename'])[1]
        
        self.ExpObj.itempanel = self

        #font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        #self.statusLabel.SetFont(font)  
        
        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)
        
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseClick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightMouseClick)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        #self.Bind(wx.EVT_CHAR, self.OnKeyPress)
        
                                       #Label, TextCtrl_ID, SPIN_ID
        self.qmax = len(ExpObj.i_raw)
                             
        self.spinControls = (("q Min:", wx.NewId(), wx.NewId(), (1, self.qmax-1), 'nlow'),        
                             ("q Max:", wx.NewId(), wx.NewId(), (2, self.qmax), 'nhigh'))
        
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
        
        self.UpdateControlsAndPlot(None)   
    
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
        
        for each in self.GetChildren():
            if each.GetId() != evt.GetId():
                
                if not evt.GetEventObject().IsChecked():
                    each.Enable(False)
                else:
                    each.Enable(True)
            
        
    def OnFloatSpinCtrlChange(self, evt):
        
        id = evt.GetId()
        value = evt.GetValue()
        
        for eachLabel, eachId, eachName, eachInitValue, eachBindfunc in self.floatSpinControls:
            
            if id == eachId:
                
                if eachName == 'scale':
                    self.ExpObj.scale(value)
                elif eachName == 'offset':
                    self.ExpObj.offset(value)
        
        self.ExpObj.plotPanel.updatePlotAfterScaling(self.ExpObj)

        evt.Skip()
                
    def OnQrangeSpinCtrlChange(self, evt):
        self.UpdateControlsAndPlot(evt.GetId())
        self.UpdatePlot()
    
    def UpdateControlsAndPlot(self, evtID):
                
        qminID = self.spinControls[0][1]
        qmaxID = self.spinControls[1][1]
        
        qmintxt = wx.FindWindowById(self.spinControls[0][2])
        qmaxtxt = wx.FindWindowById(self.spinControls[1][2])
        
        qminCtrl = wx.FindWindowById(qminID)
        qmaxCtrl = wx.FindWindowById(qmaxID)
        
        qmin = int(qminCtrl.GetValue())
        qmax = int(qmaxCtrl.GetValue())
                    
        if evtID == self.spinControls[0][1] or evtID == self.spinControls[0][2]:    
            if qmin >= qmax:
                qmin = qmax-1
                qminCtrl.SetValue(qmin)
                
            self.ExpObj.setQrange((qmin-1, qmax))
        else:
            if qmax <= qmin:
                qmax = qmin + 1
                qmaxCtrl.SetValue(qmax)
                
            self.ExpObj.setQrange((qmin-1, qmax))
        
        qmintxt.SetValue(str(round(self.ExpObj.q_raw[qmin-1],4)))
        qmaxtxt.SetValue(str(round(self.ExpObj.q_raw[qmax-1],4)))    
        
        qmaxCtrl.SetValue(qmax)
        
    def UpdatePlot(self):
        wx.CallAfter(self.ExpObj.plotPanel.updatePlotAfterScaling,self.ExpObj)
        
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
        
    def OnEnterInQrange(self, evt):
        
        id = evt.GetId()
        
        lx = self.ExpObj.q_raw
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
        
        txtctrl = wx.FindWindowById(id)
        
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            if id == self.spinControls[0][2]:
                spinctrl = wx.FindWindowById(self.spinControls[0][1])
                idx = int(spinctrl.GetValue())
                txtctrl.SetValue(str(round(self.ExpObj.q[idx],4)))
                return
            
            if id == self.spinControls[1][2]:
                spinctrl = wx.FindWindowById(self.spinControls[1][1])
                idx = int(spinctrl.GetValue())
                txtctrl.SetValue(str(round(self.ExpObj.q[idx],4)))
                return
        
        if id == self.spinControls[0][2]:
                spinctrl = wx.FindWindowById(self.spinControls[0][1])
        elif id == self.spinControls[1][2]:
                spinctrl = wx.FindWindowById(self.spinControls[1][1])
        
        closest = findClosest(val,lx)
        print closest
        
        idx = where(lx == closest)[0][0]+1 #These spincontrols starts from 1 and not from 0
        
        print idx
            
        spinctrl.SetValue(idx)
       
        #Updates txtctrls and plot:
        self.UpdateControlsAndPlot(evt.GetId())
        self.UpdatePlot()

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
            analysisPage.runBiftOnExperimentObject(self.ExpObj.copy(), expParams)
            
        if evt.GetId() == 12:
            #Add to IFT List
            autoanalysis = wx.FindWindowByName('AutoAnalysisPage')
            
            for ExpObj in ManipulationPage.GetSelectedExpObjs():
                ExpObjIFT = ExpObj.copy()
                autoanalysis.addExpObjToList(ExpObjIFT)
            
            wx.CallAfter(wx.MessageBox, 'File(s) have been added to the IFT list', 'Files Added')
            
        if evt.GetId() == 11:
            #GNOM
            analysisPage.runBiftOnExperimentObject(self.ExpObj.copy(), expParams)
            
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
            
            
            spinCtrl = FloatSpinCtrl(self, id, initValue, TextLength = 93)
            spinCtrl.Bind(EVT_MY_SPIN, bindfunc)
            
            controlSizer.Add(label, 1, wx.TOP, 3)
            controlSizer.Add(spinCtrl, 1)
        
    def CreateSimpleSpinCtrls(self, controlSizer):
        
        for eachSpinCtrl in self.spinControls:
                spin_id = eachSpinCtrl[1]
                spinLabelText = eachSpinCtrl[0]
                qtxtId = eachSpinCtrl[2]
                spinRange = eachSpinCtrl[3]
                spinName = eachSpinCtrl[4]
                
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
                
                qCtrl = wx.TextCtrl(self, qtxtId, '', size = (50,22), style = wx.PROCESS_ENTER)
                qCtrl.Bind(wx.EVT_TEXT_ENTER, self.OnEnterInQrange)
                
                spinSizer = wx.BoxSizer()
                spinSizer.Add(qCtrl, 0, wx.RIGHT, 3)
                spinSizer.Add(SpinControl, 0)
                
                controlSizer.Add(SpinLabel, 1, wx.TOP, 3)        
                controlSizer.Add(spinSizer, 1)                    
        
class ManipulationPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, name = 'ManipulationPage')
        
        self.buttonData = ( ('BIFT', self.OnBift),
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
        
        
class MyStatusBar(wx.StatusBar):
    
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
    def OnPaint(self,event):
        dc = wx.PaintDC(self)
        self.Draw(dc)
    def Draw(self,dc):
        dc.BeginDrawing()
        dc.SetBackground( wx.Brush("White") )
        dc.Clear()
        dc.SetPen(wx.Pen('BLACK'))
        dc.DrawText(self.GetStatusText(),0,0)
        dc.EndDrawing()
        
class MainFrame(wx.Frame):
    
    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title, name = 'MainFrame')
        
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
        
        splitter1 = wx.SplitterWindow(self, -1)
        splitter2 = wx.SplitterWindow(splitter1, -1)
        
        self.RAWWorkDir = os.getcwd()
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        #self.statusbar = MyStatusBar(self)
        #self.SetStatusBar(self.statusbar)
        
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
        
        # Start Plot Threads:
        plotpage1.plotWorkerThread = PlotWorkerThread(plotpage1, None)
        plotpage1.plotWorkerThread.setDaemon(True)
        plotpage1.plotWorkerThread.start()
        
        self.autoBgSubThread = AutoBgSubWorkerThread(self)
        self.autoBgSubThread.setDaemon(True)
        self.autoBgSubThread.start()
    
        plotpage2 = masking.MaskingPanel(self.plotNB, -1, 'RawPlotPanel', wxEmbedded = True)
        #plotpage3 = PlotPanel(self.plotNB, wx.NewId(), 'BIFTPlotPanel', 2)
        
        plotpage3 = IftPanel(self.plotNB, wx.NewId(), 'BIFTPlotPanel', 2)
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
                
        splitter1.SplitVertically(self.button_panel, self.plot_panel, 380)
        splitter1.SetMinimumPaneSize(50)
        
        #Load workdir from rawcfg.dat:
        self.LoadCfg()
         
        self.CreateMenuBar()
        
        self.guinierframe = None
        
    def LoadCfg(self):
        
        try:
            file = 'rawcfg.dat'
            FileObj = open(file, 'r')
            savedInfo = cPickle.load(FileObj)
            FileObj.close()
            
            dirctrl = wx.FindWindowByName('DirCtrlPanel')
            dirctrl.SetPath(savedInfo['workdir'])
            
            self.ChangeParameter('ImageFormat', savedInfo['ImageFormat'])
        except:
            pass
        
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)
        
    def SetViewMenuScale(self, id):
        self.MenuBar.FindItemById(id).Check(True)
        
    def _CreateSingleMenuBarItem(self, info):
        
        menu = wx.Menu()
        
        for each in info:
            
            type = each[3]
            bindFunc = each[2]
            menuid = each[1]
            label = each[0]
            
            if type == 'normal':
                menu.Append(menuid, label)
                self.Bind(wx.EVT_MENU, bindFunc, id = menuid)
            
            elif type == 'check':
                menu.AppendCheckItem(menuid, label)
                self.Bind(wx.EVT_MENU, bindFunc, id = menuid)
                
            elif type == 'radio':
                menu.AppendRadioItem(menuid, label)
                self.Bind(wx.EVT_MENU, bindFunc, id = menuid)
                
            elif type == 'submenu':
                submenu = self._CreateSingleMenuBarItem(bindFunc)
                menu.AppendSubMenu(submenu, label)
            
            elif type == 'separator':
                menu.AppendSeparator()
                
        return menu

    def CreateMenuBar(self):
        
        submenus = {#'viewPlot1Sub' : [('Normal',  self.MenuIDs['plot1tynormal'], self.OnViewMenu, 'radio'),
#                                      ('Guinier', self.MenuIDs['plot1tyguinier'],self.OnViewMenu, 'radio'),
#                                      ('Kratky',  self.MenuIDs['plot1tykratky'], self.OnViewMenu, 'radio'),                            
#                                      ('Porod',   self.MenuIDs['plot1typorod'],  self.OnViewMenu, 'radio')],
#        
#                    'viewPlot2Sub' : [('Subtracted',  self.MenuIDs['plot2tysubtracted'], self.OnViewMenu, 'radio'),
#                                      ('Guinier', self.MenuIDs['plot2tyguinier'],self.OnViewMenu, 'radio'),
#                                      ('Kratky',  self.MenuIDs['plot2tykratky'], self.OnViewMenu, 'radio'),
#                                      ('Porod',   self.MenuIDs['plot2typorod'],  self.OnViewMenu, 'radio')],
                    
                    'viewPlot1Scale':[('Lin-Lin', self.MenuIDs['plot1sclinlin'], self.OnViewMenu, 'radio'),
                                      ('Log-Lin', self.MenuIDs['plot1scloglin'], self.OnViewMenu, 'radio'),
                                      ('Log-Log', self.MenuIDs['plot1scloglog'], self.OnViewMenu, 'radio'),
                                      ('Lin-Log', self.MenuIDs['plot1sclinlog'], self.OnViewMenu, 'radio'),
                                      ('Guinier', self.MenuIDs['plot1tyguinier'],self.OnViewMenu, 'radio'),
                                      ('Kratky',  self.MenuIDs['plot1tykratky'], self.OnViewMenu, 'radio'),                            
                                      ('Porod',   self.MenuIDs['plot1typorod'],  self.OnViewMenu, 'radio')],
                                      
                    'viewPlot2Scale':[('Lin-Lin', self.MenuIDs['plot2sclinlin'], self.OnViewMenu, 'radio'),
                                      ('Log-Lin', self.MenuIDs['plot2scloglin'], self.OnViewMenu, 'radio'),
                                      ('Log-Log', self.MenuIDs['plot2scloglog'], self.OnViewMenu, 'radio'),
                                      ('Lin-Log', self.MenuIDs['plot2sclinlog'], self.OnViewMenu, 'radio'),
                                      ('Guinier', self.MenuIDs['plot2tyguinier'],self.OnViewMenu, 'radio'),
                                      ('Kratky',  self.MenuIDs['plot2tykratky'], self.OnViewMenu, 'radio'),
                                      ('Porod',   self.MenuIDs['plot2typorod'],  self.OnViewMenu, 'radio')],
                    
                    'onlinemenu':    [('Offline', self.MenuIDs['goOffline'], self.OnOnlineMenu, 'radio'),
                                      ('Online', self.MenuIDs['goOnline'], self.OnOnlineMenu, 'radio')]}         
                                    
        
        menus = [('&File',    [('E&xit', self.MenuIDs['exit'], self.OnFileMenu, 'normal')]),
                 
                 ('&Options', [('&Advanced Options...', self.MenuIDs['advancedOptions'], self.OnOptionsMenu, 'normal'),
                              (None, None, None, 'separator'),
                              ('&Load Settings', self.MenuIDs['loadSettings'], self.OnLoadMenu, 'normal'),
                              ('&Save Settings', self.MenuIDs['saveSettings'], self.OnSaveMenu, 'normal'),
                              (None, None, None, 'separator'),
                              ('&Online mode', None, submenus['onlinemenu'], 'submenu')]),
                              
                 ('&View',    [#('&1D Plot (top) Type', None, submenus['viewPlot1Sub'], 'submenu'),
                              #('1D &Plot (bottom) Type', None, submenus['viewPlot2Sub'], 'submenu'),
                              #(None, None, None, 'separator'),
                              ('&Top Plot Axes', None, submenus['viewPlot1Scale'], 'submenu'),
                              ('&Bottom Plot Axes', None, submenus['viewPlot2Scale'], 'submenu')]),
                              
                 ('&Tools',   [('&Guinier fit...', self.MenuIDs['guinierfit'], self.OnToolsMenu, 'normal'),
                              #('&Centering...', self.MenuIDs['centering'], self.OnToolsMenu, 'normal')
                              ]),
                              
                 ('&Help',    [('&Help!', self.MenuIDs['help'], self.OnHelp, 'normal'),
                               (None, None, None, 'separator'),
                               ('&About', self.MenuIDs['about'], self.OnAboutDlg, 'normal')])]
        
        menubar = wx.MenuBar()
        
        for each in menus:
         
            menuitem = self._CreateSingleMenuBarItem(each[1])
            menubar.Append(menuitem, each[0])    
            
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
                masking.LoadBeamStopMask(expParams['BeamStopMaskFilename'], cfgload = True) # Load beamstop mask uses BeamStopMaskParams to generate mask and only tried to load the file if no params are found
                
            elif expParams['ReadOutNoiseMaskFilename']:      
                masking.LoadBeamStopMask(expParams['ReadOutNoiseMaskFilename'], cfgload = True)
                
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
        
        if os.path.splitext(file)[1] != '.cfg':
            file = file + '.cfg'
        
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
        
    def OnToolsMenu(self, evt):
        
        id = evt.GetId()
        
        if id == self.MenuIDs['guinierfit']:
                        
            manippage = wx.FindWindowByName('ManipulationPage')
            
            if len(manippage.GetSelectedExpObjs()) > 0:
                ExpObj = manippage.GetSelectedExpObjs()[0]
                self.ShowGuinierFitFrame(ExpObj)
            else:
                wx.MessageBox("Please select a plot from the plot list on the manupulation page.", "No plot selected")
            
            #dialog = guinierGUI.GuinierFitDialog(self, ExpObj)
            #dialog.ShowModal()  
            #dialog.Destroy()
            

    def OnViewMenu(self, evt):
        
        val = evt.GetId()
        
        key = [k for k, v in self.MenuIDs.iteritems() if v == val][0]
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        if key[0:7] == 'plot2sc':
            plotpanel.plotparams['axesscale2'] = key[-6:]
            plotpanel.plotparams['plot2type'] = 'subtracted'
            plotpanel.UpdatePlotAxesScaling()
            plotpanel.UpdatePlotsAfterTypeChange(plotpanel.subplot2)
         
        elif key[0:7] == 'plot1sc':
            plotpanel.plotparams['axesscale1'] = key[-6:]
            plotpanel.plotparams['plot1type'] = 'normal'
            plotpanel.UpdatePlotAxesScaling()
            plotpanel.UpdatePlotsAfterTypeChange(plotpanel.subplot1)
            
        elif key[0:7] == 'plot1ty':
            plotpanel.plotparams['plot1type'] = key[7:]
            
            if key[7:] == 'guinier':
                plotpanel.plotparams['axesscale1'] = 'loglin'
                plotpanel.UpdatePlotAxesScaling()
                #self.MenuBar.FindItemById(self.MenuIDs['plot1scloglin']).Check(True)
            
            elif key[7:] == 'kratky' or key[7:] == 'porod':
                plotpanel.plotparams['axesscale1'] = 'linlin'
                plotpanel.UpdatePlotAxesScaling()
                #self.MenuBar.FindItemById(self.MenuIDs['plot1sclinlin']).Check(True)
                
            plotpanel.UpdatePlotsAfterTypeChange(plotpanel.subplot1)
            
    
        elif key[0:7] == 'plot2ty':
            plotpanel.plotparams['plot2type'] = key[7:]
            
            
            if key[7:] == 'guinier':
                plotpanel.plotparams['axesscale2'] = 'loglin'
                plotpanel.UpdatePlotAxesScaling()
                #self.MenuBar.FindItemById(self.MenuIDs['plot2scloglin']).Check(True)
                
            elif key[7:] == 'kratky' or key[7:] == 'porod':
                plotpanel.plotparams['axesscale2'] = 'linlin'
                plotpanel.UpdatePlotAxesScaling()
                #self.MenuBar.FindItemById(self.MenuIDs['plot2sclinlin']).Check(True)
            
            plotpanel.UpdatePlotsAfterTypeChange(plotpanel.subplot2)

    
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
        info.Version = "0.99.7.1 Beta"
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
    
        frame = MainFrame('BioXTAS RAW 0.99.7.1b', -1)
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
    
