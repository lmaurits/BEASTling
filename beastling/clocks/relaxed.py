import io
import os
import xml.etree.ElementTree as ET

from .baseclock import BaseClock

def relaxed_clock_factory(clock_config, global_config):
    distribution = clock_config.get("distribution","lognormal").lower()
    if distribution == "lognormal":
        return LogNormalRelaxedClock(clock_config, global_config)
    elif distribution == "exponential":
        return ExponentialRelaxedClock(clock_config, global_config)
    elif distribution == "gamma":
        return GammaRelaxedClock(clock_config, global_config)

class RelaxedClock(BaseClock):

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.number_of_rates = int(clock_config.get("rates","-1"))
        self.is_strict = False

    def add_state(self, state):
        BaseClock.add_state(self, state)
        # Rate categories
        ET.SubElement(state, "stateNode", {"id":"rateCategories.c:%s" % self.name, "spec":"parameter.IntegerParameter", "dimension":"42"}).text = "1"

    def add_prior(self, prior):
        BaseClock.add_prior(self, prior)

    def add_branchrate_model(self, beast):
        self.branchrate = ET.SubElement(beast, "branchRateModel", {"id":"RelaxedClockModel.c:%s"%self.name,"spec":"beast.evolution.branchratemodel.UCRelaxedClockModel","rateCategories":"@rateCategories.c:%s" % self.name, "tree":"@Tree.t:beastlingTree", "numberOfDiscreteRates":str(self.number_of_rates),"clock.rate":self.mean_rate_idref})
        self.branchrate_model_id = "RelaxedClockModel.c:%s" % self.name

    def add_pruned_branchrate_model(self, distribution, name, tree_id):
        pbrm_id = "PrunedRelaxedClockModel.c:%s" % name
        pruned_branchrate = ET.SubElement(distribution, "branchRateModel", {"id":pbrm_id,"spec":"beast.evolution.branchratemodel.PrunedRelaxedClockModel", "rates":"@%s" % self.branchrate_model_id, "tree":"@%s"%tree_id})

    def add_operators(self, run):
        BaseClock.add_operators(self, run)
        # Add category operators
        ET.SubElement(run, "operator", {"id":"rateCategoriesRandomWalkOperator.c:%s" % self.name, "spec":"IntRandomWalkOperator", "parameter":"@rateCategories.c:%s" % self.name, "windowSize": "1", "weight":"10.0"})
        ET.SubElement(run, "operator", {"id":"rateCategoriesSwapOperator.c:%s" % self.name, "spec":"SwapOperator", "intparameter":"@rateCategories.c:%s" % self.name, "weight":"10.0"})
        ET.SubElement(run, "operator", {"id":"rateCategoriesUniformOperator.c:%s" % self.name, "spec":"UniformOperator", "parameter":"@rateCategories.c:%s" % self.name, "weight":"10.0"})

    def add_param_logs(self, logger):
        BaseClock.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"id":"rate.c:%s" % self.name, "spec":"beast.evolution.branchratemodel.RateStatistic", "branchratemodel":"@%s" % self.branchrate_model_id, "tree":"@Tree.t:beastlingTree"})

class LogNormalRelaxedClock(RelaxedClock):

    def __init__(self, clock_config, global_config):
        RelaxedClock.__init__(self, clock_config, global_config)
        self.estimate_variance = clock_config.get("estimate_variance",True)
        self.initial_variance = clock_config.get("variance",0.1)

    def add_state(self, state):
        RelaxedClock.add_state(self, state)
        # Standard deviation for lognormal dist
        ET.SubElement(state, "parameter", {"id":"ucldSdev.c:%s" % self.name, "lower":"0.0", "upper":"10.0","name":"stateNode"}).text = str(self.initial_variance)

    def add_prior(self, prior):
        RelaxedClock.add_prior(self, prior)
        if self.estimate_variance:
            # Gamma prior on the standard deviation for lognormal dist
            sub_prior = ET.SubElement(prior, "prior", {"id":"ucldSdev:%s" % self.name, "name":"distribution","x":"@ucldSdev.c:%s" % self.name})
            gamma = ET.SubElement(sub_prior, "Gamma", {"id":"uclSdevPrior:%s" % self.name, "name":"distr"})
            ET.SubElement(gamma, "parameter", {"id":"uclSdevPriorAlpha:%s" % self.name, "estimate":"false", "name":"alpha"}).text = "0.5396"
            ET.SubElement(gamma, "parameter", {"id":"uclSdevPriorBeta:%s" % self.name, "estimate":"false", "name":"beta"}).text = "0.3819"

    def add_branchrate_model(self, beast):
        RelaxedClock.add_branchrate_model(self, beast)
        lognormal = ET.SubElement(self.branchrate, "LogNormal", {"id":"LogNormalDistributionModel.c:%s"%self.name,
            "S":"@ucldSdev.c:%s" % self.name, "meanInRealSpace":"true", "name":"distr"})
        # Fix mean to 1.0
        param = ET.SubElement(lognormal, "parameter", {"id":"LogNormalM.p:%s" % self.name, "name":"M", "estimate":"false", "lower":"0.0","upper":"1.0"})
        param.text = "1.0"

    def add_operators(self, run):
        RelaxedClock.add_operators(self, run)
        # Sample lognormal stddev
        if self.estimate_variance:
            ET.SubElement(run, "operator", {"id":"ucldSdevScaler.c:%s" % self.name, "spec":"ScaleOperator", "parameter":"@ucldSdev.c:%s" % self.name, "scaleFactor": "0.5", "weight":"3.0"})

    def add_param_logs(self, logger):
        RelaxedClock.add_param_logs(self, logger)
        # Log lognormal stddev
        ET.SubElement(logger,"log",{"idref":"ucldSdev.c:%s" % self.name})

class ExponentialRelaxedClock(RelaxedClock):

    def add_branchrate_model(self, beast):
        RelaxedClock.add_branchrate_model(self, beast)
        expon = ET.SubElement(self.branchrate, "Exponential", {"id":"ExponentialDistribution.c:%s"%self.name, "mean":self.mean_rate_idref, "name":"distr"})

class GammaRelaxedClock(RelaxedClock):

    def add_state(self, state):
        RelaxedClock.add_state(self, state)
        ET.SubElement(state, "parameter", {"id":"clockRateGammaShape:%s" % self.name, "lower":"0.0", "name":"stateNode"}).text = "2.0"
        ET.SubElement(state, "parameter", {"id":"clockRateGammaScale:%s" % self.name, "lower":"0.0", "name":"stateNode"}).text = "0.5"

    def add_branchrate_model(self, beast):
        RelaxedClock.add_branchrate_model(self, beast)
        ET.SubElement(self.branchrate, "Gamma", {"id":"relaxedClockDistribution:%s"%self.name, "alpha":"@clockRateGammaShape:%s" % self.name, "beta":"@clockRateGammaScale:%s" % self.name, "name":"distr"})

    def add_prior(self, prior):
        RelaxedClock.add_prior(self, prior)
        gamma_param_prior = ET.SubElement(prior, "prior", {"id":"clockRateGammaShapePrior.s:%s" % self.name, "name":"distribution", "x":"@clockRateGammaShape:%s" % self.name})
        exp = ET.SubElement(gamma_param_prior, "Exponential", {"id":"clockRateGammaShapePriorExponential.s:%s" % self.name, "name":"distr", "mean":"1.0"})

    def add_operators(self, run):
        RelaxedClock.add_operators(self, run)
        updown = ET.SubElement(run, "operator", {"id":"relaxedClockGammaUpDown:%s" % self.name, "spec":"UpDownOperator", "scaleFactor":"0.5","weight":"3.0"})
        ET.SubElement(updown, "parameter", {"idref":"clockRateGammaShape:%s" % self.name, "name":"up"})
        ET.SubElement(updown, "parameter", {"idref":"clockRateGammaScale:%s" % self.name, "name":"down"})

    def add_param_logs(self, logger):
        RelaxedClock.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"idref":"clockRateGammaShape:%s" % self.name})
