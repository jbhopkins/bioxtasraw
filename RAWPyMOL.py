import wx
from wx.glcanvas import GLCanvas
import OpenGL.GL as OGL
import pymol2

# PyMol embedded in wxPython, Soren Skou
#
# Inspiration from PyQT example: https://gist.github.com/masci/6437112
# and modules/pymol/embed/wxpymol source files in pymol source (very outdated)

class PyMOLCanvas(GLCanvas):
    def __init__(self, parent, enable_gui = False):
        GLCanvas.__init__(self, parent,-1, attribList=[wx.glcanvas.WX_GL_DOUBLEBUFFER, wx.glcanvas.WX_GL_RGBA])

        self.context = wx.glcanvas.GLContext(self)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_WINDOW_DESTROY(self, self.OnDestroy)
        wx.EVT_MOTION(self, self.OnMouseMotion)
        wx.EVT_RIGHT_DOWN(self, self.OnMouseDown) 
        wx.EVT_RIGHT_UP(self, self.OnMouseUp)
        wx.EVT_LEFT_DOWN(self, self.OnMouseDown)  
        wx.EVT_LEFT_UP(self, self.OnMouseUp)
        wx.EVT_MIDDLE_DOWN(self, self.OnMouseDown)
        wx.EVT_MIDDLE_UP(self, self.OnMouseUp)
        wx.EVT_MOUSEWHEEL(self, self.OnMouseWheel)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        wx.EVT_CHAR(self,self.OnChar)
        
        self.button_map = {wx.MOUSE_BTN_LEFT:0, wx.MOUSE_BTN_MIDDLE:1, wx.MOUSE_BTN_RIGHT:2}
        self.enable_gui = enable_gui
        
        self.InitGL()

        self.SetBackgroundColor("white")

        #self.LoadMolFile("C:/Programming/RAW/pept.pdb")

        #self._pymol.cmd.set("internal_feedback", 1)
        self.ShowInternalGUI(True)

    def OnChar(self, event):
        self.SetFocus()
        width, height = self.GetSize()
        code = event.GetKeyCode()
        print code

        shift, control, meta = event.ShiftDown(), event.ControlDown(),event.MetaDown()
        
        mod_dict = {}
        mod = 0
        P_GLUT_CHAR_EVENT = 5
        self._pymol.cmd._cmd.runwxpymol() 
        self._pymol.cmd._cmd.p_glut_event(P_GLUT_CHAR_EVENT, event.GetX(), event.GetY(), code, 0, mod)
        
        event.Skip()
        self.PymolProcess()

    def OnPaint(self, event):
        self.SetCurrent(self.context)
        width, height = self.GetSize()

        try:
            OGL.glViewport(0, 0, width, height)
            self._pymol.idle()
            self._pymol.draw()

            self.SwapBuffers()
        except Exception:
            pass

    def ShowInternalGUI(self, state):
        
        if state:
            self._pymol.cmd.set("internal_gui", 1)
            self._pymol.cmd.set("internal_feedback", 0)
            #self._pymol.cmd.button("double_left", "None", "None")
            #self._pymol.cmd.button("single_right", "None", "None")
        else:
            self._pymol.cmd.set("internal_gui", 0)
            self._pymol.cmd.set("internal_feedback", 0)
            self._pymol.cmd.button("double_left", "None", "None")
            self._pymol.cmd.button("single_right", "None", "None")

    def InitGL(self):
        self._pymol = pymol2.PyMOL()
        self._pymol.start()

        if not self.enable_gui:
            self.ShowInternalGUI(self.enable_gui)

        width, height = self.GetSize()
        self._pymol.reshape(width, height)
        
        self.PymolProcess()

    def SetBackgroundColor(self, color):
        self._pymol.cmd.bg_color(color)
        
    def OnSize(self, event):
        try:
            width, height = event.GetSize()
        except:
            width = event.GetSize().width
            height = event.GetSize().height

        try:
           self._pymol.reshape(width, height, True)
           self.PymolProcess()
        except AttributeError, e:
            print 'GL not init yet'
        
        self.Refresh()
        self.Update()
    
    def OnDestroy(self, event):
        #print "Destroying Window"
        pass
        
    def OnEraseBackground(self, event):
        #prevents flickering on MSWIN
        pass
    
    def PymolProcess(self):
        self._pymol.idle()
        self.Refresh()
        self.Update()

    def LoadMolFile(self, mol_file):
        self._pymol.cmd.load(str(mol_file))
        #self._pymol.cmd.show("sticks")

    def OnMouseMotion(self, event):
        width, height = self.GetSize()
        
        self._pymol.drag(event.GetX(), height - event.GetY(), 0)
        self.PymolProcess()
        event.Skip()

    def OnMouseDown(self, event):
        #if self.enable_gui:
        #     self._pymol.cmd.set("internal_feedback", 0)
        #    self._pymol.cmd.button("double_left", "None", "None")
        #    self._pymol.cmd.button("single_right", "None", "None")
        
        width, height = self.GetSize()
        self._pymol.button(self.button_map[event.GetButton()], 0, event.GetX(), height - event.GetY(), 0)
        self.PymolProcess()
        event.Skip()

    def OnMouseUp(self, event):
        width, height = self.GetSize()
        self._pymol.button(self.button_map[event.GetButton()], 1, event.GetX(), height - event.GetY(), 0)
        self.PymolProcess()
        event.Skip()

    def OnMouseWheel(self, event):
        button = 4 if event.GetWheelRotation() > 0 else 3
        self._pymol.button(button, 0, event.GetX(), event.GetY(), 0)
        self.PymolProcess()
        event.Skip()

    def runPyMOLCommand(self, command):
        try:
            print self._pymol.cmd.do(command)
        except NameError:
            dlg = wx.MessageDialog(self, str(command) + ' is and unknown PyMOL command, Unknown command', wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
        
        self.PymolProcess()

class PyMOLPanel(wx.Panel):

    def __init__(self, parent, panel_id, name, enable_gui = False, *args, **kwargs):

        wx.Panel.__init__(self, parent, panel_id, *args, name = name, **kwargs)
        self.enable_gui = enable_gui
        self._createLayout()

        #self.showCommandLine(False)

    def _createLayout(self):
        
        self.canvas = PyMOLCanvas(self, enable_gui = self.enable_gui)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.ALL | wx.GROW)
        sizer.Add(self.createCommandLineCtrls(), 0, wx.ALL | wx.GROW, 5)

        self.SetSizerAndFit(sizer)

    def createCommandLineCtrls(self):

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.command_line_ctrl = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        self.command_line_ctrl.Bind(wx.EVT_KEY_DOWN, self.onCommandLineCtrlEnter)
        self.command_line_label = wx.StaticText(self, -1, 'PyMOL >')
        self.execute_button = wx.Button(self, -1, 'Execute')
        self.execute_button.Bind(wx.EVT_BUTTON, self.onExecuteCommandButton)

        sizer.Add(self.command_line_label, 0, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 5)
        sizer.Add(self.command_line_ctrl, 1, wx.GROW)
        sizer.Add(self.execute_button, 0, wx.LEFT, 5)

        return sizer

    def onCommandLineCtrlEnter(self, event):
        keycode = event.GetKeyCode()
        
        if keycode == wx.WXK_RETURN or keycode == wx.WXK_NUMPAD_ENTER:
            cmd = self.command_line_ctrl.GetValue()

            if cmd == '': return

            self.canvas.runPyMOLCommand(cmd)
            self.command_line_ctrl.SetValue('')

        event.Skip()

    def onExecuteCommandButton(self, event):
        cmd = self.command_line_ctrl.GetValue()

        if cmd == '': return

        self.canvas.runPyMOLCommand(cmd)
        self.command_line_ctrl.SetValue('')

        event.Skip()

    def showCommandLine(self, state):

        if state:
            self.command_line_ctrl.Show(True)
            self.command_line_label.Show(True)
        else:
            self.command_line_ctrl.Show(False)
            self.command_line_label.Show(False)

        self.Layout()
        
        
if __name__ == '__main__':
    app = wx.App()
    frame = wx.Frame(None, -1, 'PyMol -> RAW', wx.DefaultPosition, wx.Size(400,400))
    canvas = PyMOLCanvas(frame, enable_gui = True)
    
    frame.Show()
    app.MainLoop()
