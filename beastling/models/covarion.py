import xml.etree.ElementTree as ET

from .basemodel import BaseModel


class CovarionModel(BaseModel):

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        if model_config["binarised"] is None:
            # We've not been explicitly told if the data has been binarised
            # or not.  So attempt automagic:
            if all([self.valuecounts[f]==2 for f in self.features]):
                self.binarised = True
                self.messages.append("""[INFO] Model "%s": Assuming that data source %s contains pre-binarised cognate data.  Set "binarised=False" in config to stop this.""" % (self.name, self.data_filename))
            else:
                self.binarised = False
        else:
            # If we've been told, listen.
            self.binarised = model_config["binarised"]
        if self.constant_feature:
            self.ascertained = False
            self.messages.append("""[INFO] Model "%s": Constant features in data have been retained, so ascertainment correction will be disabled.""" % (self.name))
        else:
            self.ascertained = True
        self.freq_str = self.build_freq_str()

    def build_freq_str(self):
        if self.binarised:
            all_data = []
            for f in self.features:
                for lang in self.data:
                    all_data.extend(self.data[lang][f])
        else:
            all_data = []
            for f in self.features:
                frange = sorted(list(set(self.data[lang][f] for lang in self.data)))
                for lang in self.data:
                    if self.data[lang].get(f,"?") == "?":
                        valuestring = "".join(["?" for i in range(0,len(frange)+1)])
                    else:
                        valuestring = ["0" for i in range(0,len(frange)+1)]
                        valuestring[frange.index(self.data[lang][f])+1] = "1"
                        all_data.extend(valuestring)

        all_data = [d for d in all_data if d !="?"]
        zerf = 1.0*all_data.count("0") / len(all_data)
        onef = 1.0*all_data.count("1") / len(all_data)
        return "%.2f %.2f" % (zerf, onef)

    def add_state(self, state):
        BaseModel.add_state(self, state)
        alpha = ET.SubElement(state, "parameter", {"id":"%s:covarion_alpha.s" % self.name, "lower":"1.0E-4", "name":"stateNode", "upper":"1.0"})
        alpha.text="0.5"
        switch = ET.SubElement(state, "parameter", {"id":"%s:covarion_s.s" % self.name, "lower":"1.0E-4", "name":"stateNode", "upper":"Infinity"})
        switch.text="0.5"

    def add_data(self, distribution, feature, fname):
        frange = sorted(list(set(self.data[lang][feature] for lang in self.config.languages)))
        if "?" in frange:
            frange.remove("?")
        attribs = {"id":fname, "spec":"Alignment"}
        if self.ascertained:
            attribs["ascertained"] = "true"
            attribs["excludefrom"] = "0"
            attribs["excludeto"] = "1"
        else:
            attribs["ascertained"] = "false"
        data = ET.SubElement(distribution,"data",attribs)
        ET.SubElement(data, "userDataType",{"spec":"beast.evolution.datatype.TwoStateCovarion"})
        extra_columns = 1 if self.ascertained else 0
        for lang in self.config.languages:
            if self.binarised:
                if self.data[lang][feature] == "?":
                    valuestring = "??" if self.ascertained else "?"
                else:
                    valuestring = str(frange.index(self.data[lang][feature]))
                    if self.ascertained:
                        valuestring = "0" + valuestring
            else:
                if self.data[lang][feature] == "?":
                    valuestring = "".join(["?" for i in range(0,len(frange)+extra_columns)])
                else:
                    valuestring = ["0" for i in range(0,len(frange)+extra_columns)]
                    valuestring[frange.index(self.data[lang][feature])+extra_columns] = "1"
                    valuestring = "".join(valuestring)

            seq = ET.SubElement(data, "sequence", {"id":"seq_%s_%s" % (lang, fname), "taxon":lang, "totalcount":"4","value":valuestring})

    def add_misc(self, beast):
        # The "vfrequencies" parameter here is the frequencies
        # of the *visible* states (present/absent) and should
        # be based on the data (if we are doing an empirical
        # analysis)
        substmodel = ET.SubElement(beast, "substModel",{"id":"%s:covarion.s" % self.name,"spec":"BinaryCovarion","alpha":"@%s:covarion_alpha.s" % self.name, "switchRate":"@%s:covarion_s.s" % self.name})
        vfreq = ET.SubElement(substmodel, "parameter", {"id":"%s:visiblefrequencies.s" % self.name,"dimension":"2","name":"vfrequencies"})
        if self.frequencies == "empirical":
            vfreq.text = self.freq_str
        elif self.frequencies == "uniform":
            vfreq.text="0.5 0.5"
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
        BaseModel.add_prior(self, prior)
        alpha_prior = ET.SubElement(prior, "prior", {"id":"%s:covarion_alpha_prior.s" % self.name,"name":"distribution","x":"@%s:covarion_alpha.s" % self.name})
        ET.SubElement(alpha_prior, "Uniform", {"id":"%s:CovAlphaUniform" % self.name,"name":"distr","upper":"Infinity"})
        switch_prior = ET.SubElement(prior, "prior", {"id":"%s:covarion_s_prior.s" % self.name,"name":"distribution","x":"@%s:covarion_s.s" % self.name})
        gamma = ET.SubElement(switch_prior, "Gamma", {"id":"%s:Gamma.0" % self.name, "name":"distr"})
        ET.SubElement(gamma, "parameter", {"id":"%s:covarion_switch_gamma_param1" % self.name,"name":"alpha","lower":"0.0","upper":"0.0"}).text = "0.05"
        ET.SubElement(gamma, "parameter", {"id":"%s:covarion_switch_gamma_param2" % self.name,"name":"beta","lower":"0.0","upper":"0.0"}).text = "10.0"

    def add_operators(self, run):
        BaseModel.add_operators(self, run)
        ET.SubElement(run, "operator", {"id":"%s:covarion_alpha_scaler.s" % self.name, "spec":"ScaleOperator","parameter":"@%s:covarion_alpha.s" % self.name,"scaleFactor":"0.5","weight":"1.0"})
        ET.SubElement(run, "operator", {"id":"%s:covarion_s_scaler.s" % self.name, "spec":"ScaleOperator","parameter":"@%s:covarion_s.s" % self.name,"scaleFactor":"0.5","weight":"1.0"})

    def add_param_logs(self, logger):
        BaseModel.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"idref":"%s:covarion_alpha.s" % self.name})
        ET.SubElement(logger,"log",{"idref":"%s:covarion_s.s" % self.name})
