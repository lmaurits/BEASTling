from nose.tools import *

import beastling.beastxml
import beastling.configuration

def test_extractor():
    config = beastling.configuration.Configuration(configfile="tests/configs/basic.conf")
    config.process()
    xml = beastling.beastxml.BeastXml(config)
    xml.write_file("stdout")
