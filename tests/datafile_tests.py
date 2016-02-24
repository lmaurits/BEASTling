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
