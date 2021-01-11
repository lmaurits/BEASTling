from setuptools import setup, find_packages

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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: BSD License',
    ],
    packages=find_packages(),
    install_requires=[
        'newick>=0.6.0',
        'appdirs',
        'csvw',
        'attrs>=19.1',
        'pycldf>=1.7',
        'chardet',
    ],
    extras_require={
        'dev': ['flake8', 'wheel', 'twine', 'tox'],
        'test': [
            'mock>=1.0.0',
            'pytest>=3.6',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
        ],
    },
    entry_points={
        'console_scripts': ['beastling=beastling.cli:main'],
    },
    package_data={'beastling': ['data/*']},
)
