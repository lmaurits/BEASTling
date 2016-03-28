from .util import WithConfigAndTempDir


class Tests(WithConfigAndTempDir):
    def test_duplicate_iso(self):
        config = self.make_cfg("tests/configs/basic.conf")
        config.model_configs[0]["data"] = "tests/data/duplicated_iso.csv"
        self.assertRaises(ValueError, config.process)

    def test_no_iso_field(self):
        config = self.make_cfg("tests/configs/basic.conf")
        config.model_configs[0]["data"] = "tests/data/no_iso.csv"
        self.assertRaises(ValueError, config.process)
