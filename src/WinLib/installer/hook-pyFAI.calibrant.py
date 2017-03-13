from PyInstaller.utils.hooks import collect_data_files

calibration_files = collect_data_files('pyFAI', subdir = 'resources\\calibration')

datas = calibration_files