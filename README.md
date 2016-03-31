#BEASTling

A linguistics-focussed command line tool for generating
[BEAST](http://beast2.org) XML files.  Only BEAST 2.x is supported.

[![Documentation Status](https://readthedocs.org/projects/beastling/badge/?version=latest)](http://beastling.readthedocs.org/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/lmaurits/BEASTling.svg?branch=develop)](https://travis-ci.org/lmaurits/BEASTling)
[![codecov.io](http://codecov.io/github/lmaurits/BEASTling/coverage.svg?branch=develop)](http://codecov.io/github/lmaurits/BEASTling?branch=develop)
[![PyPI](https://img.shields.io/pypi/v/beastling.svg)](https://pypi.python.org/pypi/beastling)
[![PyPI](https://img.shields.io/pypi/pyversions/beastling.svg)](https://pypi.python.org/pypi/beastling)

BEASTling is written in [Python](http://python.org).  Python versions 2.7 and
3.4+ are supported.  It is available from the Python Package Index, aka "the
Cheeseshop".  This means you can install it easily using `easy_install` or
`pip`.  Otherwise, you can clone this repo and use the `setup.py` file
included to install.

BEASTling has a few dependencies.  If you use `easy_install` or `pip`, they
should be taken care of automatically for you.  If you are installing manually,
you will also have to manually install the dependencies before BEASTling will
work.  The dependencies are:

* [appdirs](https://pypi.python.org/pypi/appdirs)
* [clldutils](https://pypi.python.org/pypi/clldutils)
* [newick](https://pypi.python.org/pypi/newick)
* [six](https://pypi.python.org/pypi/six)

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

1. Install/upgrade Python.  You need 2.7 or 3.4+
2. Install BEASTling (plus dependencies if not using `pip` etc.).
3. Install/upgrade Java.  You need Java 8.
4. Install/upgrade BEAST.  You need BEAST 2.
5. Install required BEAST packages.
6. Profit.

Bug reports, feature requests and pull requests are all welcome.
