from nose.tools import *

import beastling.configuration
import beastling.fileio.datareaders
import beastling.beastxml

@raises(ValueError)
def test_duplicate_iso():
    config = beastling.configuration.Configuration(configfile="tests/configs/basic.conf")
    config.model_configs[0]["data"] = "tests/data/duplicated_iso.csv"
    config.process()

@raises(ValueError)
def test_no_iso_field():
    config = beastling.configuration.Configuration(configfile="tests/configs/basic.conf")
    config.model_configs[0]["data"] = "tests/data/no_iso.csv"
    config.process()

def test_cldf_data_reading():
    # Load the same data from files in BEASTling format and CLDF format
    # and ensure that identical structures are returned
    beastling_format = beastling.fileio.datareaders.load_data("tests/data/basic.csv")
    cldf_format = beastling.fileio.datareaders.load_data("tests/data/cldf.csv")
    assert beastling_format.keys() == cldf_format.keys()
    for key in beastling_format:
        beastling_format[key].pop("iso")
        assert beastling_format[key].items() == cldf_format[key].items()
