from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import math

"""
The following code impliments the pairwise probability test for differences in curves,
known as the CORMAP test. It is taken and slightly modified from the freesas project:
https://github.com/kif/freesas
and used under the MIT license

Information from the original module:
__author__ = "Jerome Kieffer"
__license__ = "MIT"
__copyright__ = "2017, ESRF"
"""

class LongestRunOfHeads(object):
    """Implements the "longest run of heads" by Mark F. Schilling
    The College Mathematics Journal, Vol. 21, No. 3, (1990), pp. 196-207

    See: http://www.maa.org/sites/default/files/pdf/upload_library/22/Polya/07468342.di020742.02p0021g.pdf
    """
    def __init__(self):
        "We store already calculated values for (n,c)"
        self.knowledge = {}

    def A(self, n, c):
        """Calculate A(number_of_toss, length_of_longest_run)

        :param n: number of coin toss in the experiment, an integer
        :param c: length of the longest run of
        :return: The A parameter used in the formula

        """
        if n <= c:
            return 2 ** n
        elif (n, c) in self.knowledge:
            return self.knowledge[(n, c)]
        else:
            s = 0
            for j in range(c, -1, -1):
                s += self.A(n - 1 - j, c)
            self.knowledge[(n, c)] = s
            return s

    def B(self, n, c):
        """Calculate B(number_of_toss, length_of_longest_run)
        to have either a run of Heads either a run of Tails

        :param n: number of coin toss in the experiment, an integer
        :param c: length of the longest run of
        :return: The B parameter used in the formula
        """
        return 2 * self.A(n - 1, c - 1)

    def __call__(self, n, c):
        """Calculate the probability of a longest run of head to occur

        :param n: number of coin toss in the experiment, an integer
        :param c: length of the longest run of heads, an integer
        :return: The probablility of having c subsequent heads in a n toss of fair coin
        """
        if c >= n:
            return 0
        delta = 2 ** n - self.A(n, c)
        if delta <= 0:
            return 0
        return min(2.0**(math.log(delta, 2) - n), 1.0)

    def probaB(self, n, c):
        """Calculate the probability of a longest run of head or tails to occur

        :param n: number of coin toss in the experiment, an integer
        :param c: length of the longest run of heads or tails, an integer
        :return: The probablility of having c subsequent heads or tails in a n toss of fair coin
        """

        """Adjust C, because probability calc. is done for a run >
        than c. So in this case, we want to know probability of c, means
        we need to calculate probability of a run of length >c-1
        """
        c=c-1
        if c >= n:
            return 0
        delta = 2**n - self.B(n, c)
        if delta <= 0:
            return 0
        return min(2.0**(math.log(delta, 2) - n), 1.0)

LROH = LongestRunOfHeads()
