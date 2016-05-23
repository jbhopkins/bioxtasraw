Readme for making windows installers

To make a compiled windows .exe version of raw, use pyinstaller 3.1.1 on windows 7 (probably works on 8 and 10, but is it back compatabile?).
Move the RAW_windows.spec file into the RAW folder.
At the command line, run pyinstaller -y RAW_windows.spec

If it fails, run it again. If it still fails, try deleting the build and dist directories.

To make a .exe installer, use Inno (simple).

To make a .msi installer (preferred), use Advanced Installer (free for open source projects). The wizard is pretty straightforward, there is also a RAW.aip file in this folder which is an advanced installer project file.