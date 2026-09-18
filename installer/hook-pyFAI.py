import os

from PyInstaller.utils.hooks import collect_data_files

hiddenimports = [
    "pyFAI.ext.splitBBox_common",
    "pyFAI.ext.splitpixel_common",
    "pyFAI.ext._tree",
]

# sensors_files = collect_data_files('pyFAI', subdir = os.path.join('resources', 'sensors'))
# elem_files = collect_data_files('pyFAI', subdir = os.path.join('resources', 'elements'))
# calibration_files = collect_data_files('pyFAI', subdir = os.path.join('resources', 'calibration'))
# opencl_files = collect_data_files('pyFAI', subdir = os.path.join('resources', 'openCL'))

# datas = sensors_files + elem_files + calibration_files + opencl_files

# This is future proof and silx is not that large. If I find it gets too big
# in the future then we can reconsider grabbing just what we need.

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("pyFAI")
