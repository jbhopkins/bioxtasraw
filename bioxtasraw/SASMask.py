"""
Created on March 16, 2020

@author: Jesse Hopkins

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

This file contains masking functions for RAW.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import sys

import numpy as np
from numba import jit

class Mask(object):
    ''' Mask super class. Masking is used for masking out unwanted regions
    of an image '''

    def __init__(self, mask_id, img_dim, mask_type, negative = False):

        self._is_negative_mask = negative
        self._img_dimension = img_dim            # need image Dimentions to get the correct fill points
        self._mask_id = mask_id
        self._type = mask_type
        self._points = None

    def setAsNegativeMask(self):
        self._is_negative_mask = True

    def setAsPositiveMask(self):
        self._is_negative_mask = False

    def isNegativeMask(self):
        return self._is_negative_mask

    def getPoints(self):
        return self._points

    def setPoints(self, points):
        self._points = points

    def setId(self, id):
        self._mask_id = id

    def getId(self):
        return self._mask_id

    def getType(self):
        return self._type

    def getFillPoints(self):
        pass    # overridden when inherited

    def getSaveFormat(self):
        pass   # overridden when inherited

class CircleMask(Mask):
    ''' Create a circular mask '''

    def __init__(self, center_point, radius_point, id, img_dim, negative = False):

        Mask.__init__(self, id, img_dim, 'circle', negative)

        self.setPoints([center_point, radius_point])

    def getRadius(self):
        return self._radius

    def grow(self, pixels):
        ''' Grow the circle by extending the radius by a number
        of pixels '''

        xy_c, xy_r = self._points

        x_c, y_c = xy_c
        x_r, y_r = xy_r

        if x_r > x_c:
            x_r = x_r + pixels
        else:
            x_r = x_r - pixels

        self.setPoints([(x_c,y_c), (x_r,y_r)])

    def shrink(self, pixels):
        ''' Shrink the circle by shortening the radius by a number
        of pixels '''

        xy_c, xy_r = self._points

        x_c, y_c = xy_c
        x_r, y_r = xy_r

        if x_r > x_c:
            x_r = x_r - pixels
        else:
            x_r = x_r + pixels

        self.setPoints([(x_c,y_c), (x_r,y_r)])

    def setPoints(self, points):
        self._points = points
        self._radius = abs(points[1][0] - points[0][0])

        self._calcFillPoints()

    def _calcFillPoints(self):

        radiusC = abs(self._points[1][0] - self._points[0][0])

        P = calcBresenhamCirclePoints(radiusC, self._points[0][1], self._points[0][0])
        self.coords = []

        for i in range(0, len(P)//8):
            Pp = P[i*8 : i*8 + 8]

            q_ud1 = ( Pp[0][0], list(range(int(Pp[1][1]), int(Pp[0][1]+1))) )
            q_ud2 = ( Pp[2][0], list(range(int(Pp[3][1]), int(Pp[2][1]+1))) )

            q_lr1 = ( Pp[4][1], list(range(int(Pp[6][0]), int(Pp[4][0]+1))) )
            q_lr2 = ( Pp[5][1], list(range(int(Pp[7][0]), int(Pp[5][0]+1))) )

            for i in range(0, len(q_ud1[1])):
                self.coords.append( (int(q_ud1[0]), int(q_ud1[1][i])) )
                self.coords.append( (int(q_ud2[0]), int(q_ud2[1][i])) )
                self.coords.append( (int(q_lr1[1][i]), int(q_lr1[0])) )
                self.coords.append( (int(q_lr2[1][i]), int(q_lr2[0])) )

    def getFillPoints(self):
        ''' Really Clumsy! Can be optimized alot! triplicates the points in the middle!'''

        return self.coords

    def getSaveFormat(self):
        save = {'type'          :   self._type,
                'center_point'  :   self._points[0],
                'radius_point'  :   self._points[1],
                'negative'      :   self._is_negative_mask,
                }
        return save

class RectangleMask(Mask):
    ''' create a retangular mask '''

    def __init__(self, first_point, second_point, id, img_dim, negative = False):

        Mask.__init__(self, id, img_dim, 'rectangle', negative)
        self._points = [first_point, second_point]
        self._calcFillPoints()

    def grow(self, pixels):

        xy1, xy2 = self._points

        x1, y1 = xy1
        x2, y2 = xy2

        if x1 > x2:
            x1 = x1 + pixels
            x2 = x2 - pixels
        else:
            x1 = x1 - pixels
            x2 = x2 + pixels

        if y1 > y2:
            y1 = y1 - pixels
            y2 = y2 + pixels
        else:
            y1 = y1 + pixels
            y2 = y2 - pixels

        self._points = [(x1,y1), (x2,y2)]

        self._calcFillPoints()

    def shrink(self):
        ''' NOT IMPLEMENTED YET '''
        pass

    def _calcFillPoints(self):
        startPoint, endPoint = self._points
        '''  startPoint and endPoint: [(x1,y1) , (x2,y2)]  '''

        startPointX = int(startPoint[1])
        startPointY = int(startPoint[0])

        endPointX = int(endPoint[1])
        endPointY = int(endPoint[0])

        self.coords = []

        if startPointX > endPointX:

            if startPointY > endPointY:

                for c in range(endPointY, startPointY + 1):
                    for i in range(endPointX, startPointX + 1):
                        self.coords.append( (int(i), int(c)) )
            else:
                for c in range(startPointY, endPointY + 1):
                    for i in range(endPointX, startPointX + 1):
                        self.coords.append( (int(i), int(c)) )

        else:

            if startPointY > endPointY:

                for c in range(endPointY, startPointY + 1):
                    for i in range(startPointX, endPointX + 1):
                        self.coords.append( (int(i),int(c)) )
            else:
                for c in range(startPointY, endPointY + 1):
                    for i in range(startPointX, endPointX + 1):
                        self.coords.append( (int(i), int(c)) )

    def getFillPoints(self):

        return self.coords

    def getSaveFormat(self):
        save = {'type'          :   self._type,
                'first_point'   :   self._points[0],
                'second_point'  :   self._points[1],
                'negative'      :   self._is_negative_mask,
                }
        return save

class PolygonMask(Mask):
    ''' create a polygon mask '''

    def __init__(self, points, id, img_dim, negative = False):

        Mask.__init__(self, id, img_dim, 'polygon', negative)

        self._points = points

        self._calcFillPoints()

    def _calcFillPoints(self):
        proper_formatted_points = []
        yDim, xDim = self._img_dimension

        for each in self._points:
            proper_formatted_points.append(list(each))

        proper_formatted_points = np.array(proper_formatted_points)

        pb = Polygeom(proper_formatted_points)

        grid = np.mgrid[0:xDim,0:yDim].reshape(2,-1).swapaxes(0,1)

        inside = pb.inside(grid)

        p = np.where(inside==True)

        self.coords = getCoords(p, (int(yDim), int(xDim)))

    def getFillPoints(self):

        return self.coords

    def getSaveFormat(self):
        save = {'type'      :   self._type,
                'vertices'  :   self._points,
                'negative'  :   self._is_negative_mask,
                }
        return save

class _oldMask(object):
    """
    Exists for backwards compatibility for loading old style pickled settings
    with old style object masks.
    """
    pass

def calcBresenhamCirclePoints(radius, xOffset = 0, yOffset = 0):
    ''' Uses the Bresenham circle algorithm for determining the points
     of a circle with a certain radius '''

    x = 0
    y = radius

    switch = 3 - (2 * radius)
    points = []
    while x <= y:
        points.extend([(x + xOffset, y + yOffset),(x + xOffset,-y + yOffset),
                       (-x + xOffset, y + yOffset),(-x + xOffset,-y + yOffset),
                       (y + xOffset, x + yOffset),(y + xOffset,-x + yOffset),
                       (-y + xOffset, x + yOffset),(-y + xOffset, -x + yOffset)])
        if switch < 0:
            switch = switch + (4 * x) + 6
        else:
            switch = switch + (4 * (x - y)) + 10
            y = y - 1
        x = x + 1

    return points

def createMaskMatrix(img_dim, masks):
    ''' creates a 2D binary matrix of the same size as the image,
    corresponding to the mask pattern '''

    negmasks = []
    posmasks = []
    neg = False

    for each in masks:
        if each.isNegativeMask() == True:
            neg = True
            negmasks.append(each)
        else:
            posmasks.append(each)

    if neg:
        for each in posmasks:
            negmasks.append(each)

            masks = negmasks
        mask = np.zeros(img_dim)
    else:
        mask = np.ones(img_dim)

    maxy = mask.shape[1]
    maxx = mask.shape[0]

    for each in masks:
        fillPoints = each.getFillPoints()

        if each.isNegativeMask() == True:
            for eachp in fillPoints:
                if eachp[0] < maxx and eachp[0] >= 0 and eachp[1] < maxy and eachp[1] >= 0:
                    y = int(eachp[1])
                    x = int(eachp[0])
                    mask[(x,y)] = 1
        else:
            for eachp in fillPoints:
                if eachp[0] < maxx and eachp[0] >= 0 and eachp[1] < maxy and eachp[1] >= 0:
                    y = int(eachp[1])
                    x = int(eachp[0])
                    mask[(x,y)] = 0

    #Mask is flipped (older RAW versions had flipped image)
    mask = np.flipud(mask)

    return mask

def createMaskFromHdr(img, img_hdr, flipped = False):

    try:
        bsmask_info = img_hdr['bsmask_configuration'].split()
        detector_type = img_hdr['detectortype']

        bstop_size = float(bsmask_info[3])/2.0
        arm_width = float(bsmask_info[5])

        if flipped:
            beam_x = float(bsmask_info[1])+1
            beam_y = float(bsmask_info[2])+1
            angle = (2.*np.pi/360.) * (float(bsmask_info[4])+90)
        else:
            beam_x = float(bsmask_info[2])+1
            beam_y = float(bsmask_info[1])+1
            angle = (2.*np.pi/360.) * (float(bsmask_info[4]))

        masks = []
        masks.append(CircleMask((beam_x, beam_y), (beam_x + bstop_size, beam_y + bstop_size), 0, img.shape, False))

        if detector_type == 'PILATUS 300K':
            points = [(191,489), (214,488), (214,0), (192,0)]
            masks.append(PolygonMask(points, 1, img.shape, False))
            points = [(404,489), (426,489), (426,0), (405,0)]
            masks.append(PolygonMask(points, 1, img.shape, False))

        #Making mask as long as the image diagonal (cannot be longer)
        L = np.sqrt( img.shape[0]**2 + img.shape[1]**2 )

        #width of arm mask
        N = arm_width

        x1, y1 = beam_x, beam_y

        x2 = x1 + (L * np.cos(angle))
        y2 = y1 + (L * np.sin(angle))

        dx = x1-x2
        dy = y1-y2
        dist = np.sqrt(dx*dx + dy*dy)
        dx /= dist
        dy /= dist
        x3 = int(x1 + (N/2.)*dy)
        y3 = int(y1 - (N/2.)*dx)
        x4 = int(x1 - (N/2.)*dy)
        y4 = int(y1 + (N/2.)*dx)

        x5 = int(x2 + (N/2.)*dy)
        y5 = int(y2 - (N/2.)*dx)
        x6 = int(x2 - (N/2.)*dy)
        y6 = int(y2 + (N/2.)*dx)

        points = [(x3, y3), (x4, y4), (x6, y6), (x5, y5)]

        masks.append(PolygonMask(points, 2, img.shape, False))

    except ValueError:
        raise ValueError

    return masks


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


@jit(nopython=True, cache=True)
def npnpoly(verts,points):
    """Check whether given points are in the polygon.

    points - Nx2 array

    See http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
    """
    out = np.empty_like(points[:,0], dtype=np.bool_)

    xpi = verts[:,0]
    ypi = verts[:,1]

    # REG: added the np's below to avoid typing errors when building from source on my MacOS system

    xmin = np.min(xpi)
    xmax = np.max(xpi)
    ymin = np.min(ypi)
    ymax = np.max(ypi)
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
