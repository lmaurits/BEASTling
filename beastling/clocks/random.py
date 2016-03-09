import io
import os
import xml.etree.ElementTree as ET

from .baseclock import BaseClock

class RandomLocalClock(BaseClock):

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.distribution = clock_config.get("distribution","lognormal").lower()

    def add_state(self, state):

        # Relaxed clock params
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
        branchrate = ET.SubElement(beast, "branchRateModel", {"id":"RandomLocalClock.c:%s"%self.name,"spec":"beast.evolution.branchratemodel.RandomLocalClockModel","indicators":"@Indicators.c:%s" % self.name, "rates":"@clockrates.c:%s" % self.name, "tree":"@Tree.t:beastlingTree"})
        ET.SubElement(branchrate, "parameter", {"id":"meanClockRate.c:%s" % self.name, "name":"clock.rate", "estimate":"false"}).text = "1.0"
        self.branchrate_model_id = "RandomLocalClock.c:%s" % self.name

    def add_operators(self, run):

        # Clock scaler (only if tree is not free to vary arbitrarily)
#        if not self.config.sample_branch_lengths or self.calibrations:
#            ET.SubElement(run, "operator", {"id":"clockScaler.c:%s" % self.name, "spec":"ScaleOperator","parameter":"@ucldMean.c:%s" % self.name, "scaleFactor":"0.5","weight":"3.0"})

        # Relaxed clock operators
        ET.SubElement(run, "operator", {"id":"IndicatorsBitFlip.c:%s" % self.name, "spec":"BitFlipOperator", "parameter":"@Indicators.c:%s" % self.name, "weight":"15.0"})
        ET.SubElement(run, "operator", {"id":"ClockRateScaler.c:%s" % self.name, "spec":"ScaleOperator", "parameter":"@clockrates.c:%s" % self.name, "weight":"15.0"})

    def add_param_logs(self, logger):
        ET.SubElement(logger,"log",{"idref":"Indicators.c:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":"clockrates.c:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":"RandomRateChanges.c:%s" % self.name})

