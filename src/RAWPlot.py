import wx, os, sys, math, numpy, RAWCustomCtrl
import matplotlib
matplotlib.rcParams['backend'] = 'WxAgg'

from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backends.backend_wx import FigureCanvasBase
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backend_bases import cursors
from matplotlib.widgets import Cursor
from matplotlib.font_manager import FontProperties

RAWWorkDir = sys.path[0]

if os.path.split(sys.path[0])[1] in ['RAW.exe', 'raw.exe']:
    RAWWorkDir = os.path.split(sys.path[0])[0]

class MyFigureCanvasWxAgg(FigureCanvasWxAgg):
    
    def __init__(self, *args, **kwargs):
        FigureCanvasWxAgg.__init__(self, *args, **kwargs)   
        
    def _onMotion(self, evt):
        """Start measuring on an axis."""

        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()
        evt.Skip()
        
        try:
            FigureCanvasBase.motion_notify_event(self, x, y, guiEvent=evt)
        except:
            print 'Log fail! Switch to Lin-Lin plot in the menu'
            plotpanel = wx.FindWindowByName('PlotPanel')
            
            i=0
            for a in self.figure.get_axes():
               i = i + 1
               if a.get_yscale() == 'log':
                   a.set_yscale('linear')
                   a.set_xscale('linear')
                   
                   plotpanel.setParameter('axesscale' + str(i), 'linlin')
                   
                   wx.MessageBox('Data contains too many illegal/negative values for a log plot', 'Error!' )
                   
            
            try:
                self.draw()
            except ValueError, e:
                print 'MyFigureCanvasWxAgg: ' + str(e)
                    
            plotpanel.fitAxis()
               
               
            
    def _onLeftButtonUp(self, evt):
        """End measuring on an axis."""
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()
        #print 'release button', 1
        evt.Skip()
        if self.HasCapture(): self.ReleaseMouse()
        try:
            FigureCanvasBase.button_release_event(self, x, y, 1, guiEvent=evt)
        except:
            print 'Log fail! Switch to Lin-Lin plot in the menu'
        

    def _onLeftButtonDown(self, evt):
        """Start measuring on an axis."""
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()
        evt.Skip()
        self.CaptureMouse()
        try:
            FigureCanvasBase.button_press_event(self, x, y, 1, guiEvent=evt)
        except:
            print 'Log fail! Switch to Lin-Lin plot in the menu'

class LegendOptionsDialog(wx.Dialog):
    def __init__(self, parent, plotparams, selected_plot, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, 'Legend Options' , *args, **kwargs)
        
        self.plotparams = plotparams
        self.selected_plot = selected_plot
        
        choices = ['5','6','7','8','9','10','11','12','13','14','15','16',
                   '17', '18','19', '20', '21', '22', '23', '24', '25',
                   '26', '27', '28', '29', '30']
         
        self.font_size_choice = wx.Choice(self, -1, choices = choices)
        
        old_font_size = plotparams['legend_fontsize' +  str(selected_plot)]
        old_alpha_val = plotparams['legend_alpha' +  str(selected_plot)]
        
        self.font_size_choice.Select(choices.index(str(old_font_size)))
        
        self.border_chkbox = wx.CheckBox(self, -1, 'Border')
        font_size_text = wx.StaticText(self, -1, 'Font size : ')
        alpha_text = wx.StaticText(self, -1, 'Transparency (0.0 - 1.0) : ')
        
        self.alpha_val = RAWCustomCtrl.FloatSpinCtrl(self, -1, str(old_alpha_val), never_negative = True)
        
        alpha_sizer = wx.BoxSizer(wx.HORIZONTAL)
        alpha_sizer.Add(alpha_text, 0, wx.ALIGN_CENTER_VERTICAL)
        alpha_sizer.Add(self.alpha_val, 0)
        
        
        borderchk = plotparams['legend_border' +  str(selected_plot)]
        
        self.border_chkbox.SetValue(borderchk)
       
        fontsizer = wx.BoxSizer()
        fontsizer.Add(font_size_text, 0, wx.ALIGN_CENTER_VERTICAL)
        fontsizer.Add(self.font_size_choice, 0)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(fontsizer, 0)
        sizer.Add(alpha_sizer, 0, wx.TOP, 10)
        
        sizer.Add(self.border_chkbox, 0, wx.TOP | wx.BOTTOM, 10)
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        
        self.Bind(wx.EVT_BUTTON, self._onOk, id = wx.ID_OK)
        
        sizer.Add(buttons, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        
        top_sizer = wx.BoxSizer()
        
        top_sizer.Add(sizer,1, wx.ALL, 10)
        
        self.SetSizer(top_sizer)
        self.Fit()
        self.CenterOnParent()
    
    def _onOk(self, event):        
        self.plotparams['legend_border' +  str(self.selected_plot)] = self.border_chkbox.GetValue()
        
        fontsize = int(self.font_size_choice.GetStringSelection())
        self.plotparams['legend_fontsize' +  str(self.selected_plot)] = int(fontsize)

        alpha = self.alpha_val.GetValue()
        self.plotparams['legend_alpha' +  str(self.selected_plot)] = float(alpha)
        

        self.EndModal(wx.OK)
        
class PlotOptionsDialog(wx.Dialog):
    def __init__(self, parent, plotparams, axes, *args, **kwargs):
        
        wx.Dialog.__init__(self, parent, -1, 'Plot Options' , *args, **kwargs)
        
        self.axes = axes
        self.plotparams = plotparams
        self.parent = parent
                
        sizer = wx.BoxSizer(wx.VERTICAL)
        
      
        self.legend = axes.get_legend()
        
        self._old_xlimit = self.axes.xaxis.get_data_interval()
        self._old_ylimit = self.axes.yaxis.get_data_interval()
        
        
        #If people are still running old matplotlib:
        if self.legend == None:
            self._old_legend_settings = {'size'   :0,
                                         'alpha'  : 0,
                                         'border' : False,
                                         'shadow' : False}
        else:
            try:
                frame_on = self.legend.get_frame_on()
            except Exception, e:
                w = self.legend.get_linewidth()
                
                if w == 0:
                    frame_on = True
                else:
                    frame_on = False
            
            self._old_legend_settings = {'size'   : self.legend.get_texts()[0].get_size(),
                                         'alpha'  : self.legend.get_frame().get_alpha(),
                                         'border' : frame_on,
                                         'shadow' : self.legend.shadow}
        
        self._old_settings = {'title' : {},
                             'xlabel' : {},
                             'ylabel' : {},
                             'legtit' : {}}
        
        font_list_with_path = matplotlib.font_manager.findSystemFonts()
        
        self.font_list = []
        
        for each in font_list_with_path:
            dir, file = os.path.split(each)
            self.font_list.append(file)
        
        self.title = self.axes.title
        self.xlabel = self.axes.xaxis.get_label()
        self.ylabel = self.axes.yaxis.get_label()
        
        legax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        legax_sizer.Add(self._createLegendSettings(), 0, wx.EXPAND)
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
        self.Fit()
        self.CenterOnParent()
    
    def _updateLabels(self, event):
        label_params = ['text', 'size', 'weight', 'style']
        obj = event.GetEventObject()
        
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
            
            ctrl = wx.FindWindowById(ids[key])
            val = ctrl.GetValue()
            
            if key == 'weight':
                if val: value = 'bold'
                else: value = 'normal'
                label.set_weight(value)
            elif key == 'style':
                if val: value = 'italic'
                else: value = 'normal'
                label.set_style(value)
            elif key == 'size':
                label.set_size(val)
            elif key == 'text':
                label.set_text(val)
        
        if obj.GetName() == 'legtit':
            self.legend.set_title(label.get_text())
        
        try:
            self.parent.canvas.draw()
        except matplotlib.pyparsing.ParseFatalException, e:
            print e
        
        event.Skip()
        
        
    def _createAxesSettings(self):
        box = wx.StaticBox(self, -1, 'Axes')
        topbox = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer = wx.FlexGridSizer(rows = 6, cols = 2, hgap = 5, vgap = 3)
        
        self.axes_autolimits = wx.CheckBox(self, -1)
        self.axes_autolimits.Bind(wx.EVT_CHECKBOX, self._updateAxesSettings)
        
        val = self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)]
        self.axes_autolimits.SetValue(val)
        
        
        sizer.Add(wx.StaticText(self, -1, 'Auto limits:'), 0, wx.ALIGN_CENTRE_VERTICAL)
        sizer.Add(self.axes_autolimits, 0)
        
        self.axes_fixed_limits_data = [('xmin', wx.NewId(), self._old_xlimit[0]),
                                       ('xmax', wx.NewId(), self._old_xlimit[1]),
                                       ('ymin', wx.NewId(), self._old_ylimit[0]),
                                       ('ymax', wx.NewId(), self._old_ylimit[1])]
        
        limit_sizer = wx.FlexGridSizer(rows = 2, cols = 2, hgap = 5, vgap = 3)
        for i in range(0, len(self.axes_fixed_limits_data)-2):
            id = self.axes_fixed_limits_data[i][1]
            limit_sizer.Add(wx.TextCtrl(self, id, str(self.axes_fixed_limits_data[i][2]), size = (80, -1)), 0)
                  
        limit_sizer2 = wx.FlexGridSizer(rows = 1, cols = 2, hgap = 5, vgap = 3)
        for i in range(2, len(self.axes_fixed_limits_data)):
            id = self.axes_fixed_limits_data[i][1]
            limit_sizer2.Add(wx.TextCtrl(self, id, str(self.axes_fixed_limits_data[i][2]), size = (80, -1)), 0)
                  
        
        maxmin_sizer = wx.BoxSizer()
        maxmin_sizer.Add(wx.StaticText(self, -1, 'min'), 1, wx.EXPAND | wx.ALIGN_CENTRE_HORIZONTAL)
        maxmin_sizer.Add(wx.StaticText(self, -1, 'max'), 1, wx.EXPAND | wx.LEFT, 5)
        
        sizer.Add((5,5))
        sizer.Add(maxmin_sizer, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, -1, 'x-limits'), 0)
        sizer.Add(limit_sizer, 0)
        sizer.Add(wx.StaticText(self, -1, 'y-limits'), 0)
        sizer.Add(limit_sizer2, 0)
        
        border_sizer = wx.FlexGridSizer(rows = 2, cols = 2, hgap = 5, vgap = 3)
        
        self.axes_borders = [('Left', wx.NewId()), ('Right', wx.NewId()), ('Top', wx.NewId()), ('Bottom', wx.NewId())]
        
        for each, id in self.axes_borders:
            border_sizer.Add(wx.CheckBox(self, id, each), 0, wx.RIGHT, 5)
        
        sizer.Add(wx.StaticText(self, -1, 'Borders:'), 0)
        sizer.Add(border_sizer, 0, wx.TOP, 5)
        
        topbox.Add(sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        self._enableLimitsCtrls(not self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)])
        
        return topbox
    
    def _enableLimitsCtrls(self, state):
        
        for each, id, lim in self.axes_fixed_limits_data:
            ctrl = wx.FindWindowById(id)
            ctrl.Enable(state)
            ctrl.Refresh()
    
    def _updateAxesSettings(self, event):
        
        autolimits = self.axes_autolimits.GetValue()
        
        if autolimits:
            self._enableLimitsCtrls(False)
        else:
            self._enableLimitsCtrls(True)
            
        self.parent.plotparams['auto_fitaxes' + str(self.parent.selected_plot)] = autolimits
    
    
    def _createLegendSettings(self):
        
        box = wx.StaticBox(self, -1, 'Legend')
        topbox = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        sizer = wx.FlexGridSizer(rows = 6, cols = 2, hgap = 5, vgap = 3)
        
        self.font_size = wx.SpinCtrl(self, -1, str(self._old_legend_settings['size']))
        self.font_size.SetValue(int(self._old_legend_settings['size']))
        self.font_size.Bind(wx.EVT_SPINCTRL, self._updateLegendSettings)
        
        self.border_chkbox = wx.CheckBox(self, -1)
        self.border_chkbox.Bind(wx.EVT_CHECKBOX, self._updateLegendSettings)
        if self._old_legend_settings['border']: boxon = True
        else: boxon = False
        
        self.border_chkbox.SetValue(boxon)
        
        self.shadow_chkbox =  wx.CheckBox(self, -1)
        self.shadow_chkbox.Bind(wx.EVT_CHECKBOX, self._updateLegendSettings)
        self.shadow_chkbox.SetValue(self._old_legend_settings['shadow'])
        
        self.legend_enable = wx.CheckBox(self, -1)
        self.legend_enable.Bind(wx.EVT_CHECKBOX, self._updateLegendSettings)
        self.legend_enable.SetValue(self.legend.get_visible())
    
        alpha_text = wx.StaticText(self, -1, 'Transparency % : ')
        self.alpha = wx.SpinCtrl(self, -1, str(abs(self._old_legend_settings['alpha']-100)))
        self.alpha.SetValue(int(abs(self._old_legend_settings['alpha']*100-100)))
        self.alpha.Bind(wx.EVT_SPINCTRL, self._updateLegendSettings)
        
        sizer.Add(wx.StaticText(self, -1, 'Visible'), 0)
        sizer.Add(self.legend_enable, 0, wx.BOTTOM,2 )
        sizer.Add(wx.StaticText(self, -1, 'Font size:'), 0, wx.ALIGN_CENTRE_VERTICAL)
        sizer.Add(self.font_size, 0)
        sizer.Add(alpha_text, 0, wx.ALIGN_CENTRE_VERTICAL)
        sizer.Add(self.alpha, 0)
        sizer.Add(wx.StaticText(self, -1, 'Border'), 0)
        sizer.Add(self.border_chkbox, 0)
        sizer.Add(wx.StaticText(self, -1, 'Shadow'), 0)
        sizer.Add(self.shadow_chkbox, 0)
        
        
        
        topbox.Add(sizer, 0, wx.ALL, 5)
        return topbox
    
    def _updateLegendSettings(self, event):
        
        size = self.font_size.GetValue()
        
        for each in self.legend.get_texts():
            each.set_size(size)
        
        border = self.border_chkbox.GetValue()
        
        if border:
            #self.legend.set_frame_on(border)
            self.legend.get_frame().set_linewidth(1)
        else:
            self.legend.get_frame().set_linewidth(0)
        
        alphaval = float(abs(100-self.alpha.GetValue()) / 100.0)
        
        self.legend.get_frame().set_alpha(alphaval)
        leg_visible = self.legend_enable.GetValue()
        
        self.legend.set_visible(leg_visible)
        
        self.legend.shadow = self.shadow_chkbox.GetValue()
        
        self.parent.canvas.draw()
        
        event.Skip()
    
    def _createLabelSettings(self):
        
        self.labels = [('Title:', 'title', {'text'  : wx.NewId(),
                                       'size'  : wx.NewId(),
                                       'weight': wx.NewId(),
                                       'style' : wx.NewId()}),
                  
                  ('x-axis label:', 'xlabel',{'text'  : wx.NewId(),
                                              'size'  : wx.NewId(),
                                              'weight': wx.NewId(),
                                              'style' : wx.NewId()}),
                  
                  ('y-axis label:', 'ylabel',{'text'  : wx.NewId(),
                                              'size'  : wx.NewId(),
                                              'weight': wx.NewId(),
                                              'style' : wx.NewId()}),
                       
                  ('Legend title:', 'legtit',{'text'  : wx.NewId(),
                                              'size'  : wx.NewId(),
                                              'weight': wx.NewId(),
                                              'style' : wx.NewId()})]
        
        
        box = wx.StaticBox(self, -1, 'Labels')
        box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        sizer = wx.FlexGridSizer(cols = 6, rows = 4, vgap = 5, hgap = 5)
        
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
            elif each_name == 'legtit': label = self.legend.get_title()
    
            txt = wx.StaticText(self, -1, each_label)
            
            labtxt = label.get_text()
            if each_name == 'legtit':
                 if labtxt == 'None': labtxt = ''
            
            txt_ctrl = wx.TextCtrl(self, id['text'], labtxt, name = each_name)
            font_ctrl = wx.Choice(self, -1, name = each_name)
            font_size = wx.SpinCtrl(self, id['size'], str(label.get_size()), name = each_name)
            font_size.SetValue(int(label.get_size()))
             
            bold = wx.CheckBox(self, id['weight'], name = each_name)
            italic = wx.CheckBox(self, id['style'], name = each_name)
            
            bold.Bind(wx.EVT_CHECKBOX, self._updateLabels)
            italic.Bind(wx.EVT_CHECKBOX, self._updateLabels)
            txt_ctrl.Bind(wx.EVT_KEY_UP, self._updateLabels)
            font_size.Bind(wx.EVT_SPINCTRL, self._updateLabels)
            
            if label.get_weight() == 'bold':
                bold.SetValue(True)
            if label.get_style() == 'italic':
                italic.SetValue(True)
            
            self._old_settings[each_name]['text'] = label.get_text()
            self._old_settings[each_name]['weight'] = label.get_weight()
            self._old_settings[each_name]['size'] = label.get_size()
            self._old_settings[each_name]['style'] = label.get_style()
            
            
            sizer.Add(txt, 0)
            sizer.Add(txt_ctrl, 0)
            sizer.Add(font_ctrl, 0)
            sizer.Add(font_size, 0)
            sizer.Add(bold, 0)
            sizer.Add(italic, 0)
        
        box_sizer.Add(sizer, 1, wx.ALL, 5)
        return box_sizer
    
    def _restoreOldSettings(self):
        
        for each in self._old_settings.keys():
            for each_key in self._old_settings[each].keys():
                if each == 'title':
                    expr = 'self.title.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec expr
                elif each == 'xlabel':
                    expr = 'self.xlabel.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec expr
                elif each == 'ylabel':
                    expr = 'self.ylabel.set_' + each_key + '("' + str(self._old_settings[each][each_key]) + '")'
                    exec expr
                    
                    
        self.parent.canvas.draw()
                
    
    def _onDefaultButton(self, evt):
        old_title, old_xlabel, old_ylabel = self.parent.default_subplot_labels[self.current_type]
        
        self.title.SetValue(old_title)
        self.xlabel.SetValue(old_xlabel)
        self.ylabel.SetValue(old_ylabel)
    
    def _onOk(self, event):
        
        if self.axes == self.parent.subplot1:
            type = self.parent.plotparams['plot1type']
        else:
            type = self.parent.plotparams['plot2type']
             
        self.parent.subplot_labels[type] = [self.title.get_text(), self.xlabel.get_text(), self.ylabel.get_text()]

        self.EndModal(wx.ID_OK)
        
    def _onCancel(self, event):
        self._restoreOldSettings()
        self.EndModal(wx.ID_CANCEL)
        
class CustomPlotToolbar(NavigationToolbar2Wx):
    def __init__(self, parent, canvas):

        self.fig_axes = parent.fig.gca()
        self.parent = parent
        
        self.saved_artists = None
        
        self._MTB_ERRBARS = wx.NewId()
        self._MTB_LEGEND = wx.NewId()
        self._MTB_SHOWBOTH = wx.NewId()
        self._MTB_SHOWTOP = wx.NewId()
        self._MTB_CLR1 = wx.NewId()
        self._MTB_CLR2 = wx.NewId()
        self._MTB_SHOWBOTTOM = wx.NewId()
        
        NavigationToolbar2Wx.__init__(self, canvas)
        
        self.workdir = workdir = RAWWorkDir

        clear1IconFilename = os.path.join(self.workdir, "resources" ,"clear1white.png")
        clear2IconFilename = os.path.join(self.workdir, "resources" ,"clear2white.png")
        errbarsIconFilename = os.path.join(self.workdir, "resources" ,"errbars.png")
        legendIconFilename = os.path.join(self.workdir, "resources", "legend.png")
        showbothIconFilename = os.path.join(self.workdir, "resources", "showboth.png")
        showtopIconFilename = os.path.join(self.workdir, "resources", "showtop.png")
        showbottomIconFilename = os.path.join(self.workdir, "resources", "showbottom.png")
        
        clear1_icon = wx.Bitmap(clear1IconFilename, wx.BITMAP_TYPE_PNG)
        clear2_icon = wx.Bitmap(clear2IconFilename, wx.BITMAP_TYPE_PNG)
        errbars_icon = wx.Bitmap(errbarsIconFilename, wx.BITMAP_TYPE_PNG)
        legend_icon = wx.Bitmap(legendIconFilename, wx.BITMAP_TYPE_PNG)
        showboth_icon = wx.Bitmap(showbothIconFilename, wx.BITMAP_TYPE_PNG)
        showtop_icon = wx.Bitmap(showtopIconFilename, wx.BITMAP_TYPE_PNG)
        showbottom_icon = wx.Bitmap(showbottomIconFilename, wx.BITMAP_TYPE_PNG)
        
        self.AddSeparator()
        self.AddCheckTool(self._MTB_ERRBARS, errbars_icon, shortHelp='Show Errorbars')
        #self.AddSimpleTool(self._MTB_LEGEND, legend_icon, 'Adjust Legend')
        self.AddSeparator()
        self.AddCheckTool(self._MTB_SHOWBOTH, showboth_icon, shortHelp='Show Both Plots')
        self.AddCheckTool(self._MTB_SHOWTOP, showtop_icon,  shortHelp='Show Top Plot')
        self.AddCheckTool(self._MTB_SHOWBOTTOM, showbottom_icon, shortHelp='Show Bottom Plot')
        #self.AddSeparator()
        #self.AddSimpleTool(self._MTB_CLR1, clear1_icon, 'Clear Top Plot')
        #self.AddSimpleTool(self._MTB_CLR2, clear2_icon, 'Clear Bottom Plot')
        
        self.Bind(wx.EVT_TOOL, self.clear1, id = self._MTB_CLR1)
        self.Bind(wx.EVT_TOOL, self.clear2, id = self._MTB_CLR2)
        self.Bind(wx.EVT_TOOL, self.errbars, id = self._MTB_ERRBARS)
        self.Bind(wx.EVT_TOOL, self.legend, id = self._MTB_LEGEND)
        self.Bind(wx.EVT_TOOL, self.showboth, id = self._MTB_SHOWBOTH)
        self.Bind(wx.EVT_TOOL, self.showtop, id = self._MTB_SHOWTOP)
        self.Bind(wx.EVT_TOOL, self.showbottom, id = self._MTB_SHOWBOTTOM)
         
        self.Realize()
        
        self.ErrorbarIsOn = False
        
        self.ToggleTool(self._MTB_SHOWBOTH, True)
    
    def home(self, *args, **kwargs):
        self.parent.fitAxis(forced = True)
        self.parent.canvas.draw()
             
    def showboth(self, evt):
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, False)
        self.ToggleTool(self._MTB_SHOWBOTH, True)
      
        self.parent.subplot1.set_visible(True)
        self.parent.subplot2.set_visible(True)
        
        self.parent.subplot1.change_geometry(2,1,1)
        self.parent.subplot2.change_geometry(2,1,2)
        self.parent._plot_shown = 0
        self.parent.canvas.draw()

    def showtop(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, False)
        self.ToggleTool(self._MTB_SHOWTOP, True)
        
        self.parent.subplot1.set_visible(True)
        self.parent.subplot2.set_visible(False)
    
        self.parent.subplot1.change_geometry(1,1,1)
        
        self.parent.subplot1.set_zorder(2)
        self.parent.subplot2.set_zorder(1)
            
        self.parent._plot_shown = 1
        self.parent.canvas.draw()

    def showbottom(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, True)
        
        self.parent.subplot1.set_visible(False)
        self.parent.subplot2.set_visible(True)
        
        self.parent.subplot1.set_zorder(1)
        self.parent.subplot2.set_zorder(2)
        
        self.parent.subplot2.change_geometry(1,1,1)
        self.parent._plot_shown = 2
        self.parent.canvas.draw()
        
            
    def legend(self, evt):   
        canvas = self.parent.canvas
        plots = (self.parent.subplot1, self.parent.subplot2)
        dialog = LegendDialog(self.parent, plots, canvas)
        dialog.ShowModal()
        
    def clear1(self, evt):
        self.parent.clearSubplot(self.parent.subplot1)
    def clear2(self, evt):
        self.parent.clearSubplot(self.parent.subplot2)

#*********************************************
# *** This causes Segmentation Error on Linux! :
#*********************************************

#    def set_cursor(self, cursor):
#        ''' overriding this method from parent '''
#        
#        cursord = {
#                   cursors.MOVE : wx.Cursor(os.path.join(self.workdir, "resources" ,"SmoothMove.cur"), wx.BITMAP_TYPE_CUR),
#                   cursors.HAND : wx.Cursor(os.path.join(self.workdir, "resources" ,"SmoothMove.cur"), wx.BITMAP_TYPE_CUR),
#                   cursors.POINTER : wx.StockCursor(wx.CURSOR_ARROW),
#                   cursors.SELECT_REGION : wx.Cursor(os.path.join(self.workdir, "resources" ,"zoom-in.cur"), wx.BITMAP_TYPE_CUR),            #wx.CURSOR_CROSS,
#                   }
#        
#        cursor = cursord[cursor]
#        self.parent.canvas.SetCursor( cursor )
#       
    def errbars(self, evt):
        
        if not(self.ErrorbarIsOn):
            self.parent.plotparams['errorbars_on'] = True
            self.ErrorbarIsOn = True
            self.parent.showErrorbars(True)
        else:
            self.parent.plotparams['errorbars_on'] = False
            self.ErrorbarIsOn = False
            self.parent.showErrorbars(False)

class PlotPanel(wx.Panel):
    
    def __init__(self, parent, id, name, *args, **kwargs):
        
        wx.Panel.__init__(self, parent, id, *args, name = name, **kwargs)

        self._initFigure()
        
        self.toolbar = CustomPlotToolbar(self, self.canvas)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)
        
        #color = parent.GetThemeBackgroundColour()
        self.SetSizer(sizer)
        #self._setColor(color)
         
        # Variables for the plotted experiments:
        self.legend_names = []
        self.plotted_sasms = []
        
        self.selected_line = None
        self.selected_line_orig_width = 1
        self._plot_shown = 0
        
        #Timer to automatically restore line width after selection
        self.blink_timer = wx.Timer()
        self.blink_timer.Bind(wx.EVT_TIMER, self._onBlinkTimer)
        
        self.plotparams = {'axesscale1'          : 'linlin',
                                    'axesscale2'          : 'linlin',
                                    'plot1type'           : 'normal',
                                    'plot2type'           : 'subtracted',
                                    'plot1state'          : 'linlin',
                                    'errorbars_on'        : False,
                                    'autoLegendPos'       : True,
                                    'subplot1_legend_pos' : None,
                                    'subplot2_legend_pos' : None,
                                    'legend_position'     : (0.5,0.5),
                                    'legend_visible_1'    : True,
                                    'legend_visible_2'    : True,
                                    'legend_fontsize1'    : 10,
                                    'legend_border1'      : False,
                                    'legend_fontsize2'    : 10,
                                    'legend_border2'      : False,
                                    'legend_alpha1'       : 0.7,
                                    'legend_alpha2'       : 0.7,
                                    'plot_custom_labels1' : False,
                                    'plot_custom_labels2' : False,
                                    'auto_fitaxes1'        : True,
                                    'auto_fitaxes2'        : True,
                                    'framestyle1'          : 'XY',
                                    'framestyle2'          : 'XY',
                                    
                                    'title_fontsize1'       : 16,
                                    'xlabel_fontsize1'      : 15,
                                    'ylabel_fontsize1'      : 15,
                                    
                                    'title_fontsize2'       : 16,
                                    'xlabel_fontsize2'      : 15,
                                    'ylabel_fontsize2'      : 15
                                    
                                    
                                    }
                                    
        
        self.frame_styles = ['Full', 'XY', 'X', 'Y', 'None']
        
        self.subplot_labels = { 'subtracted'  : ['Subtracted', '$q$', '$I(q)$'],
                                'kratky'      : ['Kratky', '$q$', '$I(q)q^{2}$'],
                                'guinier'     : ['Guinier', '$q^{2}$', '$ln(I(q))$'],
                                'porod'       : ['Porod', '$q$', '$I(q)q^{4}$'],
                                'normal'      : ['Main Plot', '$q$', '$I(q)$']}
        
        self.default_subplot_labels = { 'subtracted'  : ['Subtracted', 'q [1/A]', 'I(q)'],
                                        'kratky'      : ['Kratky', 'q [1/A]', 'I(q)q^2'],
                                        'guinier'     : ['Guinier', 'q^2 [1/A^2]', 'ln(I(q)'],
                                        'porod'       : ['Porod', 'q [1/A]', 'I(q)q^4'],
                                        'normal'      : ['Main Plot', 'q [1/A]', 'I(q)']}
        
            
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
        
        self._updateFrameStylesForAllPlots()
        
        self.canvas.callbacks.connect('pick_event', self._onPickEvent)
        self.canvas.callbacks.connect('key_press_event', self._onKeyPressEvent)
        self.canvas.callbacks.connect('motion_notify_event', self._onMouseMotionEvent)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
        
        self._canvas_cursor = Cursor(self.subplot1, useblit=True, color='red', linewidth=1, linestyle ='--' )
        self._canvas_cursor.horizOn = False
    
    def _initFigure(self):
        self.fig = matplotlib.figure.Figure((5,4), 75)        
        self.subplot1 = self.fig.add_subplot(211)
        self.subplot2 = self.fig.add_subplot(212)
        
        self.fig.subplots_adjust(left = 0.12, bottom = 0.07, right = 0.93, top = 0.93, hspace = 0.26)
        self.fig.set_facecolor('white')
              
        self.canvas = MyFigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetBackgroundColour('white')
        
    def setParameter(self, param, value):
        self.plotparams[param] = value
        
    def getParameter(self, param):
        return self.plotparams[param]
    
    
    def _updateFrameStylesForAllPlots(self):
        try:
            self.updateFrameStyle(axes = self.subplot1)
            self.updateFrameStyle(axes = self.subplot2)
        except Exception, e:
            print 'Possibly too old matplotlib version: ' + str(e)
            pass
    def updateFrameStyle(self, axes):
        if axes == self.subplot1:
            plotnum = '1'
        else:
            plotnum = '2'
        
        style = self.plotparams['framestyle' + plotnum]
        
        self.setFrameStyle(axes, style)
    
    def setFrameStyle(self, axes, style):
        
        if axes == self.subplot1:
            plotnum = '1'
        else:
            plotnum = '2'
        
        if style == 'Full':
            axes.set_frame_on(True)
        elif style == 'None':
            axes.set_frame_on(False)
            
        elif style == 'XY':
            for loc, spine in axes.spines.iteritems():
                if loc in ['right','top']:
                    spine.set_color('none') # don't draw spine
            
            axes.xaxis.set_ticks_position('bottom')
            axes.yaxis.set_ticks_position('left')
            
        self.plotparams['framestyle' + plotnum] == style
        
            
    def fitAxis(self, axes = None, forced = False):
        
        if axes:
            plots = axes
        else:
            plots = [self.subplot1, self.subplot2]
        
        for eachsubplot in plots:
            if eachsubplot.lines:
                
                maxq = None
                maxi = None
            
                minq = None
                mini = None
                
                if eachsubplot == self.subplot1:
                    plotnum = '1'
                else:
                    plotnum = '2'
                
                if self.plotparams['auto_fitaxes' + plotnum] == False and forced == False:
                    print 'hello'
                    return
                        
                for each in eachsubplot.lines:
                    if each._label != '_nolegend_' and each.get_visible() == True:
                        
                        if maxq == None:
                            maxq = max(each.get_xdata())
                            maxi = max(each.get_ydata())
            
                            minq = min(each.get_xdata())
                            mini = min(each.get_ydata())
                                
                        xmax = max(each.get_xdata())
                        ymax = max(each.get_ydata())
            
                        xmin = min(each.get_xdata())
                        ymin = min(each.get_ydata())
                   
                        if xmax > maxq:
                            maxq = xmax
                        if xmin < minq:
                            minq = xmin
                        if ymax > maxi:
                            maxi = ymax
                        if ymin < mini:
                            mini = ymin
                            
                eachsubplot.set_ylim(mini, maxi)
                eachsubplot.set_xlim(minq, maxq)
        
        try:
            self.canvas.draw()
        except ValueError, e:
            print 'ValueError in fitaxis() : ' + str(e)
            
        
    def _onBlinkTimer(self, event):
     
        try:
            self.selected_line.set_linewidth(self.selected_line_orig_width)
            self.canvas.draw()
        except:
            pass    
       
        self.selected_line = None
        self.blink_timer.Stop()
        
    def _onPickEvent(self, event):        
        self.manipulation_panel = wx.FindWindowByName('ManipulationPanel')

        if self.selected_line != None:
            self.selected_line.set_linewidth(self.selected_line_orig_width)
        
        self.selected_line = event.artist
        
        try:
            self.selected_line_orig_width = self.selected_line.get_linewidth()
            self.selected_line.set_linewidth(self.selected_line_orig_width + 2)
        except AttributeError:
            self.selected_line = None
            return
                
        wx.CallAfter(self.manipulation_panel.deselectAllExceptOne, None, self.selected_line)
        self.canvas.draw()
        
        self.blink_timer.Start(500)
        
    def _onKeyPressEvent(self, event):
        pass
    
    def _onMouseMotionEvent(self, event):
  
        if event.inaxes:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('q = ' +  str(round(x,5)) + ', I = ' + str(round(y,5)), 1) 
                
    def _onMouseButtonReleaseEvent(self, event):
        ''' Find out where the mouse button was released
        and show a pop up menu to change the settings
        of the figure the mouse was over '''
        
        x_size,y_size = self.canvas.get_width_height()
        half_y = y_size / 2
        
        if self._plot_shown == 1:
            selected_plot = 1
        elif self._plot_shown == 2:
            selected_plot = 2
        elif event.y <= half_y:
            selected_plot = 2
        else:
            selected_plot = 1
            
        if event.button == 3:
            if self.toolbar.GetToolState(self.toolbar._NTB2_PAN) == False:
                self._showPopupMenu(selected_plot)

#--- ** Popup Menu ***

    def movePlots(self, sasm_list, to_axes):
        
        axesThatNeedsUpdatedLegend = []
        
        for each in sasm_list:
            if each.axes != toAxes:
                plotpanel = each.plotPanel
      
                each.line.remove()
                each.errLine[0][0].remove()
                each.errLine[0][1].remove()
                each.errLine[1][0].remove()
                
                if not each.axes in axesThatNeedsUpdatedLegend:
                    axesThatNeedsUpdatedLegend.append(each.axes)
                
                plotpanel.PlotExperimentObject(each, axes = toAxes, addToPlottedExps = False)
                
        for eachaxes in axesThatNeedsUpdatedLegend:
            plotpanel._insertLegend(axes = eachaxes)                
        
        if axesThatNeedsUpdatedLegend:
            plotpanel.canvas.draw()

    def plotSASM(self, sasm, axes_no = 1, color = None, legend_label_in = None, line_data = None, *args, **kwargs):
        
        if axes_no == 1:
            a = self.subplot1
        elif axes_no == 2:
            a = self.subplot2
        else:
            a = axes_no
            
      
        #plot with errorbars
        if a == self.subplot1:
            type = self.plotparams.get('plot1type')
        elif a == self.subplot2:  
            type = self.plotparams.get('plot2type')
        
        q_min, q_max = sasm.getQrange()
        
        if legend_label_in == None:
            legend_label = sasm.getParameter('filename')
        else:
            legend_label = legend_label_in

        if type == 'normal' or type == 'subtracted':
            line, ec, el = a.errorbar(sasm.q[q_min:q_max], sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label, **kwargs)
        elif type == 'kratky':
            line, ec, el = a.errorbar(sasm.q[q_min:q_max], sasm.i[q_min:q_max] * numpy.power(sasm.q,2), sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
        elif type == 'guinier':
            line, ec, el = a.errorbar(numpy.power(sasm.q[q_min:q_max],2), sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
        elif type == 'porod':
            line, ec, el = a.errorbar(sasm.q[q_min:q_max], numpy.power(sasm.q[q_min:q_max],4)*sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
	
        line.set_label(legend_label)        

        #Hide errorbars:
        if self.plotparams['errorbars_on'] == False:
            #ec[0].set_visible(False)
            #ec[1].set_visible(False)
            #el[0].set_visible(False)
            
            for each in ec:
                each.set_visible(False)    
            for each in el:
                each.set_visible(False)
            
        if color != None:
            line.set_color(color)
            
        sasm.line = line
        sasm.err_line = (ec, el)
        sasm.axes = a
        sasm.canvas = self.canvas
        sasm.plot_panel = self
        sasm.is_plotted = True
                
        self.plotted_sasms.append(sasm)        # Insert the plot into plotted experiments list
    
        if line_data != None:
            line.set_linewidth(line_data['line_width'])
            line.set_linestyle(line_data['line_style'])
            line.set_color(line_data['line_color'])
            line.set_marker(line_data['line_marker'])
            line.set_visible(line_data['line_visible'])
        
        
    def showErrorbars(self, state):
        
        for each in self.plotted_sasms:
            
            if each.line.get_visible():
                for each_err_line in each.err_line[0]:
                    each_err_line.set_visible(state)    
                for each_err_line in each.err_line[1]:
                    each_err_line.set_visible(state)
 
                
#                for each_line in each.err_line[0]:
#                    each_line.set_visible(state)
#                    
#                for each_line in each.err_line[1]:
#                    each_line.set_visible(state)
#                    
                #setp(each.err_line[0], visible=state)
                #setp(each.err_line[1], visible=state)
            
        self.canvas.draw()
                        
    def _showPopupMenu(self, selected_plot):
        
        self.selected_plot = selected_plot
        
        mainframe = wx.FindWindowByName('MainFrame')
    
        MenuIDs = mainframe.MenuIDs
        menu = wx.Menu()
            
        plot1SubMenu = self._createPopupAxesMenu('1')
        plot2SubMenu = self._createPopupAxesMenu('2')
            
        if selected_plot == 1:
            menu.AppendSubMenu(plot1SubMenu, 'Axes')
        else:
            menu.AppendSubMenu(plot2SubMenu, 'Axes')

        sep = menu.AppendSeparator()
        #legend_item = menu.AppendCheckItem(wx.NewId(), 'Show Legend')
        #autofitaxes_item = menu.AppendCheckItem(wx.NewId(), 'Auto axes limits')
        #sep = menu.AppendSeparator()
        #legend_options = menu.Append(wx.NewId(), 'Legend Options...')
        plot_options = menu.Append(wx.NewId(), 'Plot Options...')
        
       # if self.plotparams['legend_visible'+ '_' + str(selected_plot)]:
       #     legend_item.Check()
            
        #if self.plotparams['auto_fitaxes' + str(selected_plot)]:
        #    autofitaxes_item.Check()
            
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        #self.Bind(wx.EVT_MENU, self._onToggleLegend, legend_item)
        #self.Bind(wx.EVT_MENU, self._onAutofitaxesMenuChoice, autofitaxes_item)
        
        #self.Bind(wx.EVT_MENU, self._onLegendOptions, legend_options)
        self.Bind(wx.EVT_MENU, self._onPlotOptions, plot_options) 
            
        
        self.PopupMenu(menu)
    
    def _onPlotOptions(self, evt):
        if self.selected_plot == 1:
            axes = self.subplot1
        else:
            axes = self.subplot2
        
        dlg = PlotOptionsDialog(self, self.plotparams, axes)
        dlg.ShowModal()
        dlg.Destroy()
        
        
        
        #self.updatePlotType(axes)
    
    def _onLegendOptions(self, evt):
        dlg = LegendOptionsDialog(self, self.plotparams, self.selected_plot)
        dlg.ShowModal()
        dlg.Destroy()
        
        self.updateLegend(self.selected_plot)
        
    def _onPopupMenuChoice(self, evt):
        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        id = evt.GetId()

        for key in MenuIDs.iterkeys():
            if MenuIDs[key] == id:

                if key[4] == '1':
                    
                    if key[5:7] == 'ty':
                        self.plotparams['plot1type'] = key[7:]
                        self.updatePlotType(self.subplot1)
                        
                        if key[7:] == 'guinier':
                            self.plotparams['axesscale1'] = 'loglin'
                        else:
                            self.plotparams['axesscale1'] = 'linlin'
                        
                        self.updatePlotAxes()
                        print '1'
                    else:
                        self.plotparams['axesscale1'] = key[7:]
                        self.plotparams['plot1type'] = 'normal'
                        self.updatePlotType(self.subplot1)
                        self.updatePlotAxes()
                        print '2'
                else:
                    if key[5:7] == 'ty':
                        self.plotparams['plot2type'] = key[7:]
                        self.updatePlotType(self.subplot2)
                        
                        if key[7:] == 'guinier':
                            self.plotparams['axesscale2'] = 'loglin'
                        else:
                            self.plotparams['axesscale2'] = 'linlin'
                        self.updatePlotAxes()
                        
                        print '3'
     
                    else:
                        self.plotparams['axesscale2'] = key[7:]
                        self.plotparams['plot2type'] = 'subtracted'
                        self.updatePlotType(self.subplot2)
                        try:
                            self.updatePlotAxes()
                        except ValueError, e:
                            print e
                        print '4'

        #Update plot settings in menu bar:                        
        mainframe.setViewMenuScale(id)
        #evt.Skip()
    
    def _onAutofitaxesMenuChoice(self, evt):
        plotnum = self.selected_plot
        
        self.plotparams['auto_fitaxes' + str(plotnum)] = not self.plotparams['auto_fitaxes' + str(plotnum)]
    
    def _onToggleLegend(self, event):
        plotnum = self.selected_plot
        
        self.plotparams['legend_visible' + '_' + str(plotnum)] = not self.plotparams['legend_visible' + '_' + str(plotnum)]
        
        
        if self.selected_plot == 1:
            a = self.subplot1
        else:
            a = self.subplot2
        
        if self.plotparams['legend_visible' + '_' + str(plotnum)]:
            #self._insertLegend(a)
            a.get_legend().set_visible(True)
        else:
            a.get_legend().set_visible(False)
            #a.legend_ = None
            
            self.canvas.draw()

    def _createPopupAxesMenu(self, plot_number):
        
        mainframe = wx.FindWindowByName('MainFrame')
        MenuIDs = mainframe.getMenuIds()
        item_list = []
        pop_menu = wx.Menu()
        
        axes_list = [('sclinlin',    'Lin-Lin'),
                         ('scloglin',    'Log-Lin'),
                         ('scloglog',   'Log-Log'),
                         ('sclinlog',    'Lin-Log'),
                         ('tyguinier',  'Guinier'),
                         ('tykratky',   'Kratky'),
                         ('typorod',   'Porod') ]
        
        for key, label in axes_list:
            item = pop_menu.AppendRadioItem(MenuIDs['plot' + plot_number + key], label)
            item_list.append(item)
            
        self._markCurrentAxesSelection(item_list, plot_number)
        
        return pop_menu 
    
    def _markCurrentAxesSelection(self, item_list, plot_number):
        ''' Set the current axes selection on the newly created
           popup menu ''' 
        
        if self.plotparams['plot' + plot_number + 'type'] == 'normal' or self.plotparams['plot' + plot_number + 'type'] == 'subtracted':
        
            if self.plotparams['axesscale' + plot_number + ''] == 'loglog':
                item_list[2].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'linlog':
                item_list[3].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'loglin':
                item_list[1].Check(True)
            elif self.plotparams['axesscale' + plot_number + ''] == 'linlin':
                item_list[0].Check(True)
        
        else:
            if self.plotparams['plot' + plot_number + 'type'] == 'guinier':
                item_list[4].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'kratky':
                item_list[5].Check(True)
            elif self.plotparams['plot' + plot_number + 'type'] == 'porod':
                item_list[6].Check(True)
                
    def updatePlotType(self, axes):
                
        for each in self.plotted_sasms:
            
            q_min, q_max = each.getQrange()

            if each.axes == self.subplot1:
                c = '1'
            else:
                c = '2'
                                                
            if self.plotparams['plot' + c + 'type'] == 'kratky':
                each.line.set_ydata(each.i[q_min:q_max] * numpy.power(each.q[q_min:q_max],2))
                each.line.set_xdata(each.q[q_min:q_max]) 
            elif self.plotparams['plot' + c + 'type'] == 'guinier':
                each.line.set_ydata(each.i[q_min:q_max])
                each.line.set_xdata(numpy.power(each.q[q_min:q_max],2))
            elif self.plotparams['plot' + c + 'type'] == 'porod':
                each.line.set_ydata(numpy.power(each.q[q_min:q_max],4)*each.i[q_min:q_max])
                each.line.set_xdata(each.q[q_min:q_max])
            elif self.plotparams['plot' + c + 'type'] == 'normal' or self.plotparams['plot' + c+ 'type'] == 'subtracted':
                each.line.set_ydata(each.i[q_min:q_max])
                each.line.set_xdata(each.q[q_min:q_max])
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
            
        self.fitAxis()
        
        self.canvas.draw()
        print 'done type'
        
    def updatePlotAxes(self):
        
        axes = [self.subplot1, self.subplot2]
            
        for a in axes:
            
            if a == self.subplot1:
                c = 1
            elif a == self.subplot2:
                c = 2
            
            if self.plotparams.get('axesscale' + str(c)) == 'linlin':
                a.set_xscale('linear')
                a.set_yscale('linear')
                    
            if self.plotparams.get('axesscale'+ str(c)) == 'loglin':
                a.set_xscale('linear')
                
                a.set_ylim(1, 99999)
                a.set_yscale('log')
                a.set_ylim(1, 99999)
                #a.limit_range_for_scale(1, 99999)
    
            if self.plotparams.get('axesscale'+ str(c)) == 'loglog':
                a.set_xscale('log')
                a.set_yscale('log')
                
            if self.plotparams.get('axesscale'+ str(c)) == 'linlog':
                a.set_xscale('log')
                a.set_yscale('linear')
        
        self.fitAxis()         

        self.canvas.draw()
        print 'done Axes'
        
    def updatePlotAfterManipulation(self, sasm_list):
        
        for sasm in sasm_list:
            a = sasm.axes
        
            if a == self.subplot1:
                type = self.plotparams.get('plot1type')
            elif a == self.subplot2:  
                type = self.plotparams.get('plot2type')
              
            q_min, q_max = sasm.getQrange()
            q = sasm.q[q_min:q_max]
            i = sasm.i[q_min:q_max]
              
            if type == 'normal' or type == 'subtracted':
                #line, ec, el = a.errorbar(sasm.q, sasm.i, sasm.errorbars, picker = 3)
                sasm.line.set_data(q, i)
            elif type == 'kratky':
                #line, ec, el = a.errorbar(sasm.q, sasm.i*power(sasm.q,2), sasm.errorbars, picker = 3)
                sasm.line.set_data(q, i*numpy.power(q,2))
            elif type == 'guinier':
                #line, ec, el = a.errorbar(power(sasm.q,2), sasm.i, sasm.errorbars, picker = 3)
                sasm.line.set_data(numpy.power(q,2), i)
            elif type == 'porod':
                #line, ec, el = a.errorbar(sasm.q, power(sasm.q,4)*sasm.i, sasm.errorbars, picker = 3)
                sasm.line.set_data(q, numpy.power(q,4)*i)
        
        self.canvas.draw()
    
    
    def clearPlot(self, plot_num):
        
        if plot_num == 1:
            self.subplot1.cla()
            self._setLabels(axes = self.subplot1)
        elif plot_num == 2:
            self.subplot2.cla()
            self._setLabels(axes = self.subplot2)
    
        self.updatePlotAxes()
    
        self.canvas.draw()
        
    def clearAllPlots(self):

        self.subplot1.cla()
        self.subplot2.cla()
        
        self.plotted_sasms = []
        
        self.updatePlotAxes()
        
        self._updateFrameStylesForAllPlots()
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)

        self.canvas.draw()
                
    def _setLabels(self, sasm = None, title = None, xlabel = None, ylabel = None, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        # Set labels
        if title == None:
            if a == self.subplot1:
                plottype = self.plotparams['plot1type']
                a.title.set_text(self.subplot_labels[plottype][0])
                a.yaxis.get_label().set_text(self.subplot_labels[plottype][2])
                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize2'])
                a.xaxis.get_label().set_text(self.subplot_labels[plottype][1])
                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize2'])
                           
            elif a == self.subplot2:
                plottype = self.plotparams['plot2type']
                a.title.set_text(self.subplot_labels[plottype][0])
                a.yaxis.get_label().set_text(self.subplot_labels[plottype][2])
                a.yaxis.get_label().set_size(self.plotparams['ylabel_fontsize2'])
                a.xaxis.get_label().set_text(self.subplot_labels[plottype][1])
                a.xaxis.get_label().set_size(self.plotparams['xlabel_fontsize2'])         
        else:
            a.title.set_text(title)
    
    def updateLegend(self, plotnum):
        axes = plotnum
        
        if plotnum == 1:
            axes = self.subplot1
        if plotnum == 2:
            axes = self.subplot2
        if plotnum == self.subplot1:
            plotnum = 1
        if plotnum == self.subplot2:
            plotnum = 2
              
        if self.plotparams['legend_visible' + '_' + str(plotnum)]:
            leg = axes.legend_ = None
            self._insertLegend(axes)
    
    def _insertLegend(self, axes):
        ####################################################################
        # NB!! LEGEND IS THE BIG SPEED HOG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ###################################################################
        a = axes
        
        if axes.lines:
            legend_lines = []
            legend_labels = []
            
            for each_line in axes.lines:
                if each_line.get_visible() == True:
                    legend_lines.append(each_line)
                    legend_labels.append(each_line.get_label())
            
            if not legend_lines:
                return
            
            if axes == self.subplot1:
                fontsize = self.plotparams['legend_fontsize1']
                enable_border = self.plotparams['legend_border1']
                alpha = self.plotparams['legend_alpha1']
            else:
                fontsize = self.plotparams['legend_fontsize2']
                enable_border =  self.plotparams['legend_border2']
                alpha = self.plotparams['legend_alpha2']
            
            leg = a.legend(legend_lines, legend_labels, prop = FontProperties(size = fontsize), fancybox = True)
            leg.get_frame().set_alpha(alpha)
            
            if not enable_border:
                #leg.draw_frame(False)
                leg.get_frame().set_linewidth(0)
            else:
                leg.get_frame().set_linewidth(1)
                
            try:
                leg.draggable()
            except AttributeError:
                print "WARNING: Old matplotlib version, legend not draggable"
   
        #legend = RAWCustomCtrl.DraggableLegend(leg, self.subplot1)
  
        self.canvas.draw()
    
    def _setColor(self, rgbtuple):
        """Set figure and canvas colours to be the same"""
        if not rgbtuple:
             rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
       
        col = [c/255.0 for c in rgbtuple]
        self.fig.set_facecolor(col)
        self.fig.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))
        
        
        
class IftPlotPanel(PlotPanel):
    
    def __init__(self, parent, id, name, *args, **kwargs):
        
        PlotPanel.__init__(self, parent, id, name,*args, **kwargs)

                        
        self.subplot_labels = { 'subtracted'  : ('Fit', '$q$', '$I(q)$'),
                                'kratky'      : ('Kratky', 'q [1/A]', 'I(q)q^2'),
                                'porod'       : ('Porod', 'q [1/A]', 'I(q)q^4'),
                                'guinier'     : ('Guinier', 'q^2 [1/A^2]', 'ln(I(q)'),
                                'normal'      : ('Pair Distance Distribution Function', '$r$', '$P(r)$')}
        
        self.default_subplot_labels = { 'subtracted'  : ('Fit', '$q$', '$I(q)$'),
                                'kratky'      : ('Kratky', 'q [1/A]', 'I(q)q^2'),
                                'porod'       : ('Porod', 'q [1/A]', 'I(q)q^4'),
                                'guinier'     : ('Guinier', 'q^2 [1/A^2]', 'ln(I(q)'),
                                'normal'        : ('Pair Distance Distribution Function', '$r$', '$P(r)$')}
        
        
       
   
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
        
    
    def plotFit(self, sasm, color = None, legend_label_in = None, *args, **kwargs):
        self.clearPlot(2)
        a = self.subplot2
        
        #If no IFT info is present, just plot the intensity curve
        if not sasm.getAllParameters().has_key('orig_sasm'):
            line, ec, el = a.errorbar(sasm.q, sasm.i, picker = 3, label = sasm.getParameter('filename'), **kwargs)
            line.set_color('blue')
            
            sasm.line = line
            sasm.err_line = (ec, el)
            sasm.axes = a
            sasm.canvas = self.canvas
            sasm.plot_panel = self
            sasm.is_plotted = True
            
            self.fitAxis()
            return
        
        
        orig_sasm = sasm.getParameter('orig_sasm')
        legend_label = orig_sasm.getParameter('filename')
 
        if legend_label_in == None:
            new_label = sasm.getParameter('filename') + ' (FIT)'
        else:
            new_label = legend_label_in + ' (FIT)'
            
        
        i = sasm.getParameter('orig_i')
        q = sasm.getParameter('orig_q')
        fit = sasm.getParameter('fit')[0]
        
        line, ec, el = a.errorbar(q, i, picker = 3, label = legend_label, **kwargs)
        line.set_color('blue')
        
        sasm.origline = line
        
        line, ec, el = a.errorbar(q, fit, picker = 3, label = new_label, **kwargs)
        line.set_color('red')
        
        sasm.fitline = line
        
        self.fitAxis()
        
    def plotSASM(self, sasm, axes_no = 1, color = None, legend_label_in = None, *args, **kwargs):
        
        if axes_no == 1:
            a = self.subplot1
        elif axes_no == 2:
            a = self.subplot2
        else:
            a = axes_no
        
        #plot with errorbars
        if a == self.subplot1:
            type = self.plotparams.get('plot1type')
        elif a == self.subplot2:  
            type = self.plotparams.get('plot2type')
        
        q_min, q_max = sasm.getQrange()
        
        if legend_label_in == None:
            legend_label = sasm.getParameter('filename')
        else:
            legend_label = legend_label_in
        
        if type == 'normal' or type == 'subtracted':
            line, ec, el = a.errorbar(sasm.q[q_min:q_max], sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label, **kwargs)
        elif type == 'kratky':
            line, ec, el = a.errorbar(sasm.q[q_min:q_max], sasm.i[q_min:q_max] * numpy.power(sasm.q,2), sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
        elif type == 'guinier':
            line, ec, el = a.errorbar(numpy.power(sasm.q[q_min:q_max],2), sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
        elif type == 'porod':
            line, ec, el = a.errorbar(sasm.q[q_min:q_max], numpy.power(sasm.q[q_min:q_max],4)*sasm.i[q_min:q_max], sasm.err[q_min:q_max], picker = 3, label = legend_label,**kwargs)
        
        #Hide errorbars:
        if self.plotparams['errorbars_on'] == False:
            for each in ec:
                each.set_visible(False)
                
            for each in el:
                each.set_visible(False)
            
        if color != None:
            line.set_color(color)
            
        sasm.line = line
        sasm.err_line = (ec, el)
        sasm.axes = a
        sasm.canvas = self.canvas
        sasm.plot_panel = self
        sasm.is_plotted = True
                
        self.plotted_sasms.append(sasm)        # Insert the plot into plotted experiments list
        
        
        #Plot fit:
        self.plotFit(sasm, color = color, legend_label_in = legend_label_in)
        
        
    def _onMouseMotionEvent(self, event):
  
        if event.inaxes:
            x, y = event.xdata, event.ydata
            wx.FindWindowByName('MainFrame').SetStatusText('r = ' +  str(round(x,5)) + ', P(r) = ' + str(round(y,5)), 1) 
        
        
    
