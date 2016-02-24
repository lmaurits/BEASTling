import os
import shutil
import unittest
from tempfile import mktemp

import beastling.beastxml
import beastling.configuration
import beastling.extractor

_test_dir = os.path.dirname(__file__)


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = mktemp('testing_tmp_dir')
        os.mkdir(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_extractor(self):
        config = beastling.configuration.Configuration(
            configfile="tests/configs/embed_data.conf")
        config.process()
        xml = beastling.beastxml.BeastXml(config)
        xmlfile = os.path.join(self.tmp, "beastling.xml")
        xml.write_file(xmlfile)
        res = beastling.extractor.extract(xmlfile)
        self.assertTrue(bool(res))
