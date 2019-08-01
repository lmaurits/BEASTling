from .baseclock import BaseClock
from beastling.util import xml


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
        xml.stateNode(
            state,
            text="1",
            id="rateCategories.c:%s" % self.name,
            spec="parameter.IntegerParameter",
            dimension=42)

    def add_prior(self, prior):
        BaseClock.add_prior(self, prior)

    def add_branchrate_model(self, beast):
        self.branchrate = xml.branchRateModel(
            beast,
            id="RelaxedClockModel.c:%s" % self.name,
            spec="beast.evolution.branchratemodel.UCRelaxedClockModel",
            rateCategories="@rateCategories.c:%s" % self.name,
            tree="@Tree.t:beastlingTree",
            numberOfDiscreteRates=self.number_of_rates,
            attrib={"clock.rate":self.mean_rate_idref})
        self.branchrate_model_id = "RelaxedClockModel.c:%s" % self.name

    def add_pruned_branchrate_model(self, distribution, name, tree_id):
        xml.branchRateModel(
            distribution,
            id="PrunedRelaxedClockModel.c:%s" % name,
            spec="beast.evolution.branchratemodel.PrunedRelaxedClockModel",
            rates="@%s" % self.branchrate_model_id,
            tree="@%s" % tree_id)

    def add_operators(self, run):
        BaseClock.add_operators(self, run)
        # Add category operators
        xml.operator(
            run,
            id="rateCategoriesRandomWalkOperator.c:%s" % self.name,
            spec="IntRandomWalkOperator",
            parameter="@rateCategories.c:%s" % self.name,
            windowSize="1",
            weight="10.0")
        xml.operator(
            run,
            id="rateCategoriesSwapOperator.c:%s" % self.name,
            spec="SwapOperator",
            intparameter="@rateCategories.c:%s" % self.name,
            weight="10.0")
        xml.operator(
            run,
            id="rateCategoriesUniformOperator.c:%s" % self.name,
            spec="UniformOperator",
            parameter="@rateCategories.c:%s" % self.name,
            weight="10.0")

    def add_param_logs(self, logger):
        BaseClock.add_param_logs(self, logger)
        xml.log(
            logger,
            id="rate.c:%s" % self.name,
            spec="beast.evolution.branchratemodel.RateStatistic",
            branchratemodel="@%s" % self.branchrate_model_id,
            tree="@Tree.t:beastlingTree")


class LogNormalRelaxedClock(RelaxedClock):

    def __init__(self, clock_config, global_config):
        RelaxedClock.__init__(self, clock_config, global_config)
        default_estimate_variance = True
        if "variance" in clock_config:
            self.initial_variance = clock_config["variance"]
            default_estimate_variance = False
        else:
            self.initial_variance = 0.1
        self.estimate_variance = clock_config.get("estimate_variance",default_estimate_variance)

    def add_state(self, state):
        RelaxedClock.add_state(self, state)
        # Standard deviation for lognormal dist
        xml.parameter(
            state,
            text=self.initial_variance,
            id="ucldSdev.c:%s" % self.name,
            lower="0.0",
            upper="10.0",
            name="stateNode")

    def add_prior(self, prior):
        RelaxedClock.add_prior(self, prior)
        if self.estimate_variance:
            # Gamma prior on the standard deviation for lognormal dist
            sub_prior = xml.prior(
                prior,
                id="ucldSdev:%s" % self.name,
                name="distribution",
                x="@ucldSdev.c:%s" % self.name)
            gamma = xml.Gamma(sub_prior, id="uclSdevPrior:%s" % self.name, name="distr")
            xml.parameter(
                gamma,
                text="0.5396",
                id="uclSdevPriorAlpha:%s" % self.name,
                estimate="false",
                name="alpha")
            xml.parameter(
                gamma,
                text="0.3819",
                id="uclSdevPriorBeta:%s" % self.name,
                estimate="false",
                name="beta")

    def add_branchrate_model(self, beast):
        RelaxedClock.add_branchrate_model(self, beast)
        xml.LogNormal(
            self.branchrate,
            id="LogNormalDistributionModel.c:%s" % self.name,
            M="1.0",
            S="@ucldSdev.c:%s" % self.name,
            meanInRealSpace="true",
            name="distr")

    def add_operators(self, run):
        RelaxedClock.add_operators(self, run)
        # Sample lognormal stddev
        if self.estimate_variance:
            xml.operator(
                run,
                id="ucldSdevScaler.c:%s" % self.name,
                spec="ScaleOperator",
                parameter="@ucldSdev.c:%s" % self.name,
                scaleFactor="0.5",
                weight="3.0")

    def add_param_logs(self, logger):
        RelaxedClock.add_param_logs(self, logger)
        # Log lognormal stddev
        xml.log(logger, idref="ucldSdev.c:%s" % self.name)

class ExponentialRelaxedClock(RelaxedClock):

    def add_branchrate_model(self, beast):
        RelaxedClock.add_branchrate_model(self, beast)
        xml.Exponential(
            self.branchrate,
            id="ExponentialDistribution.c:%s" % self.name,
            mean=self.mean_rate_idref,
            name="distr")


class GammaRelaxedClock(RelaxedClock):

    def add_state(self, state):
        RelaxedClock.add_state(self, state)
        xml.parameter(
            state,
            text="2.0",
            id="clockRateGammaShape:%s" % self.name,
            lower="0.0",
            name="stateNode")
        xml.parameter(
            state,
            text="0.5",
            id="clockRateGammaScale:%s" % self.name,
            lower="0.0",
            name="stateNode")

    def add_branchrate_model(self, beast):
        RelaxedClock.add_branchrate_model(self, beast)
        xml.Gamma(
            self.branchrate,
            id="relaxedClockDistribution:%s" % self.name,
            alpha="@clockRateGammaShape:%s" % self.name,
            beta="@clockRateGammaScale:%s" % self.name,
            name="distr")

    def add_prior(self, prior):
        RelaxedClock.add_prior(self, prior)
        gamma_param_prior = xml.prior(
            prior,
            id="clockRateGammaShapePrior.s:%s" % self.name,
            name="distribution",
            x="@clockRateGammaShape:%s" % self.name)
        xml.Exponential(
            gamma_param_prior,
            id="clockRateGammaShapePriorExponential.s:%s" % self.name,
            name="distr",
            mean="1.0")

    def add_operators(self, run):
        RelaxedClock.add_operators(self, run)
        updown = xml.operator(
            run,
            id="relaxedClockGammaUpDown:%s" % self.name,
            spec="UpDownOperator",
            scaleFactor="0.5",
            weight="3.0")
        xml.parameter(updown, idref="clockRateGammaShape:%s" % self.name, name="up")
        xml.parameter(updown, idref="clockRateGammaScale:%s" % self.name, name="down")

    def add_param_logs(self, logger):
        RelaxedClock.add_param_logs(self, logger)
        xml.log(logger, idref="clockRateGammaShape:%s" % self.name)
