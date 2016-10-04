import io
import os
import xml.etree.ElementTree as ET

from ..fileio.datareaders import load_data

class BaseModel(object):
    """
    Base class from which all substitution model classes are descended.
    Implements generic functionality which is common to all substitution
    models, such as rate variation.
    """

    def __init__(self, model_config, global_config):
        """
        Parse configuration options, load data from file and pre-process data.
        """
        self.messages = []
        self.config = global_config

        self.name = model_config["name"] 
        self.data_filename = model_config["data"] 
        self.clock = model_config.get("clock", "")
        self.features = model_config.get("features",["*"])
        self.exclusions = model_config.get("exclusions",None)
        self.constant_feature = False
        self.frequencies = model_config.get("frequencies", "empirical")
        self.pruned = model_config.get("pruned", False)
        self.rate_variation = model_config.get("rate_variation", False)
        self.feature_rates = model_config.get("feature_rates", None)

        self.remove_constant_features = model_config.get("remove_constant_features", True)
        self.minimum_data = float(model_config.get("minimum_data", 0))
        self.substitution_name = self.__class__.__name__
        self.data_separator = ","

        # Load the entire dataset from the file
        self.data = load_data(self.data_filename, file_format=model_config.get("file_format",None), lang_column=model_config.get("language_column",None))
        # Remove features not wanted in this analysis
        self.build_feature_filter()
        self.apply_feature_filter()

    def build_feature_filter(self):
        """
        Create the self.feature_filter attribute, which is a set of feature
        names that functions analogously to Configuration.lang_filter
        attribute.
        """
        if self.features == ["*"]:
            random_iso = list(self.data.keys())[0]
            self.features = set()
            for lang_features in self.data.values():
                self.features |= set(lang_features.keys())
            self.features = list(self.features)
        if self.exclusions:
            self.features = [f for f in self.features if f not in self.exclusions]
        self.feature_filter = set(self.features)

    def process(self):
        """
        Subsample the data set to include only those languages and features
        which are compatible with the settings.
        """
        self.apply_language_filter()
        self.load_feature_rates()
        self.compute_feature_properties()
        self.remove_unwanted_features()
        if self.pruned:
            self.messages.append("""[DEPENDENCY] Model %s: Pruned trees are implemented in the BEAST package "BEASTlabs".""" % self.name)

    def apply_language_filter(self):
        """
        Remove all languages from the data set which are not part of the
        configured language filter.
        """
        all_langs = self.data.keys()
        langs_to_remove = [l for l in all_langs if not self.config.filter_language(l)]
        for lang in langs_to_remove:
            self.data.pop(lang)
        # Make sure we've not removed all languages
        if not self.data.keys():
            raise ValueError("Language filters leave nothing in the dataset for model '%s'!" % self.name)
        # Keep a sorted list so that the order of things in XML is deterministic
        self.languages = sorted(list(self.data.keys()))

    def load_feature_rates(self):
        """
        Load relative feature rates from .csv file.
        """
        if not self.feature_rates:
            return
        if not os.path.exists(self.feature_rates):
            raise ValueError("Could not find feature rate file %s." % self.feature_rates)
        with io.open(self.feature_rates, encoding="UTF-8") as fp:
            self.feature_rates = {}
            for line in fp:
                feature, rate = line.split(",")
                rate = float(rate.strip())
                self.feature_rates[feature] = rate
        norm = sum(self.feature_rates.values())
        for f in self.feature_rates:
            self.feature_rates[f] /= norm

    def apply_feature_filter(self):
        """
        Remove all features from the data set which are not part of the
        configured feature filter.
        """
        self.features = set()
        for language in self.data.values():
            features_in_data = set(language.keys())
            features_to_keep = features_in_data & self.feature_filter
            self.features |= features_to_keep
            features_to_remove = features_in_data - features_to_keep
            for feat in features_to_remove:
                language.pop(feat)
        self.features = sorted(list(self.features))

    def compute_feature_properties(self):
        """
        Compute various items of metadata for all remaining features.
        """

        self.valuecounts = {}
        self.unique_values = {}
        self.missing_ratios = {}
        self.counts = {}
        self.dimensions = {}
        self.codemaps = {}
        for f in self.features:
            # Compute various things
            all_values = [self.data[l].get(f,"?") for l in self.data]
            missing_data_ratio = all_values.count("?") / (1.0*len(all_values))
            non_q_values = [v for v in all_values if v != "?"]
            counts = {}
            for v in non_q_values:
                counts[v] = non_q_values.count(v)
            unique_values = list(set(non_q_values))
            # Sort unique_values carefully.
            # Possibly all feature values are numeric strings, e.g. "1", "2", "3".
            # If we sort these as strings then we get weird things like "10" < "2".
            # This can actually matter for things like ordinal models.
            # So convert these to ints first...
            if all([v.isdigit() for v in unique_values]):
                unique_values = list(map(int, unique_values))
                unique_values.sort()
                unique_values = list(map(str, unique_values))
            # ...otherwise, just sort normally
            else:
                unique_values.sort()
            self.unique_values[f] = unique_values

            N = len(unique_values)
            self.valuecounts[f] = N
            self.missing_ratios[f] = missing_data_ratio
            self.counts[f] = counts
            self.dimensions[f] = N*(N-1) // 2
            self.codemaps[f] = self.build_codemap(unique_values)

    def remove_unwanted_features(self):
        """
        Remove any undesirable features from the dataset, such as those with
        no data for the configured set of languages, constant features, etc.
        """

        bad_feats = []
        for f in self.features:

            # Exclude features with no data
            if self.valuecounts[f] == 0:
                self.messages.append("""[INFO] Model "%s": Feature %s excluded because there are no datapoints for selected languages.""" % (self.name, f))
                bad_feats.append(f)
                continue

            # Exclude features with lots of missing data
            missing_ratio = self.missing_ratios[f]
            if int(100*(1.0-missing_ratio)) < self.minimum_data:
                self.messages.append("""[INFO] Model "%s": Feature %s excluded because of excessive missing data (%d%%).""" % (self.name, f, int(missing_ratio*100)))
                bad_feats.append(f)
                continue

            # Exclude constant features
            if self.valuecounts[f] == 1:
                if self.remove_constant_features:
                    self.messages.append("""[INFO] Model "%s": Feature %s excluded because its value is constant across selected languages.  Set "remove_constant_features=False" in config to stop this.""" % (self.name, f))
                    bad_feats.append(f)
                    continue
                else:
                    self.constant_feature = True

        for bad in bad_feats:
            self.features.remove(bad)
            for lang in self.languages:
                if bad in self.data[lang]:
                    self.data[lang].pop(bad)

        # Make sure there's something left
        if not self.features:
            raise ValueError("No features specified for model %s!" % self.name)
        self.features.sort()
        self.messages.append("""[INFO] Model "%s": Using %d features from data source %s""" % (self.name, len(self.features), self.data_filename))
        if self.constant_feature and self.rate_variation:
            self.messages.append("""[WARNING] Model "%s": Rate variation enabled with constant features retained in data.  This may skew rate estimates for non-constant features.""" % self.name)

    def build_codemap(self, unique_values):
        """
        Build a codemap string for a feature.
        """
        N = len(unique_values)
        codemapbits = []
        codemapbits.append(",".join(["%s=%d" % (v,n) for (n,v) in enumerate(unique_values)]))
        codemapbits.append("?=" + " ".join([str(n) for n in range(0,N)]))
        codemapbits.append("-=" + " ".join([str(n) for n in range(0,N)]))
        return ",".join(codemapbits)

    def add_misc(self, beast):
        pass

    def add_state(self, state):
        """
        Add parameters for Gamma-distributed rate heterogenetiy, if
        configured.
        """
        if self.rate_variation:
            if not self.feature_rates:
                # Set all rates to 1.0 in a big plate
                plate = ET.SubElement(state, "plate", {
                    "var":"feature",
                    "range":",".join(self.features)})
                param = ET.SubElement(plate, "parameter", {
                    "id":"featureClockRate:%s:$(feature)" % self.name,
                    "name":"stateNode"})
                param.text="1.0"
            else:
                # Give each rate a custom value
                for f in self.features:
                    param = ET.SubElement(state, "parameter", {
                        "id":"featureClockRate:%s:%s" % (self.name, f),
                        "name":"stateNode"})
                    param.text=str(self.feature_rates.get(f,1.0))

            parameter = ET.SubElement(state, "parameter", {"id":"featureClockRateGammaShape:%s" % self.name, "lower":"0.0","upper":"100.0","name":"stateNode"})
            parameter.text="2.0"
            parameter = ET.SubElement(state, "parameter", {"id":"featureClockRateGammaScale:%s" % self.name, "name":"stateNode"})
            parameter.text="0.5"

    def add_prior(self, prior):
        """
        Add prior distributions for Gamma-distributed rate heterogenetiy, if
        configured.
        """
        if self.rate_variation:
            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRatePrior.s:%s" % self.name, "name":"distribution"})
            compound = ET.SubElement(sub_prior, "input", {"id":"featureClockRateCompound:%s" % self.name, "spec":"beast.core.parameter.CompoundValuable", "name":"x"})
            plate = ET.SubElement(compound, "plate", {
                "var":"feature",
                "range":",".join(self.features)})
            ET.SubElement(plate, "var", {
                "idref":"featureClockRate:%s:$(feature)" % self.name})
            gamma  = ET.SubElement(sub_prior, "input", {"id":"featureClockRatePriorGamma:%s" % self.name, "spec":"beast.math.distributions.Gamma", "name":"distr", "alpha":"@featureClockRateGammaShape:%s" % self.name, "beta":"@featureClockRateGammaScale:%s" % self.name})

            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRateGammaShapePrior.s:%s" % self.name, "name":"distribution", "x":"@featureClockRateGammaShape:%s" % self.name})
            ET.SubElement(sub_prior, "Exponential", {"id":"featureClockRateGammaShapePriorExponential.s:%s" % self.name, "mean":"1.0", "name":"distr"})

    def add_likelihood(self, likelihood):
        """
        Add likelihood distribution corresponding to all features in the
        dataset.
        """
        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)
            attribs = {"id":"featureLikelihood:%s" % fname,"spec":"TreeLikelihood","useAmbiguities":"true"}
            if self.pruned:
                distribution = ET.SubElement(likelihood, "distribution",attribs)
                # Create pruned tree
                tree_id = "Tree.t:prunedBeastlingTree.%s" % fname
                tree = ET.SubElement(distribution, "tree", {"id":tree_id, "spec":"beast.evolution.tree.PrunedTree","quickshortcut":"true","assert":"false"})
                ET.SubElement(tree, "tree", {"idref":"Tree.t:beastlingTree"})
                ET.SubElement(tree, "alignment", {"idref":"pruned_data_%s"%fname})
                # Create pruned branchrate
                self.clock.add_pruned_branchrate_model(distribution, fname, tree_id)
            else:
                attribs["branchRateModel"] = "@%s" % self.clock.branchrate_model_id
                attribs["tree"] = "@Tree.t:beastlingTree"
                distribution = ET.SubElement(likelihood, "distribution",attribs)

            # Sitemodel
            self.add_sitemodel(distribution, f, fname)

            # Data
            self.add_feature_data(distribution, n, f, fname)

    def add_sitemodel(self, beast):
        pass

    def add_master_data(self, beast):
        self.filters = {}
        self.weights = {}
        data = ET.SubElement(beast, "data", {
            "id":"data_%s" % self.name,
            "name":"data_%s" % self.name,
            "dataType":"integer"})
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

    def format_datapoint(self, feature, point):
        return str(point)

    def add_feature_data(self, distribution, index, feature, fname):
        """
        Add <data> element corresponding to the indicated feature, descending
        from the indicated likelihood distribution.
        """
        if self.pruned:
            pruned_align = ET.SubElement(distribution,"data",{"id":"pruned_data_%s" % fname, "spec":"PrunedAlignment"})
            parent = pruned_align
            name = "source"
        else:
            parent = distribution
            name = "data"
        data = ET.SubElement(parent, name, {
            "id":"data_%s" % fname,
            "spec":"FilteredAlignment",
            "data":"@data_%s" % self.name,
            "filter":self.filters[feature]})
        data.append(self.get_userdatatype(feature, fname))
        return data

    def get_userdatatype(self, feature, fname):
        return ET.Element("userDataType", {"id":"featureDataType.%s"%fname,"spec":"beast.evolution.datatype.UserDataType","codeMap":self.codemaps[feature],"codelength":"-1","states":str(self.valuecounts[feature])})

    def add_operators(self, run):
        """
        Add <operators> for individual feature substitution rates if rate
        variation is configured.
        """
        if self.rate_variation:
            # UpDownOperator to scale the Gamma distribution for this model's
            # feature rates
            updown = ET.SubElement(run, "operator", {"id":"featureClockRateGammaUpDown:%s" % self.name, "spec":"UpDownOperator", "scaleFactor":"0.5","weight":"0.3"})
            ET.SubElement(updown, "parameter", {"idref":"featureClockRateGammaShape:%s" % self.name, "name":"up"})
            ET.SubElement(updown, "parameter", {"idref":"featureClockRateGammaScale:%s" % self.name, "name":"down"})

    def add_param_logs(self, logger):
        """
        Add entires to the logfile corresponding to individual feature
        substition rates if rate variation is configured.
        """
        if self.config.log_fine_probs:
            plate = ET.SubElement(logger, "plate", {
                "var":"feature",
                "range":",".join(self.features)})
            ET.SubElement(plate, "log", {
                "idref":"featureLikelihood:%s:$(feature)" % self.name})
            if self.rate_variation:
                ET.SubElement(logger,"log",{"idref":"featureClockRatePrior.s:%s" % self.name})
                ET.SubElement(logger,"log",{"idref":"featureClockRateGammaShapePrior.s:%s" % self.name})

        if self.rate_variation:
            plate = ET.SubElement(logger, "plate", {
                "var":"feature",
                "range":",".join(self.features)})
            ET.SubElement(plate, "log", {
                "idref":"featureClockRate:%s:$(feature)" % self.name})
            # Log the shape, but not the scale, as it is always 1 / shape
            ET.SubElement(logger,"log",{"idref":"featureClockRateGammaShape:%s" % self.name})
