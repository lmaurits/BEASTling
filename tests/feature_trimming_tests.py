from .util import WithConfigAndTempDir, config_path


class Tests(WithConfigAndTempDir):
    def test_basic(self):
        """Load the basic config file and count the number of features
        in the instantiated model.  Then reload the same file, but
        modify it to turn off the "remove_constant_features" model.
        Reinstantiate and make sure that more features survive."""
        config = self.make_cfg(config_path('basic').as_posix())
        config.process()
        a = len(config.models[0].features)
        config = self.make_cfg(config_path('basic').as_posix())
        config.model_configs[0]["remove_constant_features"] = False
        config.process()
        b = len(config.models[0].features)
        assert b > a
