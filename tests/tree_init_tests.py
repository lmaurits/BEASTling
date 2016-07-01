from .util import WithConfigAndTempDir, config_path
from beastling.beastxml import BeastXml

class Tests(WithConfigAndTempDir):
    def _make_cfg(self, *names):
        return self.make_cfg([config_path(name).as_posix() for name in names])

    def test_random_tree(self):
        """Load a very basic config file and test that RandomTree
        from the BEAST core is used."""
        config = self._make_cfg('basic')
        xml = BeastXml(config).tostring().decode('utf8')
        self.assertTrue("beast.evolution.tree.RandomTree" in xml)

    def test_simple_random_tree(self):
        """Load a config file with a Uniform calibration and test that
        SimpleRandomTree from BEASTLabs is used."""
        config = self._make_cfg('basic','calibration_uniform_range')
        xml = BeastXml(config).tostring().decode('utf8')
        self.assertTrue("beast.evolution.tree.SimpleRandomTree" in xml)
    
    def test_constrained_random_tree(self):
        """Load a config file with monophyly constraints and test that
        ConstraintedRandomTree from BEASTLabs is used."""
        config = self._make_cfg('basic','monophyletic')
        xml = BeastXml(config).tostring().decode('utf8')
        self.assertTrue("beast.evolution.tree.ConstrainedRandomTree" in xml)
