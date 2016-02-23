#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from beastling import __version__ as version

setup(
    name='beastling',
    version=version,
    description='Command line tool to help mortal linguists use BEAST',
    author='Luke Maurits',
    author_email='luke@maurits.id.au',
    license="BSD (3 clause)",
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
    ],
    packages=['beastling','beastling.fileio','beastling.models'],
    install_requires=['newick', 'appdirs', 'six'],
    tests_require=['mock==1.0.0', 'nose'],
    package_data={'beastling': ['data/*']},
    scripts=['bin/beastling',],
)
