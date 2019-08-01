from beastling.util import xml


class GeoModel(object):
    """A geographical substitution model.

    GeoModel uses the spherical geometry Beast package for
    phylogeographic inference.

    """

    package_notice = '[DEPENDENCY]: The SphericalGeo model is '\
                     'implemented in the BEAST package "GEO_SPHERE".'

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
        xml.parameter(
            state, text="100.0", id="sphericalPrecision", lower="0.0", name="stateNode")
        xml.stateNode(
            state,
            id="location.geo",
            spec="sphericalGeo.LocationParameter",
            minordimension="2",
            estimate="true",
            value="0.0 0.0",
            lower="0.0")

    def add_prior(self, prior):
        """
        Add prior distributions for Gamma-distributed rate heterogenetiy, if
        configured.
        """
        if self.scale_precision:
            precision_prior = xml.prior(
                prior,
                id="sphericalPrecisionPrior",
                x="@sphericalPrecision",
                name="distribution")
            xml.Uniform(
                precision_prior,
                id="sphericalPrecisionPriorUniform",
                name="distr",
                lower="0",
                upper="1e10")

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
        distribution = xml.distribution(likelihood, attrib=attribs)
        # Add data first, as this may trigger the creation of additional
        # sampling points (for langs with missing locations data)
        self.add_data(distribution)
        # Now add geopriors
        if self.sampling_points:
            multi = xml.multiGeoprior(
                distribution,
                id="multiGeoPrior",
                spec="sphericalGeo.MultiGeoPrior",
                tree="@Tree.t:beastlingTree",
                newick="")
            for clade in self.sampling_points:
                # Get languages in clade
                if clade == "root":
                    langs = self.config.languages
                else:
                    langs = self.config.language_group(clade)
                if not langs:
                    continue
                # Add the geo prior, which will trigger sampling
                geoprior = xml.geoprior(
                    multi,
                    id="%s.geoPrior" %  clade,
                    spec="sphericalGeo.GeoPrior",
                    location="@location.geo",
                    tree="@Tree.t:beastlingTree")
                if len(langs) > 1:
                    self.beastxml.add_taxon_set(geoprior, "%s.geo" % clade, langs)
                else:
                    xml.taxon(geoprior, idref=list(langs)[0])
                    # Drop back to F, not F2, so singletons can be sampled
                    distribution.set("spec", "sphericalGeo.ApproxMultivariateTraitLikelihoodF")
                # Also add the KML file if we have an actual constraint
                if clade in self.geo_priors:
                    xml.region(
                        geoprior, spec="sphericalGeo.region.KMLRegion", kml=self.geo_priors[clade])

        self.add_sitemodel(distribution)
        xml.branchRateModel(distribution, idref=self.clock.branchrate_model_id)

    def add_sitemodel(self, distribution):
        site = xml.siteModel(distribution, id="sphericalGeoSiteModel", spec="SiteModel")
        xml.substModel(
            site,
            id="sphericalDiffusionSubstModel",
            spec="sphericalGeo.SphericalDiffusionModel",
            precision="@sphericalPrecision",
            fast="true",
            threshold="1")

    def add_data(self, distribution):
        """
        Add <data> element corresponding to the indicated feature, descending
        from the indicated likelihood distribution.
        """
        data = xml.data(distribution, id="locationData", spec="sphericalGeo.AlignmentFromTraitMap")
        traitmap = xml.traitMap(
            data,
            id="geographyTraitmap",
            spec="sphericalGeo.TreeTraitMap",
            initByMean="true",
            randomizelower="-90 -180",
            randomizeupper="90 180",
            traitName="location",
            tree="@Tree.t:beastlingTree")
        xml.parameter(
            traitmap,
            text="0.0 0.0",
            id="locationParameter",
            spec="sphericalGeo.LocationParameter",
            dimension=2 * (2 * len(self.config.languages) -1),
            minordimension="2")
        loc_data_text_bits = []
        for lang in self.config.languages:
            lat, lon = self.config.locations.get(lang, ("?", "?"))
            if "?" in (lat, lon):
                if lang not in self.sampling_points:
                    self.sampling_points.append(lang)
                    self.messages.append("""[INFO] Geo model: Location of language %s will be sampled.  You may wish to add a prior.""" % lang)
            else:
                bit = "%s=%.2f %.2f" % (lang, lat, lon)
                loc_data_text_bits.append(bit)
        traitmap.text = ",\n".join(loc_data_text_bits)
        xml.userDataType(data, id="LocationDataType", spec="sphericalGeo.LocationDataType")

    def add_operators(self, run):
        """
        Add <operators> for individual feature substitution rates if rate
        variation is configured.
        """
        if self.scale_precision:
            xml.operator(
                run,
                id="sphericalPrecisionScaler",
                spec="ScaleOperator",
                parameter="@sphericalPrecision",
                weight="5",
                scaleFactor="0.7")
        if self.sampling_points:
            xml.operator(
                run,
                id="location.sampler",
                spec="sphericalGeo.LocationOperatorF",
                location="@location.geo",
                likelihood="@sphericalGeographyLikelihood",
                weight="10")

    def add_param_logs(self, logger):
        """
        Add entires to the logfile corresponding to individual feature
        substition rates if rate variation is configured.
        """
        if self.config.log_fine_probs:
            xml.log(logger, idref="sphericalGeographyLikelihood")
