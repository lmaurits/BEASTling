# coding: utf8
from __future__ import unicode_literals
import argparse
import os
import sys
import traceback

from beastling.beastxml import BeastXml
from beastling.report import BeastlingReport
from beastling.report import BeastlingGeoJSON
import beastling.configuration
from beastling.extractor import extract


def errmsg(msg):
    sys.stderr.write(msg)


def main(*args):

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        help="Beastling configuration file(s) (or XML file if --extract is used)",
        default=None,
        nargs="+")
    parser.add_argument(
        "--extract",
        default=False,
        action="store_true",
        help="Extract configuration file (and possibly data files) from a BEASTling-generated XML file.")
    parser.add_argument(
        "--report",
        default=False,
        action="store_true",
        help="Save a high-level report on the analysis as a Markdown file.")
    parser.add_argument(
        "--language-list",
        default=False,
        action="store_true",
        help="Save a list of languages in the analysis as a plain text file.")
    parser.add_argument(
        "-o", "--output",
        help="Output filename, no extension",
        default=None)
    parser.add_argument(
        "--overwrite",
        help="Overwrite an existing configuration file.",
        default=False,
        action="store_true")
    parser.add_argument(
        "--stdin",
        help="Read data from stdin.",
        default=False,
        action="store_true")
    parser.add_argument(
        "--prior", "--sample-from-prior", "-p",
        help="Generate XML file which samples from the prior, not posterior.",
        default=False,
        action="store_true")
    parser.add_argument(
        "-v", "--verbose",
        help="Display details of the generated analysis.",
        default=False,
        action="store_true")
    args = parser.parse_args(args or None)
    if args.extract:
        do_extract(args)
    else:
        do_generate(args)
    sys.exit(0)


def do_extract(args):
    if len(args.config) != 1:
        errmsg("Can only extract from exactly one BEAST XML file")
        sys.exit(1)
    if not os.path.exists(args.config[0]):
        errmsg("No such BEAST XML file: %s\n" % args.config)
        sys.exit(2)
    try:
        messages = extract(args.config[0], args.overwrite)
    except Exception as e:
        errmsg("Error encountered while extracting BEASTling config and/or data files:\n")
        traceback.print_exc()
        sys.exit(3)
    for msg in messages:
        sys.stdout.write(msg)


def do_generate(args):

    # Build config object
    for conf in args.config:
        if not os.path.exists(conf):
            errmsg("No such configuration file: %s\n" % conf)
            sys.exit(1)
    try:
        config = beastling.configuration.Configuration(
            configfile=args.config, stdin_data=args.stdin, prior=args.prior)
        config.process()
    except Exception as e:
        errmsg("Error encountered while parsing configuration file:\n")
        traceback.print_exc()
        sys.exit(2)

    # If verbose mode is on, print any messages which were generated while
    # processing the configuration
    if args.verbose:
        for msg in config.messages:
            errmsg(msg + "\n")

    # Build XML file
    try:
        xml = BeastXml(config)
    except Exception as e:
        errmsg("Error encountered while building BeastXML object:\n")
        traceback.print_exc()
        sys.exit(3)

    # Write XML file
    filename = args.output if args.output else config.basename+".xml"
    if os.path.exists(filename) and not args.overwrite:
        errmsg("File %s already exists!  Run beastling with the --overwrite option if you wish to overwrite it.\n" % filename)
        sys.exit(4)
    xml.write_file(filename)

    # Build and write report
    if args.report:
        report = BeastlingReport(config)
        report.write_file(config.basename+".md")
        geojson = BeastlingGeoJSON(config)
        geojson.write_file(config.basename+".geojson")

    # Build and write language list
    if args.language_list:
        write_language_list(config)

def write_language_list(config):

    with open(config.basename + "_languages.txt", "w") as fp:
        fp.write("\n".join(config.languages)+"\n")
