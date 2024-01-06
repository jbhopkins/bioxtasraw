import platform
import codecs
import os.path
import six

if six.PY2:
    language_level ='2'
elif six.PY3:
    language_level = '3'
else:
    language_level = None

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

def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

setup(
    name='bioxtasraw',
    version=get_version('./bioxtasraw/__init__.py'),
    description='A package for processing biological small angle scattering data.',
    url="https://bioxtas-raw.readthedocs.io/en/latest/",
    packages=['bioxtasraw'],
    install_requires=[
        'numpy',
        'scipy',
        'matplotlib',
        'pillow',
        'numba',
        'h5py',
        'cython',
        'numexpr',
        'hdf5plugin',
        'silx',
        'fabio',
        'reportlab',
        'mmcif_pdbx',
        'svglib',
        'pyfai;python_version>"2.7"',
        'pyfai==0.17;python_version=="2.7"',
        'dbus-python;platform_system=="Linux"',
        ],
    ext_modules=cythonize("bioxtasraw/sascalc_exts.pyx",
        language_level=language_level),
    entry_points={
        'gui_scripts': [ 'bioxtas_raw = bioxtasraw.RAW:main']

        }
)

# Run this command to build the extensions:
# python setup.py build_ext --inplace
