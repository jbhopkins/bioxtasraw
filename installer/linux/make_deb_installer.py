# Run this script after doing the pyinstaller build

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
import builtins
from io import open

import os
import shutil
import subprocess

os.sys.path.append(os.path.abspath(os.path.join('..', '..')))

from bioxtasraw.RAWGlobals import version

deb_path = os.path.join('.', 'RAW-{}-linux-amd64'.format(version),
    'DEBIAN')
exc_path = os.path.join('.', 'RAW-{}-linux-amd64'.format(version),
    'usr', 'bin')
app_path = os.path.join('.', 'RAW-{}-linux-amd64'.format(version),
    'usr', 'share', 'applications')
png_path = os.path.join('.', 'RAW-{}-linux-amd64'.format(version),
    'usr', 'share', 'icons', 'hicolor', '48x48', 'apps')
xpm_path = os.path.join('.', 'RAW-{}-linux-amd64'.format(version),
    'usr', 'share', 'pixmaps')

os.makedirs(deb_path, exist_ok=True)
os.makedirs(exc_path, exist_ok=True)
os.makedirs(app_path, exist_ok=True)
os.makedirs(png_path, exist_ok=True)
os.makedirs(xpm_path, exist_ok=True)

shutil.copy('control', deb_path)
shutil.copy(os.path.join('..', 'dist', 'bioxtas-raw'), exc_path)
shutil.copy('bioxtas-raw.desktop', app_path)
shutil.copy(os.path.join('..', '..', 'bioxtasraw',
    'resources', 'raw.png'), os.path.join(png_path, 'bioxtas-raw.png'))
shutil.copy(os.path.join('..', '..', 'bioxtasraw',
    'resources', 'raw.xpm'), os.path.join(xpm_path, 'bioxtas-raw.xpm'))

with open(os.path.join(deb_path, 'control'), 'r') as f:
    control_lines = f.readlines()

for i in range(len(control_lines)):
    if control_lines[i].startswith('Version'):
        control_lines[i] = 'Version: {}\n'.format(version)

with open(os.path.join(deb_path, 'control'), 'w') as f:
    f.writelines(control_lines)


with open(os.path.join(app_path, 'bioxtas-raw.desktop'), 'r') as f:
    control_lines = f.readlines()

for i in range(len(control_lines)):
    if control_lines[i].startswith('Version'):
        control_lines[i] = 'Version={}\n'.format(version)

with open(os.path.join(app_path, 'bioxtas-raw.desktop'), 'w') as f:
    f.writelines(control_lines)

proc = subprocess.Popen("fakeroot dpkg-deb --build RAW-{}-linux-amd64".format(version),
    shell=True)
proc.communicate()

print('Checking .deb installer with lintian')
proc = subprocess.Popen("lintian RAW-{}-linux-amd64.deb".format(version),
    shell=True)
proc.communicate()
