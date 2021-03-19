'''
Created on Aug 2, 2010

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
from builtins import object, range, map, zip
from io import open

try:
    import queue
except Exception:
    import Queue as queue

import re
import sys
import os
import time
import math
import copy

import wx
import wx.lib.agw.customtreectrl as CT
import wx.lib.scrolledpanel as scrolled
from numpy import ceil
import pyFAI

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWSettings as RAWSettings
import bioxtasraw.RAWCustomCtrl as RAWCustomCtrl
import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.SASFileIO as SASFileIO
import bioxtasraw.SASParser as SASParser
import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.SASUtils as SASUtils


#--- ** TREE BOOK PANELS **

def CreateFileDialog(mode):

        file = None

        try:
            path = wx.FindWindowByName('FileListCtrl').path
        except:
            path = os.getcwd()

        if mode == wx.FD_OPEN:
            filters = 'All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters, defaultDir = path)
        if mode == wx.FD_SAVE:
            filters = 'All files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode|wx.FD_OVERWRITE_PROMPT, wildcard = filters, defaultDir = path)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()

        # Destroy the dialog
        dialog.Destroy()

        return file

class ArtifactOptionsPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        self.update_keys = ['ZingerRemoval',
                            'ZingerRemoveSTD',
                            'ZingerRemoveWinLen',
                            'ZingerRemoveIdx',
                            'ZingerRemovalRadAvg',
                            'ZingerRemovalRadAvgStd',
                            'ZingerRemovalRadAvgIter',
                            ]

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.artifact_removal_data = ( ('Zinger removal by smoothing', raw_settings.getIdAndType('ZingerRemoval')),
                                     ('Std:',            raw_settings.getIdAndType('ZingerRemoveSTD')),
                                     ('Window Length:',  raw_settings.getIdAndType('ZingerRemoveWinLen')),
                                     ('Start Index:',    raw_settings.getIdAndType('ZingerRemoveIdx')))

        self.artifact_removal_data3 = ( ('Zinger removal during radial average', raw_settings.getIdAndType('ZingerRemovalRadAvg')),
                                      ('Discard threshold (std.):', raw_settings.getIdAndType('ZingerRemovalRadAvgStd')),
                                      ('Number of iterations:', raw_settings.getIdAndType('ZingerRemovalRadAvgIter')))

        artifact_sizer = self.createArtifactRemoveSettings()
        artifact_sizer3 = self.createArtifactRemoveOnRadAvg()

        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(artifact_sizer, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        panelsizer.Add(artifact_sizer3, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))

        self.SetSizer(panelsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createArtifactRemoveOnRadAvg(self):

        box = wx.StaticBox(self, -1, 'Artifact Removal when performing radial averaging')
        chkbox_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(cols=4, rows=2, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))

        for label, param in self.artifact_removal_data3:

            if param is not None:

                id = param[0]
                type = param[1]

                if type != 'bool':
                    text = wx.StaticText(box, -1, label)
                    ctrl = wx.TextCtrl(box, id, 'None', style=wx.TE_PROCESS_ENTER)

                    grid_sizer.Add(text, 1, wx.EXPAND|wx.ALIGN_LEFT
                        |wx.ALIGN_CENTER_VERTICAL)
                    grid_sizer.Add(ctrl, 1, wx.EXPAND)
                else:
                    chk = wx.CheckBox(box, id, label)
                    chk.Bind(wx.EVT_CHECKBOX, self.onChkBox)
                    chkbox_sizer.Add(chk, 0, wx.EXPAND|wx.ALL,
                        border=self._FromDIP(5))

        chkbox_sizer.Add(grid_sizer, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.TOP,
            border=self._FromDIP(5))

        return chkbox_sizer

    def createArtifactRemoveSettings(self):

        box = wx.StaticBox(self, -1, 'Artifact Removal')
        chkbox_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(cols=4, rows=2, vgap=self._FromDIP(5),
            hgap=self._FromDIP(5))

        for label, param in self.artifact_removal_data:

            id = param[0]
            type = param[1]

            if type != 'bool':
                text = wx.StaticText(box, -1, label)
                ctrl = wx.TextCtrl(box, id, 'None', style = wx.TE_PROCESS_ENTER)

                grid_sizer.Add(text, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
                grid_sizer.Add(ctrl, 1, wx.EXPAND)
            else:
                chk = wx.CheckBox(box, id, label)
                chk.Bind(wx.EVT_CHECKBOX, self.onChkBox)
                chkbox_sizer.Add(chk, 0, wx.EXPAND|wx.ALL,
                    border=self._FromDIP(5))

        chkbox_sizer.Add(grid_sizer, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(5))

        return chkbox_sizer

    def onChkBox(self, event):
        pass


class CalibrationOptionsPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):
        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.update_keys = [
            'SampleDistance',
            'WaveLength',
            'DetectorPixelSizeX',
            'DetectorPixelSizeY',
            'Xcenter',
            'Ycenter',
            'DetectorTilt',
            'DetectorTiltPlanRot',
            'BinType',
            'Binsize',
            'StartPoint',
            'EndPoint',
            'DoSolidAngleCorrection',
            'DoPolarizationCorrection',
            'PolarizationFactor',
            'IntegrationMethod',
            'AngularUnit',
            'ErrorModel',
            'Detector',
            'UseImageForVariance',
            ]

        self.raw_settings = raw_settings



        detector_choices = self._get_detectors()
        integration_choices = ['numpy', 'cython', 'BBox', 'nosplit_csr', 'csr',
            'full_csr']

        if RAWGlobals.has_pyopencl:
            integration_choices.extend(['nosplit_csr_ocl', 'csr_ocl', 'full_csr_ocl'])

        error_choices = ['poisson', 'azimuthal']
        angular_choices = ['q_nm^-1', 'q_A^-1', '2th_deg', '2th_rad', 'r_mm']
        bin_choices = ['Linear',]

        self.calibConstantsData = (
            ("Wavelength [A]:", raw_settings.getId('WaveLength')),
            ("Detector:", raw_settings.getId('Detector'), detector_choices),
            ("Detector X Pixel Size [um]:", raw_settings.getId('DetectorPixelSizeX')),
            ("Detector Y Pixel Size [um]:", raw_settings.getId('DetectorPixelSizeY')),
            ("Sample-Detector Distance [mm]:", raw_settings.getId('SampleDistance')),
            ("Beam X center:", raw_settings.getId('Xcenter')),
            ("Beam Y center:", raw_settings.getId('Ycenter')),
            ("Detector Tilt [deg]:", raw_settings.getId('DetectorTilt')),
            ("Detector Tilt Plane Rotation [deg]:",
                raw_settings.getId('DetectorTiltPlanRot')),
            ('Correct for the change in the solid angle of the pixels',
                raw_settings.getId('DoSolidAngleCorrection')),
            ('Correct for the polarization of the x-ray beam',
                raw_settings.getId('DoPolarizationCorrection')),
            ('Polarization factor (-1 to 1, 0 is random):',
                raw_settings.getId('PolarizationFactor')),
            ('Integration Method:', raw_settings.getId('IntegrationMethod'),
                integration_choices),
            ('Use image pixel values as pixel variance',
                raw_settings.getId('UseImageForVariance')),
            ('Error Model:', raw_settings.getId('ErrorModel'), error_choices),
            ('Angular unit', raw_settings.getId('AngularUnit'), angular_choices),
            ('Binning type:', raw_settings.getId('BinType'), bin_choices),
            ('Bin factor:', raw_settings.getId('Binsize')),
           )

        self.expsettings_spin = (
            ("Start plots at q-point number:", raw_settings.getId('StartPoint')),
            ("Skip n points at the end of the curve:", raw_settings.getId('EndPoint')),
            )

        box = wx.StaticBox(self, -1, '2D Reduction Parameters')
        reduction_sizer = self.create2DReductionParameters(box)
        top_reduction_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        top_reduction_sizer.Add(reduction_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT
            |wx.TOP|wx.BOTTOM, border=self._FromDIP(5))

        box = wx.StaticBox(self, label='Other Parameters')
        other_params_sizer = self.createOtherParameters(box)
        top_other_params_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        top_other_params_sizer.Add(other_params_sizer, 0, wx.EXPAND|wx.LEFT
            |wx.RIGHT|wx.TOP|wx.BOTTOM, border=self._FromDIP(5))

        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(top_reduction_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        panelsizer.Add(top_other_params_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        self.SetSizer(panelsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def create2DReductionParameters(self, parent):

        ctrl_sizer = wx.GridBagSizer(vgap=self._FromDIP(5), hgap=self._FromDIP(5))

        for i in range(len(self.calibConstantsData)):
            item = self.calibConstantsData[i]
            each_text = item[0]
            ctrl_id = item[1]

            ctrl_name = self.raw_settings.findParamById(ctrl_id)
            ctrl_type = self.raw_settings.getType(ctrl_name)

            if ctrl_type == 'float' or ctrl_type == 'int' or ctrl_type == 'text':
                txt = wx.StaticText(parent, label=each_text)
                ctrl = wx.TextCtrl(parent, ctrl_id, size=self._FromDIP((60, -1)))

                ctrl_sizer.Add(txt, (i, 0), flag=wx.ALIGN_CENTER_VERTICAL)
                ctrl_sizer.Add(ctrl, (i, 1), flag=wx.ALIGN_CENTER_VERTICAL)

            elif ctrl_type == 'bool':
                ctrl = wx.CheckBox(parent, ctrl_id, label=each_text)

                ctrl_sizer.Add(ctrl, (i, 0), span=(1, 2), flag=wx.ALIGN_CENTER_VERTICAL)

            elif ctrl_type == 'choice':
                txt = wx.StaticText(parent, label=each_text)
                ctrl = wx.Choice(parent, ctrl_id, choices=item[2])

                ctrl_sizer.Add(txt, (i, 0), flag=wx.ALIGN_CENTER_VERTICAL)
                ctrl_sizer.Add(ctrl, (i, 1), flag=wx.ALIGN_CENTER_VERTICAL)

        det_id = self.raw_settings.getId('Detector')
        det_ctrl = wx.FindWindowById(det_id, self)
        det_ctrl.Bind(wx.EVT_CHOICE, self._on_detector_change)

        return ctrl_sizer


    def createOtherParameters(self, parent):

        ctrl_sizer = wx.FlexGridSizer(vgap=self._FromDIP(5), hgap=self._FromDIP(5),
            cols=2)

        for item in self.expsettings_spin:
            each_text = item[0]
            ctrl_id = item[1]

            txt = wx.StaticText(parent, label=each_text)
            ctrl = RAWCustomCtrl.IntSpinCtrl(parent, ctrl_id, TextLength=60,
                min_val=0)

            ctrl_sizer.Add(txt, flag=wx.ALIGN_CENTER_VERTICAL)
            ctrl_sizer.Add(ctrl, flag=wx.ALIGN_CENTER_VERTICAL)

        return ctrl_sizer

    def _get_detectors(self):
        det_list = SASUtils.get_det_list()

        return det_list

    def _on_detector_change(self, evt):
        det_selection = evt.GetEventObject().GetStringSelection()

        if det_selection != 'Other':
            detector = pyFAI.detector_factory(det_selection)

            pixely = detector.get_pixel1()
            pixelx = detector.get_pixel2()

            det_pix_x_id = self.raw_settings.getId('DetectorPixelSizeX')
            det_pix_y_id = self.raw_settings.getId('DetectorPixelSizeY')

            det_pix_x_ctrl = wx.FindWindowById(det_pix_x_id, self)
            det_pix_y_ctrl = wx.FindWindowById(det_pix_y_id, self)

            det_pix_x_ctrl.SetValue(str(pixelx*1e6))
            det_pix_y_ctrl.SetValue(str(pixely*1e6))

class HeaderListCtrl(wx.ListCtrl):

    def __init__(self, parent, *args, **kwargs):

        #ULC.UltimateListCtrl.__init__(self, parent, -1, *args, agwStyle = ULC.ULC_REPORT|ULC.ULC_SINGLE_SEL, **kwargs)
        wx.ListCtrl.__init__(self, parent, -1, *args, **kwargs)
        self.insertAllColumns()

    def insertAllColumns(self):
        self.InsertColumn(0, 'Name', width = self._FromDIP(150))
        self.InsertColumn(1, 'Value', width = self._FromDIP(150))
        self.InsertColumn(2, 'Binding', width = self._FromDIP(150))
        self.InsertColumn(3, 'Modifier', width = self._FromDIP(150))

    def getColumnText(self, index, col):
        item = self.GetItem(index, col)
        return item.GetText()

    def setColumnText(self, index, col, text):
        self.SetItem(index, col, str(text))

    def clearColumn(self, col):
        for idx in range(0, self.GetItemCount()):
            self.SetItem(idx, 2, '')

    def clear(self):
        self.ClearAll()
        self.insertAllColumns()
        self.Refresh()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

class ReductionImgHdrFormatPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.update_keys = ['ImageFormat', 'ImageHdrFormat', 'UseHeaderForCalib']
        self.changes = {}

        self.raw_settings = raw_settings
        self.currentItem = None
        self.imghdr_start_idx = 0

        self.hdr_format_list = list(SASFileIO.all_header_types.keys())
        self.hdr_format_list.remove('None')
        self.hdr_format_list.sort()
        self.hdr_format_list.insert(0, 'None')

        self.img_format_list = sorted(SASFileIO.all_image_types.keys())

        self.bind_choice_list = sorted(self.raw_settings.get('HeaderBindList').keys())
        self.bind_choice_list.sort()
        self.bind_choice_list.insert(0, 'No binding')

        self.choice_sizer = self.createImageHeaderChoice()
        self.list_sizer = self.createListCtrl()
        self.ctrl_sizer = self.createBindControls()
        self.button_sizer = self.createLoadAndClearButtons()
        modifier_add_button = wx.Button(self, -1, 'Add')
        modifier_add_button.Bind(wx.EVT_BUTTON, self.onModifierAddButton)
        modifier_remove_button = wx.Button(self, -1, 'Remove')
        modifier_remove_button.Bind(wx.EVT_BUTTON, self.onModifierRemoveButton)

        hsizer = wx.BoxSizer()
        hsizer.Add(self.ctrl_sizer, 0, wx.ALL, border=self._FromDIP(5))
        hsizer.Add(modifier_add_button, 0, wx.LEFT|wx.BOTTOM|wx.ALIGN_BOTTOM,
            border=self._FromDIP(5))
        hsizer.Add(modifier_remove_button, 0, wx.LEFT|wx.BOTTOM|wx.ALIGN_BOTTOM,
            border=self._FromDIP(5))
        hsizer.Add((1,1),1,wx.EXPAND)
        hsizer.Add(self.button_sizer, 0, wx.ALIGN_TOP)

        final_sizer = wx.BoxSizer(wx.VERTICAL)

        final_sizer.Add(self.choice_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        final_sizer.Add(self.list_sizer, 1, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        final_sizer.Add(hsizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))

        self.SetSizer(final_sizer)

        self.enableAllBindCtrls(raw_settings.get('UseHeaderForCalib'))

        imghdr = raw_settings.get('ImageHdrList')
        filehdr = raw_settings.get('FileHdrList')

        self.bind_list = copy.deepcopy(raw_settings.get('HeaderBindList'))

        self._updateList(imghdr, filehdr)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def enableAllBindCtrls(self, state):

        sizers = [self.ctrl_sizer]

        for each in sizers:

            for each_widget in each.GetChildren():
                each_widget.GetWindow().Enable(state)


    def createImageHeaderChoice(self):

        sizer = wx.BoxSizer()

        imgfmt_id = self.raw_settings.getId('ImageFormat')
        self.choice1_text = wx.StaticText(self, -1, 'Image format:')
        self.image_choice = wx.Choice(self, imgfmt_id, choices = self.img_format_list)
        self.image_choice.SetSelection(0)

        hdrfmt_id = self.raw_settings.getId('ImageHdrFormat')
        self.choice2_text = wx.StaticText(self, -1, 'Header file format:')
        self.header_choice = wx.Choice(self, hdrfmt_id, choices = self.hdr_format_list)
        self.header_choice.SetSelection(0)

        sizer.Add(self.choice1_text, 0, wx.ALIGN_CENTER|wx.RIGHT,
            border=self._FromDIP(5))
        sizer.Add(self.image_choice, 0, wx.RIGHT, border=self._FromDIP(10))

        sizer.Add(self.choice2_text, 0, wx.ALIGN_CENTER|wx.RIGHT,
            border=self._FromDIP(5))
        sizer.Add(self.header_choice, 0, wx.RIGHT, border=self._FromDIP(5))

        return sizer

    def createLoadAndClearButtons(self):

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.clear_bind_button = wx.Button(self, -1, 'Clear Bindings')
        self.clear_bind_button.Bind(wx.EVT_BUTTON, self.onClearBindingsButton)

        self.load_button = wx.Button(self, -1, 'Load Image',
            size=self.clear_bind_button.GetSize())
        self.load_button.Bind(wx.EVT_BUTTON, self.onLoadButton)

        self.clear_all_button = wx.Button(self, -1, 'Clear All',
            size=self.clear_bind_button.GetSize())
        self.clear_all_button.Bind(wx.EVT_BUTTON, self.onClearAllButton)

        sizer.Add(self.load_button, 0, wx.RIGHT, border=self._FromDIP(3))
        sizer.Add(self.clear_bind_button, 0, wx.TOP|wx.RIGHT,
            border=self._FromDIP(3))
        sizer.Add(self.clear_all_button, 0, wx.TOP|wx.RIGHT,
            border=self._FromDIP(3))

        return sizer

    def createListCtrl(self):

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.lc = HeaderListCtrl(self, style = wx.LC_REPORT)
        self.lc.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onListSelection)

        chkbox_id = self.raw_settings.getId('UseHeaderForCalib')
        self.chkbox = wx.CheckBox(self, chkbox_id, ('Use image-header/header '
            'file for calibration and reduction parameters'))
        self.chkbox.Bind(wx.EVT_CHECKBOX, self.onUseHeaderChkbox)

        sizer.Add(self.chkbox, 0, wx.BOTTOM, border=self._FromDIP(10))
        sizer.Add(self.lc, 1, wx.EXPAND)

        return sizer

    def createBindControls(self):

        sizer = wx.FlexGridSizer(rows=4, cols=2, vgap=self._FromDIP(2),
            hgap=self._FromDIP(2))

        name_text = wx.StaticText(self, -1, 'Name:')
        value_text = wx.StaticText(self, -1, 'Value:')
        bind_text = wx.StaticText(self, -1, 'Binding:')
        mod_text = wx.StaticText(self, -1, 'Modifier:')

        self.bind_ctrl = wx.Choice(self, -1, choices = self.bind_choice_list)
        self.bind_ctrl.Bind(wx.EVT_CHOICE, self.onBindChoice)
        self.bind_name_ctrl = wx.TextCtrl(self, -1,
            size=self.bind_ctrl.GetSize(), style=wx.TE_PROCESS_ENTER)
        self.bind_value_ctrl = wx.TextCtrl(self, -1,
            size=self.bind_ctrl.GetSize(), style=wx.TE_PROCESS_ENTER)
        self.bind_mod_ctrl = wx.TextCtrl(self, -1,
            size=self.bind_ctrl.GetSize(), style=wx.TE_PROCESS_ENTER)

        sizer.Add(name_text, 1, wx.ALIGN_CENTER)
        sizer.Add(self.bind_name_ctrl, 1)
        sizer.Add(value_text, 1, wx.ALIGN_CENTER)
        sizer.Add(self.bind_value_ctrl, 1)
        sizer.Add(bind_text,1, wx.ALIGN_CENTER)
        sizer.Add(self.bind_ctrl,1)
        sizer.Add(mod_text,1, wx.ALIGN_CENTER)
        sizer.Add(self.bind_mod_ctrl,1)

        return sizer

    def onModifierRemoveButton(self, event):
        self.bind_mod_ctrl.SetValue('')
        self.lc.setColumnText(self.currentItem, 3, '')

        bindstr = self.bind_ctrl.GetStringSelection()

        if bindstr in self.bind_list:
                self.bind_list[bindstr][2] = ''
                self.changes['HeaderBindList'] = self.bind_list

    def onModifierAddButton(self, event):
        txt = self.bind_mod_ctrl.GetValue()

        try:
            bindstr = self.bind_ctrl.GetStringSelection()

            if bindstr == 'No binding':
                wx.MessageBox('Please select a binding first.', 'Select binding first')
                return

            success = self.calcModifier()
            if not success:
                return

            self.lc.setColumnText(self.currentItem, 3, txt)

            if bindstr in self.bind_list:
                self.bind_list[bindstr][2] = txt
                self.changes['HeaderBindList'] = self.bind_list             #Updates raw_settings on OK
        except:
            pass

        event.Skip()

    def onUseHeaderChkbox(self, event):
        chkbox = event.GetEventObject()
        self.enableAllBindCtrls(chkbox.GetValue())

    def onBindChoice(self, event):

        if self.currentItem is None:
            self.bind_ctrl.Select(0)
            return


        bindstr = self.bind_ctrl.GetStringSelection()

        old_bind = self.lc.getColumnText(self.currentItem, 2)

        if bindstr == old_bind:
            return

        #Remove the bind if its already there
        num_items = self.lc.GetItemCount()
        for i in range(0, num_items):
            if self.lc.getColumnText(i, 2) == bindstr:
                self.lc.setColumnText(i, 2, '')
                self.lc.setColumnText(i, 3, '')

        # If the selected binding is No Binding
        if self.bind_ctrl.GetSelection() == 0:
            self.lc.setColumnText(self.currentItem, 2, '')
            self.lc.setColumnText(self.currentItem, 3, '')
        else:
            self.lc.setColumnText(self.currentItem, 2, self.bind_ctrl.GetStringSelection())

        if old_bind != '':
                self.bind_list[old_bind][1] = None
                self.bind_list[old_bind][2] = ''
                self.changes['HeaderBindList'] = self.bind_list

        #Store new bind in bind_list
        header_key = self.lc.getColumnText(self.currentItem, 0)

        if self.currentItem > self.imghdr_start_idx:
            selected_header = 'imghdr'
        else:
            selected_header = 'filehdr'

        if bindstr != 'No binding':
            #Set new bind
            self.bind_list[bindstr][1] = [header_key, selected_header]

            modtxt = self.bind_mod_ctrl.GetValue()
            self.bind_list[bindstr][2] = modtxt

            self.changes['HeaderBindList'] = self.bind_list             #Updates raw_settings on OK

        self.lc.Update()

    def onListSelection(self, event):
        '''
        Update the binding controls when an item in the
        list is selected.
        '''

        self.currentItem = event.GetIndex() #m_itemIndex

        name = self.lc.getColumnText(self.currentItem, 0)
        value = self.lc.getColumnText(self.currentItem, 1)
        binding = self.lc.getColumnText(self.currentItem, 2)
        mod = self.lc.getColumnText(self.currentItem, 3)

        self.bind_name_ctrl.SetValue(name)
        self.bind_value_ctrl.SetValue(value)
        self.bind_mod_ctrl.SetValue(mod)

        if binding == '':
            self.bind_ctrl.SetSelection(0)
        else:
            idx = self.bind_choice_list.index(binding)
            self.bind_ctrl.SetSelection(idx)

    def _updateList(self, imghdr, filehdr):

        self.lc.clear()

        self.file_hdr_list_dict = {}
        self.img_hdr_list_dict = {}

        if filehdr is not None:
            if wx.version().split()[0].strip()[0] == '4':
                self.lc.InsertItem(0, 'Header File:')
                self.lc.SetItemBackgroundColour(0, wx.Colour('STEEL BLUE'))
            else:
                self.lc.InsertItem(0, 'Header File:')
                self.lc.SetItemBackgroundColour(0, wx.NamedColour('STEEL BLUE'))
            item = self.lc.GetItem(0, 0)
            item.SetTextColour(wx.WHITE)
            self.lc.SetItem(item)

            for key in sorted(filehdr.keys()):
                num_items = self.lc.GetItemCount()
                if wx.version().split()[0].strip()[0] == '4':
                    self.lc.InsertItem(num_items, key)
                    self.lc.SetItem(num_items, 1, str(filehdr[key]))
                else:
                    self.lc.InsertItem(num_items, key)
                    self.lc.SetItem(num_items, 1, str(filehdr[key]))
                self.file_hdr_list_dict[key] = num_items


            self.lc.SetColumnWidth(0, wx.LIST_AUTOSIZE)
            self.lc.SetColumnWidth(1, self._FromDIP(170))
            self.lc.SetColumnWidth(2, self._FromDIP(150))

        self.imghdr_start_idx = self.lc.GetItemCount()

        if imghdr is not None:
            num_items = self.lc.GetItemCount()
            if wx.version().split()[0].strip()[0] == '4':
                self.lc.InsertItem(num_items, 'Image Header:')
                self.lc.SetItemBackgroundColour(num_items, wx.Colour('STEEL BLUE'))
            else:
                self.lc.InsertItem(num_items, 'Image Header:')
                self.lc.SetItemBackgroundColour(num_items, wx.NamedColour('STEEL BLUE'))
            item = self.lc.GetItem(num_items, 0)
            item.SetTextColour(wx.WHITE)
            self.lc.SetItem(item)

            for key in sorted(imghdr.keys()):
                num_items = self.lc.GetItemCount()
                if wx.version().split()[0].strip()[0] == '4':
                    self.lc.InsertItem(num_items, key)
                    self.lc.SetItem(num_items, 1, str(imghdr[key]))
                else:
                    self.lc.InsertItem(num_items, key)
                    self.lc.SetItem(num_items, 1, str(imghdr[key]))
                self.img_hdr_list_dict[key] = num_items

            self.lc.SetColumnWidth(0, wx.LIST_AUTOSIZE)
            self.lc.SetColumnWidth(1, self._FromDIP(170))
            self.lc.SetColumnWidth(2, self._FromDIP(150))


        for each in self.bind_list:
            data = self.bind_list[each][1]
            mod = self.bind_list[each][2]

            if data is not None:
                if data[1] == 'imghdr': hdr = self.img_hdr_list_dict
                else: hdr = self.file_hdr_list_dict

                if data[0] in hdr:
                    self.lc.SetItem(hdr[data[0]], 2, str(each))
                    self.lc.SetItem(hdr[data[0]], 3, str(mod))

        self.lc.Update()

        self.changes['ImageHdrList'] = imghdr
        self.changes['FileHdrList'] = filehdr

    def onLoadButton(self, event):
        '''
        Load the headers from the image and additional header files
        and add each header item to the list.
        '''

        filename = CreateFileDialog(wx.FD_OPEN)
        if filename is None:
            return

        image_format = self.image_choice.GetStringSelection()
        hdr_format = self.header_choice.GetStringSelection()

        try:
            imghdr, filehdr = SASFileIO.loadAllHeaders(filename, image_format, hdr_format, self.raw_settings)
        except SASExceptions.WrongImageFormat:
            wx.MessageBox('The selected file is not of the selected format.', 'Wrong image format', wx.OK|wx.ICON_INFORMATION)
            return
        except ValueError:
            wx.MessageBox('Error loading the header file.', 'Wrong header format', wx.OK|wx.ICON_INFORMATION)
            return
        except SASExceptions.HeaderLoadError as e:
            wx.MessageBox('Error loading the header file:\n' + str(e), 'Wrong header format', wx.OK|wx.ICON_INFORMATION)
            return
        except Exception:
            wx.MessageBox('Please pick the image file and not the header file itself.', 'Pick the image file', wx.OK|wx.ICON_INFORMATION)
            raise

        self.onClearBindingsButton(None)

        if isinstance(imghdr, list):
            imghdr = imghdr[0]

        self._updateList(imghdr, filehdr)

    def clearBindings(self):

        for each in self.bind_list:
            self.bind_list[each][1] = None

        self.changes['HeaderBindList'] = self.bind_list

    def onClearBindingsButton(self, event):
        self.lc.clearColumn(3)
        self.bind_ctrl.SetSelection(0)

        self.clearBindings()

    def onClearAllButton(self, event):
        self.lc.clear()
        self.bind_name_ctrl.SetValue('')
        self.bind_value_ctrl.SetValue('')
        self.bind_ctrl.SetSelection(0)

        self.changes['ImageHdrList'] = None
        self.changes['FileHdrList'] = None

        self.clearBindings()

    def calcModifier(self):

        expr = self.bind_mod_ctrl.GetValue()
        res = self.calcExpression(expr)

        if res is not None:
            wx.MessageBox(expr + ' = ' + str(res), 'Expression check:' , style = wx.ICON_INFORMATION)
            return True
        else:
            return False


    def calcExpression(self, expr):

        if expr != '':
            self.mathparser = SASParser.PyMathParser()
            self.mathparser.addDefaultFunctions()
            self.mathparser.addDefaultVariables()

            self.mathparser.addSpecialVariables(self.changes['ImageHdrList'])
            self.mathparser.addSpecialVariables(self.changes['FileHdrList'])

            self.mathparser.expression = expr

            try:
                val = self.mathparser.evaluate()
                return val
            except Exception as msg:
                wx.MessageBox(str(msg), 'Error')
                return None
        else:
            return None


    def updateEnable(self):
        self.enableAllBindCtrls(self.chkbox.GetValue())


class NormListCtrl(wx.ListCtrl):

    def __init__(self, parent, id, *args, **kwargs):

        wx.ListCtrl.__init__(self, parent, id, *args, **kwargs)
        self.populateList()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def populateList(self):
        self.InsertColumn(0, 'Operator')
        self.InsertColumn(1, 'Expression')
        self.SetColumnWidth(1, self._FromDIP(250))

    def add(self, op, expr):
        no_of_items = self.GetItemCount()
        if wx.version().split()[0].strip()[0] == '4':
            self.InsertItem(no_of_items, op)
            self.SetItem(no_of_items, 1, expr)
        else:
            self.InsertItem(no_of_items, op)
            self.SetItem(no_of_items, 1, expr)

    def moveItemUp(self, idx):
        if idx > 0:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertItem(idx-1, data[0])
            self.SetItem(idx-1, 1, data[1])
            self.Select(idx-1, True)

    def moveItemDown(self, idx):
        if idx < self.GetItemCount()-1:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertItem(idx+1, data[0])
            self.SetItem(idx+1, 1, data[1])
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


class OnlineListCtrl(wx.ListCtrl):

    def __init__(self, parent, id, *args, **kwargs):

        wx.ListCtrl.__init__(self, parent, id, *args, **kwargs)
        self.populateList()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def populateList(self):
        self.InsertColumn(0, 'Ignore/Open')
        self.InsertColumn(1, 'Filter String')
        self.InsertColumn(2, 'Location')
        self.SetColumnWidth(0, self._FromDIP(100))
        self.SetColumnWidth(1, self._FromDIP(200))

    def add(self, filt, expr, pos):
        no_of_items = self.GetItemCount()
        if wx.version().split()[0].strip()[0] == '4':
            self.InsertItem(no_of_items, filt)
            self.SetItem(no_of_items, 1, expr)
            self.SetItem(no_of_items, 2, pos)
        else:
            self.InsertItem(no_of_items, filt)
            self.SetItem(no_of_items, 1, expr)
            self.SetItem(no_of_items, 2, pos)

    def moveItemUp(self, idx):
        if idx > 0:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertItem(idx-1, data[0])
            self.SetItem(idx-1, 1, data[1])
            self.SetItem(idx-1, 2, data[2])
            self.Select(idx-1, True)

    def moveItemDown(self, idx):
        if idx < self.GetItemCount()-1:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertItem(idx+1, data[0])
            self.SetItem(idx+1, 1, data[1])
            self.SetItem(idx+1, 2, data[2])
            self.Select(idx+1, True)

    def getItemData(self, idx):
        data1 = self.GetItemText(idx)
        item = self.GetItem(idx, 1)
        data2 = item.GetText()
        item2 = self.GetItem(idx,2)
        data3 = item2.GetText()

        return [data1, data2, data3]

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
            filt = each[0]
            expr = each[1]
            pos = each[2]
            self.add(filt, expr, pos)

class MetadataListCtrl(wx.ListCtrl):

    def __init__(self, parent, id, *args, **kwargs):

        wx.ListCtrl.__init__(self, parent, id, *args, **kwargs)
        self.populateList()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def populateList(self):
        self.InsertColumn(0, 'Key')
        self.InsertColumn(1, 'Value')
        self.SetColumnWidth(1, self._FromDIP(250))

    def add(self, op, expr):
        no_of_items = self.GetItemCount()
        if wx.version().split()[0].strip()[0] == '4':
            self.InsertItem(no_of_items, op)
            self.SetItem(no_of_items, 1, expr)
        else:
            self.InsertItem(no_of_items, op)
            self.SetItem(no_of_items, 1, expr)

    def moveItemUp(self, idx):
        if idx > 0:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertItem(idx-1, data[0])
            self.SetItem(idx-1, 1, data[1])
            self.Select(idx-1, True)

    def moveItemDown(self, idx):
        if idx < self.GetItemCount()-1:
            data = self.getItemData(idx)
            self.DeleteItem(idx)
            self.InsertItem(idx+1, data[0])
            self.SetItem(idx+1, 1, data[1])
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


class ReductionNormalizationAbsScPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['NormAbsWaterEmptyFile',
                            'NormAbsWaterFile',
                            'NormAbsWaterTemp',
                            'NormAbsWaterI0',
                            'NormAbsWater',
                            'NormAbsWaterConst',
                            'NormAbsCarbon',
                            'NormAbsCarbonIgnoreBkg',
                            'NormAbsCarbonFile',
                            'NormAbsCarbonEmptyFile',
                            'NormAbsCarbonSamEmptyFile',
                            'NormAbsCarbonCalFile',
                            'NormAbsCarbonThick',
                            'NormAbsCarbonSamThick',
                            'NormAbsCarbonUpstreamCtr',
                            'NormAbsCarbonDownstreamCtr',
                            'NormAbsCarbonConst',
                            ]

             #      label,                  textCtrlId,            buttonId,
             #      clrbuttonId,    ButtonText,              BindFunction
        self.filesData = (
            ("Empty cell:", raw_settings.getId('NormAbsWaterEmptyFile'),
                self.NewControlId(), self.NewControlId(), "Set", "Clear",
                self.onSetFile, self.onClrFile),
            ("Water sample:", raw_settings.getId('NormAbsWaterFile'),
                self.NewControlId(), self.NewControlId(), "Set", "Clear",
                self.onSetFile, self.onClrFile))

        self.normConstantsData = (
            ("Water temperature [C]:", raw_settings.getId('NormAbsWaterTemp'),
                False) ,
            ("Water I(0):", raw_settings.getId('NormAbsWaterI0'), False),
            ("Absolute scaling constant:", raw_settings.getId('NormAbsWaterConst'),
                True)
            )

        self.carbonFilesData = (
            ("Glassy carbon:", raw_settings.getId('NormAbsCarbonFile'),
                self.NewControlId(), self.NewControlId(), "Set", "Clear",
                self.onSetFile, self.onClrFile),
            ("Glassy carbon calibration (optional):",
                raw_settings.getId('NormAbsCarbonCalFile'), self.NewControlId(),
                self.NewControlId(), "Set", "Clear", self.onSetFile, self.onClrFile),
            ("Glassy carbon background:",
                raw_settings.getId('NormAbsCarbonEmptyFile'),
                self.NewControlId(), self.NewControlId(), "Set", "Clear",
                self.onSetFile, self.onClrFile),
            ("Sample background:", raw_settings.getId('NormAbsCarbonSamEmptyFile'),
                self.NewControlId(), self.NewControlId(), "Set", "Clear",
                self.onSetFile, self.onClrFile),
            )

        self.carbonNormConstantsData = (
            ("Glassy carbon thickness [mm]:",
                raw_settings.getId('NormAbsCarbonThick'), 'float', False),
            ("Sample thickness [mm]:", raw_settings.getId('NormAbsCarbonSamThick'),
                'float', False),
            ("Upstream counter:", raw_settings.getId('NormAbsCarbonUpstreamCtr'),
                'choice', False),
            ("Downstream counter:", raw_settings.getId('NormAbsCarbonDownstreamCtr'),
                'choice', False),
            ("Absolute scaling constant:", raw_settings.getId('NormAbsCarbonConst'),
                'float', True),
            )

        top_sizer = self._createLayout()

        self._initialize()

        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):
        water_sizer = self._createWaterLayout()
        carbon_sizer = self._createCarbonLayout()

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(water_sizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        top_sizer.Add(carbon_sizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))

        return top_sizer

    def _createWaterLayout(self):
        box = wx.StaticBox(self, -1, 'Absolute scaling using water')

        self.abssc_chkbox = wx.CheckBox(box,
            self.raw_settings.getId('NormAbsWater'), ('Normalize processed data '
            'to absolute scale using water'))
        self.abssc_chkbox.Bind(wx.EVT_CHECKBOX, self.onChkBox)

        file_sizer = self.createWaterFileSettings(box)
        norm_const_sizer = self.createWaterNormConstants(box)
        chkbox_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkbox_sizer.Add(self.abssc_chkbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        chkbox_sizer.Add(file_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        chkbox_sizer.Add(norm_const_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        return chkbox_sizer

    def _createCarbonLayout(self):
        box = wx.StaticBox(self, -1, 'Absolute scaling using glassy carbon')

        noOfRows = int(len(self.carbonFilesData))
        file_sizer = wx.FlexGridSizer(cols=4, rows=noOfRows, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))

        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in self.carbonFilesData:

            setButton = wx.Button(box, setButton_ID, setButtonTxt)
            setButton.Bind(wx.EVT_BUTTON, setBindFunc)
            clrButton = wx.Button(box, clrButton_ID, clrButtonTxt)
            clrButton.Bind(wx.EVT_BUTTON, clrBindFunc)

            label = wx.StaticText(box, -1, labtxt)

            filenameLabel = wx.TextCtrl(box, labl_ID, "None",
                style = wx.TE_PROCESS_ENTER)
            filenameLabel.SetEditable(False)

            file_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
            file_sizer.Add(filenameLabel, 1, wx.EXPAND)
            file_sizer.Add(setButton, 1)
            file_sizer.Add(clrButton, 1)

        file_sizer.AddGrowableCol(1)


        noOfRows = int(ceil(float(len(self.carbonNormConstantsData))/2.))
        norm_const_sizer = wx.FlexGridSizer(cols=4, rows=noOfRows,
            vgap=self._FromDIP(3), hgap=self._FromDIP(5))

        counter_choices = self._getCounters()

        for eachLabel, item_id, item_type, has_button in self.carbonNormConstantsData:

            txt = wx.StaticText(box, -1, eachLabel)

            if item_type == 'choice':
                ctrl = wx.Choice(box, item_id, choices = counter_choices,
                    size=self._FromDIP((80, -1)))
            else:
                ctrl = wx.TextCtrl(box, item_id, '0', style=wx.TE_PROCESS_ENTER
                    |wx.TE_RIGHT, size=self._FromDIP((80, -1)))

            norm_const_sizer.Add(txt, 1, wx.ALIGN_CENTER_VERTICAL)
            norm_const_sizer.Add(ctrl, 1)

            if has_button == True:
                button = wx.Button(box, -1, 'Calculate')
                button.Bind(wx.EVT_BUTTON, self._onCalculateCarbonButton)
                norm_const_sizer.Add(button,1)


        abscar_chkbox = wx.CheckBox(box, self.raw_settings.getId('NormAbsCarbon'),
            'Normalize processed data to absolute scale using glassy carbon')
        abscar_chkbox.Bind(wx.EVT_CHECKBOX, self.onChkBox)
        abscarig_chkbox = wx.CheckBox(box, self.raw_settings.getId('NormAbsCarbonIgnoreBkg'),
            'Ignore background')
        abscarig_chkbox.Bind(wx.EVT_CHECKBOX, self.onIgnoreBackground)

        carbon_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        carbon_sizer.Add(abscar_chkbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        carbon_sizer.Add(abscarig_chkbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        carbon_sizer.Add(file_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))
        carbon_sizer.Add(norm_const_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        return carbon_sizer

    def createWaterFileSettings(self, parent):

        noOfRows = int(len(self.filesData))
        hSizer = wx.FlexGridSizer(cols=4, rows=noOfRows, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))

        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in self.filesData:

            setButton = wx.Button(parent, setButton_ID, setButtonTxt)
            setButton.Bind(wx.EVT_BUTTON, setBindFunc)
            clrButton = wx.Button(parent, clrButton_ID, clrButtonTxt)
            clrButton.Bind(wx.EVT_BUTTON, clrBindFunc)

            label = wx.StaticText(parent, -1, labtxt)

            filenameLabel = wx.TextCtrl(parent, labl_ID, "None",
                style=wx.TE_PROCESS_ENTER)
            filenameLabel.SetEditable(False)

            hSizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
            hSizer.Add(filenameLabel, 1, wx.EXPAND)
            hSizer.Add(setButton, 1)
            hSizer.Add(clrButton, 1)

        hSizer.AddGrowableCol(1)
        return hSizer

    def createWaterNormConstants(self, parent):

        noOfRows = int(len(self.normConstantsData))
        hSizer = wx.FlexGridSizer(cols=3, rows=noOfRows, vgap=self._FromDIP(3),
            hgap=self._FromDIP(5))

        temps = []
        for each in RAWSettings.water_scattering_table:
            temps.append(str(each))

        for eachLabel, id, has_button in self.normConstantsData:

            txt = wx.StaticText(parent, -1, eachLabel)

            if id == self.normConstantsData[0][1]:
                ctrl = wx.Choice(parent, id, choices = sorted(temps, key=int),
                    size=self._FromDIP((80, -1)))
                ctrl.Bind(wx.EVT_CHOICE, self._onTempChoice)
            else:
                ctrl = wx.TextCtrl(parent, id, '0', style=wx.TE_PROCESS_ENTER
                    |wx.TE_RIGHT, size=self._FromDIP((80, -1)))

            hSizer.Add(txt, 1, wx.ALIGN_CENTER_VERTICAL)
            hSizer.Add(ctrl, 1)

            if has_button == True:
                button = wx.Button(parent, -1, 'Calculate')
                button.Bind(wx.EVT_BUTTON, self._onCalculateWaterButton)
                hSizer.Add(button,1)

            else:
                hSizer.Add((1,1), 1)

        return hSizer

    def _getCounters(self):
        img_hdr = self.raw_settings.get('ImageHdrList')
        file_hdr = self.raw_settings.get('FileHdrList')

        try:
            counter_list = sorted(list(img_hdr.keys()) + list(file_hdr.keys()))
        except AttributeError:
            counter_list = ['']

        return counter_list

    def _initialize(self):
        self.ignoreBackground(not self.raw_settings.get('NormAbsCarbonIgnoreBkg'))

    def _onTempChoice(self, event):
        I0_ctrl = wx.FindWindowById(self.normConstantsData[1][1], self)

        temp_ctrl = event.GetEventObject()
        temp = temp_ctrl.GetStringSelection()

        I0_ctrl.SetValue(str(RAWSettings.water_scattering_table[int(temp)]))

    def _onCalculateWaterButton(self, event):
        self._calculateWaterConstant()

    def _onCalculateCarbonButton(self, event):
        self._calculateCarbonConstant()

    def _waitForWorkerThreadToFinish(self, const_name):
        mainframe = wx.FindWindowByName('MainFrame')
        thread_return_queue = mainframe.getQuestionReturnQueue()

        dialog = wx.FindWindowByName('OptionsDialog')
        dialog.Enable(False)

        while True:
            try:
                return_val = thread_return_queue.get(False)
                thread_return_queue.task_done()
                dialog.Enable(True)
                if return_val is not None:
                    constant_ctrl = wx.FindWindowById(self.raw_settings.getId(const_name), self)
                    constant_ctrl.SetValue(str(return_val))
                break
            except queue.Empty:
                wx.GetApp().Yield()
                time.sleep(0.1)

    def _calculateWaterConstant(self):
        if self._checkAbsScWaterFiles():
            waterI0 = wx.FindWindowById(self.raw_settings.getId('NormAbsWaterI0'), self).GetValue()
            try:
                waterI0 = float(waterI0)
            except TypeError:
                wx.MessageBox('Water I0 value contains illegal characters', 'Invalid input')
                return

            empty_cell_file = wx.FindWindowById(self.raw_settings.getId('NormAbsWaterEmptyFile'), self).GetValue()
            water_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsWaterFile'), self).GetValue()

            mainframe = wx.FindWindowByName('MainFrame')
            mainframe.queueTaskInWorkerThread('calculate_abs_water_const', [water_file, empty_cell_file, waterI0])
            wx.CallAfter(self._waitForWorkerThreadToFinish, 'NormAbsWaterConst')
        else:
             wx.MessageBox('Empty cell and/or water sample files could not be found.', 'Invalid input')

    def _calculateCarbonConstant(self):
        if self._checkCarbonFiles():
            carbon_bkg_file = wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonEmptyFile'), self).GetValue()
            carbon_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonFile'), self).GetValue()
            sample_bkg_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonSamEmptyFile'), self).GetValue()
            carbon_cal_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonCalFile'), self).GetValue()
            carbon_thickness =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonThick'), self).GetValue()
            sample_thickness =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonSamThick'), self).GetValue()
            ctr_upstream =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonUpstreamCtr'), self).GetStringSelection()
            ctr_downstream =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonDownstreamCtr'), self).GetStringSelection()
            ignore_background = wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonIgnoreBkg'), self).IsChecked()

            try:
                carbon_thickness = float(carbon_thickness)
                sample_thickness = float(sample_thickness)
            except TypeError:
                wx.MessageBox('Carbon or sample thickness value contains non-numeric characters', 'Invalid input')
                return

            param_dict = {'carbon_bkg_file' : carbon_bkg_file,
                        'carbon_file'       : carbon_file,
                        'sample_bkg_file'   : sample_bkg_file,
                        'carbon_cal_file'   : carbon_cal_file,
                        'carbon_thickness'  : carbon_thickness,
                        'sample_thickness'  : sample_thickness,
                        'ctr_upstream'      : ctr_upstream,
                        'ctr_downstream'    : ctr_downstream,
                        'ignore_background' : ignore_background,
                        }

            mainframe = wx.FindWindowByName('MainFrame')
            mainframe.queueTaskInWorkerThread('calculate_abs_carbon_const', param_dict)
            wx.CallAfter(self._waitForWorkerThreadToFinish, 'NormAbsCarbonConst')

        else:
             wx.MessageBox('Selected reference files could not be found.', 'Invalid input')


    def onSetFile(self, event):
        self.abssc_chkbox.SetValue(False)

        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID

        selectedFile = CreateFileDialog(wx.FD_OPEN)

        if selectedFile is None:
            return

        for each in self.filesData:
            if each[2] == ID:
                    textCtrl = wx.FindWindowById(each[1], self)
                    textCtrl.SetValue(str(selectedFile))

        for each in self.carbonFilesData:
            if each[2] == ID:
                    textCtrl = wx.FindWindowById(each[1], self)
                    textCtrl.SetValue(str(selectedFile))

    def onClrFile(self, event):

        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID

        for each in self.filesData:
            if each[3] == ID:
                textCtrl = wx.FindWindowById(each[1], self)
                textCtrl.SetValue('None')

        for each in self.carbonFilesData:
                if each[3] == ID:
                    textCtrl = wx.FindWindowById(each[1], self)
                    textCtrl.SetValue('None')


    def _checkAbsScWaterFiles(self):
        empty_cell_file = wx.FindWindowById(self.raw_settings.getId('NormAbsWaterEmptyFile'), self).GetValue()
        water_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsWaterFile'), self).GetValue()

        if os.path.isfile(empty_cell_file) and os.path.isfile(water_file):
            return True
        else:
            return False

    def _checkCarbonFiles(self):
        carbon_bkg_file = wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonEmptyFile'), self).GetValue()
        carbon_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonFile'), self).GetValue()
        sample_bkg_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonSamEmptyFile'), self).GetValue()
        carbon_calibration_file =  wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonCalFile'), self).GetValue()

        if carbon_calibration_file == 'None' or carbon_calibration_file is None:
            if wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonIgnoreBkg'), self).IsChecked():
                if os.path.isfile(carbon_file):
                    files_exist = True
                else:
                    files_exist = False
            else:
                if os.path.isfile(carbon_bkg_file) and os.path.isfile(carbon_file) and os.path.isfile(sample_bkg_file):
                    files_exist = True
                else:
                    files_exist = False
        else:
            if wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonIgnoreBkg'), self).IsChecked():
                if os.path.isfile(carbon_file) and os.path.isfile(carbon_calibration_file):
                    files_exist = True
                else:
                    files_exist = False
            else:
                if os.path.isfile(carbon_bkg_file) and os.path.isfile(carbon_file) and os.path.isfile(sample_bkg_file) and os.path.isfile(carbon_calibration_file):
                    files_exist = True
                else:
                    files_exist = False

        return files_exist

    def onIgnoreBackground(self, event):
        is_on = not event.IsChecked()
        self.ignoreBackground(is_on)

    def ignoreBackground(self, is_on):
        ignore_list =   ['NormAbsCarbonEmptyFile',
                        'NormAbsCarbonSamEmptyFile',
                        'NormAbsCarbonUpstreamCtr',
                        'NormAbsCarbonDownstreamCtr',
                        ]

        for item in ignore_list:
            item_id = self.raw_settings.getId(item)
            wx.FindWindowById(item_id).Enable(is_on)
            for each in self.carbonFilesData:
                if each[1] == item_id:
                    wx.FindWindowById(each[2]).Enable(is_on)
                    wx.FindWindowById(each[3]).Enable(is_on)

    def onChkBox(self, event):

        chkbox = event.GetEventObject()
        my_id = event.GetId()

        if my_id == self.raw_settings.getId('NormAbsWater') and chkbox.GetValue() == True:
            const = wx.FindWindowById(self.raw_settings.getId('NormAbsWaterConst'), self).GetValue()
            other_chkbox = wx.FindWindowById(self.raw_settings.getId('NormAbsCarbon'), self)
            try:
                float(const)
                other_chkbox.SetValue(False)
            except ValueError:
                wx.MessageBox('Normalization constant contains illegal characters', 'Invalid input')
                chkbox.SetValue(False)

        elif my_id == self.raw_settings.getId('NormAbsCarbon') and chkbox.GetValue() == True:
            const = wx.FindWindowById(self.raw_settings.getId('NormAbsCarbonConst'), self).GetValue()
            other_chkbox = wx.FindWindowById(self.raw_settings.getId('NormAbsWater'), self)
            try:
                float(const)
                other_chkbox.SetValue(False)
            except ValueError:
                wx.MessageBox('Normalization constant contains illegal characters', 'Invalid input')
                chkbox.SetValue(False)

class ReductionFlatfield(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = [
            'NormFlatfieldFile',
            'NormFlatfieldEnabled',
            'DarkCorrEnabled',
            'DarkCorrFilename',
            ]

        self._createLayout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self):

        flat_files_data = [("Flatfield image:",
            self.raw_settings.getId('NormFlatfieldFile'), self.NewControlId(),
            self.NewControlId(), "Set", "Clear", self.onSetFile, self.onClrFile),
            ]

        box = wx.StaticBox(self, -1, 'Flatfield correction')

        flat_chk = wx.CheckBox(box, self.raw_settings.getId('NormFlatfieldEnabled'),
            'Enable flatfield correction')

        flat_chk.Bind(wx.EVT_CHECKBOX, self._on_flat_chk)

        flat_file_sizer = self.createFileSettings(box, flat_files_data)
        flat_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flat_sizer.Add(flat_chk, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(5))
        flat_sizer.Add(flat_file_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))

        dark_files_data = [("Dark image:",
            self.raw_settings.getId('DarkCorrFilename'), self.NewControlId(),
            self.NewControlId(), "Set", "Clear", self.onSetFile, self.onClrFile),
            ]

        box = wx.StaticBox(self, -1, 'Dark correction')

        dark_chk = wx.CheckBox(box, self.raw_settings.getId('DarkCorrEnabled'),
            'Enable dark correction')

        dark_chk.Bind(wx.EVT_CHECKBOX, self._on_dark_chk)

        dark_file_sizer = self.createFileSettings(box, dark_files_data)
        dark_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        dark_sizer.Add(dark_chk, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM,
            border=self._FromDIP(5))
        dark_sizer.Add(dark_file_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(flat_sizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        final_sizer.Add(dark_sizer, 0, border=5, flag=wx.ALL|wx.EXPAND)

        self.SetSizer(final_sizer)

        self.filesData = [flat_files_data[0], dark_files_data[0]]


    def createFileSettings(self, parent, files_data):

        noOfRows = int(len(files_data))
        hSizer = wx.FlexGridSizer(cols=4, rows=noOfRows, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))

        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in files_data:

            setButton = wx.Button(parent, setButton_ID, setButtonTxt)
            setButton.Bind(wx.EVT_BUTTON, setBindFunc)
            clrButton = wx.Button(parent, clrButton_ID, clrButtonTxt)
            clrButton.Bind(wx.EVT_BUTTON, clrBindFunc)

            label = wx.StaticText(parent, -1, labtxt)

            filenameLabel = wx.TextCtrl(parent, labl_ID, "None", style = wx.TE_PROCESS_ENTER)
            filenameLabel.SetEditable(False)

            hSizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
            hSizer.Add(filenameLabel, 1, wx.EXPAND)
            hSizer.Add(setButton, 1)
            hSizer.Add(clrButton, 1)

        hSizer.AddGrowableCol(1)
        return hSizer

    def onSetFile(self, event):
        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID

        selectedFile = CreateFileDialog(wx.FD_OPEN)

        if selectedFile is not None:

            try:
                SASFileIO.loadImage(selectedFile, self.raw_settings)
                valid_file = True
            except Exception:
                valid_file = False

            if valid_file:
                for each in self.filesData:
                    if each[2] == ID:
                        textCtrl = wx.FindWindowById(each[1], self)
                        textCtrl.SetValue(str(selectedFile))

            else:
                msg = ('The selected file is not an image that RAW can load.')
                dlg = wx.MessageDialog(self, msg, "Invalid image file",
                    wx.OK|wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()

                for each in self.filesData:
                    if each[2] == ID:
                        if 'Flat' in each[0]:
                            flat_chk = wx.FindWindowById(self.raw_settings.getId('NormFlatfieldEnabled'))
                            flat_chk.SetValue(False)
                        elif 'Dark' in each[0]:
                            dark_chk = wx.FindWindowById(self.raw_settings.getId('DarkCorrEnabled'))
                            dark_chk.SetValue(False)


    def onClrFile(self, event):

        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID

        for each in self.filesData:
            if each[3] == ID:
                textCtrl = wx.FindWindowById(each[1], self)
                textCtrl.SetValue('')

                if 'Flat' in each[0]:
                    flat_chk = wx.FindWindowById(self.raw_settings.getId('NormFlatfieldEnabled'))
                    flat_chk.SetValue(False)
                elif 'Dark' in each[0]:
                    dark_chk = wx.FindWindowById(self.raw_settings.getId('DarkCorrEnabled'))
                    dark_chk.SetValue(False)

    def _on_flat_chk(self, event):
        chk = event.GetEventObject()
        file_ctrl = wx.FindWindowById(self.raw_settings.getId('NormFlatfieldFile'), self)

        selected_file = file_ctrl.GetValue()

        if event.IsChecked():
            if selected_file == '' or selected_file == 'None':
                msg = ('You must select a file to enable the flatfield correction.')
                dlg = wx.MessageDialog(self, msg, "No file selected",
                    wx.OK|wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()

                chk.SetValue(False)

            else:
                try:
                    SASFileIO.loadImage(selected_file, self.raw_settings)
                    valid_file = True
                except Exception:
                    valid_file = False

                if not valid_file:
                    msg = ('The selected flatfield file is not an image that RAW can load.')
                    dlg = wx.MessageDialog(self, msg, "Invalid image file",
                        wx.OK|wx.ICON_EXCLAMATION)
                    dlg.ShowModal()
                    dlg.Destroy()

                    chk.SetValue(False)

    def _on_dark_chk(self, event):
        chk = event.GetEventObject()
        file_ctrl = wx.FindWindowById(self.raw_settings.getId('DarkCorrFilename'), self)

        selected_file = file_ctrl.GetValue()

        if event.IsChecked():
            if selected_file == '' or selected_file == 'None':
                msg = ('You must select a file to enable the dark correction.')
                dlg = wx.MessageDialog(self, msg, "No file selected",
                    wx.OK|wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()

                chk.SetValue(False)

            else:
                try:
                    SASFileIO.loadImage(selected_file, self.raw_settings)
                    valid_file = True
                except Exception:
                    valid_file = False

                if not valid_file:
                    msg = ('The selected dark file is not an image that RAW can load.')
                    dlg = wx.MessageDialog(self, msg, "Invalid image file",
                        wx.OK|wx.ICON_EXCLAMATION)
                    dlg.ShowModal()
                    dlg.Destroy()

                    chk.SetValue(False)

class MolecularWeightPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['MWStandardMW',
                            'MWStandardI0',
                            'MWStandardConc',
                            'MWStandardFile',
                            'MWVcType',
                            'MWVcAProtein',
                            'MWVcBProtein',
                            'MWVcARna',
                            'MWVcBRna',
                            'MWVcCutoff',
                            'MWVcQmax',
                            'MWVpRho',
                            'MWVpCutoff',
                            'MWVpQmax',
                            'MWAbsRhoMprot',
                            'MWAbsRhoSolv',
                            'MWAbsNuBar',
                            'MWAbsR0']


        self.RelMWData = ( ("MW [kDa]:", raw_settings.getId('MWStandardMW')) ,
                        ("I(0):", raw_settings.getId('MWStandardI0')),
                        ("Conc. [mg/ml]:", raw_settings.getId('MWStandardConc')),
                        ("Filename:", raw_settings.getId('MWStandardFile')))
        self.VcMWData = ( ("Default Type:", raw_settings.getId('MWVcType')),
                        ("Protein Coef. A:", raw_settings.getId('MWVcAProtein')),
                        ("Protein Coef. B:", raw_settings.getId('MWVcBProtein')),
                        ("RNA Coef. A:", raw_settings.getId('MWVcARna')),
                        ("RNA Coef. B:", raw_settings.getId('MWVcBRna')),)
        self.VcMwData2 = (("Cutoff:", raw_settings.getId('MWVcCutoff')),
                        ("q Max (manual):", raw_settings.getId('MWVcQmax')),
                        )
        self.VpMWData = (("Density [kDa/A^3]:", raw_settings.getId('MWVpRho')),
                        ("Cutoff:", raw_settings.getId('MWVpCutoff')),
                        ("q Max (manual):", raw_settings.getId('MWVpQmax')),
                            )

        self.AbsMWData = (
            ("Electrons per dry mass of macromolecule [e-/g]:",
                raw_settings.getId('MWAbsRhoMprot')),
            ("Electrons per volume of aqueous solvent [e-/cm^3]:",
                raw_settings.getId('MWAbsRhoSolv')),
            ("Partial specific volume of the macromolecule [cm^3/g]:",
                raw_settings.getId('MWAbsNuBar')),
            ("Scattering length of an electron [cm/e-]:",
                raw_settings.getId('MWAbsR0')))

        rel_box = wx.StaticBox(self, -1, ('Molecular Weight Estimation Using a '
            'Standard'))
        vc_box = wx.StaticBox(self, -1, ('Molecular Weight Estimation From '
            'Volume of Correlation'))
        vp_box = wx.StaticBox(self, -1, ('Molecular Weight Estimation From '
            'Corrected Porod Volume'))
        abs_box = wx.StaticBox(self, -1, ('Molecular Weight Estimation From '
            'Absolute Intensity Calibration'))

        rel_mw_sizer = self.createRelMWSettings(rel_box)
        rel_mwbox_sizer = wx.StaticBoxSizer(rel_box, wx.VERTICAL)
        rel_mwbox_sizer.Add(rel_mw_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))

        vc_mw_sizer = self.createVcMWSettings(vc_box)
        vc_mwbox_sizer = wx.StaticBoxSizer(vc_box, wx.VERTICAL)
        vc_mwbox_sizer.Add(vc_mw_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))

        vp_mw_sizer = self.createVpMWSettings(vp_box)
        vp_mwbox_sizer = wx.StaticBoxSizer(vp_box, wx.VERTICAL)
        vp_mwbox_sizer.Add(vp_mw_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))

        abs_mw_sizer = self.createAbsMWSettings(abs_box)
        abs_mwbox_sizer = wx.StaticBoxSizer(abs_box, wx.VERTICAL)
        abs_mwbox_sizer.Add(abs_mw_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,
            border=self._FromDIP(5))

        reset_button = wx.Button(self, -1, 'Reset MW Parameters To Defaults')
        reset_button.Bind(wx.EVT_BUTTON, self._onResetButton)

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(rel_mwbox_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        final_sizer.Add(vc_mwbox_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        final_sizer.Add(vp_mwbox_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        final_sizer.Add(abs_mwbox_sizer, 0, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))
        final_sizer.AddStretchSpacer(1)
        final_sizer.Add(reset_button, 0, wx.ALIGN_RIGHT|wx.ALL,
            border=self._FromDIP(5))

        self.SetSizer(final_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createRelMWSettings(self, parent):

        hSizer = wx.FlexGridSizer(cols=4, rows=1, vgap=self._FromDIP(3),
            hgap=self._FromDIP(5))

        for txt, id in self.RelMWData:
            sizer = wx.BoxSizer(wx.VERTICAL)
            if id == self.raw_settings.getId('MWStandardFile'):
                ctrl = wx.TextCtrl(parent, id, '', size=self._FromDIP((200,-1)),
                    style = wx.TE_PROCESS_ENTER)
            else:
                ctrl = wx.TextCtrl(parent, id, '', style = wx.TE_PROCESS_ENTER)
            txt = wx.StaticText(parent, -1, txt)

            sizer.Add(txt, 0, wx.ALIGN_CENTER_HORIZONTAL)
            sizer.Add(ctrl, 0)

            hSizer.Add(sizer, 0)

        return hSizer

    def createVcMWSettings(self, parent):
        hSizer = wx.FlexGridSizer(cols=5, rows=1, vgap=self._FromDIP(3),
            hgap=self._FromDIP(5))

        for txt, my_id in self.VcMWData:
            sizer = wx.BoxSizer(wx.VERTICAL)
            if my_id == self.raw_settings.getId('MWVcType'):
                ctrl = wx.Choice(parent, my_id, choices = ['Protein', 'RNA'])
            else:
                ctrl = wx.TextCtrl(parent, my_id, '', style = wx.TE_PROCESS_ENTER)

            txt = wx.StaticText(parent, -1, txt)

            sizer.Add(txt, 0, wx.ALIGN_CENTER_HORIZONTAL)
            sizer.Add(ctrl, 0)

            hSizer.Add(sizer, 0)

        h_sizer2 = wx.FlexGridSizer(cols=2, vgap=self._FromDIP(3),
            hgap=self._FromDIP(5))

        for txt, my_id in self.VcMwData2:
            if my_id == self.raw_settings.getId('MWVcCutoff'):
                ctrl = wx.Choice(parent, my_id, choices=['Default', '8/Rg',
                    'log(I0/I(q))', 'Manual'])
            else:
                ctrl = wx.TextCtrl(parent, my_id, '', style = wx.TE_PROCESS_ENTER)

            txt = wx.StaticText(parent, -1, txt)

            h_sizer2.Add(txt, flag=wx.ALIGN_CENTER_VERTICAL)
            h_sizer2.Add(ctrl, flag=wx.ALIGN_CENTER_VERTICAL)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(hSizer)
        top_sizer.Add(h_sizer2, border=5, flag=wx.TOP)

        return top_sizer

    def createVpMWSettings(self, parent):
        sizer = wx.FlexGridSizer(cols=2, vgap=self._FromDIP(3),
            hgap=self._FromDIP(5))

        for txt, my_id in self.VpMWData:
            if my_id == self.raw_settings.getId('MWVpCutoff'):
                ctrl = wx.Choice(parent, my_id, choices=['Default', '8/Rg',
                    'log(I0/I(q))', 'Manual'])
                txt = wx.StaticText(parent, -1, txt)
            else:
                ctrl = wx.TextCtrl(parent, my_id, '', style = wx.TE_PROCESS_ENTER)
                txt = wx.StaticText(parent, -1, txt)

            sizer.Add(txt)
            sizer.Add(ctrl)

        return sizer

    def createAbsMWSettings(self, parent):
        vSizer = wx.BoxSizer(wx.VERTICAL)

        for txt, id in self.AbsMWData:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            ctrl = wx.TextCtrl(parent, id, '', style = wx.TE_PROCESS_ENTER)
            txt = wx.StaticText(parent, -1, txt)

            sizer.Add(txt, 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(ctrl, 0)

            vSizer.Add(sizer, 0)

        return vSizer

    def _onResetButton(self, evt):
        default_settings = RAWSettings.RawGuiSettings()

        for key in self.update_keys:
            id, type = self.raw_settings.getIdAndType(key)

            reset = True
            for item in self.RelMWData:
                if id == item[1]:
                    reset = False

            if reset:
                val = default_settings.get(key)
                obj = wx.FindWindowById(id, self)

                if type == 'bool':
                    obj.SetValue(val)
                elif type == 'list':
                    obj.SetValue(val)

                elif type == 'choice':
                    choice_list = obj.GetStrings()
                    idx = choice_list.index(val)
                    obj.Select(idx)

                elif type == 'text' or type == 'int' or type == 'float':
                    try:
                        obj.SetValue(val)
                    except TypeError:
                        obj.SetValue(str(val))

class ReductionNormalizationPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        self.update_keys = ['NormalizationList', 'EnableNormalization']

        self.raw_settings = raw_settings

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.norm_list_id = raw_settings.getId('NormalizationList')
        self.enable_norm_id = raw_settings.getId('EnableNormalization')


        img_hdr = self.raw_settings.get('ImageHdrList')
        file_hdr = self.raw_settings.get('FileHdrList')

        try:
            self.expr_combo_list = [''] + sorted(list(img_hdr.keys()) + list(file_hdr.keys()))
        except AttributeError:
            self.expr_combo_list = ['']

        self.selected_item = None

        normsizer = self.createNormalizeList()

        final_sizer = wx.BoxSizer(wx.VERTICAL)

        final_sizer.Add(normsizer, 1, wx.EXPAND |wx.ALL, border=self._FromDIP(5))

        self.SetSizer(final_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createNormalizeList(self):

        operator_list = ['/', '+', '-', '*']
        self.operator_choice = wx.Choice(self, -1, choices = operator_list)
        self.operator_choice.Select(0)

        self.expr_combo = wx.ComboBox(self, -1, choices = self.expr_combo_list,
            style = wx.TE_PROCESS_ENTER)
        self.expr_combo.Select(0)

        self.norm_list = NormListCtrl(self, self.norm_list_id, style = wx.LC_REPORT)
        self.norm_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onNormListSelection)

        self.norm_list_title = wx.StaticText(self, -1, 'Normalization List:')

        self.enable_norm_chkbox = wx.CheckBox(self, self.enable_norm_id,
            'Enable Normalization')

        self.up_button = wx.Button(self, -1, 'Move up')
        self.up_button.Bind(wx.EVT_BUTTON, self.onUpButton)
        self.down_button = wx.Button(self, -1, 'Move down')
        self.down_button.Bind(wx.EVT_BUTTON, self.onDownButton)

        self.delete_button = wx.Button(self, -1, 'Delete')
        self.delete_button.Bind(wx.EVT_BUTTON, self.onDeleteButton)
        self.clear_norm_list_button = wx.Button(self, -1, 'Clear all')
        self.clear_norm_list_button.Bind(wx.EVT_BUTTON, self.onClearListButton)

        add_button = wx.Button(self, -1, 'Add')
        add_button.Bind(wx.EVT_BUTTON, self.onAddButton)

        calc_button = wx.Button(self, -1, 'Calc')
        calc_button.Bind(wx.EVT_BUTTON, self.onCalcButton)

        #ud_button_sizer = wx.BoxSizer(wx.VERTICAL)
        ud_button_sizer = wx.FlexGridSizer(cols=1, rows=4, vgap=self._FromDIP(3),
            hgap=self._FromDIP(0))
        ud_button_sizer.Add(self.up_button,1, wx.EXPAND)
        ud_button_sizer.Add(self.down_button, 1, wx.EXPAND)
        ud_button_sizer.Add(self.delete_button, 1, wx.EXPAND)
        ud_button_sizer.Add(self.clear_norm_list_button, 1, wx.EXPAND)

        list_sizer= wx.BoxSizer()
        list_sizer.Add(self.norm_list,1, wx.EXPAND|wx.RIGHT,
            border=self._FromDIP(3))
        list_sizer.Add(ud_button_sizer,0, wx.LEFT,
            border=self._FromDIP(3))

        ctrl_sizer = wx.BoxSizer()
        ctrl_sizer.Add(self.operator_choice,0, wx.ALIGN_CENTER |wx.RIGHT,
            border=self._FromDIP(3))
        ctrl_sizer.Add(self.expr_combo, 1, wx.EXPAND|wx.RIGHT,
            border=self._FromDIP(3))
        ctrl_sizer.Add(add_button,0, wx.ALIGN_CENTER |wx.RIGHT,
            border=self._FromDIP(3))
        ctrl_sizer.Add(calc_button,0, wx.ALIGN_CENTER)

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(self.enable_norm_chkbox, 0, wx.BOTTOM,
            border=self._FromDIP(5))
        final_sizer.Add(self.norm_list_title,0, wx.BOTTOM, border=self._FromDIP(5))
        final_sizer.Add(list_sizer, 1, wx.EXPAND)
        final_sizer.Add(ctrl_sizer, 0, wx.EXPAND|wx.TOP, border=self._FromDIP(5))

        return final_sizer

    def onNormListSelection(self, event):
        self.selected_item = event.GetItem()

    def onDeleteButton(self, event):
        items = self.norm_list.getSelectedItems()

        if len(items) > 0:
            self.norm_list.DeleteItem(items[0])

    def onUpButton(self, event):
        itemidx = self.norm_list.GetFirstSelected()
        self.norm_list.moveItemUp(itemidx)

    def onDownButton(self, event):
        itemidx = self.norm_list.GetFirstSelected()
        self.norm_list.moveItemDown(itemidx)

    def onClearListButton(self, event):
        self.norm_list.DeleteAllItems()

    def onCalcButton(self, event):
        expr = self.expr_combo.GetValue()
        val = self.calcExpression(expr)

        if val is not None:
            wx.MessageBox(expr + ' = ' + str(val), style = wx.ICON_INFORMATION)

    def calcExpression(self, expr):

        if expr != '':
            img_hdr = self.raw_settings.get('ImageHdrList')
            file_hdr = self.raw_settings.get('FileHdrList')

            self.mathparser = SASParser.PyMathParser()
            self.mathparser.addDefaultFunctions()
            self.mathparser.addDefaultVariables()
            self.mathparser.addSpecialVariables(file_hdr)
            self.mathparser.addSpecialVariables(img_hdr)
            self.mathparser.expression = expr

            try:
                val = self.mathparser.evaluate()
                return val
            except NameError as msg:
                wx.MessageBox(str(msg), 'Error')
                return None
        else:
            return None

    def onAddButton(self, event):
        op = self.operator_choice.GetStringSelection()
        expr = self.expr_combo.GetValue()

        if expr != '':

            if self.calcExpression(expr) is None:
                return
            else:
                self.norm_list.add(op, expr)

    def updateNonGuiChanges(self):
        img_hdr = self.raw_settings.get('ImageHdrList')
        file_hdr = self.raw_settings.get('FileHdrList')

        self.expr_combo_list = [''] + sorted(list(img_hdr.keys()) + list(file_hdr.keys()))

        if not self.expr_combo.IsTextEmpty():
            expr = self.expr_combo.GetValue()
        else:
            expr = ''

        self.expr_combo.SetItems(self.expr_combo_list)

        if expr != '':
            self.expr_combo.SetValue(expr)


class OnlineModePanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        self.update_keys = ['OnlineFilterList', 'EnableOnlineFiltering']

        self.raw_settings = raw_settings

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.filt_list_id = raw_settings.getId('OnlineFilterList')
        self.enable_filt_id = raw_settings.getId('EnableOnlineFiltering')

        # self.expr_combo_list = ['test']
        self.selected_item = None

        normsizer = self.createOnlineFilterList()

        final_sizer = wx.BoxSizer(wx.VERTICAL)

        final_sizer.Add(normsizer, 1, wx.EXPAND |wx.ALL, border=self._FromDIP(5))

        self.SetSizer(final_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createOnlineFilterList(self):

        filter_list = ['Ignore', 'Open only with']
        self.filter_choice = wx.Choice(self, -1, choices = filter_list)
        self.filter_choice.Select(0)


        position_list = ['At start', 'Anywhere', 'At end']
        self.position_choice = wx.Choice(self, -1, choices = position_list)
        self.position_choice.Select(0)


        self.expr = wx.TextCtrl(self, -1, value="", style = wx.TE_PROCESS_ENTER)

        self.online_list = OnlineListCtrl(self, self.filt_list_id, style = wx.LC_REPORT)
        self.online_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onNormListSelection)

        self.online_list_title = wx.StaticText(self, -1, 'Online Filter List:')

        self.enable_norm_chkbox = wx.CheckBox(self, self.enable_filt_id, 'Enable Online Filtering')

        self.up_button = wx.Button(self, -1, 'Move up')
        self.up_button.Bind(wx.EVT_BUTTON, self.onUpButton)
        self.down_button = wx.Button(self, -1, 'Move down')
        self.down_button.Bind(wx.EVT_BUTTON, self.onDownButton)

        self.delete_button = wx.Button(self, -1, 'Delete')
        self.delete_button.Bind(wx.EVT_BUTTON, self.onDeleteButton)
        self.clear_online_list_button = wx.Button(self, -1, 'Clear all')
        self.clear_online_list_button.Bind(wx.EVT_BUTTON, self.onClearListButton)

        add_button = wx.Button(self, -1, 'Add')
        add_button.Bind(wx.EVT_BUTTON, self.onAddButton)

        #ud_button_sizer = wx.BoxSizer(wx.VERTICAL)
        ud_button_sizer = wx.FlexGridSizer(cols=1, rows=4, vgap=self._FromDIP(3),
            hgap=self._FromDIP(0))
        ud_button_sizer.Add(self.up_button,1, wx.EXPAND)
        ud_button_sizer.Add(self.down_button, 1, wx.EXPAND)
        ud_button_sizer.Add(self.delete_button, 1, wx.EXPAND)
        ud_button_sizer.Add(self.clear_online_list_button, 1, wx.EXPAND)

        list_sizer= wx.BoxSizer()
        list_sizer.Add(self.online_list,1, wx.EXPAND|wx.RIGHT,
            border=self._FromDIP(3))
        list_sizer.Add(ud_button_sizer,0, wx.LEFT,
            border=self._FromDIP(3))

        ctrl_sizer = wx.BoxSizer()
        ctrl_sizer.Add(self.filter_choice,0, wx.ALIGN_CENTER |wx.RIGHT,
            border=self._FromDIP(3))
        ctrl_sizer.Add(self.expr, 1, wx.EXPAND|wx.RIGHT,
            border=self._FromDIP(3))
        ctrl_sizer.Add(self.position_choice,0, wx.ALIGN_CENTER)
        ctrl_sizer.Add(add_button,0, wx.ALIGN_CENTER |wx.RIGHT,
            border=self._FromDIP(3))

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(self.enable_norm_chkbox, 0, wx.BOTTOM,
            border=self._FromDIP(5))
        final_sizer.Add(self.online_list_title,0, wx.BOTTOM,
            border=self._FromDIP(5))
        final_sizer.Add(list_sizer, 1, wx.EXPAND)
        final_sizer.Add(ctrl_sizer, 0, wx.EXPAND|wx.TOP, border=self._FromDIP(5))

        return final_sizer

    def onNormListSelection(self, event):
        self.selected_item = event.GetItem()

    def onDeleteButton(self, event):
        items = self.online_list.getSelectedItems()

        if len(items) > 0:
            self.online_list.DeleteItem(items[0])

    def onUpButton(self, event):
        itemidx = self.online_list.GetFirstSelected()
        self.online_list.moveItemUp(itemidx)

    def onDownButton(self, event):
        itemidx = self.online_list.GetFirstSelected()
        self.online_list.moveItemDown(itemidx)

    def onClearListButton(self, event):
        self.online_list.DeleteAllItems()

    def onAddButton(self, event):
        filt = self.filter_choice.GetStringSelection()
        expr = self.expr.GetValue()
        pos = self.position_choice.GetStringSelection()

        if expr != '':
            self.online_list.add(filt, expr, pos)

class MetadataPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        self.update_keys = ['MetadataList', 'EnableMetadata']

        self.raw_settings = raw_settings

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.meta_list_id = raw_settings.getId('MetadataList')
        self.enable_meta_id = raw_settings.getId('EnableMetadata')


        self.selected_item = None

        metasizer = self.createMetadataList()

        final_sizer = wx.BoxSizer(wx.VERTICAL)

        final_sizer.Add(metasizer, 1, wx.EXPAND |wx.ALL, border=self._FromDIP(5))

        self.SetSizer(final_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createMetadataList(self):

        self.meta_list = MetadataListCtrl(self, self.meta_list_id, style = wx.LC_REPORT)
        self.meta_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onMetaListSelection)

        self.meta_list_title = wx.StaticText(self, -1, 'Metadata List:')

        self.enable_meta_chkbox = wx.CheckBox(self, self.enable_meta_id, 'Enable Metadata')

        self.up_button = wx.Button(self, -1, 'Move up')
        self.up_button.Bind(wx.EVT_BUTTON, self.onUpButton)
        self.down_button = wx.Button(self, -1, 'Move down')
        self.down_button.Bind(wx.EVT_BUTTON, self.onDownButton)

        self.delete_button = wx.Button(self, -1, 'Delete')
        self.delete_button.Bind(wx.EVT_BUTTON, self.onDeleteButton)
        self.clear_meta_list_button = wx.Button(self, -1, 'Clear all')
        self.clear_meta_list_button.Bind(wx.EVT_BUTTON, self.onClearListButton)

        self.key_ctrl = wx.TextCtrl(self)
        self.val_ctrl = wx.TextCtrl(self)

        add_button = wx.Button(self, -1, 'Add')
        add_button.Bind(wx.EVT_BUTTON, self.onAddButton)

        #ud_button_sizer = wx.BoxSizer(wx.VERTICAL)
        ud_button_sizer = wx.FlexGridSizer(cols=1, rows=4, vgap=self._FromDIP(3),
            hgap=self._FromDIP(0))
        ud_button_sizer.Add(self.up_button,1, wx.EXPAND)
        ud_button_sizer.Add(self.down_button, 1, wx.EXPAND)
        ud_button_sizer.Add(self.delete_button, 1, wx.EXPAND)
        ud_button_sizer.Add(self.clear_meta_list_button, 1, wx.EXPAND)

        list_sizer= wx.BoxSizer()
        list_sizer.Add(self.meta_list,1, wx.EXPAND|wx.RIGHT, self._FromDIP(3))
        list_sizer.Add(ud_button_sizer,0, wx.LEFT, self._FromDIP(3))

        meta_entry_sizer = wx.FlexGridSizer(cols=2, rows=2, vgap=self._FromDIP(3),
            hgap=self._FromDIP(3))
        meta_entry_sizer.Add(wx.StaticText(self, label='Key:'))
        meta_entry_sizer.Add(self.key_ctrl, flag=wx.EXPAND, proportion=1)
        meta_entry_sizer.Add(wx.StaticText(self, label='Value:'))
        meta_entry_sizer.Add(self.val_ctrl, flag=wx.EXPAND, proportion=1)
        meta_entry_sizer.AddGrowableCol(1)

        ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        ctrl_sizer.Add(meta_entry_sizer, flag=wx.EXPAND|wx.TOP,
            border=self._FromDIP(3))
        ctrl_sizer.Add(add_button, border=self._FromDIP(5), flag=wx.TOP|wx.BOTTOM)

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(self.enable_meta_chkbox, 0, wx.BOTTOM,
            border=self._FromDIP(5))
        final_sizer.Add(self.meta_list_title,0, wx.BOTTOM, border=self._FromDIP(5))
        final_sizer.Add(list_sizer, 1, wx.EXPAND)
        final_sizer.Add(ctrl_sizer, 0, wx.EXPAND|wx.TOP, border=self._FromDIP(5))

        return final_sizer

    def onMetaListSelection(self, event):
        self.selected_item = event.GetItem()

    def onDeleteButton(self, event):
        items = self.meta_list.getSelectedItems()

        if len(items) > 0:
            self.meta_list.DeleteItem(items[0])

    def onUpButton(self, event):
        itemidx = self.meta_list.GetFirstSelected()
        self.meta_list.moveItemUp(itemidx)

    def onDownButton(self, event):
        itemidx = self.meta_list.GetFirstSelected()
        self.meta_list.moveItemDown(itemidx)

    def onClearListButton(self, event):
        self.meta_list.DeleteAllItems()

    def onAddButton(self, event):
        key = self.key_ctrl.GetValue()
        val = self.val_ctrl.GetValue()

        if key != '' and val != '':
            self.meta_list.add(key, val)
        else:
            msg = ('Key and Value must be not empty.')
            wx.MessageBox(msg, 'Cannot add empty metadata')

    def updateNonGuiChanges(self):
        img_hdr = self.raw_settings.get('ImageHdrList')
        file_hdr = self.raw_settings.get('FileHdrList')

        self.expr_combo_list = [''] + sorted(list(img_hdr.keys()) + list(file_hdr.keys()))

        if not self.expr_combo.IsTextEmpty():
            expr = self.expr_combo.GetValue()
        else:
            expr = ''

        self.expr_combo.SetItems(self.expr_combo_list)

        if expr != '':
            self.expr_combo.SetValue(expr)

class GeneralOptionsPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['ManipItemCollapsed', 'DatHeaderOnTop',
            'UseHeaderForMask', 'DetectorFlipped90', 'OnlineModeOnStartup',
            'OnlineStartupDir', 'DetectorFlipLR', 'DetectorFlipUD',
            'UseHeaderForConfig', 'HdrLoadConfigDir'
            ]# 'PromptConfigLoad']

        self.chkboxdata = [
            ('Hide controls on profile items for new plots',
                raw_settings.getId('ManipItemCollapsed')),
            ('Write header on top of dat files', raw_settings.getId('DatHeaderOnTop')),
            ('Use header for mask creation (Xenocs instruments)',
                raw_settings.getId('UseHeaderForMask')),
            ('Use header for new config load (Xenocs instruments)',
                raw_settings.getId('UseHeaderForConfig')),
            ('Detector is rotated 90 degrees (Xenocs instruments)',
                raw_settings.getId('DetectorFlipped90')),
            ('Flip detector image left-right (non-Xenocs)',
                raw_settings.getId('DetectorFlipLR')),
            ('Flip detector image up-down (non-Xenocs)',
                raw_settings.getId('DetectorFlipUD')),
            #('Prompt for config load on startup', raw_settings.getId('PromptConfigLoad')),
            ('Start online mode on startup',
                raw_settings.getId('OnlineModeOnStartup'))]

        options_sizer = self.createGeneralOptionsData()

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(options_sizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))

        self.SetSizer(final_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createGeneralOptionsData(self):

        box = wx.StaticBox(self, -1, 'General Options')
        staticBoxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        treatmentSizer = wx.BoxSizer(wx.VERTICAL)
        for each, id in self.chkboxdata:
            chkBox = wx.CheckBox(box, id, each)
            chkBox.Bind(wx.EVT_CHECKBOX, self.onChkBox)
            treatmentSizer.Add(chkBox, 0, wx.TOP, border=self._FromDIP(5))

        staticBoxSizer.Add(treatmentSizer, 0, wx.BOTTOM|wx.LEFT,
            border=self._FromDIP(5))

        online_dir_ctrl = wx.TextCtrl(box, self.raw_settings.getId('OnlineStartupDir'),
            '', style = wx.TE_PROCESS_ENTER)
        online_dir_txt = wx.StaticText(box, -1, 'Online mode startup directory:')

        setdir_button = wx.Button(box, -1, 'Set')
        setdir_button.Bind(wx.EVT_BUTTON, self.onOnlineDirSet)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(online_dir_txt, 0, wx.ALIGN_CENTER_VERTICAL)
        hsizer.Add(online_dir_ctrl, 1, wx.EXPAND|wx.LEFT, border=self._FromDIP(5))
        hsizer.Add(setdir_button, 0, wx.LEFT, border=self._FromDIP(5))

        hdrldconfig_dir_ctrl = wx.TextCtrl(box, self.raw_settings.getId('HdrLoadConfigDir'),
            '', style = wx.TE_PROCESS_ENTER)
        hdrldconfig_dir_txt = wx.StaticText(box, -1, 'Header loaded config directory:')

        hdrldsetdir_button = wx.Button(box, -1, 'Set')
        hdrldsetdir_button.Bind(wx.EVT_BUTTON, self.onHdrLdConfigDirSet)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.Add(hdrldconfig_dir_txt, 0, wx.ALIGN_CENTER_VERTICAL)
        hsizer2.Add(hdrldconfig_dir_ctrl, 1, wx.EXPAND|wx.LEFT,
            border=self._FromDIP(5))
        hsizer2.Add(hdrldsetdir_button, 0, wx.LEFT, border=self._FromDIP(5))

        staticBoxSizer.Add(hsizer, 1, wx.EXPAND|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        staticBoxSizer.Add(hsizer2, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))

        return staticBoxSizer

    def onOnlineDirSet(self, event):
        dirdlg = wx.DirDialog(self.GetParent(), "Please select directory:", '')

        if dirdlg.ShowModal() == wx.ID_OK:
            selected_path = dirdlg.GetPath()
            ctrl = wx.FindWindowById(self.raw_settings.getId('OnlineStartupDir'), self)
            ctrl.SetValue(str(selected_path))

        dirdlg.Destroy()

    def onHdrLdConfigDirSet(self, event):
        dirdlg = wx.DirDialog(self.GetParent(), "Please select directory:", '')

        if dirdlg.ShowModal() == wx.ID_OK:
            selected_path = dirdlg.GetPath()
            ctrl = wx.FindWindowById(self.raw_settings.getId('HdrLoadConfigDir'), self)
            ctrl.SetValue(str(selected_path))

        dirdlg.Destroy()

    def onChkBox(self, event):
        pass

class ConfigRootSettings(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        panelsizer = self._createLayout()
        self.SetSizer(panelsizer)

    def _createLayout(self):
        reset_button = wx.Button(self, wx.ID_ANY, 'Reset ALL settings to default values')
        reset_button.Bind(wx.EVT_BUTTON, self._onResetButton)

    def _onResetButton(self, evt):
        dial = wx.MessageDialog(self, 'Are you sure you want to reset ALL settings to default values?', 'Are you sure?',
                                wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)

        answer = dial.ShowModal()
        dial.Destroy()

        if answer == wx.ID_CANCEL or answer == wx.ID_NO:
            return

        default_settings = RAWSettings.RawGuiSettings()
        default_params = default_settings.getAllParams()

        for key, value in default_params.items():
            self.raw_settings.set(key, value[0])

        all_update_keys = wx.FindWindowByName('OptionsDialog').treebook.getAllUpdateKeys()

        for key in all_update_keys:
            val_id, val_type = self.raw_settings.getIdAndType(key)
            val = self.raw_settings.get(key)
            obj = wx.FindWindowById(val_id)

            if val_type == 'bool':
                obj.SetValue(val)
            elif val_type == 'list':
                obj.SetValue(val)

            elif val_type == 'choice':
                choice_list = obj.GetStrings()
                if val is not None:
                    idx = choice_list.index(val)
                else:
                    idx=0
                obj.Select(idx)

            elif val_type == 'text' or val_type == 'int' or val_type == 'float':
                try:
                    obj.SetValue(val)
                except TypeError:
                    obj.SetValue(str(val))

        if self.raw_settings.get('autoFindATSAS'):
            myId = -1
            all_options = wx.FindWindowByName('OptionsDialog').all_options
            for item in all_options:
                if item[2] == "ATSAS":
                    myId = item[1]

            if myId != -1:
                atsasPanel = wx.FindWindowById(myId, self.GetParent())
                atsasPanel.setATSASDir()

        myId = -1
        all_options = wx.FindWindowByName('OptionsDialog').all_options
        for item in all_options:
            if item[2] == "Image/Header Format":
                myId = item[1]

        if myId != -1:
            Panel = wx.FindWindowById(myId, self.GetParent())
            Panel.onClearAllButton(-1)

class ReductionOptionsPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

class SaveDirectoriesPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['ProcessedFilePath' , 'AveragedFilePath' ,
            'SubtractedFilePath', 'BiftFilePath', 'GnomFilePath',
            'AutoSaveOnImageFiles', 'AutoSaveOnAvgFiles', 'AutoSaveOnSub',
            'AutoSaveOnBift', 'AutoSaveOnGnom']

                                                                                      #Set button id , clr button id
        self.directory_data = (
            ('Processed files:', raw_settings.getId('ProcessedFilePath'),
                self.NewControlId(), self.NewControlId()),
            ('Averaged files:',  raw_settings.getId('AveragedFilePath'),
                self.NewControlId(), self.NewControlId()),
            ('Subtracted files:',raw_settings.getId('SubtractedFilePath'),
                self.NewControlId(), self.NewControlId()),
            ('BIFT files:', raw_settings.getId('BiftFilePath'),
                self.NewControlId(), self.NewControlId()),
            ('GNOM files:', raw_settings.getId('GnomFilePath'),
                self.NewControlId(), self.NewControlId()))

        self.auto_save_data = (
            ('Save Processed Image Files Automatically',
                raw_settings.getId('AutoSaveOnImageFiles')),
            ('Save Averaged Data Files Automatically',
                raw_settings.getId('AutoSaveOnAvgFiles')),
            ('Save Subtracted Data Files Automatically',
                raw_settings.getId('AutoSaveOnSub')),
            ('Save BIFT Data Files Automatically',
                raw_settings.getId('AutoSaveOnBift')),
            ('Save GNOM Data Files Automatically',
                raw_settings.getId('AutoSaveOnGnom')))

        dir_sizer = self.createDirectoryOptions()

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        autosave_sizer = self.createAutoSaveOptions()

        top_sizer.Add(autosave_sizer, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        top_sizer.Add(dir_sizer, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createAutoSaveOptions(self):

        box = wx.StaticBox(self, -1, 'Auto Save')
        chkbox_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        for label, id in self.auto_save_data:
            chkbox = wx.CheckBox(box, id, label)
            chkbox.Bind(wx.EVT_CHECKBOX, self.onSaveCheckbox)
            chkbox_sizer.Add(self._FromDIP((1,5)), 0)
            chkbox_sizer.Add(chkbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT,
                border=self._FromDIP(5))

        chkbox_sizer.Add(self._FromDIP((1,5)), 0)
        return chkbox_sizer

    def createDirectoryOptions(self):

        box = wx.StaticBox(self, -1, 'Save Directories')
        chkbox_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        h_sizer = wx.FlexGridSizer(cols=4, rows=len(self.directory_data),
            vgap=self._FromDIP(3), hgap=self._FromDIP(3))

        for labtxt, labl_id, set_button_id, clr_button_id in self.directory_data:

            if labtxt is not None:

                set_button = wx.Button(box, set_button_id, 'Set')
                set_button.Bind(wx.EVT_BUTTON, self.onSetFile)
                clr_button = wx.Button(box, clr_button_id, 'Clear')
                clr_button.Bind(wx.EVT_BUTTON, self.onClrFile)

                label = wx.StaticText(box, -1, labtxt)

                filenameLabel = wx.TextCtrl(box, labl_id, '',
                    style=wx.TE_PROCESS_ENTER)
                filenameLabel.SetEditable(False)

                h_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
                h_sizer.Add(filenameLabel, 1, wx.EXPAND)
                h_sizer.Add(set_button, 1)
                h_sizer.Add(clr_button, 1)

        h_sizer.AddGrowableCol(1)
        chkbox_sizer.Add(h_sizer, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))

        return chkbox_sizer

    def onSetFile(self, event):

        button_obj = event.GetEventObject()
        id = button_obj.GetId()            # Button ID

        dirdlg = wx.DirDialog(self.GetParent(), "Please select directory:", '')

        if dirdlg.ShowModal() == wx.ID_OK:
            selected_path = dirdlg.GetPath()

            for labtxt, labl_id, set_button_id, clr_button_id in self.directory_data:
                if set_button_id == id:
                    text_ctrl = wx.FindWindowById(labl_id, self)
                    text_ctrl.SetValue(str(selected_path))

        dirdlg.Destroy()

    def onClrFile(self, event):

        button_obj = event.GetEventObject()
        id = button_obj.GetId()            # Button ID

        for labtxt, labl_id, set_button_id, clr_button_id in self.directory_data:
                if clr_button_id == id:
                    textCtrl = wx.FindWindowById(labl_id)
                    textCtrl.SetValue('None')

                    if labl_id == self.raw_settings.getId('ProcessedFilePath'):
                        wx.FindWindowById(self.raw_settings.getId('AutoSaveOnImageFiles'), self).SetValue(False)
                    elif labl_id == self.raw_settings.getId('AveragedFilePath'):
                        wx.FindWindowById(self.raw_settings.getId('AutoSaveOnAvgFiles'), self).SetValue(False)
                    elif labl_id == self.raw_settings.getId('SubtractedFilePath'):
                        wx.FindWindowById(self.raw_settings.getId('AutoSaveOnSub'), self).SetValue(False)
                    elif labl_id == self.raw_settings.getId('BiftFilePath'):
                        wx.FindWindowById(self.raw_settings.getId('AutoSaveOnBift'), self).SetValue(False)
                    elif labl_id == self.raw_settings.getId('GnomFilePath'):
                        wx.FindWindowById(self.raw_settings.getId('AutoSaveOnGnom'), self).SetValue(False)

    def onSaveCheckbox(self, event):
        my_id = event.GetId()

        checkbox = wx.FindWindowById(my_id, self)

        if checkbox.GetValue():
            if my_id == self.raw_settings.getId('AutoSaveOnImageFiles'):
                directory = wx.FindWindowById(self.raw_settings.getId('ProcessedFilePath'), self).GetValue()

            elif my_id == self.raw_settings.getId('AutoSaveOnAvgFiles'):
                directory = wx.FindWindowById(self.raw_settings.getId('AveragedFilePath'), self).GetValue()

            elif my_id == self.raw_settings.getId('AutoSaveOnSub'):
                directory = wx.FindWindowById(self.raw_settings.getId('SubtractedFilePath'), self).GetValue()

            elif my_id == self.raw_settings.getId('AutoSaveOnBift'):
                directory = wx.FindWindowById(self.raw_settings.getId('BiftFilePath'), self).GetValue()

            elif my_id == self.raw_settings.getId('AutoSaveOnGnom'):
                directory = wx.FindWindowById(self.raw_settings.getId('GnomFilePath'), self).GetValue()

            if not os.path.exists(directory):
                checkbox.SetValue(False)
                wx.MessageBox('Save directory "%s" does not exist. Please select a valid save directory to enable automatic saving.' %(directory), 'Directory does not exist', parent = self)


class IftOptionsPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['maxDmax','minDmax','DmaxPoints','maxAlpha','minAlpha',
                            'AlphaPoints','PrPoints', 'mcRuns']

        self.bift_options_data = (("Dmax Upper Bound: ",   raw_settings.getId('maxDmax')),
                                ("Dmax Lower Bound: ",   raw_settings.getId('minDmax')),
                                ("Dmax Search Points: ", raw_settings.getId('DmaxPoints')),
                                ("Alpha Upper Bound:",   raw_settings.getId('maxAlpha')),
                                ("Alpha Lower Bound:",   raw_settings.getId('minAlpha')),
                                ("Alpha Search Points:", raw_settings.getId('AlphaPoints')),
                                ("P(r) Points:",         raw_settings.getId('PrPoints')),
                                ("Monte Carlo Error Runs:", raw_settings.getId('mcRuns')),
                                )

        notebook = wx.Notebook(self, -1)

        bift_panel = wx.Panel(notebook, -1)
        box = wx.StaticBox(bift_panel, -1, 'BIFT Grid-Search Parameters')
        bift_options_sizer = self.createBiftOptions(box)
        chkbox_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkbox_sizer.Add(bift_options_sizer, 1, wx.EXPAND|wx.ALL,
            border=self._FromDIP(5))

        bift_sizer = wx.BoxSizer()
        bift_sizer.Add(chkbox_sizer, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        bift_panel.SetSizer(bift_sizer)

        notebook.AddPage(bift_panel, "BIFT")

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(notebook, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))

        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createBiftOptions(self, parent):

        no_of_rows = ceil(int(len(self.bift_options_data))/2.0)
        grid_sizer = wx.FlexGridSizer(cols=4, rows=no_of_rows,
            vgap=self._FromDIP(5), hgap=self._FromDIP(5))

        for each in self.bift_options_data:
            label = each[0]
            id = each[1]

            labeltxt = wx.StaticText(parent, -1, str(label))
            ctrl = wx.TextCtrl(parent, id, '0', size=self._FromDIP((60, 21)),
                style=wx.TE_RIGHT|wx.TE_PROCESS_ENTER)

            grid_sizer.Add(labeltxt, 1)
            grid_sizer.Add(ctrl, 1)

        return grid_sizer

class AutomationOptionsPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.autoavgsizer = self.createAutoAverageSettings()
        self.autobgsubsizer = self.createAutoBgSubSettings()
        self.autobiftsizer = self.createAutoBIFTSettings()

        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(self.autoavgsizer, 0, wx.ALL|wx.EXPAND, border=self._FromDIP(5))
        panelsizer.Add(self.autobgsubsizer,0, wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        panelsizer.Add(self.autobiftsizer,0, wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT,
            border=self._FromDIP(5))
        self.SetSizer(panelsizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createAutoAverageSettings(self):

        topbox = wx.StaticBox(self, -1, 'Averaging')

        inbox = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        chkbox = wx.CheckBox(topbox, self.raw_settings.getId('AutoAvg'),
            'Automated Averaging')

        chkbox2 = wx.CheckBox(topbox, self.raw_settings.getId('AutoAvgRemovePlots'),
            'Remove Plotted Frames')

        box12 = wx.BoxSizer(wx.HORIZONTAL)

        self.reglabel = wx.StaticText(topbox, -1, 'Regular Expression (frame):')
        self.regctrl = wx.TextCtrl(topbox, self.raw_settings.getId('AutoAvgRegExp'),
            size=self._FromDIP((150,-1)), style = wx.TE_PROCESS_ENTER)

        box1 = wx.BoxSizer(wx.VERTICAL)
        box1.Add(self.reglabel,0)
        box1.Add(self.regctrl,0)

        self.reglabelname = wx.StaticText(topbox, -1, 'Regular Expression (name):')
        self.regctrlname = wx.TextCtrl(topbox, self.raw_settings.getId('AutoAvgNameRegExp'),
            size=self._FromDIP((150,-1)), style = wx.TE_PROCESS_ENTER)

        box5 = wx.BoxSizer(wx.VERTICAL)
        box5.Add(self.reglabelname,0)
        box5.Add(self.regctrlname,0)

        self.numofframesLabel = wx.StaticText(topbox, -1, 'No. of Frames:')
        self.numofframesCtrl = wx.TextCtrl(topbox,
            self.raw_settings.getId('AutoAvgNoOfFrames'), '1',
            style = wx.TE_CENTER|wx.TE_PROCESS_ENTER)
        box2 = wx.BoxSizer(wx.VERTICAL)
        box2.Add(self.numofframesLabel,0)
        box2.Add(self.numofframesCtrl,0)

        box12.Add(self._FromDIP((28,1)), 0)
        box12.Add(box1, 0, wx.RIGHT, border=self._FromDIP(10))
        box12.Add(box5, 0, wx.RIGHT, border=self._FromDIP(10))
        box12.Add(box2, 0)

        box34 = wx.BoxSizer(wx.HORIZONTAL)

        testfilenameLabel = wx.StaticText(topbox, -1, 'Test Filename:')
        self.testfilenameCtrl = wx.TextCtrl(topbox, -1,
            size=self._FromDIP((150,-1)), style = wx.TE_PROCESS_ENTER)
        box3 = wx.BoxSizer(wx.VERTICAL)
        box3.Add(testfilenameLabel, 0)
        box3.Add(self.testfilenameCtrl, 0)

        testfilenameLabelex = wx.StaticText(topbox, -1, 'Extracted Filename:')
        self.testfilenameCtrlex = wx.TextCtrl(topbox, -1,
            size=self._FromDIP((150,-1)), style = wx.TE_CENTER|wx.TE_READONLY
           |wx.TE_PROCESS_ENTER)
        box6 = wx.BoxSizer(wx.VERTICAL)
        box6.Add(testfilenameLabelex, 0)
        box6.Add(self.testfilenameCtrlex, 0)

        testframenum = wx.StaticText(topbox, -1, 'Frame #:')
        self.testframectrl = wx.TextCtrl(topbox, -1, style = wx.TE_CENTER
           |wx.TE_READONLY|wx.TE_PROCESS_ENTER)
        testbutton = wx.Button(topbox, -1 , 'Test')
        testbutton.Bind(wx.EVT_BUTTON, self.OnAutoAvgTest)

        box4 = wx.BoxSizer(wx.VERTICAL)
        box4.Add(testframenum, 0)
        box4.Add(self.testframectrl, 0)

        box34.Add(self._FromDIP((28,1)), 0)
        box34.Add(box3,0, wx.RIGHT, border=self._FromDIP(12))
        box34.Add(box6,0, wx.RIGHT, border=self._FromDIP(12))
        box34.Add(box4,0)

        inbox.Add(chkbox,0, wx.LEFT|wx.TOP|wx.BOTTOM, border=self._FromDIP(5))
        inbox.Add(chkbox2,0, wx.LEFT, border=self._FromDIP(28))
        inbox.Add(box12,0, wx.TOP, border=self._FromDIP(5))
        inbox.Add(box34,0, wx.TOP|wx.BOTTOM, border=self._FromDIP(5))
        inbox.Add(self._FromDIP((1,2)),0)
        inbox.Add(testbutton, 0, wx.LEFT, border=self._FromDIP(28))
        inbox.Add(self._FromDIP((1,5)),0)

        return inbox

    def createAutoBIFTSettings(self):

        topbox = wx.StaticBox(self, -1, 'Indirect Fourier Transform')
        inbox = wx.StaticBoxSizer(topbox, wx.VERTICAL)
        chkbox = wx.CheckBox(topbox, self.raw_settings.getId('AutoBIFT'),
            'Automated Bayesian Indirect Fourier Transform (BIFT)')
        inbox.Add(chkbox,0, wx.ALL, border=self._FromDIP(5))

        chkbox.Enable(False)
        topbox.Enable(False)

        return inbox

    def createAutoBgSubSettings(self):

        topbox = wx.StaticBox(self, -1, 'Background Subtraction')

        inbox = wx.StaticBoxSizer(topbox, wx.VERTICAL)

        chkbox = wx.CheckBox(topbox, self.raw_settings.getId('AutoBgSubtract'),
            'Automated Background Subtraction')

        box12 = wx.BoxSizer(wx.HORIZONTAL)

        self.autobgreglabel = wx.StaticText(topbox, -1, 'Regular Expression:')
        self.autobgregctrl = wx.TextCtrl(topbox, self.raw_settings.getId('AutoBgSubRegExp'),
            size=self._FromDIP((150,-1)), style = wx.TE_PROCESS_ENTER)

        box1 = wx.BoxSizer(wx.VERTICAL)
        box1.Add(self.autobgreglabel, 0)
        box1.Add(self.autobgregctrl, 0)

        box12.Add(self._FromDIP((28,1)), 0)
        box12.Add(box1, 0, wx.RIGHT, border=self._FromDIP(10))

        box34 = wx.BoxSizer(wx.HORIZONTAL)

        testfilenameLabel = wx.StaticText(topbox, -1, 'Test Filename:')
        self.autobgtestfilenameCtrl = wx.TextCtrl(topbox, -1,
            size=self._FromDIP((150,-1)), style = wx.TE_PROCESS_ENTER)
        box3 = wx.BoxSizer(wx.VERTICAL)
        box3.Add(testfilenameLabel,0)
        box3.Add(self.autobgtestfilenameCtrl,0)

        testframenum = wx.StaticText(topbox, -1, 'Match Test:')
        self.autobgtestframectrl = wx.TextCtrl(topbox, -1,
            style = wx.TE_CENTER|wx.TE_READONLY|wx.TE_PROCESS_ENTER)
        testbutton = wx.Button(topbox, -1 , 'Test')
        testbutton.Bind(wx.EVT_BUTTON, self.OnAutoBgTest)

        box4 = wx.BoxSizer(wx.VERTICAL)
        box4.Add(testframenum,0)
        box4.Add(self.autobgtestframectrl,0)

        box34.Add(self._FromDIP((28,1)), 0)
        box34.Add(box3,0, wx.RIGHT, border=self._FromDIP(10))
        box34.Add(box4,0, wx.RIGHT, border=self._FromDIP(10))
        box34.Add(testbutton, 0,wx.TOP, border=self._FromDIP(10))

        inbox.Add(chkbox,0, wx.LEFT|wx.TOP|wx.BOTTOM, border=self._FromDIP(5))
        inbox.Add(box12,0, wx.TOP, border=self._FromDIP(5))
        inbox.Add(box34,0, wx.TOP|wx.BOTTOM, border=self._FromDIP(5))

        return inbox

    def OnAutoBgTest(self, event):
        regexp = self.autobgregctrl.GetValue()
        filename = self.autobgtestfilenameCtrl.GetValue()


        match = TestAutoBgSubRegExpression(filename, regexp)

        self.autobgtestframectrl.SetValue(str(match))

    def OnAutoAvgTest(self, event):

        regexp = self.regctrl.GetValue()
        nameregexp = self.regctrlname.GetValue()
        filename = self.testfilenameCtrl.GetValue()

        name, frame = ExtractFilenameAndFrameNumber(filename, regexp, nameregexp)

        self.testframectrl.SetValue(str(frame))
        self.testfilenameCtrlex.SetValue(str(name))

    def createChkBoxSettings(self):

        box = wx.StaticBox(self, -1, 'Automation')
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkboxgridSizer = wx.GridSizer(rows = len(self.chkboxData), cols = 1)

        for eachLabel, id in self.chkboxData:

            if eachLabel is not None:
                chkBox = wx.CheckBox(box, id, eachLabel)
                chkBox.Bind(wx.EVT_CHECKBOX, self.onChkBox)
                chkboxgridSizer.Add(chkBox, 1, wx.EXPAND)


        chkboxSizer.Add(chkboxgridSizer, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP
            |wx.BOTTOM, border=self._FromDIP(5))

        return chkboxSizer

class SeriesPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['secCalcThreshold', 'IBaselineMinIter', 'IBaselineMaxIter']


        self.settings = [(('Intensity ratio (to background) threshold for '
            'calculating Rg, MW, I0:'),
            raw_settings.getId('secCalcThreshold')),
            ('Integral baseline minimum iterations:',
                raw_settings.getId('IBaselineMinIter')),
            ('Integral baseline maximum iterations:',
                raw_settings.getId('IBaselineMaxIter')),
        ]

        sizer = self.createOptions()

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer.Add(sizer, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createOptions(self):

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        for item in self.settings:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, -1, item[0])
            value = wx.TextCtrl(self, item[1], '', size=self._FromDIP((60, -1)))

            sizer.Add(label, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL,
                border=self._FromDIP(5))
            sizer.Add(value, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL,
                border=self._FromDIP(5))

            top_sizer.Add(sizer, flag=wx.TOP, border=self._FromDIP(5))


        return top_sizer



class ATSASGeneralPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['autoFindATSAS', 'ATSASDir']

        self.chkboxdata = [('Automatically find the ATSAS bin location', raw_settings.getId('autoFindATSAS'))]

        self.data = [('ATSAS bin location :', raw_settings.getId('ATSASDir'))]

        options_sizer = self.createATSASOptions()

        final_sizer = wx.BoxSizer(wx.VERTICAL)
        final_sizer.Add(options_sizer, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))

        self.SetSizer(final_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createATSASOptions(self):

        # wx.StaticBox(self, -1, '')
        self.autoFind = wx.CheckBox(self, self.chkboxdata[0][1], self.chkboxdata[0][0])
        self.autoFind.SetValue(self.raw_settings.get('autoFindATSAS'))
        self.autoFind.Bind(wx.EVT_CHECKBOX, self.onAutoFind)

        self.dirLabel = wx.StaticText(self, -1, self.data[0][0])
        self.datadir = wx.TextCtrl(self, self.data[0][1],
            self.raw_settings.get('ATSASDir'), size = self._FromDIP((475,-1)),
            style = wx.TE_PROCESS_ENTER)

        self.dirButton = wx.Button(self, -1, 'Select Directory')
        self.dirButton.Bind(wx.EVT_BUTTON, self.onDirButton)

        if not self.autoFind.GetValue():
            self.datadir.SetEditable(True)
            self.dirButton.Enable()

        else:
            self.datadir.SetEditable(False)
            self.dirButton.Disable()

        horSizer = wx.BoxSizer(wx.HORIZONTAL)
        horSizer.Add(self.datadir, 1, wx.EXPAND|wx.RIGHT, border=self._FromDIP(5))
        horSizer.Add(self.dirButton, 0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.autoFind, 0, wx.BOTTOM|wx.TOP, border=self._FromDIP(5))
        sizer.Add(self.dirLabel, 0, wx.BOTTOM|wx.TOP, border=self._FromDIP(5))
        sizer.Add(horSizer, 0, wx.BOTTOM|wx.TOP|wx.EXPAND, border=self._FromDIP(5))

        return sizer

    def onAutoFind(self, evt):
        findsas = evt.GetEventObject().GetValue()

        if not findsas:
            self.datadir.SetEditable(True)
            self.dirButton.Enable()

        else:
            self.datadir.SetEditable(False)
            self.dirButton.Disable()
            self.setATSASDir()

    def setATSASDir(self):
        atsasDirectory = SASUtils.findATSASDirectory()
        self.datadir.SetValue(atsasDirectory)

    def onDirButton(self, evt):
        path = self.datadir.GetValue()
        dirdlg = wx.DirDialog(self, "Please select ATSAS bin directory (.../ATSAS/bin):", defaultPath = path,)

        if dirdlg.ShowModal() == wx.ID_OK:
            path = dirdlg.GetPath()
        else:
            path = path

        dirdlg.Destroy()

        self.datadir.SetValue(path)


class ATSASGnom(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = [
            'gnomForceRminZero',
            'gnomForceRmaxZero',
            'gnomNPoints',
            'gnomInitialAlpha',
            'gnomCut8Rg',
            ]

        options_sizer = self.createGNOMOptions()

        self.SetSizer(options_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createGNOMOptions(self):
        standardBox = wx.StaticBox(self, -1, 'Standard Settings')

        rmin_text = wx.StaticText(standardBox, -1, 'Force P(r) to 0 at r = 0 :')
        rmin_choice = wx.Choice(standardBox, self.raw_settings.getId('gnomForceRminZero'),
            choices = ['Y', 'N'])

        rmin_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rmin_sizer.Add(rmin_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        rmin_sizer.Add(rmin_choice, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))

        rmax_text = wx.StaticText(standardBox, -1, ('Force P(r) to 0 at r = Dmax '
            '(sets default for GNOM window):'))
        rmax_choice = wx.Choice(standardBox, self.raw_settings.getId('gnomForceRmaxZero'),
            choices = ['Y', 'N'])

        rmax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rmax_sizer.Add(rmax_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        rmax_sizer.Add(rmax_choice, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))


        npts_text = wx.StaticText(standardBox, -1, ('Number of points in real space '
            '(0=auto, value sets to default):'))
        npts_ctrl = wx.TextCtrl(standardBox, self.raw_settings.getId('gnomNPoints'),
            '', size=self._FromDIP((60, -1)), style=wx.TE_PROCESS_ENTER)

        npts_sizer = wx.BoxSizer(wx.HORIZONTAL)
        npts_sizer.Add(npts_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        npts_sizer.Add(npts_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))


        alpha_text = wx.StaticText(standardBox, -1, ('Initial Alpha (0=auto, value '
            'sets default):'))
        alpha_ctrl = wx.TextCtrl(standardBox, self.raw_settings.getId('gnomInitialAlpha'),
            '', size=self._FromDIP((60, -1)), style=wx.TE_PROCESS_ENTER)

        alpha_sizer = wx.BoxSizer(wx.HORIZONTAL)
        alpha_sizer.Add(alpha_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        alpha_sizer.Add(alpha_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))

        cut_ctrl = wx.CheckBox(standardBox, self.raw_settings.getId('gnomCut8Rg'),
            'Truncate to q_max=8/Rg (dammif/n)')

        resetBox = wx.StaticBox(self, -1, 'Reset')

        resetText = wx.StaticText(resetBox, -1, ('Reset all GNOM settings '
            '(including advanced) to default:'))
        resetButton = wx.Button(resetBox, -1, 'Reset to default')
        resetButton.Bind(wx.EVT_BUTTON, self._onResetButton)


        resetSizer = wx.StaticBoxSizer(resetBox, wx.VERTICAL)
        resetSizer.Add(resetText, 0, wx.ALL, border=self._FromDIP(5))
        resetSizer.Add(resetButton, 0, wx.ALL, border=self._FromDIP(5))

        advanced_text = wx.StaticText(self, -1, ('This panel allows you to set '
            'the commonly used advanced settings used by the ATSAS software GNOM.'))


        standardSizer = wx.StaticBoxSizer(standardBox, wx.VERTICAL)
        standardSizer.Add(rmin_sizer, 0)
        standardSizer.Add(rmax_sizer, 0)
        standardSizer.Add(npts_sizer, 0)
        standardSizer.Add(alpha_sizer, 0)
        standardSizer.Add(cut_ctrl, border=5, flag=wx.ALL)



        top_sizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer.Add(advanced_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(5))
        top_sizer.Add(standardSizer, 0)
        top_sizer.Add(resetSizer, 0)

        return top_sizer


    def _onResetButton(self, evt):
        default_settings = RAWSettings.RawGuiSettings()

        for key in self.update_keys:
            id, type = self.raw_settings.getIdAndType(key)

            val = default_settings.get(key)
            obj = wx.FindWindowById(id, self)

            if type == 'bool':
                obj.SetValue(val)
            elif type == 'list':
                obj.SetValue(val)

            elif type == 'choice':
                choice_list = obj.GetStrings()
                idx = choice_list.index(val)
                obj.Select(idx)

            elif type == 'text' or type == 'int' or type == 'float':
                try:
                    obj.SetValue(val)
                except TypeError:
                    obj.SetValue(str(val))

        myId = -1
        all_options = wx.FindWindowByName('OptionsDialog').all_options
        for item in all_options:
            if item[2] == "GNOM Advanced":
                myId = item[1]

        if myId != -1:
            gnomAdvanced = wx.FindWindowById(myId, self.GetParent())

            for key in gnomAdvanced.update_keys:
                id, type = self.raw_settings.getIdAndType(key)

                val = default_settings.get(key)
                obj = wx.FindWindowById(id, gnomAdvanced)

                if type == 'bool':
                    obj.SetValue(val)
                elif type == 'list':
                    obj.SetValue(val)

                elif type == 'choice':
                    choice_list = obj.GetStrings()
                    idx = choice_list.index(val)
                    obj.Select(idx)

                elif type == 'text' or type == 'int' or type == 'float':
                    try:
                        obj.SetValue(val)
                    except TypeError:
                        obj.SetValue(str(val))



class ATSASGnomAdvanced(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['gnomAngularScale', 'gnomSystem', 'gnomExpertFile', 'gnomFormFactor',
                            'gnomRadius56', 'gnomRmin']

        self.button_ids = {'expert' : self.NewControlId(),
                            'form': self.NewControlId(),
                            'spot': self.NewControlId()}


        options_sizer = self.createGNOMOptions()

        self.SetSizer(options_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createGNOMOptions(self):


        angular_box = wx.StaticBox(self)
        angular_text1 = wx.StaticText(angular_box, -1, 'Angular Scale :')
        angular_text2 = wx.StaticText(angular_box, -1, ('1 - q=4pi*sin(theta)/lambda '
            '[A^-1]\n2 - q=4pi*sin(theta)/lambda, convert [nm^-1] to [A^-1]\n3 '
            '- q=2*sin(theta)/lambda [A^-1]\n4 - q=2*sin(theta)/lambda, convert '
            '[nm^-1] to [A^-1]'), style = wx.TE_MULTILINE)
        angular_ctrl = wx.TextCtrl(angular_box, self.raw_settings.getId('gnomAngularScale'),
            '', size = self._FromDIP((60,-1)), style = wx.TE_PROCESS_ENTER)

        angular_sizer = wx.StaticBoxSizer(angular_box, wx.VERTICAL)
        angular_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        angular_sizer2.Add(angular_text1, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        angular_sizer2.Add(angular_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))

        angular_sizer.Add(angular_sizer2, 0)
        angular_sizer.Add(angular_text2, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))


        system_box = wx.StaticBox(self)
        system_text1 = wx.StaticText(system_box, -1, 'Job Type :')
        system_text2 = wx.StaticText(system_box, -1, ('0 - P(r) for a mondisperse '
            'system\n1 - Volume distribution function for polydisperse system '
            'of solid spheres\n2 - P(r) with a user supplied form factor\n3 '
            '- Thickness distance distribution of a monodisperse system of '
            'flattened particles\n4 - Cross-section distance distribution of '
            'monodisperse rod-like particles\n5 - Length distribution of a '
            'polydisperse system of long cylinders\n6 - Surface distribution '
            'function for a polydisperse system of spherical shells'),
            style = wx.TE_MULTILINE)
        system_ctrl = wx.TextCtrl(system_box, self.raw_settings.getId('gnomSystem'),
            '', size = self._FromDIP((60,-1)), style = wx.TE_PROCESS_ENTER)

        system_sizer = wx.StaticBoxSizer(system_box, wx.VERTICAL)
        system_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        system_sizer2.Add(system_text1, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        system_sizer2.Add(system_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))

        system_sizer.Add(system_sizer2, 0)
        system_sizer.Add(system_text2, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))


        expert_text = wx.StaticText(self, -1, 'Expert parameters file :',)
        expert_ctrl = wx.TextCtrl(self, self.raw_settings.getId('gnomExpertFile'),
            '', size = self._FromDIP((325,-1)), style = wx.TE_PROCESS_ENTER)
        expert_button = wx.Button(self, self.button_ids['expert'], 'Select')
        expert_button.Bind(wx.EVT_BUTTON, self.onSelectButton)

        expert_sizer = wx.BoxSizer(wx.HORIZONTAL)
        expert_sizer.Add(expert_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        expert_sizer.Add(expert_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        expert_sizer.Add(expert_button, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))


        form_text = wx.StaticText(self, -1, 'Form factor file (job 2) :',)
        form_ctrl = wx.TextCtrl(self, self.raw_settings.getId('gnomFormFactor'),
            '', size = self._FromDIP((325,-1)), style = wx.TE_PROCESS_ENTER)
        form_button = wx.Button(self, self.button_ids['form'], 'Select')
        form_button.Bind(wx.EVT_BUTTON, self.onSelectButton)

        form_sizer = wx.BoxSizer(wx.HORIZONTAL)
        form_sizer.Add(form_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        form_sizer.Add(form_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        form_sizer.Add(form_button, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))


        radius_text = wx.StaticText(self, -1, 'Radius/thickness (job 5/6) :')
        radius_ctrl = wx.TextCtrl(self, self.raw_settings.getId('gnomRadius56'),
            size = self._FromDIP((60, -1)), style = wx.TE_PROCESS_ENTER)

        radius_sizer = wx.BoxSizer(wx.HORIZONTAL)
        radius_sizer.Add(radius_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        radius_sizer.Add(radius_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))

        radmin_text = wx.StaticText(self, -1, 'Dmin (jobs 1, 2, 5, 6) :')
        radmin_ctrl = wx.TextCtrl(self, self.raw_settings.getId('gnomRmin'),
            size = self._FromDIP((60,-1)), style = wx.TE_PROCESS_ENTER)

        radmin_sizer = wx.BoxSizer(wx.HORIZONTAL)
        radmin_sizer.Add(radmin_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        radmin_sizer.Add(radmin_ctrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))

        comb_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        comb_sizer1.Add(radius_sizer)
        comb_sizer1.Add(radmin_sizer)

        advanced_text = wx.StaticText(self, -1, ('This panel allows you to set '
            'the less common advanced settings used by the ATSAS software GNOM.'))

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer.Add(advanced_text, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,
            border=self._FromDIP(3))
        top_sizer.Add(angular_sizer,0)
        top_sizer.Add(system_sizer, 0)
        top_sizer.Add(expert_sizer, 0, wx.TOP, border=self._FromDIP(5))
        top_sizer.Add(form_sizer, 0)
        top_sizer.Add(comb_sizer1, 0)

        return top_sizer

    def onSelectButton(self, evt):

        button_id = evt.GetId()

        if button_id == self.button_ids['expert']:
            path = wx.FindWindowById(self.raw_settings.getId('gnomExpertFile'),
                self).GetValue()
        elif button_id == self.button_ids['form']:
            path = wx.FindWindowById(self.raw_settings.getId('gnomFormFactor'),
                self).GetValue()
        else:
            path = ''


        dirdlg = wx.FileDialog(self, "Please select file:", defaultDir = path,)

        if dirdlg.ShowModal() == wx.ID_OK:
            path = dirdlg.GetPath()
        else:
            path = path

        if button_id == self.button_ids['expert']:
            path = wx.FindWindowById(self.raw_settings.getId('gnomExpertFile'),
                self).SetValue(path)
        elif button_id == self.button_ids['form']:
            path = wx.FindWindowById(self.raw_settings.getId('gnomFormFactor'),
                self).SetValue(path)
        else:
            path = path

        dirdlg.Destroy()


class ATSASDammix(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['dammifProgram', 'dammifMode', 'dammifSymmetry',
            'dammifAnisometry', 'dammifUnit', 'dammifReconstruct',
            'dammifDamaver', 'dammifDamclust', 'dammifRefine']

        modeChoices = ['Fast', 'Slow', 'Custom']

        symChoices = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
            'P10', 'P11', 'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18',
            'P19', 'P22', 'P222', 'P32', 'P42', 'P52', 'P62', 'P72', 'P82',
            'P92', 'P102', 'P112', 'P122']

        anisometryChoices = ['Unknown', 'Prolate', 'Oblate']

        programChoices = ['DAMMIF', 'DAMMIN']

        self.default_options = (
            ("Program:", raw_settings.getId('dammifProgram'), 'choice',
                programChoices),
            ("Mode:",   raw_settings.getId('dammifMode'), 'choice', modeChoices),
            ("Symmetry:",   raw_settings.getId('dammifSymmetry'), 'choice',
                symChoices),
            ("Anisometry: ", raw_settings.getId('dammifAnisometry'), 'choice',
                anisometryChoices),
            ("Number of reconstructions:", raw_settings.getId('dammifReconstruct'),
                'int'),
            ("Automatically average reconstructions (DAMAVER)",
                raw_settings.getId('dammifDamaver'), 'bool'),
            ("Automatically cluster reconstructions (DAMCLUST)",
                raw_settings.getId('dammifDamclust'), 'bool'),
            ("Automatically refine DAMAVER generated damstart.pdb with DAMMIN",
                raw_settings.getId('dammifRefine'), 'bool'))

        unitChoices = ['Unknown', 'Angstrom', 'Nanometer']

        self.standard_options = (('Units:', raw_settings.getId('dammifUnit'),
            'choice', unitChoices), None) #stupid, but to keep it a list it needs another item . . .

        layoutSizer = self._createLayout(self)

        self.SetSizer(layoutSizer)

        self.Layout()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self, parent):

        defaultBox = wx.StaticBox(parent, -1, 'Defaults')
        defaultSizer = wx.StaticBoxSizer(defaultBox, wx.VERTICAL)

        defaultText = wx.StaticText(defaultBox, -1, ('The default settings applied '
            'when the DAMMIF window is opened.'))
        defaultSizer.Add(defaultText, 0, wx.ALL, border=self._FromDIP(3))

        for item in self.default_options:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(defaultBox, -1, label)
                ctrl = wx.Choice(defaultBox, myId, choices = item[3])

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(defaultBox, -1, label)
                ctrl = wx.TextCtrl(defaultBox, myId, '', size = self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'bool':
                ctrl = wx.CheckBox(defaultBox, myId, label)
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

                if (myId == self.raw_settings.getId('dammifDamaver')
                    or myId == self.raw_settings.getId('dammifDamclust')
                    or myId == self.raw_settings.getId('dammifRefine')):
                    ctrl.Bind(wx.EVT_CHECKBOX, self._onCheckBox)

            defaultSizer.Add(sizer, 0)


        standardBox = wx.StaticBox(parent, -1, 'Standard Settings')
        standardSizer = wx.StaticBoxSizer(standardBox, wx.VERTICAL)

        standardText = wx.StaticText(standardBox, -1, ('Standard settings that can '
            'be changed in Fast/Slow mode.'))
        standardSizer.Add(standardText, 0, wx.ALL, border=self._FromDIP(3))

        for item in self.standard_options:

            if item is not None:
                label = item[0]
                myId = item[1]
                itemType = item[2]

                sizer = wx.BoxSizer(wx.HORIZONTAL)

                if itemType == 'choice':
                    labeltxt = wx.StaticText(standardBox, -1, label)
                    ctrl = wx.Choice(standardBox, myId, choices = item[3])

                    sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(3))
                    sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(3))
                elif itemType == 'text':
                    labeltxt = wx.StaticText(standardBox, -1, label)
                    ctrl = wx.TextCtrl(standardBox, myId, '', size = self._FromDIP((60,-1)),
                        style = wx.TE_PROCESS_ENTER)

                    sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(3))
                    sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(3))
                elif itemType == 'bool':
                    ctrl = wx.CheckBox(standardBox, myId, label)
                    sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(3))

                standardSizer.Add(sizer, 0)


        resetBox = wx.StaticBox(parent, -1, 'Reset')

        resetText = wx.StaticText(resetBox, -1, ('Reset all DAMMIF/N settings '
            '(including advanced) to default:'))
        resetButton = wx.Button(resetBox, -1, 'Reset to default')
        resetButton.Bind(wx.EVT_BUTTON, self._onResetButton)

        resetSizer = wx.StaticBoxSizer(resetBox, wx.VERTICAL)
        resetSizer.Add(resetText, 0, wx.ALL, border=self._FromDIP(5))
        resetSizer.Add(resetButton, 0, wx.ALL, border=self._FromDIP(5))


        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(defaultSizer,0)
        top_sizer.Add(standardSizer,0)
        top_sizer.Add(resetSizer, 0)

        return top_sizer

    def _onCheckBox(self,evt):
        if evt.GetId() == self.raw_settings.getId('dammifDamaver') and evt.IsChecked():
            damrefine = wx.FindWindowById(self.raw_settings.getId('dammifRefine'), self)
            damrefine.Enable()
        #     damclust = wx.FindWindowById(self.raw_settings.getId('dammifDamclust'), self)
        #     damclust.SetValue(False)

        if evt.GetId() == self.raw_settings.getId('dammifDamaver') and not evt.IsChecked():
            damrefine = wx.FindWindowById(self.raw_settings.getId('dammifRefine'), self)
            damrefine.SetValue(False)
            damrefine.Disable()

        # elif evt.GetId() == self.raw_settings.getId('dammifDamclust') and evt.IsChecked():
        #     damaver = wx.FindWindowById(self.raw_settings.getId('dammifDamaver'), self)
        #     damaver.SetValue(False)

        #     damrefine = wx.FindWindowById(self.raw_settings.getId('dammifRefine'), self)
        #     damrefine.SetValue(False)

        # elif evt.GetId() == self.raw_settings.getId('dammifRefine') and evt.IsChecked():
        #     damaver = wx.FindWindowById(self.raw_settings.getId('dammifDamaver'), self)
        #     damaver.SetValue(True)

        #     damclust = wx.FindWindowById(self.raw_settings.getId('dammifDamclust'), self)
        #     damclust.SetValue(False)


    def _onResetButton(self, evt):
        default_settings = RAWSettings.RawGuiSettings()

        for key in self.update_keys:
            id, type = self.raw_settings.getIdAndType(key)

            val = default_settings.get(key)
            obj = wx.FindWindowById(id, self)

            if type == 'bool':
                obj.SetValue(val)
            elif type == 'list':
                obj.SetValue(val)

            elif type == 'choice':
                choice_list = obj.GetStrings()
                idx = choice_list.index(val)
                obj.Select(idx)

            elif type == 'text' or type == 'int' or type == 'float':
                try:
                    obj.SetValue(val)
                except TypeError:
                    obj.SetValue(str(val))

        myId = -1
        all_options = wx.FindWindowByName('OptionsDialog').all_options
        for item in all_options:
            if item[2] == "DAMMIF Advanced" or item[2] == "DAMMIF/N Advanced" or item[2] == "DAMMIN Advanced":
                myId = item[1]

                dammifAdvanced = wx.FindWindowById(myId, self.GetParent())

                for key in dammifAdvanced.update_keys:
                    id, type = self.raw_settings.getIdAndType(key)

                    val = default_settings.get(key)
                    obj = wx.FindWindowById(id, dammifAdvanced)

                    if type == 'bool':
                        obj.SetValue(val)
                    elif type == 'list':
                        obj.SetValue(val)

                    elif type == 'choice':
                        choice_list = obj.GetStrings()
                        idx = choice_list.index(val)
                        obj.Select(idx)

                    elif type == 'text' or type == 'int' or type == 'float':
                        try:
                            obj.SetValue(val)
                        except TypeError:
                            obj.SetValue(str(val))


class ATSASDammixAdvanced(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['dammifSH', 'dammifPropToFit', 'dammifMaxSteps',
            'dammifMaxIters', 'dammifMaxStepSuccess', 'dammifMinStepSuccess',
            'dammifLoosePen']

        self.custom_options_long = (
            ("Maximum number of spherical harmonics (1-50):",
                raw_settings.getId('dammifSH'), 'int'),
            ("Maximum temperature steps in annealing procedure (1-?):",
                raw_settings.getId('dammifMaxSteps'), 'int'),
            ("Maximum iterations within a single temperature step (1-?):",
                raw_settings.getId('dammifMaxIters'), 'int'),
            ("Maximum successes per temperature step before temperature decreased (1-?):",
                raw_settings.getId('dammifMaxStepSuccess'), 'int'),
            ("Minimum successes per temperature step before temperature decreased (1-?):",
                raw_settings.getId('dammifMinStepSuccess'), 'int')
            )

        self.custom_options_short = (
            ("Looseness penalty weight (0.0-...):",
                raw_settings.getId('dammifLoosePen'), 'float'),
            ("Proprotion of the curve to fit (0.0-1.0):",
                raw_settings.getId('dammifPropToFit'), 'float')
            )

        layoutSizer = self._createLayout(self)

        self.SetSizer(layoutSizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self, parent):

        customSizer = wx.BoxSizer(wx.VERTICAL)

        customText = wx.StaticText(parent, -1, ('These settings are used when '
            '"Custom" is selected as the mode in the DAMMIF/N panel.\nThis is '
            'equivalent to the DAMMIF/N interactive mode in the command line.\n'
            'Unless otherwise noted, a value of -1 means DAMMIF/N will use the '
            'default setting.'))
        customSizer.Add(customText, 0, wx.ALL, 5)

        for item in self.custom_options_long:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            customSizer.Add(sizer, 0)

        short_sizer = wx.FlexGridSizer(cols=4, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))

        for item in self.custom_options_short:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

        customSizer.Add(short_sizer,0)


        return customSizer


class ATSASDammifAdvanced(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['dammifDummyRadius', 'dammifKnots', 'dammifCurveWeight',
                            'dammifRandomSeed', 'dammifTFactor', 'dammifRgPen',
                            'dammifCenPen', 'dammifAnisPen', 'dammifMaxBeadCount',
                            'dammifChained', 'dammifConstant', 'dammifOmitSolvent',
                            'dammifExpectedShape',
                            ]

        weightChoices = ['l', 'p', 'e', 'n']
        shapeChoices = ['u', 'c', 'e', 'f', 'r', 'h', 'hs', 'rc']

        self.custom_options_long = (
            ("Dummy atom radius (1.0-?, Angstrom):",
                raw_settings.getId('dammifDummyRadius'), 'float'),
            ("Number of knots in the curve to fit (1-?):",
                raw_settings.getId('dammifKnots'), 'int'),
            ("Curve weighting function ([l]log, [p]orod, [e]mphasized porod, [n]one):",
                raw_settings.getId('dammifCurveWeight'), 'choice', weightChoices),
            ("Initial Random Seed (blank to automatically generate):",
                raw_settings.getId('dammifRandomSeed'), 'text'),
            ('Constant offset (blank to automatically set):',
                raw_settings.getId('dammifConstant'), 'text'),
            ('Create Pseudo-Chains in PDB output:',
                raw_settings.getId('dammifChained'), 'bool'),
            (('Expected/assumed shape ((u)nknown, (c)ompact, (e)xtended,\n'
                '(f)lat, (r)ing, (h) compact-hollow, (hs) hollow-sphere, (rc) '
                'random-chain:'), raw_settings.getId('dammifExpectedShape'),
                'choice', shapeChoices)
            )

        self.custom_options_short = (
            ("Temperature schedule factor (0.0-1.0):",
                raw_settings.getId('dammifTFactor'), 'float'),
            ("Rg penalty weight (0.0-...):", raw_settings.getId('dammifRgPen'),
                'float'),
            ("Center penalty weight (0.0-...):",
                raw_settings.getId('dammifCenPen'), 'float'),
            ("Anisometry penalty weight (0.0-...):",
                raw_settings.getId('dammifAnisPen'), 'float'),
            ("Maximum bead count:", raw_settings.getId('dammifMaxBeadCount'),
                'int'),
            ('Omit solvent PDB file:', raw_settings.getId('dammifOmitSolvent'),
                'bool'),
            )

        layoutSizer = self._createLayout(self)

        self.SetSizer(layoutSizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self, parent):

        customSizer = wx.BoxSizer(wx.VERTICAL)

        customText = wx.StaticText(parent, -1, ('These settings are used when '
            '"Custom" is selected as the mode in the DAMMIF/N panel.\nThis is '
            'equivalent to the DAMMIF interactive mode in the command line.\n'
            'Unless otherwise noted, a value of -1 means DAMMIF will use the '
            'default setting.'))
        customSizer.Add(customText, 0, wx.ALL, border=self._FromDIP(5))

        for item in self.custom_options_long:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            customSizer.Add(sizer, 0)

        short_sizer = wx.FlexGridSizer(cols=4, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))

        for item in self.custom_options_short:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

        customSizer.Add(short_sizer,0)


        return customSizer


class ATSASDamminAdvanced(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['damminInitial', 'damminKnots', 'damminConstant',
            'damminDiameter', 'damminPacking', 'damminCoordination',
            'damminDisconPen', 'damminPeriphPen', 'damminCurveWeight',
            'damminAnealSched']

        weightChoices = ['0', '1', '2']
        volumeChoices = ['S', 'E', 'C', 'P']

        self.custom_options_long = (
            (("Initial search volume ([S]phere, [E]llipsoid, [C]ylinder, "
                "[P]arallelapiped):"), raw_settings.getId('damminInitial'),
                'choice', volumeChoices),
            ("Number of knots in the curve to fit (1-?):",
                raw_settings.getId('damminKnots'), 'int'),
            ("Curve weighting function (0: porod, 1: emphasized porod, 2: log):",
                raw_settings.getId('damminCurveWeight'), 'choice', weightChoices),
            ('Constant offset (blank to automatically set):',
                raw_settings.getId('damminConstant'), 'text')
            )

        self.custom_options_short = (
            ("Sphere diamater [Angstrom]", raw_settings.getId('damminDiameter'),
                'float'),
            ('Packing radius of dummy atoms:', raw_settings.getId('damminPacking'),
                'float'),
            ('Radius of 1st coordination sphere:',
                raw_settings.getId('damminCoordination'), 'float'),
            ('Disconnectivity penalty weight:',
                raw_settings.getId('damminDisconPen'), 'float'),
            ('Peripheral penalty weight:', raw_settings.getId('damminPeriphPen'),
                'float'),
            ('Annealing schedule factor:', raw_settings.getId('damminAnealSched'),
                'float')
            )

        layoutSizer = self._createLayout(self)

        self.SetSizer(layoutSizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self, parent):

        customSizer = wx.BoxSizer(wx.VERTICAL)

        customText = wx.StaticText(parent, -1, ('These settings are used when '
            '"Custom" is selected as the mode in the DAMMIF/N panel.\nThis is '
            'equivalent to the DAMMIN interactive mode in the command line.\n'
            'Unless otherwise noted, a value of -1 means DAMMIN will use the '
            'default setting.'))
        customSizer.Add(customText, 0, wx.ALL, border=self._FromDIP(5))

        for item in self.custom_options_long:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            customSizer.Add(sizer, 0)

        short_sizer = wx.FlexGridSizer(cols=4, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))

        for item in self.custom_options_short:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

        customSizer.Add(short_sizer,0)


        return customSizer

class WeightedAveragePanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['weightCounter', 'weightByError']

        img_hdr = self.raw_settings.get('ImageHdrList')
        file_hdr = self.raw_settings.get('FileHdrList')

        try:
            self.expr_combo_list = [''] + sorted(list(img_hdr.keys()) + list(file_hdr.keys()))
        except AttributeError:
            self.expr_combo_list = ['']


        self.settings = [('Weight by error', raw_settings.getId('weightByError'), 'bool'),
                        ('Counter to use as weight for weighted average (weighted by 1/cval)', raw_settings.getId('weightCounter'), 'choice', self.expr_combo_list)]

        sizer = self.createOptions(self)

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer.Add(sizer, 1, wx.EXPAND|wx.ALL, self._FromDIP(5))
        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size


    def createOptions(self, parent):

        sizer = wx.BoxSizer(wx.VERTICAL)

        for item in self.settings:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            short_sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

                ctrl.Bind(wx.EVT_CHECKBOX, self._onCheckBox)

            sizer.Add(short_sizer,0)

        if self.raw_settings.get('weightByError'):
            wx.FindWindowById(self.raw_settings.getId('weightCounter'), self).Disable()

        return sizer

    def _onCheckBox(self, event):
        if not event.GetEventObject().GetValue():
            wx.FindWindowById(self.raw_settings.getId('weightCounter'), self).Enable()
        else:
            wx.FindWindowById(self.raw_settings.getId('weightCounter'), self).Disable()
        event.Skip()

class SimilarityPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['similarityTest', 'similarityThreshold',
                            'similarityOnAverage', 'similarityCorrection']

        self.settings = [
            ('Test for profile similarity on average',
                raw_settings.getId('similarityOnAverage'), 'bool'),
            ('P-value threshold for similarity test on average',
                raw_settings.getId('similarityThreshold'), 'float'),
            ('Similarity test to use:', raw_settings.getId('similarityTest'),
                'choice', ['CorMap']),
            ('Multiple testing correction:',
                raw_settings.getId('similarityCorrection'), 'choice', ['None',
                'Bonferroni']),
            ]

        sizer = self.createOptions(self)

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer.Add(sizer, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createOptions(self, parent):

        sizer = wx.BoxSizer(wx.VERTICAL)

        for item in self.settings:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            short_sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

            sizer.Add(short_sizer,0, wx.BOTTOM, border=self._FromDIP(5))

        return sizer

class FittingPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['errorWeight', 'normalizedResiduals']

        self.settings = [
            ('Use error weighting for fits', raw_settings.getId('errorWeight'),
                'bool'),
            ('Show normalized residuals',
                raw_settings.getId('normalizedResiduals'), 'bool'),
            ]

        sizer = self.createOptions(self)

        top_sizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer.Add(sizer, 1, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        self.SetSizer(top_sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createOptions(self, parent):

        sizer = wx.BoxSizer(wx.VERTICAL)

        for item in self.settings:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            short_sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.Choice(parent, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(parent, -1, label)
                ctrl = wx.TextCtrl(parent, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(parent, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

            sizer.Add(short_sizer,0, wx.BOTTOM, border=self._FromDIP(5))

        return sizer

class DenssPanel(scrolled.ScrolledPanel):

    def __init__(self, parent, id, raw_settings, *args, **kwargs):

        if 'style' in kwargs:
            kwargs['style'] = kwargs['style'] |wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        else:
            kwargs['style'] = wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER
        scrolled.ScrolledPanel.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate(20,20)

        self.raw_settings = raw_settings

        self.update_keys = ['denssExtrapolate', 'denssShrinkwrapSigmaStart',
            'denssShrinkwrapSigmaEnd', 'denssShrinkwrapSigmaDecay',
            'denssShrinkwrapThresFrac', 'denssShrinkwrapIter', 'denssChiEndFrac',
            'denssMode', 'denssSteps', 'denssVoxel', 'denssOversampling',
            'denssLimitDmax', 'denssLimitDmaxStep', 'denssRecenter',
            'denssRecenterStep', 'denssPositivity', 'denssShrinkwrap',
            'denssShrinkwrapMinStep', 'denssConnected', 'denssConnectivitySteps',
            'denssWriteXplor', 'denssCutOut', 'denssRecenterMode',
            'denssAverage', 'denssReconstruct', 'denssRefine',
            'denssNCS', 'denssNCSAxis', 'denssNCSSteps', 'denssGPU',
            ]

        modeChoices = ['Fast', 'Slow', 'Membrane', 'Custom']
        recenterChoices = ['com', 'max']

        self.default_options = (('Default mode:', raw_settings.getId('denssMode'), 'choice', modeChoices),
            ('Number of runs:', raw_settings.getId('denssReconstruct'), 'int'),
            ('Align and Average:', raw_settings.getId('denssAverage'), 'bool'),
            ('Refine average density:', raw_settings.getId('denssRefine'), 'bool'),

            )

        self.custom_options_long = (("Extrapolate data using Porod's law to voxel resolution limit", raw_settings.getId('denssExtrapolate'), 'bool'),
            ("Starting sigma for Gaussian blurring, in voxels:",
                raw_settings.getId('denssShrinkwrapSigmaStart'), 'float'),
            ("Ending sigma for Gaussian blurring, in voxels:",
                raw_settings.getId('denssShrinkwrapSigmaEnd'), 'float'),
            ("Rate of decay of sigma, fraction (default 0.99):",
                raw_settings.getId('denssShrinkwrapSigmaDecay'), 'float'),
            ("Minimum threshold defining support, in fraction of maximum density (default 0.20):",
                raw_settings.getId('denssShrinkwrapThresFrac'), 'float'),
            ("Number of iterations between updating support with shrinkwrap (default 20):",
                raw_settings.getId('denssShrinkwrapIter'), 'int'),
            (("Convergence criterion. Minimum threshold of chi2 std dev, as a "
                "fraction \nof the median chi2 of last 100 steps. (default 0.001):"),
            raw_settings.getId('denssChiEndFrac'), 'float'),
            ('Recenter mode (center of mass - com; maximum density - max):',
                raw_settings.getId('denssRecenterMode'), 'choice', recenterChoices),
            # ('Minimum density (e-/angstrom^3, must also set number of electrons):',
            #     raw_settings.getId('denssMinDensity'), 'text'),
            # ('Maximum density (e-/angstrom^3, must also set number of electrons):',
            #     raw_settings.getId('denssMaxDensity'), 'text'),
            # ('Set density values near zero (0.01 e-/A^3) to zero:',
            #     raw_settings.getId('denssFlattenLowDensity'), 'bool'),
            ('Use GPU computing (requires CuPy)', raw_settings.getId('denssGPU'),
                'bool')

            )

        self.custom_options_short = (('Number of iterations:', raw_settings.getId('denssSteps'), 'int'),
            ('Voxel size [A]:', raw_settings.getId('denssVoxel'), 'float'),
            ('Oversampling:', raw_settings.getId('denssOversampling'), 'float'),
            ("Limit vol. to 0.6*Dmax", raw_settings.getId('denssLimitDmax'), 'bool'),
            ('Dmax limit at steps:', raw_settings.getId('denssLimitDmaxStep'), 'text'),
            ('Recenter density', raw_settings.getId('denssRecenter'), 'bool'),
            ('Recenter density at steps:', raw_settings.getId('denssRecenterStep'), 'text'),
            ('Enforce positivity', raw_settings.getId('denssPositivity'), 'bool'),
            ('Shrinkwrap', raw_settings.getId('denssShrinkwrap'), 'bool'),
            ('Shrinkwrap first step:', raw_settings.getId('denssShrinkwrapMinStep'), 'int'),
            ('Enforce conectivity', raw_settings.getId('denssConnected'), 'bool'),
            ('Enforce connectivity at steps:', raw_settings.getId('denssConnectivitySteps'), 'text'),
            ('Write xplor files', raw_settings.getId('denssWriteXplor'), 'bool'),
            ('Reduce size of output map', raw_settings.getId('denssCutOut'), 'bool'),
            ('N-fold symmetry:', raw_settings.getId('denssNCS'), 'int'),
            ('Enforce symmetry at steps:', raw_settings.getId('denssNCSSteps'), 'text'),
            ('Symmetry Axis:', raw_settings.getId('denssNCSAxis'), 'int')
            )

        layoutSizer = self._createLayout(self)

        self.SetSizer(layoutSizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def _createLayout(self, parent):
        default_box = wx.StaticBox(parent, wx.ID_ANY, 'Default settings')
        default_sizer = wx.StaticBoxSizer(default_box, wx.VERTICAL)

        for item in self.default_options:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(default_box, -1, label)
                ctrl = wx.Choice(default_box, myId, choices = item[3])

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(default_box, -1, label)
                ctrl = wx.TextCtrl(default_box, myId, '', size=self._FromDIP((475,-1)),
                    style = wx.TE_PROCESS_ENTER)

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 1, wx.ALL|wx.EXPAND, border=self._FromDIP(2))

            elif itemType == 'bool':
                ctrl = wx.CheckBox(default_box, myId, label)
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            default_sizer.Add(sizer, 0)

        custom_box = wx.StaticBox(parent, wx.ID_ANY, 'Custom settings (only used in custom mode)')
        customSizer = wx.StaticBoxSizer(custom_box, wx.VERTICAL)

        for item in self.custom_options_long:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            sizer = wx.BoxSizer(wx.HORIZONTAL)

            if itemType == 'choice':
                labeltxt = wx.StaticText(custom_box, -1, label)
                ctrl = wx.Choice(custom_box, myId, choices = item[3])

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(custom_box, -1, label)
                ctrl = wx.TextCtrl(custom_box, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                sizer.Add(labeltxt, 0, wx.ALL, border=self._FromDIP(2))
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            elif itemType == 'bool':
                ctrl = wx.CheckBox(custom_box, myId, label)
                sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))

            customSizer.Add(sizer, 0)

        short_sizer = wx.FlexGridSizer(cols=4, hgap=self._FromDIP(2),
            vgap=self._FromDIP(2))

        for item in self.custom_options_short:
            label = item[0]
            myId = item[1]
            itemType = item[2]

            if itemType == 'choice':
                labeltxt = wx.StaticText(custom_box, -1, label)
                ctrl = wx.Choice(custom_box, myId, choices = item[3])

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'text' or itemType == 'int' or itemType =='float':
                labeltxt = wx.StaticText(custom_box, -1, label)
                ctrl = wx.TextCtrl(custom_box, myId, '', size=self._FromDIP((60,-1)),
                    style = wx.TE_PROCESS_ENTER)

                short_sizer.Add(labeltxt, 0)
                short_sizer.Add(ctrl, 0)

            elif itemType == 'bool':
                ctrl = wx.CheckBox(custom_box, myId, label)
                short_sizer.Add(ctrl, 0, wx.ALL, border=self._FromDIP(2))
                short_sizer.AddStretchSpacer(1)

        customSizer.Add(short_sizer,0)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(default_sizer)
        top_sizer.Add(customSizer)

        return top_sizer



def ExtractFilenameAndFrameNumber(filename, frameregexp, nameregexp):

    frame = 'No Match'
    name = 'No Match'

    # EXTRACT FRAME NUMBER
    try:
        pattern = re.compile(frameregexp)
        m = pattern.findall(filename)

        if len(m) > 0:
            found = ''
            for each in m:
                found = found + each

            non_decimal = re.compile(r'[^\d.]+')
            frame = non_decimal.sub('', found)

            if frame == '':
                frame = 'No Match'
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

            if found != '':
                name = found
            else:
                name = 'No Match'

    except:
        pass

    return name, frame

def TestAutoBgSubRegExpression(filename, regexp):

    try:
        pattern = re.compile(regexp)
    except:
        return 'No Match'

    m = pattern.match(filename)

    if m:
        found = m.group()

        if found == filename:
            return 'Match'
        else:
            print(found)
            return 'No Match'
    else:
        found = 'No Match'
        return found

#--- ** TREE BOOK **
class ConfigTree(CT.CustomTreeCtrl):
    """
       Tree that displays all the options. When the user clicks
       on an option, the panel to the right switches to the
       available widgets for that option.
    """
    def __init__(self, parent, *args, **kwargs):

        #Another strange Mac bug workaround:
        if sys.platform == 'darwin':
            CT.CustomTreeCtrl.__init__(self, parent, *args,
                style = wx.TR_HAS_BUTTONS|CT.TR_HIDE_ROOT|CT.TR_NO_LINES|wx.RAISED_BORDER, **kwargs)
        else:
            CT.CustomTreeCtrl.__init__(self, parent, *args,
                style = wx.TR_HAS_BUTTONS|CT.TR_HIDE_ROOT|CT.TR_NO_LINES|wx.RAISED_BORDER, **kwargs)

        self.parent = parent

        all_options = wx.FindWindowByName('OptionsDialog').all_options

        self.root = self.AddRoot("Configuration Settings", data=all_options[0][1])

        last_idx = -1
        last_sub_idx = -1
        for each_idx, id, label, panelfunc in all_options[1:]:
            idx, sub_idx, subsubidx = each_idx

            if last_idx == idx:
                if sub_idx == 0:
                    self.AppendItem(self.top_child, label, data = id)
                    last_sub_idx = sub_idx
                elif sub_idx != last_sub_idx:
                    self.middle_child = self.AppendItem(self.top_child, label, data = id)
                    last_sub_idx = sub_idx
                # elif subsubidx == 1:
                #     self.middle_child = self.AppendItem(self.top_child, label, data = id)
                else:
                    self.AppendItem(self.middle_child, label, data = id)
            else:
                self.top_child = self.AppendItem(self.root, label, data = id)

            # Select the first option in the list
            if last_idx == 0:
                self.SelectItem(self.child, True)

            last_idx = idx
            last_sub_idx = sub_idx

        self.Bind(CT.EVT_TREE_SEL_CHANGED, self.onSelChanged)

        self.ExpandAll()

    def onSelChanged(self, event):

        display = self.parent.GetParent().page_panel

        self.item = event.GetItem()

        if self.item:
            id = self.item.GetData()
            option_label = self.GetItemText(self.item)
            display.updatePage(id, option_label)

class PagePanel(wx.Panel):
    '''
        A panel that holds the individual option pages/panels.
        Using this panel it is possible to add standard buttons at the
        bottom of the page.
    '''

    def __init__(self, parent, raw_settings, *args, **kwargs):

        wx.Panel.__init__(self, parent, style=wx.BG_STYLE_SYSTEM|wx.RAISED_BORDER,
            *args, **kwargs)

        self.parent = parent

        self.all_panels = []

        page_sizer = wx.BoxSizer(wx.VERTICAL)
        self.title_string = wx.StaticText(self, -1, '')
        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD)
        self.title_string.SetFont(font)

        page_sizer.Add(self.title_string, 0, wx.EXPAND|wx.ALL, border=self._FromDIP(5))
        page_sizer.Add(wx.StaticLine(self, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)

        # Creating and inserting all panels from all_options
        all_options = wx.FindWindowByName('OptionsDialog').all_options

        for idx, id, label, panelfunc in all_options:
            if panelfunc is not None:
                panel = panelfunc(self, id, raw_settings)
                panel.SetExtraStyle(wx.WS_EX_BLOCK_EVENTS)
                panel.Hide()
                self.all_panels.append(panel)
                page_sizer.Add(panel, 1, wx.EXPAND)

        self.SetSizer(page_sizer)

        # Set the default selection to the first in the all_options list
        self.current_page = wx.FindWindowById(all_options[0][1])
        self.updatePage(all_options[0][1], all_options[0][2])

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def getPanels(self):
        return self.all_panels

    def updatePage(self, panel_id, option_label):

        try:
            new_panel = wx.FindWindowById(panel_id)
        except TypeError:
            print('TypeError in updatePage(), possibly Hide root bug in wxpython')
            return

        if new_panel is not None:
            self.current_page.Hide()
            self.current_page = new_panel
            self.current_page.Show()
            # self.current_page.SetFocus()

            self.title_string.SetLabel(option_label)
            self.Layout()
        else:
            raise Exception('Panel for ' + str(option_label) +  ' not found')

        self.Refresh()
        self.Update()


class OptionsTreebook(wx.Panel):
    '''
        A panel with a treectrl containing the individual options
        and a panel that shows the parameters available for the
        chosen option.
    '''

    def __init__(self, parent, raw_settings, *args, **kwargs):

        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        splitter = wx.SplitterWindow(self, -1, style=wx.SP_3DSASH|wx.SP_NOBORDER|wx.SP_LIVE_UPDATE)

        self.tree = ConfigTree(splitter)
        self.page_panel = PagePanel(splitter, raw_settings)

        splitter.SplitVertically(self.tree, self.page_panel, self._FromDIP(180))
        splitter.SetMinimumPaneSize(self._FromDIP(100))

        sizer = wx.BoxSizer()
        sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def getAllUpdateKeys(self):

        all_update_keys = []

        for each in self.page_panel.all_panels:
            try:
                all_update_keys.extend(each.update_keys)
            except AttributeError:
                pass

        return all_update_keys

    def getAllNonGuiChanges(self):

        changes_dict = {}

        for each in self.page_panel.all_panels:
            try:
                changes_dict = dict(list(changes_dict.items()) + list(each.changes.items()))
            except AttributeError:
                pass

        return changes_dict

    def updateAllNonGuiChanges(self):
        for each in self.page_panel.all_panels:
            try:
                each.updateNonGuiChanges()
            except AttributeError:
                pass

    def selectPage(self, heading):

        root = self.tree.GetRootItem()

        item = self.find_branch(self.tree, heading, root)

        if item:
            self.tree.SelectItem(item)


    def find_branch(self, tree, heading, root):
        item, cookie = tree.GetFirstChild(root)

        while item and item.IsOk():
            if tree.GetItemText(item) == heading:
                return item
            if tree.ItemHasChildren(item):
                item2 = self.find_branch(tree, heading, item)
                if item2:
                    return item2
            item, cookie = tree.GetNextChild(root, cookie)

        return None


#--- ** MAIN DIALOG **

class OptionsDialog(wx.Dialog):
    '''
        The option dialog that pops up when the user chooses
        options in the menu.
    '''
    def __init__(self, parent, raw_settings, focusHeader = None, *args, **kwargs):

        wx.Dialog.__init__(self, parent, -1, 'Options', *args, name='OptionsDialog',
            style=wx.RESIZE_BORDER|wx.CAPTION, **kwargs)
        self.SetSize(self._FromDIP((850,750)))

        #################################################################
        # To append more options make a custom panel class with theF
        # widgets and insert it into all_options below.
        #################################################################

        self.all_options = [
            [ (0,0,0), wx.Window.NewControlId(), 'Configuration Settings', ConfigRootSettings],
            [ (1,0,0), wx.Window.NewControlId(), 'General Settings', GeneralOptionsPanel],
            [ (2,0,0), wx.Window.NewControlId(), '2D Reduction', ReductionOptionsPanel],
            [ (2,1,0), wx.Window.NewControlId(), 'Image/Header Format', ReductionImgHdrFormatPanel],
            [ (2,2,0), wx.Window.NewControlId(), 'Radial Averaging', CalibrationOptionsPanel],
            [ (2,3,1), wx.Window.NewControlId(), 'Normalization', ReductionNormalizationPanel] ,
            [ (2,3,2), wx.Window.NewControlId(), 'Absolute Scale', ReductionNormalizationAbsScPanel],
            [ (2,3,3), wx.Window.NewControlId(), 'Flatfield and Dark Correction', ReductionFlatfield],
            [ (2,4,0), wx.Window.NewControlId(), 'Metadata', MetadataPanel],
            [ (3,0,0), wx.Window.NewControlId(), 'Molecular Weight', MolecularWeightPanel],
            [ (4,0,0), wx.Window.NewControlId(), 'Artifact Removal', ArtifactOptionsPanel],
            [ (5,0,0), wx.Window.NewControlId(), 'IFT', IftOptionsPanel],
            [ (6,0,0), wx.Window.NewControlId(), "Autosave", SaveDirectoriesPanel],
            [ (7,0,0), wx.Window.NewControlId(), 'Online Mode', OnlineModePanel],
            [ (8,0,0), wx.Window.NewControlId(), 'Series', SeriesPanel],
            # [ (8,0,0), wx.Window.NewControlId(), "Automation", AutomationOptionsPanel],
            [ (9,0,0), wx.Window.NewControlId(), "ATSAS", ATSASGeneralPanel],
            [ (9,1,1), wx.Window.NewControlId(), "GNOM", ATSASGnom],
            [ (9,1,2), wx.Window.NewControlId(), "GNOM Advanced", ATSASGnomAdvanced],
            [ (9,5,1), wx.Window.NewControlId(), "DAMMIF/N", ATSASDammix],
            [ (9,5,2), wx.Window.NewControlId(), "DAMMIF/N Advanced", ATSASDammixAdvanced],
            [ (9,5,2), wx.Window.NewControlId(), "DAMMIF Advanced", ATSASDammifAdvanced],
            [ (9,5,2), wx.Window.NewControlId(), "DAMMIN Advanced", ATSASDamminAdvanced],
            [ (10,0,0), wx.Window.NewControlId(), "Weighted Average", WeightedAveragePanel],
            [ (11,0,0), wx.Window.NewControlId(), "Similarity Testing", SimilarityPanel],
            [ (12,0,0), wx.Window.NewControlId(), "Fitting", FittingPanel],
            [ (13,0,0), wx.Window.NewControlId(), "DENSS", DenssPanel],
            ]

        self._raw_settings = raw_settings
        self.treebook = OptionsTreebook(self, raw_settings)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.treebook, 1, wx.EXPAND)
        sizer.Add(wx.StaticLine(self, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)
        sizer.Add(self.createButtonPanel(), 0, wx.ALIGN_RIGHT|wx.ALL,
            border=self._FromDIP(5))

        self.initSettings()

        item = self.treebook.tree.GetFirstVisibleItem()

        if item is not None:
            self.treebook.tree.SelectItem(item)

        if focusHeader:
            self.treebook.selectPage(focusHeader)

        self.SendSizeEvent()

        self.SetSizer(sizer)

        client_display = wx.GetClientDisplayRect()
        minsize = (min(800, client_display.Width), min(600, client_display.Height))
        self.SetMinSize(self._FromDIP(minsize))

        SASUtils.set_best_size(self)

        self.CenterOnParent()

    def _FromDIP(self, size):
        # This is a hack to provide easy back compatibility with wxpython < 4.1
        try:
            return self.FromDIP(size)
        except Exception:
            return size

    def createButtonPanel(self):

        ok_button = wx.Button(self, wx.ID_OK)
        cancel_button = wx.Button(self, wx.ID_CANCEL)
        apply_button = wx.Button(self, wx.ID_APPLY)

        ok_button.Bind(wx.EVT_BUTTON, self.onOK)
        cancel_button.Bind(wx.EVT_BUTTON, self.onCancel)
        apply_button.Bind(wx.EVT_BUTTON, self.onApply)

        button_sizer = wx.BoxSizer()
        button_sizer.Add(cancel_button, 0, wx.RIGHT, border=self._FromDIP(5))
        button_sizer.Add(apply_button, 0, wx.RIGHT, border=self._FromDIP(5))
        button_sizer.Add(ok_button, 0)

        return button_sizer

    def onOK(self, event):
        try:
            self.saveSettings()
            self.EndModal(wx.ID_OK)
            self.Destroy()
        except ValueError:
            dlg = wx.MessageDialog(self,
            "Invalid value entered. Settings not saved.",
            'Invalid input', wx.OK|wx.ICON_EXCLAMATION, parent = self)
            dlg.ShowModal()
            dlg.Destroy()

    def onApply(self, event):
        try:
            self.saveSettings()
            wx.MessageBox('Settings have been updated.', 'Settings Updated', parent = self)
        except ValueError:
            dlg = wx.MessageDialog(self,
            "Invalid value entered. Settings not saved.",
            'Invalid input', wx.OK|wx.ICON_EXCLAMATION, parent = self)
            dlg.ShowModal()
            dlg.Destroy()

    def onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()

    def initSettings(self):
        all_update_keys = self.treebook.getAllUpdateKeys()

        for key in all_update_keys:
            myId, myType = self._raw_settings.getIdAndType(key)
            val = self._raw_settings.get(key)
            obj = wx.FindWindowById(myId, self)

            if myType == 'bool':
                obj.SetValue(val)
            elif myType == 'list':
                obj.SetValue(val)

            elif myType == 'choice':
                choice_list = obj.GetStrings()
                if val is not None:
                    try:
                        idx = choice_list.index(val)
                    except ValueError:
                        idx = 0
                else:
                    idx=0
                obj.Select(idx)

            elif myType == 'text' or myType == 'int' or myType == 'float':
                try:
                    obj.SetValue(val)
                except TypeError:
                    obj.SetValue(str(val))

    def saveSettings(self):
        all_update_keys = self.treebook.getAllUpdateKeys()

        for key in all_update_keys:
            myId, myType = self._raw_settings.getIdAndType(key)

            obj = wx.FindWindowById(myId, self)

            if myType == 'bool':
                val = obj.GetValue()

            elif myType == 'text':
                val = obj.GetValue()

            elif myType == 'choice':
                val = obj.GetStringSelection()

            elif myType == 'int':
                val = obj.GetValue()
                val = int(val)

                if math.isinf(val) or math.isnan(val):
                    raise ValueError

            elif myType == 'float':
                val = obj.GetValue()
                val = float(val)

                if math.isinf(val) or math.isnan(val):
                    raise ValueError

            self._raw_settings.set(key, val)

        all_non_gui_changes = self.treebook.getAllNonGuiChanges()

        for each_key in all_non_gui_changes:
            val = all_non_gui_changes[each_key]
            self._raw_settings.set(each_key, val)

        self.treebook.updateAllNonGuiChanges()

        main_frame = wx.FindWindowByName('MainFrame')

        for mw_window in main_frame.mw_frames:
            if mw_window:
                mw_window.updateMWInfo()

        for gnom_window in main_frame.gnom_frames:
            if gnom_window:
                gnom_window.updateGNOMSettings()

        for dammif_window in main_frame.dammif_frames:
            if dammif_window:
                dammif_window.updateDAMMIFSettings()

        for denss_window in main_frame.denss_frames:
            if denss_window:
                denss_window.updateDenssSettings()

        for bift_window in main_frame.bift_frames:
            if bift_window:
                bift_window.updateBIFTSettings()

        # Load flatfield and dark images

        if self._raw_settings.get('NormFlatfieldEnabled'):
            flat_filename = self._raw_settings.get('NormFlatfieldFile')
            flat_img, _ = SASFileIO.loadImage(flat_filename, self._raw_settings)
            self._raw_settings.set('NormFlatfieldImage', flat_img[0])
        else:
            self._raw_settings.set('NormFlatfieldImage', None)

        if self._raw_settings.get('DarkCorrEnabled'):
            dark_filename = self._raw_settings.get('DarkCorrFilename')
            dark_img, _ = SASFileIO.loadImage(dark_filename, self._raw_settings)
            self._raw_settings.set('DarkCorrImage', dark_img[0])
        else:
            self._raw_settings.set('DarkCorrImage', None)



#--- ** FOR TESTING **

class OptionsFrame(wx.Frame):
    ''' A Frame for the options dialog used for testing '''

    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title)

        raw_settings = RAWSettings.RawGuiSettings()

        dialog = OptionsDialog(self, raw_settings)
        dialog.ShowModal()
        dialog.Destroy()

        self.Destroy()

class OptionsTestApp(wx.App):
    ''' A test app '''

    def OnInit(self):

        frame = OptionsFrame('Options', -1)
        self.SetTopWindow(frame)
        frame.CenterOnScreen()
        frame.Show(True)
        return True


if __name__ == "__main__":
    app = OptionsTestApp(0)   #MyApp(redirect = True)
    app.MainLoop()
