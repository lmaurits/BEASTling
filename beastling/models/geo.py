import io
import os
import xml.etree.ElementTree as ET

from ..fileio.datareaders import load_data, _language_column_names


class GeoModel(object):
    """
    Base class from which all substitution model classes are descended.
    Implements generic functionality which is common to all substitution
    models, such as rate variation.
    """

    def __init__(self, model_config, global_config):
        """
        Parse configuration options, load data from file and pre-process data.
        """
        self.config = global_config
        self.messages = []
        self.name = model_config["name"]
        self.clock = model_config.get("clock", None)
        self.scale_precision = False

    def add_misc(self, beast):
        pass

    def add_state(self, state):
        ET.SubElement(state, "parameter", {
            "id":"sphericalPrecision",
            "lower":"0.0",
            "name":"stateNode"}).text = "100.0"

    def add_prior(self, prior):
        """
        Add prior distributions for Gamma-distributed rate heterogenetiy, if
        configured.
        """
        if not self.scale_precision:
            return
        precision_prior = ET.SubElement(prior, "prior", {
            "id":"sphericalPrecisionPrior",
            "x":"@sphericalPrecision",
            "name":"distribution"})
        ET.SubElement(precision_prior, "Uniform", {
            "id":"sphericalPrecisionPriorUniform",
            "name":"distr",
            "lower":"0",
            "upper":"1e10"})

    def add_likelihood(self, likelihood):
        """
        Add likelihood distribution corresponding to all features in the
        dataset.
        """
        attribs = {"id":"sphericalGeographyLikelihood",
            "spec":"sphericalGeo.ApproxMultivariateTraitLikelihood",
            "tree":"@Tree.t:beastlingTree"
            }
        distribution = ET.SubElement(likelihood, "distribution",attribs)
        self.add_sitemodel(distribution)
        ET.SubElement(distribution, "branchRateModel", {"idref": self.clock.branchrate_model_id})
        self.add_data(distribution)

    def add_sitemodel(self, distribution):

        site = ET.SubElement(distribution, "siteModel", {
            "id":"sphericalGeoSiteModel",
            "spec":"SiteModel"})
        subst = ET.SubElement(site, "substModel", {
            "id":"sphericalDiffusionSubstModel",
            "spec":"sphericalGeo.SphericalDiffusionModel",
            "precision":"@sphericalPrecision",
            "fast":"true"})

    def add_data(self, distribution):
        """
        Add <data> element corresponding to the indicated feature, descending
        from the indicated likelihood distribution.
        """
        data = ET.SubElement(distribution,"data", {
            "id":"locationData",
            "spec":"sphericalGeo.AlignmentFromTraitMap"})
        traitmap = ET.SubElement(data,"traitMap", {
            "id":"geographyTraitmap",
            "spec":"sphericalGeo.TreeTraitMap",
            "initByMean":"true",
            "randomizelower":"-90 -180",
            "randomizeupper":"90 180",
            "traitName":"location",
            "tree":"@Tree.t:beastlingTree"})
        n = len(self.config.languages)
        param = ET.SubElement(traitmap, "parameter", {
            "id":"locationParameter",
            "spec":"sphericalGeo.LocationParameter",
            "dimension":str(2*(2*n -1)),
            "minordimension":"2"})
        param.text = "0.0 0.0"
        loc_data_text_bits = []
        for lang in self.config.languages:
            if lang not in self.config.locations:
                continue
            lat, lon = self.config.locations[lang]
            bit = "%s=%.2f %.2f" % (lang, lat, lon)
            loc_data_text_bits.append(bit)
        traitmap.text = ",\n".join(loc_data_text_bits)
        ET.SubElement(data, "userDataType", {
            "id":"LocationDataType",
            "spec":"sphericalGeo.LocationDataType"
            })

    def add_operators(self, run):
        """
        Add <operators> for individual feature substitution rates if rate
        variation is configured.
        """
        if not self.scale_precision:
            return
        ET.SubElement(run, "operator", {
            "id":"sphericalPrecisionScaler",
            "spec":"ScaleOperator",
            "parameter":"@sphericalPrecision",
            "weight":"5",
            "scaleFactor":"0.7"})


    def add_param_logs(self, logger):
        """
        Add entires to the logfile corresponding to individual feature
        substition rates if rate variation is configured.
        """
        pass
