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


import wx, masking
import fileIO, cartToPol
from numpy import power, ceil
#from os import path

class PatternRadioBox(wx.Panel):
    
    def __init__(self, parent, type_id, value_id):
        
        wx.Panel.__init__(self, parent, type_id)
        
        self.value_id = value_id
        
        self.radioButtons = ( ("Starts with :", wx.NewId(), 'start' ),
                              ("Ends with :", wx.NewId(), 'end'),
                              ("Contains :", wx.NewId(), 'contain') )
        
        sizer = self.createAutoBgSubtractOptions()
        
        self.value = 'start'
        
        self.SetSizer(sizer)
    
    def createAutoBgSubtractOptions(self):
        
        box = wx.StaticBox(self, -1, 'Background Filename Pattern')
        radioSizer = wx.BoxSizer(wx.VERTICAL)
        
        for eachLabel, id, name in self.radioButtons:
            
            if name == 'start':
                radioButton1 = wx.RadioButton(self, id, eachLabel, style = wx.RB_GROUP)
            else:
                radioButton1 = wx.RadioButton(self, id, eachLabel)
            
            radioButton1.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
            radioSizer.Add(radioButton1, 0, wx.BOTTOM, 3)
            
        text = wx.TextCtrl(self, self.value_id, '')
        
        autoSubOptionsSizer = wx.BoxSizer()
        autoSubOptionsSizer.Add(radioSizer, 0, wx.CENTER)
        autoSubOptionsSizer.Add(text, 0, wx.CENTER | wx.LEFT, 5)
        
        boxsizer = wx.StaticBoxSizer(box)
        boxsizer.Add(autoSubOptionsSizer, 1, wx.ALL, 5)
        
        return boxsizer
    
    def OnRadioButton(self, evt):
        id = evt.GetId()
        
        for each in self.radioButtons:
            if each[1] == id:
                self.value = each[2]
    
    def GetValue(self):
        return self.value

    def SetValue(self, value):
        self.value = value
        
        for each in self.radioButtons:
            if each[2] == value:
                radiobutton = wx.FindWindowById(each[1])
                radiobutton.SetValue(True)
          
class MaskingOptions(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        self.expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
        
        self.filesData = (("Beamstop Mask:"     , self.expParamsInGUI['BeamStopMaskFilename'][0], wx.NewId(), wx.NewId(), "Set..", "C", self.onSetFile, self.onClrFile),
                          ("Readout Noise Mask:", self.expParamsInGUI['ReadOutNoiseMaskFilename'][0], wx.NewId(), wx.NewId(), "Set..", "C", self.onSetFile, self.onClrFile))

        

        box = wx.StaticBox(self, -1, 'Mask Files')
        fileSizer = self.createFileSettings()
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkboxSizer.Add(fileSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(chkboxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.SetSizer(panelsizer)


    def createFileSettings(self):
        
        noOfRows = int(len(self.filesData))
        hSizer = wx.FlexGridSizer(cols = 4, rows = noOfRows, vgap = 3, hgap = 3)
        
        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in self.filesData:
            
            setButton = wx.Button(self, setButton_ID, setButtonTxt, size = (45,22))
            setButton.Bind(wx.EVT_BUTTON, setBindFunc)
            clrButton = wx.Button(self, clrButton_ID, clrButtonTxt, size = (25,22))
            clrButton.Bind(wx.EVT_BUTTON, clrBindFunc)
    
            label = wx.StaticText(self, -1, labtxt)

            filenameLabel = wx.TextCtrl(self, labl_ID, "None")
            filenameLabel.SetEditable(False)
                            
            hSizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
            hSizer.Add(filenameLabel, 1, wx.EXPAND)
            hSizer.Add(setButton, 1)
            hSizer.Add(clrButton, 1)
        
        hSizer.AddGrowableCol(1)
        
        return hSizer
    
    def _GetMaskFile(self, Text):
        
        filters = 'Mask files (*.msk)|*.msk|All files (*.*)|*.*'
        filedlg = wx.FileDialog( None, style = wx.OPEN, wildcard = filters)
        
        if filedlg.ShowModal() == wx.ID_OK:
            mask_filename = filedlg.GetFilename()
            mask_dir = filedlg.GetDirectory()
            mask_fullpath = filedlg.GetPath()
            filedlg.Destroy()
            
            return (mask_filename, mask_dir, mask_fullpath)
        else:
            filedlg.Destroy()
            return (None, None, None)

    def onSetFile(self, evt):
        
        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in self.filesData:
            id = evt.GetId()
            
            #Set button:
            if id == setButton_ID:
            
                if labl_ID == self.expParamsInGUI['BeamStopMaskFilename'][0]:
                    #optionspage = wx.FindWindowByName('OptionsPage')
                    filename = self.OnSetMask(None)
            
                    if filename != None:
                        filenameLabel = wx.FindWindowById(labl_ID)
                        filenameLabel.SetValue(filename)
                
                if labl_ID == self.expParamsInGUI['ReadOutNoiseMaskFilename'][0]:
              #      optionspage = wx.FindWindowByName('OptionsPage')
                    filename = self.OnSetReadoutMask(None)
            
                    if filename != None:
                        filenameLabel = wx.FindWindowById(labl_ID)
                        filenameLabel.SetValue(filename)
                                     
    
    def OnSetMask(self, evt):
        
        mask_filename, mask_dir, mask_fullpath = self._GetMaskFile("Please choose the Beamstop mask file.")
        
        if mask_filename != None:
            masking.LoadBeamStopMask(mask_fullpath)
            
        return mask_filename
    
    def OnSetReadoutMask(self, evt):
        (mask_filename, mask_dir, mask_fullpath) = self._GetMaskFile("Please choose the Readout mask file.")
        
        if mask_filename != None:
            masking.LoadReadoutNoiseMask(mask_fullpath)
            
        return mask_filename
    

    def onClrFile(self, evt):
        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in self.filesData:
            id = evt.GetId()
            
            if id == clrButton_ID:
                if labl_ID == self.expParamsInGUI['BeamStopMaskFilename'][0]:
                    optionspage = wx.FindWindowByName('MainFrame')
                    optionspage.ChangeParameter('BeamStopMask', None)
                    optionspage.ChangeParameter('BeamStopMaskFilename', None)
                    optionspage.ChangeParameter('BeamStopMaskParams', None)
                    
                    filenameLabel = wx.FindWindowById(labl_ID)
                    filenameLabel.SetValue('None')
                
                if labl_ID == self.expParamsInGUI['ReadOutNoiseMaskFilename'][0]:
                    optionspage = wx.FindWindowByName('MainFrame')
                    optionspage.ChangeParameter('ReadOutNoiseMask', None)
                    optionspage.ChangeParameter('ReadOutNoiseMaskFilename', None)
                    optionspage.ChangeParameter('ReadOutNoiseMaskParams', None)
                    
                    filenameLabel = wx.FindWindowById(labl_ID)
                    filenameLabel.SetValue('None')

        
class GeneralOptionsPage(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        
        expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
        
        self.chkboxData = ( ("Automatic Background Subtraction", expParamsInGUI['AutoBgSubtract'][0]),
                            ("Automatic BIFT",                   expParamsInGUI['AutoBIFT'][0]) )

        self.artifactRemovalData = ( ('Zinger Removal by Smoothing', expParamsInGUI['ZingerRemoval']),
                                     ('Std:',            expParamsInGUI['ZingerRemoveSTD']),
                                     ('Window Length:',  expParamsInGUI['ZingerRemoveWinLen']),
                                     ('Start Index:',    expParamsInGUI['ZingerRemoveIdx']))
        
        self.artifactRemovalData2 = ( ('Zinger Removal when Averageing', expParamsInGUI['ZingerRemovalAvg']),
                                      ('Sensitivty (lower is more):', expParamsInGUI['ZingerRemovalAvgStd']) )
        
        chkboxSizer = self.createChkBoxSettings()
        
        artifactSizer = self.createArtifactRemoveSettings()
        artifactSizer2 = self.createArtifactRemoveOnAvg()
        
        self.autoSubOptionsPanel = PatternRadioBox(self, expParamsInGUI['BgPatternType'][0], expParamsInGUI['BgPatternValue'][0])
        
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(artifactSizer, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,5)
        panelsizer.Add(artifactSizer2, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)
        panelsizer.Add(chkboxSizer, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM ,5)        
        panelsizer.Add(self.autoSubOptionsPanel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM ,5)
        #panelsizer.Add(wx.StaticLine(self,-1), 0, wx.EXPAND)
        #panelsizer.Add(constantsSizer, 1, wx.EXPAND | wx.TOP, 10)
        
        self.SetSizer(panelsizer)
        
    def createArtifactRemoveOnAvg(self):
        
        box = wx.StaticBox(self, -1, 'Artifact Removal when Averaging')
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 5, hgap = 5)
        
        for label, param in self.artifactRemovalData2:
            
            if param != None:
                       
                id = param[0]
                type = param[1]
            
                if type != 'bool':
                    text = wx.StaticText(self, -1, label)
                    ctrl = wx.TextCtrl(self, id, 'None')
                
                    gridSizer.Add(text, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
                    gridSizer.Add(ctrl, 1, wx.EXPAND | wx.ALIGN_CENTER)
                else:
                    chk = wx.CheckBox(self, id, label)
                    chk.Bind(wx.EVT_CHECKBOX, self.onChkBox)
                    chkboxSizer.Add(chk, 0, wx.EXPAND | wx.ALL, 5)
        
        chkboxSizer.Add(gridSizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)    
    
        return chkboxSizer
        
    
    def createArtifactRemoveSettings(self):
        
        box = wx.StaticBox(self, -1, 'Artifact Removal')
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridSizer = wx.FlexGridSizer(cols = 4, rows = 2, vgap = 5, hgap = 5)
        
        for label, param in self.artifactRemovalData:
            
            id = param[0]
            type = param[1]
            
            if type != 'bool':
                text = wx.StaticText(self, -1, label)
                ctrl = wx.TextCtrl(self, id, 'None')
                
                gridSizer.Add(text, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
                gridSizer.Add(ctrl, 1, wx.EXPAND | wx.ALIGN_CENTER)
            else:
                chk = wx.CheckBox(self, id, label)
                chk.Bind(wx.EVT_CHECKBOX, self.onChkBox)
                chkboxSizer.Add(chk, 0, wx.EXPAND | wx.ALL, 5)
        
        chkboxSizer.Add(gridSizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)    
    
        return chkboxSizer
    
    def createChkBoxSettings(self):
        
        box = wx.StaticBox(self, -1, 'Automation')
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        #chkboxSizer.Add((5,5),0)
        chkboxgridSizer = wx.GridSizer(rows = len(self.chkboxData), cols = 1)
                
        for eachLabel, id in self.chkboxData:
            
            if eachLabel != None:
                chkBox = wx.CheckBox(self, id, eachLabel)
                chkBox.Bind(wx.EVT_CHECKBOX, self.onChkBox)
                chkboxgridSizer.Add(chkBox, 1, wx.EXPAND)
        
        
        chkboxSizer.Add(chkboxgridSizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
            
        return chkboxSizer
        
    def onChkBox(self, evt):
        pass
        # Might need it later
#        expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
#        
#        chkbox = evt.GetEventObject()
#        
#        if chkbox.GetId() == expParamsInGUI['ZingerRemoval'][0]:
#            print 'hello!'

        
class CalibrationOptionsPage(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        
        self.expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
        
        optDiag = wx.FindWindowByName('OptionsDialog')
        self.expParams = optDiag.expParams
        
                          #          label,     textCtrlId,            buttonId, clrbuttonId,  ButtonText, BindFunction
        self.filesData = (("Empty cell:"   , self.expParamsInGUI['EmptyFile'][0]    , wx.NewId(), wx.NewId(), "Set..", "C", self.onSetFile, self.onClrFile),
                          ("Water sample:" , self.expParamsInGUI['WaterFile'][0]    , wx.NewId(), wx.NewId(), "Set..", "C", self.onSetFile, self.onClrFile))
                          #("Flat Field:"   , expParamsInGUI['FlatFieldFile'][0], wx.NewId(), wx.NewId(), "Set..", "C", self.onSetFile, self.onClrFile))
        
        self.normConstantsData = ( ("WaterAvgMinPoint:", self.expParamsInGUI['WaterAvgMinPoint'][0] ),
                                   ("WaterAvgMaxPoint:", self.expParamsInGUI['WaterAvgMaxPoint'][0] ))
        
        self.calibConstantsData = (("Sample-Detector Distance:" , self.expParamsInGUI['SampleDistance'][0] , 'mm'),
                                   ("Sample-Detector Offset:", self.expParamsInGUI['SmpDetectOffsetDist'][0], 'mm'),
                                   ("Wavelength:"      , self.expParamsInGUI['WaveLength'][0]     , 'A'),
                                   #("Sample thickness:", expParamsInGUI['SampleThickness'][0], 'mm'),                           
                                   #("Reference Q:", expParamsInGUI['ReferenceQ'][0], '1/A'),
                                   #("Reference Q Distance:", expParamsInGUI['ReferenceDistPixel'][0], 'pixels'),
                                   ("Detector Pixelsize:", self.expParamsInGUI['DetectorPixelSize'][0], 'um'),
                                   ("AgBe (Distance to First Ring):", self.expParamsInGUI['PixelCalX'][0], 'pixels'))                              

        self.treatmentdata = (("Absolute Scale Calibration", self.expParamsInGUI['NormalizeAbs'][0]),
                              ("Calibrate Q-range (AgBe)", self.expParamsInGUI['Calibrate'][0]),
                              ("Calibrate Q-range (Distance)", self.expParamsInGUI['CalibrateMan'][0]))


        box = wx.StaticBox(self, -1, 'Absolute Scaling')                            
        fileSizer = self.createFileSettings()
        normConstSizer = self.createNormConstants()
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkboxSizer.Add(fileSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        chkboxSizer.Add(normConstSizer, 0, wx.EXPAND | wx.ALL, 5)
        
        constantsSizer = self.createCalibConstants()
        
        treatmentSizer = self.CreateTreatmentData()
        
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(chkboxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(constantsSizer, 0, wx.EXPAND | wx.ALL, 5)
        panelsizer.Add(treatmentSizer, 0, wx.EXPAND | wx.BOTTOM | wx.RIGHT | wx.LEFT, 5)
        
        self.SetSizer(panelsizer)
        
    def onSetFile(self, event):    
        
        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID
        
        selectedFile = wx.FindWindowByName('OptionsDialog')._CreateFileDialog(wx.OPEN)
            
        for each in self.filesData:
            if each[2] == ID:
                    textCtrl = wx.FindWindowById(each[1]) 
                    textCtrl.SetValue(str(selectedFile))        

    def onClrFile(self, event):
        
        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID
        
        for each in self.filesData:
                if each[3] == ID:
                    textCtrl = wx.FindWindowById(each[1]) 
                    textCtrl.SetValue('None')
    
    def createCalibConstants(self):       
        
        box = wx.StaticBox(self, -1, 'Calibration Parameters')
        noOfRows = int(len(self.calibConstantsData))
        calibSizer = wx.FlexGridSizer(cols = 3, rows = noOfRows, vgap = 3)
        
        
        for eachText, id, unitTxt in self.calibConstantsData:
            
            txt = wx.StaticText(self, -1, eachText)
            unitlabel = wx.StaticText(self, -1, unitTxt)
            ctrl = wx.TextCtrl(self, id, '0', style = wx.TE_PROCESS_ENTER | wx.TE_RIGHT, size = (60, 21))
            
            calibSizer.Add(txt, 1, wx.EXPAND | wx.ALIGN_LEFT)
            calibSizer.Add(ctrl, 1, wx.EXPAND | wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT, 5)
            calibSizer.Add(unitlabel, 1, wx.EXPAND | wx.TOP, 2)
        
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkboxSizer.Add(calibSizer, 1, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, 5)
        
        return chkboxSizer
                        
    def createFileSettings(self):
        
        noOfRows = int(len(self.filesData))
        hSizer = wx.FlexGridSizer(cols = 4, rows = noOfRows, vgap = 3, hgap = 3)
        
        for labtxt, labl_ID, setButton_ID, clrButton_ID, setButtonTxt, clrButtonTxt, setBindFunc, clrBindFunc in self.filesData:
            
            setButton = wx.Button(self, setButton_ID, setButtonTxt, size = (45,22))
            setButton.Bind(wx.EVT_BUTTON, setBindFunc)
            clrButton = wx.Button(self, clrButton_ID, clrButtonTxt, size = (25,22))
            clrButton.Bind(wx.EVT_BUTTON, clrBindFunc)
    
            label = wx.StaticText(self, -1, labtxt)

            filenameLabel = wx.TextCtrl(self, labl_ID, "None")
            filenameLabel.SetEditable(False)
                            
            hSizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
            hSizer.Add(filenameLabel, 1, wx.EXPAND)
            hSizer.Add(setButton, 1)
            hSizer.Add(clrButton, 1)
        
        hSizer.AddGrowableCol(1)
        return hSizer
    
    def createNormConstants(self):
        
        noOfRows = int(len(self.filesData))
        hSizer = wx.FlexGridSizer(cols = 2, rows = noOfRows, vgap = 3, hgap = 3)
        
        for eachLabel, id in self.normConstantsData:
            
            txt = wx.StaticText(self, -1, eachLabel)
            ctrl = wx.TextCtrl(self, id, '0', style = wx.TE_PROCESS_ENTER | wx.TE_RIGHT, size = (60, 21))
    
            hSizer.Add(txt, 1)
            hSizer.Add(ctrl, 1)
        
        return hSizer
    
    def CreateTreatmentData(self):
        
        box = wx.StaticBox(self, -1, 'Calibration')
        staticBoxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        treatmentSizer = wx.BoxSizer(wx.VERTICAL)
        for each, id in self.treatmentdata:
            chkBox = wx.CheckBox(self, id, each)
            chkBox.Bind(wx.EVT_CHECKBOX, self.OnChkBox)
            treatmentSizer.Add(chkBox, 0)
        
        staticBoxSizer.Add(treatmentSizer, 0, wx.BOTTOM | wx.LEFT, 5)
        
        return staticBoxSizer

    def OnChkBox(self, event):
        
        chkboxID = event.GetId()
        
        self._CorrectConflictingSettings(chkboxID)
        optDialog = wx.FindWindowByName('OptionsDialog')
        
        optDialog._UpdateToExpParams()
    
    def _CorrectConflictingSettings(self, chkboxID):
    
        norm1ID = self.expParamsInGUI['NormalizeM1'][0]
        norm2ID = self.expParamsInGUI['NormalizeM2'][0]
        norm3ID = self.expParamsInGUI['NormalizeTime'][0]
        norm4ID = self.expParamsInGUI['NormalizeTrans'][0]
        
        normM1box = wx.FindWindowById(norm1ID)
        normM2box = wx.FindWindowById(norm2ID)
        normTimebox = wx.FindWindowById(norm3ID)
        normTransbox = wx.FindWindowById(norm4ID)
        
        if chkboxID == self.expParamsInGUI['CalibrateMan'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['Calibrate'][0])
            calibChkBox.SetValue(False)
        elif chkboxID == self.expParamsInGUI['Calibrate'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['CalibrateMan'][0])
            calibChkBox.SetValue(False)
            
        #################################################
        #### IF Absolute Calibration Checkbox is pressed:
        #################################################
        
        if chkboxID == self.expParamsInGUI['NormalizeAbs'][0]:
            absChkBox = wx.FindWindowById(self.expParamsInGUI['NormalizeAbs'][0])
            
            if absChkBox.GetValue() == True:
            
                if self.expParams['WaterFile'] == None or self.expParams['EmptyFile'] == None:
                    absChkBox.SetValue(False)
                    wx.MessageBox('Please enter an Empty cell sample file and a Water sample file under advanced options.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)
                else:
                    pass
                    #normM1box.SetValue(False)
                    #normM2box.SetValue(False)
                    #normTimebox.SetValue(False)
                    #normTransbox.SetValue(False)
                    
                    #normTransbox.Enable(False)
                    #normTimebox.Enable(False)
                    
            else:
                normTransbox.Enable(True)
                normTimebox.Enable(True)
                
        #################################################
        #### IF AgBe Calibration Checkbox is pressed:
        #################################################
        
        if chkboxID == self.expParamsInGUI['Calibrate'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['Calibrate'][0])
#            wavelength  = self.expParams['WaveLength']
#            pixelsize   = self.expParams['DetectorPixelSize']
            
            wavelength = float(wx.FindWindowById(self.expParamsInGUI['WaveLength'][0]).GetValue().replace(',','.'))
            pixelsize   = float(wx.FindWindowById(self.expParamsInGUI['DetectorPixelSize'][0]).GetValue().replace(',','.'))          
            
            if wavelength != 0 and pixelsize != 0:
                pass
            else:
                calibChkBox.SetValue(False)
                wx.MessageBox('Please enter a valid Wavelength and Detector Pixelsize in advanced options.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)                
        
        if chkboxID == self.expParamsInGUI['CalibrateMan'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['CalibrateMan'][0])
            
            try:
                wavelength  = float(wx.FindWindowById(self.expParamsInGUI['WaveLength'][0]).GetValue().replace(',','.'))
                pixelsize   = float(wx.FindWindowById(self.expParamsInGUI['DetectorPixelSize'][0]).GetValue().replace(',','.'))          
                smpDist     = float(wx.FindWindowById(self.expParamsInGUI['SampleDistance'][0]).GetValue().replace(',','.'))
            except:
                wavelength = 0
                pixelsize = 0
                smpDist = 0
        
            if wavelength != 0 and pixelsize != 0 and smpDist !=0:
                pass
            else:
                calibChkBox.SetValue(False)
                wx.MessageBox('Please enter a valid Wavelength, Detector Pixelsize and Sample-Detector\n' +
                              'distance in advanced options/calibration.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)                    
    
class SaveDirectoriesPage(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        
        expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
                                                                               #Set button id , clr button id
        self.directoryData = (('Reduced files:', expParamsInGUI['ReducedFilePath'], wx.NewId(), wx.NewId()),
                              (None, None, None, None))
        
        self.autoSaveData = (('Save Processed Image Files Automatically', expParamsInGUI['AutoSaveOnImageFiles'][0]),
                             ('Save Averaged Data Files Automatically', expParamsInGUI['AutoSaveOnAvgFiles'][0]))
        
        dirSizer = self.createDirectoryOptions()
        
        topSizer = wx.BoxSizer(wx.VERTICAL)
        
        autosaveSizer = self.createAutoSaveOptions()
        
        topSizer.Add(autosaveSizer, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)
        topSizer.Add(dirSizer, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(topSizer)
        
    def createAutoSaveOptions(self):
        expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
        
        box = wx.StaticBox(self, -1, 'Auto Save')
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        for label, id in self.autoSaveData:
            chkbox = wx.CheckBox(self, id, label)
            chkboxSizer.Add(chkbox, 1, wx.EXPAND | wx.ALL, 5)
        
        return chkboxSizer
        
    def createDirectoryOptions(self):
        
        box = wx.StaticBox(self, -1, 'Save Directories')
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        hSizer = wx.FlexGridSizer(cols = 4, rows = 1, vgap = 3, hgap = 3)
        
        for labtxt, param, setButton_ID, clrButton_ID in self.directoryData:
            
            if labtxt != None:
            
                labl_ID = param[0]
            
                setButton = wx.Button(self, setButton_ID, 'Set..', size = (45,22))
                setButton.Bind(wx.EVT_BUTTON, self.onSetFile)
                clrButton = wx.Button(self, clrButton_ID, 'C', size = (25,22))
                clrButton.Bind(wx.EVT_BUTTON, self.onClrFile)
    
                label = wx.StaticText(self, -1, labtxt)

                filenameLabel = wx.TextCtrl(self, labl_ID, '')
                filenameLabel.SetEditable(False)
                            
                hSizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
                hSizer.Add(filenameLabel, 1, wx.EXPAND)
                hSizer.Add(setButton, 1)
                hSizer.Add(clrButton, 1)
        
        hSizer.AddGrowableCol(1)
        chkboxSizer.Add(hSizer, 1, wx.EXPAND | wx.ALL, 5)
        return chkboxSizer
    
    def onSetFile(self, event):    
        
        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID
        
        dirdlg = wx.DirDialog(self.GetParent(), "Please select directory:", '')
        
        if dirdlg.ShowModal() == wx.ID_OK:                
            selectedPath = dirdlg.GetPath()
        
            for labtxt, param, setButton_ID, clrButton_ID in self.directoryData:
                if setButton_ID == ID:
                        textCtrl = wx.FindWindowById(param[0]) 
                        textCtrl.SetValue(str(selectedPath))        

    def onClrFile(self, event):
        
        buttonObj = event.GetEventObject()
        ID = buttonObj.GetId()            # Button ID
        
        for labtxt, param, setButton_ID, clrButton_ID in self.directoryData:
                if clrButton_ID == ID:
                    textCtrl = wx.FindWindowById(param[0]) 
                    textCtrl.SetValue('')
        
class IFTOptionsPage(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        
        expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
        
        self.biftOptionsData = (("Dmax Upper Bound: ",   expParamsInGUI['maxDmax'][0]),
                                ("Dmax Lower Bound: ",   expParamsInGUI['minDmax'][0]),
                                ("Dmax Search Points: ", expParamsInGUI['DmaxPoints'][0]),
                                ("Alpha Upper Bound:",   expParamsInGUI['maxAlpha'][0]),
                                ("Alpha Lower Bound:",   expParamsInGUI['minAlpha'][0]),
                                ("Alpha Search Points:", expParamsInGUI['AlphaPoints'][0]),
                                ("P(r) Points:",         expParamsInGUI['PrPoints'][0]))
                                
        self.gnomOptionsData = (("Alpha Upper Bound:",   expParamsInGUI['gnomMaxAlpha'][0]),
                                ("Alpha Lower Bound:",   expParamsInGUI['gnomMinAlpha'][0]),
                                ("Alpha Search Points:", expParamsInGUI['gnomAlphaPoints'][0]),
                                ("P(r) Points:",         expParamsInGUI['gnomPrPoints'][0]),
                                ("OSCILL weight:",       expParamsInGUI['OSCILLweight'][0]),
                                ("VALCEN weight:",       expParamsInGUI['VALCENweight'][0]),
                                ("POSITV weight:",       expParamsInGUI['POSITVweight'][0]),
                                ("SYSDEV weight:",       expParamsInGUI['SYSDEVweight'][0]),
                                ("STABIL weight:",       expParamsInGUI['STABILweight'][0]),
                                ("DISCRP weight:",       expParamsInGUI['DISCRPweight'][0]))
        
        self.gnomChkBoxData = (("Force P(r=0) to zero:", expParamsInGUI['gnomFixInitZero'][0]), [])
                
        
        
        
        
        box = wx.StaticBox(self, -1, 'BIFT Grid-Search Parameters')
        biftOptionsSizer = self.createBiftOptions()
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkboxSizer.Add(biftOptionsSizer, 1, wx.EXPAND | wx.ALL, 5)
        
        box2 = wx.StaticBox(self, -1, 'GNOM Parameters')
        gnomOptionsSizer = self.createGnomOptions()
        chkboxSizer2 = wx.StaticBoxSizer(box2, wx.VERTICAL)
        chkboxSizer2.Add(gnomOptionsSizer, 1, wx.EXPAND | wx.ALL, 5)
        
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(chkboxSizer, 0, wx.EXPAND | wx.ALL, 5)
        topSizer.Add(chkboxSizer2, 1, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(topSizer)
        
    def createGnomOptions(self):
        
        noOfRows = ceil(int(len(self.gnomOptionsData)) + int(len(self.gnomChkBoxData)))/2.
        gridSizer = wx.FlexGridSizer(cols = 4, rows = noOfRows, vgap = 5, hgap = 5)
    
        for each in self.gnomOptionsData:
            label = each[0]
            id = each[1]
            
            labeltxt = wx.StaticText(self, -1, label)
            ctrl = wx.TextCtrl(self, id, '0', size = (60, 21), style = wx.TE_RIGHT)
            
            gridSizer.Add(labeltxt, 1, wx.CENTER)
            gridSizer.Add(ctrl, 1)
        
        for each in self.gnomChkBoxData:
            if each != []:
                label = each[0]
                id = each[1]
            
                chkbox = wx.CheckBox(self, id)
                labeltxt = wx.StaticText(self, -1, label)
                gridSizer.Add(labeltxt, 1, wx.TOP, 3)
                gridSizer.Add(chkbox, 1)
            
        return gridSizer    
        
    def createBiftOptions(self):
        
        noOfRows = ceil(int(len(self.biftOptionsData))/2.0)
        gridSizer = wx.FlexGridSizer(cols = 4, rows = noOfRows, vgap = 5, hgap = 5)
    
        for each in self.biftOptionsData:
            label = each[0]
            id = each[1]
            
            labeltxt = wx.StaticText(self, -1, str(label))
            ctrl = wx.TextCtrl(self, id, '0', size = (60, 21), style = wx.TE_RIGHT)
            
            gridSizer.Add(labeltxt, 1)
            gridSizer.Add(ctrl, 1)
            
        return gridSizer    



class ImageFormatOptionsPage(wx.Panel):
    
    def __init__(self, parent):
        
        wx.Panel.__init__(self, parent)
        self.expParamsInGUI = wx.FindWindowByName('OptionsDialog').expParamsInGUI
        
        self.formatChoiceList = ['Quantum 210, CHESS', 'Quantum 1, CHESS', 'MarCCD 165, MaxLab', 'Medoptics, CHESS', 'FLICAM, CHESS']

        self.expsettingsdata = (("X center:", self.expParamsInGUI['Xcenter'][0]),
                                ("Y center:", self.expParamsInGUI['Ycenter'][0]))

        self.expsettings_spin = (("Binning Size:", (self.expParamsInGUI['Binsize'][0], wx.NewId())),
                                 ("Q-Low (pixels):", (self.expParamsInGUI['QrangeLow'][0], wx.NewId())),
                                 ("Q-High (pixels):", (self.expParamsInGUI['QrangeHigh'][0], wx.NewId())))
        
        self.treatmentdata = (("Normalize by Monitor 2", self.expParamsInGUI['NormalizeM2'][0]),
                              ("Normalize by Monitor 1", self.expParamsInGUI['NormalizeM1'][0]),
                              ("Normalize by M2/M1 Factor", self.expParamsInGUI['NormalizeTrans'][0]),
                              ("Normalize by Exposure Time", self.expParamsInGUI['NormalizeTime'][0]))

        self.treatmentdataTxtCtrl = (("Offset by Constant:", self.expParamsInGUI['CurveOffsetVal'][0], self.expParamsInGUI['OffsetCurve'][0]),
                                     ("Scale by Constant:", self.expParamsInGUI['CurveScaleVal'][0], self.expParamsInGUI['ScaleCurve'][0]))

        

        box = wx.StaticBox(self, -1, 'Image Format')
        fileSizer = self.createFormatsComboBox()
        chkboxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        chkboxSizer.Add(fileSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        
        box = wx.StaticBox(self, -1, '2D Reduction Parameters')
        reductionSizer = self.Create2DReductionParameters()
        staticBoxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        staticBoxSizer.Add(reductionSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        
        box = wx.StaticBox(self, -1, 'Normalization')
        normalizationSizer = self.CreateTreatmentData()
        normBoxSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        normBoxSizer.Add(normalizationSizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        panelsizer.Add(chkboxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(staticBoxSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        panelsizer.Add(normBoxSizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        
        self.SetSizer(panelsizer)

    def createFormatsComboBox(self):
        
        sizer = wx.BoxSizer()
        
        id = self.expParamsInGUI['ImageFormat'][0]
        
        combobox = wx.ComboBox(self, id, choices = self.formatChoiceList, style=wx.CB_READONLY)
        combobox.Bind(wx.EVT_COMBOBOX, self.OnSelect)

        sizer.Add(combobox, 1, wx.EXPAND)
        
        return sizer
    
    def OnSelect(self, event):
        item = event.GetString()
        
    def Create2DReductionParameters(self):
        
        staticBoxSizer = wx.BoxSizer(wx.VERTICAL)
        
        for eachText, id in self.expsettingsdata:
            txt = wx.StaticText(self, -1, eachText)
            
            if id == self.expParamsInGUI['Xcenter'][0] or id == self.expParamsInGUI['Ycenter'][0]:
                ctrl = FloatSpinCtrl(self, id)
            else:    
                ctrl = IntSpinCtrl(self, id, min = 0)
                
            ctrl.Bind(EVT_MY_SPIN, self.OnTxtCtrlChange)
            
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(txt, 1, wx.EXPAND)
            sizer.Add(ctrl, 0)
            
            staticBoxSizer.Add(sizer, 1, wx.EXPAND)
        
        for eachEntry in self.expsettings_spin:
            
            label = wx.StaticText(self, -1, eachEntry[0])
            
            spinSizer = wx.BoxSizer(wx.HORIZONTAL)
            spinSizer.Add(label, 1, wx.EXPAND)
            
            for eachSpinCtrl in eachEntry[1:]:
                txtctrl_id = eachSpinCtrl[0]
                spin_id = eachSpinCtrl[1]
                      
                txtCtrl = IntSpinCtrl(self, txtctrl_id)
                txtCtrl.Bind(EVT_MY_SPIN, self.OnTxtCtrlChange)
                
                spinSizer.Add(txtCtrl, 0)
        
            staticBoxSizer.Add(spinSizer, 1, wx.EXPAND)   
        
        return staticBoxSizer 
    
    #panelsizer.Add(staticBoxSizer, 0.1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
    def OnTxtCtrlChange(self, evt):
        pass
        #self.GetParent()._UpdateToExpParams()
    
    def OnChkBox(self, event):
        
        chkboxID = event.GetId()
        self._CorrectConflictingSettings(chkboxID)
        optDialog = wx.FindWindowByName('OptionsDialog')
        optDialog._UpdateToExpParams()
    
    def CreateTreatmentData(self):
                
        #staticBoxSizer = wx.BoxSizer(wx.VERTICAL)
        
        treatmentSizer = wx.BoxSizer(wx.VERTICAL)
        
        for txt, id in self.treatmentdata:
            chkBox = wx.CheckBox(self, id, txt)
            chkBox.Bind(wx.EVT_CHECKBOX, self.OnChkBox)
            treatmentSizer.Add(chkBox, 1, wx.EXPAND)
        
        #staticBoxSizer.Add(treatmentSizer, 0, wx.BOTTOM | wx.LEFT, 5)
        
        noOfRows = int(len(self.treatmentdataTxtCtrl))
        hSizer = wx.FlexGridSizer(cols = 2, rows = noOfRows, vgap = 1, hgap = 3)
        
        for each in self.treatmentdataTxtCtrl:
            
            if each:
                eachLabel = each[0]
                id = each[1]
                id2 = each[2]
        
                ctrl = wx.TextCtrl(self, id, '0', style = wx.TE_PROCESS_ENTER | wx.TE_RIGHT, size = (60, 21))
    
                chkBox = wx.CheckBox(self, id2, eachLabel)
                chkBox.Bind(wx.EVT_CHECKBOX, self.OnChkBox)
    
                hSizer.Add(chkBox, 1, wx.EXPAND)
                hSizer.Add(ctrl, 1, wx.EXPAND)
            
        treatmentSizer.Add(hSizer, 0)
        
        
        #panelsizer.Add(staticBoxSizer, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        return treatmentSizer
    
    def _CorrectConflictingSettings(self, chkboxID):
    
        norm1ID = self.expParamsInGUI['NormalizeM1'][0]
        norm2ID = self.expParamsInGUI['NormalizeM2'][0]
        norm3ID = self.expParamsInGUI['NormalizeTime'][0]
        norm4ID = self.expParamsInGUI['NormalizeTrans'][0]
        
        normM1box = wx.FindWindowById(norm1ID)
        normM2box = wx.FindWindowById(norm2ID)
        normTimebox = wx.FindWindowById(norm3ID)
        normTransbox = wx.FindWindowById(norm4ID)
        
        if chkboxID == self.expParamsInGUI['CalibrateMan'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['Calibrate'][0])
            calibChkBox.SetValue(False)
        elif chkboxID == self.expParamsInGUI['Calibrate'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['CalibrateMan'][0])
            calibChkBox.SetValue(False)
            
        #################################################
        #### IF Absolute Calibration Checkbox is pressed:
        #################################################
        
        if chkboxID == self.expParamsInGUI['NormalizeAbs'][0]:
            absChkBox = wx.FindWindowById(self.expParamsInGUI['NormalizeAbs'][0])
            
            if absChkBox.GetValue() == True:
            
                if self.expParams['WaterFile'] == None or self.expParams['EmptyFile'] == None:
                    absChkBox.SetValue(False)
                    wx.MessageBox('Please enter an Empty cell sample file and a Water sample file under advanced options.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)
                else:
                    pass
                    #normM1box.SetValue(False)
                    #normM2box.SetValue(False)
                    #normTimebox.SetValue(False)
                    #normTransbox.SetValue(False)
                    
                    #normTransbox.Enable(False)
                    #normTimebox.Enable(False)
                    
            else:
                normTransbox.Enable(True)
                normTimebox.Enable(True)
                
        #################################################
        #### IF AgBe Calibration Checkbox is pressed:
        #################################################
                
        if chkboxID == self.expParamsInGUI['Calibrate'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['Calibrate'][0])
            wavelength  = self.expParams['WaveLength']
            pixelsize   = self.expParams['DetectorPixelSize']
            
            if wavelength != 0 and pixelsize != 0:
                pass
            else:
                calibChkBox.SetValue(False)
                wx.MessageBox('Please enter a valid Wavelength and Detector Pixelsize in advanced options.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)                
        
        if chkboxID == self.expParamsInGUI['CalibrateMan'][0]:
            calibChkBox = wx.FindWindowById(self.expParamsInGUI['CalibrateMan'][0])
            wavelength  = self.expParams['WaveLength']
            pixelsize   = self.expParams['DetectorPixelSize']            
            smpDist     = self.expParams['SampleDistance']
        
            if wavelength != 0 and pixelsize != 0 and smpDist !=0:
                pass
            else:
                calibChkBox.SetValue(False)
                wx.MessageBox('Please enter a valid Wavelength, Detector Pixelsize and Sample-Detector\n' +
                              'distance in advanced options/calibration.', 'Attention!', wx.OK | wx.ICON_EXCLAMATION)
        
class OptionsDialog(wx.Dialog):
    
    def __init__(self, parent, expParams, focusIndex = None):
      
        wx.Dialog.__init__(self, parent, -1, 'Advanced Options', size=(400,450), name = 'OptionsDialog')

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        #######################################################################
        self.expParams = expParams
        
        self.expParamsInGUI = {'WaterFile'       : (wx.NewId(), 'calibFilename'),
                               'EmptyFile'       : (wx.NewId(), 'calibFilename'),
                               'WaveLength'      : (wx.NewId(), 'float'),
                               'SampleDistance'  : (wx.NewId(), 'float'),
                               'DetectorPixelSize'  : (wx.NewId(), 'float'),
                               'SmpDetectOffsetDist': (wx.NewId(), 'float'),
                               
                               #NORMALIZATION
                              # 'NormalizeConst'    : (wx.NewId(), 'float'),
                              # 'NormalizeConstChk' : (wx.NewId(), 'bool'),
                               'NormalizeM2'  : (wx.NewId(), 'bool'),
                               'NormalizeM1'  : (wx.NewId(), 'bool'),
                               
                               'NormalizeTime': (wx.NewId(), 'bool'),
                               'NormalizeTrans':(wx.NewId(), 'bool'),
                                                              
                               #CALIBRATION
                               'NormalizeAbs' : (wx.NewId(), 'bool'),
                               'Calibrate'    : (wx.NewId(), 'bool'),
                               'CalibrateMan' : (wx.NewId(), 'bool'),
                               
                               'WaterAvgMinPoint' : (wx.NewId(), 'int'),
                               'WaterAvgMaxPoint' : (wx.NewId(), 'int'),
                               
                               #AUTOMATION
                               'AutoBgSubtract'  : (wx.NewId(), 'bool'),
                               'AutoBIFT'        : (wx.NewId(), 'bool'),
                               'BgPatternType'   : (wx.NewId(), 'text'),
                               'BgPatternValue'  : (wx.NewId(), 'text'),
                                                          
                               #BIFT PARAMETERS:
                               'maxDmax'     : (wx.NewId(), 'float'),
                               'minDmax'     : (wx.NewId(), 'float'),
                               'DmaxPoints'  : (wx.NewId(), 'int'),
                               'maxAlpha'    : (wx.NewId(), 'float'),
                               'minAlpha'    : (wx.NewId(), 'float'),
                               'AlphaPoints' : (wx.NewId(), 'int'),
                               'PrPoints'    : (wx.NewId(), 'int'),
                               
                                #GNOM PARAMETERS:
                               'gnomMaxAlpha'    : (wx.NewId(), 'float'),
                               'gnomMinAlpha'    : (wx.NewId(), 'float'),
                               'gnomPrPoints'    : (wx.NewId(), 'int'),
                               'gnomFixInitZero' : (wx.NewId(), 'bool'),
                               'gnomAlphaPoints' : (wx.NewId(), 'int'),
                               
                               'OSCILLweight'    : (wx.NewId(), 'float'),
                               'VALCENweight'    : (wx.NewId(), 'float'),
                               'POSITVweight'    : (wx.NewId(), 'float'),
                               'SYSDEVweight'    : (wx.NewId(), 'float'),
                               'STABILweight'    : (wx.NewId(), 'float'),
                               'DISCRPweight'    : (wx.NewId(), 'float'),
                               
                               #ARTIFACT REMOVAL:
                               'ZingerRemoval'        : (wx.NewId(), 'bool'),
                               'ZingerRemoveSTD'      : (wx.NewId(), 'int'),
                               'ZingerRemoveWinLen'   : (wx.NewId(), 'int'),
                               'ZingerRemoveIdx'      : (wx.NewId(), 'int'),
                               'ZingerRemovalAvgStd'  : (wx.NewId(), 'int'),
                               'ZingerRemovalAvg'     : (wx.NewId(), 'bool'),
                               
                               #SAVE DIRECTORIES
                             #  'ReducedFilePath'      : (wx.NewId(), 'text'),
                             #  'AutoSaveOnImageFiles' : (wx.NewId(), 'bool'),
                             #  'AutoSaveOnAvgFiles'   : (wx.NewId(), 'bool'),
                               
                               #MASKING
                               'BeamStopMaskFilename' :   (wx.NewId(), 'maskFilename'),
                               'ReadOutNoiseMaskFilename':(wx.NewId(), 'maskFilename'),
                  
                               #ImageFormat
                               'ImageFormat'          : (wx.NewId(), 'list'),
                               
                               #2D reduction parameters
                               'Xcenter'      : (wx.NewId(), 'float'),
                               'Ycenter'      : (wx.NewId(), 'float'),
                               'Binsize'      : (wx.NewId(), 'int'),
                               'QrangeLow'    : (wx.NewId(), 'int'),
                               'QrangeHigh'   : (wx.NewId(), 'int'),
                  
                               'PixelCalX'    : (wx.NewId(), 'int'),
                               
                               'CurveOffsetVal': (wx.NewId(), 'float'),
                               'OffsetCurve'   : (wx.NewId(), 'bool'),
                               'CurveScaleVal' : (wx.NewId(), 'float'),
                               'ScaleCurve'    : (wx.NewId(), 'bool')
                               
                               }
        
        #######################################################################
        
        optionsNB = wx.Notebook(self)

        self.page1 = GeneralOptionsPage(optionsNB)
        self.page2 = IFTOptionsPage(optionsNB)
        self.page3 = CalibrationOptionsPage(optionsNB)
        self.page4 = MaskingOptions(optionsNB)
        self.page5 = ImageFormatOptionsPage(optionsNB)
        #self.page6 = SaveDirectoriesPage(optionsNB)

        
        optionsNB.AddPage(self.page1, "General")
        optionsNB.AddPage(self.page3, "Calibration")
        optionsNB.AddPage(self.page4, "Masking")
        optionsNB.AddPage(self.page2, "IFT")
        optionsNB.AddPage(self.page5, "2D reduction")
        #optionsNB.AddPage(self.page6, "Directories")
        

        buttonSizer = self.createButtons()

        nbsizer = wx.BoxSizer(wx.VERTICAL)
        nbsizer.Add(optionsNB, 1, wx.EXPAND)
        nbsizer.Add(buttonSizer, 0, wx.EXPAND | wx.BOTTOM, 3)
        
        self.SetSizer(nbsizer)
        
        self._UpdateFromExpParams()
        
        if focusIndex != None:
            optionsNB.SetSelection(focusIndex)
        
        self.Fit()
        self.CenterOnScreen()
            
    def getValueFromExpParams(self, key):
        return self.expParams[key]
        
    def createButtons(self):
        
        #saveButton = wx.Button(self, -1, "Save")
        #loadButton = wx.Button(self, -1, "Load")
        okButton = wx.Button(self, -1, "OK")
        cancelButton = wx.Button(self, -1, "Cancel")
        
        buttonSizer = wx.BoxSizer()
        buttonSizer.Add((3,3),1)
        #buttonSizer.Add(saveButton, 0)
        #buttonSizer.Add(loadButton, 0)
        buttonSizer.Add(okButton, 0)
        buttonSizer.Add(cancelButton, 0)
        buttonSizer.Add((3,3),1)
        
        okButton.Bind(wx.EVT_BUTTON, self.onOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)
    
        return buttonSizer
    
    def _CreateFileDialog(self, mode):
        
        file = None

        #if file = imagefile.. then save old setttings, set norm by transmission setting.. 
        #and load file then return old settings
                
        if mode == wx.OPEN:
            filters = 'Rad Files (*.rad)|*.rad|All Files (*.*)|*.*'
            dialog = wx.FileDialog( None, style = mode, wildcard = filters)
        if mode == wx.SAVE:
            filters = 'Config files (*.cfg)|*.cfg'
            dialog = wx.FileDialog( None, style = mode | wx.OVERWRITE_PROMPT, wildcard = filters)        
        
        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            
        # Destroy the dialog
        dialog.Destroy()
        
        return file
    
    def _UpdateToExpParams(self):
        ''' WHAT A MESS! '''
        
        for eachKey in self.expParamsInGUI:
            
            id = self.expParamsInGUI.get(eachKey)[0]
            type = self.expParamsInGUI.get(eachKey)[1]
            value = wx.FindWindowById(id).GetValue()
                
            if type == 'list':
                self.expParams[eachKey] = value
            
            if type == 'bool':
                self.expParams[eachKey] = value
                
            elif type == 'text':
                self.expParams[eachKey] = value
            
            ########################### Calibration files ##################################
            elif type == 'calibFilename':
                if value != 'None':
                    
                        if self.expParams[eachKey] != None:
                        
                            if value != self.expParams[eachKey].param['filename']:

                                ExpObj, FullImage = fileIO.loadFile(value, self.expParams)

                                if ExpObj.i != []: 
                                    
                                    if ExpObj.filetype == 'image': 
                                        treatments = ['NormalizeTrans', 'NormalizeTime']
                                        checkedTreatments = wx.FindWindowByName('OptionsPage').getCheckedDataTreatments()
                                    
                                        #If calibration is checked, use calibration info from options page
                                        for each in checkedTreatments:
                                            if each == 'Calibrate':
                                                treatments.append('Calibrate')
                                            elif each == 'CalibrateMan':
                                                treatments.append('CalibrateMan')                     
                                
                                        cartToPol.applyDataManipulations(ExpObj, self.expParams, treatments)
                                    
                                    self.expParams[eachKey] = ExpObj
                                else:
                                    wx.MessageBox(str(value) + ' is not a valid file!\nFile not loaded', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                                    
                        else:
                            ExpObj, FullImage = fileIO.loadFile(value, self.expParams)
                            
                            ## NB! WHat a FuckED UP case!! if I do ExpObj.i == [] .. I get False even if its []
                            ## if i use ExpObj.i != [] .. it works! WHAT THE FUCK!!!!!????  
                            if ExpObj.i != []:
                                
                                if ExpObj.filetype == 'image': 
                                    treatments = ['NormalizeTrans']
                                    checkedTreatments = wx.FindWindowByName('OptionsPage').getCheckedDataTreatments()
                                    
                                    for each in checkedTreatments:
                                        if each == 'Calibrate':
                                            treatments.append('Calibrate')
                                        elif each == 'CalibrateMan':
                                            treatments.append('CalibrateMan')                     
                                
                                    cartToPol.applyDataManipulations(ExpObj, self.expParams, treatments)
                                    
                                self.expParams[eachKey] = ExpObj
                            else:
                                wx.MessageBox(str(value) + ' is not a valid file!\nFile not loaded', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                            
                else:
                    self.expParams[eachKey] = None
                
            ################################################################################
            elif type == 'filename':
                print 'File!'
                if value != 'None':

                        if self.expParams[eachKey] != None:
                        
                            if value != self.expParams[eachKey].param['filename']:
                                
                                ExpObj, FullImage = fileIO.loadFile(value, self.expParams)
                                
                                if ExpObj.i != []:   
                                    wx.FindWindowByName('PlotPanel').applyDataManipulations(ExpObj)
                                    self.expParams[eachKey] = ExpObj
                                else:
                                    wx.MessageBox(str(value) + ' is not a valid file!\nFile not loaded', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                                    
                        else:
                            ExpObj, FullImage = fileIO.loadFile(value, self.expParams)
                            
                            ## NB! WHat a FuckED UP case!! if I do ExpObj.i == [] .. I get False even if its []
                            ## if i use ExpObj.i != [] .. it works! WHAT THE FUCK!!!!!????  
                            if ExpObj.i != []:   
                                cartToPol.applyDataManipulations(ExpObj, self.expParams, self.getTreatmentParameters())
                                self.expParams[eachKey] = ExpObj
                            else:
                                wx.MessageBox(str(value) + ' is not a valid file!\nFile not loaded', 'Load Failed!', wx.OK | wx.ICON_ERROR)
                            
                else:
                    self.expParams[eachKey] = None
            
            elif type == 'maskFilename':
                pass
            
            elif type == 'int' or type == 'float':
                
                if type == 'int':
                    self.expParams[eachKey] = int(value.replace(',','.'))
                else:
                    self.expParams[eachKey] = float(value.replace(',','.'))
    
    def _UpdateFromExpParams(self):
        
        for eachKey in self.expParamsInGUI:
            
            id = self.expParamsInGUI.get(eachKey)[0]
            type = self.expParamsInGUI.get(eachKey)[1]
            value = self.expParams.get(eachKey)
            
            if type == 'bool':

                chkbox = wx.FindWindowById(id)
                
                if chkbox != None:            ## DANGEROUS!!! 
                    if value:
                        chkbox.SetValue(True)
                    elif not(value):
                        chkbox.SetValue(False)
                    
            if type == 'int' or type == 'float' or type == 'text':
                ctrl = wx.FindWindowById(id)
                
                if ctrl != None:                ## DANGEROUS!!! 
                    ctrl.SetValue(str(value))
                
                # Set the spin buttons to the value in expparams
                #for each in self.expsettings_spin:
                    
                #    param_id = each[1][0]
                #    spin_id = each[1][1]
                    
                #    if id == param_id:
                #        spinbutton = wx.FindWindowById(spin_id)
                #        spinbutton.SetValue(int(value))     
                        
            if type == 'filename' or type == 'calibFilename':
                ctrl = wx.FindWindowById(id)
                
                if ctrl != None:
                    if value:
                        ctrl.SetValue(value.param['filename'])
                    else:
                        ctrl.SetValue('None')
            
            if type == 'maskFilename':
                ctrl = wx.FindWindowById(id)
                
                if ctrl != None:
                    if value:
                        ctrl.SetValue(value)
                    else:
                        ctrl.SetValue('None')
            
            if type == 'list':
                ctrl = wx.FindWindowById(id)
                print 'value was: ', value
                ctrl.SetStringSelection(value)
                
                
    def onCancel(self, evt):
        self.Destroy()
    
    def OnClose(self, event):
        self.Destroy()
    
    def onOK(self, evt):
        
        invalidEntriesFound = self.SeekInvaildEntries()
        
        if not(invalidEntriesFound):
            self._UpdateToExpParams()
            self.GetParent().ReplaceExpParams(self.expParams)
            self.Destroy()
            
    def SeekInvaildEntries(self):
        
        autobgsubChkbox = wx.FindWindowById(self.expParamsInGUI['AutoBgSubtract'][0])
        patternTxtCtrl = wx.FindWindowById(self.expParamsInGUI['BgPatternValue'][0])
        
        if autobgsubChkbox.GetValue() == True and patternTxtCtrl.GetValue() == '':
            wx.MessageBox('You need to specify a background filename pattern\n to do automatic background subtraction', 'Warning!', wx.OK | wx.ICON_EXCLAMATION)
            return True
        else:
            return False
        
    def getTreatmentParameters(self):
    
        P = []
    
        if self.expParams['NormalizeM2']:
            P.append('NormalizeM2')
        if self.expParams['NormalizeTime']:
            P.append('NormalizeTime')
        if self.expParams['NormalizeM1']:
            P.append('NormalizeM1')
        if self.expParams['Calibrate']:
            P.append('Calibrate')
        
        # For backwards compatibility:
        try:
            if self.expParams['CalibrateMan']:
                P.append('CalibrateMan')
        except KeyError:
            self.expParams['CalibrateMan'] = False
        
        try:
            if self.expParams['NormalizeAbs']:
                P.append('NormalizeAbs')
        except KeyError:
            self.expParams['NormalizeAbs'] = False
       
        return P
    
    
class OptionsTestFrame(wx.Frame):
    ''' Only for testing '''
    
    def __init__(self, title, frame_id):
        wx.Frame.__init__(self, None, frame_id, title)
        
        testExpParams = {
             'NormalizeConst'    : 1.0,
             'NormalizeConstChk' : False,
             'NormalizeM2'       : False,
             'NormalizeTime'     : False,
             'NormalizeM1'       : False, 
             'NormalizeAbs'      : False,
             'NormalizeTrans'    : False,
             'Calibrate'         : False,        # Calibrate AgBe
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
             
             #DEFAULT GNOM PARAMETERS
             'gnomMaxAlpha'    : 60,
             'gnomMinAlpha'    : 0.01,
             'gnomAlphaPoints' : 100,
             'gnomPrPoints'    : 50,
             'gnomFixInitZero' : True,
             
             'OSCILLweight'    : 3.0,
             'VALCENweight'    : 1.0,
             'POSITVweight'    : 1.0,
             'SYSDEVweight'    : 3.0,
             'STABILweight'    : 3.0,
             'DISCRPweight'    : 1.0,
             
             #DEFAULT IFT PARAMETERS:
             'IFTAlgoList'        : ['BIFT', 'GNOM'],
             'IFTAlgoChoice'      : 'BIFT',
             
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
        
        dialog = OptionsDialog(self, testExpParams)
        dialog.ShowModal()
        
    
class MaskingTestApp(wx.App):
    
    def OnInit(self):
        
        frame = OptionsTestFrame('Mask Creator', -1)
        self.SetTopWindow(frame)
        frame.SetSize((1024,768))
        frame.CenterOnScreen()
        frame.Show(True)
        
        return True
    
    
#------------- *** My Custom SpinCtrl's ****

class FloatSpinEvent(wx.PyCommandEvent):
    
    def __init__(self, evtType, id):
        
        wx.PyCommandEvent.__init__(self, evtType, id)
        
        self.value = 0
        
    def GetValue(self):
        return self.value
    
    def SetValue(self, value):
        self.value = value
        
myEVT_MY_SPIN = wx.NewEventType()
EVT_MY_SPIN = wx.PyEventBinder(myEVT_MY_SPIN, 1)

class FloatSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, initValue = None, button_style = wx.SP_VERTICAL, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        if initValue == None:
            initValue = '1.00'
        
        self.defaultScaleDivider = 100
        self.ScaleDivider = 100
        
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = button_style)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999) #Needed for proper function of button on Linux
                
        self.Scale = wx.TextCtrl(self, -1, initValue, size = (40,22), style = wx.TE_PROCESS_ENTER)
        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)
        
        sizer = wx.BoxSizer()
        
        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)
        
        self.oldValue = 0
        
        self.SetSizer(sizer)
                
    def CastFloatSpinEvent(self):
        
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)
        
        #print str(self.ScalerButton.GetValue())
    
    def OnScaleChange(self, event):
        
        val = self.Scale.GetValue()
        
        try:
            num_of_digits = len(val.split('.')[1])
            
            if num_of_digits == 0:
                self.ScaleDivider = self.defaultScaleDivider
            else:
                self.ScaleDivider = power(10, num_of_digits)
        except IndexError:
            self.ScaleDivider = self.defaultScaleDivider
            
        if val != self.oldValue:
            self.oldValue = val
            self.CastFloatSpinEvent()

    def OnSpinUpScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        newval = float(val.replace(',','.')) + (1/self.ScaleDivider)
        self.Scale.SetValue(str(newval))
        
        if newval != self.oldValue:            
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def OnSpinDownScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        newval = float(val.replace(',','.')) - (1/self.ScaleDivider)
        self.Scale.SetValue(str(newval))  
        
        if newval != self.oldValue:
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def GetValue(self): 
        value = self.Scale.GetValue()
        return value
    
    def SetValue(self, value):
        self.Scale.SetValue(value)
        
    
    
class IntSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, min = None, max = None, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = wx.SP_VERTICAL)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999)
        self.max = max
        self.min = min
        
        #if self.min:
            #print "min at: ", str(self.min)
        #    self.ScalerButton.SetMin(self.min)
        #    self.ScalerButton.SetMax(self.max)
        #else:
        #self.ScalerButton.SetMin(-9999)
        #self.ScalerButton.SetMax(99999)
        
        self.Scale = wx.TextCtrl(self, -1, str(min), size = (40,22), style = wx.TE_PROCESS_ENTER)
        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)
        
        sizer = wx.BoxSizer()
        
        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)
        
        self.oldValue = 0
        
        self.SetSizer(sizer)
                
    def CastFloatSpinEvent(self):
        
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)
        
        #print str(self.ScalerButton.GetValue())
    
    def OnScaleChange(self, event):
        
        self.ScalerButton.SetValue(0) # Resit spinbutton position for button to work in linux
        
        #print str(self.ScalerButton.GetValue())
        
        val = self.Scale.GetValue()
                
        if self.max != None:
            if float(val.replace(',','.')) > self.max:
                self.Scale.SetValue(str(self.max))
        if self.min != None:
            if float(val.replace(',','.')) < self.min:
                self.Scale.SetValue(str(self.min))
        
        if val != self.oldValue:
            self.oldValue = val
            self.CastFloatSpinEvent()

    def OnSpinUpScale(self, event):
        #self.ScalerButton.SetValue(80)

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        
        newval = int(val) + 1
        
        if self.max != None:
            if newval > self.max:
                self.Scale.SetValue(str(self.max))
            else:
                self.Scale.SetValue(str(newval))
        else:        
            self.Scale.SetValue(str(newval))
        
        if newval != self.oldValue:            
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def OnSpinDownScale(self, event):
        #self.ScalerButton.SetValue(80)

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        newval = int(val) - 1
        
        if self.min != None:
            if newval < self.min:
                self.Scale.SetValue(str(self.min))
            else:
                self.Scale.SetValue(str(newval))
        else:
            self.Scale.SetValue(str(newval))  
        
        if newval != self.oldValue:
            self.oldValue = newval
            self.CastFloatSpinEvent()
        
    def GetValue(self): 
        value = self.Scale.GetValue()
        return value
    
    def SetValue(self, value):
        self.Scale.SetValue(str(value))
        #print int(value)
        #self.ScalerButton.SetValue(int(str(value)))
        
    def SetRange(self, minmax):
        
        self.max = minmax[1]
        self.min = minmax[0]

class ListSpinCtrl(wx.Panel):
    
    def __init__(self, parent, id, scrollList, minIdx = None, maxIdx = None, **kwargs):
        
        wx.Panel.__init__(self, parent, id, **kwargs)
        
        self.scrollList = scrollList
        self.ScalerButton = wx.SpinButton(self, -1, size = (20,22), style = wx.SP_VERTICAL)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        
        self.Scale = wx.TextCtrl(self, -1, str(scrollList[0]), size = (40,22), style = wx.TE_PROCESS_ENTER)
        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)
        
        sizer = wx.BoxSizer()
        
        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)
   
        self.idx = 0
        
        if maxIdx == None:
            self.maxIdx = len(scrollList)-1
        else:
            self.maxIdx = maxIdx
            
        if minIdx == None:
            self.minIdx = 0
        else:
            self.minIdx = minIdx
        
        self.oldValue = 0
        
        self.SetSizer(sizer)
                
    def CastFloatSpinEvent(self):
        
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)
    
    def OnScaleChange(self, event):
        
        val = self.Scale.GetValue()
        
        if float(val.replace(',','.')) >= self.scrollList[self.maxIdx]:
            self.idx = self.maxIdx
            self.Scale.SetValue(str(self.scrollList[self.idx]))
            self.CastFloatSpinEvent()
            return
        
        if float(val.replace(',','.')) <= self.scrollList[self.minIdx]:
            self.idx = self.minIdx
            self.Scale.SetValue(str(self.scrollList[self.idx]))
            self.CastFloatSpinEvent()
            return
                
        currentmin = self.scrollList[0]
        currentidx = 0
        changed = False
        for i in range(0,len(self.scrollList)):
            chk = abs(self.scrollList[i]-float(val.replace(',','.')))
            
            if chk < currentmin:
                currentmin = chk
                currentidx = i
                changed = True
        
        if changed == True:
            self.idx = currentidx
            self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        self.CastFloatSpinEvent()
                
#        if self.max != None:
#            if float(val) > self.max:
#                self.Scale.SetValue(str(self.max))
#        if self.min != None:
#            if float(val) < self.min:
#                self.Scale.SetValue(str(self.min))
#        
#        if val != self.oldValue:
#            self.oldValue = val

    def OnSpinUpScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        val = self.Scale.GetValue()
        
        self.idx = self.idx + 1
        
        if self.idx > self.maxIdx:
            self.idx = self.maxIdx
            
        self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        self.CastFloatSpinEvent()
        
    def OnSpinDownScale(self, event):

        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update
        
        self.idx = self.idx - 1
        
        if self.idx < self.minIdx:
            self.idx = self.minIdx
        
        self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        self.CastFloatSpinEvent()
        
    def GetValue(self): 
        value = self.Scale.GetValue()
        return value
    
    def SetValue(self, value):
        self.Scale.SetValue(str(value))
        
    def SetRange(self, minmax):
        self.max = minmax[1]
        self.min = minmax[0]
    
    def SetIdx(self, idx):
        self.idx = idx
        self.Scale.SetValue(str(self.scrollList[self.idx]))
    
    def GetIdx(self):
        return self.idx
        
    def SetList(self, scrollList):
        self.idx = 0
        self.scrollList = scrollList
        self.maxIdx = len(scrollList)-1
        self.minIdx = 0
        self.Scale.SetValue(str(self.scrollList[self.idx]))
        
        
        
#---- Mask loading


        
    
        
if __name__ == "__main__":
    app = MaskingTestApp(0)   #MyApp(redirect = True)
    app.MainLoop()
