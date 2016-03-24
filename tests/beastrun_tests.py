import glob
import os
from subprocess import check_call, PIPE
from xml.etree import ElementTree as et

from nose.plugins.attrib import attr


import beastling.configuration
import beastling.beastxml
from .util import WithConfigAndTempDir


@attr('with_beast')
class Tests(WithConfigAndTempDir):
    def test_basic(self):
        """Turn each BEASTling config file in tests/configs into a
        BEAST.xml, and feed it to BEAST, testing for a zero return
        value, which suggests no deeply mangled XML."""
        temp_filename = self.tmp_path('test').as_posix()
        test_files = glob.glob("tests/configs/*.conf")
        assert test_files
        for test_file in test_files:
            xml = beastling.beastxml.BeastXml(self.make_cfg(test_file))
            xml.write_file(temp_filename)
            if os.environ.get('TRAVIS'):
                et.parse(temp_filename)
            else:
                check_call(
                    ['beast', '-overwrite', temp_filename],
                    cwd=self.tmp.as_posix(),
                    stdout=PIPE,
                    stderr=PIPE)
