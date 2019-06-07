import platform

opsys = platform.system()

if opsys == 'Windows':
    try:
        from setuptools import setup
        from setuptools import Extension
    except ImportError:
        from distutils.core import setup
        from distutils.extension import Extension
else:
    from distutils.core import setup
    from distutils.extension import Extension

from Cython.Build import cythonize

setup(
    ext_modules = cythonize("bioxtasraw/sascalc_exts.pyx")
)

# Run this command to build the extensions:
# python setup.py build_ext --inplace
