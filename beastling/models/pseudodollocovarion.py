from .binary import BinaryModelWithShareParams as BinaryModel
from beastling.util import xml
from beastling.util import log


class PseudoDolloCovarionModel(BinaryModel):
    def __init__(self, model_config, global_config):
        BinaryModel.__init__(self, model_config, global_config)
        self.subst_model_id = None
        log.dependency("Pseudo-Dollo Covarion", "Babel", model=self)

    def add_state(self, state):
        BinaryModel.add_state(self, state)

        for fname in self.parameter_identifiers():
            # One param for all features
            xml.parameter(
                state,
                text="0.5 0.5",
                id="%s:pdcovarion_s.s" % fname,
                lower="1.0E-4",
                name="stateNode",
                dimension="2",
                upper="Infinity")
            xml.parameter(
                state,
                text="10",
                id="%s:pdcovarion_origin.s" % fname,
                lower="1",
                name="stateNode",
                upper="Infinity")
            xml.parameter(
                state,
                text="1.0 0.1",
                id="%s:pdcovarion_death.s" % fname,
                lower="1.0E-4",
                name="stateNode",
                dimension="2",
                upper="1.0")

    def add_frequency_state(self, state):
        for fname in self.parameter_identifiers():
            xml.parameter(
                state,
                text="0.94 0.05 0.01",
                id="%s:visiblefrequencies.s" % fname,
                name="stateNode",
                dimension="3",
                lower="0.0",
                upper="1.0")

    def get_userdatatype(self, feature, fname):
        if not self.beastxml._covarion_userdatatype_created:
            self.beastxml._covarion_userdatatype_created = True
            return xml.userDataType(
                None,
                id="PseudoDolloCovarionDatatype",
                spec="beast.evolution.datatype.UserDataType",
                states="5",
                codelength="1",
                codeMap="""
        		        A = 0,
                		1 = 1 4,
		                B = 1,
        		        0 = 0 2 3 ,
                		? = 0 1 2 3 4,
		                - = 0 1 2 3 4,
        		        C = 2,
                		D = 3,
        		        E = 4
                                               """)
        else:
            return xml.userDataType(None, idref="PseudoDolloCovarionDatatype")

    def add_substmodel(self, sitemodel, feature, fname):
        # If we're sharing one substmodel across all features and have already
        # created it, just reference it and that's it
        if self.share_params and self.subst_model_id:
            sitemodel.set("substModel", "@%s" % self.subst_model_id)
            return

        # Otherwise, create a substmodel
        if self.share_params:
            self._add_substmodel(sitemodel, None, None)
        else:
            self._add_substmodel(sitemodel, feature, fname)

    def _add_substmodel(self, sitemodel, feature, name):
        if self.share_params:
            name = self.name
            self.subst_model_id = "%s:pdcovarion.s" % name
        subst_model_id = "%s:pdcovarion.s" % name
        substmodel = xml.substModel(
            sitemodel,
            id=subst_model_id,
            spec="BirthDeathCovarion2",
            deathprob="@{:}:pdcovarion_death.s".format(name),
            originLength="@{:s}:pdcovarion_origin.s".format(name),
            switchRate="@{:}:pdcovarion_s.s".format(name))

        # Numerical instability is an issue with this model, so we give the
        # option of using a more robust method of computing eigenvectors.
        if self.use_robust_eigensystem: # pragma: no cover
            raise ValueError(
                "Currently, Beast's pseudo-Dollo covarion model does not "
                "support robust eigensystems.")
            substmodel.set("eigenSystem", "beast.evolution.substitutionmodel.RobustEigenSystem")

        # The "vfrequencies" parameter here is the frequencies
        # of the *visible* states (present/absent) and should
        # be based on the data (if we are doing an empirical
        # analysis)
        if self.frequencies == "estimate":
            substmodel.set("vfrequencies","@%s:visiblefrequencies.s" % name)
        else:
            vfreq = xml.vfrequencies(
                substmodel,
                id="%s:visiblefrequencies.s" % name,
                dimension="3",
                spec="parameter.RealParameter")
            if self.frequencies == "empirical": # pragma: no cover
                raise ValueError("Dollo model {:} cannot derive empirical "
                                 "frequencies from data".format(self.name))
            else:
                vfreq.text="0.94 0.05 0.01"

        # These are the frequencies of the *hidden* states
        # (fast / slow), and are just set to 50: 50.  They could be estimated,
        # in principle, but this seems to lead to serious instability problems
        # so we don't expose that possibility to the user.
        xml.parameter(
            substmodel,
            text="0.5 0.5",
            id="%s: hiddenfrequencies.s" % name,
            dimension="2",
            name="hfrequencies",
            lower="0.0",
            upper="1.0")

    def add_prior(self, prior):
        BinaryModel.add_prior(self, prior)
        for fname in self.parameter_identifiers():
            self._add_prior(prior, fname)

    def _add_prior(self, prior, name):
        switch_prior = xml.prior(
            prior,
            id="%s:pdcovarion_s_prior.s" % name,
            name="distribution",
            x="@%s:pdcovarion_s.s" % name)
        gamma = xml.Gamma(switch_prior, id="%s: Gamma.0" % name, name="distr")
        xml.parameter(
            gamma,
            text="0.05",
            id="%s:pdcovarion_switch_gamma_param1" % name,
            name="alpha",
            lower="0.0",
            upper="0.0")
        xml.parameter(
            gamma,
            text="10.0",
            id="%s:pdcovarion_switch_gamma_param2" % name,
            name="beta",
            lower="0.0",
            upper="0.0")
        origin_prior = xml.prior(
            prior,
            id="%s:pdcovarion_origin_prior.s" % name,
            name="distribution",
            x="@%s:pdcovarion_origin.s" % name)
        xml.Uniform(
            origin_prior,
            id="%s:PDCovOriginUniform" % name,
            name="distr",
            upper="Infinity")
        death_prior = xml.prior(
            prior,
            id="%s:pdcovarion_death_prior.s" % name,
            name="distribution",
            x="@{:}:pdcovarion_death.s".format(name))
        xml.Exponential(
            death_prior,
            id="%s:PDCovDeathExp" % name,
            name="distr",
            mean="1.0")

    def add_operators(self, run):
        BinaryModel.add_operators(self, run)
        for fname in self.parameter_identifiers():
            self._add_operators(run, fname)

    def _add_operators(self, run, name):
        xml.operator(
            run,
            id="%s:pdcovarion_origin_scaler.s" % name,
            spec="ScaleOperator",
            parameter="@%s:pdcovarion_origin.s" % name,
            scaleFactor="0.75",
            weight="0.1")
        xml.operator(
            run,
            id="%s:pdcovarion_s_scaler.s" % name,
            spec="ScaleOperator",
            parameter="@%s:pdcovarion_s.s" % name,
            scaleFactor="0.75",
            weight="0.1")
        xml.operator(
            run,
            id="%s:pdcovarion_death_scaler.s" % name,
            spec="ScaleOperator",
            parameter="@%s:pdcovarion_death.s" % name,
            scaleFactor="0.75",
            weight="0.1")

    def add_frequency_operators(self, run):
        for fname in self.parameter_identifiers():
            xml.operator(
                run,
                id="%s:pdcovarion_frequency_sampler.s" % fname,
                spec="DeltaExchangeOperator",
                parameter="@%s:visiblefrequencies.s" % fname,
                delta="0.01",
                weight="1.0")

    def add_param_logs(self, logger):
        BinaryModel.add_param_logs(self, logger)
        for fname in self.parameter_identifiers():
            xml.log(logger, idref="%s:pdcovarion_s.s" % fname)
            xml.log(logger, idref="%s:pdcovarion_origin.s" % fname)
            xml.log(logger, idref="%s:pdcovarion_death.s" % fname)
            if self.config.admin.log_fine_probs:
                xml.log(logger, idref="%s:pdcovarion_s_prior.s" % fname)
                xml.log(logger, idref="%s:pdcovarion_origin_prior.s" % fname)
                xml.log(logger, idref="%s:pdcovarion_death_prior.s" % fname)

    def add_frequency_logs(self, logger):
        for fname in self.parameter_identifiers():
            xml.log(logger, idref="%s:visiblefrequencies.s" % fname)
