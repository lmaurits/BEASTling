from __future__ import unicode_literals

import beastling.beastxml
import beastling.configuration
from .util import WithConfigAndTempDir, old_capture, config_path


class Tests(WithConfigAndTempDir):
    def test_stdout(self):
        xml = beastling.beastxml.BeastXml(self.make_cfg(config_path("basic").as_posix()))
        with old_capture(xml.write_file, 'stdout') as output:
            self.assertIn('<?xml version=', output[0].decode('utf8'))
