import wx, os, sys, matplotlib, math, numpy, RAWCustomCtrl
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backends.backend_wx import FigureCanvasBase
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backend_bases import cursors
from matplotlib.font_manager import FontProperties
from pylab import setp


RAWWorkDir = sys.path[0].strip('RAW.exe')

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


class CustomPlotToolbar(NavigationToolbar2Wx):
    def __init__(self, parent, canvas):

        self.fig_axes = parent.fig.gca()
        self.parent = parent
        
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
        self.parent.fitAxis()
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
        self.parent._plot_shown = 1
        self.parent.canvas.draw()

    def showbottom(self, evt):
        self.ToggleTool(self._MTB_SHOWBOTH, False)
        self.ToggleTool(self._MTB_SHOWTOP, False)
        self.ToggleTool(self._MTB_SHOWBOTTOM, True)
        
        self.parent.subplot1.set_visible(False)
        self.parent.subplot2.set_visible(True)
        
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
                                    'legend_visible_1' : False,
                                    'legend_visible_2' : False,
                                    'legend_fontsize'  : 10}
         
                        
        subplotLabels = { 'subtracted'  : ('Subtracted', 'q', 'I(q)'),
                          'PDDF'        : ('PDDF', 'r', 'p(r)'),
                          'kratky'      : ('Kratky', 'q', 'I(q)q^2'),
                          'guinier'     : ('Guinier', 'q^2', 'ln(I(q)'),
                          'main'        : ('Main Plot', 'q', 'I(q)')}
        
        
        
        
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)
        
        self.canvas.callbacks.connect('pick_event', self._onPickEvent)
        self.canvas.callbacks.connect('key_press_event', self._onKeyPressEvent)
        self.canvas.callbacks.connect('motion_notify_event', self._onMouseMotionEvent)
        self.canvas.callbacks.connect('button_release_event', self._onMouseButtonReleaseEvent)
    
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
            
    def fitAxis(self, axes = None):
        
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
            wx.FindWindowByName('MainFrame').SetStatusText('x = ' +  str(round(x,5)) + ', y = ' + str(round(y,5)), 1) 
    
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
            setp(ec, visible=False)
            setp(el, visible=False)
            
        if color != None:
            line.set_color(color)
            
        sasm.line = line
        sasm.err_line = (ec, el)
        sasm.axes = a
        sasm.canvas = self.canvas
        sasm.plot_panel = self
        sasm.is_plotted = True
                
        self.plotted_sasms.append(sasm)        # Insert the plot into plotted experiments list
    
        
    def showErrorbars(self, state):
        
        for each in self.plotted_sasms:
            
            if each.line.get_visible():
                setp(each.err_line[0], visible=state)
                setp(each.err_line[1], visible=state)
            
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
        legend_item = menu.AppendCheckItem(wx.NewId(), 'Show Legend')
        
        if self.plotparams['legend_visible'+ '_' + str(selected_plot)]:
            legend_item.Check()
              
        self.Bind(wx.EVT_MENU, self._onPopupMenuChoice)
        
        self.Bind(wx.EVT_MENU, self._onToggleLegend, legend_item)
             
        self.PopupMenu(menu)
        
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
                
    def _onToggleLegend(self, event):
        plotnum = self.selected_plot
        
        self.plotparams['legend_visible' + '_' + str(plotnum)] = not self.plotparams['legend_visible' + '_' + str(plotnum)]
        
        
        if self.selected_plot == 1:
            a = self.subplot1
        else:
            a = self.subplot2
        
        if self.plotparams['legend_visible' + '_' + str(plotnum)]:
            self._insertLegend(a)
        else:
            a.legend_ = None
            
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
        
    def clearAllPlots(self):

        self.subplot1.cla()
        self.subplot2.cla()
        
        self.plotted_sasms = []
        
        self.updatePlotAxes()
        self._setLabels(axes = self.subplot1)
        self._setLabels(axes = self.subplot2)

        self.canvas.draw()
                
    def _setLabels(self, sasm = None, title = None, xlabel = None, ylabel = None, axes = None):
        
        if axes == None:
            a = self.fig.gca()
        else:
            a = axes
        
        # Set TITLE 
        if title == None:
            
            if a == self.subplot1:
                if self.plotparams['plot1type'] == 'normal':
                    a.set_title('Main plot')
                    a.set_ylabel('I(q)')
                    a.set_xlabel('q [1/A]')
                        
                elif self.plotparams['plot1type'] == 'kratky':
                    a.set_title('Kratky plot')
                    a.set_ylabel('I(q)q^2')
                    a.set_xlabel('q [1/A]')
                        
                elif self.plotparams['plot1type'] == 'guinier':
                    a.set_title('Guinier plot')
                    a.set_ylabel('I(q)')
                    a.set_xlabel('q^2 [1/A^2]')
                    
                elif self.plotparams['plot1type'] == 'porod':
                    a.set_title('Porod plot')
                    a.set_ylabel('I(q)q^4')
                    a.set_xlabel('q [1/A]')
                            
            elif a == self.subplot2:
                if self.plotparams['plot2type'] == 'subtracted':
                    a.set_title('Subtracted plot')
                    a.set_ylabel('I(q)')
                    a.set_xlabel('q [1/A]')
                elif self.plotparams['plot2type'] == 'kratky':
                    a.set_title('Kratky plot')
                    a.set_ylabel('I(q)q^2')
                    a.set_xlabel('q [1/A]')
                elif self.plotparams['plot2type'] == 'guinier':
                    a.set_title('Guinier plot')
                    a.set_ylabel('I(q)')
                    a.set_xlabel('q^2 [1/A^2]')
                elif self.plotparams['plot2type'] == 'porod':
                    a.set_title('Porod plot')
                    a.set_ylabel('I(q)q^4')
                    a.set_xlabel('q [1/A]')
        else:
            a.set_title(title)
    
    def updateLegend(self, plotnum):
        axes = plotnum
        
        if plotnum == 1:
            axes = self.subplot1
        elif plotnum == 2:
            axes = self.subplot2
        elif plotnum == self.subplot1:
            plotnum = 1
        elif plotnum == self.subplot2:
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
            
            leg = a.legend(legend_lines, legend_labels, prop = FontProperties(size = self.plotparams['legend_fontsize']), fancybox = True)
            leg.get_frame().set_alpha(0.7)
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
        
        
        
    
    
    
        
    