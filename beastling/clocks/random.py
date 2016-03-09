import io
import os
import xml.etree.ElementTree as ET

from .baseclock import BaseClock

class RandomLocalClock(BaseClock):

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.mean_rate_id = "meanClockRate.c:%s" % self.name
        self.mean_rate_idref = "@%s" % self.mean_rate_id

    def add_state(self, state):

        ET.SubElement(state, "parameter", {"id":"meanClockRate.c:%s" % self.name, "lower":"0.0"}).text = "1.0"
        ET.SubElement(state, "stateNode", {"id":"Indicators.c:%s" % self.name, "spec":"parameter.BooleanParameter","dimension":"42"}).text="false"
        ET.SubElement(state, "stateNode", {"id":"clockrates.c:%s" % self.name, "spec":"parameter.RealParameter", "dimension":"42"}).text = "0.1"

    def add_prior(self, prior):

        sub_prior = ET.SubElement(prior, "prior", {"id":"RandomRatesPrior.c:%s" % self.name, "name":"distribution","x":"@clockrates.c:%s" % self.name})
        gamma = ET.SubElement(sub_prior, "Gamma", {"id":"RandomRatesPrior:%s" % self.name, "name":"distr"})
        ET.SubElement(gamma, "parameter", {"id":"RandomRatesPriorAlpha:%s" % self.name, "estimate":"false", "name":"alpha"}).text = "0.5396"
        ET.SubElement(gamma, "parameter", {"id":"RandomRatesPriorBeta:%s" % self.name, "estimate":"false", "name":"beta"}).text = "0.3819"

        sub_prior = ET.SubElement(prior, "prior", {"id":"RandomRateChangesPrior.c:%s" % self.name, "name":"distribution"})
        ET.SubElement(sub_prior, "x", {"id":"RandomRateChangesCount","spec":"util.Sum","arg":"@Indicators.c:%s" % self.name})
        poisson = ET.SubElement(sub_prior, "distr", {"id":"RandomRatechangesPoisson.c:%s" % self.name, "spec":"beast.math.distributions.Poisson"})
        ET.SubElement(poisson, "parameter", {"id":"RandomRateChangesPoissonLambda","estimate":"false","name":"lambda"}).text = "0.6931471805599453"

    def add_branchrate_model(self, beast):
        branchrate = ET.SubElement(beast, "branchRateModel", {"id":"RandomLocalClock.c:%s"%self.name,"spec":"beast.evolution.branchratemodel.RandomLocalClockModel","clock.rate":self.mean_rate_idref, "indicators":"@Indicators.c:%s" % self.name, "rates":"@clockrates.c:%s" % self.name, "tree":"@Tree.t:beastlingTree"})
        self.branchrate_model_id = "RandomLocalClock.c:%s" % self.name

    def add_unconditional_operators(self, run):
        ET.SubElement(run, "operator", {"id":"IndicatorsBitFlip.c:%s" % self.name, "spec":"BitFlipOperator", "parameter":"@Indicators.c:%s" % self.name, "weight":"15.0"})
        ET.SubElement(run, "operator", {"id":"ClockRateScaler.c:%s" % self.name, "spec":"ScaleOperator", "parameter":"@clockrates.c:%s" % self.name, "weight":"15.0"})

    def add_timed_tree_operators(self, run):
        ET.SubElement(run, "operator", {"id":"meanClockRateScaaler.c:%s" % self.name, "spec":"ScaleOperator", "parameter":"@meanClockRate.c:%s" % self.name, "scaleFactor": "0.5", "weight":"3.0"})

    def add_param_logs(self, logger):
        ET.SubElement(logger,"log",{"idref":"Indicators.c:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":"clockrates.c:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":"RandomRateChanges.c:%s" % self.name})

