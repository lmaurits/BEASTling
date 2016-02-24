import sys
import collections

from clldutils.dsv import UnicodeDictReader


def load_data(filename, file_format=None, lang_column=None):
    if filename == 'stdin':
        filename = sys.stdin
    with UnicodeDictReader(filename) as reader:
        if all([f in reader.fieldnames for f in ("Language_ID", "Value")]) \
                and any([f in reader.fieldnames for f in ("Feature_ID", "Parameter_ID")]):
            data = load_cldf_data(reader)
        else:
            data = load_beastling_data(reader, lang_column, filename)

    return data


_language_column_names = ("iso", "iso_code", "glotto", "glottocode", "language", "language_id", "lang", "lang_id")


def load_beastling_data(reader, lang_column, filename):
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


def load_cldf_data(reader):
    if "Feature_ID" in reader.fieldnames:
        feature_column = "Feature_ID"
    else:
        feature_column = "Parameter_ID"
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))
    for row in reader:
        lang = row["Language_ID"]
        if lang not in data:
            data[lang] = collections.defaultdict(lambda :"?")
        data[lang][row[feature_column]] = row["Value"]
    return data
