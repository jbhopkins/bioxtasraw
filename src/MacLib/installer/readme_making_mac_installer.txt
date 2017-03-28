Making the mac installer users pyinstaller (tested on 3.2.1). This is vary particular about what version of python it uses. I’ve only been able to get it to work on a conda install, with the packages as listed at the end of this document. With a python build from homebrew or from canopy it doesn’t seem to work. Additionally, it doesn’t seem to work on my home machine with (presumably) the same conda python distribution.

Steps:
0) Set the appropriate python path, if needed: export PATH=~/miniconda2/bin:$PATH
1) Copy the RAW_mac.spec file into the main RAW directory.
2) Run “pyinstaller -y RAW_mac.spec”
3) Copy the RAW.app file from the MacLib/installer folder to the main RAW folder. Show the contents in finder, and copy the contents of the dist/RAW directory to the MacOS folder in the .app file.
4) Copy the info.plist into top level Contents folder in the RAW.app package 
5) Update the version number in the info.plist file that you copied.
7) Open disk utility
8) Create a new disk image (File->New Image>Blank Image) that is ~12% larger than the .app package. Name it RAW, but save it as untitled.
9) Open the mounted disk image. Copy the .app file and a shortcut of the applications folder to the disk image. Size and arrange as desired.
9) In Disk Utility, Image->Convert, select the prepared disk image, and name it RAW-1.2.2-Mac (note, the disk image must be ejected for this to work

Note: if pyopencl is installed, the build will fail.

More info on disk images here:
https://el-tramo.be/blog/fancy-dmg/

Conda packages:
# This file may be used to create an environment using:
# $ conda create --name <env> --file <this file>
# platform: osx-64
cffi=1.9.1=py27_0
conda=4.3.14=py27_0
conda-env=2.6.0=0
cryptography=1.7.1=py27_0
cycler=0.10.0=py27_0
cython=0.25.2=py27_0
enum34=1.1.6=py27_0
fftw=3.3.4=0
freetype=2.5.5=1
functools32=3.2.3.2=py27_0
h5py=2.6.0=np112py27_2
hdf5=1.8.17=1
icu=54.1=0
idna=2.2=py27_0
ipaddress=1.0.18=py27_0
jbig=2.1=0
jpeg=9b=0
libiconv=1.14=0
libpng=1.6.27=0
libtiff=4.0.6=3
libxml2=2.9.4=0
libxslt=1.1.29=0
lxml=3.7.3=py27_0
matplotlib=2.0.0=np112py27_0
mkl=2017.0.1=0
nomkl=1.0=0
numpy=1.12.0=py27_nomkl_0
olefile=0.44=py27_0
openssl=1.0.2h=1
pillow=4.0.0=py27_1
pip=9.0.1=py27_1
pyasn1=0.1.9=py27_0
pycosat=0.6.1=py27_1
pycparser=2.17=py27_0
pycrypto=2.6.1=py27_4
pyopenssl=16.2.0=py27_0
pyparsing=2.0.3=py27_0
pyqt=5.6.0=py27_0
python=2.7.12=1
python-dateutil=2.5.3=py27_0
python.app=1.2=py27_4
pytz=2016.6.1=py27_0
pyyaml=3.11=py27_4
qt=5.6.0=0
readline=6.2=2
requests=2.13.0=py27_0
ruamel_yaml=0.11.14=py27_0
scipy=0.19.0=np112py27_nomkl_0
setuptools=27.2.0=py27_0
sip=4.18=py27_0
six=1.10.0=py27_0
sqlite=3.13.0=0
subprocess32=3.2.7=py27_0
tk=8.5.18=0
wheel=0.29.0=py27_0
wxpython=3.0=py27_0
xz=5.2.2=0
yaml=0.1.6=0
zlib=1.2.8=3


Pip packages (some packages installed via pip: fabio, pyFAI, hdf5plugin, weave, pyflakes, pyinstaller):
cffi==1.9.1
conda==4.3.14
cryptography==1.7.1
cycler==0.10.0
Cython==0.25.2
enum34==1.1.6
fabio==0.4.0
fisx==1.1.2
funcsigs==1.0.2
functools32==3.2.3.post2
h5py==2.6.0
hdf5plugin==1.3.0
idna==2.2
ipaddress==1.0.18
lxml==3.7.3
matplotlib==1.5.3
mock==2.0.0
nose==1.3.7
numpy==1.12.0
olefile==0.44
pbr==1.10.0
Pillow==4.0.0
pyasn1==0.1.9
pycosat==0.6.1
pycparser==2.17
pycrypto==2.6.1
pyFAI==0.13.1
PyInstaller==3.2.1
pymca==5.1.3
PyMca5==5.1.3
pyOpenSSL==16.2.0
pyparsing==2.0.3
python-dateutil==2.5.3
pytz==2016.6.1
PyYAML==3.11
requests==2.13.0
ruamel-yaml===-VERSION
scipy==0.19.0
six==1.10.0
subprocess32==3.2.7
weave==0.15.0
wxPython==3.0.0.0
wxPython-common==3.0.0.0
