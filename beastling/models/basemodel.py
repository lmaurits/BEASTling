import codecs
import os
import xml.etree.ElementTree as ET

import scipy.stats

from ..fileio.datareaders import load_data, _language_column_names

class BaseModel:

    def __init__(self, model_config, global_config):

        self.messages = []
        self.config = global_config
        self.calibrations = global_config.calibrations

        self.name = model_config["name"] 
        self.data_filename = model_config["data"] 
        if "features" in model_config:
            self.features = model_config["features"] 
        else:
            self.features = "*"
        self.constant_feature = False
        self.frequencies = model_config.get("frequencies", "empirical")
        self.pruned = model_config.get("pruned", False)
        self.rate_variation = model_config.get("rate_variation", False)
        self.remove_constant_features = model_config.get("remove_constant_features", True)
        self.lang_column = model_config.get("language_column", None)

        self.data = load_data(self.data_filename, file_format=model_config.get("file_format",None), lang_column=model_config.get("language_column",None))
        self.load_features()
        self.preprocess()

    def build_codemap(self, unique_values):
        N = len(unique_values)
        codemapbits = []
        codemapbits.append(",".join(["%s=%d" % (v,n) for (n,v) in enumerate(unique_values)]))
        codemapbits.append("?=" + " ".join([str(n) for n in range(0,N)]))
        codemapbits.append("-=" + " ".join([str(n) for n in range(0,N)]))
        return ",".join(codemapbits)

    def preprocess(self):

        # Remove features which are in the config but not the
        # data file
        self.features = [f for f in self.features if
                any([f in self.data[lang] for lang in self.data]
                    )]

        self.valuecounts = {}
        self.counts = {}
        self.dimensions = {}
        self.codemaps = {}
        bad_feats = []
        for f in self.features:
            all_values = [self.data[l][f] for l in self.data]
            all_values = [v for v in all_values if v != "?"]
            uniq = list(set(all_values))
            counts = {}
            for v in all_values:
                counts[v] = all_values.count(v)
            uniq = list(set(all_values))
            # Sort uniq carefully.
            # Possibly all feature values are numeric strings, e.g. "1", "2", "3".
            # If we sort these as strings then we get weird things like "10" < "2".
            # This can actually matter for things like ordinal models.
            # So convert these to ints first...
            if all([v.isdigit() for v in uniq]):
                uniq = map(int, uniq)
                uniq.sort()
                uniq = map(str, uniq)
            # ...otherwise, just sort normally
            else:
                uniq.sort()
            if len(uniq) == 0:
                self.messages.append("""[INFO] Model "%s": Feature %s excluded because there are no datapoints for selected languages.""" % (self.name, f))
                bad_feats.append(f)
                continue
            if len(uniq) == 1:
                if self.remove_constant_features:
                    self.messages.append("""[INFO] Model "%s": Feature %s excluded because its value is constant across selected languages.  Set "remove_constant_features=False" in config to stop this.""" % (self.name, f))
                    bad_feats.append(f)
                    continue
                else:
                    self.constant_feature = True
            N = len(uniq)

            self.valuecounts[f] = N
            self.counts[f] = counts
            self.dimensions[f] = N*(N-1)/2
            self.codemaps[f] = self.build_codemap(uniq)
        self.features = [f for f in self.features if f not in bad_feats]
        self.features.sort()
        self.messages.append("""[INFO] Model "%s": Using %d features from data source %s""" % (self.name, len(self.features), self.data_filename))
        if self.constant_feature and self.rate_variation:
            self.messages.append("""[WARNING] Model "%s": Rate variation enabled with constant features retained in data.  This may skew rate estimates for non-constant features.""" % self.name)
        if self.pruned:
            self.messages.append("""[DEPENDENCY] Model %s: Pruned trees are implemented in the BEAST package "BEASTlabs".""" % self.name)

    def load_features(self):
        # Load features to analyse
        if os.path.exists(self.features):
            features = []
            fp = codecs.open(self.features, "r", "UTF-8")
            for line in fp:
                feature = line.strip()
                features.append(feature)
        elif self.features == "*":
            random_iso = self.data.keys()[0]
            features = self.data[random_iso].keys()
            # Need to remove the languge ID column
            if self.lang_column:
                features.remove(self.lang_column)
            else:
                # If no language column name was explicitly given, just
                # remove the first of the automatically-recognised names
                # which we encounter:
                for lc in _language_column_names:
                    if lc in features:
                        features.remove(lc)
                        break
        else:
            features = [f.strip() for f in self.features.split(",")]
        self.features = features

    def add_misc(self, beast):
        pass

    def add_state(self, state):

        # Clock
        attribs = {}
        attribs["id"] = "clockRate.c:%s" % self.name
        attribs["name"] = "stateNode"
        parameter = ET.SubElement(state, "parameter", attribs)
        parameter.text="1.0"

        # Mutation rates
        if self.rate_variation:
            for f in self.features:
                fname = "%s:%s" % (self.name, f)

                attribs = {}
                attribs["id"] = "featureClockRate:%s" % fname
                attribs["name"] = "stateNode"
                parameter = ET.SubElement(state, "parameter", attribs)
                parameter.text="1.0"
            parameter = ET.SubElement(state, "parameter", {"id":"featureClockRateGammaShape:%s" % self.name, "name":"stateNode"})
            parameter.text="2.0"

    def add_prior(self, prior):

        # Clock
        sub_prior = ET.SubElement(prior, "prior", {"id":"clockPrior:%s" % self.name, "name":"distribution","x":"@clockRate.c:%s" % self.name})
        uniform = ET.SubElement(sub_prior, "Uniform", {"id":"UniformClockPrior:%s" % self.name, "name":"distr", "upper":"Infinity"})

        # Mutation rates
        if self.rate_variation:
            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRatePrior.s:%s" % self.name, "name":"distribution"})
            compound = ET.SubElement(sub_prior, "input", {"id":"featureClockRateCompound:%s" % self.name, "spec":"beast.core.parameter.CompoundValuable", "name":"x"})
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                var = ET.SubElement(compound, "var", {"idref":"featureClockRate:%s" % fname})
            gamma  = ET.SubElement(sub_prior, "input", {"id":"featureClockRatePriorGamma:%s" % self.name, "spec":"beast.math.distributions.SingleParamGamma", "name":"distr", "alpha":"@featureClockRateGammaShape:%s" % self.name})

            sub_prior = ET.SubElement(prior, "prior", {"id":"featureClockRateGammaShapePrior.s:%s" % self.name, "name":"distribution", "x":"@featureClockRateGammaShape:%s" % self.name})
            exp = ET.SubElement(sub_prior, "Exponential", {"id":"featureClockRateGammaShapePriorExponential.s:%s" % self.name, "name":"distr"})
            param = ET.SubElement(exp, "parameter", {"id":"featureClockRateGammaShapePriorParam:%s" % self.name, "name":"mean", "lower":"0.0", "upper":"0.0"})
            param.text = "1.0"

    def add_data(self, distribution, feature, fname):
        # Data
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


    def add_likelihood(self, likelihood):

        for n, f in enumerate(self.features):
            fname = "%s:%s" % (self.name, f)
            distribution = ET.SubElement(likelihood, "distribution",{"id":"traitedtreeLikelihood.%s" % fname,"spec":"TreeLikelihood","useAmbiguities":"true"})

            # Tree
            if self.pruned:
                tree = ET.SubElement(distribution, "tree", {"id":"@Tree.t:beastlingTree.%s" % fname, "spec":"beast.evolution.tree.PrunedTree","quickshortcut":"true","assert":"false"})
                ET.SubElement(tree, "tree", {"idref":"Tree.t:beastlingTree"})
                ET.SubElement(tree, "alignment", {"idref":"%s.filt"%fname})
            else:
                tree = ET.SubElement(distribution, "tree", {"idref":"Tree.t:beastlingTree", "spec":"beast.evolution.tree.Tree"})

            # Sitemodel
            self.add_sitemodel(distribution, f, fname)

            # Branchrate
            branchrate = ET.SubElement(distribution, "branchRateModel", {"id":"StrictClockModel.c:%s"%fname,"spec":"beast.evolution.branchratemodel.StrictClockModel","clock.rate":"@clockRate.c:%s" % self.name})
            
            # Data
            self.add_data(distribution, f, fname)

    def add_operators(self, run):

        # Clock scaler (only if tree is not free to vary arbitrarily)
        if not self.config.sample_branch_lengths or self.calibrations:
            ET.SubElement(run, "operator", {"id":"clockScaler.c:%s" % self.name, "spec":"ScaleOperator","parameter":"@clockRate.c:%s" % self.name, "scaleFactor":"1.0","weight":"3.0"})

        # Mutation rates
        if self.rate_variation:
            delta = ET.SubElement(run, "operator", {"id":"featureClockRateDeltaExchanger:%s" % self.name, "spec":"DeltaExchangeOperator", "weight":"3.0"})
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                param = ET.SubElement(delta, "parameter", {"idref":"featureClockRate:%s" % fname})
            
            ET.SubElement(run, "operator", {"id":"featureClockRateGammaShapeScaler:%s" % self.name, "spec":"ScaleOperator","parameter":"@featureClockRateGammaShape:%s" % self.name, "scaleFactor":"1.0","weight":"0.1"})

    def add_param_logs(self, logger):

        # Clock
        ET.SubElement(logger,"log",{"idref":"clockRate.c:%s" % self.name})

        # Mutation rates
        if self.rate_variation:
            for f in self.features:
                fname = "%s:%s" % (self.name, f)
                ET.SubElement(logger,"log",{"idref":"featureClockRate:%s" % fname})
            ET.SubElement(logger,"log",{"idref":"featureClockRateGammaShape:%s" % self.name})
