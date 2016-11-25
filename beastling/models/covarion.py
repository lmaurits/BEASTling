import xml.etree.ElementTree as ET

from .binary import BinaryModel


class CovarionModel(BinaryModel):

    def process(self):
        BinaryModel.process(self)
        self.freq_str = self.build_freq_str()

    def build_freq_str(self):
        if self.binarised:
            all_data = []
            for f in self.features:
                for lang in self.data:
                    if self.data[lang][f] == "?":
                        continue
                    dpoint, index = self.data[lang][f], self.unique_values[f].index(self.data[lang][f])
                    all_data.append(index)
        else:
            all_data = []
            for f in self.features:
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

    def add_state(self, state):
        BinaryModel.add_state(self, state)
        alpha = ET.SubElement(state, "parameter", {"id":"%s:covarion_alpha.s" % self.name, "lower":"1.0E-4", "name":"stateNode", "upper":"1.0"})
        alpha.text="0.5"
        switch = ET.SubElement(state, "parameter", {"id":"%s:covarion_s.s" % self.name, "lower":"1.0E-4", "name":"stateNode", "upper":"Infinity"})
        switch.text="0.5"
        vfreq = ET.SubElement(state, "parameter", {"id":"%s:visiblefrequencies.s" % self.name, "dimension":"2","name":"stateNode"})
        if self.frequencies == "empirical":
            vfreq.text = self.freq_str
        else:
            vfreq.text="0.5 0.5"

    def get_userdatatype(self, feature, fname):
        if not self.beastxml._covarion_userdatatype_created:
            self.beastxml._covarion_userdatatype_created = True
            return ET.Element("userDataType", {"id":"TwoStateCovarionDatatype", "spec":"beast.evolution.datatype.TwoStateCovarion"})
        else:
            return ET.Element("userDataType", {"idref":"TwoStateCovarionDatatype"})

    def add_misc(self, beast):
        # The "vfrequencies" parameter here is the frequencies
        # of the *visible* states (present/absent) and should
        # be based on the data (if we are doing an empirical
        # analysis)
        substmodel = ET.SubElement(beast, "substModel",{"id":"%s:covarion.s" % self.name,"spec":"BinaryCovarion","alpha":"@%s:covarion_alpha.s" % self.name, "switchRate":"@%s:covarion_s.s" % self.name, "vfrequencies":"@%s:visiblefrequencies.s" % self.name})
        # These are the frequencies of the *hidden* states
        # (fast / slow), and are just set to 50:50 
        hfreq = ET.SubElement(substmodel, "parameter", {"id":"%s:hiddenfrequencies.s" % self.name,"dimension":"2","lower":"0.0","name":"hfrequencies","upper":"1.0"})
        hfreq.text="0.5 0.5"

        # Dummy frequencies - these do nothing and are required
        # to stop the BinaryCovarion model complaining that the
        # "frequencies" input is not specified, which is
        # inherited behaviour from GeneralSubstitutionModel
        # which probably should have been overridden...
        freq = ET.SubElement(substmodel, "frequencies", {"id":"%s:dummyfrequences.s" % self.name,"spec":"Frequencies","frequencies":"0.5 0.5"})

    def add_sitemodel(self, distribution, feature, fname):

        # Sitemodel
        if self.rate_variation:
            mr = "@featureClockRate:%s" % fname
        else:
            mr = "1.0"
        sitemodel = ET.SubElement(distribution, "siteModel", {"id":"SiteModel.%s"%fname,"spec":"SiteModel", "mutationRate":mr,"shape":"1","proportionInvariant":"0", "substModel":"@%s:covarion.s" % self.name})

    def add_prior(self, prior):
        BinaryModel.add_prior(self, prior)
        alpha_prior = ET.SubElement(prior, "prior", {"id":"%s:covarion_alpha_prior.s" % self.name,"name":"distribution","x":"@%s:covarion_alpha.s" % self.name})
        ET.SubElement(alpha_prior, "Uniform", {"id":"%s:CovAlphaUniform" % self.name,"name":"distr","upper":"Infinity"})
        switch_prior = ET.SubElement(prior, "prior", {"id":"%s:covarion_s_prior.s" % self.name,"name":"distribution","x":"@%s:covarion_s.s" % self.name})
        gamma = ET.SubElement(switch_prior, "Gamma", {"id":"%s:Gamma.0" % self.name, "name":"distr"})
        ET.SubElement(gamma, "parameter", {"id":"%s:covarion_switch_gamma_param1" % self.name,"name":"alpha","lower":"0.0","upper":"0.0"}).text = "0.05"
        ET.SubElement(gamma, "parameter", {"id":"%s:covarion_switch_gamma_param2" % self.name,"name":"beta","lower":"0.0","upper":"0.0"}).text = "10.0"

    def add_operators(self, run):
        BinaryModel.add_operators(self, run)
        ET.SubElement(run, "operator", {"id":"%s:covarion_alpha_scaler.s" % self.name, "spec":"ScaleOperator","parameter":"@%s:covarion_alpha.s" % self.name,"scaleFactor":"0.5","weight":"1.0"})
        ET.SubElement(run, "operator", {"id":"%s:covarion_s_scaler.s" % self.name, "spec":"ScaleOperator","parameter":"@%s:covarion_s.s" % self.name,"scaleFactor":"0.5","weight":"1.0"})

        # Estimate frequencies if asked
        if self.frequencies == "estimate":
            ET.SubElement(run, "operator", {"id":"%s:covarion_frequency_sampler.s" % self.name, "spec":"DeltaExchangeOperator","parameter":"@%s:visiblefrequencies.s" % self.name,"delta":"0.01","weight":"1.0"})

    def add_param_logs(self, logger):
        BinaryModel.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"idref":"%s:covarion_alpha.s" % self.name})
        ET.SubElement(logger,"log",{"idref":"%s:covarion_s.s" % self.name})
        if self.frequencies == "estimate":
            ET.SubElement(logger,"log",{"idref":"%s:visiblefrequencies.s" % self.name})
        if self.config.log_fine_probs:
            ET.SubElement(logger,"log",{"idref":"%s:covarion_alpha_prior.s" % self.name})
            ET.SubElement(logger,"log",{"idref":"%s:covarion_s_prior.s" % self.name})
