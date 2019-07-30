from beastling.beastxml import BeastXml


def test_random_tree(config_factory):
    """Load a very basic config file and test that RandomTree
    from the BEAST core is used."""
    config = config_factory('basic')
    xml = BeastXml(config).tostring().decode('utf8')
    assert "beast.evolution.tree.RandomTree" in xml


def test_simple_random_tree(config_factory):
    """Load a config file with a Uniform calibration and test that
    SimpleRandomTree from BEASTLabs is used."""
    config = config_factory('basic','calibration_uniform_range')
    xml = BeastXml(config).tostring().decode('utf8')
    assert "beast.evolution.tree.SimpleRandomTree" in xml


def test_constrained_random_tree(config_factory):
    """Load a config file with monophyly constraints and test that
    ConstraintedRandomTree from BEASTLabs is used."""
    config = config_factory('basic','monophyletic')
    xml = BeastXml(config).tostring().decode('utf8')
    assert "beast.evolution.tree.ConstrainedRandomTree" in xml
