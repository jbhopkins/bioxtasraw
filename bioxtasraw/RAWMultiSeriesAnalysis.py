'''
Created on Mar 23, 2010

@author: specuser

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

        self.notebook.AddPage(self.load_ctrl, 'Load Series')
        self.notebook.AddPage(self.range_ctrl, 'Select Ranges')

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

    def set_has_changes(self, panel, status):
        if panel == 'load':
            self.changes_load = status
        elif panel == 'range':
            self.changes_range = status

    def get_has_changes(self, panel):
        if panel == 'load':
            changes = self.changes_load
        elif panel == 'range':
            chagnes = self.changes_range

        return changes

    def OnCloseEvt(self, evt):
        self.OnClose()

    def OnClose(self):
        self.showBusy(show=False)

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

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        parent = self

        # load_box = wx.StaticBox(parent, label='Load series')

        # auto_load_btn = wx.Button(load_box, label='Auto Load')
        # auto_load_btn.Bind(wx.EVT_BUTTON, self._on_auto_load)

        # load_box = wx.StaticBoxSizer(load_box, wx.HORIZONTAL)
        # load_box.Add(auto_load_btn)

        # self.series_list = SeriesItemList(self, parent, size=self._FromDIP((200,-1)))

        # remove_series = wx.Button(parent, label='Remove')
        # move_up_series = wx.Button(parent, label='Move Up')
        # move_down_series = wx.Button(parent, label='Move Down')

        # remove_series.Bind(wx.EVT_BUTTON, self._on_remove_series)
        # move_up_series.Bind(wx.EVT_BUTTON, self._on_move_up_series)
        # move_down_series.Bind(wx.EVT_BUTTON, self._on_move_down_series)

        # series_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # series_btn_sizer.Add(move_up_series)
        # series_btn_sizer.Add(move_down_series, flag=wx.LEFT, border=self._FromDIP(5))
        # series_btn_sizer.Add(remove_series, flag=wx.LEFT, border=self._FromDIP(5))

        # series_list_sizer = wx.BoxSizer(wx.VERTICAL)
        # series_list_sizer.Add(self.series_list, flag=wx.EXPAND, proportion=1)
        # series_list_sizer.Add(series_btn_sizer, border=self._FromDIP(5),
        #     flag=wx.TOP|wx.ALIGN_CENTER_HORIZONTAL)

        # series_info_box = wx.StaticBox(parent, label='Series Info')

        # self.info_name = wx.StaticText(series_info_box, label='')
        # self.info_num_profiles = wx.StaticText(series_info_box, label='')
        # self.info_path = wx.StaticText(series_info_box, label='')

        # series_info_sub_sizer1 = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
        #     vgap=self._FromDIP(5))
        # series_info_sub_sizer1.Add(wx.StaticText(series_info_box, label='Series:'),
        #     flag=wx.ALIGN_CENTER_VERTICAL)
        # series_info_sub_sizer1.Add(self.info_name, flag=wx.ALIGN_CENTER_VERTICAL)
        # series_info_sub_sizer1.Add(wx.StaticText(series_info_box, label='Number of profiles:'),
        #     flag=wx.ALIGN_CENTER_VERTICAL)
        # series_info_sub_sizer1.Add(self.info_num_profiles, flag=wx.ALIGN_CENTER_VERTICAL)
        # series_info_sub_sizer1.Add(wx.StaticText(series_info_box, label='File path:'),
        #     flag=wx.ALIGN_CENTER_VERTICAL)
        # series_info_sub_sizer1.Add(self.info_path, flag=wx.ALIGN_CENTER_VERTICAL)

        # self.series_file_list = SeriesFileList(series_info_box)

        # series_info_sizer = wx.StaticBoxSizer(series_info_box, wx.VERTICAL)
        # series_info_sizer.Add(series_info_sub_sizer1, flag=wx.ALL,
        #     border=self._FromDIP(5))
        # series_info_sizer.Add(self.series_file_list, proportion=1,
        #     flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM)

        # series_top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # series_top_sizer.Add(series_list_sizer, flag=wx.EXPAND)
        # series_top_sizer.Add(series_info_sizer, flag=wx.EXPAND|wx.LEFT,
        #     border=self._FromDIP(5), proportion=1)


        # top_sizer = wx.BoxSizer(wx.VERTICAL)
        # top_sizer.Add(load_box)
        # top_sizer.Add(series_top_sizer, proportion=1, flag=wx.EXPAND)

        # self.SetSizer(top_sizer)


