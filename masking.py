#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    BioXTAS RAW is free software: you can redistribute it and/or modify
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
#    along with BioXTAS RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************


import matplotlib
matplotlib.use('WXAgg')
matplotlib.rc('image', origin = 'lower')        # turn image upside down.. x,y, starting from lower left

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg#,Toolbar, FigureCanvasWx
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.patches import Circle, Rectangle, Polygon
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor#, Slider, Button
from matplotlib.text import Text

import cPickle, threading, os
from scipy import io, optimize
import wx, fileIO
import cartToPol
from numpy import *
import polygonMasking as polymask
import Queue
#import pylab

class MaskingPanelToolbar(NavigationToolbar2Wx):
    def __init__(self, parent, canvas):

        self.fig_axes = parent.fig.gca()
        self.parent = parent
        
        self._MTB_CIRCLE    = wx.NewId()
        self._MTB_RECTANGLE = wx.NewId()
        self._MTB_POLYGON   = wx.NewId()
        self._MTB_SAVEMASK  = wx.NewId()
        self._MTB_LOADMASK  = wx.NewId()
        self._MTB_CLEAR     = wx.NewId()
        self._MTB_AGBECENT  = wx.NewId()
        self._MTB_HDRINFO   = wx.NewId()
        self._MTB_IMGSET    = wx.NewId()
        #self._MTB_EQUAL     = wx.NewId()
        
        self.allToolButtons = [self._MTB_CIRCLE, 
                               self._MTB_RECTANGLE,
                               self._MTB_POLYGON,
                               self._MTB_SAVEMASK,
                               self._MTB_LOADMASK,
                               self._MTB_CLEAR,
                               self._MTB_AGBECENT,
                               self._MTB_HDRINFO,
                               self._MTB_IMGSET]
         #                      self._MTB_EQUAL]
        
        NavigationToolbar2Wx.__init__(self, canvas)
        
        mainframe = wx.FindWindowByName('MainFrame')
        
        if mainframe:
            workdir = mainframe.RAWWorkDir
        else:
            workdir = './'   # USED WHEN RUNNING TESTS
       
        circleIcon    = wx.Bitmap(os.path.join(workdir, "ressources", "circle.png"), wx.BITMAP_TYPE_PNG)
        rectangleIcon = wx.Bitmap(os.path.join(workdir, "ressources", "rect.png"), wx.BITMAP_TYPE_PNG)
        polygonIcon   = wx.Bitmap(os.path.join(workdir, "ressources", "poly.png"), wx.BITMAP_TYPE_PNG)
        saveMaskIcon  = wx.Bitmap(os.path.join(workdir, "ressources", "savemask.png"), wx.BITMAP_TYPE_PNG)
        clearIcon     = wx.Bitmap(os.path.join(workdir, "ressources", "clear.png"), wx.BITMAP_TYPE_PNG)
        loadMaskIcon  = wx.Bitmap(os.path.join(workdir, "ressources", "load.png"), wx.BITMAP_TYPE_PNG)
        agbeCentIcon  = wx.Bitmap(os.path.join(workdir, "ressources", "agbe2.png"), wx.BITMAP_TYPE_PNG)
        hdrInfoIcon   = wx.Bitmap(os.path.join(workdir, "ressources", "hdr.png"), wx.BITMAP_TYPE_PNG)
        ImgSetIcon    = wx.Bitmap(os.path.join(workdir, "ressources", "imgctrl.png"), wx.BITMAP_TYPE_PNG)
        #EqualIcon     = wx.Bitmap(os.path.join(workdir, "ressources", "hdr.png"), wx.BITMAP_TYPE_PNG)

        self.AddSeparator()
        self.AddCheckTool(self._MTB_CIRCLE, circleIcon, shortHelp = 'Create Circle Mask')
        self.AddCheckTool(self._MTB_RECTANGLE, rectangleIcon, shortHelp = 'Create Rectangle Mask')
        self.AddCheckTool(self._MTB_POLYGON, polygonIcon, shortHelp = 'Create Polygon Mask')
        self.AddSeparator()
        self.AddSimpleTool(self._MTB_SAVEMASK, saveMaskIcon, 'Save Mask')
        self.AddSimpleTool(self._MTB_LOADMASK, loadMaskIcon, 'Load Mask')
        self.AddSimpleTool(self._MTB_CLEAR, clearIcon, 'Clear Mask')
        self.AddCheckTool(self._MTB_AGBECENT, agbeCentIcon, shortHelp ='Calibrate using AgBe')
        self.AddSeparator()
        self.AddSimpleTool(self._MTB_HDRINFO, hdrInfoIcon, 'Show Header Information')
        self.AddSimpleTool(self._MTB_IMGSET, ImgSetIcon, 'Image Display Settings')
        #self.AddSimpleTool(self._MTB_EQUAL, EqualIcon)
        self.Bind(wx.EVT_TOOL, self.circleTool, id = self._MTB_CIRCLE)
        self.Bind(wx.EVT_TOOL, self.rectangleTool, id = self._MTB_RECTANGLE)
        self.Bind(wx.EVT_TOOL, self.polygonTool, id = self._MTB_POLYGON)
        self.Bind(wx.EVT_TOOL, self.saveMask, id = self._MTB_SAVEMASK)
        self.Bind(wx.EVT_TOOL, self.loadMask, id = self._MTB_LOADMASK)
        self.Bind(wx.EVT_TOOL, self.clearButton, id = self._MTB_CLEAR)
        self.Bind(wx.EVT_TOOL, self.agbeCent, id = self._MTB_AGBECENT)
        self.Bind(wx.EVT_TOOL, self.hdrInfo, id = self._MTB_HDRINFO)
        self.Bind(wx.EVT_TOOL, self.ImgSet, id = self._MTB_IMGSET)
        #self.Bind(wx.EVT_TOOL, self.equalInfo, id = self._MTB_EQUAL)
        
        self.RemoveTool(self._NTB2_BACK)
        self.RemoveTool(self._NTB2_FORWARD)
        
        self.Realize()
    
#    def equalInfo(self, event):
#        
#        self.parent.equilibrate()
#    
    def ImgSet(self, event):
        
        self.parent.showImageSetDialog()
                
    def hdrInfo(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        self.parent.showHdrInfo()
        
    def agbeCent(self, event):
        self._deactivatePanZoom()
        
        if not self.GetToolState(self._MTB_AGBECENT):
            self.parent.setTool(None)
        else:
            self.parent.setTool('agbecent')
            self.parent.clearPatches()
            self.parent.agbeCalibration()
    
    def circleTool(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        
        if self.GetToolState(self._MTB_CIRCLE):
            self.untoggleAllToolButtons(self._MTB_CIRCLE)
            self.parent.setTool('circle')
        else:
            self.untoggleAllToolButtons()

            
    def rectangleTool(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        
        if self.GetToolState(self._MTB_RECTANGLE):
            self.untoggleAllToolButtons(self._MTB_RECTANGLE)
            self.parent.setTool('rectangle')
        else:
            self.untoggleAllToolButtons()
    
    def polygonTool(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        
        if self.GetToolState(self._MTB_POLYGON):
            self.untoggleAllToolButtons(self._MTB_POLYGON)
            self.parent.setTool('polygon')
        else:
            self.untoggleAllToolButtons()
        
    
    def clearButton(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        self.parent.onClear()

    def saveMask(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        self.parent.onSaveMask()
        
    def loadMask(self, event):
        self._deactivateAgbeCent()
        self._deactivatePanZoom()
        self.parent.onLoadMask()

    def untoggleAllToolButtons(self, tog = None):
        
        for each in self.allToolButtons:
        
            if tog == None:
                self.ToggleTool(each, False)
            elif each != tog:
                self.ToggleTool(each, False)
        
        if tog == None:
            self.parent.setTool(None)
    
    def _deactivateMaskTools(self):
        self.parent.stopMaskCreation()
        self.untoggleAllToolButtons()
    
    def _deactivateAgbeCent(self):
        
        if self.GetToolState(self._MTB_AGBECENT):
            self.ToggleTool(self._MTB_AGBECENT, False)
            self.parent.setTool(None)
            self.parent.plotStoredMasks()
    
    def _deactivatePanZoom(self):
        
        ## Disable the zoon and pan buttons if they are pressed:
        if self.GetToolState(self._NTB2_ZOOM):
            self.ToggleTool(self._NTB2_ZOOM, False)
            self.zoom()
            
        if self.GetToolState(self._NTB2_PAN):
            self.ToggleTool(self._NTB2_PAN, False)
            self.pan()
            
    def zoom(self, *args):
        self._deactivateMaskTools()
        self.ToggleTool(self._NTB2_PAN, False)
        NavigationToolbar2.zoom(self, *args)
    
    def pan(self, *args):
        self._deactivateMaskTools()
        self.ToggleTool(self._NTB2_ZOOM, False)
        NavigationToolbar2.pan(self, *args)
        
        
class MaskingPanel(wx.Panel):
    
    def __init__(self, parent, panel_id, name, wxEmbedded = False):
        
        wx.Panel.__init__(self, parent, panel_id, name = name)

        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        
        
        self.canvas.mpl_connect('motion_notify_event', self.onMotionEvent)
        self.canvas.mpl_connect('button_press_event', self.onMouseButtonPressEvent)
        self.canvas.mpl_connect('button_release_event', self.onMouseReleaseEvent)
        self.canvas.mpl_connect('pick_event', self.onPick)
        self.canvas.mpl_connect('key_press_event', self.onKeyPressEvent)
        
        self.toolbar = MaskingPanelToolbar(self, self.canvas)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)
        
        if wxEmbedded == True:
            color = parent.GetThemeBackgroundColour()
            self.SetColor(color)
        
        self.SetSizer(sizer)
        self.Fit()
        
        self.plottedPatches = []
        
        # Variables for the plotted experiments:
        
        #### FOR MASKING ######
        
        self.selectedPointsXY = []
        self.chosenPointsX = []
        self.chosenPointsY = []
        self.agbeSelectedPoints = []
        
        self.stopmove = False
        self.movementInProgress = False
        self.toggleSelect = None
        self.selectedPatch = None
        
        self.firstMousePos = None
        
        self.detectorPixelSize = None
        
        self.plottingInProgress = True
        self.guideLinePlotted = False
        
        self.mask = []
        
        self.nextMaskNumber = 0
        self.imgDim = (1,1)
        self.cursor = None
        self.cursorIsOff = True
        
        self.selectedMask = []
        
        # These are the plot parameters that can be saved:
        self.plotParameters = {'axesscale'       : 'linlin',
                               'currentTool'     : None, 
                               'imageBorder'     : 50,         # Make it an even number!
                               'usePatches'      : True,       # Use matplotlibs patches (circle patch, rect and poly)
                               'finalMask'       : [],
                               'storedMasks'     : [],
                               'imageDimentions' : (),
                               'UpperClim'       : None,
                               'LowerClim'       : None,
                               'ImgScale'        : 'linear',
                               'ColorMap'        : matplotlib.cm.jet,
                               'ClimLocked'      : False,
                               'Tst'             : 1,
                               'Brightness'      : 100,
                               'Contrast'        : 100,
                               'maxImgval'       : None,
                               'minImgVal'       : None}
        
        self.img = []
        self.imgobj = None
        self.imgcopy = []
    
        self.fig.gca().set_visible(False)
        self.ExpObj = None
        self.imgZeros = None

        
    def getMaskWithId(self, id):
        
        for each in self.plotParameters['storedMasks']:
            if each.maskID == id:
                return each
            
    def getPatchWithId(self, id):
        
        for each in self.plottedPatches:
            if each.id == id:
                return each
            
            
    def agbeCalibration(self):
        
        self.agbeSelectedPoints = []
        answer = wx.MessageBox('Please select at least 3 points just outside the inner circle of the AgBe image\nand then right click or press space.', 'AgBe Center Calibration', wx.OK | wx.CANCEL)
        
        if answer == wx.CANCEL:
            self.toolbar.untoggleAllToolButtons()
            self.plotStoredMasks()
        
    def onPick(self, event):
        
        artist = event.artist
        
        if not self.plotParameters['currentTool']:  #No tool is selected
            
            if event.artist.selected == 0:
                self.toggleSelect = artist
                 
                event.artist.selected = 1
                self.selectedPatch = artist

            else:
                self.selectedPatch = artist
                self.toggleSelect = artist
                self.movementInProgress = True

    def onKeyPressEvent(self, event):
        
        if event.key == 'escape':
            self.toolbar.untoggleAllToolButtons()
        
            if self.plottingInProgress == True:
                self.plottingInProgress = False
        
            self.agbeSelectedPoints = []
            self.stopMaskCreation()
            
        if event.key == 'delete':
            
            for each in self.plottedPatches:
                if each.selected == 1:
                    
                    for idx in range(0, len(self.plotParameters['storedMasks'])):
                        if each.id == self.plotParameters['storedMasks'][idx].maskID:
                            self.plotParameters['storedMasks'].pop(idx)
                            break
            
            self.plotStoredMasks()

        if event.key == ' ': #space # End agbeCalibration on space
            
            tool = self.plotParameters['currentTool']
            
            if tool == 'agbecent':
                    if len(self.agbeSelectedPoints) > 2:
                        self.endAgBeCalibration()
                    else:
                        answer = wx.MessageBox('You need atleast 3 points to calculate the center!', 'Not enough points!', wx.OK | wx.CANCEL)
                        
                        if answer == wx.CANCEL:
                            self.agbeSelectedPoints = []
                            self.plotStoredMasks()
                        else:
                            return
                    
                    self.toolbar.untoggleAllToolButtons()
        
        if event.key == 'a':
            for each in self.plottedPatches:
                if each.selected == 1:
                    
                    for idx in range(0, len(self.plotParameters['storedMasks'])):
                        if each.id == self.plotParameters['storedMasks'][idx].maskID:
                            points = self.plotParameters['storedMasks'][idx].getFillPoints()

                            print sum(self.img[points])/len(points)
                    
                           
    def clearCurrentTool(self):
        self.plotParameters['currentTool'] = None
        
    def setCursor(self, state):
        
        a = self.fig.gca()
        
        if state == 'off':
            if self.cursor:
                self.cursor.clear(0)
            
        elif state == 'on':
            self.cursor = Cursor(a, useblit = True, color='red', linewidth=1 )
    
    def equilibrate(self):
        
        print 'check!'
        
        allAvg = []
        maxval = []
        minval = []
        stds = []
        
        for each in self.plottedPatches:
                #if each.selected == 1:
                    
                    for idx in range(0, len(self.plotParameters['storedMasks'])):
                        if each.id == self.plotParameters['storedMasks'][idx].maskID:
                            points = self.plotParameters['storedMasks'][idx].getFillPoints()

                            vals = []
                            for eachp in points:
                                vals.append(self.img[eachp])
                            
                            averageval = sum(vals)/len(points)
                            stds.append(std(vals))
                            maxval.append(max(vals))
                            minval.append(min(vals))
                            print 'Median: ', str(median(vals))
                            
                            print '#' + str(idx) + ' STD: ', str(std(vals))
                            allAvg.append(averageval)
        
        mult = False
        
        print 'Maxs :', str(maxval)
        print 'Mins :', str(minval)
        
        avgmin = average(minval)
        avgmax = average(maxval)
        
        mineq = avgmin - minval
        
        print 'Average :', str(allAvg)
        avgOfAvg = average(allAvg)
        
        print 'Avg of Avg :', str(avgOfAvg)
        
        if mult == True:
            print 'Scale '
            scalesMult = avgOfAvg / allAvg
        else:
            scales = avgOfAvg - allAvg            

        print scales
                
        b = self.plotParameters['imageBorder']/2
        
        newImg = zeros((2048,2048))
##        # 1
        self.img[1024 +b:2048+b, 0+b:1024+b] = self.img[1024+b:2048+b, 0+b:1024+b] + scales[0]
#        # 2
        self.img[1024 +b:2048+b, 1024+b:2048+b] = self.img[1024+b:2048+b, 1024+b:2048+b] + scales[1]
#        #3
        self.img[0 +b:1024+b, 1024+b:2048+b] = self.img[0+b:1024+b, 1024+b:2048+b] + scales[2]
#        #4

        #scalemult = allAvg[4] / allAvg[5]
        #print allAvg[4], allAvg[5]
        #print 'scale:', str(scalemult)
        
        scalemult = 1
        
        self.img[0 +b:1024+b, 0+b:1024+b] = (self.img[0+b:1024+b, 0+b:1024+b] + scales[3]) * scalemult #(allAvg[2]-allAvg[3]) 
                      
        # 1
#        self.img[1024 +b:2048+b, 0+b:1024+b] = (self.img[1024+b:2048+b, 0+b:1024+b] - allAvg[0]) / stds[0] 
#        # 2
#        self.img[1024 +b:2048+b, 1024+b:2048+b] = (self.img[1024+b:2048+b, 1024+b:2048+b] - allAvg[1]) / stds[1]
#        #3
#        self.img[0 +b:1024+b, 1024+b:2048+b] = (self.img[0+b:1024+b, 1024+b:2048+b] - allAvg[2]) / stds[2]
#        #4
#        self.img[0 +b:1024+b, 0+b:1024+b] = (self.img[0+b:1024+b, 0+b:1024+b] - allAvg[3]) / stds[3]
#

        
        self.imgobj.set_data(self.img)
        self.updateImage()
        #secondQuad =
        #thridQuad =
        #fourthQuad =
        
        
        mainframe = wx.FindWindowByName('MainFrame')
        expParams = mainframe.GetAllParameters()
        
        
        
        par = {'filename' : 'test'}
        
        newImg = zeros((2048, 2048))
        newImg[0:2048, 0:2048] = self.img[0+b:2048+b, 0+b:2048+b]
        dim = shape(newImg)
        
        print shape(newImg)
        ExpObj, FullImage = cartToPol.loadM(newImg, dim, expParams['BeamStopMask'], None,(25,9999), par , 1064, 1880, pixelcal = None, binsize = 2)
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        
        cartToPol.applyDataManipulations(ExpObj, expParams,mainframe.GetTreatments())
        
        plotpanel.PlotExperimentObject(ExpObj, axes = plotpanel.subplot1)
    
    def resetMaskNumber(self):
        self.nextMaskNumber = 0
        
    def createNewMaskNumber(self):
        
        storedMasks = self.plotParameters['storedMasks']
        
        if not(storedMasks):
            self.nextMaskNumber = 0
        else:
            self.nextMaskNumber = self.nextMaskNumber + 1

        return self.nextMaskNumber
    
    def showNormalScaleImage(self):
        
        a = self.fig.gca()
        a.imshow(self.img)
        self.canvas.draw()
    
    def updateClim(self):
        
        upper = self.plotParameters['UpperClim']
        lower = self.plotParameters['LowerClim']
        
        if upper != None and lower != None and self.imgobj != None:
            self.imgobj.set_clim(lower, upper)
            self.canvas.draw()
            
    def updateImage(self):
        
        self.canvas.draw()
        
    def showImage(self, imgdata, ExpObj):
        
        self.fig.gca().set_visible(True)
        
        self.ExpObj = ExpObj
        
        self.img = imgdata[0]
        imgDimentions = imgdata[1]
        imgXdim = imgDimentions[0]
        imgYdim = imgDimentions[1]
        
        self.imgDimNoBorder = imgDimentions
        
        border = self.plotParameters['imageBorder']

        z = zeros( ( imgXdim + border, imgYdim + border) )
        z[ border/2 : imgYdim + border/2, border/2 : imgXdim + border/2] = self.img
        self.img = z
        
        imgXdim = imgXdim + border
        imgYdim = imgYdim + border
        
        self.imgDim = (imgXdim, imgYdim)
        self.plotParameters['imageDimentions'] = self.imgDim
        
        self.mask = ones(self.imgDim)
        
        a = self.fig.gca()        # Get current axis from figure
        
        a.clear()
        
        if self.cursorIsOff:
            cursor = Cursor(a, useblit=True, color='red', linewidth=1 )
            self.cursorIsOff = False
     
     
        print "Preparing image for log..."
        # Save zero positions to avoid -inf at 0.0 after log!
        
        
        print "displaying image..."
        extent = (0, imgXdim, 0, imgYdim)
        
        #self.img = uint8((self.img / self.img.max())*255) 
        self.imgZeros = where(self.img==0.0) 
        
        self.imgcopy = self.img.copy()
        
        if self.plotParameters['ImgScale'] == 'linear':
            self.imgobj = a.imshow(self.img, interpolation = 'nearest', extent = extent)
        else:
            self.img[self.imgZeros] = 1
            self.imgobj = a.imshow(log(self.img), interpolation = 'nearest', extent = extent)
            self.img[self.imgZeros] = 0
        
        self.imgobj.cmap = self.plotParameters['ColorMap']
  
        print "done"
        
        a.set_title(os.path.split(ExpObj.param.get('filename'))[1])
        a.set_xlabel('x (pixels)')
        a.set_ylabel('y (pixels)')
        
        imgaxis = [0, imgXdim, 0, imgYdim]
        a.axis('image')
        
        self.plotStoredMasks()
        
        
        self.plotParameters['maxImgVal'] = self.img.max()
        self.plotParameters['minImgVal'] = self.img.min()
        
        if self.plotParameters['ClimLocked'] == False:
            clim = self.imgobj.get_clim()
            self.plotParameters['UpperClim'] = clim[1] 
            self.plotParameters['LowerClim'] = clim[0]
        else:
            clim = self.imgobj.set_clim(self.plotParameters['LowerClim'], self.plotParameters['UpperClim'])
        
        #Update figure:
        self.canvas.draw()
        
    def showHdrInfo(self):
        
        diag = HdrInfoDialog(self, self.ExpObj)
        diag.ShowModal()
        diag.Destroy()
        
    def showImageSetDialog(self):
        
        if self.imgobj != None:
            diag = ImageSettingsDialog(self, self.ExpObj, self.imgobj)
            diag.ShowModal()
            diag.Destroy()
        
    def onMotionEvent(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
           
            mouseX = int(x)
            mouseY = int(y)
            
            #noBorderX = int(x) - int((self.plotParameters['imageBorder']/2))
            #noBorderY = int(y) - int((self.plotParameters['imageBorder']/2))
            
            noBorderX = x - int((self.plotParameters['imageBorder']/2))
            noBorderY = y - int((self.plotParameters['imageBorder']/2))
            
            try:
                z = self.img[y,x]
            except (IndexError, TypeError):
                z = 0
            
            if self.GetName() != 'test':
                wx.FindWindowByName('MainFrame').SetStatusText('Pos: (' +  str(round(noBorderX,1)) + ', ' + str(round(noBorderY,1)) + ')' + '  Pixel value: ' + str(z), 1)
            else:
                wx.FindWindowByName('TestFrame').SetStatusText('Pos: (' +  str(int(noBorderX)) + ', ' + str(int(noBorderY)) + ')' + '  Pixel value: ' + str(z), 0)

            ##################################################################          
            # Plot guideline:
            ##################################################################
            a = self.fig.gca()             # Get current axis from figure
                        
            toolIsChosen = bool(self.plotParameters['currentTool'])
            plottingHasStarted = (len(self.chosenPointsX) >= 1) and toolIsChosen
            
            if plottingHasStarted and self.plottingInProgress:              
                    
                    # remove last guideline
                    if self.guideLinePlotted == True:
                          del(a.lines[-1]) 
                    #     del(a.patches[-1])
                    
                    self.drawMaskGuideline(mouseX, mouseY)
                            
                    self.guideLinePlotted = True
                    
            
            ####################################################################
            ### MOVING PATCHES AROUND
            ####################################################################
            if self.movementInProgress == True:
                self.movePatch(mouseX, mouseY)
                
    def movePatch(self, mouseX, mouseY):
        patch = self.selectedPatch
                
        if patch.get_facecolor() == 'yellow':
            
            oldPoints = self.getMaskWithId(patch.id).points
            
            x = oldPoints[0][0]
            y = oldPoints[0][1]
            
            dX = mouseX - oldPoints[0][0]
            dY = mouseY - oldPoints[0][1]
            
            if self.firstMousePos == None:        # Is reset when mouse button is released
                self.firstMousePos = (dX, dY)
            
            if isinstance(patch, Circle):
                patch.center = (x + dX - self.firstMousePos[0], y + dY - self.firstMousePos[1])
    
            elif isinstance(patch, Rectangle):            
                patch.set_x(x + dX - self.firstMousePos[0])
                patch.set_y(y + dY - self.firstMousePos[1])
                       
            elif isinstance(patch, Polygon):
                newPoints = []
                for each in oldPoints:
                    newPoints.append((each[0]+dX - self.firstMousePos[0], each[1] + dY - self.firstMousePos[1]))
                        
                newPoints.append(newPoints[0])
                patch.set_xy(newPoints)
                        
            self.canvas.draw()
        
                    
    def drawMaskGuideline(self, x, y):
        
        tool = self.plotParameters['currentTool']
        a = self.fig.gca()             # Get current axis from figure
        
        if tool == 'circle':
            radiusC = abs(x - self.chosenPointsX[-1])
#            cir = Circle( (self.chosenPointsX[-1], self.chosenPointsY[-1]), radius = radiusC, alpha = 0.5) 
#            a.add_patch(cir)

            circlePoints = bresenhamCirclePoints(radiusC, self.chosenPointsX[-1], self.chosenPointsY[-1])
            xPoints, yPoints = zip(*circlePoints)
            a.plot(xPoints, yPoints, 'r.')
                        
        if tool == 'rectangle':
            width = x - self.chosenPointsX[-1]
            height = y - self.chosenPointsY[-1]
            #rect = Rectangle( (self.chosenPointsX[-1], self.chosenPointsY[-1]), width, height, alpha = 0.5 )
            #a.add_patch(rect)
            
            xPoints = [self.chosenPointsX[-1], x, x, self.chosenPointsX[-1], self.chosenPointsX[-1]]
            yPoints = [self.chosenPointsY[-1], self.chosenPointsY[-1], y, y, self.chosenPointsY[-1]]

            a.plot(xPoints, yPoints, 'r')

        if tool == 'polygon':
            polygonPoints = []
                        
            #for i in range(0,len(self.chosenPointsX)):
            xPoint = self.chosenPointsX[-1]
            yPoint = self.chosenPointsY[-1]
                            
            polygonPoints.append( (xPoint, yPoint) )
              
            a.plot([xPoint, x], [yPoint, y], 'r')
                            
        self.canvas.draw()
        
    def drawCircle(self, points, id):
        
        a = self.fig.gca()
        
        usePatch = self.plotParameters['usePatches']
        
        radiusC = abs(points[1][0] - points[0][0])
        circlePoints = bresenhamCirclePoints(radiusC, points[0][0], points[0][1])
        xPoints, yPoints = zip(*circlePoints)
        
        if usePatch:
             cir = Circle( (points[0][0], points[0][1]), radius = radiusC, alpha = 0.5, picker = True ) 
             a.add_patch(cir)
             
             cir.id = id              # Im creating a new parameter called Id to distingush them!
             cir.selected = 0
             self.plottedPatches.append(cir)
             
             #a.plot(xPoints, yPoints, 'r.')
        else:
            radiusC = abs(points[1][0] - points[0][0])
            circlePoints = bresenhamCirclePoints(radiusC, points[0][0], points[0][1])
            xPoints, yPoints = zip(*circlePoints)
            a.plot(xPoints, yPoints, 'r.')
        
        
    def drawRectangle(self, points, id):
        
        a = self.fig.gca()
        
        xStart = points[0][0]
        yStart = points[0][1]
        
        xEnd = points[1][0]
        yEnd = points[1][1]

        usePatch = self.plotParameters['usePatches']

        if usePatch:
            width = xEnd - xStart
            height = yEnd - yStart
            rect = Rectangle( (xStart, yStart), width, height, alpha = 0.5, picker = True )
            a.add_patch(rect)
            
            rect.id = id
            rect.selected = 0
            self.plottedPatches.append(rect)
        else:
            xPoints = [xStart, xEnd, xEnd, xStart, xStart]
            yPoints = [yStart, yStart, yEnd, yEnd, yStart]
            
            a.plot(xPoints, yPoints, 'r')
        
    def drawPolygon(self, points, id):
        
        a = self.fig.gca()
        
        usePatch = self.plotParameters['usePatches']
        
        if usePatch:
            poly = Polygon( points, alpha = 0.5, picker = True )
            a.add_patch(poly)
            
            poly.id = id
            poly.selected = 0
            self.plottedPatches.append(poly)
            
        else:
            xPoints, yPoints = zip(*points)
        
            xPoints = list(xPoints)
            yPoints = list(yPoints)
        
            xPoints.append(xPoints[0])
            yPoints.append(yPoints[0])
            
            a.plot(xPoints, yPoints, 'r')
            
    def patchToggleSelection(self):
        
        if self.toggleSelect != None:

            if self.toggleSelect.selected == 1:
                
                self.toggleSelect.set_facecolor('yellow')
                    
                id = self.toggleSelect.id
                #Paint the other masks blue
                for each in self.plottedPatches:
                    if id != each.id:
                        each.set_facecolor('blue')
                        each.selected = 0
                    
                self.toggleSelect = None
                self.canvas.draw()

            else:
                pass
                        
        else:
            for each in self.plottedPatches:
                each.set_facecolor('blue')
                each.selected = 0
            
            self.selectedPatch = None
            self.toggleSelect = None
            self.canvas.draw()
        
    def insertNewCoordsIntoMask(self):
        
        patch = self.selectedPatch
        mask = self.getMaskWithId(self.selectedPatch.id)
                        
        if isinstance(patch, Circle):
            newCenter = patch.center
            #first point is center, next point is first on circle perferie
            mask.points = [newCenter, (newCenter[0]+mask.radius, newCenter[1])]
                    
        elif isinstance(patch, Rectangle):
                        
            x = patch.get_x()
            y = patch.get_y()
            
            dx = x - mask.points[0][0]
            dy = y - mask.points[0][1]
            
            mask.points = [(x, y),(mask.points[1][0] + dx, mask.points[1][1] + dy)]
                                
        elif isinstance(patch, Polygon):
            mask.points = patch.get_xy()[:-1]
            
            
    def onMouseReleaseEvent(self, event):
        
        if event.button == 1:
                
            if self.movementInProgress == True:
                self.insertNewCoordsIntoMask()
                self.movementInProgress = False
                self.firstMousePos = None

            self.patchToggleSelection()
            
    def onMouseButtonPressEvent(self, event):
        
        xd, yd = event.xdata, event.ydata
        
        if event.button == 1:    # 1 = Left button
            self.onLeftMouseButton(xd, yd, event)
                  
        if event.button == 3:    # 3 = Right button
            self.onRightMouseButton(xd, yd)
            
    def onLeftMouseButton(self, xd, yd, event):
        
        a = self.fig.gca()        # Get current axis from figure
    
        tool = self.plotParameters['currentTool']
        storedMasks = self.plotParameters['storedMasks']
        
        if tool:
                ###########################################################
                if tool == 'polygon':
                    if self.plottingInProgress:
            
                        if event.inaxes is not None:
                        
                            if len(self.chosenPointsX) > 0:
                                newLineX = [self.chosenPointsX[-1], round(xd)]
                                newLineY = [self.chosenPointsY[-1], round(yd)]
                    
                            self.chosenPointsX.append(round(xd))
                            self.chosenPointsY.append(round(yd))

                            if len(self.chosenPointsX) >= 2:
                                a.plot(newLineX,newLineY,'r')
                                self.canvas.draw()
                    else:
                        self.chosenPointsX.append(round(xd))
                        self.chosenPointsY.append(round(yd))
                        self.plottingInProgress = True

                #############################################################
                if tool == 'circle' or tool == 'rectangle':
                    self.chosenPointsX.append(round(xd))
                    self.chosenPointsY.append(round(yd))
                    self.plottingInProgress = True

                    if len(self.chosenPointsX) == 2:
                        
                        if tool == 'circle':
                            storedMasks.append( CircleMask( [(self.chosenPointsX[0], self.chosenPointsY[0]),
                                                                  (self.chosenPointsX[1], self.chosenPointsY[1])],
                                                                   self.createNewMaskNumber(), self.imgDim ))
                        elif tool == 'rectangle':
                            storedMasks.append( RectangleMask( [ (self.chosenPointsX[0], self.chosenPointsY[0]),
                                                                      (self.chosenPointsX[1], self.chosenPointsY[1])],
                                                                       self.createNewMaskNumber(), self.imgDim ))
                                        
                        self.plottingInProgress = False
                        
                        self.stopMaskCreation()
                        self.toolbar.untoggleAllToolButtons()
                
                #############################################################
                if tool == 'agbecent':
                    self.agbeSelectedPoints.append( (xd, yd) )
                    
                    cir = Circle( (int(xd), int(yd)), radius = 3, alpha = 1, facecolor = 'yellow', edgecolor = 'yellow')
                    a.add_patch(cir)
                    self.canvas.draw()
    
    def onRightMouseButton(self, xd, yd):
        
        tool = self.plotParameters['currentTool']
        storedMasks = self.plotParameters['storedMasks']
        mainframe = wx.FindWindowByName('MainFrame')
        
        if tool:
                
            if tool == 'polygon':
                
                    if self.plottingInProgress == True:
                        self.plottingInProgress = False
                
                    if len(self.chosenPointsX) > 2:
                        #self.chosenPointsX.append(self.chosenPointsX[0])
                        #self.chosenPointsY.append(self.chosenPointsY[0])
                    
                        points = []
                        for i in range(0, len(self.chosenPointsX)):
                            points.append( (self.chosenPointsX[i], self.chosenPointsY[i]) )
                   
                        storedMasks.append( PolygonMask(points, self.createNewMaskNumber(), self.imgDim) )
                    
                    self.stopMaskCreation()
                
            ######################################################
            if tool == 'circle' or tool == 'rectangle':
                
                    if len(self.chosenPointsX) > 1:
                        storedMasks.append( (self.chosenPointsX, self.chosenPointsY) )
                        self.plottingInProgress = False
            
                    self.stopMaskCreation()
                
            if tool == 'agbecent':
                    if len(self.agbeSelectedPoints) > 2:
                        self.endAgBeCalibration()
                    else:
                        mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
                        mainframe.plotNB.SetSelection(2)
                        
                        answer = wx.MessageBox('You need atleast 3 points to calculate the center!', 'Not enough points!', wx.OK | wx.CANCEL)
                        
                        if answer == wx.CANCEL:
                            self.agbeSelectedPoints = []
                            self.plotStoredMasks()
                            mainframe.plotNB.SetSelection(1)# Fixing a focus bug under Linux in Matplotlib! Very strange!
                            mainframe.plotNB.SetSelection(2)
                        else:
                            mainframe.plotNB.SetSelection(1)# Fixing a focus bug under Linux in Matplotlib! Very strange!
                            mainframe.plotNB.SetSelection(2)
                            return
                    
            self.toolbar.untoggleAllToolButtons()
    
    def endAgBeCalibration(self):
        
        a = self.fig.gca()
        
        x, r = self.calcCenterCoords()  # x = (x_c,y_c)
        
        cir = Circle( x, radius = r, alpha = 1, fill = False, linestyle = 'dashed', linewidth = 1.5, edgecolor = 'red') 
        a.add_patch(cir)
        txt1 = a.text(x[0]-10, x[1]-r-10, 'q = 0.1076', size = 'large')
        
        cir = Circle( x, radius = 2*r, alpha = 1, fill = False, linestyle = 'dashed', linewidth = 1.5, edgecolor = 'red') 
        a.add_patch(cir)
        txt2 = a.text(x[0]-10, x[1]-2*r-10, 'q = 0.2152', size = 'large')
        
        cir = Circle( x, radius = 3*r, alpha = 1, fill = False, linestyle = 'dashed', edgecolor = 'red') 
        a.add_patch(cir)
        txt3 = a.text(x[0]-10, x[1]-3*r-10, 'q = 0.3229', size = 'large')
        
        cir = Circle( x, radius = 4*r, alpha = 1, fill = False, linestyle = 'dashed', edgecolor = 'red') 
        a.add_patch(cir)
        txt4 = a.text(x[0]-10, x[1]-4*r-10, 'q = 0.4305', size = 'large')
        
        cir = Circle( x, radius = 3, alpha = 1, facecolor = 'red', edgecolor = 'red')
        a.add_patch(cir)
        
        #txt = Text(x[0], x[1]-r, text='TEST')
    
        self.canvas.draw()
        
        border = int(self.plotParameters['imageBorder'] / 2)
        mainframe = wx.FindWindowByName('MainFrame')
        mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
        mainframe.plotNB.SetSelection(2)
        
        answer = wx.MessageBox('The center found was: x = ' + str(round(x[0]-border,2)) + ', y = ' + str(round(x[1]-border,2)) +
                               '\n\nDoes the calculated center look ok?', 'Is Everything Good?', wx.YES_NO | wx.ICON_QUESTION)
        
        mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
        mainframe.plotNB.SetSelection(2)
                        
        if answer == wx.YES:
             options = wx.FindWindowByName('MainFrame')
                            
             border = int(self.plotParameters['imageBorder'] / 2)
                            
             xlen = self.imgDimNoBorder[0]
             ylen = self.imgDimNoBorder[1]
                            
             x_c = x[0] - border
             y_c = x[1] - border
                            
             if options:
                   options.ChangeParameter('Xcenter', x[0]-border)
                   options.ChangeParameter('Ycenter', x[1]-border)
                   options.ChangeParameter('PixelCalX', int(round(r)))
                   options.ChangeParameter('PixelCalY', int(round(r)))
                   
                   options.ChangeParameter('ReferenceQ', 0.1076)
                   options.ChangeParameter('ReferenceDistPixel', int(round(r)))
                   
                   #if self.detectorPixelSize:
                   #    options.ChangeParameter('DetectorPixelSize', self.detectorPixelSize)
                   
                   wavelength, pixelsize = self.checkHeaderForParameters()
                   
                   print wavelength, pixelsize
                   
                   if wavelength and pixelsize:
                       
                       SD_Distance = cartToPol.calcAgBeSampleDetectorDist(int(round(r)), wavelength, pixelsize / 1000)
                       
                       answer = wx.MessageBox('RAW found the following wavelength and pixelsize in the image header:\n\n' +
                                              'Wavelength : ' + str(wavelength) + ' A' + '\nPixel size : ' + str(pixelsize) + ' um' +
                                              '\n\nCorresponding to a sample-detector distance of ' + str(SD_Distance) + ' mm.' +
                                              '\n\nDo you want to use these values for the calibration?', 'Use header values?', wx.YES_NO | wx.ICON_QUESTION)
                       
                       if answer == wx.YES:
                           options.ChangeParameter('WaveLength', wavelength)
                           options.ChangeParameter('DetectorPixelSize', pixelsize)
                           options.ChangeParameter('SampleDistance', SD_Distance)
                           options.ChangeParameter('Calibrate', True)
                    
                                                 
                   if options.GetParameter('WaveLength') != 0 and options.GetParameter('DetectorPixelSize') != 0:
                       SD_Distance = cartToPol.calcAgBeSampleDetectorDist(int(round(r)),
                                                                           options.GetParameter('WaveLength'),
                                                                           options.GetParameter('DetectorPixelSize') / 1000)
                       options.ChangeParameter('SampleDistance', SD_Distance)
                
                   mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
                   mainframe.plotNB.SetSelection(2)                                   
                   wx.MessageBox('Center and AgBe Q calibration parameters has been saved!', 'Parameters Saved', wx.OK)
                   mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
                   mainframe.plotNB.SetSelection(2)
                   
             else: 
                   mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
                   mainframe.plotNB.SetSelection(2)
                   wx.MessageBox('Option parameters not found (Debug mode?)', 'Parameters Not Saved', wx.OK)
                   mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
                   mainframe.plotNB.SetSelection(2)
                        
             self.clearPatches()
             self.plotStoredMasks()
        
        else:
             self.clearPatches()
             self.plotStoredMasks()
    
        a.texts.remove(txt1)
        a.texts.remove(txt2)
        a.texts.remove(txt3)
        a.texts.remove(txt4)
        
    def checkHeaderForParameters(self):
        
        wavelength = None
        pixelsize = None
        
        if self.ExpObj.param.has_key('WAVELENGTH'):               
            try:
                wavelength = float(self.ExpObj.param['WAVELENGTH']) 
            except:
                wavelength = None
                
        if self.ExpObj.param.has_key('PIXEL_SIZE'): 
            try:
                pixelsize = float(self.ExpObj.param['PIXEL_SIZE']) * 1000
            except:
                pixelsize = None
                
        return wavelength, pixelsize
        
    def stopMaskCreation(self):    
        
        self.clearCurrentTool()
        self.chosenPointsX = []
        self.chosenPointsY = []
                
        self.plotStoredMasks()
        self.guideLinePlotted = False
        
        mainframe = wx.FindWindowByName('MainFrame')
        
        if mainframe != None:
            mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
            mainframe.plotNB.SetSelection(2)
        
                
    def plotStoredMasks(self):
        
        a = self.fig.gca()        # Get current axis from figure
        storedMasks = self.plotParameters['storedMasks']
        
        self.plottedPatches = []
        
        if a.lines:
            del(a.lines[:])     # delete plotted masks
        if a.patches:
            del(a.patches[:])
        
        for each in storedMasks:
            id = wx.NewId()
            each.maskID = id
            
            if each.type == 'circle':
                self.drawCircle(each.getPoints(), id)#each.maskID)
                
            elif each.type == 'rectangle':
                self.drawRectangle(each.getPoints(), id)#each.maskID)
                
            elif each.type == 'polygon':
                self.drawPolygon(each.getPoints(), id)#each.maskID)
                
            else:
                print "Huh??? this should not happen!"
                x = each[0]
                y = each[1]
                a.plot(x, y, 'r')
            
        self.canvas.draw()
        
    def plotMasked(self, each):

        self.img[where(self.img == 0.0)] = 1
        a = self.fig.gca()
        a.clear()
        
        print "displaying image..."
        extent = (0, self.imgDim[0], 0, self.imgDim[1])
        a.imshow(log(self.img), cmap = matplotlib.cm.gray, interpolation = 'nearest', extent = extent)
        #self.drawPolygon(each.getPoints())
        a.axis('image')
        ##self.canvas.draw()

    def GetToolBar(self):
        # You will need to override GetToolBar if you are using an 
        # unmanaged toolbar in your frame
        return self.toolbar
    
    def SetColor(self, rgbtuple):
        """ Set figure and canvas colours to be the same """
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
       
        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))
        
    def setTool(self, tool):
        self.plotParameters['currentTool'] = tool
        print "Toolset: ", tool
        
    def getTool(self):
        return self.plotParameters['currentTool']
        
    def showCreateMaskDialog(self):
        
        msgdlg = wx.MessageDialog(self, 'Creating Mask, Yeeehaaaw!', 'Creating mask...', wx.OK | wx.ICON_ERROR)
        msgdlg.ShowModal()
        msgdlg.Destroy()
        #self.createFinalMask()
        #self.showMask()
        
    def createFinalMask(self):
    
        finalMask = ones(self.imgDim)
        maskOnImage = self.img
        
        storedMasks = self.plotParameters['storedMasks']
        
        for each in storedMasks:
            fillPoints = each.getFillPoints()
                
            for eachp in fillPoints:
                finalMask[eachp] = 0
                maskOnImage[eachp] = 0
        
        self.plotParameters['finalMask'] = finalMask
        
        return finalMask, maskOnImage
    
    def showMask(self):
        
        mask, maskOnImage = self.createFinalMask()
        
        #Remove the helping border around the image
        border = self.plotParameters['imageBorder']
        finalMask = mask[ border/2 : self.imgDim[1] - border/2, border/2 : self.imgDim[0] - border/2]
        
        a = self.fig.gca()
        a.clear()
        
        maskOnImage[where(maskOnImage == 0.0)] = 1
        
        print "displaying image..."
        extent = (0, self.imgDim[0], 0, self.imgDim[1])
        a.imshow(log(maskOnImage), cmap = matplotlib.cm.gray, interpolation = 'nearest', extent = extent)
        a.axis('image')
        
        self.canvas.draw()
       

    def onSaveMask(self):
        
        
        if self.plotParameters['storedMasks'] != []:
        
            #self.showCreateMaskDialog()
        
            file = self._CreateFileDialog(wx.SAVE)
             
            self.plotParameters['finalMask'] = []
        
            if file:
                if file[-3:] != 'msk':
                    file = file + '.msk'
                    
                FileObj = open(file, 'w')
                cPickle.dump(self.plotParameters, FileObj)
                FileObj.close()
            
                answer = wx.MessageBox('Do you want set this mask as the current "Beam Stop" mask?', 'Use as beamstop mask?', wx.YES_NO | wx.ICON_QUESTION)
        
                if answer == wx.NO:
                    answer = wx.MessageBox('Do you want set this mask as the current "Readout noise" mask?', 'Use as readout noise mask?', wx.YES_NO | wx.ICON_QUESTION)
                
                    if answer == wx.YES:
                        LoadReadoutNoiseMask(file)
                else:
                    LoadBeamStopMask(file)         
        else:
             wx.MessageBox('You need to create a mask before you can save it!', 'No mask to save!', wx.OK)       
        
        
    def onLoadMask(self):
        
        file = self._CreateFileDialog(wx.OPEN)
        
        if file:
            FileObj = open(file, 'r')
            
            try:
                loadedParams = cPickle.load(FileObj)
            except Exception:
                print Exception
            
            FileObj.close()
        
            self.plotParameters['storedMasks'] = loadedParams['storedMasks']
            self.plotStoredMasks()
            
            answer = wx.MessageBox('Do you want set this mask as the current "Beam Stop" mask?', 'Use as beamstop mask?', wx.YES_NO | wx.ICON_QUESTION)
        
            if answer == wx.NO:
                answer = wx.MessageBox('Do you want set this mask as the current "Readout noise" mask?', 'Use as readout noise mask?', wx.YES_NO | wx.ICON_QUESTION)
                
                if answer == wx.YES:
                    options = wx.FindWindowByName('OptionsPage')
                        
                    if options:
                        options.LoadReadoutNoiseMask(file)
            else:
                options = wx.FindWindowByName('OptionsPage')
                    
                if options:
                    options.LoadBeamStopMask(file)
                    
    def clearFigure(self):
        self.fig.gca().set_visible(False)
        self.canvas.draw()
            
    def onClear(self):
        
        self.plotParameters['storedMasks'] = []
        
        a = self.fig.gca()
        
        if a.lines:
            del(a.lines[:])     # delete plotted masks
        if a.patches:
            del(a.patches[:])
        
        self.canvas.draw()
        
    def clearPatches(self):
        a = self.fig.gca()
         
        if a.lines:
            del(a.lines[:])     # delete plotted masks
        if a.patches:
            del(a.patches[:])
            
        self.canvas.draw()
        
    def finetuneAgbePoints(self, x_c, y_c, x1, y1, r):
        a = self.fig.gca()
      
        points, xpoints, ypoints = bresenhamLinePoints(x_c, y_c, x1, y1)
        
        #try:
        line = self.img[ypoints, xpoints]
        #except IndexError:
        #    wx.MessageBox("Could not find a good fit, please try again.", 'Info')
            
                
        cutlen = int(len(line)/2)
        line2 = line[cutlen:]
        
        idx = line2.argmax()
        
        limit_percent = 0.2
        limitidx = int((limit_percent*r)/2)
        
        gaussx = xpoints[cutlen + idx - limitidx : cutlen + idx + limitidx]
        gaussy = ypoints[cutlen + idx - limitidx : cutlen + idx + limitidx]
        
        gaussline = self.img[gaussy, gaussx]
        

        fitfunc = lambda p, x: p[0] * exp(-(x-p[1])**2/(2.0*p[2]**2))
        
        # Cauchy
        #fitfunc = lambda p, x: p[0] * (1/(1+((x-p[1])/p[2])**2 ))
        errfunc = lambda p, x, y: fitfunc(p,x)-y
      
        # guess some fit parameters
        p0 = [max(gaussline), mean(range(0,len(gaussline))), std(range(0,len(gaussline)))]
        x = range(0, len(gaussline))
         
        # guess for cauchy distribution
        #p0 = [max(gaussline), median(x), 1/(max(gaussline)*pi)]
    
        # fit a gaussian
        
        p1, success = optimize.leastsq(errfunc, p0, args=(x, gaussline))
        
        #self.subplot2 = self.fig.add_subplot(211)
        #self.subplot2.plot(line2)
        #self.canvas.draw()
        
        idx = idx + cutlen - limitidx + (int(p1[1]))
        
        try:
            return (xpoints[idx] + (p1[1] % 1), ypoints[idx]+ (p1[1] % 1))
        
        except IndexError:
            return False
            #return (xpoints[idx] + (p1[1] % 1), ypoints[idx]+ (p1[1] % 1))
        
    def calcCenterCoords(self, tune = True):
        ''' Determine center from coordinates on circle peferie. 
            
            Article:
              I.D.Coope,
              "Circle Fitting by Linear and Nonlinear Least Squares",
              Journal of Optimization Theory and Applications vol 76, 2, Feb 1993
        '''
        
        numOfPoints = len(self.agbeSelectedPoints)
        
        B = []
        d = []
        
        for each in self.agbeSelectedPoints:
            x = each[0]
            y = each[1]
            
            B.append(x)                   # Build B matrix as vector
            B.append(y)
            B.append(1)
            
            d.append(x**2 + y**2)
        
        B = matrix(B)                     # Convert to numpy matrix
        d = matrix(d)
        
        B = B.reshape((numOfPoints, 3))   # Convert 1D vector to matrix
        d = d.reshape((numOfPoints, 1))
        
        Y = linalg.inv(B.T*B) * B.T * d   # Solve linear system of equations
        
        x_c = Y[0] / 2                    # Get x and r from transformation variables
        y_c = Y[1] / 2
        r = sqrt(Y[2] + x_c**2 + y_c**2)
        
        x_c = x_c.item()             
        y_c = y_c.item()
        r = r.item()
        finetune_success = True
  
        if tune:
            newPoints = []
            for each in self.agbeSelectedPoints:
                x = each[0]
                y = each[1]

                optimPoint = self.finetuneAgbePoints(int(x_c), int(y_c), int(x), int(y), r)
                
                if optimPoint == False:
                    optimPoint = (x,y)
                    finetune_success = False
                
                newPoints.append(optimPoint)
         
            self.agbeSelectedPoints = newPoints
            xy, r  = self.calcCenterCoords(tune = False)
            x_c = xy[0]
            y_c = xy[1]
            print 'x_cent: ', x_c-25
            print 'y_cent: ', y_c-25
            print 'radius: ', r
            
            mainframe = wx.FindWindowByName('MainFrame')
      
        if finetune_success == False:
            mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
            mainframe.plotNB.SetSelection(2)
            wx.MessageBox('Remember to set the points "outside" the AgBe ring, a circle will then be fitted to the first found ring behind them.', 'Center search failed', wx.OK | wx.ICON_ERROR)
            mainframe.plotNB.SetSelection(1)    # Fixing a focus bug under Linux in Matplotlib! Very strange!
            mainframe.plotNB.SetSelection(2)
        
        self.agbeSelectedPoints = []
        
        return ( (x_c, y_c), r )
        
            
    def _CreateFileDialog(self, mode):
        
        file = None
        
        if mode == wx.OPEN:
            filters = 'Mask files (*.msk)|*.msk|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters)
        if mode == wx.SAVE:
            filters = 'Mask files (*.msk)|*.msk'
            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters)        
        
        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            
        # Destroy the dialog
        dialog.Destroy()
        
        return file
    
##########################################################################   
#### Mask Creation when masking.py is imported
##########################################################################
def loadMask(filename, varname = 'mask'):
    ''' Loads a mask form a matlab .mat file. Name of the mask variable in matlab needs to be "mask" for it to work
        otherwise the variable name can be specified in varname.
        
        UPDATE: now also takes RAW mask files
        GUI is true if the function is used in a GUI (displays a progress bar)
    '''
    print filename
    if filename[-3:] == 'msk':
        
        FileObj = open(filename, 'r')            
        maskPlotParameters = cPickle.load(FileObj)
        FileObj.close()    
        
        i=0
        for each in maskPlotParameters['storedMasks']:
            each.maskID = i
            i = i + 1
        
        return createMaskFromRAWFormat(maskPlotParameters), maskPlotParameters
    

    else:    #Try matlab format (from SAXSGUI)
        
        matlab_mask_dict = io.loadmat(filename)
        return matlab_mask_dict[varname]

def createMaskFromRAWFormat(maskPlotParameters):
    
    border = maskPlotParameters['imageBorder']
    imageDimentions = maskPlotParameters['imageDimentions']
    storedMasks = maskPlotParameters['storedMasks']
    
    mask = ones(imageDimentions)
    
    for each in storedMasks:
        fillPoints = each.getFillPoints()
                
        for eachp in fillPoints:
            mask[eachp] = 0

    # Raw masks are created with a border to make edgemasking easier, this will remove the border:
    finalMask = mask[ border/2 : imageDimentions[1] - border/2, border/2 : imageDimentions[0] - border/2]
    
    
    return finalMask

##########################################################################
#### Mask classes:
##########################################################################

class CircleMask:
    def __init__(self, points, id, imgDim):
        
        self.imgDim = imgDim            # need image Dimentions to get the correct fill points
        self.maskID = id
        self.type = 'circle'
        self.points = points
        self.radius = abs(points[1][0] - points[0][0])
        self.startPoint = points[0]
        self.borderPixels = []
        self.filledPixels = []
        
    def getPoints(self):
        return self.points
    
    def getFillPoints(self):
        ''' Really Clumsy! Can be optimized alot! triplicates the points in the middle!'''
        
        radiusC = abs(self.points[1][0] - self.points[0][0])
        
        #P = bresenhamCirclePoints(radiusC, self.imgDim[0] - self.points[0][1], self.points[0][0])
        P = bresenhamCirclePoints(radiusC, self.points[0][1], self.points[0][0])
        
        fillPoints = []
        
        for i in range(0, int(len(P)/8) ):
            Pp = P[i*8 : i*8 + 8]
            
            q_ud1 = ( Pp[0][0], range( int(Pp[1][1]), int(Pp[0][1]+1)) )
            q_ud2 = ( Pp[2][0], range( int(Pp[3][1]), int(Pp[2][1]+1)) )
                     
            q_lr1 = ( Pp[4][1], range( int(Pp[6][0]), int(Pp[4][0]+1)) )
            q_lr2 = ( Pp[5][1], range( int(Pp[7][0]), int(Pp[5][0]+1)) )
        
        
            for i in range(0, len(q_ud1[1])):
                fillPoints.append( (q_ud1[0], q_ud1[1][i]) )
                fillPoints.append( (q_ud2[0], q_ud2[1][i]) )
                fillPoints.append( (q_lr1[1][i], q_lr1[0]) )
                fillPoints.append( (q_lr2[1][i], q_lr2[0]) )
       
        return fillPoints
    
        
class RectangleMask:
    
    def __init__(self, points, id, imgDim):
        
        self.maskID = id
        
        self.imgDim = imgDim
        self.type = 'rectangle'
        self.points = points
        self.startPoint = points[0]
        self.endPoint = points[1]
        self.filledPixels = []
        self.patch = []
    
    def getPoints(self):
        return self.points
    
    def getFillPoints(self):
        
        self.startPoint = self.points[0]
        self.endPoint = self.points[1]
        
        '''  startPoint and endPoint: [(x1,y1) , (x2,y2)]  '''
    
        #startPointX = self.imgDim[0] - self.startPoint[1]
        startPointX = int(self.startPoint[1])
        
        startPointY = int(self.startPoint[0])
    
        #endPointX = self.imgDim[0] - self.endPoint[1]
        
        endPointX = int(self.endPoint[1])
        endPointY = int(self.endPoint[0])
    
        fillPoints = []
        
        if startPointX > endPointX:
            
            if startPointY > endPointY:

                for c in range(endPointY, startPointY + 1):                    
                    for i in range(endPointX, startPointX + 1):
                        fillPoints.append( (i, c) )
            else:
                for c in range(startPointY, endPointY + 1):                    
                    for i in range(endPointX, startPointX + 1):
                        fillPoints.append( (i, c) )
        
        else:
        
            if startPointY > endPointY:

                for c in range(endPointY, startPointY + 1):                    
                    for i in range(startPointX, endPointX + 1):
                        fillPoints.append( (i, c) )
            else:
                for c in range(startPointY, endPointY + 1):                    
                    for i in range(startPointX, endPointX + 1):
                        fillPoints.append( (i, c) )
        
        return fillPoints
    

class PolygonMask:
    
    def __init__(self, points, id, imageDim):
        
        self.xDim = imageDim[0]
        self.yDim = imageDim[1]
        self.maskID = id
        self.points = points
        self.type = 'polygon'
        self.linePoints = []
        self.filledPixels = []
        
    #    self.patch = Polygon( points, alpha = 0.5, picker = True )
        
    def getPoints(self):
        return self.points
    
    def getFillPoints(self):
        
        print "Making grits!!"
        properFormattedPoints = []
        
        for each in self.points:
            properFormattedPoints.append(list(each))
        
        properFormattedPoints = array(properFormattedPoints)
        
        pb = polymask.Polygeom(properFormattedPoints)
        grid = mgrid[0:self.xDim,0:self.yDim].reshape(2,-1).swapaxes(0,1)
        inside = pb.inside(grid)      
        
        p = where(inside==True)
        
        coords = polymask.getCoords(p, (self.xDim, self.yDim))
        print "done!"
        
        return coords
    
def bresenhamLinePoints2(x0,y0,x1,y1):
    
    
    '''
    void line(int x0, int y0, int x1, int y1) 
    {
    int Dx = x1 - x0; 
    int Dy = y1 - y0;
    int steep = (abs(Dy) >= abs(Dx));
   
   if (steep) 
   {
       SWAP(x0, y0);
       SWAP(x1, y1);
       
       // recompute Dx, Dy after swap
       Dx = x1 - x0;
       Dy = y1 - y0;
   }
   
   int xstep = 1;
   
   if (Dx < 0) 
   {
       xstep = -1;
       Dx = -Dx;
   }
   
   int ystep = 1;
   
   if (Dy < 0) 
   {
       ystep = -1;        
       Dy = -Dy; 
   }
   
   int TwoDy = 2*Dy; 
   int TwoDyTwoDx = TwoDy - 2*Dx;         // 2*Dy - 2*Dx
   int E = TwoDy - Dx;                    // 2*Dy - Dx
   int y = y0;
   int xDraw, yDraw;
   
   for (int x = x0; x != x1; x += xstep) 
   {        
       if (steep) 
       {            
           xDraw = y;
           yDraw = x;
       } 
       else 
       {            
           xDraw = x;
           yDraw = y;
       }
   
       // plot
       plot(xDraw, yDraw);
       
       // next
       if (E > 0) {
           E += TwoDyTwoDx;              //E += 2*Dy - 2*Dx;
           y = y + ystep;
       } else {
           E += TwoDy;                   //E += 2*Dy;
       }
   }
}
'''

def bresenhamLinePoints(x0, y0, x1, y1):
    
    pointList = []
    pointXList = []
    pointYList = []
    
    Dx = x1 - x0; 
    Dy = y1 - y0;

    #Steep
    steep = abs(Dy) > abs(Dx)
    if steep:
        x0, y0 = y0, x0  
        x1, y1 = y1, x1
        
        Dx = x1 - x0
        Dy = y1 - y0
  
    xstep = 1
    
    if Dx < 0:
        xstep = -1
        Dx = -Dx
       
        xrange = range(x1, x0+1)
        xrange.reverse()
    else:
        xrange = range(x0,x1+1)
   
    ystep = 1
    
    if Dy < 0:
       ystep = -1       
       Dy = -Dy 

    TwoDy = 2*Dy
    TwoDyTwoDx = TwoDy - 2*Dx        # 2*Dy - 2*Dx
    E = TwoDy - Dx                   # //2*Dy - Dx
    y = y0
 
    for x in xrange:     #int x = x0; x != x1; x += xstep)
                                                                                                                     
       if steep:
           xDraw = y
           yDraw = x
       else:       
           xDraw = x
           yDraw = y
       
       #plot(xDraw, yDraw)
       pointList.append((xDraw,yDraw))
       pointXList.append(xDraw)
       pointYList.append(yDraw)
     
       if E > 0:
           E = E + TwoDyTwoDx             #//E += 2*Dy - 2*Dx;
           y = y + ystep
       else:
           E = E + TwoDy                 #//E += 2*Dy;
       
    return pointList, pointXList, pointYList

###############################
#  Bresenham Circle Algorithm
###############################

def bresenhamCirclePoints(radius, xOffset = 0, yOffset = 0):
    ''' Uses the Bresenham circle algorithm for determining the points
     of a circle with a certain radius '''
     
    x = 0
    y = radius
    
    switch = 3 - (2 * radius)
    points = []
    while x <= y:
        points.extend([(x + xOffset, y + yOffset),(x + xOffset,-y + yOffset),
                       (-x + xOffset, y + yOffset),(-x + xOffset,-y + yOffset),
                       (y + xOffset, x + yOffset),(y + xOffset,-x + yOffset),
                       (-y + xOffset, x + yOffset),(-y + xOffset, -x + yOffset)])
        if switch < 0:
            switch = switch + (4 * x) + 6
        else:
            switch = switch + (4 * (x - y)) + 10
            y = y - 1
        x = x + 1
        
    return points

def circleFill(P):
        ''' finds alle the points that fills the circle '''
    
        for i in range(0,len(P)/8):
            Pp = P[i*8 : i*8 + 8]
            
            q_ud = ( Pp[0][0], range(Pp[1][1], Pp[0][1]+1))
            q_lr = ( Pp[4][1], range(Pp[6][0], Pp[4][0]+1))
            print Pp
            #print q_ud
            print q_ud
            print " "
        
        
        fillPoints = []
        for i in range (0, len(q_ud[1])):
            fillPoints.append( (q_ud[0], q_ud[1][i]) )
            fillPoints.append( (q_lr[0], q_lr[1][i]) )
       
        return fillPoints
    

#---- #### MASK LOADING ####

def setBrightnessAndContrastUINT8():
    brightness = Gbrightness - 100;
    contrast = Gcontrast - 100;
    max_value = 0;

    # The algorithm is by Werner D. Streidt
    # (http://visca.com/ffactory/archives/5-99/msg00021.html)
    if( contrast > 0 ):
        delta = 127.*contrast/100;
        a = 255./(255. - delta*2);
        b = a*(brightness - delta);
    else:
        delta = -128.*contrast/100;
        a = (256.-delta*2)/255.;
        b = a*brightness + delta;

    for i in range(256):
        v = cvRound(a*i + b);
        if( v < 0 ):
            v = 0;
        if( v > 255 ):
            v = 255;
        lut[i] = v;




loadMaskQueue = Queue.Queue(0)
maskLoadingThread = None

class LoadMaskThread(threading.Thread):
    
    def __init__(self):
        
        threading.Thread.__init__(self)
        
        #self._masktype = masktype
        #self._mask_fullpath = mask_fullpath
        #self._pgthread = pgthread
        #self._maskInExpParams = maskInExpParams
        #self.expParams = expParams
        #self.type = type
        
    def run(self):
        
        while True:
        
            self._mask_fullpath, self._masktype, self.expParams, self.type = loadMaskQueue.get()
        
            mainframe = wx.FindWindowByName('MainFrame')
        
            #self._pgthread.SetStatus('Loading Mask...')
            wx.CallAfter(mainframe.SetStatusText, 'Loading mask...')    
        
            if self.type == None:
                if self.expParams['BeamStopMaskParams'] != None:
                    self.expParams['BeamStopMask'] = createMaskFromRAWFormat(self.expParams['BeamStopMaskParams'])
            
                if self.expParams['ReadOutNoiseMaskParams'] != None:
                    self.expParams['ReadOutNoiseMask'] = createMaskFromRAWFormat(self.expParams['ReadOutNoiseMaskParams'])
            else:
                if self._masktype == 'readout':
                    self.expParams['ReadOutNoiseMask'], self.expParams['ReadOutNoiseMaskParams'] = loadMask(self._mask_fullpath)
                    self.expParams['ReadOutNoiseMaskFilename'] = os.path.split(self._mask_fullpath)[1]
                elif self._masktype == 'beamstop':
                    self.expParams['BeamStopMask'], self.expParams['BeamStopMaskParams'] = loadMask(self._mask_fullpath)
                    self.expParams['BeamStopMaskFilename'] = os.path.split(self._mask_fullpath)[1]    
        
            wx.CallAfter(mainframe.SetStatusText, 'Loading mask... Done!')
            
            loadMaskQueue.task_done()    
        
        #self._pgthread.SetStatus('Done')
        #self._pgthread.stop() 
    
def LoadBeamStopMask(mask_fullpath):
    
    global maskLoadingThread
    #global expParams
    expParams = wx.FindWindowByName('MainFrame').GetAllParameters()
        #mask_filename = os.path.split(mask_fullpath)[1]
        
    if mask_fullpath:
            #filename_label = wx.FindWindowById(self.maskIds['BeamStopMask'])
            #filename_label.SetLabel(mask_filename)
            
            #progressThread = MyProgressBar(self)
            #progressThread = None
            
        if maskLoadingThread == None:
            maskLoadingThread = LoadMaskThread()
            maskLoadingThread.start()
            loadMaskQueue.put([mask_fullpath, 'beamstop', expParams, 'param'])
        else:
            loadMaskQueue.put([mask_fullpath, 'beamstop', expParams, 'param'])
            
            #progressThread.run()
            
def LoadReadoutNoiseMask(mask_fullpath):
    
    global maskLoadingThread
        
    expParams = wx.FindWindowByName('MainFrame').GetAllParameters()
        
        #mask_filename = os.path.split(mask_fullpath)[1]
        
    if mask_fullpath:
            
            #filename_label = wx.FindWindowById(self.maskIds['ReadoutMask'])
            #filename_label.SetLabel(mask_filename)
                       
            #progressThread = MyProgressBar(self)
            #progressThread= None
            
        if maskLoadingThread == None:
            maskLoadingThread = LoadMaskThread(self)
            maskLoadingThread.start()
            loadMaskQueue.put([mask_fullpath, 'readout', expParams, 'param'])
        else:
            loadMaskQueue.put([mask_fullpath, 'readout', expParams, 'param'])
            
        
            #progressThread.run()


#---- #### MASK LOADING ####


class ImageSettingsDialog(wx.Dialog):

    def __init__(self, parent, ExpObj, ImgObj):
        
        wx.Dialog.__init__(self, parent, -1, title = 'Image Display Settings')

        self.ExpObj = ExpObj
        self.ImgObj = ImgObj
        self.parent = parent
        
        self.newImg = self.parent.img.copy()
        
        sizer = wx.BoxSizer(wx.VERTICAL)
  
        if not parent.plotParameters['UpperClim'] == None and not parent.plotParameters['LowerClim'] == None:
            self.maxval = parent.plotParameters['maxImgVal']
            self.minval = parent.plotParameters['minImgVal']
        else:
            self.maxval = 100
            self.minval = 0
        
        self.sliderinfo = (                           
                           ################### ctrl,     slider #############
                           ('Upper limit:', wx.NewId(), wx.NewId(), 'UpperClim'),
                           ('Lower limit:', wx.NewId(), wx.NewId(), 'LowerClim'),
                           ('Brightness:', wx.NewId(), wx.NewId(), 'Brightness'))
                          
        
        self.scaleinfo = (('Linear', wx.NewId(), 'ImgScale'), 
                          ('Logarithmic', wx.NewId(), 'ImgScale'))
        
        slidersizer = self.createSettingsWindow()
        scalesizer = self.createScaleSelector()
        colormapsizer = self.createColormapSelector()
        
        
        box = wx.StaticBox(self, -1, 'Image parameters')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(slidersizer, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        
        self.okButton = wx.Button(self, -1, 'OK')
        self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        
        finalSizer = wx.BoxSizer(wx.VERTICAL)
        finalSizer.Add(sizer, 0, wx.EXPAND, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        finalSizer.Add(scalesizer,0, wx.EXPAND, wx.LEFT | wx.RIGHT, 5)
        finalSizer.Add(colormapsizer,0, wx.EXPAND, wx.LEFT | wx.RIGHT, 5)
        finalSizer.Add(self.okButton, 0, wx.CENTER | wx.TOP, 3)
        
        self.SetSizer(finalSizer)
        self.Fit()
        
    def OnOk(self, event):
        
        self.Destroy()
        
    def createColormapSelector(self):
        
        sizer = wx.BoxSizer()
        
        self.colorRadioList = ['Gray', 'Heat', 'Rainbow', 'Jet', 'Spectral']
        
        self.colormaps = [matplotlib.cm.gray,
                          matplotlib.cm.gist_heat,
                          matplotlib.cm.gist_rainbow,
                          matplotlib.cm.jet,
                          matplotlib.cm.spectral]
        
        rb = wx.RadioBox(self, label="Colormaps", choices=self.colorRadioList, style=wx.RA_SPECIFY_COLS)
        rb.Bind(wx.EVT_RADIOBOX, self.onColorMapsRadioBox)

        rb.SetSelection(self.colormaps.index(self.parent.plotParameters['ColorMap']))
        
        sizer.Add(rb,1,wx.EXPAND)
        
        return sizer
    
    def onColorMapsRadioBox(self, event):
        
        selection = event.GetSelection()
                
        if self.colorRadioList[selection] == 'Gray':
            self.parent.plotParameters['ColorMap'] = matplotlib.cm.gray
        elif self.colorRadioList[selection] == 'Heat':
            self.parent.plotParameters['ColorMap'] = matplotlib.cm.gist_heat
        elif self.colorRadioList[selection] == 'Rainbow':
            self.parent.plotParameters['ColorMap'] = matplotlib.cm.gist_rainbow
        elif self.colorRadioList[selection] == 'Jet':
            self.parent.plotParameters['ColorMap'] = matplotlib.cm.jet
        elif self.colorRadioList[selection] == 'Bone':
            self.parent.plotParameters['ColorMap'] = matplotlib.cm.bone
        elif self.colorRadioList[selection] == 'Spectral':
            self.parent.plotParameters['ColorMap'] = matplotlib.cm.spectral
        
        if self.ImgObj != None:
            self.ImgObj.cmap = self.parent.plotParameters['ColorMap']
            self.ImgObj.changed()
            self.parent.updateImage()
        
    def createScaleSelector(self):
        
        sizer = wx.BoxSizer()
        
        radioList = ['Linear', 'Logarithmic']
        rb = wx.RadioBox(self, label="Image scaling", choices=radioList, style=wx.RA_SPECIFY_COLS)
        rb.Bind(wx.EVT_RADIOBOX, self.onRadioBox)

        if self.parent.plotParameters['ImgScale'] == 'linear':
            rb.SetSelection(0)
        else:
            rb.SetSelection(1)

        sizer.Add(rb,1,wx.EXPAND)
        
        return sizer
    
    def onRadioBox(self, event):
        
        selection = event.GetSelection()
        
        if selection == 0:
            if self.parent.plotParameters['ImgScale'] != 'linear':
                self.parent.img[self.parent.imgZeros] = 0.0
                self.ImgObj.set_data(self.parent.img)
                self.ImgObj.changed()
                self.parent.plotParameters['ImgScale'] = 'linear'
                
                if self.parent.plotParameters['ClimLocked'] == False:
                    minval = self.parent.img.min()
                    maxval = self.parent.img.max()
                    
                    self.parent.plotParameters['UpperClim'] = maxval
                    self.parent.plotParameters['LowerClim'] = minval
                    
                    self.ImgObj.set_clim(minval, maxval)
                    self.resetSliders(maxval, minval)
                
                self.parent.updateImage()
        if selection == 1:
            if self.parent.plotParameters['ImgScale'] != 'logarithmic':
                
                self.parent.img[self.parent.imgZeros] = 1.0
                
                self.newImg = log(self.parent.img)
                self.newImg = uint16(self.newImg / self.newImg.max() * 65535)
                 
                self.ImgObj.set_data(self.newImg)
                self.ImgObj.changed()
                self.parent.plotParameters['ImgScale'] = 'logarithmic'
                
                if self.parent.plotParameters['ClimLocked'] == False:
                    minval = self.newImg.min()
                    maxval = self.newImg.max()
                    
                    self.parent.plotParameters['UpperClim'] = maxval
                    self.parent.plotParameters['LowerClim'] = minval
                    
                    self.ImgObj.set_clim(minval, maxval)
                    self.resetSliders(maxval, minval)
                
                self.parent.updateImage()
                
                  
    def createSettingsWindow(self):
        
        finalSizer = wx.BoxSizer(wx.VERTICAL)
        
        
        for each in self.sliderinfo:
                
            label = wx.StaticText(self, -1, each[0])
            val = wx.TextCtrl(self, each[1], size = (60, 21), style = wx.TE_PROCESS_ENTER)
            val.Bind(wx.EVT_TEXT_ENTER, self.OnTxtEnter)
            val.Bind(wx.EVT_KILL_FOCUS, self.OnTxtEnter)
            
            slider = wx.Slider(self, each[2], style = wx.HORIZONTAL)
            #slider.Bind(wx.EVT_SLIDER, self.OnSlider)
            
            slider.Bind(wx.EVT_SCROLL_CHANGED, self.OnSlider)
            #slider.Bind(wx.EVT_LEFT_UP, self.OnTest)
            
            if each[3] == 'Brightness' or each[3] == 'Contrast':
                slider.SetMin(0)
                slider.SetMax(200)
            else:
                slider.SetMin(self.minval)
                slider.SetMax(self.maxval)
            
            if self.parent.plotParameters[each[3]] != None:
                val.SetValue(str(self.parent.plotParameters[each[3]]))
                slider.SetValue(float(self.parent.plotParameters[each[3]]))
            
            hslider = wx.BoxSizer(wx.HORIZONTAL)
            
            
            
            hslider.Add(label, 0, wx.EXPAND | wx.TOP, 3)
            hslider.Add(val, 0, wx.EXPAND)
            hslider.Add(slider, 1, wx.EXPAND)
           
            finalSizer.Add(hslider, 0, wx.EXPAND)
        
        chkbox = wx.CheckBox(self, -1, 'Lock values')
        chkbox.Bind(wx.EVT_CHECKBOX, self.onLockValues)
        chkbox.SetValue(self.parent.plotParameters['ClimLocked'])
        
        finalSizer.Add(chkbox, 0, wx.EXPAND | wx.TOP, 3)

        return finalSizer
    
    def OnTest(self, event):
        print 'BAM!'
    
    def resetSliders(self, maxval, minval):
        
        for each in self.sliderinfo:
            txtCtrl = wx.FindWindowById(each[1])
            slider = wx.FindWindowById(each[2])
            txtCtrl.SetValue(str(self.parent.plotParameters[each[3]]))
            
            if each[3] == 'Brightness' or each[3] == 'Contrast':
                slider.SetMin(0)
                slider.SetMax(200)
            else:
                slider.SetMin(minval)
                slider.SetMax(maxval)
            
            
            slider.SetValue(float(self.parent.plotParameters[each[3]]))
    
    def onLockValues(self, event):
        
        if event.GetEventObject().IsChecked():
            self.parent.plotParameters['ClimLocked'] = True
        else:
            self.parent.plotParameters['ClimLocked'] = False
    
    def OnTxtEnter(self, event):

        id = event.GetId()
        
        for each in self.sliderinfo:
            if each[1] == id:
                ctrl = wx.FindWindowById(id)
                slider = wx.FindWindowById(each[2])
                slider.SetValue(float(ctrl.GetValue()))
                
                val = ctrl.GetValue()
                self.parent.plotParameters[each[3]] = float(val)
                
                if each[3] == 'Brightness' or each[3] == 'Contrast':
                    self.setBrightnessAndContrastUINT16()
                else:
                    self.parent.updateClim()

    def OnSlider(self, event):
        
        id = event.GetId()
        
        for each in self.sliderinfo:
            if each[2] == id:        
                slider = event.GetEventObject()
                val = slider.GetValue()    
                wx.FindWindowById(each[1]).SetValue(str(val))
                self.parent.plotParameters[each[3]] = float(val)
                
                if each[3] == 'Brightness' or each[3] == 'Contrast':
                    self.setBrightnessAndContrastUINT16()
                else:
                    self.parent.updateClim()
            
    def setBrightnessAndContrastUINT16(self):
        brightness = self.parent.plotParameters['Brightness'] - 100;
        contrast = (self.parent.plotParameters['Contrast'] - 100)/10;
        max_value = 0;
        
        print brightness
        print contrast
        
        lut = array(range(0,65536), int)

    # The algorithm is by Werner D. Streidt
    # (http://visca.com/ffactory/archives/5-99/msg00021.html)
        if( contrast > 0 ):
            delta = 32767.*contrast/100;
            a = 65535./(65535. - delta*2);
            b = a*(brightness - delta);
        else:
            delta = -32768.*contrast/100;
            a = (65536.-delta*2)/65535.;
            b = a*brightness + delta;

        for i in range(65536):
            v = round(a*i + b);
            if( v < 0 ):
                v = 0;
            if( v > 65535 ):
                v = 65535;
            lut[i] = v;
    
        newImg = lut[int_(self.parent.img)]
        
        
      #  if self.parent.plotParameters['ImgScale'] != 'logarithmic':
      #      newImg[where(newImg) == 0] = 1.0
      #      newImg = log(self.parent.img)
      #      newImg = uint16(self.newImg / self.newImg.max() * 65535)
                 
                #self.ImgObj.set_data(self.newImg)
#       newImg[where(newImg<1)] = 1
        self.ImgObj.set_data(newImg)
        self.parent.updateImage()
            
class HdrInfoDialog(wx.Dialog):
    
    def __init__(self, parent, ExpObj):
        
        wx.Dialog.__init__(self, parent, -1, size = (500,500))

        self.ExpObj = ExpObj
        
        finalSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = self.createHdrInfoWindow()
        
        finalSizer.Add(sizer, 1, wx.EXPAND)
        
        self.SetSizer(finalSizer)
        
        
    def createHdrInfoWindow(self):
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.text = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE)
        
        self.text.AppendText('#############################################\n')
        self.text.AppendText('                                                 Header information\n')
        self.text.AppendText('#############################################\n\n')
        
        
        if self.ExpObj != None:
            keys = self.ExpObj.param.iterkeys()
        
            for each in keys:
                self.text.AppendText(str(each) + ' : ' + str(self.ExpObj.param[each])+'\n')
        
        sizer.Add(self.text, 1, wx.EXPAND)
        
        return sizer
        
############################################################################
#### Mask creation progress thread
############################################################################
class MaskCreationDialog(wx.Dialog):
    def __init__(self, parent, PumpNumber):
        
        wx.Dialog.__init__(self, parent, -1, size=(385,150))
        
        self.statusText = wx.StaticText(self, -1, '')
        
    def setText(self, text):
        self.statusText.SetLabel(text)

class MaskCreationThread(threading.Thread):
    """ Mask creator thread """
    def __init__(self, notify_window, chipMotors, flowMotors):
        
        threading.Thread.__init__(self)
        
        self._notify_window = notify_window
        
        self._user_wants_to_abort = 0
        self.setDaemon(1)                       # Make sure the thread terminates on exit.
        
        self.new_experiment = 1
        self.thread_busy = False
             
    def run(self):
       
        msgdlg.ShowModal()
        msgdlg.Destroy()
        #self.createFinalMask()
        self.showMask()
        
        print "Adjusting Motors - Please wait!"
        wx.PostEvent(self._notify_window, StatusEvent('Adjusting Motors - Please wait!'))
    
    def abort(self):
        """ user wants to abort thread """
        self._user_wants_to_abort = 1

    def startMotors(self, notify_window, chipMotors, flowMotors):
        self._notify_window = notify_window
        self.flowMotors = flowMotors
        self.chipMotors = chipMotors
        
        self.new_experiment = 1
        
    def isBusy(self):
        return self.thread_busy

#############################################################################
######################## FOR TESTING: #######################################
#############################################################################

class MaskingTestFrame(wx.Frame):
    
    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title, name = 'TestFrame')
        
        self.backgroundPanel = wx.Panel(self, -1)
        sizer = wx.BoxSizer()
        
        maskingFigurePanel = MaskingPanel(self.backgroundPanel, -1, 'test')
        
        sizer.Add(maskingFigurePanel, 1, wx.GROW)
  
        self.backgroundPanel.SetSizer(sizer)
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(1)
        #self.statusbar.SetStatusWidths([-3, -2])
        
        print "Loading Test Image 19_InsulinA_300sec..."
        
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
               
        ExpObj, FullImage = fileIO.loadFile('/home/specuser/g1hutch/richard/', expParams)
        print "Done!"
        
        maskingFigurePanel.showImage(FullImage, ExpObj)
        print "finished showing image!"
    
    def SetStatusText(self, text, slot = 0):
        
        self.statusbar.SetStatusText(text, slot)

class MaskingTestApp(wx.App):
    
    def OnInit(self):
        
        frame = MaskingTestFrame('Mask Creator', -1)
        self.SetTopWindow(frame)
        frame.SetSize((1024,768))
        frame.CenterOnScreen()
        frame.Show(True)
        
        return True
        
if __name__ == "__main__":
    app = MaskingTestApp(0)   #MyApp(redirect = True)
    app.MainLoop()

   
