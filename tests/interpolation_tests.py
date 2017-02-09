# coding: utf8
from __future__ import unicode_literals

from .util import WithConfigAndTempDir
from nose.plugins.skip import SkipTest


class Tests(WithConfigAndTempDir):
    def test_interpolate(self):
        """Check that basic interpolation works."""
        raise SkipTest
        config = self._make_cfg('basic', 'interpolate')
        config.process()
        self.assertEqual(
            config.configfile["admin"]["basename_plus"],
            "beastling_test_plus")

    def test_recursive_interpolate(self):
        """Check that interpolation of a value with itself works."""
        raise SkipTest
        config = self._make_cfg('basic', 'recursive_interpolate')
        config.process()
        self.assertEqual(
            config.configfile["admin"]["basename"],
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
        raise SkipTest
        config = self._make_cfg('basic', 'multiline_interpolate')
        config.process()
        self.assertEqual(
            config.configfile["DEFAULT"]["val"],
            "line1\nline2\nline3")
        self.assertEqual(
            config.configfile["DEFAULT"]["val_inter1"],
            "line1\nline2\nline3\nline4")
        self.assertEqual(
            config.configfile["DEFAULT"]["val_inter2"],
            "line0\nline1\nline2\nline3\nline4")
        self.assertEqual(
            config.configfile["DEFAULT"]["val_self_inter"],
            "a\nn\na\nn\na\ns")
