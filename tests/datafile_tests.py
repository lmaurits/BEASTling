from .util import WithConfigAndTempDir, config_path, data_path


class Tests(WithConfigAndTempDir):
    def test_duplicate_iso(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["data"] = data_path("duplicated_iso.csv").as_posix()
        self.assertRaises(ValueError, config.process)

    def test_no_iso_field(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["data"] = data_path("no_iso.csv").as_posix()
        self.assertRaises(ValueError, config.process)
