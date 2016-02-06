#BEASTling

A linguistics-focussed command line tool for generating
[BEAST](http://beast2.org) XML files.  Only BEAST 2.x is supported.

For full documentation, see [Read the Docs](https://beastling.readthedocs.org).

BEASTling is written in [Python](http://python.org).  It is available from the
Python Package Index, aka "the Cheeseshop".  This means you can install it
easily using `easy_install` or `pip`.  Otherwise, you can clone this repo and
use the `setup.py` file included to install.

BEASTling will run without BEAST installed, but it won't be very useful.
Therefore, you should install the latest version of [BEAST
2](http://beast2.org/).  Old BEAST 1.x versions are not supported.  Note that
recent BEAST 2.x releases depend upon [Java
8](http://www.oracle.com/technetwork/java/javase/overview/java8-2100321.html).
They will *not* work with Java 7.  So, you should install the latest version of
Java for your platform first.

BEAST 2 is a modular program, with a small, simple core and additional packages
which can be installed to add functionality.  [Managing packages is
easy](http://beast2.org/managing-packages/) and can be done with a GUI.  You
should install the following packages, as BEASTling makes use of them for much
of its functionality:

* BEAST_CLASSIC
* BEASTLabs
* morph-models

In summary:

1. Install Python.
2. Install/upgrade Java.  You need Java 8.
3. Install/upgrade BEAST.  You need BEAST 2.
4. Install required BEAST packages.
5. Install BEASTling.
6. Profit.

But reports, feature requests and pull requests are all welcome.
