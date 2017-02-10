# coding: utf8
from __future__ import unicode_literals

import sys
import argparse
from . import BasicReadInterpolation, INI

def main(*args):
    """Execute CLI functionality

    Parse command line arguments to find config files and distill a an
    aggregated, interpolated configuration from them.

    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Combine multiple configuration files into one.")
    parser.add_argument(
        "config",
        type=argparse.FileType("r"),
        help="ConfigParser-style configuration file(s)",
        default=None,
        nargs="+")
    parser.add_argument(
        "-o", "--output",
        type=argparse.FileType("w"),
        help="Output filename, for example `-o gold.ini`",
        default=sys.stdout)
    args = parser.parse_args(args or None)
    
    config = INI(interpolation=BasicReadInterpolation())
    for file in args.config:
        config.read_file(file)

    # We would like to use clldutils.INI.write directly, but it does
    # not support file objects.
    args.output.write(config.write_string())
    
    sys.exit(0)
