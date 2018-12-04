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

import math
import platform
import logging

import wx
if wx.version().split()[0].strip()[0] == '4':
    control_super = wx.Control
else:
    control_super = wx.PyControl
import wx.lib.agw.flatnotebook as flatNB
from wx.lib.agw import ultimatelistctrl as ULC
import wx.lib.agw.supertooltip as STT
from wx.lib.wordwrap import wordwrap
from wx.lib.stattext import GenStaticText as StaticText
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg

import RAWIcons
import RAWGlobals


class ColourIndicator(control_super):
    """
    A custom class that shows the colour of the line plot.
    """

    def __init__(self, parent, id=wx.ID_ANY, color = 'black', pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.NO_BORDER, validator=wx.DefaultValidator,
                 name="ColourIndicator"):

        control_super.__init__(self, parent, id, pos, size, style, validator, name)

        self.parent = parent

        self.InitializeColours()
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self._line_thickness = 5
        self._linecolor = color

    def updateColour(self, colour):
        self._linecolor = colour
        self.Refresh()

    def InitializeColours(self):
        """ Initializes the focus indicator pen. """

        textClr = self.GetForegroundColour()

        if wx.Platform == "__WXMAC__":
            self._focusIndPen = wx.Pen(textClr, 1, wx.SOLID)
        else:
            self._focusIndPen  = wx.Pen(textClr, 1, wx.USER_DASH)
            self._focusIndPen.SetDashes([1,1])
            self._focusIndPen.SetCap(wx.CAP_BUTT)

    def OnPaint(self, event):
        """ Handles the wx.EVT_PAINT event for CustomCheckBox. """

        # If you want to reduce flicker, a good starting point is to
        # use wx.BufferedPaintDC.
        dc = wx.BufferedPaintDC(self)

        # Is is advisable that you don't overcrowd the OnPaint event
        # (or any other event) with a lot of code, so let's do the
        # actual drawing in the Draw() method, passing the newly
        # initialized wx.BufferedPaintDC
        self.Draw(dc)

#        """set up the device context (DC) for painting"""
#        self.dc = wx.PaintDC(self)
#        self.dc.BeginDrawing()
#        self.dc.SetPen(wx.Pen("black",style=wx.TRANSPARENT))
#        self.dc.SetBrush(wx.Brush("black", wx.SOLID))
#        # set x, y, w, h for rectangle
#        self.dc.DrawRectangle(25,25,50, 50)
#        self.dc.EndDrawing()
#        del self.dc

    def DoGetBestSize(self):
        """
        Overridden base class virtual.  Determines the best size of the control
        based on the label size, the bitmap size and the current font.
        """

        best = self.GetSize()

        # Cache the best size so it doesn't need to be calculated again,
        # at least until some properties of the window change
        self.CacheBestSize(best)

        return best

    def Draw(self, dc):
        """
        Actually performs the drawing operations, for the bitmap and
        for the text, positioning them centered vertically.
        """
        # Get the actual client size of ourselves
        width, height = self.GetClientSize()
        start_point = (height // 2) - self._line_thickness // 2

#        if not width or not height:
#            # Nothing to do, we still don't have dimensions!
#            return

        # Initialize the wx.BufferedPaintDC, assigning a background
        # colour and a foreground colour (to draw the text)


        #self.parent.GetBackgroundColour()
        backColour = self.parent.GetBackgroundColour() #wx.Colour(255,255,255)
        backBrush = wx.Brush(backColour, wx.SOLID)
        dc.SetBackground(backBrush)
        dc.Clear()

        dc.SetBrush(wx.Brush(self._linecolor, wx.SOLID))
        dc.SetPen(wx.Pen(self._linecolor))
        dc.DrawRectangle(0, start_point, width, self._line_thickness)



#        if self.IsEnabled():
#            dc.SetTextForeground(self.GetForegroundColour())
#        else:
#            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
#
#        dc.SetFont(self.GetFont())
#
#        # Get the text label for the checkbox, the associated check bitmap
#        # and the spacing between the check bitmap and the text
#        label = self.GetLabel()
#        bitmap = self.GetBitmap()
#        spacing = self.GetSpacing()
#
#        # Measure the text extent and get the check bitmap dimensions
#        textWidth, textHeight = dc.GetTextExtent(label)
#        bitmapWidth, bitmapHeight = bitmap.GetWidth(), bitmap.GetHeight()
#
#        # Position the bitmap centered vertically
#        bitmapXpos = 0
#        bitmapYpos = (height - bitmapHeight)/2
#
#        # Position the text centered vertically
#        textXpos = bitmapWidth + spacing
#        textYpos = (height - textHeight)/2
#
#        # Draw the bitmap on the DC
#        dc.DrawBitmap(bitmap, bitmapXpos, bitmapYpos, True)
#
#        # Draw the text
#        dc.DrawText(label, textXpos, textYpos)





#----------------------------------------------------------------------
def GetCheckedBitmap():
    if wx.version().split()[0].strip()[0] == '4':
        return wx.Bitmap(GetCheckedImage())
    else:
        return wx.BitmapFromImage(GetCheckedImage())

def GetCheckedImage():
    image = RAWIcons.checked.GetImage()
    return image

#----------------------------------------------------------------------

def GetNotCheckedBitmap():
    if wx.version().split()[0].strip()[0] == '4':
        return wx.Bitmap(GetNotCheckedImage())
    else:
        return wx.BitmapFromImage(GetNotCheckedImage())

def GetNotCheckedImage():
    image = RAWIcons.notchecked.GetImage()
    return image

#----------------------------------------------------------------------

def GrayOut(anImage):
    """
    Convert the given image (in place) to a grayed-out version,
    appropriate for a 'disabled' appearance.
    """

    factor = 0.7        # 0 < f < 1.  Higher Is Grayer

    if anImage.HasMask():
        maskColor = (anImage.GetMaskRed(), anImage.GetMaskGreen(), anImage.GetMaskBlue())
    else:
        maskColor = None

    if wx.version().split()[0].strip()[0] == '4':
        data = list(anImage.GetData())
    else:
        data = map(ord, list(anImage.GetData()))

    for i in range(0, len(data), 3):

        pixel = (data[i], data[i+1], data[i+2])
        pixel = MakeGray(pixel, factor, maskColor)

        for x in range(3):
            data[i+x] = pixel[x]

    anImage.SetData(''.join(map(chr, data)))

    return anImage.ConvertToBitmap()


def MakeGray((r,g,b), factor, maskColor):
    """
    Make a pixel grayed-out. If the pixel matches the maskcolor, it won't be
    changed.
    """

    if (r,g,b) != maskColor:
        return map(lambda x: int((230 - x) * factor) + x, (r,g,b))
    else:
        return (r,g,b)


class CustomCheckBox(control_super):
    """
    A custom class that replicates some of the functionalities of wx.CheckBox,
    while being completely owner-drawn with a nice check bitmaps.
    """

    def __init__(self, parent, id=wx.ID_ANY, label="", pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.NO_BORDER, validator=wx.DefaultValidator,
                 name="CustomCheckBox"):
        """
        Default class constructor.

        @param parent: Parent window. Must not be None.
        @param id: CustomCheckBox identifier. A value of -1 indicates a default value.
        @param label: Text to be displayed next to the checkbox.
        @param pos: CustomCheckBox position. If the position (-1, -1) is specified
                    then a default position is chosen.
        @param size: CustomCheckBox size. If the default size (-1, -1) is specified
                     then a default size is chosen.
        @param style: not used in this demo, CustomCheckBox has only 2 state
        @param validator: Window validator.
        @param name: Window name.
        """

        # Ok, let's see why we have used wx.PyControl instead of wx.Control.
        # Basically, wx.PyControl is just like its wxWidgets counterparts
        # except that it allows some of the more common C++ virtual method
        # to be overridden in Python derived class. For CustomCheckBox, we
        # basically need to override DoGetBestSize and AcceptsFocusFromKeyboard

        control_super.__init__(self, parent, id, pos, size, style, validator, name)

        # Initialize our cool bitmaps
        self.InitializeBitmaps()

        # Initialize the focus pen colour/dashes, for faster drawing later
        self.InitializeColours()

        # By default, we start unchecked
        self._checked = False

        # Set the spacing between the check bitmap and the label to 3 by default.
        # This can be changed using SetSpacing later.
        self._spacing = 3
        self._hasFocus = False

        # Ok, set the wx.PyControl label, its initial size (formerly known an
        # SetBestFittingSize), and inherit the attributes from the standard
        # wx.CheckBox
        # print label
        self.SetLabel(label)
        self.SetInitialSize(size)
        self.InheritAttributes()

        # Bind the events related to our control: first of all, we use a
        # combination of wx.BufferedPaintDC and an empty handler for
        # wx.EVT_ERASE_BACKGROUND (see later) to reduce flicker
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

        # Then we want to monitor user clicks, so that we can switch our
        # state between checked and unchecked
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseClick)
        if wx.Platform == '__WXMSW__':
            # MSW Sometimes does strange things...
            self.Bind(wx.EVT_LEFT_DCLICK,  self.OnMouseClick)

        # We want also to react to keyboard keys, namely the
        # space bar that can toggle our checked state
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

        # Then, we react to focus event, because we want to draw a small
        # dotted rectangle around the text if we have focus
        # This might be improved!!!
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)


    def InitializeBitmaps(self):
        """ Initializes the check bitmaps. """

        # We keep 4 bitmaps for CustomCheckBox, depending on the
        # checking state (Checked/UnCkecked) and the control
        # state (Enabled/Disabled).
        self._bitmaps = {"CheckedEnable": GetCheckedBitmap(),
                         "UnCheckedEnable": GetNotCheckedBitmap(),
                         "CheckedDisable": GrayOut(GetCheckedImage()),
                         "UnCheckedDisable": GrayOut(GetNotCheckedImage())}


    def InitializeColours(self):
        """ Initializes the focus indicator pen. """

        textClr = self.GetForegroundColour()
        if wx.Platform == "__WXMAC__":
            self._focusIndPen = wx.Pen(textClr, 1, wx.SOLID)
        else:
            self._focusIndPen  = wx.Pen(textClr, 1, wx.USER_DASH)
            self._focusIndPen.SetDashes([1,1])
            self._focusIndPen.SetCap(wx.CAP_BUTT)


    def GetBitmap(self):
        """
        Returns the appropriated bitmap depending on the checking state
        (Checked/UnCkecked) and the control state (Enabled/Disabled).
        """

        if self.IsEnabled():
            # So we are Enabled
            if self.IsChecked():
                # We are Checked
                return self._bitmaps["CheckedEnable"]
            else:
                # We are UnChecked
                return self._bitmaps["UnCheckedEnable"]
        else:
            # Poor CustomCheckBox, Disabled and ignored!
            if self.IsChecked():
                return self._bitmaps["CheckedDisable"]
            else:
                return self._bitmaps["UnCheckedDisable"]


    def SetLabel(self, label):
        """
        Sets the CustomCheckBox text label and updates the control's size to
        exactly fit the label plus the bitmap.
        """

        control_super.SetLabel(self, label)

        # The text label has changed, so we must recalculate our best size
        # and refresh ourselves.
        self.InvalidateBestSize()
        self.Refresh()


    def SetFont(self, font):
        """
        Sets the CustomCheckBox text font and updates the control's size to
        exactly fit the label plus the bitmap.
        """

        control_super.SetFont(self, font)

        # The font for text label has changed, so we must recalculate our best
        # size and refresh ourselves.
        self.InvalidateBestSize()
        self.Refresh()


    def DoGetBestSize(self):
        """
        Overridden base class virtual.  Determines the best size of the control
        based on the label size, the bitmap size and the current font.
        """

        # Retrieve our properties: the text label, the font and the check
        # bitmap
        label = self.GetLabel()
        font = self.GetFont()
        bitmap = self.GetBitmap()

        if not font:
            # No font defined? So use the default GUI font provided by the system
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

        # Set up a wx.ClientDC. When you don't have a dc available (almost
        # always you don't have it if you are not inside a wx.EVT_PAINT event),
        # use a wx.ClientDC (or a wx.MemoryDC) to measure text extents
        dc = wx.ClientDC(self)
        dc.SetFont(font)

        # Measure our label
        textWidth, textHeight = dc.GetTextExtent(label)

        # Retrieve the check bitmap dimensions
        bitmapWidth, bitmapHeight = bitmap.GetWidth(), bitmap.GetHeight()

        # Get the spacing between the check bitmap and the text
        spacing = self.GetSpacing()

        # Ok, we're almost done: the total width of the control is simply
        # the sum of the bitmap width, the spacing and the text width,
        # while the height is the maximum value between the text width and
        # the bitmap width
        totalWidth = bitmapWidth + spacing + textWidth
        totalHeight = max(textHeight, bitmapHeight)

        best = wx.Size(totalWidth, totalHeight)

        # Cache the best size so it doesn't need to be calculated again,
        # at least until some properties of the window change
        self.CacheBestSize(best)

        return best


    def AcceptsFocusFromKeyboard(self):
        """Overridden base class virtual."""

        # We can accept focus from keyboard, obviously
        return True


    def AcceptsFocus(self):
        """ Overridden base class virtual. """

        # It seems to me that wx.CheckBox does not accept focus with mouse
        # but please correct me if I am wrong!
        return False


    def HasFocus(self):
        """ Returns whether or not we have the focus. """

        # We just returns the _hasFocus property that has been set in the
        # wx.EVT_SET_FOCUS and wx.EVT_KILL_FOCUS event handlers.
        return self._hasFocus


    def SetForegroundColour(self, colour):
        """ Overridden base class virtual. """

        control_super.SetForegroundColour(self, colour)

        # We have to re-initialize the focus indicator per colour as it should
        # always be the same as the foreground colour
        self.InitializeColours()
        self.Refresh()


    def SetBackgroundColour(self, colour):
        """ Overridden base class virtual. """

        control_super.SetBackgroundColour(self, colour)

        # We have to refresh ourselves
        self.Refresh()


    def Enable(self, enable=True):
        """ Enables/Disables CustomCheckBox. """

        control_super.Enable(self, enable)

        # We have to refresh ourselves, as our state changed
        self.Refresh()


    def GetDefaultAttributes(self):
        """
        Overridden base class virtual.  By default we should use
        the same font/colour attributes as the native wx.CheckBox.
        """

        return wx.CheckBox.GetClassDefaultAttributes()


    def ShouldInheritColours(self):
        """
        Overridden base class virtual.  If the parent has non-default
        colours then we want this control to inherit them.
        """

        return True


    def SetSpacing(self, spacing):
        """ Sets a new spacing between the check bitmap and the text. """

        self._spacing = spacing

        # The spacing between the check bitmap and the text has changed,
        # so we must recalculate our best size and refresh ourselves.
        self.InvalidateBestSize()
        self.Refresh()


    def GetSpacing(self):
        """ Returns the spacing between the check bitmap and the text. """

        return self._spacing


    def GetValue(self):
        """
        Returns the state of CustomCheckBox, True if checked, False
        otherwise.
        """

        return self._checked


    def IsChecked(self):
        """
        This is just a maybe more readable synonym for GetValue: just as the
        latter, it returns True if the CustomCheckBox is checked and False
        otherwise.
        """

        return self._checked


    def SetValue(self, state):
        """
        Sets the CustomCheckBox to the given state. This does not cause a
        wx.wxEVT_COMMAND_CHECKBOX_CLICKED event to get emitted.
        """

        self._checked = state

        # Refresh ourselves: the bitmap has changed
        self.Refresh()


    def OnKeyUp(self, event):
        """ Handles the wx.EVT_KEY_UP event for CustomCheckBox. """

        if event.GetKeyCode() == wx.WXK_SPACE:
            # The spacebar has been pressed: toggle our state
            self.SendCheckBoxEvent()
            event.Skip()
            return

        event.Skip()


    def OnSetFocus(self, event):
        """ Handles the wx.EVT_SET_FOCUS event for CustomCheckBox. """

        self._hasFocus = True

        # We got focus, and we want a dotted rectangle to be painted
        # around the checkbox label, so we refresh ourselves
        self.Refresh()

        event.Skip()


    def OnKillFocus(self, event):
        """ Handles the wx.EVT_KILL_FOCUS event for CustomCheckBox. """

        self._hasFocus = False

        # We lost focus, and we want a dotted rectangle to be cleared
        # around the checkbox label, so we refresh ourselves
        self.Refresh()

        event.Skip()


    def OnPaint(self, event):
        """ Handles the wx.EVT_PAINT event for CustomCheckBox. """

        # If you want to reduce flicker, a good starting point is to
        # use wx.BufferedPaintDC.

        if wx.version().split()[0].strip()[0] == '4' and self.GetContentScaleFactor() > 1:
            dc = wx.PaintDC(self)
        else:
            dc = wx.BufferedPaintDC(self)

        # Is is advisable that you don't overcrowd the OnPaint event
        # (or any other event) with a lot of code, so let's do the
        # actual drawing in the Draw() method, passing the newly
        # initialized wx.BufferedPaintDC
        self.Draw(dc)


    def Draw(self, dc):
        """
        Actually performs the drawing operations, for the bitmap and
        for the text, positioning them centered vertically.
        """

        # Get the actual client size of ourselves
        width, height = self.GetClientSize()

        if not width or not height:
            # Nothing to do, we still don't have dimensions!
            return

        # Initialize the wx.BufferedPaintDC, assigning a background
        # colour and a foreground colour (to draw the text)
        backColour = self.GetParent().GetBackgroundColour()
        backBrush = wx.Brush(backColour, wx.SOLID)
        dc.SetBackground(backBrush)
        dc.Clear()

        if self.IsEnabled():
            dc.SetTextForeground(self.GetForegroundColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        dc.SetFont(self.GetParent().GetFont())

        # Get the text label for the checkbox, the associated check bitmap
        # and the spacing between the check bitmap and the text
        label = self.GetLabel()
        bitmap = self.GetBitmap()
        spacing = self.GetSpacing()

        # Measure the text extent and get the check bitmap dimensions
        textWidth, textHeight = dc.GetTextExtent(label)
        bitmapWidth, bitmapHeight = bitmap.GetWidth(), bitmap.GetHeight()

        # Position the bitmap centered vertically
        bitmapXpos = 0
        bitmapYpos = (height - bitmapHeight)/2

        # Position the text centered vertically
        textXpos = bitmapWidth + spacing
        textYpos = (height - textHeight)/2

        # Draw the bitmap on the DC
        dc.DrawBitmap(bitmap, bitmapXpos, bitmapYpos, True)

        # Draw the text
        dc.DrawText(label, textXpos, textYpos)

        # Let's see if we have keyboard focus and, if this is the case,
        # we draw a dotted rectangle around the text (Windows behavior,
        # I don't know on other platforms...)
        if self.HasFocus():
            # Yes, we are focused! So, now, use a transparent brush with
            # a dotted black pen to draw a rectangle around the text
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(self._focusIndPen)
            dc.DrawRectangle(textXpos, textYpos, textWidth, textHeight)


    def OnEraseBackground(self, event):
        """ Handles the wx.EVT_ERASE_BACKGROUND event for CustomCheckBox. """

        # This is intentionally empty, because we are using the combination
        # of wx.BufferedPaintDC + an empty OnEraseBackground event to
        # reduce flicker
        pass


    def OnMouseClick(self, event):
        """ Handles the wx.EVT_LEFT_DOWN event for CustomCheckBox. """

        x,y = event.GetPosition()

        if not self.IsEnabled():
            # Nothing to do, we are disabled
            return

        if x < 20:
                self.SendCheckBoxEvent()

        event.Skip()


    def SendCheckBoxEvent(self):
        """ Actually sends the wx.wxEVT_COMMAND_CHECKBOX_CLICKED event. """

        # This part of the code may be reduced to a 3-liner code
        # but it is kept for better understanding the event handling.
        # If you can, however, avoid code duplication; in this case,
        # I could have done:
        #
        # self._checked = not self.IsChecked()
        # checkEvent = wx.CommandEvent(wx.wxEVT_COMMAND_CHECKBOX_CLICKED,
        #                              self.GetId())
        # checkEvent.SetInt(int(self._checked))
        if self.IsChecked():

            # We were checked, so we should become unchecked
            self._checked = False

            # Fire a wx.CommandEvent: this generates a
            # wx.wxEVT_COMMAND_CHECKBOX_CLICKED event that can be caught by the
            # developer by doing something like:
            # MyCheckBox.Bind(wx.EVT_CHECKBOX, self.OnCheckBox)
            checkEvent = wx.CommandEvent(wx.wxEVT_COMMAND_CHECKBOX_CLICKED,
                                         self.GetId())

            # Set the integer event value to 0 (we are switching to unchecked state)
            checkEvent.SetInt(0)

        else:

            # We were unchecked, so we should become checked
            self._checked = True

            checkEvent = wx.CommandEvent(wx.wxEVT_COMMAND_CHECKBOX_CLICKED,
                                         self.GetId())

            # Set the integer event value to 1 (we are switching to checked state)
            checkEvent.SetInt(1)

        # Set the originating object for the event (ourselves)
        checkEvent.SetEventObject(self)

        # Watch for a possible listener of this event that will catch it and
        # eventually process it
        self.GetEventHandler().ProcessEvent(checkEvent)

        # Refresh ourselves: the bitmap has changed
        self.Refresh()


class FloatSpinEvent(wx.PyCommandEvent):

    def __init__(self, evtType, id, object):

        wx.PyCommandEvent.__init__(self, evtType, id)
        self.value = 0
        self.object = object

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        self.value = value

    def GetEventObject(self):
        return self.object

myEVT_MY_SPIN = wx.NewEventType()
EVT_MY_SPIN = wx.PyEventBinder(myEVT_MY_SPIN, 1)


class FloatSpinCtrl(wx.Panel):

    def __init__(self, parent, id, initValue = None, button_style = wx.SP_VERTICAL, TextLength = 40, never_negative = False,  **kwargs):

        wx.Panel.__init__(self, parent, id, **kwargs)

        if initValue == None:
            initValue = '1.00'

        self.defaultScaleDivider = 100
        self.ScaleDivider = 100

        if platform.system() != 'Windows':
            self.ScalerButton = wx.SpinButton(self, -1, style = button_style)
        else:
            self.ScalerButton = wx.SpinButton(self, -1, size = (-1, 22), style = button_style)
        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnFocusChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999)   #Needed for proper function of button on Linux

        if platform.system() != 'Windows':
            self.Scale = wx.TextCtrl(self, -1, initValue, size = (TextLength,-1), style = wx.TE_PROCESS_ENTER)
        else:
            self.Scale = wx.TextCtrl(self, -1, initValue, size = (TextLength,22), style = wx.TE_PROCESS_ENTER)

        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnFocusChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

        self._never_negative = never_negative

        sizer = wx.BoxSizer()

        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)

        self.oldValue = 0

        self.SetSizer(sizer)

        self.ScalerButton.SetValue(0)

    def CastFloatSpinEvent(self):
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId(), self)
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)

    def OnFocusChange(self, event):

        val = self.Scale.GetValue()

        try:
             float(val)
        except ValueError:
            return

        self.CastFloatSpinEvent()

        event.Skip()

    def OnEnter(self, event):
        self.OnScaleChange(None)
        self.Scale.SelectAll()
        self.CastFloatSpinEvent()

        event.Skip()

    def OnScaleChange(self, event):

        val = self.Scale.GetValue()
        val = val.replace(',', '.')

        try:
            self.num_of_digits = len(val.split('.')[1])

            if self.num_of_digits == 0:
                self.ScaleDivider = self.defaultScaleDivider
            else:
                self.ScaleDivider = math.pow(10, self.num_of_digits)

        except IndexError:
            self.ScaleDivider = 1.0
            self.num_of_digits = 0

    def OnSpinUpScale(self, event):

        self.OnScaleChange(None)

        val = self.Scale.GetValue()
        val = val.replace(',', '.')

        # Reset spinbutton counter. Fixes bug on MAC
        if self.ScalerButton.GetValue() > 90000:
            self.ScalerButton.SetValue(0)

        try:
            newval = float(val) + (1/self.ScaleDivider)
        except ValueError:
            self.CastFloatSpinEvent()
            return

        if self.num_of_digits > 0:
            newval_str = ("%." + str(self.num_of_digits) + "f") %  newval
        else:
            newval_str = ("%d") %  newval

        self.Scale.SetValue(newval_str)
        self.CastFloatSpinEvent()

    def _showInvalidNumberError(self):
        wx.CallAfter(wx.MessageBox, 'The entered value is invalid. Please remove non-numeric characters.', 'Invalid Value Error', style = wx.ICON_ERROR)

    def OnSpinDownScale(self, event):

        self.OnScaleChange(None)

        val = self.Scale.GetValue()
        val = val.replace(',', '.')

        # Reset spinbutton counter. Fixes bug on MAC
        if self.ScalerButton.GetValue() < -90000:
            self.ScalerButton.SetValue(0)

        try:
            newval = float(val) - (1/self.ScaleDivider)

            if newval == 0.0 and self._never_negative == True:
                self.num_of_digits = self.num_of_digits + 1
                self.ScaleDivider = math.pow(10, self.num_of_digits)

                newval = float(val) - (1/self.ScaleDivider)

        except ValueError:
            self.CastFloatSpinEvent()
            return

        if self.num_of_digits > 0:
            newval_str = ("%." + str(self.num_of_digits) + "f") %  newval
        else:
            newval_str = ("%d") %  newval

        self.Scale.SetValue(str(newval_str))
        self.CastFloatSpinEvent()

    def GetValue(self):
        value = self.Scale.GetValue()
        return value

    def SetValue(self, value):
        self.Scale.SetValue(value)


class IntSpinCtrl(wx.Panel):

    def __init__(self, parent, id, min = None, max = None, TextLength = 40, **kwargs):

        wx.Panel.__init__(self, parent, id, **kwargs)

        if platform.system() != 'Windows':
            self.ScalerButton = wx.SpinButton(self, -1, style = wx.SP_VERTICAL)
        else:
            self.ScalerButton = wx.SpinButton(self, -1, size=(-1,22), style = wx.SP_VERTICAL)

        self.ScalerButton.Bind(wx.EVT_SET_FOCUS, self.OnScaleChange)
        self.ScalerButton.Bind(wx.EVT_SPIN_UP, self.OnSpinUpScale)
        self.ScalerButton.Bind(wx.EVT_SPIN_DOWN, self.OnSpinDownScale)
        self.ScalerButton.SetRange(-99999, 99999)
        self.max = max
        self.min = min

        if platform.system() != 'Windows':
            self.Scale = wx.TextCtrl(self, -1, str(min), size = (TextLength,-1), style = wx.TE_PROCESS_ENTER)
        else:
            self.Scale = wx.TextCtrl(self, -1, str(min), size = (TextLength,22), style = wx.TE_PROCESS_ENTER)

        self.Scale.Bind(wx.EVT_KILL_FOCUS, self.OnScaleChange)
        self.Scale.Bind(wx.EVT_TEXT_ENTER, self.OnScaleChange)

        sizer = wx.BoxSizer()

        sizer.Add(self.Scale, 0, wx.RIGHT, 1)
        sizer.Add(self.ScalerButton, 0)

        self.oldValue = 0

        self.SetSizer(sizer)

        self.ScalerButton.SetValue(0)

    def CastFloatSpinEvent(self):
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId(), self)
        event.SetValue( self.Scale.GetValue() )
        self.GetEventHandler().ProcessEvent(event)

    def OnScaleChange(self, event):
        self.ScalerButton.SetValue(0) # Resit spinbutton position for button to work in linux

        val = self.Scale.GetValue()

        try:
            float(val)
        except ValueError:
            return

        if self.max is not None:
            if float(val) > self.max:
                self.Scale.SetValue(str(self.max))
        if self.min is not None:
            if float(val) < self.min:
                self.Scale.SetValue(str(self.min))

        #if val != self.oldValue:
        self.oldValue = val
        self.CastFloatSpinEvent()

        event.Skip()

    def OnSpinUpScale(self, event):
        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update

        val = self.Scale.GetValue()
        try:
            float(val)
        except ValueError:
            if self.min is not None:
                val = self.min -1
            elif self.max is not None:
                val = self.max -1
            else:
                return

        newval = int(val) + 1

        # Reset spinbutton counter. Fixes bug on MAC
        if self.ScalerButton.GetValue() > 90000:
            self.ScalerButton.SetValue(0)

        #print self.min, self.max, val, self.ScalerButton.GetMax(), self.ScalerButton.GetValue()

        if self.max is not None:
            if newval > self.max:
                self.Scale.SetValue(str(self.max))
            else:
                self.Scale.SetValue(str(newval))
        else:
            self.Scale.SetValue(str(newval))

        self.oldValue = newval
        wx.CallAfter(self.CastFloatSpinEvent)

    def OnSpinDownScale(self, event):
        #self.ScalerButton.SetValue(80)   # This breaks the spinbutton on Linux
        self.ScalerButton.SetFocus()    # Just to remove focus from the bgscaler to throw kill_focus event and update

        val = self.Scale.GetValue()

        try:
            float(val)
        except ValueError:
            if self.max is not None:
                val = self.max +1
            elif self.min is not None:
                val = self.min +1
            else:
                return

        newval = int(val) - 1

        # Reset spinbutton counter. Fixes bug on MAC
        if self.ScalerButton.GetValue() < -90000:
            self.ScalerButton.SetValue(0)

        if self.min is not None:
            if newval < self.min:
                self.Scale.SetValue(str(self.min))
            else:
                self.Scale.SetValue(str(newval))
        else:
            self.Scale.SetValue(str(newval))

        self.oldValue = newval
        wx.CallAfter(self.CastFloatSpinEvent)


    def GetValue(self):
        value = self.Scale.GetValue()

        try:
            return int(value)
        except ValueError:
            return value

    def SetValue(self, value):
        self.Scale.SetValue(str(value))

    def SetRange(self, minmax):
        self.max = minmax[1]
        self.min = minmax[0]

    def GetRange(self):
        return (self.min, self.max)

class CustomConsoleHandler(logging.Handler):
    """Sends logger output to a queue
    Based on code from:
    https://www.blog.pythonlibrary.org/2013/08/09/wxpython-how-to-redirect-pythons-logging-module-to-a-textctrl/
    """

    #----------------------------------------------------------------------
    def __init__(self, queue):
        """"""
        logging.Handler.__init__(self)
        self.queue = queue

    #----------------------------------------------------------------------
    def emit(self, record):
        """Constructor"""
        msg = self.format(record)
        self.queue.put_nowait(msg + "\n")
        self.flush()


class RawPanelFileDropTarget(wx.FileDropTarget):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, window, style):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.style = style

    #----------------------------------------------------------------------
    def OnDropFiles(self, x, y, filenames):
        """
        When files are dropped, write where they were dropped and then
        the file paths themselves
        """
        if self.style == 'main' or self.style == 'ift':
            RAWGlobals.mainworker_cmd_queue.put(['plot', filenames])
        elif self.style == 'sec':
            frame_list = range(len(filenames))
            RAWGlobals.mainworker_cmd_queue.put(['sec_plot', [filenames, frame_list]])

        return True

class RawPlotFileDropTarget(wx.FileDropTarget):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, window, style):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.style = style

    #----------------------------------------------------------------------
    def OnDropFiles(self, x, y, filenames):
        """
        When files are dropped, write where they were dropped and then
        the file paths themselves
        """
        if self.style == 'main':
            if self.window.subplot1.get_visible() and self.window.subplot2.get_visible():
                #both plots shown
                x1, y1 = self.window.fig.transFigure.transform((0,0))
                x2, y2 = self.window.fig.transFigure.transform((1,1))

                if y < (y2-y1)/2.:
                    RAWGlobals.mainworker_cmd_queue.put(['plot_specific', [filenames, 1]])
                elif y > (y2-y1)/2.:
                    RAWGlobals.mainworker_cmd_queue.put(['plot_specific', [filenames, 2]])
                else:
                    RAWGlobals.mainworker_cmd_queue.put(['plot_specific', [filenames, 1]])

            elif self.window.subplot1.get_visible() and not self.window.subplot2.get_visible():
                #only plot one shown
                RAWGlobals.mainworker_cmd_queue.put(['plot_specific', [filenames, 1]])
            elif not self.window.subplot1.get_visible() and self.window.subplot2.get_visible():
                #only plot two shown
                RAWGlobals.mainworker_cmd_queue.put(['plot_specific', [filenames, 2]])
        elif self.style == 'ift':
            RAWGlobals.mainworker_cmd_queue.put(['plot', filenames])
        elif self.style == 'sec':
            frame_list = range(len(filenames))
            RAWGlobals.mainworker_cmd_queue.put(['sec_plot', [filenames, frame_list]])
        elif self.style == 'image':
            RAWGlobals.mainworker_cmd_queue.put(['show_image', [filenames[0], 0]])

        return True

class ItemList(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self._create_layout()

        self.all_items = []
        self.selected_items = []
        self.modified_items = []
        self._marked_item = None

    def _create_layout(self):
        self.list_panel = wx.ScrolledWindow(self, style=wx.BORDER_SUNKEN)
        self.list_panel.SetScrollRate(20,20)

        self.list_panel.SetBackgroundColour('white')

        self.list_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_panel.SetSizer(self.list_panel_sizer)

        toolbar_sizer = self._create_toolbar()
        button_sizer = self._create_buttons()

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        if toolbar_sizer is not None:
            panel_sizer.Add(toolbar_sizer, border=5, flag=wx.LEFT|wx.RIGHT|wx.EXPAND)
        panel_sizer.Add(self.list_panel, proportion=1, border=3,
            flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.EXPAND)
        if button_sizer is not None:
            panel_sizer.Add(button_sizer, border=10, flag=wx.EXPAND|wx.ALIGN_CENTER|wx.ALL)

        self.SetSizer(panel_sizer)

    def _create_toolbar(self):
        return None

    def _create_buttons(self):
        return None

    def create_items(self):
        pass

    def resize_list(self):
        self.list_panel.SetVirtualSize(self.list_panel.GetBestVirtualSize())
        self.list_panel.Layout()
        self.list_panel.Refresh()

    def add_items(self, items):
        for item in items:
            self.list_panel_sizer.Add(item, flag=wx.EXPAND)
            self.all_items.append(item)

        self.resize_list

    def mark_item(self, item):
        self._marked_item = item

    def get_marked_item(self):
        return self._marked_item

    def clear_marked_item(self):
        self._marked_item = None

    def clear_list(self):
        self._marked_item = None
        self.selected_items = []
        self.modified_items = []

        remaining_items = []

        for item in self.all_items:
            try:
                item.Destroy()
            except Exception:
                remaining_items.append(item)

        self.all_items = remaining_items

        self.resize_list()

    def get_selected_items(self):
        self.selected_items = []

        for item in self.all_items:
            if item.get_selected():
                self.selected_items.append(item)

        return self.selected_items

    def select_all(self):
        for item in self.all_items:
            item.set_selected(True)

    def deselect_all_but_one(self, sel_item):
        selected_items = self.get_selected_items()

        for item in selected_items:
            if item is not sel_item:
                item.set_selected(False)

    def select_to_item(self, sel_item):
        selected_items = self.get_selected_items()

        sel_idx = self.get_item_index(sel_item)

        first_idx = self.get_item_index(selected_items[0])

        if sel_item in selected_items:
            for item in self.all_items[first_idx:sel_idx]:
                item.set_selected(False)
        else:
            if sel_idx < first_idx:
                for item in self.all_items[sel_idx:first_idx]:
                    item.set_selected(True)
            else:
                last_idx = self.get_item_index(selected_items[-1])
                for item in self.all_items[last_idx+1:sel_idx+1]:
                    item.set_selected(True)

    def remove_items(self, items):
        for item in items:
            item.remove()

            if item in self.modified_items:
                self.modified_items.remove(item)

            if item in self.selected_items:
                self.selected_items.remove(item)

            self.all_items.remove(item)

            item.Destroy()

        self.resize_list()

    def remove_selected_items(self):
        selected_items = self.get_selected_items()

        if len(selected_items) > 0:
            self.remove_items(selected_items)

    def get_items(self):
        return self.all_items

    def get_item_index(self, item):
        return self.all_items.index(item)

class ListItem(wx.Panel):
    def __init__(self, item_list, *args, **kwargs):
        wx.Panel.__init__(self, *args, style=wx.BORDER_RAISED, **kwargs)

        self._selected = False

        self.item_list = item_list

        self.text_list = []

        self._create_layout()

        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_mouse_btn)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_right_mouse_btn)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_press)

    def _create_layout(self):
        pass

    def get_selected(self):
        return self._selected

    def set_selected(self, selected):
        self._selected = selected

        if self._selected:
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
            bkg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            self.SetBackgroundColour(bkg_color)

            for text_item in self.text_list:
                text_item.SetForegroundColour(text_color)

        else:
            self.SetBackgroundColour(wx.Colour(250,250,250))
            for text_item in self.text_list:
                text_item.SetForegroundColour('black')

        self.Refresh()

    def toggle_selected(self):
        self.set_selected(not self._selected)

    def remove(self):
        pass

    def _on_left_mouse_btn(self, event):
        if self.IsEnabled():
            ctrl_is_down = event.CmdDown()
            shift_is_down = event.ShiftDown()

            if shift_is_down:
                self.item_list.select_to_item(self)
            elif ctrl_is_down:
                self.toggle_selected()
            else:
                self.item_list.deselect_all_but_one(self)
                self.toggle_selected()

    def _on_right_mouse_btn(self, event):
        pass

    def _on_key_press(self, event):
        pass

class CustomPlotToolbar(NavigationToolbar2WxAgg):
    """
    A custom plot toolbar that displays the cursor position (or other text)
    in addition to the usual controls.
    """
    def __init__(self, canvas):
        """
        Initializes the toolbar.

        :param wx.Window parent: The parent window
        :param matplotlib.Canvas: The canvas associated with the toolbar.
        """
        NavigationToolbar2WxAgg.__init__(self, canvas)

        self.status = wx.StaticText(self, label='')

        self.AddControl(self.status)

    def set_status(self, status):
        """
        Called to set the status text in the toolbar, i.e. the cursor position
        on the plot.
        """
        self.status.SetLabel(status)

#Monkey patch flatNB.PageContainer
def OnPaintFNB(self, event):
    """
    Handles the ``wx.EVT_PAINT`` event for :class:`PageContainer`.

    :param `event`: a :class:`PaintEvent` event to be processed.
    """

    if wx.version().split()[0].strip()[0] == '4' and self.GetContentScaleFactor() > 1:
        dc = wx.PaintDC(self)
    else:
        dc = wx.BufferedPaintDC(self)

    parent = self.GetParent()

    renderer = self._mgr.GetRenderer(parent.GetAGWWindowStyleFlag())
    renderer.DrawTabs(self, dc)

    if self.HasAGWFlag(flatNB.FNB_HIDE_ON_SINGLE_TAB) and len(self._pagesInfoVec) <= 1 or \
       self.HasAGWFlag(flatNB.FNB_HIDE_TABS) or parent._orientation or \
       (parent._customPanel and len(self._pagesInfoVec) == 0):
        self.Hide()
        self.GetParent()._mainSizer.Layout()
        self.Refresh()

flatNB.PageContainer.OnPaint = OnPaintFNB


#Monkey patch ULC.UltimateListHeaderWindow

def OnPaintULCHeader(self, event):
    """
    Handles the ``wx.EVT_PAINT`` event for :class:`UltimateListHeaderWindow`.
    :param `event`: a :class:`PaintEvent` event to be processed.
    """

    if wx.version().split()[0].strip()[0] == '4' and self.GetContentScaleFactor() > 1:
        dc = wx.PaintDC(self)
    else:
        dc = wx.BufferedPaintDC(self)
    # width and height of the entire header window
    w, h = self.GetClientSize()
    w, dummy = self._owner.CalcUnscrolledPosition(w, 0)
    dc.SetBrush(wx.Brush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)))
    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.DrawRectangle(0, -1, w, h+2)

    self.AdjustDC(dc)

    dc.SetBackgroundMode(wx.TRANSPARENT)
    dc.SetTextForeground(self.GetForegroundColour())

    x = ULC.HEADER_OFFSET_X

    numColumns = self._owner.GetColumnCount()
    item = ULC.UltimateListItem()
    renderer = wx.RendererNative.Get()
    enabled = self.GetParent().IsEnabled()
    virtual = self._owner.IsVirtual()
    isFooter = self._isFooter

    for i in range(numColumns):

        # Reset anything in the dc that a custom renderer might have changed
        dc.SetTextForeground(self.GetForegroundColour())

        if x >= w:
            break

        if not self.IsColumnShown(i):
            continue # do next column if not shown

        item = self._owner.GetColumn(i)
        wCol = item._width

        cw = wCol
        ch = h

        flags = 0
        if not enabled:
            flags |= wx.CONTROL_DISABLED

        # NB: The code below is not really Mac-specific, but since we are close
        # to 2.8 release and I don't have time to test on other platforms, I
        # defined this only for wxMac. If this behavior is desired on
        # other platforms, please go ahead and revise or remove the #ifdef.

        if "__WXMAC__" in wx.PlatformInfo:
            if not virtual and item._mask & ULC.ULC_MASK_STATE and item._state & ULC.ULC_STATE_SELECTED:
                flags |= wx.CONTROL_SELECTED

        if i == 0:
           flags |= wx.CONTROL_SPECIAL # mark as first column

        if i == self._currentColumn:
            if self._leftDown:
                flags |= wx.CONTROL_PRESSED
            else:
                if self._enter:
                    flags |= wx.CONTROL_CURRENT

        # the width of the rect to draw: make it smaller to fit entirely
        # inside the column rect
        header_rect = wx.Rect(x-1, ULC.HEADER_OFFSET_Y-1, cw-1, ch)

        if self._headerCustomRenderer != None:
           self._headerCustomRenderer.DrawHeaderButton(dc, header_rect, flags)

           # The custom renderer will specify the color to draw the header text and buttons
           dc.SetTextForeground(self._headerCustomRenderer.GetForegroundColour())

        elif item._mask & ULC.ULC_MASK_RENDERER:
           item.GetCustomRenderer().DrawHeaderButton(dc, header_rect, flags)

           # The custom renderer will specify the color to draw the header text and buttons
           dc.SetTextForeground(item.GetCustomRenderer().GetForegroundColour())
        else:
            renderer.DrawHeaderButton(self, dc, header_rect, flags)


        # see if we have enough space for the column label
        if isFooter:
            if item.GetFooterFont().IsOk():
                dc.SetFont(item.GetFooterFont())
            else:
                dc.SetFont(self.GetFont())
        else:
            if item.GetFont().IsOk():
                dc.SetFont(item.GetFont())
            else:
                dc.SetFont(self.GetFont())

        wcheck = hcheck = 0
        kind = (isFooter and [item.GetFooterKind()] or [item.GetKind()])[0]
        checked = (isFooter and [item.IsFooterChecked()] or [item.IsChecked()])[0]

        if kind in [1, 2]:
            # We got a checkbox-type item
            ix, iy = self._owner.GetCheckboxImageSize()
            # We draw it on the left, always
            self._owner.DrawCheckbox(dc, x + ULC.HEADER_OFFSET_X, ULC.HEADER_OFFSET_Y + (h - 4 - iy)/2, kind, checked, enabled)
            wcheck += ix + ULC.HEADER_IMAGE_MARGIN_IN_REPORT_MODE
            cw -= ix + ULC.HEADER_IMAGE_MARGIN_IN_REPORT_MODE

        # for this we need the width of the text
        text = (isFooter and [item.GetFooterText()] or [item.GetText()])[0]
        wLabel, hLabel, dummy = dc.GetFullMultiLineTextExtent(text)
        wLabel += 2*ULC.EXTRA_WIDTH

        # and the width of the icon, if any
        image = (isFooter and [item._footerImage] or [item._image])[0]

        if image:
            imageList = self._owner._small_image_list
            if imageList:
                for img in image:
                    if img >= 0:
                        ix, iy = imageList.GetSize(img)
                        wLabel += ix + ULC.HEADER_IMAGE_MARGIN_IN_REPORT_MODE

        else:

            imageList = None

        # ignore alignment if there is not enough space anyhow
        align = (isFooter and [item.GetFooterAlign()] or [item.GetAlign()])[0]
        align = (wLabel < cw and [align] or [ULC.ULC_FORMAT_LEFT])[0]

        if align == ULC.ULC_FORMAT_LEFT:
            xAligned = x + wcheck

        elif align == ULC.ULC_FORMAT_RIGHT:
            xAligned = x + cw - wLabel - ULC.HEADER_OFFSET_X

        elif align == ULC.ULC_FORMAT_CENTER:
            xAligned = x + wcheck + (cw - wLabel)/2

        # if we have an image, draw it on the right of the label
        if imageList:
            for indx, img in enumerate(image):
                if img >= 0:
                    imageList.Draw(img, dc,
                                   xAligned + wLabel - (ix + ULC.HEADER_IMAGE_MARGIN_IN_REPORT_MODE)*(indx+1),
                                   ULC.HEADER_OFFSET_Y + (h - 4 - iy)/2,
                                   wx.IMAGELIST_DRAW_TRANSPARENT)

                    cw -= ix + ULC.HEADER_IMAGE_MARGIN_IN_REPORT_MODE

        # draw the text clipping it so that it doesn't overwrite the column
        # boundary
        dc.SetClippingRegion(x, ULC.HEADER_OFFSET_Y, cw, h - 4)
        self.DrawTextFormatted(dc, text, wx.Rect(xAligned+ULC.EXTRA_WIDTH, ULC.HEADER_OFFSET_Y, cw-ULC.EXTRA_WIDTH, h-4))

        x += wCol
        dc.DestroyClippingRegion()

    # Fill in what's missing to the right of the columns, otherwise we will
    # leave an unpainted area when columns are removed (and it looks better)
    if x < w:
        header_rect = wx.Rect(x, ULC.HEADER_OFFSET_Y, w - x, h)
        if self._headerCustomRenderer != None:
            # Why does the custom renderer need this adjustment??
            header_rect.x = header_rect.x - 1
            header_rect.y = header_rect.y - 1
            self._headerCustomRenderer.DrawHeaderButton(dc, header_rect, wx.CONTROL_SPECIAL)
        else:
            renderer.DrawHeaderButton(self, dc, header_rect, wx.CONTROL_SPECIAL) # mark as last column

ULC.UltimateListHeaderWindow.OnPaint = OnPaintULCHeader

#Monkey patch ULC.UltimateListMainWindow

def OnPaintULCMain(self, event):
    """
    Handles the ``wx.EVT_PAINT`` event for :class:`UltimateListMainWindow`.

    :param `event`: a :class:`PaintEvent` event to be processed.
    """

    # Note: a wxPaintDC must be constructed even if no drawing is
    # done (a Windows requirement).
    if wx.version().split()[0].strip()[0] == '4' and self.GetContentScaleFactor() > 1:
        dc = wx.PaintDC(self)
    else:
        dc = wx.BufferedPaintDC(self)

    dc.SetBackgroundMode(wx.TRANSPARENT)

    self.PrepareDC(dc)

    dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.Clear()

    self.TileBackground(dc)
    self.PaintWaterMark(dc)

    if self.IsEmpty():
        # nothing to draw or not the moment to draw it
        return

    if self._dirty:
        # delay the repainting until we calculate all the items positions
        self.RecalculatePositions(False)

    useVista, useGradient = self._vistaselection, self._usegradients
    dev_x, dev_y = self.CalcScrolledPosition(0, 0)

    dc.SetFont(self.GetFont())

    if self.InReportView():
        visibleFrom, visibleTo = self.GetVisibleLinesRange()

        # mrcs: draw additional items
        if visibleFrom > 0:
            visibleFrom -= 1

        if visibleTo < self.GetItemCount() - 1:
            visibleTo += 1

        xOrig = dc.LogicalToDeviceX(0)
        yOrig = dc.LogicalToDeviceY(0)

        # tell the caller cache to cache the data
        if self.IsVirtual():

            evCache = ULC.UltimateListEvent(ULC.wxEVT_COMMAND_LIST_CACHE_HINT, self.GetParent().GetId())
            evCache.SetEventObject(self.GetParent())
            evCache.m_oldItemIndex = visibleFrom
            evCache.m_itemIndex = visibleTo
            self.GetParent().GetEventHandler().ProcessEvent(evCache)

        no_highlight = self.HasAGWFlag(ULC.ULC_NO_HIGHLIGHT)

        for line in range(visibleFrom, visibleTo+1):
            rectLine = self.GetLineRect(line)

            if not self.IsExposed(rectLine.x + xOrig, rectLine.y + yOrig, rectLine.width, rectLine.height):
                # don't redraw unaffected lines to avoid flicker
                continue

            theLine = self.GetLine(line)
            enabled = theLine.GetItem(0, ULC.CreateListItem(line, 0)).IsEnabled()
            oldPN, oldBR = dc.GetPen(), dc.GetBrush()
            theLine.DrawInReportMode(dc, line, rectLine,
                                     self.GetLineHighlightRect(line),
                                     self.IsHighlighted(line) and not no_highlight,
                                     line==self._current, enabled, oldPN, oldBR)

        if self.HasAGWFlag(ULC.ULC_HRULES):
            pen = wx.Pen(self.GetRuleColour(), 1, wx.PENSTYLE_SOLID)
            clientSize = self.GetClientSize()

            # Don't draw the first one
            start = (visibleFrom > 0 and [visibleFrom] or [1])[0]

            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            for i in range(start, visibleTo+1):
                lineY = self.GetLineY(i)
                dc.DrawLine(0 - dev_x, lineY, clientSize.x - dev_x, lineY)

            # Draw last horizontal rule
            if visibleTo == self.GetItemCount() - 1:
                lineY = self.GetLineY(visibleTo) + self.GetLineHeight(visibleTo)
                dc.SetPen(pen)
                dc.SetBrush(wx.TRANSPARENT_BRUSH)
                dc.DrawLine(0 - dev_x, lineY, clientSize.x - dev_x , lineY)

        # Draw vertical rules if required
        if self.HasAGWFlag(ULC.ULC_VRULES) and not self.IsEmpty():
            pen = wx.Pen(self.GetRuleColour(), 1, wx.PENSTYLE_SOLID)

            firstItemRect = self.GetItemRect(visibleFrom)
            lastItemRect = self.GetItemRect(visibleTo)
            x = firstItemRect.GetX()
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            for col in range(self.GetColumnCount()):

                if not self.IsColumnShown(col):
                    continue

                colWidth = self.GetColumnWidth(col)
                x += colWidth

                x_pos = x - dev_x
                if col < self.GetColumnCount()-1:
                    x_pos -= 2

                dc.DrawLine(x_pos, firstItemRect.GetY() - 1 - dev_y, x_pos, lastItemRect.GetBottom() + 1 - dev_y)


    else: # !report

        for i in range(self.GetItemCount()):
            self.GetLine(i).Draw(i, dc)

    if wx.Platform not in ["__WXMAC__", "__WXGTK__"]:
        # Don't draw rect outline under Mac at all.
        # Draw it elsewhere on GTK
        if self.HasCurrent():
            if self._hasFocus and not self.HasAGWFlag(ULC.ULC_NO_HIGHLIGHT) and not useVista and not useGradient \
               and not self.HasAGWFlag(ULC.ULC_BORDER_SELECT) and not self.HasAGWFlag(ULC.ULC_NO_FULL_ROW_SELECT):
                dc.SetPen(wx.BLACK_PEN)
                dc.SetBrush(wx.TRANSPARENT_BRUSH)
                dc.DrawRectangle(self.GetLineHighlightRect(self._current))

ULC.UltimateListMainWindow.OnPaint = OnPaintULCMain


#Monkey patch agw supertooltip.ToolTipWindowBase

def OnPaintSTT(self, event):
    """
    Handles the ``wx.EVT_PAINT`` event for :class:`SuperToolTip`.
    If the `event` parameter is ``None``, calculates best size and returns it.
    :param `event`: a :class:`PaintEvent` event to be processed or ``None``.
    """

    maxWidth = 0
    if event is None:
        dc = wx.ClientDC(self)
    else:
        # Go with double buffering...
        if wx.version().split()[0].strip()[0] == '4' and self.GetContentScaleFactor() > 1:
            dc = wx.PaintDC(self)
        else:
            dc = wx.BufferedPaintDC(self)

    frameRect = self.GetClientRect()
    x, y, width, _height = frameRect
    # Store the rects for the hyperlink lines
    self._hyperlinkRect, self._hyperlinkWeb = [], []
    classParent = self._classParent

    # Retrieve the colours for the blended triple-gradient background
    topColour, middleColour, bottomColour = classParent.GetTopGradientColour(), \
                                            classParent.GetMiddleGradientColour(), \
                                            classParent.GetBottomGradientColour()

    # Get the user options for header, bitmaps etc...
    drawHeader, drawFooter = classParent.GetDrawHeaderLine(), classParent.GetDrawFooterLine()
    topRect = wx.Rect(frameRect.x, frameRect.y, frameRect.width, frameRect.height/2)
    bottomRect = wx.Rect(frameRect.x, frameRect.y+frameRect.height/2, frameRect.width, frameRect.height/2+1)
    # Fill the triple-gradient
    dc.GradientFillLinear(topRect, topColour, middleColour, wx.SOUTH)
    dc.GradientFillLinear(bottomRect, middleColour, bottomColour, wx.SOUTH)

    header, headerBmp = classParent.GetHeader(), classParent.GetHeaderBitmap()
    headerFont, messageFont, footerFont, hyperlinkFont = classParent.GetHeaderFont(), classParent.GetMessageFont(), \
                                                         classParent.GetFooterFont(), classParent.GetHyperlinkFont()

    yPos = 0
    bmpXPos = 0
    bmpHeight = textHeight = bmpWidth = 0

    if headerBmp and headerBmp.IsOk():
        # We got the header bitmap
        bmpHeight, bmpWidth = headerBmp.GetHeight(), headerBmp.GetWidth()
        bmpXPos = self._spacing

    if header:
        # We got the header text
        dc.SetFont(headerFont)
        textWidth, textHeight = dc.GetTextExtent(header)
        maxWidth = max(bmpWidth+(textWidth+self._spacing*3), maxWidth)
    # Calculate the header height
    height = max(textHeight, bmpHeight)
    if header:
        dc.DrawText(header, bmpXPos+bmpWidth+self._spacing, (height-textHeight+self._spacing)/2)
    if headerBmp and headerBmp.IsOk():
        dc.DrawBitmap(headerBmp, bmpXPos, (height-bmpHeight+self._spacing)/2, True)

    if header or (headerBmp and headerBmp.IsOk()):
        yPos += height
        if drawHeader:
            # Draw the separator line after the header
            dc.SetPen(wx.GREY_PEN)
            dc.DrawLine(self._spacing, yPos+self._spacing, width-self._spacing, yPos+self._spacing)
            yPos += self._spacing

    maxWidth = max(bmpXPos + bmpWidth + self._spacing, maxWidth)
    # Get the big body image (if any)
    embeddedImage = classParent.GetBodyImage()
    bmpWidth = bmpHeight = -1
    if embeddedImage and embeddedImage.IsOk():
        bmpWidth, bmpHeight = embeddedImage.GetWidth(), embeddedImage.GetHeight()

    # A bunch of calculations to draw the main body message
    messageHeight = 0
    lines = classParent.GetMessage().split("\n")
    yText = yPos
    embImgPos = yPos
    normalText = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUTEXT)
    hyperLinkText = wx.BLUE
    messagePos = self._getTextExtent(dc, lines[0] if lines else "")[1] // 2 + self._spacing
    for line in lines:
        # Loop over all the lines in the message
        if line.startswith("<hr>"):     # draw a line
            yText += self._spacing * 2
            dc.DrawLine(self._spacing, yText+self._spacing, width-self._spacing, yText+self._spacing)
        else:
            isLink = False
            dc.SetTextForeground(normalText)
            if line.startswith("</b>"):      # is a bold line
                line = line[4:]
                font = STT.MakeBold(messageFont)
                dc.SetFont(font)
            elif line.startswith("</l>"):    # is a link
                dc.SetFont(hyperlinkFont)
                isLink = True
                line, hl = STT.ExtractLink(line)
                dc.SetTextForeground(hyperLinkText)
            else:
                # Is a normal line
                dc.SetFont(messageFont)

            textWidth, textHeight = self._getTextExtent(dc, line)

            messageHeight += textHeight

            xText = (bmpWidth + 2 * self._spacing) if bmpWidth > 0 else self._spacing
            yText += textHeight/2+self._spacing
            maxWidth = max(xText + textWidth + self._spacing, maxWidth)
            dc.DrawText(line, xText, yText)
            if isLink:
                self._storeHyperLinkInfo(xText, yText, textWidth, textHeight, hl)

    toAdd = 0
    if bmpHeight > messageHeight:
        yPos += 2*self._spacing + bmpHeight
        toAdd = self._spacing
    else:
        yPos += messageHeight + 2*self._spacing

    yText = max(messageHeight, bmpHeight+2*self._spacing)
    if embeddedImage and embeddedImage.IsOk():
        # Draw the main body image
        dc.DrawBitmap(embeddedImage, self._spacing, embImgPos + (self._spacing * 2), True)

    footer, footerBmp = classParent.GetFooter(), classParent.GetFooterBitmap()
    bmpHeight = bmpWidth = textHeight = textWidth = 0
    bmpXPos = 0

    if footerBmp and footerBmp.IsOk():
        # Got the footer bitmap
        bmpHeight, bmpWidth = footerBmp.GetHeight(), footerBmp.GetWidth()
        bmpXPos = self._spacing

    if footer:
        # Got the footer text
        dc.SetFont(footerFont)
        textWidth, textHeight = dc.GetTextExtent(footer)

    if textHeight or bmpHeight:
        if drawFooter:
            # Draw the separator line before the footer
            dc.SetPen(wx.GREY_PEN)
            dc.DrawLine(self._spacing, yPos-self._spacing/2+toAdd,
                        width-self._spacing, yPos-self._spacing/2+toAdd)
    # Draw the footer and footer bitmap (if any)
    dc.SetTextForeground(normalText)
    height = max(textHeight, bmpHeight)
    yPos += toAdd
    if footer:
        toAdd = (height - textHeight + self._spacing) // 2
        dc.DrawText(footer, bmpXPos + bmpWidth + self._spacing, yPos + toAdd)
        maxWidth = max(bmpXPos + bmpWidth + (self._spacing*2) + textWidth, maxWidth)
    if footerBmp and footerBmp.IsOk():
        toAdd = (height - bmpHeight + self._spacing) / 2
        dc.DrawBitmap(footerBmp, bmpXPos, yPos + toAdd, True)
        maxWidth = max(footerBmp.GetSize().GetWidth() + bmpXPos, maxWidth)

    maxHeight = yPos + height + toAdd
    if event is None:
        return maxWidth, maxHeight

STT.ToolTipWindowBase.OnPaint = OnPaintSTT


# ----------------------------------------------------------------------------
# Auto-wrapping static text class
# ----------------------------------------------------------------------------
class AutoWrapStaticText(StaticText):
    """
    A simple class derived from :mod:`lib.stattext` that implements auto-wrapping
    behaviour depending on the parent size.
    .. versionadded:: 0.9.5
    Code from: https://github.com/wxWidgets/Phoenix/blob/master/wx/lib/agw/infobar.py
    Original author: Andrea Gavana
    """
    def __init__(self, parent, label):
        """
        Defsult class constructor.
        :param Window parent: a subclass of :class:`Window`, must not be ``None``;
        :param string `label`: the :class:`AutoWrapStaticText` text label.
        """
        StaticText.__init__(self, parent, wx.ID_ANY, label, style=wx.ST_NO_AUTORESIZE)
        self.label = label
        # colBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK)
        # self.SetBackgroundColour(colBg)
        # self.SetOwnForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT))

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSize)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.OnSize)

    def OnSize(self, event):
        """
        Handles the ``wx.EVT_SIZE`` event for :class:`AutoWrapStaticText`.
        :param `event`: a :class:`SizeEvent` event to be processed.
        """
        event.Skip()
        self.Wrap(event.GetSize().width)

    def Wrap(self, width):
        """
        This functions wraps the controls label so that each of its lines becomes at
        most `width` pixels wide if possible (the lines are broken at words boundaries
        so it might not be the case if words are too long).
        If `width` is negative, no wrapping is done.
        :param integer `width`: the maximum available width for the text, in pixels.
        :note: Note that this `width` is not necessarily the total width of the control,
        since a few pixels for the border (depending on the controls border style) may be added.
        """
        if width < 0:
           return
        self.Freeze()

        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        text = wordwrap(self.label, width, dc)
        self.SetLabel(text, wrapped=True)

        self.Thaw()

    def SetLabel(self, label, wrapped=False):
        """
        Sets the :class:`AutoWrapStaticText` label.
        All "&" characters in the label are special and indicate that the following character is
        a mnemonic for this control and can be used to activate it from the keyboard (typically
        by using ``Alt`` key in combination with it). To insert a literal ampersand character, you
        need to double it, i.e. use "&&". If this behaviour is undesirable, use `SetLabelText` instead.
        :param string `label`: the new :class:`AutoWrapStaticText` text label;
        :param bool `wrapped`: ``True`` if this method was called by the developer using :meth:`~AutoWrapStaticText.SetLabel`,
        ``False`` if it comes from the :meth:`~AutoWrapStaticText.OnSize` event handler.
        :note: Reimplemented from :class:`PyControl`.
        """

        if not wrapped:
            self.label = label

        StaticText.SetLabel(self, label)
