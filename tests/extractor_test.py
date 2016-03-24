# coding: utf8
from __future__ import unicode_literals
import unittest
from tempfile import mktemp

from clldutils.path import Path, rmtree, remove
from clldutils.inifile import INI

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
            configfile=[self.test_dir.joinpath("configs", f+".conf").as_posix() for f in ("admin", "mk", "embed_data")])
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
        beastling.extractor.extract(xmlfile)
        p = Path('abcdefg.conf')
        self.assertTrue(p.exists())
        cfg = INI(interpolation=None)
        cfg.read(p.as_posix())
        remove(p)
        self.assertEqual(cfg['admin']['basename'], 'abcdefg')
        self.assertEqual(cfg['model']['model'], 'mk')

        fname = self.tmp.joinpath('test.xml')
        datafile = self.tmp.joinpath(('test.csv'))
        self.assertFalse(datafile.exists())
        with fname.open('w', encoding='utf8') as fp:
            fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<r>
  <!--%s
%s
[admin]
[model]
-->
  <!--%s:%s-->
</r>
""" % (beastling.extractor._generated_str,
       beastling.extractor._config_file_str,
       beastling.extractor._data_file_str,
       datafile.as_posix()))
        beastling.extractor.extract(fname)
        self.assertTrue(datafile.exists())
