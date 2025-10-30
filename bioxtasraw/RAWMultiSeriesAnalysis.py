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

import os
import copy
import multiprocessing
import threading
import time
import platform
import traceback
import glob
from concurrent.futures import ThreadPoolExecutor
import json

import numpy as np
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.listctrl as listmix
import wx.lib.agw.supertooltip as STT
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
import bioxtasraw.SASFileIO as SASFileIO
import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.SASUtils as SASUtils
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
        self._initialize()

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

        self.simplebook = wx.Simplebook(panel)
        self.load_ctrl = MultiSeriesLoadPanel(self, self.simplebook)
        self.range_ctrl = MultiSeriesRangePanel(self, self.simplebook)
        self.profile_ctrl = MultiSeriesProfilesPanel(self, self.simplebook)

        self.simplebook.AddPage(self.load_ctrl, 'Load Series')
        self.simplebook.AddPage(self.range_ctrl, 'Select Ranges')
        self.simplebook.AddPage(self.profile_ctrl, 'Generate Profiles')

        self.simplebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)

        self.next_btn = wx.Button(panel, label='Next')
        self.back_btn = wx.Button(panel, label='Back')

        self.next_btn.Bind(wx.EVT_BUTTON, self._on_next_page)
        self.back_btn.Bind(wx.EVT_BUTTON, self._on_back_page)

        self.back_btn.Disable()

        cancel_btn = wx.Button(panel, label='Cancel')
        self.done_btn = wx.Button(panel, label='Done')

        cancel_btn.Bind(wx.EVT_BUTTON, self._on_cancel_btn)
        self.done_btn.Bind(wx.EVT_BUTTON, self._on_done_btn)

        self.done_btn.Disable()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(cancel_btn, flag=wx.RIGHT, border=self._FromDIP(5))
        btn_sizer.Add(self.done_btn)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(self.back_btn, flag=wx.RIGHT, border=self._FromDIP(5))
        btn_sizer.Add(self.next_btn)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.simplebook, proportion=1, flag=wx.EXPAND)
        panel_sizer.Add(btn_sizer, flag=wx.ALL|wx.EXPAND, border=self._FromDIP(5))
        panel.SetSizer(panel_sizer)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(top_sizer)

    def updateColors(self):
        pass

    def _initialize(self):
        if len(self.selected_series) > 0:
            series_list = []

            for secm in self.selected_series:

                series_data = {
                    'files' : secm.file_list,
                    'scan'  : '',
                    'path'  : '',
                    'name'  : secm.getParameter('filename'),
                    'series': secm
                    }

                series_list.append(series_data)

            self.load_ctrl._add_series(series_list)

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

    def _on_next_page(self, evt):
        cur_page = self.simplebook.GetSelection()

        if cur_page < 2:
            self.simplebook.SetSelection(cur_page+1)

        if cur_page == 1:
            self.next_btn.Disable()
            self.done_btn.Enable()

        self.back_btn.Enable()

    def _on_back_page(self, evt):
        cur_page = self.simplebook.GetSelection()

        if cur_page > 0:
            self.simplebook.SetSelection(cur_page-1)

        if cur_page == 1:
            self.back_btn.Disable()

        elif cur_page == 2:
            self.done_btn.Disable()

        self.next_btn.Enable()

    def _on_page_changed(self, evt):
        new_page_num = evt.GetSelection()
        new_page = self.simplebook.GetPage(new_page_num)
        new_page.on_page_selected()

    def get_multi_series_settings(self):
        load_settings = self.load_ctrl.get_settings()
        range_settings = self.range_ctrl.get_settings()
        prof_settings = self.profile_ctrl.get_settings()

        all_settings = load_settings
        all_settings.update(range_settings)
        all_settings.update(prof_settings)

        return all_settings

    def _on_cancel_btn(self, evt):
        self.OnClose()

    def _on_done_btn(self, evt):
        series = self.profile_ctrl.multi_series_results['series']

        settings = self.get_multi_series_settings()

        analysis_dict = series.getParameter('analysis')
        analysis_dict['multi_series'] = settings

        RAWGlobals.mainworker_cmd_queue.put(['to_plot_series', [series,
            None, None, True]])

        self.OnClose()

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

        load_box = wx.StaticBox(parent, label='Select series')

        other_box = wx.StaticBox(load_box, label='Other')

        auto_load_btn = wx.Button(other_box, label='Auto select')
        auto_load_btn.Bind(wx.EVT_BUTTON, self._on_auto_load)

        add_from_raw_btn = wx.Button(other_box, label='Add from series panel')
        add_from_raw_btn.Bind(wx.EVT_BUTTON, self._on_add_from_raw)

        other_btn_sizer = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_btn_sizer.Add(add_from_raw_btn, flag=wx.ALL, border=self._FromDIP(5))
        other_btn_sizer.Add(auto_load_btn, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))

        load_settings = wx.Button(load_box, label='Load analysis settings')
        load_settings.Bind(wx.EVT_BUTTON, self._on_load_settings)

        other_sizer = wx.BoxSizer(wx.VERTICAL)
        other_sizer.Add(other_btn_sizer)
        other_sizer.Add(load_settings, flag=wx.TOP, border=self._FromDIP(5))

        adv_load_box = wx.StaticBox(load_box, label='Select from disk')

        self.load_dir = wx.DirPickerCtrl(adv_load_box)
        self.load_fname = wx.TextCtrl(adv_load_box)

        self.scan_start = RAWCustomCtrl.IntSpinCtrl(adv_load_box, min_val=0,
            TextLength=60)
        self.scan_end = RAWCustomCtrl.IntSpinCtrl(adv_load_box, min_val=0,
            TextLength=60)
        self.scan_zpad = RAWCustomCtrl.IntSpinCtrl(adv_load_box, min_val=0,
            TextLength=60)
        self.fnum_start = RAWCustomCtrl.IntSpinCtrl(adv_load_box, min_val=0,
            TextLength=60)
        self.fnum_end = RAWCustomCtrl.IntSpinCtrl(adv_load_box, min_val=0,
            TextLength=60)
        self.fnum_zpad = RAWCustomCtrl.IntSpinCtrl(adv_load_box, min_val=0,
            TextLength=60)

        adv_load_sub_sizer = wx.FlexGridSizer(cols=6,  hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        adv_load_sub_sizer.Add(wx.StaticText(adv_load_box, label='Series # (<s>):'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(self.scan_start, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(wx.StaticText(adv_load_box, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(self.scan_end, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(wx.StaticText(adv_load_box, label='Zero pad:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(self.scan_zpad, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(wx.StaticText(adv_load_box, label='Profile # (<f>):'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(self.fnum_start, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(wx.StaticText(adv_load_box, label='to'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(self.fnum_end, flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(wx.StaticText(adv_load_box, label='Zero pad:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer.Add(self.fnum_zpad, flag=wx.ALIGN_CENTER_VERTICAL)

        adv_load_btn = wx.Button(adv_load_box, label='Select files')
        adv_load_btn.Bind(wx.EVT_BUTTON, self._on_load_files)

        adv_load_sub_sizer2 = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        adv_load_sub_sizer2.Add(wx.StaticText(adv_load_box, label='Directory:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer2.Add(self.load_dir, flag=wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        adv_load_sub_sizer2.Add(wx.StaticText(adv_load_box, label='Filename:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        adv_load_sub_sizer2.Add(self.load_fname, flag=wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        adv_load_sub_sizer2.AddGrowableCol(1)

        adv_load_sizer = wx.StaticBoxSizer(adv_load_box, wx.VERTICAL)
        adv_load_sizer.Add(adv_load_sub_sizer2, flag=wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        adv_load_sizer.Add(adv_load_sub_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        adv_load_sizer.Add(adv_load_btn, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|
            wx.ALIGN_CENTER_HORIZONTAL, border=self._FromDIP(5))

        load_sizer = wx.StaticBoxSizer(load_box, wx.HORIZONTAL)
        load_sizer.Add(adv_load_sizer, proportion=1, flag=wx.ALL,
            border=self._FromDIP(5))
        load_sizer.Add(other_sizer, flag=wx.RIGHT|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(5))


        self.series_list = SeriesItemList(self, parent, size=self._FromDIP((200,-1)))

        remove_series = wx.Button(parent, label='Remove')
        move_up_series = wx.Button(parent, label='Move up')
        move_down_series = wx.Button(parent, label='Move down')

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

        sub_sizer1 = wx.BoxSizer(wx.VERTICAL)
        sub_sizer1.Add(load_sizer, flag=wx.EXPAND)
        sub_sizer1.Add(series_info_sizer, flag=wx.EXPAND|wx.TOP,
            border=self._FromDIP(5), proportion=1)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(series_list_sizer, flag=wx.ALL|wx.EXPAND,
            border=self._FromDIP(5))
        top_sizer.Add(sub_sizer1, proportion=1, flag=wx.EXPAND|wx.TOP|wx.RIGHT|
            wx.BOTTOM, border=self._FromDIP(5))

        self.SetSizer(top_sizer)

    def _on_auto_load(self, evt):
        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        load_path = dirctrl_panel.getDirLabel()

        dialog = wx.FileDialog(self, message='Select a file',
            defaultDir=load_path, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        # Destroy the dialog
        dialog.Destroy()

        if file is not None:
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
                    'series': None
                    }

                series_list.append(series_data)

            self._add_series(series_list)

    def _on_load_files(self, evt):

        wx.CallAfter(self._select_files_from_disk)

    def _select_files_from_disk(self):

        self.series_frame.showBusy(msg='Searching for files')

        path = self.load_dir.GetPath()
        fname = self.load_fname.GetValue()

        snum_start = int(self.scan_start.GetValue())
        snum_end = int(self.scan_end.GetValue())
        snum_zpad = int(self.scan_zpad.GetValue())

        fnum_start = int(self.fnum_start.GetValue())
        fnum_end = int(self.fnum_end.GetValue())
        fnum_zpad = int(self.fnum_zpad.GetValue())

        if fname == '' or path == '':
            msg = ("Filename and path must not be blank")
            wx.CallAfter(self.series_frame.main_frame.showMessageDialog,
                self.series_frame, msg, "Finding files failed", wx.ICON_ERROR|wx.OK)

            self.series_frame.showBusy(False)

            return

        if '<s>' in fname:
            if snum_start < snum_end:
                snums = list(range(snum_start, snum_end+1))
            else:
                snums = list(range(snum_end, snum_start+1))
                snums = snums[::-1]
        else:
            snums =[]

        if '<f>' in fname:
            if fnum_start < fnum_end:
                fnums = list(range(fnum_start, fnum_end+1))
            else:
                fnums = list(range(fnum_end, fnum_start+1))
                fnums = fnums[::-1]
        else:
            fnums = []

        sname_list = []

        if len(snums) > 0:
            for snum in snums:
                cur_fname = fname.replace('<s>', '{:0{z}d}'.format(snum, z=snum_zpad))
                sname_list.append(cur_fname)

        else:
            sname_list.append(fname)

        if len(fnums) > 0:
            fname_list = []

            for sname in sname_list:
                fname_list.append([])
                for fnum in fnums:
                    cur_fname = sname.replace('<f>', '{:0{z}d}'.format(fnum, z=fnum_zpad))
                    fname_list[-1].append(cur_fname)

        else:
            fname_list = [[sname,] for sname in sname_list]

        series_name = fname.split('<s>')[0]
        if series_name == '':
            series_name = fname

        no_files = []
        series_list = []

        for i, series in enumerate(fname_list):
            flist = []
            for fname in series:
                if '?' or '*' in fname:
                    files = glob.glob(os.path.join(path, fname))
                elif os.path.exists(fname):
                    files = [fname]
                else:
                    files = []
                flist.extend(files)

            if len(files) > 0:
                series_data = {
                        'files' : flist,
                        'scan'  : snums[i],
                        'path'  : path,
                        'name'  : '{}{:0{z}d}'.format(series_name, snums[i], z=snum_zpad),
                        'series': None,
                        }

                series_list.append(series_data)

            else:
                if len(snums) > 0:
                    no_files.append(snums[i])

        self._add_series(series_list)

        self.series_frame.showBusy(False)

        if len(no_files) > 0:
            msg = ("Failed to find any files for the following series numbers: ")
            msg += ','.join(map(str, no_files))
            wx.CallAfter(self.series_frame.main_frame.showMessageDialog,
                self.series_frame, msg, "Finding files failed", wx.ICON_ERROR|wx.OK)
        elif len(series_list) == 0:
            msg = ("Failed to find any files ")
            msg += ', '.join(no_files)
            wx.CallAfter(self.series_frame.main_frame.showMessageDialog,
                self.series_frame, msg, "Finding files failed", wx.ICON_ERROR|wx.OK)

    def _on_add_from_raw(self, evt):
        wx.CallAfter(self._add_from_raw)

    def _add_from_raw(self):
        choices = [item.getSECM().getParameter('filename') for item
            in self.series_frame.main_frame.series_panel.all_manipulation_items]
        secm_list = [item.getSECM() for item
            in self.series_frame.main_frame.series_panel.all_manipulation_items]

        dialog = wx.MultiChoiceDialog(self.series_frame,
            'Select series to include in analysis', 'Select Series',
            choices)

        res = dialog.ShowModal()

        if res == wx.ID_OK:
            selection = dialog.GetSelections()
        else:
            selection = []

        series_list = []

        for index in selection:
            secm = secm_list[index]

            series_data = {
                'files' : secm.file_list,
                'scan'  : '',
                'path'  : '',
                'name'  : secm.getParameter('filename'),
                'series': secm
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

    def get_settings(self):
        series_data = self.get_series_data()

        input_series = []

        for sd in series_data:
            data = {
                'name'              : sd['name'],
                'scan'              : sd['scan'],
                'path'              : sd['path'],
                'number_of_files'   : len(sd['files']),
                }

            if sd['series'] is not None:
                data['loaded_from_raw'] = True
            else:
                data['loaded_from_raw'] = False

            input_series.append(data)

        settings = {
            'input_series'      : input_series,
            'load_path'         : self.load_dir.GetPath(),
            'load_filename'     : self.load_fname.GetValue(),
            'load_scan_start'   : self.scan_start.GetValue(),
            'load_scan_end'     : self.scan_end.GetValue(),
            'load_scan_zpad'    : self.scan_zpad.GetValue(),
            'load_fnum_start'   : self.fnum_start.GetValue(),
            'load_fnum_end'     : self.fnum_end.GetValue(),
            'load_fnum_zpad'    : self.fnum_zpad.GetValue(),
        }

        return settings

    def set_settings(self, settings):
        self.load_dir.SetPath(settings['load_path'])
        self.load_fname.SetValue(settings['load_filename'])
        self.scan_start.SetValue(settings['load_scan_start'])
        self.scan_end.SetValue(settings['load_scan_end'])
        self.scan_zpad.SetValue(settings['load_scan_zpad'])
        self.fnum_start.SetValue(settings['load_fnum_start'])
        self.fnum_end.SetValue(settings['load_fnum_end'])
        self.fnum_zpad.SetValue(settings['load_fnum_zpad'])

    def _on_load_settings(self, evt):
        dialog = wx.FileDialog(self, message='Select a file',
            style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        # Destroy the dialog
        dialog.Destroy()

        if file is not None:
            self.series_frame.showBusy(msg='Loading settings')
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    settings = f.read()
                settings = dict(json.loads(settings))
            except Exception:
                msg = ("Failed to load multi-series analysis settings.")
                wx.CallAfter(self.series_frame.main_frame.showMessageDialog,
                    self.series_frame, msg, "Load failed", wx.ICON_ERROR|wx.OK)
                settings = None

                traceback.print_exc()

            if settings is not None:
                self.set_settings(settings)
                self.series_frame.range_ctrl.set_settings(settings)
                self.series_frame.profile_ctrl.set_settings(settings)

            self.series_frame.showBusy(False)

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

        self._panel_loaded = False
        self._first_settings = None

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
            nproc = min(os.cpu_count(), 3)
            self.executor = multiprocessing.Pool(nproc)

        self.series_futures = []

        for series_data in self.load_series_data:
            if series_data['series'] is None:
                if self.single_proc:
                    series_future = self.executor.submit(RAWAPI.load_profiles,
                        series_data['files'], self.series_frame.raw_settings)
                else:
                    series_future = self.executor.apply_async(RAWAPI.load_profiles,
                        args=(series_data['files'], self.series_frame.raw_settings))
            else:
                series_future = DummyLoadFuture(series_data['series'])

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

            if not self._panel_loaded and self._first_settings is not None:
                self._update_settings(self._first_settings)

            self._panel_loaded = True

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

        self._set_baseline_range(event_object, value)

    def _set_baseline_range(self, event_object, value):
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
                bl_start_range = (self.bl_r1_start.GetValue()-1,
                    self.bl_r1_end.GetValue()-1)
                bl_end_range = (self.bl_r2_start.GetValue()-1,
                    self.bl_r2_end.GetValue()-1)

            else:
                bl_start_range = []
                bl_end_range = []

        else:
            baseline_valid = True
            bl_start_range = []
            bl_end_range = []

        for i in range(len(buffer_range_list)):
            br = buffer_range_list[i]
            buffer_range_list[i] = [br[0]-1, br[1]-1]

        for i in range(len(sample_range_list)):
            sr = sample_range_list[i]
            sample_range_list[i] = [sr[0]-1, sr[1]-1]

        return (self.sasm_list, buffer_valid, buffer_range_list, sample_valid,
            sample_range_list, baseline_valid, bl_type, bl_start_range,
            bl_end_range)

    def get_settings(self):
        (series_data, buffer_valid, buffer_range_list, sample_valid,
            sample_range_list, baseline_valid, bl_type, bl_start_range,
            bl_end_range) = self.get_ranges_and_data()

        settings = {
            'buffer_range'          : buffer_range_list,
            'sample_range'          : sample_range_list,
            'baseline_type'         : bl_type,
            'baseline_start_range'  : bl_start_range,
            'baseline_end_range'    : bl_end_range
        }
        return settings

    def set_settings(self, settings):
        if not self._panel_loaded:
            self._first_settings = settings
        else:
            self._update_settings(settings)

    def _update_settings(self, settings):
        for item in self.buffer_range_list.get_items():
            idx = item.GetId()
            self.remove_plot_range(idx)

        self.buffer_range_list.clear_list()

        for item in self.sample_range_list.get_items():
            idx = item.GetId()
            self.remove_plot_range(idx)

        self.sample_range_list.clear_list()

        for item in settings['buffer_range']:
            index, _, _, color = self._addSeriesRange(self.buffer_range_list)
            self.setPickRange(index, [int(item[0])+1, int(item[1])+1], '')

        for item in settings['sample_range']:
            index, _, _, color = self._addSeriesRange(self.sample_range_list)
            self.setPickRange(index, [int(item[0])+1, int(item[1])+1], '')

        self.baseline_cor.SetStringSelection(settings['baseline_type'])

        if settings['baseline_type'].lower() != 'none':
            self.setPickRange('bl_start', settings['baseline_start_range'], '')
            self.setPickRange('bl_end', settings['baseline_end_range'], '')


    def on_close(self):
        self.loading_timer.Stop()

        if self.executor is not None:
            if self.single_proc:
                self.executor.shutdown(cancel_futures=True)
            else:
                self.executor.close()
                self.executor.terminate()
                self.executor.join()

class DummyLoadFuture(object):
    def __init__(self, series):
        self.series = series

    def done(self):
        return True

    def ready(self):
        return True

    def result(self):
        return self.series.getAllSASMs()

    def get(self):
        return self.series.getAllSASMs()

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
        self.param_vlines = []

        self._panel_loaded = False
        self._first_settings = None

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
        self.qbin_factor = RAWCustomCtrl.FloatSpinCtrl(q_box, initValue='10',
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

        load_cal_btn = wx.Button(cal_box, label='Load calibration')
        load_cal_btn.Bind(wx.EVT_BUTTON, self._on_load_cal)
        self.cal_file_label = wx.StaticText(cal_box)

        self.cal_x_key = wx.Choice(cal_box)
        self.cal_result_key = wx.TextCtrl(cal_box)
        self.cal_offset = wx.TextCtrl(cal_box, value='0',
            validator=RAWCustomCtrl.CharValidator('float_sci_neg'))
        self.cal_in_header = wx.CheckBox(cal_box, label='Calibration in header')

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
        cal_sizer.Add(self.cal_in_header, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))


        self.run_calcs = wx.Button(ctrl_box, label='Process data')
        self.run_calcs.Bind(wx.EVT_BUTTON, self._on_run_calcs)

        save_settings = wx.Button(ctrl_box, label='Save analysis settings')
        save_settings.Bind(wx.EVT_BUTTON, self._on_save_settings)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.run_calcs, flag=wx.RIGHT, border=self._FromDIP(5))
        btn_sizer.Add(save_settings)

        ctrl_box_sizer = wx.StaticBoxSizer(ctrl_box, wx.VERTICAL)
        ctrl_box_sizer.Add(cal_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5))
        ctrl_box_sizer.Add(q_sizer, flag=wx.ALL, border=self._FromDIP(5))
        ctrl_box_sizer.Add(series_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,
            border=self._FromDIP(5), proportion=1)
        ctrl_box_sizer.Add(btn_sizer, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|
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
        self.profile_canvas.mpl_connect('motion_notify_event',
            self._onMouseMotionEventProfile)

        self.profile_plot_index = RAWCustomCtrl.FloatSpinCtrlList(parent,
            TextLength=60, value_list=[0], sig_figs=4)
        self.profile_plot_index.Bind(RAWCustomCtrl.EVT_MY_SPIN,
            self._on_plot_index_change)
        self.plot_multiple_profiles = wx.CheckBox(parent, label='Plot multiple profiles')
        self.plot_multiple_profiles.SetValue(False)
        self.plot_multiple_profiles.Bind(wx.EVT_CHECKBOX, self._on_plot_multiple)
        self.plot_step = RAWCustomCtrl.IntSpinCtrl(parent, min_val=1, TextLength=60)
        self.plot_step.SetValue(5)
        self.plot_step.Bind(RAWCustomCtrl.EVT_MY_SPIN, self._on_plot_step_change)
        self.profile_plot_index_end = RAWCustomCtrl.FloatSpinCtrlList(parent,
            TextLength=60, value_list=[0], sig_figs=4)
        self.profile_plot_index_end.Bind(RAWCustomCtrl.EVT_MY_SPIN,
            self._on_plot_index_change)

        self.plot_step.Disable()
        self.profile_plot_index_end.Disable()

        profile_plot_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        profile_plot_sizer1.Add(wx.StaticText(parent, label='Plot profile:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        profile_plot_sizer1.Add(self.profile_plot_index, flag=wx.LEFT|
            wx.ALIGN_CENTER_VERTICAL, border=self._FromDIP(5))

        profile_plot_sizer2 = wx.FlexGridSizer(cols=2, hgap=self._FromDIP(5),
            vgap=self._FromDIP(5))
        profile_plot_sizer2.Add(wx.StaticText(parent, label='Plot every:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        profile_plot_sizer2.Add(self.plot_step, flag=wx.ALIGN_CENTER_VERTICAL)
        profile_plot_sizer2.Add(wx.StaticText(parent, label='Last profile:'),
            flag=wx.ALIGN_CENTER_VERTICAL)
        profile_plot_sizer2.Add(self.profile_plot_index_end,
            flag=wx.ALIGN_CENTER_VERTICAL)

        profile_sub_sizer2 = wx.BoxSizer(wx.VERTICAL)
        profile_sub_sizer2.Add(profile_plot_sizer1)
        profile_sub_sizer2.Add(self.plot_multiple_profiles, flag=wx.TOP,
            border=self._FromDIP(5))
        profile_sub_sizer2.Add(profile_plot_sizer2, flag=wx.TOP,
            border=self._FromDIP(5))

        profile_sizer = wx.BoxSizer(wx.HORIZONTAL)
        profile_sizer.Add(profile_sub_sizer2, flag=wx.RIGHT,
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

        self.background = self.param_canvas.copy_from_bbox(self.param_fig.bbox)

        self.redrawLines()

        self.param_cid = self.param_canvas.mpl_connect('draw_event',
            self.ax_redraw)
        self.profile_cid = self.profile_canvas.mpl_connect('draw_event',
            self.ax_redraw)

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

    def plot_series_data(self):
        rg = self.multi_series_results['rg']
        i0 = self.multi_series_results['i0']
        mwvc = self.multi_series_results['mwvc']
        mwvp = self.multi_series_results['mwvp']
        cal = self.multi_series_results['cal_vals']
        cal_label = self.multi_series_results['cal_save_key']
        used_frames = self.multi_series_results['used_frames']

        if len(cal) == 0:
            xdata = used_frames
            xlabel = 'Frames'
        else:
            xdata = cal
            xlabel = cal_label

        self.rg_plot.cla()
        self.i0_plot.cla()
        self.mw_plot.cla()

        color1 = matplotlib.color_sequences['Dark2'][0]
        color2 = matplotlib.color_sequences['Dark2'][5]

        self.rg_plot.plot(xdata, rg, 'o', color=color1)
        self.i0_plot.plot(xdata, i0, 'o', color=color1)
        self.mw_plot.plot(xdata, mwvc, 'o', label='Vc', color=color1)
        self.mw_plot.plot(xdata, mwvp, 'v', label='Vp', color=color2)

        sasm_list = self.multi_series_results['series'].getAllSASMs()

        self.param_vlines = []

        for j, sasm in enumerate(self.plotted_sasms):
            color = self.profile_plot.lines[j].get_color()
            index = sasm_list.index(sasm)

            line1 = self.rg_plot.axvline(xdata[index], color=color, animated=True)
            line2 = self.i0_plot.axvline(xdata[index], color=color, animated=True)
            line3 = self.mw_plot.axvline(xdata[index], color=color, animated=True)

            self.param_vlines.append([line1, line2, line3])

        self.mw_plot.legend()

        self.label_param_plots(xlabel)

        plot_scale = self.param_plot_scale
        self.param_plot_scale = ''

        self.updatePlot(plot_scale, 'param', False)


        self.param_canvas.mpl_disconnect(self.param_cid)

        self.param_fig.tight_layout(pad=1, h_pad=1)
        self.param_canvas.draw()

        self.background = self.param_canvas.copy_from_bbox(self.param_fig.bbox)

        self.redrawLines()

        self.param_cid = self.param_canvas.mpl_connect('draw_event',
            self.ax_redraw)

    def redrawLines(self):

        if len(self.param_vlines) != 0:
            self.param_canvas.restore_region(self.background)

            for lines in self.param_vlines:
                for line in lines:
                    self.param_fig.draw_artist(line)

            self.param_canvas.blit(self.param_fig.bbox)

    def plot_profile_data(self):
        if len(self.multi_series_results.keys()) > 0:
            self.profile_plot.cla()

            start_idx = self.profile_plot_index.GetIndex()
            end_idx = self.profile_plot_index_end.GetIndex()
            step = int(self.plot_step.GetValue())
            plot_multiple_profiles = self.plot_multiple_profiles.GetValue()

            if plot_multiple_profiles and start_idx != end_idx:
                idx_list = list(range(start_idx, end_idx+1, step))
            else:
                idx_list = [start_idx]

            series = self.multi_series_results['series']

            self.plotted_sasms = [series.getSASM(idx, 'sub') for idx in idx_list]

            for sasm in self.plotted_sasms:
                self.profile_plot.plot(sasm.getQ(), sasm.getI(), '-')

            plot_scale = self.profile_plot_scale
            self.profile_plot_scale = ''

            self.updatePlot(plot_scale, 'profile', False)

            self.label_profile_plot()

            self.profile_canvas.mpl_disconnect(self.profile_cid)

            self.profile_fig.tight_layout(pad=1, h_pad=1)
            self.profile_canvas.draw()

            self.profile_cid = self.profile_canvas.mpl_connect('draw_event',
                self.ax_redraw)


    def replot_series_lines(self):
        if len(self.plotted_sasms) == len(self.param_vlines):
            cal = self.multi_series_results['cal_vals']
            cal_label = self.multi_series_results['cal_save_key']
            used_frames = self.multi_series_results['used_frames']
            sasm_list = self.multi_series_results['series'].getAllSASMs()

            if len(cal) == 0:
                xdata = used_frames
            else:
                xdata = cal

            for j, sasm in enumerate(self.plotted_sasms):
                color = self.profile_plot.lines[j].get_color()
                index = sasm_list.index(sasm)

                for line in self.param_vlines[j]:
                    line.set_xdata([xdata[index],xdata[index]])
                    line.set_color(color)

            self.redrawLines()

        else:
            self.plot_series_data()

    def _on_plot_index_change(self, evt):
        if len(self.multi_series_results.keys()) > 0:
            plt_idx = self.profile_plot_index.GetIndex()

            end_range = self.profile_plot_index_end.GetRange()
            self.profile_plot_index_end.SetRange([plt_idx, end_range[1]])

            if plt_idx > self.profile_plot_index_end.GetIndex():
                self.profile_plot_index.SetIndex(min(plt_idx, end_range[1]))

            self.plot_profile_data()

            self.replot_series_lines()

    def _on_plot_step_change(self, evt):
        if len(self.multi_series_results.keys()) > 0:
            self.plot_profile_data()

            self.replot_series_lines()

    def _on_plot_multiple(self, evt):
        if self.plot_multiple_profiles.GetValue():
            self.plot_step.Enable()
            self.profile_plot_index_end.Enable()
        else:
            self.plot_step.Disable()
            self.profile_plot_index_end.Disable()

        if len(self.multi_series_results.keys()) > 0:
            self.plot_profile_data()

            self.replot_series_lines()

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

                if draw:

                    self.param_canvas.mpl_disconnect(self.param_cid)

                    self.param_fig.tight_layout(pad=1, h_pad=1)
                    self.param_canvas.draw()

                    self.background = self.param_canvas.copy_from_bbox(self.param_fig.bbox)

                    self.redrawLines()

                    self.param_cid = self.param_canvas.mpl_connect('draw_event',
                        self.ax_redraw)

        elif plot == 'profile':
            if plot_scale != self.profile_plot_scale:
                old_ps = copy.copy(self.profile_plot_scale)

                self.profile_plot_scale = plot_scale

                if self.profile_plot_scale == 'linlin':
                    for j, sasm in enumerate(self.plotted_sasms):
                        self.profile_plot.lines[j].set_ydata(sasm.getI())
                        self.profile_plot.lines[j].set_xdata(sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'loglin':
                    for j, sasm in enumerate(self.plotted_sasms):
                        self.profile_plot.lines[j].set_ydata(sasm.getI())
                        self.profile_plot.lines[j].set_xdata(sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('log')

                elif self.profile_plot_scale == 'loglog':
                    for j, sasm in enumerate(self.plotted_sasms):
                        self.profile_plot.lines[j].set_ydata(sasm.getI())
                        self.profile_plot.lines[j].set_xdata(sasm.getQ())
                    self.profile_plot.set_xscale('log')
                    self.profile_plot.set_yscale('log')

                elif self.profile_plot_scale == 'linlog':
                    for j, sasm in enumerate(self.plotted_sasms):
                        self.profile_plot.lines[j].set_ydata(sasm.getI())
                        self.profile_plot.lines[j].set_xdata(sasm.getQ())
                    self.profile_plot.set_xscale('log')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'kratky':
                    for j, sasm in enumerate(self.plotted_sasms):
                        y_val = sasm.getQ()**2*sasm.getI()
                        self.profile_plot.lines[j].set_ydata(y_val)
                        self.profile_plot.lines[j].set_xdata(sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'porod':
                    for j, sasm in enumerate(self.plotted_sasms):
                        y_val = sasm.getQ()**4*sasm.getI()
                        self.profile_plot.lines[j].set_ydata(y_val)
                        self.profile_plot.lines[j].set_xdata(sasm.getQ())
                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                elif self.profile_plot_scale == 'dimensionlesskratky':
                    sasm_list = self.multi_series_results['series'].getAllSASMs()
                    for j, sasm in enumerate(self.plotted_sasms):
                        index = sasm_list.index(sasm)

                        rg = self.multi_series_results['rg'][index]
                        i0 = self.multi_series_results['i0'][index]

                        if rg > 0:
                            y_val = (rg*sasm.getQ())**2*(sasm.getI()/i0)

                            self.profile_plot.lines[j].set_ydata(y_val)
                            self.profile_plot.lines[j].set_xdata(sasm.getQ())

                        else:
                            self.profile_plot.lines[j].set_ydata([])
                            self.profile_plot.lines[j].set_xdata([])

                    self.profile_plot.set_xscale('linear')
                    self.profile_plot.set_yscale('linear')

                if (old_ps == 'kratky' or old_ps == 'porod'
                    or old_ps == 'dimensionlesskratky'):
                    self.autoscale_plot(self.profile_canvas, draw=False)
                else:
                    if (plot_scale == 'kratky' or plot_scale == 'porod'
                        or plot_scale == 'dimensionlesskratky'):
                        self.autoscale_plot(self.profile_canvas, draw=False)

                self.label_profile_plot()

                if draw:
                    self.profile_canvas.mpl_disconnect(self.profile_cid)

                    self.profile_fig.tight_layout(pad=1, h_pad=1)
                    self.profile_canvas.draw()

                    self.profile_cid = self.profile_canvas.mpl_connect('draw_event',
                        self.ax_redraw)


    def autoscale_plot(self, canvas=None, draw=True):
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

        if draw:
            self.ax_redraw()

    def _exportData(self):
        if len(self.multi_series_results.keys()) > 0:
            header = 'Frame,'
            data_list = [self.multi_series_results['used_frames']]

            if len(self.multi_series_results['cal_vals']) > 0:
                xkey = self.multi_series_results['cal_save_key'].replace(' ', '_')
                xdata = self.multi_series_results['cal_vals']

                header +='{},'.format(xkey)
                data_list.append(xdata)



            header += 'Rg,Rg_Err,I0,I0_Err,Vc_MW,Vp_MW'.format(xkey)
            data_list.extend([self.multi_series_results['rg'],
                self.multi_series_results['rger'], self.multi_series_results['i0'],
                self.multi_series_results['i0er'], self.multi_series_results['mwvc'],
                self.multi_series_results['mwvp'],])

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

                    if x < 1e-4:
                        x_val = '{:.2e}'.format(x)
                    else:
                        x_val = round(x,5)

                    _, idx = SASUtils.find_closest(x,
                        self.multi_series_results['cal_vals'])
                    frame_num = self.multi_series_results['used_frames'][idx]

                else:
                    xlabel = 'Frame'
                    x_val = int(x+0.5)
            else:
                xlabel = 'Frame'
                x_val = int(x+0.5)

            if y < 1e-1:
                y_val = '{:.2e}'.format(y)
            else:
                y_val = round(y, 2)

            if xlabel == 'Frame':
                self.param_toolbar.set_status('{}: {}, {}: {}'.format(xlabel,
                    x_val, ylabel, y_val))
            else:
                self.param_toolbar.set_status('{}: {}, {}: {}, {}: {}'.format(
                    'Frame', frame_num, xlabel, x_val, ylabel, y_val))

        else:
            self.param_toolbar.set_status('')

    def _onMouseMotionEventProfile(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata

            if x < 1e-4:
                x_val = '{:.2e}'.format(x)
            else:
                x_val = round(x,5)

            if y < 1e-4:
                y_val = '{:.2e}'.format(y)
            else:
                y_val = round(y,5)

            ylabel = self.profile_plot.get_ylabel()

            ylabel = ylabel.replace('$', '')

            self.profile_toolbar.set_status('{}: {}, {}: {}'.format('q',
                x_val, ylabel, y_val))

        else:
            self.profile_toolbar.set_status('')

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
        wx.CallAfter(self._process_data)

    def _on_save_settings(self, evt):
        dialog = wx.FileDialog(self.series_frame,
            message='Please select save directory and enter save file name',
            wildcard='*.json', style=wx.FD_SAVE)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
        else:
            file = None

        dialog.Destroy()

        if file is not None:
            file=os.path.splitext(file)[0]+'.json'

            settings = self.series_frame.get_multi_series_settings()
            settings['cal_data'] = self.calc_args['cal_data']
            settings['cal_file'] = self._cal_file

            with open(file, 'w', encoding='utf-8') as f:
                settings_str = json.dumps(settings, indent=4,
                    cls=SASUtils.MyEncoder, ensure_ascii=False)

                f.write(settings_str)

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

                if float(self.profile_plot_index_end.GetValue()) == 0:
                    self.profile_plot_index_end.SetValueList(list(range(len(series_data[0][0]))))
                    self.profile_plot_index_end.SetRange([1, len(series_data[0][0])-1])
                    self.profile_plot_index_end.SetValue(len(series_data[0][0])-1)

                if not self._panel_loaded and self._first_settings is not None:
                    self._update_settings(self._first_settings)

                self._panel_loaded = True

            wx.CallAfter(self._process_data)
            self.series_frame.set_has_changes('range', False)


    def _process_data(self):
        self.run_calcs.Disable()
        self.series_frame.showBusy(msg='Processing profiles')

        self.proc_thread = threading.Thread(target=self._inner_process_data)
        self.proc_thread.daemon = True
        self.proc_thread.start()

    def _inner_process_data(self):
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
                if len(exclude) > 0:
                    series_exclude_keys = [int(val) for val in exclude.split(',')]
                else:
                    series_exclude_keys = []
                bad_exclude_key = False
            except Exception:
                series_exclude_keys = []
                bad_exclude_key = True

            cal_val_key = self.cal_x_key.GetStringSelection()
            cal_save_key = self.cal_result_key.GetValue()
            cal_offset = self.cal_offset.GetValue()
            cal_in_header = self.cal_in_header.GetValue()

            if not cal_in_header:
                try:
                    cal_offset = float(cal_offset)
                    bad_cal_offset= False
                except Exception:
                    cal_offset = ''
                    bad_cal_offset = True

                if (cal_val_key != '' and cal_save_key != '' and cal_offset != ''
                    and self._cal_x is not None and self._cal_y is not None):
                    cal_data = [cal_val_key, cal_save_key, cal_offset, self._cal_x,
                        self._cal_y]
                else:
                    cal_data = []
            else:
                cal_data = []
                cal_save_key = cal_val_key
                bad_cal_offset = False


            if cal_val_key != '':
                series_bin_keys = [cal_val_key]
            else:
                series_bin_keys = []

            if bad_exclude_key or bad_cal_offset:
                msg = ('The multi-series processing settings have the '
                    'following errors:\n')
                if bad_exclude_key:
                    msg += ('- The excluded profiles list could not be '
                        'processed as a list of integers.\n')
                if bad_cal_offset:
                    msg += ('- The calibration offset is not a number.\n')

                wx.CallAfter(self.series_frame.main_frame.showMessageDialog,
                    self.series_frame, msg,
                    "Multi-series processing settings invalid",
                    wx.ICON_ERROR|wx.OK)

                return

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

            self._additional_calc_settings = {
                'cal_in_header' : cal_in_header,
                'qbin_mode'    : qbin_mode,
            }

            (sub_series, rg, rger, i0, i0er, vcmw, vcmwer, vpmw,
                cal_vals) = RAWAPI.multi_series_calc(self.series_sasm_list,
                sample_range_list, buffer_range_list, **self.calc_args)

            if cal_in_header:
                cal_vals = np.array([sasm.getParameter('counters')[cal_save_key]
                    for sasm in sub_series.getAllSASMs('sub')])

            # Set the naming if it seems reasonable
            series_load_data = self.series_frame.load_ctrl.get_series_data()
            fnames = [d['name'] for d in series_load_data]
            prefix = os.path.commonprefix(fnames)

            if len(prefix) > 3: #This is just a weak guess/heuristic for what's enough overlap
                sub_series.setParameter('filename', prefix)


            all_frames = list(range(len(series_data[0][0])))

            if len(series_exclude_keys) > 0:
                series_exclude_keys.sort(reverse=True)

                for index in series_exclude_keys:
                    if index < len(all_frames):
                        del all_frames[index]

            if bin_series and series_rebin_factor != 1:
                used_frames = []
                for j in range(0, len(all_frames), series_rebin_factor):
                    used_frames.append(all_frames[j])
                used_frames = np.array(used_frames)
            else:
                used_frames = np.array(all_frames)

            self.multi_series_results = {
                'series'        : sub_series,
                'rg'            : rg,
                'rger'          : rger,
                'i0'            : i0,
                'i0er'          : i0er,
                'mwvc'          : vcmw,
                'mwvcer'        : vcmwer,
                'mwvp'          : vpmw,
                'cal_vals'      : cal_vals,
                'cal_save_key'  : cal_save_key,
                'used_frames'   : used_frames,
            }

            wx.CallAfter(self._update_processed_data)

    def _update_processed_data(self):
        self.series_frame.showBusy(False)

        self.proc_thread.join()

        if len(self.multi_series_results['cal_vals']) > 0:
            self.plot_index_list = [round(val, 4) for val in
                self.multi_series_results['cal_vals']]
        else:
            self.plot_index_list = self.multi_series_results['used_frames']

        self.profile_plot_index.SetValueList(self.plot_index_list)
        self.profile_plot_index.SetRange([0, len(self.plot_index_list)-1])

        prof_idx = self.profile_plot_index.GetIndex()

        self.profile_plot_index_end.SetValueList(self.plot_index_list)
        self.profile_plot_index_end.SetRange([prof_idx, len(self.plot_index_list)-1])

        self.plot_profile_data()
        self.plot_series_data()

        self.series_frame.set_has_changes('range', False)
        self.run_calcs.Enable()

    def get_settings(self):
        settings = {
            'set_qrange'            : self.calc_args['set_qrange'],
            'qrange'                : self.calc_args['qrange'],
            'bin_series'            : self.calc_args['bin_series'],
            'series_rebin_factor'   : self.calc_args['series_rebin_factor'],
            'do_q_rebin'            : self.calc_args['do_q_rebin'],
            'q_npts'                : self.calc_args['q_npts'],
            'q_rebin_factor'        : self.calc_args['q_rebin_factor'],
            'q_log_rebin'           : self.calc_args['q_log_rebin'],
            'q_bin_mode'            : self._additional_calc_settings['qbin_mode'],
            'window_size'           : self.calc_args['window_size'],
            'vc_protein'            : self.calc_args['vc_protein'],
            'series_exclude_keys'   : self.calc_args['series_exclude_keys'],
            'series_bin_keys'       : self.calc_args['series_bin_keys'],
            'cal_in_header'         : self._additional_calc_settings['cal_in_header'],
        }

        return settings

    def set_settings(self, settings):
        if not self._panel_loaded:
            self._first_settings = settings
        else:
            self._update_settings(settings)

    def _update_settings(self, settings):
        if settings['set_qrange']:
            self.q_range_end.SetValue(settings['qrange'][1])
            self._on_qrange_change(None)
            self.q_range_start.SetValue(settings['qrange'][0])
            self._on_qrange_change(None)

        self.do_series_bin.SetValue(settings['bin_series'])
        self.sbin_factor.SetValue(settings['series_rebin_factor'])
        self.do_qbin.SetValue(settings['do_q_rebin'])
        self.qbin_points.SetValue(settings['q_npts'])
        self.qbin_factor.SetValue(settings['q_rebin_factor'])
        self.qbin_mode.SetStringSelection(settings['q_bin_mode'])

        if settings['q_log_rebin']:
            self.qbin_type.SetStringSelection('Log')
        else:
            self.qbin_type.SetStringSelection('Linear')

        self.saver_window.SetValue(settings['window_size'])
        if settings['vc_protein']:
            self.series_vc_type.SetStringSelection('Protein')
        else:
            self.series_vc_type.SetStringSelection('RNA')

        exclude_keys = [str(val) for val in settings['series_exclude_keys']]
        self.series_exclude.SetValue(','.join(exclude_keys))

        self.cal_in_header.SetValue(settings['cal_in_header'])

        if len(settings['cal_data']) > 0:
            (cal_val_key, cal_save_key, cal_offset, self._cal_x,
                self._cal_y) = settings['cal_data']

            self.cal_x_key.SetStringSelection(cal_val_key)
            self.cal_result_key.SetValue(cal_save_key)
            self.cal_offset.SetValue(str(cal_offset))

            if settings['cal_file'] is not None:
                self._cal_file = settings['cal_file']

                self.cal_file_label.SetLabel(os.path.basename(self._cal_file))

                if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
                    file_tip = STT.SuperToolTip(" ", header = self._cal_file, footer = "") #Need a non-empty header or you get an error in the library on mac with wx version 3.0.2.0
                    file_tip.SetTarget(self.cal_file_label)
                    file_tip.ApplyStyle('Blue Glass')

                else:
                    self.showitem_icon.SetToolTip(wx.ToolTip(self._cal_file))

        elif settings['cal_in_header'] and len(settings['series_bin_keys']) > 0:
            self.cal_x_key.SetStringSelection(settings['series_bin_keys'][0])

    def on_close(self):
        pass

