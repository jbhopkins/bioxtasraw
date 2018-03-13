The RAW documentation is now formatted for sphinx. This requires sphinx be
installed, along with appropriate themes (alabaster and read-the-docs).

To build html, be in the top level (docs) folder and use:
make html

To build pdfs, be in the top level (docs) folder and use:
make latexpdf

It is recommended that you first delete any old files in the build folder, as some
changes may not propagate when rebuilding.

When releasing new documentation, update the version number in the conf.py file.
