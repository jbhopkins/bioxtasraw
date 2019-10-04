"""Polygon geometry.

Copyright (C) 2006, Robert Hetland
Copyright (C) 2006, Stefan van der Walt

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the
   distribution.
3. The name of the author may not be used to endorse or promote
   products derived from this software without specific prior written
   permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map
from io import open

import sys

import numpy as np
from numba import jit

@jit(nopython=True, cache=True)
def npnpoly(verts,points):
    """Check whether given points are in the polygon.

    points - Nx2 array

    See http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
    """
    out = np.empty_like(points[:,0], dtype=np.bool_)

    xpi = verts[:,0]
    ypi = verts[:,1]

    xmin = min(xpi)
    xmax = max(xpi)
    ymin = min(ypi)
    ymax = max(ypi)
    # shift
    xpj = xpi[np.arange(xpi.size)-1]
    ypj = ypi[np.arange(ypi.size)-1]
    maybe = np.empty(len(xpi),dtype=np.bool_)
    for i in range(points.shape[0]):
        x,y = points[i]

        if (x<xmin or xmax<x) or (y<ymin or ymax<y):
            out[i] = 0
        else:
            maybe[:] = ((ypi <= y) & (y < ypj)) | ((ypj <= y) & (y < ypi))

            out[i] = np.sum(x < (xpj[maybe]-xpi[maybe])*(y - ypi[maybe]) \
                           / (ypj[maybe] - ypi[maybe]) + xpi[maybe]) % 2

    return out



class Polygeom(np.ndarray):
    """
    Polygeom -- Polygon geometry class
    """

    def __new__(self, verts):
        """
        Given xp and yp (both 1D arrays or sequences), create a new polygon.

        p = Polygon(vertices) where vertices is an Nx2 array

        p.inside(x, y) - Calculate whether points lie inside the polygon.
        p.area() - The area enclosed by the polygon.
        p.centroid() - The centroid of the polygon
        """
        verts = np.atleast_2d(verts)

        assert verts.shape[1] == 2, 'Vertices should be an Nx2 array, but is %s' % str(verts.shape)
        assert len(verts) >= 3, 'Need 3 vertices to create polygon.'

        # close polygon, if needed
        if not np.all(verts[0]==verts[-1]):
            verts = np.vstack((verts,verts[0]))

        self.verts = verts

        return verts.view(Polygeom).copy()


    def inside(self,points):
        points = np.atleast_2d(points)

        assert points.shape[1] == 2, \
               "Points should be of shape Nx2, is %s" % str(points.shape)
        return npnpoly(self.verts,points).astype(bool)

    def get_area(self):
        """
        Return the area of the polygon.

        From Paul Bourke's webpage:
          http://astronomy.swin.edu.au/~pbourke/geometry
        """
        v = self.verts
        v_first = v[:-1][:,[1,0]]
        v_second = v[1:]
        return np.diff(v_first*v_second).sum()/2.0

    def get_centroid(self):
        "Return the centroid of the polygon"
        v = self.verts
        a = np.diff(v[:-1][:,[1,0]]*v[1:])
        area = a.sum()/2.0
        return ((v[:-1,:] + v[1:,:])*a).sum(axis=0) / (6.0*area)

    area = property(get_area)
    centroid = property(get_centroid)

def getCoords(p, dims):
    (xDim, yDim) = dims

    points = []
    for each in p[0]:

        y = int(each // xDim)
        x = each % xDim

        #points.append( (abs(yDim-x), y) )    #Damn that x,y is really y,x thing..

        # ARGH! there is a major screwup between x,y somewhere.. this works in RAW: but masking test need the one above
        points.append( (x, y) )    #Damn that x,y is really y,x thing..

    return points

if __name__ == '__main__':
    import pylab as pl

    #grid = np.mgrid[0:1:10j,0:1:10j].reshape(2,-1).swapaxes(0,1)

    grid = np.mgrid[0:10,0:10].reshape(2,-1).swapaxes(0,1)
    # simple area test

    verts = np.array([[0.0,0.0],
                      [0.0,5.0],
                      [6.0,0.0]])

    pb = Polygeom(verts)
    inside = pb.inside(grid)
    print(inside)

    p = np.where(inside==True)
    coords = getCoords(p, (10, 10))

    print(coords)

    tst = np.zeros((10,10))
    for each in coords:
        tst[each] = 1
    print(tst)


#    # concave enclosure test-case for inside.
#    verts = np.array([[0.15,0.15],
#                      [0.25,0.15],
#                      [0.45,0.15],
#                      [0.45,0.25],
#                      [0.25,0.25],
#                      [0.25,0.55],
#                      [0.65,0.55],
#                      [0.65,0.15],
#                      [0.85,0.15],
#                      [0.85,0.85]])
#    pb = Polygeom(verts)
#    inside = pb.inside(grid)
    pl.plot(grid[:,0][inside], grid[:,1][inside], 'g.')
    pl.plot(grid[:,0][~inside], grid[:,1][~inside],'r.')
    pl.plot(pb.verts[:,0],pb.verts[:,1], '-k')
    print(pb.centroid)
    xc, yc = pb.centroid
    print(xc, yc)
    pl.plot([xc], [yc], 'co')
    pl.show()

    pl.figure()
    # many points in a semicircle, to test speed.
    grid = np.mgrid[0:1:1000j,0:1:1000j].reshape(2,-1).swapaxes(0,1)
    xp = np.sin(np.arange(0,np.pi,0.01))
    yp = np.cos(np.arange(0,np.pi,0.01))
    pc = Polygeom(np.hstack([xp[:,np.newaxis],yp[:,np.newaxis]]))
    print("%d points inside %d vertex poly..." % (grid.size//2,len(verts)), end='')
    sys.stdout.flush()
    inside = pc.inside(grid)
    print("done.")
    pl.plot(grid[:,0][inside], grid[:,1][inside], 'g+')
    pl.plot(grid[:,0][~inside], grid[:,1][~inside], 'r.')
    pl.plot(pc.verts[:,0], pc.verts[:,1], '-k')
    xc, yc = pc.centroid
    print(xc, yc)
    pl.plot([xc], [yc], 'co')
    pl.show()
#


