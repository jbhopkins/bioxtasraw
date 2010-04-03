'''
Created on Mar 18, 2010

@author: specuser
'''

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

ext_modules = [Extension("CythonTest", ["CythonTest.pyx"], libraries=["m"], include_dirs=[numpy.get_include()])]

setup(
  name = 'Cython test app',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules
  )
