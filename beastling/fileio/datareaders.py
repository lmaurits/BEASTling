import sys
import collections
from .unicodecsv import UnicodeDictReader

def sniff_format(fp):
    header = fp.readline()
    # Is this a CLDF format?
    if (all([f in header for f in ("Language_ID", "Value")])
        and
        any([f in header for f in ("Feature_ID", "Parameter_ID")])
       ):
        diag = "cldf"
    # If not, assume it uses the default BEASTling format
    else:
        diag = "beastling"
    return diag, header

def load_data(filename, file_format=None, lang_column=None):
    # Open file
    if filename == "stdin":
        fp = sys.stdin
    else:
        fp = open(filename, "r")

    # Determine format (if not given)
    if not file_format:
        file_format, header = sniff_format(fp)
    else:
        header = fp.readline()

    # Load data
    if file_format == "cldf":
        data = load_cldf_data(fp, header)
    elif file_format == "beastling":
        data = load_beastling_data(fp, header, lang_column, filename)

    # Close file if necessary
    if filename != "stdin":
        fp.close()

    return data

_language_column_names = ("iso", "iso_code", "glotto", "glottocode", "language", "language_id", "lang", "lang_id")

def load_beastling_data(fp, header, lang_column, filename):
    reader = UnicodeDictReader(fp, header)
    if not lang_column:
        for candidate in reader.fieldnames:
            if candidate.lower() in _language_column_names:
                lang_column = candidate
                break

    if not lang_column or lang_column not in reader.fieldnames:
        raise ValueError("Cold not find language column in data file %s" % filename)
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))
    for row in reader:
        if row[lang_column] in data:
            raise ValueError("Duplicated language identifier '%s' found in data file %s" % (row[lang_column], filename))
        data[row[lang_column]] = collections.defaultdict(lambda : "?", row)
    return data

def load_cldf_data(fp, header):
    if "Feature_ID" in header:
        feature_column = "Feature_ID"
    else:
        feature_column = "Parameter_ID"
    reader = UnicodeDictReader(fp, header)
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))
    for row in reader:
        lang = row["Language_ID"]
        if lang not in data:
            data[lang] = collections.defaultdict(lambda :"?")
        data[lang][row[feature_column]] = row["Value"]
    return data
