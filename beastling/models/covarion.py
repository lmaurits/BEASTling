import xml.etree.ElementTree as ET

from .binary import BinaryModelWithShareParams as BinaryModel


class CovarionModel(BinaryModel):

    def __init__(self, model_config, global_config):

        BinaryModel.__init__(self, model_config, global_config)
        self.subst_model_id = None

    def add_state(self, state):
        BinaryModel.add_state(self, state)
        # Each feature gets a param
        for fname in self.parameter_identifiers():
            ET.SubElement(state, "parameter", {"id":"%s:covarion_alpha.s" % fname, "lower":"1.0E-4", "name":"stateNode", "upper":"1.0"}).text="0.5"
            ET.SubElement(state, "parameter", {"id":"%s:covarion_s.s" % fname, "lower":"1.0E-4", "name":"stateNode", "upper":"Infinity"}).text="0.5"

    def add_frequency_state(self, state):
        for fname in self.parameter_identifiers():
            ET.SubElement(state, "parameter", {"id":"%s:visiblefrequencies.s" % fname, "name":"stateNode", "dimension":"2", "lower":"0.0", "upper":"1.0"}).text="0.5 0.5"

    def get_userdatatype(self, feature, fname):
        if not self.beastxml._covarion_userdatatype_created:
            self.beastxml._covarion_userdatatype_created = True
            return ET.Element("userDataType", {"id":"TwoStateCovarionDatatype", "spec":"beast.evolution.datatype.TwoStateCovarion"})
        else:
            return ET.Element("userDataType", {"idref":"TwoStateCovarionDatatype"})


    def add_sitemodel(self, distribution, feature, fname):

        # Sitemodel
        mr = self.get_mutation_rate(feature, fname)
        sitemodel = ET.SubElement(distribution, "siteModel", {"id":"SiteModel.%s"%fname,"spec":"SiteModel", "mutationRate":mr,"shape":"1","proportionInvariant":"0"})
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
            self.subst_model_id = "%s:covarion.s" % name
        subst_model_id = "%s:covarion.s" % name
        substmodel = ET.SubElement(sitemodel, "substModel",{"id":subst_model_id,"spec":"BinaryCovarion","alpha":"@%s:covarion_alpha.s" % name, "switchRate":"@%s:covarion_s.s" % name})

        # Numerical instability is an issue with this model, so we give the
        # option of using a more robust method of computing eigenvectors.
        if self.use_robust_eigensystem:
            substmodel.set("eigenSystem","beast.evolution.substitutionmodel.RobustEigenSystem")

        # The "vfrequencies" parameter here is the frequencies
        # of the *visible* states (present/absent) and should
        # be based on the data (if we are doing an empirical
        # analysis)
        if self.frequencies == "estimate":
            substmodel.set("vfrequencies","@%s:visiblefrequencies.s" % name)
        else:
            vfreq = ET.SubElement(substmodel, "vfrequencies", {"id":"%s:visiblefrequencies.s" % name, "dimension":"2","spec":"parameter.RealParameter"})
            if self.frequencies == "empirical":
                if self.share_params:
                    vfreq.text = self.build_freq_str()
                else:
                    vfreq.text = self.build_freq_str(feature)
            else:
                vfreq.text="0.5 0.5"

        # These are the frequencies of the *hidden* states
        # (fast / slow), and are just set to 50:50.  They could be estimated,
        # in principle, but this seems to lead to serious instability problems
        # so we don't expose that possibility to the user.
        hfreq = ET.SubElement(substmodel, "parameter", {"id":"%s:hiddenfrequencies.s" % name,"dimension":"2","lower":"0.0","name":"hfrequencies","upper":"1.0"})
        hfreq.text="0.5 0.5"

        # Dummy frequencies - these do nothing and are required
        # to stop the BinaryCovarion model complaining that the
        # "frequencies" input is not specified, which is
        # inherited behaviour from GeneralSubstitutionModel
        # which probably should have been overridden...
        freq = ET.SubElement(substmodel, "frequencies", {"id":"%s:dummyfrequences.s" % name,"spec":"Frequencies","frequencies":"0.5 0.5"})

    def add_prior(self, prior):
        BinaryModel.add_prior(self, prior)
        for fname in self.parameter_identifiers():
            self._add_prior(prior, fname)

    def _add_prior(self, prior, name):
        alpha_prior = ET.SubElement(prior, "prior", {"id":"%s:covarion_alpha_prior.s" % name,"name":"distribution","x":"@%s:covarion_alpha.s" % name})
        ET.SubElement(alpha_prior, "Uniform", {"id":"%s:CovAlphaUniform" % name,"name":"distr","upper":"Infinity"})
        switch_prior = ET.SubElement(prior, "prior", {"id":"%s:covarion_s_prior.s" % name,"name":"distribution","x":"@%s:covarion_s.s" % name})
        gamma = ET.SubElement(switch_prior, "Gamma", {"id":"%s:Gamma.0" % name, "name":"distr"})
        ET.SubElement(gamma, "parameter", {"id":"%s:covarion_switch_gamma_param1" % name,"name":"alpha","lower":"0.0","upper":"0.0"}).text = "0.05"
        ET.SubElement(gamma, "parameter", {"id":"%s:covarion_switch_gamma_param2" % name,"name":"beta","lower":"0.0","upper":"0.0"}).text = "10.0"

    def add_operators(self, run):
        BinaryModel.add_operators(self, run)
        for fname in self.parameter_identifiers():
            self._add_operators(run, fname)

    def _add_operators(self, run, name):
        ET.SubElement(run, "operator", {"id":"%s:covarion_alpha_scaler.s" % name, "spec":"ScaleOperator","parameter":"@%s:covarion_alpha.s" % name,"scaleFactor":"0.5","weight":"1.0"})
        ET.SubElement(run, "operator", {"id":"%s:covarion_s_scaler.s" % name, "spec":"ScaleOperator","parameter":"@%s:covarion_s.s" % name,"scaleFactor":"0.5","weight":"1.0"})

    def add_frequency_operators(self, run):
        for fname in self.parameter_identifiers():
            ET.SubElement(run, "operator", {"id":"%s:covarion_frequency_sampler.s" % fname, "spec":"DeltaExchangeOperator","parameter":"@%s:visiblefrequencies.s" % fname,"delta":"0.01","weight":"1.0"})

    def add_param_logs(self, logger):
        BinaryModel.add_param_logs(self, logger)
        for fname in self.parameter_identifiers():
            ET.SubElement(logger,"log",{"idref":"%s:covarion_alpha.s" % fname})
            ET.SubElement(logger,"log",{"idref":"%s:covarion_s.s" % fname})
            if self.config.log_fine_probs:
                ET.SubElement(logger,"log",{"idref":"%s:covarion_alpha_prior.s" % fname})
                ET.SubElement(logger,"log",{"idref":"%s:covarion_s_prior.s" % fname})

    def add_frequency_logs(self, logger):
        for fname in self.parameter_identifiers():
            ET.SubElement(logger,"log",{"idref":"%s:visiblefrequencies.s" % fname})
