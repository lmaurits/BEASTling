import io
import os
import xml.etree.ElementTree as ET

class BaseClock(object):

    def __init__(self, clock_config, global_config):

        self.config = global_config
        self.calibrations = global_config.calibrations

        self.name = clock_config["name"] 
        self.is_used = False

    def add_pruned_branchrate_model(self, distribution, name, tree_id):
        # Most clocks will not need special treatment for pruned trees
        return self.branchrate_model_id
