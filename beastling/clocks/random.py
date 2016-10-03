import io
import xml.etree.ElementTree as ET

from .baseclock import BaseClock

class RandomLocalClock(BaseClock):

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.is_strict = False
        self.correlated = str(clock_config.get("correlated","false")).lower()
        self.estimate_variance = clock_config.get("estimate_variance",True)

    def add_state(self, state):
        BaseClock.add_state(self, state)
        ET.SubElement(state, "stateNode", {"id":"Indicators.c:%s" % self.name, "spec":"parameter.BooleanParameter","dimension":"42"}).text="false"
        ET.SubElement(state, "stateNode", {"id":"clockrates.c:%s" % self.name, "spec":"parameter.RealParameter", "dimension":"42"}).text = "0.1"
        self.shape_id = "randomClockGammaShape:%s" % self.name
        parameter = ET.SubElement(state, "parameter", {"id":self.shape_id, "name":"stateNode"})
        parameter.text="2.0"
        self.scale_id = "randomClockGammaScale:%s" % self.name
        parameter = ET.SubElement(state, "parameter", {"id":self.scale_id, "name":"stateNode"})
        parameter.text="0.5"

    def add_prior(self, prior):
        BaseClock.add_prior(self, prior)

        # Gamma prior over rates
        sub_prior = ET.SubElement(prior, "prior", {"id":"RandomRatesPrior.c:%s" % self.name, "name":"distribution","x":"@clockrates.c:%s" % self.name})
        gamma = ET.SubElement(sub_prior, "Gamma", {
            "id":"RandomRatesPrior:%s" % self.name,
            "name":"distr",
            "alpha":"@%s" % self.shape_id,
            "beta":"@%s" % self.scale_id})

        # Exponential prior over Gamma shape parameter
        if self.estimate_variance:
            sub_prior = ET.SubElement(prior, "prior", {"id":"randomClockGammaShapePrior.s:%s" % self.name, "name":"distribution", "x":"@%s" % self.shape_id})
            exp = ET.SubElement(sub_prior, "Exponential", {"id":"randomClockGammaShapePriorExponential.s:%s" % self.name, "name":"distr"})
            param = ET.SubElement(exp, "parameter", {"id":"randomClockGammaShapePriorParam:%s" % self.name, "name":"mean", "lower":"0.0", "upper":"0.0"})
            param.text = "1.0"

        # Poisson prior over number of rate changes
        sub_prior = ET.SubElement(prior, "prior", {"id":"RandomRateChangesPrior.c:%s" % self.name, "name":"distribution"})
        ET.SubElement(sub_prior, "x", {"id":"RandomRateChangesCount:%s" % self.name,"spec":"util.Sum","arg":"@Indicators.c:%s" % self.name})
        poisson = ET.SubElement(sub_prior, "distr", {"id":"RandomRatechangesPoisson.c:%s" % self.name, "spec":"beast.math.distributions.Poisson"})
        ET.SubElement(poisson, "parameter", {"id":"RandomRateChangesPoissonLambda:%s" % self.name,"estimate":"false","name":"lambda"}).text = "0.6931471805599453"

        # Should we be estimating and have a prior on the Poisson parameter?

    def add_branchrate_model(self, beast):
        branchrate = ET.SubElement(beast, "branchRateModel", {"id":"RandomLocalClock.c:%s"%self.name,"spec":"beast.evolution.branchratemodel.RandomLocalClockModel","clock.rate":self.mean_rate_idref, "indicators":"@Indicators.c:%s" % self.name, "rates":"@clockrates.c:%s" % self.name, "ratesAreMultipliers":self.correlated, "tree":"@Tree.t:beastlingTree"})
        self.branchrate_model_id = "RandomLocalClock.c:%s" % self.name

    def add_operators(self, run):
        BaseClock.add_operators(self, run)
        # Operate on indicators
        ET.SubElement(run, "operator", {"id":"IndicatorsBitFlip.c:%s" % self.name, "spec":"BitFlipOperator", "parameter":"@Indicators.c:%s" % self.name, "weight":"15.0"})
        # Operate on branch rates
        ET.SubElement(run, "operator", {"id":"ClockRateScaler.c:%s" % self.name, "spec":"ScaleOperator", "parameter":"@clockrates.c:%s" % self.name, "weight":"15.0"})
        # Up/down for Gamma params
        if self.estimate_variance:
            updown = ET.SubElement(run, "operator", {"id":"randomClockGammaUpDown:%s" % self.name, "spec":"UpDownOperator", "scaleFactor":"0.5","weight":"1.0"})
            ET.SubElement(updown, "parameter", {"idref":self.shape_id, "name":"up"})
            ET.SubElement(updown, "parameter", {"idref":self.scale_id, "name":"down"})

    def add_param_logs(self, logger):
        BaseClock.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"idref":"Indicators.c:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":"clockrates.c:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":"RandomRateChangesCount:%s" % self.name})
        ET.SubElement(logger,"log",{"idref":self.shape_id})
