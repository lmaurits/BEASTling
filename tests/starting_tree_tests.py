# coding: utf8
from nose.tools import *

from .util import WithConfigAndTempDir, config_path, tests_path


class Tests(WithConfigAndTempDir):

    def _make_tree_cfg(self, tree_file):
        config_files = [config_path(cf).as_posix() for cf in ["admin", "mk", tree_file]]
        cfg = self.make_cfg(config_files)
        cfg.starting_tree = tests_path('trees', "%s.nex" % tree_file).as_posix()
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
    def test_duplicate_taxa_tree(self):
        cfg = self._make_tree_cfg("duplicates")
        cfg.process()
