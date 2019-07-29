# coding: utf8
from __future__ import unicode_literals
import argparse
import os
import sys
import traceback

from beastling import __version__
from beastling.beastxml import BeastXml
from beastling.configuration import Configuration
from beastling.extractor import extract
from beastling.report import BeastlingReport
from beastling.report import BeastlingGeoJSON

wrap_errors = Exception

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
        help="Output filename, for example `-o analysis.xml`",
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
    parser.add_argument(
        "--version",
        action="version",
        version = "BEASTling %s" % __version__)
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
    except wrap_errors as e:
        errmsg("Error encountered while extracting BEASTling config and/or data files:\n")
        traceback.print_exc()
        sys.exit(3)
    for msg in messages:
        sys.stdout.write(msg)


def do_generate(args):

    # Make sure the requested configuration file exists
    for conf in args.config:
        if not os.path.exists(conf):
            errmsg("No such configuration file: %s\n" % conf)
            sys.exit(1)

    # Build but DON'T PROCESS the Config object
    # This is fast, and gives us enough information to check whether or not
    try:
        config = Configuration(
            configfile=args.config, stdin_data=args.stdin, prior=args.prior)
    except wrap_errors as e: # PRAGMA: NO COVER
        errmsg("Error encountered while parsing configuration file:\n")
        traceback.print_exc()
        sys.exit(2)

    # Make sure we can write to the appropriate output filename
    output_filename = args.output if args.output else config.basename+".xml"
    if os.path.exists(output_filename) and not args.overwrite:
        errmsg("File %s already exists!  Run beastling with the --overwrite option if you wish to overwrite it.\n" % output_filename)
        sys.exit(4)

    # Now that we know we will be able to save the resulting XML, we can take
    # the time to process the config object
    try:
        config.process()
    except wrap_errors as e:
        errmsg("Error encountered while parsing configuration file:\n")
        traceback.print_exc()
        sys.exit(2)

    # Print messages
    ## Urgent messages are printed first, whether verbose mode is on or not
    for msg in config.urgent_messages:
        errmsg(msg + "\n")
    ## Non-urgent messages are next, but only if verbose mode is on
    if args.verbose:
        for msg in config.messages:
            errmsg(msg + "\n")

    # Build XML file
    try:
        xml = BeastXml(config)
    except wrap_errors as e:
        errmsg("Error encountered while building BeastXML object:\n")
        traceback.print_exc()
        sys.exit(3)

    # Write XML file
    xml.write_file(output_filename)

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
