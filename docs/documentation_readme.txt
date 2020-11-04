The RAW documentation is now formatted for sphinx. This requires sphinx be
installed, along with appropriate themes (alabaster and read-the-docs). To do so:
conda install sphinx sphinx_rtd_theme

To build html, be in the top level (docs) folder and use:
make html

To build pdfs, be in the top level (docs) folder and use:
make latexpdf

On windows without make you can use:
sphinx-build -b html source build\html

It is recommended that you first delete any old files in the build folder, as some
changes may not propagate when rebuilding. Do this with a:
make clean

When releasing new documentation, update the version number in the conf.py file.

Useful site for embedding youtube videos in a mobile friendly way:
https://embedresponsively.com/?

For video tutorials, intro/outro:
Hello and welcome to this tutorial for bioxtas raw. In this tutorial you will learn how to . . . .

With that, that’s the end of the tutorial. You should now know how too . . . .
