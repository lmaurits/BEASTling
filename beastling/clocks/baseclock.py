import io
import os
import xml.etree.ElementTree as ET

class BaseClock(object):

    def __init__(self, clock_config, global_config):

        self.config = global_config
        # By default, whether or not to estimate the rate is left up to
        # BEASTling.
        default_estimate_rate = None
        # But if the user specifies a rate, we assume they do not want it
        # estimated...
        if any([k in clock_config for k in ("mean", "rate")]):
            k = "mean" if "mean" in clock_config else "rate"
            self.initial_mean = clock_config[k]
            default_estimate_rate = False
        else:
            self.initial_mean = 1.0
        # ...but they can override this by explicitly saying so.
        self.estimate_rate = clock_config.get("estimate_rate",default_estimate_rate)
        self.calibrations = global_config.calibrations
        self.name = clock_config["name"] 
        self.mean_rate_id = "clockRate.c:%s" % self.name
        self.mean_rate_idref = "@%s" % self.mean_rate_id
        self.is_used = False

    def add_state(self, state):
        # Add mean clock rate
        parameter = ET.SubElement(state, "parameter", {
            "id": self.mean_rate_id,
            "name": "stateNode"
            })
        parameter.text=str(self.initial_mean)

    def add_prior(self, prior):
        # Uniform prior on mean clock rate
        sub_prior = ET.SubElement(prior, "prior", {"id":"clockPrior:%s" % self.name, "name":"distribution","x":"@clockRate.c:%s" % self.name})
        uniform = ET.SubElement(sub_prior, "Uniform", {"id":"UniformClockPrior:%s" % self.name, "name":"distr", "upper":"Infinity"})

    def add_branchrate_model(self, beast):
        pass

    def add_pruned_branchrate_model(self, distribution, name, tree_id):
        raise Exception("This clock is not compatible with PrunedTrees!")

    def add_operators(self, run):
        if self.estimate_rate:
            # Scale mean clock rate
            ET.SubElement(run, "operator", {"id":"clockScaler.c:%s" % self.name, "spec":"ScaleOperator","parameter":"@clockRate.c:%s" % self.name, "scaleFactor":"0.5","weight":"3.0"})

    def add_param_logs(self, logger):
        # Log mean clock rate
        ET.SubElement(logger,"log",{"idref":"clockRate.c:%s" % self.name})

