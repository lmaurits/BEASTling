# coding: utf8
from unittest import TestCase
import os

from nose.tools import *

from beastling.configuration import Configuration


class Tests(TestCase):

    def _make_tree_cfg(self, tree_file):
        cfg = Configuration(configfile=os.path.join(
            os.path.dirname(__file__), 'configs/starting_tree.conf'))
        cfg.starting_tree = "tests/trees/%s.nex" % tree_file
        return cfg

    def test_basic_starting_tree(self):
        cfg = self._make_tree_cfg("basic")
        cfg.process()

    def test_superset_tree(self):
        cfg = self._make_tree_cfg("superset")
        cfg.process()

    def test_polytomy_tree(self):
        cfg = self._make_tree_cfg("polytomies")
        cfg.process()

    @raises(ValueError)
    def test_subset_tree(self):
        cfg = self._make_tree_cfg("subset")
        cfg.process()

    @raises(ValueError)
    def test_subset_tree(self):
        cfg = self._make_tree_cfg("duplicates")
        cfg.process()
