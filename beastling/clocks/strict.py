import io
import os
import xml.etree.ElementTree as ET

from .baseclock import BaseClock

class StrictClock(BaseClock):

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.mean_rate_id = "clockRate.c:%s" % self.name
        self.mean_rate_idref = "@%s" % self.mean_rate_id
        self.branchrate_model_id = "StrictClockModel.c:%s" % self.name

    def add_state(self, state):

        # Strict clock params
        attribs = {}
        attribs["id"] = self.mean_rate_id
        attribs["name"] = "stateNode"
        parameter = ET.SubElement(state, "parameter", attribs)
        parameter.text="1.0"

    def add_prior(self, prior):

        # Clock
        sub_prior = ET.SubElement(prior, "prior", {"id":"clockPrior:%s" % self.name, "name":"distribution","x":"@clockRate.c:%s" % self.name})
        uniform = ET.SubElement(sub_prior, "Uniform", {"id":"UniformClockPrior:%s" % self.name, "name":"distr", "upper":"Infinity"})

    def add_branchrate_model(self, beast):
        ET.SubElement(beast, "branchRateModel", {"id":"StrictClockModel.c:%s"%self.name,"spec":"beast.evolution.branchratemodel.StrictClockModel","clock.rate":"@clockRate.c:%s" % self.name})

    def add_timed_tree_operators(self, run):
        ET.SubElement(run, "operator", {"id":"clockScaler.c:%s" % self.name, "spec":"ScaleOperator","parameter":"@clockRate.c:%s" % self.name, "scaleFactor":"0.5","weight":"3.0"})

    def add_param_logs(self, logger):

        # Clock
        ET.SubElement(logger,"log",{"idref":"clockRate.c:%s" % self.name})

