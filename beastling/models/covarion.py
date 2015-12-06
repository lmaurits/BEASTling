import codecs
import os
import xml.etree.ElementTree as ET

from .basemodel import BaseModel
from ..unicodecsv import UnicodeDictReader

class CovarionModel(BaseModel):

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        self.freq_str = self.build_freq_str()

    def build_freq_str(self):
        all_data = []
        for n, trait in enumerate(self.traits):
            traitname = "%s:%s" % (self.name, trait)
            traitrange = sorted(list(set(self.data[lang][trait] for lang in self.data)))
            for lang in self.data:
                if self.data[lang].get(trait,"?") == "?":
                    valuestring = "".join(["?" for i in range(0,len(traitrange)+1)])
                else:
                    valuestring = ["0" for i in range(0,len(traitrange)+1)]
                    valuestring[traitrange.index(self.data[lang][trait])+1] = "1"
                    all_data.extend(valuestring)

        all_data = [d for d in all_data if d !="?"]
        zerf = 1.0*all_data.count("0") / len(all_data)
        onef = 1.0*all_data.count("1") / len(all_data)
        return "%.2f %.2f" % (zerf, onef)

    def add_state(self, state):
        BaseModel.add_state(self, state)
        alpha = ET.SubElement(state, "parameter", {"id":"covarion_alpha.s", "lower":"1.0E-4", "name":"stateNode", "upper":"1.0"})
        alpha.text="0.5"
        switch = ET.SubElement(state, "parameter", {"id":"covarion_s.s", "lower":"1.0E-4", "name":"stateNode", "upper":"Infinity"})
        switch.text="0.5"

        freq = ET.SubElement(state, "parameter", {"id":"frequencies.s","dimension":"2","lower":"0.0","name":"stateNode","upper":"1.0"})
        freq.text=self.freq_str

    def add_data(self, distribution, trait, traitname):
        traitrange = sorted(list(set(self.data[lang][trait] for lang in self.config.languages)))
        data = ET.SubElement(distribution,"data",{"id":traitname, "spec":"Alignment", "ascertained":"true", "excludefrom":"0","excludeto":"1"})
        ET.SubElement(data, "userDataType",{"spec":"beast.evolution.datatype.TwoStateCovarion"})
        for lang in self.config.languages:
            if self.data[lang][trait] == "?":
                valuestring = "".join(["?" for i in range(0,len(traitrange)+1)])
            else:
                valuestring = ["0" for i in range(0,len(traitrange)+1)]
                valuestring[traitrange.index(self.data[lang][trait])+1] = "1"
                valuestring = "".join(valuestring)

            seq = ET.SubElement(data, "sequence", {"id":"seq_%s_%s" % (lang, traitname), "taxon":lang, "totalcount":"4","value":valuestring})

    def add_misc(self, beast):
        # The "vfrequencies" parameter here is the frequencies
        # of the *visible* states (present/absent) and should
        # be based on the data
        substmodel = ET.SubElement(beast, "substModel",{"id":"covarion.s","spec":"BinaryCovarion","alpha":"@covarion_alpha.s", "switchRate":"@covarion_s.s", "vfrequencies":"@frequencies.s"})
        # These are the frequencies of the *hidden* states
        # (fast / slow), and are just set to 50:50 
        hfreq = ET.SubElement(substmodel, "parameter", {"id":"hiddenfrequencies.s","dimension":"2","lower":"0.0","name":"hfrequencies","upper":"1.0"})
        hfreq.text="0.5 0.5"

        # Dummy frequencies - these do nothing and are required
        # to stop the BinaryCovarion model complaining that the
        # "frequencies" input is not specified.
        freq = ET.SubElement(substmodel, "frequencies", {"id":"dummyfrequences.s","spec":"Frequencies","frequencies":"0.5 0.5"})

    def add_sitemodel(self, distribution, trait, traitname):

            # Sitemodel
            sitemodel = ET.SubElement(distribution, "siteModel", {"gammaCategoryCount":"1","id":"geoSiteModel.%s"%traitname,"spec":"SiteModel", "mutationRate":"1","shape":"1","proportionInvariant":"0", "substModel":"@covarion.s"})

    def add_prior(self, prior):
        BaseModel.add_prior(self, prior)
        alpha_prior = ET.SubElement(prior, "prior", {"id":"covarion_alpha_prior.s","name":"distribution","x":"@covarion_alpha.s"})
        ET.SubElement(alpha_prior, "Uniform", {"id":"CovAlphaUniform","name":"distr","upper":"Infinity"})
        switch_prior = ET.SubElement(prior, "prior", {"id":"covarion_s_prior.s","name":"distribution","x":"@covarion_s.s"})
        gamma = ET.SubElement(switch_prior, "Gamma", {"id":"Gamma.0", "name":"distr"})
        ET.SubElement(gamma, "parameter", {"id":"covarion_switch_gamma_param1","name":"alpha","lower":"0.0","upper":"0.0"}).text = "0.05"
        ET.SubElement(gamma, "parameter", {"id":"covarion_switch_gamma_param2","name":"beta","lower":"0.0","upper":"0.0"}).text = "10.0"

    def add_operators(self, run):
        BaseModel.add_operators(self, run)
        ET.SubElement(run, "operator", {"id":"covarion_alpha_scaler.s", "spec":"ScaleOperator","parameter":"@covarion_alpha.s","scaleFactor":"0.75","weight":"0.1"})
        ET.SubElement(run, "operator", {"id":"covarion_s_scaler.s", "spec":"ScaleOperator","parameter":"@covarion_s.s","scaleFactor":"0.75","weight":"0.1"})
        delta = ET.SubElement(run, "operator", {"id":"frequenciesDelta", "spec":"DeltaExchangeOperator","delta":"0.01","weight":"0.1"})
        ET.SubElement(delta, "parameter", {"idref":"frequencies.s"})

    def add_param_logs(self, logger):
        BaseModel.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"idref":"covarion_alpha.s"})
        ET.SubElement(logger,"log",{"idref":"covarion_s.s"})
