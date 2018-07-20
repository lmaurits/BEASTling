import xml.etree.ElementTree as ET

from .binary import BinaryModel


class PseudoDolloCovarionModel(BinaryModel):
    def __init__(self, model_config, global_config):
        BinaryModel.__init__(self, model_config, global_config)
        self.subst_model_id = None
        self.share_params = model_config.get("share_params", True)
        self.messages.append(
            """[DEPENDENCY] Model %s: Pseudo-Dollo Covarion is implemented in"""
            """ the BEAST package "Babel".""" % self.name)

    def build_freq_str(self, feature=None):
        # TODO: I think this should probably go in BinaryModel
        # But right now it is (loosely) coupled to Covarion via
        # self.share_params
        assert feature or self.share_params

        if feature is None:
            features = self.features
        else:
            features = [feature]

        all_data = []
        if self.binarised:
            for f in features:
                for lang in self.data:
                    if self.data[lang][f] == "?":
                        continue
                    dpoint, index = self.data[lang][f], self.unique_values[f].index(self.data[lang][f])
                    all_data.append(index)
        else:
            for f in features:
                for lang in self.data:
                    if self.data[lang].get(f,"?") == "?":
                        valuestring = "".join(["?" for i in range(0,len(self.unique_values[f])+1)])
                    else:
                        valuestring = ["0" for i in range(0,len(self.unique_values[f])+1)]
                        valuestring[self.unique_values[f].index(self.data[lang][f])+1] = "1"
                        all_data.extend(valuestring)

        all_data = [d for d in all_data if d !="?"]
        all_data = [int(d) for d in all_data]
        zerf = 1.0*all_data.count(0) / len(all_data)
        onef = 1.0*all_data.count(1) / len(all_data)
        assert abs(1.0 - (zerf+onef)) < 1e-6
        return "%.2f %.2f" % (zerf, onef)

    def _fnames(self):
        if self.share_params:
            return [self.name]
        else:
            return ["{:s}:{:s}".format(self.name, f)
                      for f in features]

    def add_state(self, state):
        BinaryModel.add_state(self, state)

        for fname in self._fnames():
            # One param for all features
            ET.SubElement(
                state, "parameter",
                {"id": "%s:pdcovarion_s.s" % fname,
                 "lower": "1.0E-4",
                 "name": "stateNode",
                 "dimension": "2",
                 "upper": "Infinity"}).text="0.5 0.5"
            ET.SubElement(
                state, "parameter",
                {"id": "%s:pdcovarion_origin.s" % fname,
                 "lower": "1",
                 "name": "stateNode",
                 "upper": "Infinity"}).text="10"
            ET.SubElement(
                state, "parameter",
                {"id": "%s:pdcovarion_death.s" % fname,
                 "lower": "1.0E-4",
                 "name": "stateNode",
                 "dimension": "2",
                 "upper": "1.0"}).text="1.0 0.1"

    def add_frequency_state(self, state):
        for fname in self._fnames():
            ET.SubElement(
                state, "parameter",
                {"id": "%s:visiblefrequencies.s" % fname,
                 "name": "stateNode",
                 "dimension": "3",
                 "lower": "0.0", "upper": "1.0"}).text="0.94 0.05 0.01"

    def get_userdatatype(self, feature, fname):
        if not self.beastxml._covarion_userdatatype_created:
            self.beastxml._covarion_userdatatype_created = True
            return ET.Element("userDataType", {"id": "PseudoDolloCovarionDatatype",
                                               "spec": "beast.evolution.datatype.UserDataType",
                                               "states": "5",
                                               "codelength": "1",
                                               "codeMap": """
        		        A = 0,
                		1 = 1 4,
		                B = 1,
        		        0 = 0 2 3 ,
                		? = 0 1 2 3 4,
		                - = 0 1 2 3 4,
        		        C = 2,
                		D = 3,
        		        E = 4
                                               """})
        else:
            return ET.Element("userDataType", {"idref": "PseudoDolloCovarionDatatype"})

    def add_sitemodel(self, distribution, feature, fname):
        # Sitemodel
        mr = self.get_mutation_rate(feature, fname)
        sitemodel = ET.SubElement(distribution, "siteModel",
                                  {"id": "SiteModel.{:s}".format(fname),
                                   "spec": "SiteModel",
                                   "mutationRate": mr,
                                   "shape": "1",
                                   "proportionInvariant": "0"})
        substmodel = self.add_substmodel(sitemodel, feature, fname)

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
        substmodel = ET.SubElement(
            sitemodel, "substModel",
            {"id": subst_model_id,
             "spec": "BirthDeathCovarion2",
             "deathprob": "@{:}:pdcovarion_death.s".format(name),
             "originLength": "@{:s}:pdcovarion_origin.s".format(name),
             "switchRate": "@{:}:pdcovarion_s.s".format(name)})

        # Numerical instability is an issue with this model, so we give the
        # option of using a more robust method of computing eigenvectors.
        if self.use_robust_eigensystem:
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
            if self.frequencies == "empirical":
                raise ValueError("Dollo model {:} cannot derive empirical "
                                 "frequencies from data".format(self.name))
            else:
                vfreq.text="0.94 0.05 0.01"

        # These are the frequencies of the *hidden* states
        # (fast / slow), and are just set to 50: 50.  They could be estimated,
        # in principle, but this seems to lead to serious instability problems
        # so we don't expose that possibility to the user.
        hfreq = ET.SubElement(
            substmodel, "parameter",
            {"id": "%s: hiddenfrequencies.s" % name,
             "dimension": "2",
             "name": "hfrequencies",
             "lower": "0.0","upper": "1.0"}).text="0.5 0.5"

    def add_prior(self, prior):
        BinaryModel.add_prior(self, prior)
        if self.share_params:
            self._add_prior(prior, self.name)
        else:
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                self._add_prior(prior, fname)

    def _add_prior(self, prior, name):
        switch_prior = ET.SubElement(
            prior, "prior",
            {"id": "%s:pdcovarion_s_prior.s" % name,
             "name": "distribution",
             "x": "@%s:pdcovarion_s.s" % name})
        gamma = ET.SubElement(
            switch_prior, "Gamma",
            {"id": "%s: Gamma.0" % name, "name": "distr"})
        ET.SubElement(
            gamma, "parameter",
            {"id": "%s:pdcovarion_switch_gamma_param1" % name,
             "name": "alpha",
             "lower": "0.0", "upper": "0.0"}).text = "0.05"
        ET.SubElement(
            gamma, "parameter",
            {"id": "%s:pdcovarion_switch_gamma_param2" % name,
             "name": "beta",
             "lower": "0.0", "upper": "0.0"}).text = "10.0"

        origin_prior = ET.SubElement(
            prior, "prior",
            {"id": "%s:pdcovarion_origin_prior.s" % name,
             "name": "distribution",
             "x": "@%s:pdcovarion_origin.s" % name})
        ET.SubElement(
            origin_prior, "Uniform",
            {"id": "%s:PDCovOriginUniform" % name,
             "name": "distr",
             "upper": "Infinity"})

        death_prior = ET.SubElement(
            prior, "prior",
            {"id": "%s:pdcovarion_death_prior.s" % name,
             "name": "distribution",
             "x": "@{:}:pdcovarion_death.s".format(name)})
        ET.SubElement(
            death_prior, "Exponential",
            {"id": "%s:PDCovDeathExp" % name,
             "name": "distr",
             "mean": "1.0"})

    def add_operators(self, run):
        BinaryModel.add_operators(self, run)
        if self.share_params:
            self._add_operators(run, self.name)
        else:
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                self._add_operators(run, fname)

    def _add_operators(self, run, name):
        ET.SubElement(
            run, "operator",
            {"id": "%s:pdcovarion_origin_scaler.s" % name,
             "spec": "ScaleOperator",
             "parameter": "@%s:pdcovarion_origin.s" % name,
             "scaleFactor": "0.75","weight": "0.1"})
        ET.SubElement(
            run, "operator",
            {"id": "%s:pdcovarion_s_scaler.s" % name,
             "spec": "ScaleOperator",
             "parameter": "@%s:pdcovarion_s.s" % name,
             "scaleFactor": "0.75","weight": "0.1"})
        ET.SubElement(
            run, "operator",
            {"id": "%s:pdcovarion_death_scaler.s" % name,
             "spec": "ScaleOperator",
             "parameter": "@%s:pdcovarion_death.s" % name,
             "scaleFactor": "0.75","weight": "0.1"})

    def add_frequency_operators(self, run):
        for fname in self._fnames():
            ET.SubElement(
                run, "operator",
                {"id": "%s:pdcovarion_frequency_sampler.s" % fname,
                 "spec": "DeltaExchangeOperator",
                 "parameter": "@%s:visiblefrequencies.s" % fname,
                 "delta": "0.01","weight": "1.0"})

    def add_param_logs(self, logger):
        BinaryModel.add_param_logs(self, logger)
        for fname in self._fnames():
            ET.SubElement(logger, "log", {"idref": "%s:pdcovarion_s.s" % fname})
            ET.SubElement(logger, "log", {"idref": "%s:pdcovarion_origin.s" % fname})
            ET.SubElement(logger, "log", {"idref": "%s:pdcovarion_death.s" % fname})
            if self.config.log_fine_probs:
                ET.SubElement(logger, "log", {"idref": "%s:pdcovarion_s_prior.s" % fname})
                ET.SubElement(logger, "log", {"idref": "%s:pdcovarion_origin_prior.s" % fname})
                ET.SubElement(logger, "log", {"idref": "%s:pdcovarion_death_prior.s" % fname})

    def add_frequency_logs(self, logger):
        if self.share_params:
            ET.SubElement(logger, "log", {"idref": "%s:visiblefrequencies.s" % self.name})
        else:
            for f in self.features:
                fname = "%s: %s" % (self.name, f)
                ET.SubElement(logger, "log", {"idref": "%s:visiblefrequencies.s" % fname})
