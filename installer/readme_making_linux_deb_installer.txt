Making the .deb installer uses pyinstaller (tested on 3.6.0). This must be done with
miniconda to properly package the LLVMLite package for numba. In order to set up the
proper build environment, simply install from source as in the RAW documentation, then
additionally install pyinstaller through pip or conda: pip install pyinstaller.

Note: currently requires setuptools<45 to work.

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
9)  Rename the package appropriate (e.g. RAW-2.0.0-linux-amd64.deb)

Current build notes:
- Using ubuntu 18.04 LTS
- Using wxpython 4.2.0, python 3.11, pyinstaller 5.11.0 (requires
    up to date pyinstaller, which currently isn't available on conda for py311,
    so had to pip install)
- Using raw_py311 environment on the virtualbox machine



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
