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
import six
from six.moves import cPickle as pickle

from ctypes import c_uint32, c_void_p, POINTER, byref
import ctypes.util
import atexit
import platform
import copy
import os
import subprocess
import glob
import json
import sys
import math
import time

import numpy as np
import matplotlib as mpl
import matplotlib.font_manager as fm
import pyFAI

try:
    import wx
except Exception:
    pass #Installed as API

try:
    import dbus
except Exception:
    pass



#NOTE: SASUtils should never import another RAW module besides RAWGlobals, to avoid circular imports.
raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWGlobals as RAWGlobals


def loadFileDefinitions():
    file_defs = {'hdf5' : {}}
    errors = []

    if os.path.exists(os.path.join(RAWGlobals.RAWDefinitionsDir, 'hdf5')):
        def_files = glob.glob(os.path.join(RAWGlobals.RAWDefinitionsDir, 'hdf5', '*'))
        for fname in def_files:
            file_def, error = loadHDF5Definition(fname)

            if file_def is not None:
                file_defs['hdf5'][os.path.splitext(os.path.basename(fname))[0]] = file_def

            if error is not None:
                errors.append(error)

    return file_defs, errors

def loadHDF5Definition(fname):
    error = None

    try:
        with open(fname, 'r') as f:
            file_def = f.read()
            file_def = dict(json.loads(file_def))

    except Exception:
        file_def = None
        error = fname

    return file_def, error

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
        if self.sleep_inhibit is not None:
            try:
                self.sleep_inhibit.on()
                self.sleep_count = self.sleep_count + 1
            except Exception:
                pass

    def off(self):
        if self.sleep_inhibit is not None:
            self.sleep_count = self.sleep_count - 1

            if self.sleep_count <= 0:
                try:
                    self.sleep_inhibit.off()
                except Exception:
                    pass

    def force_off(self):
        if self.sleep_inhibit is not None:
            try:
                self.sleep_inhibit.off()
            except Exception:
                pass

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
        if self.sleep_inhibitor is not None:
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
        self.cookie = self._inhibit('Bioxtas RAW', 'long_process')

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
        self.cookie = self._inhibit('Bioxtas RAW',
                                    GnomeSessionInhibitor.TOPLEVEL_XID,
                                    'long_process',
                                    GnomeSessionInhibitor.INHIBIT_SUSPEND)


def findATSASDirectory():
    opsys= platform.system()

    if opsys== 'Darwin':
        dirs = glob.glob(os.path.expanduser('~/ATSAS*'))
        if len(dirs) > 0:
            try:
                versions = {}
                for item in dirs:
                    atsas_dir = os.path.split(item)[1]
                    version = atsas_dir.lstrip('ATSAS-')
                    versions[version] = item

                max_version = get_max_version(versions, True)

                default_path = versions[max_version]

            except Exception:
                default_path = dirs[0]

            default_path = os.path.join(default_path, 'bin')

        else:
            default_path = '/Applications/ATSAS/bin'

    elif opsys== 'Windows':
        dirs = glob.glob(os.path.expanduser('C:\\Program Files (x86)\\ATSAS*'))
        dirs2 = glob.glob(os.path.expanduser('C:\\Program Files\\ATSAS*'))
        dirs += dirs2

        if len(dirs) > 0:
            try:
                versions = {}
                for item in dirs:
                    atsas_dir = os.path.split(item)[1]
                    version = atsas_dir.lstrip('ATSAS-')
                    versions[version] = item

                max_version = get_max_version(versions, False)

                default_path = versions[max_version]

            except Exception:
                default_path = dirs[0]

            default_path = os.path.join(default_path, 'bin')

        else:
            default_path = 'C:\\atsas\\bin'

    elif opsys== 'Linux':
        default_path = '~/atsas'
        default_path = os.path.expanduser(default_path)

        if os.path.exists(default_path):
            dirs = glob.glob(default_path+'/*')

            for item in dirs:
                if item.split('/')[-1].lower().startswith('atsas'):
                    default_path = item
                    break

            default_path = os.path.join(default_path, 'bin')

    is_path = os.path.exists(default_path)

    if is_path:
        return default_path

    if opsys == 'Windows':
        which = subprocess.Popen('where dammif', stdout=subprocess.PIPE,shell=True)
        output = which.communicate()

        atsas_path = output[0].strip()

    else:
        which = subprocess.Popen('which dammif', stdout=subprocess.PIPE,shell=True)
        output = which.communicate()

        atsas_path = output[0].strip()

    if isinstance(atsas_path, bytes):
        atsas_path = atsas_path.decode('utf-8')

    if atsas_path != '':
        return os.path.dirname(atsas_path)

    try:
        path = os.environ['PATH']
    except Exception:
        path = None

    if path is not None:
        if opsys == 'Windows':
            split_path = path.split(';')
        else:
            split_path = path.split(':')

        for item in split_path:
            if item.lower().find('atsas') > -1 and item.lower().find('bin') > -1:
                if os.path.exists(item):
                    return item

    try:
        atsas_path = os.environ['ATSAS']
    except Exception:
        atsas_path = None

    if atsas_path is not None:
        if atsas_path.lower().find('atsas') > -1:
            atsas_path = atsas_path.rstrip('\\')
            atsas_path = atsas_path.rstrip('/')
            if atsas_path.endswith('bin'):
                return atsas_path
            else:
                if os.path.exists(os.path.join(atsas_path, 'bin')):
                        return os.path.join(atsas_path, 'bin')

    return ''

def get_max_version(versions, use_sub_minor):
    if use_sub_minor:
        max_version = '0.0.0-0'
    else:
        max_version = '0.0.0'
    for version in versions:
        if int(max_version.split('.')[0]) < int(version.split('.')[0]):
            max_version = version

        if (int(max_version.split('.')[0]) == int(version.split('.')[0])
            and int(max_version.split('.')[1]) < int(version.split('.')[1])):
            max_version = version

        if (int(max_version.split('.')[0]) == int(version.split('.')[0])
            and int(max_version.split('.')[1]) == int(version.split('.')[1])
            and int(max_version.split('.')[2].split('-')[0]) < int(version.split('.')[2].split('-')[0])):
            max_version = version

        if use_sub_minor:
            if (int(max_version.split('.')[0]) == int(version.split('.')[0])
                and int(max_version.split('.')[1]) == int(version.split('.')[1])
                and int(max_version.split('.')[2].split('-')[0]) == int(version.split('.')[2].split('-')[0])
                and int(max_version.split('-')[1]) < int(version.split('-')[1])):
                max_version = version

    return max_version


#This class goes with write header, and was lifted from:
#https://stackoverflow.com/questions/27050108/convert-numpy-type-to-python/27050186#27050186
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)

def find_global(module, name):
    if module == 'SASImage':
        module = 'bioxtasraw.SASMask'

        if name == 'RectangleMask':
            name = '_oldMask'
        elif name == 'CircleMask':
            name = '_oldMask'
        elif name == 'PolygonMask':
            name = '_oldMask'

    __import__(module)
    mod = sys.modules[module]

    klass = getattr(mod, name)
    return klass

if six.PY3:
    class SafeUnpickler(pickle.Unpickler):
        find_class = staticmethod(find_global)

def signal_handler(sig, frame):
    main_frame = wx.Window.FindWindowByName('MainFrame')
    main_frame.cleanup_and_quit_forced()


def load_DIP_bitmap(filepath, bitmap_type):
    if platform.system() == 'Darwin':
        bmp = wx.Bitmap(filepath, bitmap_type)
    else:

        try:
            content_scale = wx.GetApp().GetTopWindow().GetDPIScaleFactor()
        except Exception:
            content_scale = wx.GetApp().GetTopWindow().GetContentScaleFactor()

        img_scale = math.ceil(content_scale)

        img = None

        current_scale = img_scale

        while current_scale > 1:
            path, ext = os.path.splitext(filepath)
            imgpath = '{}@{}x{}'.format(path, current_scale, ext)
            if os.path.isfile(imgpath):
                img = wx.Image(imgpath, bitmap_type)
                break
            else:
                current_scale = current_scale -1

        if img is None:
            img = wx.Image(filepath, bitmap_type)

        # Should I rescale for intermediate resolutions? Or just have larger crisp icons?
        w, h = img.GetSize()
        extra_scale = content_scale/current_scale
        img.Rescale(int(w*extra_scale), int(h*extra_scale))

        bmp = wx.Bitmap(img)

    return bmp

def load_DIP_image(filepath, bitmap_type):
    if platform.system() == 'Darwin':
        img = wx.Image(filepath, bitmap_type)
    else:

        try:
            content_scale = wx.GetApp().GetTopWindow().GetDPIScaleFactor()
        except Exception:
            content_scale = wx.GetApp().GetTopWindow().GetContentScaleFactor()

        img_scale = math.ceil(content_scale)

        img = None

        current_scale = img_scale

        while current_scale > 1:
            path, ext = os.path.splitext(filepath)
            imgpath = '{}@{}x{}'.format(path, current_scale, ext)
            if os.path.isfile(imgpath):
                img = wx.Image(imgpath, bitmap_type)
                break
            else:
                current_scale = current_scale -1

        if img is None:
            img = wx.Image(filepath, bitmap_type)

        # Should I rescale for intermediate resolutions? Or just have larger crisp icons?
        w, h = img.GetSize()
        extra_scale = content_scale/current_scale
        img.Rescale(int(w*extra_scale), int(h*extra_scale))

    return img

def set_best_size(window, shrink=False):

    best_size = window.GetBestSize()
    current_size = window.GetSize()

    client_display = wx.GetClientDisplayRect()

    best_width = min(best_size.GetWidth(), client_display.Width)
    best_height = min(best_size.GetHeight(), client_display.Height)

    if best_size.GetWidth() > current_size.GetWidth():
        best_size.SetWidth(best_width)
    else:
        if not shrink:
            best_size.SetWidth(current_size.GetWidth())
        else:
            best_size.SetWidth(best_width)

    if best_size.GetHeight() > current_size.GetHeight():
        best_size.SetHeight(best_height)
    else:
        if not shrink:
            best_size.SetHeight(current_size.GetHeight())
        else:
            best_size.SetHeight(best_height)

    window.SetSize(best_size)


def find_closest(val, array):
    argmin = np.argmin(np.absolute(array-val))

    return array[argmin], argmin

def sphere_intensity(q, R):
    """
    Scattering for a sphere
    """
    return (4*np.pi*R**3/3)**2*(3*np.pi*(np.sin(q*R)-(q*R)*np.cos(q*R))/(q*R)**3)**2

def get_mpl_fonts():

        fonts = []

        mpl_flist = fm.fontManager.ttflist

        for f in mpl_flist:
            if f.name != 'System Font' and not f.name.startswith('.') and f.name not in fonts:
                fonts.append(f.name)

        fonts = sorted(fonts)

        possible_fonts = mpl.rcParams['font.'+mpl.rcParams['font.family'][0]]

        found_font = False
        i = 0

        default_plot_font = None
        while not found_font and i in range(len(possible_fonts)):
            test_font = possible_fonts[i]

            if test_font in fonts:
                default_plot_font = test_font
                found_font = True

            i = i + 1

        if default_plot_font is None:
            default_plot_font = 'Arial'

        return fonts, default_plot_font

def update_mpl_style(forced=None):

    if forced is None:
        system_settings = wx.SystemSettings()

        try:
            system_appearance = system_settings.GetAppearance()
            is_dark = system_appearance.IsDark()
        except Exception:
            is_dark = False

    elif forced == 'light':
        is_dark = False

    else:
        is_dark = True

    if is_dark:
        mpl.style.use('dark_background')
        color = 'white'
    else:
        mpl.style.use('default')
        color = 'black'

    if int(mpl.__version__.split('.')[0]) >= 2:
        mpl.rcParams['errorbar.capsize'] = 3

    mpl.rc('mathtext', default='regular')
    mpl.rc('image', origin = 'lower')
    mpl.rcParams['backend'] = 'WxAgg'

    return color

def enqueue_output(proc, queue, read_semaphore):
    #Solution for non-blocking reads adapted from stack overflow
    #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python

    with read_semaphore:
        out = proc.stdout
        line = ''
        line2=''
        while proc.poll() is None:
            line = out.read(1)

            if not isinstance(line, str):
                line = str(line, encoding='UTF-8')

            line2+=line
            if line == '\n':
                queue.put_nowait([line2])
                line2=''
            time.sleep(0.00001)

        line = out.read(1)

        if not isinstance(line, str):
            line = str(line, encoding='UTF-8')

        line2 += line
        queue.put_nowait([line2])

def guess_units(q, val=None, is_dmax=True):

    if val is not None:
        if not is_dmax:
            val = val*3

    if val is not None:
        if q[0] > 0.015 and q[-1] > 2 and val < 150:
            units = '1/nm'
        else:
            units = '1/A'

    else:
        if q[0] > 0.015 and q[-1] > 2:
            units = '1/nm'
        else:
            units = '1/A'

    return units
