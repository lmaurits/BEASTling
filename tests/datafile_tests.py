from .util import WithConfigAndTempDir, config_path, data_path


class Tests(WithConfigAndTempDir):
    def test_duplicate_iso(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["data"] = data_path("duplicated_iso.csv")
        self.assertRaises(ValueError, config.process)

    def test_no_iso_field(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["data"] = data_path("no_iso.csv")
        self.assertRaises(ValueError, config.process)

    def test_cldf_misspecified_as_beastling(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["data"] = data_path("cldf.csv")
        config.model_configs[0]["file_format"] = 'beastling'
        self.assertRaises(ValueError, config.process)

    def test_beastling_misspecified_as_cldf(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["file_format"] = 'cldf'
        self.assertRaises(ValueError, config.process)

    def test_unknown_file_format(self):
        config = self.make_cfg(config_path("basic").as_posix())
        config.model_configs[0]["file_format"] = 'does_not_exist'
        self.assertRaises(ValueError, config.process)

    
