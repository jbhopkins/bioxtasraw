import os.path

from PyInstaller.utils.hooks import collect_data_files

calibration_files = collect_data_files('silx', subdir=os.path.join('resources', 'opencl'))

datas = calibration_files
