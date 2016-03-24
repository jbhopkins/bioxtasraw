"""
Created on January 14, 2015

@author: Jesse B. Hopkins


The purpose of this module is to create a file which contains wxpython embedded images
all of the files in a directory. The purpose is to make code packaging easier, by removing
the need to package extra resource files. Everything will instead be in a python file.


"""

import os
import glob
import sys
from wx.tools.img2py import img2py
import time

RAWWorkDir = sys.path[0]

RAWResourceDir = RAWWorkDir + '/resources/'

png_list = glob.glob(RAWResourceDir+'*.png')
ico_list = glob.glob(RAWResourceDir+'*.ico')
gif_list = glob.glob(RAWResourceDir+'*.gif')

image_list = png_list + ico_list + gif_list

img_code = ''

for i in range(len(image_list)):
    image = image_list[i]

    if image.split('.')[-1] == '.ico':
        img2py(image,RAWWorkDir+'/temp.py', icon=True)
    else:
        img2py(image,RAWWorkDir+'/temp.py')

    f = open(RAWWorkDir+'/temp.py','r')
    code = f.readlines()
    f.close()
    for line in code:
        img_code = img_code + line
    

os.remove(RAWWorkDir+'/temp.py')

file_header = "'''Created on " + time.ctime() + "\n\n@author: Jesse B. Hopkins\n\nThis module contains embedded image data for all of the image\nfiles in the resources directory. It was generated using the\nwx.tools.img2py.img2py function, and automated with the\nEmbeddedRAWIcons.py file.\n\n'''\n\n"

f = open('RAWIcons.py','w')
f.write(file_header)
f.write(img_code)
f.close()