import os
import shutil

from nose.tools import *

import beastling.beastxml
import beastling.configuration
import beastling.extractor

_test_dir = os.path.dirname(__file__)

def test_extractor():
    config = beastling.configuration.Configuration(configfile="tests/configs/embed_data.conf")
    config.process()
    xml = beastling.beastxml.BeastXml(config)
    os.makedirs("testing_tmp_dir")
    os.chdir("testing_tmp_dir")
    xml.write_file("beastling.xml")
    beastling.extractor.extract("beastling.xml")

def teardown():
    os.chdir(os.path.join(_test_dir, ".."))
    shutil.rmtree("testing_tmp_dir")
