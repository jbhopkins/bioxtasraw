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
import wx.lib.agw.supertooltip as STT
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

        self.main_frame = wx.FindWindowByName('MainFrame')
        is_gtk3 = self.main_frame.is_gtk3

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
        self.profile_ctrl = MultiSeriesProfilesPanel(self, self.notebook)

        self.notebook.AddPage(self.load_ctrl, 'Load Series')
        self.notebook.AddPage(self.range_ctrl, 'Select Ranges')
        self.notebook.AddPage(self.profile_ctrl, 'Generate Profiles')

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

        #######
        # TODO
        # For loading, I think autoload is probably best by having users define a name
        # with a series and profile number token (e.g. <s> and <p>), then define
        # The number of zero padding and range fo each of those. RAW then generate
        # the set of all possible filenames and loads them if they exist.
        # I can't think of an easy way to get existing file numbers, since it's
        # Unclear of how to split it and do the search in the folder. Maybe
        # I'll have a brainwave.

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

    def _validateSampleRange(self):
        valid = True

        sample_items = self.sample_range_list.get_items()

        if len(sample_items) == 0:
            valid = False
            msg = ("You must specify at least one sample range.")
        else:
            sample_range_list = [item.get_range() for item in sample_items]

            for i in range(len(sample_range_list)):
                start, end = sample_range_list[i]

                for j in range(len(sample_range_list)):
                    if j != i:
                        jstart, jend = sample_range_list[j]
                        if jstart < start and start < jend:
                            valid = False
                        elif jstart < end and end < jend:
                            valid = False
                        elif jstart == start and jend == end:
                            valid = False

                    if not valid:
                        break

                if not valid:
                    break

            msg = ("Sample ranges should be non-overlapping.")

        if not valid:
            wx.CallAfter(self.series_frame.main_frame.showMessageDialog, self.series_frame, msg,
                "Sample range invalid", wx.ICON_ERROR|wx.OK)

        return valid

    def _validateBufferRange(self):
        valid = True

        buffer_items = self.buffer_range_list.get_items()
        buffer_range_list = [item.get_range() for item in buffer_items]

        for i in range(len(buffer_range_list)):
            start, end = buffer_range_list[i]

            for j in range(len(buffer_range_list)):
                if j != i:
                    jstart, jend = buffer_range_list[j]
                    if jstart < start and start < jend:
                        valid = False
                    elif jstart < end and end < jend:
                        valid = False
                    elif jstart == start and jend == end:
                        valid = False

                if not valid:
                    break

            if not valid:
                break

        msg = ("Buffer ranges should be non-overlapping.")

        if not valid:
            wx.CallAfter(self.series_frame.main_frame.showMessageDialog, self.series_frame, msg,
                "Buffer range invalid", wx.ICON_ERROR|wx.OK)

        return valid

    def _validateBaselineRange(self):
        valid = True

        r1 = (self.bl_r1_start.GetValue(), self.bl_r1_end.GetValue())
        r2 = (self.bl_r2_start.GetValue(), self.bl_r2_end.GetValue())

        if r1[1] >= r2[0]:
            valid = False
            msg = ('The end of the start region must be before the start of '
                'the end region.')

        if self.baseline_cor.GetStringSelection() == 'Integral':
            if r1[1]-r1[0] < 10 or r2[1]-r2[0] < 10:
                valid = False
                msg = ('For the integral method both regions must be at least '
                    '10 frames long.')

        if not valid:
            wx.CallAfter(self.series_frame.main_frame.showMessageDialog, self.series_frame,
                msg, "Baseline start/end range invalid", wx.ICON_ERROR|wx.OK)

        return valid

    def get_ranges_and_data(self):
        buffer_valid = self._validateBufferRange()

        if buffer_valid:
            buffer_items = self.buffer_range_list.get_items()
            buffer_range_list = [item.get_range() for item in buffer_items]
        else:
            buffer_range_list = []

        sample_valid = self._validateSampleRange()

        if sample_valid:
            sample_items = self.sample_range_list.get_items()
            sample_range_list = [item.get_range() for item in sample_items]
        else:
            sample_range_list = []

        bl_type = self.baseline_cor.GetStringSelection()

        if bl_type.lower() != 'none':
            baseline_valid = self._validateBaselineRange()

            if baseline_valid:
                bl_start_range = (self.bl_r1_start.GetValue(),
                    self.bl_r1_end.GetValue())
                bl_end_range = (self.bl_r2_start.GetValue(),
                    self.bl_r2_end.GetValue())

            else:
                bl_start_range = []
                bl_end_range = []

        else:
            baseline_valid = True
            bl_start_range = []
            bl_end_range = []

        return (self.sasm_list, buffer_valid, buffer_range_list, sample_valid,
            sample_range_list, baseline_valid, bl_type, bl_start_range,
            bl_end_range)

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

        self.series_data = []
        self.calc_args = {}
        self._cal_file = None
        self._cal_x = None
        self._cal_y = None
        self.multi_series_results = {}

        self.param_plot_scale = 'linlin'
        self.profile_plot_scale = 'loglin'

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        parent = self

        ctrl_box = wx.StaticBox(parent, label='Controls')

        q_box = wx.StaticBox(ctrl_box, label='Q controls')
        self.q_range_start = RAWCustomCtrl.FloatSpinCtrlList(q_box, TextLength=60,
            value_list=[0], sig_figs=5)
        self.q_range_end = RAWCustomCtrl.FloatSpinCtrlList(q_box, TextLength=60,
            value_list=[1], sig_figs=5)
        self.q_range_start.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_qrange_change)
        self.q_range_end.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_qrange_change)

        qrange_sizer = wx.BoxSizer(wx.HORIZONTAL)
        qrange_sizer.Add(wx.StaticText(q_box, label='Q range:'), flag=wx.RIGHT|
            wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))
        qrange_sizer.Add(self.q_range_start, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
            border=self._FromDIP(5))
        qrange_sizer.Add(wx.StaticText(q_box, label='to'), flag=wx.RIGHT|
            wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))
        qrange_sizer.Add(self.q_range_end, flag=wx.ALIGN_CENTER_VERTICAL)

        self.do_qbin = wx.CheckBox(q_box, label='Rebin q')
        self.do_qbin.SetValue(False)
        self.qbin_type = wx.Choice(q_box, choices=['Linear', 'Log'])
        self.qbin_type.SetSelection(1)
        self.qbin_mode = wx.Choice(q_box, choices=['Factor', 'Points'])
        self.qbin_mode.SetSelection(0)
        self.qbin_mode.Bind(wx.EVT_CHOICE, self._on_qbin_mode)
        self.qbin_factor = RAWCustomCtrl.FloatSpinCtrl(q_box, initValue='1',
            TextLength=60, never_negative=True)
        self.qbin_points = RAWCustomCtrl.IntSpinCtrl(q_box, min_val=1,
            TextLength=60)
        self.qbin_points.SetValue(100)
        self.qbin_points.Disable()

        qbin_sub_sizer = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        qbin_sub_sizer.Add(wx.StaticText(q_box, label='Q bin type:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(self.qbin_type, flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(wx.StaticText(q_box, label='Q bin mode:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(self.qbin_mode, flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(wx.StaticText(q_box, label='Q bin factor:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(self.qbin_factor, flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(wx.StaticText(q_box, label='Q bin points:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        qbin_sub_sizer.Add(self.qbin_points, flag=wx.ALIGN_CENTER_VERTICAL)

        qbin_sizer = wx.BoxSizer(wx.VERTICAL)
        qbin_sizer.Add(self.do_qbin, flag=wx.BOTTOM, border=self._FromDIP(5))
        qbin_sizer.Add(qbin_sub_sizer)


        q_sizer = wx.StaticBoxSizer(q_box, wx.VERTICAL)
        q_sizer.Add(qrange_sizer, flag=wx.ALL, border=self._FromDIP(5))
        q_sizer.Add(qbin_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))


        series_box = wx.StaticBox(ctrl_box, label='Series controls')

        self.do_series_bin = wx.CheckBox(series_box, label='Rebin series')
        self.do_series_bin.SetValue(0)
        self.sbin_factor = RAWCustomCtrl.IntSpinCtrl(series_box, min_val=1,
            TextLength=60)
        self.saver_window = RAWCustomCtrl.IntSpinCtrl(series_box, min_val=1,
            TextLength=60)
        self.series_vc_type = wx.Choice(series_box, choices=['Protein', 'RNA'])
        self.series_vc_type.SetSelection(0)
        self.series_exclude = wx.TextCtrl(series_box, style=wx.TE_MULTILINE|wx.TE_BESTWRAP)

        series_sub_sizer = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        series_sub_sizer.Add(wx.StaticText(series_box, label='Series bin factor:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        series_sub_sizer.Add(self.sbin_factor, flag=wx.ALIGN_CENTER_VERTICAL)
        series_sub_sizer.Add(wx.StaticText(series_box, label='Series average window:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        series_sub_sizer.Add(self.saver_window, flag=wx.ALIGN_CENTER_VERTICAL)
        series_sub_sizer.Add(wx.StaticText(series_box, label='Vc type:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        series_sub_sizer.Add(self.series_vc_type, flag=wx.ALIGN_CENTER_VERTICAL)

        series_sub_sizer2 = wx.BoxSizer(wx.VERTICAL)
        series_sub_sizer2.Add(wx.StaticText(series_box, label='Exclude Profiles:'))
        series_sub_sizer2.Add(self.series_exclude, proportion=1, flag=wx.EXPAND|wx.TOP,
            border=self._FromDIP(5))


        series_sizer = wx.StaticBoxSizer(series_box, wx.VERTICAL)
        series_sizer.Add(self.do_series_bin, flag=wx.ALL, border=self._FromDIP(5))
        series_sizer.Add(series_sub_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        series_sizer.Add(series_sub_sizer2, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5), proportion=1)


        cal_box = wx.StaticBox(ctrl_box, label='Calibration controls')

        load_cal_btn = wx.Button(cal_box, label='Load Calibration')
        load_cal_btn.Bind(wx.EVT_BUTTON, self._on_load_cal)
        self.cal_file_label = wx.StaticText(cal_box)

        self.cal_x_key = wx.Choice(cal_box)
        self.cal_result_key = wx.TextCtrl(cal_box)
        self.cal_offset = wx.TextCtrl(cal_box, value='0',
            validator=RAWCustomCtrl.CharValidator('float_sci_neg'))

        cal_sub_sizer = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        cal_sub_sizer.Add(wx.StaticText(cal_box, label='Calibration file:'))
        cal_sub_sizer.Add(self.cal_file_label)
        cal_sub_sizer.Add(wx.StaticText(cal_box, label='Cal. input key:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        cal_sub_sizer.Add(self.cal_x_key, flag=wx.ALIGN_CENTER_VERTICAL|
            wx.EXPAND)
        cal_sub_sizer.Add(wx.StaticText(cal_box, label='Cal. output key:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        cal_sub_sizer.Add(self.cal_result_key, flag=wx.ALIGN_CENTER_VERTICAL|
            wx.EXPAND)
        cal_sub_sizer.Add(wx.StaticText(cal_box, label='Cal. offset:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        cal_sub_sizer.Add(self.cal_offset, flag=wx.ALIGN_CENTER_VERTICAL|
            wx.EXPAND)
        cal_sub_sizer.AddGrowableCol(1)


        cal_sizer = wx.StaticBoxSizer(cal_box, wx.VERTICAL)
        cal_sizer.Add(load_cal_btn, flag=wx.ALL, border=self._FromDIP(5))
        cal_sizer.Add(cal_sub_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5))


        run_calcs = wx.Button(ctrl_box, label='Run calculations')
        run_calcs.Bind(wx.EVT_BUTTON, self._on_run_calcs)

        ctrl_box_sizer = wx.StaticBoxSizer(ctrl_box, wx.VERTICAL)
        ctrl_box_sizer.Add(cal_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5))
        ctrl_box_sizer.Add(q_sizer, flag=wx.ALL, border=self._FromDIP(5))
        ctrl_box_sizer.Add(series_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5), proportion=1)
        ctrl_box_sizer.Add(run_calcs, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|
            wx.ALIGN_CENTER_HORIZONTAL, border=self._FromDIP(5))

        plot_panel = self._make_plot_panel()

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(ctrl_box_sizer, flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(5))
        top_sizer.Add(plot_panel, proportion=1, flag=wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        self.SetSizer(top_sizer)

    def _make_plot_panel(self):
        parent = self

        self.param_fig = Figure((5,4), 75)
        self.rg_plot = self.param_fig.add_subplot(3,1,1)
        self.i0_plot = self.param_fig.add_subplot(3,1,2, sharex=self.rg_plot)
        self.mw_plot = self.param_fig.add_subplot(3,1,3, sharex=self.rg_plot)

        self.label_param_plots('Frames')

        self.param_canvas = FigureCanvasWxAgg(parent, -1, self.param_fig)
        self.param_toolbar = RAWCustomCtrl.CustomPlotToolbar(self,
            self.param_canvas)
        self.param_toolbar.Realize()

        param_sizer = wx.BoxSizer(wx.VERTICAL)
        param_sizer.Add(self.param_canvas, proportion=1, flag=wx.EXPAND)
        param_sizer.Add(self.param_toolbar, flag=wx.EXPAND)

        self.param_fig.tight_layout(pad=1, h_pad=1)

        self.param_canvas.draw()
        self.param_cid = self.param_canvas.mpl_connect('draw_event',
            self.ax_redraw)
        self.param_canvas.callbacks.connect('button_release_event',
            self._onMouseButtonReleaseEvent)
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        self.param_canvas.mpl_connect('motion_notify_event',
            self._onMouseMotionEvent)


        self.profile_fig = Figure((5,4), 75)
        self.profile_plot = self.profile_fig.add_subplot(1,1,1)

        self.label_profile_plot()

        self.profile_canvas = FigureCanvasWxAgg(parent, -1, self.profile_fig)
        self.profile_toolbar = RAWCustomCtrl.CustomPlotToolbar(self,
            self.profile_canvas)
        self.profile_toolbar.Realize()

        profile_sub_sizer = wx.BoxSizer(wx.VERTICAL)
        profile_sub_sizer.Add(self.profile_canvas, proportion=1, flag=wx.EXPAND)
        profile_sub_sizer.Add(self.profile_toolbar, flag=wx.EXPAND)

        self.profile_fig.tight_layout(pad=1, h_pad=1)

        self.profile_canvas.draw()
        self.profile_cid = self.profile_canvas.mpl_connect('draw_event',
            self.ax_redraw)
        self.profile_canvas.callbacks.connect('button_release_event',
            self._onMouseButtonReleaseEvent)
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)

        self.profile_plot_index = RAWCustomCtrl.FloatSpinCtrlList(parent,
            TextLength=60, value_list=[0], sig_figs=4)
        self.profile_plot_index.Bind(RAWCustomCtrl.EVT_MY_SPIN,
            self._on_plot_index_change)

        profile_sizer = wx.BoxSizer(wx.HORIZONTAL)
        profile_sizer.Add(self.profile_plot_index, flag=wx.RIGHT,
            border=self._FromDIP(5))
        profile_sizer.Add(profile_sub_sizer, flag=wx.EXPAND, proportion=1)


        plot_sizer = wx.BoxSizer(wx.VERTICAL)
        plot_sizer.Add(param_sizer, proportion=2, flag=wx.EXPAND)
        plot_sizer.Add(profile_sizer, proportion=1, flag=wx.EXPAND)

        return plot_sizer

    def ax_redraw(self, widget=None):
        ''' Redraw plots on window resize event '''

        self.param_canvas.mpl_disconnect(self.param_cid)
        self.profile_canvas.mpl_disconnect(self.profile_cid)

        self.param_fig.tight_layout(pad=1, h_pad=1)
        self.param_canvas.draw()

        self.profile_fig.tight_layout(pad=1, h_pad=1)
        self.profile_canvas.draw()

        self.profile_cid = self.profile_canvas.mpl_connect('draw_event', self.ax_redraw)

    def label_param_plots(self, cal_key):
        self.rg_plot.set_ylabel('Rg')
        self.rg_plot.tick_params('x', labelbottom=False)
        self.i0_plot.set_ylabel('I(0)')
        self.i0_plot.tick_params('x', labelbottom=False)
        self.mw_plot.set_ylabel('MW (kDa)')
        self.mw_plot.set_xlabel(cal_key)

    def label_profile_plot(self):
        if (self.profile_plot_scale != 'kratky'
            and self.profile_plot_scale != 'porod'
            and self.profile_plot_scale != 'dimensionlesskratky'):
            self.profile_plot.set_xlabel('q')
            self.profile_plot.set_ylabel('I(q)')
        elif self.profile_plot_scale == 'kratky':
            self.profile_plot.set_xlabel('q')
            self.profile_plot.set_ylabel('$q^2$I(q)')
        elif self.profile_plot_scale == 'porod':
            self.profile_plot.set_xlabel('q')
            self.profile_plot.set_ylabel('$q^4$I(q)')
        elif self.profile_plot_scale == 'dimensionlesskratky':
            self.profile_plot.set_xlabel('q$R_g$')
            self.profile_plot.set_ylabel('$(qR_g)^2$I(q)/(I(0)')


    def plot_series_data(self, rg, i0, mwvc, mwvp, cal, cal_label):
        if len(cal) == 0:
            xdata = range(len(rg))
            xlabel = 'Frames'
        else:
            xdata = cal
            xlabel = cal_label

        self.rg_plot.cla()
        self.i0_plot.cla()
        self.mw_plot.cla()

        self.rg_plot.plot(xdata, rg, 'o')
        self.i0_plot.plot(xdata, i0, 'o')
        self.mw_plot.plot(xdata, mwvc, 'o', label='Vc')
        self.mw_plot.plot(xdata, mwvp, 'o', label='Vp')

        self.mw_plot.legend()

        self.label_param_plots(xlabel)

        plot_scale = self.param_plot_scale
        self.param_plot_scale = ''

        self.updatePlot(plot_scale, 'param', False)

        self.ax_redraw()

    def plot_profile_data(self, sasm):
        self.profile_plot.cla()

        self.plotted_sasm = sasm

        self.profile_plot.plot(sasm.getQ(), sasm.getI(), '-')

        plot_scale = self.profile_plot_scale
        self.profile_plot_scale = ''

        self.updatePlot(plot_scale, 'profile', False)

        self.label_profile_plot()

        self.ax_redraw()

    def _on_plot_index_change(self, evt):
        if len(self.multi_series_results.keys()) > 0:
            plt_idx_val = float(self.profile_plot_index.GetValue())

            try:
                plt_idx = self.plot_index_list.index(plt_idx_val)
            except Exception:
                plot_idx_val = int(plot_idx_val)
                plt_idx = self.plot_index_list.index(plt_idx_val)

            self.plot_profile_data(self.multi_series_results['series'].getSASM(plt_idx, 'sub'))

    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''

        if event.button == 3:
            if float(matplotlib.__version__[:3]) >= 1.2:
                if self.param_toolbar.GetToolState(self.param_toolbar.wx_ids['Pan']) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, event)
                    else:
                        self._showPopupMenu(event)

            else:
                if self.param_toolbar.GetToolState(self.param_toolbar._NTB2_PAN) == False:
                    if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                        wx.CallAfter(self._showPopupMenu, event)
                    else:
                        self._showPopupMenu(event)

    def _showPopupMenu(self, event):
        menu = wx.Menu()

        if event.inaxes == self.profile_plot:

            axes_list = [
                (7, 'Lin-Lin'),
                (8, 'Log-Lin'),
                (9, 'Log-Log'),
                (10, 'Lin-Log'),
                (11, 'Kratky'),
                (12, 'Porod'),
                (13, 'Dimensionless Kratky')
                ]

            for key, label in axes_list:
                item = menu.AppendRadioItem(key, label)

                if (label.replace('-', '').replace(' ', '').lower() ==
                    self.profile_plot_scale):
                    item.Check(True)

            self.PopupMenu(menu)

        else:
            menu.Append(2, 'Export Data As CSV')

            axes_menu = wx.Menu()

            axes_list = [
                (3, 'Lin-Lin'),
                (4, 'Log-Lin'),
                (5, 'Log-Log'),
                (6, 'Lin-Log'),
                ]

            for key, label in axes_list:
                item = axes_menu.AppendRadioItem(key, label)

                if label.replace('-', '').lower() == self.param_plot_scale:
                    item.Check(True)

            menu.AppendSubMenu(axes_menu, 'Axes')

            self.PopupMenu(menu)

            menu.Destroy()

    def _onPopupMenuChoice(self, evt):
        my_id = evt.GetId()

        if my_id == 2:
            self._exportData()

        elif my_id == 3:
            self.updatePlot('linlin', 'param')
        elif my_id == 4:
            self.updatePlot('loglin', 'param')
        elif my_id == 5:
            self.updatePlot('loglog', 'param')
        elif my_id == 6:
            self.updatePlot('linlog', 'param')
        elif my_id == 7:
            self.updatePlot('linlin', 'profile')
        elif my_id == 8:
            self.updatePlot('loglin', 'profile')
        elif my_id == 9:
            self.updatePlot('loglog', 'profile')
        elif my_id == 10:
            self.updatePlot('linlog', 'profile')
        elif my_id == 11:
            self.updatePlot('kratky', 'profile')
        elif my_id == 12:
            self.updatePlot('porod', 'profile')
        elif my_id == 13:
            self.updatePlot('dimensionlesskratky', 'profile')


    def updatePlot(self, plot_scale, plot, draw=True):

        if plot == 'param':
            if plot_scale != self.param_plot_scale:
                self.param_plot_scale = plot_scale

                if self.param_plot_scale == 'linlin':
                    self.rg_plot.set_xscale('linear')
                    self.rg_plot.set_yscale('linear')
                    self.i0_plot.set_xscale('linear')
                    self.i0_plot.set_yscale('linear')
                    self.mw_plot.set_xscale('linear')
                    self.mw_plot.set_yscale('linear')

                elif self.param_plot_scale == 'loglin':
                    self.rg_plot.set_xscale('linear')
                    self.rg_plot.set_yscale('log')
                    self.i0_plot.set_xscale('linear')
                    self.i0_plot.set_yscale('log')
                    self.mw_plot.set_xscale('linear')
                    self.mw_plot.set_yscale('log')

                elif self.param_plot_scale == 'loglog':
                    self.rg_plot.set_xscale('log')
                    self.rg_plot.set_yscale('log')
                    self.i0_plot.set_xscale('log')
                    self.i0_plot.set_yscale('log')
                    self.mw_plot.set_xscale('log')
                    self.mw_plot.set_yscale('log')

                elif self.param_plot_scale == 'linlog':
                    self.rg_plot.set_xscale('log')
                    self.rg_plot.set_yscale('linear')
                    self.i0_plot.set_xscale('log')
                    self.i0_plot.set_yscale('linear')
                    self.mw_plot.set_xscale('log')
                    self.mw_plot.set_yscale('linear')

        elif plot == 'profile':
            if plot_scale != self.profile_plot_scale:
                # TODO
                # Need to check if dimensionless kratky plot is selected and possible !!!!!!!!!!!!!!!!!
                old_ps = copy.copy(self.profile_plot_scale)

                self.profile_plot_scale = plot_scale

                if self.profile_plot_scale == 'linlin':
                    self.profile_plot.lines[0].set_ydata(self.plotted_sasm.getI())
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'loglin':
                    self.profile_plot.lines[0].set_ydata(self.plotted_sasm.getI())
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('log')

                elif self.profile_plot_scale == 'loglog':
                    self.profile_plot.lines[0].set_ydata(self.plotted_sasm.getI())
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ())
                    self.profile_plot.set_xscale('log')
                    self.profile_plot.set_yscale('log')

                elif self.profile_plot_scale == 'linlog':
                    self.profile_plot.lines[0].set_ydata(self.plotted_sasm.getI())
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ())
                    self.profile_plot.set_xscale('log')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'kratky':
                    y_val = self.plotted_sasm.getQ()**2*self.plotted_sasm.getI()
                    self.profile_plot.lines[0].set_ydata(y_val)
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'porod':
                    y_val = self.plotted_sasm.getQ()**4*self.plotted_sasm.getI()
                    self.profile_plot.lines[0].set_ydata(y_val)
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'dimensionlesskratky':
                    sasm_list = self.multi_series_results['series'].getAllSASMs()
                    index = sasm_list.index(self.plotted_sasm)

                    rg = self.multi_series_results['rg'][index]
                    i0 = self.multi_series_results['i0'][index]

                    y_val = (rg*self.plotted_sasm.getQ())**2*(self.plotted_sasm.getI()/i0)
                    self.profile_plot.lines[0].set_ydata(y_val)
                    self.profile_plot.lines[0].set_xdata(self.plotted_sasm.getQ()*rg)
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                if (old_ps == 'kratky' or old_ps == 'porod'
                    or old_ps == 'dimensionlesskratky'):
                    self.autoscale_plot(self.profile_canvas)
                else:
                    if (plot_scale == 'kratky' or plot_scale == 'porod'
                        or plot_scale == 'dimensionlesskratky'):
                        self.autoscale_plot(self.profile_canvas)

                self.label_profile_plot()

        if draw:
            self.ax_redraw()


    def autoscale_plot(self, canvas=None):
        if canvas == self.param_canvas:
            self.rg_plot.set_autoscale_on(True)
            self.rg_plot.relim(True)
            self.rg_plot.autoscale_view()
            self.i0_plot.set_autoscale_on(True)
            self.i0_plot.relim(True)
            self.i0_plot.autoscale_view()
            self.mw_plot.set_autoscale_on(True)
            self.mw_plot.relim(True)
            self.mw_plot.autoscale_view()

        elif canvas == self.profile_canvas:
            self.profile_plot.set_autoscale_on(True)
            self.profile_plot.relim(True)
            self.profile_plot.autoscale_view()

        self.ax_redraw()

    def _exportData(self):
        if len(self.multi_series_results.keys()) > 0:
            if len(self.multi_series_results['cal_vals']) > 0:
                xkey = self.multi_series_results['cal_save_key'].replace(' ', '_')
                xdata = self.multi_series_results['cal_vals']
            else:
                xkey = 'Frames'
                xdata = np.array(range(len(self.multi_series_results['rg'])))

            header = '{},Rg,Rg_Err,I0,I0_Err,Vc_MW,Vp_MW'.format(xkey)
            data_list = [xdata, self.multi_series_results['rg'],
                self.multi_series_results['rger'], self.multi_series_results['i0'],
                self.multi_series_results['i0er'], self.multi_series_results['vcmw'],
                self.multi_series_results['vpmw'],]

            dialog = wx.FileDialog(self, message=("Please select save "
                "directory and enter save file name"), style = wx.FD_SAVE,
                defaultFile = 'multi_series_data.csv')

            if dialog.ShowModal() == wx.ID_OK:
                save_path = dialog.GetPath()
                name, ext = os.path.splitext(save_path)
                save_path = name + '.csv'
                dialog.Destroy()
            else:
                dialog.Destroy()
                return

            RAWGlobals.save_in_progress = True
            self.series_frame.main_frame.setStatus('Saving Multi-Series data', 0)

            SASFileIO.saveUnevenCSVFile(save_path, data_list, header)

            RAWGlobals.save_in_progress = False
            self.series_frame.main_frame.setStatus('', 0)

    def _onMouseMotionEvent(self, event):

        if event.inaxes == self.rg_plot:
            ylabel = 'Rg'
        elif event.inaxes == self.i0_plot:
            ylabel = 'I(0)'
        elif event.inaxes == self.mw_plot:
            ylabel = 'MW (kDa)'

        if event.inaxes:
            x, y = event.xdata, event.ydata

            if len(self.multi_series_results.keys()) > 0:
                if len(self.multi_series_results['cal_vals']) > 0:
                    xlabel = self.multi_series_results['cal_save_key']
                else:
                    xlabel = 'Frame'
                    x_val = int(x+0.5)
            else:
                xlabel = 'Frame'
                x_val = int(x+0.5)

            y_val = round(y, 2)

            self.param_toolbar.set_status('{}: {}, {}: {}'.format(xlabel, x_val,
                ylabel, y_val))

        else:
            self.param_toolbar.set_status('')

    def _on_qrange_change(self, evt):
        _, end = self.q_range_end.GetRange()
        self.q_range_start.SetRange((0, self.q_range_end.GetIndex()-1))
        self.q_range_end.SetRange((self.q_range_start.GetIndex()+1, end))

    def _on_qbin_mode(self, evt):
        if self.qbin_mode.GetStringSelection() == 'Factor':
            self.qbin_factor.Enable()
            self.qbin_points.Disable()
        elif self.qbin_mode.GetStringSelection() == 'Points':
            self.qbin_factor.Disable()
            self.qbin_points.Enable()

    def _on_run_calcs(self, evt):
        self._process_data()
        self.series_frame.set_has_changes('range', False)

    def _on_load_cal(self, evt):
        dialog = wx.FileDialog(self.series_frame, message='Select calibration file',
            wildcard='*.csv', style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        dialog.Destroy()

        if file is not None:
            self._cal_file = file
            self._load_cal_file()

    def _load_cal_file(self):
        if self._cal_file is not None:
            x, y = np.loadtxt(self._cal_file, delimiter=',',
                unpack=True)

            self._cal_x = x
            self._cal_y = y

            self.cal_file_label.SetLabel(os.path.basename(self._cal_file))

            if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                file_tip = STT.SuperToolTip(" ", header = self._cal_file, footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
                file_tip.SetTarget(self.cal_file_label)
                file_tip.ApplyStyle('Blue Glass')

            else:
                self.showitem_icon.SetToolTip(wx.ToolTip(self._cal_file))

    def on_page_selected(self):
        range_changes = self.series_frame.get_has_changes('range')

        if range_changes:
            (series_data, buffer_valid, buffer_range_list, sample_valid,
                sample_range_list, baseline_valid, bl_type, bl_start_range,
                bl_end_range) = self.series_frame.range_ctrl.get_ranges_and_data()

            if len(series_data) > 0:
                profile = series_data[0][0][0]
                qvals = profile.getQ()
                self.q_range_start.SetValueList(qvals)
                self.q_range_start.SetRange([0, len(qvals)-2])
                self.q_range_end.SetValueList(qvals)
                self.q_range_end.SetRange([1, len(qvals)-1])
                if self.q_range_end.GetIndex() == 0:
                    self.q_range_end.SetIndex(len(qvals)-1)
                self._on_qrange_change(None)

                header_keys = [''] + list(profile.getParameter('counters').keys())

                cal_key = self.cal_x_key.GetStringSelection()

                self.cal_x_key.Set(header_keys)

                if cal_key in header_keys:
                    self.cal_x_key.SetStringSelection(cal_key)
                else:
                    self.cal_x_key.SetSelection(0)

            self._process_data()
            self.series_frame.set_has_changes('range', False)


    def _process_data(self):
        (series_data, buffer_valid, buffer_range_list, sample_valid,
            sample_range_list, baseline_valid, bl_type, bl_start_range,
            bl_end_range) = self.series_frame.range_ctrl.get_ranges_and_data()

        if buffer_valid and sample_valid:
            profile = series_data[0][0][0]
            qvals = profile.getQ()

            if bl_type.lower() != 'none':
                do_baseline = True
            else:
                do_baseline = False

            self.series_sasm_list = []
            for data in series_data:
                self.series_sasm_list.append(data[0])

            qmin = float(self.q_range_start.GetValue())
            qmax = float(self.q_range_end.GetValue())
            if qmin != qvals[0] or qmax != qvals[-1]:
                set_qrange = True
                qrange = [qmin, qmax]
            else:
                set_qrange = False
                qrange = []

            bin_series = self.do_series_bin.GetValue()
            series_rebin_factor = int(self.sbin_factor.GetValue())

            do_q_rebin = self.do_qbin.GetValue()
            qbin_type = self.qbin_type.GetStringSelection()
            qbin_mode = self.qbin_mode.GetStringSelection()
            qbin_pts = int(self.qbin_points.GetValue())

            if qbin_mode == 'Points':
                qbin_factor = 1
            else:
                qbin_factor = float(self.qbin_factor.GetValue())

            if qbin_type == 'Log':
                q_log_bin = True
            else:
                q_log_bin = False

            window_size = int(self.saver_window.GetValue())
            vc_type = self.series_vc_type.GetStringSelection()

            if vc_type == 'Protein':
                vc_protein = True
            else:
                vc_protein = False

            exclude = self.series_exclude.GetValue()
            exclude.replace('\n', '')
            exclude.replace(' ', '')
            try:
                series_exclude_keys = [int(val) for val in exclude.split(',')]
            except Exception:
                series_exclude_keys = []

            # TODO
            # Raise a warning about bad settings here

            cal_val_key = self.cal_x_key.GetStringSelection()
            cal_save_key = self.cal_result_key.GetValue()
            cal_offset = self.cal_offset.GetValue()

            try:
                cal_offset = float(cal_offset)
            except Exception:
                cal_offset = ''

            if (cal_val_key != '' and cal_save_key != '' and cal_offset != ''
                and self._cal_x is not None and self._cal_y is not None):
                cal_data = [cal_val_key, cal_save_key, cal_offset, self._cal_x,
                    self._cal_y]
            else:
                cal_data = []

            if cal_val_key != '':
                series_bin_keys = [cal_val_key]
            else:
                series_bin_keys = []


            self.calc_args = {
                'do_baseline'           : do_baseline,
                'bl_start_range'        : bl_start_range,
                'bl_end_range'          : bl_end_range,
                'baseline_type'         : bl_type,
                'set_qrange'            : set_qrange,
                'qrange'                : qrange,
                'bin_series'            : bin_series,
                'series_rebin_factor'   : series_rebin_factor,
                'do_q_rebin'            : do_q_rebin,
                'q_npts'                : qbin_pts,
                'q_rebin_factor'        : qbin_factor,
                'q_log_rebin'           : q_log_bin,
                'window_size'           : window_size,
                'vc_protein'            : vc_protein,
                'cal_data'              : cal_data,
                'series_exclude_keys'   : series_exclude_keys,
                'series_bin_keys'       : series_bin_keys,

                'error_weight'  : self.series_frame.raw_settings.get('errorWeight'),
                'vp_cutoff'     : self.series_frame.raw_settings.get('MWVpCutoff'),
                'vp_density'    : self.series_frame.raw_settings.get('MWVpRho'),
                'vp_qmax'       : self.series_frame.raw_settings.get('MWVpQmax'),
                'vc_cutoff'     : self.series_frame.raw_settings.get('MWVcCutoff'),
                'vc_qmax'       : self.series_frame.raw_settings.get('MWVcQmax'),

            }

            # This might be slow?
            series_data = copy.deepcopy(self.series_sasm_list)

            (sub_series, rg, rger, i0, i0er, vcmw, vcmwer, vpmw,
                cal_vals) = RAWAPI.multi_series_calc( series_data,
                sample_range_list, buffer_range_list, **self.calc_args)

            ####### TODO:
            # Need to add messages about bad settings where necessary
            # Profile multi_series_calc and work on speeding it up

            self.multi_series_results = {
                'series'        : sub_series,
                'rg'            : rg,
                'rger'          : rger,
                'i0'            : i0,
                'i0er'          : i0er,
                'vcmw'          : vcmw,
                'vcmwer'        : vcmwer,
                'vpmw'          : vpmw,
                'cal_vals'      : cal_vals,
                'cal_save_key'  : cal_save_key,
            }

            if len(cal_vals) > 0:
                self.plot_index_list = [round(val, 4) for val in cal_vals]
            else:
                self.plot_index_list = [j for j in range(len(rg))]

            self.profile_plot_index.SetValueList(self.plot_index_list)
            self.profile_plot_index.SetRange([0, len(self.plot_index_list)-1])
            plt_idx_val = float(self.profile_plot_index.GetValue())

            try:
                plt_idx = self.plot_index_list.index(plt_idx_val)
            except Exception:
                plot_idx_val = int(plot_idx_val)
                plt_idx = self.plot_index_list.index(plt_idx_val)

            self.plot_series_data(rg, i0, vcmw, vpmw, cal_vals, cal_save_key)
            self.plot_profile_data(sub_series.getSASM(plt_idx, 'sub'))

            self.series_frame.set_has_changes('range', False)

    def on_close(self):
        pass

