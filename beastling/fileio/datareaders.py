import codecs
import os
import xml.etree.ElementTree as ET

import scipy.stats

from .unicodecsv import UnicodeDictReader

def sniff_format(fp):
    header = fp.readline()
    fp.seek(0)
    # Is this a CLDF format?
    if "language_id" in header.lower():
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
    fieldnames = [f.lower() for f in reader.fieldnames]
    assert len(fieldnames) == 3
    assert "value" in fieldnames
    lang_fieldname_i = fieldnames.index("language_id")
    lang_fieldname = reader.fieldnames[lang_fieldname_i]
    value_fieldname_i = fieldnames.index("value")
    value_fieldname = reader.fieldnames[value_fieldname_i]
    param_fieldname_i = [0,1,2]
    param_fieldname_i.remove(lang_fieldname_i)
    param_fieldname_i.remove(value_fieldname_i)
    param_fieldname = reader.fieldnames[param_fieldname_i[0]]
    data = {}
    for row in reader:
        lang = row[lang_fieldname]
        if lang not in data:
            data[lang] = {}
        data[lang][row[param_fieldname]] = row[value_fieldname]
    fp.close()
    return data
