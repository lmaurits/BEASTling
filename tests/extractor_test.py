# coding: utf8
from __future__ import unicode_literals
import re
import os

from clldutils.path import Path, remove
from clldutils.inifile import INI

import beastling.beastxml
import beastling.configuration
import beastling.extractor
from .util import WithConfigAndTempDir


TESTS_DIR = Path(__file__).parent
PATH_PATTERN = re.compile(' file (?P<path>[^\s]+)$')


class Tests(WithConfigAndTempDir):
    def test_read_comments(self):
        fname = self.tmp.joinpath('test.xml')
        with fname.open('w', encoding='utf8') as fp:
            fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<r><!-- cümment --></r>
""")
        res = beastling.extractor.read_comments(fname)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].text.strip(), 'cümment')

    def _extract(self, xmlfile):
        res = beastling.extractor.extract(xmlfile)
        for line in res:
            match = PATH_PATTERN.search(line)
            if match:
                path = match.group('path').strip()[:-1]
                try:
                    self.assertTrue(os.path.exists(path))
                except:
                    raise ValueError(path)
                os.remove(path)
        return res

    def test_extractor(self):
        config = self.make_cfg([
            TESTS_DIR.joinpath("configs", f + ".conf").as_posix()
            for f in ("admin", "mk", "embed_data")])
        xml = beastling.beastxml.BeastXml(config)
        xmlfile = self.tmp.joinpath("beastling.xml")
        xml.write_file(xmlfile.as_posix())
        self.assertTrue(bool(self._extract(xmlfile)))

        config = self.make_cfg({
            'admin': {'basename': 'abcdefg'},
            'model': {
                'model': 'mk',
                'data': TESTS_DIR.joinpath('data', 'basic.csv').as_posix()}})
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
        res = self._extract(fname)
        self.assertIn(datafile.name, ''.join(res))
