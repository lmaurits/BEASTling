# coding: utf8
from __future__ import unicode_literals
import unittest
from tempfile import mktemp

from clldutils.path import Path, rmtree, remove

import beastling.beastxml
import beastling.configuration
import beastling.extractor


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(mktemp('testing_tmp_dir'))
        self.tmp.mkdir()
        self.test_dir = Path(__file__).parent

    def tearDown(self):
        rmtree(self.tmp)

    def test_read_comments(self):
        fname = self.tmp.joinpath('test.xml')
        with fname.open('w', encoding='utf8') as fp:
            fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<r><!-- cümment --></r>
""")
        res = beastling.extractor.read_comments(fname)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].text.strip(), 'cümment')

    def test_extractor(self):
        config = beastling.configuration.Configuration(
            configfile=self.test_dir.joinpath("configs", "embed_data.conf").as_posix())
        config.process()
        xml = beastling.beastxml.BeastXml(config)
        xmlfile = self.tmp.joinpath("beastling.xml")
        xml.write_file(xmlfile.as_posix())
        res = beastling.extractor.extract(xmlfile)
        self.assertTrue(bool(res))

        config = beastling.configuration.Configuration(
            configfile={
                'admin': {'basename': 'abcdefg'},
                'model': {
                    'model': 'mk',
                    'data': self.test_dir.joinpath('data', 'basic.csv').as_posix()}})
        config.process()
        xml = beastling.beastxml.BeastXml(config)
        xmlfile = self.tmp.joinpath("beastling.xml")
        xml.write_file(xmlfile.as_posix())
        res = beastling.extractor.extract(xmlfile)
        p = Path('abcdefg.conf')
        self.assertTrue(p.exists())
        remove(p)
