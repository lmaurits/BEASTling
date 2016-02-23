# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase
import glob
import os

from nose.tools import *

from beastling.configuration import Configuration


class Tests(TestCase):
    def _make_cfg(self, name):
        return Configuration(configfile=os.path.join(
            os.path.dirname(__file__), 'configs', '%s.conf' % name))

    def _make_bad_cfg(self, name):
        return Configuration(configfile=os.path.join(
            os.path.dirname(__file__), 'configs/bad_configs/',
            '%s.conf' % name))

    def test_families(self):
        cfg1 = self._make_cfg('glottolog_families')
        cfg2 = self._make_cfg('glottolog_families_from_file')
        cfg1.process()
        cfg2.process()
        self.assertEqual(cfg1.lang_filter, cfg2.lang_filter)
        self.assertEqual(len(cfg1.lang_filter), 6107)

    @raises(ValueError)
    def test_no_data(self):
        cfg = self._make_bad_cfg("no_data")
        cfg.process()

    @raises(ValueError)
    def test_no_langs(self):
        cfg = self._make_bad_cfg("no_langs")
        cfg.process()

    @raises(ValueError)
    def test_no_langs(self):
        cfg = self._make_bad_cfg("no_model_sec")
        cfg.process()
        
    @raises(ValueError)
    def test_no_langs(self):
        cfg = self._make_bad_cfg("no_model")
        cfg.process()
        
    @raises(ValueError)
    def test_no_langs(self):
        cfg = self._make_bad_cfg("unknown_model")
        cfg.process()

    @raises(ValueError)
    def test_no_langs(self):
        cfg = self._make_bad_cfg("bad_overlap")
        cfg.process()
