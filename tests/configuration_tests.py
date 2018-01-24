# coding: utf8
from __future__ import unicode_literals
import os
import io
import sys

from nose.tools import *
from mock import patch, Mock
import newick
from clldutils.path import Path

from beastling.configuration import (
    Configuration, get_glottolog_data, _BEAST_MAX_LENGTH,
)
from beastling.beastxml import BeastXml
from .util import WithConfigAndTempDir, config_path

def check_lat_lon(provided, target_lat, target_lon):
    prov_lat, prov_lon = provided
    return round(prov_lat, 2) == target_lat and round(prov_lon, 2) == target_lon

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
    def test_bad_overlap(self):
        cfg = self._make_bad_cfg("bad_overlap")
        cfg.process()

    @raises(ValueError)
    def test_bad_frequencies(self):
        cfg = self._make_bad_cfg("bad_frequencies")
        cfg.process()
        # This is an error in a model section, which is only raised
        # when the model is constructed as XML.
        BeastXml(cfg)

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
        self.assertEqual(list(config.calibrations.values())[0].param2, sys.maxsize)
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


    @raises(ValueError)
    def test_calibration_bad_bounds(self):
        config = Configuration(configfile=[
            config_path("basic").as_posix(),
            config_path("bad_cal_endpoints", bad=True).as_posix(),
            ])
        config.process()

    @raises(ValueError)
    def test_calibration_bad_monophyly(self):
        config = Configuration(configfile=[
            config_path("basic").as_posix(),
            config_path("monophyletic").as_posix(),
            config_path("bad_cal_monophyly", bad=True).as_posix(),
            ])
        config.process()

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

    def test_pruned_rlc(self):
        # Make sure pruned trees are disabled if used in conjunction with RLC
        config = self._make_cfg('basic', 'pruned', 'random')
        self.assertTrue(config.model_configs[0]["pruned"])
        config.process()
        self.assertFalse(config.models[0].pruned)

    def test_no_monophyly_geo(self):
        # Make sure that geographic sampling without monophyly constraints emits a warning
        config = self._make_cfg('basic', 'geo', 'geo_sampled')
        config.process()
        self.assertTrue(any(["[WARNING] Geographic sampling" in m for m in config.messages]))

    def test_ascertainment_auto_setting(self):
        # Without calibration, there should be no ascertainment...
        config = self._make_cfg('basic')
        config.process()
        self.assertFalse(config.models[0].ascertained)
        # But with it there should...
        config = self._make_cfg('basic', 'calibration')
        config.process()
        self.assertTrue(config.models[0].ascertained)
        # Unless, of course, we have constant data...
        config = self._make_cfg('covarion_multistate', 'calibration')
        config.model_configs[0]["remove_constant_features"] = False
        config.process()
        self.assertFalse(config.models[0].ascertained)

    def test_ascertainment_override(self):
        # Make sure we can override the above automagic
        config = self._make_cfg('basic', 'ascertainment_true')
        config.process()
        self.assertTrue(config.models[0].ascertained)
        # And with calibrations...
        config = self._make_cfg('basic', 'calibration', 'ascertainment_false')
        config.process()
        self.assertFalse(config.models[0].ascertained)

    def test_bad_ascertainment(self):
        # Make sure we refuse to produce a misspecified model
        config = self._make_cfg('covarion_multistate','ascertainment_true')
        config.model_configs[0]["remove_constant_features"] = False
        with self.assertRaises(ValueError):
            config.process()

    def test_binarisation_ascertainment(self):
        # Even with ascertainment = False, ascertainment should still
        # be done for recoded data
        config = self._make_cfg('covarion_binarised','ascertainment_false')
        config.process()
        xml = BeastXml(config).tostring().decode('utf8')
        self.assertTrue("ascertained=\"true\"" in xml)
        self.assertTrue("excludeto=\"1\"" in xml)

    def test_user_locations(self):
        # First check that we correctly load Glottolog's locations for aiw and abp
        config = self._make_cfg('basic', 'geo')
        config.process()
        self.assertTrue(check_lat_lon(config.locations["aiw"], 5.95, 36.57))
        self.assertTrue(check_lat_lon(config.locations["abp"], 15.41, 120.20))
        # Now check that we can overwrite just one of these...
        config = self._make_cfg('basic', 'geo', 'geo_user_loc')
        config.process()
        self.assertTrue(check_lat_lon(config.locations["aiw"], 4.20, 4.20))
        self.assertTrue(check_lat_lon(config.locations["abp"], 15.41, 120.20))
        # Make sure that specifying the location data in [languages] caused a deprecation warning
        self.assertTrue(len(config.urgent_messages) > 0)
        # Repeat the above test but specifying location data in [geography], which should cause no warning
        config = self._make_cfg('basic', 'geo', 'new_geo_user_loc')
        config.process()
        self.assertTrue(check_lat_lon(config.locations["aiw"], 4.20, 4.20))
        self.assertTrue(check_lat_lon(config.locations["abp"], 15.41, 120.20))
        self.assertTrue(len(config.urgent_messages) == 0)
        # Now check that we can overwrite them both using multiple files
        config = self._make_cfg('basic', 'geo', 'geo_user_loc_multifile')
        config.process()
        self.assertTrue(check_lat_lon(config.locations["aiw"], 4.20, 4.20))
        self.assertTrue(check_lat_lon(config.locations["abp"], 6.66, 6.66))

    def test_monophyly_levels(self):
        # The isolates.csv data file contains Japanese, Korean and Basque, plus
        # English and Russian.  When used with standard monophly, we should see
        # a four-way polytomy with eng+rus grouped (IE) and the rest isolated.
        config = self._make_cfg('admin', 'mk', 'isolates', 'monophyletic')
        config.process()
        tree = newick.loads(config.monophyly_newick)[0]
        assert len(tree.descendants) == 4
        for node in tree.descendants:
            if len(node.descendants) == 2:
                assert all((l.is_leaf and l.name in ("eng", "rus") for l in node.descendants))
        # Now we set monophyly_start_depth to 1, i.e. ignore the top-most
        # level of Glottolog constraints.  Now we should just have a massive
        # polytomy, since IE no longer matters and eng and rus are in separate
        # subfamilies (Germanic vs Balto-Slavic).
        config = self._make_cfg('admin', 'mk', 'isolates', 'monophyletic-start-depth')
        config.process()
        tree = newick.loads(config.monophyly_newick)[0]
        assert len(tree.descendants) == 5

    def test_subsampling(self):
        # First check how many languages there usually are
        config = self._make_cfg('admin', 'mk')
        config.process()
        full_lang_count = len(config.languages)
        # Try various subsamples and make sure they work
        for subsample_size in range(2, full_lang_count):
            config = self._make_cfg('admin', 'mk')
            config.subsample_size = subsample_size
            config.process()
            assert len(config.languages) == subsample_size
        # Make sure if we ask for more languages than we have nothing happens
        config = self._make_cfg('admin', 'mk')
        config.subsample_size = full_lang_count + 42
        config.process()
        assert len(config.languages) == full_lang_count

    def test_language_groups(self):
        config = self._make_cfg('basic', 'taxa')
        config.process()
        self.assertEqual(config.language_groups["abf"], {"abf"})
        self.assertEqual(config.language_groups["macronesian"], {"kbt", "abf", "abg"})

    @raises(KeyError)
    def test_nonexisting_language_group(self):
        config = self._make_cfg('basic', 'reconstruct_one')
        config.process()
