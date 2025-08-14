'''
#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
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
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, str
from io import open

import queue
import sys
import os
import copy
import multiprocessing
import threading
import time
import platform
import collections
import traceback
import tempfile
import shutil
import glob
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import numpy as np
import wx
import wx.lib.agw.flatnotebook as flatNB
from wx.lib.agw import ultimatelistctrl as ULC
import wx.lib.scrolledpanel as scrolled
import wx.grid
import wx.lib.mixins.listctrl as listmix
import scipy.stats as stats
import scipy.integrate as integrate
import matplotlib

matplotlib.rcParams['backend'] = 'WxAgg'
matplotlib.rc('image', origin = 'lower')        # turn image upside down.. x,y, starting from lower left

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
import matplotlib.colors as mplcol
from mpl_toolkits.mplot3d import Axes3D
from  matplotlib.colors import colorConverter as cc

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWSettings as RAWSettings
import bioxtasraw.RAWCustomCtrl as RAWCustomCtrl
import bioxtasraw.SASCalc as SASCalc
import bioxtasraw.SASFileIO as SASFileIO
import bioxtasraw.SASM as SASM
import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.RAWCustomDialogs as RAWCustomDialogs
import bioxtasraw.SASProc as SASProc
import bioxtasraw.BIFT as BIFT
import bioxtasraw.DENSS as DENSS
import bioxtasraw.SECM as SECM
import bioxtasraw.SASUtils as SASUtils
import bioxtasraw.REGALS as REGALS
import bioxtasraw.RAWAnalysis as RAWAnalysis
import bioxtasraw.RAWAPI as RAWAPI

class MultiSeriesFrame(wx.Frame):

    def __init__(self, parent, title, raw_settings, all_series, selected_series):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title)

        self.raw_settings = raw_settings
        self.all_series = all_series
        self.selected_series = selected_series

        client_display = wx.GetClientDisplayRect()

        main_frame = wx.FindWindowByName('MainFrame')
        is_gtk3 = main_frame.is_gtk3

        if not is_gtk3:
            size = (min(1000, client_display.Width), min(900, client_display.Height))
        else:
            size = (min(1080, client_display.Width), min(900, client_display.Height))

        self.SetSize(self._FromDIP(size))

        self.changes_load = False
        self.changes_range = False

        self._createLayout()

        SASUtils.set_best_size(self)
        self.SendSizeEvent()

        self.Bind(wx.EVT_CLOSE, self.OnCloseEvt)

        self.CenterOnParent()
        self.Raise()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):
        panel = wx.Panel(self)

        self.notebook = wx.Notebook(panel)
        self.load_ctrl = MultiSeriesLoadPanel(self, self.notebook)
        self.range_ctrl = MultiSeriesRangePanel(self, self.notebook)
        self.profile_ctrl = MultiSeriesProfilePanel(self, self.notebook)

        self.notebook.AddPage(self.load_ctrl, 'Load Series')
        self.notebook.AddPage(self.range_ctrl, 'Select Ranges')
        self.notebook.AddPage(self.range_ctrl, 'Generate Profiles')

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.notebook, proportion=1, flag=wx.EXPAND)
        panel.SetSizer(panel_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

    def updateColors(self):
        pass

    def initialize(self):
        pass

    def showBusy(self, show=True, msg=''):
        if show:
            self.bi = wx.BusyInfo(msg, self)
        else:
            try:
                del self.bi
                self.bi = None
            except Exception:
                pass

        wx.GetApp().Yield(True)

    def set_has_changes(self, panel, status):
        if panel == 'load':
            self.changes_load = status
        elif panel == 'range':
            self.changes_range = status
        elif panel == 'profiles':
            self.changes_range = status

    def get_has_changes(self, panel):
        if panel == 'load':
            changes = self.changes_load
        elif panel == 'range':
            changes = self.changes_range
        elif panel == 'profiles':
            changes = self.changes_range

        return changes

    def _on_page_changed(self, evt):
        new_page_num = evt.GetSelection()
        new_page = self.notebook.GetPage(new_page_num)
        new_page.on_page_selected()

    def OnCloseEvt(self, evt):
        self.OnClose()

    def OnClose(self):
        self.showBusy(show=False)

        self.load_ctrl.on_close()
        self.range_ctrl.on_close()

        self.Destroy()


class MultiSeriesLoadPanel(wx.ScrolledWindow):

    def __init__(self, series_frame, parent):

        wx.ScrolledWindow.__init__(self, parent,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER|wx.VSCROLL)
        self.SetScrollRate(20,20)

        self.series_frame = series_frame

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        parent = self

        load_box = wx.StaticBox(parent, label='Load series')

        auto_load_btn = wx.Button(load_box, label='Auto Load')
        auto_load_btn.Bind(wx.EVT_BUTTON, self._on_auto_load)

        load_box = wx.StaticBoxSizer(load_box, wx.HORIZONTAL)
        load_box.Add(auto_load_btn)

        self.series_list = SeriesItemList(self, parent, size=self._FromDIP((200,-1)))

        remove_series = wx.Button(parent, label='Remove')
        move_up_series = wx.Button(parent, label='Move Up')
        move_down_series = wx.Button(parent, label='Move Down')

        remove_series.Bind(wx.EVT_BUTTON, self._on_remove_series)
        move_up_series.Bind(wx.EVT_BUTTON, self._on_move_up_series)
        move_down_series.Bind(wx.EVT_BUTTON, self._on_move_down_series)

        series_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        series_btn_sizer.Add(move_up_series)
        series_btn_sizer.Add(move_down_series, flag=wx.LEFT, border=self._FromDIP(5))
        series_btn_sizer.Add(remove_series, flag=wx.LEFT, border=self._FromDIP(5))

        series_list_sizer = wx.BoxSizer(wx.VERTICAL)
        series_list_sizer.Add(self.series_list, flag=wx.EXPAND, proportion=1)
        series_list_sizer.Add(series_btn_sizer, border=self._FromDIP(5),
            flag=wx.TOP|wx.ALIGN_CENTER_HORIZONTAL)

        series_info_box = wx.StaticBox(parent, label='Series Info')

        self.info_name = wx.StaticText(series_info_box, label='')
        self.info_num_profiles = wx.StaticText(series_info_box, label='')
        self.info_path = wx.StaticText(series_info_box, label='')

        series_info_sub_sizer1 = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        series_info_sub_sizer1.Add(wx.StaticText(series_info_box, label='Series:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        series_info_sub_sizer1.Add(self.info_name, flag=wx.ALIGN_CENTER_VERTICAL)
        series_info_sub_sizer1.Add(wx.StaticText(series_info_box, label='Number of profiles:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        series_info_sub_sizer1.Add(self.info_num_profiles, flag=wx.ALIGN_CENTER_VERTICAL)
        series_info_sub_sizer1.Add(wx.StaticText(series_info_box, label='File path:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        series_info_sub_sizer1.Add(self.info_path, flag=wx.ALIGN_CENTER_VERTICAL)

        self.series_file_list = SeriesFileList(series_info_box)

        series_info_sizer = wx.StaticBoxSizer(series_info_box, wx.VERTICAL)
        series_info_sizer.Add(series_info_sub_sizer1, flag=wx.ALL,
            border=self._FromDIP(5))
        series_info_sizer.Add(self.series_file_list, proportion=1,
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM)

        series_top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        series_top_sizer.Add(series_list_sizer, flag=wx.EXPAND)
        series_top_sizer.Add(series_info_sizer, flag=wx.EXPAND|wx.LEFT,
            border=self._FromDIP(5), proportion=1)


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(load_box)
        top_sizer.Add(series_top_sizer, proportion=1, flag=wx.EXPAND)

        self.SetSizer(top_sizer)

    def _on_auto_load(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        dialog = wx.FileDialog(self, message='Select a file',
            defaultDir=load_path, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()

        # Destroy the dialog
        dialog.Destroy()

        path, filename = os.path.split(file)

        fprefix, ext = os.path.splitext(filename)

        search_prefix = '_'.join(fprefix.split('_')[:-4])

        scan_list = []

        search_key = '{}_*{}'.format(search_prefix, ext)
        files = glob.glob(os.path.join(path, search_key))

        series_files = {}

        for f in files:
            scan = f.split('_')[-4]

            if scan not in scan_list:
                scan_list.append(scan)
                series_files[scan] = [f, ]
            else:
                temp_flist = series_files[scan]
                temp_flist.append(f)
                series_files[scan] = temp_flist

        scan_list.sort()

        series_list = []

        for scan in scan_list:
            flist = series_files[scan]
            flist.sort()

            _, first_filename = os.path.split(flist[0])

            series_name = '_'.join(first_filename.split('_')[:-3])

            series_data = {
                'files' : flist,
                'scan'  : scan,
                'path'  : path,
                'name'  : series_name,
                }

            series_list.append(series_data)

        self._add_series(series_list)

    def _add_series(self, series_list):
        for series in series_list:
            self.series_list.create_items(series)

        self.series_frame.set_has_changes('load', True)

    def _on_remove_series(self, evt):
        self.series_list.remove_selected_items()
        self.series_list.renumber_items()
        self.update_series_info(None, False)

        self.series_frame.set_has_changes('load', True)

    def _on_move_up_series(self, evt):
        self.series_list.move_selected_items_up()
        self.series_list.renumber_items()

        self.series_frame.set_has_changes('load', True)

    def _on_move_down_series(self, evt):
        self.series_list.move_selected_items_down()
        self.series_list.renumber_items()

        self.series_frame.set_has_changes('load', True)

    def update_series_info(self, series_data, selected):
        if selected:
            flist = [os.path.basename(f) for f in series_data['files']]
            self.info_name.SetLabel(series_data['name'])
            self.info_num_profiles.SetLabel(str(len(series_data['files'])))
            self.info_path.SetLabel(series_data['path'])
            self.series_file_list.set_files(flist)
        else:
            self.info_name.SetLabel('')
            self.info_num_profiles.SetLabel('')
            self.info_path.SetLabel('')
            self.series_file_list.set_files([])

        self.Layout()
        self.series_file_list.SetVirtualSize(self.series_file_list.GetBestVirtualSize())

    def on_page_selected(self):
        pass

    def get_series_data(self):
        return self.series_list.get_all_item_data()

    def on_close(self):
        pass

class SeriesItemList(RAWCustomCtrl.ItemList):

    def __init__(self, load_panel, *args, **kwargs):
        self.load_panel = load_panel

        RAWCustomCtrl.ItemList.__init__(self, *args, **kwargs)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _create_toolbar(self):
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        toolbar_sizer.AddStretchSpacer(1)

        return toolbar_sizer

    def create_items(self, series_data):
        item = SeriesItem(self.load_panel, series_data, self, self.list_panel)
        self.add_items([item])

        return item

    def add_items(self, items):
        for item in items:
            self.list_panel_sizer.Add(item, flag=wx.EXPAND)
            self.all_items.append(item)

            series_num = len(self.all_items)
            item.set_series_num(series_num)

        self.resize_list()

    def renumber_items(self):
        for i, item in enumerate(self.all_items):
            item.set_series_num(i+1)

    def get_all_item_data(self):
        item_data = [item.series_data for item in self.all_items]

        return item_data

class SeriesItem(RAWCustomCtrl.ListItem):

    def __init__(self, series_panel, series_data, *args, **kwargs):
        self.series_panel = series_panel
        self.series_data = series_data

        RAWCustomCtrl.ListItem.__init__(self, *args, **kwargs)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _create_layout(self):

        self.series_num = wx.StaticText(self, label='', size=self._FromDIP((35, -1)),
            style=wx.ST_NO_AUTORESIZE)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.series_num, border=self._FromDIP(5), flag=wx.LEFT
            |wx.ALIGN_CENTER_VERTICAL)
        top_sizer.Add(wx.StaticText(self, label=self.series_data['name']),
            border=self._FromDIP(5), flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        top_sizer.AddStretchSpacer(1)

        self.SetSizer(top_sizer)

    def set_series_num(self, num):
        self.series_num.SetLabel(str(num))

    def set_selected(self, selected, update=True):
        self._selected = selected

        if self._selected:

            self.SetBackgroundColour(self.bkg_color)

            for text_item in self.text_list:
                text_item.SetForegroundColour(self.text_color)

        else:
            self.SetBackgroundColour(RAWGlobals.list_bkg_color)
            for text_item in self.text_list:
                text_item.SetForegroundColour(RAWGlobals.general_text_color)

        if update:
            self.Refresh()
            self.series_panel.update_series_info(self.series_data, selected)

class SeriesFileList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, *args, **kwargs):
        wx.ListCtrl.__init__(self, *args, style=wx.LC_REPORT|wx.LC_VIRTUAL, **kwargs)

        self.AppendColumn('Files')
        self.file_list = []
        self.SetItemCount(len(self.file_list))

        self.SetMinSize(self._FromDIP((200,-1)))

        listmix.ListCtrlAutoWidthMixin.__init__(self)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def set_files(self, file_list):
        self.file_list = file_list
        self.SetItemCount(len(self.file_list))

    def OnGetItemText(self, item, column):
        return self.file_list[item]


class MultiSeriesRangePanel(wx.ScrolledWindow):

    def __init__(self, series_frame, parent):

        wx.ScrolledWindow.__init__(self, parent,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER|wx.VSCROLL)
        self.SetScrollRate(20,20)

        self.series_frame = series_frame

        self.executor = None

        if platform.system() == 'Darwin' and RAWGlobals.frozen:
            self.single_proc = True
        else:
            self.single_proc = False

        self.load_futures = []
        self.loading_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_loading_timer, self.loading_timer)

        self.range = (0, 1)
        self.prop_cycle = matplotlib.rcParams['axes.prop_cycle']()

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        parent = self

        self.series_plot = RAWAnalysis.SeriesPlotPanel(parent, 'multi', 'MultiSeries')

        buffer_box = wx.StaticBox(parent, label='Buffer Range')

        self.buffer_range_list = RAWAnalysis.SeriesRangeItemList(self, 'buffer', buffer_box,
            list_type='MultiSeries')
        self.buffer_range_list.SetMinSize(self._FromDIP((150,130)))

        self.buffer_add_btn = wx.Button(buffer_box, label='Add region')
        self.buffer_add_btn.Bind(wx.EVT_BUTTON, self._onSeriesAdd)

        self.buffer_remove_btn = wx.Button(buffer_box, label='Remove region')
        self.buffer_remove_btn.Bind(wx.EVT_BUTTON, self._onSeriesRemove)

        buf_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        buf_btn_sizer.Add(self.buffer_add_btn, flag=wx.RIGHT, border=self._FromDIP(5))
        buf_btn_sizer.Add(self.buffer_remove_btn)

        buffer_sizer = wx.StaticBoxSizer(buffer_box, wx.VERTICAL)
        buffer_sizer.Add(self.buffer_range_list, proportion=1,
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=self._FromDIP(5))
        buffer_sizer.Add(buf_btn_sizer, flag=wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))


        sample_box = wx.StaticBox(parent, label='Sample Range')

        self.sample_range_list = RAWAnalysis.SeriesRangeItemList(self, 'sample', sample_box,
            list_type='MultiSeries')
        self.sample_range_list.SetMinSize(self._FromDIP((150,130)))

        self.sample_add_btn = wx.Button(sample_box, label='Add region')
        self.sample_add_btn.Bind(wx.EVT_BUTTON, self._onSeriesAdd)

        self.sample_remove_btn = wx.Button(sample_box, label='Remove region')
        self.sample_remove_btn.Bind(wx.EVT_BUTTON, self._onSeriesRemove)

        buf_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        buf_btn_sizer.Add(self.sample_add_btn, flag=wx.RIGHT, border=self._FromDIP(5))
        buf_btn_sizer.Add(self.sample_remove_btn)

        sample_sizer = wx.StaticBoxSizer(sample_box, wx.VERTICAL)
        sample_sizer.Add(self.sample_range_list, proportion=1,
            flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=self._FromDIP(5))
        sample_sizer.Add(buf_btn_sizer, flag=wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,
            border=self._FromDIP(5))


        baseline_box = wx.StaticBox(parent, label='Baseline Correction')
        self.baseline_cor = wx.Choice(baseline_box,
            choices=['None', 'Linear', 'Integral'])
        self.baseline_cor.SetStringSelection('None')
        self.baseline_cor.Bind(wx.EVT_CHOICE, self.onBaselineChange)

        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_sizer.Add(wx.StaticText(baseline_box, label='Baseline correction:'),
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(2))
        type_sizer.Add(self.baseline_cor, border=self._FromDIP(2),
            flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        type_sizer.AddStretchSpacer(1)

        r1_0 = self.range[0]
        r2_0 = self.range[0]
        r1_1 = self.range[1]
        r2_1 = self.range[1]


        self.bl_r1_start = RAWCustomCtrl.IntSpinCtrl(baseline_box,
            wx.ID_ANY, min_val=r1_0, max_val=r1_1, TextLength=45)
        self.bl_r1_end = RAWCustomCtrl.IntSpinCtrl(baseline_box,
            wx.ID_ANY, min_val=r1_1, max_val=self.range[1], TextLength=45)
        self.bl_r1_start.SetValue(r1_0)
        self.bl_r1_end.SetValue(self.range[1])
        self.bl_r1_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)
        self.bl_r1_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)

        self.bl_r2_start = RAWCustomCtrl.IntSpinCtrl(baseline_box,
            wx.ID_ANY, min_val=r2_0, max_val=r2_1, TextLength=45)
        self.bl_r2_end = RAWCustomCtrl.IntSpinCtrl(baseline_box,
            wx.ID_ANY, min_val=r2_1, max_val=self.range[1], TextLength=45)
        self.bl_r2_start.SetValue(r2_1)
        self.bl_r2_end.SetValue(self.range[1])
        self.bl_r2_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)
        self.bl_r2_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateBaselineRange)

        self.bl_r1_pick = wx.Button(baseline_box, label='Pick')
        self.bl_r2_pick = wx.Button(baseline_box, label='Pick')
        self.bl_r1_pick.Bind(wx.EVT_BUTTON, self.onBaselinePick)
        self.bl_r2_pick.Bind(wx.EVT_BUTTON, self.onBaselinePick)

        baseline_ctrl_sizer = wx.FlexGridSizer(rows=2, cols=5, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_box, label='Start:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r1_start, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_box, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r1_end, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r1_pick, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_box, label='End:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r2_start, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(wx.StaticText(baseline_box, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r2_end, flag=wx.ALIGN_CENTER_VERTICAL)
        baseline_ctrl_sizer.Add(self.bl_r2_pick, flag=wx.ALIGN_CENTER_VERTICAL)


        baseline_sizer = wx.StaticBoxSizer(baseline_box, wx.VERTICAL)
        baseline_sizer.Add(type_sizer, border=self._FromDIP(2), flag=wx.EXPAND
            |wx.ALL)
        baseline_sizer.Add(baseline_ctrl_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(2))


        range_ctrls = wx.BoxSizer(wx.HORIZONTAL)
        range_ctrls.Add(buffer_sizer, proportion=1)
        range_ctrls.Add(sample_sizer, flag=wx.LEFT, border=self._FromDIP(5),
            proportion=1)
        range_ctrls.Add(baseline_sizer, flag=wx.LEFT, border=self._FromDIP(5))


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.series_plot, proportion=1, flag=wx.EXPAND)
        top_sizer.Add(wx.StaticLine(self, style=wx.LI_HORIZONTAL), flag=wx.EXPAND)
        top_sizer.Add(range_ctrls, flag=wx.ALL|wx.EXPAND, border=self._FromDIP(5))

        self.SetSizer(top_sizer)

    def initialize(self):
        self.bl_r1_start.Disable()
        self.bl_r1_end.Disable()
        self.bl_r1_pick.Disable()
        self.bl_r2_start.Disable()
        self.bl_r2_end.Disable()
        self.bl_r2_pick.Disable()

    def on_page_selected(self):
        load_changes = self.series_frame.get_has_changes('load')

        if load_changes:
            self._load_data()
            self.series_frame.set_has_changes('load', False)

    def _load_data(self):
        self.series_frame.showBusy(True, 'Loading series data')
        self.load_series_data = self.series_frame.load_ctrl.get_series_data()

        self.sasm_list = []

        if self.single_proc:
            self.executor = ThreadPoolExecutor()
        else:
            self.executor = multiprocessing.Pool()

        self.series_futures = []

        for series_data in self.load_series_data:

            if self.single_proc:
                series_future = self.executor.submit(RAWAPI.load_profiles,
                    series_data['files'], self.series_frame.raw_settings)
            else:
                series_future = self.executor.apply_async(RAWAPI.load_profiles,
                    args=(series_data['files'], self.series_frame.raw_settings))
            self.series_futures.append(series_future)

        if not self.single_proc:
            self.executor.close()

        self.loading_timer.Start(1000)

    def _on_loading_timer(self, evt):
        if self.single_proc:
            load_finished = all([future.done() for future in self.series_futures])
        else:
            load_finished = all([future.ready() for future in self.series_futures])

        if load_finished:
            self.loading_timer.Stop()
            self.series_frame.showBusy(False)


            if self.single_proc:
                results = [future.result() for future in self.series_futures]
                self.executor.shutdown()
            else:
                results = [future.get() for future in self.series_futures]
                self.executor.join()

            for i, sasms in enumerate(results):
                series_data = self.load_series_data[i]
                self.sasm_list.append([sasms, series_data])

            self.series_frame.set_has_changes('range', True)

            self.plot_data()

    def plot_data(self):
        x_data = np.array(range(len(self.sasm_list)))+1
        y_data = np.array([np.array([sasm.getTotalI() for sasm in sasms]).sum()
            for sasms, _ in self.sasm_list])

        self.range = (x_data[0], x_data[-1])

        self.update_plot_data(x_data, y_data, 'total', 'left')

        r1_0 = x_data[0]

        if len(x_data) < 22:
            r1_1 = x_data[len(x_data)//2]
            r2_0 = x_data[min(len(x_data)//2+1, len(x_data)-1)]
        else:
            r1_1 = x_data[10]
            r2_0 = x_data[-11]

        self.bl_r1_start.SetRange((r1_0, r1_1))
        self.bl_r1_end.SetRange((r1_0, r2_0))
        self.bl_r2_start.SetRange((r1_1, x_data[-1]))
        self.bl_r2_end.SetRange((r2_0, x_data[-1]))

        self.bl_r1_start.SetValue(r1_0)
        self.bl_r1_end.SetValue(r1_1)
        self.bl_r2_start.SetValue(r2_0)
        self.bl_r2_end.SetValue(x_data[-1])



    def update_plot_data(self, xdata, ydata, label, axis):
        self.series_plot.plot_data(xdata, ydata, label, axis)

    def update_plot_range(self, start, end, index, color):
        self.series_plot.plot_range(start, end, index, color)

    def update_plot_label(self, label, axis):
        self.series_plot.plot_label(label, axis)

    def remove_plot_range(self, index):
        self.series_plot.remove_range(index)

    def remove_plot_data(self, index):
        self.series_plot.remove_data(index)

    def pick_plot_range(self, start_item, end_item, index, color):
        self.series_plot.pick_range(start_item, end_item, index, color)

    def show_plot_range(self, index, show):
        self.series_plot.show_range(index, show)

    def _onSeriesAdd(self, evt):
        """Called when the Add control buttion is used."""
        ctrl = evt.GetEventObject()
        if ctrl is self.buffer_add_btn:
            parent_list = self.buffer_range_list
        elif ctrl is self.sample_add_btn:
            parent_list = self.sample_range_list

        index, start, end, color = self._addSeriesRange(parent_list)
        self.update_plot_range(start, end, index, color)

    def _addSeriesRange(self, parent_list):
        range_item = parent_list.create_items()

        start, end = range_item.get_range()
        index = range_item.GetId()

        if parent_list == self.buffer_range_list:
            range_item.color = None
        elif parent_list == self.sample_range_list:
            range_item.color = '#CDA7D8'

        self.Layout()
        self.SendSizeEvent()

        self.series_frame.set_has_changes('range', True)

        return index, start, end, range_item.color

    def _onSeriesRemove(self, evt):
        """Called by the Remove control button, removes a control."""
        ctrl = evt.GetEventObject()
        if ctrl is self.buffer_remove_btn:
            parent_list = self.buffer_range_list
        elif ctrl is self.sample_remove_btn:
            parent_list = self.sample_range_list

        selected = parent_list.get_selected_items()

        while len(selected) > 0:
            item = selected[0]
            idx = item.GetId()

            self.remove_plot_range(idx)

            if len(selected) > 1:
                parent_list.remove_item(item, resize=False)
            else:
                parent_list.remove_item(item, resize=True)

        self.Layout()
        self.SendSizeEvent()

        self.series_frame.set_has_changes('range', True)

    def onSeriesPick(self, event):
        event_object = event.GetEventObject()
        event_item = event_object.GetParent()

        index = event_item.GetId()

        start_item = event_item.start_ctrl
        end_item = event_item.end_ctrl
        color = event_item.color

        wx.CallAfter(self.pick_plot_range, start_item, end_item, index, color)

    def setPickRange(self, index, pick_range, plot_type):
        pick_range.sort()

        if isinstance(index, str):
            if index == 'bl_start':
                start_ctrl = self.bl_r1_start
                end_ctrl = self.bl_r1_end
            else:
                start_ctrl = self.bl_r2_start
                end_ctrl = self.bl_r2_end

            color = None

        else:
            item = wx.FindWindowById(index)
            start_ctrl = item.start_ctrl
            end_ctrl = item.end_ctrl

            color = item.color

        current_start_range = start_ctrl.GetRange()
        current_end_range = end_ctrl.GetRange()

        new_start = max(pick_range[0], current_start_range[0])
        new_end = min(pick_range[1], current_end_range[1])

        start_ctrl.SetValue(new_start)
        end_ctrl.SetValue(new_end)

        start_ctrl.SetRange((current_start_range[0], new_end))

        current_end_range = end_ctrl.GetRange()
        end_ctrl.SetRange((new_start, current_end_range[1]))

        self.update_plot_range(new_start, new_end, index, color)

        if isinstance(index, str):

            r1_start = self.bl_r1_start.GetValue()
            r1_end = self.bl_r1_end.GetValue()
            r2_start = self.bl_r2_start.GetValue()
            r2_end = self.bl_r2_end.GetValue()

            r1_end_range = self.bl_r1_end.GetRange()

            new_r1_end_range = (r1_end_range[0], r2_start-1)
            self.bl_r1_end.SetRange(new_r1_end_range)

            r2_start_range = self.bl_r2_start.GetRange()
            new_r2_start_range = (r1_end+1, r2_start_range[1])
            self.bl_r2_start.SetRange(new_r2_start_range)


        self.series_frame.set_has_changes('range', True)

    def updateSeriesRange(self, event):
        event_object = event.GetEventObject()
        event_item = event_object.GetParent()
        value = event_object.GetValue()

        start, end = event_item.get_range()
        index = event_item.GetId()

        if event_object is event_item.start_ctrl:
            current_range = event_item.end_ctrl.GetRange()
            event_item.end_ctrl.SetRange((value, current_range[-1]))
        else:
            current_range = event_item.start_ctrl.GetRange()
            event_item.start_ctrl.SetRange((current_range[0], value))

        self.update_plot_range(start, end, index, event_item.color)

        self.series_frame.set_has_changes('range', True)

    def onBaselineChange(self, event):
        baseline = self.baseline_cor.GetStringSelection()

        if baseline == 'None':
            self.bl_r1_start.Disable()
            self.bl_r1_end.Disable()
            self.bl_r2_start.Disable()
            self.bl_r2_end.Disable()
            self.bl_r1_pick.Disable()
            self.bl_r2_pick.Disable()

            try:
                self.remove_plot_range('bl_start')
            except KeyError:
                pass
            try:
                self.remove_plot_range('bl_end')
            except KeyError:
                pass

        else:
            self.bl_r1_start.Enable()
            self.bl_r1_end.Enable()
            self.bl_r2_start.Enable()
            self.bl_r2_end.Enable()
            self.bl_r1_pick.Enable()
            self.bl_r2_pick.Enable()

            r1_start = self.bl_r1_start.GetValue()
            r1_end = self.bl_r1_end.GetValue()

            r2_start = self.bl_r2_start.GetValue()
            r2_end = self.bl_r2_end.GetValue()

            self.update_plot_range(r1_start, r1_end, 'bl_start', None)
            self.update_plot_range(r2_start, r2_end, 'bl_end', None)

        self.series_frame.set_has_changes('range', True)


    def updateBaselineRange(self, event):
        event_object = event.GetEventObject()
        value = event_object.GetValue()

        if event_object is self.bl_r1_start:
            current_range = self.bl_r1_end.GetRange()
            self.bl_r1_end.SetRange((value, current_range[-1]))

        elif event_object is self.bl_r1_end:
            current_range = self.bl_r1_start.GetRange()
            self.bl_r1_start.SetRange((current_range[0], value))

            r2_start_range = self.bl_r2_start.GetRange()
            self.bl_r2_start.SetRange((value+1, r2_start_range[1]))

        elif event_object is self.bl_r2_start:
            current_range = self.bl_r2_end.GetRange()
            self.bl_r2_end.SetRange((value, current_range[-1]))

            r1_end_range = self.bl_r1_end.GetRange()
            self.bl_r1_end.SetRange((r1_end_range[0], value-1))

        elif event_object is self.bl_r2_end:
            current_range = self.bl_r2_start.GetRange()
            self.bl_r2_start.SetRange((current_range[0], value))

        if event_object is self.bl_r1_start or event_object is self.bl_r1_end:
            start = self.bl_r1_start.GetValue()
            end = self.bl_r1_end.GetValue()
            index = 'bl_start'

        elif event_object is self.bl_r2_start or event_object is self.bl_r2_end:
            start = self.bl_r2_start.GetValue()
            end = self.bl_r2_end.GetValue()
            index = 'bl_end'

        self.update_plot_range(start, end, index, None)

        self.series_frame.set_has_changes('range', True)

    def onBaselinePick(self, event):
        event_object = event.GetEventObject()

        if event_object is self.bl_r1_pick:
            start_item = self.bl_r1_start
            end_item = self.bl_r1_end
            index = 'bl_start'

        elif event_object is self.bl_r2_pick:
            start_item = self.bl_r2_start
            end_item = self.bl_r2_end
            index = 'bl_end'

        wx.CallAfter(self.pick_plot_range, start_item, end_item, index, None)

        self.series_frame.set_has_changes('range', True)

    def on_close(self):
        self.loading_timer.Stop()

        if self.executor is not None:
            if self.single_proc:
                self.executor.shutdown(cancel_futures=True)
            else:
                self.executor.close()
                self.executor.terminate()
                self.executor.join()


class MultiSeriesProfilesPanel(wx.ScrolledWindow):

    def __init__(self, series_frame, parent):

        wx.ScrolledWindow.__init__(self, parent,
            style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER|wx.VSCROLL)
        self.SetScrollRate(20,20)

        self.series_frame = series_frame

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        # parent = self

        # top_sizer = wx.BoxSizer(wx.VERTICAL)
        # top_sizer.Add(load_box)
        # top_sizer.Add(series_top_sizer, proportion=1, flag=wx.EXPAND)

        # self.SetSizer(top_sizer)
        pass

    def on_page_selected(self):
        range_changes = self.series_frame.get_has_changes('range')

        if range_changes:
            self._process_data()
            self.series_frame.set_has_changes('range', False)

    def _process_data(self):
        pass

    def on_close(self):
        pass

