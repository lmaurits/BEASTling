from .util import WithConfigAndTempDir, config_path


class Tests(WithConfigAndTempDir):
    def test_basic(self):
        """Load the basic config file and count the number of features
        in the instantiated model.  Then reload the same file, but
        modify it to turn off the "remove_constant_features" model.
        Reinstantiate and make sure that more features survive."""
        config = self.make_cfg(config_path('covarion').as_posix())
        model_config = [mc for mc in config.model_configs if mc["name"] == "multistate"][0]
        model_config["remove_constant_features"] = True
        config.process()
        model = [m for m in config.models if m.name =="multistate"][0]
        a = len(model.features)
        config = self.make_cfg(config_path('covarion').as_posix())
        model_config = [mc for mc in config.model_configs if mc["name"] == "multistate"][0]
        model_config["remove_constant_features"] = False
        config.process()
        model = [m for m in config.models if m.name =="multistate"][0]
        b = len(model.features)
        assert b > a
