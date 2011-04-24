"""
Usage:
    python setup.py build
"""

from cx_Freeze import setup, Executable, sys

exe = Executable(
    script="RAW.py",
#    base="Win32GUI",
    )

includes = ['_lbfgsb', 'flapack', 'scipy.optimize._lbfgsb']
path = sys.path + ['C:/Python27/Lib/site-packages/scipy/optimize'] + ['C:/Python27/Lib/site-packages/scipy/linalg']

setup(
      
    options = {
    "build_exe" : {"includes": includes,
                   "path" : path}},
    name = "RAW",
    version = "0.1",
    description = "An example wxPython script",
    executables = [exe]
    
    )    
    
    
