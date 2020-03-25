"""
Created on March 17, 2020

@author: Jesse Hopkins

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

This file contains functions used in several places in the program that don't really
fit anywhere else.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

from ctypes import c_uint32, cdll, c_int, c_void_p, POINTER, byref
import ctypes.util
import atexit
import platform
import copy

try:
    import dbus
except Exception:
    pass

import pyFAI

def get_det_list():

    extra_det_list = ['detector']

    final_dets = pyFAI.detectors.ALL_DETECTORS

    for key in extra_det_list:
        if key in final_dets:
            final_dets.pop(key)

    for key in copy.copy(list(final_dets.keys())):
        if '_' in key:
            reduced_key = ''.join(key.split('_'))
            if reduced_key in final_dets:
                final_dets.pop(reduced_key)

    det_list = list(final_dets.keys()) + [str('Other')]
    det_list = sorted(det_list, key=str.lower)

    return det_list


class SleepInhibit(object):
    def __init__(self):
        self.platform = platform.system()

        if self.platform == 'Darwin':
            self.sleep_inhibit = MacOSSleepInhibit()

        elif self.platform == 'Windows':
            self.sleep_inhibit = WindowsSleepInhibit()

        elif self.platform == 'Linux':
            self.sleep_inhibit = LinuxSleepInhibit()

        else:
            self.sleep_inhibit = None

        self.sleep_count = 0

    def on(self):
        print('turning sleep inhibit on')
        if self.sleep_inhibit is not None:
            self.sleep_inhibit.on()
            self.sleep_count = self.sleep_count + 1

    def off(self):
        print('turning sleep inhibit off')
        if self.sleep_inhibit is not None:
            self.sleep_count = self.sleep_count - 1

            if self.sleep_count <= 0:
                self.sleep_inhibit.off()

    def force_off(self):
        if self.sleep_inhibit is not None:
            self.sleep_inhibit.off()


class MacOSSleepInhibit(object):
    """
    Code adapted from the python caffeine module here:
    https://github.com/jpn--/caffeine

    Used with permission under MIT license
    """

    def __init__(self):
        self.libIOKit = ctypes.cdll.LoadLibrary(ctypes.util.find_library('IOKit'))
        self.cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library('CoreFoundation'))
        self.libIOKit.IOPMAssertionCreateWithName.argtypes = [ c_void_p, c_uint32, c_void_p, POINTER(c_uint32) ]
        self.libIOKit.IOPMAssertionRelease.argtypes = [ c_uint32 ]
        self.cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32]
        self.cf.CFStringCreateWithCString.restype = ctypes.c_void_p

        self.kCFStringEncodingUTF8 = 0x08000100
        self._kIOPMAssertionLevelOn = 255
        self._IOPMAssertionRelease = self.libIOKit.IOPMAssertionRelease
        self._assertion = None
        self.reason = "RAW running long process"

        self._assertID = c_uint32(0)
        self._errcode = None

        atexit.register(self.off)

    def _CFSTR(self, py_string):
        return self.cf.CFStringCreateWithCString(None, py_string.encode('utf-8'), self.kCFStringEncodingUTF8)

    def _IOPMAssertionCreateWithName(self, assert_name, assert_level, assert_msg):
        assertID = c_uint32(0)
        p_assert_name = self._CFSTR(assert_name)
        p_assert_msg = self._CFSTR(assert_msg)
        errcode = self.libIOKit.IOPMAssertionCreateWithName(p_assert_name,
            assert_level, p_assert_msg, byref(assertID))
        return (errcode, assertID)

    def _assertion_type(self, display):
        if display:
            return 'NoDisplaySleepAssertion'
        else:
            return "NoIdleSleepAssertion"

    def on(self, display=False):
        # Stop idle sleep
        a = self._assertion_type(display)
        # if a != self._assertion:
        #     self.off()
        if self._assertID.value ==0:
            self._errcode, self._assertID = self._IOPMAssertionCreateWithName(a,
        self._kIOPMAssertionLevelOn, self.reason)

    def off(self):
        self._errcode = self._IOPMAssertionRelease(self._assertID)
        self._assertID.value = 0


class WindowsSleepInhibit(object):
    """
    Prevent OS sleep/hibernate in windows; code from:
    https://github.com/h3llrais3r/Deluge-PreventSuspendPlus/blob/master/preventsuspendplus/core.py
    and
    https://trialstravails.blogspot.com/2017/03/preventing-windows-os-from-sleeping.html
    API documentation:
    https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx
    """

    def __init__(self):
        self.ES_CONTINUOUS = 0x80000000
        self.ES_SYSTEM_REQUIRED = 0x00000001

    def on(self):
        ctypes.windll.kernel32.SetThreadExecutionState(
            self.ES_CONTINUOUS | \
            self.ES_SYSTEM_REQUIRED)

    def off(self):
        ctypes.windll.kernel32.SetThreadExecutionState(
            self.ES_CONTINUOUS)

# For linux
class LinuxSleepInhibit(object):
    """
    Based on code from:
    https://github.com/h3llrais3r/Deluge-PreventSuspendPlus
    """
    def __init__(self):
        self.sleep_inhibitor = None
        self.get_inhibitor()


    def get_inhibitor(self):
        try:
            #Gnome session inhibitor
            self.sleep_inhibitor = GnomeSessionInhibitor()
            return
        except Exception:
            pass

        try:
            #Free desktop inhibitor
            self.sleep_inhibitor = DBusInhibitor('org.freedesktop.PowerManagement',
                '/org/freedesktop/PowerManagement/Inhibit',
                'org.freedesktop.PowerManagement.Inhibit')
            return
        except Exception:
            pass

        try:
            #Gnome inhibitor
            self.sleep_inhibitor = DBusInhibitor('org.gnome.PowerManager',
                '/org/gnome/PowerManager',
                'org.gnome.PowerManager')
            return
        except Exception:
            pass

    def on(self):
        if self.sleep_inhibitor is not None:
            self.sleep_inhibitor.inhibit()

    def off(self):
        self.sleep_inhibitor.uninhibit()

class DBusInhibitor:
    def __init__(self, name, path, interface, method=['Inhibit', 'UnInhibit']):
        self.name = name
        self.path = path
        self.interface_name = interface

        bus = dbus.SessionBus()
        devobj = bus.get_object(self.name, self.path)
        self.iface = dbus.Interface(devobj, self.interface_name)
        # Check we have the right attributes
        self._inhibit = getattr(self.iface, method[0])
        self._uninhibit = getattr(self.iface, method[1])

    def inhibit(self):
        self.cookie = self._inhibit(APPNAME, REASON)

    def uninhibit(self):
        self._uninhibit(self.cookie)


class GnomeSessionInhibitor(DBusInhibitor):
    TOPLEVEL_XID = 0
    INHIBIT_SUSPEND = 4

    def __init__(self):
        DBusInhibitor.__init__(self, 'org.gnome.SessionManager',
                               '/org/gnome/SessionManager',
                               'org.gnome.SessionManager',
                               ['Inhibit', 'Uninhibit'])

    def inhibit(self):
        log.info('Inhibit (prevent) suspend mode')
        self.cookie = self._inhibit(APPNAME,
                                    GnomeSessionInhibitor.TOPLEVEL_XID,
                                    REASON,
                                    GnomeSessionInhibitor.INHIBIT_SUSPEND)
