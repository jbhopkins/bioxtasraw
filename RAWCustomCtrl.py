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

import wx
import math
import platform
import logging
import RAWIcons
# import time

class ColourIndicator(wx.PyControl):
    """
    A custom class that shows the colour of the line plot.
    """

    def __init__(self, parent, id=wx.ID_ANY, color = 'black', pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.NO_BORDER, validator=wx.DefaultValidator,
                 name="ColourIndicator"):

        wx.PyControl.__init__(self, parent, id, pos, size, style, validator, name)

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
    return wx.BitmapFromImage(GetCheckedImage())

def GetCheckedImage():

    image = RAWIcons.checked.GetImage()
    return image

#----------------------------------------------------------------------

def GetNotCheckedBitmap():
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


class CustomCheckBox(wx.PyControl):
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

        wx.PyControl.__init__(self, parent, id, pos, size, style, validator, name)

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

        wx.PyControl.SetLabel(self, label)

        # The text label has changed, so we must recalculate our best size
        # and refresh ourselves.
        self.InvalidateBestSize()
        self.Refresh()


    def SetFont(self, font):
        """
        Sets the CustomCheckBox text font and updates the control's size to
        exactly fit the label plus the bitmap.
        """

        wx.PyControl.SetFont(self, font)

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

        wx.PyControl.SetForegroundColour(self, colour)

        # We have to re-initialize the focus indicator per colour as it should
        # always be the same as the foreground colour
        self.InitializeColours()
        self.Refresh()


    def SetBackgroundColour(self, colour):
        """ Overridden base class virtual. """

        wx.PyControl.SetBackgroundColour(self, colour)

        # We have to refresh ourselves
        self.Refresh()


    def Enable(self, enable=True):
        """ Enables/Disables CustomCheckBox. """

        wx.PyControl.Enable(self, enable)

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

        dc.SetFont(self.GetFont())

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
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
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
        event = FloatSpinEvent(myEVT_MY_SPIN, self.GetId())
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

class DraggableLegend:
    def __init__(self, legend, ax):
        self.subplot = ax

        self.legend = legend
        self.gotLegend = False

        self.legend.set_axes(self.subplot)
        legend.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
        legend.figure.canvas.mpl_connect('pick_event', self.on_pick)
        legend.figure.canvas.mpl_connect('button_release_event', self.on_release)
        legend.set_picker(self.my_legend_picker)

    def on_motion(self, evt):
        if self.gotLegend:
            dx = evt.x - self.mouse_x
            dy = evt.y - self.mouse_y
            loc_in_canvas = self.legend_x + dx, self.legend_y + dy
            loc_in_norm_axes = self.legend.parent.transAxes.inverted().transform_point(loc_in_canvas)
            self.legend._loc = tuple(loc_in_norm_axes)
            self.legend.figure.canvas.draw()

    def my_legend_picker(self, legend, evt):
        self.legend.set_axes(self.subplot)
        return self.legend.legendPatch.contains(evt)

    def on_pick(self, evt):

        if evt.artist == self.legend:
            bbox = self.legend.get_window_extent()
            self.mouse_x = evt.mouseevent.x
            self.mouse_y = evt.mouseevent.y
            self.legend_x = bbox.xmin
            self.legend_y = bbox.ymin
            self.gotLegend = 1

    def on_release(self, event):
        if self.gotLegend:
            self.gotLegend = False



class CustomConsoleHandler(logging.Handler):
    """Sends logger output to a wxpython TextCtrl
    Original code from:
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
