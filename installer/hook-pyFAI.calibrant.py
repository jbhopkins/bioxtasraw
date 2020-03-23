import os.path

from PyInstaller.utils.hooks import collect_data_files

calibration_files = collect_data_files('pyFAI', subdir = os.path.join('resources', 'calibration'))

datas = calibration_files
