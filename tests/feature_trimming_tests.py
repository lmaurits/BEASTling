from nose.tools import *

import beastling.configuration
import beastling.beastxml

def test_basic():
    """Load the basic config file and count the number of traits
    in the instantiated model.  Then reload the same file, but
    modify it to turn off the "remove_constant_traits" model.
    Reinstantiate and make sure that more traits survive."""
    config = beastling.configuration.Configuration(configfile="tests/configs/basic.conf")
    config.process()
    a = len(config.models[0].traits)
    config = beastling.configuration.Configuration(configfile="tests/configs/basic.conf")
    config.model_configs[0]["remove_constant_traits"] = False
    config.process()
    b = len(config.models[0].traits)
    assert b > a
