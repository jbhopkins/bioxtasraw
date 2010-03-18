#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    BioXTAS RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Foobar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************


from __future__ import division
import os #sys, time, os, gc
#import matplotlib
import wx
import fileIO, cartToPol
import BIFT
import threading
import RAW
import OpenGnom
from math import *
from numpy import transpose, ones

biftparams  = {'maxDmax' : 400,
               'minDmax' : 50,
               'DmaxPoints' : 55,
               'maxAlpha' : 14,
               'minAlpha' : 5,
               'AlphaPoints' : 20,
               'PrPoints' : 50 }


class BiftInfoPanel(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent, -1)
        
        self.parent = parent
        
        self.controlData = (  ('File :', parent.paramsInGui['Filename']),
                              ('I(0) :', parent.paramsInGui['I(0)']),
                              ('Rg :',   parent.paramsInGui['Rg']),
                              ('Dmax :', parent.paramsInGui['Dmax']),
                              ('Alpha (log):',parent.paramsInGui['Alpha']),
                              ('Qmin :', parent.paramsInGui['Qmin']),
                              ('Qmax :', parent.paramsInGui['Qmax']))
                          
        
        topsizer = self.createControls()
        
        self.currentExpObj = None
        
        self.SetSizer(topsizer)
        
    def createControls(self):
        
        cols = 4
        rows = round(len(self.controlData)/ 2)
        sizer = wx.FlexGridSizer(cols = cols, rows = rows, vgap = 5, hgap = 5)
        
        for each in self.controlData:
            
            label = each[0]
            type = each[1][1]
            id = each[1][0]
            
            if type == 'filename':
                labelbox = wx.StaticText(self, -1, label)
                infobox = wx.StaticText(self, id, '', size = (60,20))
                sizer.Add(labelbox, 0)
                sizer.Add(infobox, 0)
                sizer.Add((1,1),0)
                sizer.Add((1,1),0)
            
            if type == 'info':
                labelbox = wx.StaticText(self, -1, label)
                infobox = wx.TextCtrl(self, id, '', size = (60,20))
                infobox.SetEditable(False)
                sizer.Add(labelbox, 0)
                sizer.Add(infobox, 0)
            
            elif type == 'ctrl':
                labelbox = wx.StaticText(self, -1, label)
                ctrl = RAW.FloatSpinCtrl(self, id)
                ctrl.Bind(RAW.EVT_MY_SPIN, self._onSpinChange)
                ctrl.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)
                sizer.Add(labelbox, 0)
                sizer.Add(ctrl, 0, wx.ALIGN_CENTER)
            
            elif type == 'listctrl':
                labelbox = wx.StaticText(self, -1, label)
                ctrl = RAW.ListSpinCtrl(self, id, [1.0])
                ctrl.Bind(RAW.EVT_MY_SPIN, self._onSpinChange)
                sizer.Add(labelbox, 0)
                sizer.Add(ctrl, 0, wx.ALIGN_CENTER)
                
        return sizer    
    
    def _onSpinChange(self, evt):
        
        if evt.GetId() == self.parent.paramsInGui['Qmin'][0]:
            QMIN = wx.FindWindowById(self.parent.paramsInGui['Qmin'][0])
            idx = QMIN.GetIdx()
            c = self.currentExpObj.idx
            c[0] = idx
            self.currentExpObj.idx = c
        
        if evt.GetId() == self.parent.paramsInGui['Qmax'][0]:
            QMAX = wx.FindWindowById(self.parent.paramsInGui['Qmax'][0])
            idx = QMAX.GetIdx()
            c = self.currentExpObj.idx
            c[1] = idx
            self.currentExpObj.idx = c
            
    def clear(self):
        for each in self.controlData:
            label = each[0]
            type = each[1][1]
            id = each[1][0]
            
            if type == 'info' or type == 'filename':
                infobox = wx.FindWindowById(id)
                infobox.SetLabel('')
            elif type == 'ctrl':
                ctrl = wx.FindWindowById(id)
                ctrl.SetValue('1.00')
                
    def onKillFocus(self, evt):
        print 'HELLO!'
    
    def getDmaxAlpha(self):
        
        D = wx.FindWindowById(self.parent.paramsInGui['Dmax'][0])
        dmax = D.GetValue()
            
        A = wx.FindWindowById(self.parent.paramsInGui['Alpha'][0])
        alpha = A.GetValue()
        
        return (dmax, alpha)
    
    def updateInfo(self, Data):
        
        if len(Data) == 1:
            ExpObj = Data[0]
        else:
            ExpObj = Data[1]
  
        if ExpObj.type == 'rad':
            self.currentExpObj = ExpObj
            self.Enable(True)
            self.clear()
            fileId = wx.FindWindowById(self.parent.paramsInGui['Filename'][0])
            fileId.SetLabel(ExpObj.param['filename'])
            
            I = wx.FindWindowById(self.parent.paramsInGui['I(0)'][0])
            I.Enable(False)
            R = wx.FindWindowById(self.parent.paramsInGui['Rg'][0])
            R.Enable(False)
            
            #print ExpObj.q_raw
            QMAX = wx.FindWindowById(self.parent.paramsInGui['Qmax'][0])
            QMAX.SetList(ExpObj.q_raw)
            QMAX.SetIdx(ExpObj.idx[1])
            
            QMIN = wx.FindWindowById(self.parent.paramsInGui['Qmin'][0])
            QMIN.SetList(ExpObj.q_raw)
            QMIN.SetIdx(ExpObj.idx[0])
            
        else:
            self.currentExpObj = Data[0]
            
            self.Enable(True)
            fileId = wx.FindWindowById(self.parent.paramsInGui['Filename'][0])
            filename = os.path.split(ExpObj.param['filename'])[1]
            fileId.SetLabel(filename)

            I0 = ExpObj.allData['I0']
            dmax = ExpObj.allData['dmax']
            Rg = ExpObj.allData['Rg']
            alpha = ExpObj.allData['alpha']
            
            I = wx.FindWindowById(self.parent.paramsInGui['I(0)'][0])
            I.SetValue(str(round(I0,4)))
            I.Enable(True)
            
            D = wx.FindWindowById(self.parent.paramsInGui['Dmax'][0])
            D.SetValue(str(dmax))
            
            R = wx.FindWindowById(self.parent.paramsInGui['Rg'][0])
            R.SetValue(str(round(Rg,4)))
            R.Enable(True)
            
            A = wx.FindWindowById(self.parent.paramsInGui['Alpha'][0])
            A.SetValue(str(alpha))        
            
            QMAX = wx.FindWindowById(self.parent.paramsInGui['Qmax'][0])
            QMAX.SetList(self.currentExpObj.q_raw)
            QMAX.SetIdx(self.currentExpObj.idx[1])
            
            QMIN = wx.FindWindowById(self.parent.paramsInGui['Qmin'][0])
            QMIN.SetList(self.currentExpObj.q_raw)
            QMIN.SetIdx(self.currentExpObj.idx[0])
            
    
class BiftCalculationThread(threading.Thread):
    
    def __init__(self, parent, selectedFile):
        
        threading.Thread.__init__(self)
        
        self._parent = parent
        self.selectedFile = selectedFile
        self._pgthread = RAW.MyProgressBar(self._parent)
    
    def run(self):
        
        algo = self._parent.expParams['IFTAlgoChoice']
        #self._pgthread.run()
        #self._pgthread.SetStatus('Calculating P(r) ...')
        
        if isinstance(self.selectedFile, list):
            for eachExp in self.selectedFile:

                ExpObj = eachExp  #self.selectedFile
                
                if algo == 'BIFT':
                    IFTObj = self.getBIFT(ExpObj)
                elif algo == 'GNOM':
                    ctrl = wx.FindWindowById(self._parent.paramsInGui['Dmax'][0])
                    dmax = float(ctrl.GetValue())
                    IFTObj = self.getGNOM(ExpObj, dmax)
        
                biftPlotPanel = wx.FindWindowByName('BIFTPlotPanel')

                IFTObj.isBifted = True
        
                wx.CallAfter(biftPlotPanel.PlotBIFTExperimentObject,IFTObj)
        
                infoPanel = wx.FindWindowByName('InfoPanel')
                wx.CallAfter(infoPanel.WriteText, 'IFT : ' + IFTObj.param['filename'] + '\n')
                wx.CallAfter(infoPanel.WriteText,'Dmax : ' + str(IFTObj.allData['dmax']) + '\nAlpha : ' + str(IFTObj.allData['alpha']) + '\nI0 : ' + str(IFTObj.allData['I0']) + '\nRg : ' + str(IFTObj.allData['Rg']) + '\nChi^2 : ' + str(IFTObj.allData['ChiSquared']) + '\n')
        
                if algo == 'GNOM':
                    wx.CallAfter(infoPanel.WriteText, 'TOTAL : ' + str(IFTObj.allData['gnomTOTAL']) + '\n' )
                    
                    for each in IFTObj.allData['all_posteriors']:
                        wx.CallAfter(infoPanel.WriteText, each[0] + ' : ' + str(each[1]) + '\n' )
                    
                    wx.CallAfter(infoPanel.WriteText, '\n\n')
                    
                else:
                    wx.CallAfter(infoPanel.WriteText, '\n')
                    
                biftPage = wx.FindWindowByName('AutoAnalysisPage')
                wx.CallAfter(biftPage.addBiftObjToList, ExpObj, IFTObj)
        
        else:
            
                ExpObj = self.selectedFile
        
                if algo == 'BIFT':
                    IFTObj = self.getBIFT(ExpObj)
                elif algo == 'GNOM':
                    ctrl = wx.FindWindowById(self._parent.paramsInGui['Dmax'][0])
                    dmax = float(ctrl.GetValue())
                    IFTObj = self.getGNOM(ExpObj, dmax)
        
                biftPlotPanel = wx.FindWindowByName('BIFTPlotPanel')

                IFTObj.isBifted = True
        
                wx.CallAfter(biftPlotPanel.PlotBIFTExperimentObject, IFTObj)
        
                infoPanel = wx.FindWindowByName('InfoPanel')
                wx.CallAfter(infoPanel.WriteText,'IFT : ' + IFTObj.param['filename'] + '\n')
                wx.CallAfter(infoPanel.WriteText,'Dmax : ' + str(IFTObj.allData['dmax']) + '\nAlpha : ' + str(IFTObj.allData['alpha']) + '\nI0 : ' + str(IFTObj.allData['I0']) + '\nRg : ' + str(IFTObj.allData['Rg']) + '\nChi^2 : ' + str(IFTObj.allData['ChiSquared']) + '\n')
        
                if algo == 'GNOM':
                    wx.CallAfter(infoPanel.WriteText, 'TOTAL : ' + str(IFTObj.allData['gnomTOTAL']) + '\n' )
                    
                    for each in IFTObj.allData['all_posteriors']:
                        wx.CallAfter(infoPanel.WriteText, each[0] + ' : ' + str(each[1]) + '\n' )
                    
                    wx.CallAfter(infoPanel.WriteText, '\n')
                else:
                    wx.CallAfter(infoPanel.WriteText, '\n')
        
                biftPage = wx.FindWindowByName('AutoAnalysisPage')
                wx.CallAfter(biftPage.addBiftObjToList, ExpObj, IFTObj)
        
        #self._pgthread.SetStatus('Done')
        #self._pgthread.stop()
        
        
    def getBIFT(self, ExpObj):
            
        BiftObj = BIFT.doBift(ExpObj,
                                  self._parent.expParams['PrPoints'],
                                  self._parent.expParams['maxAlpha'],
                                  self._parent.expParams['minAlpha'],
                                  self._parent.expParams['AlphaPoints'],
                                  self._parent.expParams['maxDmax'],
                                  self._parent.expParams['minDmax'],
                                  self._parent.expParams['DmaxPoints'])
            
        return BiftObj
        
    def getGNOM(self, ExpObj, dmax):
            
        I = ExpObj.i
        q = ExpObj.q
        sigma = ExpObj.errorbars
                        
        WCA_Params = [[self._parent.expParams['DISCRPweight'], 0.3, 0.7],
                      [self._parent.expParams['OSCILLweight'], 0.6, 1.1],
                      [self._parent.expParams['STABILweight'], 0.12, 0.0],
                      [self._parent.expParams['SYSDEVweight'], 0.12, 1.0],
                      [self._parent.expParams['POSITVweight'], 0.12, 1.0],
                      [self._parent.expParams['VALCENweight'], 0.12, 0.95]]
        
        forceInitZero = self._parent.expParams['gnomFixInitZero']
        
        Pr, r, Fit, info = OpenGnom.getGnomPr(I, q, sigma,
                                               self._parent.expParams['gnomPrPoints'],
                                               dmax, 0,
                                               self._parent.expParams['gnomMinAlpha'],
                                               self._parent.expParams['gnomMaxAlpha'],
                                               self._parent.expParams['gnomAlphaPoints'],
                                               WCA_Params, forceInitZero)
            
        IFTObj = cartToPol.BIFTMeasurement(transpose(Pr), r, ones((len(transpose(Pr)),1)), ExpObj.param, Fit, info)
            
        return IFTObj

class AutoAnalysisPage(wx.Panel):
    def __init__(self, parent, expParams):
        wx.Panel.__init__(self, parent, name = 'AutoAnalysisPage')
        
        self.expParams = expParams
        
        self.iftAlgoLabels = self.expParams['IFTAlgoList']
        
        self.paramsInGui={'Filename' : (wx.NewId(), 'filename'),
                          'I(0)' : (wx.NewId(), 'info'),
                          'Rg'   : (wx.NewId(), 'info'),
                          'Dmax' : (wx.NewId(), 'ctrl'),
                          'Alpha': (wx.NewId(), 'ctrl'),
                          'Qmin' : (wx.NewId(), 'listctrl'),
                          'Qmax' : (wx.NewId(), 'listctrl'),
                          'AlgoChoice' : (wx.NewId(), 'listctrl')}
        
        self.buttons = (("IFT", self._OnDoBift),
                        ("Load", self._OnLoadFile),
                        ("Options", self._OnOptions),
                        ("Clear Plot", self._OnClearAll),
                        ("Solve", self._OnManual),
                        ("Clear List", self._OnClearList))
        
        # /* INSERT WIDGETS */ 
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        
        self.filelist = wx.ListBox(self, style = wx.LB_EXTENDED)
        self.filelist.Bind(wx.EVT_LISTBOX, self._OnListBoxEvent)
        self.filelist.Bind(wx.EVT_KEY_DOWN, self._OnListBoxKeyEvent)
        
        self.infoBox = BiftInfoPanel(self)
        self.infoBox.Enable(False)
        
        self.algoList = self.createAlgoList()
        
        panelsizer.Add(self.algoList, 0, wx.EXPAND | wx.TOP | wx.BOTTOM |  wx.LEFT | wx.RIGHT, 10)
        panelsizer.Add(self.infoBox, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        panelsizer.Add(self.filelist, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.createButtons(panelsizer)
        
        #panelsizer.Add((5,5),0)
        
        self.SetSizer(panelsizer)
        
 #      self.filelist.Insert('Test.dat', 0)
 
    def createAlgoList(self):
        
        #sizer = wx.FlexGridSizer(rows = 1, cols = 2, hgap = 5)
        sizer = wx.BoxSizer()
        
        id = self.paramsInGui['AlgoChoice'][0]
        
        self.combobox = wx.ComboBox(self, id, choices = self.iftAlgoLabels, style=wx.CB_READONLY, size = (100, 25))
        self.combobox.Bind(wx.EVT_COMBOBOX, self._onAlgoSelect)
        self.combobox.SetStringSelection(self.expParams['IFTAlgoChoice'])

        txt = wx.StaticText(self, -1, 'Algorithm :')
        
        sizer.Add((2,2), wx.EXPAND)
        sizer.Add(txt, 0, wx.EXPAND | wx.RIGHT | wx.TOP, 3)
        sizer.Add(self.combobox, 0, wx.EXPAND)
        sizer.Add((2,2), wx.EXPAND)
        
        return sizer
    
    def _onAlgoSelect(self, evt):
        self.expParams['IFTAlgoChoice'] = self.combobox.GetStringSelection()
 
    def _OnListBoxEvent(self, evt):
        
        #Hm.. evt.GetClientData() seems to be broken
        num = self.filelist.GetSelections()
        Data = self.filelist.GetClientData(num[0])
        self.infoBox.updateInfo(Data)
    
    def _OnListBoxKeyEvent(self, evt):
        
        key = evt.GetKeyCode()
        
        if key == wx.WXK_DELETE:
            
            items = self.filelist.GetSelections()
            
            if items:
                self.filelist.Delete(items[0])
                
                if not self.filelist.IsEmpty():
                    self.filelist.SetSelection(0)
                    SelectedExpObjList = self.filelist.GetClientData(0)
                    self.infoBox.updateInfo(SelectedExpObjList)
                else:
                    self.infoBox.Enable(False)
                    self.infoBox.clear()
                    
    def _OnClearList(self, evt):
        self.filelist.Clear()
        self.infoBox.clear()
        self.infoBox.Enable(False)
        
    def _OnManual(self, evt):
        ''' Solve button '''
        
        selectedFile = self.filelist.GetSelections()
        
        if selectedFile == None or selectedFile == ():
            return
        
        selectedFile = selectedFile[0]
        
        NO_FILE_SELECTED = -1

        if selectedFile == NO_FILE_SELECTED:
            return
        else:
            SelectedExpObj = self.filelist.GetClientData(selectedFile)[0]
        
        dmax, alpha = self.infoBox.getDmaxAlpha()
        
        dmax = float(dmax)
        alpha = float(alpha)
        
        #print SelectedExpObj.type
        SelectedExpObj.setQrange(SelectedExpObj.idx)
        
        
        algo = self.expParams['IFTAlgoChoice']
        
        if algo == 'BIFT':
            N = self.expParams['PrPoints']
            ExpObj = BIFT.SingleSolve(alpha, dmax, SelectedExpObj, N)
        elif algo == 'GNOM':
            WCA_Param  = [[self.expParams['DISCRPweight'], 0.3, 0.7],
                          [self.expParams['OSCILLweight'], 0.6, 1.1],
                          [self.expParams['STABILweight'], 0.12, 0.0],
                          [self.expParams['SYSDEVweight'], 0.12, 1.0],
                          [self.expParams['POSITVweight'], 0.12, 1.0],
                          [self.expParams['VALCENweight'], 0.12, 0.95]]
            
            forceInitZero = self.expParams['gnomFixInitZero']
            N = self.expParams['gnomPrPoints']
            Pr, r, Fit, info = OpenGnom.singleSolveInRAW(alpha, dmax, SelectedExpObj, N, 0, forceInitZero, WCA_Param)
            ExpObj = cartToPol.BIFTMeasurement(transpose(Pr), r, ones((len(transpose(Pr)),1)), SelectedExpObj.param, Fit, info)
        
        ExpObj.isBifted = True
        
        biftPlotPanel = wx.FindWindowByName('BIFTPlotPanel')
        biftPlotPanel.PlotBIFTExperimentObject(ExpObj)
        
        self.infoBox.updateInfo([SelectedExpObj, ExpObj])
  
    def _OnClearAll(self, evt):
        plotpage = wx.FindWindowByName('BIFTPlotPanel')
        plotpage.OnClear(0)
        
    def _OnOptions(self, evt):
        
        mainframe = wx.FindWindowByName('MainFrame')
        mainframe.ShowOptionsDialog(3)    # Index 1 = BIFT page
    
    def _OnDoBift(self, evt):
                
        expList = []
        for each in self.filelist.GetSelections():
            expList.append(self.filelist.GetClientData(each)[0])
        
        if expList == []:
            return
        
        for each in expList:
            each.setQrange(each.idx)
        
        calculationThread = BiftCalculationThread(self, expList)
        calculationThread.start()
    
    def addBiftObjToList(self, ExpObj, BiftObj):
         
         print 'HELLO'
         for idx in range(0, self.filelist.GetCount()):
             E = self.filelist.GetClientData(idx)
             print E
             
             if ExpObj == E[0]:
                 self.filelist.SetClientData(idx, [ExpObj, BiftObj])
                 self.infoBox.updateInfo([ExpObj, BiftObj])
                 return
                  
         self.filelist.Insert(BiftObj.param['filename'], 0, [ExpObj, BiftObj])
         self.filelist.DeselectAll()
         self.filelist.SetSelection(0)
         self.infoBox.updateInfo([ExpObj, BiftObj])
         self.filelist.SetItemBackgroundColour(0, (100,100,100))
         
    def runBiftOnExperimentObject(self, ExpObj, expParams):
        
        self.expParams = expParams
        biftThread = BiftCalculationThread(self, ExpObj)
        biftThread.start()

    def _setBIFTParamsFromGui(self):
        
        for eachParam in biftparams.keys():
            
            id = self.biftParamsId.get(eachParam)[0]
            textctrl = wx.FindWindowById(id)
            value = textctrl.GetValue()
        
            biftparams[eachParam] = int(value)
    
    def _OnLoadFile(self, evt):   
        
        selected_file = self._CreateFileDialog(wx.OPEN)
        
        if selected_file:
       
            ExpObj, FullImageDummyVar = fileIO.loadFile(selected_file)
            
            noPathfilename = os.path.split(selected_file)[1]
            ExpObj.param['filename'] = noPathfilename
                        
            self.filelist.Insert(noPathfilename, 0,  [ExpObj])
                        
            self.filelist.DeselectAll()    
            self.filelist.SetSelection(0)
            self.infoBox.updateInfo([ExpObj])
            
            print self.filelist.GetSelections()
#            if ExpObj.type == 'bift':
#                self.infoBox.Enable(True)
#            else:
#                self.infoBox.Enable(False)
 
    def _CreateFileDialog(self, mode):
        
        file = None
        
        if mode == wx.OPEN:
            filters = 'Rad files (*.rad)|*.rad|Dat files (*.dat)|*.dat|Txt files (*.txt)|*.txt|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters)
        if mode == wx.SAVE:
            filters = 'Rad files (*.cfg)|*.cfg'
            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters)        
        
        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            
        # Destroy the dialog
        dialog.Destroy()
        
        return file
    
    def createButtons(self, panelsizer):
        
        sizer = wx.GridSizer(cols = 3, rows = ceil(len(self.buttons)/3))
        
        #sizer.Add((10,10) ,1 , wx.EXPAND)
        for each in self.buttons:
            if each:
                
                label = each[0]
                bindfunc = each[1]
                
                button = wx.Button(self, -1, label)
                button.Bind(wx.EVT_BUTTON, bindfunc)
                
                sizer.Add(button, 1, wx.EXPAND | wx.ALIGN_CENTER)         
          
        panelsizer.Add(sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP | wx.ALIGN_CENTRE | wx.EXPAND, 10)
        
    def createBiftOptions(self, panelsizer):
        
        for each in self.biftoptions:
            if each:
                labeltxt = each[0]
                id = each[1]
                param_value = biftparams.get(each[2])
                
                sizer = wx.BoxSizer()

                label = wx.StaticText(self, -1, labeltxt)
                ctrl = wx.TextCtrl(self, id, str(param_value), style = wx.TE_PROCESS_ENTER, size = (45,22))

                sizer.Add(label, 1, wx.EXPAND)
                sizer.Add(ctrl,0)
                
                panelsizer.Add(sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
           
    def createMaxMinOptions(self, panelsizer):
        
        topsizer = wx.BoxSizer()
        
        topsizer.Add((9,10),1, wx.EXPAND)
        topsizer.Add(wx.StaticText(self,-1,'Min',size = (45,15)),0)
        topsizer.Add(wx.StaticText(self,-1,'  Max',size = (45,15)),0)
        topsizer.Add(wx.StaticText(self,-1,'   Points',size = (45,15)),0)
                     
        panelsizer.Add(topsizer, 0.1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        first = True
        for each in self.biftmaxminoptions:
            
            sizer = wx.BoxSizer()
            
            labeltxt = each[0]
            
            min_id = each[1][1]
            max_id = each[1][0]
            points_id = each[1][2]
            
            max_param_value = biftparams.get(each[2][0])
            min_param_value = biftparams.get(each[2][1])
            points_param_value = biftparams.get(each[2][2])
                        
            label = wx.StaticText(self, -1, labeltxt)
            minCtrl = wx.TextCtrl(self, min_id, str(min_param_value), style = wx.TE_PROCESS_ENTER, size = (45,22))
            maxCtrl = wx.TextCtrl(self, max_id, str(max_param_value), style = wx.TE_PROCESS_ENTER, size = (45,22))        
            pointsCtrl = wx.TextCtrl(self, points_id, str(points_param_value), style = wx.TE_PROCESS_ENTER, size = (45,22))        
        
           # self.sampleScale.Bind(wx.EVT_KILL_FOCUS, self.OnSampleScaleChange)
           # self.sampleScale.Bind(wx.EVT_TEXT_ENTER, self.OnSampleScaleChange)
        
            sizer.Add(label, 1, wx.EXPAND)
            sizer.Add(minCtrl,0, wx.RIGHT, 10)
            sizer.Add(maxCtrl,0, wx.RIGHT, 10)
            sizer.Add(pointsCtrl,0)

            if not(first):
                panelsizer.Add(sizer, 0.1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
            else:
                panelsizer.Add(sizer, 0.1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
                first = False
        
        
        
        
        
