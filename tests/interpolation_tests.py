# coding: utf8
from __future__ import unicode_literals

import unittest

from configalchemy import INI, BasicReadInterpolation
from clldutils.path import Path
from clldutils.misc import nfilter
from clldutils.testing import WithTempDirMixin


def tests_path(*comps):
    return Path(__file__).parent.joinpath(*nfilter(comps))


def config_path(name):
    if not name.endswith('.conf'):
        name += '.conf'
    return tests_path('configs', name)


class WithConfigMixin(WithTempDirMixin):
    def _make_cfg(self, *names):
        return self.make_cfg([config_path(name).as_posix() for name in names])

    def make_cfg(self, configfiles):
        config = INI(interpolation=BasicReadInterpolation())
        for conf in configfiles:
            with open(conf) as conffile:
                config.read_file(conffile)
        return config


class Tests(WithConfigMixin, unittest.TestCase):
    def test_interpolate(self):
        """Check that basic interpolation works."""
        config = self._make_cfg('basic', 'interpolate')
        self.assertEqual(
            config["admin"]["basename_plus"],
            "beastling_test_plus")

    def test_recursive_interpolate(self):
        """Check that interpolation of a value with itself works."""
        config = self._make_cfg('basic', 'recursive_interpolate')
        self.assertEqual(
            config["admin"]["basename"],
            "beastling_test_plus")

    def test_multiline_interpolate(self):
        """Check that interpolation of a multiline value with itself works.

        This must work as expected given read-time expansion of interpolations, so

        text = a
         n
         %(text)s
         a
         s

        should expand to

         a
         n
         a
         n
         a
         s

        etc.

        """
        config = self._make_cfg('basic', 'multiline_interpolate')
        self.assertEqual(
            config["DEFAULT"]["val"],
            "line1\nline2\nline3")
        self.assertEqual(
            config["DEFAULT"]["val_inter1"],
            "line1\nline2\nline3\nline4")
        self.assertEqual(
            config["DEFAULT"]["val_inter2"],
            "line0\nline1\nline2\nline3\nline4")
        self.assertEqual(
            config["DEFAULT"]["val_self_inter"],
            "a\nn\na\nn\na\ns")
