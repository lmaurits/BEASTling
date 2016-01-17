import sys

from .unicodecsv import UnicodeDictReader

def sniff_format(fp):
    header = fp.readline()
    # Is this a CLDF format?
    if all([f in header for f in ("Language_ID", "Feature_ID", "Value")]):
        diag = "cldf"
    # If not, assume it uses the default BEASTling format
    else:
        diag = "beastling"
    return diag, header

def load_data(filename):
    # Load data
    if filename == "stdin":
        fp = sys.stdin
    else:
        fp = open(filename, "r")
    diag, header = sniff_format(fp)
    if diag == "cldf":
        data = load_cldf_data(fp, header)
    elif diag == "beastling":
        data = load_beastling_data(fp, header, filename)
    if filename != "stdin":
        fp.close()
    return data

def load_beastling_data(fp, header, filename):
    reader = UnicodeDictReader(fp, header)
    if "iso" not in reader.fieldnames:
        raise ValueError("No 'iso' fieldname found in data file %s" % filename)
    data = {}
    for row in reader:
        if row["iso"] in data:
            raise ValueError("Duplicated ISO code '%s' found in data file %s" % (row["iso"], filename))
        data[row["iso"]] = row
    return data

def load_cldf_data(fp, header):
    reader = UnicodeDictReader(fp, header)
    data = {}
    for row in reader:
        lang = row["Language_ID"]
        if lang not in data:
            data[lang] = {}
        data[lang][row["Feature_ID"]] = row["Value"]
    return data
