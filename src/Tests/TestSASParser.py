'''
Unit tests for PyMathParser.

#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************
'''
import sys
sys.path.append("..") 
import unittest
import SASParser
from math import *

class Test(unittest.TestCase):

    def setUp(self):
        self.mathparser = SASParser.PyMathParser()
        self.mathparser.addDefaultFunctions()
        self.mathparser.addDefaultVariables()
        self.mathparser.variables['x'] = 1.5;
        self.mathparser.variables['y'] = 2.0;

    def tearDown(self):
        pass

    def testBasic(self):
        self.mathparser.expression = '1+ 2'
        val = self.mathparser.evaluate()
        self.assertEquals(3, val)
        print val

    def testEvalExpression(self):
        self.mathparser.expression = '1+ 2+sin (x+ y)/e+pi'
        print self.mathparser.evaluate()

    def testNegativeFailNoFunction(self):
        self.mathparser.expression = '1+2+sin( x + y)/abc(x)'
        try:
            print self.mathparser.evaluate()
        except NameError as (err):
            if (err.message!="name 'abc' is not defined"):
                raise err
            print 'Expected error: ', err #expected error: name 'abc' is not defined

    def testFunctionNames(self):
        print self.mathparser.getFunctionNames()

    def testVariableNames(self):
        print self.mathparser.getVariableNames()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()