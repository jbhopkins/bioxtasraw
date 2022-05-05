OS X and macOS install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _macsource:

#.  Install Miniconda python distribution

    *   Download the free miniconda python 3.x, e.g. 3.8, installer from:
        `https://docs.conda.io/en/latest/miniconda.html <https://docs.conda.io/en/latest/miniconda.html>`_

        *   Make sure you get the python 3.x version!

    *   Open a Terminal window by starting the Terminal app.

        *   Using the Launcher, it is located in the Other section.

        |10000201000006900000041A52DBF3453A0EEDE9_png|

        |10000201000007800000043899D84AD76212B4C9_png|

        *   Browsing the Applications folder in Finder, Terminal is in the Utilities folder.

    *   In the terminal window type ``cd ~\Downloads`` and hit enter.

    *   In the terminal window type ``bash Miniconda3-latest-MacOSX-x86_64.sh`` and hit enter.

    *   Agree to all of the prompts.

    *   More detailed install instructions are available here:
        `https://conda.io/docs/user-guide/install/macos.html <https://conda.io/docs/user-guide/install/macos.html>`_

    *   Close the terminal window.

#.  Install the necessary python packages.

    *   Open a new terminal window as in the previous step

    *   Type ``conda upgrade conda pip wheel setuptools`` and hit enter. Agree to all the prompts.

    *   Type ``conda install numpy scipy matplotlib pillow numba h5py cython numexpr reportlab`` and hit enter.
        Agree to all the prompts.

    *   Type ``conda install -c conda-forge wxpython hdf5plugin fabio pyfai mmcif_pdbx`` and hit enter. Agree
        to all prompts.

#.  Download RAW from sourceforge

    *   `https://sourceforge.net/projects/bioxtasraw <https://sourceforge.net/projects/bioxtasraw>`_

    *   Navigate to the :guilabel:`Files` tab and download the latest source code,
        :file:`RAW-{x}.{y}.{z}-Source.zip`. Or download the latest development version
        from the git by navigating to the :guilabel:`Code` tab.

#.  Expand the downloaded zip file in the Downloads folder by double clicking on it.

    *   This step may not be necessary, some browsers may automatically expand zip files.

#.  In the terminal or in the graphical file manager, confirm that the file named :file:`setup.py`
    is in your expanded raw directory. If it isn’t, it’s likely that when you expanded the
    RAW download, you ended up with unnecessary layers of directories. Find the
    directory with :file:`setup.py` in it, and make that the top level folder.

#.  Move the RAW files to Applications folder

    *   Move the folder that contains all of the RAW files to the :file:`Applications` folder.
        As above, this would be the folder with :file:`setup.py` in it.

    *   Rename the folder that you just moved to :file:`raw`.

#.  In a terminal, change directory into the top level RAW folder

    *   If you used the suggested path of :file:`Applications/raw`
        type: ``cd /Applications/raw``

#.  Build the extensions.

    *   ``python setup.py build_ext --inplace``

#.  Navigate to the :file:`bioxtasraw` subfolder

    *   From the top level RAW folder it should be ``cd ./bioxtasraw``

#.  Run RAW

    *   ``pythonw RAW.py``

#.  Enjoy!

    *   In the future, you can start RAW as in the previous step.

    *   If RAW doesn’t work, check out the :ref:`solutions to common problems <mactrb>`



.. |10000201000007800000043899D84AD76212B4C9_png| image:: images/mac_install/10000201000007800000043899D84AD76212B4C9.png


.. |10000201000006900000041A52DBF3453A0EEDE9_png| image:: images/mac_install/10000201000006900000041A52DBF3453A0EEDE9.png
