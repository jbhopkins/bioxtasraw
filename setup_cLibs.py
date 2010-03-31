'''
Created on Mar 18, 2010

@author: specuser
'''

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

ext_modules = [Extension("hello", ["hello.pyx"], libraries=["m"], include_dirs=[numpy.get_include()])]

setup(
  name = 'Hello world app',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules
  )
