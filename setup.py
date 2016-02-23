#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from beastling import __version__ as version


requires = [
    'six',
    'newick',
    'clldutils',
]

setup(
    name='beastling',
    version=version,
    description='Command line tool to help mortal linguists use BEAST',
    author='Luke Maurits',
    author_email='luke@maurits.id.au',
    license="BSD (3 clause)",
    classifiers=[
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: BSD License',
    ],
    packages=['beastling','beastling.fileio','beastling.models'],
    install_requires=requires,
    package_data={'beastling': ['data/*']},
    scripts=['bin/beastling',],
)
