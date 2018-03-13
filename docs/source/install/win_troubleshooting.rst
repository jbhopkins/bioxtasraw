Common problems/troubleshooting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _wintrb:

**Prebuilt installer:**

*   Because the RAW team is an ‘unknown’ developer, you will probably see some
    security warnings when you install RAW. When you do, just give the installer
    and program permission to run on your computer.

*   RAW is used by (relatively) few people, which means many antivirus programs
    have not seen the RAW software before. Occasionally virus scanners will mark
    a file (typically RAW.exe) as a threat (it will usually be in the ‘general
    malware’ category). If this happens, please do the following:

    *   Upload the file to
        `https://www.virustotal.com/ <https://www.virustotal.com/>`_
        and see if any other antivirus programs identify it as a problem (it is
        always possible someone hijacked the installer somehow!).

    *   If most or all of the antivirus programs on virustotal.com clear the file, make an
        exception for it in your virus scanner.

    *   Contact the RAW developers, so we can report the false identification to the
        virus scanner company and get the file whitelisted in future definitions files.


**From source:**

*   The compiler can fail if there are any spaces in the directory paths. Make sure raw,
    the compiler (MinGW), and python are all installed in directory paths without spaces
    in the names.

*   The compiler can fail if it tries to compile the modules when some of them are
    already compiled. If the compilation is failing, try deleting all **.pyd** files in
    the raw directory.

*   The compiler can fail if you try to compile when you’re not using the command line.
    This most commonly happens if someone tries to run **RAW.py** for the first time by
    double clicking on it, rather than using the *python RAW.py* command in the command
    prompt window.

*   If the extensions won’t compile properly (you’ll get a popup message when you start
    RAW warning you of this), you can try copying the precompiled extensions (**.pyd**
    files) from the appropriate WinLib folder into the main raw folder.

*   If you are updating your RAW installation, you should completely delete the old RAW
    source files, and then replace them with the new ones.

*   You may have trouble with various pieces of the installation if your path variable
    isn’t set right. The windows PATH variable cannot have spaces. That is, your path
    should look like: item1;item2;item3 not: item1; item2; item3. For Windows 10,
    where you enter separate entries in your path variable (which Windows automatically
    concatenates), make sure that you don’t have leading or training spaces in any
    of the items.

*   On some systems, we’ve found it necessary to install the packages from pip in multiple
    steps. If a *pip install* fails, trying running it on each package separately. For example,
    if *pip install matplotlib pillow fabio* fails, try running:

    *   *pip install matplotlib*

    *   *pip install pillow*

    *   *pip install fabio*
