# import os.path

# from PyInstaller.utils.hooks import collect_data_files

# calibration_files = collect_data_files('silx', subdir=os.path.join('resources', 'opencl'))

# datas = calibration_files

# This is future proof and silx is not that large. If I find it gets too big
# in the future then we can reconsider grabbing just what we need.

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("silx")
