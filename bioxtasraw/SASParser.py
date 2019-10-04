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

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import math

class PyMathParser(object):
    '''
    Taken from http://www.bestcode.com/html/evaluate_math_expressions_pyth.html

    Mathematical Expression Evaluator class.
    You can set the expression member, set the functions, variables and then call
    evaluate() function that will return you the result of the mathematical expression
    given as a string.
    '''

    '''
    Mathematical expression to evaluate.
    '''
    expression = ''

    '''
    Dictionary of functions that can be used in the expression.
    '''
    functions = {'__builtins__':None};

    '''
    Dictionary of variables that can be used in the expression.
    '''
    variables = {'__builtins__':None};

    def __init__(self):
        '''
        Constructor
        '''

    def evaluate(self):
        '''
        Evaluate the mathematical expression given as a string in the expression member variable.

        '''
        return eval(self.expression, self.variables, self.functions);

    def addSpecialVariables(self, var_dict):

        if var_dict == None:
            return

        for each_key in var_dict:

            try:
                val = float(var_dict[each_key])
                self.variables[each_key] = val
            except:
                pass

    def addDefaultFunctions(self):
        '''
        Add the following Python functions to be used in a mathemtical expression:
        acos
        asin
        atan
        atan2
        ceil
        cos
        cosh
        degrees
        exp
        fabs
        floor
        fmod
        frexp
        hypot
        ldexp
        log
        log10
        modf
        pow
        radians
        sin
        sinh
        sqrt
        tan
        tanh
        '''
        self.functions['acos']=math.acos
        self.functions['asin']=math.asin
        self.functions['atan']=math.atan
        self.functions['atan2']=math.atan2
        self.functions['ceil']=math.ceil
        self.functions['cos']=math.cos
        self.functions['cosh']=math.cosh
        self.functions['degrees']=math.degrees
        self.functions['exp']=math.exp
        self.functions['fabs']=math.fabs
        self.functions['floor']=math.floor
        self.functions['fmod']=math.fmod
        self.functions['frexp']=math.frexp
        self.functions['hypot']=math.hypot
        self.functions['ldexp']=math.ldexp
        self.functions['log']=math.log
        self.functions['log10']=math.log10
        self.functions['modf']=math.modf
        self.functions['pow']=pow
        self.functions['radians']=math.radians
        self.functions['sin']=math.sin
        self.functions['sinh']=math.sinh
        self.functions['sqrt']=math.sqrt
        self.functions['tan']=math.tan
        self.functions['tanh']=math.tanh

    def addDefaultVariables(self):
        '''
        Add e and pi to the list of defined variables.
        '''
        #self.variables['e']=e
        self.variables['pi']=math.pi

    def getVariableNames(self):
        '''
        Return a List of defined variables names in sorted order.
        '''
        mylist = list(self.variables.keys())
        try:
            mylist.remove('__builtins__')
        except ValueError:
            pass
        mylist.sort()
        return mylist


    def getFunctionNames(self):
        '''
        Return a List of defined function names in sorted order.
        '''
        mylist = list(self.functions.keys())
        try:
            mylist.remove('__builtins__')
        except ValueError:
            pass
        mylist.sort()
        return mylist
