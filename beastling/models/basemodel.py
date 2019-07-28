import io
import os
import collections
import xml.etree.ElementTree as ET

from ..fileio.datareaders import load_data

class BaseModel(object):
    """
    Base class from which all substitution model classes are descended.
    Implements generic functionality which is common to all substitution
    models, such as rate variation.
    """

    treewide_reconstruction = False
    """Should ASR be performed on the entire tree (if at all)?"""

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
        self.reconstruct = model_config.get("reconstruct", None)
        self.reconstruct_at = model_config.get("reconstruct_at", [])
        self.exclusions = model_config.get("exclusions",None)
        self.constant_feature = False
        self.constant_feature_removed = False
        self.frequencies = model_config.get("frequencies", "empirical")
        self.pruned = model_config.get("pruned", False)
        self.rate_variation = model_config.get("rate_variation", False)
        self.feature_rates = model_config.get("feature_rates", None)
        self.rate_partition = model_config.get("rate_partition", None)
        self.ascertained = model_config.get("ascertained", None)
        # Force removal of constant features here
        # This can be set by the user in BinaryModel only
        self.remove_constant_features = True
        self.minimum_data = float(model_config.get("minimum_data", 0))
        self.substitution_name = self.__class__.__name__
        self.data_separator = ","
        self.use_robust_eigensystem = model_config.get("use_robust_eigensystem", False)
        self.metadata = []
        self.treedata = []

        # Load the entire dataset from the file
        self.data, language_code_map = load_data(
            self.data_filename,
            file_format=model_config.get("file_format", None),
            lang_column=model_config.get("language_column", None),
            value_column=model_config.get("value_column", None),
            expect_multiple=True)

        # Augment the Glottolog classifications with human-friendly language
        # names which may have been read from a CLDF dataset.  Note that we
        # store both the actual language ID and its lowercase transformation.
        # This is kind of ugly, but we inconsistently convert things to
        # lowercase before doing Glottolog lookups all over the place, so
        # this is the easiest way to make this work everywhere.  We should
        # clean this up some day!
        for language_id, glottocode in language_code_map.items():
            if glottocode in global_config.classifications:
                global_config.classifications[language_id] = global_config.classifications[glottocode]
                global_config.classifications[language_id.lower()] = global_config.classifications[language_id]
            if glottocode in global_config.glotto_macroareas:
                global_config.glotto_macroareas[language_id] = global_config.glotto_macroareas[glottocode]
                global_config.glotto_macroareas[language_id.lower()] = global_config.glotto_macroareas[language_id]
            if glottocode in global_config.locations:
                global_config.locations[language_id] = global_config.locations[glottocode]
                global_config.locations[language_id.lower()] = global_config.locations[language_id]

        # Remove features not wanted in this analysis
        self.build_feature_filter()
        self.apply_feature_filter()

        # Keep this around for later...
        self.global_config = global_config

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

        if self.reconstruct == ["*"]:
            self.reconstruct = self.features[:]
        elif self.reconstruct:
            fail_to_find = [f for f in self.reconstruct if f not in self.features]
            if fail_to_find:
                self.messages.append(
                    "[WARNING] Model {:s}:"
                    " Features {:} not found, cannot be reconstructed.""".format(
                        self.name, fail_to_find))
            self.reconstruct = [f for f in self.reconstruct if f in self.features]
            self.messages.append(
                    "[INFO] Model \"{:s}\":"
                    " Features {:} will be reconstructed.""".format(
                        self.name, self.reconstruct))
            # Note: That is a lie. Features can still be filtered out by
            # subsequent decisions, eg. because they are constant.
        else:
            self.reconstruct = []

        if self.reconstruct_at == ["*"]:
            self.reconstruct_at = None
            self.treewide_reconstruction = True
        elif self.reconstruct_at:
            if len(self.reconstruct_at) > 1:
                raise ValueError("Cannot currently reconstruct at more than one location.")
            for f in self.reconstruct_at:
                if f not in self.config.language_group_configs:
                    raise KeyError("Language group {:} is undefined. Valid groups are: {:}".format(
                        f, ", ".join(self.config.language_groups.keys())))
        elif self.reconstruct:
            self.reconstruct_at=["root"]

    def process(self):
        """
        Subsample the data set to include only those languages and features
        which are compatible with the settings.
        """
        self.apply_language_filter()
        self.compute_feature_properties()
        self.remove_unwanted_features()
        self.load_rate_partition()
        if self.rate_partition:
            self.all_rates = sorted(list(set(self.rate_partition.values())))
        elif self.rate_variation or self.feature_rates:
            self.all_rates = self.features
        self.load_feature_rates()
        if self.rate_partition and not (self.feature_rates or self.rate_variation):
            self.messages.append("""[WARNING] Model %s: Estimating rates for feature partitions because no fixed rates were provided, is this what you wnated?  Use rate_variation=True to make this implicit.""" % self.name)
            self.rate_variation = True
        self.compute_weights()
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

    def load_rate_partition(self):
        """
        Load a partition of features for sharing mutation rates.
        """
        if not self.rate_partition:
            self.rate_partition = {}
            return
        if not os.path.exists(self.rate_partition):
            raise ValueError("Could not find feature rate file %s." % self.rate_partition)
        fname = self.rate_partition
        with open(fname) as fp:
            # TODO: check that the partition includes all features
            self.rate_partition = {}
            for line in fp:
                name, part = line.split(":",1)
                name = name.strip()
                part = [p.strip() for p in part.split(",")]
                part = [p for p in part if p in self.features]
                for p in part:
                    self.rate_partition[p] = name

    def load_feature_rates(self):
        """
        Load relative feature rates from .csv file.
        """
        if not self.feature_rates:
            self.feature_rates = {}
            return
        if not os.path.exists(self.feature_rates):
            raise ValueError("Could not find feature rate file %s." % self.feature_rates)
        fname = self.feature_rates
        with io.open(self.feature_rates, encoding="UTF-8") as fp:
            self.feature_rates = {}
            for line in fp:
                feature, rate = line.split(",")
                feature = feature.strip()
                # Skip irrelevant things
                if feature not in self.all_rates:
                    continue
                rate = float(rate.strip())
                self.feature_rates[feature] = rate
        if not all((rate in self.feature_rates for rate in self.all_rates)):
            self.messages.append("""[WARNING] Model "%s": Rate file %s does not contain rates for every feature/partition.  Missing rates will default to 1.0, please check that this is okay.""" % (self.name, fname))
        if not self.feature_rates:
            self.messages.append("""[WARNING] Model "%s": Could not find any valid feature or partition rates in the file %s, is this the correct file for this analysis?""" % (self.name, fname))
            return
        norm = sum(self.feature_rates.values()) / len(self.feature_rates.values())
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

    def reduce_multivalue_data(self, list_of_data_points):
        """Reduce a list of data points to a single one.

        Given a list of data points (for a feature in a language), select the
        last of these data points as the one to be included in the analysis.

        """
        try:
            return list_of_data_points[-1]
        except IndexError:
            return "?"

    def compute_feature_properties(self):
        """
        Compute various items of metadata for all remaining features.
        """
        self.valuecounts = {}
        self.extracolumns = collections.defaultdict(int)
        self.unique_values = {}
        self.missing_ratios = {}
        self.counts = {}
        self.codemaps = {}
        for f in self.features:
            # Compute various things
            all_values = []
            for l in self.data:
                point = self.reduce_multivalue_data(self.data[l].get(f, ["?"]))
                all_values.append(point)
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
                    self.constant_feature_removed = True
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
            self.messages.append("""[WARNING] Model "%s": Rate variation enabled with constant features retained in data.  This *may* skew rate estimates for non-constant features.""" % self.name)

    def compute_weights(self):
        self.weights = []
        # Weights feed into a DeltaExchangeOperator, so they need to
        # be integers. This is currently implicit, not enforced.
        if self.rate_partition:
            parts = list(self.rate_partition.values())
            partition_weights = {p:parts.count(p) for p in parts}
            for part in sorted(list(set(self.rate_partition.values()))):
                self.weights.append(partition_weights[part])
        else:
            for f in self.features:
                self.weights.append(1)

    def set_ascertained(self):
        """
        Decide whether or not to do ascertainment correction for non-constant
        data, unless the user has provided an explicit setting.
        """

        # Do the correction if the tree is calibrated, as ascertainment
        # correction influences timing estimates
        if self.ascertained == None:
            self.ascertained = not self.global_config.arbitrary_tree

    def build_codemap(self, unique_values):
        """
        Build a codemap string for a feature.
        """
        N = len(unique_values)
        codemapbits = []
        codemapbits.append(",".join(["%d=%d" % (n,n) for n in range(0,len(unique_values))]))
        codemapbits.append("?=" + " ".join([str(n) for n in range(0,N)]))
        codemapbits.append("-=" + " ".join([str(n) for n in range(0,N)]))
        return ",".join(codemapbits)

    def add_misc(self, beast):
        pass

    def add_state(self, state):
        """Construct the model's state nodes.

        Add parameters for Gamma-distributed rate heterogenetiy, if
        configured.

        """

        if self.frequencies == "estimate":
            self.add_frequency_state(state)

        if self.rate_variation:
            if self.feature_rates:
                # If user specified rates have been provided for either
                # features or partitions, we need to list each rate
                # individually
                for rate in self.all_rates:
                    param = ET.SubElement(state, "parameter", {
                        "id":"featureClockRate:%s:%s" % (self.name, rate),
                        "name":"stateNode"})
                    param.text=str(self.feature_rates.get(rate,1.0))
            else:
                # If not, and everything is initialised to the same
                # value, we can just whack 'em all in a big plate
                plate = ET.SubElement(state, "plate", {
                    "var":"rate",
                    "range":",".join(self.all_rates)})
                param = ET.SubElement(plate, "parameter", {
                    "id":"featureClockRate:%s:$(rate)" % self.name,
                    "name":"stateNode"})
                param.text="1.0"

            # Give Gamma shape parameter a finite domain
            # Must be > 1.0 for the distribution to be bell-shaped,
            # rather than L-shaped.  The domain [1.1,1000] limits feature
            # rate variation to the realms of vague plausibity
            parameter = ET.SubElement(state, "parameter", {"id":"featureClockRateGammaShape:%s" % self.name, "lower":"1.1","upper":"100.0","name":"stateNode"})
            parameter.text="5.0"
            # Gamma scale parameter's domain is defined *implicilty*
            # by the fact that the operators maintain shape*scale = 1.0
            parameter = ET.SubElement(state, "parameter", {"id":"featureClockRateGammaScale:%s" % self.name, "name":"stateNode"})
            parameter.text="0.2"

    def add_frequency_state(self, state):
        for f in self.features:
            fname = "%s:%s" % (self.name, f)
            param = ET.SubElement(state,"stateNode",{
                "id":"feature_freqs_param.s:%s"%fname,
                "spec":"parameter.RealParameter",
                "dimension":str(self.valuecounts[f]),
                "lower":"0.0",
                "upper":"1.0",
            })
            param.text = str(1.0/self.valuecounts[f])

    def add_prior(self, prior):
        """
        Add prior distributions for Gamma-distributed rate heterogenetiy, if
        configured.
        """
        if self.rate_variation:
            # Gamma prior with mean 1 over all mutation rates
            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRatePrior.s:%s" % self.name, "name":"distribution"})
            compound = ET.SubElement(sub_prior, "input", {"id":"featureClockRateCompound:%s" % self.name, "spec":"beast.core.parameter.CompoundValuable", "name":"x"})
            plate = ET.SubElement(compound, "plate", {
                "var":"rate",
                "range":",".join(self.all_rates)})
            ET.SubElement(plate, "var", {
                "idref":"featureClockRate:%s:$(rate)" % self.name})
            gamma  = ET.SubElement(sub_prior, "input", {"id":"featureClockRatePriorGamma:%s" % self.name, "spec":"beast.math.distributions.Gamma", "name":"distr", "alpha":"@featureClockRateGammaShape:%s" % self.name, "beta":"@featureClockRateGammaScale:%s" % self.name})
            # Exponential hyperprior on scale of Gamma prior
            # Exponential prior favours small scales over large scales, i.e. less rate variation
            # Mean scale 0.23 chosen for general sensibility, e.g.:
            #   - Prior distribution is roughly 50/50 that ratio of fastest
            #     to slowest feature rate in a dataset of size 200 is below
            #     or above 10.
            #   - Prior probability of roughly 0.90 that this ratio is below
            #     100.
            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRateGammaScalePrior.s:%s" % self.name, "name":"distribution", "x":"@featureClockRateGammaScale:%s" % self.name})
            ET.SubElement(sub_prior, "Exponential", {"id":"featureClockRateGammaShapePriorExponential.s:%s" % self.name, "mean":"0.23", "name":"distr"})

    def pattern_names(self, feature):
        """Content of the columns corresponding to this feature in the alignment.

        This method is used for displaying helpful column names in ancestral
        state reconstruction output. It gives column headers for actual value
        columns as well as for dummy columns used in ascertainment correction,
        if such columns exist.

        """
        if self.ascertained:
            return ["{:}_dummy{:d}".format(feature, i)
                    for i in range(self.extracolumns[feature])] + [feature]
        else:
            return [feature]

    def add_likelihood(self, likelihood):
        """
        Add likelihood distribution corresponding to all features in the
        dataset.
        """
        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)
            attribs = {"id": "featureLikelihood:%s" % fname,
                       "spec": "TreeLikelihood",
                       "useAmbiguities": "true"}

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

            if f in  self.reconstruct:
                # Use a different likelihood spec (also depending on whether
                # the whole tree is reconstructed, or only some nodes)
                if self.treewide_reconstruction:
                    distribution.attrib["spec"] = "AncestralStateTreeLikelihood"
                    self.treedata.append(attribs["id"])
                    distribution.attrib["tag"] = f
                else:
                    distribution.attrib["spec"] = "AncestralStateLogger"
                    distribution.attrib["value"] = " ".join(self.pattern_names(f))
                    for label in self.reconstruct_at:
                        langs = self.config.language_group(label)
                        self.beastxml.add_taxon_set(distribution, label, langs)
                    self.metadata.append(attribs["id"])
                distribution.attrib["useAmbiguities"] = "false"

            # Sitemodel
            self.add_sitemodel(distribution, f, fname)

            # Data
            self.add_feature_data(distribution, n, f, fname)

    def add_sitemodel(self, distribution, feature, fname):
        mr = self.get_mutation_rate(feature, fname)
        sitemodel = ET.SubElement(distribution, "siteModel", {"id":"SiteModel.%s"%fname,"spec":"SiteModel", "mutationRate":mr,"proportionInvariant":"0"})
        substmodel = self.add_substmodel(sitemodel, feature, fname)

    def add_substmodel(self, sitemodel, feature, fname):
        pass

    def add_master_data(self, beast):
        self.filters = {}
        data = ET.SubElement(beast, "data", {
            "id":"data_%s" % self.name,
            "name":"data_%s" % self.name,
            "dataType":"integer"})
        for lang in self.languages:
            formatted_points = [
                self.format_datapoint(
                    f, self.data[lang].get(f, ["?"]))
                for f in self.features]
            value_string = self.data_separator.join(formatted_points)
            if not self.filters:
                n = 1
                for f, x in zip(self.features, formatted_points):
                    # Format the FilteredAlignment filter appropriately
                    if self.data_separator:
                        length = len(x.split(self.data_separator))
                    else:
                        length = len(x)
                    if length == 1:
                        self.filters[f] = str(n)
                    else:
                        self.filters[f] = "%d-%d" % (n, n+length-1)
                    n += length
            seq = ET.SubElement(data, "sequence", {
                "id":"language_data_%s:%s" % (self.name, lang),
                "taxon":lang,
                "value":value_string})

    def format_datapoint(self, feature, point):
        point = self.reduce_multivalue_data(point)
        if self.ascertained:
            return self._ascertained_format_datapoint(feature, point)
        else:
            return self._standard_format_datapoint(feature, point)

    def _standard_format_datapoint(self, feature, point):
        if point == "?":
            return point
        else:
            return str(self.unique_values[feature].index(point))

    def _ascertained_format_datapoint(self, feature, point):
        extra_cols = self.valuecounts[feature]
        self.extracolumns[feature] = extra_cols
        if point == "?":
            return self.data_separator.join(["?" for i in range(0, extra_cols + 1)])
        else:
            cols = list(range(0, extra_cols))
            cols.append(self.unique_values[feature].index(point))
            return self.data_separator.join(map(str, cols))

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
            "id":"feature_data_%s" % fname,
            "spec":"FilteredAlignment",
            "data":"@data_%s" % self.name,
            "filter":self.filters[feature]})
        if self.ascertained:
            data.set("ascertained", "true")
            data.set("excludefrom", "0")
            data.set("excludeto", str(self.valuecounts[feature]))
        data.append(self.get_userdatatype(feature, fname))
        return data

    def get_userdatatype(self, feature, fname):
        return ET.Element("userDataType", {"id":"featureDataType.%s"%fname,"spec":"beast.evolution.datatype.UserDataType","codeMap":self.codemaps[feature],"codelength":"-1","states":str(self.valuecounts[feature])})

    def get_mutation_rate(self, feature, fname):
        """
        Get a string which can be used as the mutationRate for a sitemodel.
        """
        if self.rate_variation:
            if self.rate_partition:
                mr = "@featureClockRate:%s:%s" % (self.name, self.rate_partition[feature])
            else:
                mr = "@featureClockRate:%s" % fname
        elif self.feature_rates:
            if self.rate_partition:
                mr = str(self.feature_rates.get(self.rate_partition[feature], 1.0))
            else:
                mr = str(self.feature_rates.get(feature, 1.0))
        else:
            mr = "1.0"
        return mr

    def add_operators(self, run):
        """
        Add <operators> for individual feature substitution rates if rate
        variation is configured.
        """
        if self.frequencies == "estimate":
            self.add_frequency_operators(run)
        if self.rate_variation:
            # UpDownOperator to scale the Gamma distribution for this model's
            # feature rates
            updown = ET.SubElement(run, "operator", {"id":"featureClockRateGammaUpDown:%s" % self.name, "spec":"UpDownOperator", "scaleFactor":"0.5","weight":"0.3"})
            ET.SubElement(updown, "parameter", {"idref":"featureClockRateGammaShape:%s" % self.name, "name":"up"})
            ET.SubElement(updown, "parameter", {"idref":"featureClockRateGammaScale:%s" % self.name, "name":"down"})

    def add_frequency_operators(self, run):
        for f in self.features:
            fname = "%s:%s" % (self.name, f)
            ET.SubElement(run, "operator", {"id":"estimatedFrequencyOperator:%s" % fname, "spec":"DeltaExchangeOperator", "parameter":"@feature_freqs_param.s:%s" % fname, "delta":"0.01","weight":"0.1"})

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
                ET.SubElement(logger,"log",{"idref":"featureClockRateGammaScalePrior.s:%s" % self.name})

        if self.frequencies == "estimate":
            self.add_frequency_logs(logger)
        if self.rate_variation:
            plate = ET.SubElement(logger, "plate", {
                "var":"rate",
                "range":",".join(self.all_rates)})
            ET.SubElement(plate, "log", {
                "idref":"featureClockRate:%s:$(rate)" % self.name})
            # Log the scale, but not the shape, as it is always 1 / scale
            # We prefer the scale because it is positively correlated with extent of variation
            ET.SubElement(logger,"log",{"idref":"featureClockRateGammaShape:%s" % self.name})

    def add_frequency_logs(self, logger):
        for f in self.features:
            fname = "%s:%s" % (self.name, f)
            ET.SubElement(logger,"log",{"idref":"feature_freqs_param.s:%s" % fname})
