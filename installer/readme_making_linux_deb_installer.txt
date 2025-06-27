Making the .deb installer uses pyinstaller This must be done with
miniconda to properly package the LLVMLite package for numba. In order to set up the
proper build environment, simply install from source as in the RAW documentation, then
additionally install pyinstaller through pip or conda: pip install pyinstaller.

Steps:
1)  Install fakeroot, lintian: sudo apt-get install fakeroot lintian
2)  Install conda nomkl: conda install nomkl
3)  Fix pyFAI utils error (should be fixed in 0.20 release) by editing line 166 of utils/__init__.py
    in site packages to use os.path.abspath.
4)  Make a fresh git-free folder for RAW: git archive master | tar -x -C /somewhere/else
5)  Build the extensions and run RAW in that new folder.
6)  Build the html documentation
7)  In the installer directory, run “pyinstaller -y RAW.spec”
8)  In the installer/linux directory run "python make_deb_installer.py"

Current build notes:
- Using ubuntu 22.04 LTS
- Using raw_py311 environment on the virtualbox machine
- Helps a lot if you set up guest additions on the virtualbox
- If installed by conda there's current some x11 error (seems to be GUI toolkit, not RAW)
with the GTK3 versions of wxpython, which means wxpython >4.2.0, so use 4.2.0 and GTK2 for
now. Could try a build via pip with the GTK3 at some point.



Older notes (not relevant unless I need to go back to the older build):
- Using Ubuntu 14.04 LTS
- On linux requires wxpython 4.0.4 (later versions don't package right with pyinstaller)
- With conda on linux, 4.0.4 requires python 3.7
- Requires pyinstaller 4.1 or earlier?
- Using raw_build environment on the virtualbox machine.

Note: If installer is built on Ubuntu 14.04 LTS it works on Debian 8-10 and Ubuntu 14-18.
If installer is built on Debian 8 it works on Debian 8-10 and Ubuntu 16-18.

Need wxpython < 4.1 on Ubuntu 16.04?

Useful resources for building .deb package:
https://plashless.wordpress.com/2013/08/25/a-short-debian-packaging-case-gui-apps-gpl-pyinstaller/
https://plashless.wordpress.com/2013/08/31/app-icons/
https://plashless.wordpress.com/2013/08/29/creating-new-mime-types-in-a-shortcut-debian-packaging/
https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-description
https://linuxconfig.org/easy-way-to-create-a-debian-package-and-local-package-repository
https://martin.hoppenheit.info/blog/2016/where-to-put-application-icons-on-linux/
https://www.howtoforge.com/tutorial/how-to-convert-packages-between-deb-and-rpm/
