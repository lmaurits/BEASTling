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
        self.sampling_points = model_config.get("sampling_points", [])
        self.geo_priors = model_config.get("geo_priors", {})
        self.scale_precision = False

    def add_misc(self, beast):
        pass

    def add_state(self, state):
        ET.SubElement(state, "parameter", {
            "id":"sphericalPrecision",
            "lower":"0.0",
            "name":"stateNode"}).text = "100.0"
        ET.SubElement(state, "stateNode", {
            "id":"location.geo",
            "spec":"sphericalGeo.LocationParameter",
            "minordimension":"2",
            "estimate":"true",
            "value":"0.0 0.0",
            "lower":"0.0"})

    def add_prior(self, prior):
        """
        Add prior distributions for Gamma-distributed rate heterogenetiy, if
        configured.
        """
        if self.scale_precision:
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
            "tree":"@Tree.t:beastlingTree",
            "logAverage":"true",
            "scale":"false",
            "location":"@location.geo"}
        # Use appropriate Likelihood implementation depending
        # upon presence/absence of sampled locations
        if self.sampling_points:
            attribs["spec"] = "sphericalGeo.ApproxMultivariateTraitLikelihoodF2"
        else:
            attribs["spec"] = "sphericalGeo.ApproxMultivariateTraitLikelihood"
        distribution = ET.SubElement(likelihood, "distribution",attribs)
        if self.sampling_points:
            multi = ET.SubElement(distribution, "multiGeoprior", {
                "id":"multiGeoPrior",
                "spec":"sphericalGeo.MultiGeoPrior",
                "tree":"@Tree.t:beastlingTree",
                "newick":""})
            for clade in self.sampling_points:
                # Get languages in clade
                if clade == "root":
                    langs = self.config.languages
                else:
                    langs = self.config.get_languages_by_glottolog_clade(clade)
                if not langs:
                    continue
                # Add the geo prior, which will trigger sampling
                geoprior = ET.SubElement(multi, "geoprior", {
                    "id":"%s.geoPrior" %  clade,
                    "spec":"sphericalGeo.GeoPrior",
                    "location":"@location.geo",
                    "tree":"@Tree.t:beastlingTree"})
                self.beastxml.add_taxon_set(geoprior, "%s.geo" % clade, langs)
                # Also add the KML file if we have an actual constraint
                if clade in self.geo_priors:
                    kml = self.geo_priors[clade]
                    ET.SubElement(geoprior, "region", {
                        "spec":"sphericalGeo.region.KMLRegion",
                        "kml":kml})

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
            "fast":"true",
            "threshold":"1"})

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
        if self.scale_precision:
            ET.SubElement(run, "operator", {
                "id":"sphericalPrecisionScaler",
                "spec":"ScaleOperator",
                "parameter":"@sphericalPrecision",
                "weight":"5",
                "scaleFactor":"0.7"})
        if self.sampling_points:
            ET.SubElement(run, "operator", {
                "id":"location.sampler",
                "spec":"sphericalGeo.LocationOperatorF",
                "location":"@location.geo",
                "likelihood":"@sphericalGeographyLikelihood",
                "weight":"10"})

    def add_param_logs(self, logger):
        """
        Add entires to the logfile corresponding to individual feature
        substition rates if rate variation is configured.
        """
        if self.config.log_fine_probs:
            ET.SubElement(logger,"log",{"idref":"sphericalGeographyLikelihood"})
