import io
import os
import xml.etree.ElementTree as ET

from ..fileio.datareaders import load_data, _language_column_names


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
        self.calibrations = global_config.calibrations

        self.name = model_config["name"] 
        self.data_filename = model_config["data"] 
        self.clock = model_config.get("clock", "")
        self.features = model_config.get("features",["*"])
        self.constant_feature = False
        self.frequencies = model_config.get("frequencies", "empirical")
        self.pruned = model_config.get("pruned", False)
        self.rate_variation = model_config.get("rate_variation", False)
        self.remove_constant_features = model_config.get("remove_constant_features", True)
        self.minimum_data = float(model_config.get("minimum_data", 0))
        self.lang_column = model_config.get("language_column", None)
        self.substitution_name = self.__class__.__name__


        self.data = load_data(self.data_filename, file_format=model_config.get("file_format",None), lang_column=model_config.get("language_column",None))
        self.build_feature_filter()
        self.process()

    def build_feature_filter(self):
        """
        Create the self.feature_filter attribute, which is a set of feature
        names that functions analogously to Configuration.lang_filter
        attribute.
        """
        if self.features == ["*"]:
            random_iso = list(self.data.keys())[0]
            self.features = list(self.data[random_iso].keys())
            # Need to remove the language ID column
            if self.lang_column:
                self.features.remove(self.lang_column)
            else:
                # If no language column name was explicitly given, just
                # remove the first of the automatically-recognised names
                # which we encounter:
                for lc in _language_column_names:
                    if lc in self.features:
                        self.features.remove(lc)
                        break
        self.feature_filter = set(self.features)

    def process(self):
        """
        Subsample the data set to include only those languages and features
        which are compatible with the settings.
        """
        self.apply_language_filter()
        self.apply_feature_filter()
        self.compute_feature_properties()
        self.remove_unwanted_features()
        if self.pruned:
            self.messages.append("""[DEPENDENCY] Model %s: Pruned trees are implemented in the BEAST package "BEASTlabs".""" % self.name)

    def apply_language_filter(self):
        """
        Remove all languages from the data set which are not part of the
        configured language filter.
        """
        languages_in_data = set(self.data.keys())
        languages_to_keep = languages_in_data & self.config.lang_filter
        languages_to_remove = languages_in_data - languages_to_keep
        for lang in languages_to_remove:
            self.data.pop(lang)

    def apply_feature_filter(self):
        """
        Remove all features from the data set which are not part of the
        configured feature filter.
        """
        self.features = set()
        for lang in self.data:
            features_in_data = set(self.data[lang].keys())
            features_to_keep = features_in_data & self.feature_filter
            self.features |= features_to_keep
            features_to_remove = features_in_data - features_to_keep
            for feat in features_to_remove:
                self.data[lang].pop(feat)
        self.features = sorted(list(self.features))

    def compute_feature_properties(self):
        """
        Compute various items of metadata for all remaining features.
        """

        self.valuecounts = {}
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
            for lang in self.data:
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
            for f in self.features:
                fname = "%s:%s" % (self.name, f)

                attribs = {}
                attribs["id"] = "featureClockRate:%s" % fname
                attribs["name"] = "stateNode"
                parameter = ET.SubElement(state, "parameter", attribs)
                parameter.text="1.0"
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
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                var = ET.SubElement(compound, "var", {"idref":"featureClockRate:%s" % fname})
            gamma  = ET.SubElement(sub_prior, "input", {"id":"featureClockRatePriorGamma:%s" % self.name, "spec":"beast.math.distributions.Gamma", "name":"distr", "alpha":"@featureClockRateGammaShape:%s" % self.name, "beta":"@featureClockRateGammaScale:%s" % self.name})

            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRateGammaShapePrior.s:%s" % self.name, "name":"distribution", "x":"@featureClockRateGammaShape:%s" % self.name})
            exp = ET.SubElement(sub_prior, "Exponential", {"id":"featureClockRateGammaShapePriorExponential.s:%s" % self.name, "name":"distr"})
            param = ET.SubElement(exp, "parameter", {"id":"featureClockRateGammaShapePriorParam:%s" % self.name, "name":"mean", "lower":"0.0", "upper":"0.0"})
            param.text = "1.0"

    def add_likelihood(self, likelihood):
        """
        Add likelihood distribution corresponding to all features in the
        dataset.
        """
        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)
            attribs = {"id":"traitedtreeLikelihood:%s" % fname,"spec":"TreeLikelihood","useAmbiguities":"true"}
            if self.pruned:
                distribution = ET.SubElement(likelihood, "distribution",attribs)
                # Create pruned tree
                tree_id = "Tree.t:prunedBeastlingTree.%s" % fname
                tree = ET.SubElement(distribution, "tree", {"id":tree_id, "spec":"beast.evolution.tree.PrunedTree","quickshortcut":"true","assert":"false"})
                ET.SubElement(tree, "tree", {"idref":"Tree.t:beastlingTree"})
                ET.SubElement(tree, "alignment", {"idref":"%s.filt"%fname})
                # Create pruned branchrate
                self.clock.add_pruned_branchrate_model(distribution, fname, tree_id)
            else:
                attribs["branchRateModel"] = "@%s" % self.clock.branchrate_model_id
                attribs["tree"] = "@Tree.t:beastlingTree"
                distribution = ET.SubElement(likelihood, "distribution",attribs)

            # Sitemodel
            self.add_sitemodel(distribution, f, fname)

            # Data
            self.add_data(distribution, f, fname)

    def add_sitemodel(self, beast):
        pass

    def add_data(self, distribution, feature, fname):
        """
        Add <data> element corresponding to the indicated feature, descending
        from the indicated likelihood distribution.
        """
        if self.pruned:
            data = ET.SubElement(distribution,"data",{"id":"%s.filt" % fname, "spec":"PrunedAlignment"})
            source = ET.SubElement(data,"source",{"id":fname,"spec":"AlignmentFromTrait"})
            parent = source
        else:
            data = ET.SubElement(distribution,"data",{"id":fname, "spec":"AlignmentFromTrait"})
            parent = data
        traitset = ET.SubElement(parent, "traitSet", {"id":"traitSet.%s" % fname,"spec":"beast.evolution.tree.TraitSet","taxa":"@taxa","traitname":"discrete"})
        stringbits = []
        for lang in self.config.languages:
           if lang in self.data:
               stringbits.append("%s=%s," % (lang, self.data[lang][feature]))
           else:
               stringbits.append("%s=?," % lang)
        traitset.text = " ".join(stringbits)
        userdatatype = ET.SubElement(parent, "userDataType", {"id":"traitDataType.%s"%fname,"spec":"beast.evolution.datatype.UserDataType","codeMap":self.codemaps[feature],"codelength":"-1","states":str(self.valuecounts[feature])})

    def add_operators(self, run):
        """
        Add <operators> for individual feature substitution rates if rate
        variation is configured.
        """
        if self.rate_variation:
            delta = ET.SubElement(run, "operator", {"id":"featureClockRateDeltaExchanger:%s" % self.name, "spec":"DeltaExchangeOperator", "weight":"3.0"})
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                param = ET.SubElement(delta, "parameter", {"idref":"featureClockRate:%s" % fname})
            
            updown = ET.SubElement(run, "operator", {"id":"featureClockRateGammaUpDown:%s" % self.name, "spec":"UpDownOperator", "scaleFactor":"0.5","weight":"0.3"})
            ET.SubElement(updown, "parameter", {"idref":"featureClockRateGammaShape:%s" % self.name, "name":"up"})
            ET.SubElement(updown, "parameter", {"idref":"featureClockRateGammaScale:%s" % self.name, "name":"down"})

    def add_param_logs(self, logger):
        """
        Add entires to the logfile corresponding to individual feature
        substition rates if rate variation is configured.
        """
        if self.config.log_fine_probs:
            for n, f in enumerate(self.features):
                fname = "%s:%s" % (self.name, f)
                ET.SubElement(logger,"log",{"idref":"traitedtreeLikelihood:%s" % fname})
            if self.rate_variation:
                ET.SubElement(logger,"log",{"idref":"featureClockRatePrior.s:%s" % self.name})
                ET.SubElement(logger,"log",{"idref":"featureClockRateGammaShapePrior.s:%s" % self.name})

        if self.rate_variation:
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                ET.SubElement(logger,"log",{"idref":"featureClockRate:%s" % fname})
            # Log the shape, but not the scale, as it is always 1 / shape
            ET.SubElement(logger,"log",{"idref":"featureClockRateGammaShape:%s" % self.name})
