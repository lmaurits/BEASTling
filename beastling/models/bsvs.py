import math

from .basemodel import BaseModel
from beastling.util import xml


class BSVSModel(BaseModel):

    package_notice = ("The BSVS substitution model", "BEAST_CLASSIC")
    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        symm = model_config.get("symmetric", "True")
        if symm.lower().strip() == "true":
            self.symmetric = True
        elif symm.lower().strip() == "false":
            self.symmetric = False
        else:
            raise ValueError("Invalid setting of 'symmetric' (%s) for model %s: use for BSVS model must be set to True or False, " % (symm, self.name))
        self.svsprior = model_config.get("svsprior", "poisson")

    def add_state(self, state):

        BaseModel.add_state(self, state)
        for f in self.features:
            fname = "%s:%s" % (self.name, f)

            N = self.valuecounts[f]
            dimension = N*(N-1)
            if self.symmetric:
                dimension = int(dimension/2)

            xml.stateNode(
                state,
                text="true",
                id="rateIndicator.s:%s" % fname,
                spec="parameter.BooleanParameter",
                dimension=dimension)

            xml.parameter(
                state,
                text="1.0",
                id="relativeGeoRates.s:%s" % fname,
                name="stateNode",
                dimension=dimension)

    def add_prior(self, prior):

        BaseModel.add_prior(self, prior)
        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)

            # Boolean Rate on/off
            sub_prior = xml.prior(prior, id="nonZeroRatePrior.s:%s" % fname, name="distribution")
            xml.x(sub_prior, arg="@rateIndicator.s:%s" % fname, spec="util.Sum")
            N = self.valuecounts[f]
            if self.symmetric:
                offset = N-1
                dim = N*(N-1)/2
            else:
                offset = N
                dim = N*(N-1)
            if dim == offset:
                # In this situation (e.g. N=2, symmetric), we have no real
                # freedom in the number of non-zero rates.  So just set a
                # uniform prior
                xml.distr(
                    sub_prior,
                    id="Poisson:%s.%d" % (fname, n),
                    offset=offset,
                    spec="beast.math.distributions.Uniform",
                    lower="0.0",
                    upper="Infinity")
            elif self.svsprior == "poisson":
                distr  = xml.distr(
                    sub_prior,
                    id="Poisson:%s.%d" % (fname, n),
                    offset=offset,
                    spec="beast.math.distributions.Poisson")
                xml.parameter(
                    distr,
                    # Set Poisson mean equal to the midpoint of the range of sensible values
                    text=(dim - offset) / 2.0,
                    id="RealParameter:%s.%d.0" % (fname, n),
                    lower="0.0",
                    name="lambda",
                    upper="0.0")
            elif self.svsprior == "exponential":
                # Set Exponential mean so that 99% of probability density
                # lies inside the sensible range
                # Exponential quantile function is
                # F(p,lambda) = -ln(1-p) / lambda
                exponential_mean = math.log(100.0) / (dim - offset)
                distr  = xml.distr(
                    sub_prior,
                    id="Exponential:%s.%d" % (fname, n),
                    offset=offset,
                    spec="beast.math.distributions.Exponential")
                xml.parameter(
                    distr,
                    text=exponential_mean,
                    id="RealParameter:%s.%d.0" % (fname, n),
                    lower="0.0",
                    name="mean",
                    upper="0.0")

            # Relative rate
            sub_prior = xml.prior(
                prior,
                id="relativeGeoRatesPrior.s:%s" % fname,
                name="distribution",
                x="@relativeGeoRates.s:%s" % fname)
            gamma = xml.Gamma(sub_prior, id="Gamma:%s.%d.0" % (fname, n), name="distr")
            xml.parameter(
                gamma,
                text="1.0",
                id="RealParameter:%s.%d.1" % (fname, n),
                lower="0.0",
                name="alpha",
                upper="0.0")
            xml.parameter(
                gamma,
                text="1.0",
                id="RealParameter:%s.%d.2" % (fname, n),
                lower="0.0",
                name="beta",
                upper="0.0")

    def add_substmodel(self, sitemodel, feature, fname):
        attribs = {
            "id": "svs.s:%s"%fname,
            "rateIndicator": "@rateIndicator.s:%s" % fname,
            "rates": "@relativeGeoRates.s:%s" % fname,
            "spec": "SVSGeneralSubstitutionModel"}
        if not self.symmetric:
            attribs['symmetric'] = 'false'
        if self.use_robust_eigensystem:
            attribs["eigenSystem"] = "beast.evolution.substitutionmodel.RobustEigenSystem"
        substmodel = xml.substModel(sitemodel, **attribs)
        attribs = {
            "id": "feature_freqs.s:%s"%fname,
            "spec": "Frequencies",
        }
        freq_string=None
        if self.frequencies == "estimate":
            attribs["frequencies"] = "@feature_freqs_param.s:%s"%fname
        elif self.frequencies == "uniform":
            freq_string = str(1.0/self.valuecounts[feature])
        elif self.frequencies == "empirical":
            #TODO: Do this in the BEAStly way
            freqs = [
                self.counts[feature].get(
                    self.unique_values[feature][v], 0)
                for v in range(self.valuecounts[feature])]
            norm = float(sum(freqs))
            freqs = [f/norm for f in freqs]
            # Sometimes, due to WALS oddities, there's a zero frequency, and that makes BEAST sad.  So do some smoothing in these cases:
            if 0 in freqs:
                freqs = [0.1/self.valuecounts[feature] + 0.9*f for f in freqs]
            norm = float(sum(freqs))
            freq_string = " ".join([str(c/norm) for c in freqs])
        else:
            raise ValueError(
                "Model BSVS does not recognize frequencies %r, "
                "should be 'uniform' or 'empirical'." % self.frequencies)
        freq = xml.frequencies(substmodel, **attribs)
        if self.frequencies != "estimate":
            xml.parameter(
                freq,
                text=freq_string,
                dimension=self.valuecounts[feature],
                id="feature_frequencies.s:%s" % fname,
                name="frequencies")

    def add_operators(self, run):
        BaseModel.add_operators(self, run)
        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)
            xml.operator(
                run,
                id="onGeorateScaler.s:%s" % fname,
                spec="ScaleOperator",
                parameter="@relativeGeoRates.s:%s" % fname,
                indicator="@rateIndicator.s:%s" % fname,
                scaleAllIndependently="true",
                scaleFactor="0.5",
                weight="10.0")

            if self.rate_variation:
                xml.operator(
                    run,
                    id="BSSVSoperator.c:%s" % fname,
                    spec="BitFlipBSSVSOperator",
                    indicator="@rateIndicator.s:%s" % fname,
                    mu="@featureClockRate:%s" % fname,
                    weight="30.0")
                bssvs_bitflip = True
            elif not self.global_config.arbitrary_tree:
                # Don't scale the clock of a tree with arbitrary branch
                # lengths, as birthRate is also scaled and one or the other
                # will run away to infinity.
                xml.operator(
                    run,
                    id="BSSVSoperator.c:%s" % fname,
                    spec="BitFlipBSSVSOperator",
                    indicator="@rateIndicator.s:%s" % fname,
                    mu=self.clock.mean_rate_idref,
                    weight="30.0")
                bssvs_bitflip = True
            else:
                bssvs_bitflip = False
            xml.operator(
                run,
                id="indicatorFlip.s:%s" % fname,
                spec="BitFlipOperator",
                parameter="@rateIndicator.s:%s" % fname,
                weight="30.0" if bssvs_bitflip else "60.0")
            sampoffop = xml.operator(
                run,
                id="offGeorateSampler:%s" % fname,
                spec="SampleOffValues",
                all="false",
                values="@relativeGeoRates.s:%s" % fname,
                indicators="@rateIndicator.s:%s" % fname,
                weight="30.0")
            xml.dist(sampoffop, idref="Gamma:%s.%d.0" % (fname, n))

    def add_param_logs(self, logger):
        BaseModel.add_param_logs(self, logger)
        for f in self.features:
            fname = "%s:%s" % (self.name, f)
            xml.log(logger, idref="rateIndicator.s:%s" % fname)
            xml.log(logger, idref="relativeGeoRates.s:%s" % fname)
