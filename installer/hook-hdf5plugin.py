from PyInstaller.utils.hooks import collect_data_files

calibration_files = collect_data_files('hdf5plugin')

datas = calibration_files