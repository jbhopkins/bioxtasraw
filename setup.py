from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize("bioxtasraw/sascalc_exts.pyx")
)

# Run this command to build the extensions:
# python setup.py build_ext --inplace
