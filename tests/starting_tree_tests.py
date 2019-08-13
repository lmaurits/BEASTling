import pytest


def _make_tree_cfg(config_factory, tree_dir, tree_file):
    cfg = config_factory('admin', 'mk', tree_file)
    cfg.languages.starting_tree = tree_dir.joinpath(
        "{0}.nex".format(tree_file)).read_text(encoding='utf8')
    return cfg


def test_basic_starting_tree(config_factory, tree_dir):
    cfg = _make_tree_cfg(config_factory, tree_dir, "basic")
    cfg.process()


def test_superset_tree(config_factory, tree_dir):
    cfg = _make_tree_cfg(config_factory, tree_dir, "superset")
    cfg.process()


def test_polytomy_tree(config_factory, tree_dir):
    cfg = _make_tree_cfg(config_factory, tree_dir, "polytomies")
    cfg.process()


def test_subset_tree(config_factory, tree_dir):
    cfg = _make_tree_cfg(config_factory, tree_dir, "subset")
    with pytest.raises(ValueError):
        cfg.process()


def test_duplicate_taxa_tree(config_factory, tree_dir):
    cfg = _make_tree_cfg(config_factory, tree_dir, "duplicates")
    with pytest.raises(ValueError):
        cfg.process()
