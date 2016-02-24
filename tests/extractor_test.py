import os
import shutil

from nose.tools import *

import beastling.beastxml
import beastling.configuration
import beastling.extractor

def test_extractor():
    config = beastling.configuration.Configuration(configfile="tests/configs/embed_data.conf")
    config.process()
    xml = beastling.beastxml.BeastXml(config)
    os.makedirs("testing_tmp_dir")
    os.chdir("testing_tmp_dir")
    xml.write_file("beastling.xml")
    beastling.extractor.extract("beastling.xml")
    os.chdir("..")
    shutil.rmtree("testing_tmp_dir")
    assert not os.path.exists("testing_tmp_dir")
