'''
Unit tests for PyMathParser.
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