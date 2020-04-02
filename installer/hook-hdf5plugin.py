from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files('hdf5plugin')
binaries = collect_dynamic_libs('hdf5plugin')