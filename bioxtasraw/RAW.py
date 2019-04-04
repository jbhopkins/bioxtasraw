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
import sys
import os
import subprocess
import time
import threading
import Queue
import cPickle
import copy
import glob
import platform
import fnmatch
import shutil
import itertools
import traceback
import scipy.constants
import multiprocessing
from collections import OrderedDict, defaultdict

import hdf5plugin #HAS TO BE FIRST
import numpy as np
import matplotlib.colors as mplcol
import pyFAI, pyFAI.calibrant#, pyFAI.peak_picker
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.listctrl as listmix
import wx.lib.buttons as wxbutton
import wx.lib.agw.supertooltip as STT
import wx.aui as aui
import wx.lib.dialogs

if wx.version().split()[0].strip()[0] == '4':
    import wx.adv
    SplashScreen = wx.adv.SplashScreen
    TaskBarIcon = wx.adv.TaskBarIcon
    AboutDialogInfo = wx.adv.AboutDialogInfo
    AboutBox = wx.adv.AboutBox
else:
    SplashScreen = wx.SplashScreen
    TaskBarIcon = wx.TaskBarIcon
    AboutDialogInfo = wx.AboutDialogInfo
    Aboutbox = wx.AboutBox


import SASFileIO
import SASM
import SASExceptions
import SASImage
import SASCalc
import SASCalib
import RAWPlot
import RAWImage
import RAWOptions
import RAWSettings
import RAWCustomCtrl
import RAWAnalysis
import BIFT
import RAWIcons
import RAWGlobals
import RAWCustomDialogs
from RAWGlobals import mainworker_cmd_queue
import SASProc

thread_wait_event = threading.Event()
question_return_queue = Queue.Queue()


class MainFrame(wx.Frame):

    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title, name = 'MainFrame')

        self.MenuIDs = {'exit'                  : self.NewControlId(),
                        'advancedOptions'       : self.NewControlId(),
                        'loadSettings'          : self.NewControlId(),
                        'saveSettings'          : self.NewControlId(),
                        'centering'             : self.NewControlId(),
                        'masking'               : self.NewControlId(),
                        'goOnline'              : self.NewControlId(),
                        'goOffline'             : self.NewControlId(),
                        'changeOnline'          : self.NewControlId(),
                        'plot1tynormal'         : self.NewControlId(),
                        'plot1tyguinier'        : self.NewControlId(),
                        'plot1tykratky'         : self.NewControlId(),
                        'plot1typorod'          : self.NewControlId(),
                        'plot1tysubtracted'     : self.NewControlId(),
                        'plot2tynormal'         : self.NewControlId(),
                        'plot2tyguinier'        : self.NewControlId(),
                        'plot2tykratky'         : self.NewControlId(),
                        'plot2tysubtracted'     : self.NewControlId(),
                        'plot2typorod'          : self.NewControlId(),
                        'plot1sclinlin'         : self.NewControlId(),
                        'plot1scloglog'         : self.NewControlId(),
                        'plot1scloglin'         : self.NewControlId(),
                        'plot1sclinlog'         : self.NewControlId(),
                        'plot2sclinlin'         : self.NewControlId(),
                        'plot2scloglog'         : self.NewControlId(),
                        'plot2scloglin'         : self.NewControlId(),
                        'plot2sclinlog'         : self.NewControlId(),
                        'secplottotal'          : self.NewControlId(),
                        'secplotmean'           : self.NewControlId(),
                        'secplotq'              : self.NewControlId(),
                        'secplotqr'             : self.NewControlId(),
                        'secplotframe'          : self.NewControlId(),
                        'secplottime'           : self.NewControlId(),
                        'secplotrg'             : self.NewControlId(),
                        'secplotvcmw'           : self.NewControlId(),
                        'secplotvpmw'           : self.NewControlId(),
                        'secploti0'             : self.NewControlId(),
                        'secplotnone'           : self.NewControlId(),
                        'secplotunsub'          : self.NewControlId(),
                        'secplotsub'            : self.NewControlId(),
                        'secplotbaseline'       : self.NewControlId(),
                        'help'                  : self.NewControlId(),
                        'about'                 : self.NewControlId(),
                        'guinierfit'            : self.NewControlId(),
                        'molweight'             : self.NewControlId(),
                        'saveWorkspace'         : self.NewControlId(),
                        'loadWorkspace'         : self.NewControlId(),
                        'average'               : self.NewControlId(),
                        'subtract'              : self.NewControlId(),
                        'merge'                 : self.NewControlId(),
                        'rebin'                 : self.NewControlId(),
                        'interpolate'           : self.NewControlId(),
                        'q*10'                  : self.NewControlId(),
                        'q/10'                  : self.NewControlId(),
                        'norm_conc'             : self.NewControlId(),
                        'mwstandard'            : self.NewControlId(),
                        'showimage'             : self.NewControlId(),
                        'showdata'              : self.NewControlId(),
                        'showheader'            : self.NewControlId(),
                        'rungnom'               : self.NewControlId(),
                        'rundammif'             : self.NewControlId(),
                        'bift'                  : self.NewControlId(),
                        'runambimeter'          : self.NewControlId(),
                        'runsvd'                : self.NewControlId(),
                        'runefa'                : self.NewControlId(),
                        'showhistory'           : self.NewControlId(),
                        'weightedAverage'       : self.NewControlId(),
                        'similarityTest'        : self.NewControlId(),
                        'normalizedKratky'      : self.NewControlId(),
                        'superimpose'           : self.NewControlId(),
                        'sync'                  : self.NewControlId(),
                        'rundenss'              : self.NewControlId(),
                        'calcUVconc'            : self.NewControlId()
                        }

        self.tbIcon = RawTaskbarIcon(self)

        self.guinierframe = None
        self.molweightframe = None
        self.gnomframe = None
        self.biftframe = None
        self.dammifframe = None
        self.ambimeterframe = None
        self.svdframe = None
        self.efaframe = None
        self.similarityframe = None
        self.kratkyframe = None
        self.denssframe = None
        self.lc_series_frame = None

        self.raw_settings = RAWSettings.RawGuiSettings()

        self.OnlineControl = OnlineController(self, self.raw_settings)
        self.OnlineSECControl = OnlineSECController(self, self.raw_settings)

        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -2, -1])
        self.statusbar.SetStatusText('Mode: OFFLINE', 2)
        self.Bind(wx.EVT_CLOSE, self._onCloseWindow)

        # *************** Set minimum frame size ***************
        client_display = wx.GetClientDisplayRect()
        minsize = (min(800, client_display.Width), min(600, client_display.Height))
        self.SetMinSize(minsize)

        # /* CREATE PLOT NOTEBOOK */
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.plot_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS)

        plot_panel = RAWPlot.PlotPanel(self.plot_notebook, -1, 'PlotPanel')
        img_panel = RAWImage.ImagePanel(self.plot_notebook, -1, 'ImagePanel')
        iftplot_panel = RAWPlot.IftPlotPanel(self.plot_notebook, -1, 'IFTPlotPanel')
        sec_panel = RAWPlot.SeriesPlotPanel(self.plot_notebook,-1, 'SECPlotPanel')

        self.plot_notebook.AddPage(plot_panel, "Main Plot", True)
        self.plot_notebook.AddPage(iftplot_panel, "IFT Plot", False)
        self.plot_notebook.AddPage(img_panel, "Image", False)
        self.plot_notebook.AddPage(sec_panel, "Series", False)


        self.control_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE)
        page2 = ManipulationPanel(self.control_notebook, self.raw_settings)
        page4 = SECPanel(self.control_notebook, self.raw_settings)
        page3 = IFTPanel(self.control_notebook, self.raw_settings)
        page1 = FilePanel(self.control_notebook)

        self.control_notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onControlTabChange)


        self.control_notebook.AddPage(page1, "Files", True)
        self.control_notebook.AddPage(page2, "Manipulation", False)
        self.control_notebook.AddPage(page3, "IFT", False)
        self.control_notebook.AddPage(page4, "Series",False)

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

        icon = RAWIcons.raw.GetIcon()
        self.SetIcon(icon)
        app.SetTopWindow(self)

        size = (min(1024, client_display.Width), min(768, client_display.Height))
        self.SetSize(size)
        self.CenterOnScreen()
        self.Show(True)

    def _onStartup(self, data):
        file = os.path.join(RAWGlobals.RAWWorkDir, 'backup.cfg')

        if os.path.exists(file):

            if self.raw_settings.get('PromptConfigLoad'):
                dlg = wx.MessageDialog(parent = self, message = 'Load last saved configuration?', caption = 'Restore configuration', style=wx.YES_NO|wx.ICON_QUESTION)
                answer = dlg.ShowModal()
                dlg.Destroy()
            else:
                answer = wx.ID_YES

            if answer == wx.ID_YES:
                success = RAWSettings.loadSettings(self.raw_settings, file)

                if success:
                    self.raw_settings.set('CurrentCfg', file)
                else:
                    wx.CallAfter(wx.MessageBox,'Load failed, config file might be corrupted.',
                                  'Load failed', style = wx.ICON_ERROR | wx.OK)

        dirctrl = wx.FindWindowByName('DirCtrlPanel')
        dirctrl._useSavedPathIfExisits()

        find_atsas = self.raw_settings.get('autoFindATSAS')

        if find_atsas:
            atsas_dir = RAWOptions.findATSASDirectory()
            self.raw_settings.set('ATSASDir', atsas_dir)

        start_online_mode = self.raw_settings.get('OnlineModeOnStartup')
        online_path = self.raw_settings.get('OnlineStartupDir')

        if start_online_mode and os.path.isdir(online_path):
            if online_path != None:
                self.OnlineControl.seek_dir = online_path
                self.OnlineControl.goOnline()

                self.setStatus('Mode: ONLINE', 2)

            menubar = self.GetMenuBar()
            item = menubar.FindItemById(self.MenuIDs['goOnline'])
            item.Check(True)

        if len(data)>1:
            files_to_plot = data[1:]
            if isinstance(files_to_plot, list):
                firstfile = files_to_plot[0]
            else:
                firstfile = files_to_plot

            if not firstfile.startswith('-psn'):
                mainworker_cmd_queue.put(['plot', files_to_plot])

    def getRawSettings(self):
        return self.raw_settings

    def findAtsas(self):
        find_atsas = self.raw_settings.get('autoFindATSAS')
        if find_atsas:
            atsas_dir = RAWOptions.findATSASDirectory()

            self.raw_settings.set('ATSASDir', atsas_dir)

    def queueTaskInWorkerThread(self, taskname, data):
        mainworker_cmd_queue.put([taskname, data])

    def closeBusyDialog(self):
        del self._busyDialog
        self._busyDialog = None

    def showBusyDialog(self, text):
        self._busyDialog = wx.BusyInfo(text, self)

    def getWorkerThreadQueue(self):
        return mainworker_cmd_queue

    def getQuestionReturnQueue(self):
        return question_return_queue

    def showMaskingPane(self):
        if self._mgr.GetPane(self.centering_panel).IsShown():
            image_panel = wx.FindWindowByName('ImagePanel')

            if self.centering_panel.autocenter:
                self.centering_panel._cleanUpAutoCenter()

            image_panel.enableCenterClickMode(False)

            self.centering_panel.updateCenterFromSettings()

            image_panel.clearPatches()

        self._mgr.GetPane(self.masking_panel).Show(True)
        self._mgr.GetPane(self.centering_panel).Show(False)
        self._mgr.GetPane(self.control_notebook).Show(False)
        self._mgr.Update()

        page = -1

        for i in range(self.plot_notebook.GetPageCount()):
            if self.plot_notebook.GetPageText(i) == 'Image':
                page = i
                self.plot_notebook.SetSelection(page)

        #This is stupid and shouldn't be necessary!
        if page > -1:
            while self.plot_notebook.GetSelection() != page:
                time.sleep(.001)
                self.plot_notebook.SetSelection(page)

        self.masking_panel.updateView()

    def closeMaskingPane(self):
        self._mgr.GetPane(self.masking_panel).Show(False)
        self._mgr.GetPane(self.control_notebook).Show(True)
        self._mgr.Update()

        page = -1

        for i in range(self.plot_notebook.GetPageCount()):
            if self.plot_notebook.GetPageText(i) == 'Main Plot':
                page = i
                self.plot_notebook.SetSelection(page)

        #This is stupid and shouldn't be necessary!
        if page > -1:
            while self.plot_notebook.GetSelection() != page:
                time.sleep(.001)
                self.plot_notebook.SetSelection(page)

    def showCenteringPane(self):
        if self._mgr.GetPane(self.masking_panel).IsShown():
            image_panel = wx.FindWindowByName('ImagePanel')
            image_panel.stopMaskCreation()
            image_panel.clearAllMasks()
            image_panel.removeCenterPatch()

        self._mgr.GetPane(self.centering_panel).Show(True)
        self._mgr.GetPane(self.control_notebook).Show(False)
        self._mgr.GetPane(self.masking_panel).Show(False)
        self._mgr.Update()

        page = -1

        for i in range(self.plot_notebook.GetPageCount()):
            if self.plot_notebook.GetPageText(i) == 'Image':
                page = i
                self.plot_notebook.SetSelection(page)

        #This is stupid and shouldn't be necessary!
        if page > -1:
            while self.plot_notebook.GetSelection() != page:
                time.sleep(.001)
                self.plot_notebook.SetSelection(page)

        self.centering_panel.updateAll()

    def closeCenteringPane(self):
        self._mgr.GetPane(self.centering_panel).Show(False)
        self._mgr.GetPane(self.control_notebook).Show(True)
        self._mgr.Update()
        page = -1

        for i in range(self.plot_notebook.GetPageCount()):
            if self.plot_notebook.GetPageText(i) == 'Main Plot':
                page = i
                self.plot_notebook.SetSelection(page)

        #This is stupid and shouldn't be necessary!
        if page > -1:
            while self.plot_notebook.GetSelection() != page:
                time.sleep(.001)
                self.plot_notebook.SetSelection(page)


    def showQuestionDialogFromThread(self, question, label, button_list, icon = None, filename = None, save_path = None):
        ''' Function to show a question dialog from the thread '''

        question_dialog = RAWCustomDialogs.CustomQuestionDialog(self, question, button_list, label, icon, filename, save_path, style = wx.CAPTION | wx.RESIZE_BORDER)
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

    def showGNOMFrame(self, sasm, manip_item):

        atsasPath = self.raw_settings.get('ATSASDir')

        opsys = platform.system()
        if opsys == 'Windows':
            gnomPath = os.path.join(atsasPath, 'gnom.exe')
        else:
            gnomPath = os.path.join(atsasPath, 'gnom')

        if os.path.exists(gnomPath):

            if self.gnomframe:
                self.gnomframe.Destroy()

            #if not self.guinierframe:
            self.gnomframe = RAWAnalysis.GNOMFrame(self, 'GNOM', sasm, manip_item)
            self.gnomframe.SetIcon(self.GetIcon())
            self.gnomframe.Show(True)

        else:
            msg = 'The GNOM program in the ATSAS package could not be found. Please make sure that ATSAS is installed, and that you have defined the ATSAS directory in the RAW Advanced Options. '
            dial2 = wx.MessageDialog(self, msg, "Can't find ATSAS",
                                    wx.OK | wx.ICON_INFORMATION)
            dial2.ShowModal()
            dial2.Destroy()


    def showBIFTFrame(self, sasm, manip_item):

        if self.biftframe:
            self.biftframe.Destroy()

        #if not self.guinierframe:
        self.biftframe = RAWAnalysis.BIFTFrame(self, 'BIFT', sasm, manip_item)
        self.biftframe.SetIcon(self.GetIcon())
        self.biftframe.Show(True)

    def showMolWeightFrame(self, sasm, manip_item):

        if self.molweightframe:
            self.molweightframe.Destroy()

        #if not self.guinierframe:
        self.molweightframe = RAWAnalysis.MolWeightFrame(self, 'Molecular Weight', sasm, manip_item)
        self.molweightframe.SetIcon(self.GetIcon())
        self.molweightframe.Show(True)

    def showGuinierFitFrame(self, sasm, manip_item):

        if self.guinierframe:
            self.guinierframe.Destroy()

        self.guinierframe = RAWAnalysis.GuinierFrame(self, 'Guinier Fit', sasm, manip_item)
        self.guinierframe.SetIcon(self.GetIcon())
        self.guinierframe.Show(True)

    def showDAMMIFFrame(self, iftm, manip_item):

        if iftm.getParameter('algorithm') != 'GNOM':
            msg = 'DAMMIF can only process IFTs produced by GNOM. This was produced using %s.' %(iftm.getParameter('algorithm'))
            dial2 = wx.MessageDialog(self, msg, "Wrong IFT type",
                                    wx.OK | wx.ICON_ERROR)
            dial2.ShowModal()
            dial2.Destroy()

            return

        atsasPath = self.raw_settings.get('ATSASDir')

        opsys = platform.system()
        if opsys == 'Windows':
            dammifPath = os.path.join(atsasPath, 'dammif.exe')
        else:
            dammifPath = os.path.join(atsasPath, 'dammif')

        if os.path.exists(dammifPath):

            if self.dammifframe:
                result = self.dammifframe.Close()
            else:
                result = True

            #if not self.guinierframe:

            if result:
                self.dammifframe = RAWAnalysis.DammifFrame(self, 'DAMMIF/N', iftm, manip_item)
                self.dammifframe.SetIcon(self.GetIcon())
                self.dammifframe.Show(True)
            else:
                return

        else:
            msg = 'The DAMMIF program in the ATSAS package could not be found. Please make sure that ATSAS is installed, and that you have defined the ATSAS directory in the RAW Advanced Options. '
            dial2 = wx.MessageDialog(self, msg, "Can't find ATSAS",
                                    wx.OK | wx.ICON_INFORMATION)
            dial2.ShowModal()
            dial2.Destroy()

    def showAmbiFrame(self, iftm, manip_item):

        if iftm.getParameter('algorithm') != 'GNOM':
            msg = 'AMBIMETER can only process IFTs produced by GNOM. This was produced using %s.' %(iftm.getParameter('algorithm'))
            dial2 = wx.MessageDialog(self, msg, "Wrong IFT type",
                                    wx.OK | wx.ICON_ERROR)
            dial2.ShowModal()
            dial2.Destroy()

            return

        atsasPath = self.raw_settings.get('ATSASDir')

        opsys = platform.system()
        if opsys == 'Windows':
            ambiPath = os.path.join(atsasPath, 'ambimeter.exe')
        else:
            ambiPath = os.path.join(atsasPath, 'ambimeter')

        if os.path.exists(ambiPath):

            process = subprocess.Popen('%s -v' %(ambiPath), shell= True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)

            output, error = process.communicate()

            rev = output.split('\n')[0].split()[-1].strip().strip(')(rM').strip('aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ')

            if int(rev) >= 6669:


                if self.ambimeterframe:
                    self.ambimeterframe.Close()

                self.ambimeterframe = RAWAnalysis.AmbimeterFrame(self, 'AMBIMETER', iftm, manip_item)
                self.ambimeterframe.SetIcon(self.GetIcon())
                self.ambimeterframe.Show(True)

            else:
                msg = 'The AMBIMETER version is not recent enough. You need to have ATSAS >= 2.7.1 installed to use this feature.'
                dial2 = wx.MessageDialog(self, msg, "Wrong AMBIMETER Version",
                                        wx.OK | wx.ICON_INFORMATION)
                dial2.ShowModal()
                dial2.Destroy()

        else:
            msg = 'The AMBIMETER program in the ATSAS package could not be found. Please make sure that ATSAS is installed, and that you have defined the ATSAS directory in the RAW Advanced Options. '
            dial2 = wx.MessageDialog(self, msg, "Can't find ATSAS",
                                    wx.OK | wx.ICON_INFORMATION)
            dial2.ShowModal()
            dial2.Destroy()

    def showSVDFrame(self, secm, manip_item):

        if self.svdframe:
            self.svdframe.Destroy()

        self.svdframe = RAWAnalysis.SVDFrame(self, 'Singular Value Decomposition', secm, manip_item)
        self.svdframe.SetIcon(self.GetIcon())
        self.svdframe.Show(True)

    def showEFAFrame(self, secm, manip_item):

        if self.efaframe:
            self.efaframe.Destroy()

        #make a subtracted profile SECM
        if len(secm.subtracted_sasm_list) == 0 and manip_item != None:
            msg = ('No subtracted files are available for this series curve. '
                'It is recommended that you run EFA on subtracted profiles. '
                'You can create subtracted profiles using the LC Series analysis '
                'panel, accessible by right clicking on the item in the Series '
                'panel. Click OK to continue with the EFA without subtracted files.'
                )
            dlg = wx.MessageDialog(self, msg, "No subtracted files", style = wx.ICON_INFORMATION | wx.CANCEL | wx.OK)
            proceed = dlg.ShowModal()
            dlg.Destroy()

            if proceed == wx.ID_CANCEL:
                return

        self.efaframe = RAWAnalysis.EFAFrame(self, 'Evolving Factor Analysis', secm, manip_item)
        self.efaframe.SetIcon(self.GetIcon())
        self.efaframe.Show(True)

    def showSimilarityFrame(self, sasm_list):

        if self.similarityframe:
            self.similarityframe.Destroy()

        if not sasm_list or len(sasm_list) == 1:
            msg = 'You must select at least 2 items to test similarity.'
            dlg = wx.MessageDialog(self, msg, "Select more items", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return

        self.similarityframe = RAWAnalysis.SimilarityFrame(self, 'Similarity Testing', sasm_list)
        self.similarityframe.SetIcon(self.GetIcon())
        self.similarityframe.Show(True)

    def showNormKratkyFrame(self, sasm_list):

        if self.kratkyframe:
            self.kratkyframe.Destroy()

        if not sasm_list or sasm_list is None:
            msg = 'You must select at least 1 profile.'
            dlg = wx.MessageDialog(self, msg, "Select more profiles", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return

        missing_rg = []
        for sasm in sasm_list:
            analysis_dict = sasm.getParameter('analysis')
            if 'guinier' not in analysis_dict or 'Rg' not in analysis_dict['guinier'] or 'I0' not in analysis_dict['guinier']:
                missing_rg.append(sasm)

        if len(missing_rg) > 0:
            question = ('One or more of the selected profiles does not have\n'
                'Guinier analysis data. All selected profiles must '
                'have Rg\nand I0 from Guinier analysis. Select an action below.')
            button_list = [('Cancel', wx.ID_CANCEL),('Proceed using AutoRg', wx.ID_YES)]
            label = "Missing Guinier Analysis"
            icon = wx.ART_WARNING

            question_dialog = RAWCustomDialogs.CustomQuestionDialog(self, question, button_list, label, icon, None, None, style = wx.CAPTION | wx.RESIZE_BORDER)
            result = question_dialog.ShowModal()
            question_dialog.Destroy()

            if result == wx.ID_CANCEL:
                return
            else:
                failed_autorg = []
                error_weight = self.raw_settings.get('errorWeight')
                for sasm in missing_rg:
                    rg, rger, i0, i0er, idx_min, idx_max = SASCalc.autoRg(sasm,
                        single_fit=True, error_weight=error_weight)
                    if rg > 0:
                        qs = np.square(sasm.q)
                        il = np.log(sasm.i)
                        iler = il*np.absolute(sasm.err/sasm.i)
                        a = np.log(i0)
                        b = np.square(rg)/-3.
                        r_sqr = 1 - np.square(il[idx_min:idx_max]-SASCalc.linear_func(qs[idx_min:idx_max], a, b)).sum()/np.square(il[idx_min:idx_max]-il[idx_min:idx_max].mean()).sum()

                        guinier_data = {'I0'        : str(i0),
                                        'Rg'        : str(rg),
                                        'nStart'    : str(idx_min),
                                        'nEnd'      : str(idx_max),
                                        'qStart'    : str(sasm.q[idx_min]),
                                        'qEnd'      : str(sasm.q[idx_max]),
                                        'qRg_min'   : str(sasm.q[idx_min]*rg),
                                        'qRg_max'   : str(sasm.q[idx_max]*rg),
                                        'rsq'       : str(r_sqr),
                                        }

                        analysis_dict = sasm.getParameter('analysis')
                        analysis_dict['guinier'] = guinier_data

                    else:
                        failed_autorg.append(sasm)

            if len(failed_autorg) > 0:
                msg = ('AutoRg failed for one or more of the files, so the '
                        'normalized Kratky plot cannot be shown. Autorg failed on:')
                for sasm in failed_autorg:
                    msg = msg + '\n%s' %(sasm.getParameter('filename'))

                wx.MessageBox(msg, 'AutoRg Failed', style=wx.ICON_ERROR|wx.OK)

                return

        self.kratkyframe = RAWAnalysis.NormKratkyFrame(self, 'Normalized Kratky Plots', sasm_list)
        self.kratkyframe.SetIcon(self.GetIcon())
        self.kratkyframe.Show(True)

    def showDenssFrame(self, iftm, manip_item):
        if self.denssframe:
            self.denssframe.Destroy()

        self.denssframe = RAWAnalysis.DenssFrame(self, 'DENSS', iftm, manip_item)
        self.denssframe.SetIcon(self.GetIcon())
        self.denssframe.Show(True)

    def showLCSeriesFrame(self, secm, manip_item):

        if self.lc_series_frame:
            self.lc_series_frame.Destroy()

        self.lc_series_frame = RAWAnalysis.LCSeriesFrame(self, 'Liquid Chromatography Series Analysis', secm, manip_item, self.raw_settings)
        self.lc_series_frame.SetIcon(self.GetIcon())
        self.lc_series_frame.Show(True)

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
        msg = "In program help is not current available for RAW. For tutorials, demo videos, and installation guides, please see the RAW project home page (select Help->About for more details)."
        wx.CallAfter(wx.MessageBox, msg, 'Sorry!', style=wx.OK|wx.ICON_INFORMATION)
        # os.execl('xchm')

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
                                      ('Online', self.MenuIDs['goOnline'], self._onOnlineMenu, 'radio'),
                                      ('Change Directory', self.MenuIDs['changeOnline'], self._onOnlineMenu, 'normal')],

                    'viewSECLeft':   [('Integrated Intensity', self.MenuIDs['secplottotal'], self._onViewMenu, 'radio'),
                                      ('Mean Intensity', self.MenuIDs['secplotmean'], self._onViewMenu, 'radio'),
                                      ('Intensity a specific q', self.MenuIDs['secplotq'], self._onViewMenu, 'radio'),
                                      ('Intensity in q range', self.MenuIDs['secplotqr'], self._onViewMenu, 'radio')],

                    'viewSECInt':   [('Unsubtracted', self.MenuIDs['secplotunsub'], self._onViewMenu, 'radio'),
                                        ('Subtracted', self.MenuIDs['secplotsub'], self._onViewMenu, 'radio'),
                                        ('Baseline Corrected', self.MenuIDs['secplotbaseline'], self._onViewMenu, 'radio'),
                                        ],

                    'viewSECRight':  [('RG', self.MenuIDs['secplotrg'], self._onViewMenu, 'radio'),
                                      ('MW (Vc)', self.MenuIDs['secplotvcmw'], self._onViewMenu, 'radio'),
                                      ('MW (Vp)', self.MenuIDs['secplotvpmw'], self._onViewMenu, 'radio'),
                                      ('I0', self.MenuIDs['secploti0'], self._onViewMenu, 'radio'),
                                      ('None', self.MenuIDs['secplotnone'], self._onViewMenu, 'radio')],

                    'viewSECX':      [('Frame Number', self.MenuIDs['secplotframe'], self._onViewMenu, 'radio'),
                                      ('Time', self.MenuIDs['secplottime'], self._onViewMenu, 'radio')],
                    'operations':    [('Subtract', self.MenuIDs['subtract'], self._onToolsMenu, 'normal'),
                                      ('Average', self.MenuIDs['average'], self._onToolsMenu, 'normal'),
                                      ('Weighted Average', self.MenuIDs['weightedAverage'], self._onToolsMenu, 'normal'),
                                      ('Interpolate', self.MenuIDs['interpolate'], self._onToolsMenu, 'normal'),
                                      ('Merge', self.MenuIDs['merge'], self._onToolsMenu, 'normal'),
                                      ('Normalize by concentration', self.MenuIDs['norm_conc'], self._onToolsMenu, 'normal'),
                                      ('Rebin', self.MenuIDs['rebin'], self._onToolsMenu, 'normal'),
                                      ('Superimpose', self.MenuIDs['superimpose'], self._onToolsMenu, 'normal'),
                                      ('Sync', self.MenuIDs['sync'], self._onToolsMenu, 'normal'),
                                      ],
                    'convertq':      [('q * 10', self.MenuIDs['q*10'], self._onToolsMenu, 'normal'),
                                      ('q / 10', self.MenuIDs['q/10'], self._onToolsMenu, 'normal')],
                    'atsas':         [('GNOM', self.MenuIDs['rungnom'], self._onToolsMenu, 'normal'),
                                      ('DAMMIF/N', self.MenuIDs['rundammif'], self._onToolsMenu, 'normal'),
                                      ('AMBIMETER', self.MenuIDs['runambimeter'], self._onToolsMenu, 'normal')]
                                      }


        menus = [('&File',    [('&Load Settings', self.MenuIDs['loadSettings'], self._onLoadMenu, 'normal'),
                               ('&Save Settings', self.MenuIDs['saveSettings'], self._onSaveMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('&Load Workspace', self.MenuIDs['loadWorkspace'], self._onLoadWorkspaceMenu, 'normal'),
                               ('&Save Workspace', self.MenuIDs['saveWorkspace'], self._onSaveWorkspaceMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('E&xit', self.MenuIDs['exit'], self._onFileMenu, 'normal')]),

                 ('&Options', [('&Advanced Options...', self.MenuIDs['advancedOptions'], self._onOptionsMenu, 'normal'),
                              ('&Online mode', None, submenus['onlinemenu'], 'submenu')]),

                 ('&View',    [('&Show Image', self.MenuIDs['showimage'], self._onViewMenu, 'normal'),
                               ('&Show Data', self.MenuIDs['showdata'], self._onViewMenu, 'normal'),
                               ('&Show Header', self.MenuIDs['showheader'], self._onViewMenu, 'normal'),
                               ('&Show History', self.MenuIDs['showhistory'], self._onViewMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('&Main Plot Top Axes', None, submenus['viewPlot1Scale'], 'submenu'),
                               ('&Main Plot Bottom Axes', None, submenus['viewPlot2Scale'], 'submenu'),
                               ('&Series Plot Left Y Axis', None, submenus['viewSECLeft'], 'submenu'),
                               ('&Series Plot Right Y Axis', None, submenus['viewSECRight'], 'submenu'),
                               ('&Series Plot Intensity Type', None, submenus['viewSECInt'], 'submenu'),
                               ('&Series Plot X Axis', None, submenus['viewSECX'], 'submenu')
                               ]),

                 ('&Tools',   [('&Operations', None, submenus['operations'], 'submenu'),
                               ('&Convert q-scale', None, submenus['convertq'], 'submenu'),
                               ('&Use as MW standard', self.MenuIDs['mwstandard'], self._onToolsMenu, 'normal'),
                               ('&Calculate conc. from UV', self.MenuIDs['calcUVconc'], self._onToolsMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('&Guinier fit', self.MenuIDs['guinierfit'], self._onToolsMenu, 'normal'),
                               ('&Molecular weight', self.MenuIDs['molweight'], self._onToolsMenu, 'normal'),
                               ('&BIFT', self.MenuIDs['bift'], self._onToolsMenu, 'normal'),
                               ('&ATSAS', None, submenus['atsas'], 'submenu'),
                               ('&Electron Density (DENSS)', self.MenuIDs['rundenss'], self._onToolsMenu, 'normal'),
                               ('&SVD', self.MenuIDs['runsvd'], self._onToolsMenu, 'normal'),
                               ('&EFA', self.MenuIDs['runefa'], self._onToolsMenu, 'normal'),
                               ('&Similarity Test', self.MenuIDs['similarityTest'], self._onToolsMenu, 'normal'),
                               ('&Normalized Kratky Plots', self.MenuIDs['normalizedKratky'], self._onToolsMenu, 'normal'),
                               (None, None, None, 'separator'),
                               ('&Centering/Calibration', self.MenuIDs['centering'], self._onToolsMenu, 'normal'),
                               ('&Masking', self.MenuIDs['masking'], self._onToolsMenu, 'normal')
                              ]),

                 ('&Help',    [('&Help!', self.MenuIDs['help'], self._onHelp, 'normal'),
                               (None, None, None, 'separator'),
                               ('&About', self.MenuIDs['about'], self._onAboutDlg, 'normal')])]

        menubar = wx.MenuBar()

        for each in menus:

            menuitem = self._createSingleMenuBarItem(each[1])
            menubar.Append(menuitem, each[0])

        self.Bind(wx.EVT_MENU, self._onFileMenu, id = wx.ID_EXIT)

        self.SetMenuBar(menubar)

    def _onToolsMenu(self, evt):

        id = evt.GetId()

        if id == self.MenuIDs['guinierfit']:

            manippage = wx.FindWindowByName('ManipulationPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                sasm = manippage.getSelectedItems()[0].getSASM()
                self.showGuinierFitFrame(sasm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select a scattering profile from the list on the manipulation page.", "No profile selected")

        elif id == self.MenuIDs['molweight']:
            manippage = wx.FindWindowByName('ManipulationPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                sasm = manippage.getSelectedItems()[0].getSASM()
                self.showMolWeightFrame(sasm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select a scattering profile from the list on the manipulation page.", "No profile selected")

        elif id == self.MenuIDs['centering']:
            self.showCenteringPane()

        elif id == self.MenuIDs['masking']:
            self.showMaskingPane()

        elif id == self.MenuIDs['subtract']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            marked_item = page.getBackgroundItem()
            mainworker_cmd_queue.put(['subtract_items', [marked_item, selected_items]])

        elif id == self.MenuIDs['average']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            mainworker_cmd_queue.put(['average_items', selected_items])

        elif id == self.MenuIDs['merge']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            marked_item = page.getBackgroundItem()
            mainworker_cmd_queue.put(['merge_items', [marked_item, selected_items]])

        elif id == self.MenuIDs['rebin']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()

            dlg = RAWCustomDialogs.RebinDialog(self)
            retval = dlg.ShowModal()
            ret, logbin = dlg.getValues()
            dlg.Destroy()

            if retval != wx.ID_CANCEL:
                mainworker_cmd_queue.put(['rebin_items', [selected_items, ret, logbin]])

        elif id == self.MenuIDs['interpolate']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            marked_item = page.getBackgroundItem()
            mainworker_cmd_queue.put(['interpolate_items', [marked_item, selected_items]])

        elif id == self.MenuIDs['weightedAverage']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            mainworker_cmd_queue.put(['weighted_average_items', selected_items])

        elif id == self.MenuIDs['superimpose']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            page.Superimpose()

        elif id == self.MenuIDs['sync']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            page.Sync()

        elif id == self.MenuIDs['q*10']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel') and page != wx.FindWindowByName('IFTPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation or IFT window is selected.', 'Select Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            altered=[]
            for item in selected_items:
                sasm = item.sasm

                sasm.scaleBinnedQ(10.0)
                item._updateQTextCtrl()
                item.markAsModified()
                altered.append(sasm)

            wx.CallAfter(sasm.plot_panel.updatePlotAfterManipulation, altered)

        elif id == self.MenuIDs['q/10']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel') and page != wx.FindWindowByName('IFTPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation or IFT window is selected.', 'Select Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            altered=[]
            for item in selected_items:
                sasm = item.sasm

                sasm.scaleBinnedQ(0.1)
                item._updateQTextCtrl()
                item.markAsModified()
                altered.append(sasm)

            wx.CallAfter(sasm.plot_panel.updatePlotAfterManipulation, altered)

        elif id == self.MenuIDs['norm_conc']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            mainworker_cmd_queue.put(['normalize_conc', [selected_items]])

        elif id == self.MenuIDs['mwstandard']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()

            if len(selected_items) !=1:
                wx.MessageBox('Please select one (and only one) item to use as the MW standard.', 'Select Item', style = wx.ICON_INFORMATION)
                return

            selected_items[0].useAsMWStandard()

        elif id == self.MenuIDs['rungnom']:
            manippage = wx.FindWindowByName('ManipulationPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                sasm = manippage.getSelectedItems()[0].getSASM()
                self.showGNOMFrame(sasm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select a scattering profile from the list on the manipulation page.", "No profile selected")

        elif id == self.MenuIDs['rundammif']:
            manippage = wx.FindWindowByName('IFTPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the IFT window is selected.', 'Select IFT Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                iftm = manippage.getSelectedItems()[0].getIFTM()
                self.showDAMMIFFrame(iftm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select an IFT from the list on the IFT page.", "No IFT selected")

        elif id == self.MenuIDs['bift']:
            manippage = wx.FindWindowByName('ManipulationPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                sasm = manippage.getSelectedItems()[0].getSASM()
                self.showBIFTFrame(sasm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select a scattering profile from the list on the manipulation page.", "No profile selected")

        elif id == self.MenuIDs['runambimeter']:
            manippage = wx.FindWindowByName('IFTPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the IFT window is selected.', 'Select IFT Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                iftm = manippage.getSelectedItems()[0].getIFTM()
                self.showAmbiFrame(iftm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select an IFT from the list on the IFT page.", "No IFT selected")


        elif id == self.MenuIDs['runsvd']:
            secpage = wx.FindWindowByName('SECPanel')
            manippage = wx.FindWindowByName('ManipulationPanel')
            iftpage = wx.FindWindowByName('IFTPanel')
            filepage = wx.FindWindowByName('FilePanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page == manippage:
                selected_items = manippage.getSelectedItems()

                if len(selected_items) > 1:
                    selected_sasms = [item.sasm for item in selected_items]

                    selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

                    frame_list = range(len(selected_sasms))

                    secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

                    manip_item = None

                else:
                    msg = 'You must select at least 2 scattering profiles to run SVD.'
                    dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()

                    return

            elif page == iftpage:
                selected_items = iftpage.getSelectedItems()

                if len(selected_items) > 1:

                    selected_iftms = [item.iftm for item in selected_items]

                    selected_sasms = [SASM.SASM(iftm.p, iftm.r, iftm.err, iftm.getAllParameters()) for iftm in selected_iftms]

                    selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

                    frame_list = range(len(selected_sasms))

                    secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

                    manip_item = None

                else:
                    msg = 'You must select at least 2 P(r) functions to run SVD.'
                    dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()

                    return

            elif page == secpage:
                selected_items = secpage.getSelectedItems()

                if len(selected_items) > 0:
                    secm = selected_items[0].getSECM()
                    manip_item = selected_items[0]
                else:
                    wx.MessageBox("Please select a series curve from the list on the series page.", "No series curve selected")
                    return

            elif page == filepage:
                wx.MessageBox('The selected operation cannot be performed from the file tab.', 'Select Different Tab', style = wx.ICON_INFORMATION)
                return

            self.showSVDFrame(secm, manip_item)


        elif id == self.MenuIDs['runefa']:
            secpage = wx.FindWindowByName('SECPanel')
            manippage = wx.FindWindowByName('ManipulationPanel')
            iftpage = wx.FindWindowByName('IFTPanel')
            filepage = wx.FindWindowByName('FilePanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page == manippage:
                selected_items = manippage.getSelectedItems()

                if len(selected_items) > 1:
                    selected_sasms = [item.sasm for item in selected_items]

                    selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

                    frame_list = range(len(selected_sasms))

                    secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

                    manip_item = None

                else:
                    msg = 'You must select at least 2 scattering profiles to run EFA.'
                    dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()

                    return

            elif page == iftpage:
                selected_items = iftpage.getSelectedItems()

                if len(selected_items) > 1:

                    selected_iftms = [item.iftm for item in selected_items]

                    selected_sasms = [SASM.SASM(iftm.p, iftm.r, iftm.err, iftm.getAllParameters()) for iftm in selected_iftms]

                    selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

                    frame_list = range(len(selected_sasms))

                    secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

                    manip_item = None

                else:
                    msg = 'You must select at least 2 P(r) functions to run EFA.'
                    dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()

                    return

            elif page == secpage:
                selected_items = secpage.getSelectedItems()

                if len(selected_items) > 0:
                    secm = selected_items[0].getSECM()
                    manip_item = selected_items[0]
                else:
                    wx.MessageBox("Please select a series curve from the list on the series page.", "No series curve selected")
                    return

            elif page == filepage:
                wx.MessageBox('The selected operation cannot be performed from the file tab.', 'Select Different Tab', style = wx.ICON_INFORMATION)
                return

            self.showEFAFrame(secm, manip_item)

        elif id == self.MenuIDs['similarityTest']:
            manippage = wx.FindWindowByName('ManipulationPanel')
            secpage = wx.FindWindowByName('SECPanel')
            iftpage = wx.FindWindowByName('IFTPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page !=manippage and page != secpage and page != iftpage:
                wx.MessageBox('The selected operation cannot be performed unless the Manipulation, IFT, or Series control panel is selected.', 'Select Appropriate Control Panel', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            if selected_items:
                if page == manippage:
                    selected_sasms = [item.getSASM() for item in selected_items]
                elif page == iftpage:
                    selected_iftms = [item.getIFTM() for item in selected_items]
                    selected_sasms = [SASM.SASM(iftm.p, iftm.r, iftm.err, iftm.getAllParameters()) for iftm in selected_iftms]
                elif page == secpage:
                    selected_secms = [item.getSECM() for item in selected_items]
                    selected_sasms = []
                    sec_plot_panel = wx.FindWindowByName('SECPlotPanel')
                    ydata_type = sec_plot_panel.plotparams['y_axis_display']

                    for secm in selected_secms:
                        if ydata_type == 'q_val':
                            intensity = secm.I_of_q
                        elif ydata_type == 'mean':
                            intensity = secm.mean_i
                        elif ydata_type == 'q_range':
                            intensity = secm.qrange_I
                        else:
                            intensity = secm.total_i

                        selected_sasms.append(SASM.SASM(intensity, secm.frame_list, np.sqrt(intensity), secm.getAllParameters()))

            self.showSimilarityFrame(selected_sasms)

        elif id == self.MenuIDs['normalizedKratky']:
            manippage = wx.FindWindowByName('ManipulationPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the Manipulation control panel is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return

            selected_items = manippage.getSelectedItems()
            if selected_items:
                selected_sasms = [item.getSASM() for item in selected_items]
            else:
                selected_sasms = []

            self.showNormKratkyFrame(selected_sasms)

        elif id == self.MenuIDs['rundenss']:
            manippage = wx.FindWindowByName('IFTPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)
            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the IFT window is selected.', 'Select IFT Window', style = wx.ICON_INFORMATION)
                return

            if len(manippage.getSelectedItems()) > 0:
                iftm = manippage.getSelectedItems()[0].getIFTM()
                self.showDenssFrame(iftm, manippage.getSelectedItems()[0])
            else:
                wx.MessageBox("Please select an IFT from the list on the IFT page.", "No IFT selected")

        elif id == self.MenuIDs['calcUVconc']:
            manippage = wx.FindWindowByName('ManipulationPanel')

            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page !=manippage:
                wx.MessageBox('The selected operation cannot be performed unless the Manipulation control panel is selected.', 'Select Manipulation Window', style = wx.ICON_INFORMATION)
                return
            
            selected_items = manippage.getSelectedItems()
            marked_item = manippage.getBackgroundItem()    
            
            if marked_item == None:
                wx.MessageBox('The background file needs to be selected by clicking the star icon.', 'Select background first', style = wx.ICON_INFORMATION)
                return
            else:
                try:
                    selected_items.pop(selected_items.index(marked_item))
                except ValueError:
                    pass
                
            if selected_items:
                selected_sasms = [item.getSASM() for item in selected_items]
            else:
                wx.MessageBox('No items were selected. For unsubtracted files you need to select at least a background and a sample.', 'No selected items', style = wx.ICON_INFORMATION)
                return
                #selected_sasms = []             
            
            for each in selected_sasms + [marked_item.getSASM()]:
                if not each.getParameter('analysis').has_key('uvvis'):
                    wx.MessageBox('The file ' + str(each.getParameter('filename')) + ' does not have UV-VIS data stored in the header', 'UV-VIS data not found', style = wx.ICON_EXCLAMATION)
                    return
                print each.getParameter('analysis')['uvvis']
                
            dlg = RAWAnalysis.UVConcentrationDialog(self, 'Concentration from UV transmission', selected_sasms, marked_item.getSASM())
            retval = dlg.ShowModal()
            #ret, logbin = dlg.getValues()
            dlg.Destroy()

    def _onViewMenu(self, evt):

        val = evt.GetId()

        if val == self.MenuIDs['showimage']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            if len(selected_items) !=1:
                wx.MessageBox('Please select one (and only one) item to view the image.', 'Select Item', style = wx.ICON_INFORMATION)
                return

            if not selected_items[0].sasm.getAllParameters().has_key('load_path'):
                wx.MessageBox('The image associated with the data could not be found.', 'Image Not Found', style = wx.ICON_INFORMATION)
                return

            selected_items[0]._onShowImage()


        elif val == self.MenuIDs['showdata']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel') and page != wx.FindWindowByName('IFTPanel') and page != wx.FindWindowByName('SECPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation or IFT window is selected.', 'Select Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            if len(selected_items) !=1:
                wx.MessageBox('Please select one (and only one) item to view the data.', 'Select Item', style = wx.ICON_INFORMATION)
                return
            if page == wx.FindWindowByName('SECPanel'):
                dlg = RAWCustomDialogs.SeriesDataDialog(self, selected_items[0].secm)
            elif page == wx.FindWindowByName('IFTPanel'):
                dlg = RAWCustomDialogs.IFTDataDialog(self, selected_items[0].iftm)
            else:
                dlg = RAWCustomDialogs.DataDialog(self, selected_items[0].sasm)
            dlg.ShowModal()
            dlg.Destroy()

        elif val == self.MenuIDs['showheader']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            if len(selected_items) !=1:
                wx.MessageBox('Please select one (and only one) item to view the data.', 'Select Item', style = wx.ICON_INFORMATION)
                return

            dlg = RAWCustomDialogs.HdrDataDialog(self, selected_items[0].sasm)
            dlg.ShowModal()
            dlg.Destroy()

        elif val == self.MenuIDs['showhistory']:
            current_page = self.control_notebook.GetSelection()
            page = self.control_notebook.GetPage(current_page)

            if page != wx.FindWindowByName('ManipulationPanel'):
                wx.MessageBox('The selected operation cannot be performed unless the manipulation window is selected.', 'Select Window', style = wx.ICON_INFORMATION)
                return

            selected_items = page.getSelectedItems()
            if len(selected_items) !=1:
                wx.MessageBox('Please select one (and only one) item to view the history.', 'Select Item', style = wx.ICON_INFORMATION)
                return

            dlg = RAWCustomDialogs.HistoryDialog(self, selected_items[0].sasm)
            dlg.ShowModal()
            dlg.Destroy()

        else:
            key = [k for k, v in self.MenuIDs.iteritems() if v == val][0]

            plotpanel = wx.FindWindowByName('PlotPanel')
            secplotpanel = wx.FindWindowByName('SECPlotPanel')

            if key[0:7] == 'plot2sc':
                plotpanel.plotparams['axesscale2'] = key[-6:]
                plotpanel.plotparams['plot2type'] = 'subtracted'

                plotpanel.updatePlotType(plotpanel.subplot2)
                plotpanel.updatePlotAxes()

            elif key[0:7] == 'plot1sc':
                plotpanel.plotparams['axesscale1'] = key[-6:]
                plotpanel.plotparams['plot1type'] = 'normal'

                plotpanel.updatePlotType(plotpanel.subplot1)
                plotpanel.updatePlotAxes()

            elif key[0:7] == 'plot1ty':
                plotpanel.plotparams['plot1type'] = key[7:]
                if key[7:] == 'guinier':
                    plotpanel.plotparams['axesscale1'] = 'loglin'
                elif key[7:] == 'kratky' or key[7:] == 'porod':
                    plotpanel.plotparams['axesscale1'] = 'linlin'

                plotpanel.updatePlotType(plotpanel.subplot1)
                plotpanel.updatePlotAxes()


            elif key[0:7] == 'plot2ty':
                plotpanel.plotparams['plot2type'] = key[7:]
                if key[7:] == 'guinier':
                    plotpanel.plotparams['axesscale2'] = 'loglin'
                elif key[7:] == 'kratky' or key[7:] == 'porod':
                    plotpanel.plotparams['axesscale2'] = 'linlin'

                plotpanel.updatePlotType(plotpanel.subplot2)
                plotpanel.updatePlotAxes()

            elif key == 'secplottotal':
                secplotpanel.plotparams['y_axis_display'] = 'total'
                secplotpanel.updatePlotData()

            elif key == 'secplotmean':
                secplotpanel.plotparams['y_axis_display'] = 'mean'
                secplotpanel.updatePlotData()

            elif key == 'secplotq':
                secplotpanel.plotparams['y_axis_display'] = 'q_val'
                secplotpanel._getQValue()
                secplotpanel.updatePlotData()

            elif key == 'secplotqr':
                secplotpanel.plotparams['y_axis_display'] = 'q_range'
                secplotpanel._getQRange()
                secplotpanel.updatePlotData()

            elif key == 'secplotframe':
                secplotpanel.plotparams['x_axis_display'] = 'frame'
                secplotpanel.updatePlotData()
            elif key == 'secplottime':
                secplotpanel.plotparams['x_axis_display'] = 'time'
                secplotpanel.updatePlotData()

            elif key == 'secplotrg':
                secplotpanel.plotparams['secm_plot_calc'] = 'RG'
                raxis_on = secplotpanel.plotparams['framestyle1'].find('r')
                if raxis_on>-1:
                    secplotpanel.plotparams['framestyle1'] = secplotpanel.plotparams['framestyle1'].replace('r','')
                    secplotpanel.plotparams['framestyle2'] = secplotpanel.plotparams['framestyle2']+'r'
                    secplotpanel._updateFrameStylesForAllPlots()
                secplotpanel.updatePlotData()

            elif key == 'secplotmw':
                secplotpanel.plotparams['secm_plot_calc'] = 'MW'
                raxis_on = secplotpanel.plotparams['framestyle1'].find('r')
                if raxis_on>-1:
                    secplotpanel.plotparams['framestyle1'] = secplotpanel.plotparams['framestyle1'].replace('r','')
                    secplotpanel.plotparams['framestyle2'] = secplotpanel.plotparams['framestyle2']+'r'
                    secplotpanel._updateFrameStylesForAllPlots()
                secplotpanel.updatePlotData()

            elif key == 'secploti0':
                secplotpanel.plotparams['secm_plot_calc'] = 'I0'
                raxis_on = secplotpanel.plotparams['framestyle1'].find('r')
                if raxis_on>-1:
                    secplotpanel.plotparams['framestyle1'] = secplotpanel.plotparams['framestyle1'].replace('r','')
                    secplotpanel.plotparams['framestyle2'] = secplotpanel.plotparams['framestyle2']+'r'
                    secplotpanel._updateFrameStylesForAllPlots()
                secplotpanel.updatePlotData()

            elif key == 'secplotnone':
                secplotpanel.plotparams['secm_plot_calc'] = 'None'
                secplotpanel.updatePlotData()

            elif key == 'secplotunsub':
                secplotpanel.plotparams['plot_intensity'] = 'unsub'
                secplotpanel.updatePlotData()

            elif key == 'secplotunsub':
                secplotpanel.plotparams['plot_intensity'] = 'unsub'
                secplotpanel.updatePlotData()

            elif key == 'secplotsub':
                secplotpanel.plotparams['plot_intensity'] = 'sub'
                secplotpanel.updatePlotData()

            elif key == 'secplotbaseline':
                secplotpanel.plotparams['plot_intensity'] = 'baseline'
                secplotpanel.updatePlotData()



    def _onSaveMenu(self, event):
        self._onSaveSettings(None)

    def _onOnlineMenu(self, event):

        id = event.GetId()
#
        if id == self.MenuIDs['goOnline']:
            is_online = self.OnlineControl.goOnline()

            if is_online:
                self.setStatus('Mode: ONLINE', 2)
            else:
                menubar = self.GetMenuBar()
                item = menubar.FindItemById(self.MenuIDs['goOffline'])
                item.Check(True)

        elif id == self.MenuIDs['goOffline']:
            self.setStatus('Mode: OFFLINE', 2)
            self.OnlineControl.goOffline()

        elif id == self.MenuIDs['changeOnline']:
            result = self.OnlineControl.changeOnline()

            if result == False:
                wx.MessageBox('Could not change online directory. Online mode must be active to change the directory.', 'Change directory failed', style = wx.ICON_INFORMATION | wx.OK)


    def _onOptionsMenu(self, event):

        if event.GetId() == self.MenuIDs['advancedOptions']:
            self.showOptionsDialog()

    def _onFileMenu(self, event):

        if event.GetId() == self.MenuIDs['exit'] or event.GetId() == wx.ID_EXIT:
            self.Close()

    def _onLoadMenu(self, event):
        self._onLoadSettings(None)

    def _onLoadSettings(self, evt):

        file = self._createFileDialog(wx.FD_OPEN)

        if file:
            success = RAWSettings.loadSettings(self.raw_settings, file)

            if success:
                self.raw_settings.set('CurrentCfg', file)

            else:
                wx.CallAfter(wx.MessageBox,'Load failed, config file might be corrupted.',
                              'Load failed', style = wx.ICON_ERROR| wx.OK)


    def _onSaveSettings(self, evt):
        file = self._createFileDialog(wx.FD_SAVE)

        if file:

            if os.path.splitext(file)[1] != '.cfg':
                file = file + '.cfg'

            success = RAWSettings.saveSettings(self.raw_settings, file)

            if success:
                self.raw_settings.set('CurrentCfg', file)

            else:
                wx.MessageBox('Your settings failed to save! Please try again.', 'Save failed!', style = wx.ICON_ERROR | wx.OK)

    def _onLoadWorkspaceMenu(self, evt):
        file = self._createFileDialog(wx.FD_OPEN, 'Workspace files', '*.wsp')

        if file:
            if os.path.splitext(file)[1] != '.wsp':
                file = file + '.wsp'

            mainworker_cmd_queue.put(['load_workspace', [file]])

    def _onSaveWorkspaceMenu(self, evt):
        self.saveWorkspace()

    def saveWorkspace(self):

        manip_panel = wx.FindWindowByName('ManipulationPanel')
        ift_panel = wx.FindWindowByName('IFTPanel')
        sec_panel = wx.FindWindowByName('SECPanel')

        sasm_items = manip_panel.getItems()
        ift_items = ift_panel.getItems()
        secm_items = sec_panel.getItems()

        file = self._createFileDialog(wx.FD_SAVE, 'Workspace files', '*.wsp')

        if file:
            if os.path.splitext(file)[1] != '.wsp':
                file = file + '.wsp'

            mainworker_cmd_queue.put(['save_workspace', [sasm_items, ift_items, secm_items, file]])


    def showOptionsDialog(self, focusHead = None):

        if focusHead != None:
            dialog = RAWOptions.OptionsDialog(self, self.raw_settings, focusHeader = focusHead)
        else:

            dialog = RAWOptions.OptionsDialog(self, self.raw_settings)

        dialog.ShowModal()

    def getMenuIds(self):
        return self.MenuIDs

    def setStatus(self, statustxt, idx):

        self.statusbar.SetStatusText(statustxt,idx)

    def setViewMenuScale(self, my_id):
        self.MenuBar.FindItemById(my_id).Check(True)

    def _onAboutDlg(self, event):
        info = AboutDialogInfo()
        info.SetName("RAW")
        info.SetVersion(RAWGlobals.version)
        info.SetCopyright("Copyright(C) 2009 RAW")
        info.SetDescription(('RAW is a software package primarily for SAXS 2D data '
                            'reduction and 1D data analysis.\nIt provides an easy '
                            'GUI for handling multiple files fast, and a\ngood '
                            'alternative to commercial or protected software packages\n\n'
                            'Please cite:\n"BioXTAS RAW: improvements to a free open-source program for\n'
                            'small-angle X-ray scattering data reduction and analysis."\n'
                            'J. B. Hopkins, R. E. Gillilan, and S. Skou. Journal of Applied\n'
                            'Crystallography (2017). 50, 1545-1553'))

        info.SetWebSite("http://bioxtas-raw.readthedocs.io/", "The RAW Project Homepage")
        info.SetDevelopers([u"Soren Skou", u"Jesse B. Hopkins", u"Richard E. Gillilan", u"Jesper Nygaard"])
        info.SetLicense(('This program is free software: you can redistribute it '
                        'and/or modify it under the terms of the\nGNU General '
                        'Public License as published by the Free Software '
                        'Foundation, either version 3\n of the License, or (at '
                        'your option) any later version.\n\nThis program is '
                        'distributed in the hope that it will be useful, but '
                        'WITHOUT ANY WARRANTY;\nwithout even the implied warranty '
                        'of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n'
                        'See the GNU General Public License for more details.\n\n'
                        'You should have received a copy of the GNU General Public '
                        'License along with this program.\nIf not, see '
                        'http://www.gnu.org/licenses/'))

        # Show the wx.AboutBox
        AboutBox(info)

    def saveBackupData(self):
        file = os.path.join(RAWGlobals.RAWWorkDir,'backup.ini')

        try:
            file_obj = open(file, 'w')

            path = wx.FindWindowByName('FileListCtrl').path
            save_info = {'workdir' : path}

            cPickle.dump(save_info, file_obj)
            file_obj.close()
        except Exception, e:
            print e

    def _onCloseWindow(self, event):

        if event.CanVeto():
            manipulation_panel = wx.FindWindowByName('ManipulationPanel')
            sec_panel = wx.FindWindowByName('SECPanel')

            exit_without_saving = wx.ID_YES

            if manipulation_panel.modified_items != [] or sec_panel.modified_items != []:

                if manipulation_panel.modified_items !=[] and sec_panel.modified_items != []:
                    message = 'manipulation and series '
                elif manipulation_panel.modified_items !=[] and sec_panel.modified_items == []:
                    message = 'manipulation '
                else:
                    message = 'series '

                dial2 = wx.MessageDialog(self, 'You have unsaved changes in your ' + message + 'data. Do you want to discard these changes?', 'Discard changes?',
                                         wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
                exit_without_saving = dial2.ShowModal()
                dial2.Destroy()

            if exit_without_saving == wx.ID_YES:
                dammif_window = wx.FindWindowByName('DammifFrame')
                dammif_closed = True
                if dammif_window != None:
                    dammif_closed = dammif_window.Close()
            else:
                event.Veto()
                return

            if exit_without_saving == wx.ID_YES and dammif_closed:
                denss_window = wx.FindWindowByName('DenssFrame')
                denss_closed = True
                if denss_window != None:
                    denss_closed = denss_window.Close()
            else:
                event.Veto()
                return

            if exit_without_saving == wx.ID_YES and dammif_closed and denss_closed:
                force_quit = wx.ID_YES
                if RAWGlobals.save_in_progress:
                    dial = wx.MessageDialog(self, 'RAW is currently saving one or more files. Do you want to force quit (may corrupt files being saved)?', 'Force quit?',
                                         wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
                    force_quit = dial.ShowModal()
                    dial.Destroy()
            else:
                event.Veto()
                return

            if exit_without_saving == wx.ID_YES and dammif_closed and denss_closed and force_quit == wx.ID_YES:
                self.saveBackupData()
                self.tbIcon.RemoveIcon()
                self.tbIcon.Destroy()
                self.Destroy()
            else:
                event.Veto()
                return

        else:
            self.saveBackupData()
            self.tbIcon.RemoveIcon()
            self.tbIcon.Destroy()
            self.Destroy()

    def _createFileDialog(self, mode, name = 'Config files', ext = '*.cfg'):

        f = None

        path = wx.FindWindowByName('FileListCtrl').path

        if mode == wx.FD_OPEN:
            filters = name + ' (' + ext + ')|' + ext + '|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters, defaultDir = path)
        if mode == wx.FD_SAVE:
            filters = name + ' ('+ext+')|'+ext
            dialog = wx.FileDialog( None, style = mode | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = path)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            f = dialog.GetPath()

        # Destroy the dialog
        dialog.Destroy()

        return f

    def controlTimer(self, state):
        if state:
            self.OnlineControl.startTimer()
        else:
            self.OnlineControl.stopTimer()

    def onControlTabChange(self, evt):
        page = self.control_notebook.GetPageText(evt.GetSelection())

        if page == 'IFT' or page == 'Series':
            self.info_panel.clearInfo()

        elif page == 'Manipulation':
            manip = wx.FindWindowByName('ManipulationPanel')
            selected_items = manip.getSelectedItems()

            if len(selected_items) > 0:
                self.info_panel.updateInfoFromItem(selected_items[0])

        elif page == 'Files':
            file_panel = wx.FindWindowByName('FilePanel')
            file_panel.dir_panel.refresh()



class OnlineController(object):
    def __init__(self, parent, raw_settings):

        self.parent = parent

        self.main_frame = parent

        self._raw_settings = raw_settings

        # self.update_keys = ['OnlineFilterList', 'EnableOnlineFiltering']

        self._filt_list=self._raw_settings.get('OnlineFilterList')
        self._enable_filt=self._raw_settings.get('EnableOnlineFiltering')

        # Setup the online file checker timer
        self.online_timer = wx.Timer()

        self.online_timer.Bind(wx.EVT_TIMER, self.onOnlineTimer)

        self.old_dir_list_dict = {}
        self.is_online = False
        self.seek_dir = []
        self.bg_filename = None

        if self._raw_settings.get('OnlineModeOnStartup') and os.path.isdir(self._raw_settings.get('OnlineStartupDir')):
            path = self._raw_settings.get('OnlineStarupDir')

            if path != None:
                self.seek_dir = path
                self.goOnline()
                self.main_frame.setStatus('Mode: ONLINE', 2)

                menubar = self.main_frame.GetMenuBar()
                item = menubar.FindItemById(self.main_frame.MenuIDs['goOnline'])
                item.Check(True)


    def selectSearchDir(self):
        self.dirctrl = wx.FindWindowByName('DirCtrlPanel')

        found_path = False

        if self.seek_dir == []:
            start_dir = str(self.dirctrl.getDirLabel())
        else:
            start_dir = self.seek_dir

        dirdlg = wx.DirDialog(self.parent, "Please select search directory:", str(start_dir))

        if dirdlg.ShowModal() == wx.ID_OK:
            self.seek_dir = dirdlg.GetPath()
            found_path = True

        return found_path

    def changeOnline(self):
        if self.isRunning():
            found_path = self.selectSearchDir()

            if found_path != None:
                dir_list = os.listdir(self.seek_dir)

                dir_list_dict = {}
                for each_file in dir_list:
                    dir_list_dict[each_file] = (os.path.getmtime(os.path.join(self.seek_dir, each_file)),os.path.getsize(os.path.join(self.seek_dir, each_file)))

                self.old_dir_list_dict = dir_list_dict

                return True

        return False

    def goOnline(self):

        if self.seek_dir == []:
            found_path = self.selectSearchDir()
        else:
            found_path = True

        if found_path:
            dir_list = os.listdir(self.seek_dir)

            dir_list_dict = {}
            for each_file in dir_list:
                dir_list_dict[each_file] = (os.path.getmtime(os.path.join(self.seek_dir, each_file)), os.path.getsize(os.path.join(self.seek_dir, each_file)))

            self.old_dir_list_dict = dir_list_dict

            self.online_timer.Start(2000)
            return True

        return False

    def goOffline(self):
        self.main_frame.setStatus('', 0)

        return self.online_timer.Stop()

    def startTimer(self):
        return self.online_timer.Start(2000)

    def stopTimer(self):
        return self.online_timer.Stop()

    def isRunning(self):
        return self.online_timer.IsRunning()

    def getTargetDir(self):
        return self.seek_dir

    def onOnlineTimer(self, evt):
        ''' This function checks for new files and processes them as they come in '''
        self._filt_list=self._raw_settings.get('OnlineFilterList')
        self._enable_filt=self._raw_settings.get('EnableOnlineFiltering')

        self.file_list_ctrl = wx.FindWindowByName('FileListCtrl')

        self.main_frame.setStatus('', 0)

        if not os.path.exists(self.seek_dir):
            self.seek_dir = []

            question = "Warning: the online mode directory does not exist.\nWhat do you want to do?"
            button_list = [('Change Directory', wx.Window.NewControlId()),('Go Offline', wx.Window.NewControlId())]
            label = "Missing Directory"
            icon = wx.ART_WARNING

            question_dialog = RAWCustomDialogs.CustomQuestionDialog(self.main_frame, question, button_list, label, icon, None, None, style = wx.CAPTION | wx.RESIZE_BORDER)
            result = question_dialog.ShowModal()
            question_dialog.Destroy()

            if result == button_list[0][1]:
                success = self.changeOnline()
                if not success:
                    self.goOffline()
                    self.main_frame.setStatus('Mode: OFFLINE', 2)
                    menubar = self.main_frame.GetMenuBar()
                    item = menubar.FindItemById(self.main_frame.MenuIDs['goOffline'])
                    item.Check(True)
            else:
                self.goOffline()
                self.main_frame.setStatus('Mode: OFFLINE', 2)
                menubar = self.main_frame.GetMenuBar()
                item = menubar.FindItemById(self.main_frame.MenuIDs['goOffline'])
                item.Check(True)
                return

        dir_list = os.listdir(self.seek_dir)

        dir_list_dict = {}

        for each_file in dir_list:
            try:
                dir_list_dict[each_file] = (os.path.getmtime(os.path.join(self.seek_dir, each_file)), os.path.getsize(os.path.join(self.seek_dir, each_file)))
            except OSError:
                pass

        diff_list = list(set(dir_list_dict.items()) - set(self.old_dir_list_dict.items()))
        diff_list.sort(key = lambda name: name[0])

        files_to_plot=[]

        if diff_list != []:
            if not self._enable_filt:

                for each in diff_list:
                    each_newfile = each[0]

                    process_str = 'Processing incomming file: ' + str(each_newfile)
                    self.main_frame.setStatus(process_str, 0)

                    filepath = os.path.join(self.seek_dir, str(each_newfile))

                    if self._fileTypeIsCompatible(filepath):

                        if each_newfile in self.old_dir_list_dict:
                            #ONLY UPDATE IMAGE
                            mainworker_cmd_queue.put(['online_mode_update_data', [filepath]])
                            print 'Changed: ' + str(each_newfile)
                        else:
                            print process_str
                            files_to_plot.append(filepath)
                            # mainworker_cmd_queue.put(['plot', [filepath]])
                            #UPDATE PLOT

            else:
                for each in diff_list:
                    load=True
                    each_newfile = each[0]

                    for item in self._filt_list:
                        if item[0]=='Ignore':
                            if item[2]=='At start':
                                if each_newfile.startswith(item[1]):
                                    load=False
                            elif item[2]=='Anywhere':
                                if each_newfile.find(item[1])!=-1:
                                    load=False
                            else:
                                if each_newfile.endswith(item[1]):
                                    load=False
                        else:
                            if item[2]=='At start':
                                if not each_newfile.startswith(item[1]):
                                    load=False
                            elif item[2]=='Anywhere':
                                if not each_newfile.find(item[1])!=-1:
                                    load=False
                            else:
                                if not each_newfile.endswith(item[1]):
                                    load=False

                    if load:
                        process_str = 'Processing incomming file: ' + str(each_newfile)
                        self.main_frame.setStatus(process_str, 0)

                        filepath = os.path.join(self.seek_dir, str(each_newfile))

                        if self._fileTypeIsCompatible(filepath):

                            if each_newfile in self.old_dir_list_dict:
                                if each[1][1] == self.old_dir_list_dict[each_newfile][1]:
                                    #If the size is the same, ONLY UPDATE IMAGE
                                    mainworker_cmd_queue.put(['online_mode_update_data', [filepath]])
                                    print 'Changed: ' + str(each_newfile)
                                else:
                                    print process_str
                                    files_to_plot.append(filepath)
                            else:
                                print process_str
                                files_to_plot.append(filepath)
                                # mainworker_cmd_queue.put(['plot', [filepath]])
                                #UPDATE PLOT
                    else:
                        print 'Ignored: '+str(each_newfile)

            if len(files_to_plot) > 0:
                mainworker_cmd_queue.put(['plot', files_to_plot])

            self.old_dir_list_dict.update(diff_list)


    def _fileTypeIsCompatible(self, path):
        root, ext = os.path.splitext(path)
        compatible_formats = self.main_frame.getRawSettings().get('CompatibleFormats')

        if str(ext) in compatible_formats:
            return True
        else:
            print 'Not compatible file format.'
            return False

    def updateSkipList(self, file_list):
        dir_list_dict = {}

        for each_file in file_list:
            dir_list_dict[each_file] = (os.path.getmtime(os.path.join(self.seek_dir, each_file)), os.path.getsize(os.path.join(self.seek_dir, each_file)))

        diff_list = list(set(dir_list_dict.items()) - set(self.old_dir_list_dict.items()))
        diff_list.sort(key = lambda name: name[0])

        self.old_dir_list_dict.update(diff_list)

class OnlineSECController(object):
    def __init__(self, parent, raw_settings):

        self.parent = parent

        self.main_frame = parent

        self._raw_settings = raw_settings

        self.online_timer = wx.Timer()

        self.online_timer.Bind(wx.EVT_TIMER, self.onOnlineTimer)

    def goOnline(self):
        self.sec_control_panel = wx.FindWindowByName('SECControlPanel')
        self.online_timer.Start(1000)

    def goOffline(self):
        self.online_timer.Stop()

    def onOnlineTimer(self, evt):
        self.sec_control_panel.onUpdate()



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
        self.dir_panel = wx.FindWindowByName('DirCtrlPanel')


        self.sec_plot_panel = wx.FindWindowByName('SECPlotPanel')
        self.sec_item_panel = wx.FindWindowByName('SECPanel')
        self.sec_control_panel = wx.FindWindowByName('SECControlPanel')


        self.ift_plot_panel = wx.FindWindowByName('IFTPlotPanel')
        self.ift_item_panel = wx.FindWindowByName('IFTPanel')

        self._commands = {'plot'                        : self._loadAndPlot,
                        'online_mode_update_data'       : self._onlineModeUpdate,
                        'show_nextprev_img'             : self._loadAndShowNextImage,
                        'show_image'                    : self._loadAndShowImage,
                        'subtract_filenames'            : self._subtractFilenames,
                        'subtract_items'                : self._subtractItems,
                        'average_items'                 : self._averageItems,
                        'save_items'                    : self._saveItems,
                        'save_iftitems'                 : self._saveIftItems,
                        'quick_reduce'                  : self._quickReduce,
                        'load_mask'                     : self._loadMaskFile,
                        'save_mask'                     : self._saveMaskFile,
                        'create_mask'                   : self._createMask,
                        'recreate_all_masks'            : self._recreateAllMasks,
                        'calculate_abs_water_const'     : self._calcAbsScWaterConst,
                        'save_workspace'                : self._saveWorkspace,
                        'load_workspace'                : self._loadWorkspace,
                        'superimpose_items'             : self._superimposeItems,
                        'save_analysis_info'            : self._saveAnalysisInfo,
                        'save_all_analysis_info'        : self._saveAllAnalysisInfo,
                        'merge_items'                   : self._mergeItems,
                        'rebin_items'                   : self._rebinItems,
                        'ift'                           : self._runIft,
                        'interpolate_items'             : self._interpolateItems,
                        'plot_iftfit'                   : self._plotIftFit,
                        'normalize_conc'                : self._normalizeByConc,
                        'sec_plot'                      : self._loadAndPlotSEC,
                        'update_secm'                   : self._updateSECM,
                        'to_plot'                       : self._sendSASMToPlot,
                        'to_plot_ift'                   : self._plotIFTM,
                        'to_plot_SEC'                   : self._sendSASMToPlotSEC,
                        'save_sec_data'                 : self._saveSeriesData,
                        'save_sec_item'                 : self._saveSECItem,
                        'save_sec_profiles'             : self._saveSECProfiles,
                        # 'calculate_params_sec'          : self._calculateSECParams, #Maybe can remove?
                        'save_iftm'                     : self._saveIFTM,
                        'to_plot_sasm'                  : self._plotSASM,
                        'secm_average_sasms'            : self._averageItemSeries,
                        'weighted_average_items'        : self._weightedAverageItems,
                        'calculate_abs_carbon_const'    : self._calcAbsScCarbonConst,
                        'plot_specific'                 : self._loadAndPlotWrapper,
                        'update_secm_plot'              : self._updateSECMPlot,
                        }


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


    def _onlineModeUpdate(self, data):
        filename = data[0]

        try:
            if not os.path.isfile(filename):
                raise SASExceptions.WrongImageFormat('not a valid file!')

            img, imghdr = SASFileIO.loadImage(filename, self._raw_settings)

            if img[-1] == None:
                raise SASExceptions.WrongImageFormat('not a valid file!')

        except Exception, e:
            print  'File load failed: ' + str(e)
            return

        parameters = {'filename' : os.path.split(filename)[1],
                      'imageHeader' : imghdr[-1]}

        bogus_sasm = SASM.SASM([0,1], [0,1], [0,1], parameters)

        self._sendImageToDisplay(img, bogus_sasm)


    def _sendIFTMToPlot(self, iftm, item_colour = 'black', line_color = None, no_update = False, update_legend = False, notsaved = False):
        wx.CallAfter(self.ift_plot_panel.plotIFTM, iftm)
        wx.CallAfter(self.ift_item_panel.addItem, iftm, item_colour, notsaved = notsaved)

        if update_legend:
            wx.CallAfter(self.ift_plot_panel.updateLegend, 1, False)
            wx.CallAfter(self.ift_plot_panel.updateLegend, 2, False)

        if no_update == False:
            wx.CallAfter(self.ift_plot_panel.fitAxis)


    def _sendSASMToPlot(self, sasm, axes_num = 1, item_colour = 'black', line_color = None, no_update = False, notsaved = False, update_legend = True):

        wx.CallAfter(self.plot_panel.plotSASM, sasm, axes_num, color = line_color)
        wx.CallAfter(self.manipulation_panel.addItem, sasm, item_colour, notsaved = notsaved)

        if update_legend:
            wx.CallAfter(self.plot_panel.updateLegend, axes_num, False)

        if not no_update:
            wx.CallAfter(self.plot_panel.fitAxis)


    def _sendSASMToPlotSEC(self, sasm, axes_num = 1, item_colour = 'black', line_color = None, no_update = False, notsaved = False, update_legend = True):
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while plotting frames...')

        wx.CallAfter(self.plot_panel.plotSASM, sasm, axes_num, color = line_color)
        wx.CallAfter(self.manipulation_panel.addItem, sasm, item_colour, notsaved = notsaved)

        if update_legend:
            wx.CallAfter(self.plot_panel.updateLegend, axes_num, False)

        if not no_update:
            wx.CallAfter(self.plot_panel.fitAxis)

        wx.CallAfter(self.main_frame.closeBusyDialog)


    def _sendSECMToPlot(self, secm, item_colour = 'black', line_color = None, no_update = False, notsaved = False, update_legend = True):

        wx.CallAfter(self.sec_plot_panel.plotSECM, secm, color = line_color)
        wx.CallAfter(self.sec_item_panel.addItem, secm, item_colour, notsaved = notsaved)

        if update_legend:
            wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)

        if not no_update:
            wx.CallAfter(self.sec_plot_panel.fitAxis)


    def _updateSECMPlot(self, secm, item_colour = 'black', line_color = None, no_update = False, notsaved = False):
        if isinstance(secm, list):
            wx.CallAfter(self.sec_plot_panel.updatePlotData, secm, draw=False)

        else:
            secm_list=[secm]
            wx.CallAfter(self.sec_plot_panel.updatePlotData, secm_list, draw=False)

        wx.CallAfter(self.sec_plot_panel.updateLegend, 1, draw = False)

        if not no_update:
            wx.CallAfter(self.sec_plot_panel.fitAxis)


    def _sendImageToDisplay(self, img, sasm, fnum=0):
        wx.CallAfter(self.image_panel.showImage, img, sasm, fnum)

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
        except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat):
            wx.CallAfter(self._showDataFormatError, os.path.split(filename)[1])
            wx.CallAfter(self.main_frame.closeBusyDialog)
            question_return_queue.put(None)
            return

        if isinstance(water_sasm, list):
            if len(water_sasm) == 1:
                water_sasm = water_sasm[0]
            else:
                water_sasm = SASProc.average(water_sasm)

        if isinstance(empty_sasm, list):
            if len(empty_sasm) == 1:
                empty_sasm = empty_sasm[0]
            else:
                empty_sasm = SASProc.average(empty_sasm)
        try:
            abs_scale_constant = SASM.calcAbsoluteScaleWaterConst(water_sasm, empty_sasm, waterI0, self._raw_settings)
        except SASExceptions.DataNotCompatible:
            wx.CallAfter(self.main_frame.closeBusyDialog)
            wx.CallAfter(self._showSubtractionError, water_sasm, empty_sasm)
            question_return_queue.put(None)
            return

        wx.CallAfter(self.main_frame.closeBusyDialog)
        question_return_queue.put(abs_scale_constant)
        return

    def _calcAbsScCarbonConst(self, data):
        ignore_bkg = data['ignore_background']
        carbon_file = data['carbon_file']
        carbon_cal_file = data['carbon_cal_file']
        carbon_bkg_file = data['carbon_bkg_file']
        carbon_thickness = data['carbon_thickness']
        ctr_ups = data['ctr_upstream']
        ctr_dns = data['ctr_downstream']

        if carbon_cal_file is not None and carbon_cal_file != 'None':
            try:
                cal_q, cal_i, cal_err = np.loadtxt(carbon_cal_file, unpack=True)
            except Exception:
                try:
                    cal_q, cal_i, cal_err = np.loadtxt(carbon_cal_file, unpack=True, delimiter=',')
                except Exception:
                    cal_q = RAWSettings.glassy_carbon_cal[0]
                    cal_i = RAWSettings.glassy_carbon_cal[1]
                    cal_err = RAWSettings.glassy_carbon_cal[2]
                    msg = ('Cannot read data in selected calibration file, will'
                        ' use default calibration curve instead.')
                    wx.CallAfter(self._showGenericError, msg, 'Invalid Calibration File')
        else:
            cal_q = RAWSettings.glassy_carbon_cal[0]
            cal_i = RAWSettings.glassy_carbon_cal[1]
            cal_err = RAWSettings.glassy_carbon_cal[2]


        if ignore_bkg:
            try:
                carbon_sasm, img = SASFileIO.loadFile(carbon_file, self._raw_settings, no_processing=True)
            except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat):
                wx.CallAfter(self._showDataFormatError, os.path.split(carbon_file)[1])
                question_return_queue.put(None)
                return

            if isinstance(carbon_sasm, list):
                if len(carbon_sasm) == 1:
                    carbon_sasm = carbon_sasm[0]
                else:
                    carbon_sasm = SASProc.average(carbon_sasm)

            carbon_ctr_ups_val = -1
            carbon_ctr_dns_val = -1
            bkg_ctr_ups_val = -1
            bkg_ctr_dns_val = -1
            bkg_sasm = None

        else:
            try:
                carbon_sasm, img = SASFileIO.loadFile(carbon_file, self._raw_settings, no_processing=True)
                bkg_sasm, img = SASFileIO.loadFile(carbon_bkg_file, self._raw_settings, no_processing=True)
            except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat):
                wx.CallAfter(self._showDataFormatError, os.path.split(carbon_file)[1] + ' or ' + os.path.split(carbon_bkg_file)[1])
                question_return_queue.put(None)
                return

            if isinstance(carbon_sasm, list):
                if len(carbon_sasm) == 1:
                    carbon_sasm = carbon_sasm[0]
                else:
                    carbon_sasm = SASProc.average(carbon_sasm)

            if isinstance(bkg_sasm, list):
                if len(bkg_sasm) == 1:
                    bkg_sasm = bkg_sasm[0]
                else:
                    bkg_sasm = SASProc.average(bkg_sasm)

            carbon_ctrs = carbon_sasm.getParameter('imageHeader')
            carbon_file_hdr = carbon_sasm.getParameter('counters')
            carbon_ctrs.update(carbon_file_hdr)

            bkg_ctrs = bkg_sasm.getParameter('imageHeader')
            bkg_file_hdr = bkg_sasm.getParameter('counters')
            bkg_ctrs.update(bkg_file_hdr)

            carbon_ctr_ups_val = float(carbon_ctrs[ctr_ups])
            carbon_ctr_dns_val = float(carbon_ctrs[ctr_dns])
            bkg_ctr_ups_val = float(bkg_ctrs[ctr_ups])
            bkg_ctr_dns_val = float(bkg_ctrs[ctr_dns])

        try:
            abs_scale_const = SASM.calcAbsoluteScaleCarbonConst(carbon_sasm, carbon_thickness,
                            self._raw_settings, cal_q, cal_i, cal_err, ignore_bkg, bkg_sasm,
                            carbon_ctr_ups_val, carbon_ctr_dns_val, bkg_ctr_ups_val,
                            bkg_ctr_dns_val)
        except SASExceptions.DataNotCompatible:
            wx.CallAfter(self._showSubtractionError, carbon_sasm, bkg_sasm)
            question_return_queue.put(None)
            return

        question_return_queue.put(abs_scale_const)

    def _runBIFT(self, sasm, bift_queue, parameters):
        ift_sasm = BIFT.doBift(sasm, bift_queue, *parameters)
        return ift_sasm

    def _runManualIft(self, sasm, parameters):
        dmax = parameters['dmax']
        alpha = parameters['alpha']

        ift_sasm = BIFT.SingleSolve(alpha, dmax, sasm, 50)
        return ift_sasm

    def _runGnomIft(self, data):
        pass

    def _runIft(self, data):
        algo = data[0]
        sasm = data[1]
        bift_queue = data[2]
        ift_parameters = data[3]

        if algo == 'BIFT':
            try:
                try:
                    ift_sasm = self._runBIFT(sasm, bift_queue, ift_parameters)
                    if ift_sasm != None:
                        bift_queue.put({'success' : True, 'results' : ift_sasm})
                except ValueError, e:
                    print 'Error in: ift_sasm = self._runBIFT(sasm, parameters)'
                    print e


            except UnboundLocalError, e:
                print 'doBift error: ', e

                bift_queue.put({'failed' : True})

        if algo == 'Manual':

            try:
                ift_sasm = self._runManualIft(sasm, ift_parameters)
            except ValueError, e:
                print 'doBift error: ', e

                bift_queue.put({'failed' : True})


    def _saveMaskFile(self, data):

        fullpath_filename = data[0]

        masks = data[1]

        path, ext = os.path.splitext(fullpath_filename)

        if ext != '.msk':
            fullpath_filename = fullpath_filename + '.msk'

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving mask', 0)

        with open(fullpath_filename, 'w') as file_obj:
            cPickle.dump(masks, file_obj)

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)


    def _loadMaskFile(self, data):
            wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading and creating mask...')

            fullpath_filename = data[0]

            filenamepath, extension = os.path.splitext(fullpath_filename)

            if extension == '.msk':
                with open(fullpath_filename, 'r') as file_obj:
                    masks = cPickle.load(file_obj)

                i=0
                for each in masks:
                    each.maskID = i
                    i = i + 1

                plot_param = self.image_panel.getPlotParameters()
                plot_param['storedMasks'].extend(masks)
                wx.CallAfter(self.image_panel.setPlotParameters, plot_param)

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
        wx.CallAfter(self._showGenericMsg, 'The mask has been created and enabled.', 'Mask creation finished')

    def _loadAndPlotWrapper(self, data):
        #In order to specify axes_num, but not break loadAndPlot everywhere, I have
        #to have a wrapper
        filename_list, axes_num = data

        self._loadAndPlot(filename_list, axes_num)

    def _loadAndPlot(self, filename_list, axes_num=1):
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while plotting...')

        loaded_secm = False
        loaded_sasm = False
        loaded_iftm = False

        do_auto_save = self._raw_settings.get('AutoSaveOnImageFiles')

        sasm_list = []
        iftm_list = []
        secm_list = []

        try:
            for i in range(len(filename_list)):
                each_filename = filename_list[i]
                file_ext = os.path.splitext(each_filename)[1]

                if file_ext == '.sec':
                    try:
                        secm = SASFileIO.loadSeriesFile(each_filename)
                    except Exception as e:
                        print e
                        wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1], include_sec = True)
                        wx.CallAfter(self.main_frame.closeBusyDialog)
                        return
                    secm_list.append(secm)

                    img = None
                    loaded_secm = True

                elif file_ext == '.ift' or file_ext == '.out':
                    iftm, img = SASFileIO.loadFile(each_filename, self._raw_settings)

                    if file_ext == '.ift':
                        item_colour = 'blue'
                    else:
                        item_colour = 'black'

                    if type(iftm) == list:
                        iftm_list.append(iftm[0])

                    loaded_iftm = True

                else:
                    sasm, img = SASFileIO.loadFile(each_filename, self._raw_settings)
                    loaded_sasm = True

                    if img is not None:
                        start_point = self._raw_settings.get('StartPoint')
                        end_point = self._raw_settings.get('EndPoint')

                        if not isinstance(sasm, list):
                            qrange = (start_point, len(sasm.getBinnedQ())-end_point)
                            sasm.setQrange(qrange)
                        else:
                            qrange = (start_point, len(sasm[0].getBinnedQ())-end_point)
                            for each_sasm in sasm:
                                each_sasm.setQrange(qrange)

                    if type(sasm) == list:
                        sasm_list.extend(sasm)
                    else:
                        sasm_list.append(sasm)

                    if do_auto_save:
                        save_path = self._raw_settings.get('ProcessedFilePath')

                        try:
                            self._saveSASM(sasm, '.dat', save_path)
                        except IOError, e:
                            self._raw_settings.set('AutoSaveOnImageFiles', False)
                            do_auto_save = False
                            msg = (str(e) + '\n\nAutosave of processed images '
                                'has been disabled. If you are using a config '
                                'file from a different computer please go into '
                                'Advanced Options/Autosave to change the save '
                                'folders, or save you config file to avoid this '
                                'message next time.')
                            wx.CallAfter(wx._showGenericError, msg, 'Autosave Error')

                if np.mod(i,20) == 0 and i != 0:
                    if i == 20:
                        no_update = False
                    else:
                        no_update = True

                    if loaded_sasm:
                        self._sendSASMToPlot(sasm_list, axes_num=axes_num, no_update=no_update, update_legend=False)
                        wx.CallAfter(self.plot_panel.canvas.draw_idle)
                    if loaded_secm:
                        self._sendSECMToPlot(secm_list, no_update=no_update, update_legend = False)
                        wx.CallAfter(self.sec_plot_panel.canvas.draw_idle)
                    if loaded_iftm:
                        self._sendIFTMToPlot(iftm_list, item_colour = item_colour, no_update=no_update, update_legend = False)
                        wx.CallAfter(self.ift_plot_panel.canvas.draw_idle)

                    sasm_list = []
                    iftm_list = []
                    secm_list = []

            if len(sasm_list) > 0:
                self._sendSASMToPlot(sasm_list, axes_num=axes_num, no_update=True, update_legend=False)

            if len(iftm_list) > 0:
                self._sendIFTMToPlot(iftm_list, item_colour = item_colour, no_update = True, update_legend = False)

            if len(secm_list) > 0:
                self._sendSECMToPlot(secm_list, no_update = True, update_legend = False)

        except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
            wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1])
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        except SASExceptions.HeaderLoadError, msg:
            wx.CallAfter(self._showHeaderError, msg)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        except SASExceptions.MaskSizeError, msg:
            wx.CallAfter(self._showGenericError, str(msg), 'Saved mask does not fit loaded image')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        except SASExceptions.HeaderMaskLoadError, msg:
            wx.CallAfter(self._showGenericError, str(msg), 'Mask information was not found in header')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        except SASExceptions.ImageLoadError, msg:
            wx.CallAfter(wx.MessageBox, "\n".join(msg.parameter), 'Image load error', style = wx.ICON_ERROR)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        except SASExceptions.AbsScaleNormFailed:
            msg = ('Failed to apply absolute scale. The most '
                    'likely cause is a mismatch between the q vector of the '
                    'loaded file and the selected sample background file. '
                    'It failed on the following file:\n')
            msg = msg + os.path.split(each_filename)[1]
            wx.CallAfter(self._showGenericError, msg, 'Absolute scale failed')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        if img is not None:
            self._sendImageToDisplay(img, sasm)

        if loaded_secm and not loaded_sasm and not loaded_iftm:
            wx.CallAfter(self.main_frame.plot_notebook.SetSelection, 3)
        elif loaded_iftm and not loaded_sasm:
            wx.CallAfter(self.main_frame.plot_notebook.SetSelection, 1)
        else:
            wx.CallAfter(self.main_frame.plot_notebook.SetSelection, 0)

        if loaded_sasm:
            wx.CallAfter(self.plot_panel.updateLegend, 1, False)
            wx.CallAfter(self.plot_panel.fitAxis)
        if loaded_secm:
            wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)
            wx.CallAfter(self.sec_plot_panel.fitAxis)
        if loaded_iftm:
            wx.CallAfter(self.ift_plot_panel.updateLegend, 1, False)
            wx.CallAfter(self.ift_plot_panel.updateLegend, 2, False)
            wx.CallAfter(self.ift_plot_panel.fitAxis)


        file_list = wx.FindWindowByName('FileListCtrl')
        if file_list != None:
            wx.CallAfter(file_list.SetFocus)

        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _loadAndPlotSEC(self, data):
        filename_list=data[0]
        frame_list=data[1]

        secm_list = []

        if len(data) == 3:
            update_sec_object = data[2]
        else:
            update_sec_object = False

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while series data loads')

        all_secm = True
        for name in filename_list:
            if os.path.splitext(name)[1] != '.sec':
                all_secm = False
                break

        if all_secm:
            for each_filename in filename_list:
                try:
                    secm = SASFileIO.loadSeriesFile(each_filename)
                except:
                    wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1],include_sec=True)
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                    return

                secm_list.append(secm)

            self._sendSECMToPlot(secm_list, no_update = True, update_legend = False)

        else:
            sasm_list=[]

            try:
                for j in range(len(filename_list)):
                    each_filename = filename_list[j]
                    sasm, img = SASFileIO.loadFile(each_filename, self._raw_settings)

                    if img is not None:
                        start_point = self._raw_settings.get('StartPoint')
                        end_point = self._raw_settings.get('EndPoint')

                        if not isinstance(sasm, list):
                            qrange = (start_point, len(sasm.getBinnedQ())-end_point)
                            sasm.setQrange(qrange)
                        else:
                            qrange = (start_point, len(sasm[0].getBinnedQ())-end_point)
                            for each_sasm in sasm:
                                each_sasm.setQrange(qrange)
                    if isinstance(sasm, list):
                        sasm_list.extend(sasm)
                    else:
                        sasm_list.append(sasm)

            except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
                wx.CallAfter(self._showSECFormatError, os.path.split(each_filename)[1])
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return
            except SASExceptions.HeaderLoadError, msg:
                wx.CallAfter(self._showHeaderError, str(msg))
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return
            except SASExceptions.MaskSizeError, msg:
                wx.CallAfter(self._showGenericError, str(msg), 'Saved mask does not fit loaded image')
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return
            except SASExceptions.HeaderMaskLoadError, msg:
                wx.CallAfter(self._showGenericError, str(msg), 'Mask information was not found in header')
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return
            except SASExceptions.AbsScaleNormFailed:
                msg = ('Failed to apply absolute scale. The most '
                        'likely cause is a mismatch between the q vector of the '
                        'loaded file and the selected sample background file. '
                        'It failed on the following file:\n')
                msg = msg + os.path.split(each_filename)[1]
                wx.CallAfter(wx._showGenericError, msg, 'Absolute scale failed')
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return

            try:
                secm = SASM.SECM(filename_list, sasm_list, frame_list, {})
            except AttributeError:
                msg = ('Some or all of the selected files were not scattering '
                    'profiles or images, so a series dataset could not be generated.')
                wx.CallAfter(self._showGenericError, msg, 'Could not make series')
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return

            self._sendSECMToPlot(secm, notsaved = True, no_update = True, update_legend = False)

        if update_sec_object:
            wx.CallAfter(self.sec_control_panel.updateSECItem, secm)

        wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)
        wx.CallAfter(self.sec_plot_panel.fitAxis)
        wx.CallAfter(self.main_frame.closeBusyDialog)

        secpage = -1

        for i in range(self.main_frame.plot_notebook.GetPageCount()):
            if self.main_frame.plot_notebook.GetPageText(i) == 'Series':
                secpage = i
                wx.CallAfter(self.main_frame.plot_notebook.SetSelection, secpage)

        #This is stupid and shouldn't be necessary!
        if secpage > -1:
            while self.main_frame.plot_notebook.GetSelection() != secpage:
                time.sleep(.001)
                wx.CallAfter(self.main_frame.plot_notebook.SetSelection, secpage)


    def _updateSECM(self, data):
        filename_list = data[0]
        frame_list = data[1]
        secm = data[2]

        if len(filename_list)>5:
            wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while series data loads')

        sasm_list=[[] for i in range(len(filename_list))]

        for j in range(len(filename_list)):
            try:
                each_filename = filename_list[j]
                sasm, img = SASFileIO.loadFile(each_filename, self._raw_settings)

                if img is not None:
                    start_point = self._raw_settings.get('StartPoint')
                    end_point = self._raw_settings.get('EndPoint')

                    if type(sasm) != list:
                        qrange = (start_point, len(sasm.getBinnedQ())-end_point)
                        sasm.setQrange(qrange)
                    else:
                        qrange = (start_point, len(sasm[0].getBinnedQ())-end_point)
                        for each_sasm in sasm:
                            each_sasm.setQrange(qrange)

                        if len(sasm) == 1:
                            sasm = sasm[0]
                        else:
                            sasm = SASProc.average(sasm) #If load sec loads a file with multiple sasms, it averages them into one sasm

                sasm_list[j]=sasm

            except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
                if len(filename_list)>5:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                wx.CallAfter(self.sec_control_panel.updateFailed, each_filename, 'file', msg)
                return
            except SASExceptions.HeaderLoadError, msg:
                if len(filename_list)>5:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                wx.CallAfter(self.sec_control_panel.updateFailed, each_filename, 'header', msg)
                return
            except SASExceptions.MaskSizeError, msg:
                if len(filename_list)>5:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                wx.CallAfter(self.sec_control_panel.updateFailed, each_filename, 'mask', msg)
                return
            except SASExceptions.HeaderMaskLoadError, msg:
                if len(filename_list)>5:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                wx.CallAfter(self.sec_control_panel.updateFailed, each_filename, 'mask_header', msg)
                return
            except SASExceptions.AbsScaleNormFailed:
                msg = ('Failed to apply absolute scale. The most '
                        'likely cause is a mismatch between the q vector of the '
                        'loaded file and the selected sample background file. '
                        'It failed on the following file:\n')
                msg = msg + os.path.split(each_filename)[1]
                wx.CallAfter(self.sec_control_panel.updateFailed, each_filename, 'abs_scale', msg)
                if len(filename_list)>5:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                return

        largest_frame = secm.plot_frame_list[-1]

        secm.append(filename_list, sasm_list, frame_list)

        if secm.calc_has_data:
            self._updateCalcSECParams(secm, range(len(frame_list))+largest_frame+1)

        self._updateSECMPlot(secm)

        wx.CallAfter(self.sec_control_panel.updateSucceeded)
        if len(filename_list)>5:
            wx.CallAfter(self.main_frame.closeBusyDialog)


    def _updateCalcSECParams(self, secm, frame_list):
        molecule = secm.mol_type
        if molecule == 'Protein':
            is_protein = True
        else:
            is_protein = False

        vp_density = secm.mol_density

        threshold = self._raw_settings.get('secCalcThreshold')
        error_weight = self._raw_settings.get('errorWeight')

        first_update_frame = int(frame_list[0])
        last_update_frame = int(frame_list[-1])

        window_size = secm.window_size

        secm.acquireSemaphore()

        if window_size == -1:
            secm.releaseSemaphore()
            return

        buffer_avg_sasm = secm.average_buffer_sasm

        #Find the reference intensity of the average buffer sasm
        plot_y = self.sec_plot_panel.getParameter('y_axis_display')

        if plot_y == 'total':
            ref_intensity = buffer_avg_sasm.getTotalI()

        elif plot_y == 'mean':
            ref_intensity = buffer_avg_sasm.getMeanI()

        elif plot_y == 'q_val':
            ref_intensity = buffer_avg_sasm.getIofQ(secm.qref)

        elif plot_y == 'q_range':
            ref_intensity = buffer_avg_sasm.getIofQRange(secm.qrange[0], secm.qrange[1])

        #Now subtract the average buffer from all of the items in the secm list
        sub_sasm = buffer_avg_sasm

        first_frame = first_update_frame - window_size

        if first_frame <0:
            first_frame = 0

        last_frame = last_update_frame

        full_sasm_list = secm.getSASMList(first_frame, last_frame)

        subtracted_sasm_list = []

        use_subtracted_sasm = []

        yes_to_all = False

        for sasm in full_sasm_list:

            #check to see whether we actually need to subtract this curve
            if plot_y == 'total':
                sasm_intensity = sasm.getTotalI()

            elif plot_y == 'mean':
                sasm_intensity = sasm.getMeanI()

            elif plot_y == 'q_val':
                sasm_intensity = buffer_avg_sasm.getIofQ(secm.qref)

            elif plot_y == 'q_range':
                sasm_intensity = buffer_avg_sasm.getIofQRange(secm.qrange[0], secm.qrange[1])

            if sasm_intensity/ref_intensity > threshold:
                use_subtracted_sasm.append(True)
            else:
                use_subtracted_sasm.append(False)

            result = wx.ID_YES

            qmin, qmax = sasm.getQrange()
            sub_qmin, sub_qmax = sub_sasm.getQrange()

            if np.all(np.round(sasm.q[qmin:qmax],5) == np.round(sub_sasm.q[sub_qmin:sub_qmax],5)) == False and not yes_to_all:
                result = self._showQvectorsNotEqualWarning(sasm, sub_sasm)[0]

                if result == wx.ID_YESTOALL:
                    yes_to_all = True
                elif result == wx.ID_CANCEL:
                    try:
                        wx.CallAfter(self.main_frame.closeBusyDialog)
                    except Exception:
                        pass
                    secm.releaseSemaphore()
                    return
                try:
                    if result == wx.ID_YES or result == wx.ID_YESTOALL:
                        subtracted_sasm = SASProc.subtract(sasm, sub_sasm, forced = True)
                        self._insertSasmFilenamePrefix(subtracted_sasm, 'S_')

                        subtracted_sasm_list.append(subtracted_sasm)
                except SASExceptions.DataNotCompatible:
                    wx.CallAfter(self._showSubtractionError, sasm, sub_sasm)
                    try:
                        wx.CallAfter(self.main_frame.closeBusyDialog)
                    except Exception:
                        pass
                    secm.releaseSemaphore()
                    return
            elif np.all(np.round(sasm.q[qmin:qmax],5) == np.round(sub_sasm.q[sub_qmin:sub_qmax],5)) == False and yes_to_all:
                try:
                    subtracted_sasm = SASProc.subtract(sasm, sub_sasm, forced = True)
                    self._insertSasmFilenamePrefix(subtracted_sasm, 'S_')

                    subtracted_sasm_list.append(subtracted_sasm)
                except SASExceptions.DataNotCompatible:
                    wx.CallAfter(self._showSubtractionError, sasm, sub_sasm)
                    try:
                        wx.CallAfter(self.main_frame.closeBusyDialog)
                    except Exception:
                        pass
                    secm.releaseSemaphore()
                    return
            else:
                try:
                    subtracted_sasm = SASProc.subtract(sasm, sub_sasm)
                    self._insertSasmFilenamePrefix(subtracted_sasm, 'S_')

                    subtracted_sasm_list.append(subtracted_sasm)
                except SASExceptions.DataNotCompatible:
                    wx.CallAfter(self._showSubtractionError, sasm, sub_sasm)
                    try:
                        wx.CallAfter(self.main_frame.closeBusyDialog)
                    except Exception:
                        pass
                    secm.releaseSemaphore()
                    return


        secm.appendSubtractedSASMs(subtracted_sasm_list, use_subtracted_sasm, window_size)


        if secm.baseline_subtracted_sasm_list:
            r1_start = secm.baseline_start_range[0]
            r1_end = secm.baseline_start_range[1]
            r2_start = secm.baseline_end_range[0]
            r2_end = secm.baseline_end_range[1]

            bl_type = secm.baseline_type
            bl_extrap = secm.baseline_extrap

            new_sasms = secm.subtracted_sasm_list[first_frame:]

            bl_sasms = []
            baselines = secm.baseline_corr
            fit_results = secm.baseline_fit_results

            bl_q = copy.deepcopy(new_sasms[0].getQ())
            bl_err = np.zeros_like(new_sasms[0].getQ())
            new_baselines = []

            for j, sasm in enumerate(new_sasms):
                idx = j + first_frame
                q = copy.deepcopy(sasm.getQ())

                if bl_type == 'Integral':
                    if idx < r1_start:
                        baseline = baselines[0].getI()
                        i = copy.deepcopy(sasm.getI())
                        err = copy.deepcopy(sasm.getErr())
                    elif idx >= r1_end and idx < r2_start:
                        baseline = baselines[idx-r1_end].getI()
                        i = sasm.getI() - baseline
                        err = sasm.getErr() * i/sasm.getI()
                    else:
                        baseline = baselines[-1].getI()
                        i = sasm.getI() - baseline
                        err = sasm.getErr() * i/sasm.getI()

                elif bl_type == 'Linear':

                    if bl_extrap:
                        baseline = np.array([SASCalc.linear_func(idx, fit[0], fit[1]) for fit in fit_results])
                        i = sasm.getI() - baseline
                        err = sasm.getErr() * i/sasm.getI()

                        bl_newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                        new_baselines.append(bl_newSASM)

                    else:
                        if idx >= r1_start and idx <= r2_end:
                            baseline = np.array([SASCalc.linear_func(idx, fit[0], fit[1]) for fit in fit_results])
                            i = sasm.getI() - baseline
                            err = sasm.getErr() * i/sasm.getI()

                            bl_newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                            new_baselines.append(bl_newSASM)
                        else:
                            i = copy.deepcopy(sasm.getI())
                            err = copy.deepcopy(sasm.getErr())
                            baseline = np.zeros_like(i)

                parameters = copy.deepcopy(sasm.getAllParameters())
                newSASM = SASM.SASM(i, q, err, {})
                newSASM.setParameter('filename', parameters['filename'])

                history = newSASM.getParameter('history')

                history = {}

                history1 = []
                history1.append(copy.deepcopy(sasm.getParameter('filename')))
                for key in sasm.getParameter('history'):
                    history1.append({ key : copy.deepcopy(sasm.getParameter('history')[key])})

                history['baseline_correction'] = {'initial_file':history1, 'baseline':list(baseline)}

                newSASM.setParameter('history', history)

                bl_sasms.append(newSASM)

            if bl_type == 'Linear':
                if bl_extrap:
                    baselines = baselines[:-window_size]+new_baselines
                else:
                    if first_frame <= r2_end:
                        bl_idx = min(r2_end-first_frame, window_size)
                        baselines = baselines[:-bl_idx] + new_baselines

            baseline_use_subtracted_sasms = []

            buffer_sub_sasms = secm.subtracted_sasm_list
            start_frames = range(r1_start, r1_end+1)
            start_sasms = [buffer_sub_sasms[k] for k in start_frames]

            start_avg_sasm = SASProc.average(start_sasms, forced=True)

            if  plot_y == 'total':
                ref_intensity = start_avg_sasm.getTotalI()
            elif plot_y == 'mean':
                ref_intensity = start_avg_sasm.getMeanI()
            elif plot_y == 'q_val':
                qref = float(self.plot_page.q_val.GetValue())
                ref_intensity = start_avg_sasm.getIofQ(qref)
            elif plot_y == 'q_range':
                q1 = float(self.plot_page.q_range_start.GetValue())
                q2 = float(self.plot_page.q_range_end.GetValue())
                ref_intensity = start_avg_sasm.getIofQRange(q1, q2)

            for sasm in bl_sasms:
                if plot_y == 'total':
                    sasm_intensity = sasm.getTotalI()
                elif plot_y == 'mean':
                    sasm_intensity = sasm.getMeanI()
                elif plot_y == 'q_val':
                    sasm_intensity = sasm.getIofQ(qref)
                elif plot_y == 'q_range':
                    sasm_intensity = sasm.getIofQRange(q1, q2)

                if abs(sasm_intensity/ref_intensity) > threshold:
                    baseline_use_subtracted_sasms.append(True)
                else:
                    baseline_use_subtracted_sasms.append(False)

            secm.appendBCSubtractedSASMs(bl_sasms, baseline_use_subtracted_sasms,
                window_size)
            secm.baseline_corr = baselines

            success, results = SASCalc.run_secm_calcs(bl_sasms,
                baseline_use_subtracted_sasms, window_size, is_protein, error_weight,
                vp_density)

        else:
            success, results = SASCalc.run_secm_calcs(subtracted_sasm_list,
                use_subtracted_sasm, window_size, is_protein, error_weight,
                vp_density)

        if not success:
            secm.releaseSemaphore()
            wx.CallAfter(self._showAverageError, 1)
            return

        rg = results['rg']
        rger = results['rger']
        i0 = results['i0']
        i0er = results['i0er']
        vcmw = results['vcmw']
        vcmwer = results['vcmwer']
        vpmw = results['vpmw']

        secm.appendCalcValues(rg, rger, i0, i0er, vcmw, vcmwer, vpmw,
            first_frame, window_size)

        secm.calc_has_data = True
        secm.releaseSemaphore()

        return

    def _loadAndShowNextImage(self, data):

        current_file = data[0]
        direction = data[1]

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading image...')

        path = self.dir_panel.file_list_box.path
        dir = sorted(os.listdir(path))

        if current_file is None:
            idx = 0
        else:
            try:
                idx = dir.index(current_file)
            except ValueError:
                idx = 0
                msg = ('Could not find the current image file in the active '
                    'directory. Defaulting to the first file in the active '
                    'directory (if possible). Please check the active directory '
                    'in the Files control tab.')
                wx.CallAfter(self._showGenericError, msg, 'Error Loading Image')


        while True:
            idx = idx + direction

            if idx < 0: break
            if idx >= len(dir): break

            next_file = dir[idx]
            next_file_path = os.path.join(path, next_file)

            try:
                img = None
                if self._fileTypeIsCompatible(next_file_path):
                    img, imghdr = SASFileIO.loadImage(next_file_path, self._raw_settings)

                if img is not None:
                    parameters = {'filename' : os.path.split(next_file_path)[1],
                                  'imageHeader' : imghdr[-1]}

                    bogus_sasm = SASM.SASM([0,1], [0,1], [0,1], parameters)

                    if isinstance(img, list) and len(img) > 1 and direction == -1:
                        fnum = len(img) - 1
                    else:
                        fnum = 0

                    self._sendImageToDisplay(img, bogus_sasm, fnum)
                    break
            except Exception:
                pass

        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _fileTypeIsCompatible(self, path):
        root, ext = os.path.splitext(path)

        compatible_formats = self.main_frame.getRawSettings().get('CompatibleFormats')

        if str(ext) in compatible_formats:
            return True
        else:
            return False

    def _loadAndShowImage(self, data):
        filename = data[0]
        fnum = data[1]

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading image...')

        print filename
        try:
            if not os.path.isfile(filename):
                raise SASExceptions.WrongImageFormat('not a valid file!')

            img, imghdr = SASFileIO.loadImage(filename, self._raw_settings)

            if img is None:
                raise SASExceptions.WrongImageFormat('not a valid file!')

        except SASExceptions.WrongImageFormat:
            wx.CallAfter(self._showDataFormatError, os.path.split(filename)[1], include_ascii = False)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        parameters = {'filename' : os.path.split(filename)[1],
                      'imageHeader' : imghdr[-1]}

        bogus_sasm = SASM.SASM([0,1], [0,1], [0,1], parameters)

        self._sendImageToDisplay(img, bogus_sasm, fnum)
        wx.CallAfter(self.main_frame.plot_notebook.SetSelection, 2)
        file_list = wx.FindWindowByName('FileListCtrl')
        wx.CallAfter(file_list.SetFocus)
        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _calibrateSASM(self, sasm):

        #if self._raw_settings.get('CalibrateMan'):
        sd_distance = self._raw_settings.get('SampleDistance')
        pixel_size = self._raw_settings.get('DetectorPixelSize')
        wavelength = self._raw_settings.get('WaveLength')

        sasm.calibrateQ(sd_distance, pixel_size, wavelength)

    def _showDataFormatError(self, filename, include_ascii = True, include_sec = False):
        img_fmt = self._raw_settings.get('ImageFormat')

        if include_ascii:
            ascii = ' or any of the supported ASCII formats'
        else:
            ascii = ''

        if include_sec:
            sec = ' or the RAW series format'
        else:
            sec = ''
        msg = ('The selected file: ' + filename + '\ncould not be recognized as a '
            + str(img_fmt) + ' image format' + ascii + sec + '. This can be '
            'caused by failing to load the correct configuration file.\n\n'
            'You can change the image format under Advanced Options in the '
            'Options menu.')
        wx.CallAfter(wx.MessageBox, msg , 'Error loading file', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showSECFormatError(self, filename, include_ascii = True):
        img_fmt = self._raw_settings.get('ImageFormat')

        if include_ascii:
            ascii = ' or any of the supported ASCII formats'
        else:
            ascii = ''

        msg = ('The selected file: ' + filename + '\ncould not be recognized as '
            'a '   + str(img_fmt) + ' image format' + ascii + '. This can be '
            'caused by failing to load the correct configuration file. \n\n'
            'If you are loading a set of files as a series curve, make sure the '
            'selection contains only individual scattering profiles (no .sec files).'
            '\n\nYou can change the image format under Advanced Options in the '
            'Options menu.')
        wx.CallAfter(wx.MessageBox, msg , 'Error loading file', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showSubtractionError(self, sasm, sub_sasm):
        filename1 = sasm.getParameter('filename')
        q1_min, q1_max = sasm.getQrange()
        points1 = len(sasm.i[q1_min:q1_max])
        filename2 = sub_sasm.getParameter('filename')
        q2_min, q2_max = sub_sasm.getQrange()
        points2 = len(sub_sasm.i[q2_min:q2_max])

        msg = (filename1 + ' has ' + str(points1) + ' data points.\n'  +
            filename2 + ' has ' + str(points2) + ' data points.\n\n' +
            'Subtraction is not possible. Data files must have equal number of points.')

        wx.CallAfter(wx.MessageBox, msg, 'Subtraction Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showAverageError(self, err_no, sasm_list=[]):
        if err_no == 1:
            msg = ('The selected items must have the same total number of '
                'points to be averaged.')
            wx.CallAfter(wx.MessageBox, msg, 'Average Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)
        elif err_no == 2:
            msg = 'Please select at least two items to be averaged.'
            wx.CallAfter(wx.MessageBox, msg, 'Average Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)
        elif err_no == 3:
            msg = 'The selected items must have the same q vectors to be averaged.'
            wx.CallAfter(wx.MessageBox, msg, 'Average Error', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

        elif err_no == 4:
            test = self._raw_settings.get('similarityTest')
            threshold = self._raw_settings.get('similarityThreshold')
            msg = ('One or more of the selected items to be averaged is '
                'statistically\ndifferent from the first item, as found '
                'using the %s test\nand a pval threshold of %f.\n\nThe '
                'following profiles were found to be different:\n'
                %(test, threshold))
            for sasm in sasm_list:
                msg = msg + sasm.getParameter('filename') + '\n'
            msg = msg + ('\nPlease select an action below.')
            answer = self._displayQuestionDialog(msg, 'Warning: Profiles to average are different',
                            [('Cancel Average', wx.ID_CANCEL), ('Average All Files', wx.ID_YESTOALL),
                            ('Average Only Similar Files', wx.ID_YES)], wx.ART_WARNING)
            return answer[0]

    def _showPleaseSelectItemsError(self, err_type):

        if err_type == 'average':
            msg = ('Please select the items you want to average.\n\nYou can '
                'select multiple items by holding down the CTRL or SHIFT key.')
            wx.CallAfter(wx.MessageBox, msg, 'No items selected', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)
        elif err_type == 'subtract':
            msg = ('Please select the items you want the marked (star) item '
                'subtracted from.\nUse CTRL or SHIFT to select multiple items.')
            wx.CallAfter(wx.MessageBox, msg, 'No items selected', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)
        elif err_type == 'superimpose':
            msg = ('Please select the items you want to superimpose.\n\nYou '
            'can select multiple items by holding down the CTRL or SHIFT key.')
            wx.CallAfter(wx.MessageBox, msg, 'No items selected', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showPleaseMarkItemError(self, err_type):

        if err_type == 'subtract':
            msg = 'Please mark (star) the item you are using for subtraction'
        elif err_type == 'merge':
            msg = ('Please mark (star) the item you are using as the main '
                'curve for merging')
        elif err_type == 'superimpose':
            msg = 'Please mark (star) the item you want to superimpose to.'
        elif err_type == 'interpolate':
            msg = 'Please mark (star) the item you are using as the main curve for interpolation'

        wx.CallAfter(wx.MessageBox, msg, 'No item marked', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showSaveError(self, err_type):
        if err_type == 'header':
            msg = 'Header values could not be saved, file was saved without them.'
            wx.CallAfter(wx.MessageBox, msg, 'Invalid Header Values', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showQvectorsNotEqualWarning(self, sasm, sub_sasm):

        sub_filename = sub_sasm.getParameter('filename')
        filename = sasm.getParameter('filename')

        button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO), ('Cancel', wx.ID_CANCEL)]
        question = ('Q vectors for ' + str(filename) + ' and ' + str(sub_filename) +
            ' are not the same. \nContinuing subtraction will attempt to find '
            'matching q regions in or create matching q regions by binning.\n'
            'Do you wish to continue?')
        label = 'Q vectors do not match'
        icon = wx.ART_WARNING

        answer = self._displayQuestionDialog(question, label, button_list, icon)

        return answer

    def _showQuickReduceFinished(self, processed_files, number_of_files):
        msg = ('Quick reduction finished. Processed ' + str(processed_files) +
            ' out of ' + str(number_of_files) + ' files.')
        wx.CallAfter(wx.MessageBox, msg, 'Quick reduction finished', style = wx.ICON_INFORMATION | wx.STAY_ON_TOP)

    def _showOverwritePrompt(self, filename, save_path):

        button_list = [('Yes', wx.ID_YES), ('Yes to all', wx.ID_YESTOALL), ('No', wx.ID_NO),
                       ('No to all', wx.ID_NOTOALL), ('Rename', wx.ID_EDIT), ('Cancel', wx.ID_CANCEL)]

        path = os.path.join(save_path, filename)

        question = ('Filename: ' + str(path) + '\nalready exists. Do you '
            'wish to overwrite the existing file?')
        label = 'File exists'
        icon = wx.ART_WARNING

        answer = self._displayQuestionDialog(question, label, button_list, icon, filename, save_path)

        return answer

    def _showHeaderError(self, err_msg):
        msg = (str(err_msg)+'\n\nPlease check that the header file is in '
            'the directory with the data.')
        wx.CallAfter(wx.MessageBox, msg, 'Error Loading Header File', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showGenericError(self, msg, title):
        wx.CallAfter(wx.MessageBox, msg, title, style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    def _showGenericMsg(self, msg, title):
        wx.CallAfter(wx.MessageBox, msg, title, style = wx.ICON_INFORMATION | wx.STAY_ON_TOP)

    def _displayQuestionDialog(self, question, label, button_list, icon = None, filename = None, save_path = None):

        wx.CallAfter(self.main_frame.showQuestionDialogFromThread, question, label, button_list, icon, filename, save_path)

        thread_wait_event.wait()
        thread_wait_event.clear()

        answer = question_return_queue.get()
        question_return_queue.task_done()

        return answer

    def _subtractFilenames(self):
        pass

    def _plotIFTM(self, data):

        iftm = data[0]
        item_colour = data[1]
        line_color = data[2]
        notsaved = data[3]

        self._sendIFTMToPlot(iftm, item_colour=item_colour, line_color=line_color,
            notsaved=notsaved)

    def _plotSASM(self, data):

        sasm = data[0]
        item_colour = data[1]
        line_color = data[2]
        notsaved = data[3]
        plot = data[4]

        self._sendSASMToPlot(sasm, axes_num=plot, item_colour=item_colour,
            line_color=line_color, notsaved=notsaved)

    def _plotIftFit(self, data):

        selected_items = data[0]

        selected_sasms = []
        for each_item in selected_items:
            selected_sasms.append(each_item.getSASM())

        for each in selected_sasms:

            param = each.getAllParameters()

            if param.has_key('orig_sasm'):
                self._sendSASMToPlot(each.getParameter('orig_sasm').copy())
            if param.has_key('fit_sasm'):
                self._sendSASMToPlot(each.getParameter('fit_sasm').copy())


        wx.CallAfter(self.plot_panel.updateLegend, 1)

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

                        start_point = self._raw_settings.get('StartPoint')
                        end_point = self._raw_settings.get('EndPoint')

                        if type(sasm) != list:
                            qrange = (start_point, len(sasm.getBinnedQ())-end_point)
                            sasm.setQrange(qrange)
                        else:
                            qrange = (start_point, len(sasm[0].getBinnedQ())-end_point)
                            for each_sasm in sasm:
                                each_sasm.setQrange(qrange)

                        if result[0] == wx.ID_EDIT:
                            final_save_path, new_filename = os.path.split(result[1][0])
                            sasm.setParameter('filename', new_filename)

                            if type(sasm) != list:
                                sasm.setParameter('filename', new_filename)
                            else:
                                for each_sasm in sasm:
                                    sasm.setParameter('filename', new_filename)
                        else:
                            final_save_path = save_path

                        if img is not None:
                            try:
                                SASFileIO.saveMeasurement(sasm, final_save_path, self._raw_settings)
                            except SASExceptions.HeaderSaveError:
                                wx.CallAfter(self._showSaveError, 'header')

                            processed_files += 1
                        else:
                            wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1], include_ascii = False)
                    except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat):
                        wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1], include_ascii = False)
                    except SASExceptions.HeaderLoadError, msg:
                        wx.CallAfter(self._showHeaderError, str(msg))
                    except SASExceptions.AbsScaleNormFailed:
                        msg = ('Failed to apply absolute scale. The most '
                                'likely cause is a mismatch between the q vector of the '
                                'loaded file and the selected sample background file. '
                                'It failed on the following file:\n%s\n'
                                'Skipping this file and proceeding.') %(os.path.split(each_filename)[1])
                        wx.CallAfter(self._showGenericError, msg, 'Absolute scale failed')

            else:
                try:
                    sasm, img = SASFileIO.loadFile(full_load_path, self._raw_settings)

                    start_point = self._raw_settings.get('StartPoint')
                    end_point = self._raw_settings.get('EndPoint')

                    if type(sasm) != list:
                        qrange = (start_point, len(sasm.getBinnedQ())-end_point)
                        sasm.setQrange(qrange)
                    else:
                        qrange = (start_point, len(sasm[0].getBinnedQ())-end_point)
                        for each_sasm in sasm:
                            each_sasm.setQrange(qrange)

                    if img is not None:
                        try:
                            SASFileIO.saveMeasurement(sasm, save_path, self._raw_settings)
                        except SASExceptions.HeaderSaveError:
                            wx.CallAfter(self._showSaveError, 'header')

                        processed_files += 1
                    else:
                        wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1], include_ascii = False)
                except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat):
                    wx.CallAfter(self._showDataFormatError, os.path.split(each_filename)[1], include_ascii = False)
                except SASExceptions.HeaderLoadError, msg:
                    wx.CallAfter(self._showHeaderError, str(msg))
                except SASExceptions.AbsScaleNormFailed:
                    msg = ('Failed to apply absolute scale. The most '
                            'likely cause is a mismatch between the q vector of the '
                            'loaded file and the selected sample background file. '
                            'It failed on the following file:\n%s\n'
                            'Skipping this file and proceeding.') %(os.path.split(each_filename)[1])
                    wx.CallAfter(self._showGenericError, msg, 'Absolute scale failed')

        wx.CallAfter(self._showQuickReduceFinished, processed_files, len(filename_list))


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

        button_list = [('Scale', wx.Window.NewControlId()), ('Offset', wx.Window.NewControlId()),
                        ('Scale and Offset', wx.Window.NewControlId())]

        question = 'Select whether superimpose should scale, offset, or scale and offset the data.'
        label = 'Select Superimpose Parameters'
        icon = wx.ART_QUESTION

        answer = self._displayQuestionDialog(question, label, button_list, icon)
        answer_id = answer[0]

        for param, button_id in button_list:
            if answer_id == button_id:
                choice = param

        SASProc.superimpose(star_item.getSASM(), selected_sasms, choice)

        for each_item in selected_items:
            wx.CallAfter(each_item.updateControlsFromSASM, updatePlot=False)

        wx.CallAfter(self.plot_panel.updatePlotAfterManipulation, selected_sasms)

    def _subtractItems(self, data):
        ''' subtracts the marked item from other selected items in the
        manipulation list '''

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while subtracting and plotting...')

        do_auto_save = self._raw_settings.get('AutoSaveOnSub')

        marked_item = data[0]
        selected_items = data[1]

        if marked_item in selected_items:
            selected_items.remove(marked_item)

        if marked_item == None:
            wx.CallAfter(self._showPleaseMarkItemError, 'subtract')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return
        elif len(selected_items) == 0:
            wx.CallAfter(self._showPleaseSelectItemsError, 'subtract')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        sub_sasm = marked_item.getSASM()

        yes_to_all = False

        subtracted_list = []

        for i in range(len(selected_items)):
            each = selected_items[i]
            # result = wx.ID_YES
            sasm = each.getSASM()

            print sasm.getParameter('filename')

            qmin, qmax = sasm.getQrange()
            sub_qmin, sub_qmax = sub_sasm.getQrange()

            if np.all(np.round(sasm.q[qmin:qmax],5) == np.round(sub_sasm.q[sub_qmin:sub_qmax],5)) == False and not yes_to_all:
                result = self._showQvectorsNotEqualWarning(sasm, sub_sasm)[0]

                if result == wx.ID_YESTOALL:
                    yes_to_all = True
                elif result == wx.ID_CANCEL:
                    wx.CallAfter(self.main_frame.closeBusyDialog)
                    return
                try:
                    if result == wx.ID_YES or result == wx.ID_YESTOALL:
                        subtracted_sasm = SASProc.subtract(sasm, sub_sasm, forced = True)
                        self._insertSasmFilenamePrefix(subtracted_sasm, 'S_')

                        subtracted_list.append(subtracted_sasm)
                        # self._sendSASMToPlot(subtracted_sasm, no_update = True, update_legend = False, axes_num = 2, item_colour = 'red', notsaved = True)

                        if do_auto_save:
                            save_path = self._raw_settings.get('SubtractedFilePath')
                            try:
                                self._saveSASM(subtracted_sasm, '.dat', save_path)
                            except IOError, e:
                                self._raw_settings.set('AutoSaveOnSub', False)
                                do_auto_save = False
                                msg = (str(e) + '\n\nAutosave of subtracted '
                                    'images has been disabled. If you are '
                                    'using a config file from a different '
                                    'computer please go into Advanced '
                                    'Options/Autosave to change the save '
                                    'folders, or save you config file to '
                                    'avoid this message next time.')
                                wx.CallAfter(self._showGenericError, msg, 'Autosave Error')

                except SASExceptions.DataNotCompatible:
                   wx.CallAfter(self._showSubtractionError, sasm, sub_sasm)
                   wx.CallAfter(self.main_frame.closeBusyDialog)
                   return
            elif np.all(np.round(sasm.q[qmin:qmax],5) == np.round(sub_sasm.q[sub_qmin:sub_qmax],5)) == False and yes_to_all:
                try:
                    subtracted_sasm = SASProc.subtract(sasm, sub_sasm, forced = True)
                    self._insertSasmFilenamePrefix(subtracted_sasm, 'S_')

                    subtracted_list.append(subtracted_sasm)
                    # self._sendSASMToPlot(subtracted_sasm, no_update = True, update_legend = False, axes_num = 2, item_colour = 'red', notsaved = True)

                    if do_auto_save:
                        save_path = self._raw_settings.get('SubtractedFilePath')
                        try:
                            self._saveSASM(subtracted_sasm, '.dat', save_path)
                        except IOError, e:
                            self._raw_settings.set('AutoSaveOnSub', False)
                            do_auto_save = False
                            msg = (str(e) + '\n\nAutosave of subtracted '
                                'images has been disabled. If you are '
                                'using a config file from a different '
                                'computer please go into Advanced '
                                'Options/Autosave to change the save '
                                'folders, or save you config file to '
                                'avoid this message next time.')
                            wx.CallAfter(self._showGenericError, msg, 'Autosave Error')

                except SASExceptions.DataNotCompatible:
                   wx.CallAfter(self._showSubtractionError, sasm, sub_sasm)
                   wx.CallAfter(self.main_frame.closeBusyDialog)
                   return
            else:
                try:
                    subtracted_sasm = SASProc.subtract(sasm, sub_sasm)
                    self._insertSasmFilenamePrefix(subtracted_sasm, 'S_')

                    subtracted_list.append(subtracted_sasm)
                    # self._sendSASMToPlot(subtracted_sasm, no_update = True, update_legend = False, axes_num = 2, item_colour = 'red', notsaved = True)

                    if do_auto_save:
                        save_path = self._raw_settings.get('SubtractedFilePath')
                        try:
                            self._saveSASM(subtracted_sasm, '.dat', save_path)
                        except IOError, e:
                            self._raw_settings.set('AutoSaveOnSub', False)
                            do_auto_save = False
                            msg = (str(e) + '\n\nAutosave of subtracted '
                                'images has been disabled. If you are '
                                'using a config file from a different '
                                'computer please go into Advanced '
                                'Options/Autosave to change the save '
                                'folders, or save you config file to '
                                'avoid this message next time.')
                            wx.CallAfter(self._showGenericError, msg, 'Autosave Error')

                except SASExceptions.DataNotCompatible:
                   wx.CallAfter(self._showSubtractionError, sasm, sub_sasm)
                   wx.CallAfter(self.main_frame.closeBusyDialog)
                   return

            if np.mod(i,20) == 0:
                self._sendSASMToPlot(subtracted_list, no_update = True, update_legend = False, axes_num = 2, item_colour = 'red', notsaved = True)
                wx.CallAfter(self.plot_panel.canvas.draw)
                subtracted_list = []

        if len(subtracted_list) > 0:
            self._sendSASMToPlot(subtracted_list, no_update = True, update_legend = False, axes_num = 2, item_colour = 'red', notsaved = True)

        wx.CallAfter(self.plot_panel.updateLegend, 2, False)
        wx.CallAfter(self.plot_panel.fitAxis)
        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _average(self, sasm_list, weight=False, weightByError=True, weightCounter=None):
        profiles_to_use = wx.ID_YESTOALL

        if self._raw_settings.get('similarityOnAverage'):
            ref_sasm = sasm_list[0]
            qi_ref, qf_ref = ref_sasm.getQrange()
            pvals = np.ones(len(sasm_list[1:]), dtype=float)
            threshold = self._raw_settings.get('similarityThreshold')
            sim_test = self._raw_settings.get('similarityTest')
            correction = self._raw_settings.get('similarityCorrection')

            for index, sasm in enumerate(sasm_list[1:]):
                qi, qf = sasm.getQrange()
                if not np.all(np.round(sasm.q[qi:qf], 5) == np.round(ref_sasm.q[qi_ref:qf_ref], 5)):
                    wx.CallAfter(self._showAverageError, 3)
                    return None

                if sim_test == 'CorMap':
                    n, c, pval = SASCalc.cormap_pval(ref_sasm.i[qi_ref:qf_ref], sasm.i[qi:qf])
                pvals[index] = pval

            if correction == 'Bonferroni':
                pvals = pvals*len(sasm_list[1:])
                pvals[pvals>1] = 1

            if np.any(pvals<threshold):
                wx.CallAfter(self.main_frame.closeBusyDialog)
                profiles_to_use = self._showAverageError(4, itertools.compress(sasm_list[1:], pvals<threshold))

                if profiles_to_use == wx.ID_CANCEL:
                    return None

                wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while averaging and plotting...')
        try:
            if profiles_to_use == wx.ID_YESTOALL:
                if not weight:
                    avg_sasm = SASProc.average(sasm_list)
                else:
                    avg_sasm = SASProc.weightedAverage(sasm_list, weightByError, weightCounter)

            elif profiles_to_use == wx.ID_YES:
                reduced_sasm_list = [sasm_list[0]]
                for i, sasm in enumerate(sasm_list[1:]):
                    if pvals[i] >= threshold:
                        reduced_sasm_list.append(sasm)

                if not weight:
                    avg_sasm = SASProc.average(sasm_list)
                else:
                    avg_sasm = SASProc.weightedAverage(sasm_list, weightByError, weightCounter)

        except SASExceptions.DataNotCompatible:
            wx.CallAfter(self._showAverageError, 3)
            return None

        self._insertSasmFilenamePrefix(avg_sasm, 'A_')

        return avg_sasm

    def _averageItems(self, item_list):

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while averaging and plotting...')

        sasm_list = []

        if len(item_list) < 2:
            wx.CallAfter(self._showAverageError, 2)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        for each_item in item_list:
            sasm_list.append(each_item.getSASM())

        avg_sasm = self._average(sasm_list)

        if avg_sasm is not None:
            self._sendSASMToPlot(avg_sasm, axes_num = 1, item_colour = 'forest green', notsaved = True)

            do_auto_save = self._raw_settings.get('AutoSaveOnAvgFiles')

            if do_auto_save:
                save_path = self._raw_settings.get('AveragedFilePath')

                try:
                    self._saveSASM(avg_sasm, '.dat', save_path)
                except IOError as e:
                    self._raw_settings.set('AutoSaveOnAvgFiles', False)
                    msg = (str(e) + '\n\nAutosave of averaged images has been '
                        'disabled. If you are using a config file from a '
                        'different computer please go into Advanced '
                        'Options/Autosave to change the save folders, or '
                        'save you config file to avoid this message next time.')
                    wx.CallAfter(self._showGenericError, msg, 'Autosave Error')

        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _averageItemSeries(self, sasm_list):
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while averaging and plotting...')

        if len(sasm_list) < 2:
            wx.CallAfter(self._showAverageError, 2)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        avg_sasm = self._average(sasm_list)

        if avg_sasm is not None:
            self._sendSASMToPlot(avg_sasm, axes_num = 1, item_colour = 'forest green', notsaved = True)

            do_auto_save = self._raw_settings.get('AutoSaveOnAvgFiles')

            if do_auto_save:
                save_path = self._raw_settings.get('AveragedFilePath')

                try:
                    self._saveSASM(avg_sasm, '.dat', save_path)
                except IOError as e:
                    self._raw_settings.set('AutoSaveOnAvgFiles', False)
                    msg = (str(e) + '\n\nAutosave of averaged images has been '
                        'disabled. If you are using a config file from a '
                        'different computer please go into Advanced '
                        'Options/Autosave to change the save folders, or '
                        'save you config file to avoid this message next time.')
                    wx.CallAfter(self._showGenericError, msg, 'Autosave Error')

        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _weightedAverageItems(self, item_list):

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while averaging and plotting...')

        sasm_list = []

        if len(item_list) < 2:
            self._showAverageError(2)
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        for each_item in item_list:
            sasm_list.append(each_item.getSASM())

        weightByError = self._raw_settings.get('weightByError')
        weightCounter = self._raw_settings.get('weightCounter')

        if not weightByError and weightCounter == '':
            msg = ('An appropriate counter to weight the data is not '
                'selected and error weighting is not enabled. Weighted '
                'average aborted.')
            wx.CallAfter(self._showGenericError, msg, 'Weighted Average Error')
            wx.CallAfter(self.main_frame.closeBusyDialog)
            return

        if not weightByError:
            has_header = []

            for each_sasm in sasm_list:
                header_keys = []
                if each_sasm.getAllParameters().has_key('counters'):
                    file_hdr = each_sasm.getParameter('counters')
                    header_keys = header_keys + file_hdr.keys()
                if each_sasm.getAllParameters().has_key('imageHeader'):
                    img_hdr = each_sasm.getParameter('imageHeader')
                    header_keys = header_keys + img_hdr.keys()

                if weightCounter in header_keys:
                    has_header.append(True)
                else:
                    has_header.append(False)

            if not np.all(has_header):
                msg = ('Not all selected items had the counter value '
                    'selected as the weight. Weighted average aborted.')
                wx.CallAfter(self._showGenericError, msg, 'Weighted Average Error')
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return

        avg_sasm = self._average(sasm_list, weight=True,
            weightByError=weightByError, weightCounter=weightCounter)

        if avg_sasm is not None:

            self._sendSASMToPlot(avg_sasm, axes_num = 1, item_colour = 'forest green', notsaved = True)

            do_auto_save = self._raw_settings.get('AutoSaveOnAvgFiles')

            if do_auto_save:
                save_path = self._raw_settings.get('AveragedFilePath')

                try:
                    self._saveSASM(avg_sasm, '.dat', save_path)
                except IOError as e:
                    self._raw_settings.set('AutoSaveOnAvgFiles', False)
                    msg = (str(e) + '\n\nAutosave of averaged images has been '
                        'disabled. If you are using a config file from a '
                        'different computer please go into Advanced '
                        'Options/Autosave to change the save folders, or '
                        'save you config file to avoid this message next time.')
                    wx.CallAfter(self._showGenericError, msg, 'Autosave Error')

        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _rebinItems(self, data):

        selected_items = data[0]
        rebin_factor = data[1]
        log_rebin = data[2]

        for each in selected_items:
            sasm = each.getSASM()

            points = np.floor(len(sasm.q) / rebin_factor)

            if log_rebin:
                rebin_sasm = SASProc.logBinning(sasm, points)
            else:
                rebin_sasm = SASProc.rebin(sasm, rebin_factor)

            self._insertSasmFilenamePrefix(rebin_sasm, 'R_')

            self._sendSASMToPlot(rebin_sasm, axes_num = 1, notsaved = True)

    def _insertSasmFilenamePrefix(self, sasm, prefix = '', extension = ''):
        filename = sasm.getParameter('filename')
        new_filename, ext = os.path.splitext(filename)
        sasm.setParameter('filename', prefix + new_filename + extension)

    def _mergeItems(self, data):

        marked_item = data[0]
        selected_items = data[1]

        if marked_item in selected_items:
            idx = selected_items.index(marked_item)
            selected_items.pop(idx)

        if marked_item == None:
            wx.CallAfter(self._showPleaseMarkItemError, 'merge')
            return

        marked_sasm = marked_item.getSASM()
        sasm_list = []
        for each_item in selected_items:
            sasm_list.append(each_item.getSASM())

        merged_sasm = SASProc.merge(marked_sasm, sasm_list)

        filename = marked_sasm.getParameter('filename')
        merged_sasm.setParameter('filename', filename)
        self._insertSasmFilenamePrefix(merged_sasm, 'M_')

        self._sendSASMToPlot(merged_sasm, axes_num = 1, notsaved = True)

    def _interpolateItems(self, data):
        marked_item = data[0]
        selected_items = data[1]

        if marked_item in selected_items:
            idx = selected_items.index(marked_item)
            selected_items.pop(idx)

        if marked_item == None:
            wx.CallAfter(self._showPleaseMarkItemError, 'interpolate')
            return

        marked_sasm = marked_item.getSASM()
        sasm_list = []

        for each_item in selected_items:
            sasm = each_item.getSASM()

            interpolate_sasm = SASProc.interpolateToFit(marked_sasm, sasm)

            filename = sasm.getParameter('filename')
            interpolate_sasm.setParameter('filename', filename)

            self._insertSasmFilenamePrefix(interpolate_sasm, 'I_')

            sasm_list.append(interpolate_sasm)

        self._sendSASMToPlot(sasm_list, axes_num = 1, notsaved = True)


    def _saveSASM(self, sasm, filetype = 'dat', save_path = ''):

        if self.main_frame.OnlineControl.isRunning() and save_path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving dat item(s)', 0)

        newext = filetype

        filename = sasm.getParameter('filename')
        check_filename, ext = os.path.splitext(filename)
        check_filename = check_filename + newext

        filepath = os.path.join(save_path, check_filename)
        # file_exists = os.path.isfile(filepath)
        filepath = save_path

        try:
            SASFileIO.saveMeasurement(sasm, filepath, self._raw_settings, filetype = newext)
        except SASExceptions.HeaderSaveError:
            wx.CallAfter(self._showSaveError, 'header')

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [check_filename])
            wx.CallAfter(self.main_frame.controlTimer, True)


    def _saveIFTM(self, data):

        sasm = data[0]
        save_path = data[1]

        if self.main_frame.OnlineControl.isRunning() and save_path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving ift item(s)', 0)

        if sasm.getParameter('algorithm') == 'GNOM':
            newext = '.out'
        else:
            newext = '.ift'

        filename = sasm.getParameter('filename')

        check_filename, ext = os.path.splitext(filename)

        check_filename = check_filename + newext

        filepath = os.path.join(save_path, check_filename)
        # file_exists = os.path.isfile(filepath)
        filepath = save_path

        try:
            SASFileIO.saveMeasurement(sasm, filepath, self._raw_settings, filetype = newext)
        except SASExceptions.HeaderSaveError:
            wx.CallAfter(self._showSaveError, 'header')

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAFter(self.main_frame.OnlineControl.updateSkipList, [check_filename])
            wx.CallAfter(self.main_frame.controlTimer, True)


    def _saveAnalysisInfo(self, data):
        #Saves selected analysis info
        all_items = data[0]
        include_data = data[1]
        save_path = data[2]

        if self.main_frame.OnlineControl.isRunning() and os.path.split(save_path)[0] == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving analysis info', 0)

        selected_sasms = []

        check_filename, ext = os.path.splitext(save_path)
        save_path = check_filename + '.csv'

        for each_item in all_items:
            sasm = each_item.getSASM()
            selected_sasms.append(sasm)

        SASFileIO.saveAnalysisCsvFile(selected_sasms, include_data, save_path)

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [os.path.split(save_path)[1]])
            wx.CallAfter(self.main_frame.controlTimer, True)

    def _saveAllAnalysisInfo(self, data):

        save_path, selected_sasms = data[0], data[1]

        if self.main_frame.OnlineControl.isRunning() and os.path.split(save_path)[0] == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving analysis info', 0)

        SASFileIO.saveAllAnalysisData(save_path, selected_sasms)

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [os.path.split(save_path)[1]])
            wx.CallAfter(self.main_frame.controlTimer, True)


    def _saveWorkspace(self, data):
        sasm_items = data[0]
        ift_items = data[1]
        secm_items = data[2]
        save_path = data[3]

        if self.main_frame.OnlineControl.isRunning() and os.path.split(save_path)[0] == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving workspace', 0)


        save_dict = OrderedDict()

        for idx in range(0, len(sasm_items)):

            sasm = sasm_items[idx].getSASM()
            sasm_dict = sasm.extractAll()

            sasm_dict['line_color'] = sasm.line.get_color()
            sasm_dict['line_width'] = sasm.line.get_linewidth()
            sasm_dict['line_style'] = sasm.line.get_linestyle()
            sasm_dict['line_marker'] = sasm.line.get_marker()
            sasm_dict['line_marker_face_color'] = sasm.line.get_markerfacecolor()
            sasm_dict['line_marker_edge_color'] = sasm.line.get_markeredgecolor()
            sasm_dict['line_errorbar_color'] = sasm.err_line[0][0].get_color()
            sasm_dict['line_visible'] = sasm.line.get_visible()
            if sasm.line.get_label() != sasm_dict['parameters']['filename']:
                sasm_dict['line_legend_label'] = sasm.line.get_label()
            else:
                sasm_dict['line_legend_label'] = ''

            sasm_dict['item_controls_visible'] = sasm.item_panel.getControlsVisible()
            sasm_dict['item_font_color'] = sasm.item_panel.getFontColour()
            sasm_dict['item_selected_for_plot'] = sasm.item_panel.getSelectedForPlot()

            sasm_dict['parameters_analysis'] = sasm_dict['parameters']['analysis']  #pickle wont save this unless its raised up

            if sasm.axes == sasm.plot_panel.subplot1:
                sasm_dict['plot_axes'] = 1
            else:
                sasm_dict['plot_axes'] = 2

            save_dict['sasm_'+str(idx)] = sasm_dict

        for idx in range(0, len(ift_items)):

            iftm = ift_items[idx].getIFTM()
            iftm_dict = iftm.extractAll()

            iftm_dict['r_line_color'] = iftm.r_line.get_color()
            iftm_dict['r_line_width'] = iftm.r_line.get_linewidth()
            iftm_dict['r_line_style'] = iftm.r_line.get_linestyle()
            iftm_dict['r_line_marker'] = iftm.r_line.get_marker()
            iftm_dict['r_line_marker_face_color'] = iftm.r_line.get_markerfacecolor()
            iftm_dict['r_line_marker_edge_color'] = iftm.r_line.get_markeredgecolor()
            iftm_dict['r_line_errorbar_color'] = iftm.r_err_line[0][0].get_color()
            iftm_dict['r_line_visible'] = iftm.r_line.get_visible()
            if iftm.r_line.get_label() != iftm_dict['parameters']['filename']+'_P(r)':
                iftm_dict['r_line_legend_label'] = iftm.r_line.get_label()
            else:
                iftm_dict['r_line_legend_label'] = ''

            iftm_dict['qo_line_color'] = iftm.qo_line.get_color()
            iftm_dict['qo_line_width'] = iftm.qo_line.get_linewidth()
            iftm_dict['qo_line_style'] = iftm.qo_line.get_linestyle()
            iftm_dict['qo_line_marker'] = iftm.qo_line.get_marker()
            iftm_dict['qo_line_marker_face_color'] = iftm.qo_line.get_markerfacecolor()
            iftm_dict['qo_line_marker_edge_color'] = iftm.qo_line.get_markeredgecolor()
            iftm_dict['qo_line_errorbar_color'] = iftm.qo_err_line[0][0].get_color()
            iftm_dict['qo_line_visible'] = iftm.qo_line.get_visible()
            if iftm.qo_line.get_label() != iftm_dict['parameters']['filename']+'_Exp':
                iftm_dict['qo_line_legend_label'] = iftm.qo_line.get_label()
            else:
                iftm_dict['qo_line_legend_label'] = ''

            iftm_dict['qf_line_color'] = iftm.qf_line.get_color()
            iftm_dict['qf_line_width'] = iftm.qf_line.get_linewidth()
            iftm_dict['qf_line_style'] = iftm.qf_line.get_linestyle()
            iftm_dict['qf_line_marker'] = iftm.qf_line.get_marker()
            iftm_dict['qf_line_marker_face_color'] = iftm.qf_line.get_markerfacecolor()
            iftm_dict['qf_line_marker_edge_color'] = iftm.qf_line.get_markeredgecolor()
            iftm_dict['qf_line_visible'] = iftm.qf_line.get_visible()
            if iftm.qo_line.get_label() != iftm_dict['parameters']['filename']+'_Fit':
                iftm_dict['qf_line_legend_label'] = iftm.qf_line.get_label()
            else:
                iftm_dict['qf_line_legend_label'] = ''

            iftm_dict['item_font_color'] = iftm.item_panel.getFontColour()
            iftm_dict['item_selected_for_plot'] = iftm.item_panel.getSelectedForPlot()

            save_dict['iftm_'+str(idx)] = iftm_dict


        for idx in range(0, len(secm_items)):

            secm = secm_items[idx].getSECM()
            secm_dict = secm.extractAll()

            secm_dict['line_color'] = secm.line.get_color()
            secm_dict['line_width'] = secm.line.get_linewidth()
            secm_dict['line_style'] = secm.line.get_linestyle()
            secm_dict['line_marker'] = secm.line.get_marker()
            secm_dict['line_marker_face_color'] = secm.line.get_markerfacecolor()
            secm_dict['line_marker_edge_color'] = secm.line.get_markeredgecolor()
            secm_dict['line_visible'] = secm.line.get_visible()
            secm_dict['line_legend_label'] = secm.line.get_label()

            secm_dict['calc_line_color'] = secm.calc_line.get_color()
            secm_dict['calc_line_width'] = secm.calc_line.get_linewidth()
            secm_dict['calc_line_style'] = secm.calc_line.get_linestyle()
            secm_dict['calc_line_marker'] = secm.calc_line.get_marker()
            secm_dict['calc_line_marker_face_color'] = secm.calc_line.get_markerfacecolor()
            secm_dict['calc_line_marker_edge_color'] = secm.calc_line.get_markeredgecolor()
            secm_dict['calc_line_visible'] = secm.calc_line.get_visible()
            secm_dict['calc_line_legend_label'] = secm.calc_line.get_label()

            secm_dict['item_font_color'] = secm.item_panel.getFontColour()
            secm_dict['item_selected_for_plot'] = secm.item_panel.getSelectedForPlot()

            secm_dict['parameters_analysis'] = secm_dict['parameters']['analysis']  #pickle wont save this unless its raised up

            save_dict['secm_'+str(idx)] = secm_dict

        SASFileIO.saveWorkspace(save_dict, save_path)

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [os.path.split(save_path)[1]])
            wx.CallAfter(self.main_frame.controlTimer, True)

    def _loadWorkspace(self, data):

        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait while loading workspace...')

        load_path = data[0]

        try:
            item_dict = SASFileIO.loadWorkspace(load_path)
        except SASExceptions.UnrecognizedDataFormat:
            wx.CallAfter(self.main_frame.closeBusyDialog)
            msg = ('The workspace could not be loaded. It may be an invalid '
                'file type, or the file may be corrupted.')
            wx.CallAfter(wx._showGenericError, msg, 'Workspace Load Error')
            return

        if type(item_dict) == OrderedDict:
            keylist = item_dict.keys()
        else:
            keylist = sorted(item_dict.keys())

        for each_key in keylist:
            if str(each_key).startswith('secm'):

                secm_data = item_dict[each_key]

                new_secm, line_data, calc_line_data = SASFileIO.makeSeriesFile(secm_data)

                new_secm.is_visible = secm_data['line_visible']

                wx.CallAfter(self.sec_plot_panel.plotSECM, new_secm,
                              color = secm_data['line_color'],
                              line_data = line_data,
                              calc_line_data = calc_line_data)

                while new_secm.line is None or new_secm.calc_line is None:
                    time.sleep(0.001)

                #Backwards compatibility
                try:
                    legend_label = {new_secm.line:      secm_data['line_legend_label'],
                                    new_secm.calc_line: secm_data['calc_line_legend_label']
                                    }
                except:
                    legend_label = defaultdict(str)

                wx.CallAfter(self.sec_item_panel.addItem, new_secm,
                              item_colour = secm_data['item_font_color'],
                              item_visible = secm_data['item_selected_for_plot'],
                              legend_label=legend_label)

            elif str(each_key).startswith('ift'):
                iftm_data = item_dict[each_key]
                p = iftm_data['p_raw']
                r = iftm_data['r_raw']
                err = iftm_data['err_raw']
                i_orig = iftm_data['i_orig_raw']
                q_orig = iftm_data['q_orig_raw']
                err_orig = iftm_data['err_orig_raw']
                i_fit = iftm_data['i_fit_raw']
                parameters = iftm_data['parameters']
                i_extrap = iftm_data['i_extrap_raw']
                q_extrap = iftm_data['q_extrap_raw']

                new_iftm = SASM.IFTM(p, r, err, i_orig, q_orig, err_orig, i_fit, parameters, i_extrap, q_extrap)

                new_iftm.setQrange(iftm_data['selected_qrange'])

                line_data = {}
                line_data['r_line_color'] = iftm_data['r_line_color']
                line_data['r_line_width'] = iftm_data['r_line_width']
                line_data['r_line_style'] = iftm_data['r_line_style']
                line_data['r_line_marker'] = iftm_data['r_line_marker']
                line_data['r_line_visible'] = iftm_data['r_line_visible']

                line_data['qo_line_color'] = iftm_data['qo_line_color']
                line_data['qo_line_width'] = iftm_data['qo_line_width']
                line_data['qo_line_style'] = iftm_data['qo_line_style']
                line_data['qo_line_marker'] = iftm_data['qo_line_marker']
                line_data['qo_line_visible'] = iftm_data['qo_line_visible']

                line_data['qf_line_color'] = iftm_data['qf_line_color']
                line_data['qf_line_width'] = iftm_data['qf_line_width']
                line_data['qf_line_style'] = iftm_data['qf_line_style']
                line_data['qf_line_marker'] = iftm_data['qf_line_marker']
                line_data['qf_line_visible'] = iftm_data['qf_line_visible']

                try:
                    line_data['r_line_marker_edge_color'] = iftm_data['r_line_marker_edge_color']
                    line_data['r_line_marker_face_color'] = iftm_data['r_line_marker_face_color']
                    line_data['r_line_errorbar_color'] = iftm_data['r_line_errorbar_color']
                    line_data['qo_line_marker_edge_color'] = iftm_data['qo_line_marker_edge_color']
                    line_data['qo_line_marker_face_color'] = iftm_data['qo_line_marker_face_color']
                    line_data['qo_line_errorbar_color'] = iftm_data['qo_line_errorbar_color']
                    line_data['qf_line_marker_edge_color'] = iftm_data['qf_line_marker_edge_color']
                    line_data['qf_line_marker_face_color'] = iftm_data['qf_line_marker_face_color']

                except KeyError:
                    pass #Workspaces <1.3.0 won't have these keys

                wx.CallAfter(self.ift_plot_panel.plotIFTM, new_iftm, line_data = line_data)

                while new_iftm.r_line is None or new_iftm.qo_line is None or new_iftm.qf_line is None:
                    time.sleep(0.001)

                #Backwards compatibility
                try:
                    legend_label = {new_iftm.r_line:    iftm_data['r_line_legend_label'],
                                    new_iftm.qo_line:   iftm_data['qo_line_legend_label'],
                                    new_iftm.qf_line:   iftm_data['qf_line_legend_label']
                                    }
                except:
                    legend_label = defaultdict(str)

                wx.CallAfter(self.ift_item_panel.addItem, new_iftm,
                              item_colour = iftm_data['item_font_color'],
                              item_visible = iftm_data['item_selected_for_plot'],
                              legend_label=legend_label)

            else:
                #Backwards compatability requires us to not test the sasm prefix
                sasm_data = item_dict[each_key]

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

                try:
                    line_data = {'line_color' : sasm_data['line_color'],
                                 'line_width' : sasm_data['line_width'],
                                 'line_style' : sasm_data['line_style'],
                                 'line_marker': sasm_data['line_marker'],
                                 'line_visible' :sasm_data['line_visible']}
                except KeyError:
                    line_data = None    #Backwards compatibility
                    sasm_data['line_visible'] = True

                try:
                    line_data['line_marker_edge_color'] = sasm_data['line_marker_edge_color']
                    line_data['line_marker_face_color'] = sasm_data['line_marker_face_color']
                    line_data['line_errorbar_color'] = sasm_data['line_errorbar_color']
                except KeyError:
                    pass #Workspaces <1.3.0 won't have these keys

                wx.CallAfter(self.plot_panel.plotSASM, new_sasm,
                              sasm_data['plot_axes'], color = sasm_data['line_color'],
                              line_data = line_data)

                #Backwards compatibility
                try:
                    legend_label = sasm_data['line_legend_label']
                except KeyError:
                    legend_label = ''

                wx.CallAfter(self.manipulation_panel.addItem, new_sasm,
                              item_colour = sasm_data['item_font_color'],
                              item_visible = sasm_data['item_selected_for_plot'],
                              legend_label = legend_label)

        wx.CallAfter(self.plot_panel.updateLegend, 1, False)
        wx.CallAfter(self.plot_panel.updateLegend, 2, False)
        wx.CallAfter(self.plot_panel.fitAxis)

        wx.CallAfter(self.ift_plot_panel.updateLegend, 1, False)
        wx.CallAfter(self.ift_plot_panel.updateLegend, 2, False)
        wx.CallAfter(self.ift_plot_panel.fitAxis)

        wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)
        wx.CallAfter(self.sec_plot_panel.fitAxis)

        wx.CallAfter(self.main_frame.closeBusyDialog)

    def _saveIftItems(self, data):
        self._saveItems(data, iftmode=True)

    def _saveSeriesData(self,data):
        save_path, selected_items = data[0], data[1]

        if self.main_frame.OnlineControl.isRunning() and os.path.split(save_path[0])[0] == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving series data', 0)

        overwrite_all = False
        no_to_all = False

        for b in range(len(selected_items)):

            selected_secm = selected_items[b].secm

            filepath = save_path[b]
            file_exists = os.path.isfile(filepath)

            if file_exists and overwrite_all == False:
                if no_to_all == False:
                    result = self._showOverwritePrompt(os.path.split(filepath)[1], os.path.split(filepath)[0])

                if result[0] == wx.ID_CANCEL:
                    RAWGlobals.save_in_progress = False
                    wx.CallAfter(self.main_frame.setStatus, '', 0)

                    if restart_timer:
                        wx.CallAfter(self.main_frame.controlTimer, True)
                    return

                if result[0] == wx.ID_EDIT:
                    filepath = result[1][0]

                if result[0] == wx.ID_YES or result[0] == wx.ID_YESTOALL or result[0] == wx.ID_EDIT:
                    SASFileIO.saveSeriesData(save_path[b], selected_secm)

                if result[0] == wx.ID_YESTOALL:
                    overwrite_all = True

                if result[0] == wx.ID_NOTOALL:
                    no_to_all = True

            else:
                SASFileIO.saveSeriesData(save_path[b], selected_secm)

            if restart_timer:
                self.main_frame.OnlineControl.updateSkipList([os.path.split(save_path[b])[1]])

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

    def _saveSECItem(self,data):
        save_path, selected_items = data[0], data[1]

        if self.main_frame.OnlineControl.isRunning() and os.path.split(save_path[0])[0] == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving series item(s)', 0)

        overwrite_all = False
        no_to_all = False

        for b in range(len(selected_items)):

            item = selected_items[b]
            secm = item.secm

            secm_dict = secm.extractAll()

            secm_dict['line_color'] = secm.line.get_color()
            secm_dict['line_width'] = secm.line.get_linewidth()
            secm_dict['line_style'] = secm.line.get_linestyle()
            secm_dict['line_marker'] = secm.line.get_marker()
            secm_dict['line_visible'] = secm.line.get_visible()

            secm_dict['calc_line_color'] = secm.calc_line.get_color()
            secm_dict['calc_line_width'] = secm.calc_line.get_linewidth()
            secm_dict['calc_line_style'] = secm.calc_line.get_linestyle()
            secm_dict['calc_line_marker'] = secm.calc_line.get_marker()
            secm_dict['calc_line_visible'] = secm.calc_line.get_visible()

            secm_dict['item_font_color'] = secm.item_panel.getFontColour()
            secm_dict['item_selected_for_plot'] = secm.item_panel.getSelectedForPlot()

            secm_dict['parameters_analysis'] = secm_dict['parameters']['analysis']  #pickle wont save this unless its raised up

            filepath = save_path[b]

            file_exists = os.path.isfile(filepath)

            if file_exists and overwrite_all == False:

                if no_to_all == False:
                    result = self._showOverwritePrompt(os.path.split(filepath)[1], os.path.split(filepath)[0])

                if result[0] == wx.ID_CANCEL:
                    RAWGlobals.save_in_progress = False
                    wx.CallAfter(self.main_frame.setStatus, '', 0)
                    wx.CallAfter(secm.item_panel.parent.Refresh)
                    wx.CallAfter(secm.item_panel.parent.Layout)

                    wx.CallAfter(secm.plot_panel.updateLegend, 1)
                    if restart_timer:
                        wx.CallAfter(self.main_frame.controlTimer, True)
                    return

                if result[0] == wx.ID_EDIT:
                    filepath = result[1][0]
                    path, new_filename = os.path.split(filepath)
                    secm.setParameter('filename', new_filename)

                if result[0] == wx.ID_YES or result[0] == wx.ID_YESTOALL or result[0] == wx.ID_EDIT:
                    SASFileIO.saveSECItem(filepath, secm_dict)
                    filename, ext = os.path.splitext(secm.getParameter('filename'))
                    secm.setParameter('filename', filename+'.sec')
                    wx.CallAfter(secm.item_panel.updateFilenameLabel, updateParent = False,  updateLegend = False)
                    wx.CallAfter(item.unmarkAsModified, updateParent = False)

                if result[0] == wx.ID_YESTOALL:
                    overwrite_all = True

                if result[0] == wx.ID_NOTOALL:
                    no_to_all = True

            else:
                SASFileIO.saveSECItem(filepath, secm_dict)
                filename, ext = os.path.splitext(secm.getParameter('filename'))
                secm.setParameter('filename', filename+'.sec')
                wx.CallAfter(secm.item_panel.updateFilenameLabel, updateParent = False,  updateLegend = False)
                wx.CallAfter(item.unmarkAsModified, updateParent = False)


            if restart_timer:
                wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [os.path.split(save_path[b])[1]])

        wx.CallAfter(secm.item_panel.parent.Refresh)
        wx.CallAfter(secm.item_panel.parent.Layout)

        wx.CallAfter(secm.plot_panel.updateLegend, 1)

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

    def _saveSECProfiles(self, data):
        wx.CallAfter(self.main_frame.showBusyDialog, 'Please wait, saving profiles...')

        save_path = data[0]
        item_list = data[1]

        if self.main_frame.OnlineControl.isRunning() and save_path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving series profile(s)', 0)

        overwrite_all = False
        no_to_all = False
        for item in item_list:
            sasm = item

            filename = sasm.getParameter('filename')

            check_filename, ext = os.path.splitext(filename)

            newext = '.dat'

            check_filename = check_filename + newext

            filepath = os.path.join(save_path, check_filename)
            file_exists = os.path.isfile(filepath)
            filepath = save_path

            if file_exists and overwrite_all == False:

                if no_to_all == False:
                    result = self._showOverwritePrompt(check_filename, save_path)

                    if result[0] == wx.ID_CANCEL:
                        RAWGlobals.save_in_progress = False
                        wx.CallAfter(self.main_frame.setStatus, '', 0)

                        if restart_timer:
                            wx.CallAfter(self.main_frame.controlTimer, True)

                        wx.CallAfter(self.main_frame.closeBusyDialog)
                        return

                    if result[0] == wx.ID_EDIT: #rename
                        filepath = result[1][0]
                        filepath, new_filename = os.path.split(filepath)
                        sasm.setParameter('filename', new_filename)

                    if result[0] == wx.ID_YES or result[0] == wx.ID_YESTOALL or result[0] == wx.ID_EDIT:
                        try:
                            SASFileIO.saveMeasurement(sasm, filepath, self._raw_settings, filetype = newext)
                        except SASExceptions.HeaderSaveError:
                            wx.CallAfter(self._showSaveError, 'header')
                        filename, ext = os.path.splitext(sasm.getParameter('filename'))
                        sasm.setParameter('filename', filename + newext)

                    if result[0] == wx.ID_YESTOALL:
                        overwrite_all = True

                    if result[0] == wx.ID_NOTOALL:
                        no_to_all = True

            else:
                try:
                    SASFileIO.saveMeasurement(sasm, filepath, self._raw_settings, filetype = newext)
                except SASExceptions.HeaderSaveError:
                    wx.CAllAfter(self._showSaveError, 'header')
                filename, ext = os.path.splitext(sasm.getParameter('filename'))
                sasm.setParameter('filename', filename + newext)

            if restart_timer:
                wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [check_filename])

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)

        wx.CallAfter(self.main_frame.closeBusyDialog)


    def _normalizeByConc(self, data):
        selected_items = data[0]

        for each in selected_items:
            sasm = each.getSASM()

            if sasm.getAllParameters().has_key('Conc'):
                conc = sasm.getParameter('Conc')

                try:
                    conc = float(conc)

                    scale = 1/conc
                    sasm.scaleRelative(scale)
                    wx.CallAfter(each.updateControlsFromSASM)

                except ValueError:
                    continue


    def _saveItems(self, data, iftmode = False):
        save_path = data[0]
        item_list = data[1]

        if self.main_frame.OnlineControl.isRunning() and save_path == self.main_frame.OnlineControl.getTargetDir():
            self.main_frame.controlTimer(False)
            restart_timer = True
        else:
            restart_timer = False

        RAWGlobals.save_in_progress = True
        wx.CallAfter(self.main_frame.setStatus, 'Saving item(s)', 0)

        if not iftmode:
            axes_update_list = []

        overwrite_all = False
        no_to_all = False
        for item in item_list:

            if iftmode:
                sasm = item.iftm
            else:
                sasm = item.sasm

            filename = sasm.getParameter('filename')

            check_filename, ext = os.path.splitext(filename)

            if iftmode:
                if sasm.getParameter('algorithm') == 'GNOM':
                    newext = '.out'
                else:
                    newext = '.ift'
            else:
                newext = '.dat'

            check_filename = check_filename + newext

            filepath = os.path.join(save_path, check_filename)
            file_exists = os.path.isfile(filepath)
            filepath = save_path

            if file_exists and overwrite_all == False:

                if no_to_all == False:
                    result = self._showOverwritePrompt(check_filename, save_path)

                    if result[0] == wx.ID_CANCEL:
                        wx.CallAfter(sasm.item_panel.parent.Refresh)
                        wx.CallAfter(sasm.item_panel.parent.Layout)

                        if iftmode:
                            wx.CallAfter(sasm.item_panel.ift_plot_panel.updateLegend, 1)
                            wx.CallAfter(sasm.item_panel.ift_plot_panel.updateLegend, 2)
                        else:
                            axes_update_list = set(axes_update_list)

                            for axis in axes_update_list:
                                wx.CallAfter(sasm.item_panel.plot_panel.updateLegend, axis)

                        RAWGlobals.save_in_progress = False
                        wx.CallAfter(self.main_frame.setStatus, '', 0)

                        if restart_timer:
                            wx.CallAfter(self.main_frame.controlTimer, True)
                        return

                    if result[0] == wx.ID_EDIT: #rename
                        filepath = result[1]
                        filepath, new_filename = os.path.split(filepath)
                        sasm.setParameter('filename', new_filename)

                    if result[0] == wx.ID_YES or result[0] == wx.ID_YESTOALL or result[0] == wx.ID_EDIT:
                        try:
                            SASFileIO.saveMeasurement(sasm, filepath, self._raw_settings, filetype = newext)
                        except SASExceptions.HeaderSaveError:
                            self._showSaveError('header')
                        filename, ext = os.path.splitext(sasm.getParameter('filename'))
                        sasm.setParameter('filename', filename + newext)

                        wx.CallAfter(sasm.item_panel.updateFilenameLabel, updateParent = False,  updateLegend = False)
                        wx.CallAfter(item.unmarkAsModified, updateParent = False)

                        if not iftmode:
                            axes_update_list.append(sasm.axes)

                    if result[0] == wx.ID_YESTOALL:
                        overwrite_all = True

                    if result[0] == wx.ID_NOTOALL:
                        no_to_all = True

            else:
                try:
                    SASFileIO.saveMeasurement(sasm, filepath, self._raw_settings, filetype = newext)
                except SASExceptions.HeaderSaveError:
                    self._showSaveError('header')
                filename, ext = os.path.splitext(sasm.getParameter('filename'))
                sasm.setParameter('filename', filename + newext)

                wx.CallAfter(sasm.item_panel.updateFilenameLabel, updateParent = False, updateLegend = False)
                wx.CallAfter(item.unmarkAsModified, updateParent = False)

                if not iftmode:
                    axes_update_list.append(sasm.axes)

            if restart_timer:
                wx.CallAfter(self.main_frame.OnlineControl.updateSkipList, [check_filename])

        wx.CallAfter(sasm.item_panel.parent.Refresh)
        wx.CallAfter(sasm.item_panel.parent.Layout)

        if iftmode:
            wx.CallAfter(sasm.item_panel.ift_plot_panel.updateLegend, 1)
            wx.CallAfter(sasm.item_panel.ift_plot_panel.updateLegend, 2)
        else:
            axes_update_list = set(axes_update_list)

            for axis in axes_update_list:
                wx.CallAfter(sasm.item_panel.plot_panel.updateLegend, axis)

        RAWGlobals.save_in_progress = False
        wx.CallAfter(self.main_frame.setStatus, '', 0)

        if restart_timer:
            wx.CallAfter(self.main_frame.controlTimer, True)


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
        self.sec_panel = wx.FindWindowByName('SECPanel')
        self.sec_plot_panel = wx.FindWindowByName('SECPlotPanel')
        self.ift_panel = wx.FindWindowByName('IFTPanel')
        self.ift_plot_panel = wx.FindWindowByName('IFTPlotPanel')


        # *************** buttons ****************************
        self.dir_panel = DirCtrlPanel(self)

        self.button_data = ( ("Quick Reduce", self._onReduceButton),
                           ("Plot", self._onPlotButton),
                           ("Clear All", self._onClearAllButton),
                           ("System Viewer", self._onViewButton),
                           ("Show Image", self._onShowImageButton),
                           ("Plot Series", self._onPlotSECButton))

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
        no_of_rows = int(np.ceil(no_of_buttons / self.NO_OF_BUTTONS_IN_EACH_ROW))

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


    def _fileTypeIsCompatible(self, path):
        root, ext = os.path.splitext(path)

        compatible_formats = self.main_frame.getRawSettings().get('CompatibleFormats')

        if str(ext) in compatible_formats:
            return True
        else:
            return False

    def _onViewButton(self, event):

        filelist = wx.FindWindowByName('FileListCtrl')
        filelist.openFileInExternalViewer()

    def _onPlotButton(self, event):

        files = []

        for each_filename in self.dir_panel.file_list_box.getSelectedFilenames():
            if each_filename != '..':
                path = os.path.join(self.dir_panel.file_list_box.path, each_filename)

                if not os.path.isdir(path):
                    files.append(path)

        if files:
            mainworker_cmd_queue.put(['plot', files])

    def _onPlotSECButton(self, event):

        files = []

        for each_filename in self.dir_panel.file_list_box.getSelectedFilenames():
            if each_filename != '..':
                path = os.path.join(self.dir_panel.file_list_box.path, each_filename)

                if not os.path.isdir(path):
                    files.append(path)

        if files:
            frame_list = range(len(files))

            mainworker_cmd_queue.put(['sec_plot', [files, frame_list]])

    def _onClearAllButton(self, event):

        dial = wx.MessageDialog(self, 'Are you sure you want to clear everything?', 'Are you sure?',
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)

        answer = dial.ShowModal()
        dial.Destroy()

        if answer == wx.ID_CANCEL or answer == wx.ID_NO:
            return
        else:
            answer2 = wx.ID_YES

            info_panel = wx.FindWindowByName('InformationPanel')
            info_panel.clearInfo()

            if self.manipulation_panel.modified_items != [] or self.sec_panel.modified_items != [] or self.ift_panel.modified_items !=[]:

                msg_list = []
                if self.manipulation_panel.modified_items !=[]:
                    msg_list.append('Manipulation')

                if self.sec_panel.modified_items != []:
                    msg_list.append('Series')

                if self.ift_panel.modified_items != []:
                    msg_list.append('IFT')

                if len(msg_list) == 1:
                    message = msg_list[0]
                elif len(msg_list) == 2:
                    message = ' and '.join(msg_list)
                else:
                    message = ', '.join(msg_list[:-1]) + ' and ' + msg_list[-1]



                dial2 = wx.MessageDialog(self, 'You have unsaved changes in your ' + message + ' data. Do you want to discard these changes?', 'Discard changes?',
                                         wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
                answer2 = dial2.ShowModal()
                dial2.Destroy()

            if answer2 == wx.ID_YES:
                self.image_panel.clearFigure()
                self.plot_panel.clearAllPlots()
                self.manipulation_panel.clearList()
                self.ift_plot_panel.clearAllPlots()
                self.ift_panel.clearList()
                self.sec_plot_panel.clearAllPlots()
                self.sec_panel.clearList()



    def _onReduceButton(self, event):

        files = []

        for each_filename in self.dir_panel.file_list_box.getSelectedFilenames():
            if each_filename != '..':
                path = os.path.join(self.dir_panel.file_list_box.path, each_filename)

                if not os.path.isdir(path):
                    files.append(path)

        if files:

            load_path = self.dir_panel.getDirLabel()

            dlg = RAWCustomDialogs.QuickReduceDialog(self, load_path, files)
            result = dlg.ShowModal()

            if result == wx.ID_OK:
                save_path = dlg.getPath()
            else:
                return

            dlg.Destroy()

            mainworker_cmd_queue.put(['quick_reduce', [save_path, load_path, files, '.dat']])


    def _onShowImageButton(self, event):

        if len(self.dir_panel.file_list_box.getSelectedFilenames()) > 0:
            filename = self.dir_panel.file_list_box.getSelectedFilenames()[0]
            if filename != '..':
                path = os.path.join(self.dir_panel.file_list_box.path, filename)
                if not os.path.isdir(path):
                    mainworker_cmd_queue.put(['show_image', [path, 0]])


class CustomListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):

    def __init__(self, parent, id):
        wx.ListCtrl.__init__(self, parent, id, style = wx.LC_REPORT |wx.LC_VIRTUAL, name = 'FileListCtrl')

        self.path = os.getcwd()
        self.files = []
        self.parent = parent
        self.mainframe = wx.FindWindowByName('MainFrame')
        self.file_panel = wx.FindWindowByName('FilePanel')
        self.dirctrl_panel = parent

        self.filteredFilesList = []
        self.dirsList = []
        self.file_list_dict = {}
        self.folder_list_dict = {}

        self.copylist = []
        self.cut_selected = False
        self.copy_selected = False

        self.InsertColumn(0, 'Name')
        self.InsertColumn(1, 'Ext')
        self.InsertColumn(2, 'Modified')
        self.InsertColumn(3, 'Size', wx.LIST_FORMAT_RIGHT)
        self.SetColumnWidth(0, 160)
        self.SetColumnWidth(1, 40)
        self.SetColumnWidth(2, 125)
        self.SetColumnWidth(3, 70)

        self.attr1 = wx.ListItemAttr()
        self.attr1.SetBackgroundColour('#e6f1f5')
        self.attr2 = wx.ListItemAttr()
        self.attr2.SetBackgroundColour("White")

        ### Prepare list images:
        self.il = wx.ImageList(16, 16)

        dir_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-folder-16.png')
        doc_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-document-16.png')
        up_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-thick-arrow-blue-pointing-up-16.png')
        sort_up_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-sort-up-filled-16.png')
        sort_down_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-sort-down-filled-16.png')

        self.documentimg = self.il.Add(wx.Bitmap(doc_png, wx.BITMAP_TYPE_PNG))
        self.folderimg = self.il.Add(wx.Bitmap(dir_png, wx.BITMAP_TYPE_PNG))
        self.upimg = self.il.Add(wx.Bitmap(up_png, wx.BITMAP_TYPE_PNG))
        self.sm_up = self.il.Add(wx.Bitmap(sort_up_png, wx.BITMAP_TYPE_PNG))
        self.sm_dn = self.il.Add(wx.Bitmap(sort_down_png, wx.BITMAP_TYPE_PNG))
        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

        #Init the list:
        self.itemDataMap = {}
        self.itemIndexMap = {}.keys()
        self.SetItemCount(len({}))

        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.ColumnSorterMixin.__init__(self, 4)

        #Default sorting order:
        self.SortListItems(0, 1)

        self.Bind(wx.EVT_LEFT_DCLICK, self._onDoubleLeftMouseClickOrEnterKey)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPressEvent)
        self.Bind(wx.EVT_RIGHT_UP, self._onRightMouseClick)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.onColClick)

        #---------------------------------------------------
        # These methods are callbacks for implementing the
        # "virtualness" of the list...


#    def GetSecondarySortValues(self, col, key1, key2):
#
#        def ss(key):
#            return self.itemDataMap[key][3]
#
#        return (ss(key1), ss(key2))

    def OnGetItemText(self, item, col):
        index=self.itemIndexMap[item]
        s = self.itemDataMap[index][col]
        return s

    def OnGetItemImage(self, item):
        index=self.itemIndexMap[item]
        itemtype = self.itemDataMap[index][4]

        if itemtype == 'file':
            return self.documentimg
        elif itemtype == 'up':
            return self.upimg
        elif itemtype == 'dir':
            return self.folderimg
        else:
            return -1

    def OnGetItemAttr(self, item):
        if (item % 2) == 0:
           return self.attr1
        elif (item % 2) == 1:
           return self.attr2
        else:
           return None

    def GetSortImages(self):
        return (self.sm_dn, self.sm_up)

    #---------------------------------------------------
    # Matt C, 2006/02/22
    # Here's a better SortItems() method --
    # the ColumnSorterMixin.__ColumnSorter() method already handles the ascending/descending,
    # and it knows to sort on another column if the chosen columns have the same value.

    def SortItems(self,sorter=cmp):
        items = list(self.itemDataMap.keys())
        items.sort(sorter)
        self.itemIndexMap = items

        # redraw the list
        self.Refresh()

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
#    def GetSortImages(self):
#        return (self.sm_dn, self.sm_up)

    def onColClick(self, event):

#        if event.GetColumn() == self.sort_column:
#            self.reverse_sort = not self.reverse_sort
#        else:
#            self.reverse_sort = False

#        self.sort_column = event.GetColumn()

#    self.updateSorting()

        event.Skip()
        #self.updateFileList()

    def readFileList(self):
        try:
            self.files = os.listdir(self.path)

        except OSError, msg:
            print msg
            wx.MessageBox(str(msg), 'Error loading folder', style = wx.ICON_ERROR | wx.OK)

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
            filteredFiles[i] = str(filteredFiles[i].encode("iso-8859-15", "backslashreplace"))

        filteredFiles.sort(key = str.lower)

        return filteredFiles

    def getListDict(self):
        return self.list_dict

    def refreshFileList(self):
        self.DeleteAllItems()

        self.dirsList = []

        self.file_list_dict = {}
        self.folder_list_dict = {}

        ### Take out the directories and sort them:
        for each in self.files:
            if os.path.isdir(os.path.join(self.path, each)):
                self.dirsList.append(str(each))

        self.dirsList.sort(key = str.lower)

        ## Remove directories fromt the file list:
        for each in self.dirsList:
            self.files.remove(each)

        filteredFiles = self.getFilteredFileList()

        if len(self.path) > 1:
            #self.InsertStringItem(0, '..')
            #self.SetItemImage(0,0)
            j = 1
        else:
            j = 1

        for i in self.dirsList:
            (name, ext) = os.path.splitext(i)
            ex = ext[1:]

            try:
                size = os.path.getsize(os.path.join(self.path, i))
                sec = os.path.getmtime(os.path.join(self.path, i))
            except WindowsError:
                size = 1
                sec = 1

            self.file_list_dict[j] = (name, ex, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)), '', 'dir')

            j += 1

        end_of_folders_idx = j

        for i in filteredFiles:
            (name, ext) = os.path.splitext(i)
            ex = ext[1:]
            try:
                size = os.path.getsize(os.path.join(self.path, i))
                sec = os.path.getmtime(os.path.join(self.path, i))
            except Exception, e:
                print e
                size = 0
                sec = 1

            self.file_list_dict[j] = (name, ex, time.strftime('%Y-%m-%d %H:%M', time.localtime(sec)), str(round(size/1000,1)) + ' KB', 'file')

            j += 1

        self.insertSortedFilesIntoList(end_of_folders_idx)

    def insertSortedFilesIntoList(self, end_of_folders_idx):

        self.file_list_dict[0] = ('..', '', '', '', 'up')
        self.itemDataMap = self.file_list_dict
        self.itemIndexMap = self.file_list_dict.keys()
        self.SetItemCount(len(self.file_list_dict))

        self.OnSortOrderChanged()


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
        col, ascending = self.GetSortState()

        self.readFileList()
        self.refreshFileList()
        self.itemDataMap = self.file_list_dict
        self.itemIndexMap = self.file_list_dict.keys()

        # self.OnSortOrderChanged()
        self.SortListItems(col, ascending)

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

        menu.Append(1, 'New Folder')
        menu.AppendSeparator()
        menu.Append(2, 'Rename' )
        menu.AppendSeparator()
        menu.Append(3, 'Cut')
        menu.Append(4, 'Copy')
        paste = menu.Append(5, 'Paste')
        paste.Enable(False)

        if self.copy_selected or self.cut_selected:
            paste.Enable(True)


        menu.AppendSeparator()
        menu.Append(6, 'Delete')

        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        self.PopupMenu(menu)

        menu.Destroy()

    def _onRightMouseClick(self, event):

        if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
            wx.CallAfter(self._showPopupMenu)
        else:
            self._showPopupMenu()


    def _onPopupMenuChoice(self, event):
        choice_id = event.GetId()

        choices = {1 : self._createNewFolder,
                   2 : self._renameFile,
                   3 : self._cutFile,
                   4 : self._copyFile,
                   5 : self._pasteFile,
                   6 : self._deleteFile}

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

        dlg = RAWCustomDialogs.FilenameChangeDialog(self, 'New Folder')
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

        dlg = wx.MessageDialog(self, 'Are you sure you want to PERMANETLY delete ' + txt + ' file'+ txt2 +'?:', 'Are you sure?', wx.YES_NO | wx.ICON_INFORMATION)

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
        dlg = RAWCustomDialogs.FilenameChangeDialog(self, filename)

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

            file, ext = os.path.splitext(full_dir_filename)

            if ext == '.wsp':
                mainworker_cmd_queue.put(['load_workspace', [full_dir_filename]])

            elif ext == '.cfg':
                ret = wx.MessageBox('Are you sure you want to load this config file?',
                              'Load new configuration?', style = wx.YES_NO | wx.ICON_QUESTION)

                if ret == wx.YES:
                    raw_settings = self.mainframe.getRawSettings()

                    try:
                        success = RAWSettings.loadSettings(raw_settings, full_dir_filename)
                    except IOError, e:
                        wx.MessageBox(str(e), 'Error loading file', style = wx.OK | wx.ICON_EXCLAMATION)


                    if success:
                        raw_settings.set('CurrentCfg', file)
                    else:
                        wx.MessageBox('Load failed, config file might be corrupted',
                              'Load failed', style = wx.OK | wx.ICON_ERROR)

            else:
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

        self.main_frame = wx.FindWindowByName('MainFrame')
        self.raw_settings = self.main_frame.getRawSettings()

        self.file_extension_list = ['All files (*.*)',
                                    'No Extension files (*.)',
                                    'TIFF files (*.tiff)',
                                    'TIF files (*.tif)',
                                    # 'RAD Files (*.rad)',
                                    'DAT files (*.dat)',
                                    'SEC files (*.sec)',
                                    'TXT files (*.txt)',
                                    'IMG files (*.img)',
                                    'FIT files (*.fit)',
                                    'WSP files (*.wsp)',
                                    'CFG files (*.cfg)']

        dirctrlpanel_sizer = wx.BoxSizer(wx.VERTICAL)

        self.ext_choice = self._createExtentionBox()       #File extention filter

        self._createDirCtrl(dirctrlpanel_sizer)            #Listbox containing filenames

        dirctrlpanel_sizer.Add(self.ext_choice, 0, wx.EXPAND | wx.TOP, 2)

        self.SetSizer(dirctrlpanel_sizer, wx.EXPAND)

        self.selected_file = None
        self._old_path = '.'

        self.file_list = []


    def _useSavedPathIfExisits(self):
        path = None

        load_path = os.path.join(RAWGlobals.RAWWorkDir, 'backup.ini')

        try:
            with open(load_path, 'r') as file_obj:
                data = cPickle.load(file_obj)

            path = data['workdir']
        except Exception:
            path = None

        if path != None and os.path.exists(path):
            self.setDirLabel(path)
            self.file_list_box.setDir(path)
        else:
            path = wx.StandardPaths.Get().GetDocumentsDir()
            self.setDirLabel(path)
            self.file_list_box.setDir(path)


    def _createDirCtrl(self, dirctrlpanel_sizer):

        dir_label_sizer = wx.BoxSizer()

        self.dir_label = wx.TextCtrl(self, -1, "/" , size = (30,16), style = wx.TE_PROCESS_ENTER)
        self.dir_label.Bind(wx.EVT_KILL_FOCUS, self._onEnterOrFocusShiftInDirLabel)
        self.dir_label.Bind(wx.EVT_TEXT_ENTER, self._onEnterOrFocusShiftInDirLabel)

        dir_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-opened-folder-16.png')
        refresh_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-synchronize-16.png')

        dir_bitmap = wx.Bitmap(dir_png, wx.BITMAP_TYPE_PNG)
        refresh_bitmap = wx.Bitmap(refresh_png, wx.BITMAP_TYPE_PNG)

        self.dir_button = wx.BitmapButton(self, -1, dir_bitmap)
        self.dir_button.Bind(wx.EVT_BUTTON, self._onSetDirButton)

        self.refresh_button = wx.BitmapButton(self, -1, refresh_bitmap)
        self.refresh_button.Bind(wx.EVT_BUTTON, self._onRefreshButton)

        self.dir_button.SetToolTip(wx.ToolTip('Open Folder'))
        self.refresh_button.SetToolTip(wx.ToolTip('Refresh'))

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
        self.dropdown = wx.ComboBox(self, style=wx.TE_PROCESS_ENTER,
            choices=self.file_extension_list)
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

        event.Skip()

    def _onSetDirButton(self, event):
        pathtxt = self.getDirLabel()
        dirdlg = wx.DirDialog(self, "Please select directory:", str(pathtxt))

        if dirdlg.ShowModal() == wx.ID_OK:
            path = dirdlg.GetPath()
            self.file_list_box.setDir(path)
            self.setDirLabel(path)

    def _onRefreshButton(self, event):
        self.refresh()

    def refresh(self):
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

        file_drop_target = RAWCustomCtrl.RawPanelFileDropTarget(self.underpanel, 'main')
        self.underpanel.SetDropTarget(file_drop_target)

        self.underpanel.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        self.all_manipulation_items = []
        self.selected_item_list = []

        self.modified_items = []

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

        #Icons for ManipulationPanel (some shared with ManipItemPanel)
        collapse_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-collapse-filled-16.png')
        expand_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-expand-filled-16.png')
        show_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-eye-16.png')
        hide_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-hide-16.png')
        select_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-select-all-16.png')

        self.collapse_all_png = wx.Bitmap(collapse_all, wx.BITMAP_TYPE_PNG)
        self.expand_all_png = wx.Bitmap(expand_all, wx.BITMAP_TYPE_PNG)
        self.show_all_png = wx.Bitmap(show_all, wx.BITMAP_TYPE_PNG)
        self.hide_all_png = wx.Bitmap(hide_all, wx.BITMAP_TYPE_PNG)
        self.select_all_png = wx.Bitmap(select_all, wx.BITMAP_TYPE_PNG)

        #Items for ManipItemPanel
        gray_star = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-star-filled-gray-16.png')
        orange_star = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-star-filled-orange-16.png')
        target = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-16.png')
        target_on = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-red-16.png')
        info = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-info-16.png')
        expand = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-sort-down-filled-16.png')
        collapse = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-sort-up-filled-16.png')

        self.gray_png = wx.Bitmap(gray_star, wx.BITMAP_TYPE_PNG)
        self.star_png = wx.Bitmap(orange_star, wx.BITMAP_TYPE_PNG)
        self.target_png = wx.Bitmap(target, wx.BITMAP_TYPE_PNG)
        self.target_on_png = wx.Bitmap(target_on, wx.BITMAP_TYPE_PNG)
        self.info_png = wx.Bitmap(info, wx.BITMAP_TYPE_PNG)
        self.expand_png = wx.Bitmap(expand, wx.BITMAP_TYPE_PNG)
        self.collapse_png = wx.Bitmap(collapse, wx.BITMAP_TYPE_PNG)

    def _createToolbar(self):

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        if platform.system() == 'Darwin':
            size = (28, -1)
        else:
            size = (-1, -1)

        collapse_all = wx.BitmapButton(self, -1, self.collapse_all_png)
        expand_all = wx.BitmapButton(self, -1, self.expand_all_png)
        show_all = wx.BitmapButton(self, -1, self.show_all_png, size=size)
        hide_all = wx.BitmapButton(self, -1, self.hide_all_png, size=size)
        select_all= wx.BitmapButton(self, -1, self.select_all_png)

        select_all.Bind(wx.EVT_BUTTON, self._onSelectAllButton)
        collapse_all.Bind(wx.EVT_BUTTON, self._onCollapseAllButton)
        expand_all.Bind(wx.EVT_BUTTON, self._onExpandAllButton)
        show_all.Bind(wx.EVT_BUTTON, self._onShowAllButton)
        hide_all.Bind(wx.EVT_BUTTON, self._onHideAllButton)


        if platform.system() == 'Darwin':
            show_tip = STT.SuperToolTip(" ", header = "Show", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            show_tip.SetTarget(show_all)
            show_tip.ApplyStyle('Blue Glass')

            hide_tip = STT.SuperToolTip(" ", header = "Hide", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            hide_tip.SetTarget(hide_all)
            hide_tip.ApplyStyle('Blue Glass')

            select_tip = STT.SuperToolTip(" ", header = "Select All", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            select_tip.SetTarget(select_all)
            select_tip.ApplyStyle('Blue Glass')

            collapse_tip = STT.SuperToolTip(" ", header = "Collapse", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            collapse_tip.SetTarget(collapse_all)
            collapse_tip.ApplyStyle('Blue Glass')

            expand_tip = STT.SuperToolTip(" ", header = "Expand", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            expand_tip.SetTarget(expand_all)
            expand_tip.ApplyStyle('Blue Glass')

        else:
            select_all.SetToolTip(wx.ToolTip('Select All'))
            show_all.SetToolTip(wx.ToolTip('Show'))
            hide_all.SetToolTip(wx.ToolTip('Hide'))
            collapse_all.SetToolTip(wx.ToolTip('Collapse'))
            expand_all.SetToolTip(wx.ToolTip('Expand'))

        sizer.Add(show_all, 0, wx.LEFT, 5)
        sizer.Add(hide_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)
        sizer.Add(select_all, 0, wx.LEFT, 5)
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

    def addItem(self, sasm, item_colour = 'black', item_visible = True, notsaved = False, legend_label=''):

        self.underpanel.Freeze()

        if not isinstance(sasm, list):
            sasm = [sasm]

        for item in sasm:
            newItem = ManipItemPanel(self.underpanel, item, font_colour = item_colour,
                         item_visible = item_visible, modified = notsaved,
                         legend_label = legend_label)

            self.underpanel_sizer.Add(newItem, 0, wx.GROW)
            self.all_manipulation_items.append(newItem)
            item.item_panel = newItem

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

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
        self._star_marked_item = None
        self.modified_items = []
        self.selected_item_list = []

        rest_of_items = []
        for each in self.all_manipulation_items:
            try:
                each.Destroy()
            except ValueError:
                rest_of_items.append(each)

        self.all_manipulation_items = rest_of_items

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

    def clearBackgroundItem(self):
        self._raw_settings.set('BackgroundSASM', None)
        self._star_marked_item = None

    def _collapseAllItems(self):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
                each.showControls(False)
        else:
            for each in selected_items:
                each.showControls(False)

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

    def _expandAllItems(self):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
                each.showControls(True)
        else:
            for each in selected_items:
                each.showControls(True)

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

    def getSelectedItems(self):

        self.selected_item_list = []

        for each in self.all_manipulation_items:
            if each._selected == True:
                self.selected_item_list.append(each)

        return self.selected_item_list

    def selectAll(self):
        for i in range(len(self.all_manipulation_items)):
            each = self.all_manipulation_items[i]
            each._selected = False
            if i != len(self.all_manipulation_items) -1:
                each.toggleSelect(update_info = False)
            else:
                each.toggleSelect()

    def deselectAllExceptOne(self, item, line = None, enableLocatorLine = False):

        if line == None:
            for each in self.all_manipulation_items:
                if each != item:
                    each._selected = True
                    each.toggleSelect(update_info=False)
        else:
            for each in self.all_manipulation_items:
                if each.sasm.getLine() == line:
                    each._selected = False
                    each.toggleSelect(update_info = True)
                else:
                    each._selected = True
                    each.toggleSelect(update_info = False)

    def removeSelectedItems(self):
        if len(self.getSelectedItems()) == 0:
            return

        # self.underpanel.Freeze()

        info_panel = wx.FindWindowByName('InformationPanel')
        info_panel.clearInfo()

        axes_that_needs_updated_legend = []

        for each in self.getSelectedItems():
            try:
                self.modified_items.remove(each)
            except:
                pass

            plot_panel = each.sasm.plot_panel

            each.sasm.line.remove()
            each.sasm.line = None
            each.sasm.err_line[0][0].remove()
            each.sasm.err_line[0][1].remove()
            each.sasm.err_line[1][0].remove()
            each.sasm.err_line = None

            i = plot_panel.plotted_sasms.index(each.sasm)
            plot_panel.plotted_sasms.pop(i)

            if each.sasm.axes not in axes_that_needs_updated_legend:
                axes_that_needs_updated_legend.append(each.sasm.axes)

            if each == self._star_marked_item:
                self._star_marked_item = None

            idx = self.all_manipulation_items.index(each)
            self.all_manipulation_items[idx].Destroy()
            self.all_manipulation_items.pop(idx)

        for eachaxes in axes_that_needs_updated_legend:
            if eachaxes == plot_panel.subplot1:
                wx.CallAfter(plot_panel.updateLegend, 1, False)
            else:
                wx.CallAfter(plot_panel.updateLegend, 2, False)

        wx.CallAfter(plot_panel.fitAxis)

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

        # self.underpanel.Thaw()

    def _onShowAllButton(self, event):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
               each.showItem(True)

        else:
            for each in selected_items:
                each.showItem(True)

        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

        plot_panel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plot_panel.updateLegend, 1, False)
        wx.CallAfter(plot_panel.updateLegend, 2, False)
        wx.CallAfter(plot_panel.fitAxis)

        event.Skip()

    def _onHideAllButton(self, event):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
               each.showItem(False)

        else:
            for each in selected_items:
                each.showItem(False)

        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

        plot_panel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plot_panel.updateLegend, 1, False)
        wx.CallAfter(plot_panel.updateLegend, 2, False)
        wx.CallAfter(plot_panel.fitAxis)

        event.Skip()

    def _onSelectAllButton(self, event):
        self.selectAll()
        event.Skip()

    def _onCollapseAllButton(self, event):
        self._collapseAllItems()
        event.Skip()

    def _onExpandAllButton(self, event):
        self._expandAllItems()
        event.Skip()

    def _onAverageButton(self, event):
        selected_items = self.getSelectedItems()
        mainworker_cmd_queue.put(['average_items', selected_items])
        event.Skip()

    def _onRemoveButton(self, event):
        self.removeSelectedItems()
        event.Skip()

    def _onSaveButton(self, event):
        self.saveItems()
        event.Skip()

    def _onSyncButton(self, event):
        self.Sync()
        event.Skip()

    def _onSubtractButton(self, event):
        mainworker_cmd_queue.put(['subtract_items', (self._star_marked_item, self.getSelectedItems())])
        event.Skip()

    def _onSuperimposeButton(self, event):
        self.Superimpose()
        event.Skip()

    def Sync(self):
        star_item = self.getBackgroundItem()
        selected_items = self.getSelectedItems()

        if star_item is None or not selected_items or len(selected_items) == 0:
            msg = ('In order to synchronize (sync) items, you must star the item '
                'that all others will be synchronized with. You must also select'
                ' one or more items to synchronize with the starred item.')
            wx.MessageBox(msg, 'Cannot sync items', wx.OK | wx.ICON_INFORMATION)
            return

        syncdialog = RAWCustomDialogs.SyncDialog(self)
        syncdialog.ShowModal()
        syncdialog.Destroy()

    def Superimpose(self):
        mainworker_cmd_queue.put(['superimpose_items', (self._star_marked_item, self.getSelectedItems())])

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

        manip_plot = wx.FindWindowByName("PlotPanel")

        sasm_list = []

        for each_item in selected_items:
            if each_item == star_item:
                continue

            sasm = each_item.getSASM()

            sasm_list.append(sasm)

            old_nmin, old_nmax = sasm.getQrange()

            modified = False

            try:
                if 'nmin' in sync_parameters and 'nmax' in sync_parameters:
                    sasm.setQrange([nmin, nmax])
                    if nmin != old_nmin or nmax != old_nmax:
                        modified = True
                elif 'nmin' in sync_parameters:
                    sasm.setQrange([nmin, old_nmax])
                    if nmin != old_nmin:
                        modified = True
                elif 'nmax' in sync_parameters:
                    sasm.setQrange([old_nmin, nmax])
                    if nmax != old_nmax:
                        modified = True

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
                new_nmin = np.where(q == closest)[0][0]
                closest = findClosest(qmax, q)
                new_nmax = np.where(q == closest)[0][0]+1
                sasm.setQrange([new_nmin, new_nmax])

                if new_nmin != old_nmin or new_nmax != old_nmax:
                    modified = True

            elif 'qmin' in sync_parameters:
                closest = findClosest(qmin, q)
                new_nmin = np.where(q == closest)[0][0]
                sasm.setQrange([new_nmin, old_nmax])

                if new_nmin != old_nmin:
                    modified = True

            elif 'qmax' in sync_parameters:
                closest = findClosest(qmax, q)
                new_nmax = np.where(q == closest)[0][0]+1
                sasm.setQrange([old_nmin, new_nmax])

                if new_nmax != old_nmax:
                    modified = True

            if 'scale' in sync_parameters:
                old_scale = sasm.getScale()
                sasm.scale(scale)

                if old_scale != scale:
                    modified = True

            if 'offset' in sync_parameters:
                old_offset = sasm.getOffset()
                sasm.offset(offset)

                if old_offset != offset:
                    modified = True

            if 'linestyle' in sync_parameters:
                old_linestyle = sasm.line.get_linestyle()
                sasm.line.set_linestyle(linestyle)

                if old_linestyle != linestyle:
                    modified = True

            if 'linewidth' in sync_parameters:
                old_linewidth = sasm.line.get_linewidth()
                sasm.line.set_linewidth(linewidth)

                if old_linewidth != linewidth:
                    modified = True

            if 'linemarker' in sync_parameters:
                old_linemarker = sasm.line.get_marker()
                sasm.line.set_marker(linemarker)

                if old_linemarker != linemarker:
                    modified = True

            wx.CallAfter(each_item.updateControlsFromSASM, updatePlot=False)

            if modified:
                wx.CallAfter(each_item.markAsModified, updateParent = False)

        wx.CallAfter(each_item.parent.Refresh)
        wx.CallAfter(each_item.parent.Layout)

        wx.CallAfter(manip_plot.updatePlotAfterManipulation, sasm_list)

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

                visible = each_item._selected_for_plot

                wx.CallAfter(each_item.showItem, visible)


        plotpanel = wx.FindWindowByName('PlotPanel')
        wx.CallAfter(plotpanel.updateLegend, 1, False)
        wx.CallAfter(plotpanel.updateLegend, 2, False)
        wx.CallAfter(plotpanel.fitAxis)

    def getItems(self):
        return self.all_manipulation_items

    def saveItems(self):
        selected_items = self.getSelectedItems()

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        if len(selected_items) == 1:

            # filters = 'Comma Separated Files (*.csv)|*.csv'

            # dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path)
            fname = os.path.splitext(os.path.basename(selected_items[0].sasm.getParameter('filename')))[0]+'.dat'
            msg = "Please select save directory and enter save file name"
            dialog = wx.FileDialog(self, message = msg, style = wx.FD_SAVE, defaultDir = path, defaultFile = fname)

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
            else:
                return

            path=os.path.splitext(path)[0]+'.dat'
            filename = os.path.basename(path)
            selected_items[0].sasm.setParameter('filename', filename)
            wx.CallAfter(selected_items[0].updateFilenameLabel)

            save_path = os.path.dirname(path)

        elif len(selected_items) == 0:
            return

        else:
            dirdlg = wx.DirDialog(self, "Please select save directory (multiple files will be saved):", defaultPath = path)

            if dirdlg.ShowModal() == wx.ID_OK:
                path = dirdlg.GetPath()
            else:
                return
            save_path = path

        mainworker_cmd_queue.put(['save_items', [save_path, selected_items]])

    def _onKeyPress(self, evt):
        key = evt.GetKeyCode()

        if key == 65 and evt.CmdDown():
            self.selectAll()


class ManipItemPanel(wx.Panel):
    def __init__(self, parent, sasm, font_colour = 'BLACK', legend_label = '', item_visible = True, modified = False):

        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)

        self.parent = parent
        self.sasm = sasm
        self.sasm.itempanel = self

        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')
        self.plot_panel = wx.FindWindowByName('PlotPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')

        self.raw_settings = self.main_frame.raw_settings

        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.info_settings = {'hdr_choice' : 0}

        self._selected_as_bg = False
        self._selected_for_plot = item_visible
        self._controls_visible = True
        self._selected = False
        self._legend_label = legend_label

        self._font_colour = font_colour

        filename = sasm.getParameter('filename')

        opsys = platform.system()

        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        self._initializeIcons()

        self.qmax = len(self.sasm.q)

        self.spin_controls = (("q Min:", 100, 101, (1, self.qmax-1), 'nlow'),
                             ("q Max:", 102, 103, (2, self.qmax), 'nhigh'))

        self.float_spin_controls = (("Scale:", 105, 'scale', str(sasm.getScale()), self._onScaleOffsetChange),
                                    ("Offset:", 106, 'offset', str(sasm.getOffset()), self._onScaleOffsetChange))

        self.showitem_icon = wx.StaticBitmap(self, wx.ID_ANY, self.show_png)
        self.showitem_icon.Bind(wx.EVT_LEFT_DOWN, self._onShowItem)

        self.item_name = wx.StaticText(self, wx.ID_ANY, filename)
        self.item_name.SetForegroundColour(font_colour)

        self.legend_label_text = wx.StaticText(self, -1, '')

        if opsys != 'Darwin':
            self.item_name.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            self.item_name.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            self.item_name.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

            self.legend_label_text.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            self.legend_label_text.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            self.legend_label_text.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.sasm.line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self.colour_indicator = RAWCustomCtrl.ColourIndicator(self, -1, color, size = (20,15))
        self.colour_indicator.Bind(wx.EVT_LEFT_DOWN, self._onLinePropertyButton)

        self.bg_star = wx.StaticBitmap(self, -1, self.gray_png)
        self.bg_star.Bind(wx.EVT_LEFT_DOWN, self._onStarButton)

        self.expand_collapse = wx.StaticBitmap(self, -1, self.collapse_png)
        self.expand_collapse.Bind(wx.EVT_LEFT_DOWN, self._onExpandCollapseButton)

        self.target_icon = wx.StaticBitmap(self, -1, self.target_png)
        self.target_icon.Bind(wx.EVT_LEFT_DOWN, self._onTargetButton)


        self.info_icon = wx.StaticBitmap(self, -1, self.info_png)

        if int(wx.__version__.split('.')[0]) >= 3 and opsys == 'Darwin':
            show_tip = STT.SuperToolTip(" ", header = "Show Plot", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            show_tip.SetTarget(self.showitem_icon)
            show_tip.ApplyStyle('Blue Glass')

            line_tip = STT.SuperToolTip(" ", header = "Line Properties", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            line_tip.SetTarget(self.colour_indicator)
            line_tip.ApplyStyle('Blue Glass')

            mark_tip = STT.SuperToolTip(" ", header = "Mark", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            mark_tip.SetTarget(self.bg_star)
            mark_tip.ApplyStyle('Blue Glass')

            expand_tip = STT.SuperToolTip(" ", header = "Collapse/Expand", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            expand_tip.SetTarget(self.expand_collapse)
            expand_tip.ApplyStyle('Blue Glass')

            target_tip = STT.SuperToolTip(" ", header = "Locate Line", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            target_tip.SetTarget(self.target_icon)
            target_tip.ApplyStyle('Blue Glass')

            self.info_tip = STT.SuperToolTip("Rg: N/A\nI(0): N/A", header = "Extended Info", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            self.info_tip.SetDrawHeaderLine(True)
            self.info_tip.SetTarget(self.info_icon)
            self.info_tip.ApplyStyle('Blue Glass')

        else:
            self.showitem_icon.SetToolTip(wx.ToolTip('Show Plot'))
            self.colour_indicator.SetToolTip(wx.ToolTip('Line Properties'))
            self.bg_star.SetToolTip(wx.ToolTip('Mark'))
            self.expand_collapse.SetToolTip(wx.ToolTip('Collapse/Expand'))
            self.target_icon.SetToolTip(wx.ToolTip('Locate Line'))
            self.info_icon.SetToolTip(wx.ToolTip('Extended Info\n--------------------------------\nRg: N/A\nI(0): N/A'))

        self.locator_on = False
        self.locator_old_width = 1
        self.locator_old_marker = 1

        panelsizer = wx.BoxSizer()
        panelsizer.Add(self.showitem_icon, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add(self.item_name, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add(self.legend_label_text, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add((1,1), 1, wx.EXPAND)
        panelsizer.Add(self.expand_collapse, 0, wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 5)
        panelsizer.Add(self.info_icon, 0, wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 5)
        panelsizer.Add(self.target_icon, 0, wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 4)
        panelsizer.Add(self.colour_indicator, 0, wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 5)
        panelsizer.Add(self.bg_star, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)


        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(panelsizer, 1, wx.EXPAND)

        #self.controlSizer = wx.BoxSizer(wx.VERTICAL)
        self.controlSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 3, hgap = 7)

        self._createSimpleSpinCtrls(self.controlSizer)
        self._createFloatSpinCtrls(self.controlSizer)

        self.topsizer.Add((5,5),0)
        self.topsizer.Add(self.controlSizer, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)

        self.SetSizer(self.topsizer)

        self.SetBackgroundColour(wx.Colour(250,250,250))

        self._initStartPosition()
        self._updateQTextCtrl()

        if self.sasm.getParameter('analysis').has_key('guinier'):
            self.updateInfoTip(self.sasm.getParameter('analysis'))

        controls_not_shown = self.main_frame.raw_settings.get('ManipItemCollapsed')

        if not self._selected_for_plot:
            controls_not_shown = True

        if controls_not_shown:
            self.showControls(not controls_not_shown)

        if modified:
            parent = self.GetParent()

            filename = self.sasm.getParameter('filename')
            self.item_name.SetLabel('* ' + str(filename))
            self.item_name.Refresh()

            if self not in self.manipulation_panel.modified_items:
                self.manipulation_panel.modified_items.append(self)

        self.updateShowItem()
        self._updateLegendLabel(False)


    def updateInfoTip(self, analysis_dict, fromGuinierDialog = False):

        if analysis_dict.has_key('guinier'):
            guinier = analysis_dict['guinier']
        else:
            guinier = {}

        string0 = 'Extended Info\n--------------------------------\n'
        string1 = ''
        string2 = ''
        string3 = ''

        if guinier.has_key('Rg') and guinier.has_key('I0'):
            rg = guinier['Rg']
            i_zero = guinier['I0']

            string1 = 'Rg: ' + str(rg) + '\nI(0): ' + str(i_zero) + '\n'
        else:
            string1 = 'Rg: N/A' + '\nI(0): N/A\n'

        if self.sasm.getAllParameters().has_key('Conc'):
            string2 = 'Conc: ' + str(self.sasm.getParameter('Conc')) + '\n'

        if self.sasm.getAllParameters().has_key('Notes'):
            if self.sasm.getParameter('Notes') != '':
                string3 = 'Note: ' + str(self.sasm.getParameter('Notes'))

        if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
            string = string1+string2+string3
        else:
            string = string0+string1+string2+string3

        if string != '':
            if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                self.info_tip.SetMessage(string)
            else:
                self.info_icon.SetToolTip(wx.ToolTip(string))

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

    def updateControlsFromSASM(self, updatePlot = True):
        scale = self.sasm.getScale()
        offset = self.sasm.getOffset()
        qmin, qmax = self.sasm.getQrange()

        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1], self)
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1], self)
        qmintxt = wx.FindWindowById(self.spin_controls[0][2], self)
        qmaxtxt = wx.FindWindowById(self.spin_controls[1][2], self)

        qmin_ctrl.SetValue(str(qmin))
        qmax_ctrl.SetValue(str(qmax-1))
        qmintxt.SetValue(str(round(self.sasm.q[qmin],4)))
        qmaxtxt.SetValue(str(round(self.sasm.q[qmax-1],4)))

        scale_ctrl = wx.FindWindowById(self.float_spin_controls[0][1], self)
        offset_ctrl = wx.FindWindowById(self.float_spin_controls[1][1], self)

        offset_ctrl.SetValue(str(offset))
        scale_ctrl.SetValue(str(scale))

        if updatePlot:
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])

    def toggleSelect(self, set_focus = False, update_info = True):
        if self._selected:
            self._selected = False
            self.SetBackgroundColour(wx.Colour(250,250,250))
            if update_info:
                self.info_panel.clearInfo()
        else:
            self._selected = True
            self.SetBackgroundColour(wx.Colour(200,200,200))
            if set_focus:
                self.SetFocusIgnoringChildren()
            if update_info:
                self.info_panel.updateInfoFromItem(self)

        self.Refresh()

    def enableLocatorLine(self):

        self.locator_on = not self.locator_on

        if self.locator_on:
            self.target_icon.SetBitmap(self.target_on_png)
            self.locator_old_width = self.sasm.line.get_linewidth()
            self.locator_old_marker = self.sasm.line.get_markersize()

            new_width = self.locator_old_width + 2.0
            new_marker = self.locator_old_marker + 2.0

            self.sasm.line.set_linewidth(new_width)
            self.sasm.line.set_markersize(new_marker)
            wx.CallAfter(self.sasm.plot_panel.canvas.draw)
        else:
            self.target_icon.SetBitmap(self.target_png)
            self.sasm.line.set_linewidth(self.locator_old_width)
            self.sasm.line.set_markersize(self.locator_old_marker)
            wx.CallAfter(self.sasm.plot_panel.canvas.draw)

        self.target_icon.Refresh()

    def getControlsVisible(self):
        return self._controls_visible

    def showControls(self, state):

        if state == False:
            self.expand_collapse.SetBitmap(self.expand_png)
            self._controls_visible = False
            self.topsizer.Hide(self.controlSizer, recursive=True)
        else:
            self.expand_collapse.SetBitmap(self.collapse_png)
            self._controls_visible = True
            self.topsizer.Show(self.controlSizer, recursive=True)

        self.expand_collapse.Refresh()
        self.topsizer.Layout()


    def showItem(self, state):
        self._selected_for_plot = state

        if not self._selected_for_plot:
            self._controls_visible = False
            self.showControls(self._controls_visible)
            self.showitem_icon.SetBitmap(self.hide_png)
        else:
            self.showitem_icon.SetBitmap(self.show_png)

        self.sasm.line.set_visible(self._selected_for_plot)
        self.sasm.line.set_picker(self._selected_for_plot)      #Line can't be selected when it's hidden

        each = self.sasm
        item_plot_panel = each.plot_panel
        err_bars = item_plot_panel.plotparams['errorbars_on']

        if err_bars:

            for each_err_line in each.err_line[0]:
                each_err_line.set_visible(state)

            for each_err_line in each.err_line[1]:
                each_err_line.set_visible(state)

            if self._selected_for_plot:
                item_plot_panel.updateErrorBars(each)

    def updateShowItem(self):
        if not self._selected_for_plot:
            self.showitem_icon.SetBitmap(self.hide_png)
        else:
            self.showitem_icon.SetBitmap(self.show_png)

        self.sasm.line.set_picker(self._selected_for_plot)

    def markAsModified(self, updateSelf = True, updateParent = True):
        filename = self.sasm.getParameter('filename')
        self.item_name.SetLabel('* ' + str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()

        if self not in self.manipulation_panel.modified_items:
            self.manipulation_panel.modified_items.append(self)

    def unmarkAsModified(self, updateSelf = True, updateParent = True):
        filename = self.sasm.getParameter('filename')

        self.item_name.SetLabel(str(filename))
        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()
        try:
            self.manipulation_panel.modified_items.remove(self)
        except:
            pass

    def updateFilenameLabel(self, updateSelf = True, updateParent = True, updateLegend = True):
        filename = self.sasm.getParameter('filename')

        if self._legend_label == '':
            self.sasm.line.set_label(filename)

        if updateLegend:
            self.plot_panel.updateLegend(self.sasm.axes)

        self.item_name.SetLabel(str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()

    def useAsMWStandard(self):

        if self.sasm.getAllParameters().has_key('Conc'):
            conc = self.sasm.getParameter('Conc')

            if float(conc) > 0:
                if self.sasm.getParameter('analysis').has_key('guinier'):
                    analysis = self.sasm.getParameter('analysis')
                    guinier = analysis['guinier']

                    if guinier.has_key('I0'):
                        i0 = guinier['I0']

                        if float(i0)>0:
                            MW = wx.GetTextFromUser('Please enter the molecular weight of the standard in units of [kDa].')

                            try:
                                MW = float(MW)
                            except Exception:
                                wx.MessageBox('Invalid input!', 'ERROR', wx.OK | wx.ICON_EXCLAMATION)
                                return

                            filename = os.path.basename(self.sasm.getParameter('filename'))

                            self.raw_settings.set('MWStandardMW', float(MW))
                            self.raw_settings.set('MWStandardI0', float(i0))
                            self.raw_settings.set('MWStandardConc', float(conc))
                            self.raw_settings.set('MWStandardFile', filename)

                            self.sasm.setParameter('MW', MW)
                            self.info_panel.updateInfoFromItem(self)

                            wx.MessageBox('New standard parameters has been saved.', 'Saved', wx.OK | wx.ICON_INFORMATION)

                    else:
                        wx.MessageBox('Please perform a Guinier analysis to obtain I0', 'I0 not found', wx.OK | wx.ICON_EXCLAMATION)
                else:
                    wx.MessageBox('Please perform a Guinier analysis to obtain I0', 'I0 not found', wx.OK | wx.ICON_EXCLAMATION)
            else:
                wx.MessageBox('Please enter the concentration in the information panel.', 'Concentration not found', wx.OK | wx.ICON_EXCLAMATION)
        else:
            wx.MessageBox('Please enter the concentration in the information panel.', 'Concentration not found', wx.OK | wx.ICON_EXCLAMATION)  #  except Exception, e:


    def _initializeIcons(self):

        self.gray_png = self.manipulation_panel.gray_png
        self.star_png = self.manipulation_panel.star_png
        self.target_png = self.manipulation_panel.target_png
        self.target_on_png = self.manipulation_panel.target_on_png
        self.info_png = self.manipulation_panel.info_png
        self.expand_png = self.manipulation_panel.expand_png
        self.collapse_png = self.manipulation_panel.collapse_png
        self.show_png = self.manipulation_panel.show_all_png
        self.hide_png = self.manipulation_panel.hide_all_png


    def _initStartPosition(self):
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1], self)
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1], self)

        qrange = self.sasm.getQrange()

        qmin_ctrl.SetValue(str(qrange[0]))
        qmax_ctrl.SetValue(str(qrange[1]-1))

    def _updateColourIndicator(self):
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.sasm.line.get_color())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self.colour_indicator.updateColour(color)

    def _onLinePropertyButton(self, event):

        try:
            legend_label = self.getLegendLabel()
            dialog = RAWCustomDialogs.LinePropertyDialog(self, self.sasm, legend_label)
            answer = dialog.ShowModal()
            new_legend_label = dialog.getLegendLabel()
            self._updateColourIndicator()
            dialog.Destroy()

            if answer == wx.ID_OK:
                self._legend_label = new_legend_label
                self._updateLegendLabel()

        except TypeError:
            return

    def _onExpandCollapseButton(self, event):
        self._controls_visible = not self._controls_visible
        self.showControls(self._controls_visible)

        self.manipulation_panel.underpanel.SetVirtualSize(self.manipulation_panel.underpanel.GetBestVirtualSize())
        self.GetParent().Layout()
        self.GetParent().Refresh()

        self.GetParent().GetParent().Layout()
        self.GetParent().GetParent().Refresh()

    def _onTargetButton(self, event):
        self.enableLocatorLine()

    def _showPopupMenu(self):
        opsys = platform.system()

        menu = wx.Menu()

        convertq_menu = wx.Menu()
        convertq_menu.Append(15, 'q * 10')
        convertq_menu.Append(16, 'q / 10')

        other_ops_menu = wx.Menu()
        if wx.version().split()[0].strip()[0] == '4':
            other_ops_menu.Append(wx.ID_ANY, 'Convert q-scale', convertq_menu)
        else:
            other_ops_menu.AppendMenu(wx.ID_ANY, 'Convert q-scale', convertq_menu)
        other_ops_menu.Append(25, 'Interpolate')
        other_ops_menu.Append(22, 'Merge')
        other_ops_menu.Append(28, 'Normalize by conc.')
        other_ops_menu.Append(23, 'Rebin')
        other_ops_menu.Append(39, 'Sync')
        other_ops_menu.Append(40, 'Superimpose')
        other_ops_menu.Append(27, 'Use as MW standard')

        other_an_menu = wx.Menu()
        other_an_menu.Append(34, 'SVD')
        other_an_menu.Append(35, 'EFA')

        menu.Append(4, 'Subtract')
        menu.Append(6, 'Average' )
        menu.Append(36, 'Weighted Average')
        if wx.version().split()[0].strip()[0] == '4':
            menu.Append(wx.ID_ANY, 'Other Operations', other_ops_menu)
        else:
            menu.AppendMenu(wx.ID_ANY, 'Other Operations', other_ops_menu)
        menu.AppendSeparator()

        menu.Append(5, 'Remove' )
        menu.AppendSeparator()
        menu.Append(13, 'Guinier fit')
        menu.Append(29, 'Molecular weight')
        menu.Append(32, 'IFT (BIFT)')
        if opsys == 'Windows':
            if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'gnom.exe')):
                menu.Append(31, 'IFT (GNOM)')
        else:
            if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'gnom')):
                menu.Append(31, 'IFT (GNOM)')

        menu.Append(37, 'Similarity Test')
        menu.Append(38, 'Normalized Kratky Plots')
        if wx.version().split()[0].strip()[0] == '4':
            menu.Append(wx.ID_ANY, 'Other Analysis', other_an_menu)
        else:
            menu.AppendMenu(wx.ID_ANY, 'Other Analysis', other_an_menu)

        menu.AppendSeparator()
        img = menu.Append(19, 'Show image')

        if not self.sasm.getAllParameters().has_key('load_path'):
            img.Enable(False)
        menu.Append(20, 'Show data')
        menu.Append(21, 'Show header')
        menu.Append(33, 'Show history')

        menu.AppendSeparator()
        menu.Append(8, 'Move to top plot')
        menu.Append(9, 'Move to bottom plot')
        menu.AppendSeparator()
        menu.Append(14, 'Rename')
        menu.AppendSeparator()
        menu.Append(30, 'Save all analysis info')
        menu.Append(18, 'Save item info')
        menu.Append(7, 'Save selected file(s)')

        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        self.PopupMenu(menu)

        menu.Destroy()

    def _onShowImage(self):

        if self.sasm.getAllParameters().has_key('load_path'):
            path = self.sasm.getParameter('load_path')

            try:
                fnum = int(self.sasm.getParameter('filename').split('_')[-1].split('.')[0])-1
            except ValueError:
                fnum = 0
    
            mainworker_cmd_queue.put(['show_image', [path, fnum]])

    def _onPopupMenuChoice(self, evt):

        if evt.GetId() == 4:
            #Subtract
            selected_items = self.manipulation_panel.getSelectedItems()
            marked_item = self.manipulation_panel.getBackgroundItem()
            mainworker_cmd_queue.put(['subtract_items', [marked_item, selected_items]])

        elif evt.GetId() == 5:
            #Delete
            wx.CallAfter(self.manipulation_panel.removeSelectedItems)

        elif evt.GetId() == 6:
            #Average
            selected_items = self.manipulation_panel.getSelectedItems()
            mainworker_cmd_queue.put(['average_items', selected_items])

        elif evt.GetId() == 7:
            self.manipulation_panel.saveItems()

        elif evt.GetId() == 8:
            #Move to top plot
            plotpanel = wx.FindWindowByName('PlotPanel')
            selected_items = self.manipulation_panel.getSelectedItems()
            self.manipulation_panel.movePlots(selected_items, plotpanel.subplot1)
            wx.CallAfter(plotpanel.fitAxis)

        elif evt.GetId() == 9:
            #Move to bottom plot
            plotpanel = wx.FindWindowByName('PlotPanel')
            selected_items = self.manipulation_panel.getSelectedItems()
            self.manipulation_panel.movePlots(selected_items, plotpanel.subplot2)
            wx.CallAfter(plotpanel.fitAxis)

        elif evt.GetId() == 13:
            #Guinier fit
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSASMList = self.manipulation_panel.getSelectedItems()

            sasm = selectedSASMList[0].getSASM()
            Mainframe.showGuinierFitFrame(sasm, selectedSASMList[0])

        elif evt.GetId() == 14:
            dlg = RAWCustomDialogs.FilenameChangeDialog(self, self.sasm.getParameter('filename'))
            dlg.ShowModal()
            filename =  dlg.getFilename()
            dlg.Destroy()

            if filename:
                self.sasm.setParameter('filename', filename)
                self.updateFilenameLabel()
                self.markAsModified()

        elif evt.GetId() == 15:
            #A to s
            self.sasm.scaleBinnedQ(10.0)
            self._updateQTextCtrl()
            self.markAsModified()
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])

        elif evt.GetId() == 16:
            #s to A
            self.sasm.scaleBinnedQ(0.1)
            self._updateQTextCtrl()
            self.markAsModified()
            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])

        elif evt.GetId() == 18:
            dlg = RAWCustomDialogs.SaveAnalysisInfoDialog(self, self.main_frame.raw_settings, self.manipulation_panel.getSelectedItems())
            dlg.ShowModal()
            dlg.Destroy()

        elif evt.GetId() == 19:
            #Show Image
            self._onShowImage()

        elif evt.GetId() == 20:
            dlg = RAWCustomDialogs.DataDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()

            wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])

        elif evt.GetId() == 21:
            dlg = RAWCustomDialogs.HdrDataDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()

        elif evt.GetId() == 22:
            selected_items = self.manipulation_panel.getSelectedItems()
            marked_item = self.manipulation_panel.getBackgroundItem()
            mainworker_cmd_queue.put(['merge_items', [marked_item, selected_items]])

        elif evt.GetId() == 23:
            selected_items = self.manipulation_panel.getSelectedItems()

            dlg = RAWCustomDialogs.RebinDialog(self)
            retval = dlg.ShowModal()
            ret, logbin = dlg.getValues()
            dlg.Destroy()

            if retval != wx.ID_CANCEL:
                mainworker_cmd_queue.put(['rebin_items', [selected_items, ret, logbin]])

        elif evt.GetId() == 25:
            selected_items = self.manipulation_panel.getSelectedItems()
            marked_item = self.manipulation_panel.getBackgroundItem()
            mainworker_cmd_queue.put(['interpolate_items', [marked_item, selected_items]])

        elif evt.GetId() == 27:
           self.useAsMWStandard()

        elif evt.GetId() == 28:
           selected_items = self.manipulation_panel.getSelectedItems()
           mainworker_cmd_queue.put(['normalize_conc', [selected_items]])

        elif evt.GetId() == 29:
            #Molecular weight panel fit
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSASMList = self.manipulation_panel.getSelectedItems()

            sasm = selectedSASMList[0].getSASM()
            Mainframe.showMolWeightFrame(sasm, selectedSASMList[0])

        elif evt.GetId() == 30:
            #Save All Analysis Info
            self._saveAllAnalysisInfo()

        elif evt.GetId() == 31:
            #Open the GNOM window
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSASMList = self.manipulation_panel.getSelectedItems()

            sasm = selectedSASMList[0].getSASM()
            Mainframe.showGNOMFrame(sasm, selectedSASMList[0])

        elif evt.GetId() == 32:
            #Open the GNOM window
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSASMList = self.manipulation_panel.getSelectedItems()

            sasm = selectedSASMList[0].getSASM()
            Mainframe.showBIFTFrame(sasm, selectedSASMList[0])

        elif evt.GetId() == 33:
            #Show the history viewer dialog
            dlg = RAWCustomDialogs.HistoryDialog(self, self.sasm)
            dlg.ShowModal()
            dlg.Destroy()

        elif evt.GetId() == 34:
            #Run SVD on the selected profiles
            self._runSVD()

        elif evt.GetId() == 35:
            #Run EFA on the selected profiles
            self._runEFA()

        elif evt.GetId() == 36:
            #Weighted Average
            selected_items = self.manipulation_panel.getSelectedItems()
            mainworker_cmd_queue.put(['weighted_average_items', selected_items])

        elif evt.GetId() == 37:
            #Similarity testing
            Mainframe = wx.FindWindowByName('MainFrame')
            selected_items = self.manipulation_panel.getSelectedItems()

            if selected_items:
                selected_sasms = [item.getSASM() for item in selected_items]
            else:
                selected_sasms = []

            Mainframe.showSimilarityFrame(selected_sasms)

        elif evt.GetId() == 38:
            #Normalized Kratky Plots
            Mainframe = wx.FindWindowByName('MainFrame')
            selected_items = self.manipulation_panel.getSelectedItems()

            if selected_items:
                selected_sasms = [item.getSASM() for item in selected_items]
            else:
                selected_sasms = []

            Mainframe.showNormKratkyFrame(selected_sasms)

        elif evt.GetId() == 39:
            self.manipulation_panel.Sync()

        elif evt.GetId() == 40:
            self.manipulation_panel.Superimpose()


    def _saveAllAnalysisInfo(self):
        selected_items = self.manipulation_panel.getSelectedItems()

        selected_sasms = [item.sasm for item in selected_items]

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        if len(selected_sasms) >= 1:

            filters = 'Comma Separated Files (*.csv)|*.csv'

            fname = 'RAW_analysis.csv'
            msg = "Please select save directory and enter save file name"
            dialog = wx.FileDialog( None, message = msg, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = path, defaultFile = fname)

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
            else:
                return

            path=os.path.splitext(path)[0]+'.csv'
            save_path = path

        else:
            return

        mainworker_cmd_queue.put(['save_all_analysis_info', [save_path, selected_sasms]])

    def _runSVD(self):
        Mainframe = wx.FindWindowByName('MainFrame')

        selected_items = self.manipulation_panel.getSelectedItems()

        if len(selected_items) > 1:
            selected_sasms = [item.sasm for item in selected_items]

            selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

            frame_list = range(len(selected_sasms))

            secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

            Mainframe.showSVDFrame(secm, None)

        else:
            msg = 'You must select at least 2 scattering profiles to run EFA.'
            dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def _runEFA(self):
        Mainframe = wx.FindWindowByName('MainFrame')

        selected_items = self.manipulation_panel.getSelectedItems()

        if len(selected_items) > 1:
            selected_sasms = [item.sasm for item in selected_items]

            selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

            frame_list = range(len(selected_sasms))

            secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

            Mainframe.showEFAFrame(secm, None)

        else:
            msg = 'You must select at least 2 scattering profiles to run SVD.'
            dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def _onKeyPress(self, evt):

        key = evt.GetKeyCode()

        if ((key == wx.WXK_DELETE) or (key == wx.WXK_BACK and evt.CmdDown())) and self._selected == True:
            self.removeSelf()

        elif key == 83: #S
            self._onShowImage()

        elif key == 65 and evt.CmdDown(): #A
            self.manipulation_panel.selectAll()


    def _onRightMouseButton(self, evt):
        self.SetFocusIgnoringChildren()

        if not self._selected:
            self.toggleSelect()
            self.manipulation_panel.deselectAllExceptOne(self)

        #This is stupid. In wxpython 2.8, calling with the call after means no popup menu when multiple
        #items are selected. In wxpython 3.0, calling without the callafter creates a segfault on mac.
        #In wxpython 3.0 on linux (debian), with the callafter causes the menu to only show while you hold
        #down the button.
        if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
            wx.CallAfter(self._showPopupMenu)
        else:
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
                item_list = manipulation_panel.all_manipulation_items[bottom_item+adj:top_item+adj]
                for i in range(len(item_list)):
                    each = item_list[i]
                    if i != len(item_list)-1:
                        each.toggleSelect(update_info = False)
                    else:
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
        event.Skip()

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

        self.markAsModified()
        event.Skip()

    def _updateQTextCtrl(self):
        qmin_ctrl = wx.FindWindowById(self.spin_controls[0][1], self)
        qmax_ctrl = wx.FindWindowById(self.spin_controls[1][1], self)

        qmintxt = wx.FindWindowById(self.spin_controls[0][2], self)
        qmaxtxt = wx.FindWindowById(self.spin_controls[1][2], self)

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

    def _updateLegendLabel(self, update_plot=True):

        if self._legend_label == '' or self._legend_label == None:
            self.sasm.line.set_label(self.sasm.getParameter('filename'))
            self.legend_label_text.SetLabel('')
        else:
            self.sasm.line.set_label(str(self._legend_label))
            self.legend_label_text.SetLabel('[' + str(self._legend_label) + ']')

        if update_plot:
            wx.CallAfter(self.sasm.plot_panel.updateLegend, self.sasm.axes)


    def _onQrangeChange(self, event):
        self._updateQTextCtrl()
        wx.CallAfter(self.sasm.plot_panel.updatePlotAfterManipulation, [self.sasm])
        self.markAsModified()

    def _onEnterInQrangeTextCtrl(self, evt):

        id = evt.GetId()
        txtctrl = wx.FindWindowById(id, self)

        try:
            val = float(txtctrl.GetValue())
        except ValueError:
            self._showInvalidValueError()
            return

        if id == self.spin_controls[0][2]:
                spinctrl = wx.FindWindowById(self.spin_controls[0][1], self)
        elif id == self.spin_controls[1][2]:
                spinctrl = wx.FindWindowById(self.spin_controls[1][1], self)

        q = self.sasm.getBinnedQ()

        findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))

        closest = findClosest(val, q)
        idx = np.where(q == closest)[0][0]

        spinctrl.SetValue(idx)
        self._onQrangeChange(None)
        txtctrl.SelectAll()
        evt.Skip()

    def _onShowItem(self, event):
        self._selected_for_plot = not self._selected_for_plot

        self.showItem(self._selected_for_plot)

        self.GetParent().Layout()
        self.GetParent().Refresh()

        self.plot_panel.updateLegend(self.sasm.axes, False)

        self.sasm.plot_panel.fitAxis([self.sasm.axes])

        event.Skip()

    def _createFloatSpinCtrls(self, control_sizer):

        for label, id, name, initValue, bindfunc in self.float_spin_controls:

            label = wx.StaticText(self, -1, label)

            if platform.system() != 'Darwin':
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
            # spin_range = each_spinctrl[3]
            spin_name = each_spinctrl[4]

            nlow, nhigh = 0, (len(self.sasm.getBinnedQ())-1)

            spin_label = wx.StaticText(self, -1, spin_label_text)

            if platform.system() != 'Darwin':
                spin_label.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
                spin_label.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
                spin_label.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

            spin_control = RAWCustomCtrl.IntSpinCtrl(self, spin_id, min = nlow, max = nhigh, TextLength = 43)

            if spin_name == 'nlow':
                spin_control.SetValue(nlow)
            elif spin_name == 'nhigh':
                spin_control.SetValue(nhigh)

            spin_control.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onQrangeChange)

            q_ctrl = wx.TextCtrl(self, qtxtId, '', size = (55,-1), style = wx.TE_PROCESS_ENTER)
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

        self.buttons = (("Save", self._onSaveButton),
                        ("Remove", self._onRemoveButton),
                        ("Clear IFT Data", self._onClearList))

        # /* INSERT WIDGETS */

        self.panelsizer = wx.BoxSizer(wx.VERTICAL)

        self._initializeIcons()
        toolbarsizer = self._createToolbar()

        self.underpanel = scrolled.ScrolledPanel(self, -1, style = wx.BORDER_SUNKEN)
        self.underpanel.SetVirtualSize((200, 200))
        self.underpanel.SetScrollRate(20,20)

        file_drop_target = RAWCustomCtrl.RawPanelFileDropTarget(self.underpanel, 'ift')
        self.underpanel.SetDropTarget(file_drop_target)

        self.underpanel.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        self.all_manipulation_items = []
        self.selected_item_list = []
        self.modified_items = []

        self.underpanel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.underpanel.SetSizer(self.underpanel_sizer)

        self.panelsizer.Add(toolbarsizer, 0, wx.LEFT | wx.TOP | wx.RIGHT | wx.EXPAND, 5)
        self.panelsizer.Add(self.underpanel, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 3)

        self.createButtons(self.panelsizer)

        self.SetSizer(self.panelsizer)

        self._star_marked_item = None
        self._raw_settings = raw_settings

    def _initializeIcons(self):

        #Icons for the IFTPanel and IFTItemPanel
        show_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-eye-16.png')
        hide_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-hide-16.png')
        select_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-select-all-16.png')

        self.show_all_png = wx.Bitmap(show_all, wx.BITMAP_TYPE_PNG)
        self.hide_all_png = wx.Bitmap(hide_all, wx.BITMAP_TYPE_PNG)
        self.select_all_png = wx.Bitmap(select_all, wx.BITMAP_TYPE_PNG)

        #Icons for the IFTItemPanel
        target = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-16.png')
        target_on = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-red-16.png')
        info = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-info-16.png')

        self.info_png = wx.Bitmap(info, wx.BITMAP_TYPE_PNG)
        self.target_png = wx.Bitmap(target, wx.BITMAP_TYPE_PNG)
        self.target_on_png = wx.Bitmap(target_on, wx.BITMAP_TYPE_PNG)

    def _createToolbar(self):

        sizer = wx.BoxSizer()

        if platform.system() == 'Darwin':
            size = (28, -1)
        else:
            size = (-1, -1)

        show_all = wx.BitmapButton(self, -1, self.show_all_png, size=size)
        hide_all = wx.BitmapButton(self, -1, self.hide_all_png, size=size)
        select_all= wx.BitmapButton(self, -1, self.select_all_png)


        if platform.system() == 'Darwin':
            show_tip = STT.SuperToolTip(" ", header = "Show", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            show_tip.SetTarget(show_all)
            show_tip.ApplyStyle('Blue Glass')

            hide_tip = STT.SuperToolTip(" ", header = "Hide", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            hide_tip.SetTarget(hide_all)
            hide_tip.ApplyStyle('Blue Glass')

            select_tip = STT.SuperToolTip(" ", header = "Select All", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            select_tip.SetTarget(select_all)
            select_tip.ApplyStyle('Blue Glass')

        else:
            select_all.SetToolTip(wx.ToolTip('Select All'))
            show_all.SetToolTip(wx.ToolTip('Show'))
            hide_all.SetToolTip(wx.ToolTip('Hide'))

        show_all.Bind(wx.EVT_BUTTON, self._onShowAllButton)
        hide_all.Bind(wx.EVT_BUTTON, self._onHideAllButton)
        select_all.Bind(wx.EVT_BUTTON, self._onSelectAllButton)

        sizer.Add(show_all, 0, wx.LEFT, 5)
        sizer.Add(hide_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)
        sizer.Add(select_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)

        return sizer


    def addItem(self, iftm_list, item_colour = 'black', item_visible = True, notsaved = False, legend_label=defaultdict(str)):
        if not isinstance(iftm_list, list):
            iftm_list = [iftm_list]

        for iftm in iftm_list:
            newItem = IFTItemPanel(self.underpanel, iftm, font_colour = item_colour,
                ift_parameters = iftm.getAllParameters(), item_visible = item_visible,
                modified = notsaved, legend_label=legend_label)
            self.underpanel_sizer.Add(newItem, 0, wx.GROW)

            iftm.item_panel = newItem

            # Keeping track of all items in our list:
            self.all_manipulation_items.append(newItem)

            try:
                newItem._updateColourIndicator()
            except AttributeError:
                pass


        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

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
        rest_of_items = []

        self._star_marked_item = None
        self.selected_item_list = []
        self.modified_items = []

        for each in self.all_manipulation_items:
            try:
                each.Destroy()
            except ValueError:
                rest_of_items.append(each)

        self.all_manipulation_items = rest_of_items

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

    def clearBackgroundItem(self):
        self._raw_settings.set('BackgroundSASM', None)
        self._star_marked_item = None

    def getSelectedItems(self):

        self.selected_item_list = []

        for each in self.all_manipulation_items:
            if each._selected == True:
                self.selected_item_list.append(each)

        return self.selected_item_list

    def _onSelectAllButton(self, event):
        self.selectAll()

    def selectAll(self):
        for i in range(len(self.all_manipulation_items)):
            each = self.all_manipulation_items[i]
            each._selected = False
            if i != len(self.all_manipulation_items) -1:
                each.toggleSelect(update_info = False)
            else:
                each.toggleSelect()

    def deselectAllExceptOne(self, item, line = None, enableLocatorLine = False):

        if line == None:
            for each in self.all_manipulation_items:
                if each != item:
                    each._selected = True
                    each.toggleSelect(update_info=False)
        else:
            for each in self.all_manipulation_items:
                if line in each.lines:
                    each._selected = False
                    each.toggleSelect(update_info = False)
                else:
                    each._selected = True
                    each.toggleSelect(update_info = False)

    def removeSelectedItems(self):

        if len(self.getSelectedItems()) == 0:
            return

        for each in self.getSelectedItems():
            for line in each.lines:
                try:
                    line.remove()
                except (IndexError, ValueError):
                    pass

            try:
                each.iftm.r_err_line[0][0].remove()
                each.iftm.r_err_line[0][1].remove()
                each.iftm.r_err_line[1][0].remove()

                each.iftm.qo_err_line[0][0].remove()
                each.iftm.qo_err_line[0][1].remove()
                each.iftm.qo_err_line[1][0].remove()

                i = self.iftplot_panel.plotted_iftms.index(each.iftm)
                self.iftplot_panel.plotted_iftms.pop(i)
            except (IndexError, ValueError):
                    pass

            idx = self.all_manipulation_items.index(each)
            self.all_manipulation_items[idx].Destroy()
            self.all_manipulation_items.pop(idx)

        wx.CallAfter(self.iftplot_panel.updateLegend, 1, False)
        wx.CallAfter(self.iftplot_panel.updateLegend, 2, False)

        wx.CallAfter(self.iftplot_panel.fitAxis)

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

    def _onShowAllButton(self, event):

        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
               each.showItem(True)

        else:
            for each in selected_items:
                each.showItem(True)

        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

        wx.CallAfter(self.iftplot_panel.updateLegend, 1, False)
        wx.CallAfter(self.iftplot_panel.updateLegend, 2, False)
        wx.CallAfter(self.iftplot_panel.fitAxis)

    def _onHideAllButton(self, event):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
               each.showItem(False)

        else:
            for each in selected_items:
                each.showItem(False)

        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

        wx.CallAfter(self.iftplot_panel.updateLegend, 1, False)
        wx.CallAfter(self.iftplot_panel.updateLegend, 2, False)
        wx.CallAfter(self.iftplot_panel.fitAxis)

    def _onRemoveButton(self, event):
        self.removeSelectedItems()

    def _onSaveButton(self, event):
        self.saveItems()

    def getItems(self):
        return self.all_manipulation_items

    def saveItems(self):
        selected_items = self.getSelectedItems()

        selected_items = self.getSelectedItems()

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        if len(selected_items) == 1:

            item = selected_items[0]
            iftm = item.iftm
            if iftm.getParameter('algorithm') == 'GNOM':
                file_ext = '.out'
            else:
                file_ext = '.ift'


            # filters = 'Comma Separated Files (*.csv)|*.csv'

            # dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path)
            fname = os.path.splitext(os.path.basename(selected_items[0].iftm.getParameter('filename')))[0]+file_ext
            msg = "Please select save directory and enter save file name"
            dialog = wx.FileDialog(self, message = msg, style = wx.FD_SAVE, defaultDir = path, defaultFile = fname)

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
            else:
                return

            path=os.path.splitext(path)[0]+file_ext
            filename = os.path.basename(path)
            selected_items[0].iftm.setParameter('filename', filename)
            wx.CallAfter(selected_items[0].updateFilenameLabel)

            save_path = os.path.dirname(path)

        elif len(selected_items) == 0:
            return

        else:
            dirdlg = wx.DirDialog(self, "Please select save directory (multiple files will be saved):", defaultPath = path,)

            if dirdlg.ShowModal() == wx.ID_OK:
                path = dirdlg.GetPath()
            else:
                return
            save_path = path

        mainworker_cmd_queue.put(['save_iftitems', [save_path, selected_items]])

    def _onClearList(self, evt):
        self.iftplot_panel.clearAllPlots()
        self.clearList()

    def _CreateFileDialog(self, mode):

        file = None

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        if mode == wx.FD_OPEN:
            filters = 'All files (*.*)|*.*|Rad files (*.rad)|*.rad|Dat files (*.dat)|*.dat|Txt files (*.txt)|*.txt'
            dialog = wx.FileDialog( None, 'Select a file', load_path, style = mode, wildcard = filters)
        if mode == wx.FD_SAVE:
            filters = 'Dat files (*.dat)|*.dat'
            dialog = wx.FileDialog( None, 'Name file and location', load_path, style = mode | wx.FD_OVERWRITE_PROMPT, wildcard = filters)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()

        # Destroy the dialog
        dialog.Destroy()

        return file

    def createButtons(self, panelsizer):

        sizer = wx.GridSizer(cols=3, rows=np.ceil(len(self.buttons)/3), hgap=3, vgap=3)

        #sizer.Add((10,10) ,1 , wx.EXPAND)
        for each in self.buttons:
            if each:

                label = each[0]
                bindfunc = each[1]

                button = wx.Button(self, -1, label)
                button.Bind(wx.EVT_BUTTON, bindfunc)

                sizer.Add(button, 1, wx.EXPAND | wx.ALIGN_CENTER)

        panelsizer.Add(sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP | wx.ALIGN_CENTRE | wx.EXPAND, 10)

    def _onKeyPress(self, evt):
        key = evt.GetKeyCode()

        if key == 65 and evt.CmdDown():
            self.selectAll()


class IFTItemPanel(wx.Panel):
    def __init__(self, parent, iftm, font_colour = 'BLACK', legend_label = defaultdict(str),
        ift_parameters = {}, item_visible = True, modified = False):

        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)

        self.parent = parent
        self.iftm = iftm
        self.iftm.itempanel = self
        self.ift_parameters = ift_parameters

        self.lines = [self.iftm.r_line, self.iftm.qo_line, self.iftm.qf_line]

        self.plot_panel = wx.FindWindowByName('PlotPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.ift_panel = wx.FindWindowByName('IFTPanel')

        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.ift_plot_panel = wx.FindWindowByName('IFTPlotPanel')

        self.info_settings = {'hdr_choice' : 0}

        self._selected_as_bg = False
        self._selected_for_plot = item_visible
        self._controls_visible = True
        self._selected = False
        self._legend_label = legend_label

        self._font_colour = font_colour

        filename = iftm.getParameter('filename')

        opsys = platform.system()

        if self.iftm.getParameter('algorithm') == 'GNOM':
            self.is_gnom = True
        else:
            self.is_gnom = False

        self.raw_settings = self.main_frame.raw_settings

        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        self._initializeIcons()

        self.showitem_icon = wx.StaticBitmap(self, wx.ID_ANY, self.show_png)
        self.showitem_icon.Bind(wx.EVT_LEFT_DOWN, self._onShowItem)

        self.item_name = wx.StaticText(self, wx.ID_ANY, filename)
        self.item_name.SetForegroundColour(font_colour)

        self.legend_label_text = wx.StaticText(self, -1, '')

        if opsys != 'Darwin':
            self.item_name.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            self.item_name.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            self.item_name.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

            self.legend_label_text.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            self.legend_label_text.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            self.legend_label_text.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        color = [1,1,1]
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self.colour_indicator = RAWCustomCtrl.ColourIndicator(self, -1, color, size = (20,15))
        self.colour_indicator.Bind(wx.EVT_LEFT_DOWN, self._onLinePropertyButton)

        self.target_icon = wx.StaticBitmap(self, -1, self.target_png)
        self.target_icon.Bind(wx.EVT_LEFT_DOWN, self._onTargetButton)

        self.info_icon = wx.StaticBitmap(self, -1, self.info_png)

        if opsys == 'Darwin':
            show_tip = STT.SuperToolTip(" ", header = "Show Plot", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            show_tip.SetTarget(self.showitem_icon)
            show_tip.ApplyStyle('Blue Glass')

            line_tip = STT.SuperToolTip(" ", header = "Line Properties", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            line_tip.SetTarget(self.colour_indicator)
            line_tip.ApplyStyle('Blue Glass')

            target_tip = STT.SuperToolTip(" ", header = "Locate Line", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            target_tip.SetTarget(self.target_icon)
            target_tip.ApplyStyle('Blue Glass')

            info_str = "Dmax: {}\nMethod: {}".format(self.iftm.getParameter('dmax'), self.iftm.getParameter('algorithm'))
            info_tip = STT.SuperToolTip(info_str, header="Extended Info", footer="")
            info_tip.SetTarget(self.info_icon)
            info_tip.ApplyStyle("Blue Glass")

        else:
            self.showitem_icon.SetToolTip(wx.ToolTip('Show Plot'))
            self.colour_indicator.SetToolTip(wx.ToolTip('Line Properties'))
            self.target_icon.SetToolTip(wx.ToolTip('Locate Line'))
            info_str = "Extended Info\n--------------------------------\nDmax: {}\nMethod: {}".format(self.iftm.getParameter('dmax'), self.iftm.getParameter('algorithm'))
            self.info_icon.SetToolTip(wx.ToolTip(info_str))

        self.locator_on = False
        self.locator_old_width = {}
        self.locator_old_marker = {}

        panelsizer = wx.BoxSizer()
        panelsizer.Add(self.showitem_icon, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add(self.item_name, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add(self.legend_label_text, 0, wx.LEFT | wx.TOP, 3)
        panelsizer.Add((1,1), 1, wx.EXPAND)
        panelsizer.Add(self.info_icon, 0, wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 5)
        panelsizer.Add(self.target_icon, 0, wx.RIGHT | wx.TOP, 4)
        panelsizer.Add(self.colour_indicator, 0, wx.RIGHT | wx.TOP, 5)

        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(panelsizer, 1, wx.EXPAND)


        self.topsizer.Add((5,5),0)

        self.SetSizer(self.topsizer)

        self.SetBackgroundColour(wx.Colour(250,250,250))

        self.updateShowItem()

        self._updateLegendLabel(False)

        if modified:
            parent = self.GetParent()

            filename = self.iftm.getParameter('filename')
            self.item_name.SetLabel('* ' + str(filename))
            self.item_name.Refresh()

            if self not in self.ift_panel.modified_items:
                self.ift_panel.modified_items.append(self)


    def setCurrentIFTParameters(self, ift_parameters):
        self.ift_parameters = ift_parameters

    def getIftParameters(self):
        return self.ift_parameters

    def updateShowItem(self):
        if not self._selected_for_plot:
            self.showitem_icon.SetBitmap(self.hide_png)
        else:
            self.showitem_icon.SetBitmap(self.show_png)

        for line in self.lines:
            line.set_picker(self._selected_for_plot)

    def markAsModified(self, updateSelf = True, updateParent = True):
        filename = self.iftm.getParameter('filename')

        self.item_name.SetLabel('* ' + str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()

        if self not in self.ift_panel.modified_items:
            self.ift_panel.modified_items.append(self)

    def unmarkAsModified(self, updateSelf = True, updateParent = True):
        filename = self.iftm.getParameter('filename')

        self.item_name.SetLabel(str(filename))
        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()
        try:
            self.ift_panel.modified_items.remove(self)
        except:
            pass

    def removeSelf(self):
        #Has to be callafter under Linux.. or it'll crash
        wx.CallAfter(self.ift_panel.removeSelectedItems)

    def getIFTM(self):
        return self.iftm

    def getFontColour(self):
        return self._font_colour

    def getSelectedForPlot(self):
        return self._selected_for_plot

    def getLegendLabel(self):
        return self._legend_label

    def toggleSelect(self, set_focus = False, update_info = True):

        if self._selected:
            self._selected = False
            self.SetBackgroundColour(wx.Colour(250,250,250))
            # if update_info:
                # self.info_panel.clearInfo()
        else:
            self._selected = True
            self.SetBackgroundColour(wx.Colour(200,200,200))
            if set_focus:
                self.SetFocusIgnoringChildren()
            # if update_info:
                # self.info_panel.updateInfoFromItem(self)

        self.Refresh()

    def enableLocatorLine(self):

        self.locator_on = not self.locator_on

        if self.locator_on:
            self.target_icon.SetBitmap(self.target_on_png)
        else:
            self.target_icon.SetBitmap(self.target_png)

        for line in self.lines:
            if self.locator_on:
                self.locator_old_width[line] = line.get_linewidth()
                self.locator_old_marker[line] = line.get_markersize()

                new_width = self.locator_old_width[line] + 2.0
                new_marker = self.locator_old_marker[line] + 2.0

                line.set_linewidth(new_width)
                line.set_markersize(new_marker)

                wx.CallAfter(self.iftm.plot_panel.canvas.draw)
            else:
                line.set_linewidth(self.locator_old_width[line])
                line.set_markersize(self.locator_old_marker[line])
                wx.CallAfter(self.iftm.plot_panel.canvas.draw)

        self.target_icon.Refresh()

    def showItem(self, state):
        self._selected_for_plot = state

        if not self._selected_for_plot:
            self.showitem_icon.SetBitmap(self.hide_png)
        else:
            self.showitem_icon.SetBitmap(self.show_png)

        for line in self.lines:
            line.set_visible(state)
            line.set_picker(state)      #Line can't be selected when it's hidden

        each = self.iftm
        item_plot_panel = each.plot_panel
        err_bars = item_plot_panel.plotparams['errorbars_on']

        if err_bars:
            for each_err_line in each.r_err_line[0]:
                each_err_line.set_visible(state)

            for each_err_line in each.r_err_line[1]:
                each_err_line.set_visible(state)

            for each_err_line in each.qo_err_line[0]:
                each_err_line.set_visible(state)

            for each_err_line in each.qo_err_line[1]:
                each_err_line.set_visible(state)

            for each_err_line in each.r_err_line[0]:
                each_err_line.set_visible(state)

            for each_err_line in each.r_err_line[1]:
                each_err_line.set_visible(state)

            item_plot_panel.updateErrorBars(each)

    def updateFilenameLabel(self, updateSelf = True, updateParent = True, updateLegend = True):
        filename = self.iftm.getParameter('filename')

        if self._legend_label == '':
            for line in self.lines:
                current_label = line.get_label()

                line.set_label(filename+current_label.split('_')[-1])

        if updateLegend:
            self.ift_plot_panel.updateLegend(1)
            self.ift_plot_panel.updateLegend(2)

        self.item_name.SetLabel(str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()

    def _initializeIcons(self):

        self.target_png = self.ift_panel.target_png
        self.target_on_png = self.ift_panel.target_on_png
        self.info_png = self.ift_panel.info_png
        self.show_png = self.ift_panel.show_all_png
        self.hide_png = self.ift_panel.hide_all_png

    def _updateColourIndicator(self):
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.iftm.r_line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self.colour_indicator.updateColour(color)

    def _onLinePropertyButton(self, event):
        try:
            legend_label = self.getLegendLabel()
            dialog = RAWCustomDialogs.IFTMLinePropertyDialog(self, self.iftm, legend_label)
            answer = dialog.ShowModal()
            new_legend_labels = dialog.getLegendLabel()
            self._updateColourIndicator()
            dialog.Destroy()

            if answer == wx.ID_OK:
                self._legend_label = new_legend_labels
                self._updateLegendLabel()

        except TypeError:
            return

    def _onTargetButton(self, event):
        self.enableLocatorLine()

    def _showPopupMenu(self):
        opsys = platform.system()

        menu = wx.Menu()


        menu.Append(14, 'Rename')
        menu.AppendSeparator()
        menu.Append(22, 'To Main Plot')

        if self.is_gnom:
            if opsys == 'Windows':
                if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'ambimeter.exe')):
                    menu.Append(24, 'AMBIMETER')
                if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'dammif.exe')):
                    menu.Append(23, 'Bead Model (DAMMIF/N)')
            else:
                if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'ambimeter')):
                    menu.Append(24, 'AMBIMETER')
                if os.path.exists(os.path.join(self.raw_settings.get('ATSASDir'), 'dammif')):
                    menu.Append(23, 'Bead Model (DAMMIF/N)')

        menu.Append(28, 'Electron Density (DENSS)')
        menu.Append(25, 'SVD')
        menu.Append(26, 'EFA')
        menu.Append(27, 'Similarity Test')

        menu.AppendSeparator()
        menu.Append(20, 'Show data')

        menu.AppendSeparator()
        menu.Append(5, 'Remove' )

        menu.AppendSeparator()
        menu.Append(7, 'Save selected file(s)')

        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        self.PopupMenu(menu)

        menu.Destroy()

    def _onPopupMenuChoice(self, evt):

        if evt.GetId() == 5:
            #Delete
            wx.CallAfter(self.ift_panel.removeSelectedItems)

        elif evt.GetId() == 7:
            self.ift_panel.saveItems()

        elif evt.GetId() == 14:
            dlg = RAWCustomDialogs.FilenameChangeDialog(self, self.iftm.getParameter('filename'))
            dlg.ShowModal()
            filename =  dlg.getFilename()
            dlg.Destroy()

            if filename:
                self.iftm.setParameter('filename', filename)
                self.updateFilenameLabel()
                self.markAsModified()

        elif evt.GetId() == 20:
            dlg = RAWCustomDialogs.IFTDataDialog(self, self.iftm)
            dlg.ShowModal()
            dlg.Destroy()

        elif evt.GetId() == 22:
            #To main plot
            self._toMainPlot()

        elif evt.GetId() == 23:
            #DAMMIF
            self.main_frame.showDAMMIFFrame(self.iftm, self)

        elif evt.GetId() == 24:
            #AMBIMETER
            self.main_frame.showAmbiFrame(self.iftm, self)

        elif evt.GetId() == 25:
            #SVD
            self._runSVD()

        elif evt.GetId() == 26:
            #EFA
            self._runEFA()

        elif evt.GetId() == 27:
            #Similarity testing
            selected_items = self.ift_panel.getSelectedItems()

            if selected_items:
                selected_iftms = [item.getIFTM() for item in selected_items]
                selected_sasms = [SASM.SASM(iftm.p, iftm.r, iftm.err, iftm.getAllParameters()) for iftm in selected_iftms]
            else:
                selected_sasms = []

            self.main_frame.showSimilarityFrame(selected_sasms)

        elif evt.GetId() == 28:
            #DENSS
            self.main_frame.showDenssFrame(self.iftm, self)

    def _toMainPlot(self):
        selected_items = self.ift_panel.getSelectedItems()

        sasm_list=[]

        for item in selected_items:
            filename = os.path.splitext(item.iftm.getParameter('filename'))[0]
            data_sasm = SASM.SASM(item.iftm.i_orig, item.iftm.q_orig, item.iftm.err_orig, {item.iftm.getParameter('algorithm') : item.iftm.getAllParameters(), 'filename' : filename+'_data'})
            fit_sasm = SASM.SASM(item.iftm.i_fit, item.iftm.q_orig, np.ones(len(item.iftm.i_fit)), {item.iftm.getParameter('algorithm') : item.iftm.getAllParameters(), 'filename' : filename+'_fit'})

            sasm_list.append(data_sasm)
            sasm_list.append(fit_sasm)

            if len(item.iftm.q_extrap) > 0:
                extrap_sasm = SASM.SASM(item.iftm.i_extrap, item.iftm.q_extrap, np.ones(len(item.iftm.i_extrap)), {item.iftm.getParameter('algorithm') : item.iftm.getAllParameters(), 'filename' : filename+'_extrap'})
                sasm_list.append(extrap_sasm)


        mainworker_cmd_queue.put(['to_plot', sasm_list])

    def _runSVD(self):
        Mainframe = wx.FindWindowByName('MainFrame')

        selected_items = self.ift_panel.getSelectedItems()

        if len(selected_items) > 1:

            selected_iftms = [item.iftm for item in selected_items]

            selected_sasms = [SASM.SASM(iftm.p, iftm.r, iftm.err, iftm.getAllParameters()) for iftm in selected_iftms]

            selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

            frame_list = range(len(selected_sasms))

            secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

            Mainframe.showSVDFrame(secm, None)

        else:
            msg = 'You must select at least 2 P(r) functions to run SVD.'
            dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def _runEFA(self):
        Mainframe = wx.FindWindowByName('MainFrame')

        selected_items = self.ift_panel.getSelectedItems()

        if len(selected_items) > 1:

            selected_iftms = [item.iftm for item in selected_items]

            selected_sasms = [SASM.SASM(iftm.p, iftm.r, iftm.err, iftm.getAllParameters()) for iftm in selected_iftms]

            selected_filenames = [sasm.getParameter('filename') for sasm in selected_sasms]

            frame_list = range(len(selected_sasms))

            secm = SASM.SECM(selected_filenames, selected_sasms, frame_list, {})

            Mainframe.showSVDFrame(secm, None)

        else:
            msg = 'You must select at least 2 P(r) functions to run EFA.'
            dlg = wx.MessageDialog(self, msg, "Not enough files selected", style = wx.ICON_INFORMATION | wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def _onKeyPress(self, evt):

        key = evt.GetKeyCode()

        if ((key == wx.WXK_DELETE) or (key == wx.WXK_BACK and evt.CmdDown())) and self._selected == True:
            self.removeSelf()

        elif key == 65 and evt.CmdDown(): #A
            self.ift_panel.selectAll()

    def _onRightMouseButton(self, evt):
        if not self._selected:
            self.toggleSelect()
            self.ift_panel.deselectAllExceptOne(self)

        if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
            wx.CallAfter(self._showPopupMenu)
        else:
            self._showPopupMenu()

    def _onLeftMouseButton(self, evt):
        ctrl_is_down = evt.CmdDown()
        shift_is_down = evt.ShiftDown()

        ift_panel = wx.FindWindowByName('IFTPanel')

        if shift_is_down:
            try:

                first_marked_item_idx = ift_panel.all_manipulation_items.index(ift_panel.getSelectedItems()[0])
                last_marked_item = ift_panel.getSelectedItems()[-1]
                last_marked_item_idx = ift_panel.all_manipulation_items.index(last_marked_item)

                this_item_idx = ift_panel.all_manipulation_items.index(self)

                if last_marked_item_idx > this_item_idx:
                    adj = 0
                    idxs = [first_marked_item_idx, this_item_idx]
                else:
                    idxs = [last_marked_item_idx, this_item_idx]
                    adj = 1

                top_item = max(idxs)
                bottom_item = min(idxs)

                item_list = ift_panel.all_manipulation_items[bottom_item+adj:top_item+adj]
                for i in range(len(item_list)):
                    each = item_list[i]
                    if i != len(item_list)-1:
                        each.toggleSelect(update_info = False)
                    else:
                        each.toggleSelect()
            except IndexError:
                pass

        elif ctrl_is_down:
            self.toggleSelect()
        else:
            ift_panel.deselectAllExceptOne(self)
            self.toggleSelect()

        evt.Skip()

    def _onStarButton(self, event):

        if self._selected_as_bg == True:
            self.enableStar(False)
            self.ift_panel.clearBackgroundItem()
        else:
            self.ift_panel.setItemAsBackground(self)

    def _updateLegendLabel(self, update_plot=True):

        labels = np.array(self._legend_label.values())

        if self._legend_label is None or len(labels) == 0 or np.all(labels == ''):
            self.iftm.r_line.set_label(self.iftm.getParameter('filename')+'_P(r)')
            self.iftm.qo_line.set_label(self.iftm.getParameter('filename')+'_Exp')
            self.iftm.qf_line.set_label(self.iftm.getParameter('filename')+'_Fit')

            self.legend_label_text.SetLabel('')
        else:
            if str(self._legend_label[self.iftm.r_line]) != '':
                self.iftm.r_line.set_label(str(self._legend_label[self.iftm.r_line]))
            else:
                self.iftm.r_line.set_label(self.iftm.getParameter('filename')+'_P(r)')
            if str(self._legend_label[self.iftm.qo_line]) != '':
                self.iftm.qo_line.set_label(str(self._legend_label[self.iftm.qo_line]))
            else:
                self.iftm.qo_line.set_label(self.iftm.getParameter('filename')+'_Exp')
            if str(self._legend_label[self.iftm.qf_line]) != '':
                self.iftm.qf_line.set_label(str(self._legend_label[self.iftm.qf_line]))
            else:
                self.iftm.qf_line.set_label(self.iftm.getParameter('filename')+'_Fit')

            if str(self._legend_label[self.iftm.r_line]) != self.iftm.getParameter('filename')+'_P(r)' and str(self._legend_label[self.iftm.r_line]) != '':
                self.legend_label_text.SetLabel('[' + str(self._legend_label[self.iftm.r_line]) + ']')
            else:
                self.legend_label_text.SetLabel('')

        if update_plot:
            wx.CallAfter(self.iftm.plot_panel.updateLegend, 1)
            wx.CallAfter(self.iftm.plot_panel.updateLegend, 2)

    def _onShowItem(self, event):
        self._selected_for_plot = not self._selected_for_plot

        self.showItem(self._selected_for_plot)

        self.GetParent().Layout()
        self.GetParent().Refresh()

        self.ift_plot_panel.updateLegend(self.iftm.r_axes, False)
        self.ift_plot_panel.updateLegend(self.iftm.qo_axes, False)

        self.iftm.plot_panel.fitAxis()

#--- ** SEC Panel **

class SECPanel(wx.Panel):
    def __init__(self, parent, raw_settings, expParams = []):
        wx.Panel.__init__(self, parent, name = 'SECPanel')

        self.expParams = expParams
        self._raw_settings = raw_settings
        self.sec_plot_panel = wx.FindWindowByName('SECPlotPanel')

        self.all_manipulation_items = []

        self.modified_items = []

        self.otherParams={'Frame List' : (self.NewControlId(), 'framelist'),
                        'Manual' : (self.NewControlId(), 'manual')}

        self.paramsInGui={'Image Header'           : (self.NewControlId(), 'imghdr'),
                          'Initial Run #'          : (self.NewControlId(), 'irunnum'),
                          'Initial Frame #'        : (self.NewControlId(), 'iframenum'),
                          'Final Frame #'          : (self.NewControlId(), 'fframenum'),
                          'Initial Selected Frame' : (self.NewControlId(), 'isframenum'),
                          'Final Selected Frame'   : (self.NewControlId(), 'fsframenum'),
                          'Initial Buffer Frame'   : (self.NewControlId(), 'ibufframe'),
                          'Final Buffer Frame'     : (self.NewControlId(), 'fbufframe'),
                          'Window Size'            : (self.NewControlId(), 'wsize')}

        self.buttons = (("Save",self._onSaveButton),
                        ("Remove", self._onRemoveButton),
                        ("Clear Series Data", self._onClearList))

        # /* INSERT WIDGETS */

        self.panelsizer = wx.BoxSizer(wx.VERTICAL)

        self._initializeIcons()
        toolbarsizer = self._createToolbar()

        self.underpanel = scrolled.ScrolledPanel(self, -1, style = wx.BORDER_SUNKEN)
        self.underpanel.SetVirtualSize((200, 200))
        self.underpanel.SetScrollRate(20,20)

        file_drop_target = RAWCustomCtrl.RawPanelFileDropTarget(self.underpanel, 'sec')
        self.underpanel.SetDropTarget(file_drop_target)

        self.underpanel.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        self.all_manipulation_items = []
        self.selected_item = []

        self.starred_item = None

        self.underpanel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.underpanel.SetSizer(self.underpanel_sizer)

        self.sec_control_panel = SECControlPanel(self)

        self.panelsizer.Add(self.sec_control_panel, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER | wx.EXPAND, 5)
        self.panelsizer.Add(toolbarsizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        self.panelsizer.Add(self.underpanel, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 3)

        self.createButtons(self.panelsizer)

        self.SetSizer(self.panelsizer)

    def _onRemoveButton(self, event):
        self.removeSelectedItems()


    def _onSaveButton(self, event):
        self._saveItems()

    def _initializeIcons(self):

        #Icons for the SECPanel
        show_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-eye-16.png')
        hide_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-hide-16.png')
        select_all = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-select-all-16.png')

        self.show_all_png = wx.Bitmap(show_all, wx.BITMAP_TYPE_PNG)
        self.hide_all_png = wx.Bitmap(hide_all, wx.BITMAP_TYPE_PNG)
        self.select_all_png = wx.Bitmap(select_all, wx.BITMAP_TYPE_PNG)

        #Icons for the SeriesItemPanel
        gray_star = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-star-filled-gray-16.png')
        orange_star = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-star-filled-orange-16.png')
        target = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-16.png')
        target_on = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-red-16.png')
        info = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-info-16.png')

        self.gray_png = wx.Bitmap(gray_star, wx.BITMAP_TYPE_PNG)
        self.star_png = wx.Bitmap(orange_star, wx.BITMAP_TYPE_PNG)
        self.target_png = wx.Bitmap(target, wx.BITMAP_TYPE_PNG)
        self.target_on_png = wx.Bitmap(target_on, wx.BITMAP_TYPE_PNG)
        self.info_png = wx.Bitmap(info, wx.BITMAP_TYPE_PNG)


    def _createToolbar(self):

        sizer = wx.BoxSizer()

        if platform.system() == 'Darwin':
            size = (28, -1)
        else:
            size = (-1, -1)

        select_all= wx.BitmapButton(self, -1, self.select_all_png)
        show_all = wx.BitmapButton(self, -1, self.show_all_png, size=size)
        hide_all = wx.BitmapButton(self, -1, self.hide_all_png,size=size)

        if platform.system() == 'Darwin':
            show_tip = STT.SuperToolTip(" ", header = "Show", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            show_tip.SetTarget(show_all)
            show_tip.ApplyStyle('Blue Glass')

            hide_tip = STT.SuperToolTip(" ", header = "Hide", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            hide_tip.SetTarget(hide_all)
            hide_tip.ApplyStyle('Blue Glass')

            select_tip = STT.SuperToolTip(" ", header = "Select All", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            select_tip.SetTarget(select_all)
            select_tip.ApplyStyle('Blue Glass')

        else:
            select_all.SetToolTip(wx.ToolTip('Select All'))
            show_all.SetToolTip(wx.ToolTip('Show'))
            hide_all.SetToolTip(wx.ToolTip('Hide'))


        # collapse_all.Bind(wx.EVT_BUTTON, self._onCollapseAllButton)
        # expand_all.Bind(wx.EVT_BUTTON, self._onExpandAllButton)
        show_all.Bind(wx.EVT_BUTTON, self._onShowAllButton)
        hide_all.Bind(wx.EVT_BUTTON, self._onHideAllButton)
        select_all.Bind(wx.EVT_BUTTON, self._onSelectAllButton)

        sizer.Add(show_all, 0, wx.LEFT, 5)
        sizer.Add(hide_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)
        sizer.Add(select_all, 0, wx.LEFT, 5)
        sizer.Add((1,1),1, wx.EXPAND)
        # sizer.Add(collapse_all, 0, wx.RIGHT, 5)
        # sizer.Add(expand_all, 0, wx.RIGHT, 3)

        return sizer

    def selectAll(self):
        for i in range(len(self.all_manipulation_items)):
            each = self.all_manipulation_items[i]
            each._selected = False
            if i != len(self.all_manipulation_items) -1:
                each.toggleSelect(update_info = False)
            else:
                each.toggleSelect()

    def _onShowAllButton(self, event):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
               each.showItem(True)

        else:
            for each in selected_items:
                each.showItem(True)

        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

        wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)
        wx.CallAfter(self.sec_plot_panel.fitAxis)

    def _onHideAllButton(self, event):
        self.underpanel.Freeze()

        selected_items = self.getSelectedItems()

        if len(selected_items) == 0:
            for each in self.all_manipulation_items:
               each.showItem(False)

        else:
            for each in selected_items:
                each.showItem(False)

        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

        wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)
        wx.CallAfter(self.sec_plot_panel.fitAxis)

    def _onCollapseAllButton(self, event):
        self._collapseAllItems()

    def _onExpandAllButton(self, event):
        self._expandAllItems()

    def _onSelectAllButton(self, event):
        self.selectAll()

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
                    each.toggleSelect(update_info = False)
        else:
            for each in self.all_manipulation_items:
                if each.secm.getLine() == line or each.secm.getCalcLine() == line:
                    each._selected = False
                    each.toggleSelect(update_info = False)
                else:
                    each._selected = True
                    each.toggleSelect(update_info = False)

    def removeSelectedItems(self):

        sec_control_panel = wx.FindWindowByName('SECControlPanel')

        if len(self.getSelectedItems()) == 0:
            return

        axes_that_needs_updated_legend = []

        for each in self.getSelectedItems():
            try:
                self.modified_items.remove(each)
            except:
                pass

            if each.secm == sec_control_panel.secm:
                sec_control_panel.secm = None

            if each.secm.line != None:
                plot_panel = each.secm.plot_panel
                try:
                    each.secm.line.remove()
                    if each.secm.origline != None:
                        each.secm.origline.remove()
                    i = plot_panel.plotted_secms.index(each.secm)
                    plot_panel.plotted_secms.pop(i)
                except (IndexError, ValueError):
                    pass

                if not each.secm.axes in axes_that_needs_updated_legend:
                    axes_that_needs_updated_legend.append(each.secm.axes)

            if each.secm.calc_line != None:
                plot_panel = each.secm.plot_panel
                try:
                    each.secm.calc_line.remove()
                except (IndexError, ValueError):
                    pass

            if each == self.starred_item:
                self.starred_item = None

            idx = self.all_manipulation_items.index(each)
            self.all_manipulation_items[idx].Destroy()
            self.all_manipulation_items.pop(idx)

        wx.CallAfter(self.sec_plot_panel.updateLegend, 1, False)

        wx.CallAfter(self.sec_plot_panel.fitAxis)

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

    def addItem(self, secm_list, item_colour = 'black', item_visible = True, notsaved = False, legend_label=defaultdict(str)):
        self.underpanel.Freeze()

        if not isinstance(secm_list, list):
            secm_list = [secm_list]

        for secm in secm_list:

            newItem = SeriesItemPanel(self.underpanel, secm, font_colour = item_colour,
                                     item_visible = item_visible, modified = notsaved,
                                     legend_label=legend_label)

            self.underpanel_sizer.Add(newItem, 0, wx.GROW)

            # Keeping track of all items in our list:
            self.all_manipulation_items.append(newItem)

            secm.item_panel = newItem

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.underpanel.Thaw()

    def saveData(self):
        selected_items = self.getSelectedItems()

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        if len(selected_items) == 1:

            filters = 'Comma Separated Files (*.csv)|*.csv'

            # dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path)
            fname = os.path.splitext(os.path.basename(selected_items[0].secm.getParameter('filename')))[0]+'.csv'
            msg = "Please select save directory and enter save file name"
            dialog = wx.FileDialog( None, message = msg, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = path, defaultFile = fname)

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
            else:
                return

            path=os.path.splitext(path)[0]+'.csv'
            save_path = [path]

        elif len(selected_items) == 0:
            return

        else:
            dirdlg = wx.DirDialog(self, "Please select save directory (multiple files will be saved):", defaultPath = path)

            if dirdlg.ShowModal() == wx.ID_OK:
                path = dirdlg.GetPath()
            else:
                return
            save_path=[]

            for item in selected_items:
                name=os.path.splitext(os.path.basename(item.secm.getParameter('filename')))[0]+'_sec_data.csv'
                save_path.append(os.path.join(path, name))


        mainworker_cmd_queue.put(['save_sec_data', [save_path, selected_items]])

    def _saveItems(self):
        selected_items = self.getSelectedItems()

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        if len(selected_items) == 1:

            # filters = 'Comma Separated Files (*.csv)|*.csv'

            # dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path)
            fname = os.path.splitext(os.path.basename(selected_items[0].secm.getParameter('filename')))[0]+'.sec'
            msg = "Please select save directory and enter save file name"
            dialog = wx.FileDialog(self, message = msg, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, defaultDir = path, defaultFile = fname)

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
            else:
                return

            path=os.path.splitext(path)[0]+'.sec'
            save_path = [path]

            name = os.path.split(path)[1]
            selected_items[0].secm.setParameter('filename', name)

        elif len(selected_items) == 0:
            return

        else:
            dirdlg = wx.DirDialog(self, "Please select save directory (multiple files will be saved):", defaultPath = path,)

            if dirdlg.ShowModal() == wx.ID_OK:
                path = dirdlg.GetPath()
            else:
                return
            save_path=[]

            for item in selected_items:
                name=os.path.splitext(os.path.split(item.secm.getParameter('filename'))[1])[0]+'.sec'
                save_path.append(os.path.join(path, name))


        mainworker_cmd_queue.put(['save_sec_item', [save_path, selected_items]])

    def _saveProfiles(self, profile_type):
        selected_items = self.getSelectedItems()

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        path = dirctrl_panel.getDirLabel()

        if len(selected_items) == 0:
            return

        else:
            dirdlg = wx.DirDialog(self, "Please select save directory (multiple files will be saved):", defaultPath = path,)

            if dirdlg.ShowModal() == wx.ID_OK:
                save_path = dirdlg.GetPath()
            else:
                return

            for item in selected_items:

                if profile_type == 'unsub':
                    sasms = item.secm._sasm_list
                elif profile_type == 'sub':
                    sasms = item.secm.subtracted_sasm_list
                elif profile_type == 'baseline':
                    sasms = item.secm.baseline_subtracted_sasm_list

                if sasms:
                    mainworker_cmd_queue.put(['save_sec_profiles', [save_path, sasms]])

    def _OnClearAll(self, evt):
        plotpage = wx.FindWindowByName('SECPlotPanel')
        plotpage.OnClear(0)

    def _onClearList(self, evt):
        self.sec_plot_panel.clearAllPlots()
        self.clearList()


    def clearList(self):
        rest_of_items = []

        self.modified_items = []
        self.selected_item = []
        self.starred_item = None

        for each in self.all_manipulation_items:

            try:
                each.Destroy()
            except ValueError:
                rest_of_items.append(each)
            except AttributeError:
                each = None

        self.all_manipulation_items = rest_of_items

        self.underpanel.SetVirtualSize(self.underpanel.GetBestVirtualSize())
        self.underpanel.Layout()
        self.underpanel.Refresh()

        self.sec_control_panel.clearAll()

    def _CreateFileDialog(self, mode):

        file = None

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        if mode == wx.FD_OPEN:
            filters = 'All files (*.*)|*.*|Rad files (*.rad)|*.rad|Dat files (*.dat)|*.dat|Txt files (*.txt)|*.txt'
            dialog = wx.FileDialog( None, 'Select a file', load_path, style = mode, wildcard = filters)
        if mode == wx.FD_SAVE:
            filters = 'Dat files (*.dat)|*.dat'
            dialog = wx.FileDialog( None, 'Name file and location', load_path, style = mode | wx.FD_OVERWRITE_PROMPT, wildcard = filters)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()

        # Destroy the dialog
        dialog.Destroy()

        return file

    def createButtons(self, panelsizer):

        sizer = wx.GridSizer(cols=3, rows=np.ceil(len(self.buttons)/3), hgap=3, vgap=3)

        #sizer.Add((10,10) ,1 , wx.EXPAND)
        for each in self.buttons:
            if each:

                label = each[0]
                bindfunc = each[1]

                button = wx.Button(self, -1, label)
                button.Bind(wx.EVT_BUTTON, bindfunc)

                sizer.Add(button, 1, wx.EXPAND | wx.ALIGN_CENTER)

        panelsizer.Add(sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP | wx.ALIGN_CENTRE | wx.EXPAND, 10)

    def setItemAsData(self, item):

        bg_secm = self._raw_settings.get('DataSECM')

        if bg_secm != None:
            try:
                bg_secm.itempanel.enableStar(False)
                self.clearDataItem()
            except:
                pass
        elif self.getDataItem() != None:
            bg_secm = self.getDataItem()
            try:
                bg_secm.itempanel.enableStar(False)
                self.clearDataItem()
            except:
                pass


        self._raw_settings.set('DataSECM', item.secm)
        item.enableStar(True)
        self.starred_item = item

    def getDataItem(self):
        return self.starred_item

    def clearDataItem(self):
        self._raw_settings.set('DataSECM', None)
        self.starred_item = None

    def getItems(self):
        return self.all_manipulation_items

    def _onKeyPress(self, evt):
        key = evt.GetKeyCode()

        if key == 65 and evt.CmdDown():
            self.selectAll()


class SeriesItemPanel(wx.Panel):
    def __init__(self, parent, secm, font_colour = 'BLACK', legend_label = defaultdict(str), item_visible = True, modified = False):

        wx.Panel.__init__(self, parent, style = wx.BORDER_RAISED)

        self.parent = parent
        self.secm = secm
        self.secm.itempanel = self

        self.sec_plot_panel = wx.FindWindowByName('SECPlotPanel')
        self.main_frame = wx.FindWindowByName('MainFrame')
        self.sec_control_panel = wx.FindWindowByName('SECControlPanel')
        self.sec_panel = wx.FindWindowByName('SECPanel')

        self.raw_settings = self.main_frame.raw_settings

        self.info_panel = wx.FindWindowByName('InformationPanel')
        self.info_settings = {'hdr_choice' : 0}

        self._selected_as_bg = False
        self._selected_for_plot = item_visible
        self._controls_visible = True
        self._selected = False
        self._legend_label = legend_label

        self._font_colour = font_colour

        filename = secm.getParameter('filename')

        opsys = platform.system()

        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
        self.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        self._initializeIcons()

        self.showitem_icon = wx.StaticBitmap(self, wx.ID_ANY, self.show_png)
        self.showitem_icon.Bind(wx.EVT_LEFT_DOWN, self._onShowItem)

        self.item_name = wx.StaticText(self, wx.ID_ANY, filename)
        self.item_name.SetForegroundColour(font_colour)

        self.legend_label_text = wx.StaticText(self, -1, '')

        if opsys != 'Darwin':
            self.item_name.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            self.item_name.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            self.item_name.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

            self.legend_label_text.Bind(wx.EVT_LEFT_DOWN, self._onLeftMouseButton)
            self.legend_label_text.Bind(wx.EVT_RIGHT_DOWN, self._onRightMouseButton)
            self.legend_label_text.Bind(wx.EVT_KEY_DOWN, self._onKeyPress)

        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.secm.line.get_mfc())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self.colour_indicator = RAWCustomCtrl.ColourIndicator(self, -1, color, size = (20,15))
        self.colour_indicator.Bind(wx.EVT_LEFT_DOWN, self._onLinePropertyButton)


        self.bg_star = wx.StaticBitmap(self, -1, self.gray_png)
        self.bg_star.Bind(wx.EVT_LEFT_DOWN, self._onStarButton)

        self.target_icon = wx.StaticBitmap(self, -1, self.target_png)
        self.target_icon.Bind(wx.EVT_LEFT_DOWN, self._onTargetButton)


        self.info_icon = wx.StaticBitmap(self, -1, self.info_png)

        if int(wx.__version__.split('.')[0]) >= 3 and opsys == 'Darwin':
            show_tip = STT.SuperToolTip(" ", header = "Show Plot", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            show_tip.SetTarget(self.showitem_icon)
            show_tip.ApplyStyle('Blue Glass')

            line_tip = STT.SuperToolTip(" ", header = "Line Properties", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            line_tip.SetTarget(self.colour_indicator)
            line_tip.ApplyStyle('Blue Glass')

            mark_tip = STT.SuperToolTip(" ", header = "Mark", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            mark_tip.SetTarget(self.bg_star)
            mark_tip.ApplyStyle('Blue Glass')

            target_tip = STT.SuperToolTip(" ", header = "Locate Line", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            target_tip.SetTarget(self.target_icon)
            target_tip.ApplyStyle('Blue Glass')

            msg = ("First buffer frame: N/A\nLast buffer frame: N/A\nAverage "
                "window size: N/A\nMol. type: N/A\nBaseline: N/A")
            self.info_tip = STT.SuperToolTip(msg, header = "Extended Info", footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
            self.info_tip.SetDrawHeaderLine(True)
            self.info_tip.SetTarget(self.info_icon)
            self.info_tip.ApplyStyle('Blue Glass')

        else:
            self.showitem_icon.SetToolTip(wx.ToolTip('Show Plot'))
            self.colour_indicator.SetToolTip(wx.ToolTip('Line Properties'))
            self.bg_star.SetToolTip(wx.ToolTip('Mark'))
            self.target_icon.SetToolTip(wx.ToolTip('Locate Line'))
            tip = ('Show Extended Info\n--------------------------------\n'
                'First buffer frame: N/A\nLast buffer frame: N/A\nAverage '
                'window size: N/A\nMol. type: N/A\nBaseline: N/A')
            self.info_icon.SetToolTip(wx.ToolTip(tip))

        self.locator_on = False
        self.locator_old_width = 1
        self.locator_old_marker = 1
        self.locator_old_width_calc = 1
        self.locator_old_marker_calc = 1

        panelsizer = wx.BoxSizer()
        panelsizer.Add(self.showitem_icon, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add(self.item_name, 0, wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL, 3)
        panelsizer.Add(self.legend_label_text, 0, wx.LEFT | wx.TOP, 3)
        panelsizer.Add((1,1), 1, wx.EXPAND)
        panelsizer.Add(self.info_icon, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.target_icon, 0, wx.RIGHT | wx.TOP, 4)
        panelsizer.Add(self.colour_indicator, 0, wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(self.bg_star, 0, wx.LEFT | wx.RIGHT | wx.TOP, 3)


        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(panelsizer, 1, wx.EXPAND)

        self.controlSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 3, hgap = 7)

        self.topsizer.Add((5,5),0)
        self.topsizer.Add(self.controlSizer, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)

        self.SetSizer(self.topsizer)

        self.SetBackgroundColour(wx.Colour(250,250,250))

        if self.secm.buffer_range:
            self.updateInfoTip()

        if modified:
            parent = self.GetParent()

            filename = self.secm.getParameter('filename')
            self.item_name.SetLabel('* ' + str(filename))
            self.item_name.Refresh()

            if self not in self.sec_panel.modified_items:
                self.sec_panel.modified_items.append(self)

        self.updateShowItem()

        self._updateLegendLabel(False)


    def updateInfoTip(self):

        buffer_range = self.secm.buffer_range
        window = self.secm.window_size
        mol_type = self.secm.mol_type
        mol_density = self.secm.mol_density

        if window == -1:
            if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                msg = ('First buffer frame: N/A\nLast buffer frame: N/A\n'
                    'Average window size: N/A\nMol. type: N/A\nBaseline: N/A')
                self.info_tip.SetMessage(msg)
            else:
                msg = ('Show Extended Info\n--------------------------------\n'
                    'First buffer frame: N/A\nLast buffer frame: N/A\n'
                    'Average window size: N/A\nMol. type: N/A\nBaseline: N/A')
                self.info_icon.SetToolTip(wx.ToolTip(msg))
        else:
            if not self.secm.already_subtracted:
                buffer_str = ',\n   '.join(['{} to {}'.format(r1, r2) for (r1, r2) in buffer_range])
                buffer_str = 'Buffer range:\n   {}\n'.format(buffer_str)
            else:
                buffer_str = 'Already subtracted\n'

            if self.secm.baseline_type != '':
                baseline = self.secm.baseline_type
            else:
                baseline = 'N/A'

            tip = ('{}Average window size: {}\nMol. type: {}\n'
                'Mol. density: {}\nBaseline: {}'.format(buffer_str, window,
                    mol_type, mol_density, baseline))

            if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                self.info_tip.SetMessage(tip)
            else:
                msg = ('Show Extended Info\n--------------------------------\n'
                    '{}'.format(tip))
                self.info_icon.SetToolTip(wx.ToolTip(msg))

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
        wx.CallAfter(self.sec_panel.removeSelectedItems)

    def getSECM(self):
        return self.secm

    def getFontColour(self):
        return self._font_colour

    def getSelectedForPlot(self):
        return self._selected_for_plot

    def getLegendLabel(self):
        return self._legend_label

    def toggleSelect(self, set_focus = False, update_info = True):

        if self._selected:
            self._selected = False
            self.SetBackgroundColour(wx.Colour(250,250,250))
        else:
            self._selected = True
            self.SetBackgroundColour(wx.Colour(200,200,200))
            if set_focus:
                self.SetFocusIgnoringChildren()

        self.Refresh()

    def enableLocatorLine(self):

        self.locator_on = not self.locator_on

        if self.locator_on:
            self.target_icon.SetBitmap(self.target_on_png)
            self.locator_old_width = self.secm.line.get_linewidth()
            self.locator_old_marker = self.secm.line.get_markersize()
            new_width = self.locator_old_width + 2.0
            new_marker = self.locator_old_marker + 2.0
            self.secm.line.set_linewidth(new_width)
            self.secm.line.set_markersize(new_marker)

            if self.secm.calc_has_data and self.secm.calc_is_plotted:
                self.locator_old_width_calc = self.secm.calc_line.get_linewidth()
                self.locator_old_marker_calc = self.secm.calc_line.get_markersize()
                new_width = self.locator_old_width_calc + 2.0
                new_marker = self.locator_old_marker_calc + 2.0
                self.secm.calc_line.set_linewidth(new_width)
                self.secm.calc_line.set_markersize(new_marker)

            wx.CallAfter(self.secm.plot_panel.canvas.draw)
        else:
            self.target_icon.SetBitmap(self.target_png)
            self.secm.line.set_linewidth(self.locator_old_width)
            self.secm.line.set_markersize(self.locator_old_marker)

            if self.secm.calc_has_data and self.secm.calc_is_plotted:
                self.secm.calc_line.set_linewidth(self.locator_old_width_calc)
                self.secm.calc_line.set_markersize(self.locator_old_marker_calc)

            wx.CallAfter(self.secm.plot_panel.canvas.draw)

        self.target_icon.Refresh()


    def showItem(self, state):
        self._selected_for_plot = state

        if self._selected_for_plot == False:
            self.showitem_icon.SetBitmap(self.hide_png)
        else:
            self.showitem_icon.SetBitmap(self.show_png)

        self.secm.line.set_visible(self._selected_for_plot)
        self.secm.line.set_picker(self._selected_for_plot)      #Line can't be selected when it's hidden

        if self.sec_plot_panel.plotparams['secm_plot_calc'] != 'None' and self.secm.calc_has_data:
            self.secm.calc_line.set_visible(self._selected_for_plot)
            self.secm.calc_line.set_picker(self._selected_for_plot)      #Line can't be selected when it's hidden
        self.secm.is_visible = self._selected_for_plot

    def updateShowItem(self):
        if not self._selected_for_plot:
            self.showitem_icon.SetBitmap(self.hide_png)
        else:
            self.showitem_icon.SetBitmap(self.show_png)

        self.secm.line.set_picker(self._selected_for_plot)
        if self.sec_plot_panel.plotparams['secm_plot_calc'] != 'None' and self.secm.calc_has_data:
            self.secm.calc_line.set_picker(self._selected_for_plot)      #Line can't be selected when it's hidden

    def markAsModified(self, updateSelf = True, updateParent = True):
        filename = self.secm.getParameter('filename')
        self.item_name.SetLabel('* ' + str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()

        if self not in self.sec_panel.modified_items:
            self.sec_panel.modified_items.append(self)

    def unmarkAsModified(self, updateSelf = True, updateParent = True):
        filename = self.secm.getParameter('filename')
        self.item_name.SetLabel(str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()
        try:
            self.sec_panel.modified_items.remove(self)
        except:
            pass

    def updateFilenameLabel(self, updateSelf = True, updateParent = True, updateLegend = True):
        filename = self.secm.getParameter('filename')

        if self._legend_label == '':
            self.secm.line.set_label(filename)

        if updateLegend:
            self.sec_plot_panel.updateLegend(self.secm.axes)

        self.item_name.SetLabel(str(filename))

        if updateSelf:
            self.item_name.Refresh()
            self.topsizer.Layout()

        if updateParent:
            self.parent.Layout()
            self.parent.Refresh()

    def _initializeIcons(self):

        self.gray_png = self.sec_panel.gray_png
        self.star_png = self.sec_panel.star_png
        self.target_png = self.sec_panel.target_png
        self.target_on_png = self.sec_panel.target_on_png
        self.info_png = self.sec_panel.info_png
        self.show_png = self.sec_panel.show_all_png
        self.hide_png = self.sec_panel.hide_all_png

    def _updateColourIndicator(self):
        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.secm.line.get_color())
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self.colour_indicator.updateColour(color)

    def _onLinePropertyButton(self, event):

        try:
            legend_label = self.getLegendLabel()
            dialog = RAWCustomDialogs.SECMLinePropertyDialog(self, self.secm, legend_label)
            answer = dialog.ShowModal()
            new_legend_labels = dialog.getLegendLabel()
            self._updateColourIndicator()
            dialog.Destroy()

            if answer == wx.ID_OK:
                self._legend_label = new_legend_labels
                self._updateLegendLabel()

        except TypeError:
            return

    def _onTargetButton(self, event):
        self.enableLocatorLine()

    def _showPopupMenu(self):

        if self.sec_control_panel._is_online:
            self.sec_control_panel._goOffline()

        menu = wx.Menu()

        menu.Append(1, 'Remove' )
        menu.Append(2, 'Export data')
        menu.Append(6, 'Save all profiles as .dats')
        if self.secm.subtracted_sasm_list:
            menu.Append(11, 'Save all subtracted profiles as .dats')
        if self.secm.baseline_subtracted_sasm_list:
            menu.Append(12, 'Save all baseline corrected profiles as .dats')
        menu.Append(3, 'Save')
        menu.AppendSeparator()
        menu.Append(10, 'LC Series analysis')
        menu.Append(7, 'SVD')
        menu.Append(8, 'EFA')
        menu.Append(9, 'Similarity Test')
        menu.AppendSeparator()

        menu.Append(4, 'Show data')

        menu.AppendSeparator()
        menu.Append(5, 'Rename')


        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        self.PopupMenu(menu)

        menu.Destroy()

        if self.sec_control_panel.online_mode_button.IsChecked() and not self.sec_control_panel._is_online:
            self.sec_control_panel._goOnline()

    def _onPopupMenuChoice(self, evt):

        if evt.GetId() == 1:
            #Delete
            wx.CallAfter(self.sec_panel.removeSelectedItems)

        elif evt.GetId() == 2:
            self.sec_panel.saveData()

        elif evt.GetId() == 3:
            self.sec_panel._saveItems()

        elif evt.GetId() == 4:
            dlg = RAWCustomDialogs.SeriesDataDialog(self, self.secm)
            dlg.ShowModal()
            dlg.Destroy()

        elif evt.GetId() == 5:
            dlg = RAWCustomDialogs.FilenameChangeDialog(self, self.secm.getParameter('filename'))
            dlg.ShowModal()
            filename =  dlg.getFilename()
            dlg.Destroy()

            if filename:
                self.secm.setParameter('filename', filename)
                self.updateFilenameLabel()
                self.markAsModified()

        elif evt.GetId() ==6:
            self.sec_panel._saveProfiles('unsub')

        elif evt.GetId() == 7:
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSECMList = self.sec_panel.getSelectedItems()

            secm = selectedSECMList[0].getSECM()
            Mainframe.showSVDFrame(secm, selectedSECMList[0])

        elif evt.GetId() == 8:
            Mainframe = wx.FindWindowByName('MainFrame')
            selectedSECMList = self.sec_panel.getSelectedItems()

            secm = selectedSECMList[0].getSECM()
            Mainframe.showEFAFrame(secm, selectedSECMList[0])

        elif evt.GetId() == 9:
            #Similarity testing
            selected_items = self.sec_panel.getSelectedItems()

            if selected_items:
                selected_secms = [item.getSECM() for item in selected_items]
                selected_sasms = []
                ydata_type = self.sec_plot_panel.plotparams['y_axis_display']

                for secm in selected_secms:
                    if ydata_type == 'q_val':
                        intensity = secm.I_of_q
                    elif ydata_type == 'mean':
                        intensity = secm.mean_i
                    elif ydata_type == 'q_range':
                        intensity = secm.qrange_I
                    else:
                        intensity = secm.total_i

                    selected_sasms.append(SASM.SASM(intensity, secm.frame_list, np.sqrt(intensity), secm.getAllParameters()))
            else:
                selected_sasms = []

            self.main_frame.showSimilarityFrame(selected_sasms)

        elif evt.GetId() == 10:
            #Series analysis
            mainframe = wx.FindWindowByName('MainFrame')
            selectedSECMList = self.sec_panel.getSelectedItems()

            secm = selectedSECMList[0].getSECM()
            mainframe.showLCSeriesFrame(secm, selectedSECMList[0])

        elif evt.GetId() == 11:
            self.sec_panel._saveProfiles('sub')

        elif evt.GetId() == 12:
            self.sec_panel._saveProfiles('baseline')

    def _onKeyPress(self, evt):

        key = evt.GetKeyCode()

        if ((key == wx.WXK_DELETE) or (key == wx.WXK_BACK and evt.CmdDown())) and self._selected == True:
            self.removeSelf()
        elif key == 65 and evt.CmdDown(): #A
            self.sec_panel.selectAll()

    def _onRightMouseButton(self, evt):
        self.SetFocusIgnoringChildren()

        if not self._selected:
            self.toggleSelect()
            self.sec_panel.deselectAllExceptOne(self)

        if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
            wx.CallAfter(self._showPopupMenu)
        else:
            self._showPopupMenu()

    def _onLeftMouseButton(self, evt):
        ctrl_is_down = evt.CmdDown()
        shift_is_down = evt.ShiftDown()

        sec_panel = wx.FindWindowByName('SECPanel')

        if shift_is_down:
            try:

                first_marked_item_idx = sec_panel.all_manipulation_items.index(sec_panel.getSelectedItems()[0])
                last_marked_item = sec_panel.getSelectedItems()[-1]
                last_marked_item_idx = sec_panel.all_manipulation_items.index(last_marked_item)

                this_item_idx = sec_panel.all_manipulation_items.index(self)

                if last_marked_item_idx > this_item_idx:
                    adj = 0
                    idxs = [first_marked_item_idx, this_item_idx]
                else:
                    idxs = [last_marked_item_idx, this_item_idx]
                    adj = 1

                top_item = max(idxs)
                bottom_item = min(idxs)

                item_list = sec_panel.all_manipulation_items[bottom_item+adj:top_item+adj]
                for i in range(len(item_list)):
                    each = item_list[i]
                    if i != len(item_list)-1:
                        each.toggleSelect(update_info = False)
                    else:
                        each.toggleSelect()
            except IndexError:
                pass

        elif ctrl_is_down:
            self.toggleSelect()
        else:
            sec_panel.deselectAllExceptOne(self)
            self.toggleSelect()

        evt.Skip()

    def _onStarButton(self, event):

        if self._selected_as_bg == True:
            self.enableStar(False)
            self.sec_panel.clearDataItem()
        else:
            self.sec_panel.setItemAsData(self)

    def _updateLegendLabel(self, update_plot=True):

        labels = np.array(self._legend_label.values())

        if self._legend_label is None or len(labels) == 0 or np.all(labels == ''):
            self.secm.line.set_label(self.secm.getParameter('filename'))
            self.secm.calc_line.set_label(self.sec_plot_panel.plotparams['secm_plot_calc'])
            self.legend_label_text.SetLabel('')
        else:
            for key in self._legend_label:
                if str(self._legend_label[key]) != '':
                    if key == self.secm.line and str(self._legend_label[key]) != self.secm.getParameter('filename'):
                        key.set_label(str(self._legend_label[key]))
                        self.legend_label_text.SetLabel('[' + str(self._legend_label[self.secm.line]) + ']')
                    else:
                        key.set_label(str(self._legend_label[key]))
                else:
                    if key == self.secm.line:
                        self.secm.line.set_label(self.secm.getParameter('filename'))
                    elif key == self.secm.calc_line:
                        self.secm.calc_line.set_label(self.sec_plot_panel.plotparams['secm_plot_calc'])

        if update_plot:
            wx.CallAfter(self.secm.plot_panel.updateLegend, self.secm.axes)

    def _onShowItem(self, event):
        self._selected_for_plot = not self._selected_for_plot

        self.showItem(self._selected_for_plot)

        self.GetParent().Layout()
        self.GetParent().Refresh()

        self.sec_plot_panel.updateLegend(self.secm.axes, False)

        self.secm.plot_panel.fitAxis()


class SECControlPanel(wx.Panel):

    def __init__(self, parent):

        wx.Panel.__init__(self, parent, -1, name = 'SECControlPanel')

        self.parent = parent

        self.main_frame = wx.FindWindowByName('MainFrame')

        self.sec_panel = wx.FindWindowByName('SECPanel')
        self.sec_plot_panel = wx.FindWindowByName('SECPlotPanel')

        self._raw_settings = self.main_frame.raw_settings

        self._is_online = False
        self.tries = 1
        self.max_tries = 3

        self.filename = ''
        self.frame_list = []
        self.image_prefix = ""
        self.directory = ""
        self.initial_frame_number = ""
        self.final_frame_number = ""
        self.initial_selected_frame = ""
        self.final_selected_frame = ""
        self.secm = None

        self.controlData = (  ('Series:', parent.paramsInGui['Image Header'], self.image_prefix),
                              ('Initial Frame # :', parent.paramsInGui['Initial Frame #'], self.initial_frame_number),
                              ('Final Frame # :',parent.paramsInGui['Final Frame #'], self.final_frame_number),
                              ('Initial Selected Frame :', parent.paramsInGui['Initial Selected Frame'], self.initial_selected_frame),
                              ('Final Selected Frame :', parent.paramsInGui['Final Selected Frame'], self.final_selected_frame),
                              )


        topsizer = self.createControls()

        self.currentExpObj = None

        self.SetSizer(topsizer)

    def createControls(self):

        sizer = wx.BoxSizer(wx.VERTICAL)

        select_button = wx.Button(self, -1, 'Select')
        select_button.Bind(wx.EVT_BUTTON, self._onSelectButton)

        update_button = wx.Button(self, -1, 'Update')
        update_button.Bind(wx.EVT_BUTTON, self._onUpdateButton)

        self.online_mode_button = wx.CheckBox(self, -1, "AutoUpdate")
        self.online_mode_button.SetValue(self._is_online)
        self.online_mode_button.Bind(wx.EVT_CHECKBOX, self._onOnlineButton)


        for each in self.controlData:

            label = each[0]
            type = each[1][1]
            id = each[1][0]

            if type == 'imghdr':

                labelbox = wx.StaticText(self, -1, label)

                self.image_prefix_box=wx.TextCtrl(self, id=id,
                    value=self.image_prefix, style=wx.TE_READONLY)

                img_sizer = wx.BoxSizer(wx.HORIZONTAL)

                img_sizer.Add(labelbox, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
                    border = 2)
                img_sizer.Add(self.image_prefix_box, 1,
                    flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
                img_sizer.Add(select_button, flag=wx.ALIGN_CENTER_VERTICAL)

            elif type == 'iframenum':
                labelbox = wx.StaticText(self, -1, "Frames:")
                labelbox2=wx.StaticText(self,-1,"to")

                self.initial_frame_number_box = wx.TextCtrl(self, id=id,
                    value=self.initial_frame_number, size=(45,-1), style=wx.TE_READONLY)

                run_sizer = wx.BoxSizer(wx.HORIZONTAL)

                run_sizer.Add(labelbox, 0, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
                    border=2)
                run_sizer.Add(self.initial_frame_number_box, 1,
                    flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=2)
                run_sizer.Add(labelbox2, 0, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
                    border=2)

            elif type == 'fframenum':
                self.final_frame_number_box = wx.TextCtrl(self, id=id,
                    value=self.final_frame_number, size=(45,-1), style=wx.TE_READONLY)

                run_sizer.Add(self.final_frame_number_box, 1,
                    flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=5)

        run_sizer.Add(update_button, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=2)
        run_sizer.Add(self.online_mode_button, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=2)


        load_box = wx.StaticBox(self, -1, 'Load/Online Mode')
        load_sizer = wx.StaticBoxSizer(load_box, wx.VERTICAL)
        load_sizer.Add(img_sizer, 0, flag = wx.EXPAND|wx.ALL, border=2)
        load_sizer.Add(run_sizer, 0, flag = wx.EXPAND|wx.ALL, border=2)

        sizer.Add(load_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)


        selected_sizer = wx.BoxSizer(wx.HORIZONTAL)

        for each in self.controlData:

            label = each[0]
            ctrl_type = each[1][1]
            ctrl_id = each[1][0]

            if ctrl_type == 'isframenum':

                labelbox = wx.StaticText(self, -1, "Frames:")
                labelbox2 = wx.StaticText(self, -1, "to")
                self.initial_selected_box = wx.TextCtrl(self, ctrl_id, value = self.initial_selected_frame, size = (50,-1))

                selected_sizer.Add(labelbox, border=2,
                    flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
                selected_sizer.Add(self.initial_selected_box, border=2,
                    flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
                selected_sizer.Add(labelbox2, border=2,
                    flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)

            elif ctrl_type == 'fsframenum':
                self.final_selected_box = wx.TextCtrl(self, ctrl_id, value = self.final_selected_frame, size = (50,-1))
                selected_sizer.Add(self.final_selected_box, border=5,
                    flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)

        ####
        frames_plot_button = wx.Button(self, -1, 'Plot')
        frames_plot_button.Bind(wx.EVT_BUTTON, self._onFramesToMainPlot)
        average_plot_button = wx.Button(self, -1, 'Average')
        average_plot_button.Bind(wx.EVT_BUTTON, self._onAverageToMainPlot)

        selected_sizer.Add(frames_plot_button, 0, border=5,
            flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
        selected_sizer.Add(average_plot_button, 0, flag =wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)

        selected_sizer.AddStretchSpacer(1)

        send_box = wx.StaticBox(self, -1, 'Data to main plot')
        send_sizer = wx.StaticBoxSizer(send_box, wx.VERTICAL)

        send_sizer.Add(selected_sizer, flag=wx.EXPAND|wx.ALL, border=2)

        sizer.Add(send_sizer, flag=wx.EXPAND|wx.BOTTOM, border=5)

        return sizer

    def updateSECItem(self,secm):
        self.secm = secm

    def _onOnlineButton(self, evt):
        go_online = evt.IsChecked()

        if go_online:
            self._goOnline()
        else:
            self._goOffline()

    def _goOnline(self):
        self._is_online = True
        self.main_frame.OnlineSECControl.goOnline()

    def _goOffline(self):
        self._is_online = False
        self.main_frame.OnlineSECControl.goOffline()

    def _onSelectButton(self, evt):

        hdr_format = self._raw_settings.get('ImageHdrFormat')

        if hdr_format == 'G1, CHESS' or hdr_format == 'G1 WAXS, CHESS' or hdr_format == 'BioCAT, APS':
            fname = self.parent._CreateFileDialog(wx.FD_OPEN)

            if fname == None:
                return

            try:
                sasm, img = SASFileIO.loadFile(fname, self.parent._raw_settings)
            except (SASExceptions.UnrecognizedDataFormat, SASExceptions.WrongImageFormat), msg:
                img_fmt = self._raw_settings.get('ImageFormat')
                ascii = ' or any of the supported ASCII formats'
                wx.CallAfter(wx.MessageBox, 'The selected file: ' + fname + '\ncould not be recognized as a '   + str(img_fmt) +
                                 ' image format' + ascii + '.\n\nYou can change the image format under Advanced Options in the Options menu.' ,
                                  'Error loading file', style = wx.ICON_ERROR | wx.OK)
                fname = None
            except SASExceptions.HeaderLoadError, msg:
                wx.CallAfter(wx.MessageBox, str(msg), "Can't find Header file for selected image", style = wx.ICON_ERROR | wx.OK)
                fname = None
            except SASExceptions.MaskSizeError, msg:
                wx.CallAfter(wx.MessageBox, str(msg), 'Saved mask does not fit selected image', style = wx.ICON_ERROR)
                fname = None
            except SASExceptions.HeaderMaskLoadError, msg:
                wx.CallAfter(wx.MessageBox, str(msg), 'Mask information was not found in header', style = wx.ICON_ERROR)
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return
            except SASExceptions.AbsScaleNormFailed:
                msg = ('Failed to apply absolute scale. The most '
                        'likely cause is a mismatch between the q vector of the '
                        'loaded file and the selected sample background file.')
                wx.CallAfter(wx.MessageBox, msg, 'Absolute scale failed', style = wx.ICON_ERROR | wx.OK)
                wx.CallAfter(self.main_frame.closeBusyDialog)
                return

            if fname != None:
                self.directory, self.filename = os.path.split(fname)
                self._fillBoxes()
                self._onLoad()
        else:
             wx.CallAfter(wx.MessageBox, 'The "%s" header format is not supported for automated SEC-SAXS file loading. You can use the "Plot SEC" button in the file window to plot any SEC-SAXS data. Please contact the RAW developers if you want to add automated loading support for a particular header format.' %(hdr_format) ,
                                      'Error loading file', style = wx.ICON_ERROR | wx.OK)

    def _onLoad(self):
        if self._is_online:
            self._goOffline()

        file_list, frame_list = self._makeFileList()

        if len(file_list) > 0:

            mainworker_cmd_queue.put(['sec_plot', [file_list, frame_list, True]])

        else:
            wx.MessageBox("Can't find files to load", style=wx.ICON_ERROR | wx.OK)

        if self.online_mode_button.IsChecked() and not self._is_online:
            self._goOnline()

    def _onUpdateButton(self,evt):
        self.onUpdate()

    def onUpdate(self):

        if self.secm != None:

            if self._is_online:
                self._goOffline()

            old_frame_list = self._getFrameList(self.secm._file_list)
            self._fillBoxes()

            dif_frame_list = list(set(self.frame_list)-set(old_frame_list))

            dif_frame_list.sort(key=lambda frame: int(frame))

            if len(dif_frame_list)>0:

              file_list, modified_frame_list = self._makeFileList(dif_frame_list)

            else:
                file_list=[]

            if len(file_list) > 0:
                mainworker_cmd_queue.put(['update_secm', [file_list, modified_frame_list, self.secm]])

            else:
                self.updateSucceeded()

    def updateFailed(self, name, error, msg):
        self.tries = self.tries + 1
        if self.tries <= self.max_tries:
            time.sleep(1)
            self.onUpdate()
        else:
            self._goOffline()
            self.online_mode_button.SetValue(False)
            if error == 'file':
                wx.CallAfter(self._showDataFormatError, os.path.split(name)[1])
            elif error == 'header':
                wx.CallAfter(wx.MessageBox, str(msg)+ ' Automatic series updating turned off.', 'Error Loading Headerfile', style = wx.ICON_ERROR | wx.OK)
            elif error == 'mask':
                 wx.CallAfter(wx.MessageBox, str(msg)+ ' Automatic series updating turned off.', 'Saved mask does not fit loaded image', style = wx.ICON_ERROR)
            elif error == 'mask_header':
                wx.CallAfter(wx.MessageBox, str(msg)+ ' Automatic series updating turned off.', 'Mask information was not found in header', style = wx.ICON_ERROR)
            elif error == 'abs_scale':
                wx.CallAfter(wx.MessageBox, str(msg)+ ' Automatic series updating turned off.', 'Absolute scale failed', style = wx.ICON_ERROR)

    def updateSucceeded(self):
        if self.online_mode_button.IsChecked() and not self._is_online:
            self._goOnline()

        self.tries = 1

    def _showDataFormatError(self, filename, include_ascii = True, include_sec = False):
        img_fmt = self._raw_settings.get('ImageFormat')

        if include_ascii:
            ascii = ' or any of the supported ASCII formats'
        else:
            ascii = ''

        if include_sec:
            sec = ' or the RAW series format'
        else:
            sec = ''

        wx.CallAfter(wx.MessageBox, 'The selected file: ' + filename + '\ncould not be recognized as a '   + str(img_fmt) +
                         ' image format' + ascii + sec + '.\n\nYou can change the image format under Advanced Options in the Options menu.\n'+
                         'Automatic series updating turned off.' ,
                          'Error loading file', style = wx.ICON_ERROR | wx.OK)

    def _onFramesToMainPlot(self,evt):

        if self._is_online:
            self._goOffline()

        self._updateControlValues()

        selected_item = self.sec_panel.getDataItem()
        secm = None

        if len(self.initial_selected_frame)>0 and len(self.final_selected_frame)>0 and len(self.sec_panel.all_manipulation_items) > 0:

            if len(self.sec_panel.all_manipulation_items) == 1:
                secm = self.sec_panel.all_manipulation_items[0].secm

            elif len(self.sec_panel.all_manipulation_items)>1:

                if selected_item != None:
                    if not selected_item.getSelectedForPlot():
                        msg = "Warning: The selected series curve is not shown on the plot. Send frames to main plot anyways?\nNote: You can select a different series curve by starring it."
                        dlg = wx.MessageDialog(self.main_frame, msg, "Verify Selection", style = wx.ICON_QUESTION | wx.YES_NO)
                        proceed = dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        proceed = wx.ID_YES

                    if proceed == wx.ID_YES:
                        secm = selected_item.secm

                else:
                    msg = "To send data to the main plot, select a series curve by starring it."
                    wx.CallAfter(wx.MessageBox, msg, "No series curve selected", style = wx.ICON_ERROR | wx.OK)

        elif len(self.sec_panel.all_manipulation_items) > 0:
            msg = "To send data to the main plot, enter a valid frame range (missing start or end frame)."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)

        if secm is not None:
            if secm.axes.xaxis.get_label_text() == 'Time (s)':
                msg = "Warning: Plot is displaying time. Make sure frame #s, not time, are selected to send to plot. Proceed?"
                dlg = wx.MessageDialog(self.main_frame, msg, "Verify Frame Range", style = wx.ICON_QUESTION | wx.YES_NO)
                proceed = dlg.ShowModal()
                dlg.Destroy()
            else:
                proceed = wx.ID_YES

            if proceed == wx.ID_YES:
                int_type = secm.plot_panel.plotparams['plot_intensity']
                sasm_list = secm.getSASMList(self.initial_selected_frame,
                    self.final_selected_frame, int_type)
            else:
                sasm_list = None

        if sasm_list is not None and sasm_list:
            sasm_list = map(copy.deepcopy, sasm_list)

            mainworker_cmd_queue.put(['to_plot_SEC', sasm_list])

        if self.online_mode_button.IsChecked() and not self._is_online:
            self._goOnline()

    def _onAverageToMainPlot(self,evt):

        if self._is_online:
            self._goOffline()

        self._updateControlValues()

        selected_item = self.sec_panel.getDataItem()
        secm = None

        if len(self.initial_selected_frame)>0 and len(self.final_selected_frame)>0 and len(self.sec_panel.all_manipulation_items) > 0:

            if len(self.sec_panel.all_manipulation_items) == 1:
                secm = self.sec_panel.all_manipulation_items[0].secm

            elif len(self.sec_panel.all_manipulation_items)>1:

                if selected_item != None:
                    if not selected_item.getSelectedForPlot():
                        msg = "Warning: The selected series curve is not shown on the plot. Send frames to main plot anyways?\nNote: You can select a different series curve by starring it."
                        dlg = wx.MessageDialog(self.main_frame, msg, "Verify Selection", style = wx.ICON_QUESTION | wx.YES_NO)
                        proceed = dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        proceed = wx.ID_YES

                    if proceed == wx.ID_YES:
                        secm = selected_item.secm

                else:
                    msg = "To send data to the main plot, select a series curve by starring it."
                    wx.CallAfter(wx.MessageBox, msg, "No series curve selected", style = wx.ICON_ERROR | wx.OK)

        elif len(self.sec_panel.all_manipulation_items) > 0:
            msg = "To send data to the main plot, enter a valid frame range (missing start or end frame)."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)

        if secm is not None:
            if secm.axes.xaxis.get_label_text() == 'Time (s)':
                msg = "Warning: Plot is displaying time. Make sure frame #s, not time, are selected to send to plot. Proceed?"
                dlg = wx.MessageDialog(self.main_frame, msg, "Verify Frame Range", style = wx.ICON_QUESTION | wx.YES_NO)
                proceed = dlg.ShowModal()
                dlg.Destroy()
            else:
                proceed = wx.ID_YES

            if proceed == wx.ID_YES:
                int_type = secm.plot_panel.plotparams['plot_intensity']
                sasm_list = secm.getSASMList(self.initial_selected_frame,
                    self.final_selected_frame, int_type)
            else:
                sasm_list = None

        if sasm_list is not None and sasm_list:
            sasm_list = map(copy.deepcopy, sasm_list)

            mainworker_cmd_queue.put(['secm_average_sasms', sasm_list])

        if self.online_mode_button.IsChecked() and not self._is_online:
            self._goOnline()


    def _findWindowId(self,type):
        my_id=-1

        for item in self.controlData:
            item_type = item[1][1]
            item_id = item[1][0]

            if type == item_type:
                my_id = item_id

        return my_id


    def _updateControlValues(self):

        for parameter in self.controlData:
            ptype = parameter[1][1]
            pid = parameter[1][0]

            if ptype != 'framelist':
                data = wx.FindWindowById(pid, self)

                if ptype == 'imghdr':
                    self.image_prefix = data.GetValue()

                elif ptype == 'iframenum':
                    self.initial_frame_number = data.GetValue()

                elif ptype == 'fframenum':
                    self.final_frame_number = data.GetValue()

                elif ptype == 'isframenum':
                    self.initial_selected_frame = data.GetValue()

                elif ptype == 'fsframenum':
                    self.final_selected_frame = data.GetValue()


    def _makeFileList(self,modified_frame_list=[]):

        self._updateControlValues()

        file_list = []
        bad_file_list = []

        if len(modified_frame_list) == 0 :
            modified_frame_list = copy.copy(self.frame_list)

        hdr_format = self._raw_settings.get('ImageHdrFormat')

        if hdr_format == 'G1, CHESS' or hdr_format == 'G1 WAXS, CHESS':
            if self.image_prefix != '' or self.filename != '':
                for frame in modified_frame_list:
                    name = os.path.join(self.directory, '{}_{}'.format(self.image_prefix, frame))
                    if os.path.isfile(name+'.dat'):
                        file_list.append(name+'.dat')
                    elif os.path.isfile(name+'.tiff'):
                        file_list.append(name+'.tiff')
                    else:
                        files = glob.glob(name+'.*')
                        if files and not files[0].endswith('.tmp'):
                            file_list.append(files[0])
                        else:
                            bad_file_list.append(frame)

        elif hdr_format == 'BioCAT, APS':
            if self.image_prefix != '' or self.filename != '':
                for frame in modified_frame_list:
                    name = os.path.join(self.directory, '%s_%s' %(self.image_prefix, frame))

                    if os.path.isfile(name+'.dat'):
                        file_list.append(name+'.dat')
                    elif os.path.isfile(name+'.tiff'):
                        file_list.append(name+'.tiff')
                    elif os.path.isfile(name+'.tif'):
                        file_list.append(name+'.tif')
                    else:
                        files = glob.glob(name+'.*')
                        if files and not files[0].endswith('.tmp'):
                            file_list.append(files[0])
                        else:
                            bad_file_list.append(frame)

        if bad_file_list:
            for frame in bad_file_list:
                modified_frame_list.pop(modified_frame_list.index(frame))

        return file_list, modified_frame_list


    def _fillBoxes(self):

        hdr_format = self._raw_settings.get('ImageHdrFormat')

        if hdr_format == 'G1, CHESS' or hdr_format == 'G1 WAXS, CHESS':

            if self.filename != '':

                count_filename, run_number, frame_number = SASFileIO.parseCHESSG1Filename(os.path.join(self.directory, self.filename))

                filelist=glob.glob(count_filename + '_' + run_number + '_*')

                self.frame_list = self._getFrameList(filelist)

                self.image_prefix = '{}_{}'.format(os.path.basename(count_filename), run_number)

                self.image_prefix_box.SetValue(self.image_prefix)
                self.initial_frame_number = self.frame_list[0]
                self.initial_frame_number_box.SetValue(self.initial_frame_number)
                self.final_selected_frame = self.frame_list[-1]
                self.final_frame_number_box.SetValue(self.final_selected_frame)

                self._updateControlValues

        elif hdr_format == 'BioCAT, APS':

            count_filename, frame_number = SASFileIO.parseBiocatFilename(os.path.join(self.directory, self.filename))

            filelist=glob.glob(count_filename + '_*')

            self.frame_list = self._getFrameList(filelist)

            junk, self.image_prefix = os.path.split(count_filename)
            self.image_prefix_box.SetValue(self.image_prefix)

            self.initial_frame_number = self.frame_list[0]
            self.initial_frame_number_box.SetValue(self.initial_frame_number)

            self.final_selected_frame = self.frame_list[-1]
            self.final_frame_number_box.SetValue(self.final_selected_frame)

            self._updateControlValues

    def _getFrameList(self, filelist):

        framelist=[]

        hdr_format = self._raw_settings.get('ImageHdrFormat')

        if hdr_format == 'G1, CHESS' or hdr_format == 'G1 WAXS, CHESS':

            for f in filelist:
                frame=SASFileIO.parseCHESSG1Filename(f)[2]
                try:
                    int(frame)
                    framelist.append(frame)
                except ValueError:
                    pass

        elif hdr_format == 'BioCAT, APS':
            for f in filelist:
                frame=SASFileIO.parseBiocatFilename(f)[1]
                try:
                    int(frame)
                    framelist.append(frame)
                except ValueError:
                    pass

        framelist = list(set(framelist))
        framelist.sort(key=lambda frame: int(frame))

        return framelist


    def clearAll(self):
        for each in self.controlData:
            each_type = each[1][1]
            each_id = each[1][0]

            if each_type != 'framelist' and each_type != 'wsize':
                infobox = wx.FindWindowById(each_id, self)
                infobox.SetValue('')
            elif each_type == 'wsize':
                infobox = wx.FindWindowById(each_id, self)
                infobox.SetValue('5')

        self.secm=None

        self.filename = ''
        self.frame_list = []
        self.directory = ""

        self._updateControlValues


#--- ** Masking Panel **

class MaskingPanel(wx.Panel):

    def __init__(self, parent,id):

        wx.Panel.__init__(self, parent, id, name = 'MaskingPanel')

        self.mask_choices = {'Beamstop mask' : 'BeamStopMask',
                             'Readout-Dark mask' : 'ReadOutNoiseMask',
                             'ROI Counter mask' : 'TransparentBSMask',
                             'SAXSLAB BS mask' : 'SaxslabBSMask'}

        self.CIRCLE_ID, self.RECTANGLE_ID, self.POLYGON_ID = self.NewControlId(), self.NewControlId(), self.NewControlId()
        self.all_button_ids = [self.CIRCLE_ID, self.RECTANGLE_ID, self.POLYGON_ID]

        self._main_frame = wx.FindWindowByName('MainFrame')
        self.image_panel = wx.FindWindowByName('ImagePanel')

        self._initBitmaps()

        self._create_layout()

        self._center = [0,0]
        self.show_center = False

        self.mask_modified = False

    def setTool(self, tool):
        self.image_panel.setTool(tool)

    def _create_layout(self):
        manual_box = wx.StaticBox(self, -1, 'Mask Drawing')
        self.manual_boxsizer = wx.StaticBoxSizer(manual_box)
        self.manual_boxsizer.Add(self._createDrawCtrls(), 1)

        auto_box = wx.StaticBox(self, -1, 'Mask Creation')
        auto_boxsizer = wx.StaticBoxSizer(auto_box)
        auto_boxsizer.Add(self._createMaskSelector(), 0)

        button_sizer = self._createButtonSizer()

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.manual_boxsizer, flag=wx.EXPAND)
        self.sizer.Add(auto_boxsizer, flag=wx.EXPAND)
        self.sizer.Add(button_sizer, border=3, flag=wx.ALL|wx.ALIGN_CENTER)

        self.SetSizer(self.sizer)

    def _createDrawCtrls(self):

        self.circle_button = wxbutton.GenBitmapToggleButton(self, self.CIRCLE_ID, self.circle_bmp, size = (60,60))
        self.rectangle_button = wxbutton.GenBitmapToggleButton(self, self.RECTANGLE_ID, self.rectangle_bmp, size = (60,60))
        self.polygon_button = wxbutton.GenBitmapToggleButton(self, self.POLYGON_ID, self.polygon_bmp, size = (60,60))

        self.circle_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        self.rectangle_button.Bind(wx.EVT_BUTTON, self._onDrawButton)
        self.polygon_button.Bind(wx.EVT_BUTTON, self._onDrawButton)

        draw_sizer = wx.FlexGridSizer(rows=2, cols=3, vgap=2, hgap=5)
        draw_sizer.Add(self.circle_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        draw_sizer.Add(self.rectangle_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        draw_sizer.Add(self.polygon_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        draw_sizer.Add(wx.StaticText(self, label='Circle'), flag=wx.ALIGN_CENTER_HORIZONTAL)
        draw_sizer.Add(wx.StaticText(self, label='Rectangle'), flag=wx.ALIGN_CENTER_HORIZONTAL)
        draw_sizer.Add(wx.StaticText(self, label='Polygon'), flag=wx.ALIGN_CENTER_HORIZONTAL)

        self.circ_radius = wx.TextCtrl(self, size=(50,-1))
        self.circ_x = wx.TextCtrl(self, size=(50,-1))
        self.circ_y = wx.TextCtrl(self, size=(50,-1))
        circ_btn2 = wx.Button(self, label='Create')
        circ_btn2.Bind(wx.EVT_BUTTON, self._on_create_circle)

        circ_sub_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        circ_sub_sizer1.Add(wx.StaticText(self, label='Circle'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        circ_sub_sizer1.Add(circ_btn2, border=15,
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        circ_sub_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        circ_sub_sizer2.Add(wx.StaticText(self, label='Radius:'), border=15,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        circ_sub_sizer2.Add(self.circ_radius, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        circ_sub_sizer2.Add(wx.StaticText(self, label='X cen.:'), border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        circ_sub_sizer2.Add(self.circ_x, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        circ_sub_sizer2.Add(wx.StaticText(self, label='Y cen.:'), border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        circ_sub_sizer2.Add(self.circ_y, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)

        circ_sizer = wx.BoxSizer(wx.VERTICAL)
        circ_sizer.Add(circ_sub_sizer1)
        circ_sizer.Add(circ_sub_sizer2, border=3, flag=wx.TOP)

        self.rect_width = wx.TextCtrl(self, size=(50,-1))
        self.rect_height = wx.TextCtrl(self, size=(50,-1))
        self.rect_x = wx.TextCtrl(self, size=(50,-1))
        self.rect_y = wx.TextCtrl(self, size=(50,-1))
        rect_btn2 = wx.Button(self, label='Create')
        rect_btn2.Bind(wx.EVT_BUTTON, self._on_create_rectangle)

        rect_sub_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        rect_sub_sizer1.Add(wx.StaticText(self, label='Rectangle'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        rect_sub_sizer1.Add(rect_btn2, border=15,
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        rect_sub_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        rect_sub_sizer2.Add(wx.StaticText(self, label='X1:'), border=15,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(self.rect_x, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(wx.StaticText(self, label='Y1:'), border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(self.rect_y, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(wx.StaticText(self, label='W.:'), border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(self.rect_width, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(wx.StaticText(self, label='H.:'), border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)
        rect_sub_sizer2.Add(self.rect_height, border=3,
            flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT)

        rect_sizer = wx.BoxSizer(wx.VERTICAL)
        rect_sizer.Add(rect_sub_sizer1)
        rect_sizer.Add(rect_sub_sizer2, border=3, flag=wx.TOP)

        man_box = wx.StaticBox(self, label='Manual')
        man_sizer = wx.StaticBoxSizer(man_box, wx.VERTICAL)
        man_sizer.Add(draw_sizer, border=3, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM)
        man_sizer.Add(wx.StaticLine(self, style=wx.LI_HORIZONTAL), border=10,
            flag=wx.LEFT|wx.RIGHT|wx.EXPAND)
        man_sizer.Add(circ_sizer, border=3, flag=wx.TOP)
        man_sizer.Add(rect_sizer, border=3, flag=wx.TOP)


        self.auto_type = wx.Choice(self, choices=['>', '<','=', '>=', '<='])
        self.auto_type.SetSelection(2)
        self.auto_val = wx.TextCtrl(self, value='-2', size=(65,-1))
        auto_pixel_btn = wx.Button(self, label='Create')
        auto_pixel_btn.Bind(wx.EVT_BUTTON, self._on_auto_pixel_mask)

        pixel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pixel_sizer.Add(wx.StaticText(self, label='Mask all pixels'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        pixel_sizer.Add(self.auto_type, border=3, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        pixel_sizer.Add(self.auto_val, border=3, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        pixel_sizer.Add(auto_pixel_btn, border=15, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        self.auto_det_type = wx.Choice(self, choices=self._getDetList(), size=(150,-1))
        self.auto_det_type.SetStringSelection('pilatus1m')
        auto_det_btn = wx.Button(self, label='Create')
        auto_det_btn.Bind(wx.EVT_BUTTON, self._on_auto_det_mask)

        det_sizer = wx.BoxSizer(wx.HORIZONTAL)
        det_sizer.Add(wx.StaticText(self, label='Mask detector:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        det_sizer.Add(self.auto_det_type, proportion=1, border=3,
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        det_sizer.Add(auto_det_btn, border = 15, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        auto_box = wx.StaticBox(self, label='Automatic')
        auto_sizer = wx.StaticBoxSizer(auto_box, wx.VERTICAL)
        auto_sizer.Add(pixel_sizer)
        auto_sizer.Add(det_sizer, border=3, flag=wx.TOP|wx.EXPAND)


        options = self._createMaskOptions()
        options_sizer = wx.StaticBoxSizer(wx.StaticBox(self, label='Options'))
        options_sizer.Add(options)

        save_button= wx.Button(self, -1, "Save to file")
        save_button.Bind(wx.EVT_BUTTON, self._onSaveMaskToFile)
        load_button= wx.Button(self, -1, "Load from file")
        load_button.Bind(wx.EVT_BUTTON, self._onLoadMaskFromFile)
        clear_button= wx.Button(self, -1, "Clear")
        clear_button.Bind(wx.EVT_BUTTON, self._onClearDrawnMasks)

        button_sizer = wx.BoxSizer()
        button_sizer.Add(save_button, 0, wx.RIGHT, 3)
        button_sizer.Add(load_button, 0, wx.RIGHT, 3)
        button_sizer.Add(clear_button, 0)


        final_sizer = wx.BoxSizer(wx.VERTICAL)

        final_sizer.Add(man_sizer, flag=wx.EXPAND)
        final_sizer.Add(auto_sizer, border=3, flag=wx.TOP|wx.EXPAND)
        final_sizer.Add(options_sizer, border=3, flag=wx.TOP|wx.EXPAND)
        final_sizer.Add(button_sizer, border=3, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.TOP)

        return final_sizer

    def _createMaskOptions(self):

        sizer = wx.BoxSizer(wx.VERTICAL)
        center_chkbox = wx.CheckBox(self, -1, 'Show Beam Center')
        center_chkbox.Bind(wx.EVT_CHECKBOX, self._onShowCenterChkbox)
        sizer.Add(center_chkbox)

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
        self.selector_choice.SetStringSelection('Beamstop mask')

        set_button = wx.Button(self, -1, 'Set', size = (60,-1))
        set_button.Bind(wx.EVT_BUTTON, self._onSetButton)

        clear_button = wx.Button(self, -1, 'Remove', size = (65,-1))
        clear_button.Bind(wx.EVT_BUTTON, self._onClearButton)

        show_button = wx.Button(self, -1, 'Show', size = (60,-1))
        show_button.Bind(wx.EVT_BUTTON, self._onShowButton)

        sizer.Add(self.selector_choice, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(clear_button, 0)
        sizer.Add(set_button,0)
        sizer.Add(show_button,0)

        return sizer

    def _calcSaxslabBSMask(self):
        sasm = self.image_panel.current_sasm

        img_hdr = sasm.getParameter('imageHeader')
        img = self.image_panel.img

        if img is not None and img_hdr != None and 'bsmask_configuration' in img_hdr:
            mask_params = SASImage.createMaskFromHdr(img, img_hdr, flipped = self._main_frame.raw_settings.get('DetectorFlipped90'))
        else:
            wx.MessageBox('The image does not have a SAXSLAB Beamstop Mask in the header.', 'No mask available.', style = wx.ICON_EXCLAMATION)

        #mask_params contains the mask and the individual maskshapes

        return [None, mask_params]

    def _on_create_circle(self, event):
        selected_mask = self.selector_choice.GetStringSelection()
        mask_key = self.mask_choices[selected_mask]
        if mask_key == 'TransparentBSMask':
            negative = True
        else:
            negative = False

        try:
            r = float(self.circ_radius.GetValue())
            x = float(self.circ_x.GetValue())
            y = float(self.circ_y.GetValue())
        except Exception:
            msg = ('Cannot create a circle mask. The radius and center x and '
                'y positions must be numbers.')
            wx.MessageBox(msg, 'Failed to create mask', style=wx.ICON_EXCLAMATION)
            return

        self.image_panel.create_circ_mask((x, x+r), (y, y), negative)
        return

    def _on_create_rectangle(self, event):
        selected_mask = self.selector_choice.GetStringSelection()
        mask_key = self.mask_choices[selected_mask]
        if mask_key == 'TransparentBSMask':
            negative = True
        else:
            negative = False

        try:
            x = float(self.rect_x.GetValue())
            y = float(self.rect_y.GetValue())
            w = float(self.rect_width.GetValue())
            h = float(self.rect_height.GetValue())
        except Exception:
            msg = ('Cannot create a rectangle mask. The corner x and y '
                'positions and the width and height must be numbers.')
            wx.MessageBox(msg, 'Failed to create mask', style=wx.ICON_EXCLAMATION)
            return

        self.image_panel.create_rect_mask((x, x+w), (y, y+h), negative)
        return

    def _on_auto_pixel_mask(self, event):
        img = self.image_panel.img

        conditional = self.auto_type.GetStringSelection()
        comp_val = float(self.auto_val.GetValue())

        if conditional == '<':
            comp = img < comp_val
        elif conditional == '>':
           comp = img > comp_val
        elif conditional == '=':
            comp = img == comp_val
        elif conditional == '>=':
            comp = img >= comp_val
        elif conditional == '<=':
            comp = img <= comp_val

        self._maskConditional(comp)

    def _on_auto_det_mask(self,event):
        det_sel = self.auto_det_type.GetStringSelection()
        det = pyFAI.detector_factory(det_sel)
        comp = det.get_mask()

        self._maskConditional(comp)

    def _maskConditional(self, comp):
        selected_mask = self.selector_choice.GetStringSelection()
        mask_key = self.mask_choices[selected_mask]
        if mask_key == 'TransparentBSMask':
            negative = True
        else:
            negative = False

        idx_x = np.unique(SASCalc.contiguous_regions(comp[0,:]))
        idx_y = np.unique(SASCalc.contiguous_regions(comp[:,0]))

        x_regions = []
        y_regions = []

        for i in range(len(idx_x)):
            if i < len(idx_x)-1:
                idx1 = idx_x[i]
                idx2 = idx_x[i+1]

                if np.all(comp[:,idx1:idx2]):
                    x_regions.append((idx1, idx2))

        for i in range(len(idx_y)):
            if i < len(idx_y)-1:
                idx1 = idx_y[i]
                idx2 = idx_y[i+1]

                if np.all(comp[idx1:idx2,:]):
                    y_regions.append((idx1, idx2))

        y_extent = (0, comp.shape[0])
        x_extent = (0, comp.shape[1])

        for pts in x_regions:
            comp[:,pts[0]:pts[1]] = False
            self.image_panel.create_rect_mask(pts, y_extent, negative, False)

        for pts in y_regions:
            comp[pts[0]:pts[1],:] = False
            self.image_panel.create_rect_mask(x_extent, pts, negative, False)

        points = np.transpose(np.nonzero(comp))

        for pt in points:
            x = pt[1]
            y = pt[0]
            self.image_panel.create_rect_mask((x, x+1), (y, y+1), negative, False)

        self.image_panel.plotStoredMasks()

    def _getDetList(self):

        extra_det_list = ['detector']

        final_dets = pyFAI.detectors.ALL_DETECTORS

        for key in extra_det_list:
            if final_dets.has_key(key):
                final_dets.pop(key)

        det_list = sorted(final_dets.keys(), key = str.lower)

        return det_list

    def _onShowButton(self, event):
        selected_mask = self.selector_choice.GetStringSelection()
        mask_key = self.mask_choices[selected_mask]

        plot_parameters = self.image_panel.getPlotParameters()
        mask_dict = self._main_frame.raw_settings.get('Masks')

        if mask_key == 'SaxslabBSMask':
            mask_params = self._calcSaxslabBSMask()
        else:
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

        if selected_mask != 'SAXSLAB BS mask':
            mask_key = self.mask_choices[selected_mask]

            mask_dict = self._main_frame.raw_settings.get('Masks')

            if mask_dict[mask_key][1] is not None:
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

            if masks == [] or self.image_panel.img is None:
                wx.MessageBox('No masks has been drawn. Draw a mask before setting it as the current mask.', 'Setting mask failed')
                return

            img_dim = self.image_panel.img.shape

            if len(masks) != 0:
                queue = self._main_frame.getWorkerThreadQueue()
                queue.put(['create_mask', [mask_key, masks_copy, img_dim]])

        else:
            dial = wx.MessageDialog(None, 'SAXSLAB beamstop masks are set in the image header, and cannot be modified. If you wish to disable the use of this mask, you can do so by unchecking the "Use header for mask creation" option in the General Settings in the Advanced Options panel.\n\nIf you wish to mask additional portions of the image, please set a normal Beamstop Mask.', 'Cannot remove mask',
            wx.OK | wx.ICON_WARNING)
            dial.ShowModal()

        self.mask_modified = False

    def _onClearButton(self, event):

        selected_mask = self.selector_choice.GetStringSelection()

        if selected_mask != 'SAXSLAB BS mask':

            dial = wx.MessageDialog(None, 'Are you sure you want to delete this mask?', 'Are you sure?',
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            answer = dial.ShowModal()

            if answer == wx.ID_NO:
                return

            mask_key = self.mask_choices[selected_mask]
            mask_dict = self._main_frame.raw_settings.get('Masks')
            mask_dict[mask_key] = [None, None]
            self.image_panel.clearAllMasks()

        else:
            dial = wx.MessageDialog(None, 'SAXSLAB beamstop masks are set in the image header, and cannot be modified. If you wish to disable the use of this mask, you can do so by unchecking the "Use header for mask creation" option in the General Settings in the Advanced Options panel.', 'Cannot remove mask',
            wx.OK | wx.ICON_WARNING)
            dial.ShowModal()

        self.mask_modified = True

    def _onClearDrawnMasks(self, event):
        wx.CallAfter(self.image_panel.clearAllMasks)

    def _onLoadMaskFromFile(self, event):
        file = self._createFileDialog(wx.FD_OPEN)

        if file:
            queue = self._main_frame.getWorkerThreadQueue()
            queue.put(['load_mask', [file]])

    def _onSaveMaskToFile(self, event):

        file = self._createFileDialog(wx.FD_SAVE)

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
                wx.FindWindowById(each, self).SetToggle(False)

    def _createButtonSizer(self):
        sizer = wx.BoxSizer()
        ok_button = wx.Button(self, wx.ID_OK, 'OK')
        sizer.Add(ok_button)
        ok_button.Bind(wx.EVT_BUTTON, self._onOkButton)

        return sizer

    def _onOkButton(self, event):

        if self.mask_modified:
            msg = ('Warning: There are unsaved changes to your mask. If you proceed, '
                'these will be discarded. To save changes to your mask, use the Set '
                'button in the Mask Creation section. Are you sure you want to '
                'exit the masking panel?')
            dlg = wx.MessageDialog(self, msg, 'Unsaved Mask Changes',
                style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)

            result = dlg.ShowModal()

            if result == wx.ID_NO:
                return

        self.image_panel.stopMaskCreation()
        wx.CallAfter(self.image_panel.clearAllMasks)
        wx.CallAfter(self._main_frame.closeMaskingPane)
        wx.CallAfter(self.image_panel.removeCenterPatch)
        self.mask_modified = False
        return

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

        if mode == wx.FD_OPEN:
            filters = 'Mask files (*.msk)|*.msk|All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters, defaultDir = path)
        if mode == wx.FD_SAVE:
            filters = 'Mask files (*.msk)|*.msk'
            dialog = wx.FileDialog( None, style = mode | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = path)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()

        # Destroy the dialog
        dialog.Destroy()

        return file

    def _initBitmaps(self):
        circle_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-full-moon-48.png')
        rectangle_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-rectangular-48.png')
        polygon_png = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-polygon-48.png')

        self.circle_bmp = wx.Bitmap(circle_png, wx.BITMAP_TYPE_PNG)
        self.rectangle_bmp = wx.Bitmap(rectangle_png, wx.BITMAP_TYPE_PNG)
        self.polygon_bmp = wx.Bitmap(polygon_png, wx.BITMAP_TYPE_PNG)



class CenteringPanel(wx.Panel):


    def __init__(self, parent,id):

        wx.Panel.__init__(self, parent, id, name = 'CenteringPanel')

        self.ID_UP, self.ID_DOWN, self.ID_RIGHT, self.ID_LEFT, self.ID_TARGET =  ( self.NewControlId(), self.NewControlId(), self.NewControlId(), self.NewControlId(), self.NewControlId())

        self._x_center = None
        self._y_center = None
        self._repeat_timer = wx.Timer()
        self._repeat_timer.Bind(wx.EVT_TIMER, self._onRepeatTimer)

        self._fix_list = [  ('Wavelength', self.NewControlId()),
                            ('S-D Dist.', self.NewControlId()),
                            ('Beam X', self.NewControlId()),
                            ('Beam Y', self.NewControlId())
                        ]

        self._fix_keywords = {self._fix_list[0][1]      : 'wavelength',
                                self._fix_list[1][1]    : 'dist',
                                self._fix_list[2][1]    : 'poni2',
                                self._fix_list[3][1]    : 'poni1'
                            }

        self.pyfai_autofit_ids = {  'ring':         self.NewControlId(),
                                    'detector':     self.NewControlId(),
                                    'remove_pts':   self.NewControlId(),
                                    'start':        self.NewControlId(),
                                    'done':         self.NewControlId(),
                                    'cancel':       self.NewControlId(),
                                    'help':         self.NewControlId()
                                }

        self.pyfai_enable = ['detector', 'remove_pts', 'start', 'done', 'cancel']

        self.old_calibrant = None

        self.autocenter = False

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

        auto_box = wx.StaticBox(self, -1, 'Automatic Centering/Calibration')
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
        wx.CallAfter(self._updateCenteringRings)

    def _initBitmaps(self):
        up = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-thick-arrow-pointing-up-32.png')
        right = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-thick-arrow-pointing-right-32.png')
        down = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-thick-arrow-pointing-down-32.png')
        left = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-thick-arrow-pointing-left-32.png')
        target = os.path.join(RAWGlobals.RAWResourcesDir, 'icons8-center-of-gravity-filled-32.png')

        self.up_arrow_bmp = wx.Bitmap(up, wx.BITMAP_TYPE_PNG)
        self.right_arrow_bmp = wx.Bitmap(right, wx.BITMAP_TYPE_PNG)
        self.down_arrow_bmp = wx.Bitmap(down, wx.BITMAP_TYPE_PNG)
        self.left_arrow_bmp = wx.Bitmap(left, wx.BITMAP_TYPE_PNG)
        self.target_bmp = wx.Bitmap(target, wx.BITMAP_TYPE_PNG)

    def _createAutoCenteringSizer(self):

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        fix_ctrl_sizer = wx.FlexGridSizer(cols = 4, rows = int(len(self._fix_list)/4. + .5), hgap = 3, vgap = 3)

        for label, newid in self._fix_list:
            chkbox = wx.CheckBox(self, newid, label)
            if label == 'Wavelength':
                chkbox.SetValue(True)
            else:
                chkbox.SetValue(False)

            fix_ctrl_sizer.Add(chkbox)

        fix_sizer = wx.BoxSizer(wx.HORIZONTAL)

        fix_text = wx.StaticText(self, -1, 'Fix:')
        fix_sizer.Add(fix_text, 0, wx.LEFT | wx.RIGHT, 3)
        fix_sizer.Add(fix_ctrl_sizer, 1, wx.RIGHT, 3)


        ring_text = wx.StaticText(self, -1, 'Ring #:')
        ring_ctrl = RAWCustomCtrl.IntSpinCtrl(self, self.pyfai_autofit_ids['ring'], min = 0, max = 100, TextLength = 43)
        ring_ctrl.SetValue(0)
        ring_ctrl.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onAutoRingSpinner)

        ring_remove_btn = wx.Button(self, self.pyfai_autofit_ids['remove_pts'], 'Clear All Points In Ring')
        ring_remove_btn.Bind(wx.EVT_BUTTON, self._onAutoRingRemoveButton)
        ring_remove_btn.Enable(False)

        ring_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ring_sizer.Add(ring_text, 0, wx.LEFT | wx.RIGHT, 3)
        ring_sizer.Add(ring_ctrl, 0, wx.RIGHT, 3)
        ring_sizer.Add(ring_remove_btn, 0, wx.RIGHT, 3)

        det_list = self._getDetList()

        det_text = wx.StaticText(self, -1, 'Detector: ')
        det_choice = wx.Choice(self, self.pyfai_autofit_ids['detector'], choices = det_list)
        det_choice.SetStringSelection('pilatus1m')

        det_sizer = wx.BoxSizer(wx.HORIZONTAL)
        det_sizer.Add(det_text, 0, wx.LEFT | wx.RIGHT, 3)
        det_sizer.Add(det_choice, 0, wx.RIGHT, 3)

        start_btn = wx.Button(self, self.pyfai_autofit_ids['start'], 'Start')
        start_btn.Bind(wx.EVT_BUTTON, self._onAutoCenterStartButton)

        done_btn = wx.Button(self, self.pyfai_autofit_ids['done'], 'Done')
        done_btn.Bind(wx.EVT_BUTTON, self._onAutoCenterDoneButton)
        done_btn.Enable(False)

        cancel_btn = wx.Button(self, self.pyfai_autofit_ids['cancel'], 'Cancel')
        cancel_btn.Bind(wx.EVT_BUTTON, self._onAutoCenterCancelButton)
        cancel_btn.Enable(False)

        help_btn = wx.Button(self, self.pyfai_autofit_ids['help'], 'How To Use')
        help_btn.Bind(wx.EVT_BUTTON, self._onAutoCenterHelpButton)

        ctrl_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ctrl_button_sizer.Add(start_btn, 0, wx.LEFT | wx.RIGHT, 3)
        ctrl_button_sizer.Add(done_btn, 0, wx.RIGHT, 3)
        ctrl_button_sizer.Add(cancel_btn, 0, wx.RIGHT, 3)
        ctrl_button_sizer.Add(help_btn, 0, wx.RIGHT, 3)

        top_sizer.Add(fix_sizer, 0, wx.BOTTOM, 3)
        top_sizer.Add(ring_sizer, 0, wx.BOTTOM, 3)
        top_sizer.Add(det_sizer, 0, wx.BOTTOM, 3)
        top_sizer.Add(ctrl_button_sizer, 0, wx.TOP, 3)

        return top_sizer

    def _createCenteringButtonsSizer(self):

        buttonsizer = wx.FlexGridSizer(rows=3, cols=3, hgap=0, vgap=0)

        up_button = wx.BitmapButton(self, self.ID_UP, self.up_arrow_bmp)
        down_button = wx.BitmapButton(self,self.ID_DOWN, self.down_arrow_bmp)
        right_button = wx.BitmapButton(self, self.ID_RIGHT , self.right_arrow_bmp)
        left_button = wx.BitmapButton(self, self.ID_LEFT, self.left_arrow_bmp)
        target_button = wx.BitmapButton(self, self.ID_TARGET, self.target_bmp)

        up_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        down_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        right_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)
        left_button.Bind(wx.EVT_LEFT_DOWN, self._onCenteringButtons)

        up_button.Bind(wx.EVT_LEFT_DCLICK, self._onCenteringButtons)
        down_button.Bind(wx.EVT_LEFT_DCLICK, self._onCenteringButtons)
        right_button.Bind(wx.EVT_LEFT_DCLICK, self._onCenteringButtons)
        left_button.Bind(wx.EVT_LEFT_DCLICK, self._onCenteringButtons)

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

        step_list= ['0.1', '1', '2', '5', '10', '20', '50', '100', '500']

        pattern_list = ['None'] + sorted(pyFAI.calibrant.names(), key = str.lower)

        self._x_cent_text = wx.TextCtrl(self, -1, '0', size = (65, -1), style = wx.TE_PROCESS_ENTER)
        self._y_cent_text = wx.TextCtrl(self, -1, '0', size = (65, -1), style = wx.TE_PROCESS_ENTER)
        self._y_cent_text.Bind(wx.EVT_TEXT_ENTER, self._onEnterInCenterCtrl)
        self._x_cent_text.Bind(wx.EVT_TEXT_ENTER, self._onEnterInCenterCtrl)
        self._x_cent_text.Bind(wx.EVT_KILL_FOCUS, self._onEnterInCenterCtrl)
        self._y_cent_text.Bind(wx.EVT_KILL_FOCUS, self._onEnterInCenterCtrl)

        self._step_combo = wx.ComboBox(self, -1, choices = step_list)
        self._step_combo.Select(1)

        self._wavelen_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 70)
        self._energy_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 70)
        self._pixel_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 80)
        self._sd_text = RAWCustomCtrl.FloatSpinCtrl(self, -1, TextLength = 80)

        self._sd_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onSampDetDistSpin)
        self._wavelen_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onWavelengthChange)
        self._pixel_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onPixelWavelengthChange)
        self._energy_text.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._onEnergyChange)

        self._pattern_list = wx.Choice(self, -1, choices = pattern_list)
        if 'AgBh' in pattern_list:
            self._pattern_list.SetStringSelection('AgBh')
        else:
            self._pattern_list.Select(1)
        self._pattern_list.Bind(wx.EVT_CHOICE, self._onPatternChoice)

        wavelen_label = wx.StaticText(self, -1, 'Wavelength:')
        energy_label = wx.StaticText(self, -1, 'Energy:')
        sd_label = wx.StaticText(self, -1, 'Sample-Detector Distance:')
        pixel_label = wx.StaticText(self, -1, 'Detector Pixel Size:')

        ylabel = wx.StaticText(self, -1, 'Y center:')
        xlabel = wx.StaticText(self, -1, 'X center:')
        step_label = wx.StaticText(self, -1, 'Steps:')
        pattern_label = wx.StaticText(self, -1, 'Standard:')

        sd_unit_label = wx.StaticText(self, -1, 'mm')
        pixelsize_unit_label = wx.StaticText(self, -1, 'um')
        wavelength_unit_label = wx.StaticText(self, -1, 'A')
        energy_unit_label = wx.StaticText(self, -1, 'keV')

        x_sizer = wx.BoxSizer(wx.VERTICAL)
        y_sizer = wx.BoxSizer(wx.VERTICAL)
        step_sizer = wx.BoxSizer(wx.VERTICAL)
        wave_sizer = wx.BoxSizer(wx.VERTICAL)
        energy_sizer = wx.BoxSizer(wx.VERTICAL)
        pixel_sizer = wx.BoxSizer(wx.VERTICAL)
        sd_sizer = wx.BoxSizer(wx.VERTICAL)
        pattern_sizer = wx.BoxSizer(wx.VERTICAL)

        sd_unit_sizer = wx.BoxSizer()
        pixelsize_unit_sizer = wx.BoxSizer()
        wavelength_unit_sizer = wx.BoxSizer()
        energy_unit_sizer = wx.BoxSizer()

        step_sizer.Add(step_label,0, wx.TOP,-1)
        step_sizer.Add(self._step_combo, 0)
        x_sizer.Add(xlabel, 0)
        x_sizer.Add(self._x_cent_text,0)
        y_sizer.Add(ylabel, 0)
        y_sizer.Add(self._y_cent_text,0)

        sd_unit_sizer.Add(self._sd_text, 0, wx.RIGHT, 3)
        sd_unit_sizer.Add(sd_unit_label, 0, wx.ALIGN_CENTER_VERTICAL)

        pixelsize_unit_sizer.Add(self._pixel_text, 0, wx.RIGHT, 3)
        pixelsize_unit_sizer.Add(pixelsize_unit_label, 0, wx.ALIGN_CENTER_VERTICAL)

        wavelength_unit_sizer.Add(self._wavelen_text, 0, wx.RIGHT, 3)
        wavelength_unit_sizer.Add(wavelength_unit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

        energy_unit_sizer.Add(self._energy_text, 0, wx.RIGHT, 3)
        energy_unit_sizer.Add(energy_unit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

        wave_sizer.Add(wavelen_label, 0)
        wave_sizer.Add(wavelength_unit_sizer, 0)

        energy_sizer.Add(energy_label, 0)
        energy_sizer.Add(energy_unit_sizer, 0)

        sd_sizer.Add(sd_label, 0)
        sd_sizer.Add(sd_unit_sizer, 0)

        pixel_sizer.Add(pixel_label, 0)
        pixel_sizer.Add(pixelsize_unit_sizer, 0)

        pattern_sizer.Add(pattern_label, 0)
        pattern_sizer.Add(self._pattern_list, 0)


        self.xycenter_sizer = wx.BoxSizer()
        self.xycenter_sizer.Add(x_sizer,0, wx.RIGHT, 5)
        self.xycenter_sizer.Add(y_sizer,0, wx.RIGHT, 5)
        self.xycenter_sizer.Add(step_sizer,0)


        energy_wl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        energy_wl_sizer.Add(wave_sizer, 0, wx.RIGHT, 15)
        energy_wl_sizer.Add(energy_sizer, 0)


        self.calib_sizer = wx.BoxSizer(wx.VERTICAL)

        self.calib_sizer.Add(energy_wl_sizer, 0, wx.BOTTOM, 5)
        self.calib_sizer.Add(sd_sizer, 0, wx.BOTTOM, 5)
        self.calib_sizer.Add(pixel_sizer, 0, wx.BOTTOM, 5)
        self.calib_sizer.Add(pattern_sizer,0, wx.BOTTOM, 5)

        self.final_sizer = wx.BoxSizer(wx.VERTICAL)

        self.final_sizer.Add(self.xycenter_sizer,0, wx.BOTTOM, 5)
        self.final_sizer.Add(self.calib_sizer,0)

        self.manual_widget_list.append(self._x_cent_text)
        self.manual_widget_list.append(self._y_cent_text)
        self.manual_widget_list.append(self._step_combo)
        self.manual_widget_list.append(self._wavelen_text)
        self.manual_widget_list.append(self._pixel_text)
        self.manual_widget_list.append(self._sd_text)
        self.manual_widget_list.append(self._pattern_list)
        self.manual_widget_list.append(self._energy_text)

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

    def _getDetList(self):

        extra_det_list = ['detector']

        # Gets rid of all the aliases, not sure if I want to do that

        # dets = pyFAI.detectors.ALL_DETECTORS

        # keys = dets.keys()

        # for key in keys:
        #     if key.find('_') > -1:
        #         tmp_key = ''.join(key.split('_'))

        #         if dets.has_key(tmp_key):
        #             dets.pop(tmp_key)

        #         tmp_key = '-'.join(key.split('_'))

        #         if dets.has_key(tmp_key):
        #             dets.pop(tmp_key)

        # unique_dets = defaultdict(list)

        # for k, v in dets.iteritems():
        #     unique_dets[v].append(k)

        # final_dets = {}

        # for k, v in unique_dets.iteritems():
        #     if len(v) > 1:
        #         v = sorted(v, key = len, reverse = True)

        #     final_dets[v[0]] = k


        # Keeps all the aliases
        final_dets = pyFAI.detectors.ALL_DETECTORS


        for key in extra_det_list:
            if final_dets.has_key(key):
                final_dets.pop(key)

        det_list = ['Other'] + sorted(final_dets.keys(), key = str.lower)

        return det_list

    def _onEnterInCenterCtrl(self, event):

        x = str(self._x_cent_text.GetValue()).replace(',','.')
        y = str(self._y_cent_text.GetValue()).replace(',','.')

        try:
            self.setCenter([float(x),float(y)])
        except ValueError:
            pass
        event.Skip()

    def _onOkButton(self, event):
        if self.autocenter:
            self._cleanUpAutoCenter()
        self.image_panel.enableCenterClickMode(False)

        wx.CallAfter(self._main_frame.closeCenteringPane)
        wx.CallAfter(self.image_panel.clearPatches)

        self._main_frame.raw_settings.set('Xcenter', self._center[0])
        self._main_frame.raw_settings.set('Ycenter', self._center[1])

        sd, wavelength, pixel_size = self._getCalibValues()

        self._main_frame.raw_settings.set('SampleDistance', sd)
        self._main_frame.raw_settings.set('WaveLength', wavelength)
        self._main_frame.raw_settings.set('DetectorPixelSize', pixel_size)

    def _getCalibValues(self):

        sd = float(self._sd_text.GetValue())
        wavelength = float(self._wavelen_text.GetValue())
        pixel_size = float(self._pixel_text.GetValue())

        return sd, wavelength, pixel_size

    def _onCancelButton(self, event):
        if self.autocenter:
            self._cleanUpAutoCenter()

        self.image_panel.enableCenterClickMode(False)


        self.updateCenterFromSettings()
        wx.CallAfter(self._main_frame.closeCenteringPane)
        wx.CallAfter(self.image_panel.clearPatches)

    def _onRepeatTimer(self, event):
        steps = float(self._step_combo.GetValue())
        wx.Yield()
        wx.CallAfter(self._moveCenter, self._pressed_button_id, steps)

    def _onCenteringButtonsUp(self, event):
        self._repeat_timer.Stop()
        event.Skip()

    def _onCenteringButtons(self, event):

        id = event.GetId()

        steps = float(self._step_combo.GetValue())
        self._pressed_button_id = id
        wx.CallAfter(self._moveCenter, id, steps)

        # if platform.system() != 'Darwin':
        self._repeat_timer.Start(150)

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

    def _onWavelengthChange(self, evt):
        c = scipy.constants.c
        h = scipy.constants.h
        e = scipy.constants.e

        wl = float(evt.GetValue().replace(',','.'))*1e-10

        E=c*h/(wl*e)*1e-3

        self._energy_text.SetValue(str(E))

        self._updatePlots()

    def _onEnergyChange(self, evt):
        c = scipy.constants.c
        h = scipy.constants.h
        e = scipy.constants.e

        E = float(evt.GetValue().replace(',','.'))*1e3

        wl=c*h/(E*e)*1e10

        self._wavelen_text.SetValue(str(wl))

        self._updatePlots()

    def _onTargetButton(self, event):
        self.image_panel.enableCenterClickMode()

        wx.MessageBox('Click on the image to move the center to a new location.', 'Select center on image')

    def _onPatternChoice(self, event):
        selection = self._pattern_list.GetStringSelection()

        if selection == 'None': #none
            wx.CallAfter(self.image_panel.clearPatches)

        else: #Agbe
            wx.CallAfter(self._updateCenteringRings)

    def _onSampDetDistSpin(self, event):
        self._updatePlots()

    def _enableControls(self, state):

        for each in self.manual_widget_list:
            each.Enable(state)

    def _updateCenteringRings(self):
        sd_distance, wavelength, pixel_size = self._getCalibValues()

        selection = self._pattern_list.GetStringSelection()

        if selection != 'None':

            self.calibrant = pyFAI.calibrant.get_calibrant(selection)
            self.calibrant.set_wavelength(wavelength*1e-10) #set the wavelength in m

            #Calculate pixel position of the calibrant rings
            two_thetas = np.array(self.calibrant.get_2th())
            if len(two_thetas) > 0:
                opposite = np.tan(two_thetas) * sd_distance
                agbh_dist_list = list(opposite / (pixel_size/1000.))
            else:
                agbh_dist_list = [np.nan]

            if self.old_calibrant is not None and self.old_calibrant != selection:
                wx.CallAfter(self.image_panel.clearPatches)
            self.old_calibrant = selection

            if not np.isnan(agbh_dist_list[0]): #If wavelength is too long, can get values for the ring radius that are nans
                wx.CallAfter(self.image_panel._drawCenteringRings, self._center, agbh_dist_list)
            else:
                self._wavelen_text.SetValue('1')
                wx.MessageBox('Wavelength too long, cannot show centering rings on the plot.', 'Invalid Entry', style=wx.ICON_ERROR)
                return

    def updateCenterTextCtrls(self):
        self._x_cent_text.SetValue(str(self._center[0]))
        self._y_cent_text.SetValue(str(self._center[1]))

    def _updatePlots(self):
        if self._pattern_list.GetStringSelection() != 'None':
            self._updateCenteringRings()

    def updateCenterFromSettings(self):
        x_center = self._main_frame.raw_settings.get('Xcenter')
        y_center = self._main_frame.raw_settings.get('Ycenter')

        wavelength = self._main_frame.raw_settings.get('WaveLength')
        pixel_size = self._main_frame.raw_settings.get('DetectorPixelSize')
        samp_detc_dist = self._main_frame.raw_settings.get('SampleDistance')

        c = scipy.constants.c
        h = scipy.constants.h
        e = scipy.constants.e

        wl = float(wavelength)*1e-10

        energy=c*h/(wl*e)*1e-3

        self._sd_text.SetValue(str(samp_detc_dist))
        self._pixel_text.SetValue(str(pixel_size))
        self._wavelen_text.SetValue(str(wavelength))
        self._energy_text.SetValue(str(energy))

        self._center = [x_center, y_center]
        self.updateCenterTextCtrls()

    def updateAll(self):
        self.updateCenterFromSettings()
        self._updatePlots()

    def setCenter(self, center):
        self._center = center
        self.updateCenterTextCtrls()
        self._updatePlots()

    #Controls for autocentering, most of them for the pyfai based method
    def _onAutoRingSpinner(self, evt):
        value = evt.GetValue()
        self.image_panel.pyfai_ring_num = value

    def _onAutoRingRemoveButton(self, evt):
        value = wx.FindWindowById(self.pyfai_autofit_ids['ring'], self).GetValue()

        self.c.points.pop(int(value))

        wx.CallAfter(self.image_panel.clearPatches)

        wx.CallAfter(self.image_panel.drawCenteringPoints, self.c.points.getList())

    def _onAutoCenterStartButton(self, event):
        self.autocenter = True
        self._startAutoCentering()

    def _onAutoCenterDoneButton(self, evt):
        self._stopAutoCentering()

    def _onAutoCenterCancelButton(self, evt):
        self._cleanUpAutoCenter()

    def _onAutoCenterHelpButton(self, evt):
        msg = ("To run automatic centering and calibration you should:\n"
                "1) Select the appropriate Standard in the manual calibration section.\n"
                "2) Select the parameters to hold constant by checking boxes in the Fix section.\n"
                "3) Select the detector type to be used. If your detector is not in the list, select Other.\n"
                "4) Set the Ring # to the index of the first ring visible on the detector. The ring index starts at zero for the largest "
                "d-spacing ring (nearest the beam) and increments by one for each ring thereafter. IMPORTANT: The first ring visible on your "
                "detector image may not be ring 0!\n"
                "5) Click the Start button. Then click on the first ring in the image. Points in that ring will be automatically selected. "
                "Click on other parts of the ring as necessary to fill in points.\n"
                "6) Increment the ring number as appropriate for the next ring visible on the image (usually increment by 1, for example from 0 to 1), "
                "and click on the next ring on the image to select points there. Repeat for all visible rings.\n"
                "7) (If necessary) To remove points in a ring, set the Ring # to that ring, and click the Clear All Points In Ring button.\n"
                "8) Click the Done button once you have selected points in all of the visible standard rings. At this point, automatic centering and calibration will be carried out.\n"
                "Note: ring points cannot be selected if the Pan or Zoom tool are selected.")

        wx.MessageBox(msg, 'Instructions')

    #Autocenter using pyFAI, the new RAW way
    def _startAutoCentering(self):

        img = self.image_panel.img

        if img is None:
            wx.MessageBox('You must have an image shown in the Image plot to use auto centering.', 'No Image Loaded', wx.OK)
            return

        sd_distance, wavelength, pixel_size = self._getCalibValues()
        cal_selection = self._pattern_list.GetStringSelection()
        det_selection = wx.FindWindowById(self.pyfai_autofit_ids['detector'], self).GetStringSelection()

        if cal_selection == 'None':
            wx.MessageBox('You must select a calibration standard to use autocentering.', 'No Calibration Standard Selected', wx.OK)
            return

        wx.CallAfter(self.image_panel.clearPatches)

        self._enableControls(False)
        self._enablePyfaiControls()

        calibrant = pyFAI.calibrant.get_calibrant(cal_selection)
        calibrant.set_wavelength(wavelength*1e-10)

        if det_selection != 'Other':
            detector = pyFAI.detector_factory(det_selection)

        else:
            pixel_size = float(self._pixel_text.GetValue())*1e-6

            detector = pyFAI.detectors.Detector(pixel1 = pixel_size, pixel2 = pixel_size, max_shape = img.shape)

        self.c = SASCalib.RAWCalibration(img, wavelength = calibrant.wavelength, calibrant = calibrant, detector = detector)
        self.c.ai = pyFAI.AzimuthalIntegrator(wavelength = wavelength, detector = detector)
        self.c.ai.setFit2D(sd_distance, self._center[0], self._center[1]) #Takes the sample-detector distance in mm, beamx and beam y in pixels.
        self.c.points = pyFAI.peak_picker.ControlPoints(None, calibrant=calibrant, wavelength=calibrant.wavelength)

        self.image_panel.enableAutoCentMode()

    def _stopAutoCentering(self):
        img = self.image_panel.img

        self.c.data = self.c.points.getWeightedList(img)

        if not self.c.weighted:
            self.c.data = np.array(self.c.data)[:, :-1]

        for my_id, keyword in self._fix_keywords.iteritems():

            value = wx.FindWindowById(my_id, self).GetValue()

            self.c.fixed.add_or_discard(keyword, value)

        self.c.refine()

        results = self.c.geoRef.getFit2D()

        self._center = [results['centerX'], results['centerY']]
        self._sd_text.SetValue(str(results['directDist']))

        wavelength = self.c.geoRef.get_wavelength()*1e10
        pixel_size = self.c.geoRef.get_pixel1()*1e6

        self._wavelen_text.SetValue(str(wavelength))
        self._pixel_text.SetValue(str(pixel_size))

        self.updateCenterTextCtrls()
        wx.CallAfter(self.image_panel.clearPatches)
        self._cleanUpAutoCenter()

    def _enablePyfaiControls(self):
        for key in self.pyfai_enable:
            window = wx.FindWindowById(self.pyfai_autofit_ids[key], self)
            status = window.IsEnabled()
            window.Enable(not status)

    def _cleanUpAutoCenter(self):
        self._updateCenteringRings()
        self._enableControls(True)
        self._enablePyfaiControls()
        self.image_panel.enableAutoCentMode(False)
        self.autocenter = False

#----- **** InformationPanel ****

class InformationPanel(wx.Panel):

    def __init__(self, parent):

        self.font_size1 = 11
        self.font_size2 = 12

        if platform.system() == 'Windows' or platform.system() == 'Linux':
            self.font_size1 = 8
            self.font_size2 = 10

        self.used_font1 = wx.Font(self.font_size1, wx.FONTFAMILY_SWISS,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        wx.Panel.__init__(self, parent, name = 'InformationPanel')

        infoSizer = wx.BoxSizer(wx.VERTICAL)

        self.analysis_data = [('Rg:', 'Rg', self.NewControlId()),
                              ('I0:', 'I0', self.NewControlId()),
                              ('MW:', 'MW', self.NewControlId())]

        self.conc_data = ('Conc:', 'Conc', self.NewControlId())

        self.analysis_info_sizer = self._createAnalysisInfoSizer()

        infoSizer.Add(self.analysis_info_sizer, 0, wx.ALL | wx.EXPAND, 5)


        #header_note_box = wx.StaticBox(self, -1, 'Header data / Notes')
        #header_note_boxsizer = wx.StaticBoxSizer(header_note_box, orient = wx.VERTICAL)

        header_note_boxsizer = wx.BoxSizer(wx.VERTICAL)

        note_txt = wx.StaticText(self,-1,'Description / Notes:')
        note_txt.SetFont(self.used_font1)

        hdrbrow_txt = wx.StaticText(self,-1,'Header browser:')
        hdrbrow_txt.SetFont(self.used_font1)

        header_note_boxsizer.Add(note_txt, 0)
        header_note_boxsizer.Add(self._createNoteSizer(), 0, wx.ALL | wx.EXPAND, 5)
        header_note_boxsizer.Add(hdrbrow_txt, 0)
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
        self.header_txt = wx.TextCtrl(self, -1, '', style = wx.TE_CENTRE)
        self.header_choice.SetFont(self.used_font1)
        self.header_txt.SetFont(self.used_font1)
        self.header_choice.Bind(wx.EVT_CHOICE, self._onHeaderBrowserChoice)

        sizer.Add(self.header_choice, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(self.header_txt, 2, wx.EXPAND)

        return sizer

    def _createAnalysisInfoSizer(self):

        sizer = wx.BoxSizer(wx.VERTICAL)

        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.name_label = wx.StaticText(self, -1, 'Name:')
        self.name_txt = wx.StaticText(self, -1, 'None')

        self.name_label.SetFont(self.used_font1)
        self.name_txt.SetFont(self.used_font1)


        name_sizer.Add(self.name_label, 0, wx.RIGHT, 10)
        name_sizer.Add(self.name_txt, 1, wx.EXPAND)

        analysis_sizer = wx.BoxSizer()
        for each in self.analysis_data:
            label = each[0]
            id = each[2]
            value = 'N/A'

            label_txt = wx.StaticText(self, -1, label)
            value_txt = wx.TextCtrl(self, id, value, size = (60, -1), style = wx.TE_READONLY)
            label_txt.SetFont(self.used_font1)
            value_txt.SetFont(self.used_font1)
            value_txt.SetSize((60,-1))

            siz = wx.BoxSizer()
            siz.Add(label_txt, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 3)
            siz.Add(value_txt, 1, wx.EXPAND)

            analysis_sizer.Add(siz, 1, wx.RIGHT | wx.EXPAND, 10)

        ## add conc ctrl:
        label_txt = wx.StaticText(self, -1, self.conc_data[0])
        label_txt.SetFont(self.used_font1)

        self.conc_txt = wx.TextCtrl(self, self.conc_data[2], 'N/A', size = (60, -1))
        self.conc_txt.Bind(wx.EVT_KILL_FOCUS, self._onNoteTextKillFocus)
        self.conc_txt.Bind(wx.EVT_TEXT, self._updateConc)
        self.conc_txt.SetFont(self.used_font1)

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

        event.Skip()

    def _updateConc(self, event):
        try:
            conc = self.conc_txt.GetValue().replace(',','.')
            if self.sasm != None and conc != 'N/A' and conc != 'N/' and conc !='N' and conc !='/A' and conc !='A' and conc != 'NA' and conc != '' and conc !='.':

                float(conc)
                self.sasm.setParameter('Conc', float(conc))


        except Exception, e:
            print e
            print 'info error, Conc'

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
            except Exception:
                pass

        try:
            note_txt = self.noteTextBox.GetValue()
            self.sasm.setParameter('Notes', note_txt)

        except AttributeError:
            pass

        self.name_txt.SetLabel('')

        for each in self.analysis_data:
            id = each[2]

            label = wx.FindWindowById(id, self)
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
                for each in self.analysis_data:
                    key = each[1]
                    id = each[2]

                    txt = wx.FindWindowById(id, self)

                    if guinier.has_key(key):
                        txt.SetValue(str(guinier[key]))

        if self.sasm.getAllParameters().has_key('Conc'):
            conc_ctrl = wx.FindWindowById(self.conc_data[2], self)
            conc_ctrl.SetValue(str(self.sasm.getParameter('Conc')))

        if self.sasm.getAllParameters().has_key('MW'):
            mw_ctrl = wx.FindWindowById(self.analysis_data[2][2], self)
            mw_ctrl.SetValue(str(self.sasm.getParameter('MW')))

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



#########################################
#This gets around not being able to catch errors in threads
#Code from: https://bugs.python.org/issue1230540
def setup_thread_excepthook():
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads.
    """

    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):

        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


#--- ** Startup app **


class WelcomeDialog(wx.Frame):
    def __init__(self, parent, *args, **kwargs):

        wx.Frame.__init__(self,parent, -1, style = wx.RESIZE_BORDER | wx.STAY_ON_TOP, *args, **kwargs)

        self.panel = wx.Panel(self, -1, style = wx.BG_STYLE_SYSTEM | wx.RAISED_BORDER)

        self.ok_button = wx.Button(self.panel, -1, 'OK')
        self.ok_button.Bind(wx.EVT_BUTTON, self._onOKButton)
        self.ok_button.SetDefault()

        raw_bitmap = RAWIcons.raw.GetBitmap()
        rawimg = wx.StaticBitmap(self.panel, -1, raw_bitmap)

        headline = wx.StaticText(self.panel, -1, 'Welcome to RAW %s!' %(RAWGlobals.version))

        text1 = 'Developers/Contributors:'
        text2 = '\nSoren Skou'
        text3 = 'Jesse B. Hopkins'
        text4 = 'Richard E. Gillilan'
        text5 = 'Jesper Nygaard'
        text6 = 'Kurt Andersen'

        text7 = ('\nHelp this software become better by reporting bugs to:\n     http://bit.ly/rawhelp\n'
                '     or to soren.skou@saxslab.com and hopkins.jesse@gmail.com\n')

        text8 = 'If you use this software for your SAXS data processing please cite:    \n'
        text9 = ('"BioXTAS RAW: improvements to a free open-source program for\n'
                'small-angle X-ray scattering data reduction and analysis."\n'
                'J. B. Hopkins, R. E. Gillilan, and S. Skou. Journal of Applied\n'
                'Crystallography (2017). 50, 1545-1553\n\n')

        all_text = [text1, text2, text3, text4, text5, text6, text7, text8, text9]

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(rawimg, 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 10)
        final_sizer.Add(headline, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 15)

        for each in all_text:
            txt = wx.StaticText(self.panel, -1, each)
            final_sizer.Add(txt, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT | wx.RIGHT, 15)

        final_sizer.Add(self.ok_button, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        self.panel.SetSizer(final_sizer)
        self.panel.Layout()
        self.panel.Fit()
        self.Fit()

        self.SetDefaultItem(self.ok_button)

        self.panel.Bind(wx.EVT_KEY_DOWN, self._onKeyDown)

        self.Raise()

        self.CenterOnParent()


    def _onOKButton(self, event):
        # mainworker_cmd_queue.put(['startup', sys.argv])
        wx.CallLater(1, wx.FindWindowByName("MainFrame")._onStartup, sys.argv)
        self.OnClose()

    def _onKeyDown(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self._onOKButton(-1)
        else:
            event.Skip()

    def OnClose(self):
        self.Destroy()

    def getFilename(self):
        return self._filename


class MyApp(wx.App):

    def __init__(self, *args, **kwargs):
        wx.App.__init__(self, *args, **kwargs)
        # This catches events when the app is asked to activate by some other
        # process on Mac
        # self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

    def OnInit(self):
        standard_paths = wx.StandardPaths.Get()

        sys.excepthook = self.ExceptionHook

        RAWGlobals.RAWWorkDir = standard_paths.GetUserLocalDataDir()
        if not os.path.exists(RAWGlobals.RAWWorkDir):
            os.mkdir(RAWGlobals.RAWWorkDir)

        if RAWGlobals.frozen:
            if platform.system() == 'Windows':
                RAWGlobals.RAWResourcesDir = os.path.join(standard_paths.GetResourcesDir(),'resources')
            else:
                RAWGlobals.RAWResourcesDir = standard_paths.GetResourcesDir()
        else:
            RAWGlobals.RAWResourcesDir = os.path.join(sys.path[0], 'resources')

        MySplash = MySplashScreen()
        MySplash.Show()

        return True

    def BringWindowToFront(self):
        try: # it's possible for this event to come when the frame is closed
            self.GetTopWindow().Raise()
        except:
            pass

    #########################
    # Here's some stuff to inform users of unhandled errors, and quit
    # gracefully. From http://apprize.info/python/wxpython/10.html

    def ExceptionHook(self, errType, value, trace):
        err = traceback.format_exception(errType, value, trace)
        errTxt = "\n".join(err)
        msg = ("An unexpected error has occurred, please report it to the "
                "developers. You may need to restart RAW to continue working"
                "\n\nError:\n%s" %(errTxt))

        if self and self.IsMainLoopRunning():
            if not self.HandleError(value):
                wx.CallAfter(wx.lib.dialogs.scrolledMessageDialog, None, msg, "Unexpected Error")
        else:
            sys.stderr.write(msg)

    def HandleError(self, error):
        """ Override in subclass to handle errors
        @return: True to allow program to continue running withou showing error"""

        return False



    # def OnActivate(self, event):
    #     # if this is an activate event, rather than something else, like iconize.
    #     if event.GetActive():
    #         self.BringWindowToFront()
    #     event.Skip()


    #NOTE: These mac specific events *should* be implimented, but
    #currently pyinstaller doesn't actually forward these vents to the
    #program, so there is not way of testing whether they actually work.
    #For now they remain commented out.
    # #Mac specific
    # def MacOpenFiles(self, filename):
    #     """Called for files droped on dock icon, or opened via finders context menu"""
    #     mainworker_cmd_queue.put(['plot', filename])

    # #Mac specific
    # def MacReopenApp(self):
    #     """Called when the doc icon is clicked, and ???"""
    #     self.BringWindowToFront().Raise()


class MySplashScreen(SplashScreen):
    """
        Create a splash screen widget.
    """

    def __init__(self, parent = None):

        aBitmap = RAWIcons.logo_atom.GetBitmap()

        if wx.version().split()[0].strip()[0] == '4':
            splashStyle = wx.adv.SPLASH_CENTRE_ON_SCREEN | wx.adv.SPLASH_TIMEOUT
        else:
            splashStyle = wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_TIMEOUT
        splashDuration = 2000 # milliseconds

        SplashScreen.__init__(self, aBitmap, splashStyle, splashDuration, parent)

        self.Bind(wx.EVT_CLOSE, self.OnExit)

        wx.Yield()

        self.fc = wx.CallLater(1, self.ShowMain)

    def OnExit(self, evt):
        if self.fc.IsRunning():
            self.fc.Stop()
            self.ShowMain()
        self.Hide()
        evt.Skip()

    def ShowMain(self):
        frame = MainFrame('RAW %s' %(RAWGlobals.version), -1)

        dlg = WelcomeDialog(frame, name = "WelcomeDialog")
        dlg.SetIcon(frame.GetIcon())
        dlg.Show(True)


class RawTaskbarIcon(TaskBarIcon):
    TBMENU_RESTORE = wx.Window.NewControlId()
    TBMENU_CLOSE   = wx.Window.NewControlId()
    TBMENU_CHANGE  = wx.Window.NewControlId()
    TBMENU_REMOVE  = wx.Window.NewControlId()

    #----------------------------------------------------------------------
    def __init__(self, frame):
        if platform.system() == 'Darwin':
            if wx.version().split()[0].strip()[0] == '4':
                icontype = wx.adv.TBI_DOCK
            else:
                icontype = wx.TBI_DOCK
            TaskBarIcon.__init__(self, iconType=icontype)
        else:
            TaskBarIcon.__init__(self)
        self.frame = frame

        # Set the image
        self.tbIcon = RAWIcons.raw.GetIcon()

        self.SetIcon(self.tbIcon, "Test")

        # bind some events
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)
        # self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftClick)

    #----------------------------------------------------------------------
    # def CreatePopupMenu(self, evt=None):
    #     """
    #     This method is called by the base class when it needs to popup
    #     the menu for the default EVT_RIGHT_DOWN event.  Just create
    #     the menu how you want it and return it from this function,
    #     the base class takes care of the rest.
    #     """
    #     menu = wx.Menu()
    #     menu.Append(self.TBMENU_RESTORE, "Open Program")
    #     menu.Append(self.TBMENU_CHANGE, "Show all the Items")
    #     menu.AppendSeparator()
    #     menu.Append(self.TBMENU_CLOSE,   "Exit Program")
    #     return menu

    #----------------------------------------------------------------------
    def OnTaskBarActivate(self, evt):
        """"""
        pass

    #----------------------------------------------------------------------
    def OnTaskBarClose(self, evt):
        """
        Destroy the taskbar icon and frame from the taskbar icon itself
        """
        self.frame.Close()

    #----------------------------------------------------------------------
    # def OnTaskBarLeftClick(self, evt):
    #     """
    #     Create the right-click menu
    #     """
    #     menu = self.CreatePopupMenu()
    #     self.PopupMenu(menu)
    #     menu.Destroy()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    setup_thread_excepthook()
    app = MyApp(0)   #MyApp(redirect = True)
    app.MainLoop()

