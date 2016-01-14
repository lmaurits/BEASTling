import codecs
import os
import xml.etree.ElementTree as ET

import scipy.stats

from .unicodecsv import UnicodeDictReader

def sniff_format(fp):
    header = fp.readline()
    fp.seek(0)
    # Is this a CLDF format?
    if all([f in header for f in ("Language_ID", "Parameter_ID", "Value")]):
        diag = "cldf"
    # If not, assume it uses the default BEASTling format
    else:
        diag = "beastling"
    return diag

def load_data(filename):
    # Load data
    fp = open(filename, "r")
    diag = sniff_format(fp)
    if diag == "cldf":
        data = load_cldf_data(fp)
    elif diag == "beastling":
        data = load_beastling_data(fp, filename)
    return data

def load_beastling_data(fp, filename):
    reader = UnicodeDictReader(fp)
    if "iso" not in reader.fieldnames:
        raise ValueError("No 'iso' fieldname found in data file %s" % filename)
    data = {}
    for row in reader:
        if row["iso"] in data:
            raise ValueError("Duplicated ISO code '%s' found in data file %s" % (row["iso"], filename))
        data[row["iso"]] = row
    fp.close()
    return data

def load_cldf_data(fp):
    reader = UnicodeDictReader(fp)
    data = {}
    for row in reader:
        lang = row["Language_ID"]
        if lang not in data:
            data[lang] = {}
        data[lang][row["Parameter_ID"]] = row["Value"]
    fp.close()
    return data
