# coding: utf8
from __future__ import unicode_literals
import os
import io

from nose.tools import *
from mock import patch, Mock
import newick
from clldutils.path import Path

from beastling.configuration import (
    Configuration, get_glottolog_data, _BEAST_MAX_LENGTH,
)
from beastling.beastxml import BeastXml
from .util import WithConfigAndTempDir, config_path


class Tests(WithConfigAndTempDir):
    def _make_cfg(self, *names):
        return self.make_cfg([config_path(name).as_posix() for name in names])

    def _make_bad_cfg(self, name):
        return self.make_cfg(config_path(name, bad=True).as_posix())

    def test_get_glottolog_geo(self):
        geodata = self.tmp.joinpath('glottolog-2.5-geo.csv')
        with geodata.open('w', encoding='utf8') as fp:
            fp.write('x')

        with patch(
                'beastling.configuration.user_data_dir',
                new=Mock(return_value=self.tmp.as_posix())):
            self.assertEqual(Path(get_glottolog_data('geo', '2.5')), geodata)

    def test_get_glottolog_newick(self):
        with self.tmp.joinpath('glottolog-2.5.newick').open('w', encoding='utf8') as fp:
            fp.write('(B [abcd1234],C [abcd1234])A [abcd1234];')

        with patch(
                'beastling.configuration.user_data_dir',
                new=Mock(return_value=self.tmp.as_posix())):
            trees = newick.read(get_glottolog_data('newick', '2.5'))
            self.assertEqual(trees[0].name, 'A [abcd1234]')

    def test_get_glottolog_data_download(self):
        data_dir = os.path.join(self.tmp.as_posix(), 'data')

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
                get_glottolog_data('newick', '2.5')

        with patch.multiple(
            'beastling.configuration',
            user_data_dir=Mock(return_value=data_dir),
            URLopener=URLopener,
        ):
            assert get_glottolog_data('newick', '2.5')

    def test_families(self):
        cfg1 = self._make_cfg('glottolog_families')
        cfg2 = self._make_cfg('glottolog_families_from_file')
        cfg1.process()
        cfg2.process()
        self.assertEqual(cfg1.languages, cfg2.languages)

    def test_config(self):
        cfg = Configuration(configfile={
            'admin': {

            },
            'languages': {
                'monophyly': True,
                'starting_tree': 'T',
                'sample_topology': False,
                'sample_branch_lengths': False,
            },
            'calibration': {
                'abcd1234, efgh5678': '10-20',
            },
            'model': {
                'binarised': True,
                'minimum_data': '4.5'
            },
            'model2': {
                'binarized': True,
            },
        })
        self.assertAlmostEqual(cfg.calibration_configs['abcd1234, efgh5678'], "10-20")
        self.assertTrue(cfg.model_configs[1]['binarised'])

        with self.assertRaisesRegexp(ValueError, 'Value for overlap') as e:
            Configuration(configfile={'languages': {'overlap': 'invalid'}, 'models': {}})

        with self.assertRaisesRegexp(ValueError, 'Config file') as e:
            Configuration(configfile={'languages': {}})

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

    def test_calibration(self):
        config = self._make_cfg('basic', 'calibration')
        config.process()
        self.assertIn('Austronesian', config.calibrations)
        v = config.calibrations['Austronesian']
        xml1 = BeastXml(config).tostring().decode('utf8')

        # Now remove one calibration point ...
        del config.calibrations['Austronesian']
        xml2 = BeastXml(config).tostring().decode('utf8')
        self.assertNotEqual(
            len(xml1.split('CalibrationDistribution.')), len(xml2.split('CalibrationDistribution.')))

        # ... and add it back in with using the glottocode:
        config.calibrations['aust1307'] = v
        xml2 = BeastXml(config).tostring().decode('utf8')
        self.assertEqual(
            len(xml1.split('CalibrationDistribution.')), len(xml2.split('CalibrationDistribution.')))

    def test_calibration_string_formats(self):
        # Test lower bound format
        config = self._make_cfg('basic', 'calibration_lower_bound')
        config.process()
        self.assertEqual(list(config.calibrations.values())[0].dist, "uniform")
        self.assertEqual(list(config.calibrations.values())[0].param2, "Infinity")
        # Test upper bound format
        config = self._make_cfg('basic', 'calibration_upper_bound')
        config.process()
        self.assertEqual(list(config.calibrations.values())[0].dist, "uniform")
        self.assertEqual(list(config.calibrations.values())[0].param1, 0.0)

        # Test range and param formats for all three distributions
        for dist in ('normal', 'lognormal', 'uniform'):
            for style in ('range', 'params'):
                config = self._make_cfg('basic', 'calibration_%s_%s' % (dist, style))
                config.process()
            self.assertEqual(list(config.calibrations.values())[0].dist, dist)


    def test_overlong_chain(self):
        config = self._make_cfg('basic')
        config.chainlength = 9e999
        config.process()
        self.assertEqual(config.chainlength, _BEAST_MAX_LENGTH)

    def test_file_embedding(self):
        config = self._make_cfg('glottolog_families_from_file','embed_data')
        xml = BeastXml(config).tostring().decode('utf8')
        # Check for evidence of data
        self.assertTrue("aari1239,1,1,1,1,1,1,?,1,?,1" in xml)
        # Check for evidence of families
        self.assertTrue("Malayo-Polynesian" in xml)

    def test_minimum_data(self):
        # f8 has 60% missing data.  By default it should be included...
        config = self._make_cfg('basic')
        config.process()
        self.assertTrue("f8" in config.models[0].features)
        # ...but if we insist on 75% data or more it should be excluded...
        config = self._make_cfg('basic', 'minimum_data')
        config.process()
        self.assertEqual(config.models[0].minimum_data, 75.0)
        self.assertTrue("f8" not in config.models[0].features)
