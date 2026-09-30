Readme for making windows installers


Steps:

1) Make a fresh git-free folder for RAW using the git export command
2) Build the extensions and run RAW in that new folder.
3) Build the html documentation (sphinx-build -b html source build\html)
5) In the installer directory, run “pyinstaller -y RAW.spec”


If it fails, run it again. If it still fails, try deleting the build and dist directories.

Note:
- Currently using the raw_py312 environment on both Windows 10 and 11
- Requires having the console option True in pyinstaller, otherwise whenever
you run ATSAS programs it opens a new terminal window which is really annoying.

To make a .exe installer, use Inno (simple).

To make a .msi installer (preferred), use Advanced Installer (free for open source projects).
The wizard is pretty straightforward.
