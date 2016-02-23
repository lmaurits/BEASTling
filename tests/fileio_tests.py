# coding: utf8
from __future__ import unicode_literals, print_function
from unittest import TestCase

from clldutils.path import Path

from beastling.fileio.datareaders import load_data


TEST_DATA = Path(__file__).parent.joinpath('data')


class Tests(TestCase):
    def test_load_data(self):
        for p in TEST_DATA.iterdir():
            if p.suffix == '.csv':
                print(p.name)
                if p.stem in ['duplicated_iso', 'no_iso', 'nonstandard_lang_col']:
                    self.assertRaises(ValueError, load_data, p)
                else:
                    data = load_data(p)
                    self.assertNotEqual(len(data), 0)
