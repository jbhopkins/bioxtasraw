#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
sys.stdout = open('screen.txt','w',0)
sys.stderr = open('errors.txt','w',0)

sys.path.insert(0, "../Filters")
sys.path.insert(0, "../SysFiles")

def rmdir_recursive(dir, keep=[]):
    """Remove a directory, and all its contents if it is not already empty."""

    print >>sys.__stdout__,'> Removing files in directory :' + dir + ',keeping protected files...'
    print '> Removing files in directory :' + dir + ',keeping protected files...'
    for name in os.listdir(dir):
        if name not in keep:
            full_name = os.path.join(dir, name)
            
            # on Windows, if we don't have write permission we can't remove
            # the file/directory either, so turn that on
            if not os.access(full_name, os.W_OK):
                os.chmod(full_name, 0600)
            if os.path.isdir(full_name):
                rmdir_recursive(full_name, keep=keep)
            else:
                os.remove(full_name)
        else:
            print >>sys.__stdout__,'> keeping ' + name + ' in ' + dir
            print '> keeping ' + name + ' in ' + dir
    if keep == []:
        print >>sys.__stdout__,'> Removing directory :' + dir + 'because no file asked to be kept.'
        print '> Removing directory :' + dir + 'because no file asked to be kept.'
        os.rmdir(dir)

try:
    rmdir_recursive('./dist', keep=".svn")
except:
    print >>sys.__stdout__,'./dist: nothing to remove.'
    print './dist: nothing to remove.'
             
# setup.py

# Used successfully in Python2.5 with matplotlib 0.91.2 and PyQt4 (and Qt 4.3.3) 
from distutils.core import setup
import py2exe

# We need to exclude matplotlib backends not being used by this executable.  You may find
# that you need different excludes to create a working executable with your chosen backend.
# We also need to include include various numerix libraries that the other functions call.

opts = {
    'py2exe': { "compressed": 1,
                "optimize": 1,
                #"ascii": 1,
                "bundle_files": 1,
                'packages' : ["matplotlib.backends.backend_wxagg",
                              "matplotlib.numerix.fft",
                              "matplotlib.numerix.linear_algebra",
                              "matplotlib.numerix.random_array",
                              "matplotlib.numerix.ma"
                              ],
                'excludes': ['_tkinter'
                #             '_gtkagg', '_tkagg', '_agg2', '_cairo', '_cocoaagg',
                #             '_fltkagg', '_gtk', '_gtkcairo','_backend_gdk',
                #             '_gobject','_gtkagg','_tkinter','glade','pango',
                #             'QtCore','QtGui'
                             ],
                'dll_excludes': ['tk84.dll',
                                 'tcl84.dll',
                #                 'libgdk_pixbuf-2.0-0.dll',
                #                 'libgdk-win32-2.0-0.dll',
                #                 'libgobject-2.0-0.dll',
                #                 'libgtk-win32-2.0-0.dll',
                #                 'libglib-2.0-0.dll',
                #                 'libcairo-2.dll',
                #                 'libpango-1.0-0.dll',
                #                 'libpangowin32-1.0-0.dll',
                #                 'libpangocairo-1.0-0.dll',
                #                 'libglade-2.0-0.dll',
                #                 'libgmodule-2.0-0.dll',
                #                 'libgthread-2.0-0.dll',
                #                 'tk84.dll',
                #                 'tcl84.dll',
                                  ]
              }
       }

# Save matplotlib-data to mpl-data ( It is located in the matplotlib\mpl-data 
# folder and the compiled programs will look for it in \mpl-data
import matplotlib
data_files = matplotlib.get_py2exe_datafiles()
data_files.append(('ressources', ['ressources\\raw.png']))
data_files.append(('ressources', ['ressources\\linlin.png']))
data_files.append(('ressources', ['ressources\\loglin.png']))
data_files.append(('ressources', ['ressources\\loglog.png']))
data_files.append(('ressources', ['ressources\\load.png']))
data_files.append(('ressources', ['ressources\\clear.png']))
data_files.append(('ressources', ['ressources\\savemask.png']))
data_files.append(('ressources', ['ressources\\rect.png']))
data_files.append(('ressources', ['ressources\\poly.png']))
data_files.append(('ressources', ['ressources\\circle.png']))
data_files.append(('ressources', ['ressources\\errbars.png']))
data_files.append(('ressources', ['ressources\\Bob2.gif']))
data_files.append(('ressources', ['ressources\\logo_atom.gif']))
data_files.append(('ressources', ['ressources\\wi0009-16.png']))
data_files.append(('ressources', ['ressources\\agbe2.png']))
data_files.append(('ressources', ['ressources\\showboth.png']))
data_files.append(('ressources', ['ressources\\showtop.png']))
data_files.append(('ressources', ['ressources\\showbottom.png']))
data_files.append(('ressources', ['ressources\\legend.png']))
data_files.append(('', ['raw.ico']))
data_files.append(('', ['RAW.chm']))


# for console program use 'console = [{"script" : "scriptname.py"}]
# windows = 
setup(name='BioXTAS RAW',
      version='0.98',
      author='Soren S. Nielsen',
      console=[{'script' : "RAW.py",
                'icon_resources':[(1,'ressources\\raw.ico')],
                'other_resources':[(24, 1, manifest)],
               }],
      options = opts,
      zipfile = None,
      data_files = data_files)

#some cleanup
#rmdir_recursive('./dist/tcl')
#rmdir_recursive('./build')
print "---Done---"
