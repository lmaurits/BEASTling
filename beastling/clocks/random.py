from .baseclock import BaseClock
from beastling.util import xml


class RandomLocalClock(BaseClock):
    __type__ = 'random'

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.is_strict = False
        self.correlated = clock_config.correlated
        self.estimate_variance = True if clock_config.estimate_variance is None \
            else clock_config.estimate_variance

    def add_state(self, state):
        BaseClock.add_state(self, state)
        xml.stateNode(
            state,
            text=False,
            id="Indicators.c:%s" % self.name,
            spec="parameter.BooleanParameter",
            dimension=42)
        xml.stateNode(
            state,
            text="0.1",
            id="clockrates.c:%s" % self.name,
            spec="parameter.RealParameter",
            dimension=42)
        self.shape_id = "randomClockGammaShape:%s" % self.name
        # Domain and initial values for Gamma params copied from rate heterogeneity
        # implementation in BaseModel
        xml.parameter(
            state, text="5.0", id=self.shape_id, name="stateNode", lower="1.1", upper="1000.0")
        self.scale_id = "randomClockGammaScale:%s" % self.name
        xml.parameter(state, text="0.2", id=self.scale_id, name="stateNode")

    def add_prior(self, prior):
        BaseClock.add_prior(self, prior)

        # Gamma prior over rates
        sub_prior = xml.prior(
            prior,
            id="RandomRatesPrior.c:%s" % self.name,
            name="distribution",
            x="@clockrates.c:%s" % self.name)
        xml.Gamma(
            sub_prior,
            id="RandomRatesPrior:%s" % self.name,
            name="distr",
            alpha="@%s" % self.shape_id,
            beta="@%s" % self.scale_id)

        # Exponential prior over Gamma scale parameter
        # (mean param copied from rate heterogeneity implementation in BaseModel)
        if self.estimate_variance:
            sub_prior = xml.prior(
                prior,
                id="randomClockGammaScalePrior.s:%s" % self.name,
                name="distribution",
                x="@%s" % self.shape_id)
            xml.Exponential(
                sub_prior,
                id="randomClockGammaScalePriorExponential.s:%s" % self.name,
                mean="0.23",
                name="distr")

        # Poisson prior over number of rate changes
        sub_prior = xml.prior(
            prior, id="RandomRateChangesPrior.c:%s" % self.name, name="distribution")
        xml.x(
            sub_prior,
            id="RandomRateChangesCount:%s" % self.name,
            spec="util.Sum",
            arg="@Indicators.c:%s" % self.name)
        poisson = xml.distr(
            sub_prior,
            id="RandomRatechangesPoisson.c:%s" % self.name,
            spec="beast.math.distributions.Poisson")
        xml.parameter(
            poisson,
            text="0.6931471805599453",
            id="RandomRateChangesPoissonLambda:%s" % self.name,
            estimate=False,
            name="lambda")

        # Should we be estimating and have a prior on the Poisson parameter?

    def add_branchrate_model(self, beast):
        xml.branchRateModel(
            beast,
            attrib={"clock.rate":self.mean_rate_idref},
            id="RandomLocalClock.c:%s"%self.name,
            spec="beast.evolution.branchratemodel.RandomLocalClockModel",
            indicators="@Indicators.c:%s" % self.name,
            rates="@clockrates.c:%s" % self.name,
            ratesAreMultipliers=self.correlated,
            tree="@Tree.t:beastlingTree")
        self.branchrate_model_id = "RandomLocalClock.c:%s" % self.name

    def add_operators(self, run):
        BaseClock.add_operators(self, run)
        # Operate on indicators
        xml.operator(
            run,
            id="IndicatorsBitFlip.c:%s" % self.name,
            spec="BitFlipOperator",
            parameter="@Indicators.c:%s" % self.name,
            weight="15.0")
        # Operate on branch rates
        xml.operator(
            run,
            id="ClockRateScaler.c:%s" % self.name,
            spec="ScaleOperator",
            parameter="@clockrates.c:%s" % self.name,
            scaleFactor="0.5",
            weight="15.0")
        # Up/down for Gamma params
        if self.estimate_variance:
            updown = xml.operator(
                run,
                id="randomClockGammaUpDown:%s" % self.name,
                spec="UpDownOperator",
                scaleFactor="0.5",
                weight="1.0")
            xml.parameter(updown, idref=self.shape_id, name="up")
            xml.parameter(updown, idref=self.scale_id, name="down")

    def add_param_logs(self, logger):
        BaseClock.add_param_logs(self, logger)
        xml.log(logger, idref="Indicators.c:%s" % self.name)
        xml.log(logger, idref="clockrates.c:%s" % self.name)
        xml.log(logger, idref="RandomRateChangesCount:%s" % self.name)
        xml.log(logger, idref=self.shape_id)
