#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import xml.etree.ElementTree as ET

from .binary import BinaryModel
from .basemodel import BaseModel


class StochasticDolloModel(BinaryModel):
    package_notice = """[DEPENDENCY]: The Stochastic Dollo model is implemented in the BEAST package "Babel"."""

    def __init__(self, model_config, global_config):

        BinaryModel.__init__(self, model_config, global_config)
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
        alpha = ET.SubElement(state, "parameter", {"id":"%s:dollo_alpha.s" % self.name, "lower":"1.0E-4", "name":"stateNode", "upper":"1.0"})
        alpha.text="0.5"
        switch = ET.SubElement(state, "parameter", {"id":"%s:dollo_s.s" % self.name, "lower":"1.0E-4", "name":"stateNode", "upper":"Infinity"})
        switch.text="0.5"

    def get_userdatatype(self, feature, fname):
        return ET.Element("userDataType", {"idref":"mutationdeathtype.%s"%self.name})

    def add_misc(self, beast):
        pass

    def add_sitemodel(self, distribution, feature, fname):
        """ Add an *observationprocess* for the ALSTreeLikelihood `distribution`. """

        # Observation process

        # The death rate is the main clock rate of this model.
        if self.rate_variation:
            dr = "@featureClockRate:%s" % fname
        else:
            dr = "1.0"
        observationprocess = ET.SubElement(
            distribution,
            "observationprocess",
            {"id": "AnyTipObservationProcess.%s"%fname,
             "spec": "AnyTipObservationProcess",
             "integrateGainRate": "true",
             "mu": dr, 
             "tree": "@Tree.t:beastlingTree",
             "data": "@orgdata.%s"%fname}
            )
        sitemodel = ET.SubElement(
            observationprocess,
            "siteModel",
            {"id": "SiteModel.%s"%fname,
             "spec": "SiteModel",
             "mutationRate": dr,
             "shape": "1.0",
             "proportionInvariant": "0.0"})
        substmodel = ET.SubElement(
            sitemodel,
            "substModel",
            {"id": "SDollo.%s" % fname,
             "spec": "MutationDeathModel",
             "deathprob": dr})
        freq = ET.SubElement(
            substmodel,
            "frequencies",
            {"id": "%s:dummyfrequences.s" % fname,
             "spec": "Frequencies",
             "frequencies":"0.5 0.5"})

    def add_feature_data(self, distribution, index, feature, fname):
        """ Add feature data for the ALSTreeLikelihood `distribution`. 

        Ensure that the data type is MutationDeathType."""
        data = BaseModel.add_feature_data(self, distribution, index, feature, fname)
        if self.ascertained:
            data.set("ascertained", "true")
            data.set("excludefrom", "0")
            data.set("excludeto", "1")
        else:
            data.set("ascertained", "false")

        data.set("id", "orgdata.%s"%fname)

    def add_prior(self, prior):
        BinaryModel.add_prior(self, prior)
        alpha_prior = ET.SubElement(prior, "prior", {"id":"%s:dollo_alpha_prior.s" % self.name,"name":"distribution","x":"@%s:dollo_alpha.s" % self.name})
        ET.SubElement(alpha_prior, "Uniform", {"id":"%s:CovAlphaUniform" % self.name,"name":"distr","upper":"Infinity"})
        switch_prior = ET.SubElement(prior, "prior", {"id":"%s:dollo_s_prior.s" % self.name,"name":"distribution","x":"@%s:dollo_s.s" % self.name})
        gamma = ET.SubElement(switch_prior, "Gamma", {"id":"%s:Gamma.0" % self.name, "name":"distr"})
        ET.SubElement(gamma, "parameter", {"id":"%s:dollo_switch_gamma_param1" % self.name,"name":"alpha","lower":"0.0","upper":"0.0"}).text = "0.05"
        ET.SubElement(gamma, "parameter", {"id":"%s:dollo_switch_gamma_param2" % self.name,"name":"beta","lower":"0.0","upper":"0.0"}).text = "10.0"

    def add_operators(self, run):
        BinaryModel.add_operators(self, run)
        ET.SubElement(run, "operator", {"id":"%s:dollo_alpha_scaler.s" % self.name, "spec":"ScaleOperator","parameter":"@%s:dollo_alpha.s" % self.name,"scaleFactor":"0.5","weight":"1.0"})
        ET.SubElement(run, "operator", {"id":"%s:dollo_s_scaler.s" % self.name, "spec":"ScaleOperator","parameter":"@%s:dollo_s.s" % self.name,"scaleFactor":"0.5","weight":"1.0"})

    def add_param_logs(self, logger):
        BinaryModel.add_param_logs(self, logger)
        ET.SubElement(logger,"log",{"idref":"%s:dollo_alpha.s" % self.name})
        ET.SubElement(logger,"log",{"idref":"%s:dollo_s.s" % self.name})
        if self.config.log_fine_probs:
            ET.SubElement(logger,"log",{"idref":"%s:dollo_alpha_prior.s" % self.name})
            ET.SubElement(logger,"log",{"idref":"%s:dollo_s_prior.s" % self.name})

    def add_likelihood(self, likelihood):
        """ Add an ALS likelihood distribution  corresponding to all features in the dataset.
        """
        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)
            attribs = {"id":"featureLikelihood:%s" % fname,"spec":"ALSTreeLikelihood","useAmbiguities":"true","siteModel":"@SiteModel.%s"%fname}
            if self.pruned:
                raise NotImplementedError
            else:
                #attribs["branchRateModel"] = "@%s" % self.clock.branchrate_model_id
                attribs["tree"] = "@Tree.t:beastlingTree"
                distribution = ET.SubElement(likelihood, "distribution", attribs)

            # Sitemodel
            self.add_sitemodel(distribution, f, fname)

            # Data
            self.add_feature_data(distribution, n, f, fname)

    def add_master_data(self, beast):
        self.filters = {}
        self.weights = {}
        # Compared to BaseModel.add_master_data, this function only
        # differs in the data type.
        data = ET.SubElement(beast, "data", {
            "id": "data_%s" % self.name,
            "userDataType": "@mutationdeathtype.%s"%self.name,
            "name": "data_%s" % self.name})
        mutationdeathtype = ET.SubElement(beast, "userDataType", {
            "id": "mutationdeathtype.%s"%self.name,
            "spec": "beast.evolution.datatype.MutationDeathType",
            "deathChar": "0",
            "extantCode": "1"})
        for lang in self.languages:
            formatted_points = [self.format_datapoint(f, self.data[lang][f]) for f in self.features]
            value_string = self.data_separator.join(formatted_points)
            if not self.filters:
                n = 1
                for f, x in zip(self.features, formatted_points):
                    # Find out how many sites in the sequence correspond to this feature
                    if self.data_separator:
                        length = len(x.split(self.data_separator))
                    else:
                        length = len(x)
                    self.weights[f] = length
                    # Format the FilteredAlignment filter appropriately
                    if length == 1:
                        self.filters[f] = str(n)
                    else:
                        self.filters[f] = "%d-%d" % (n, n+length-1)
                    n += length
            seq = ET.SubElement(data, "sequence", {
                "id":"data_%s:%s" % (self.name, lang),
                "taxon":lang,
                "value":value_string})
