import io
import os
import xml.etree.ElementTree as ET

class BaseClock(object):

    def __init__(self, clock_config, global_config):

        self.config = global_config
        self.calibrations = global_config.calibrations

        self.name = clock_config["name"] 
        self.pruned = clock_config.get("pruned", False)
        self.branchrate_model_instantiated = False
