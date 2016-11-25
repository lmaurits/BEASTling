import io
import os
import xml.etree.ElementTree as ET

from .baseclock import BaseClock

class StrictClock(BaseClock):

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.branchrate_model_id = "StrictClockModel.c:%s" % self.name
        self.is_strict = True

    def add_branchrate_model(self, beast):
        ET.SubElement(beast, "branchRateModel", {"id":"StrictClockModel.c:%s"%self.name,"spec":"beast.evolution.branchratemodel.StrictClockModel","clock.rate":"@clockRate.c:%s" % self.name})

    def add_pruned_branchrate_model(self, distribution, name, tree_id):
        # For StrictClocks, it's safe to just reuse the global branchRateModel
        self.branchrate = ET.SubElement(distribution, "branchRateModel", {"idref": self.branchrate_model_id})

