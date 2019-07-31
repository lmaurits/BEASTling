import re
import os
import pathlib

from clldutils.path import Path, remove
from clldutils.inifile import INI

import beastling.beastxml
import beastling.configuration
import beastling.extractor

PATH_PATTERN = re.compile(' file (?P<path>[^\s]+)$')


def test_read_comments(tmppath):
    fname = tmppath / 'test.xml'
    with fname.open('w', encoding='utf8') as fp:
        fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<r><!-- cümment --></r>
""")
    res = beastling.extractor.read_comments(fname)
    assert len(res) == 1
    assert res[0].text.strip() == 'cümment'


def _extract(xmlfile):
    res = beastling.extractor.extract(xmlfile)
    for line in res:
        match = PATH_PATTERN.search(line)
        if match:
            path = match.group('path').strip()[:-1]
            try:
                assert os.path.exists(path)
            except:
                raise ValueError(path)
            os.remove(path)
    return res


def test_extractor(config_factory, tmppath, data_dir):
    config = config_factory("admin", "mk", "embed_data")
    xml = beastling.beastxml.BeastXml(config)
    xmlfile = str(tmppath / "beastling.xml")
    xml.write_file(xmlfile)
    assert bool(_extract(xmlfile))

    config = config_factory({
            'admin': {'basename': 'abcdefg'},
            'model model': {
                'model': 'mk',
                'data': str(data_dir / 'basic.csv')}})
    xml = beastling.beastxml.BeastXml(config)
    xmlfile = str(tmppath / "beastling.xml")
    xml.write_file(xmlfile)
    beastling.extractor.extract(xmlfile)
    p = Path('abcdefg.conf')
    assert p.exists()
    cfg = INI(interpolation=None)
    cfg.read(p.as_posix())
    remove(p)
    assert cfg['admin']['basename'] == 'abcdefg'
    assert cfg['model model']['model'] == 'mk'

    fname = tmppath / 'test.xml'
    datafile = tmppath / 'test.csv'
    assert not datafile.exists()
    with fname.open('w', encoding='utf8') as fp:
        fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<r>
  <!--%s
%s
[admin]
[model model]
-->
  <!--%s:%s-->
</r>
""" % (beastling.extractor._generated_str,
       beastling.extractor._config_file_str,
       beastling.extractor._data_file_str,
       datafile.as_posix()))
    res = _extract(fname)
    assert datafile.name in ''.join(res)
