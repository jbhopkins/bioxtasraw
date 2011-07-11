#!/usr/bin/env python
'''
Created on Sep 31, 2010

@author: Nielsen

#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************
'''

import wx, os, subprocess, time, math, threading, Queue, numpy, cPickle, copy, sys
import platform, fnmatch, shutil
import wx.lib.scrolledpanel as scrolled
import wx.lib.wordwrap as wordwrap
import wx.grid as gridlib
from numpy import ceil

import wx.aui as aui
import RAWPlot, RAWImage, RAWOptions, RAWSettings, RAWCustomCtrl, RAWAnalysis
import SASFileIO, SASM, SASExceptions, SASImage
import matplotlib.colors as mplcol
import wx.lib.colourchooser as colorchooser
import wx.lib.buttons as wxbutton
from wx.lib.agw.balloontip import *
from wx._core import ICON_ERROR

mainworker_cmd_queue = Queue.Queue()
thread_wait_event = threading.Event()
question_return_queue = Queue.Queue()

RAWWorkDir = sys.path[0]

if os.path.split(sys.path[0])[1] in ['RAW.exe', 'raw.exe']:
    RAWWorkDir = os.path.split(sys.path[0])[0]

global workspace_saved
workspace_saved = True

class MainFrame(wx.Frame):
    
    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title, name = 'MainFrame')

        self.MenuIDs = {'exit'                : wx.NewId(),
                        'advancedOptions'     : wx.NewId(),
                        'loadSettings'        : wx.NewId(),
                        'saveSettings'        : wx.NewId(),
                        'centering'           : wx.NewId(),
                        'masking'             : wx.NewId(),
                        'goOnline'            : wx.NewId(),
                        'goOffline'           : wx.NewId(),
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
                        'help'                : wx.NewId(),
                        'about'               : wx.NewId(),
                        'guinierfit'          : wx.NewId(),
                        'saveWorkspace'       : wx.NewId(),
                        'loadWorkspace'       : wx.NewId()}
        
        self.guinierframe = None
        self.raw_settings = RAWSettings.RawGuiSettings()
        
        self.RAWWorkDir = sys.path[0].strip('RAW.exe')
          
        self.OnlineControl = OnlineController(self)
         
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -2, -1])
        self.statusbar.SetStatusText('Mode: OFFLINE', 2)    
        self.Bind(wx.EVT_CLOSE, self._onCloseWindow)
        
        # *************** Set minimum frame size ***************
        self.SetMinSize((800,600))
        
        # /* CREATE PLOT NOTEBOOK */
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        
        self.plot_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS)
        plot_panel = RAWPlot.PlotPanel(self.plot_notebook, -1, 'PlotPanel')
        img_panel = RAWImage.ImagePanel(self.plot_notebook, -1, 'ImagePanel')
        iftplot_panel = RAWPlot.IftPlotPanel(self.plot_notebook, -1, 'IFTPlotPanel')
        
        self.plot_notebook.AddPage(plot_panel, "Main Plot", False)
        self.plot_notebook.AddPage(iftplot_panel, "IFT Plot")
        self.plot_notebook.AddPage(img_panel, "Image", False)
        
                             
        self.control_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE)
        page2 = ManipulationPanel(self.control_notebook, self.raw_settings)
        page1 = FilePanel(self.control_notebook)
        page3 = IFTPanel(self.control_notebook, self.raw_settings)
       
        self.control_notebook.AddPage(page1, "Files", False)
        self.control_notebook.AddPage(page2, "Manipulation", False)
        self.control_notebook.AddPage(page3, "IFT")
        
        self.info_panel = InformationPanel(self)
        self.centering_panel = CenteringPanel(self, -1)
        self.masking_panel = MaskingPanel(self, -1)

        self._mgr.AddPane(self.info_panel, aui.AuiPaneInfo().Name("infopanel").
                          CloseButton(False).Left().Layer(0).Caption("Information Panel").PinButton(True).Row(0).Position(0))
        self._mgr.AddPane(self.control_notebook, aui.AuiPaneInfo().Name("ctrlpanel").
                          CloseButton(False).Left().Layer(0).Caption("Control Panel").MinSize((400,300)).PinButton(True).Row(0).Position(1))
        self._mgr.AddPane(self.plot_notebook, aui.AuiPaneInfo().Name("plotpanel").
                          CloseButton(False).Centre().Layer(0).Caption("Plot Panel"))
        
        self._mgr.AddPane(self.centering_panel, aui.AuiPaneInfo().Name("centeringpanel").
                           CloseButton(False).Left().Layer(0).Caption("Centering / Calibration").
                           PinButton(True).Row(0).Position(2))

        self._mgr.AddPane(self.masking_panel, aui.AuiPaneInfo().Name("maskingpanel").
                           CloseButton(False).Left().Layer(0).Caption("Masking").
                           PinButton(True).Row(0).Position(2))

        self._mgr.GetPane(self.centering_panel).Show(False)
        self._mgr.GetPane(self.centering_panel).dock_proportion = 350000
        
        self._mgr.GetPane(self.masking_panel).Show(False)
        self._mgr.GetPane(self.masking_panel).dock_proportion = 350000

        self._mgr.GetPane(self.info_panel).FloatingSize((300,200))
        self._mgr.GetPane(self.control_notebook).dock_proportion = 350000
        
        self._mgr.GetPane(self.info_panel).dock_proportion = 120000
        
        self._mgr.Update()
        
        self._mgr.GetPane(self.control_notebook).MinSize((200,300))

        #Load workdir from rawcfg.dat:
        self._loadCfg()
        self._createMenuBar()        
                
        # Start Plot Thread:
        self.main_worker_thread = MainWorkerThread(self, self.raw_settings)
        self.main_worker_thread.setDaemon(True)
        self.main_worker_thread.start()
        
            

    def test(self):
        self._mgr.GetPane(self.info_panel).Show(False)
        self._mgr.Update()
        
    def queueTaskInWorkerThread(self, taskname, data):
        mainworker_cmd_queue.put([taskname, data])
        
    def closeBusyDialog(self):
        self._busyDialog.Destroy()
        self._busyDialog = None
    
    def showBusyDialog(self, text): 
        self._busyDialog = wx.BusyInfo(text, self)
    
    def getWorkerThreadQueue(self):
        return mainworker_cmd_queue
    
    def getQuestionReturnQueue(self):
        return question_return_queue
    
    def showMaskingPane(self):
        self._mgr.GetPane(self.masking_panel).Show(True)
        self._mgr.GetPane(self.centering_panel).Show(False)
        self._mgr.GetPane(self.control_notebook).Show(False)
        self._mgr.Update()
        self.plot_notebook.SetSelection(2)
        wx.FindWindowByName('MaskingPanel').updateView()
        
    def closeMaskingPane(self):
        self._mgr.GetPane(self.masking_panel).Show(False)
        self._mgr.GetPane(self.control_notebook).Show(True)
        self._mgr.Update()
        self.plot_notebook.SetSelection(0)
        
    def showCenteringPane(self):
        self._mgr.GetPane(self.centering_panel).Show(True)
        self._mgr.GetPane(self.control_notebook).Show(False)
        self._mgr.GetPane(self.masking_panel).Show(False)
        self._mgr.Update()
        self.plot_notebook.SetSelection(2)
        
        self.centering_panel.updateAll()
        
    def closeCenteringPane(self):
        self._mgr.GetPane(self.centering_panel).Show(False)
        self._mgr.GetPane(self.control_notebook).Show(True)
        self._mgr.Update()
        self.plot_notebook.SetSelection(0)

        
    def showQuestionDialogFromThread(self, question, label, button_list, icon = None, filename = None, save_path = None):
        ''' Function to show a question dialog from the thread '''
        
        question_dialog = RAWCustomCtrl.CustomQuestionDialog(self, question, button_list, label, icon, filename, save_path, style = wx.CAPTION)
        result = question_dialog.ShowModal()
        path = question_dialog.getPath()
        question_dialog.Destroy()        
        
        if path:
            question_return_queue.put([result, path])
        else:
            question_return_queue.put([result])  # put answer in thread safe queue 
        
        thread_wait_event.set()                 # Release thread from its waiting state
        
    def _loadCfg(self):
        
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
        
    def showGuinierFitFrame(self, sasm, manip_item):
        
        if self.guinierframe:
            self.guinierframe.Destroy()
        
        #if not self.guinierframe:
        self.guinierframe = RAWAnalysis.GuinierTestFrame(self, 'Guinier Fit', sasm, manip_item)
        self.guinierframe.SetIcon(self.GetIcon())
        self.guinierframe.Show(True)
        #else:
        #    self.guinierframe.SetFocus()
        #    self.guinierframe.Raise()
        #    self.guinierframe.RequestUserAttention()
    
    def _onSaveSettings(self, evt):
        ############################ KILLS BEAMSTOP MASK !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        global expParams
        
        expParamsToSave = expParams
    
        file = self._createFileDialog(wx.SAVE)
        
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
            
    def _createSingleMenuBarItem(self, info):
        
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
                submenu = self._createSingleMenuBarItem(bindFunc)
                menu.AppendSubMenu(submenu, label)
                
            elif type == 'separator':
                menu.AppendSeparator()
                
        return menu
    
    def _onHelp(self, event):
        os.execl('xchm')
    
    def _createMenuBar(self):
        
        submenus = {                    
                    'viewPlot1Scale':[('Lin-Lin', self.MenuIDs['plot1sclinlin'], self._onViewMenu, 'radio'),
                                      ('Log-Lin', self.MenuIDs['plot1scloglin'], self._onViewMenu, 'radio'),
                                      ('Log-Log', self.MenuIDs['plot1scloglog'], self._onViewMenu, 'radio'),
                                      ('Lin-Log', self.MenuIDs['plot1sclinlog'], self._onViewMenu, 'radio'),
                                      ('Guinier', self.MenuIDs['plot1tyguinier'],self._onViewMenu, 'radio'),
                                      ('Kratky',  self.MenuIDs['plot1tykratky'], self._onViewMenu, 'radio'),                            
                                      ('Porod',   self.MenuIDs['plot1typorod'],  self._onViewMenu, 'radio')],
                                      
                    'viewPlot2Scale':[('Lin-Lin', self.MenuIDs['plot2sclinlin'], self._onViewMenu, 'radio'),
                                      ('Log-Lin', self.MenuIDs['plot2scloglin'], self._onViewMenu, 'radio'),
                                      ('Log-Log', self.MenuIDs['plot2scloglog'], self._onViewMenu, 'radio'),
                                      ('Lin-Log', self.MenuIDs['plot2sclinlog'], self._onViewMenu, 'radio'),
                                      ('Guinier', self.MenuIDs['plot2tyguinier'],self._onViewMenu, 'radio'),
                                      ('Kratky',  self.MenuIDs['plot2tykratky'], self._onViewMenu, 'radio'),
                                      ('Porod',   self.MenuIDs['plot2typorod'],  self._onViewMenu, 'radio')],
                    
                    'onlinemenu':    [('Offline', self.MenuIDs['goOffline'], self._onOnlineMenu, 'radio'),
                                      ('Online', self.MenuIDs['goOnline'], self._onOnlineMenu, 'radio')]}         
                                    
        
        menus = [('&File',    [('&Load Settings', self.MenuIDs['loadSettings'], self._onLoadMenu, 'normal'),
                               ('&Save Settings', self.MenuIDs['saveSettings'], self._onSaveMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('&Load Workspace', self.MenuIDs['loadWorkspace'], self._onLoadWorkspaceMenu, 'normal'),
                               ('&Save Workspace', self.MenuIDs['saveWorkspace'], self._onSaveWorkspaceMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('E&xit', self.MenuIDs['exit'], self._onFileMenu, 'normal')]),
                 
                 ('&Options', [('&Advanced Options...', self.MenuIDs['advancedOptions'], self._onOptionsMenu, 'normal'),
                              ('&Online mode', None, submenus['onlinemenu'], 'submenu')]),
                              
                 ('&View',    [
                               ('&Top Plot Axes', None, submenus['viewPlot1Scale'], 'submenu'),
                               ('&Bottom Plot Axes', None, submenus['viewPlot2Scale'], 'submenu')]),
                              
                 ('&Tools',   [('&Guinier fit...', self.MenuIDs['guinierfit'], self._onToolsMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('&Centering/Calibration...', self.MenuIDs['centering'], self._onToolsMenu, 'normal'),
                               ('&Masking...', self.MenuIDs['masking'], self._onToolsMenu, 'normal')
                              ]),
                              
                 ('&Help',    [('&Help!', self.MenuIDs['help'], self._onHelp, 'normal'),
                               (None, None, None, 'separator'),
                               ('&About', self.MenuIDs['about'], self._onAboutDlg, 'normal')])]
        
        menubar = wx.MenuBar()
        
        for each in menus:
         
            menuitem = self._createSingleMenuBarItem(each[1])
            menubar.Append(menuitem, each[0])    
            
        self.SetMenuBar(menubar)
        
    def _onToolsMenu(self, evt):
        
        id = evt.GetId()
        
        if id == self.MenuIDs['guinierfit']:
                        
            manippage = wx.FindWindowByName('ManipulationPanel')
            
            if len(manippage.getSelectedItems()) > 0:
                sasm = manippage.getSelectedItems()[0].getSASM()
                self.showGuinierFitFrame(sasm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select a plot from the plot list on the manipulation page.", "No plot selected")
                
        if id == self.MenuIDs['centering']:
            self.showCenteringPane()
        elif id == self.MenuIDs['masking']:
            self.showMaskingPane()
            
    def _onViewMenu(self, evt):
        
        val = evt.GetId()
        
        key = [k for k, v in self.MenuIDs.iteritems() if v == val][0]
        
        plotpanel = wx.FindWindowByName('PlotPanel')
        
        if key[0:7] == 'plot2sc':
            plotpanel.plotparams['axesscale2'] = key[-6:]
            plotpanel.plotparams['plot2type'] = 'subtracted'
            plotpanel.updatePlotAxes()
            plotpanel.updatePlotType(plotpanel.subplot2)
         
        elif key[0:7] == 'plot1sc':
            plotpanel.plotparams['axesscale1'] = key[-6:]
            plotpanel.plotparams['plot1type'] = 'normal'
            plotpanel.updatePlotAxes()
            plotpanel.updatePlotType(plotpanel.subplot1)
            
        elif key[0:7] == 'plot1ty':
            plotpanel.plotparams['plot1type'] = key[7:]
            
            if key[7:] == 'guinier':
                plotpanel.plotparams['axesscale1'] = 'loglin'
                plotpanel.updatePlotAxes()
            
            elif key[7:] == 'kratky' or key[7:] == 'porod':
                plotpanel.plotparams['axesscale1'] = 'linlin'
                plotpanel.updatePlotAxes()
                
            plotpanel.updatePlotType(plotpanel.subplot1)
            
    
        elif key[0:7] == 'plot2ty':
            plotpanel.plotparams['plot2type'] = key[7:]
            
            
            if key[7:] == 'guinier':
                plotpanel.plotparams['axesscale2'] = 'loglin'
                plotpanel.updatePlotAxes()
                
            elif key[7:] == 'kratky' or key[7:] == 'porod':
                plotpanel.plotparams['axesscale2'] = 'linlin'
                plotpanel.updatePlotAxes()
            
            plotpanel.updatePlotType(plotpanel.subplot2)
    
    def _onSaveMenu(self, event):
        self._onSaveSettings(None)

    def _onOnlineMenu(self, event):
        
        wx.MessageBox('Feature still under construction', 'Feature not available')
        
#        id = event.GetId()
#        
#        if id == self.MenuIDs['goOnline']:
#            state = 'Online'
#        else:
#            state = 'Offline'
#        
#        self.OnlineControl.OnOnlineButton(state)
        
    def _onOptionsMenu(self, event):
        
        if event.GetId() == self.MenuIDs['advancedOptions']:
            self.showOptionsDialog()
    
    def _onFileMenu(self, event):
        
        if event.GetId() == self.MenuIDs['exit']:
            self._onCloseWindow(0)
            
    def _onLoadMenu(self, event):
        self._onLoadSettings(None)
    
    def _onLoadSettings(self, evt):   
        
        file = self._createFileDialog(wx.OPEN)
        
        if file:
            success = RAWSettings.loadSettings(self.raw_settings, file)
            
            if success:
                self.raw_settings.set('CurrentCfg', file)
            
            
    def _onSaveSettings(self, evt):   
        file = self._createFileDialog(wx.SAVE)
        
        if file:
            
            if os.path.splitext(file)[1] != '.cfg':
                file = file + '.cfg'
            
            success = RAWSettings.saveSettings(self.raw_settings, file)
            
            if success:
                self.raw_settings.set('CurrentCfg', file)
                
    def _onLoadWorkspaceMenu(self, evt):
        manip_panel = wx.FindWindowByName('ManipulationPanel')
        
        all_items = manip_panel.getItems()
        
        file = self._createFileDialog(wx.OPEN, 'Workspace files', '*.wsp')
        
        if file:
            if os.path.splitext(file)[1] != '.wsp':
                file = file + '.wsp'
        
            mainworker_cmd_queue.put(['load_workspace', [file]])
    
    def _onSaveWorkspaceMenu(self, evt):
        self.saveWorkspace()
        
    def saveWorkspace(self):
        
        manip_panel = wx.FindWindowByName('ManipulationPanel')
        
        all_items = manip_panel.getItems()
        
        file = self._createFileDialog(wx.SAVE, 'Workspace files', '*.wsp')
        
        if file:
            if os.path.splitext(file)[1] != '.wsp':
                file = file + '.wsp'
        
            mainworker_cmd_queue.put(['save_workspace', [all_items, file]])
    
    
    def showOptionsDialog(self, focusIdx = None):
        
        if focusIdx != None:
            dialog =RAWOptions.OptionsDialog(self, self.raw_settings, focusIndex = focusIdx)
        else:
            dialog = RAWOptions.OptionsDialog(self, self.raw_settings)
        
        dialog.ShowModal()
        
    def getMenuIds(self):
        return self.MenuIDs
    
    def setViewMenuScale(self, id):
        self.MenuBar.FindItemById(id).Check(True)
    
    def _onAboutDlg(self, event):
        info = wx.AboutDialogInfo()
        info.Name = "RAW"
        info.Version = "0.99.8.4 Beta"
        info.Copyright = "Copyright(C) 2009 RAW"
        info.Description = "RAW is a software package primarily for SAXS 2D data reduction and 1D data analysis.\nIt provides an easy GUI for handling multiple files fast, and a\ngood alternative to commercial or protected software packages for finding\nthe Pair Distance Distribution Function\n\nPlease cite:\nBioXTAS RAW, a software program for high-throughput automated small-angle\nX-ray scattering data reduction and preliminary analysis, J. Appl. Cryst. (2009). 42, 959-964"

        info.WebSite = ("http://bioxtasraw.sourceforge.net/", "The RAW Project Homepage")
        info.Developers = [u"Soren S. Nielsen", u"Richard E. Gillilan", u"Jesper Nygaard"]
        info.License = "This program is free software: you can redistribute it and/or modify it under the terms of the\nGNU General Public License as published by the Free Software Foundation, either version 3\n of the License, or (at your option) any later version.\n\nThis program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;\nwithout even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\nSee the GNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License along with this program.\nIf not, see http://www.gnu.org/licenses/"
        
        # Show the wx.AboutBox
        wx.AboutBox(info)
        
    def _onCloseWindow(self, event):
        self.Destroy()
        
        file = 'rawcfg.dat'
        
        try:
            file_obj = open(file, 'w')
        
            path = wx.FindWindowByName('DirCtrlPanel').path
            saveInfo = {'workdir' : path,
                        'ImageFormat' : self.GetParameter('ImageFormat')}
        
            cPickle.dump(saveInfo, FileObj)
            FileObj.close()
        except:
            pass
        
    def _createFileDialog(self, mode, name = 'Config files', ext = '*.cfg'):
        
        file = None
        
        path = wx.FindWindowByName('FileListCtrl').path
        
        if mode == wx.OPEN:
            filters = name + ' (' + ext + ')|' + ext + '|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters, defaultDir = path)
        if mode == wx.SAVE:
            filters = name + ' ('+ext+')|'+ext
            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters, defaultDir = path)        
        
        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            
        # Destroy the dialog
        dialog.Destroy()
        
        return file
        
class OnlineController:                                   
    def __init__(self, parent):
        
        self.parent = parent
        
        # Setup the online file checker timer
        self.online_timer = wx.Timer()
        
        self.online_timer.Bind(wx.EVT_TIMER, self.onOnlineTimer)

        self.old_dir_list = []
        self.is_online = False
        self.seek_dir = []
        self.bg_filename = None
   
    def onOnlineTimer(self, evt):
        ''' This function checks for new files and processes them as they come in '''
        
        info_panel = wx.FindWindowByName('InfoPanel')
        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        dir_list = os.listdir(self.seekDir)
                
        if dir_list != self.old_dir_list:

            for idx in range(0, len(dir_list)):

                try:
                    chk = self.old_dir_list.index(dir_list[idx])
                except ValueError:
                    
                    self.old_dir_list.append(dir_list[idx])
                    dirctrl.filterFileListAndUpdateListBox()
                                    
                    info_panel.writeText('Incomming file:\n' + str(dir_list[idx] + '\n\n'))
                    filepath = os.path.join(self.seek_dir, str(dir_list[idx]))

                    if not(self._fileTypeIsExcluded(filepath)):
                        self.processIncommingFile(filepath)


class MainWorkerThread(threading.Thread):
    
    def __init__(self, parent, raw_settings):
        
        threading.Thread.__init__(self)
        
        self._raw_settings = raw_settings
        self._parent = parent
        self._abort = False
        
        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')
        self.plot_panel = wx.FindWindowByName('PlotPanel')
        self.image_panel = wx.FindWindowByName('ImagePanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        
        self._commands = {'plot' : self._loadAndPlot,
                                    'show_image'            : self._loadAndShowImage,
                                    'subtract_filenames'    : self._subtractFilenames,
                                    'subtract_items'        : self._subtractItems,
                                    'average_items'         : self._averageItems,
                                    'save_items'            : self._saveItems,
                                    'quick_reduce'          : self._quickReduce,
                                    'load_mask'             : self._loadMaskFile,
                                    'save_mask'             : self._saveMaskFile,
                                    'create_mask'           : self._createMask,
                                    'recreate_all_masks'    : self._recreateAllMasks,
                                    'calculate_abs_water_const' : self._calcAbsScWaterConst,
                                    'save_workspace'        : self._saveWorkspace,
                                    'load_workspace'        : self._loadWorkspace,
                                    'superimpose_items'     : self._superimposeItems,
                                    'save_analysis_info'    : self._saveAnalysisInfo,
                                    'merge_items'           : self._mergeItems,
                                    'rebin_items'           : self._rebinItems}
         
        
    def run(self):
        
        while True:
            try:
                command, data = mainworker_cmd_queue.get()
            except Queue.Empty:
                command = None
                
            if command != None:
                
                if self._abort == True:
                    self._cleanUpAfterAbort()
                else:
                    self._commands[command](data)
        
    def _cleanUpAfterAbort(self):
        pass
    
    def _sendSASMToPlot(self, sasm, axes_num = 1, item_colour = 'black', line_color = None, no_update = False):
        wx.CallAfter(self.plot_panel.plotSASM, sasm, axes_num, color = line_color)
        
        if no_update == False:
            wx.CallAfter(self.plot_panel.fitAxis)
                    
        wx.CallAfter(self.manipulation_panel.addItem, sasm, item_colour)
                
        
    def _sendImageToDisplay(self, img, sasm):
        wx.CallAfter(self.image_panel.showImage, img, sasm)
    
    ################################
    # COMMANDS:
    ################################
    
    def _calcAbsScWaterConst(self, data):
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading files and calculating the absolute scale constant...')
    
        abs_scale_constant = 1.0
        water_filename = data[0]
        empty_filename = data[1]
        waterI0 = data[2]

        try:
            filename = water_filename
            water_sasm, img = SASFileIO.loadFile(filename, self._raw_settings, no_processing = True)
            filename = empty_filename
            empty_sasm, img = SASFileIO.loadFile(filename, self._raw_settings, no_processing = True)
                        
            abs_scale_constant = SASM.calcAbsoluteScaleWaterConst(water_sasm, empty_sasm, waterI0, self._raw_settings)
        except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
            self._showDataFormatError(os.path.split(filename)[1])    
        except SASExceptions.DataNotCompatible, msg:
            self._showSubtractionError(water_sasm, empty_sasm)

        wx.CallAfter(self.main_frame.closeBusyDialog) 
        question_return_queue.put(abs_scale_constant)
         
    def _saveMaskFile(self, data):
        
        fullpath_filename = data[0]
        
        masks = data[1]
        
        path, ext = os.path.splitext(fullpath_filename)
        
        if ext != '.msk':
            fullpath_filename = fullpath_filename + '.msk'
                    
        file_obj = open(fullpath_filename, 'w')
        cPickle.dump(masks, file_obj)
        file_obj.close()
    
        #wx.CallAfter(wx.MessageBox, 'The mask has been saved.', 'Mask Saved')
        img_dim = self.image_panel.img.shape
        #wx.CallAfter(RAWImage.showUseMaskDialog, fullpath_filename, img_dim)
        
    
    def _loadMaskFile(self, data):        
            wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading and creating mask...')

            fullpath_filename = data[0]
            
            filenamepath, extension = os.path.splitext(fullpath_filename)
        
            if extension == '.msk':
                file_obj = open(fullpath_filename, 'r')
                masks = cPickle.load(file_obj)
                file_obj.close()
        
                i=0
                for each in masks:
                    each.maskID = i
                    i = i + 1
                        
                plot_param = self.image_panel.getPlotParameters()
                plot_param['storedMasks'] = masks
                self.image_panel.setPlotParameters(plot_param)

                #Plot mask on load:                
#                parameters = {'filename' : os.path.split(filenamepath)[1],
#                              'imageHeader' : []}
#                bogus_sasm= SASM.SASM([0,1], [0,1], [0,1], parameters)
#                wx.CallAfter(self.image_panel.showImage,mask, bogus_sasm)

                wx.CallAfter(self.image_panel.plotStoredMasks)
                       
            wx.CallAfter(self.main_frame.closeBusyDialog)
    
    def _recreateAllMasks(self, data):
        
        mask_dict = self._raw_settings.get('Masks')
        img_dim = self._raw_settings.get('MaskDimension')
        
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while creating all masks...')
        
        for each_key in mask_dict.keys():
            masks = mask_dict[each_key][1]
            
            if masks != None:
                mask_img = SASImage.createMaskMatrix(img_dim, masks)
                mask_param = mask_dict[each_key]
                mask_param[0] = mask_img
                mask_param[1] = masks
        
        wx.CallAfter(self.main_frame.closeBusyDialog)
    
    def _createMask(self, data):
        
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while creating the mask...')
        
        mask_key = data[0]
        masks = data[1]
        img_dim = data[2]
        
        mask_img = SASImage.createMaskMatrix(img_dim, masks)
        
        self._raw_settings.set('MaskDimension', img_dim)
        mask_dict = self._raw_settings.get('Masks')
        mask_param = mask_dict[mask_key]
        
        mask_param[0] = mask_img
        mask_param[1] = masks
                
        wx.CallAfter(self.main_frame.closeBusyDialog)
        wx.CallAfter(wx.MessageBox, 'The mask has been created and enabled.', 'Mask creation finished', style = wx.ICON_INFORMATION)
        
    def _loadAndPlot(self, filename_list):     
       
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while plotting...')
       
        try:
            for each_filename in filename_list:
                sasm, img = SASFileIO.loadFile(each_filename, self._raw_settings)
                
                if img != None:
                    qrange = sasm.getQrange()
                    start_point = self._raw_settings.get('StartPoint')
                    qrange = (start_point, len(sasm.getBinnedQ()))
                    sasm.setQrange(qrange)
                
                self._sendSASMToPlot(sasm, no_update = True)
                
        except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
            self._showDataFormatError(os.path.split(each_filename)[1])
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        except SASExceptions.HeaderLoadError, msg:
            wx.CallAfter(wx.MessageBox, str(msg), 'Error Loading Headerfile', style = wx.ICON_ERROR)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
            
        if len(filename_list) == 1 and  img != None:
            self._sendImageToDisplay(img, sasm)
        
        wx.CallAfter(self.main_frame.plot_notebook.SetSelection, 0)
        file_list = wx.FindWindowByName('FileListCtrl')
        wx.CallAfter(file_list.SetFocus)
        
        wx.CallAfter(self.plot_panel.updateLegend, 1)
        wx.CallAfter(self.plot_panel.fitAxis)
        wx.CallAfter(self.main_frame.closeBusyDialog)
        
    def _loadAndShowImage(self, filename):
        
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading image...')
       
        img_fmt = self._raw_settings.get('ImageFormat')
        
        try:
            if not os.path.isfile(filename):
                raise SASExceptions.WrongImageFormat('not a valid file!')
            
            img, imghdr = SASFileIO.loadImage(filename, img_fmt)
            
            if img == None:
                raise SASExceptions.WrongImageFormat('not a valid file!')
                
        except SASExceptions.WrongImageFormat, msg:
            self._showDataFormatError(os.path.split(filename)[1], include_ascii = False)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        
        parameters = {'filename' : os.path.split(filename)[1],
                      'imageHeader' : imghdr}
        
        bogus_sasm= SASM.SASM([0,1], [0,1], [0,1], parameters)
        
        self._sendImageToDisplay(img, bogus_sasm)
        wx.CallAfter(self.main_frame.plot_notebook.SetSelection, 1)
        file_list = wx.FindWindowByName('FileListCtrl')
        wx.CallAfter(file_list.SetFocus)
        wx.CallAfter(self.main_frame.closeBusyDialog)
    
    def _calibrateSASM(self, sasm):
    
        #if self._raw_settings.get('CalibrateMan'):
        sd_distance = self._raw_settings.get('SampleDistance')
        pixel_size = self._raw_settings.get('DetectorPixelSize')
        wavelength = self._raw_settings.get('WaveLength')
        
        sasm.calibrateQ(sd_distance, pixel_size, wavelength)
        
    def _showDataFormatError(self, filename, include_ascii = True):
        img_fmt = self._raw_settings.get('ImageFormat')
        
        if include_ascii:
            ascii = ' or any of the supported ASCII formats'
        else:
            ascii = ''
        
        wx.CallAfter(wx.MessageBox, 'The selected file: ' + filename + '\ncould not be recognized as a '   + str(img_fmt) +
                         ' image format' + ascii + '.\n\nYou can change the image format under Advanced Options in the Options menu.' ,
                          'Error loading file', style = wx.ICON_ERROR)
        
    def _showSubtractionError(self, sasm, sub_sasm):
        filename1 = sasm.getParameter('filename')
        q1_min, q1_max = sasm.getQrange()
        points1 = len(sasm.i[q1_min:q1_max])
        filename2 = sub_sasm.getParameter('filename')
        q2_min, q2_max = sub_sasm.getQrange()
        points2 = len(sub_sasm.i[q2_min:q2_max])
        wx.CallAfter(wx.MessageBox, filename1 + ' has ' + str(points1) + ' data points.\n'  +
            filename2 + ' has ' + str(points2) + ' data points.\n\n' +
            'Subtraction is not possible. Data files must have equal number of points.', 'Subtraction Error')
        
    def _showAverageError(self, err_no):
        
        if err_no == 1:
            wx.CallAfter(wx.MessageBox, 'The selected items must have the same total number of points to be averaged.', 'Average Error')
        elif err_no == 2:
            wx.CallAfter(wx.MessageBox, 'Please select at least two items to be averaged.' , 'Average Error')
    
    def _showPleaseSelectItemsError(self, type):
        
        if type == 'average':
            wx.CallAfter(wx.MessageBox, 'Please select the items you want to average.\n\nYou can select multiple items by holding down the CTRL or SHIFT key.' , 'No items selected')
        if type == 'subtract': 
            wx.CallAfter(wx.MessageBox, 'Please select the items you want the marked (star) item subtracted from.'+
                              '\nUse CTRL or SHIFT to select multiple items.', 'No items selected')
        if type == 'superimpose':
            wx.CallAfter(wx.MessageBox, 'Please select the items you want to superimpose.\n\nYou can select multiple items by holding down the CTRL or SHIFT key.' , 'No items selected')            
           
    def _showPleaseMarkItemError(self, type):
        
        if type == 'subtract':
            wx.CallAfter(wx.MessageBox, 'Please mark (star) the item you are using for subtraction', 'No item marked')
        if type == 'merge':
            wx.CallAfter(wx.MessageBox, 'Please mark (star) the item you are using as the main curve for merging', 'No item marked')
        if type == 'superimpose':
            wx.CallAfter(wx.MessageBox, 'Please mark (star) the item you want to superimpose to.', 'No item marked')
            
    def _showQvectorsNotEqualWarning(self, sasm, sub_sasm):
        
        sub_filename = sub_sasm.getParameter('filename')
        filename = sasm.getParameter('filename')
        
        button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO), ('Cancel', wx.ID_CANCEL)]
        question = 'Q vectors for ' + str(filename) + ' and ' + str(sub_filename) + ' are not the same.\nDo you wish to continue?'
        label = 'Q vectors do not match'
        icon = wx.ART_WARNING
        
        answer = self._displayQuestionDialog(question, label, button_list, icon)
        
        return answer
    
    def _showQuickReduceFinished(self, processed_files, number_of_files):
        wx.CallAfter(wx.MessageBox, 'Quick reduction finished. Processed ' + str(processed_files) + ' out of ' + str(number_of_files) + ' files.', 'Quick reduction finished', style = wx.ICON_INFORMATION)
        
    def _showOverwritePrompt(self, filename, save_path):
        
        button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO), 
                       ('No to all', wx.ID_NOTOALL), ('Rename', wx.ID_EDIT), ('Cancel', wx.ID_CANCEL)]
        
        path = os.path.join(save_path, filename)
        
        question = 'Filename: ' + str(path) + '\nalready exists. Do you wish to overwrite the existing file?'
        label = 'File exists'
        icon = wx.ART_WARNING
        
        answer = self._displayQuestionDialog(question, label, button_list, icon, filename, save_path)
        
        return answer
        
    def _displayQuestionDialog(self, question, label, button_list, icon = None, filename = None, save_path = None):
        
        wx.CallAfter(self.main_frame.showQuestionDialogFromThread, question, label, button_list, icon, filename, save_path)
     
        thread_wait_event.wait()
        thread_wait_event.clear()
        
        answer = question_return_queue.get()
        question_return_queue.task_done()
        
        return answer    
                    
    def _subtractFilenames(self):
        pass
    
    def _quickReduce(self, data):
        
        save_path = data[0]
        load_path = data[1]
        filename_list = data[2]
        format_ext = data[3]
        
        yes_to_all = False
        no_to_all = False
        processed_files = 0
        
        for each_filename in filename_list:
                
            full_load_path = os.path.join(load_path, each_filename)
            no_ext_filename, ext = os.path.splitext(each_filename)
                
            check_filename = no_ext_filename + format_ext
            check_path = os.path.join(save_path, check_filename)
                
            if os.path.exists(check_path) and yes_to_all == False:
                
                if no_to_all == True:
                    result = wx.ID_NO
                else:
                    result = self._showOverwritePrompt(check_filename, save_path)
                    
                if result[0] == wx.ID_NOTOALL:
                    no_to_all = True
            
                if result[0] == wx.ID_YESTOALL:
                    yes_to_all = True
                
                if result[0] == wx.ID_YES or result[0] == wx.ID_YESTOALL or result[0] == wx.ID_EDIT:
                    try:
                        sasm, img = SASFileIO.loadFile(full_load_path, self._raw_settings)
                        
                        if result[0] == wx.ID_EDIT:
                            final_save_path, new_filename = os.path.split(result[1][0])                
                            sasm.setParameter('filename', new_filename)
                        else:
                            final_save_path = save_path
                        
                        if img != None:
                            SASFileIO.saveMeasurement(sasm, final_save_path)
                            processed_files += 1
                        else:
                            self._showDataFormatError(os.path.split(each_filename)[1], include_ascii = False)
                    except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
                        self._showDataFormatError(os.path.split(each_filename)[1], include_ascii = False)
            
            else:
                try:
                    sasm, img = SASFileIO.loadFile(full_load_path, self._raw_settings)
                    
                    if img != None:
                        SASFileIO.saveMeasurement(sasm, save_path)
                        processed_files += 1
                    else:
                        self._showDataFormatError(os.path.split(each_filename)[1], include_ascii = False)
                except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
                    self._showDataFormatError(os.path.split(each_filename)[1], include_ascii = False)
                        
        self._showQuickReduceFinished(processed_files, len(filename_list))
    
    
    def _superimposeItems(self, data):
        
        star_item = data[0]
        selected_items = data[1]
        
        if star_item == None:
            self._showPleaseMarkItemError('superimpose')
            return 
        
        if star_item in selected_items:
            selected_items.remove(star_item)
         
        if len(selected_items) == 0:
            self._showPleaseSelectItemsError('superimpose')
            return
        
        selected_sasms = []
        for each_item in selected_items:
            selected_sasms.append(each_item.getSASM())
            
        SASM.superimpose(star_item.getSASM(), selected_sasms)
        
        for each_item in selected_items:
            each_item.updateControlsFromSASM()
        
        wx.CallAfter(self.plot_panel.updatePlotAfterManipulation, selected_sasms)
    
    def _subtractItems(self, data):
        ''' subtracts the marked item from other selected items in the
        manipulation list '''

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while subtracting and plotting...')

        marked_item = data[0]
        selected_items = data[1]
        
        if marked_item == None:
            self._showPleaseMarkItemError('subtract')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        elif len(selected_items) == 0:
            self._showPleaseSelectItemsError('subtract')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        
        sub_sasm = marked_item.getSASM()
        
        yes_to_all = False
        for each in selected_items:
            result = wx.ID_YES
            sasm = each.getSASM()
            
            qmin, qmax = sasm.getQrange()
            sub_qmin, sub_qmax = sub_sasm.getQrange()
               
            if numpy.all(sasm.q[qmin:qmax] == sub_sasm.q[sub_qmin:sub_qmax]) == False and yes_to_all == False:
                result = self._showQvectorsNotEqualWarning(sasm, sub_sasm)[0]
    
                if result == wx.ID_YESTOALL:
                    yes_to_all = True
                elif result == wx.ID_CANCEL:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                    return
                
            try:
                if result == wx.ID_YES or result == wx.ID_YESTOALL:
                    subtracted_sasm = SASM.subtract(sasm, sub_sasm)
                    
                    filename = subtracted_sasm.getParameter('filename')
                    subtracted_sasm.setParameter('filename', 'S_' + filename)
                    
                    self._sendSASMToPlot(subtracted_sasm, axes_num = 2, item_colour = 'red')
            except SASExceptions.DataNotCompatible, msg:
               self._showSubtractionError(sasm, sub_sasm)
               wx.CallAfter(self.main_frame.closeBusyDialog)
               return
        
        wx.CallAfter(self.plot_panel.updateLegend, 2)
        wx.CallAfter(self.main_frame.closeBusyDialog)
                
    def _averageItems(self, item_list):
        
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while averaging and plotting...')
        
        sasm_list = []
                
        if len(item_list) < 2:
            self._showAverageError(2)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        
        for each_item in item_list:
            sasm_list.append(each_item.getSASM())
            
        try:
            avg_sasm = SASM.average(sasm_list)
        except SASExceptions.DataNotCompatible:
            self._showAverageError(1)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        
        filename = avg_sasm.getParameter('filename')
        avg_sasm.setParameter('filename', 'A_' + filename)
        
        self._sendSASMToPlot(avg_sasm, axes_num = 1, item_colour = 'green')
        
        wx.CallAfter(self.plot_panel.updateLegend, 1)
        wx.CallAfter(self.main_frame.closeBusyDialog)
        
    
    def _rebinItems(self, data):
        
        selected_items = data[0]
        rebin_factor = data[1]
        
        
    
    def _mergeItems(self, data):
        
        marked_item = data[0]
        selected_items = data[1]
        
        if marked_item in selected_items:
            idx = selected_items.index(marked_item)
            selected_items.pop(idx)
        
        if marked_item == None:
            self._showPleaseMarkItemError('merge')
            return 
        
        marked_sasm = marked_item.getSASM()    
        sasm_list = []
        for each_item in selected_items:
            sasm_list.append(each_item.getSASM())
        
        merged_sasm = SASM.merge(marked_sasm, sasm_list)
        
        filename = marked_sasm.getParameter('filename')
        merged_sasm.setParameter('filename', 'M_' + filename)
        
        self._sendSASMToPlot(merged_sasm, axes_num = 1)
        
        wx.CallAfter(self.plot_panel.updateLegend, 1)
        #wx.CallAfter(self.main_frame.closeBusyDialog)
               
    def _saveSASM(self, sasm, filetype = 'dat'):
        pass
    
#    def _saveAnalysisInfo(self, data):
#        
#        all_items = data[0]
#        save_path = data[1]
#        
#        selected_sasms = []
#        
#        check_filename, ext = os.path.splitext(save_path)
#        save_path = check_filename + '.csv'
#        
#        for each_item in all_items:
#            sasm = each_item.getSASM()
#            selected_sasms.append(sasm)
#            
#            analysis_dict = sasm.getParameter('analysis')
#            
#            if analysis_dict.keys() == []:
#                wx.CallAfter(wx.MessageBox, 'No analysis information was found for file: ' + sasm.getParameter('filename') + '\n\nSave was aborted.', 'Analysis information not found', style = wx.ICON_EXCLAMATION)
#                return
#        
#        result = SASFileIO.saveAnalysisCsvFile(selected_sasms, save_path)
        
    def _saveAnalysisInfo(self, data):
        
        all_items = data[0]
        include_data = data[1]
        save_path = data[2]
        
        selected_sasms = []
        
        check_filename, ext = os.path.splitext(save_path)
        save_path = check_filename + '.csv'
        
        for each_item in all_items:
            sasm = each_item.getSASM()
            selected_sasms.append(sasm)
            
#            if analysis_dict.keys() == []:
#                wx.CallAfter(wx.MessageBox, 'No analysis information was found for file: ' + sasm.getParameter('filename') + '\n\nSave was aborted.', 'Analysis information not found', style = wx.ICON_EXCLAMATION)
#                return
        
        result = SASFileIO.saveAnalysisCsvFile(selected_sasms, include_data, save_path)
        
        
    def _saveWorkspace(self, data):
        
        all_items = data[0]
        save_path = data[1]
         
        save_dict = {}
        
        for idx in range(0, len(all_items)):
            
            sasm = all_items[idx].getSASM()
            sasm_dict = sasm.extractAll()
        
            sasm_dict['line_color'] = sasm.line.get_color()
            sasm_dict['item_controls_visible'] = sasm.item_panel.getControlsVisible()
            sasm_dict['item_font_color'] = sasm.item_panel.getFontColour()
            sasm_dict['item_selected_for_plot'] = sasm.item_panel.getSelectedForPlot()
            
            sasm_dict['parameters_analysis'] = sasm_dict['parameters']['analysis']  #pickle wont save this unless its raised up
    
            if sasm.axes == sasm.plot_panel.subplot1:
                sasm_dict['plot_axes'] = 1
            else:
                sasm_dict['plot_axes'] = 2
            
            save_dict[idx] = sasm_dict
        
        SASFileIO.saveWorkspace(save_dict, save_path)
        
        global workspace_saved
        workspace_saved = True
        
    def _loadWorkspace(self, data):
        
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading workspace...')
        
        load_path = data[0]
        
        sasm_dict = SASFileIO.loadWorkspace(load_path)
        
        for each_key in sasm_dict.keys():
            sasm_data = sasm_dict[each_key]
            
            new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'], sasm_data['err_raw'], sasm_data['parameters'])
            new_sasm.setBinnedI(sasm_data['i_binned'])
            new_sasm.setBinnedQ(sasm_data['q_binned'])
            new_sasm.setBinnedErr(sasm_data['err_binned'])
            
            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                                    sasm_data['norm_factor'], sasm_data['q_scale_factor'],
                                    sasm_data['bin_size'])
            
            new_sasm.setQrange(sasm_data['selected_qrange'])
            
            try:
                new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
            except KeyError:
                pass
            
            new_sasm._update()

            wx.CallAfter(self.plot_panel.plotSASM, new_sasm,
                          sasm_data['plot_axes'],
                          color = sasm_data['line_color'])
                            
            wx.CallAfter(self.manipulation_panel.addItem, new_sasm,
                          item_colour = sasm_data['item_font_color'])
            
        wx.CallAfter(self.plot_panel.updateLegend, 1)
        wx.CallAfter(self.plot_panel.updateLegend, 2)
        wx.CallAfter(self.plot_panel.fitAxis)
        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _backupWorkspace(self, data):
        all_items = data[0]
        
        backupfile = os.path.join(RAWWorkDir, '_wspBackup.wsp')
        
        data_out = [all_items, backupfile]
        
        self._saveWorkspace(data_out)
    
    def _backupSettings(self, data):
        pass 

    def _saveItems(self, data):
        
        save_path = data[0]
        item_list = data[1]
        
        overwrite_all = False
        no_to_all = False
        for item in item_list:
            sasm = item.sasm
            
            filename = sasm.getParameter('filename')
            
            check_filename, ext = os.path.splitext(filename)
            check_filename = check_filename + '.dat'
            
            filepath = os.path.join(save_path, check_filename)
            file_exists = os.path.isfile(filepath)
            filepath = save_path
            
            if file_exists and overwrite_all == False:
                
                if no_to_all == False:
                    result = self._showOverwritePrompt(check_filename, save_path)
                    
                    if result[0] == wx.ID_CANCEL:
                        return
                
                    if result[0] == wx.ID_EDIT: #rename
                        filepath = result[1][0]
                        filepath, new_filename = os.path.split(filepath)
                        sasm.setParameter('filename', new_filename)
                        wx.CallAfter(sasm.item_panel.updateFilenameLabel)
                        
                    if result[0] == wx.ID_YES or result[0] == wx.ID_YESTOALL or result[0] == wx.ID_EDIT: 
                        SASFileIO.saveMeasurement(sasm, filepath)
                    
                    if result[0] == wx.ID_YESTOALL:
                        overwrite_all = True
                        
                    if result[0] == wx.ID_NOTOALL:
                        no_to_all = True
                
            else:
                SASFileIO.saveMeasurement(sasm, filepath)
            

#--- ** Info Panel **

class InfoPanel(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent, name = 'InfoPanel')
        
        infoSizer = wx.BoxSizer()
        
        self.infoTextBox = wx.TextCtrl(self, -1, 'Welcome to RAW 0.99.8.4b!\n--------------------------------\n\n', style = wx.TE_MULTILINE)
        
        self.infoTextBox.SetBackgroundColour('WHITE')
        self.infoTextBox.SetForegroundColour('BLACK')
        
        infoSizer.Add(self.infoTextBox, 1, wx.EXPAND)
        
        self.SetSizer(infoSizer)
        
    def WriteText(self, text):
        
        self.infoTextBox.AppendText(text)
        
    def Clear(self):
        
        self.infoTextBox.Clear()
        
#***************        
#--- ** File Panel **
#***************
                             
class FilePanel(wx.Panel):
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent, size = (400,600), name = 'FilePanel')
        
        self.plot_panel = wx.FindWindowByName('PlotPanel')
        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.image_panel = wx.FindWindowByName('ImagePanel')
        
        # *************** buttons ****************************
        self.dir_panel = DirCtrlPanel(self)
        
        self.button_data = ( ("Quick Reduce", self._onReduceButton),
                           ("Plot", self._onPlotButton),
                           ("Clear All", self._onClearAllButton),
                           ("Execute", self._onViewButton),
                           ("Show Image", self._onShowImageButton),
                           ("", self._onSubtractButton))

        self.NO_OF_BUTTONS_IN_EACH_ROW = 3
        
        #bg_label_sizer = self._createBackgroundFileLabels()
        button_sizer = self._createButtons()
        
        # *************** Directory Control ***********************
        b2sizer = wx.BoxSizer(wx.VERTICAL) 
        b2sizer.Add((10,10), 0)
       # b2sizer.Add(bg_label_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE, 10) 
        b2sizer.Add((5,5))
        b2sizer.Add(self.dir_panel, 1, wx.EXPAND| wx.LEFT | wx.RIGHT, 10)
        b2sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)                      

        self.SetSizer(b2sizer)
        
    def _createBackgroundFileLabels(self):
        box = wx.StaticBox(self, -1, 'Background File:')
        bg_label_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        bg_filename = wx.StaticText(self, -1, 'None')
        bg_filename.SetMinSize((230,20))
        
        bg_label_sizer.Add(bg_filename, 1, wx.EXPAND)
        
        return bg_label_sizer
        
    def _createButtons(self):
        no_of_buttons = len(self.button_data)
        no_of_rows = int(math.ceil(no_of_buttons / self.NO_OF_BUTTONS_IN_EACH_ROW))
        
        button_sizer = wx.GridSizer( cols = self.NO_OF_BUTTONS_IN_EACH_ROW, rows = no_of_rows, hgap = 3, vgap = 3)
        
        for button_txt, bindfunc in self.button_data:
            button = wx.Button(self, -1, button_txt)
            button.Bind(wx.EVT_BUTTON, bindfunc)    
            button_sizer.Add(button, 1, wx.ALIGN_CENTER | wx.EXPAND)
            
            #################################################3
            if button_txt == '' or button_txt == 'Average':
                #button.Enable(False)
                pass
                
        return button_sizer    
        
    def _onViewButton(self, event):
        
        filelist = wx.FindWindowByName('FileListCtrl')
        filelist.openFileInExternalViewer() 
        #wx.CallAfter(self.main_frame.test2)
        
#        dlg = TestDialog2(self, -1)
#        dlg.ShowModal()
#        dlg.Destroy()
#        plot_panel = wx.FindWindowByName('PlotPanel')
#        ax = plot_panel.subplot1
#        plot_panel._insertLegend(ax)
#        

        
    def _onPlotButton(self, event):
        
        files = []
        
        for each_filename in self.dir_panel.file_list_box.getSelectedFilenames():
            path = os.path.join(self.dir_panel.file_list_box.path, each_filename)
            files.append(path)
            
        mainworker_cmd_queue.put(['plot', files])
    
    def _onClearAllButton(self, event):
        
        global workspace_saved

        if workspace_saved == False:
            dial = SaveDialog(self, -1, 'Workspace not saved', 'The workspace has been modified, do you want to save your changes?')
        else: 
            dial = wx.MessageDialog(self, 'Are you sure you want to clear everything?', 'Are you sure?', 
                                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        
        answer = dial.ShowModal()
        dial.Destroy()
        
        if answer == wx.ID_CANCEL or answer == wx.ID_NO:
            return
        if answer == wx.ID_SAVE:
            self.main_frame.saveWorkspace()
            
        else:
            self.plot_panel.clearAllPlots()
            self.image_panel.clearFigure()
            self.manipulation_panel.clearList()
        
        info_panel = wx.FindWindowByName('InformationPanel')
        info_panel.clearInfo()
    
    def _onReduceButton(self, event):
        
        selected_files = self.dir_panel.file_list_box.getSelectedFilenames()
        
        load_path = self.dir_panel.getDirLabel()
        
        dlg = QuickReduceDialog(self, load_path, selected_files)
        result = dlg.ShowModal()

        if result == wx.ID_OK:
            save_path = dlg.getPath()
        else:
            return
        
        dlg.Destroy()
        
        mainworker_cmd_queue.put(['quick_reduce', [save_path, load_path, selected_files, '.dat']])
        
        
    def _onShowImageButton(self, event):
        
        if len(self.dir_panel.file_list_box.getSelectedFilenames()) > 0:
            filename = self.dir_panel.file_list_box.getSelectedFilenames()[0]        
            path = os.path.join(self.dir_panel.file_list_box.path, filename)
            mainworker_cmd_queue.put(['show_image', path])
        
    def _onSubtractButton(self, event):
        #wx.CallAfter(self.main_frame.showCenteringPane)
        
        #RAWSettings.loadSettings(self.main_frame.raw_settings, 'testdat.dat')
        
        dlg = SaveAnalysisInfoDialog(self)
        dlg.ShowModal()

class CustomListCtrl(wx.ListCtrl):

    def __init__(self, parent, id):
        wx.ListCtrl.__init__(self, parent, id, style = wx.LC_REPORT, name = 'FileListCtrl')
        
        self.path = os.getcwd()
        self.files = []
        self.parent = parent
        
        self.filteredFilesList = []
        self.dirsList = []
        
        self.dirctrl_panel = parent 
        
        self.copylist = []
        self.cut_selected = False
        self.copy_selected = False
        
        self.file_panel = wx.FindWindowByName('FilePanel')
        
        images = ['Up.png', 'Folder.png', 'document.png']
        
        self.InsertColumn(0, 'Name')
        self.InsertColumn(1, 'Ext')
        self.InsertColumn(2, 'Modified')
        self.InsertColumn(3, 'Size', wx.LIST_FORMAT_RIGHT)
        

        self.SetColumnWidth(0, 160)
        self.SetColumnWidth(1, 40)
        self.SetColumnWidth(2, 125)
        self.SetColumnWidth(3, 70)
        
        self.il = wx.ImageList(16, 16)
        
        mainframe = wx.FindWindowByName('MainFrame')
        
        for each in images:
            self.il.Add(wx.Bitmap(os.path.join(mainframe.RAWWorkDir, 'resources',each)))
            
        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        
        self.Bind(wx.EVT_LEFT_DCLICK, self._onDoubleLeftMouseClickOrEnterKey)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPressEvent)
        self.Bind(wx.EVT_RIGHT_UP, self._onRightMouseClick)
        
        self.parent.setDirLabel(self.path)
        self.updateFileList()
        
    def readFileList(self):
        try:
            self.files = os.listdir(self.path)
                
        except OSError, msg:
            print msg
            wx.MessageBox(str(msg), 'Error loading folder', style = wx.ICON_ERROR)
            
    def getFilteredFileList(self):
        
        sel = self.dirctrl_panel.getExtensionFilterString() 
        extIdx = sel.find('*.')
        
        if self.dirctrl_panel.getExtensionFilterString() not in self.dirctrl_panel.file_extension_list:
            filteredFiles = fnmatch.filter(self.files, sel)
        else:
            try:
                if sel[-1] == ')':
                    extension = sel[extIdx+1:-1]
                else:
                    extension = sel[extIdx+1:]
            except IndexError:
                extension = ''

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
    
    def refreshFileList(self):
        
        self.DeleteAllItems()
        
        self.dirsList = []
        
        ### Take out the directories and sort them:
        for each in self.files:
            if os.path.isdir(os.path.join(self.path, each)):
                self.dirsList.append(each)
        
        for i in range(0, len(self.dirsList)):
            self.dirsList[i] = str(self.dirsList[i])
        
        self.dirsList.sort(key = str.lower)
        
        ## Remove directories fromt the file list:
        for each in self.dirsList:
            self.files.remove(each)
        
        filteredFiles = self.getFilteredFileList()  
        
        if len(self.path) > 1:
            self.InsertStringItem(0, '..')
            self.SetItemImage(0,0)
            j = 1
        else:
            j = 0
        
        for i in self.dirsList:
            (name, ext) = os.path.splitext(i)
            ex = ext[1:]
            
            try:
                size = os.path.getsize(os.path.join(self.path, i))
                sec = os.path.getmtime(os.path.join(self.path, i))
            except WindowsError:
                size = 1
                sec = 1
            
            self.InsertStringItem(j, name)
            self.SetStringItem(j, 1, ex)
            self.SetStringItem(j, 3, '')
            self.SetStringItem(j, 2, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)))

            if os.path.isdir(os.path.join(self.path,i)):
                self.SetItemImage(j, 1)
            
            if not (j % 2) == 0:
                self.SetItemBackgroundColour(j, '#e6f1f5')
            j += 1
                
        for i in filteredFiles:
            (name, ext) = os.path.splitext(i)
            ex = ext[1:]
            try:
                size = os.path.getsize(os.path.join(self.path, i))
                sec = os.path.getmtime(os.path.join(self.path, i))
            except WindowsError, e:
                size = 0
                sec = 1
            
            self.InsertStringItem(j, name)
            self.SetStringItem(j, 1, ex)
            self.SetStringItem(j, 3, str(round(size/1000,1)) + ' KB')
            self.SetStringItem(j, 2, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)))

            
            if os.path.isdir(os.path.join(self.path,i)):
                self.SetItemImage(j, 1)
            else:
                self.SetItemImage(j, 2)
            #self.SetStringItem(j, 2, str(size) + ' B')
            #self.SetStringItem(j, 3, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)))

            if not (j % 2) == 0:
                self.SetItemBackgroundColour(j, '#e6f1f5')
            j += 1
        
    def getSelectedFilenames(self):
         
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
    
    def updateFileList(self):
        self.readFileList()
        self.refreshFileList()
        
    def setDir(self, dir):
        self.path = dir
        self.updateFileList()
        
    def getDir(self):
        return self.path
        
    def _onKeyPressEvent(self, event):
        
        shift_is_down = event.ShiftDown()
        
        if event.GetKeyCode() ==  wx.WXK_F5:
            self.readFileList()
            self.refreshFileList()
            
        elif event.GetKeyCode() ==  wx.WXK_UP:
            self._onUpKey(shift_is_down)
            
        elif event.GetKeyCode() ==  wx.WXK_DOWN:
            self._onDownKey(shift_is_down)
            
        elif event.GetKeyCode() == wx.WXK_RETURN:
            self._onDoubleLeftMouseClickOrEnterKey(event)
            
        elif event.GetKeyCode() == 83: #S
            wx.CallAfter(self.file_panel._onShowImageButton, None)
            
        elif event.GetKeyCode() == 80: #P
            wx.CallAfter(self.file_panel._onPlotButton, None)
            
        elif event.GetKeyCode() == 67: #C
            wx.CallAfter(self.file_panel._onClearAllButton, None)
        
        elif event.GetKeyCode() == 81: #Q
            wx.CallAfter(self.file_panel._onReduceButton, None)
        
        elif event.GetKeyCode() == 69: #e
            self.openFileInExternalViewer()
            
    def _onUpKey(self, shift_is_down):
        
        selidx = self.GetFirstSelected()
        no_of_items = self.GetItemCount()
        
        new_idx = selidx - 1
        
        if new_idx != -1:
            if not shift_is_down:
                self.Select(selidx, False)
            self.Select(new_idx, True)
            self.EnsureVisible(new_idx)
     
    def _onDownKey(self, shift_is_down):
        selidx = self.GetFirstSelected()
        no_of_items = self.GetItemCount()
        
        new_idx = selidx + 1
        
        if selidx < no_of_items-1 :
            if not shift_is_down:
                self.Select(selidx, False)
            
            self.Select(new_idx, True)
            self.EnsureVisible(new_idx)
    
    
    def _showPopupMenu(self):
        
        menu = wx.Menu()
              
        menu.Append(0, 'New Folder')
        menu.AppendSeparator()
        menu.Append(1, 'Rename' )
        menu.AppendSeparator()
        menu.Append(2, 'Cut')
        menu.Append(3, 'Copy')
        paste = menu.Append(4, 'Paste')
        paste.Enable(False)
        
        if self.copy_selected or self.cut_selected:
            paste.Enable(True)
            
        
        menu.AppendSeparator()
        menu.Append(5, 'Delete')
        
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)        
        self.PopupMenu(menu)
    
    def _onRightMouseClick(self, event):
        self._showPopupMenu()
    
    def _onPopupMenuChoice(self, event):
        choice_id = event.GetId()
        
        choices = {0 : self._createNewFolder,
                   1 : self._renameFile,
                   2 : self._cutFile,
                   3 : self._copyFile,
                   4 : self._pasteFile,
                   5 : self._deleteFile}
        
        if choices.has_key(choice_id):
            choices[choice_id]()
    
    def _pasteFile(self):
        
        if self.cut_selected or self.copy_selected:
           
            for each in self.copylist:
                
                try:
                    srcdir, filename = os.path.split(each)
                    dstpath = os.path.join(self.path, filename)
                
                    if self.cut_selected:        
                        shutil.move(each, dstpath)
                    elif self.copy_selected:
                        shutil.copy(each, dstpath)
                        
                except Exception, e: 
                    wx.MessageBox('Paste failed:\n' + str(e), 'Failed')
        
            self.cut_selected = False
            self.copy_selected = False
            self.copylist = []
            
            self.updateFileList()
        
    def _copyFile(self):
        
        filename_list = self.getSelectedFilenames()
        
        self.copylist = []
        for each in filename_list:
            self.copylist.append(os.path.join(self.path, each))
            
        self.copy_selected = True
        self.cut_selected = False
        
    def _cutFile(self):
        filename_list = self.getSelectedFilenames()
        
        self.copylist = []
        for each in filename_list:
            self.copylist.append(os.path.join(self.path, each))
            
        self.copy_selected = False
        self.cut_selected = True
        
    def _createNewFolder(self):
        
        dlg = FilenameChangeDialog(self, 'New Folder')
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            dirname = dlg.getFilename()
            
            try:
                os.mkdir(os.path.join(self.path, dirname))
            except Exception, e:
                wx.MessageBox('Folder creation failed:\n' + str(e), 'Failed')
                return
    
        self.updateFileList()
    
    def _deleteFile(self):
        
        filename_list = self.getSelectedFilenames()
        
        if len(filename_list) == 1:
            txt = 'this'
            txt2 = ''
        elif len(filename_list) > 1:
            txt = 'these'
            txt2 = 's'
        else:
            wx.MessageBox('No files selected', 'Failed')
            return
        
        dlg = wx.MessageDialog(self, 'Are you sure you want to PERMANETLY delete ' + txt + ' file'+ txt2 +'?:', 'Are you sure?', wx.YES | wx.ICON_INFORMATION)
    
        answer = dlg.ShowModal()
        
        if answer == wx.ID_YES:
            for each in filename_list:
                try:
                    if os.path.isdir(os.path.join(self.path, each)):
                        os.rmdir(os.path.join(self.path, each))
                    else:
                        os.remove(os.path.join(self.path, each))
                except Exception, e:
                     wx.MessageBox('Delete failed: ' + str(e), 'Failed')
                     return
                 
        self.updateFileList()
    
    def _renameFile(self):
        
        filename = self.getSelectedFilenames()[0]
        dlg = FilenameChangeDialog(self, filename)
        
        answer = dlg.ShowModal()
        
        if answer == wx.ID_OK:
            new_filename = dlg.getFilename()
            
            if new_filename != filename:
            
                try:
                    os.rename(os.path.join(self.path, filename), os.path.join(self.path, new_filename))
                except Exception, e:
                    wx.MessageBox('Rename failed: ' + str(e), 'Failed')
                    
                self.updateFileList()
            
        dlg.Destroy()
            
        
    
    def _onDoubleLeftMouseClickOrEnterKey(self, event):
        
        if self.getSelectedFilenames() != []:
            fullfilename = self.getSelectedFilenames()[0]
        else:
            return
        
        if fullfilename == '..':
            self.path = os.path.split(self.path)[0]
            if self.path == '.':
                self.path += '/' 
            self.parent.setDirLabel(self.path)
            self.updateFileList()
            
        elif os.path.isdir(os.path.join(self.path, fullfilename)):
            self.path = os.path.join(self.path, fullfilename)
            self.parent.setDirLabel(self.path)
            self.updateFileList()
            
        else:
            full_dir_filename = os.path.join(self.path, fullfilename)
            mainworker_cmd_queue.put(('plot', [full_dir_filename]))
            
    def openFileInExternalViewer(self):

        if self.getSelectedFilenames():
            filepath = os.path.join(self.getDir(), self.getSelectedFilenames()[0])
        else:
            return

        try:
            if platform.system() == 'Darwin':
                subprocess.call(('open', filepath))
            elif os.name == 'nt':
                subprocess.call(('start', filepath), shell = True)
            elif os.name == 'posix':
                subprocess.call(('xdg-open', filepath))
        except Exception, e:
            print e

class DirCtrlPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, name = 'DirCtrlPanel')
        self.parent = parent
        
        self.file_extension_list = ['All files (*.*)',
                                    'No Extension files (*.)',
                                    'TIFF files (*.tiff)',
                                    'TIF files (*.tif)',
                                    'RAD Files (*.rad)',
                                    'DAT files (*.dat)',
                                    'TXT files (*.txt)',
                                    'IMG files (*.img)']
        
        dirctrlpanel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.ext_choice = self._createExtentionBox()       #File extention filter
        
        self._createDirCtrl(dirctrlpanel_sizer)            #Listbox containing filenames
        
        dirctrlpanel_sizer.Add(self.ext_choice, 0, wx.EXPAND | wx.TOP, 2)
        
        self.SetSizer(dirctrlpanel_sizer, wx.EXPAND)
        
        self.selected_file = None
        self._old_path = '.'
        
        self.file_list = []
        

    def _createDirCtrl(self, dirctrlpanel_sizer):
        
        dir_label_sizer = wx.BoxSizer()
        
        self.dir_label = wx.TextCtrl(self, -1, "/" , size = (30,16), style = wx.TE_PROCESS_ENTER)
        self.dir_label.Bind(wx.EVT_KILL_FOCUS, self._onEnterOrFocusShiftInDirLabel)
        self.dir_label.Bind(wx.EVT_TEXT_ENTER, self._onEnterOrFocusShiftInDirLabel)

        dir_bitmap = wx.Bitmap(os.path.join(RAWWorkDir, "resources", "folder-search.png"))
        refresh_bitmap = wx.Bitmap(os.path.join(RAWWorkDir, "resources", "refreshlist2.png"))
        
        self.dir_button = wx.BitmapButton(self, -1, dir_bitmap)
        self.dir_button.Bind(wx.EVT_BUTTON, self._onSetDirButton)
        self.dir_button.SetToolTipString('Open Folder')
        
        self.refresh_button = wx.BitmapButton(self, -1, refresh_bitmap)
        self.refresh_button.Bind(wx.EVT_BUTTON, self._onRefreshButton)
        self.refresh_button.SetToolTipString('Refresh')
        
        dir_label_sizer.Add(self.dir_label, 1, wx.EXPAND | wx.RIGHT, 2)
        dir_label_sizer.Add(self.dir_button,0)
        dir_label_sizer.Add(self.refresh_button,0)
        
        self.file_list_box = CustomListCtrl(self, -1)
        self.file_list_box.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onLeftMouseClick)
        self.file_list_box.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._onRightMouseClick)
        
        dirctrlpanel_sizer.Add(dir_label_sizer, 0, wx.EXPAND | wx.BOTTOM, 2)
        dirctrlpanel_sizer.Add(self.file_list_box, 1, wx.EXPAND)
        
        self.selected_files = []
        self.bg_filename = []
              
    def _createExtentionBox(self):
        self.dropdown = wx.ComboBox(self, style = wx.TE_PROCESS_ENTER)
        self.dropdown.AppendItems(strings = self.file_extension_list)
        self.dropdown.Select(n=0)
        self.dropdown.Bind(wx.EVT_COMBOBOX, self._onExtensionComboChoice)
        self.dropdown.Bind(wx.EVT_TEXT_ENTER, self._onExtensionComboEnterKey)
        self.dropdown.Bind(wx.EVT_TEXT, self._onExtensionComboTextChange)
        return self.dropdown
    
    def getExtensionFilterString(self):
        return self.dropdown.GetValue()
    
    def _onExtensionComboTextChange(self, event):
        self.file_list_box.updateFileList()
        
    def _onExtensionComboEnterKey(self, event):
        self.file_list_box.updateFileList()

    def _onExtensionComboChoice(self, event):   
        self.file_list_box.updateFileList()
        
    def _onEnterOrFocusShiftInDirLabel(self, event):
        pathtxt = self.getDirLabel()
        
        if pathtxt != self.file_list_box.getDir():
            if os.path.isdir(pathtxt):               
                self._old_path = pathtxt
                self.file_list_box.setDir(pathtxt)
            else:
                self.setDirLabel(str(self._old_path))
    
    def _onSetDirButton(self, event):
        pathtxt = self.getDirLabel()
        dirdlg = wx.DirDialog(self, "Please select directory:", str(pathtxt))
            
        if dirdlg.ShowModal() == wx.ID_OK:               
            path = dirdlg.GetPath()
            self.file_list_box.setDir(path)
            self.setDirLabel(path)
            
    def _onRefreshButton(self, event):
        self.file_list_box.updateFileList()
            
    def setDirLabel(self, path):
        self.dir_label.SetValue(path)
        
    def getDirLabel(self):
        return self.dir_label.GetValue()
      
    def _onLeftMouseClick(self, event):
        pass
    
    def _onRightMouseClick(self, event):
        pass
    

#--- ** Manipulation panel **

class ManipulationPanel(wx.Panel):
    def __init__(self, parent, raw_settings):
        wx.Panel.__init__(self, parent, name = 'ManipulationPanel')
        
        self.button_data = ( ('Save', self._onSaveButton),
                                     ('Sync', self._onSyncButton),
                                     ('Remove', self._onRemoveButton),
                                     ('Superimpose', self._onSuperimposeButton),
                                     ('Average', self._onAverageButton),
                                     ('Subtract', self._onSubtractButton))

        self.panelsizer = wx.BoxSizer(wx.VERTICAL)
        
        self._initializeIcons()
        toolbarsizer = self._createToolbar()

        self.underpanel = scrolled.ScrolledPanel(self, -1, style = wx.BORDER_SUNKEN)
        self.underpanel.SetVirtualSize((200, 200))
        self.underpanel.SetScrollRate(20,20)
      
        self.all_manipulation_items = []
        self.selected_item_list = []
        
        self.underpanel_sizer = wx.BoxSizer(wx.VERTICAL)    
        self.underpanel.SetSizer(self.underpanel_sizer)
        
        self.buttonSizer = self.createButtons()

        self.panelsizer.Add(toolbarsizer, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND, 5)        
        self.panelsizer.Add(self.underpanel, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 3)
        self.panelsizer.Add(self.buttonSizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.TOP |wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        
        self.SetSizer(self.panelsizer)
        
        self._star_marked_item = None
        self._raw_settings = raw_settings
        
    def _initializeIcons(self):
        self.collapse_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'collapse_all.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.expand_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'expand_all.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        self.show_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'open_eye.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.hide_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'close_eye.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
    def _createToolbar(self):
        
        sizer = wx.BoxSizer()
        
        collapse_all = wx.StaticBitmap(self, -1, self.collapse_all_png)
        expand_all = wx.StaticBitmap(self, -1, self.expand_all_png)
        show_all = wx.StaticBitmap(self, -1, self.show_all_png)
        hide_all = wx.StaticBitmap(self, -1, self.hide_all_png)
        show_all.SetToolTipString('Show All')
        hide_all.SetToolTipString('Hide All')
        
        collapse_all.SetToolTipString('Collapse All')
        expand_all.SetToolTipString('Expand All')
        collapse_all.Bind(wx.EVT_LEFT_DOWN, self._onCollapseAllButton)
        expand_all.Bind(wx.EVT_LEFT_DOWN, self._onExpandAllButton)
        show_all.Bind(wx.EVT_LEFT_DOWN, self._onShowAllButton)
        hide_all.Bind(wx.EVT_LEFT_DOWN, self._onHideAllButton)
        
        sizer.Add(show_all, 0, wx.LEFT, 5)
        sizer.Add(hide_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)
        sizer.Add(collapse_all, 0, wx.RIGHT, 5)
        sizer.Add(expand_all, 0, wx.RIGHT, 3)
        
        return sizer
                
    def createButtons(self):
        
        cols = 3
        rows = round(len(self.button_data)/cols)
        
        sizer = wx.GridSizer(cols = cols, rows = rows, hgap = 3, vgap = 3)
        
        for each in self.button_data:
            label = each[0]
            func = each[1]
            
            button = wx.Button(self, -1, label)
            button.Bind(wx.EVT_BUTTON, func)
            
            ##########################################
            if label == 'BIFT':
                button.Enable(False)
            
            sizer.Add(button, 1, wx.ALIGN_CENTER | wx.EXPAND)
        
        return sizer
    
    def addItem(self, sasm, item_colour = 'black'):
        
        newItem = ManipItemPanel(self.underpanel, sasm, font_colour = item_colour)
        self.Freeze()
        self.underpanel_sizer.Add(newItem, 0, wx.GROW)
        self.underpanel_sizer.Layout()
        
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.Layout()            
        self.Refresh()
        self.Thaw()
        
        # Keeping track of all items in our list:
        self.all_manipulation_items.append(newItem)
        
        
        sasm.item_panel = newItem
        
    def setItemAsBackground(self, item):
        
        bg_sasm = self._raw_settings.get('BackgroundSASM')
        
        if bg_sasm != None:
            try:
                bg_sasm.itempanel.enableStar(False)
            except:
                pass
        
        self._raw_settings.set('BackgroundSASM', item.sasm)
        item.enableStar(True)
        self._star_marked_item = item
        
    def getBackgroundItem(self):
        return self._star_marked_item
        
    def clearList(self):
        self.Freeze()
        
        rest_of_items = []
        for each in self.all_manipulation_items:
            
            try:
                each.Destroy()
            except ValueError:
                rest_of_items.append(each)
                
        self.all_manipulation_items = rest_of_items
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        
        self._star_marked_item = None
        
        self.Thaw()
        
    def clearBackgroundItem(self):
        self._raw_settings.set('BackgroundSASM', None)
        self._star_marked_item = None
        
    def _collapseAllItems(self):
        for each in self.all_manipulation_items:
            each.showControls(False)
        
        self.underpanel.Layout()            
        self.underpanel.Refresh()
        
        self.Layout()            
        self.Refresh()
            
    def _expandAllItems(self):
        for each in self.all_manipulation_items:
            each.showControls(True)
            
        self.underpanel.Layout()            
        self.underpanel.Refresh()
        
        self.Layout()            
        self.Refresh()
    
    def removeItem(self, item):
        
        self.all_manipulation_items.remove(item)
        
        if item == self._star_marked_item:
            self._star_marked_item = None
        
        item.Destroy()
        
    def getSelectedItems(self):
        
        self.selected_item_list = []
        
        for each in self.all_manipulation_items:
            if each._selected == True:
                self.selected_item_list.append(each)
            
        return self.selected_item_list
    
    def deselectAllExceptOne(self, item, line = None, enableLocatorLine = False):
        
        if line == None:    
            for each in self.all_manipulation_items:
                if each != item:
                    each._selected = True
                    each.toggleSelect()
        else:
            for each in self.all_manipulation_items:
                if each.sasm.getLine() == line:
                    each._selected = False
                    each.toggleSelect()
                else:
                    each._selected = True
                    each.toggleSelect()
                    
    def removeSelectedItems(self):
       
        if len(self.getSelectedItems()) == 0: return
        
        self.Freeze()
        
        info_panel = wx.FindWindowByName('InformationPanel')
        info_panel.clearInfo()
        
        axes_that_needs_updated_legend = []
         
        for each in self.getSelectedItems():
                     
            plot_panel = each.sasm.plot_panel
            
            each.sasm.line.remove()
            each.sasm.err_line[0][0].remove()
            each.sasm.err_line[0][1].remove()
            each.sasm.err_line[1][0].remove()
            
            i = plot_panel.plotted_sasms.index(each.sasm)
            plot_panel.plotted_sasms.pop(i)
            
            if not each.sasm.axes in axes_that_needs_updated_legend:
                axes_that_needs_updated_legend.append(each.sasm.axes)
            
            if each == self._star_marked_item:
                self._star_marked_item = None
            
            idx = self.all_manipulation_items.index(each)
            self.all_manipulation_items[idx].Destroy()
            self.all_manipulation_items.pop(idx)
        
        for eachaxes in axes_that_needs_updated_legend:
            if eachaxes == plot_panel.subplot1:
                wx.CallAfter(plot_panel.updateLegend, 1)
            else:
                wx.CallAfter(plot_panel.updateLegend, 2)
            
        wx.CallAfter(plot_panel.canvas.draw)
        
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Refresh()    
        
        self.Thaw()
        
    def _onShowAllButton(self, event):
        
        for each in self.all_manipulation_items:
           each.showItem(True)
           
        plot_panel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plot_panel.updateLegend, 1)
        wx.CallAfter(plot_panel.updateLegend, 2)
        wx.CallAfter(plot_panel.fitAxis)
        
        self.underpanel.Layout()            
        self.underpanel.Refresh()
            
        self.Layout()            
        self.Refresh()
           
    def _onHideAllButton(self, event):
        self.underpanel.Freeze()
        
        for each in self.all_manipulation_items:
           each.showItem(False)
        
        self.underpanel.Layout()            
        self.underpanel.Refresh()
            
        self.Layout()            
        self.Refresh()
        
        self.underpanel.Thaw()
        
        plot_panel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plot_panel.updateLegend, 1)
        wx.CallAfter(plot_panel.updateLegend, 2)
        wx.CallAfter(plot_panel.canvas.draw)
               
    def _onCollapseAllButton(self, event):
        self._collapseAllItems()
        
    def _onExpandAllButton(self, event):
        self._expandAllItems()
            
    def _onBiftButton(self, event):
        pass
    
    def _onAverageButton(self, event):
        selected_items = self.getSelectedItems()
        mainworker_cmd_queue.put(['average_items', selected_items])
        
    def _onRemoveButton(self, event):
        self.removeSelectedItems()
    
    def _onSaveButton(self, event):
        self.saveItems()
    
    def _onSyncButton(self, event):
        syncdialog = SyncDialog(self)
        syncdialog.ShowModal()
        syncdialog.Destroy()
        
    def _onSubtractButton(self, event):
        mainworker_cmd_queue.put(['subtract_items', ( self._star_marked_item, self.getSelectedItems()  )])
        
    def _onSuperimposeButton(self, event):
        mainworker_cmd_queue.put(['superimpose_items', ( self._star_marked_item, self.getSelectedItems()  )])
        
    
    def synchronizeSelectedItems(self, sync_parameters):
        star_item = self.getBackgroundItem()
        
        if not star_item or (len(sync_parameters) == 0):
            return
        
        star_sasm = star_item.getSASM()
        
        scale = star_sasm.getScale()
        offset = star_sasm.getOffset()
        nmin, nmax = star_sasm.getQrange()
        qmin, qmax = star_sasm.getBinnedQ()[nmin], star_sasm.getBinnedQ()[nmax-1]
        linestyle = star_sasm.line.get_linestyle()
        linewidth = star_sasm.line.get_linewidth()
        linemarker = star_sasm.line.get_marker() 
        
        selected_items = self.getSelectedItems()
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
        
        for each_item in selected_items:
            if each_item == star_item:
                continue
            
            sasm = each_item.getSASM()
            
            old_nmin, old_nmax = sasm.getQrange()
            
            try:
                if 'nmin' in sync_parameters and 'nmax' in sync_parameters:
                    sasm.setQrange([nmin, nmax])
                elif 'nmin' in sync_parameters:
                    sasm.setQrange([nmin, old_nmax])
                elif 'nmax' in sync_parameters:
                    sasm.setQrange([old_nmin, nmax])                    
                    
            except SASExceptions.InvalidQrange, msg:
                dial = wx.MessageDialog(None, 'Filename : ' + sasm.getParameter('filename') + '\n\n' + str(msg),
                                'Invalid Qrange',
                                wx.OK | wx.CANCEL | wx.NO_DEFAULT | wx.ICON_QUESTION)
                answer = dial.ShowModal()
                    
                if answer == wx.ID_CANCEL:
                    return
                
            q = sasm.getBinnedQ()
            
            if 'qmin' in sync_parameters and 'qmax' in sync_parameters:
                closest = findClosest(qmin, q)
                new_nmin = numpy.where(q == closest)[0][0]
                closest = findClosest(qmax, q)
                new_nmax = numpy.where(q == closest)[0][0]
                sasm.setQrange([new_nmin, new_nmax])
            elif 'qmin' in sync_parameters:
                closest = findClosest(qmin, q)
                new_nmin = numpy.where(q == closest)[0][0]
                sasm.setQrange([new_nmin, old_nmax])    
            elif 'qmax' in sync_parameters:
                closest = findClosest(qmax, q)
                new_nmax = numpy.where(q == closest)[0][0]
                sasm.setQrange([old_nmin, new_nmax])
                
            if 'scale' in sync_parameters:
                sasm.scale(scale)
            if 'offset' in sync_parameters:
                sasm.offset(offset)
            if 'linestyle' in sync_parameters:
                sasm.line.set_linestyle(linestyle)
            if 'linewidth' in sync_parameters:
                sasm.line.set_linewidth(linewidth)
            if 'linemarker' in sync_parameters:
                sasm.line.set_marker(linemarker)
            
            each_item.updateControlsFromSASM()
        
    def movePlots(self, ExpObjList, toAxes):
        
        for each_item in ExpObjList:
            
            each = each_item.getSASM()
            
            if each.axes != toAxes:
                plotpanel = each.plot_panel
      
                each.line.remove()
                each.err_line[0][0].remove()
                each.err_line[0][1].remove()
                each.err_line[1][0].remove()
        
                line_color = each.line.get_color()
                
                if each_item.getLegendLabel() != '':
                    label = each_item.getLegendLabel()
                else:
                    label = None
                
                wx.CallAfter(plotpanel.plotSASM, each, toAxes, color = line_color, legend_label_in = label)
                
                
        plotpanel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plotpanel.updateLegend, 1)
        wx.CallAfter(plotpanel.updateLegend, 2)
        wx.CallAfter(plotpanel.canvas.draw)
    
    def getItems(self):
        return self.all_manipulation_items
            
    def updateLayout(self):
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
    
    def saveItems(self):
        selected_items = self.getSelectedItems()
        
        if len(selected_items) == 0:
            return
        
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        save_path = dirctrl_panel.getDirLabel()
        
        dirdlg = wx.DirDialog(self, "Please select save directory:", str(save_path))
            
        if dirdlg.ShowModal() == wx.ID_OK:               
            save_path = dirdlg.GetPath()
        else:
            return
        
        mainworker_cmd_queue.put(['save_items', [save_path, selected_items]])
        

class ManipItemPanel(wx.Panel):
    def __init__(self, parent, sasm, font_colour = 'BLACK', legend_label = ''):
        
        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)
        
        self.parent = parent
        self.sasm = sasm
        self.sasm.itempanel = self
        
        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')
        self.plot_panel = wx.FindWindowByName('PlotPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        
        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.info_settings = {'hdr_choice' : 0}
        
        self._selected_as_bg = False
        self._selected_for_plot = True
        self._controls_visible = True
        self._selected = False
        self._legend_label = legend_label
        
        self._font_colour = font_colour
        
        filename = sasm.getParameter('filename')
               
        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
        #Label, TextCtrl_ID, SPIN_ID
        
        self._initializeIcons()
                                       
        self.qmax = len(self.sasm.q)
                             
        self.spin_controls = (("q Min:", wx.NewId(), wx.NewId(), (1, self.qmax-1), 'nlow'),        
                             ("q Max:", wx.NewId(), wx.NewId(), (2, self.qmax), 'nhigh'))
        
        self.float_spin_controls = (
                                   # ("Conc:", wx.NewId(), 'conc', '1.0', self._onScaleOffsetChange),
                                    ("Scale:", wx.NewId(), 'scale', str(sasm.getScale()), self._onScaleOffsetChange),
                                    ("Offset:", wx.NewId(), 'offset', str(sasm.getOffset()), self._onScaleOffsetChange))
    
        self.SelectedForPlot = RAWCustomCtrl.CustomCheckBox(self, -1, filename)
        self.SelectedForPlot.SetValue(True)
        self.SelectedForPlot.Bind(wx.EVT_CHECKBOX, self._onSelectedChkBox)
        self.SelectedForPlot.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.SelectedForPlot.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
        self.SelectedForPlot.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        
        self.SelectedForPlot.SetToolTipString('Show Plot')
        self.SelectedForPlot.SetForegroundColour(font_colour)
        
        self.legend_label_text = wx.StaticText(self, -1, '')
        
        self.legend_label_text.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.legend_label_text.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.legend_label_text.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
        
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.sasm.line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        
        self.colour_indicator = RAWCustomCtrl.ColourIndicator(self, -1, color, size = (20,15))
        self.colour_indicator.Bind(wx.EVT_LEFT_DOWN, self._onLinePropertyButton)
        self.colour_indicator.SetToolTipString('Line Properties')

        self.bg_star = wx.StaticBitmap(self, -1, self.gray_png)
        self.bg_star.Bind(wx.EVT_LEFT_DOWN, self._onStarButton)
        self.bg_star.SetToolTipString('Mark')
        
        self.expand_collapse = wx.StaticBitmap(self, -1, self.collapse_png)
        self.expand_collapse.Bind(wx.EVT_LEFT_DOWN, self._onExpandCollapseButton)
        self.expand_collapse.SetToolTipString('Collapse/Expand')
        
        self.target_icon = wx.StaticBitmap(self, -1, self.target_png)
        self.target_icon.Bind(wx.EVT_LEFT_DOWN, self._onTargetButton)
        self.target_icon.SetToolTipString('Locate Line')

        self.info_icon = wx.StaticBitmap(self, -1, self.info_png)
        self.info_icon.Bind(wx.EVT_LEFT_DOWN, self._onInfoButton)
        self.info_icon.SetToolTipString('Show Extended Info\n--------------------------------\nRg: N/A\nI(0): N/A')
        
        self.locator_on = False
        self.locator_old_width = 1
        
        panelsizer = wx.BoxSizer()
        panelsizer.Add(self.SelectedForPlot, 0, wx.LEFT | wx.TOP, 3)
        panelsizer.Add(self.legend_label_text, 0, wx.LEFT | wx.TOP, 3)
        panelsizer.Add((1,1), 1, wx.EXPAND)
        panelsizer.Add(self.expand_collapse, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.info_icon, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.target_icon, 0, wx.RIGHT | wx.TOP, 4)
        panelsizer.Add(self.colour_indicator, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.bg_star, 0, wx.LEFT | wx.RIGHT | wx.TOP, 3)
        
    
        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(panelsizer, 1, wx.EXPAND)
        
        #self.controlSizer = wx.BoxSizer(wx.VERTICAL)
        self.controlSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 3, hgap = 7)
       
        self._createSimpleSpinCtrls(self.controlSizer)
        self._createFloatSpinCtrls(self.controlSizer) 
        
        self.topsizer.Add((5,5),0)
        self.topsizer.Add(self.controlSizer, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)
        
        self.SetSizer(self.topsizer)
        
        self.SetBackgroundColour(wx.Color(250,250,250))
        
        self._initStartPosition()
        self._updateQTextCtrl()
        
        if self.sasm.getParameter('analysis').has_key('guinier'):
            self.updateInfoTip(self.sasm.getParameter('analysis'))
            
        controls_not_shown = self.main_frame.raw_settings.get('ManipItemCollapsed')
        if controls_not_shown:
            self.showControls(not controls_not_shown)
        
    
    def updateInfoTip(self, analysis_dict, fromGuinierDialog = False):
        
        
        if analysis_dict.has_key('guinier'):
            guinier = analysis_dict['guinier']
        else:
            guinier = {}
        
        string0 = 'Show Extended Info\n--------------------------------'
        string1 = ''
        string2 = ''
        string3 = ''
        
        if guinier.has_key('Rg') and guinier.has_key('I0'):
            rg = guinier['Rg']
            i_zero = guinier['I0']
        
            string1 = '\nRg: ' + str(rg) + '\nI(0): ' + str(i_zero)
        else:
            string1 = '\nRg: N/A' + '\nI(0): N/A'
            
        if self.sasm.getAllParameters().has_key('Conc'):
            string2 = '\nConc: ' + str(self.sasm.getParameter('Conc'))   
        
        if self.sasm.getAllParameters().has_key('Notes'):
            if self.sasm.getParameter('Notes') != '':
                string3 = '\nNote: ' + str(self.sasm.getParameter('Notes'))  
        
        string = string0+string1+string2+string3
        
        if string != '':    
            self.info_icon.SetToolTipString(string)
                  
        if fromGuinierDialog:
            self.info_panel.updateInfoFromItem(self)
                
    def enableStar(self, state):
        if state == True:
            self.bg_star.SetBitmap(self.star_png)
            self._selected_as_bg = True
        else:
            self.bg_star.SetBitmap(self.gray_png)
            self._selected_as_bg = False
        
        self.bg_star.Refresh()
        
    def removeSelf(self):
        #Has to be callafter under Linux.. or it'll crash
        wx.CallAfter(self.manipulation_panel.removeSelectedItems)
        
    def getSASM(self):
        return self.sasm        
    
    def getFontColour(self):
        return self._font_colour
    
    def getSelectedForPlot(self):
        return self._selected_for_plot
    
    def getLegendLabel(self):
        return self._legend_label
    
    def updateControlsFromSASM(self):    
        scale = self.sasm.getScale()
        offset = self.sasm.getOffset()
        qmin, qmax = self.sasm.getQrange()
        
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1])
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1])
        qmintxt = wx.FindWindowById(self.spin_controls[0][2])
        qmaxtxt = wx.FindWindowById(self.spin_controls[1][2])
        
        qmin_ctrl.SetValue(str(qmin))
        qmax_ctrl.SetValue(str(qmax-1))        
        qmintxt.SetValue(str(round(self.sasm.q[qmin],4)))
        qmaxtxt.SetValue(str(round(self.sasm.q[qmax-1],4)))
        
        scale_ctrl = wx.FindWindowById(self.float_spin_controls[0][1])
        offset_ctrl = wx.FindWindowById(self.float_spin_controls[1][1])
    
        offset_ctrl.SetValue(str(offset))
        scale_ctrl.SetValue(str(scale))
        
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
    
    def toggleSelect(self):
        
        if self._selected:
            self._selected = False
            self.SetBackgroundColour(wx.Color(250,250,250))
            self.info_panel.clearInfo()
        else:
            self._selected = True
            self.SetBackgroundColour(wx.Color(200,200,200))
            self.SetFocusIgnoringChildren()
            self.info_panel.updateInfoFromItem(self)
        
        self.Refresh()
        
    def enableLocatorLine(self):
        
        self.locator_on = not self.locator_on
        
        if self.locator_on == True:
            self.target_icon.SetBitmap(self.target_on_png)
            self.locator_old_width = self.sasm.line.get_linewidth()
            new_width = self.locator_old_width + 2.0
            self.sasm.line.set_linewidth(new_width)
            wx.CallAfter(self.sasm.plot_panel.canvas.draw)
        else:
            self.target_icon.SetBitmap(self.target_png)
            self.sasm.line.set_linewidth(self.locator_old_width)
            wx.CallAfter(self.sasm.plot_panel.canvas.draw)
            
        self.target_icon.Refresh()
        
    def getControlsVisible(self):
        return self._controls_visible
        
    def showControls(self, state):
        
        if state == False:
            self.expand_collapse.SetBitmap(self.expand_png)
            self._controls_visible = False
            self.controlSizer.Hide(0, True)
            self.controlSizer.Hide(1, True)
            self.controlSizer.Hide(2, True)
            self.controlSizer.Hide(3, True)
            self.controlSizer.Hide(4, True)
            self.controlSizer.Hide(5, True)
            self.controlSizer.Hide(6, True)
            self.controlSizer.Hide(7, True)
        else:
            self.expand_collapse.SetBitmap(self.collapse_png)
            self._controls_visible = True
            self.controlSizer.Show(0, True)
            self.controlSizer.Show(1, True)
            self.controlSizer.Show(2, True)
            self.controlSizer.Show(3, True)
            self.controlSizer.Show(4, True)
            self.controlSizer.Show(5, True)
            self.controlSizer.Show(6, True)
            self.controlSizer.Show(7, True)
            
        self.expand_collapse.Refresh()
        self.topsizer.Layout()
        
    
    def showItem(self, state):
        self._selected_for_plot = state
        
        if self._selected_for_plot == False:
            self._controls_visible = False
            self.showControls(self._controls_visible)
        
        self.SelectedForPlot.SetValue(self._selected_for_plot)
        self.sasm.line.set_visible(self._selected_for_plot)
        self.sasm.line.set_picker(self._selected_for_plot)      #Line can't be selected when it's hidden
        
    def updateFilenameLabel(self):
        filename = self.sasm.getParameter('filename')
        
        if self._legend_label == '':
            self.sasm.line.set_label(filename)
        self.plot_panel.updateLegend(self.sasm.axes)
        self.SelectedForPlot.SetLabel(str(filename))
        self.SelectedForPlot.Refresh()
        self.topsizer.Layout()
        self.GetParent().Layout()            
        self.GetParent().Refresh()
    
    def _initializeIcons(self):
        
        self.gray_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'Star-icon_notenabled.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.star_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'Star-icon_org.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        self.collapse_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'collapse.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.expand_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'expand.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        self.target_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'target.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.target_on_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'target_orange.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()

        self.info_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'info_16_2.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()

    def _initStartPosition(self):
        
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1])
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1])
        
        qrange = self.sasm.getQrange()
        
        qmin_ctrl.SetValue(str(qrange[0]))
        
    def _updateColourIndicator(self):
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.sasm.line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        
        self.colour_indicator.updateColour(color)
        
    def _onLinePropertyButton(self, event):
        
        try:
            dialog = LinePropertyDialog(self, self.sasm.line)
            dialog.ShowModal()
            dialog.Destroy()
            self._updateColourIndicator()
        except TypeError:
            return
           
        if self.sasm.axes == self.plot_panel.subplot1:
            wx.CallAfter(self.plot_panel.updateLegend, 1)
        else:
            wx.CallAfter(self.plot_panel.updateLegend, 2)
            
        self.sasm.plot_panel.canvas.draw()
        
    def _onExpandCollapseButton(self, event):
        self._controls_visible = not self._controls_visible
        self.showControls(self._controls_visible)
        
        self.GetParent().Layout()            
        self.GetParent().Refresh()
        
        self.GetParent().GetParent().Layout()            
        self.GetParent().GetParent().Refresh()
            
    def _onTargetButton(self, event):
        self.enableLocatorLine()
        
    def _onInfoButton(self, event):
        pass
            
    def _showPopupMenu(self):

        menu = wx.Menu()
        
        number_of_selected_items = len(self.manipulation_panel.getSelectedItems())
        
#        iftmenu = wx.Menu()
#        iftmenu.Append(10, 'Run BIFT')
#        iftmenu.Append(11, 'Run GNOM using current Dmax')
#        iftmenu.AppendSeparator()
#        iftmenu.Append(12, 'Add to IFT list')
        
        convertq_menu = wx.Menu()
        convertq_menu.Append(15, '>> 10')
        convertq_menu.Append(16, '<< 10^-1')
        
        submenu = menu.Append(4, 'Subtract')
        avgmenu = menu.Append(6, 'Average' )
        mermenu = menu.Append(22, 'Merge')
        rebmenu = menu.Append(23, 'Rebin')
        menu.Append(14, 'Rename')
            
        menu.AppendSeparator()
        menu.Append(5, 'Remove' )
        menu.AppendSeparator()
        menu.Append(13, 'Guinier fit...')
        #menu.AppendMenu(3, 'Indirect Fourier Transform', iftmenu)
        menu.AppendMenu(wx.NewId(), 'Convert q-scale', convertq_menu)
        
        menu.AppendSeparator()
        img = menu.Append(19, 'Show image')
        
        if not self.sasm.getAllParameters().has_key('load_path'):
            img.Enable(False)
        menu.Append(20, 'Show data...')
        menu.Append(21, 'Show header...')
        
        menu.AppendSeparator()
        menu.Append(8, 'Move to top plot')
        menu.Append(9, 'Move to bottom plot')
        menu.AppendSeparator()
        menu.Append(17, 'Set legend label...')
        menu.Append(18, 'Save analysis info...')
        menu.AppendSeparator()
        menu.Append(7, 'Save selected file(s)')
        
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)        
        self.PopupMenu(menu)
    
    def _onShowImage(self):
        
        if self.sasm.getAllParameters().has_key('load_path'):
            path = self.sasm.getParameter('load_path')
            mainworker_cmd_queue.put(['show_image', path])
    
    def _onPopupMenuChoice(self, evt):
            
        if evt.GetId() == 3:
            #IFT
            analysisPage.runBiftOnExperimentObject(self.ExpObj, expParams)
        
        if evt.GetId() == 4:
            #Subtract
            selected_items = self.manipulation_panel.getSelectedItems()
            marked_item = self.manipulation_panel.getBackgroundItem()
            mainworker_cmd_queue.put(['subtract_items', [marked_item, selected_items]])
        
        if evt.GetId() == 5:
            #Delete
            wx.CallAfter(self.manipulation_panel.removeSelectedItems)
        
        if evt.GetId() == 6:
            #Average 
            selected_items = self.manipulation_panel.getSelectedItems()
            mainworker_cmd_queue.put(['average_items', selected_items])
            
        if evt.GetId() == 7:
            self.manipulation_panel.saveItems()
                
        if evt.GetId() == 8:
            #Move to top plot
            plotpanel = wx.FindWindowByName('PlotPanel')
            selected_items = self.manipulation_panel.getSelectedItems()
            self.manipulation_panel.movePlots(selected_items, plotpanel.subplot1)
                
        if evt.GetId() == 9:
            #Move to bottom plot
            plotpanel = wx.FindWindowByName('PlotPanel')
            selected_items = self.manipulation_panel.getSelectedItems()
            self.manipulation_panel.movePlots(selected_items, plotpanel.subplot2)
            
        if evt.GetId() == 13:
            #Guinier fit
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSASMList = self.manipulation_panel.getSelectedItems()
            
            sasm = selectedSASMList[0].getSASM()
            Mainframe.showGuinierFitFrame(sasm, selectedSASMList[0])
            
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
            
        if evt.GetId() == 14:
            dlg = FilenameChangeDialog(self, self.sasm.getParameter('filename'))
            dlg.ShowModal()
            filename =  dlg.getFilename()
            dlg.Destroy()
            
            if filename:
                self.sasm.setParameter('filename', filename)
                self.updateFilenameLabel()
        
        if evt.GetId() == 15:
            #A to s
            self.sasm.scaleBinnedQ(10.0)
            self._updateQTextCtrl()
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
            
        if evt.GetId() == 16:
            #s to A
            self.sasm.scaleBinnedQ(0.1)
            self._updateQTextCtrl()
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
        
        if evt.GetId() == 17:
            dlg = LegendLabelChangeDialog(self, self._legend_label)
            answer = dlg.ShowModal()
            legend_label = dlg.getLegendLabel()
            dlg.Destroy()
            
            if answer == wx.ID_OK:
                self._legend_label = legend_label
                self._updateLegendLabel()
                
        if evt.GetId() == 18:
            #Save Analysis Info
            #self._saveAnalysisInfo()
            
            dlg = SaveAnalysisInfoDialog(self, self.main_frame.raw_settings, self.manipulation_panel.getSelectedItems())
            dlg.ShowModal()
            dlg.Destroy()
            
        if evt.GetId() == 19:
            #Show Image
            self._onShowImage()
            
        if evt.GetId() == 20:
            dlg = DataDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()
            
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
            
        if evt.GetId() == 21:
            dlg = HdrDataDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()
            
            #wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
        
        if evt.GetId() == 22:
            selected_items = self.manipulation_panel.getSelectedItems()
            marked_item = self.manipulation_panel.getBackgroundItem()
            mainworker_cmd_queue.put(['merge_items', [marked_item, selected_items]])
            
        if evt.GetId() == 23:
            
            dlg = RebinDialog(self)
            dlg.ShowModal()
            
            selected_items = self.manipulation_panel.getSelectedItems()
            #mainworker_cmd_queue.put(['rebin_items', selected_items])
            
    
    def _saveAnalysisInfo(self):
        selected_items = self.manipulation_panel.getSelectedItems()
            
        if len(selected_items) == 0:
            return
        
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        save_path = dirctrl_panel.getDirLabel()
        
        filters = 'Comma Separated Files (*.csv)|*.csv'
            
        dialog = wx.FileDialog( None, style = wx.SAVE | wx.OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path) 
        #dirdlg = wx.DirDialog(self, "Please select save directory:", str(save_path))
            
        if dialog.ShowModal() == wx.ID_OK:               
            save_path = dialog.GetPath()
        else:
             return
            
        mainworker_cmd_queue.put(['save_analysis_info', [selected_items, save_path]])
    
    def _onKeyPress(self, evt):
        
        key = evt.GetKeyCode()
   
        if key == wx.WXK_DELETE and self._selected == True:
            self.removeSelf()
            
        if key == wx.WXK_UP:
            if evt.CmdDown():
                print 'CTRL UP'
            else:
                print "UP!"
        if key == wx.WXK_DOWN:
            if evt.CmdDown():
                print 'CTRL DOWN'
            else:
                print "DOWN!"
                
        if key == 83: #S
            self._onShowImage()
            
            
    def _onRightMouseButton(self, evt):
        if not self._selected:
            self.toggleSelect()
            self.manipulation_panel.deselectAllExceptOne(self)
                    
        self._showPopupMenu()
        
    def _onLeftMouseButton(self, evt):
        ctrl_is_down = evt.CmdDown()
        shift_is_down = evt.ShiftDown()
        
        manipulation_panel = wx.FindWindowByName('ManipulationPanel')
        
        if shift_is_down:
            try:
                
                first_marked_item_idx = manipulation_panel.all_manipulation_items.index(manipulation_panel.getSelectedItems()[0])
                last_marked_item = manipulation_panel.getSelectedItems()[-1]
                last_marked_item_idx = manipulation_panel.all_manipulation_items.index(last_marked_item)
                
                this_item_idx = manipulation_panel.all_manipulation_items.index(self)
            
                if last_marked_item_idx > this_item_idx:
                    adj = 0
                    idxs = [first_marked_item_idx, this_item_idx]
                else:
                    idxs = [last_marked_item_idx, this_item_idx]
                    adj = 1
                        
                top_item = max(idxs)
                bottom_item = min(idxs)
            
                for each in manipulation_panel.all_manipulation_items[bottom_item+adj:top_item+adj]:
                    each.toggleSelect()
            except IndexError:
                pass
            
        elif ctrl_is_down:
            self.toggleSelect()
        else:
            manipulation_panel.deselectAllExceptOne(self)
            self.toggleSelect()
            
        evt.Skip()
              
    def _onStarButton(self, event):

        if self._selected_as_bg == True:
            self.enableStar(False)
            self.manipulation_panel.clearBackgroundItem()
        else:
            self.manipulation_panel.setItemAsBackground(self)
            
    def _showInvalidValueError(self):
        wx.CallAfter(wx.MessageBox, 'The entered value is invalid. Please remove non-numeric characters.', 'Invalid Value Error', style = wx.ICON_ERROR)
                    
    def _onScaleOffsetChange(self, event):
        id = event.GetId()
        
        try:
            value = float(event.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return
        
        for each_label, each_id, each_name, eachInit_value, each_bindfunc in self.float_spin_controls:
            
            if id == each_id:
                
                if each_name == 'scale':
                    self.sasm.scale(value)
                elif each_name == 'offset':
                    self.sasm.offset(value)
        
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])

        event.Skip()
        
    def _updateQTextCtrl(self):
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1])
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1])
        
        qmintxt = wx.FindWindowById(self.spin_controls[0][2])
        qmaxtxt = wx.FindWindowById(self.spin_controls[1][2])
        
        try:
            qmin = int(qmin_ctrl.GetValue())
            qmax = int(qmax_ctrl.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return
        
        qmintxt.SetValue(str(round(self.sasm.q[qmin],4)))
        qmaxtxt.SetValue(str(round(self.sasm.q[qmax],4)))
        
        qrange = (qmin, qmax+1) # +1 to be able to use the range for array slicing [0:n+1]

        self.sasm.setQrange(qrange)   
    
    def _updateLegendLabel(self):
        
        if self._legend_label == '' or self._legend_label == None:
            self.sasm.line.set_label(self.sasm.getParameter('filename'))
            self.legend_label_text.SetLabel('')
        else:
            self.sasm.line.set_label(str(self._legend_label))
            self.legend_label_text.SetLabel('[' + str(self._legend_label) + ']')
            
        wx.CallAfter(self.sasm.plot_panel.updateLegend, self.sasm.axes)
        
    
    def _onQrangeChange(self, event):
        self._updateQTextCtrl()
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
        
    def _onEnterInQrangeTextCtrl(self, evt):
        
        id = evt.GetId()
        txtctrl = wx.FindWindowById(id)
        
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return
        
        if id == self.spin_controls[0][2]:
                spinctrl = wx.FindWindowById(self.spin_controls[0][1])
        elif id == self.spin_controls[1][2]:
                spinctrl = wx.FindWindowById(self.spin_controls[1][1])
        
        q = self.sasm.getBinnedQ()
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
                
        closest = findClosest(val, q)
        idx = numpy.where(q == closest)[0][0]  
        
        spinctrl.SetValue(idx)
        self._onQrangeChange(None)
        txtctrl.SelectAll()
     
    def _onSelectedChkBox(self, event):
        self._selected_for_plot = not self._selected_for_plot
        
        self.showItem(self._selected_for_plot)
        
        self.GetParent().Layout()            
        self.GetParent().Refresh()
        
        wx.CallAfter(self.plot_panel.updateLegend, self.sasm.axes)
        wx.CallAfter(self.sasm.plot_panel.canvas.draw)
        
        self.sasm.plot_panel.fitAxis([self.sasm.axes])
        
    def _createFloatSpinCtrls(self, control_sizer):
        
        for label, id, name, initValue, bindfunc in self.float_spin_controls:
            
            label = wx.StaticText(self, -1, label)
            
            label.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            label.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            label.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
            
            if initValue.find('.') == -1:
                initValue = initValue + '.0'
            
            if name == 'scale':
                spinCtrl = RAWCustomCtrl.FloatSpinCtrl(self, id, initValue, TextLength = 100, never_negative = True)
            else:
                spinCtrl = RAWCustomCtrl.FloatSpinCtrl(self, id, initValue, TextLength = 100)
                
            spinCtrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, bindfunc)
            
            control_sizer.Add(label, 1, wx.TOP, 3)
            control_sizer.Add(spinCtrl, 1, wx.EXPAND)
            
        
    def _createSimpleSpinCtrls(self, control_sizer):
        
        
        for each_spinctrl in self.spin_controls:
                spin_id = each_spinctrl[1]
                spin_label_text = each_spinctrl[0]
                qtxtId = each_spinctrl[2]
                spin_range = each_spinctrl[3]
                spin_name = each_spinctrl[4]
                
                spin_min = spin_range[0]
                spin_max = spin_range[1]
    
                spin_min, spin_max = self.sasm.getBinnedQ()[0], self.sasm.getBinnedQ()[-1]
            
                nlow, nhigh = 0, (len(self.sasm.getBinnedQ())-1)
                      
                spin_label = wx.StaticText(self, -1, spin_label_text)
                spin_label.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
                spin_label.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
                spin_label.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
                        
                spin_control = RAWCustomCtrl.IntSpinCtrl(self, spin_id, min = nlow, max = nhigh, TextLength = 43) 
                                        
                if spin_name == 'nlow':
                    spin_control.SetValue(nlow)
                elif spin_name == 'nhigh':
                    spin_control.SetValue(nhigh)
                
                spin_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onQrangeChange)
                
                q_ctrl = wx.TextCtrl(self, qtxtId, '', size = (55,22), style = wx.PROCESS_ENTER)
                q_ctrl.Bind(wx.EVT_TEXT_ENTER, self._onEnterInQrangeTextCtrl)
                
                spin_sizer = wx.BoxSizer()
                spin_sizer.Add(q_ctrl, 0, wx.RIGHT, 3)
                spin_sizer.Add(spin_control, 0)
                
                control_sizer.Add(spin_label, 0)        
                control_sizer.Add(spin_sizer, 0)
                
#--- ** IFT Panel **

class IFTPanel(wx.Panel):
    def __init__(self, parent, raw_settings, expParams = []):
        wx.Panel.__init__(self, parent, name = 'IFTPanel')
        
        self.expParams = expParams
        self.raw_settings = raw_settings
        self.iftplot_panel = wx.FindWindowByName('IFTPlotPanel')
        
        self.paramsInGui={'Filename' : (wx.NewId(), 'filename'),
                          'Algorithm' : (wx.NewId(), 'algo'),
                          'ForceZero' : (wx.NewId(), 'forcezero'),
                          'I(0)' : (wx.NewId(), 'info'),
                          'Rg'   : (wx.NewId(), 'info'),
                          'Dmax' : (wx.NewId(), 'intctrl'),
                          'Alpha': (wx.NewId(), 'ctrl'),
                          'Qmin' : (wx.NewId(), 'listctrl'),
                          'Qmax' : (wx.NewId(), 'listctrl')}
        
        self.buttons = (("BIFT", self._OnDoBift),
                        ("Load", self._OnLoadFile),
                        ("Options", self._OnOptions),
                        ("Clear Plot", self._OnClearAll),
                        ("Solve", self._OnManual),
                        ("Clear List", self._OnClearList))
        
        # /* INSERT WIDGETS */ 
        
        self.panelsizer = wx.BoxSizer(wx.VERTICAL)
        
        self._initializeIcons()
        toolbarsizer = self._createToolbar()

        self.underpanel = scrolled.ScrolledPanel(self, -1, style = wx.BORDER_SUNKEN)
        self.underpanel.SetVirtualSize((200, 200))
        self.underpanel.SetScrollRate(20,20)
      
        self.all_manipulation_items = []
        self.selected_item_list = []
        
        self.underpanel_sizer = wx.BoxSizer(wx.VERTICAL)    
        self.underpanel.SetSizer(self.underpanel_sizer)
        
        self.infoBox = IFTControlPanel(self)
        #self.infoBox.Enable(False)
        
        self.panelsizer.Add(self.infoBox, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 10)
        self.panelsizer.Add(toolbarsizer, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND, 5)        
        self.panelsizer.Add(self.underpanel, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 3)
        
        self.createButtons(self.panelsizer)
        #self.panelsizer.Add(self.buttonSizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.TOP |wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        
        self.SetSizer(self.panelsizer)
        
        self._star_marked_item = None
        self._raw_settings = raw_settings
        
    def _initializeIcons(self):
        self.collapse_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'collapse_all.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.expand_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'expand_all.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        self.show_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'open_eye.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.hide_all_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'close_eye.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
    def _createToolbar(self):
        
        sizer = wx.BoxSizer()
        
        collapse_all = wx.StaticBitmap(self, -1, self.collapse_all_png)
        expand_all = wx.StaticBitmap(self, -1, self.expand_all_png)
        show_all = wx.StaticBitmap(self, -1, self.show_all_png)
        hide_all = wx.StaticBitmap(self, -1, self.hide_all_png)
        show_all.SetToolTipString('Show All')
        hide_all.SetToolTipString('Hide All')
        
        collapse_all.SetToolTipString('Collapse All')
        expand_all.SetToolTipString('Expand All')
        
        collapse_all.Bind(wx.EVT_LEFT_DOWN, self._onCollapseAllButton)
        expand_all.Bind(wx.EVT_LEFT_DOWN, self._onExpandAllButton)
        show_all.Bind(wx.EVT_LEFT_DOWN, self._onShowAllButton)
        hide_all.Bind(wx.EVT_LEFT_DOWN, self._onHideAllButton)
        
        sizer.Add(show_all, 0, wx.LEFT, 5)
        sizer.Add(hide_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)
        sizer.Add(collapse_all, 0, wx.RIGHT, 5)
        sizer.Add(expand_all, 0, wx.RIGHT, 3)
        
        return sizer
    
    
    def addItem(self, sasm, item_colour = 'black'):
        
        newItem = IFTItemPanel(self.underpanel, sasm, font_colour = item_colour)
        self.Freeze()
        self.underpanel_sizer.Add(newItem, 0, wx.GROW)
        self.underpanel_sizer.Layout()
        
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.Layout()            
        self.Refresh()
        self.Thaw()
        
        # Keeping track of all items in our list:
        self.all_manipulation_items.append(newItem)
        
        sasm.item_panel = newItem
        
        
        self.iftplot_panel.plotSASM(sasm, 2)
        self.iftplot_panel.canvas.draw()
        
        self.deselectAllExceptOne(newItem)
        newItem.toggleSelect()
        newItem._updateColourIndicator()
        
    def setItemAsBackground(self, item):
        
        bg_sasm = self._raw_settings.get('BackgroundSASM')
        
        if bg_sasm != None:
            try:
                bg_sasm.itempanel.enableStar(False)
            except:
                pass
        
        self._raw_settings.set('BackgroundSASM', item.sasm)
        item.enableStar(True)
        self._star_marked_item = item
        
    def getBackgroundItem(self):
        return self._star_marked_item
        
    def clearList(self):
        self.Freeze()
        
        rest_of_items = []
        for each in self.all_manipulation_items:
            
            try:
                each.Destroy()
            except ValueError:
                rest_of_items.append(each)
                
        self.all_manipulation_items = rest_of_items
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        
        self._star_marked_item = None
        
        self.Thaw()
        
    def clearBackgroundItem(self):
        self._raw_settings.set('BackgroundSASM', None)
        self._star_marked_item = None
        
    def _collapseAllItems(self):
        for each in self.all_manipulation_items:
            each.showControls(False)
        
        self.underpanel.Layout()            
        self.underpanel.Refresh()
        
        self.Layout()            
        self.Refresh()
            
    def _expandAllItems(self):
        for each in self.all_manipulation_items:
            each.showControls(True)
            
        self.underpanel.Layout()            
        self.underpanel.Refresh()
        
        self.Layout()            
        self.Refresh()
    
    def removeItem(self, item):
        
        self.all_manipulation_items.remove(item)
        
        if item == self._star_marked_item:
            self._star_marked_item = None
        
        item.Destroy()
        
    def getSelectedItems(self):
        
        self.selected_item_list = []
        
        for each in self.all_manipulation_items:
            if each._selected == True:
                self.selected_item_list.append(each)
            
        return self.selected_item_list
    
    def deselectAllExceptOne(self, item, line = None, enableLocatorLine = False):
        
        if line == None:    
            for each in self.all_manipulation_items:
                if each != item:
                    each._selected = True
                    each.toggleSelect()
        else:
            for each in self.all_manipulation_items:
                if each.sasm.getLine() == line:
                    each._selected = False
                    each.toggleSelect()
                else:
                    each._selected = True
                    each.toggleSelect()
                    
    def removeSelectedItems(self):
       
        if len(self.getSelectedItems()) == 0: return
        
        self.Freeze()
        
        info_panel = wx.FindWindowByName('InformationPanel')
        info_panel.clearInfo()
        
        axes_that_needs_updated_legend = []
         
        for each in self.getSelectedItems():
                     
            plot_panel = each.sasm.plot_panel
            
            each.sasm.line.remove()
            each.sasm.err_line[0][0].remove()
            each.sasm.err_line[0][1].remove()
            each.sasm.err_line[1][0].remove()
            
            i = plot_panel.plotted_sasms.index(each.sasm)
            plot_panel.plotted_sasms.pop(i)
            
            if not each.sasm.axes in axes_that_needs_updated_legend:
                axes_that_needs_updated_legend.append(each.sasm.axes)
            
            if each == self._star_marked_item:
                self._star_marked_item = None
            
            idx = self.all_manipulation_items.index(each)
            self.all_manipulation_items[idx].Destroy()
            self.all_manipulation_items.pop(idx)
        
        for eachaxes in axes_that_needs_updated_legend:
            if eachaxes == plot_panel.subplot1:
                wx.CallAfter(plot_panel.updateLegend, 1)
            else:
                wx.CallAfter(plot_panel.updateLegend, 2)
            
        wx.CallAfter(plot_panel.canvas.draw)
        
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Refresh()    
        
        self.Thaw()
        
    def _onShowAllButton(self, event):
        
        for each in self.all_manipulation_items:
           each.showItem(True)
           
        plot_panel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plot_panel.updateLegend, 1)
        wx.CallAfter(plot_panel.updateLegend, 2)
        wx.CallAfter(plot_panel.fitAxis)
        
        self.underpanel.Layout()            
        self.underpanel.Refresh()
            
        self.Layout()            
        self.Refresh()
           
    def _onHideAllButton(self, event):
        self.underpanel.Freeze()
        
        for each in self.all_manipulation_items:
           each.showItem(False)
        
        self.underpanel.Layout()            
        self.underpanel.Refresh()
            
        self.Layout()            
        self.Refresh()
        
        self.underpanel.Thaw()
        
        plot_panel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plot_panel.updateLegend, 1)
        wx.CallAfter(plot_panel.updateLegend, 2)
        wx.CallAfter(plot_panel.canvas.draw)
               
    def _onCollapseAllButton(self, event):
        self._collapseAllItems()
        
    def _onExpandAllButton(self, event):
        self._expandAllItems()
            
    def _onBiftButton(self, event):
        pass
         
    def _onRemoveButton(self, event):
        self.removeSelectedItems()
    
    def _onSaveButton(self, event):
        self.saveItems()
    
    def _onSyncButton(self, event):
        syncdialog = SyncDialog(self)
        syncdialog.ShowModal()
        syncdialog.Destroy()
             
    def _onSuperimposeButton(self, event):
        mainworker_cmd_queue.put(['superimpose_items', ( self._star_marked_item, self.getSelectedItems()  )])
        
    def synchronizeSelectedItems(self, sync_parameters):
        star_item = self.getBackgroundItem()
        
        if not star_item or (len(sync_parameters) == 0):
            return
        
        star_sasm = star_item.getSASM()
        
        scale = star_sasm.getScale()
        offset = star_sasm.getOffset()
        nmin, nmax = star_sasm.getQrange()
        qmin, qmax = star_sasm.getBinnedQ()[nmin], star_sasm.getBinnedQ()[nmax-1]
        linestyle = star_sasm.line.get_linestyle()
        linewidth = star_sasm.line.get_linewidth()
        linemarker = star_sasm.line.get_marker() 
        
        selected_items = self.getSelectedItems()
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
        
        for each_item in selected_items:
            if each_item == star_item:
                continue
            
            sasm = each_item.getSASM()
            
            old_nmin, old_nmax = sasm.getQrange()
            
            try:
                if 'nmin' in sync_parameters and 'nmax' in sync_parameters:
                    sasm.setQrange([nmin, nmax])
                elif 'nmin' in sync_parameters:
                    sasm.setQrange([nmin, old_nmax])
                elif 'nmax' in sync_parameters:
                    sasm.setQrange([old_nmin, nmax])                    
                    
            except SASExceptions.InvalidQrange, msg:
                dial = wx.MessageDialog(None, 'Filename : ' + sasm.getParameter('filename') + '\n\n' + str(msg),
                                'Invalid Qrange',
                                wx.OK | wx.CANCEL | wx.NO_DEFAULT | wx.ICON_QUESTION)
                answer = dial.ShowModal()
                    
                if answer == wx.ID_CANCEL:
                    return
                
            q = sasm.getBinnedQ()
            
            if 'qmin' in sync_parameters and 'qmax' in sync_parameters:
                closest = findClosest(qmin, q)
                new_nmin = numpy.where(q == closest)[0][0]
                closest = findClosest(qmax, q)
                new_nmax = numpy.where(q == closest)[0][0]
                sasm.setQrange([new_nmin, new_nmax])
            elif 'qmin' in sync_parameters:
                closest = findClosest(qmin, q)
                new_nmin = numpy.where(q == closest)[0][0]
                sasm.setQrange([new_nmin, old_nmax])    
            elif 'qmax' in sync_parameters:
                closest = findClosest(qmax, q)
                new_nmax = numpy.where(q == closest)[0][0]
                sasm.setQrange([old_nmin, new_nmax])
                
            if 'scale' in sync_parameters:
                sasm.scale(scale)
            if 'offset' in sync_parameters:
                sasm.offset(offset)
            if 'linestyle' in sync_parameters:
                sasm.line.set_linestyle(linestyle)
            if 'linewidth' in sync_parameters:
                sasm.line.set_linewidth(linewidth)
            if 'linemarker' in sync_parameters:
                sasm.line.set_marker(linemarker)
            
            each_item.updateControlsFromSASM()
        
    def movePlots(self, ExpObjList, toAxes):
        
        for each_item in ExpObjList:
            
            each = each_item.getSASM()
            
            if each.axes != toAxes:
                plotpanel = each.plot_panel
      
                each.line.remove()
                each.err_line[0][0].remove()
                each.err_line[0][1].remove()
                each.err_line[1][0].remove()
        
                line_color = each.line.get_color()
                
                if each_item.getLegendLabel() != '':
                    label = each_item.getLegendLabel()
                else:
                    label = None
                
                wx.CallAfter(plotpanel.plotSASM, each, toAxes, color = line_color, legend_label_in = label)
                
                
        plotpanel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plotpanel.updateLegend, 1)
        wx.CallAfter(plotpanel.updateLegend, 2)
        wx.CallAfter(plotpanel.canvas.draw)
    
    def getItems(self):
        return self.all_manipulation_items
            
    def updateLayout(self):
        self.underpanel_sizer.Layout()
        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
    
    def saveItems(self):
        selected_items = self.getSelectedItems()
        
        if len(selected_items) == 0:
            return
        
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        save_path = dirctrl_panel.getDirLabel()
        
        dirdlg = wx.DirDialog(self, "Please select save directory:", str(save_path))
            
        if dirdlg.ShowModal() == wx.ID_OK:               
            save_path = dirdlg.GetPath()
        else:
            return
        
        mainworker_cmd_queue.put(['save_items', [save_path, selected_items]])
    
##################################################################################### 

 
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
        
        N = self.expParams['PrPoints']
        
        
        ExpObj = BIFT.SingleSolve(alpha, dmax, SelectedExpObj, N)
        
        ExpObj.isBifted = True
        
        biftPlotPanel = wx.FindWindowByName('BIFTPlotPanel')
        biftPlotPanel.PlotBIFTExperimentObject(ExpObj)
        
        self.infoBox.updateInfo([SelectedExpObj, ExpObj])
  
    def _OnClearAll(self, evt):
        plotpage = wx.FindWindowByName('BIFTPlotPanel')
        plotpage.OnClear(0)
        
    def _OnOptions(self, evt):
        
        optionsPage = wx.FindWindowByName('OptionsPage')
        optionsPage.ShowOptionsDialog(3)    # Index 1 = BIFT page
    
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
         
         for idx in range(0, self.filelist.GetCount()):
             E = self.filelist.GetClientData(idx)
             
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
       
            sasm, img = SASFileIO.loadFile(selected_file, self.raw_settings)
                        
            self.addItem(sasm)
            
 
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
                
                panelsizer.Add(sizer, 0.1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
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

class IFTItemPanel(wx.Panel):
    def __init__(self, parent, sasm, font_colour = 'BLACK', legend_label = ''):
        
        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)
        
        self.parent = parent
        self.sasm = sasm
        self.sasm.itempanel = self
        
        self.manipulation_panel = wx.FindWindowByName('IFTPanel')
        self.plot_panel = wx.FindWindowByName('PlotPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.ift_panel = wx.FindWindowByName('IFTPanel')
        self.iftctrl_panel = wx.FindWindowByName('IFTControlPanel')
        
        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.info_settings = {'hdr_choice' : 0}
        
        self._selected_as_bg = False
        self._selected_for_plot = True
        self._controls_visible = True
        self._selected = False
        self._legend_label = legend_label
        
        self._font_colour = font_colour
        
        filename = sasm.getParameter('filename')
               
        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
        #Label, TextCtrl_ID, SPIN_ID
        
        self._initializeIcons()
                                       
        self.qmax = len(self.sasm.q)
                             
        self.spin_controls = (("q Min:", wx.NewId(), wx.NewId(), (1, self.qmax-1), 'nlow'),        
                             ("q Max:", wx.NewId(), wx.NewId(), (2, self.qmax), 'nhigh'))
        
        self.float_spin_controls = (
                                   # ("Conc:", wx.NewId(), 'conc', '1.0', self._onScaleOffsetChange),
                                    ("Scale:", wx.NewId(), 'scale', str(sasm.getScale()), self._onScaleOffsetChange),
                                    ("Offset:", wx.NewId(), 'offset', str(sasm.getOffset()), self._onScaleOffsetChange))
    
        self.SelectedForPlot = RAWCustomCtrl.CustomCheckBox(self, -1, filename)
        self.SelectedForPlot.SetValue(True)
        self.SelectedForPlot.Bind(wx.EVT_CHECKBOX, self._onSelectedChkBox)
        self.SelectedForPlot.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.SelectedForPlot.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
        self.SelectedForPlot.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        
        self.SelectedForPlot.SetToolTipString('Show Plot')
        self.SelectedForPlot.SetForegroundColour(font_colour)
        
        self.legend_label_text = wx.StaticText(self, -1, '')
        
        self.legend_label_text.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.legend_label_text.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.legend_label_text.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
        
        conv = mplcol.ColorConverter()
        #color = conv.to_rgb(self.sasm.line.get_mfc())
        color = [1,1,1]
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        
        self.colour_indicator = RAWCustomCtrl.ColourIndicator(self, -1, color, size = (20,15))
        self.colour_indicator.Bind(wx.EVT_LEFT_DOWN, self._onLinePropertyButton)
        self.colour_indicator.SetToolTipString('Line Properties')

        self.bg_star = wx.StaticBitmap(self, -1, self.gray_png)
        self.bg_star.Bind(wx.EVT_LEFT_DOWN, self._onStarButton)
        self.bg_star.SetToolTipString('Mark')
        
        self.expand_collapse = wx.StaticBitmap(self, -1, self.collapse_png)
        self.expand_collapse.Bind(wx.EVT_LEFT_DOWN, self._onExpandCollapseButton)
        self.expand_collapse.SetToolTipString('Collapse/Expand')
        
        self.target_icon = wx.StaticBitmap(self, -1, self.target_png)
        self.target_icon.Bind(wx.EVT_LEFT_DOWN, self._onTargetButton)
        self.target_icon.SetToolTipString('Locate Line')

        self.info_icon = wx.StaticBitmap(self, -1, self.info_png)
        self.info_icon.Bind(wx.EVT_LEFT_DOWN, self._onInfoButton)
        self.info_icon.SetToolTipString('Show Extended Info\n--------------------------------\nRg: N/A\nI(0): N/A')
        
        self.locator_on = False
        self.locator_old_width = 1
        
        panelsizer = wx.BoxSizer()
        panelsizer.Add(self.SelectedForPlot, 0, wx.LEFT | wx.TOP, 3)
        panelsizer.Add(self.legend_label_text, 0, wx.LEFT | wx.TOP, 3)
        panelsizer.Add((1,1), 1, wx.EXPAND)
        panelsizer.Add(self.expand_collapse, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.info_icon, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.target_icon, 0, wx.RIGHT | wx.TOP, 4)
        panelsizer.Add(self.colour_indicator, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.bg_star, 0, wx.LEFT | wx.RIGHT | wx.TOP, 3)
        
        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(panelsizer, 1, wx.EXPAND)
        
        self.controlSizer = wx.BoxSizer(wx.VERTICAL)
        self.controlSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 3, hgap = 7)
       
        self._createSimpleSpinCtrls(self.controlSizer)
        self._createFloatSpinCtrls(self.controlSizer) 
        
        self.topsizer.Add((5,5),0)
        self.topsizer.Add(self.controlSizer, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)
        
        self.SetSizer(self.topsizer)
        
        self.SetBackgroundColour(wx.Color(250,250,250))
        
        self._initStartPosition()
        self._updateQTextCtrl()
        
        if self.sasm.getParameter('analysis').has_key('guinier'):
            self.updateInfoTip(self.sasm.getParameter('analysis'))
            
        #controls_not_shown = self.main_frame.raw_settings.get('ManipItemCollapsed')
        controls_not_shown = True
        if controls_not_shown:
            self.showControls(not controls_not_shown)
        
    
    def updateInfoTip(self, analysis_dict, fromGuinierDialog = False):
        
        
        if analysis_dict.has_key('guinier'):
            guinier = analysis_dict['guinier']
        else:
            guinier = {}
        
        string0 = 'Show Extended Info\n--------------------------------'
        string1 = ''
        string2 = ''
        string3 = ''
        
        if guinier.has_key('Rg') and guinier.has_key('I0'):
            rg = guinier['Rg']
            i_zero = guinier['I0']
        
            string1 = '\nRg: ' + str(rg) + '\nI(0): ' + str(i_zero)
        else:
            string1 = '\nRg: N/A' + '\nI(0): N/A'
            
        if self.sasm.getAllParameters().has_key('Conc'):
            string2 = '\nConc: ' + str(self.sasm.getParameter('Conc'))   
        
        if self.sasm.getAllParameters().has_key('Notes'):
            if self.sasm.getParameter('Notes') != '':
                string3 = '\nNote: ' + str(self.sasm.getParameter('Notes'))  
        
        string = string0+string1+string2+string3
        
        if string != '':    
            self.info_icon.SetToolTipString(string)
                  
        if fromGuinierDialog:
            self.info_panel.updateInfoFromItem(self)
                
    def enableStar(self, state):
        if state == True:
            self.bg_star.SetBitmap(self.star_png)
            self._selected_as_bg = True
        else:
            self.bg_star.SetBitmap(self.gray_png)
            self._selected_as_bg = False
        
        self.bg_star.Refresh()
        
    def removeSelf(self):
        #Has to be callafter under Linux.. or it'll crash
        wx.CallAfter(self.manipulation_panel.removeSelectedItems)
        
    def getSASM(self):
        return self.sasm        
    
    def getFontColour(self):
        return self._font_colour
    
    def getSelectedForPlot(self):
        return self._selected_for_plot
    
    def getLegendLabel(self):
        return self._legend_label
    
    def updateControlsFromSASM(self):    
        scale = self.sasm.getScale()
        offset = self.sasm.getOffset()
        qmin, qmax = self.sasm.getQrange()
        
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1])
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1])
        qmintxt = wx.FindWindowById(self.spin_controls[0][2])
        qmaxtxt = wx.FindWindowById(self.spin_controls[1][2])
        
        qmin_ctrl.SetValue(str(qmin))
        qmax_ctrl.SetValue(str(qmax-1))        
        qmintxt.SetValue(str(round(self.sasm.q[qmin],4)))
        qmaxtxt.SetValue(str(round(self.sasm.q[qmax-1],4)))
        
        scale_ctrl = wx.FindWindowById(self.float_spin_controls[0][1])
        offset_ctrl = wx.FindWindowById(self.float_spin_controls[1][1])
    
        offset_ctrl.SetValue(str(offset))
        scale_ctrl.SetValue(str(scale))
        
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
    
    def toggleSelect(self):
        
        if self._selected:
            self._selected = False
            self.SetBackgroundColour(wx.Color(250,250,250))
            self.info_panel.clearInfo()
            self.iftctrl_panel.updateInfo()
        else:
            self._selected = True
            self.SetBackgroundColour(wx.Color(200,200,200))
            self.SetFocusIgnoringChildren()
            self.info_panel.updateInfoFromItem(self)
            self.iftctrl_panel.updateInfo()
        
        self.Refresh()
        
    def enableLocatorLine(self):
        
        self.locator_on = not self.locator_on
        
        if self.locator_on == True:
            self.target_icon.SetBitmap(self.target_on_png)
            self.locator_old_width = self.sasm.line.get_linewidth()
            new_width = self.locator_old_width + 2.0
            self.sasm.line.set_linewidth(new_width)
            wx.CallAfter(self.sasm.plot_panel.canvas.draw)
        else:
            self.target_icon.SetBitmap(self.target_png)
            self.sasm.line.set_linewidth(self.locator_old_width)
            wx.CallAfter(self.sasm.plot_panel.canvas.draw)
            
        self.target_icon.Refresh()
        
    def getControlsVisible(self):
        return self._controls_visible
        
    def showControls(self, state):
        
        if state == False:
            self.expand_collapse.SetBitmap(self.expand_png)
            self._controls_visible = False
            self.controlSizer.Hide(0, True)
            self.controlSizer.Hide(1, True)
            self.controlSizer.Hide(2, True)
            self.controlSizer.Hide(3, True)
            self.controlSizer.Hide(4, True)
            self.controlSizer.Hide(5, True)
            self.controlSizer.Hide(6, True)
            self.controlSizer.Hide(7, True)
        else:
            self.expand_collapse.SetBitmap(self.collapse_png)
            self._controls_visible = True
            self.controlSizer.Show(0, True)
            self.controlSizer.Show(1, True)
            self.controlSizer.Show(2, True)
            self.controlSizer.Show(3, True)
            self.controlSizer.Show(4, True)
            self.controlSizer.Show(5, True)
            self.controlSizer.Show(6, True)
            self.controlSizer.Show(7, True)
            
        self.expand_collapse.Refresh()
        self.topsizer.Layout()
        
    
    def showItem(self, state):
        self._selected_for_plot = state
        
        if self._selected_for_plot == False:
            self._controls_visible = False
            self.showControls(self._controls_visible)
        
        self.SelectedForPlot.SetValue(self._selected_for_plot)
        self.sasm.line.set_visible(self._selected_for_plot)
        self.sasm.line.set_picker(self._selected_for_plot)      #Line can't be selected when it's hidden
        
    def updateFilenameLabel(self):
        filename = self.sasm.getParameter('filename')
        
        if self._legend_label == '':
            self.sasm.line.set_label(filename)
        self.plot_panel.updateLegend(self.sasm.axes)
        self.SelectedForPlot.SetLabel(str(filename))
        self.SelectedForPlot.Refresh()
        self.topsizer.Layout()
        self.GetParent().Layout()            
        self.GetParent().Refresh()
    
    def _initializeIcons(self):
        
        self.gray_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'Star-icon_notenabled.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.star_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'Star-icon_org.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        self.collapse_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'collapse.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.expand_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'expand.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        self.target_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'target.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.target_on_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'target_orange.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()

        self.info_png = wx.Image(os.path.join(RAWWorkDir, 'resources', 'info_16_2.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()

    def _initStartPosition(self):
        
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1])
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1])
        
        qrange = self.sasm.getQrange()
        
        qmin_ctrl.SetValue(str(qrange[0]))
        
    def _updateColourIndicator(self):
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.sasm.line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        
        self.colour_indicator.updateColour(color)
        
    def _onLinePropertyButton(self, event):
        dialog = LinePropertyDialog(self, self.sasm.line)
        dialog.ShowModal()
        dialog.Destroy()
        self._updateColourIndicator()
        
        if self.sasm.axes == self.plot_panel.subplot1:
            wx.CallAfter(self.plot_panel.updateLegend, 1)
        else:
            wx.CallAfter(self.plot_panel.updateLegend, 2)
            
        self.sasm.plot_panel.canvas.draw()
        
    def _onExpandCollapseButton(self, event):
        self._controls_visible = not self._controls_visible
        self.showControls(self._controls_visible)
        
        self.GetParent().Layout()            
        self.GetParent().Refresh()
        
        self.GetParent().GetParent().Layout()            
        self.GetParent().GetParent().Refresh()
            
    def _onTargetButton(self, event):
        self.enableLocatorLine()
        
    def _onInfoButton(self, event):
        pass
            
    def _showPopupMenu(self):

        menu = wx.Menu()
        
        number_of_selected_items = len(self.manipulation_panel.getSelectedItems())
        
#        iftmenu = wx.Menu()
#        iftmenu.Append(10, 'Run BIFT')
#        iftmenu.Append(11, 'Run GNOM using current Dmax')
#        iftmenu.AppendSeparator()
#        iftmenu.Append(12, 'Add to IFT list')
        
        convertq_menu = wx.Menu()
        convertq_menu.Append(15, '>> 10')
        convertq_menu.Append(16, '<< 10^-1')
        
        submenu = menu.Append(4, 'Subtract')
        avgmenu = menu.Append(6, 'Average' )
        menu.Append(14, 'Rename')
            
        menu.AppendSeparator()
        menu.Append(5, 'Remove' )
        menu.AppendSeparator()
        menu.Append(13, 'Guinier fit...')
        #menu.AppendMenu(3, 'Indirect Fourier Transform', iftmenu)
        menu.AppendMenu(wx.NewId(), 'Convert q-scale', convertq_menu)
        
        menu.AppendSeparator()
        img = menu.Append(19, 'Show image')
        
        if not self.sasm.getAllParameters().has_key('load_path'):
            img.Enable(False)
        menu.Append(20, 'Show data...')
        menu.Append(21, 'Show header...')
        
        menu.AppendSeparator()
        menu.Append(8, 'Move to top plot')
        menu.Append(9, 'Move to bottom plot')
        menu.AppendSeparator()
        menu.Append(17, 'Set legend label...')
        menu.Append(18, 'Save analysis info...')
        menu.AppendSeparator()
        menu.Append(7, 'Save selected file(s)')
        
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)        
        self.PopupMenu(menu)
    
    def _onShowImage(self):
        
        if self.sasm.getAllParameters().has_key('load_path'):
            path = self.sasm.getParameter('load_path')
            mainworker_cmd_queue.put(['show_image', path])
    
    def _onPopupMenuChoice(self, evt):
            
        if evt.GetId() == 3:
            #IFT
            analysisPage.runBiftOnExperimentObject(self.ExpObj, expParams)
        
        if evt.GetId() == 4:
            #Subtract
            selected_items = self.manipulation_panel.getSelectedItems()
            marked_item = self.manipulation_panel.getBackgroundItem()
            mainworker_cmd_queue.put(['subtract_items', [marked_item, selected_items]])
        
        if evt.GetId() == 5:
            #Delete
            wx.CallAfter(self.manipulation_panel.removeSelectedItems)
        
        if evt.GetId() == 6:
            #Average 
            selected_items = self.manipulation_panel.getSelectedItems()
            mainworker_cmd_queue.put(['average_items', selected_items])
            
        if evt.GetId() == 7:
            self.manipulation_panel.saveItems()
                
        if evt.GetId() == 8:
            #Move to top plot
            plotpanel = wx.FindWindowByName('PlotPanel')
            selected_items = self.manipulation_panel.getSelectedItems()
            self.manipulation_panel.movePlots(selected_items, plotpanel.subplot1)
                
        if evt.GetId() == 9:
            #Move to bottom plot
            plotpanel = wx.FindWindowByName('PlotPanel')
            selected_items = self.manipulation_panel.getSelectedItems()
            self.manipulation_panel.movePlots(selected_items, plotpanel.subplot2)
            
        if evt.GetId() == 13:
            #Guinier fit
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSASMList = self.manipulation_panel.getSelectedItems()
            
            sasm = selectedSASMList[0].getSASM()
            Mainframe.showGuinierFitFrame(sasm, selectedSASMList[0])
            
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
            
        if evt.GetId() == 14:
            dlg = FilenameChangeDialog(self, self.sasm.getParameter('filename'))
            dlg.ShowModal()
            filename =  dlg.getFilename()
            dlg.Destroy()
            
            if filename:
                self.sasm.setParameter('filename', filename)
                self.updateFilenameLabel()
        
        if evt.GetId() == 15:
            #A to s
            self.sasm.scaleBinnedQ(10.0)
            self._updateQTextCtrl()
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
            
        if evt.GetId() == 16:
            #s to A
            self.sasm.scaleBinnedQ(0.1)
            self._updateQTextCtrl()
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
        
        if evt.GetId() == 17:
            dlg = LegendLabelChangeDialog(self, self._legend_label)
            answer = dlg.ShowModal()
            legend_label = dlg.getLegendLabel()
            dlg.Destroy()
            
            if answer == wx.ID_OK:
                self._legend_label = legend_label
                self._updateLegendLabel()
                
        if evt.GetId() == 18:
            #Save Analysis Info
            #self._saveAnalysisInfo()
            
            dlg = SaveAnalysisInfoDialog(self, self.main_frame.raw_settings, self.manipulation_panel.getSelectedItems())
            dlg.ShowModal()
            dlg.Destroy()
            
        if evt.GetId() == 19:
            #Show Image
            self._onShowImage()
            
        if evt.GetId() == 20:
            dlg = DataDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()
            
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
            
        if evt.GetId() == 21:
            dlg = HdrDataDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()
            
            #wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
    
    def _saveAnalysisInfo(self):
        selected_items = self.manipulation_panel.getSelectedItems()
            
        if len(selected_items) == 0:
            return
        
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        save_path = dirctrl_panel.getDirLabel()
        
        filters = 'Comma Separated Files (*.csv)|*.csv'
            
        dialog = wx.FileDialog( None, style = wx.SAVE | wx.OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path) 
        #dirdlg = wx.DirDialog(self, "Please select save directory:", str(save_path))
            
        if dialog.ShowModal() == wx.ID_OK:               
            save_path = dialog.GetPath()
        else:
             return
            
        mainworker_cmd_queue.put(['save_analysis_info', [selected_items, save_path]])
    
    def _onKeyPress(self, evt):
        
        key = evt.GetKeyCode()
   
        if key == wx.WXK_DELETE and self._selected == True:
            self.removeSelf()
            
        if key == wx.WXK_UP:
            if evt.CmdDown():
                print 'CTRL UP'
            else:
                print "UP!"
        if key == wx.WXK_DOWN:
            if evt.CmdDown():
                print 'CTRL DOWN'
            else:
                print "DOWN!"
                
        if key == 83: #S
            self._onShowImage()
            
            
    def _onRightMouseButton(self, evt):
        if not self._selected:
            self.toggleSelect()
            self.manipulation_panel.deselectAllExceptOne(self)
                    
        self._showPopupMenu()
        
    def _onLeftMouseButton(self, evt):
        ctrl_is_down = evt.CmdDown()
        shift_is_down = evt.ShiftDown()
        
        manipulation_panel = wx.FindWindowByName('IFTPanel')
        
        if shift_is_down:
            try:
                
                first_marked_item_idx = manipulation_panel.all_manipulation_items.index(manipulation_panel.getSelectedItems()[0])
                last_marked_item = manipulation_panel.getSelectedItems()[-1]
                last_marked_item_idx = manipulation_panel.all_manipulation_items.index(last_marked_item)
                
                this_item_idx = manipulation_panel.all_manipulation_items.index(self)
            
                if last_marked_item_idx > this_item_idx:
                    adj = 0
                    idxs = [first_marked_item_idx, this_item_idx]
                else:
                    idxs = [last_marked_item_idx, this_item_idx]
                    adj = 1
                        
                top_item = max(idxs)
                bottom_item = min(idxs)
            
                for each in manipulation_panel.all_manipulation_items[bottom_item+adj:top_item+adj]:
                    each.toggleSelect()
            except IndexError:
                pass
            
        elif ctrl_is_down:
            self.toggleSelect()
        else:
            manipulation_panel.deselectAllExceptOne(self)
            self.toggleSelect()
            
        evt.Skip()
              
    def _onStarButton(self, event):

        if self._selected_as_bg == True:
            self.enableStar(False)
            self.manipulation_panel.clearBackgroundItem()
        else:
            self.manipulation_panel.setItemAsBackground(self)
            
    def _showInvalidValueError(self):
        wx.CallAfter(wx.MessageBox, 'The entered value is invalid. Please remove non-numeric characters.', 'Invalid Value Error', style = wx.ICON_ERROR)
                    
    def _onScaleOffsetChange(self, event):
        id = event.GetId()
        
        try:
            value = float(event.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return
        
        for each_label, each_id, each_name, eachInit_value, each_bindfunc in self.float_spin_controls:
            
            if id == each_id:
                
                if each_name == 'scale':
                    self.sasm.scale(value)
                elif each_name == 'offset':
                    self.sasm.offset(value)
        
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])

        event.Skip()
        
    def _updateQTextCtrl(self):
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1])
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1])
        
        qmintxt = wx.FindWindowById(self.spin_controls[0][2])
        qmaxtxt = wx.FindWindowById(self.spin_controls[1][2])
        
        try:
            qmin = int(qmin_ctrl.GetValue())
            qmax = int(qmax_ctrl.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return
        
        qmintxt.SetValue(str(round(self.sasm.q[qmin],4)))
        qmaxtxt.SetValue(str(round(self.sasm.q[qmax],4)))
        
        qrange = (qmin, qmax+1) # +1 to be able to use the range for array slicing [0:n+1]

        self.sasm.setQrange(qrange)   
    
    def _updateLegendLabel(self):
        
        if self._legend_label == '' or self._legend_label == None:
            self.sasm.line.set_label(self.sasm.getParameter('filename'))
            self.legend_label_text.SetLabel('')
        else:
            self.sasm.line.set_label(str(self._legend_label))
            self.legend_label_text.SetLabel('[' + str(self._legend_label) + ']')
            
        wx.CallAfter(self.sasm.plot_panel.updateLegend, self.sasm.axes)
        
    
    def _onQrangeChange(self, event):
        self._updateQTextCtrl()
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
        
    def _onEnterInQrangeTextCtrl(self, evt):
        
        id = evt.GetId()
        txtctrl = wx.FindWindowById(id)
        
        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return
        
        if id == self.spin_controls[0][2]:
                spinctrl = wx.FindWindowById(self.spin_controls[0][1])
        elif id == self.spin_controls[1][2]:
                spinctrl = wx.FindWindowById(self.spin_controls[1][1])
        
        q = self.sasm.getBinnedQ()
        
        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
                
        closest = findClosest(val, q)
        idx = numpy.where(q == closest)[0][0]  
        
        spinctrl.SetValue(idx)
        self._onQrangeChange(None)
        txtctrl.SelectAll()
     
    def _onSelectedChkBox(self, event):
        self._selected_for_plot = not self._selected_for_plot
        
        self.showItem(self._selected_for_plot)
        
        self.GetParent().Layout()            
        self.GetParent().Refresh()
        
        wx.CallAfter(self.plot_panel.updateLegend, self.sasm.axes)
        wx.CallAfter(self.sasm.plot_panel.canvas.draw)
        
        self.sasm.plot_panel.fitAxis([self.sasm.axes])
        
    def _createFloatSpinCtrls(self, control_sizer):
        
        for label, id, name, initValue, bindfunc in self.float_spin_controls:
            
            label = wx.StaticText(self, -1, label)
            
            label.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            label.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            label.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
            
            if initValue.find('.') == -1:
                initValue = initValue + '.0'
            
            if name == 'scale':
                spinCtrl = RAWCustomCtrl.FloatSpinCtrl(self, id, initValue, TextLength = 100, never_negative = True)
            else:
                spinCtrl = RAWCustomCtrl.FloatSpinCtrl(self, id, initValue, TextLength = 100)
                
            spinCtrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, bindfunc)
            
            control_sizer.Add(label, 1, wx.TOP, 3)
            control_sizer.Add(spinCtrl, 1, wx.EXPAND)
            
        
    def _createSimpleSpinCtrls(self, control_sizer):
        
        
        for each_spinctrl in self.spin_controls:
                spin_id = each_spinctrl[1]
                spin_label_text = each_spinctrl[0]
                qtxtId = each_spinctrl[2]
                spin_range = each_spinctrl[3]
                spin_name = each_spinctrl[4]
                
                spin_min = spin_range[0]
                spin_max = spin_range[1]
    
                spin_min, spin_max = self.sasm.getBinnedQ()[0], self.sasm.getBinnedQ()[-1]
            
                nlow, nhigh = 0, (len(self.sasm.getBinnedQ())-1)
                      
                spin_label = wx.StaticText(self, -1, spin_label_text)
                spin_label.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
                spin_label.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
                spin_label.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)
                        
                spin_control = RAWCustomCtrl.IntSpinCtrl(self, spin_id, min = nlow, max = nhigh, TextLength = 43) 
                                        
                if spin_name == 'nlow':
                    spin_control.SetValue(nlow)
                elif spin_name == 'nhigh':
                    spin_control.SetValue(nhigh)
                
                spin_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onQrangeChange)
                
                q_ctrl = wx.TextCtrl(self, qtxtId, '', size = (55,22), style = wx.PROCESS_ENTER)
                q_ctrl.Bind(wx.EVT_TEXT_ENTER, self._onEnterInQrangeTextCtrl)
                
                spin_sizer = wx.BoxSizer()
                spin_sizer.Add(q_ctrl, 0, wx.RIGHT, 3)
                spin_sizer.Add(spin_control, 0)
                
                control_sizer.Add(spin_label, 0)        
                control_sizer.Add(spin_sizer, 0)

class IFTControlPanel(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent, -1, name = 'IFTControlPanel')
        
        self.parent = parent
        
        self.ift_panel = wx.FindWindowByName('IFTPanel')
        self.sasm = None
        
        self.controlData = (  ('File :', parent.paramsInGui['Filename']),
                          #    ('I(0) :', parent.paramsInGui['I(0)']),
                          #    ('Rg :',   parent.paramsInGui['Rg']),
                              ('Dmax :', parent.paramsInGui['Dmax']),
                              ('Alpha (log):',parent.paramsInGui['Alpha']),
                              ('Algorithm :', parent.paramsInGui['Algorithm']),
                              ('Force zero :', parent.paramsInGui['ForceZero'])
                              )
                          #    ('Qmin :', parent.paramsInGui['Qmin']),
                          #    ('Qmax :', parent.paramsInGui['Qmax']))
                          
        
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
                self.filename_label = wx.StaticText(self, id, '', size = (60,20))
                sizer.Add(labelbox, 0)
                sizer.Add(self.filename_label, 0)
                sizer.Add((1,1),0)
                sizer.Add((1,1),0)
                
            elif type == 'forcezero':
                labelbox = wx.StaticText(self, -1, label)
                self.dzero_chkbox = wx.CheckBox(self, -1, 'D0')
                self.dmax_chkbox = wx.CheckBox(self, -1, 'Dmax')
                chkbox = wx.CheckBox(self, -1, 'Continous')
                box = wx.BoxSizer() 
                sizer.Add(labelbox, 0,  wx.ALIGN_CENTER_VERTICAL)
                box.Add(self.dzero_chkbox, 0, wx.RIGHT, 5)
                box.Add(self.dmax_chkbox, 0)
                sizer.Add(box,0)
                sizer.Add(wx.StaticText(self, -1, 'Update :'),0, wx.ALIGN_CENTER)
                sizer.Add(chkbox, 0, wx.ALIGN_CENTER)
               
                self.dzero_chkbox.SetValue(True)
                
            elif type == 'algo':
                labelbox = wx.StaticText(self, -1, label)
                ctrl = wx.Choice(self, id, size = (80,20), choices = ['BIFT', 'GNOM', 'Manual'])
                ctrl.Select(0)
                #ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onSpinChange)
                button = wx.Button(self, -1, 'Run')
                button2 = wx.Button(self, -1, 'Settings')
                
                
                sizer.Add(labelbox, 0, wx.ALIGN_CENTER_VERTICAL)
                sizer.Add(ctrl, 0, wx.ALIGN_CENTER)
                sizer.Add(button, 0, wx.ALIGN_CENTER)
                sizer.Add(button2, 0, wx.ALIGN_CENTER)
            
            elif type == 'info':
                labelbox = wx.StaticText(self, -1, label)
                infobox = wx.TextCtrl(self, id, '', size = (60,20))
                infobox.SetEditable(False)
                sizer.Add(labelbox, 0)
                sizer.Add(infobox, 0)
            
            elif type == 'ctrl':
                labelbox = wx.StaticText(self, -1, label)
                ctrl = RAWCustomCtrl.FloatSpinCtrl(self, id)
                ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onSpinChange)
                sizer.Add(labelbox, 0, wx.ALIGN_CENTER)
                sizer.Add(ctrl, 0, wx.ALIGN_CENTER)
                
            elif type == 'intctrl':
                labelbox = wx.StaticText(self, -1, label)
                ctrl = RAWCustomCtrl.IntSpinCtrl(self, id, 1)
                ctrl.SetValue(80)
                ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onSpinChange)
                sizer.Add(labelbox, 0, wx.ALIGN_CENTER_VERTICAL)
                sizer.Add(ctrl, 0, wx.ALIGN_CENTER)
            
            elif type == 'listctrl':
                labelbox = wx.StaticText(self, -1, label)
                ctrl = RAWCustomCtrl.IntSpinCtrl(self, id, [1.0])
                ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onSpinChange)
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
    
    def getDmaxAlpha(self):
        
        D = wx.FindWindowById(self.parent.paramsInGui['Dmax'][0])
        dmax = D.GetValue()
            
        A = wx.FindWindowById(self.parent.paramsInGui['Alpha'][0])
        alpha = A.GetValue()
        
        return (dmax, alpha)
    
    def updateInfo(self):   
        
        
        items = self.ift_panel.getSelectedItems()
        
        if len(items) == 1:
            sasm = items[0].getSASM()
            filename = sasm.getParameter('filename')
            self.filename_label.SetLabel(str(filename))
        elif len(items) > 1:
            self.filename_label.SetLabel('Multiple Selections')
        else:
            self.clearInfo()
        
    def clearInfo(self):
        self.filename_label.SetLabel('')
#--- ** Centering Panel **

class MaskingPanel(wx.Panel):
    
    def __init__(self, parent,id):
        
        wx.Panel.__init__(self, parent, id, name = 'MaskingPanel')
        
        self.mask_choices = {'Beamstop mask' : 'BeamStopMask',
                             'Readout-Dark mask' : 'ReadOutNoiseMask',
                             'Transparent BS mask' : 'TransparentBSMask'}
        
        self.CIRCLE_ID, self.RECTANGLE_ID, self.POLYGON_ID = wx.NewId(), wx.NewId(), wx.NewId()
        self.all_button_ids = [self.CIRCLE_ID, self.RECTANGLE_ID, self.POLYGON_ID]
        
        self._main_frame = wx.FindWindowByName('MainFrame')
        self.image_panel = wx.FindWindowByName('ImagePanel')
        
        self._initBitmaps()
        manual_box = wx.StaticBox(self, -1, 'Mask Drawing')
        self.manual_boxsizer = wx.StaticBoxSizer(manual_box)
        self.manual_boxsizer.Add((1,1), 1, wx.EXPAND)
        self.manual_boxsizer.Add(self._createDrawButtons(), 0, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        self.manual_boxsizer.Add((1,1), 1, wx.EXPAND)
        
        auto_box = wx.StaticBox(self, -1, 'Mask Creation')
        auto_boxsizer = wx.StaticBoxSizer(auto_box)
        auto_boxsizer.Add(self._createMaskSelector(), 1, wx.EXPAND |wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        
        option_box = wx.StaticBox(self, -1, 'Mask Drawing Options')
        option_boxsizer = wx.StaticBoxSizer(option_box)
        option_boxsizer.Add(self._createMaskOptions(), 1, wx.EXPAND |wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        
        button_sizer = self._createButtonSizer()
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.manual_boxsizer, 0, wx.EXPAND | wx.ALL, 5)
        self.sizer.Add(option_boxsizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.sizer.Add(auto_boxsizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        self.SetSizer(self.sizer)
        
        self._center = [0,0]
        self.show_center = False
        #self.updateCenterFromSettings()
        
    def setTool(self, tool):
        self.image_panel.setTool(tool)
        
    def _createDrawButtons(self):
        
        sizer = wx.BoxSizer()
    
        self.circle_button = wxbutton.GenBitmapToggleButton(self, self.CIRCLE_ID, self.circle_bmp, size = (80,80))
        self.rectangle_button = wxbutton.GenBitmapToggleButton(self, self.RECTANGLE_ID, self.rectangle_bmp, size = (80,80))
        self.polygon_button = wxbutton.GenBitmapToggleButton(self, self.POLYGON_ID, self.polygon_bmp, size = (80,80))
        
        self.circle_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        self.rectangle_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        self.polygon_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        
        self.circle_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        self.rectangle_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        self.polygon_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        sizer.Add(self.circle_button, 0)
        sizer.Add(self.rectangle_button,0)
        sizer.Add(self.polygon_button,0)
        
        
        save_button= wx.Button(self, -1, "Save")
        save_button.Bind(wx.EVT_BUTTON, self._onSaveMaskToFile)
        
        load_button= wx.Button(self, -1, "Load")
        load_button.Bind(wx.EVT_BUTTON, self._onLoadMaskFromFile)
        
        clear_button= wx.Button(self, -1, "Clear")
        clear_button.Bind(wx.EVT_BUTTON, self._onClearDrawnMasks)
        
        button_sizer = wx.BoxSizer()
        button_sizer.Add(save_button, 0, wx.RIGHT, 3)
        button_sizer.Add(load_button, 0, wx.RIGHT, 3)
        button_sizer.Add(clear_button, 0)
        
        
        final_sizer = wx.BoxSizer(wx.VERTICAL)
        
        final_sizer.Add(sizer,0)
        final_sizer.Add(button_sizer,0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 10)
        
        return final_sizer
    
    def _createMaskOptions(self):
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        center_chkbox = wx.CheckBox(self, -1, 'Show Beam Center')
        center_chkbox.Bind(wx.EVT_CHECKBOX, self._onShowCenterChkbox)
    
        sizer.Add(center_chkbox, 0)
        #sizer.Add(button_sizer,0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 5)
            
        return sizer
        
    def _onShowCenterChkbox(self, event):
        
        x_c = self._main_frame.raw_settings.get('Xcenter')
        y_c = self._main_frame.raw_settings.get('Ycenter')
        
        cent = (x_c, y_c)
        
        chkbox = event.GetEventObject()
        
        if chkbox.GetValue() == True:
            self.show_center = True
            wx.CallAfter(self.image_panel.drawCenterPatch, cent)
        else:
            self.show_center = False
            wx.CallAfter(self.image_panel.removeCenterPatch)
    
    def _createMaskSelector(self):
        
        sizer = wx.BoxSizer()

        self.selector_choice = wx.Choice(self, -1, choices = self.mask_choices.keys())
        self.selector_choice.Select(2)
        
        set_button = wx.Button(self, -1, 'Set', size = (60,-1))
        set_button.Bind(wx.EVT_BUTTON, self._onSetButton)
        
        clear_button = wx.Button(self, -1, 'Remove', size = (60,-1))
        clear_button.Bind(wx.EVT_BUTTON, self._onClearButton)
        
        show_button = wx.Button(self, -1, 'Show', size = (60,-1))
        show_button.Bind(wx.EVT_BUTTON, self._onShowButton)
        
        sizer.Add(self.selector_choice, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(clear_button, 0)
        sizer.Add(set_button,0)
        sizer.Add(show_button,0)
        
        return sizer
    
    def _onShowButton(self, event):
        selected_mask = self.selector_choice.GetStringSelection()
        mask_key = self.mask_choices[selected_mask]
        
        plot_parameters = self.image_panel.getPlotParameters()        
        mask_dict = self._main_frame.raw_settings.get('Masks')
        mask_params = mask_dict[mask_key]
        
        saved_mask = mask_params[1]
        
        masks_copy = []     # Need to copy the masks to new objects, ortherwise all kinds of strange things happen
                            # when you switch between masks or modify masks.
        
        if saved_mask != None:
            for each in saved_mask:
                masks_copy.append(copy.copy(each))
            plot_parameters['storedMasks'] = masks_copy
            wx.CallAfter(self.image_panel.plotStoredMasks)
        else:
            wx.CallAfter(self.image_panel.clearAllMasks)
            wx.MessageBox('No mask has been set for this mask type.', 'No mask set.', style = wx.ICON_EXCLAMATION)
    
    def _onSetButton(self, event):
        
        selected_mask = self.selector_choice.GetStringSelection()
        
        if selected_mask != '':
            mask_key = self.mask_choices[selected_mask]
            
            mask_dict = self._main_frame.raw_settings.get('Masks')
            
            if mask_dict[mask_key][1] != None:
                dial = wx.MessageDialog(None, 'Do you want to overwrite the existing mask?', 'Overwrite exisiting mask?', 
                                        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
                answer = dial.ShowModal()

                if answer == wx.ID_NO:
                    return
            
            plot_parameters = self.image_panel.getPlotParameters()
            masks = plot_parameters['storedMasks']
            masks_copy = []
            
            for each in masks:
                masks_copy.append(copy.copy(each))
            
            if masks == [] or self.image_panel.img == None:
                wx.MessageBox('No masks has been drawn. Draw a mask before setting it as the current mask.', 'Setting mask failed') 
                return
            
            img_dim = self.image_panel.img.shape
    
            if len(masks) != 0:
                queue = self._main_frame.getWorkerThreadQueue()
                queue.put(['create_mask', [mask_key, masks_copy, img_dim]])
                            
        
    def _onClearButton(self, event):
        
        selected_mask = self.selector_choice.GetStringSelection()
        
        if selected_mask != '':
            
            dial = wx.MessageDialog(None, 'Are you sure you want to delete this mask?', 'Are you sure?', 
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            answer = dial.ShowModal()

            if answer == wx.ID_NO:
                return
            
            mask_key = self.mask_choices[selected_mask]
            mask_dict = self._main_frame.raw_settings.get('Masks')
            mask_dict[mask_key] = [None, None]
            self.image_panel.clearAllMasks()
    
    def _onClearDrawnMasks(self, event):
        wx.CallAfter(self.image_panel.clearAllMasks)
    
    def _onLoadMaskFromFile(self, event):
        file = self._createFileDialog(wx.OPEN)
        
        if file:
            queue = self._main_frame.getWorkerThreadQueue()
            queue.put(['load_mask', [file]])
    
    def _onSaveMaskToFile(self, event):
        
        file = self._createFileDialog(wx.SAVE)
        
        if file:
            plot_parameters = self.image_panel.getPlotParameters()
            masks = plot_parameters['storedMasks']
            masks_copy = []
        
            for each in masks:
                masks_copy.append(copy.copy(each))
        
            queue = self._main_frame.getWorkerThreadQueue()
            queue.put(['save_mask', [file, masks_copy]])
    
    def _onDrawButton(self, event):
        button = event.GetEventObject()
        id = button.GetId()
        
        if button.GetToggle():
            self.disableDrawButtons(id)
            
            if self.CIRCLE_ID == id:
                self.setTool('circle')
            elif self.RECTANGLE_ID == id:
                self.setTool('rectangle')
            elif self.POLYGON_ID == id:
                self.setTool('polygon')
                    
    def disableDrawButtons(self, id = None):
        for each in self.all_button_ids:
                if each != id:
                    wx.FindWindowById(each).SetToggle(False)
        
    def _createButtonSizer(self):
        sizer = wx.BoxSizer()
        
        ok_button = wx.Button(self, wx.ID_OK, 'OK')
        #cancel_button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        
        sizer.Add(ok_button, 0, wx.RIGHT, 10)
        #sizer.Add(cancel_button, 0)
        
        ok_button.Bind(wx.EVT_BUTTON, self._onOkButton)
        #cancel_button.Bind(wx.EVT_BUTTON, self._onCancelButton)
    
        return sizer
    
    def _onOkButton(self, event):
        self.image_panel.stopMaskCreation()
        wx.CallAfter(self.image_panel.clearAllMasks)
        wx.CallAfter(self._main_frame.closeMaskingPane)
    
    def _onCancelButton(self, event):
        self.image_panel.stopMaskCreation()
        wx.CallAfter(self._main_frame.closeMaskingPane)
        wx.CallAfter(self.image_panel.clearAllMasks)
    
    def updateView(self):
        wx.CallAfter(self.image_panel.clearPatches)
        if self.show_center:
            x_c = self._main_frame.raw_settings.get('Xcenter')
            y_c = self._main_frame.raw_settings.get('Ycenter')
        
            cent = (x_c, y_c)
            wx.CallAfter(self.image_panel.drawCenterPatch, cent)
             
    def _createFileDialog(self, mode):
         
        file = None
        
        path = wx.FindWindowByName('FileListCtrl').path
        
        if mode == wx.OPEN:
            filters = 'Mask files (*.msk)|*.msk|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters, defaultDir = path)
        if mode == wx.SAVE:
            filters = 'Mask files (*.msk)|*.msk'
            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters, defaultDir = path)        
        
        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            
        # Destroy the dialog
        dialog.Destroy()
        
        return file
    
    def _initBitmaps(self):
        
        workdir = self._main_frame.RAWWorkDir
        
        self.circle_bmp = wx.Image(os.path.join(workdir, 'resources', 'CircleIcon.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.rectangle_bmp = wx.Image(os.path.join(workdir, 'resources', 'RectangleIcon.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.polygon_bmp = wx.Image(os.path.join(workdir, 'resources', 'PolygonIcon3.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()

class CenteringPanel(wx.Panel):
    
    
    def __init__(self, parent,id):
        
        wx.Panel.__init__(self, parent, id, name = 'CenteringPanel')
        
        self.ID_UP, self.ID_DOWN, self.ID_RIGHT, self.ID_LEFT, self.ID_TARGET =  ( wx.NewId(), wx.NewId(), wx.NewId(), wx.NewId(), wx.NewId())
        
        self._x_center = None
        self._y_center = None
        self._repeat_timer = wx.Timer()
        self._repeat_timer.Bind(wx.EVT_TIMER, self._onRepeatTimer)
        
        self.manual_widget_list = []
        
        self._main_frame = wx.FindWindowByName('MainFrame')
        self.image_panel = wx.FindWindowByName('ImagePanel')
        
        self._initBitmaps()
        manual_box = wx.StaticBox(self, -1, 'Manual Center/Calibration Adjustments')
        self.manual_boxsizer = wx.StaticBoxSizer(manual_box)
        
        button_sizer = self._createCenteringButtonsSizer()
        info_sizer = self._createCenteringInfoSizer()
        
        self.manual_boxsizer.Add(info_sizer, 0, wx.ALL, 5)
        self.manual_boxsizer.Add((1,1), 1, wx.EXPAND)
        self.manual_boxsizer.Add(button_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.RIGHT, 15)
        
        auto_box = wx.StaticBox(self, -1, 'Automatic Centering')
        auto_boxsizer = wx.StaticBoxSizer(auto_box)
        
        auto_sizer = self._createAutoCenteringSizer()
        auto_boxsizer.Add(auto_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        button_sizer = self._createButtonSizer()
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.manual_boxsizer, 0, wx.EXPAND | wx.ALL, 5)
        self.sizer.Add(auto_boxsizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        self.SetSizer(self.sizer)
        
        self._center = [0,0]
        self.updateCenterFromSettings()
        wx.CallAfter(self._updateAgbeRings)
                
    def _initBitmaps(self):
        
        workdir = self._main_frame.RAWWorkDir
        
        self.up_arrow_img = wx.Image(os.path.join(workdir, 'resources', 'center_arrow_up.png'), wx.BITMAP_TYPE_ANY)
        self.right_arrow_img = self.up_arrow_img.Rotate90()
        self.down_arrow_img = self.right_arrow_img.Rotate90()
        self.left_arrow_img = self.down_arrow_img.Rotate90()
        
        self.up_arrow_bmp = self.up_arrow_img.ConvertToBitmap()
        self.right_arrow_bmp = self.right_arrow_img.ConvertToBitmap()
        self.down_arrow_bmp = self.down_arrow_img.ConvertToBitmap()
        self.left_arrow_bmp = self.left_arrow_img.ConvertToBitmap()
        
        self.target_bmp = wx.Image(os.path.join(workdir, 'resources', 'center_target.png'), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
    
    def _createAutoCenteringSizer(self):
        
        sizer = wx.BoxSizer()
        
        choices = ['Silver-Behenate']
        
        self.method_text = wx.StaticText(self, -1, 'Method:')
        
        self.auto_method_choice = wx.Choice(self, -1, choices = choices)
        self.auto_method_choice.Select(0)
        
        method_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        method_sizer.Add(self.method_text,0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        method_sizer.Add(self.auto_method_choice, 0)
        
        self.auto_start_button = wx.Button(self, -1, 'Start')
        self.auto_start_button.Bind(wx.EVT_BUTTON, self._onAutoCenterStartButton)
        
        #Automatic centering doesn't work on compiled versions!
        #self.auto_start_button.Enable(False)
        
        sizer.Add(method_sizer,0, wx.RIGHT, 10)
        sizer.Add((1,1), 1, wx.EXPAND)
        sizer.Add(self.auto_start_button,0)
        
        return sizer
    
    def _createCenteringButtonsSizer(self):
        
        buttonsizer = wx.FlexGridSizer(rows = 3, cols = 3)
        
        up_button = wx.BitmapButton(self, self.ID_UP, self.up_arrow_bmp)
        down_button = wx.BitmapButton(self,self.ID_DOWN, self.down_arrow_bmp)
        right_button = wx.BitmapButton(self, self.ID_RIGHT , self.right_arrow_bmp)
        left_button = wx.BitmapButton(self, self.ID_LEFT, self.left_arrow_bmp)
        target_button = wx.BitmapButton(self, self.ID_TARGET, self.target_bmp)
        
        up_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        down_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        right_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        left_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        
        up_button.Bind(wx.EVT_LEFT_UP, self._onCenteringButtonsUp)
        down_button.Bind(wx.EVT_LEFT_UP, self._onCenteringButtonsUp)
        right_button.Bind(wx.EVT_LEFT_UP, self._onCenteringButtonsUp)
        left_button.Bind(wx.EVT_LEFT_UP, self._onCenteringButtonsUp)
        
        
        target_button.Bind(wx.EVT_BUTTON, self._onTargetButton)
        
        buttonsizer.Add((1,1))
        buttonsizer.Add(up_button, 0)
        buttonsizer.Add((1,1))
        buttonsizer.Add(left_button,0)
        buttonsizer.Add(target_button, 0)
        buttonsizer.Add(right_button, 0)
        buttonsizer.Add((1,1))
        buttonsizer.Add(down_button, 0)
        buttonsizer.Add((1,1))
        
        self.manual_widget_list.append(up_button)
        self.manual_widget_list.append(down_button)
        self.manual_widget_list.append(left_button)
        self.manual_widget_list.append(right_button)
        self.manual_widget_list.append(target_button)
        
        return buttonsizer
    
    def _createCenteringInfoSizer(self):
        
        info_sizer = wx.BoxSizer()
        
        step_list= ['1', '2', '5', '10', '20', '50', '100', '500']
        pattern_list = ['None', 'Silver-Behenate']
        
        self._x_cent_text = wx.TextCtrl(self, -1, '0', size = (65, -1), style = wx.TE_PROCESS_ENTER)
        self._y_cent_text = wx.TextCtrl(self, -1, '0', size = (65, -1), style = wx.TE_PROCESS_ENTER)
        self._y_cent_text.Bind(wx.EVT_TEXT_ENTER, self._onEnterInCenterCtrl)
        self._x_cent_text.Bind(wx.EVT_TEXT_ENTER, self._onEnterInCenterCtrl)
        self._x_cent_text.Bind(wx.EVT_KILL_FOCUS, self._onEnterInCenterCtrl)
        self._y_cent_text.Bind(wx.EVT_KILL_FOCUS, self._onEnterInCenterCtrl)
        
        self._step_combo = wx.ComboBox(self, -1, choices = step_list, size = self._x_cent_text.GetSize())
        self._step_combo.Select(0)
        
        self._wavelen_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 80)
        self._pixel_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 80)
        self._sd_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 80)
        
        self._sd_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onSampDetDistSpin)
        self._wavelen_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onPixelWavelengthChange)
        self._pixel_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onPixelWavelengthChange)
                
        self._pattern_list = wx.Choice(self, -1, choices = pattern_list)
        self._pattern_list.Select(1)
        self._pattern_list.Bind(wx.EVT_CHOICE, self._onPatternChoice)
        
        wavelen_label = wx.StaticText(self, -1, 'Wavelength:')
        sd_label = wx.StaticText(self, -1, 'Sample-Detector Distance:')
        pixel_label = wx.StaticText(self, -1, 'Detector Pixel Size:')
        
        ylabel = wx.StaticText(self, -1, 'Y center:')
        xlabel = wx.StaticText(self, -1, 'X center:')
        step_label = wx.StaticText(self, -1, 'Steps:')
        pattern_label = wx.StaticText(self, -1, 'Pattern:')
        
        sd_unit_label = wx.StaticText(self, -1, 'mm')
        pixelsize_unit_label = wx.StaticText(self, -1, 'um')
        wavelength_unit_label = wx.StaticText(self, -1, 'A')
        
        x_sizer = wx.BoxSizer(wx.VERTICAL)
        y_sizer = wx.BoxSizer(wx.VERTICAL)
        step_sizer = wx.BoxSizer(wx.VERTICAL)
        wave_sizer = wx.BoxSizer(wx.VERTICAL)
        pixel_sizer = wx.BoxSizer(wx.VERTICAL)
        sd_sizer = wx.BoxSizer(wx.VERTICAL)
        pattern_sizer = wx.BoxSizer(wx.VERTICAL)
    
        sd_unit_sizer = wx.BoxSizer()
        pixelsize_unit_sizer = wx.BoxSizer()
        wavelength_unit_sizer = wx.BoxSizer()
    
        step_sizer.Add(step_label,0)
        step_sizer.Add(self._step_combo, 0)
        x_sizer.Add(xlabel, 0)
        x_sizer.Add(self._x_cent_text,0)        
        y_sizer.Add(ylabel, 0)
        y_sizer.Add(self._y_cent_text,0)
    
        sd_unit_sizer.Add(self._sd_text, 0, wx.RIGHT, 5)
        sd_unit_sizer.Add(sd_unit_label, 0, wx.ALIGN_CENTER_VERTICAL)
        
        pixelsize_unit_sizer.Add(self._pixel_text, 0, wx.RIGHT, 5)
        pixelsize_unit_sizer.Add(pixelsize_unit_label, 0, wx.ALIGN_CENTER_VERTICAL)
        
        wavelength_unit_sizer.Add(self._wavelen_text, 0, wx.RIGHT, 5)
        wavelength_unit_sizer.Add(wavelength_unit_label, 0, wx.ALIGN_CENTER_VERTICAL)
    
        wave_sizer.Add(wavelen_label, 0)
        wave_sizer.Add(wavelength_unit_sizer, 0)
        
        sd_sizer.Add(sd_label, 0)
        sd_sizer.Add(sd_unit_sizer, 0)
        
        pixel_sizer.Add(pixel_label, 0)
        pixel_sizer.Add(pixelsize_unit_sizer, 0)
        
        pattern_sizer.Add(pattern_label, 0)
        pattern_sizer.Add(self._pattern_list, 0)
        
    
        self.final_sizer = wx.BoxSizer(wx.VERTICAL)
    
        self.xycenter_sizer = wx.BoxSizer()
        self.xycenter_sizer.Add(x_sizer,0, wx.RIGHT, 5)
        self.xycenter_sizer.Add(y_sizer,0, wx.RIGHT, 5)
        self.xycenter_sizer.Add(step_sizer,0)
        
        self.calib_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.calib_sizer.Add(wave_sizer, 0, wx.BOTTOM, 5)
        self.calib_sizer.Add(sd_sizer, 0, wx.BOTTOM, 5)
        self.calib_sizer.Add(pixel_sizer, 0, wx.BOTTOM, 5)
        self.calib_sizer.Add(pattern_sizer,0, wx.BOTTOM, 5)
        
        self.final_sizer.Add(self.xycenter_sizer,0, wx.BOTTOM, 5)
        self.final_sizer.Add(self.calib_sizer,0)
        
        self.manual_widget_list.append(self._x_cent_text)
        self.manual_widget_list.append(self._y_cent_text)
        self.manual_widget_list.append(self._step_combo)
        self.manual_widget_list.append(self._wavelen_text)
        self.manual_widget_list.append(self._pixel_text)
        self.manual_widget_list.append(self._sd_text)
        self.manual_widget_list.append(self._pattern_list)
        
        return self.final_sizer
            
    def _createButtonSizer(self):
        sizer = wx.BoxSizer()
        
        ok_button = wx.Button(self, wx.ID_OK, 'OK')
        cancel_button = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        
        sizer.Add(ok_button, 0, wx.RIGHT, 10)
        sizer.Add(cancel_button, 0)
        
        ok_button.Bind(wx.EVT_BUTTON, self._onOkButton)
        cancel_button.Bind(wx.EVT_BUTTON, self._onCancelButton)
    
        return sizer
    
    def _onEnterInCenterCtrl(self, event):
        
        x = str(self._x_cent_text.GetValue()).replace(',','.')
        y = str(self._y_cent_text.GetValue()).replace(',','.')
        
        try:
            self.setCenter([int(float(x)),int(float(y))])
        except ValueError:
            pass
        
    def _onOkButton(self, event):
        self.image_panel.enableCenterClickMode(False)
        self.image_panel.enableAgbeAutoCentMode(False)
        self.image_panel.agbe_selected_points = []
        
        button = self.auto_start_button
        if button.GetLabelText() == 'Done':
            button.SetLabel('Start')
            self._enableControls(True)
        
        wx.CallAfter(self._main_frame.closeCenteringPane)
        wx.CallAfter(self.image_panel.clearPatches)
        
        self._main_frame.raw_settings.set('Xcenter', self._center[0])
        self._main_frame.raw_settings.set('Ycenter', self._center[1])
        
        sd, wavelength, pixel_size = self._getCalibValues()
        
        self._main_frame.raw_settings.set('SampleDistance', sd)
        self._main_frame.raw_settings.set('WaveLength', wavelength)
        self._main_frame.raw_settings.set('DetectorPixelSize', pixel_size)
        
        sd_pixels = round(SASImage.calcFromSDToAgBePixels(sd, wavelength, pixel_size / 1000.0),0)
                
        self._main_frame.raw_settings.set('PixelCalX', sd_pixels)
    
    def _getCalibValues(self):
        
        sd = float(self._sd_text.GetValue())
        wavelength = float(self._wavelen_text.GetValue())
        pixel_size = float(self._pixel_text.GetValue())

        return sd, wavelength, pixel_size

    def _onCancelButton(self, event):
        self.image_panel.enableCenterClickMode(False)
        self.image_panel.enableAgbeAutoCentMode(False)
        self.image_panel.agbe_selected_points = []
        
        self.updateCenterFromSettings()
        wx.CallAfter(self._main_frame.closeCenteringPane)
        wx.CallAfter(self.image_panel.clearPatches)
        
        button = self.auto_start_button
        if button.GetLabelText() == 'Done':
            button.SetLabel('Start')
            self._enableControls(True)
            
            
    
    def _onRepeatTimer(self, event):
        steps = int(self._step_combo.GetValue())
        wx.Yield()
        wx.CallAfter(self._moveCenter, self._pressed_button_id, steps)
    
    def _onCenteringButtonsUp(self, event):

        self._repeat_timer.Stop()
        event.Skip()
    
    def _onCenteringButtons(self, event):
        id = event.GetId()
        
        steps = int(self._step_combo.GetValue())
        self._pressed_button_id = id
        wx.CallAfter(self._moveCenter, id, steps)
        
        if platform.system() != 'Darwin':
            self._repeat_timer.Start(100)
        
        event.Skip()
    
    def _moveCenter(self, id, steps):
        
        if id == self.ID_UP:
            self._center[1] += steps
        if id == self.ID_DOWN:
            self._center[1] -= steps
        if id == self.ID_RIGHT:
            self._center[0] += steps
        if id == self.ID_LEFT:
            self._center[0] -= steps
            
        self.updateCenterTextCtrls()
        wx.CallAfter(self._updatePlots)
        
    def _onPixelWavelengthChange(self, event):
        self._updatePlots()
        
    def _onTargetButton(self, event): 
        self.image_panel.enableCenterClickMode()
        
        wx.MessageBox('Click on the image to move the center to a new location.', 'Select center on image')
    
    def _onPatternChoice(self, event):
        selection = self._pattern_list.GetSelection()
        
        if selection == 1: #Agbe
            wx.CallAfter(self._updateAgbeRings)
            
        elif selection == 0: #none
            wx.CallAfter(self.image_panel.clearPatches)
            
    def _onSampDetDistSpin(self, event):
        self._updatePlots()
        
    def _onAutoCenterStartButton(self, event):
        button = event.GetEventObject()
        
        if button.GetLabelText() == 'Start':
            button.SetLabel('Done')
            self._startAgbeAutoCentering()
        elif button.GetLabelText() == 'Done':
            button.SetLabel('Start')
            self._endAgbeAutoCentering()
            #self._updatePlots()
           
    def _endAgbeAutoCentering(self):
        for each in self.manual_widget_list:
            each.Enable(True)
        
        self.image_panel.enableAgbeAutoCentMode(False)
        points = self.image_panel.getSelectedAgbePoints()
        img = self.image_panel.img
        
        try:
            x, r = SASImage.calcCenterCoords(img, points, tune = True)  # x = (x_c,y_c)
        except SASExceptions.CenterNotFound:
            self.image_panel.agbe_selected_points = []
            wx.MessageBox('The center could not be found.\nPlease try again or use the manual settings.', 'Center was not found')
            return
        
        self._center = [int(x[0]), int(x[1])]
        
        wavelength = float(self._wavelen_text.GetValue())
        pixel_size = float(self._pixel_text.GetValue())
        
        sd_dist = round(SASImage.calcAgBeSampleDetectorDist(r, wavelength, pixel_size / 1000.0),1)
        self._sd_text.SetValue(str(sd_dist))
        self.updateCenterTextCtrls()
        
        self._pattern_list.Select(1)
        wx.CallAfter(self.image_panel._drawAgBeRings, x, r)
        self.image_panel.agbe_selected_points = []

    def _enableControls(self, state):
        
        for each in self.manual_widget_list:
            each.Enable(state)

    def _startAgbeAutoCentering(self):
        
        self._enableControls(False)
        
        wx.CallAfter(self.image_panel.clearPatches)
        answer = wx.MessageBox('Please select at least 3 points just outside the inner circle of the AgBe image and then press the "Done" button', 'AgBe Center Calibration', wx.OK | wx.CANCEL)
        
        self.image_panel.enableAgbeAutoCentMode()
        
    def _updateAgbeRings(self):
        
        sd_distance, wavelength, pixel_size = self._getCalibValues()
        
        sample_detec_pixels = SASImage.calcFromSDToAgBePixels(sd_distance, wavelength, pixel_size / 1000.0)
                
        wx.CallAfter(self.image_panel.clearPatches)
        wx.CallAfter(self.image_panel._drawAgBeRings, self._center, sample_detec_pixels)
    
    def updateCenterTextCtrls(self):
        self._x_cent_text.SetValue(str(self._center[0]))
        self._y_cent_text.SetValue(str(self._center[1]))
    
    def _updatePlots(self):
        
        if self._pattern_list.GetSelection() == 1:
            self._updateAgbeRings()
            
    def updateCenterFromSettings(self):    
        x_center = self._main_frame.raw_settings.get('Xcenter')
        y_center = self._main_frame.raw_settings.get('Ycenter')
        
        wavelength = self._main_frame.raw_settings.get('WaveLength')
        pixel_size = self._main_frame.raw_settings.get('DetectorPixelSize') 
        samp_detc_dist = self._main_frame.raw_settings.get('SampleDistance')
        
        self._sd_text.SetValue(str(samp_detc_dist))
        self._pixel_text.SetValue(str(pixel_size))
        self._wavelen_text.SetValue(str(wavelength))
        
        self._center = [x_center, y_center]
        self.updateCenterTextCtrls()
    
    def _updateSampleDetectorDist(self):
        
        wavelength = float(self._wavelen_text.GetValue())
        pixel_size = float(self._pixel_text.GetValue())
        samp_dist = float(self._sd_text.GetValue())
        
        samp_dist_in_pixels = SASImage.calcFromSDToAgBePixels(samp_dist, wavelength, pixel_size)
        
        print samp_dist_in_pixels
        
        samp_dist_in_mm = round(SASImage.calcAgBeSampleDetectorDist(samp_dist_in_pixels, wavelength, pixel_size),1)
        
        self._sd_text.SetValue(str(samp_dist_in_mm))      
        
        print 'wops!'
        
    def updateAll(self):
        self._updatePlots()
        self.updateCenterFromSettings()
    
    def setCenter(self, center):
        self._center = center
        self.updateCenterTextCtrls()
        self._updatePlots()
        


#----- **** InformationPanel ****

class InformationPanel(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent, name = 'InformationPanel')
        
        infoSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.analysis_data = [('Rg:', 'Rg', wx.NewId()),
                              ('I0:', 'I0', wx.NewId()),
                              ('MW:', 'MW', wx.NewId())]
        
        self.conc_data = ('Conc:', 'Conc', wx.NewId())
        
        self.analysis_info_sizer = self._createAnalysisInfoSizer()
        
        infoSizer.Add(self.analysis_info_sizer, 0, wx.ALL | wx.EXPAND, 5)

        #header_note_box = wx.StaticBox(self, -1, 'Header data / Notes')
        #header_note_boxsizer = wx.StaticBoxSizer(header_note_box, orient = wx.VERTICAL)
        
        header_note_boxsizer = wx.BoxSizer(wx.VERTICAL)
        
        header_note_boxsizer.Add(wx.StaticText(self,-1,'Description / Notes:'), 0)
        header_note_boxsizer.Add(self._createNoteSizer(), 0, wx.ALL | wx.EXPAND, 5)
        header_note_boxsizer.Add(wx.StaticText(self,-1,'Header browser:'), 0)
        self.header_browser_sizer = self._createHeaderBrowserSizer()
        header_note_boxsizer.Add(self.header_browser_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        infoSizer.Add(header_note_boxsizer, 1, wx.EXPAND | wx.ALL, 5)
 
        self.SetSizer(infoSizer)
        
        self.header_choice_key = None
        self.header_choice_hdr = None
        self.selectedItem = None
        self.sasm = None
        self.num_of_file_hdr_keys = 0
        self.num_of_imghdr_keys = 0
        
        self._disableAllControls()
    def _disableAllControls(self):
        for each in self.GetChildren():
            each.Enable(False)

    def _enableAllControls(self):
        for each in self.GetChildren():
            each.Enable(True)
        
    def _createHeaderBrowserSizer(self):
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.header_choice = wx.Choice(self, -1)
        self.header_txt = wx.TextCtrl(self, -1, '')
        
        self.header_choice.Bind(wx.EVT_CHOICE, self._onHeaderBrowserChoice)
        
        sizer.Add(self.header_choice, .5, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(self.header_txt, 1, wx.EXPAND)
        
        return sizer
    
    def _createAnalysisInfoSizer(self):
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.name_label = wx.StaticText(self, -1, 'Name:')
        self.name_txt = wx.StaticText(self, -1, 'None')
    
        name_sizer.Add(self.name_label, 0, wx.RIGHT, 10)
        name_sizer.Add(self.name_txt, 1, wx.EXPAND)
        
        analysis_sizer = wx.BoxSizer()
        for each in self.analysis_data:
            label = each[0]
            id = each[2]
            value = 'N/A'
            
            label_txt = wx.StaticText(self, -1, label)
            value_txt = wx.TextCtrl(self, id, value, size = (60, -1))
            
            siz = wx.BoxSizer()
            siz.Add(label_txt, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 3)
            siz.Add(value_txt, 1, wx.EXPAND)
            
            analysis_sizer.Add(siz, 1, wx.RIGHT | wx.EXPAND, 10)
            
        ## add conc ctrl:
        label_txt = wx.StaticText(self, -1, self.conc_data[0])
        self.conc_txt = wx.TextCtrl(self, self.conc_data[2], 'N/A', size = (60, -1))
        self.conc_txt.Bind(wx.EVT_KILL_FOCUS, self._onNoteTextKillFocus)
        siz = wx.BoxSizer()
        siz.Add(label_txt, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 3)
        siz.Add(self.conc_txt, 1, wx.EXPAND)    
        analysis_sizer.Add(siz, 1, wx.RIGHT | wx.EXPAND, 10)
            
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)
        sizer.Add(analysis_sizer, 1, wx.EXPAND | wx.RIGHT, 5)
        
        return sizer
    
    def _createNoteSizer(self):
        sizer = wx.BoxSizer()
                
        self.noteTextBox = wx.TextCtrl(self, -1, '')
        self.noteTextBox.SetBackgroundColour('WHITE')
        self.noteTextBox.SetForegroundColour('BLACK')
        
        #length, height = self.noteTextBox.GetTextExtent('TEST')
        #self.noteTextBox.SetMaxSize((-1,30))
        #self.noteTextBox.SetSize((-1, 2*height))
        
        self.noteTextBox.Bind(wx.EVT_KILL_FOCUS, self._onNoteTextKillFocus)
        
        sizer.Add(self.noteTextBox, 1, wx.EXPAND)
        
        return sizer
    
    def _onNoteTextKillFocus(self, event):
        
        note_txt = self.noteTextBox.GetValue()
        
        try:        
            self.sasm.setParameter('Notes', note_txt)
        except AttributeError:
            pass
    
        try:
            conc = self.conc_txt.GetValue().replace(',','.')
            if self.sasm != None and conc != 'N/A':
            
                float(conc)
                self.sasm.setParameter('Conc', float(conc))
        
            
        except Exception, e:
            print e
            print 'info error, Conc'
    
    
        if self.sasm != None and self.selectedItem != None:
            try:
                self.selectedItem.updateInfoTip(self.sasm.getParameter('analysis'))
            except Exception, e:
                pass
        
    def _onHeaderBrowserChoice(self, event):
        
        key = self.header_choice.GetStringSelection()
        sel_idx = self.header_choice.GetSelection()
        
        if self.sasm == None or key == 'No header info':
            return
        
        self.header_choice_key = key
        
        if sel_idx < (self.num_of_file_hdr_keys):
            self.header_choice_hdr = 'counters'
        else:
            self.header_choice_hdr = 'imageHeader'
        
        img_hdr = self.sasm.getParameter('imageHeader')
        file_hdr = self.sasm.getParameter('counters')
        
        if self.header_choice_hdr == 'imageHeader' and img_hdr.has_key(key):
            self.header_txt.SetValue(str(img_hdr[key]))
        if self.header_choice_hdr == 'counters' and file_hdr.has_key(key):
            self.header_txt.SetValue(str(file_hdr[key]))
            
        if sel_idx != wx.NOT_FOUND:
            self.selectedItem.info_settings['hdr_choice'] = sel_idx
        else:
            self.selectedItem.info_settings['hdr_choice'] = 0
    
    def clearInfo(self):
        
        self._disableAllControls()
        
        if self.sasm != None and self.selectedItem != None:
            try:
                self.selectedItem.updateInfoTip(self.sasm.getParameter('analysis'))
            except Exception, e:
                pass
        
        try:
            note_txt = self.noteTextBox.GetValue()
            self.sasm.setParameter('Notes', note_txt)
        
            conc = self.conc_txt.GetValue().replace(',','.')
            
            try:
                if conc != 'N/A' and conc != 'N\A' and self.sasm != None:
                    float(conc)
                    self.sasm.setParameter('Conc', float(conc))
            except Exception, e:
                print e
                print 'info error, Conc'
            
        except AttributeError:
            pass
        
        self.name_txt.SetLabel('')
        
        for each in self.analysis_data:
            id = each[2]
            
            label = wx.FindWindowById(id)
            label.SetValue('N/A')
            
        self.header_txt.SetValue('')
        self.header_choice.SetItems([''])
        self.noteTextBox.SetValue('')
        self.conc_txt.SetValue('N/A')
        self.num_of_file_hdr_keys = 0
        self.num_of_imghdr_keys = 0
        
        self.sasm = None
        self.selectedItem = None
        
        self.analysis_info_sizer.Layout()
        self.Refresh()   

    def updateInfoFromItem(self, item):
        self.clearInfo()
        
        self.sasm = item.getSASM()
        self.selectedItem = item
        
        filename = self.sasm.getParameter('filename')
        self.name_txt.SetLabel(str(filename))
        
        if self.sasm.getParameter('analysis').has_key('guinier'):
            analysis_dict = self.sasm.getParameter('analysis')
            guinier = analysis_dict['guinier']
        
            if guinier.has_key('Rg') and guinier.has_key('I0'):
                rg = guinier['Rg']
                i_zero = guinier['I0']
        
                for each in self.analysis_data:
                    key = each[1]
                    id = each[2]
                    
                    txt = wx.FindWindowById(id)
                    
                    if guinier.has_key(key):
                        txt.SetValue(str(guinier[key]))       
                        
        if self.sasm.getAllParameters().has_key('Conc'):
            conc_ctrl = self.conc_txt
            conc_ctrl.SetValue(str(self.sasm.getParameter('Conc')))
        
        all_choices = []
        file_hdr = {}
        img_hdr = {}
        if self.sasm.getAllParameters().has_key('counters'):
            file_hdr = self.sasm.getParameter('counters')            
            all_filehdr_keys = file_hdr.keys()
            all_choices.extend(all_filehdr_keys)
            self.num_of_file_hdr_keys = len(all_filehdr_keys)
        
        if self.sasm.getAllParameters().has_key('imageHeader'):
            img_hdr = self.sasm.getParameter('imageHeader')
            all_imghdr_keys = img_hdr.keys()
            all_choices.extend(all_imghdr_keys)
            self.num_of_imghdr_keys = len(all_imghdr_keys)
            
            
        if len(all_choices) > 0:    
            self.header_choice.SetItems(all_choices)
            
            try:
                if self.header_choice_key != None:
                    if self.header_choice_hdr == 'imageHeader' and img_hdr.has_key(self.header_choice_key):
                        idx = all_imghdr_keys.index(self.header_choice_key)
                        idx = idx + self.num_of_file_hdr_keys
                        self.header_choice.SetSelection(idx)
                        
                    elif self.header_choice_hdr == 'counters' and file_hdr.has_key(self.header_choice_key):
                        idx = all_filehdr_keys.index(self.header_choice_key)
                        self.header_choice.SetSelection(idx)
                    else:
                        self.header_choice.SetSelection(item.info_settings['hdr_choice'])
                else:
                    self.header_choice.SetSelection(item.info_settings['hdr_choice'])
                    
                self._onHeaderBrowserChoice(None)
            except Exception, e:
                self.header_choice.SetSelection(0)
                print e
                print 'InfoPanel error'
        
        else:
            self.header_choice.SetItems(['No header info'])
            self.header_choice.Select(0)
        
        if self.sasm.getParameter('Notes') != None:
            self.noteTextBox.SetValue(self.sasm.getParameter('Notes'))
        
        self.analysis_info_sizer.Layout()
        self.header_browser_sizer.Layout()
        
        self._enableAllControls()
        self.Refresh()   
    
    def WriteText(self, text):    
        self.infoTextBox.AppendText(text)
        

class SaveAnalysisInfoPanel(wx.Panel):
    
    def __init__(self, parent, item_list = None, include_data = None):
        wx.Panel.__init__(self, parent, name = 'SaveAnalysisInfoPanel')
        
        self.SetMinSize((600,400))
        
        self.variable_data = {}
        
        self.item_list = item_list
        self.included_data = {}
        sizer = wx.BoxSizer()
        
        self.include_listctrl = SaveAnalysisListCtrl(self, -1, style = wx.LC_REPORT | wx.LC_NO_HEADER)
        self.variable_listctrl = SaveAnalysisListCtrl(self, -1, style = wx.LC_REPORT | wx.LC_NO_HEADER)
        
        include_sizer = wx.BoxSizer(wx.VERTICAL)
        include_sizer.Add(wx.StaticText(self, -1, 'Include list:'), 0)
        include_sizer.Add(self.include_listctrl, 1, wx.EXPAND)
        
        variable_sizer = wx.BoxSizer(wx.VERTICAL)
        variable_sizer.Add(wx.StaticText(self, -1, 'Variable list:'), 0)
        variable_sizer.Add(self.variable_listctrl, 1, wx.EXPAND)
        
        self.include_button = wx.Button(self, -1, '->')
        self.exclude_button = wx.Button(self, -1, '<-')
        
        self.include_button.Bind(wx.EVT_BUTTON, self._onIncludeButton)
        self.exclude_button.Bind(wx.EVT_BUTTON, self._onExcludeButton)
        
        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer.Add(self.include_button, 0)
        self.button_sizer.Add(self.exclude_button, 0)
        
        sizer.Add(variable_sizer, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.button_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        sizer.Add(include_sizer, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(sizer)
        
        self.variable_listctrl.InsertColumn(0, 'name')
        width, height = self.variable_listctrl.GetSize()
        
        self.variable_listctrl.SetColumnWidth(0, 300)
        
        self._addGeneralVariables()
        self._addGuinierVariables()
        self._addFileHdrVariables()
        self._addImageHdrVariables()
    
        self._updateIncludeList(include_data)
        
    def _onIncludeButton(self, event):
        selected_items = self.variable_listctrl.getSelectedItems()
        
        all_items = []
        
        for each_item in selected_items:
            data = copy.copy(self.variable_data[each_item])
            
            if data[1] == None:
                continue
            
            txt = self.variable_listctrl.GetItem(each_item).GetText()
            all_items.append(data)
  
            idx = self.include_listctrl.GetItemCount()
            self.include_listctrl.InsertStringItem(idx, txt)
                
            self.included_data[idx] = data   
        
    def _onExcludeButton(self, event):
        selected_items = self.include_listctrl.getSelectedItems()
        
        if len(selected_items) > 0:
            each = selected_items[0]
        else:
            return
        
        self.include_listctrl.DeleteItem(each)
        del self.included_data[each]
        
        self._updateIncludedData()
            
    def _updateIncludedData(self):
        
        idx = 0
        new_dict = {}
        for each in sorted(self.included_data.keys()):
            
            new_dict[idx] = self.included_data[each]
            idx = idx+1
            
        self.included_data = new_dict
               
    def _getAllImageHdrKeys(self):
        all_imghdr_keys = []
        
        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()
            
            if each_sasm.getAllParameters().has_key('imageHeader'):
               img_hdr = each_sasm.getParameter('imageHeader')
               keys = img_hdr.keys()
               all_keys.extend(keys)
               
        all_imghdr_keys.extend(set(all_keys))
        
        return all_imghdr_keys
            
    def _getAllFileHdrKeys(self):
        all_filehdr_keys = []
        
        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()
            
            if each_sasm.getAllParameters().has_key('counters'):
               img_hdr = each_sasm.getParameter('counters')
               keys = img_hdr.keys()
               all_keys.extend(keys)
               
        all_filehdr_keys.extend(set(all_keys))
        
        return all_filehdr_keys
    
    def _getAllGuinierKeys(self):
        all_guinier_keys = []
        
        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()
            
            if each_sasm.getParameter('analysis').has_key('guinier'):
               analysis = each_sasm.getParameter('analysis')
               guinier = analysis['guinier']
               keys = guinier.keys()
               all_keys.extend(keys)
               
        all_guinier_keys.extend(set(all_keys))
        
        return all_guinier_keys
        
    
    def _addGeneralVariables(self):
        general_data = [('General', None), ('Concentration', 'Conc'), ('Description / Notes', 'Notes')]
        
        idx = 0
        for each in general_data: 
            self.variable_listctrl.InsertStringItem(idx, each[0])
            self.variable_data[idx] = ['general' , each[1], each[0]]
            
            idx = idx + 1
            
        self.variable_listctrl.SetItemBackgroundColour(0, 'GRAY')
    
    def _addGuinierVariables(self):
        keys = self._getAllGuinierKeys()
        
        if len(keys) == 0:
            return
        
        idx = self.variable_listctrl.GetItemCount()
                
        self.variable_listctrl.InsertStringItem(idx, 'Guinier Analysis')
        self.variable_data[idx] = ['guinier', None]
        
        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys: 
            self.variable_listctrl.InsertStringItem(idx, each)
            self.variable_data[idx] = ['guinier', each, each]         
            idx = idx + 1

    
    def _addFileHdrVariables(self):
        keys = self._getAllFileHdrKeys()
        
        if len(keys) == 0:
            return
        
        idx = self.variable_listctrl.GetItemCount()
        
        self.variable_listctrl.InsertStringItem(idx, 'Header File')
        self.variable_data[idx] = ['Header File', None]
        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys: 
            self.variable_listctrl.InsertStringItem(idx, each)
            self.variable_data[idx] = ['counters', each, each]                   
            idx = idx + 1
    
    def _addImageHdrVariables(self):
        keys = self._getAllImageHdrKeys()
        
        if len(keys) == 0:
            return
        
        idx = self.variable_listctrl.GetItemCount()
        
        self.variable_listctrl.InsertStringItem(idx, 'Image Header')
        self.variable_data[idx] = ['Image Header', None]
        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys: 
            self.variable_listctrl.InsertStringItem(idx, each)
            self.variable_data[idx] = ['imageHeader', each, each]        
            idx = idx + 1
            
    def getIncludeData(self):
        return self.included_data
    
    def _updateIncludeList(self, include_data):
        
        if include_data == None:
            return
        
        for each in sorted(include_data.keys()):
            idx = self.include_listctrl.GetItemCount()
            self.include_listctrl.InsertStringItem(idx, include_data[each][2])
                
            self.included_data[idx] = include_data[each]

        
#----- **** Dialogs ****

class SaveDialog(wx.Dialog):
    def __init__(self, parent, id, title, text):
        wx.Dialog.__init__(self, parent, id, title)

        sizer =  wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, -1, text), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)
        
        button_sizer = wx.BoxSizer()
      
        button_sizer.Add(wx.Button(self, wx.ID_SAVE, 'Save'), 0, wx.RIGHT, 5)
        button_sizer.Add(wx.Button(self, wx.ID_DELETE, 'Discard'), 0, wx.RIGHT, 5)
        button_sizer.Add(wx.Button(self, wx.ID_CANCEL, 'Cancel'), 0)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)
        
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self._onDiscard, id=wx.ID_DELETE)
        self.Bind(wx.EVT_BUTTON, self._onSave, id=wx.ID_SAVE)

        self.SetSizer(sizer)
        self.Fit()
        
    def _onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
    
    def _onDiscard(self, event):
        self.EndModal(wx.ID_DELETE)
    
    def _onSave(self, event):
        self.EndModal(wx.ID_SAVE)
        
class SaveAnalysisListCtrl(wx.ListCtrl):
    
    def __init__(self, parent, id, *args, **kwargs):
        
        wx.ListCtrl.__init__(self, parent, id, *args, **kwargs)
        self.populateList()
        
    def populateList(self):
        self.InsertColumn(0, 'Name')
        self.SetColumnWidth(0, 300)
        
    def add(self, expr):
        no_of_items = self.GetItemCount()
        self.SetStringItem(no_of_items, 0, expr)
        
    def moveItemUp(self, idx):
        if idx > 0:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertStringItem(idx-1, data[0])
            self.SetStringItem(idx-1, 1, data[1])
            self.Select(idx-1, True)
            
    def moveItemDown(self, idx):
        if idx < self.GetItemCount()-1:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertStringItem(idx+1, data[0])
            self.SetStringItem(idx+1, 1, data[1])
            self.Select(idx+1, True)
        
    def getItemData(self, idx):
        data1 = self.GetItemText(idx)
        item = self.GetItem(idx, 1)
        data2 = item.GetText()
        
        return [data1, data2]
        
    def getSelectedItems(self):
        """    Gets the selected items for the list control.
          Selection is returned as a list of selected indices,
          low to high.
        """
        selection = []
        index = self.GetFirstSelected()
        
        if index == -1:
            return []
        
        selection.append(index)
        
        while len(selection) != self.GetSelectedItemCount():
            index = self.GetNextSelected(index)
            selection.append(index)

        return selection
    
    def getAllItems(self):
        ''' returns a list with all items and operator '''
        all_items = []
        for i in range(0, self.GetItemCount()):
             all_items.append(self.getItemData(i))
        
        return all_items
    
    def GetValue(self):
        ''' Creating a function to mimic other normal control widgets,
        this makes it easier to update and save settings for this
        control.'''
        
        return self.getAllItems()
    
    def SetValue(self, value_list):
        
        if value_list == None:
            return
        
        for each in value_list:
            op = each[0]
            expr = each[1]    
            self.add(op, expr)

class SaveAnalysisInfoDialog(wx.Dialog):
    
    def __init__(self, parent, raw_settings, item_list = None, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, 'Select variables to include in the comma separated file.', *args, **kwargs)
        
        self.raw_settings = raw_settings
        
        include_data = self.raw_settings.get('csvIncludeData')
        
        self.item_list = item_list    
        self.panel = SaveAnalysisInfoPanel(self, item_list = item_list, include_data = include_data)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.sizer.Add(self.panel,0, wx.ALL, 10)
        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.sizer.Add(buttonsizer,0, wx.BOTTOM | wx.RIGHT | wx.LEFT | wx.ALIGN_RIGHT, 10)
        
        self.Bind(wx.EVT_BUTTON, self._onOk, id = wx.ID_OK)
        
        self.SetSizer(self.sizer)
        self.Fit()
        
    def _onOk(self, event):
        include_data = self.panel.getIncludeData()
        
        if len(include_data) > 0:
            
            save_path = self._showSaveDialog()
            if save_path == None:
                return
            
            data = [self.item_list, include_data, save_path]
            mainworker_cmd_queue.put(['save_analysis_info', data])
            #make the workerthread make a csv file.
        
        self.raw_settings.set('csvIncludeData', include_data)
        self.EndModal(wx.ID_OK)
        
    
    def _showSaveDialog(self):
            
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        save_path = dirctrl_panel.getDirLabel()
        
        filters = 'Comma Separated Files (*.csv)|*.csv'
            
        dialog = wx.FileDialog( None, style = wx.SAVE | wx.OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path) 
            
        if dialog.ShowModal() == wx.ID_OK:               
            save_path = dialog.GetPath()
            return save_path
        else:
             return None

class TestDialog(wx.Dialog):
    
    def __init__(self, parent, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, *args, **kwargs)
        
        #self.panel = CenteringPanel(self, -1)
    
        self.panel = InformationPanel(self)
        
        self.sizer = wx.BoxSizer()
        
        self.sizer.Add(self.panel,0, wx.ALL, 10)
        self.SetSizer(self.sizer)
        self.Fit()
   
class HdrDataDialog(wx.Dialog):
    
    def __init__(self, parent, sasm = None, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, 'Header Data Display', *args, **kwargs)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.grid_changed = False
        self.sasm = sasm
        
        #For testing
        if self.sasm == None:
            data_len = 100
            filename_label = wx.StaticText(self, -1, 'Filename :')
        else:
            data_len = len(sasm.getBinnedI())
            filename_label = wx.StaticText(self, -1, 'Filename : ' + sasm.getParameter('filename'))
        
        self.data_grid = gridlib.Grid(self)
        self.data_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE) 
        
        data_len = self._getNumOfHeaderValues()
                
        self.data_grid.CreateGrid(data_len, 2)
        self.data_grid.SetColLabelValue(0, 'Key')
        self.data_grid.SetColLabelValue(1, 'Value')
        self.data_grid.SetMinSize((400,400))
        
        self.sizer.Add(filename_label, 0, wx.TOP | wx.LEFT, 10)
        self.sizer.Add(self.data_grid, 1, wx.ALL, 10)
        self.sizer.Add(self._CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
        
        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        self.Bind(gridlib.EVT_GRID_CELL_CHANGE, self._onChange)
        self.Bind(gridlib.EVT_GRID_EDITOR_SHOWN, self._onEditCell)
        
        self.SetSizer(self.sizer)
        
        if self.sasm != None:
            self._insertData()
        
        self.data_grid.AutoSizeColumns()
        self.Fit()
        
        self.CenterOnParent()
    
    def _onEditCell(self, event):
        col = self.data_grid.GridCursorCol
        row = self.data_grid.GridCursorRow
        
        self.saved_value = self.data_grid.GetCellValue(row, col)
        
        event.Skip()
    
    def _onChange(self, event):
        
        try:
            col = self.data_grid.GridCursorCol
            row = self.data_grid.GridCursorRow
        
            value = self.data_grid.GetCellValue(row, col)
            float(value)
            self.grid_changed = True
        except ValueError:
            wx.MessageBox('Illegal value entered', 'Invalid Entry', style=ICON_ERROR)
            self.data_grid.SetCellValue(row, col, self.saved_value)
            
    def _getNumOfHeaderValues(self):
        
        all_keys = []
        
        if self.sasm.getAllParameters().has_key('counters'):
            file_hdr = self.sasm.getParameter('counters')
            keys = file_hdr.keys()
            all_keys.extend(keys)
            
        if self.sasm.getAllParameters().has_key('imageHeader'):
            img_hdr = self.sasm.getParameter('imageHeader')
            keys = img_hdr.keys()    
            all_keys.extend(keys)
            
        return len(all_keys)
        
    def _insertData(self):
          
        imghdr_data_len = 0
        filehdr_data_len = 0

        if self.sasm.getAllParameters().has_key('counters'):
            file_hdr = self.sasm.getParameter('counters')
            keys = file_hdr.keys()
        
            if len(keys) > 0:
                filehdr_data_len = len(keys)
                
                for i in range(0, filehdr_data_len):
                    self.data_grid.SetCellValue(i, 0, str(keys[i]))
                    self.data_grid.SetCellValue(i, 1, str(file_hdr[keys[i]]))        
        
        if self.sasm.getAllParameters().has_key('imageHeader'):
            img_hdr = self.sasm.getParameter('imageHeader')
            keys = img_hdr.keys()
        
            if len(keys) > 0:
                imghdr_data_len = len(keys)
                
                for i in range(filehdr_data_len, filehdr_data_len + imghdr_data_len):
                    self.data_grid.SetCellValue(i, 0, str(keys[i-filehdr_data_len]))
                    self.data_grid.SetCellValue(i, 1, str(img_hdr[keys[i-filehdr_data_len]]))

    
    def _writeData(self):
        data_len = len(self.sasm.getBinnedI())
        
        new_I = []
        new_Q = []
        new_Err = []
        
        for i in range(0, data_len):
            new_Q.append(float(self.data_grid.GetCellValue(i, 0)))
            new_I.append(float(self.data_grid.GetCellValue(i, 1)))
            new_Err.append(float(self.data_grid.GetCellValue(i, 2)))   
            
        self.sasm.setBinnedI(numpy.array(new_I))
        self.sasm.setBinnedQ(numpy.array(new_Q))
        self.sasm.setBinnedErr(numpy.array(new_Err))
        
        self.sasm._update()
        
    def _onOk(self, event):
#        if self.grid_changed:
#            self._writeData()
            
        self.EndModal(wx.ID_OK)
    def _onCancel(self, event):
        self.EndModal(wx.ID_CANCEL) 
        
class DataDialog(wx.Dialog):
    
    def __init__(self, parent, sasm = None, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, 'Data Display', *args, **kwargs)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.grid_changed = False
        self.sasm = sasm
        #For testing
        if self.sasm == None:
            data_len = 100
            filename_label = wx.StaticText(self, -1, 'Filename :')
        else:
            data_len = len(sasm.getBinnedI())
            filename_label = wx.StaticText(self, -1, 'Filename : ' + sasm.getParameter('filename'))
        
        self.data_grid = gridlib.Grid(self)
        self.data_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE) 
        
        self.data_grid.CreateGrid(data_len, 3)
        self.data_grid.SetColLabelValue(0, 'q')
        self.data_grid.SetColLabelValue(1, 'i')
        self.data_grid.SetColLabelValue(2, 'err')
        self.data_grid.SetMinSize((600,400))
        
        self.sizer.Add(filename_label, 0, wx.TOP | wx.LEFT, 10)
        self.sizer.Add(self.data_grid, 1, wx.ALL, 10)
        self.sizer.Add(self._CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
        
        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        self.Bind(gridlib.EVT_GRID_CELL_CHANGE, self._onChange)
        self.Bind(gridlib.EVT_GRID_EDITOR_SHOWN, self._onEditCell)
        
        self.SetSizer(self.sizer)
        
        if self.sasm != None:
            self._insertData()
        
        
        self.data_grid.AutoSizeColumns()
        self.Fit()
        
#        try:
#            file_list_ctrl = wx.FindWindowByName('PlotPanel')
#            pos = file_list_ctrl.GetScreenPosition()
#            self.MoveXY(pos[0], pos[1])
#        except:
#            pass

        self.CenterOnParent()
    
    def _onEditCell(self, event):
        col = self.data_grid.GridCursorCol
        row = self.data_grid.GridCursorRow
        
        self.saved_value = self.data_grid.GetCellValue(row, col)
        
        event.Skip()
    
    def _onChange(self, event):
        
        try:
            col = self.data_grid.GridCursorCol
            row = self.data_grid.GridCursorRow
        
            value = self.data_grid.GetCellValue(row, col)
            float(value)
            self.grid_changed = True
        except ValueError:
            wx.MessageBox('Illegal value entered', 'Invalid Entry', style=ICON_ERROR)
            self.data_grid.SetCellValue(row, col, self.saved_value)
        
    def _insertData(self):
        data_len = len(self.sasm.getBinnedI())
        
        I = self.sasm.getBinnedI()
        Q = self.sasm.getBinnedQ()
        Err = self.sasm.getBinnedErr()
        
        for i in range(0, data_len):
            self.data_grid.SetCellValue(i, 0, str(Q[i]))
            self.data_grid.SetCellValue(i, 1, str(I[i]))
            self.data_grid.SetCellValue(i, 2, str(Err[i]))
    
    def _writeData(self):
        data_len = len(self.sasm.getBinnedI())
        
        new_I = []
        new_Q = []
        new_Err = []
        
        for i in range(0, data_len):
            new_Q.append(float(self.data_grid.GetCellValue(i, 0)))
            new_I.append(float(self.data_grid.GetCellValue(i, 1)))
            new_Err.append(float(self.data_grid.GetCellValue(i, 2)))   
            
        self.sasm.setBinnedI(numpy.array(new_I))
        self.sasm.setBinnedQ(numpy.array(new_Q))
        self.sasm.setBinnedErr(numpy.array(new_Err))
        
        self.sasm._update()
        
    def _onOk(self, event):
        if self.grid_changed:
            self._writeData()
            
        self.EndModal(wx.ID_OK)
    def _onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
    

class TestDialog2(wx.Dialog):
    
    def __init__(self, parent, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, *args, **kwargs)
        
        self.panel = MaskingPanel(self, -1)
        
        self.sizer = wx.BoxSizer()
        
        self.sizer.Add(self.panel,0, wx.ALL, 10)
        self.SetSizer(self.sizer)
        self.Fit()
        
class SyncDialog(wx.Dialog):
    
    def __init__(self, parent, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, 'Synchronize', *args, **kwargs)
            
        self.chkbox_list = [('q min', 'qmin', wx.NewId()),
                       ('q max', 'qmax', wx.NewId()),
                       ('n min', 'nmin', wx.NewId()),
                       ('n max', 'nmax', wx.NewId()),
                       ('scale', 'scale', wx.NewId()),
                       ('offset', 'offset', wx.NewId()),
                       ('line style', 'linestyle', wx.NewId()),
                       ('line width', 'linewidth', wx.NewId()),
                       ('line marker', 'linemarker', wx.NewId())]
        
        self.selected_boxes = []
        
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        
        sync_box = wx.StaticBox(self, -1, 'Synchronize Parameters')
        sync_boxsizer = wx.StaticBoxSizer(sync_box)
        sync_boxsizer.SetOrientation(wx.VERTICAL)
        
        for each in self.chkbox_list:
            label, key, id = each
            chkbox = wx.CheckBox(self, id, label, name = key)
            chkbox.Bind(wx.EVT_CHECKBOX, self._onCheckBox)
            sync_boxsizer.Add(chkbox, 0, wx.TOP | wx.LEFT, 5)
            
        sync_boxsizer.Add((5,5),0)

        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkClicked, id=wx.ID_OK )
        
        top_sizer.Add(sync_boxsizer, 1, wx.EXPAND | wx.ALL, 10)
        top_sizer.Add(button_sizer, 0, wx.ALL, 10)
            
        self.SetSizer(top_sizer)
        
        self.Fit()
        self.CenterOnParent()
    
    def _onOkClicked(self, event):
        manipulation_panel = wx.FindWindowByName('ManipulationPanel')
        
        wx.CallAfter(manipulation_panel.synchronizeSelectedItems, self.selected_boxes)
        
        self.EndModal(wx.ID_OK)
    
    def _onCheckBox(self, event):
        
        chkbox = event.GetEventObject()
        
        if chkbox.IsChecked():
            self.selected_boxes.append(chkbox.GetName())
        else:
            self.selected_boxes.remove(chkbox.GetName())
         
class QuickReduceDialog(wx.Dialog):
    
    def __init__(self, parent, path, selected_files, *args, **kwargs):
        
        wx.Dialog.__init__(self,parent, -1, 'Quick Reduce Settings', *args, **kwargs)
        
        self._path = path
        filecount_label = wx.StaticText(self, -1, '# of files selected : ' + str(len(selected_files)))
        
        savedir_label = wx.StaticText(self, -1, 'Save Directory :')
        format_label = wx.StaticText(self, -1, 'Format :')
        
        savedir_sizer = wx.BoxSizer()
        self.save_textctrl = wx.TextCtrl(self, -1, path, size = (400, -1))
        
        folder_bmp = wx.ArtProvider.GetBitmap(wx.ART_FOLDER,  wx.ART_MENU)
        save_search_button = wx.BitmapButton(self, -1, folder_bmp)
        save_search_button.Bind(wx.EVT_BUTTON, self._onSearchButton)
        
        savedir_sizer.Add(self.save_textctrl, 1, wx.RIGHT | wx.EXPAND, 2)
        savedir_sizer.Add(save_search_button, 0)
        
        format_choice = wx.Choice(self, -1, choices = ['.rad (RAW)', '.dat (ATSAS)'])
        format_choice.Select(0)
        
        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkClicked, id=wx.ID_OK )
        
        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(filecount_label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        final_sizer.Add(savedir_label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        final_sizer.Add(savedir_sizer, 0, wx.LEFT | wx.RIGHT, 10)
        final_sizer.Add(format_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        final_sizer.Add(format_choice, 0, wx.LEFT | wx.RIGHT, 10)
        final_sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP, 10)
        final_sizer.Add(button_sizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10)
        
        self.SetSizer(final_sizer)
        
        self.Fit()
        self.CenterOnParent()
    
    def _onOkClicked(self, event):
        
        self._path = self.save_textctrl.GetValue()
        if not os.path.exists(self._path):
            wx.MessageBox('Path does not exist or contains illegal characters.', 'Path not valid', style = wx.ICON_ERROR)
            return
        else:
            self.EndModal(wx.ID_OK)
        
    def _onSearchButton(self, event):

        dirdlg = wx.DirDialog(self, "Please select directory:", str(self._path))
            
        if dirdlg.ShowModal() == wx.ID_OK:
            self._path = dirdlg.GetPath()
            self.save_textctrl.SetValue(str(self._path))
            
    def getPath(self):
        return self._path
        

class FilenameChangeDialog(wx.Dialog):
    
    def __init__(self, parent, filename, dlgtype = None, *args, **kwargs):
        
        if dlgtype == 'Folder':
            hdr = 'Folder Name'
        else:
            hdr = 'Change Name'
            
        wx.Dialog.__init__(self,parent, -1, hdr, *args, **kwargs)
        
        self.ok_button = wx.Button(self, -1, 'OK')
        self.cancel_button = wx.Button(self, -1, 'Cancel')
        self._filename = None
        
        self.ok_button.Bind(wx.EVT_BUTTON, self._onOKButton)
        self.cancel_button.Bind(wx.EVT_BUTTON, self._onCancelButton)
        
        button_sizer = wx.BoxSizer()
        button_sizer.Add(self.ok_button,0, wx.RIGHT, 5)
        button_sizer.Add(self.cancel_button,0)        
        
        label = wx.StaticText(self, -1, 'Name :')
        self.ctrl = wx.TextCtrl(self, -1, '', size = (200, -1))
        self.ctrl.SetValue(str(filename))
        
        filename_sizer = wx.BoxSizer()
        filename_sizer.Add(label,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        filename_sizer.Add(self.ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        
        final_sizer = wx.BoxSizer(wx.VERTICAL)
        
        final_sizer.Add(filename_sizer, 0, wx.ALL, 15)
        final_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        self.SetSizer(final_sizer)
        self.Fit()
        self.CenterOnParent()
    
    def _onOKButton(self, event):
        self._filename = self.ctrl.GetValue()
        self.EndModal(wx.ID_OK)
        
    def _onCancelButton(self, event):
        self.EndModal(wx.ID_CANCEL)
        
    def getFilename(self):
        return self._filename
    
        

class LegendLabelChangeDialog(wx.Dialog):
    
    def __init__(self, parent, legend_label, *args, **kwargs):
        
        wx.Dialog.__init__(self,parent, -1, 'Change Legend Label', *args, **kwargs)
        
        self.ok_button = wx.Button(self, -1, 'OK')
        self.cancel_button = wx.Button(self, -1, 'Cancel')
        self._legend_label = ''
        
        self.ok_button.Bind(wx.EVT_BUTTON, self._onOKButton)
        self.cancel_button.Bind(wx.EVT_BUTTON, self._onCancelButton)
        
        button_sizer = wx.BoxSizer()
        button_sizer.Add(self.ok_button,0, wx.RIGHT, 5)
        button_sizer.Add(self.cancel_button,0)        
        
        label_txt = 'Label :'
        label = wx.StaticText(self, -1,label_txt)
        self.ctrl = wx.TextCtrl(self, -1, '', size = (200, -1))
        self.ctrl.SetValue(str(legend_label))
        
        filename_sizer = wx.BoxSizer()
        filename_sizer.Add(label,0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        filename_sizer.Add(self.ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        
        final_sizer = wx.BoxSizer(wx.VERTICAL)
        
        final_sizer.Add(filename_sizer, 0, wx.ALL, 15)
        final_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        self.SetSizer(final_sizer)
        self.Fit()
        self.CenterOnParent()
    
    def _onOKButton(self, event):
        self._legend_label = self.ctrl.GetValue()
        self.EndModal(wx.ID_OK)
        
    def _onCancelButton(self, event):
        self.EndModal(wx.ID_CANCEL)
        
    def getLegendLabel(self):
        return self._legend_label

class RebinDialog(wx.Dialog):
    
    def __init__(self, parent, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, *args, **kwargs)
        
        top_sizer = wx.BoxSizer()
        
        choices = ['2','3','4','5','6','7','8','9','10']
        text = wx.StaticText(self, -1, 'Select bin reduction factor :')
        choice = wx.Choice(self, -1, choices = choices)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        sizer.Add(text, 1)
        sizer.Add(choice, 0)
        
        top_sizer.Add(sizer, 1, wx.ALL, 10)
        
        self.SetSizer(top_sizer)
        self.Fit()
     

class LinePropertyDialog(wx.Dialog):
    
    def __init__(self, parent, line, *args, **kwargs):
        
        if line == None:
            wx.MessageBox('Unable to change line properties.\nNo plot has been made for this item.', 'No plot')
            return
            
        
        wx.Dialog.__init__(self, parent, -1, *args, **kwargs)
        
        self.linewidth_combo_choices = ['1.0', '2.0', '3.0', '4.0', '5.0']
        self.linestyle_list_choices = ['None', '-', '--', '-.', ':']
        self.linemarker_list_choices = ['None', '+', '*', ',','.','1','2','3','4','<', '>', 'D', 'H', '^','_','d','h','o','p','s','v','x','|']
        
        self.line = line
        
        self._linestyle = line.get_linestyle()
        self._linemarker = line.get_marker()
        self._linewidth = line.get_linewidth()
        
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.line.get_color())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self._linecolour = color
           
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer = self._createControls()
        buttonsizer = self._createButtons()
        top_sizer.Add(sizer, 0, wx.ALL, 10)
        top_sizer.Add(wx.StaticLine(self, -1), wx.EXPAND |wx.TOP | wx.BOTTOM, 3)
        top_sizer.Add(buttonsizer, 0, wx.CENTER | wx.BOTTOM, 10)
        
        self.SetSizer(top_sizer)
        self.Fit()
        self.CenterOnParent()

    def _createControls(self):
        
        linewidth_label = wx.StaticText(self, -1, 'Linewidth :')
        linestyle_label = wx.StaticText(self, -1, 'Linestyle :')
        linemarker_label = wx.StaticText(self, -1, 'Linemarker :')
        linecolour_label = wx.StaticText(self, -1, 'Linecolour :')
        
        self.linewidth_combo = wx.ComboBox(self, -1, choices = self.linewidth_combo_choices)
        self.linewidth_combo.SetValue(str(self._linewidth))
        
        self.linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
        self.linestyle_list.Select(self.linestyle_list_choices.index(str(self._linestyle)))
        
        self.linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
        self.linemarker_list.Select(self.linemarker_list_choices.index(str(self._linemarker)))
        
        self.colourchoice = colorchooser.PyColourChooser(self, -1)
        self.colourchoice.SetValue(self._linecolour)
               
        sizer = wx.FlexGridSizer(cols = 2, rows = 4, vgap = 3, hgap = 3)
        
        sizer.Add(linewidth_label, 0)
        sizer.Add(self.linewidth_combo, 0, wx.EXPAND)
        sizer.Add(linestyle_label, 0)
        sizer.Add(self.linestyle_list, 0, wx.EXPAND)
        sizer.Add(linemarker_label, 0)
        sizer.Add(self.linemarker_list, 0, wx.EXPAND)
        sizer.Add(linecolour_label, 0)
        sizer.Add(self.colourchoice, 0)
        
        return sizer 
    
    def _createButtons(self):
        sizer = wx.BoxSizer()
        
        ok_button = wx.Button(self, -1, 'OK')
        cancel_button = wx.Button(self, -1, 'Cancel')
        
        ok_button.Bind(wx.EVT_BUTTON, self._onOkButton)
        cancel_button.Bind(wx.EVT_BUTTON, self._onCancelButton)
        
        sizer.Add(cancel_button, 0, wx.RIGHT, 10)
        sizer.Add(ok_button, 0)
        
        return sizer
        
    def _onCancelButton(self, event):
        self.EndModal(wx.CANCEL)

    def _onOkButton(self, event):
        marker =  self.linemarker_list.GetStringSelection()
        width =  self.linewidth_combo.GetValue()
        style =  self.linestyle_list.GetStringSelection()
        colour =  self.colourchoice.GetValue().Get(False)
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self.line.set_marker(marker)
        self.line.set_linewidth(float(width))
        self.line.set_linestyle(style)    
        self.line.set_color(colour)
      
        self.EndModal(wx.OK)
        
#--- ** Startup app **

class MyApp(wx.App):
    
    def OnInit(self):     
        MySplash = MySplashScreen()
        MySplash.Show()
        
        return True
    
class MySplashScreen(wx.SplashScreen):
    """
        Create a splash screen widget.
    """
    
    def __init__(self, parent = None):
        
        aBitmap = wx.Image(name = os.path.join(RAWWorkDir, "resources","logo_atom.gif")).ConvertToBitmap()
        splashStyle = wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_TIMEOUT
        splashDuration = 2000 # milliseconds
        
        wx.SplashScreen.__init__(self, aBitmap, splashStyle, splashDuration, parent)
        
        self.Bind(wx.EVT_CLOSE, self.OnExit)

        wx.Yield()

    def OnExit(self, evt):
        self.Hide()
            
        frame = MainFrame('RAW 0.99.8.4b', -1)
        icon = wx.Icon(name= os.path.join(RAWWorkDir, "resources","raw.ico"), type = wx.BITMAP_TYPE_ICO)
        frame.SetIcon(icon)
        app.SetTopWindow(frame)
  
        frame.SetSize((1024,768))
        frame.CenterOnScreen()
        frame.Show(True)

        # The program will freeze without this line.
        evt.Skip()
       
if __name__ == '__main__':
    app = MyApp(0)   #MyApp(redirect = True)
    app.MainLoop()
        
