# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase
import os

from beastling.configuration import Configuration


class Tests(TestCase):
    def _make_cfg(self, name):
        return Configuration(configfile=os.path.join(
            os.path.dirname(__file__), 'configs', '%s.conf' % name))

    def test_families(self):
        cfg1 = self._make_cfg('glottolog_families')
        cfg2 = self._make_cfg('glottolog_families_from_file')
        cfg1.process()
        cfg2.process()
        self.assertEqual(cfg1.lang_filter, cfg2.lang_filter)
        self.assertEqual(len(cfg1.lang_filter), 6107)
