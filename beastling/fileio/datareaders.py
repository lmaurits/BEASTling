import csv
import sys
import collections

from six import PY2

import pycldf.dataset
from pycldf.util import Path

from clldutils.dsv import UnicodeDictReader


def sniff(filename):
    """Read the beginning of the file and guess its csv dialect.

    Parameters
    ----------
    filename: str or pathlib.Path
        Path to a csv file to be sniffed

    Returns
    -------
    csv.Dialect
    """
    with Path(filename).open("rb" if PY2 else "r") as fp:
        # On large files, csv.Sniffer seems to need a lot of data to make a
        # successful inference...
        sample = fp.read(1024)
        while True:
            try:
                return csv.Sniffer().sniff(sample, [",", "\t"])
            except csv.Error: # pragma: no cover
                blob = fp.read(1024)
                sample += blob
                if not blob:
                    raise


def load_data(filename, file_format=None, lang_column=None, value_column=None):
    # Handle CSV dialect issues
    if str(filename) == 'stdin':
        filename = sys.stdin
        # We can't sniff from stdin, so guess comma-delimited and hope for
        # the best
        dialect = "excel" # Default dialect for csv module
    elif file_format and file_format.lower() == "cldf":
        return read_cldf_dataset(filename, value_column)
    elif file_format and file_format.lower() == "cldf-legacy":
        # CLDF pre-1.0 standard says delimiter is indicated by file extension
        if filename.suffix.lower() == ".csv" or str(filename) == "stdin":
            dialect = "excel"
        elif filename.suffix.lower() == ".tsv":
            dialect = "excel-tab"
        else:
            raise ValueError("CLDF standard dictates that filenames must end in .csv or .tsv")
    elif filename.suffix == ".json" or filename.name in {"forms.csv", "values.csv"}:
        # TODO: Should we just let the pycldf module try its hands on the file
        # and fall back to other formats if that doesn't work?
        return read_cldf_dataset(filename, value_column)
    else:
        # Use CSV dialect sniffer in all other cases
        dialect = sniff(filename)
    # Read
    with UnicodeDictReader(filename, dialect=dialect) as reader:
        # Guesstimate file format if user has not been explicit
        if file_format is None:
            file_format = 'cldf-legacy' if all(
                [f in reader.fieldnames for f in ("Language_ID", "Value")]) and any(
                    [f in reader.fieldnames for f in ("Feature_ID", "Parameter_ID")]
                ) else 'beastling'

        # Load data
        if file_format == 'cldf-legacy':
            data = load_cldf_data(reader, value_column, filename)
        elif file_format == 'beastling':
            data = load_beastling_data(reader, lang_column, filename)
        else:
            raise ValueError("File format specification '{:}' not understood".format(file_format))
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
        lang = row.pop(lang_column)
        data[lang] = collections.defaultdict(lambda : "?", row)
    return data


def load_cldf_data(reader, value_column, filename):
    if not value_column:
        value_column = "Value"
    if "Feature_ID" in reader.fieldnames:
        feature_column = "Feature_ID"
    elif "Parameter_ID" in reader.fieldnames:
        feature_column = "Parameter_ID"
    else:
        raise ValueError("Could not find Feature_ID or Parameter_ID column, is %s a valid CLDF file?" % filename)
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))
    for row in reader:
        lang = row["Language_ID"]
        if lang not in data:
            data[lang] = collections.defaultdict(lambda :"?")
        data[lang][row[feature_column]] = row[value_column]
    return data


def load_location_data(filename):

    # Use CSV dialect sniffer in all other cases
    with open(str(filename), "r") as fp: # Cast PosixPath to str
        # On large files, csv.Sniffer seems to need a lot of datta to make a
        # successful inference...
        sample = fp.read(1024)
        while True:
            try:
                dialect = csv.Sniffer().sniff(sample, [",","\t"])
                break
            except csv.Error: # pragma: no cover
                blob = fp.read(1024)
                sample += blob
                if not blob:
                    raise

    # Read
    with UnicodeDictReader(filename, dialect=dialect) as reader:
        # Identify fieldnames
        for fieldname in reader.fieldnames:
            if fieldname.lower() in _language_column_names:
                break
        else:
            raise ValueError("Could not find a language identifier column in location data file %s" % filename)
        lang_field = fieldname

        for fieldname in reader.fieldnames:
            if fieldname.lower() in ("latitude", "lat"):
                break
        else:
            raise ValueError("Could not find a latitude column in location data file %s" % filename)
        latitude_field = fieldname

        for fieldname in reader.fieldnames:
            if fieldname.lower() in ("longitude", "lon", "long"):
                break
        else:
            raise ValueError("Could not find a longitude column in location data file %s" % filename)
        longitude_field = fieldname

        locations = {}
        for row in reader:
            (lat, lon) = row[latitude_field], row[longitude_field]
            try:
                lat = float(lat) if lat != "?" else lat
                lon = float(lon) if lon != "?" else lon
            except ValueError:
                lat, lon = "?", "?"
            locations[row[lang_field].strip()] = (lat, lon)

        return locations


def get_dataset(fname):
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Dataset
    """
    fname = Path(fname)
    if not fname.exists():
        raise FileNotFoundError(
            '{:} does not exist'.format(fname))
    if fname.suffix == '.json':
        return pycldf.dataset.Dataset.from_metadata(fname)
    return pycldf.dataset.Dataset.from_data(fname)


def read_cldf_dataset(filename, code_column=None):
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Dataset
    """
    dataset = get_dataset(filename)
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))
    if dataset.module == "Wordlist":
        if code_column:
            cognate_column_in_form_table = True
        else:
            try:
                code_column = dataset["FormTable", "cognatesetReference"].name
                cognate_column_in_form_table = True
                # The form table contains cognate sets!
            except KeyError:
                cognatesets = collections.defaultdict(lambda: "?")
                try:
                    form_reference = dataset["CognateTable", "formReference"].name
                    code_column = dataset["CognateTable", "cognatesetReference"].name
                except KeyError:
                    raise ValueError(
                        "Dataset {:} has no cognatesetReference column in its "
                        "primary table or in a separate cognate table. "
                        "Is this a metadata-free wordlist and you forgot to "
                        "specify code_column explicitly?".format(filename))
                for row in dataset["CognateTable"].iterdicts():
                    cognatesets[row[form_reference]] = row[code_column]
                form_column = dataset["FormTable", "id"].name
                cognate_column_in_form_table = False

        language_column = dataset["FormTable", "languageReference"].name
        parameter_column = dataset["FormTable", "parameterReference"].name

        for row in dataset["FormTable"].iterdicts():
            if cognate_column_in_form_table:
                data[row[language_column]][row[parameter_column]] = row[code_column]
            else:
                data[row[language_column]][row[parameter_column]] = cognatesets[row[form_column]]
        return data
    elif dataset.module == "StructureDataset":
        language_column = dataset["ValueTable", "languageReference"].name
        parameter_column = dataset["ValueTable", "parameterReference"].name
        code_column = code_column or dataset["ValueTable", "codeReference"].name
        for row in dataset["ValueTable"].iterdicts():
            data[row[language_column]][row[parameter_column]] = row[code_column]
        return data
    else:
        raise ValueError("Beastling does not know how to interpret CLDF {:} data.".format(
            dataset.module))


