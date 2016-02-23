# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase
import glob
import os
from tempfile import mktemp
from shutil import rmtree, copy
import io

from nose.tools import *
from mock import patch, Mock

import beastling
from beastling.configuration import Configuration, get_glottolog_newick


class Tests(TestCase):
    def setUp(self):
        self.tmp = mktemp()
        os.mkdir(self.tmp)

    def tearDown(self):
        rmtree(self.tmp)

    def _make_cfg(self, name):
        return Configuration(configfile=os.path.join(
            os.path.dirname(__file__), 'configs', '%s.conf' % name))

    def _make_bad_cfg(self, name):
        return Configuration(configfile=os.path.join(
            os.path.dirname(__file__), 'configs/bad_configs/',
            '%s.conf' % name))

    def test_get_glottolog_newick(self):
        with io.open(
            os.path.join(self.tmp, 'glottolog-2.5.newick'), 'w', encoding='utf8'
        ) as fp:
            fp.write('(B [abcd1234],C [abcd1234])A [abcd1234];')

        with patch(
                'beastling.configuration.user_data_dir', new=Mock(return_value=self.tmp)):
            trees = get_glottolog_newick('2.5')
            self.assertEqual(trees[0].name, 'A [abcd1234]')

    def test_get_glottolog_newick_download(self):
        data_dir = os.path.join(self.tmp, 'data')

        class URLopener(object):
            def retrieve(self, url, fname):
                with io.open(fname, 'w', encoding='utf8') as fp:
                    fp.write('(B [abcd1234],C [abcd1234])A [abcd1234];')

        class URLopenerError(object):
            def retrieve(self, url, fname):
                raise IOError()

        with patch.multiple(
            'beastling.configuration',
            user_data_dir=Mock(return_value=data_dir),
            URLopener=URLopenerError,
        ):
            with self.assertRaises(ValueError):
                get_glottolog_newick('2.5')

        with patch.multiple(
            'beastling.configuration',
            user_data_dir=Mock(return_value=data_dir),
            URLopener=URLopener,
        ):
            trees = get_glottolog_newick('2.5')
            self.assertEqual(trees[0].name, 'A [abcd1234]')

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
    def bad_overlap(self):
        cfg = self._make_bad_cfg("bad_overlap")
        cfg.process()
