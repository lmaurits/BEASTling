def test_basic(config_factory):
    """Load the basic config file and count the number of features
    in the instantiated model.  Then reload the same file, but
    modify it to turn off the "remove_constant_features" model.
    Reinstantiate and make sure that more features survive."""
    config = config_factory('covarion_multistate')
    config.model_configs[0]["remove_constant_features"] = True
    config.process()
    a = len(config.models[0].features)

    config = config_factory('covarion_multistate')
    config.model_configs[0]["remove_constant_features"] = False
    config.process()
    b = len(config.models[0].features)

    assert b > a
