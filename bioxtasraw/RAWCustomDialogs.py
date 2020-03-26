"""
Created on June 14, 2017

@author: Jesse B. Hopkins

#***********************************************************************
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
#***********************************************************************

The purpose of this module is to custom dialogs for RAW that may be used
in various other modules.
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import copy
import os
import json

import numpy as np
import wx
import wx.lib.dialogs
import wx.lib.colourchooser as colorchooser
import wx.lib.scrolledpanel
import wx.grid as gridlib
import matplotlib
import matplotlib.colors as mplcol
import matplotlib.font_manager as fm

try:
    import RAWCustomCtrl
    import RAWGlobals
except Exception:
    from . import RAWCustomCtrl
    from . import RAWGlobals


class SaveAnalysisInfoDialog(wx.Dialog):

    def __init__(self, parent, raw_settings, item_list = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Select variables to include in the comma separated file.', style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, size = (900,600), *args, **kwargs)

        self.raw_settings = raw_settings

        include_data = self.raw_settings.get('csvIncludeData')

        self.item_list = item_list
        self.panel = SaveAnalysisInfoPanel(self, item_list = item_list, include_data = include_data)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sizer.Add(self.panel,1, wx.ALL | wx.EXPAND, 10)
        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.sizer.Add(buttonsizer,0, wx.BOTTOM | wx.RIGHT | wx.LEFT | wx.ALIGN_RIGHT, 10)

        self.Bind(wx.EVT_BUTTON, self._onOk, id = wx.ID_OK)

        self.SetSizer(self.sizer)

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

    def _onOk(self, event):
        include_data = self.panel.getIncludeData()

        if len(include_data) > 0:

            save_path = self._showSaveDialog()
            if save_path is None:
                return

            data = [self.item_list, include_data, save_path]
            RAWGlobals.mainworker_cmd_queue.put(['save_analysis_info', data])
            #make the workerthread make a csv file.

        self.raw_settings.set('csvIncludeData', include_data)
        self.EndModal(wx.ID_OK)


    def _showSaveDialog(self):

        dirctrl_panel = wx.FindWindowByName('DirCtrlPanel')
        save_path = dirctrl_panel.getDirLabel()

        filters = 'Comma Separated Files (*.csv)|*.csv'

        dialog = wx.FileDialog( None, style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = save_path)

        if dialog.ShowModal() == wx.ID_OK:
            save_path = dialog.GetPath()
            return save_path
        else:
             return None


class SaveAnalysisInfoPanel(wx.Panel):

    def __init__(self, parent, item_list = None, include_data = None):
        wx.Panel.__init__(self, parent, name = 'SaveAnalysisInfoPanel')

        self.SetMinSize((600,600))

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
        self.include_listctrl.SetColumnWidth(0, 300)

        self._addGeneralVariables()
        self._addGuinierVariables()
        self._addMWVariables()
        self._addGNOMVariables()
        self._addBIFTVariables()
        self._addFileHdrVariables()
        self._addImageHdrVariables()

        self._updateIncludeList(include_data)

    def _onIncludeButton(self, event):
        selected_items = self.variable_listctrl.getSelectedItems()

        all_items = []

        for each_item in selected_items:
            data = copy.copy(self.variable_data[each_item])

            if data[1]is None:
                continue

            txt = self.variable_listctrl.GetItem(each_item).GetText()
            all_items.append(data)

            idx = self.include_listctrl.GetItemCount()
            if wx.version().split()[0].strip()[0] == '4':
                self.include_listctrl.InsertItem(idx, txt)
            else:
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

            if 'imageHeader' in each_sasm.getAllParameters():
               img_hdr = each_sasm.getParameter('imageHeader')
               keys = list(img_hdr.keys())
               all_keys.extend(keys)

        all_imghdr_keys.extend(set(all_keys))

        return all_imghdr_keys

    def _getAllFileHdrKeys(self):
        all_filehdr_keys = []

        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()

            if 'counters' in each_sasm.getAllParameters():
               img_hdr = each_sasm.getParameter('counters')
               keys = list(img_hdr.keys())
               all_keys.extend(keys)

        all_filehdr_keys.extend(set(all_keys))

        return all_filehdr_keys

    def _getAllGuinierKeys(self):
        all_guinier_keys = []

        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()

            if 'guinier' in each_sasm.getParameter('analysis'):
               analysis = each_sasm.getParameter('analysis')
               guinier = analysis['guinier']
               keys = list(guinier.keys())
               all_keys.extend(keys)

        all_guinier_keys.extend(set(all_keys))

        return all_guinier_keys

    def _getAllMWKeys(self):
        all_mw_keys = []

        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()

            if 'molecularWeight' in each_sasm.getParameter('analysis'):
                analysis = each_sasm.getParameter('analysis')
                mw = analysis['molecularWeight']
                key_list = []
                keys = list(mw.keys())
                for each_key in keys:
                    subkeys = list(mw[each_key].keys())
                    for each_subkey in subkeys:
                        key_list.append((each_key, each_subkey))

                all_keys.extend(key_list)

        all_mw_keys.extend(set(all_keys))

        return all_mw_keys


    def _getAllGNOMKeys(self):
        all_gnom_keys = []

        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()

            if 'GNOM' in each_sasm.getParameter('analysis'):
               analysis = each_sasm.getParameter('analysis')
               gnom = analysis['GNOM']
               keys = list(gnom.keys())
               all_keys.extend(keys)

        all_gnom_keys.extend(set(all_keys))

        return all_gnom_keys


    def _getAllBIFTKeys(self):
        all_gnom_keys = []

        all_keys = []
        for each_item in self.item_list:
            each_sasm = each_item.getSASM()

            if 'BIFT' in each_sasm.getParameter('analysis'):
               analysis = each_sasm.getParameter('analysis')
               gnom = analysis['BIFT']
               keys = list(gnom.keys())
               all_keys.extend(keys)

        all_gnom_keys.extend(set(all_keys))

        return all_gnom_keys


    def _addGeneralVariables(self):
        general_data = [('General', None), ('\tConcentration', 'Conc'), ('\tDescription / Notes', 'Notes'),
                        ('\tScale', 'scale'), ('\tOffset', 'offset')]

        idx = 0
        for each in general_data:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, each[0])
            else:
                self.variable_listctrl.InsertStringItem(idx, each[0])
            self.variable_data[idx] = ['general' , each[1], each[0]]

            idx = idx + 1

        self.variable_listctrl.SetItemBackgroundColour(0, 'GRAY')

    def _addGuinierVariables(self):
        keys = self._getAllGuinierKeys()

        if len(keys) == 0:
            return

        idx = self.variable_listctrl.GetItemCount()
        if wx.version().split()[0].strip()[0] == '4':
            self.variable_listctrl.InsertItem(idx, 'Guinier Analysis')
        else:
            self.variable_listctrl.InsertStringItem(idx, 'Guinier Analysis')
        self.variable_data[idx] = ['guinier', None]

        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, '\t'+each)
            else:
                self.variable_listctrl.InsertStringItem(idx, '\t'+each)
            self.variable_data[idx] = ['guinier', each, each]
            idx = idx + 1

    def _addMWVariables(self):
        keys = self._getAllMWKeys()

        # print keys

        if len(keys) == 0:
            return

        idx = self.variable_listctrl.GetItemCount()

        if wx.version().split()[0].strip()[0] == '4':
            self.variable_listctrl.InsertItem(idx, 'MW Analysis')
        else:
            self.variable_listctrl.InsertStringItem(idx, 'MW Analysis')
        self.variable_data[idx] = ['molecularWeight', None]

        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, '\t%s_%s' %(each[0], each[1]))
            else:
                self.variable_listctrl.InsertStringItem(idx, '\t%s_%s' %(each[0], each[1]))
            self.variable_data[idx] = ['molecularWeight', each[0], each[1]]
            idx = idx + 1


    def _addGNOMVariables(self):
        keys = self._getAllGNOMKeys()

        if len(keys) == 0:
            return

        idx = self.variable_listctrl.GetItemCount()

        if wx.version().split()[0].strip()[0] == '4':
            self.variable_listctrl.InsertItem(idx, 'GNOM Analysis')
        else:
            self.variable_listctrl.InsertStringItem(idx, 'GNOM Analysis')
        self.variable_data[idx] = ['GNOM', None]

        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, '\t'+each)
            else:
                self.variable_listctrl.InsertStringItem(idx, '\t'+each)
            self.variable_data[idx] = ['GNOM', each, each]
            idx = idx + 1

    def _addBIFTVariables(self):
        keys = self._getAllBIFTKeys()

        if len(keys) == 0:
            return

        idx = self.variable_listctrl.GetItemCount()

        if wx.version().split()[0].strip()[0] == '4':
            self.variable_listctrl.InsertItem(idx, 'BIFT Analysis')
        else:
            self.variable_listctrl.InsertStringItem(idx, 'BIFT Analysis')
        self.variable_data[idx] = ['BIFT', None]

        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, '\t'+each)
            else:
                self.variable_listctrl.InsertStringItem(idx, '\t'+each)
            self.variable_data[idx] = ['BIFT', each, each]
            idx = idx + 1

    def _addFileHdrVariables(self):
        keys = self._getAllFileHdrKeys()

        if len(keys) == 0:
            return

        idx = self.variable_listctrl.GetItemCount()

        if wx.version().split()[0].strip()[0] == '4':
            self.variable_listctrl.InsertItem(idx, 'Header File')
        else:
            self.variable_listctrl.InsertStringItem(idx, 'Header File')
        self.variable_data[idx] = ['Header File', None]
        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, '\t'+each)
            else:
                self.variable_listctrl.InsertStringItem(idx, '\t'+each)
            self.variable_data[idx] = ['counters', each, each]
            idx = idx + 1

    def _addImageHdrVariables(self):
        keys = self._getAllImageHdrKeys()

        if len(keys) == 0:
            return

        idx = self.variable_listctrl.GetItemCount()

        if wx.version().split()[0].strip()[0] == '4':
            self.variable_listctrl.InsertItem(idx, 'Image Header')
        else:
            self.variable_listctrl.InsertStringItem(idx, 'Image Header')
        self.variable_data[idx] = ['Image Header', None]
        self.variable_listctrl.SetItemBackgroundColour(idx, 'GRAY')
        idx = idx + 1
        for each in keys:
            if wx.version().split()[0].strip()[0] == '4':
                self.variable_listctrl.InsertItem(idx, '\t'+each)
            else:
                self.variable_listctrl.InsertStringItem(idx, '\t'+each)
            self.variable_data[idx] = ['imageHeader', each, each]
            idx = idx + 1

    def getIncludeData(self):
        return self.included_data

    def _updateIncludeList(self, include_data):
        if include_data is None:
            return

        for each in sorted(include_data.keys()):
            idx = self.include_listctrl.GetItemCount()
            if wx.version().split()[0].strip()[0] == '4':
                self.include_listctrl.InsertItem(idx, include_data[each][2])
            else:
                self.include_listctrl.InsertStringItem(idx, include_data[each][2])

            self.included_data[idx] = include_data[each]


class SaveAnalysisListCtrl(wx.ListCtrl):

    def __init__(self, parent, id, *args, **kwargs):

        wx.ListCtrl.__init__(self, parent, id, *args, **kwargs)
        self.populateList()

    def populateList(self):
        self.InsertColumn(0, 'Name')
        self.SetColumnWidth(0, 300)

    def add(self, expr):
        no_of_items = self.GetItemCount()
        if wx.version().split()[0].strip()[0] == '4':
            self.SetItem(no_of_items, 0, expr)
        else:
            self.SetStringItem(no_of_items, 0, expr)

    def moveItemUp(self, idx):
        if idx > 0:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            if wx.version().split()[0].strip()[0] == '4':
                self.InsertItem(idx-1, data[0])
                self.SetItem(idx-1, 1, data[1])
            else:
                self.InsertStringItem(idx-1, data[0])
                self.SetStringItem(idx-1, 1, data[1])
            self.Select(idx-1, True)

    def moveItemDown(self, idx):
        if idx < self.GetItemCount()-1:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            if wx.version().split()[0].strip()[0] == '4':
                self.InsertItem(idx+1, data[0])
                self.SetItem(idx+1, 1, data[1])
            else:
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

        if value_list is None:
            return

        for each in value_list:
            op = each[0]
            expr = each[1]
            self.add(op, expr)


class HdrDataDialog(wx.Dialog):

    def __init__(self, parent, sasm = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Header Data Display', style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.grid_changed = False
        self.sasm = sasm

        #For testing
        if self.sasm is None:
            data_len = 100
            filename_label = wx.StaticText(self, -1, 'Filename :')
        else:
            data_len = len(sasm.getRawI())
            filename_label = wx.StaticText(self, -1, 'Filename : ' + sasm.getParameter('filename'))

        self.data_grid = gridlib.Grid(self)
        self.data_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)

        data_len = self._getNumOfHeaderValues()

        self.data_grid.CreateGrid(data_len, 2)
        self.data_grid.SetColLabelValue(0, 'Key')
        self.data_grid.SetColLabelValue(1, 'Value')
        self.data_grid.SetMinSize((400,400))

        self.sizer.Add(filename_label, 0, wx.TOP | wx.LEFT, 10)
        self.sizer.Add(self.data_grid, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        self.Bind(gridlib.EVT_GRID_CELL_CHANGED, self._onChange)
        self.Bind(gridlib.EVT_GRID_EDITOR_SHOWN, self._onEditCell)

        self.SetSizer(self.sizer)

        if self.sasm is not None:
            self._insertData()

        self.data_grid.AutoSizeColumns()
        # self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

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
            wx.MessageBox('Illegal value entered', 'Invalid Entry', style=wx.ICON_ERROR)
            self.data_grid.SetCellValue(row, col, self.saved_value)

    def _getNumOfHeaderValues(self):

        all_keys = []

        if 'counters' in self.sasm.getAllParameters():
            file_hdr = self.sasm.getParameter('counters')
            keys = list(file_hdr.keys())
            all_keys.extend(keys)

        if 'metadata' in self.sasm.getAllParameters():
            metadata = self.sasm.getParameter('metadata')
            keys =list( metadata.keys())
            all_keys.extend(keys)

        if 'calibration_params' in self.sasm.getAllParameters():
            calibration_params = self.sasm.getParameter('calibration_params')
            keys = list(calibration_params.keys())
            all_keys.extend(keys)

        if 'raw_version' in self.sasm.getAllParameters():
            all_keys.extend(['raw_version'])

        if 'imageHeader' in self.sasm.getAllParameters():
            img_hdr = self.sasm.getParameter('imageHeader')
            keys = list(img_hdr.keys())
            all_keys.extend(keys)

        return len(all_keys)

    def _insertData(self):

        total_len = 0

        if 'counters' in self.sasm.getAllParameters():
            file_hdr = self.sasm.getParameter('counters')
            keys = list(file_hdr.keys())

            if len(keys) > 0:
                data_len = len(keys)

                for i in range(0, data_len):
                    self.data_grid.SetCellValue(i, 0, str(keys[i]))
                    self.data_grid.SetCellValue(i, 1, str(file_hdr[keys[i]]))

                total_len = total_len + data_len

        if 'metadata' in self.sasm.getAllParameters():
            metadata = self.sasm.getParameter('metadata')
            keys = list(metadata.keys())

            if len(keys) > 0:
                data_len = len(keys)

                for i in range(total_len, total_len+data_len):
                    self.data_grid.SetCellValue(i, 0, str(keys[i-total_len]))
                    self.data_grid.SetCellValue(i, 1, str(metadata[keys[i-total_len]]))

                total_len = total_len + data_len

        if 'calibration_params' in self.sasm.getAllParameters():
            calibration_params = self.sasm.getParameter('calibration_params')
            keys = list(calibration_params.keys())

            if len(keys) > 0:
                data_len = len(keys)

                for i in range(total_len, total_len+data_len):
                    self.data_grid.SetCellValue(i, 0, str(keys[i-total_len]))
                    self.data_grid.SetCellValue(i, 1, str(calibration_params[keys[i-total_len]]))

                total_len = total_len + data_len

        if 'raw_version' in self.sasm.getAllParameters():
            raw_version = self.sasm.getParameter('raw_version')
            self.data_grid.SetCellValue(total_len, 0, 'raw_version')
            self.data_grid.SetCellValue(total_len, 1, str(raw_version))

            total_len = total_len + 1

        if 'imageHeader' in self.sasm.getAllParameters():
            img_hdr = self.sasm.getParameter('imageHeader')
            keys = list(img_hdr.keys())

            if len(keys) > 0:
                data_len = len(keys)

                for i in range(total_len, total_len + data_len):
                    self.data_grid.SetCellValue(i, 0, str(keys[i-total_len]))
                    self.data_grid.SetCellValue(i, 1, str(img_hdr[keys[i-total_len]]))


    def _onOk(self, event):
        self.EndModal(wx.ID_OK)

    def _onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)


class DataDialog(wx.Dialog):

    def __init__(self, parent, sasm = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Scattering Data Display', style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.grid_changed = False
        self.sasm = sasm
        #For testing
        if self.sasm is None:
            data_len = 100
            filename_label = wx.StaticText(self, -1, 'Filename :')
        else:
            data_len = len(sasm.getRawI())
            filename_label = wx.StaticText(self, -1, 'Filename : ' + sasm.getParameter('filename'))

        self.data_grid = gridlib.Grid(self)
        self.data_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)

        self.data_grid.CreateGrid(data_len, 3)
        self.data_grid.SetColLabelValue(0, 'q')
        self.data_grid.SetColLabelValue(1, 'i')
        self.data_grid.SetColLabelValue(2, 'err')
        self.data_grid.SetMinSize((400,400))

        self.data_grid.EnableEditing(False)

        self.sizer.Add(filename_label, 0, wx.TOP | wx.LEFT, 10)
        self.sizer.Add(self.data_grid, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.CreateButtonSizer(wx.OK), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        # self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        # self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        # self.Bind(gridlib.EVT_GRID_CELL_CHANGED, self._onChange)
        # self.Bind(gridlib.EVT_GRID_EDITOR_SHOWN, self._onEditCell)

        self.SetSizer(self.sizer)

        if self.sasm is not None:
            self._insertData()


        self.data_grid.AutoSizeColumns()
        self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

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
            wx.MessageBox('Illegal value entered', 'Invalid Entry', style=wx.ICON_ERROR)
            self.data_grid.SetCellValue(row, col, self.saved_value)

    def _insertData(self):
        data_len = len(self.sasm.getRawI())

        I = self.sasm.getRawI()
        Q = self.sasm.getRawQ()
        Err = self.sasm.getRawErr()

        for i in range(0, data_len):
            self.data_grid.SetCellValue(i, 0, str(Q[i]))
            self.data_grid.SetCellValue(i, 1, str(I[i]))
            self.data_grid.SetCellValue(i, 2, str(Err[i]))

    def _onOk(self, event):
        self.EndModal(wx.ID_OK)

    def _onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)


class SeriesDataDialog(wx.Dialog):

    def __init__(self, parent, secm = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Series Data Display', style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sec_plot_panel = wx.FindWindowByName('SECPlotPanel')

        self.secm = secm

        if self.secm.qref != 0:
            self.show_qval=True
        else:
            self.show_qval=False

        if self.secm.qrange[0] != 0 and self.secm.qrange[1] != 0:
            self.show_qrange = True
        else:
            self.show_qrange = False

        time = self.secm.getTime()

        if len(time)>0 and time[0] != -1 and len(time) == len(self.secm.plot_frame_list):
            self.showtime = True
        else:
            self.showtime = False

        self.showcalc = self.secm.calc_has_data

        self.create_layout()

        if self.secm is not None:
            self._insertData()


        self.data_grid.AutoSizeColumns()
        self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()

    def create_layout(self):
        if self.secm is None:
            data_len = 100
            filename_label = wx.StaticText(self, -1, 'Filename :')
        else:
            data_len = len(self.secm.total_i)
            filename_label = wx.StaticText(self, -1, 'Filename : ' + self.secm.getParameter('filename'))

        self.data_grid = gridlib.Grid(self)
        self.data_grid.EnableEditing(False)
        self.data_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)

        columns = 4

        mult = 1
        if self.secm.subtracted_sasm_list:
            columns = columns+2
            mult = mult+1
        if self.secm.baseline_subtracted_sasm_list:
            columns = columns+2
            mult = mult+1

        if self.show_qval:
            columns = columns + 1*mult
        if self.show_qrange:
            columns = columns + 1*mult
        if self.showtime:
            columns = columns + 1
        if self.showcalc:
            columns = columns + 7

        self.data_grid.CreateGrid(data_len, columns)
        self.data_grid.SetColLabelValue(0, 'Frame Number')
        self.data_grid.SetColLabelValue(1, 'Integrated Intensity')
        self.data_grid.SetColLabelValue(2, 'Mean Intensity')

        index = 3
        if self.show_qval:
            self.data_grid.SetColLabelValue(index, 'Intensity at q={}'.format(self.secm.qref))
            index = index +1
        if self.show_qrange:
            label = 'Intensity from q={} to {}'.format(self.secm.qrange[0], self.secm.qrange[1])
            self.data_grid.SetColLabelValue(index, label)
            index = index +1
        if self.secm.subtracted_sasm_list:
            self.data_grid.SetColLabelValue(index, 'Subtracted Integrated Intensity')
            index=index+1
            self.data_grid.SetColLabelValue(index, 'Subtracted Mean Intensity')
            index=index+1
            if self.show_qval:
                self.data_grid.SetColLabelValue(index, 'Subtracted Intensity at q={}'.format(self.secm.qref))
                index = index +1
            if self.show_qrange:
                label = 'Subtracted Intensity from q={} to {}'.format(self.secm.qrange[0], self.secm.qrange[1])
                self.data_grid.SetColLabelValue(index, label)
                index = index +1
        if self.secm.baseline_subtracted_sasm_list:
            self.data_grid.SetColLabelValue(index, 'Baseline Corrected Integrated Intensity')
            index=index+1
            self.data_grid.SetColLabelValue(index, 'Baseline Corrected Mean Intensity')
            index=index+1
            if self.show_qval:
                self.data_grid.SetColLabelValue(index, 'Baseline Corrected Intensity at q={}'.format(self.secm.qref))
                index = index +1
            if self.show_qrange:
                label = 'Baseline Corrected Intensity from q={} to {}'.format(self.secm.qrange[0], self.secm.qrange[1])
                self.data_grid.SetColLabelValue(index, label)
                index = index +1
        if self.showtime:
            self.data_grid.SetColLabelValue(index, 'Time (s)')
            index = index +1
        if self.showcalc:
            self.data_grid.SetColLabelValue(index, 'Rg (A)')
            index = index +1
            self.data_grid.SetColLabelValue(index, 'Rg error (A)')
            index = index +1
            self.data_grid.SetColLabelValue(index, 'I0')
            index = index +1
            self.data_grid.SetColLabelValue(index, 'I0 error')
            index = index +1
            self.data_grid.SetColLabelValue(index, 'MW, Vc (kDa)')
            index = index +1
            self.data_grid.SetColLabelValue(index, 'MW, Vc error (kDa)')
            index = index +1
            self.data_grid.SetColLabelValue(index, 'MW, Vp (kDa)')
            index = index +1

        self.data_grid.SetColLabelValue(index, 'File Name')

        self.data_grid.SetMinSize((600,400))

        self.sizer.Add(filename_label, 0, wx.TOP | wx.LEFT, 10)
        self.sizer.Add(self.data_grid, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.CreateButtonSizer(wx.OK), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)

        self.SetSizer(self.sizer)

    def _insertData(self):

        data_len = len(self.secm.total_i)

        for i in range(data_len):
            self.data_grid.SetCellValue(i, 0, str(self.secm.plot_frame_list[i]))
            self.data_grid.SetCellValue(i, 1, str(self.secm.total_i[i]))
            self.data_grid.SetCellValue(i, 2, str(self.secm.mean_i[i]))

            index = 3
            if self.show_qval:
                self.data_grid.SetCellValue(i, index, str(self.secm.I_of_q[i]))
                index = index +1
            if self.show_qrange:
                self.data_grid.SetCellValue(i, index, str(self.secm.qrange_I[i]))
                index = index +1
            if self.secm.subtracted_sasm_list:
                self.data_grid.SetCellValue(i, index, str(self.secm.total_i_sub[i]))
                index=index+1
                self.data_grid.SetCellValue(i, index, str(self.secm.mean_i_sub[i]))
                index=index+1
                if self.show_qval:
                    self.data_grid.SetCellValue(i, index, str(self.secm.I_of_q_sub[i]))
                    index = index +1
                if self.show_qrange:
                    self.data_grid.SetCellValue(i, index, str(self.secm.qrange_I_sub[i]))
                    index = index +1
            if self.secm.baseline_subtracted_sasm_list:
                self.data_grid.SetCellValue(i, index, str(self.secm.total_i_bcsub[i]))
                index=index+1
                self.data_grid.SetCellValue(i, index, str(self.secm.mean_i_bcsub[i]))
                index=index+1
                if self.show_qval:
                    self.data_grid.SetCellValue(i, index, str(self.secm.I_of_q_bcsub[i]))
                    index = index +1
                if self.show_qrange:
                    self.data_grid.SetCellValue(i, index, str(self.secm.qrange_I_bcsub[i]))
                    index = index +1
            if self.showtime:
                self.data_grid.SetCellValue(i, index, str(self.secm.time[i]))
                index = index +1
            if self.showcalc:
                self.data_grid.SetCellValue(i, index, str(self.secm.rg_list[i]))
                index = index +1
                self.data_grid.SetCellValue(i, index, str(self.secm.rger_list[i]))
                index = index +1
                self.data_grid.SetCellValue(i, index, str(self.secm.i0_list[i]))
                index = index +1
                self.data_grid.SetCellValue(i, index, str(self.secm.i0er_list[i]))
                index = index +1
                self.data_grid.SetCellValue(i, index, str(self.secm.vcmw_list[i]))
                index = index +1
                self.data_grid.SetCellValue(i, index, str(self.secm.vcmwer_list[i]))
                index = index +1
                self.data_grid.SetCellValue(i, index, str(self.secm.vpmw_list[i]))
                index = index +1

            self.data_grid.SetCellValue(i, index, os.path.split(self.secm._file_list[i])[1])

    def _onOk(self, event):
        self.EndModal(wx.ID_OK)


class IFTDataDialog(wx.Dialog):

    def __init__(self, parent, iftm = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'IFT Data Display', style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.iftm = iftm

        if len(self.iftm.i_extrap) != 0:
            self.extrap=True
        else:
            self.extrap=False

        self.data_len = max(len(self.iftm.i_extrap), len(self.iftm.r), len(self.iftm.i_orig))
        filename_label = wx.StaticText(self, -1, 'Filename : ' + self.iftm.getParameter('filename'))

        self.data_grid = gridlib.Grid(self)
        self.data_grid.EnableEditing(False)
        self.data_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)

        columns = 7

        if self.extrap:
            columns = columns + 2

        self.data_grid.CreateGrid(self.data_len, columns)
        self.data_grid.SetColLabelValue(0, 'R')
        self.data_grid.SetColLabelValue(1, 'P(r)')
        self.data_grid.SetColLabelValue(2, 'P(r) Error')

        self.data_grid.SetColLabelValue(3, 'Exp. q')
        self.data_grid.SetColLabelValue(4, 'Exp. I')
        self.data_grid.SetColLabelValue(5, 'Exp. I Error')

        self.data_grid.SetColLabelValue(6, 'Fit I (from P(r))')

        index = 7
        if self.extrap:
            self.data_grid.SetColLabelValue(index, 'Extrap. q')
            self.data_grid.SetColLabelValue(index+1, 'Extrap. I')
            index = index +2


        self.data_grid.SetMinSize((700,400))

        self.sizer.Add(filename_label, 0, wx.TOP | wx.LEFT, 10)
        self.sizer.Add(self.data_grid, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.CreateButtonSizer(wx.OK), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)

        self.SetSizer(self.sizer)

        self._insertData()

        self.data_grid.AutoSizeColumns()
        self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()

    def _insertData(self):

        for i in range(self.data_len):
            if i < len(self.iftm.r):
                self.data_grid.SetCellValue(i, 0, str(self.iftm.r[i]))
            else:
                self.data_grid.SetCellValue(i, 0, '')

            if i < len(self.iftm.p):
                self.data_grid.SetCellValue(i, 1, str(self.iftm.p[i]))
            else:
                self.data_grid.SetCellValue(i, 1, '')

            if i < len(self.iftm.err):
                self.data_grid.SetCellValue(i, 2, str(self.iftm.err[i]))
            else:
                self.data_grid.SetCellValue(i, 2, '')

            if i < len(self.iftm.q_orig):
                self.data_grid.SetCellValue(i, 3, str(self.iftm.q_orig[i]))
            else:
                self.data_grid.SetCellValue(i, 3, '')

            if i < len(self.iftm.i_orig):
                self.data_grid.SetCellValue(i, 4, str(self.iftm.i_orig[i]))
            else:
                self.data_grid.SetCellValue(i, 4, '')

            if i < len(self.iftm.err_orig):
                self.data_grid.SetCellValue(i, 5, str(self.iftm.err_orig[i]))
            else:
                self.data_grid.SetCellValue(i, 5, '')

            if i < len(self.iftm.i_fit):
                self.data_grid.SetCellValue(i, 6, str(self.iftm.i_fit[i]))
            else:
                self.data_grid.SetCellValue(i, 6, '')

            if self.extrap:
                if i < len(self.iftm.q_extrap):
                    self.data_grid.SetCellValue(i, 7, str(self.iftm.q_extrap[i]))
                else:
                    self.data_grid.SetCellValue(i, 7, '')

                if i < len(self.iftm.i_extrap):
                    self.data_grid.SetCellValue(i, 8, str(self.iftm.i_extrap[i]))
                else:
                    self.data_grid.SetCellValue(i, 8, '')

    def _onOk(self, event):
        self.EndModal(wx.ID_OK)


class HistoryDialog(wx.Dialog):

    def __init__(self, parent, sasm = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'History Display', style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, size = (-1,600), *args, **kwargs)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sasm = sasm

        self.text = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE | wx.TE_READONLY)
        self.text.AppendText('#############################################\n')
        self.text.AppendText('History of : %s\n' %(sasm.getParameter('filename')))
        self.text.AppendText('#############################################\n\n')

        history = sasm.getParameter('history')

        if history != {} and history is not None:
            self.text.AppendText(json.dumps(history, indent = 4, sort_keys = True))

        else:
            norm = sasm.getParameter('normalizations')
            config = sasm.getParameter('config_file')
            load = sasm.getParameter('load_path')
            params = sasm.getParameter('calibration_params')
            version = sasm.getParameter('raw_version')
            metadata = sasm.getParameter('metadata')

            if norm != {} and norm is not None:
                self.text.AppendText('Normalizations:\n%s\n\n' %(json.dumps(norm, indent = 4, sort_keys = True)))
            if config != {} and config is not None:
                self.text.AppendText('Configuration File:\n%s\n\n' %(json.dumps(config, indent = 4, sort_keys = True)))
            if load != {} and load is not None:
                self.text.AppendText('Load Path:\n%s\n\n' %(json.dumps(load, indent = 4, sort_keys = True)))
            if params != {} and params is not None:
                self.text.AppendText('Calibration Parameters:\n%s\n\n' %(json.dumps(params, indent = 4, sort_keys = True)))
            if metadata != {} and metadata is not None:
                self.text.AppendText('Metadata:\n%s\n\n' %(json.dumps(metadata, indent = 4, sort_keys = True)))
            if version != {} and version is not None:
                self.text.AppendText('Created with RAW version:\n%s\n\n' %(json.dumps(version, indent = 4, sort_keys = True)))


        self.sizer.Add(self.text, 1, wx.ALL | wx.EXPAND, 10)

        self.sizer.Add(self.CreateButtonSizer(wx.OK), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)

        self.SetSizer(self.sizer)

        self.Layout()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()


    def _onOk(self, event):

        self.EndModal(wx.ID_OK)


class SyncDialog(wx.Dialog):

    def __init__(self, parent, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Synchronize', *args, **kwargs)

        self.chkbox_list = [('q min', 'qmin', wx.ID_ANY),
                       ('q max', 'qmax', wx.ID_ANY),
                       ('n min', 'nmin', wx.ID_ANY),
                       ('n max', 'nmax', wx.ID_ANY),
                       ('scale', 'scale', wx.ID_ANY),
                       ('offset', 'offset', wx.ID_ANY),
                       ('line style', 'linestyle', wx.ID_ANY),
                       ('line width', 'linewidth', wx.ID_ANY),
                       ('line marker', 'linemarker', wx.ID_ANY)]

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

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

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
        # format_label = wx.StaticText(self, -1, 'Format :')

        savedir_sizer = wx.BoxSizer()
        self.save_textctrl = wx.TextCtrl(self, -1, path, size = (400, -1))

        folder_bmp = wx.ArtProvider.GetBitmap(wx.ART_FOLDER,  wx.ART_MENU)
        save_search_button = wx.BitmapButton(self, -1, folder_bmp)
        save_search_button.Bind(wx.EVT_BUTTON, self._onSearchButton)

        savedir_sizer.Add(self.save_textctrl, 1, wx.RIGHT | wx.EXPAND, 2)
        savedir_sizer.Add(save_search_button, 0)

        # format_choice = wx.Choice(self, -1, choices = ['.rad (RAW)', '.dat (ATSAS)'])
        # format_choice.Select(0)

        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkClicked, id=wx.ID_OK )

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(filecount_label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        final_sizer.Add(savedir_label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        final_sizer.Add(savedir_sizer, 0, wx.LEFT | wx.RIGHT, 10)
        # final_sizer.Add(format_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        # final_sizer.Add(format_choice, 0, wx.LEFT | wx.RIGHT, 10)
        # final_sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP, 10)
        final_sizer.Add(button_sizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10)

        self.SetSizer(final_sizer)

        self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

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

    def __init__(self, parent, filename, dlgtype = None, style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs):

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

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()

    def _onOKButton(self, event):
        self._filename = self.ctrl.GetValue()
        self.EndModal(wx.ID_OK)

    def _onCancelButton(self, event):
        self.EndModal(wx.ID_CANCEL)

    def getFilename(self):
        return self._filename


class RebinDialog(wx.Dialog):

    def __init__(self, parent, style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Rebinning', *args, **kwargs)

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        choices = ['2','3','4','5','6','7','8','9','10']
        text = wx.StaticText(self, -1, 'Select bin reduction factor :')
        self.choice = wx.Choice(self, -1, choices = choices)
        self.choice.Select(0)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.log_box = wx.CheckBox(self, -1, 'Logarithmic')

        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkClicked, id=wx.ID_OK )

        sizer.Add(text, 1)
        sizer.Add(self.choice, 0)
        sizer.Add(self.log_box, 0, wx.TOP, 5)

        top_sizer.Add(sizer, 1, wx.ALL, 10)
        top_sizer.Add(buttonsizer, 1, wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)

        self.SetSizer(top_sizer)
        self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()

    def _onOkClicked(self, event):
        ret = int(self.choice.GetStringSelection())
        self.EndModal(ret)

    def getValues(self):
        ret = int(self.choice.GetStringSelection())
        log_rebin = self.log_box.GetValue()

        return [ret, log_rebin]


class ColourChangeDialog(wx.Dialog):
    def __init__(self, parent, sasm, linename, line=None, plotpanel=None ,style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Pick a Colour', *args, **kwargs)
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.linename = linename
        self.sasm = sasm
        self.line = line
        self.plotpanel = plotpanel

        old_color = self.getOldColour()

        if old_color == "None": #Transparant marker
            old_color = self.sasm.line.get_color()

        conv = mplcol.ColorConverter()
        color = conv.to_rgb(old_color)
        self._old_linecolour = color
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self._linecolour = color

        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkClicked, id=wx.ID_OK )
        self.Bind( wx.EVT_BUTTON, self._onCancelButton, id=wx.ID_CANCEL )

        self.colourchoice = colorchooser.PyColourChooser(self, -1)
        self.colourchoice.SetValue(self._linecolour)
        self.colourchoice.palette.Bind(wx.EVT_LEFT_UP, self.updateLine)

        for each in self.colourchoice.colour_boxs:
            each.GetColourBox().Bind(wx.EVT_LEFT_UP, self.updateLine)

        for each in self.colourchoice.custom_boxs:
            each.GetColourBox().Bind(wx.EVT_LEFT_UP, self.updateLine)

        self.colourchoice.slider.Bind(wx.EVT_COMMAND_SCROLL, self.updateLine)

        sizer.Add(self.colourchoice, 1)

        top_sizer.Add(sizer, 0, wx.ALL, 10)
        top_sizer.Add(buttonsizer, 0, wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10)

        self.SetSizer(top_sizer)
        self.Fit()

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()

    def getOldColour(self):

        if self.linename == 'MarLineColour':
            return self.sasm.line.get_markeredgecolor()
        elif self.linename == 'MarFillColour':
            return self.sasm.line.get_markerfacecolor()
        elif self.linename == 'LineColour':
            return self.sasm.line.get_color()
        elif self.linename == 'ErrColour':
            return self.sasm.err_line[0][0].get_color()
        elif self.linename == 'CalcMarLineColour':
            return self.sasm.calc_line.get_markeredgecolor()
        elif self.linename == 'CalcMarFillColour':
            return self.sasm.calc_line.get_markerfacecolor()
        elif self.linename == 'CalcLineColour':
            return self.sasm.calc_line.get_color()

        elif self.linename == 'PrMarLineColour':
            return self.sasm.r_line.get_markeredgecolor()
        elif self.linename == 'PrMarFillColour':
            return self.sasm.r_line.get_markerfacecolor()
        elif self.linename == 'PrLineColour':
            return self.sasm.r_line.get_color()
        elif self.linename == 'PrErrColour':
            return self.sasm.r_err_line[0][0].get_color()

        elif self.linename == 'QoMarLineColour':
            return self.sasm.qo_line.get_markeredgecolor()
        elif self.linename == 'QoMarFillColour':
            return self.sasm.qo_line.get_markerfacecolor()
        elif self.linename == 'QoLineColour':
            return self.sasm.qo_line.get_color()
        elif self.linename == 'QoErrColour':
            return self.sasm.qo_err_line[0][0].get_color()

        elif self.linename == 'QfMarLineColour':
            return self.sasm.qf_line.get_markeredgecolor()
        elif self.linename == 'QfMarFillColour':
            return self.sasm.qf_line.get_markerfacecolor()
        elif self.linename == 'QfLineColour':
            return self.sasm.qf_line.get_color()

        elif self.linename == 'NormKratky':
            return self.line.get_color()

    def updateLine(self, event):
        colour =  self.colourchoice.GetValue().Get(False)
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self._setLineColor(colour)

        event.Skip()

    def _setLineColor(self, colour):
        if self.linename == 'MarFillColour':
            self.sasm.line.set_markerfacecolor(colour)
        elif self.linename == 'MarLineColour':
            self.sasm.line.set_markeredgecolor(colour)
        elif self.linename == 'LineColour':
            self.sasm.line.set_color(colour)
        elif self.linename == 'ErrColour':

            for each in self.sasm.err_line:
                for line in each:
                    line.set_color(colour)

        elif self.linename == 'CalcMarFillColour':
            self.sasm.calc_line.set_markerfacecolor(colour)
        elif self.linename == 'CalcMarLineColour':
            self.sasm.calc_line.set_markeredgecolor(colour)
        elif self.linename == 'CalcLineColour':
            self.sasm.calc_line.set_color(colour)


        elif self.linename == 'PrMarFillColour':
            self.sasm.r_line.set_markerfacecolor(colour)
        elif self.linename == 'PrMarLineColour':
            self.sasm.r_line.set_markeredgecolor(colour)
        elif self.linename == 'PrLineColour':
            self.sasm.r_line.set_color(colour)
        elif self.linename == 'PrErrColour':

            for each in self.sasm.r_err_line:
                for line in each:
                    line.set_color(colour)

        elif self.linename == 'QoMarFillColour':
            self.sasm.qo_line.set_markerfacecolor(colour)
        elif self.linename == 'QoMarLineColour':
            self.sasm.qo_line.set_markeredgecolor(colour)
        elif self.linename == 'QoLineColour':
            self.sasm.qo_line.set_color(colour)
        elif self.linename == 'QoErrColour':

            for each in self.sasm.qo_err_line:
                for line in each:
                    line.set_color(colour)

        elif self.linename == 'QfMarFillColour':
            self.sasm.qf_line.set_markerfacecolor(colour)
        elif self.linename == 'QfMarLineColour':
            self.sasm.qf_line.set_markeredgecolor(colour)
        elif self.linename == 'QfLineColour':
            self.sasm.qf_line.set_color(colour)

        elif self.linename == 'NormKratky':
            self.line.set_color(colour)


        if self.sasm is not None:
            self.sasm.plot_panel.canvas.draw()
        else:
            if self.linename == 'NormKratky':
                self.plotpanel.redrawLines()

    def _onOkClicked(self, event):
        self.EndModal(wx.ID_OK)

    def _onCancelButton(self, event):
        self._setLineColor(self._old_linecolour)
        self.EndModal(wx.ID_CANCEL)


class LinePropertyDialog(wx.Dialog):

    def __init__(self, parent, sasm, legend_label, size = (400, 418), style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs):
        if sasm.line is None:
            wx.MessageBox('Unable to change line properties.\nNo plot has been made for this item.', 'No plot')
            return


        wx.Dialog.__init__(self, parent, -1, "Line Properties", size =size, style=style, *args, **kwargs)

        self.sasm = sasm
        self.line = sasm.line
        self.legend_label = legend_label

        self.linewidth_combo_choices = ['1.0', '2.0', '3.0', '4.0', '5.0']
        self.linestyle_list_choices = ['None', '-', '--', '-.', ':']
        self.linemarker_list_choices = ['None', '+', '*', ',','.','1','2','3','4','<', '>', 'D', 'H', '^','_','d','h','o','p','s','v','x','|']

        self._linestyle = self.line.get_linestyle()
        self._linemarker = self.line.get_marker()
        self._linewidth = self.line.get_linewidth()

        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.line.get_color())
        self._old_linecolour = color
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self._linecolour = color


        mfc = self.line.get_markerfacecolor()
        if mfc != "None":
            color = conv.to_rgb(self.line.get_markerfacecolor())
            self._marcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.hollow_marker = False
        else:
            color = conv.to_rgb(self.line.get_markeredgecolor())
            self._marcolour =  wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.hollow_marker = True

        color = conv.to_rgb(self.line.get_markeredgecolor())
        self._marlinecolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        color = conv.to_rgb(self.sasm.err_line[0][0].get_color())
        self._errcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self._old_linestyle = self.line.get_linestyle()
        self._old_linemarker = self.line.get_marker()
        self._old_linewidth = self.line.get_linewidth()
        self._old_marcolour = self.line.get_markerfacecolor()
        self._old_marlinecolour = self.line.get_markeredgecolor()
        self._old_marsize = self.line.get_markersize()
        self._old_errcolour = self.sasm.err_line[0][0].get_color()
        self._old_errlinewidth = self.sasm.err_line[0][0].get_linewidth()

        errstyle = self.sasm.err_line[1][0].get_linestyle()

        if errstyle[0][0] is None:
            err_style = '-'
        elif len(errstyle[0][1]) == 4:
            err_style = '-.'
        else:
            if errstyle[0][1][0] > errstyle[0][1][1]:
                err_style = '--'
            else:
                err_style = ':'

        self._old_errlinestyle = err_style

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkButton, id=wx.ID_OK )
        self.Bind( wx.EVT_BUTTON, self._onCancelButton, id=wx.ID_CANCEL )

        linesettings_sizer = wx.FlexGridSizer(cols = 5, rows = 2, vgap = 5, hgap = 10)
        linesettings_sizer.AddGrowableCol(0)
        linesettings_sizer.AddGrowableCol(2)
        linesettings_sizer.AddGrowableCol(4)

        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.Add(self._createLineControls(), 1, wx.EXPAND)
        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.Add(self._createErrorBarsControls(), 1, wx.EXPAND)
        linesettings_sizer.AddStretchSpacer(1)

        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.Add(self._createLineMarkerControls(), 1, wx.EXPAND)
        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.AddStretchSpacer(1)

        top_sizer.Add(self._createLegendLabelControls(), 0, wx.ALL | wx.EXPAND, 10)
        top_sizer.Add(linesettings_sizer, 0, wx.ALL | wx.EXPAND, 10)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(wx.StaticLine(self, -1), wx.EXPAND |wx.TOP | wx.BOTTOM, 3)
        top_sizer.Add(buttonsizer, 0, wx.CENTER | wx.BOTTOM, 10)

        self.SetSizer(top_sizer)

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()


    def _createLegendLabelControls(self):
        topbox = wx.StaticBox(self, -1, 'Legend Label')
        box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        self.legend_label_text = wx.TextCtrl(self, -1, self.legend_label)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.legend_label_text, 1, wx.EXPAND)

        box.Add(sizer, 0, wx.EXPAND | wx.ALL, 5)
        return box

    def _createErrorBarsControls(self):
        topbox = wx.StaticBox(self, -1, 'Error Bars')
        box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        err_linewidth_label = wx.StaticText(self, -1, 'Width :')
        err_linestyle_label = wx.StaticText(self, -1, 'Style :')
        err_colour_label = wx.StaticText(self, -1, 'Line Colour :')

        self.err_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
        self.err_linewidth.SetValue(str(self._old_errlinewidth))
        self.err_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

        self.err_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
        self.err_linestyle_list.Select(self.linestyle_list_choices.index(str(self._old_errlinestyle)))
        self.err_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

        self.err_colour = wx.Panel(self, -1, name = 'ErrColour', style = wx.RAISED_BORDER)
        self.err_colour.SetBackgroundColour(self._errcolour)
        self.err_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

        sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
        sizer.Add(err_linestyle_label, 0)
        sizer.Add(self.err_linestyle_list, 0, wx.EXPAND)
        sizer.Add(err_linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.err_linewidth, 0, wx.EXPAND)
        sizer.Add(err_colour_label, 0)
        sizer.Add(self.err_colour, 0, wx.EXPAND)

        box.Add(sizer, 0, wx.ALL, 5)

        return box

    def _onColourPress(self, event):

        colour_panel = event.GetEventObject()

        dlg = ColourChangeDialog(self, self.sasm, colour_panel.GetName())
        dlg.ShowModal()
        dlg.Destroy()

        if colour_panel.GetName() == 'LineColour':
            color = self.line.get_color()
        elif colour_panel.GetName() == 'ErrColour':
            color = self.sasm.err_line[0][0].get_color()
        elif colour_panel.GetName() == 'MarLineColour':
            color = self.line.get_markeredgecolor()
        elif colour_panel.GetName() == 'MarFillColour':
            color = self.line.get_markerfacecolor()

        conv = mplcol.ColorConverter()

        if color != "None": #Not transparent
            color = conv.to_rgb(color)
            color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

            colour_panel.SetBackgroundColour(color)
            colour_panel.Refresh()

    def _createLineMarkerControls(self):
        topbox = wx.StaticBox(self, -1, 'Data Point Marker')
        box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        mar_size_label = wx.StaticText(self, -1, 'Size :')
        self.mar_fillcolour_label = wx.StaticText(self, -1, 'Fill Colour :')
        self.mar_fillcolour_label.Enable(not self.hollow_marker)
        mar_linecolour_label = wx.StaticText(self, -1, 'Line Colour :')
        mar_linemarker_label = wx.StaticText(self, -1, 'Marker :')
        mar_hollow_label = wx.StaticText(self, -1, 'Hollow :')

        self.mar_size = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
        self.mar_size.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)
        self.mar_size.SetValue(str(self._old_marsize))

        self.mar_fillcolour = wx.Panel(self, -1, name = 'MarFillColour', style = wx.RAISED_BORDER)
        self.mar_fillcolour.SetBackgroundColour(self._marcolour)
        self.mar_fillcolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)
        self.mar_fillcolour.Enable(not self.hollow_marker)

        self.mar_linecolour = wx.Panel(self, -1, name = 'MarLineColour', style = wx.RAISED_BORDER)
        self.mar_linecolour.SetBackgroundColour(self._marlinecolour)
        self.mar_linecolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

        self.mar_linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
        self.mar_linemarker_list.Select(self.linemarker_list_choices.index(str(self._linemarker)))
        self.mar_linemarker_list.Bind(wx.EVT_CHOICE, self.updateLine)

        self.mar_hollow = wx.CheckBox(self, -1)
        self.mar_hollow.SetValue(self.hollow_marker)
        self.mar_hollow.Bind(wx.EVT_CHECKBOX, self._onHollowCheckBox)

        sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
        sizer.Add(mar_linemarker_label, 0)
        sizer.Add(self.mar_linemarker_list, 0, wx.EXPAND)
        sizer.Add(mar_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.mar_size, 0, wx.EXPAND)
        sizer.Add(mar_linecolour_label, 0)
        sizer.Add(self.mar_linecolour, 0, wx.EXPAND)
        sizer.Add(self.mar_fillcolour_label, 0)
        sizer.Add(self.mar_fillcolour, 0, wx.EXPAND)
        sizer.Add(mar_hollow_label, 0)
        sizer.Add(self.mar_hollow, 0, wx.EXPAND)


        box.Add(sizer, 0, wx.ALL, 5)

        return box

    def _onHollowCheckBox(self, event):

        chkbox = event.GetEventObject()

        if chkbox.GetValue() == True:
            self.line.set_markerfacecolor("None")
            self.sasm.plot_panel.canvas.draw()
            self.mar_fillcolour.Enable(False)
            self.mar_fillcolour_label.Enable(False)
        else:
            self.mar_fillcolour.Enable(True)
            self.mar_fillcolour_label.Enable(True)
            colour =  self.mar_fillcolour.GetBackgroundColour()
            colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)
            self.line.set_markerfacecolor(colour)
            self.sasm.plot_panel.canvas.draw()

    def _createLineControls(self):

        topbox = wx.StaticBox(self, -1, 'Line')
        box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        linewidth_label = wx.StaticText(self, -1, 'Width :')
        linestyle_label = wx.StaticText(self, -1, 'Style :')
        linecolour_label = wx.StaticText(self, -1, 'Line Colour :')

        self.linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
        self.linewidth.SetValue(str(self._old_linewidth))
        self.linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

        self.linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
        self.linestyle_list.Select(self.linestyle_list_choices.index(str(self._linestyle)))
        self.linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

        self.line_colour = wx.Panel(self, -1, name = 'LineColour', style = wx.RAISED_BORDER)
        self.line_colour.SetBackgroundColour(self._linecolour)
        self.line_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

        sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)

        sizer.Add(linestyle_label, 0)
        sizer.Add(self.linestyle_list, 0, wx.EXPAND)
        sizer.Add(linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.linewidth, 0, wx.EXPAND)
        sizer.Add(linecolour_label, 0)
        sizer.Add(self.line_colour, 0, wx.EXPAND)

        box.Add(sizer, 0, wx.ALL, 5)

        return box

    def getLegendLabel(self):
        return self.legend_label_text.GetValue()

    def updateErrorLines(self, data):

        for each in self.sasm.err_line:
            for line in each:
                func, param = data
                getattr(line, func)(param)

    def updateLine(self, event):
        marker =  self.mar_linemarker_list.GetStringSelection()
        width =  float(self.linewidth.GetValue())
        style =  self.linestyle_list.GetStringSelection()

        mar_size = float(self.mar_size.GetValue())
        err_linewidth = float(self.err_linewidth.GetValue())
        err_linestyle = self.err_linestyle_list.GetStringSelection()

        self.line.set_marker(marker)

        colour =  self.mar_linecolour.GetBackgroundColour()
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self.updateErrorLines(['set_linewidth', err_linewidth])

        each = self.sasm.err_line[1]
        if err_linestyle != "None":
            for line in each:
                line.set_linestyle(err_linestyle)

        self.line.set_markeredgecolor(colour)
        self.line.set_linewidth(width)
        self.line.set_linestyle(style)
        #self.line.set_color(colour)
        self.line.set_markersize(mar_size)

        self.sasm.plot_panel.canvas.draw()

        if event is not None:
            event.Skip()

    def _onCancelButton(self, event):
        self.line.set_linewidth(self._old_linewidth)
        self.line.set_linestyle(self._old_linestyle)
        self.line.set_color(self._old_linecolour)

        self.line.set_marker(self._old_linemarker)
        self.line.set_markeredgecolor(self._old_marlinecolour)
        self.line.set_markerfacecolor(self._old_marcolour)
        self.line.set_markersize(self._old_marsize)

        #Stupid errorbars:
        line1, line2 = self.sasm.err_line
        for each in line2:
            each.set_linestyle(self._old_errlinestyle)
            each.set_linewidth(self._old_errlinewidth)
            each.set_color(self._old_errcolour)
        for each in line1:
            each.set_linewidth(self._old_errlinewidth)
            each.set_color(self._old_errcolour)

        self.sasm.plot_panel.canvas.draw()

        self.EndModal(wx.ID_CANCEL)

    def _onOkButton(self, event):
        self.updateLine(None)

        self.EndModal(wx.ID_OK)


class IFTMLinePropertyDialog(wx.Dialog):

    def __init__(self, parent, iftm, legend_label, size = (500, 598), style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs):

        if iftm.r_line is None:
            wx.MessageBox('Unable to change line properties.\nNo plot has been made for this item.', 'No plot')
            return


        wx.Dialog.__init__(self, parent, -1, "IFT Line Properties", size=size, style = style, *args, **kwargs)

        self.iftm = iftm
        self.r_line = iftm.r_line
        self.qo_line = iftm.qo_line
        self.qf_line = iftm.qf_line
        self.legend_label = legend_label

        self.linewidth_combo_choices = ['1.0', '2.0', '3.0', '4.0', '5.0']
        self.linestyle_list_choices = ['None', '-', '--', '-.', ':']
        self.linemarker_list_choices = ['None', '+', '*', ',','.','1','2','3','4','<', '>', 'D', 'H', '^','_','d','h','o','p','s','v','x','|']

        self.r_linestyle = self.r_line.get_linestyle()
        self.r_linemarker = self.r_line.get_marker()
        self.r_linewidth = self.r_line.get_linewidth()

        self.qo_linestyle = self.qo_line.get_linestyle()
        self.qo_linemarker = self.qo_line.get_marker()
        self.qo_linewidth = self.qo_line.get_linewidth()

        self.qf_linestyle = self.qf_line.get_linestyle()
        self.qf_linemarker = self.qf_line.get_marker()
        self.qf_linewidth = self.qf_line.get_linewidth()


        conv = mplcol.ColorConverter()

        r_color = conv.to_rgb(self.r_line.get_color())
        qo_color = conv.to_rgb(self.qo_line.get_color())
        qf_color = conv.to_rgb(self.qf_line.get_color())

        self._old_r_linecolour = r_color
        self._old_qo_linecolour = qo_color
        self._old_qf_linecolour = qf_color

        r_color = wx.Colour(int(r_color[0]*255), int(r_color[1]*255), int(r_color[2]*255))
        qo_color = wx.Colour(int(qo_color[0]*255), int(qo_color[1]*255), int(qo_color[2]*255))
        qf_color = wx.Colour(int(qf_color[0]*255), int(qf_color[1]*255), int(qf_color[2]*255))

        self.r_linecolour = r_color
        self.qo_linecolour = qo_color
        self.qf_linecolour = qf_color


        r_mfc = self.r_line.get_markerfacecolor()

        if r_mfc != "None":
            color = conv.to_rgb(r_mfc)
            self.r_marcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.r_hollow_marker = False
        else:
            color = conv.to_rgb(self.r_line.get_markeredgecolor())
            self.r_marcolour =  wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.r_hollow_marker = True

        qo_mfc = self.qo_line.get_markerfacecolor()

        if qo_mfc != "None":
            color = conv.to_rgb(qo_mfc)
            self.qo_marcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.qo_hollow_marker = False
        else:
            color = conv.to_rgb(self.qo_line.get_markeredgecolor())
            self.qo_marcolour =  wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.qo_hollow_marker = True

        qf_mfc = self.qf_line.get_markerfacecolor()

        if qf_mfc != "None":
            color = conv.to_rgb(qf_mfc)
            self.qf_marcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.qf_hollow_marker = False
        else:
            color = conv.to_rgb(self.qf_line.get_markeredgecolor())
            self.qf_marcolour =  wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.qf_hollow_marker = True

        color = conv.to_rgb(self.r_line.get_markeredgecolor())
        self.r_marlinecolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        color = conv.to_rgb(self.qo_line.get_markeredgecolor())
        self.qo_marlinecolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        color = conv.to_rgb(self.qf_line.get_markeredgecolor())
        self.qf_marlinecolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        color = conv.to_rgb(self.iftm.r_err_line[0][0].get_color())
        self.r_errcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        color = conv.to_rgb(self.iftm.qo_err_line[0][0].get_color())
        self.qo_errcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        self._old_r_linestyle = self.r_line.get_linestyle()
        self._old_r_linemarker = self.r_line.get_marker()
        self._old_r_linewidth = self.r_line.get_linewidth()
        self._old_r_marcolour = self.r_line.get_markerfacecolor()
        self._old_r_marlinecolour = self.r_line.get_markeredgecolor()
        self._old_r_marsize = self.r_line.get_markersize()

        self._old_qo_linestyle = self.qo_line.get_linestyle()
        self._old_qo_linemarker = self.qo_line.get_marker()
        self._old_qo_linewidth = self.qo_line.get_linewidth()
        self._old_qo_marcolour = self.qo_line.get_markerfacecolor()
        self._old_qo_marlinecolour = self.qo_line.get_markeredgecolor()
        self._old_qo_marsize = self.qo_line.get_markersize()

        self._old_qf_linestyle = self.qf_line.get_linestyle()
        self._old_qf_linemarker = self.qf_line.get_marker()
        self._old_qf_linewidth = self.qf_line.get_linewidth()
        self._old_qf_marcolour = self.qf_line.get_markerfacecolor()
        self._old_qf_marlinecolour = self.qf_line.get_markeredgecolor()
        self._old_qf_marsize = self.r_line.get_markersize()


        self._old_r_errcolour = self.iftm.r_err_line[0][0].get_color()
        self._old_r_errlinewidth = self.iftm.r_err_line[0][0].get_linewidth()

        errstyle = self.iftm.r_err_line[1][0].get_linestyle()

        if errstyle[0][0] is None:
            r_err_style = '-'
        elif len(errstyle[0][1]) == 4:
            r_err_style = '-.'
        else:
            if errstyle[0][1][0] > errstyle[0][1][1]:
                r_err_style = '--'
            else:
                r_err_style = ':'

        self._old_r_errlinestyle = r_err_style

        self._old_qo_errcolour = self.iftm.qo_err_line[0][0].get_color()
        self._old_qo_errlinewidth = self.iftm.qo_err_line[0][0].get_linewidth()

        errstyle = self.iftm.qo_err_line[1][0].get_linestyle()

        if errstyle[0][0] is None:
            qo_err_style = '-'
        elif len(errstyle[0][1]) == 4:
            qo_err_style = '-.'
        else:
            if errstyle[0][1][0] > errstyle[0][1][1]:
                qo_err_style = '--'
            else:
                qo_err_style = ':'

        self._old_qo_errlinestyle = qo_err_style


        top_sizer = wx.BoxSizer(wx.VERTICAL)

        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkButton, id=wx.ID_OK )
        self.Bind( wx.EVT_BUTTON, self._onCancelButton, id=wx.ID_CANCEL )


        r_linesettings_sizer = wx.FlexGridSizer(cols = 2, rows = 2, vgap = 3, hgap = 3)
        r_linesettings_sizer.Add(self._createLineControls(self.r_line), 1, wx.EXPAND)
        r_linesettings_sizer.Add(self._createErrorBarsControls(self.r_line), 1, wx.EXPAND)
        r_linesettings_sizer.Add(self._createLineMarkerControls(self.r_line), 1, wx.EXPAND)

        qo_linesettings_sizer = wx.FlexGridSizer(cols = 2, rows = 2, vgap = 3, hgap = 3)
        qo_linesettings_sizer.Add(self._createLineControls(self.qo_line), 1, wx.EXPAND)
        qo_linesettings_sizer.Add(self._createErrorBarsControls(self.qo_line), 1, wx.EXPAND)
        qo_linesettings_sizer.Add(self._createLineMarkerControls(self.qo_line), 1, wx.EXPAND)

        qf_linesettings_sizer = wx.FlexGridSizer(cols = 2, rows = 1, vgap = 3, hgap = 3)
        qf_linesettings_sizer.Add(self._createLineControls(self.qf_line), 1, wx.EXPAND)
        # qf_linesettings_sizer.Add(self._createErrorBarsControls(self.qf_line), 1, wx.EXPAND)
        qf_linesettings_sizer.Add(self._createLineMarkerControls(self.qf_line), 1, wx.EXPAND)


        rbox = wx.StaticBox(self, -1, 'P(r) line settings')
        qobox = wx.StaticBox(self, -1, 'Data line settings')
        qfbox = wx.StaticBox(self, -1, 'Fit line settings')

        rboxSizer = wx.StaticBoxSizer(rbox, wx.VERTICAL)
        rboxSizer.Add(self._createLegendLabelControls(self.r_line), 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 3)
        rboxSizer.Add(r_linesettings_sizer, 0, wx.EXPAND)

        qoboxSizer = wx.StaticBoxSizer(qobox, wx.VERTICAL)
        qoboxSizer.Add(self._createLegendLabelControls(self.qo_line), 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 3)
        qoboxSizer.Add(qo_linesettings_sizer, 0, wx.EXPAND)

        qfboxSizer = wx.StaticBoxSizer(qfbox, wx.VERTICAL)
        qfboxSizer.Add(self._createLegendLabelControls(self.qf_line), 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 3)
        qfboxSizer.Add(qf_linesettings_sizer, 0, wx.EXPAND)

        side_sizer = wx.BoxSizer(wx.HORIZONTAL)
        side_sizer.Add(rboxSizer, 0, wx.EXPAND)
        side_sizer.AddStretchSpacer(1)
        side_sizer.Add(qoboxSizer, 0, wx.EXPAND|wx.LEFT, border=10)

        side_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        side_sizer2.Add(qfboxSizer, 0, wx.EXPAND)
        side_sizer2.AddStretchSpacer(1)


        top_sizer.Add(side_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(side_sizer2, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(buttonsizer, 0, wx.CENTER | wx.BOTTOM, 5)

        self.SetSizer(top_sizer)

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()


    def _createLegendLabelControls(self, line):
        if line == self.r_line:
            topbox = wx.StaticBox(self, -1, 'Legend Label')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            self.r_legend_label_text = wx.TextCtrl(self, -1, self.legend_label[self.r_line])

            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(self.r_legend_label_text, 1, wx.EXPAND)

            box.Add(sizer, 0, wx.EXPAND | wx.ALL, 3)

        elif line == self.qo_line:
            topbox = wx.StaticBox(self, -1, 'Legend Label')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            self.qo_legend_label_text = wx.TextCtrl(self, -1, self.legend_label[self.qo_line])

            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(self.qo_legend_label_text, 1, wx.EXPAND)

            box.Add(sizer, 0, wx.EXPAND | wx.ALL, 3)

        elif line == self.qf_line:
            topbox = wx.StaticBox(self, -1, 'Legend Label')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            self.qf_legend_label_text = wx.TextCtrl(self, -1, self.legend_label[self.qf_line])

            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(self.qf_legend_label_text, 1, wx.EXPAND)

            box.Add(sizer, 0, wx.EXPAND | wx.ALL, 3)


        return box

    def _createErrorBarsControls(self, line):

        topbox = wx.StaticBox(self, -1, 'Error Bars')
        box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        if line == self.r_line:

            err_linewidth_label = wx.StaticText(self, -1, 'Width :')
            err_linestyle_label = wx.StaticText(self, -1, 'Style :')
            err_colour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.r_err_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.r_err_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.r_err_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.r_err_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.r_err_colour = wx.Panel(self, -1, name = 'PrErrColour', style = wx.RAISED_BORDER)
            self.r_err_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(err_linestyle_label, 0)
            sizer.Add(self.r_err_linestyle_list, 0, wx.EXPAND)
            sizer.Add(err_linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.r_err_linewidth, 0, wx.EXPAND)
            sizer.Add(err_colour_label, 0)
            sizer.Add(self.r_err_colour, 0, wx.EXPAND)

            self.r_err_linewidth.SetValue(str(self._old_r_errlinewidth))
            self.r_err_linestyle_list.Select(self.linestyle_list_choices.index(str(self._old_r_errlinestyle)))
            self.r_err_colour.SetBackgroundColour(self.r_errcolour)

        elif line == self.qo_line:
            err_linewidth_label = wx.StaticText(self, -1, 'Width :')
            err_linestyle_label = wx.StaticText(self, -1, 'Style :')
            err_colour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.qo_err_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.qo_err_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.qo_err_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.qo_err_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.qo_err_colour = wx.Panel(self, -1, name = 'QoErrColour', style = wx.RAISED_BORDER)
            self.qo_err_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(err_linestyle_label, 0)
            sizer.Add(self.qo_err_linestyle_list, 0, wx.EXPAND)
            sizer.Add(err_linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.qo_err_linewidth, 0, wx.EXPAND)
            sizer.Add(err_colour_label, 0)
            sizer.Add(self.qo_err_colour, 0, wx.EXPAND)

            self.qo_err_linewidth.SetValue(str(self._old_qo_errlinewidth))
            self.qo_err_linestyle_list.Select(self.linestyle_list_choices.index(str(self._old_qo_errlinestyle)))
            self.qo_err_colour.SetBackgroundColour(self.qo_errcolour)


        box.Add(sizer, 0, wx.ALL, 5)

        return box

    def _onColourPress(self, event):

        colour_panel = event.GetEventObject()

        dlg = ColourChangeDialog(self, self.iftm, colour_panel.GetName())
        dlg.ShowModal()
        dlg.Destroy()

        if colour_panel.GetName() == 'PrLineColour':
            color = self.r_line.get_color()
        elif colour_panel.GetName() == 'PrErrColour':
            color = self.iftm.r_err_line[0][0].get_color()
        elif colour_panel.GetName() == 'PrMarLineColour':
            color = self.r_line.get_markeredgecolor()
        elif colour_panel.GetName() == 'PrMarFillColour':
            color = self.r_line.get_markerfacecolor()

        elif colour_panel.GetName() == 'QoLineColour':
            color = self.qo_line.get_color()
        elif colour_panel.GetName() == 'QoErrColour':
            color = self.iftm.qo_err_line[0][0].get_color()
        elif colour_panel.GetName() == 'QoMarLineColour':
            color = self.qo_line.get_markeredgecolor()
        elif colour_panel.GetName() == 'QoMarFillColour':
            color = self.qo_line.get_markerfacecolor()

        elif colour_panel.GetName() == 'QfLineColour':
            color = self.qf_line.get_color()
        elif colour_panel.GetName() == 'QfMarLineColour':
            color = self.qf_line.get_markeredgecolor()
        elif colour_panel.GetName() == 'QfMarFillColour':
            color = self.qf_line.get_markerfacecolor()

        conv = mplcol.ColorConverter()

        if color != "None": #Not transparent
            color = conv.to_rgb(color)
            color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

            colour_panel.SetBackgroundColour(color)
            colour_panel.Refresh()

    def _createLineMarkerControls(self, line):

        if line == self.r_line:
            topbox = wx.StaticBox(self, -1, 'Data Point Marker')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            mar_size_label = wx.StaticText(self, -1, 'Size :')
            self.r_mar_fillcolour_label = wx.StaticText(self, -1, 'Fill Colour :')
            self.r_mar_fillcolour_label.Enable(not self.r_hollow_marker)
            mar_linecolour_label = wx.StaticText(self, -1, 'Line Colour :')
            mar_linemarker_label = wx.StaticText(self, -1, 'Marker :')
            mar_hollow_label = wx.StaticText(self, -1, 'Hollow :')

            self.r_mar_size = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.r_mar_size.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)
            self.r_mar_size.SetValue(str(self._old_r_marsize))

            self.r_mar_fillcolour = wx.Panel(self, -1, name = 'PrMarFillColour', style = wx.RAISED_BORDER)
            self.r_mar_fillcolour.SetBackgroundColour(self.r_marcolour)
            self.r_mar_fillcolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)
            self.r_mar_fillcolour.Enable(not self.r_hollow_marker)

            self.r_mar_linecolour = wx.Panel(self, -1, name = 'PrMarLineColour', style = wx.RAISED_BORDER)
            self.r_mar_linecolour.SetBackgroundColour(self.r_marlinecolour)
            self.r_mar_linecolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            self.r_mar_linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
            self.r_mar_linemarker_list.Select(self.linemarker_list_choices.index(str(self.r_linemarker)))
            self.r_mar_linemarker_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.r_mar_hollow = wx.CheckBox(self, -1)
            self.r_mar_hollow.SetValue(self.r_hollow_marker)
            self.r_mar_hollow.Bind(wx.EVT_CHECKBOX, self.r_onHollowCheckBox)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(mar_linemarker_label, 0)
            sizer.Add(self.r_mar_linemarker_list, 0, wx.EXPAND)
            sizer.Add(mar_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.r_mar_size, 0, wx.EXPAND)
            sizer.Add(mar_linecolour_label, 0)
            sizer.Add(self.r_mar_linecolour, 0, wx.EXPAND)
            sizer.Add(self.r_mar_fillcolour_label, 0)
            sizer.Add(self.r_mar_fillcolour, 0, wx.EXPAND)
            sizer.Add(mar_hollow_label, 0)
            sizer.Add(self.r_mar_hollow, 0, wx.EXPAND)


            box.Add(sizer, 0, wx.ALL, 5)

        elif line == self.qo_line:
            topbox = wx.StaticBox(self, -1, 'Data Point Marker')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            mar_size_label = wx.StaticText(self, -1, 'Size :')
            self.qo_mar_fillcolour_label = wx.StaticText(self, -1, 'Fill Colour :')
            self.qo_mar_fillcolour_label.Enable(not self.qo_hollow_marker)
            mar_linecolour_label = wx.StaticText(self, -1, 'Line Colour :')
            mar_linemarker_label = wx.StaticText(self, -1, 'Marker :')
            mar_hollow_label = wx.StaticText(self, -1, 'Hollow :')

            self.qo_mar_size = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.qo_mar_size.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)
            self.qo_mar_size.SetValue(str(self._old_qo_marsize))

            self.qo_mar_fillcolour = wx.Panel(self, -1, name = 'QoMarFillColour', style = wx.RAISED_BORDER)
            self.qo_mar_fillcolour.SetBackgroundColour(self.qo_marcolour)
            self.qo_mar_fillcolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)
            self.qo_mar_fillcolour.Enable(not self.qo_hollow_marker)

            self.qo_mar_linecolour = wx.Panel(self, -1, name = 'QoMarLineColour', style = wx.RAISED_BORDER)
            self.qo_mar_linecolour.SetBackgroundColour(self.qo_marlinecolour)
            self.qo_mar_linecolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            self.qo_mar_linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
            self.qo_mar_linemarker_list.Select(self.linemarker_list_choices.index(str(self.qo_linemarker)))
            self.qo_mar_linemarker_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.qo_mar_hollow = wx.CheckBox(self, -1)
            self.qo_mar_hollow.SetValue(self.qo_hollow_marker)
            self.qo_mar_hollow.Bind(wx.EVT_CHECKBOX, self.qo_onHollowCheckBox)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(mar_linemarker_label, 0)
            sizer.Add(self.qo_mar_linemarker_list, 0, wx.EXPAND)
            sizer.Add(mar_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.qo_mar_size, 0, wx.EXPAND)
            sizer.Add(mar_linecolour_label, 0)
            sizer.Add(self.qo_mar_linecolour, 0, wx.EXPAND)
            sizer.Add(self.qo_mar_fillcolour_label, 0)
            sizer.Add(self.qo_mar_fillcolour, 0, wx.EXPAND)
            sizer.Add(mar_hollow_label, 0)
            sizer.Add(self.qo_mar_hollow, 0, wx.EXPAND)


            box.Add(sizer, 0, wx.ALL, 5)


        elif line == self.qf_line:
            topbox = wx.StaticBox(self, -1, 'Data Point Marker')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            mar_size_label = wx.StaticText(self, -1, 'Size :')
            self.qf_mar_fillcolour_label = wx.StaticText(self, -1, 'Fill Colour :')
            self.qf_mar_fillcolour_label.Enable(not self.qf_hollow_marker)
            mar_linecolour_label = wx.StaticText(self, -1, 'Line Colour :')
            mar_linemarker_label = wx.StaticText(self, -1, 'Marker :')
            mar_hollow_label = wx.StaticText(self, -1, 'Hollow :')

            self.qf_mar_size = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.qf_mar_size.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)
            self.qf_mar_size.SetValue(str(self._old_qf_marsize))

            self.qf_mar_fillcolour = wx.Panel(self, -1, name = 'QfMarFillColour', style = wx.RAISED_BORDER)
            self.qf_mar_fillcolour.SetBackgroundColour(self.qf_marcolour)
            self.qf_mar_fillcolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)
            self.qf_mar_fillcolour.Enable(not self.qf_hollow_marker)

            self.qf_mar_linecolour = wx.Panel(self, -1, name = 'QfMarLineColour', style = wx.RAISED_BORDER)
            self.qf_mar_linecolour.SetBackgroundColour(self.qf_marlinecolour)
            self.qf_mar_linecolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            self.qf_mar_linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
            self.qf_mar_linemarker_list.Select(self.linemarker_list_choices.index(str(self.qf_linemarker)))
            self.qf_mar_linemarker_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.qf_mar_hollow = wx.CheckBox(self, -1)
            self.qf_mar_hollow.SetValue(self.qf_hollow_marker)
            self.qf_mar_hollow.Bind(wx.EVT_CHECKBOX, self.qf_onHollowCheckBox)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(mar_linemarker_label, 0)
            sizer.Add(self.qf_mar_linemarker_list, 0, wx.EXPAND)
            sizer.Add(mar_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.qf_mar_size, 0, wx.EXPAND)
            sizer.Add(mar_linecolour_label, 0)
            sizer.Add(self.qf_mar_linecolour, 0, wx.EXPAND)
            sizer.Add(self.qf_mar_fillcolour_label, 0)
            sizer.Add(self.qf_mar_fillcolour, 0, wx.EXPAND)
            sizer.Add(mar_hollow_label, 0)
            sizer.Add(self.qf_mar_hollow, 0, wx.EXPAND)


            box.Add(sizer, 0, wx.ALL, 5)

        return box

    def r_onHollowCheckBox(self, event):

        chkbox = event.GetEventObject()

        if chkbox.GetValue() == True:
            self.r_line.set_markerfacecolor("None")
            self.iftm.plot_panel.canvas.draw()
            self.r_mar_fillcolour.Enable(False)
            self.r_mar_fillcolour_label.Enable(False)
        else:
            self.r_mar_fillcolour.Enable(True)
            self.r_mar_fillcolour_label.Enable(True)
            colour =  self.r_mar_fillcolour.GetBackgroundColour()
            colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)
            self.r_line.set_markerfacecolor(colour)
            self.iftm.plot_panel.canvas.draw()

    def qo_onHollowCheckBox(self, event):

        chkbox = event.GetEventObject()

        if chkbox.GetValue() == True:
            self.qo_line.set_markerfacecolor("None")
            self.iftm.plot_panel.canvas.draw()
            self.qo_mar_fillcolour.Enable(False)
            self.qo_mar_fillcolour_label.Enable(False)
        else:
            self.qo_mar_fillcolour.Enable(True)
            self.qo_mar_fillcolour_label.Enable(True)
            colour =  self.qo_mar_fillcolour.GetBackgroundColour()
            colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)
            self.qo_line.set_markerfacecolor(colour)
            self.iftm.plot_panel.canvas.draw()

    def qf_onHollowCheckBox(self, event):

        chkbox = event.GetEventObject()

        if chkbox.GetValue() == True:
            self.qf_line.set_markerfacecolor("None")
            self.iftm.plot_panel.canvas.draw()
            self.qf_mar_fillcolour.Enable(False)
            self.qf_mar_fillcolour_label.Enable(False)
        else:
            self.qf_mar_fillcolour.Enable(True)
            self.qf_mar_fillcolour_label.Enable(True)
            colour =  self.qf_mar_fillcolour.GetBackgroundColour()
            colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)
            self.qf_line.set_markerfacecolor(colour)
            self.iftm.plot_panel.canvas.draw()

    def _createLineControls(self, line):

        if line == self.r_line:
            topbox = wx.StaticBox(self, -1, 'Line')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            linewidth_label = wx.StaticText(self, -1, 'Width :')
            linestyle_label = wx.StaticText(self, -1, 'Style :')
            linecolour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.r_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.r_linewidth.SetValue(str(self._old_r_linewidth))
            self.r_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.r_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.r_linestyle_list.Select(self.linestyle_list_choices.index(str(self.r_linestyle)))
            self.r_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.r_line_colour = wx.Panel(self, -1, name = 'PrLineColour', style = wx.RAISED_BORDER)
            self.r_line_colour.SetBackgroundColour(self.r_linecolour)
            self.r_line_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)

            sizer.Add(linestyle_label, 0)
            sizer.Add(self.r_linestyle_list, 0, wx.EXPAND)
            sizer.Add(linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.r_linewidth, 0, wx.EXPAND)
            sizer.Add(linecolour_label, 0)
            sizer.Add(self.r_line_colour, 0, wx.EXPAND)

            box.Add(sizer, 0, wx.ALL, 5)

        elif line == self.qo_line:
            topbox = wx.StaticBox(self, -1, 'Line')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            linewidth_label = wx.StaticText(self, -1, 'Width :')
            linestyle_label = wx.StaticText(self, -1, 'Style :')
            linecolour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.qo_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.qo_linewidth.SetValue(str(self._old_qo_linewidth))
            self.qo_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.qo_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.qo_linestyle_list.Select(self.linestyle_list_choices.index(str(self.qo_linestyle)))
            self.qo_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.qo_line_colour = wx.Panel(self, -1, name = 'QoLineColour', style = wx.RAISED_BORDER)
            self.qo_line_colour.SetBackgroundColour(self.qo_linecolour)
            self.qo_line_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)

            sizer.Add(linestyle_label, 0)
            sizer.Add(self.qo_linestyle_list, 0, wx.EXPAND)
            sizer.Add(linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.qo_linewidth, 0, wx.EXPAND)
            sizer.Add(linecolour_label, 0)
            sizer.Add(self.qo_line_colour, 0, wx.EXPAND)

            box.Add(sizer, 0, wx.ALL, 5)

        elif line == self.qf_line:
            topbox = wx.StaticBox(self, -1, 'Line')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            linewidth_label = wx.StaticText(self, -1, 'Width :')
            linestyle_label = wx.StaticText(self, -1, 'Style :')
            linecolour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.qf_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.qf_linewidth.SetValue(str(self._old_qf_linewidth))
            self.qf_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.qf_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.qf_linestyle_list.Select(self.linestyle_list_choices.index(str(self.qf_linestyle)))
            self.qf_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.qf_line_colour = wx.Panel(self, -1, name = 'QfLineColour', style = wx.RAISED_BORDER)
            self.qf_line_colour.SetBackgroundColour(self.qf_linecolour)
            self.qf_line_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)

            sizer.Add(linestyle_label, 0)
            sizer.Add(self.qf_linestyle_list, 0, wx.EXPAND)
            sizer.Add(linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.qf_linewidth, 0, wx.EXPAND)
            sizer.Add(linecolour_label, 0)
            sizer.Add(self.qf_line_colour, 0, wx.EXPAND)

            box.Add(sizer, 0, wx.ALL, 5)

        return box

    def getLegendLabel(self):
        data = {self.r_line : self.r_legend_label_text.GetValue(),
                self.qo_line : self.qo_legend_label_text.GetValue(),
                self.qf_line : self.qf_legend_label_text.GetValue()}
        return data

    def updateErrorLines(self, data):

        if data[2] == self.r_line:
            for each in self.iftm.r_err_line:
                for line in each:
                    func, param = data[0], data[1]
                    getattr(line, func)(param)

        elif data[2] == self.qo_line:
            for each in self.iftm.qo_err_line:
                for line in each:
                    func, param = data[0], data[1]
                    getattr(line, func)(param)


    def updateLine(self, event):
        marker =  self.r_mar_linemarker_list.GetStringSelection()
        width =  float(self.r_linewidth.GetValue())
        style =  self.r_linestyle_list.GetStringSelection()

        mar_size = float(self.r_mar_size.GetValue())
        err_linewidth = float(self.r_err_linewidth.GetValue())
        err_linestyle = self.r_err_linestyle_list.GetStringSelection()

        self.r_line.set_marker(marker)

        colour =  self.r_mar_linecolour.GetBackgroundColour()
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self.updateErrorLines(['set_linewidth', err_linewidth, self.r_line])

        each = self.iftm.r_err_line[1]
        if err_linestyle != "None":
            for line in each:
                line.set_linestyle(err_linestyle)

        self.r_line.set_markeredgecolor(colour)
        self.r_line.set_linewidth(width)
        self.r_line.set_linestyle(style)
        #self.line.set_color(colour)
        self.r_line.set_markersize(mar_size)


        marker =  self.qo_mar_linemarker_list.GetStringSelection()
        width =  float(self.qo_linewidth.GetValue())
        style =  self.qo_linestyle_list.GetStringSelection()

        mar_size = float(self.qo_mar_size.GetValue())
        err_linewidth = float(self.qo_err_linewidth.GetValue())
        err_linestyle = self.qo_err_linestyle_list.GetStringSelection()

        self.qo_line.set_marker(marker)

        colour =  self.qo_mar_linecolour.GetBackgroundColour()
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self.updateErrorLines(['set_linewidth', err_linewidth, self.qo_line])

        each = self.iftm.qo_err_line[1]
        if err_linestyle != "None":
            for line in each:
                line.set_linestyle(err_linestyle)

        self.qo_line.set_markeredgecolor(colour)
        self.qo_line.set_linewidth(width)
        self.qo_line.set_linestyle(style)
        #self.line.set_color(colour)
        self.qo_line.set_markersize(mar_size)


        marker =  self.qf_mar_linemarker_list.GetStringSelection()
        width =  float(self.qf_linewidth.GetValue())
        style =  self.qf_linestyle_list.GetStringSelection()

        mar_size = float(self.qf_mar_size.GetValue())

        self.qf_line.set_marker(marker)

        colour =  self.qf_mar_linecolour.GetBackgroundColour()
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self.qf_line.set_markeredgecolor(colour)
        self.qf_line.set_linewidth(width)
        self.qf_line.set_linestyle(style)
        #self.line.set_color(colour)
        self.qf_line.set_markersize(mar_size)


        self.iftm.plot_panel.canvas.draw()

        if event is not None:
            event.Skip()

    def _onCancelButton(self, event):
        self.r_line.set_linewidth(self._old_r_linewidth)
        self.r_line.set_linestyle(self._old_r_linestyle)
        self.r_line.set_color(self._old_r_linecolour)

        self.r_line.set_marker(self._old_r_linemarker)
        self.r_line.set_markeredgecolor(self._old_r_marlinecolour)
        self.r_line.set_markerfacecolor(self._old_r_marcolour)
        self.r_line.set_markersize(self._old_r_marsize)


        self.qo_line.set_linewidth(self._old_qo_linewidth)
        self.qo_line.set_linestyle(self._old_qo_linestyle)
        self.qo_line.set_color(self._old_qo_linecolour)

        self.qo_line.set_marker(self._old_qo_linemarker)
        self.qo_line.set_markeredgecolor(self._old_qo_marlinecolour)
        self.qo_line.set_markerfacecolor(self._old_qo_marcolour)
        self.qo_line.set_markersize(self._old_qo_marsize)


        self.qf_line.set_linewidth(self._old_qf_linewidth)
        self.qf_line.set_linestyle(self._old_qf_linestyle)
        self.qf_line.set_color(self._old_qf_linecolour)

        self.qf_line.set_marker(self._old_qf_linemarker)
        self.qf_line.set_markeredgecolor(self._old_qf_marlinecolour)
        self.qf_line.set_markerfacecolor(self._old_qf_marcolour)
        self.qf_line.set_markersize(self._old_qf_marsize)

        # Stupid errorbars:
        line1, line2 = self.iftm.r_err_line
        for each in line2:
            each.set_linestyle(self._old_r_errlinestyle)
            each.set_linewidth(self._old_r_errlinewidth)
            each.set_color(self._old_r_errcolour)
        for each in line1:
            each.set_linewidth(self._old_r_errlinewidth)
            each.set_color(self._old_r_errcolour)

        line1, line2 = self.iftm.qo_err_line
        for each in line2:
            each.set_linestyle(self._old_qo_errlinestyle)
            each.set_linewidth(self._old_qo_errlinewidth)
            each.set_color(self._old_qo_errcolour)
        for each in line1:
            each.set_linewidth(self._old_qo_errlinewidth)
            each.set_color(self._old_qo_errcolour)

        self.iftm.plot_panel.canvas.draw()

        self.EndModal(wx.ID_CANCEL)

    def _onOkButton(self, event):
        self.updateLine(None)

        self.EndModal(wx.ID_OK)


class SECMLinePropertyDialog(wx.Dialog):

    def __init__(self, parent, secm, legend_label, size = (433, 549), style = wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, *args, **kwargs):

        if secm.line is None:
            wx.MessageBox('Unable to change line properties.\nNo plot has been made for this item.', 'No plot')
            return


        wx.Dialog.__init__(self, parent, -1, "Series Line Properties", size = size, style = style, *args, **kwargs)

        self.secm = secm
        self.line = secm.line
        self.calc_line = secm.calc_line
        self.legend_label = legend_label

        self.linewidth_combo_choices = ['1.0', '2.0', '3.0', '4.0', '5.0']
        self.linestyle_list_choices = ['None', '-', '--', '-.', ':']
        self.linemarker_list_choices = ['None', '+', '*', ',','.','1','2','3','4','<', '>', 'D', 'H', '^','_','d','h','o','p','s','v','x','|']

        self._linestyle = self.line.get_linestyle()
        self._linemarker = self.line.get_marker()
        self._linewidth = self.line.get_linewidth()

        self._calclinestyle = self.calc_line.get_linestyle()
        self._calclinemarker = self.calc_line.get_marker()
        self._calclinewidth = self.calc_line.get_linewidth()

        conv = mplcol.ColorConverter()
        color = conv.to_rgb(self.line.get_color())
        calc_color = conv.to_rgb(self.calc_line.get_color())
        self._old_linecolour = color
        self._old_calclinecolour = calc_color
        color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        calc_color = wx.Colour(int(calc_color[0]*255), int(calc_color[1]*255), int(calc_color[2]*255))
        self._linecolour = color
        self._calclinecolour = calc_color


        mfc = self.line.get_markerfacecolor()

        if mfc != "None":
            color = conv.to_rgb(mfc)
            self._marcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.hollow_marker = False
        else:
            color = conv.to_rgb(self.line.get_markeredgecolor())
            self._marcolour =  wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.hollow_marker = True

        mfc_calc = self.calc_line.get_markerfacecolor()
        if mfc_calc != "None":
            color = conv.to_rgb(mfc_calc)
            self._calcmarcolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.hollow_marker_calc = False
        else:
            color = conv.to_rgb(self.calc_line.get_markeredgecolor())
            self._calcmarcolour =  wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            self.hollow_marker_calc = True

        color = conv.to_rgb(self.line.get_markeredgecolor())
        self._marlinecolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

        color = conv.to_rgb(self.calc_line.get_markeredgecolor())
        self._calcmarlinecolour = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))


        self._old_linestyle = self.line.get_linestyle()
        self._old_linemarker = self.line.get_marker()
        self._old_linewidth = self.line.get_linewidth()
        self._old_marcolour = self.line.get_markerfacecolor()
        self._old_marlinecolour = self.line.get_markeredgecolor()
        self._old_marsize = self.line.get_markersize()

        self._old_calclinestyle = self.calc_line.get_linestyle()
        self._old_calclinemarker = self.calc_line.get_marker()
        self._old_calclinewidth = self.calc_line.get_linewidth()
        self._old_calcmarcolour = self.calc_line.get_markerfacecolor()
        self._old_calcmarlinecolour = self.calc_line.get_markeredgecolor()
        self._old_calcmarsize = self.calc_line.get_markersize()


        top_sizer = wx.BoxSizer(wx.VERTICAL)

        buttonsizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind( wx.EVT_BUTTON, self._onOkButton, id=wx.ID_OK )
        self.Bind( wx.EVT_BUTTON, self._onCancelButton, id=wx.ID_CANCEL )

        sec_box = wx.StaticBox(self, -1, 'Series Line')
        secline_sizer = wx.StaticBoxSizer(sec_box, wx.VERTICAL)

        line_legend = self._createLegendLabelControls(self.line)

        linesettings_sizer = wx.FlexGridSizer(cols = 5, rows = 1, vgap = 5, hgap = 10)
        linesettings_sizer.AddGrowableCol(0)
        linesettings_sizer.AddGrowableCol(2)
        linesettings_sizer.AddGrowableCol(4)

        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.Add(self._createLineControls(), 1, wx.EXPAND)
        linesettings_sizer.AddStretchSpacer(1)
        linesettings_sizer.Add(self._createLineMarkerControls(), 1, wx.EXPAND)
        linesettings_sizer.AddStretchSpacer(1)

        secline_sizer.Add(line_legend, 0, wx.ALL | wx.EXPAND, 5)
        secline_sizer.Add(linesettings_sizer, 0, wx.ALL | wx.EXPAND, 5)


        calc_box = wx.StaticBox(self, -1, 'Calculated Line')
        calcline_sizer = wx.StaticBoxSizer(calc_box, wx.VERTICAL)

        calc_legend = self._createLegendLabelControls(self.calc_line)

        calclinesettings_sizer = wx.FlexGridSizer(cols = 5, rows = 1, vgap = 5, hgap = 10)
        calclinesettings_sizer.AddGrowableCol(0)
        calclinesettings_sizer.AddGrowableCol(2)
        calclinesettings_sizer.AddGrowableCol(4)

        calclinesettings_sizer.AddStretchSpacer(1)
        calclinesettings_sizer.Add(self._createLineControls(calc = True), 1, wx.EXPAND)
        calclinesettings_sizer.AddStretchSpacer(1)
        calclinesettings_sizer.Add(self._createLineMarkerControls(calc = True), 1, wx.EXPAND)
        calclinesettings_sizer.AddStretchSpacer(1)

        calcline_sizer.Add(calc_legend, 0, wx.ALL | wx.EXPAND, 5)
        calcline_sizer.Add(calclinesettings_sizer, 0, wx.ALL | wx.EXPAND, 5)


        top_sizer.Add(secline_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(calcline_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.AddStretchSpacer(1)
        top_sizer.Add(buttonsizer, 0, wx.CENTER | wx.ALL, 5)

        self.SetSizer(top_sizer)

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()


    def _createLegendLabelControls(self, line):

        if line == self.line:
            topbox = wx.StaticBox(self, -1, 'Legend Label')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            self.line_legend_label_text = wx.TextCtrl(self, -1, self.legend_label[self.line])

            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(self.line_legend_label_text, 1, wx.EXPAND)

            box.Add(sizer, 0, wx.EXPAND | wx.ALL, 5)

        elif line == self.calc_line:
            topbox = wx.StaticBox(self, -1, 'Legend Label')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            self.calc_legend_label_text = wx.TextCtrl(self, -1, self.legend_label[self.calc_line])

            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(self.calc_legend_label_text, 1, wx.EXPAND)

            box.Add(sizer, 0, wx.EXPAND | wx.ALL, 5)


        return box


    def _createErrorBarsControls(self):
        topbox = wx.StaticBox(self, -1, 'Error Bars')
        box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        err_linewidth_label = wx.StaticText(self, -1, 'Width :')
        err_linestyle_label = wx.StaticText(self, -1, 'Style :')
        err_colour_label = wx.StaticText(self, -1, 'Line Colour :')

        self.err_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
        self.err_linewidth.SetValue(str(self._old_errlinewidth))
        self.err_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

        self.err_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
        self.err_linestyle_list.Select(self.linestyle_list_choices.index(str(self._old_errlinestyle)))
        self.err_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

        self.err_colour = wx.Panel(self, -1, name = 'ErrColour', style = wx.RAISED_BORDER)
        self.err_colour.SetBackgroundColour(self._errcolour)
        self.err_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

        sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
        sizer.Add(err_linestyle_label, 0)
        sizer.Add(self.err_linestyle_list, 0, wx.EXPAND)
        sizer.Add(err_linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.err_linewidth, 0, wx.EXPAND)
        sizer.Add(err_colour_label, 0)
        sizer.Add(self.err_colour, 0, wx.EXPAND)

        box.Add(sizer, 0, wx.ALL, 5)

        return box

    def _onColourPress(self, event):

        colour_panel = event.GetEventObject()

        dlg = ColourChangeDialog(self, self.secm, colour_panel.GetName())
        dlg.ShowModal()
        dlg.Destroy()

        if colour_panel.GetName() == 'LineColour':
            color = self.line.get_color()
        # elif colour_panel.GetName() == 'ErrColour':
            # color = self.secm.err_line[0][0].get_color()
        elif colour_panel.GetName() == 'MarLineColour':
            color = self.line.get_markeredgecolor()
        elif colour_panel.GetName() == 'MarFillColour':
            color = self.line.get_markerfacecolor()

        elif colour_panel.GetName() == 'CalcLineColour':
            color = self.calc_line.get_color()
        # elif colour_panel.GetName() == 'ErrColour':
            # color = self.secm.err_line[0][0].get_color()
        elif colour_panel.GetName() == 'CalcMarLineColour':
            color = self.calc_line.get_markeredgecolor()
        elif colour_panel.GetName() == 'CalcMarFillColour':
            color = self.calc_line.get_markerfacecolor()

        conv = mplcol.ColorConverter()

        if color != "None": #Not transparent
            color = conv.to_rgb(color)
            color = wx.Colour(int(color[0]*255), int(color[1]*255), int(color[2]*255))

            colour_panel.SetBackgroundColour(color)
            colour_panel.Refresh()

    def _createLineMarkerControls(self, calc = False):

        if not calc:
            topbox = wx.StaticBox(self, -1, 'Data Point Marker')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            mar_size_label = wx.StaticText(self, -1, 'Size :')
            self.mar_fillcolour_label = wx.StaticText(self, -1, 'Fill Colour :')
            self.mar_fillcolour_label.Enable(not self.hollow_marker)
            mar_linecolour_label = wx.StaticText(self, -1, 'Line Colour :')
            mar_linemarker_label = wx.StaticText(self, -1, 'Marker :')
            mar_hollow_label = wx.StaticText(self, -1, 'Hollow :')

            #self.mar_size = wx.SpinCtrl(self, -1, '1')
            self.mar_size = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.mar_size.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)
            self.mar_size.SetValue(str(self._old_marsize))
            #self.mar_size.Bind(wx.EVT_SPINCTRL, self.updateLine)

            self.mar_fillcolour = wx.Panel(self, -1, name = 'MarFillColour', style = wx.RAISED_BORDER)
            self.mar_fillcolour.SetBackgroundColour(self._marcolour)
            self.mar_fillcolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)
            self.mar_fillcolour.Enable(not self.hollow_marker)

            self.mar_linecolour = wx.Panel(self, -1, name = 'MarLineColour', style = wx.RAISED_BORDER)
            self.mar_linecolour.SetBackgroundColour(self._marlinecolour)
            self.mar_linecolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            self.mar_linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
            self.mar_linemarker_list.Select(self.linemarker_list_choices.index(str(self._linemarker)))
            self.mar_linemarker_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.mar_hollow = wx.CheckBox(self, -1)
            self.mar_hollow.SetValue(self.hollow_marker)
            self.mar_hollow.Bind(wx.EVT_CHECKBOX, self._onHollowCheckBox)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(mar_linemarker_label, 0)
            sizer.Add(self.mar_linemarker_list, 0, wx.EXPAND)
            sizer.Add(mar_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.mar_size, 0, wx.EXPAND)
            sizer.Add(mar_linecolour_label, 0)
            sizer.Add(self.mar_linecolour, 0, wx.EXPAND)
            sizer.Add(self.mar_fillcolour_label, 0)
            sizer.Add(self.mar_fillcolour, 0, wx.EXPAND)
            sizer.Add(mar_hollow_label, 0)
            sizer.Add(self.mar_hollow, 0, wx.EXPAND)


            box.Add(sizer, 0, wx.ALL, 5)

        else:
            topbox = wx.StaticBox(self, -1, 'Calc Data Point Marker')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            mar_size_label = wx.StaticText(self, -1, 'Size :')
            self.calc_mar_fillcolour_label = wx.StaticText(self, -1, 'Fill Colour :')
            self.calc_mar_fillcolour_label.Enable(not self.hollow_marker_calc)
            mar_linecolour_label = wx.StaticText(self, -1, 'Line Colour :')
            mar_linemarker_label = wx.StaticText(self, -1, 'Marker :')
            mar_hollow_label = wx.StaticText(self, -1, 'Hollow :')

            #self.mar_size = wx.SpinCtrl(self, -1, '1')
            self.calc_mar_size = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.calc_mar_size.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)
            self.calc_mar_size.SetValue(str(self._old_calcmarsize))
            #self.mar_size.Bind(wx.EVT_SPINCTRL, self.updateLine)

            self.calc_mar_fillcolour = wx.Panel(self, -1, name = 'CalcMarFillColour', style = wx.RAISED_BORDER)
            self.calc_mar_fillcolour.SetBackgroundColour(self._calcmarcolour)
            self.calc_mar_fillcolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)
            self.calc_mar_fillcolour.Enable(not self.hollow_marker_calc)

            self.calc_mar_linecolour = wx.Panel(self, -1, name = 'CalcMarLineColour', style = wx.RAISED_BORDER)
            self.calc_mar_linecolour.SetBackgroundColour(self._calcmarlinecolour)
            self.calc_mar_linecolour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            self.calc_mar_linemarker_list = wx.Choice(self, -1, choices = self.linemarker_list_choices)
            self.calc_mar_linemarker_list.Select(self.linemarker_list_choices.index(str(self._calclinemarker)))
            self.calc_mar_linemarker_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.calc_mar_hollow = wx.CheckBox(self, -1)
            self.calc_mar_hollow.SetValue(self.hollow_marker_calc)
            self.calc_mar_hollow.Bind(wx.EVT_CHECKBOX, self._onHollowCheckBoxCalc)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)
            sizer.Add(mar_linemarker_label, 0)
            sizer.Add(self.calc_mar_linemarker_list, 0, wx.EXPAND)
            sizer.Add(mar_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.calc_mar_size, 0, wx.EXPAND)
            sizer.Add(mar_linecolour_label, 0)
            sizer.Add(self.calc_mar_linecolour, 0, wx.EXPAND)
            sizer.Add(self.calc_mar_fillcolour_label, 0)
            sizer.Add(self.calc_mar_fillcolour, 0, wx.EXPAND)
            sizer.Add(mar_hollow_label, 0)
            sizer.Add(self.calc_mar_hollow, 0, wx.EXPAND)


            box.Add(sizer, 0, wx.ALL, 5)

        return box

    def _onHollowCheckBox(self, event):

        chkbox = event.GetEventObject()

        if chkbox.GetValue() == True:
            self.line.set_markerfacecolor("None")
            self.secm.plot_panel.canvas.draw()
            self.mar_fillcolour.Enable(False)
            self.mar_fillcolour_label.Enable(False)
        else:
            self.mar_fillcolour.Enable(True)
            self.mar_fillcolour_label.Enable(True)
            colour =  self.mar_fillcolour.GetBackgroundColour()
            colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)
            self.line.set_markerfacecolor(colour)
            self.secm.plot_panel.canvas.draw()

    def _onHollowCheckBoxCalc(self, event):

        chkbox = event.GetEventObject()

        if chkbox.GetValue() == True:
            self.calc_line.set_markerfacecolor("None")
            self.secm.plot_panel.canvas.draw()
            self.calc_mar_fillcolour.Enable(False)
            self.calc_mar_fillcolour_label.Enable(False)
        else:
            self.calc_mar_fillcolour.Enable(True)
            self.calc_mar_fillcolour_label.Enable(True)
            colour =  self.calc_mar_fillcolour.GetBackgroundColour()
            colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)
            self.calc_line.set_markerfacecolor(colour)
            self.secm.plot_panel.canvas.draw()

    def _createLineControls(self, calc = False):

        if not calc:
            topbox = wx.StaticBox(self, -1, 'Line')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            linewidth_label = wx.StaticText(self, -1, 'Width :')
            linestyle_label = wx.StaticText(self, -1, 'Style :')
            linecolour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.linewidth.SetValue(str(self._old_linewidth))
            self.linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.linestyle_list.Select(self.linestyle_list_choices.index(str(self._linestyle)))
            self.linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.line_colour = wx.Panel(self, -1, name = 'LineColour', style = wx.RAISED_BORDER)
            self.line_colour.SetBackgroundColour(self._linecolour)
            self.line_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)

            sizer.Add(linestyle_label, 0)
            sizer.Add(self.linestyle_list, 0, wx.EXPAND)
            sizer.Add(linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.linewidth, 0, wx.EXPAND)
            sizer.Add(linecolour_label, 0)
            sizer.Add(self.line_colour, 0, wx.EXPAND)

            box.Add(sizer, 0, wx.ALL, 5)

        else:
            topbox = wx.StaticBox(self, -1, 'Calc Line')
            box = wx.StaticBoxSizer(topbox, wx.VERTICAL)

            linewidth_label = wx.StaticText(self, -1, 'Width :')
            linestyle_label = wx.StaticText(self, -1, 'Style :')
            linecolour_label = wx.StaticText(self, -1, 'Line Colour :')

            self.calc_linewidth = RAWCustomCtrl.FloatSpinCtrl(self, -1, '1.0', TextLength = 60, never_negative = True)
            self.calc_linewidth.SetValue(str(self._old_calclinewidth))
            self.calc_linewidth.Bind(RAWCustomCtrl.EVT_MY_SPIN, self.updateLine)

            self.calc_linestyle_list = wx.Choice(self, -1, choices = self.linestyle_list_choices)
            self.calc_linestyle_list.Select(self.linestyle_list_choices.index(str(self._calclinestyle)))
            self.calc_linestyle_list.Bind(wx.EVT_CHOICE, self.updateLine)

            self.calc_line_colour = wx.Panel(self, -1, name = 'CalcLineColour', style = wx.RAISED_BORDER)
            self.calc_line_colour.SetBackgroundColour(self._calclinecolour)
            self.calc_line_colour.Bind(wx.EVT_LEFT_DOWN, self._onColourPress)

            sizer = wx.FlexGridSizer(cols = 2, rows = 5, vgap = 5, hgap = 3)

            sizer.Add(linestyle_label, 0)
            sizer.Add(self.calc_linestyle_list, 0, wx.EXPAND)
            sizer.Add(linewidth_label, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.calc_linewidth, 0, wx.EXPAND)
            sizer.Add(linecolour_label, 0)
            sizer.Add(self.calc_line_colour, 0, wx.EXPAND)

            box.Add(sizer, 0, wx.ALL, 5)

        return box

    def getLegendLabel(self):
        data = {self.line       : self.line_legend_label_text.GetValue(),
                self.calc_line  : self.calc_legend_label_text.GetValue()}

        return data

    def updateErrorLines(self, data):

        for each in self.secm.err_line:
            for line in each:
                func, param = data
                getattr(line, func)(param)


    def updateLine(self, event):
        marker =  self.mar_linemarker_list.GetStringSelection()
        width =  float(self.linewidth.GetValue())
        style =  self.linestyle_list.GetStringSelection()

        mar_size = float(self.mar_size.GetValue())

        self.line.set_marker(marker)

        colour =  self.mar_linecolour.GetBackgroundColour()
        colour =  (colour[0]/255.0, colour[1]/255.0, colour[2]/255.0)

        self.line.set_markeredgecolor(colour)
        self.line.set_linewidth(float(width))
        self.line.set_linestyle(style)
        self.line.set_markersize(float(mar_size))


        calc_marker =  self.calc_mar_linemarker_list.GetStringSelection()
        calc_width =  float(self.calc_linewidth.GetValue())
        calc_style =  self.calc_linestyle_list.GetStringSelection()

        calc_mar_size = float(self.calc_mar_size.GetValue())

        self.calc_line.set_marker(calc_marker)

        calc_colour =  self.calc_mar_linecolour.GetBackgroundColour()
        calc_colour =  (calc_colour[0]/255.0, calc_colour[1]/255.0, calc_colour[2]/255.0)

        self.calc_line.set_markeredgecolor(calc_colour)
        self.calc_line.set_linewidth(calc_width)
        self.calc_line.set_linestyle(calc_style)
        self.calc_line.set_markersize(calc_mar_size)

        self.secm.plot_panel.canvas.draw()

        if event is not None:
            event.Skip()

    def _onCancelButton(self, event):
        self.line.set_linewidth(self._old_linewidth)
        self.line.set_linestyle(self._old_linestyle)
        self.line.set_color(self._old_linecolour)

        self.line.set_marker(self._old_linemarker)
        self.line.set_markeredgecolor(self._old_marlinecolour)
        self.line.set_markerfacecolor(self._old_marcolour)
        self.line.set_markersize(self._old_marsize)


        self.calc_line.set_linewidth(self._old_calclinewidth)
        self.calc_line.set_linestyle(self._old_calclinestyle)
        self.calc_line.set_color(self._old_calclinecolour)

        self.calc_line.set_marker(self._old_calclinemarker)
        self.calc_line.set_markeredgecolor(self._old_calcmarlinecolour)
        self.calc_line.set_markerfacecolor(self._old_calcmarcolour)
        self.calc_line.set_markersize(self._old_calcmarsize)

        self.secm.plot_panel.canvas.draw()

        self.EndModal(wx.ID_CANCEL)

    def _onOkButton(self, event):
        self.updateLine(None)

        self.EndModal(wx.ID_OK)

class CustomQuestionDialog(wx.Dialog):

    def __init__(self, parent,
                 question_text,
                 button_list,
                 title,
                 icon = None,
                 filename = None,
                 current_dir = None,
                 *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, title, *args, **kwargs)

        self.icon = icon
        self._path = None
        self._filename = filename
        self._current_directory = current_dir

        self.question_text = question_text
        self.button_list = button_list

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        button_panel = self._createButtonPanel()
        question_panel = CustomQuestionPanel(self, question_text, icon)

        self.main_sizer.Add(question_panel, 1, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 15)
        self.main_sizer.Add(button_panel, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.SetSizer(self.main_sizer)

        self.Layout()

        bp_size = self.button.GetBestSize()
        qp_size = question_panel.question_label.GetBestSize()
        icn_size = question_panel.bitmap.GetBestSize()

        total_width = qp_size[0]+icn_size[0]+55
        total_height = qp_size[1]+bp_size[1]+75

        self.SetMaxSize((800,600))

        panel_size = self.GetBestSize()

        best_width = min(800, max(total_width, panel_size[0]))
        best_height = min(600, max(total_height, panel_size[1]))

        if best_width == 800 and best_height<600:
            best_height = min(600, best_height+20)
        if best_height == 600 and best_width < 800:
            best_width = min(800, best_width+20)

        client_display = wx.GetClientDisplayRect()
        best_width = min(best_width, client_display.Width)
        best_height = min(best_height, client_display.Height)

        self.SetSize((best_width, best_height))

    def _createButtonPanel(self):

        button_panel = wx.BoxSizer()

        for button_label, id in self.button_list:
            self.button = wx.Button(self, id, button_label)

            if (button_label, id) != self.button_list[-1]:
                button_panel.Add(self.button, 0, wx.RIGHT, 5)
            else:
                button_panel.Add(self.button, 0)

            self.button.Bind(wx.EVT_BUTTON, self._onButton)

        return button_panel

    def _onButton(self, event):
        id = event.GetId()

        if id == wx.ID_EDIT:
            self._onRenameButton()
        else:
            self.EndModal(id)

    def _onRenameButton(self):
        ok = self._openFileDialog(self._filename)

        if ok:
            self.EndModal(wx.ID_EDIT)

    def _openFileDialog(self, filename):
        """
        Create and show the Open FileDialog
        """
        dlg = wx.FileDialog(
            self, message="Choose filename and location.",
            defaultDir=self._current_directory,
            defaultFile=filename,
            wildcard = "All files (*.*)|*.*",

            style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE)

        dlg.SetDirectory(self._current_directory)

        result = dlg.ShowModal()

        if result == wx.ID_OK:
            self._path = dlg.GetPath()

        dlg.Destroy()

        if self._path:
            return True
        else:
            return False

    def getPath(self):
        return self._path

class CustomQuestionPanel(wx.lib.scrolledpanel.ScrolledPanel):

    def __init__(self, parent, question_text, icon):

        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY)

        vbox = wx.BoxSizer(wx.HORIZONTAL)
        self.question_label = wx.StaticText(self, -1, question_text)

        if icon:
            cbmp = wx.ArtProvider.GetBitmap(icon,  wx.ART_MESSAGE_BOX)
            self.bitmap = wx.StaticBitmap(self, -1, cbmp)
            vbox.Add(self.bitmap, 0,  wx.RIGHT, 15)

        vbox.Add(self.question_label, 1, wx.EXPAND)

        self.SetSizer(vbox)
        self.SetupScrolling()
        self.Layout()
        self.SetMinSize((200,100))

class PlotOptionsDialog(wx.Dialog):
    def __init__(self, parent, plotparams, axes, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Plot Options' , size = (575,522),
            style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX, *args, **kwargs)

        self.axes = axes
        self.plotparams = plotparams
        self.parent = parent

        if self.parent == wx.FindWindowByName('SECPlotPanel'):
            self.is_sec = True
            self.sec_calc = self.plotparams['secm_plot_calc']
            self.axes = self.parent.subplot1
            self.axes2 = self.parent.ryaxis
        else:
            self.is_sec = False


        plotnum = str(self.parent.selected_plot)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.legend = self.axes.get_legend()

        self._old_xlimit = self.axes.get_xlim()
        self._old_ylimit = self.axes.get_ylim()

        if self.is_sec:
            self._old_y2limit = self.axes2.get_ylim()

        self._old_legend_settings = {'fontsize'     : self.parent.plotparams['legend_fontsize'+plotnum],
                                        'font'      : self.parent.plotparams['legend_font' + plotnum],
                                        'alpha'     : self.parent.plotparams['legend_alpha'+plotnum],
                                        'border'    : self.parent.plotparams['legend_border'+plotnum],
                                        'shadow'    : self.parent.plotparams['legend_shadow'+plotnum],
                                        'visible'   : self.parent.plotparams['legend_visible'+plotnum]}

        if self.is_sec:
            self._old_legend_settings ['showcalc'] = self.parent.plotparams['legend_showcalc'+plotnum]

        if self.legend is None:
            self.is_legend = False
        else:
            self.is_legend = True

        self._old_settings = {'title' : {},
                                'xlabel' : {},
                                'ylabel' : {},
                                'legtit' : {}}

        if self.is_sec and self.sec_calc != 'None':
            self._old_settings['y2label'] = {}

        self.font_list = self._getFonts()

        self.title = self.axes.title
        self.xlabel = self.axes.xaxis.get_label()
        self.ylabel = self.axes.yaxis.get_label()

        if self.is_sec and self.sec_calc != 'None':
            self.y2label = self.axes2.yaxis.get_label()

        legax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        legax_sizer.Add(self._createLegendSettings(), 0, wx.EXPAND)
        legax_sizer.AddStretchSpacer(1)
        legax_sizer.Add(self._createAxesSettings(), 0, wx.LEFT | wx.EXPAND, 10)

        sizer.Add(self._createLabelSettings(), 0, wx.EXPAND)
        sizer.Add(legax_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.Bind(wx.EVT_BUTTON, self._onOk, id = wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)

        sizer.Add(buttons, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        top_sizer = wx.BoxSizer()
        top_sizer.Add(sizer,1, wx.ALL, 10)

        self.SetSizer(top_sizer)

        best_size = self.GetBestSize()
        current_size = self.GetSize()

        client_display = wx.GetClientDisplayRect()
        if best_size.GetWidth() > current_size.GetWidth():
            best_width = min(best_size.GetWidth(), client_display.Width)
            best_size.SetWidth(best_width)
        else:
            best_size.SetWidth(current_size.GetWidth())

        if best_size.GetHeight() > current_size.GetHeight():
            best_height = min(best_size.GetHeight(), client_display.Height)
            best_size.SetHeight(best_height)
        else:
            best_size.SetHeight(current_size.GetHeight())

        self.SetSize(best_size)

        self.CenterOnParent()


    def _getFonts(self):
        font_list = fm.get_fontconfig_fonts()

        names=[]

        for item in font_list:
            try:
                font_name = fm.FontProperties(fname=item).get_name()

                if font_name != 'System Font' and not font_name.startswith('.'):
                    names.append(font_name)
            except:
                pass

        mpl_font_dir = os.path.join(matplotlib.rcParams['datapath'],'fonts/ttf')
        font_list2 = fm.list_fonts(mpl_font_dir, '*.ttf')

        for item in font_list2:
            fp = fm.FontProperties()
            try:
                fp.set_file(item)
                font_name = fp.get_name()
                if font_name != 'System Font' and not font_name.startswith('.'):
                    names.append(font_name)
            except:
                pass

        names = sorted(set(names))

        return names

    def _createLabelSettings(self):

        self.labels = [('Title:', 'title', {'text'  : self.NewControlId(),
                                               'size'  : self.NewControlId(),
                                               'weight': self.NewControlId(),
                                               'style' : self.NewControlId(),
                                               'fontname'  : self.NewControlId()}),

                      ('x-axis label:', 'xlabel',{'text'  : self.NewControlId(),
                                                  'size'  : self.NewControlId(),
                                                  'weight': self.NewControlId(),
                                                  'style' : self.NewControlId(),
                                                  'fontname'  : self.NewControlId()}),

                      ('y-axis label:', 'ylabel',{'text'  : self.NewControlId(),
                                                  'size'  : self.NewControlId(),
                                                  'weight': self.NewControlId(),
                                                  'style' : self.NewControlId(),
                                                  'fontname'  : self.NewControlId()}),

                      ('Legend title:', 'legtit',{'text'  : self.NewControlId(),
                                                  'size'  : self.NewControlId(),
                                                  'weight': self.NewControlId(),
                                                  'style' : self.NewControlId(),
                                                  'fontname'  : self.NewControlId()})]

        if self.is_sec and self.sec_calc != 'None':
            self.labels.insert(3, ('y-axis (right) label:', 'y2label',{'text'  : self.NewControlId(),
                                                  'size'  : self.NewControlId(),
                                                  'weight': self.NewControlId(),
                                                  'style' : self.NewControlId(),
                                                  'fontname'  : self.NewControlId()})
                                )

        box = wx.StaticBox(self, -1, 'Labels')
        box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        nrows = len(self.labels)+1
        sizer = wx.FlexGridSizer(cols = 6, rows = nrows, vgap = 5, hgap = 5)

        sizer.Add((5,5),0)
        sizer.Add((5,5),0)
        sizer.Add(wx.StaticText(self, -1, 'Font'),1)
        sizer.Add(wx.StaticText(self, -1, 'Size'),1)
        sizer.Add(wx.StaticText(self, -1, 'Bold'),1)
        sizer.Add(wx.StaticText(self, -1, 'Italic'),1)

        for each_label, each_name, id in self.labels:
            if each_name == 'title': label = self.title
            elif each_name == 'xlabel': label = self.xlabel
            elif each_name == 'ylabel': label = self.ylabel
            elif each_name == 'y2label': label = self.y2label
            elif each_name == 'legtit':
                if self.legend is None:
                    label=matplotlib.text.Text()
                else:
                    label = self.legend.get_title()

            txt = wx.StaticText(self, -1, each_label)

            labtxt = label.get_text()

            if each_name == 'legtit':
                 if labtxt == 'None': labtxt = ''

            txt_ctrl = wx.TextCtrl(self, id['text'], labtxt, name = each_name)

            font_ctrl = wx.Choice(self, id['fontname'], choices = self.font_list ,name = each_name)
            if each_name == 'legtit' and not self.is_legend:
                font_ctrl.SetStringSelection(self._old_legend_settings['font'])
            else:
                font_ctrl.SetStringSelection(label.get_fontname())

            font_size = wx.SpinCtrl(self, id['size'], str(label.get_size()), name = each_name)
            font_size.SetValue(int(label.get_size()))

            bold = wx.CheckBox(self, id['weight'], name = each_name)
            italic = wx.CheckBox(self, id['style'], name = each_name)

            bold.Bind(wx.EVT_CHECKBOX, self._updateLabels)
            italic.Bind(wx.EVT_CHECKBOX, self._updateLabels)
            txt_ctrl.Bind(wx.EVT_KEY_UP, self._updateLabels)
            font_ctrl.Bind(wx.EVT_CHOICE, self._updateLabels)
            font_size.Bind(wx.EVT_SPINCTRL, self._updateLabels)

            if label.get_weight() == 'bold':
                bold.SetValue(True)
            if label.get_style() == 'italic':
                italic.SetValue(True)

            self._old_settings[each_name]['text'] = label.get_text()
            self._old_settings[each_name]['weight'] = label.get_weight()
            self._old_settings[each_name]['size'] = label.get_size()
            self._old_settings[each_name]['style'] = label.get_style()
            self._old_settings[each_name]['fontname'] = label.get_fontname()

            if each_name == 'legtit' and not self.is_legend:
                txt_ctrl.Enable(False)
                font_ctrl.Enable(False)
                font_size.Enable(False)
                bold.Enable(False)
                italic.Enable(False)

            sizer.Add(txt, 0)
            sizer.Add(txt_ctrl, 0)
            sizer.Add(font_ctrl, 0)
            sizer.Add(font_size, 0)
            sizer.Add(bold, 0)
            sizer.Add(italic, 0)

        box_sizer.Add(sizer, 1, wx.ALL, 5)
        return box_sizer


    def _createAxesSettings(self):
        box = wx.StaticBox(self, -1, 'Axes')
        topbox = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer = wx.FlexGridSizer(rows = 7, cols = 2, hgap = 5, vgap = 3)

        self.axes_autolimits = wx.CheckBox(self, -1)
        self.axes_autolimits.Bind(wx.EVT_CHECKBOX, self._updateAxesSettings)

        val = self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)]
        self.axes_autolimits.SetValue(val)

        sizer.Add(wx.StaticText(self, -1, 'Auto limits:'), 0, wx.ALIGN_CENTRE_VERTICAL)
        sizer.Add(self.axes_autolimits, 0)

        self.axes_fixed_limits_data = [('xmin', self.NewControlId(), self._old_xlimit[0]),
                                           ('xmax', self.NewControlId(), self._old_xlimit[1]),
                                           ('ymin', self.NewControlId(), self._old_ylimit[0]),
                                           ('ymax', self.NewControlId(), self._old_ylimit[1])]

        if self.is_sec and self.sec_calc != 'None':
            self.axes_fixed_limits_data = self.axes_fixed_limits_data + [('y2min', self.NewControlId(), self._old_y2limit[0]),
                                           ('y2max', self.NewControlId(), self._old_y2limit[1])]

        limit_sizer = wx.FlexGridSizer(rows = 2, cols = 2, hgap = 5, vgap = 3)
        for i in range(0, 2):
            id = self.axes_fixed_limits_data[i][1]
            limit_sizer.Add(wx.TextCtrl(self, id, str(self.axes_fixed_limits_data[i][2]), size = (80, -1)), 0)
            wx.FindWindowById(id, self).Bind(wx.EVT_TEXT, self._updateAxesRange)

        limit_sizer2 = wx.FlexGridSizer(rows = 1, cols = 2, hgap = 5, vgap = 3)
        for i in range(2, 4):
            id = self.axes_fixed_limits_data[i][1]
            limit_sizer2.Add(wx.TextCtrl(self, id, str(self.axes_fixed_limits_data[i][2]), size = (80, -1)), 0)
            wx.FindWindowById(id, self).Bind(wx.EVT_TEXT, self._updateAxesRange)

        if self.is_sec and self.sec_calc != 'None':
            limit_sizer3 = wx.FlexGridSizer(rows = 1, cols = 2, hgap = 5, vgap = 3)
            for i in range(4, 6):
                id = self.axes_fixed_limits_data[i][1]
                limit_sizer3.Add(wx.TextCtrl(self, id, str(self.axes_fixed_limits_data[i][2]), size = (80, -1)), 0)
                wx.FindWindowById(id, self).Bind(wx.EVT_TEXT, self._updateAxesRange)

        maxmin_sizer = wx.BoxSizer()
        maxmin_sizer.Add(wx.StaticText(self, -1, 'min'), 1, wx.EXPAND | wx.ALIGN_CENTRE_HORIZONTAL)
        maxmin_sizer.Add(wx.StaticText(self, -1, 'max'), 1, wx.EXPAND | wx.LEFT, 5)

        sizer.Add((5,5))
        sizer.Add(maxmin_sizer, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, -1, 'x-limits'), 0)
        sizer.Add(limit_sizer, 0)
        if self.is_sec and self.sec_calc != 'None':
            sizer.Add(wx.StaticText(self, -1, 'y-limits (left)'), 0)
            sizer.Add(limit_sizer2, 0)
            sizer.Add(wx.StaticText(self, -1, 'y-limits (right)'), 0)
            sizer.Add(limit_sizer3, 0)

        else:
            sizer.Add(wx.StaticText(self, -1, 'y-limits'), 0)
            sizer.Add(limit_sizer2, 0)

        border_sizer = wx.FlexGridSizer(rows = 2, cols = 2, hgap = 5, vgap = 3)

        self.axes_borders = [('Left', self.NewControlId()), ('Right', self.NewControlId()), ('Top', self.NewControlId()), ('Bottom', self.NewControlId())]

        framestyle = self.parent.plotparams['framestyle' + str(self.parent.selected_plot)]

        if self.is_sec and self.sec_calc != 'None':
            framestyle2 = self.parent.plotparams['framestyle2']
            framestyle = framestyle+framestyle2

        for each, id in self.axes_borders:
            border_sizer.Add(wx.CheckBox(self, id, each), 0, wx.RIGHT, 5)
            wx.FindWindowById(id, self).Bind(wx.EVT_CHECKBOX, self._updateAxesSettings)

            if each == 'Left' and framestyle.find('l')>-1:
                wx.FindWindowById(id, self).SetValue(True)
            if each == 'Right' and framestyle.find('r')>-1:
                wx.FindWindowById(id, self).SetValue(True)
            if each == 'Top' and framestyle.find('t')>-1:
                wx.FindWindowById(id, self).SetValue(True)
            if each == 'Bottom' and framestyle.find('b')>-1:
                wx.FindWindowById(id, self).SetValue(True)

        sizer.Add(wx.StaticText(self, -1, 'Borders:'), 0)
        sizer.Add(border_sizer, 0, wx.TOP, 5)

        topbox.Add(sizer, 0, wx.ALL | wx.EXPAND, 5)

        self._enableLimitsCtrls(not self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)])


        self.zero_line = wx.CheckBox(self, -1)
        self.zero_line.Bind(wx.EVT_CHECKBOX, self._updateAxesSettings)

        zval = self.parent.plotparams['zero_line'+ str(self.parent.selected_plot)]
        self.zero_line.SetValue(zval)

        sizer.Add(wx.StaticText(self, -1, 'Zero Line:'), 0, wx.ALIGN_CENTRE_VERTICAL)
        sizer.Add(self.zero_line, 0)


        x_tick_label = wx.StaticText(self, -1, 'X-tick label font size:')


        if self.is_sec and self.sec_calc != 'None':
            y_tick_label = wx.StaticText(self, -1, 'Y-tick (left) label font size:')
            y2_tick_label = wx.StaticText(self, -1, 'Y-tick (right) label font size:')
        else:
            y_tick_label = wx.StaticText(self, -1, 'Y-tick label font size:')

        for tick in self.axes.xaxis.get_major_ticks():
            x_tick_size = tick.label.get_fontsize()
            break

        for tick in self.axes.yaxis.get_major_ticks():
            y_tick_size = tick.label.get_fontsize()
            break

        if self.is_sec and self.sec_calc != 'None':
            for tick in self.axes2.yaxis.get_major_ticks():
                y2_tick_size = tick.label.get_fontsize()
                break


        x_tick_font_size = wx.SpinCtrl(self, -1, str(x_tick_size), name = 'xticksize')
        x_tick_font_size.SetValue(int(x_tick_size))

        y_tick_font_size = wx.SpinCtrl(self, -1, str(y_tick_size), name = 'yticksize')
        y_tick_font_size.SetValue(int(y_tick_size))

        if self.is_sec and self.sec_calc != 'None':
            y2_tick_font_size = wx.SpinCtrl(self, -1, str(y2_tick_size), name = 'y2ticksize')
            y2_tick_font_size.SetValue(int(y2_tick_size))

        x_tick_font_size.Bind(wx.EVT_SPINCTRL, self._updateAxesSettings)
        y_tick_font_size.Bind(wx.EVT_SPINCTRL, self._updateAxesSettings)

        if self.is_sec and self.sec_calc != 'None':
            y2_tick_font_size.Bind(wx.EVT_SPINCTRL, self._updateAxesSettings)

        x_tick_sizer = wx.BoxSizer()
        x_tick_sizer.Add(x_tick_label, 0)
        x_tick_sizer.Add(x_tick_font_size, 0)

        y_tick_sizer = wx.BoxSizer()
        y_tick_sizer.Add(y_tick_label, 0)
        y_tick_sizer.Add(y_tick_font_size, 0)

        if self.is_sec and self.sec_calc != 'None':
            y2_tick_sizer = wx.BoxSizer()
            y2_tick_sizer.Add(y2_tick_label, 0)
            y2_tick_sizer.Add(y2_tick_font_size, 0)

        topbox.Add(x_tick_sizer, 0)
        topbox.Add(y_tick_sizer, 0)

        if self.is_sec and self.sec_calc != 'None':
            topbox.Add(y2_tick_sizer, 0)


        self.old_axes_settings = {'auto_fitaxes'    : self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)],
                                'zero_line'         : self.parent.plotparams['zero_line'+ str(self.parent.selected_plot)],
                                'framestyle'        : self.parent.plotparams['framestyle' + str(self.parent.selected_plot)],
                                'xrange'            : (self._old_xlimit[0], self._old_xlimit[1]),
                                'yrange'            : (self._old_ylimit[0], self._old_ylimit[1]),
                                'xticksize'         : x_tick_size,
                                'yticksize'         : y_tick_size
                                }

        if self.is_sec and self.sec_calc != 'None':
            self.old_axes_settings['framestyle2'] = self.parent.plotparams['framestyle2']
            self.old_axes_settings['y2range'] = (self._old_y2limit[0], self._old_y2limit[1])
            self.old_axes_settings['y2ticksize'] = y2_tick_size

        return topbox


    def _createLegendSettings(self):

        self.legend_items = [('visible', 'Visible:', self.NewControlId(), self._old_legend_settings['visible'], 'bool'),
                            ('border', 'Border:', self.NewControlId(), self._old_legend_settings['border'], 'bool'),
                            ('shadow', 'Shadow:', self.NewControlId(), self._old_legend_settings['shadow'], 'bool'),
                            ('alpha', 'Transparency %:', self.NewControlId(), self._old_legend_settings['alpha'], 'int'),
                            ('fontsize', 'Font size:', self.NewControlId(), self._old_legend_settings['fontsize'], 'int'),
                            ('font', 'Font:', self.NewControlId(), self._old_legend_settings['font'], 'choice')
                            ]

        if self.is_sec:
            self.legend_items.append(('showcalc', 'Show labels for calculated lines:',
                self.NewControlId(), self._old_legend_settings['showcalc'], 'bool'))

        self.legend_ids = {item[2] : (item[0], item[-1]) for item in self.legend_items}

        box = wx.StaticBox(self, wx.ID_ANY, 'Legend')
        topbox = wx.StaticBoxSizer(box, wx.VERTICAL)

        sizer = wx.FlexGridSizer(rows = len(self.legend_ids.keys()), cols = 2, hgap = 5, vgap = 3)

        for item in self.legend_items:
            each_key = item[0]
            label = item[1]
            my_id = item[2]
            val = item[3]
            my_type = item[4]

            lbl_txt = wx.StaticText(self, -1, label)

            if my_type == 'bool':
                ctrl = wx.CheckBox(self, my_id)
                ctrl.SetValue(val)
                ctrl.Bind(wx.EVT_CHECKBOX, self._updateLegendSettings)

            elif my_type == 'int':
                ctrl = wx.SpinCtrl(self, my_id, '')
                if each_key == 'alpha':
                    ctrl.SetValue(int(abs(val*100-100)))
                else:
                    ctrl.SetValue(int(val))
                ctrl.Bind(wx.EVT_SPINCTRL, self._updateLegendSettings)

            elif my_type == 'choice':
                if each_key == 'font':
                    choices = self.font_list

                ctrl = wx.Choice(self, my_id, choices = choices)
                ctrl.SetStringSelection(val)
                ctrl.Bind(wx.EVT_CHOICE, self._updateLegendSettings)

            sizer.Add(lbl_txt, 0)
            sizer.Add(ctrl, 0)

        topbox.Add(sizer, 0, wx.ALL, 5)

        return topbox


    def _enableLimitsCtrls(self, state):

        for each, id, lim in self.axes_fixed_limits_data:
            ctrl = wx.FindWindowById(id, self)
            ctrl.Enable(state)
            ctrl.Refresh()

    def _updateAxesSettings(self, event):

        autolimits = self.axes_autolimits.GetValue()

        if autolimits:
            self._enableLimitsCtrls(False)
            self.parent.fitAxis(forced = True)
        else:
            self._enableLimitsCtrls(True)

        self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)] = autolimits

        iszline = self.parent.plotparams['zero_line' + str(self.parent.selected_plot)]

        wantzline = self.zero_line.GetValue()

        if iszline and not wantzline:
            index=-1
            lines=self.axes.get_lines()

            for a in range(len(lines)):
                if lines[a].get_label()=='_zero_':
                    index=a

            if index>-1:
                self.axes.lines[index].remove()


        if not iszline and wantzline:
            zero = self.axes.axhline(color='k')
            zero.set_label('_zero_')

        self.parent.plotparams['zero_line' + str(self.parent.selected_plot)]= wantzline

        obj = event.GetEventObject()

        if obj.GetName() == 'xticksize':
            self.axes.tick_params(axis='x', labelsize=int(obj.GetValue()))

        elif obj.GetName() == 'yticksize':
            self.axes.tick_params(axis='y', labelsize=int(obj.GetValue()))

        elif obj.GetName() == 'y2ticksize':
            self.axes2.tick_params(axis='y', labelsize=int(obj.GetValue()))


        framestyle = ''

        if self.is_sec and self.sec_calc != 'None':
            framestyle2 = ''

        for item in self.axes_borders:
            value = wx.FindWindowById(item[1], self).GetValue()
            if value:
                if item[0] == 'Left':
                    framestyle = framestyle+'l'
                elif item[0] == 'Right':
                    if self.is_sec and self.sec_calc != 'None':
                        framestyle2 = framestyle2+'r'
                    else:
                        framestyle = framestyle+'r'
                elif item[0] == 'Top':
                    framestyle = framestyle+'t'
                elif item[0] == 'Bottom':
                    framestyle = framestyle+'b'


        self.parent.plotparams['framestyle' + str(self.parent.selected_plot)]= framestyle

        if self.is_sec and self.sec_calc != 'None':
            self.parent.plotparams['framestyle2'] = framestyle2
            self.parent._updateFrameStylesForAllPlots()

        else:
            self.parent.updateFrameStyle(self.axes)

        try:
            self.parent.canvas.draw()
        except matplotlib.pyparsing.ParseFatalException as e:
            print(e)

        event.Skip()


    def _updateLegendSettings(self, event):
        plotnum = str(self.parent.selected_plot)

        evt_id = event.GetId()
        evt_key, evt_type = self.legend_ids[evt_id]

        if evt_type != 'choice':
            val = wx.FindWindowById(evt_id, self).GetValue()
        else:
            val = wx.FindWindowById(evt_id, self).GetStringSelection()

        if evt_key == 'alpha':
            val = abs(100-val)/100.0

        self.parent.plotparams['legend_%s%s' %(evt_key, plotnum)] = val

        if not self.is_legend:
            self.parent.updateLegend(int(plotnum))

        self.legend = self.axes.get_legend()


        #It's painful, but faster to list out the choices by hand and update the legend properties
        #than to redraw the legend
        if self.legend is not None:
            if evt_key == 'visible':
                self.legend.set_visible(val)
            elif evt_key == 'border':
                if val:
                    self.legend.get_frame().set_linewidth(1)
                else:
                    self.legend.get_frame().set_linewidth(0)
            elif evt_key == 'shadow':
                self.legend.shadow = val
            elif evt_key == 'alpha':
                self.legend.get_frame().set_alpha(val)
            elif evt_key == 'fontsize':
                for each in self.legend.get_texts():
                    each.set_size(val)
            elif evt_key == 'font':
                for each in self.legend.get_texts():
                    each.set_fontname(val)
            elif evt_key == 'showcalc':
                self.parent.updateLegend(int(plotnum))

            if self.parent.plotparams['legend_visible%s' %(plotnum)] or evt_key == 'visible':
                self.parent.canvas.draw()


        #This is some stupid stuff that's necessary to prevent errors in the title part when there is
        #legend on the plot

        if self.legend is None:
            self.is_legend = False
        else:
            self.is_legend = True

        if self.is_legend:
            if self.is_sec and self.sec_calc != 'None':
                ids = self.labels[4][2]
                idlist = list(ids.values())
            else:
                ids = self.labels[3][2]
                idlist = list(ids.values())

            if not wx.FindWindowById(idlist[0], self).IsEnabled():
                for id in idlist:
                    wx.FindWindowById(id, self).Enable(True)

                wx.FindWindowById(ids['size'], self).Bind(wx.EVT_SPINCTRL, self._updateLabels)

        event.Skip()

    def _updateAxesRange(self, event):
        for i in range(0, len(self.axes_fixed_limits_data)):
            id = self.axes_fixed_limits_data[i][1]

            try:

                if self.axes_fixed_limits_data[i][0] == 'xmin':
                    xmin = float(wx.FindWindowById(id, self).GetValue())
                elif self.axes_fixed_limits_data[i][0] == 'xmax':
                    xmax = float(wx.FindWindowById(id, self).GetValue())
                elif self.axes_fixed_limits_data[i][0] == 'ymin':
                    ymin = float(wx.FindWindowById(id, self).GetValue())
                elif self.axes_fixed_limits_data[i][0] == 'ymax':
                    ymax = float(wx.FindWindowById(id, self).GetValue())
                elif self.axes_fixed_limits_data[i][0] == 'y2min':
                    y2min = float(wx.FindWindowById(id, self).GetValue())
                elif self.axes_fixed_limits_data[i][0] == 'y2max':
                    y2max = float(wx.FindWindowById(id, self).GetValue())

            except ValueError:
                pass
        try:
            self.axes.set_xlim((xmin, xmax))
            self.axes.set_ylim((ymin, ymax))
        except UnboundLocalError:
            pass
            #Catches the error when an axis range is blank or has just a period


        if self.is_sec and self.sec_calc != 'None':
            try:
                self.axes2.set_xlim((xmin, xmax))
                self.axes2.set_ylim((y2min, y2max))
            except UnboundLocalError:
                pass

        event.Skip()

    def _updateLabels(self, event):

        plotnum = str(self.parent.selected_plot)

        label_params = ['text', 'size', 'weight', 'style', 'fontname']
        obj = event.GetEventObject()

        if self.is_sec and self.sec_calc != 'None':
            if obj.GetName() == 'title':
                label = self.title
                ids = self.labels[0][2]
            elif obj.GetName() == 'xlabel':
                label = self.xlabel
                ids = self.labels[1][2]
            elif obj.GetName() == 'ylabel':
                label = self.ylabel
                ids = self.labels[2][2]
            elif obj.GetName() == 'y2label':
                label = self.y2label
                ids = self.labels[3][2]
            elif obj.GetName() == 'legtit':
                label = self.legend.get_title()
                ids = self.labels[4][2]

        else:
            if obj.GetName() == 'title':
                label = self.title
                ids = self.labels[0][2]
            elif obj.GetName() == 'xlabel':
                label = self.xlabel
                ids = self.labels[1][2]
            elif obj.GetName() == 'ylabel':
                label = self.ylabel
                ids = self.labels[2][2]
            elif obj.GetName() == 'legtit':
                label = self.legend.get_title()
                ids = self.labels[3][2]

        for key in label_params:

            ctrl = wx.FindWindowById(ids[key], self)
            if key != 'fontname':
                val = ctrl.GetValue()
            else:
                val = ctrl.GetStringSelection()

            if key == 'weight':
                if val:
                    value = 'bold'
                else:
                    value = 'normal'
                label.set_weight(value)

            elif key == 'style':
                if val:
                    value = 'italic'
                else:
                    value = 'normal'
                label.set_style(value)

            elif key == 'size':
                label.set_size(val)
                self.parent.plotparams['%s_fontsize%s' %(obj.GetName(), plotnum)] = val

            elif key == 'text':
                label.set_text(val)

            elif key == 'fontname':
                label.set_fontname(val)
                self.parent.plotparams['%s_font%s' %(obj.GetName(), plotnum)] = val

        if obj.GetName() == 'legtit':
            self.legend.set_title(label.get_text())

        try:
            self.parent.canvas.draw()
        except (matplotlib.pyparsing.ParseFatalException, ValueError) as e:
            print(e)

        event.Skip()


    def _restoreOldSettings(self):
        plotnum = str(self.parent.selected_plot)

        for each in self._old_settings:
            for each_key in self._old_settings[each]:
                if each == 'title':
                    expr = 'self.title.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec(expr)
                elif each == 'xlabel':
                    expr = 'self.xlabel.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec(expr)
                elif each == 'ylabel':
                    expr = 'self.ylabel.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec(expr)
                elif each == 'y2label':
                    expr = 'self.y2label.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec(expr)
                elif each == 'legtit' and self.is_legend:
                    expr = 'self.legend.get_title().set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec(expr)

                if each_key == 'size':
                    self.parent.plotparams['%s_fontsize%s' %(each, plotnum)] = self._old_settings[each][each_key]

                if each_key == 'fontname':
                    self.parent.plotparams['%s_font%s' %(each, plotnum)] = self._old_settings[each][each_key]


        if self.is_legend:
            for key in self._old_legend_settings:
                self.parent.plotparams['legend_%s%s' %(key, plotnum)] = self._old_legend_settings[key]

            self.parent.updateLegend(int(plotnum))

        for key, value in self.old_axes_settings.items():
            if key == 'xticksize':
                self.axes.tick_params(axis='x', labelsize=int(value))

            elif key == 'yticksize':
                self.axes.tick_params(axis='y', labelsize=int(value))

            elif key == 'y2ticksize':
                self.axes2.tick_params(axis='y', labelsize=int(value))

            elif key == 'xrange':
                self.axes.set_xlim(value)

            elif key == 'yrange':
                self.axes.set_ylim(value)

            elif key == 'y2range':
                self.axes2.set_xlim(self.old_axes_settings['xrange'])
                self.axes2.set_ylim(value)
            elif key == 'framestyle2':
                self.parent.plotparams[key] = value
            else:
                self.parent.plotparams[key + plotnum] = value

        if self.is_sec and self.sec_calc != 'None':
            self.parent._updateFrameStylesForAllPlots()

        else:
            self.parent.updateFrameStyle(self.axes)

        self.parent.canvas.draw()

    def _onOk(self, event):

        if self.axes == self.parent.subplot1:
            type = self.parent.plotparams['plot1type']
        else:
            type = self.parent.plotparams['plot2type']

        self.parent.subplot_labels[type] = [self.title.get_text(), self.xlabel.get_text(), self.ylabel.get_text()]

        if self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)]:
            self.parent.fitAxis(forced = True)
        else:
            self.parent.canvas.draw()


        self.EndModal(wx.ID_OK)

    def _onCancel(self, event):
        self._restoreOldSettings()
        self.EndModal(wx.ID_CANCEL)
