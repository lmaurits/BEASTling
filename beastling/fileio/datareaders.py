import csv
import sys
import collections
from pathlib import Path
import chardet

import pycldf.dataset
from csvw.dsv import UnicodeDictReader

from beastling.util import log


def sniff(filename, default_dialect=csv.excel):
    """Read the beginning of the file and guess its csv dialect.

    Parameters
    ----------
    filename: str or pathlib.Path
        Path to a csv file to be sniffed

    Returns
    -------
    csv.Dialect
    """
    with Path(filename).open("rb") as fp:
        # On large files, csv.Sniffer seems to need a lot of data to make a
        # successful inference...
        sample = fp.read(1024)
        encoding = chardet.detect(sample)["encoding"]
        sample = sample.decode(encoding)
        while True:
            try:
                return csv.Sniffer().sniff(sample, [",", "\t"])
            except csv.Error: # pragma: no cover
                blob = fp.read(1024).decode(encoding)
                sample += blob
                if not blob:
                    # If blob is emtpy we've somehow hit the end of the file
                    # without figuring out the dialect.  Something is probably
                    # quite wrong with the file, but let's default to Excel and
                    # hope for the best...
                    if default_dialect is not None:
                        return default_dialect
                    raise


def sanitise_name(name):
    """
    Take a name for a language or a feature which has come from somewhere like
    a CLDF dataset and make sure it does not contain any characters which
    will cause trouble for BEAST or postanalysis tools.
    """
    return name.replace(" ", "_")


def load_data(filename, file_format=None, lang_column=None, value_column=None, expect_multiple=False):
    # Handle CSV dialect issues
    if str(filename) == 'stdin':
        filename = sys.stdin
        # We can't sniff from stdin, so guess comma-delimited and hope for
        # the best
        dialect = "excel" # Default dialect for csv module
    elif file_format and file_format.lower() == "cldf":
        return read_cldf_dataset(filename, value_column, expect_multiple=expect_multiple)
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
        return read_cldf_dataset(filename, value_column, expect_multiple=expect_multiple)
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
            data = load_cldf_data(reader, value_column, filename, expect_multiple=expect_multiple)
        elif file_format == 'beastling':
            data = load_beastling_data(reader, lang_column, filename, expect_multiple=expect_multiple)
        else:
            raise ValueError("File format specification '{:}' not understood".format(file_format))
    return data, {}

_language_column_names = ("iso", "iso_code", "glotto", "glottocode", "language", "language_id", "lang", "lang_id")


def load_beastling_data(reader, lang_column, filename, expect_multiple=False):
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
        if expect_multiple:
            data[lang] = collections.defaultdict(lambda : "?", {key: [value] for key, value in row.items()})
        else:
            data[lang] = collections.defaultdict(lambda : "?", row)
    return data


def load_cldf_data(reader, value_column, filename, expect_multiple=False):
    value_column = value_column or "Value"
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
            if expect_multiple:
                data[lang] = collections.defaultdict(lambda: [])
            else:
                data[lang] = collections.defaultdict(lambda: "?")
        if expect_multiple:
            data[lang][row[feature_column]].append(row[value_column])
        else:
            data[lang][row[feature_column]] = row[value_column]
    return data


def iterlocations(filename):
    with UnicodeDictReader(filename, dialect=sniff(filename, default_dialect=None)) as reader:
        # Identify fieldnames
        fieldnames = [(n.lower(), n) for n in reader.fieldnames]
        fieldmap = {}

        for field, aliases in [
            ('language identifier', _language_column_names),
            ('latitude', ("latitude", "lat")),
            ('longitude', ("longitude", "lon", "long")),
        ]:
            for lname, fieldname in fieldnames:
                if lname in aliases:
                    fieldmap[field] = fieldname
                    break
            else:
                raise ValueError(
                    "Could not find a {0} column in location data file {1}".format(field, filename))

        for row in reader:
            (lat, lon) = row[fieldmap['latitude']], row[fieldmap['longitude']]
            try:
                lat = float(lat) if lat != "?" else lat
                lon = float(lon) if lon != "?" else lon
            except ValueError:
                lat, lon = "?", "?"
            yield (row[fieldmap['language identifier']].strip(), (lat, lon))


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
        raise FileNotFoundError('{:} does not exist'.format(fname))
    if fname.suffix == '.json':
        return pycldf.dataset.Dataset.from_metadata(fname)
    return pycldf.dataset.Dataset.from_data(fname)


def read_cldf_dataset(filename, code_column=None, expect_multiple=False):
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
    if expect_multiple:
        data = collections.defaultdict(lambda: collections.defaultdict(lambda: []))
    else:
        data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))

    # Make sure this is a kind of dataset BEASTling can handle
    if dataset.module not in ("Wordlist", "StructureDataset"):
        raise ValueError("BEASTling does not know how to interpret CLDF {:} data.".format(
            dataset.module))

    # Build dictionaries of nice IDs for languages and features
    col_map = dataset.column_names
    lang_ids, language_code_map = build_lang_ids(dataset, col_map)
    feature_ids = {}
    if col_map.parameters:
        for row in dataset["ParameterTable"]:
            feature_ids[row[col_map.parameters.id]] = sanitise_name(row[col_map.parameters.name])

    # Build actual data dictionary, based on dataset type
    if dataset.module == "Wordlist":
        # We search for cognatesetReferences in the FormTable or a separate CognateTable.
        # If we find them in CognateTable, we store them keyed with formReference:
        cognatesets = collections.defaultdict(lambda: "?")
        if not code_column:  # If code_column is given explicitly, we don't have to search!
            code_column = col_map.forms.cognatesetReference
            if not code_column:
                if col_map.cognates:
                    code_column = col_map.cognates.cognatesetReference
                    for row in dataset["CognateTable"]:
                        #
                        # Note: We assume that each form belongs to at most one cognate set!
                        # If this is not the case, the last cognate set wins.
                        #
                        cognatesets[row[col_map.cognates.formReference]] = row[code_column]
                else:
                    raise ValueError(
                        "Dataset {:} has no cognatesetReference column in its "
                        "primary table or in a separate cognate table. "
                        "Is this a metadata-free wordlist and you forgot to "
                        "specify code_column explicitly?".format(filename))

        for row in dataset["FormTable"]:
            lang_id = lang_ids.get(
                row[col_map.forms.languageReference], row[col_map.forms.languageReference])
            feature_id = feature_ids.get(
                row[col_map.forms.parameterReference], row[col_map.forms.parameterReference])

            cogset = cognatesets[row[col_map.forms.id]] if cognatesets else row[code_column]
            if expect_multiple:
                data[lang_id][feature_id].append(cogset)
            else:
                data[lang_id][feature_id] = cogset
        return data, language_code_map

    if dataset.module == "StructureDataset":
        code_column = col_map.values.codeReference or col_map.values.value
        for row in dataset["ValueTable"]:
            lang_id = lang_ids.get(
                row[col_map.values.languageReference], row[col_map.values.languageReference])
            feature_id = feature_ids.get(
                row[col_map.values.parameterReference], row[col_map.values.parameterReference])
            if expect_multiple:
                data[lang_id][feature_id].append(row[code_column] or '')
            else:
                data[lang_id][feature_id] = row[code_column] or ''
        return data, language_code_map


def build_lang_ids(dataset, col_map):
    if col_map.languages is None:
        # No language table so we can't do anything
        return {}, {}

    col_map = col_map.languages
    lang_ids = {}
    language_code_map = {}

    # First check for unique names and Glottocodes
    names = []
    gcs = []
    langs = []
    for row in dataset["LanguageTable"]:
        langs.append(row)
        names.append(row[col_map.name])
        if row[col_map.glottocode]:
            gcs.append(row[col_map.glottocode])

    unique_names = len(set(names)) == len(names)
    unique_gcs = len(set(gcs)) == len(gcs) == len(names)

    log.info('{0} are used as language identifiers'.format(
        'Names' if unique_names else ('Glottocodes' if unique_gcs else 'dataset-local IDs')))

    for row in langs:
        if unique_names:
            # Use names if they're unique, for human-friendliness
            lang_ids[row[col_map.id]] = sanitise_name(row[col_map.name])
        elif unique_gcs:
            # Otherwise, use glottocodes as at least they are meaningful
            lang_ids[row[col_map.id]] = row[col_map.glottocode]
        else:
            # As a last resort, use the IDs which are guaranteed to be unique
            lang_ids[row[col_map.id]] = row[col_map.id]
        if row[col_map.glottocode]:
            language_code_map[lang_ids[row[col_map.id]]] = row[col_map.glottocode]
    return lang_ids, language_code_map
