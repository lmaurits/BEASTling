import codecs
import os
import xml.etree.ElementTree as ET

import scipy.stats

from ..fileio.datareaders import load_data

class BaseModel:

    def __init__(self, model_config, global_config):

        self.config = global_config
        self.calibrations = global_config.calibrations

        self.name = model_config["name"] 
        self.data_filename = model_config["data"] 
        self.clock = model_config.get("clock", "clockRate")
        if "traits" in model_config:
            self.traits = model_config["traits"] 
        else:
            self.traits = "*"
        self.frequencies = model_config.get("frequencies", "empirical")
        self.pruned = model_config.get("pruned", False)
        self.rate_variation = model_config.get("rate_variation", False)
        self.remove_constant_traits = model_config.get("remove_constant_traits", True)

        self.data = load_data(self.data_filename)
        self.load_traits()
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
        self.traits = [t for t in self.traits if
                any([t in self.data[lang] for lang in self.data]
                    )]

        # Remove features which are in the config but are entirely
        # question marks for the specified languages
        self.traits = [t for t in self.traits if
                not all([self.data[lang][t] == "?" for lang in self.data]
                    )]

        self.valuecounts = {}
        self.counts = {}
        self.dimensions = {}
        self.codemaps = {}
        bad_traits = []
        for trait in self.traits:
            all_values = [self.data[l][trait] for l in self.data]
            all_values = [v for v in all_values if v != "?"]
            uniq = list(set(all_values))
            counts = {}
            for v in all_values:
                counts[v] = all_values.count(v)
            uniq = list(set(all_values))
            uniq.sort()
            if len(uniq) == 0 or (len(uniq) == 1 and self.remove_constant_traits):
                bad_traits.append(trait)
                continue
            N = len(uniq)

            self.valuecounts[trait] = N
            self.counts[trait] = counts
            self.dimensions[trait] = N*(N-1)/2
            self.codemaps[trait] = self.build_codemap(uniq)
        self.traits = [t for t in self.traits if t not in bad_traits]
        self.traits.sort()

    def load_traits(self):
        # Load traits to analyse
        if os.path.exists(self.traits):
            traits = []
            fp = codecs.open(self.traits, "r", "UTF-8")
            for line in fp:
                feature = line.strip()
                traits.append(feature)
        elif self.traits == "*":
            random_iso = self.data.keys()[0]
            traits = self.data[random_iso].keys()
            traits.remove("iso")
        else:
            traits = [t.strip() for t in self.traits.split(",")]
        self.traits = traits

    def add_misc(self, beast):
        pass

    def add_state(self, state):

        if self.rate_variation:
            # We need to add some trait-specific clock rates
            for trait in self.traits:
                traitname = "%s:%s" % (self.name, trait)

                attribs = {}
                attribs["id"] = "traitClockRate.c:%s" % traitname
                attribs["name"] = "stateNode"
                parameter = ET.SubElement(state, "parameter", attribs)
                parameter.text="1.0"
        else:
            pass

    def add_prior(self, prior):

        if self.rate_variation:
            for n, trait in enumerate(self.traits):
                traitname = "%s:%s" % (self.name, trait)

                # Clock
                sub_prior = ET.SubElement(prior, "prior", {"id":"geoclockPrior.s:%s" % traitname, "name":"distribution","x":"@traitClockRate.c:%s"% traitname})
                gamma  = ET.SubElement(sub_prior, "Gamma", {"id":"Gamma:%s.%d.1" % (traitname, n), "name":"distr"})
                param = ET.SubElement(gamma, "parameter", {"id":"RealParameter:%s.%d.3" % (traitname, n),"lower":"0.0","name":"alpha","upper":"0.0"})
                param.text = "0.001"
                param = ET.SubElement(gamma, "parameter", {"id":"RealParameter:%s.%d.4" % (traitname, n),"lower":"0.0","name":"beta","upper":"0.0"})
                param.text = "1000.0"

    def add_data(self, distribution, trait, traitname):
        # Data
        if self.pruned:
            data = ET.SubElement(distribution,"data",{"id":"%s.filt" % traitname, "spec":"PrunedAlignment"})
            source = ET.SubElement(data,"source",{"id":traitname,"spec":"AlignmentFromTrait"})
            parent = source
        else:
            data = ET.SubElement(distribution,"data",{"id":traitname, "spec":"AlignmentFromTrait"})
            parent = data
        traitset = ET.SubElement(parent, "traitSet", {"id":"traitSet.%s" % traitname,"spec":"beast.evolution.tree.TraitSet","taxa":"@taxa","traitname":"discrete"})
        stringbits = []
        for lang in self.config.languages:
           if lang in self.data:
               stringbits.append("%s=%s," % (lang, self.data[lang][trait]))
           else:
               stringbits.append("%s=?," % lang)
        traitset.text = " ".join(stringbits)
        userdatatype = ET.SubElement(parent, "userDataType", {"id":"traitDataType.%s"%traitname,"spec":"beast.evolution.datatype.UserDataType","codeMap":self.codemaps[trait],"codelength":"-1","states":str(self.valuecounts[trait])})


    def add_likelihood(self, likelihood):

        for n, trait in enumerate(self.traits):
            traitname = "%s:%s" % (self.name, trait)
            distribution = ET.SubElement(likelihood, "distribution",{"id":"traitedtreeLikelihood.%s" % traitname,"spec":"TreeLikelihood","useAmbiguities":"true"})

            # Tree
            if self.pruned:
                tree = ET.SubElement(distribution, "tree", {"id":"@Tree.t:beastlingTree.%s" % traitname, "spec":"beast.evolution.tree.PrunedTree","quickshortcut":"true","assert":"false"})
                ET.SubElement(tree, "tree", {"idref":"Tree.t:beastlingTree"})
                ET.SubElement(tree, "alignment", {"idref":"%s.filt"%traitname})
            else:
                tree = ET.SubElement(distribution, "tree", {"idref":"Tree.t:beastlingTree", "spec":"beast.evolution.tree.Tree"})

            # Sitemodel
            self.add_sitemodel(distribution, trait, traitname)

            # Branchrate
            if self.rate_variation:
                branchrate = ET.SubElement(distribution, "branchRateModel", {"id":"StrictClockModel.c:%s"%traitname,"spec":"beast.evolution.branchratemodel.StrictClockModel","clock.rate":"@traitClockRate.c:%s"%traitname})
            else:
                branchrate = ET.SubElement(distribution, "branchRateModel", {"id":"StrictClockModel.c:%s"%traitname,"spec":"beast.evolution.branchratemodel.StrictClockModel","clock.rate":"@clockRate_%s.c" % self.clock})
            
            # Data
            self.add_data(distribution, trait, traitname)

    def add_operators(self, run):

        # Updown for rate variation clocks
        # Note that this is not terribly sensible
        # There should not be separate up/downs for common and
        # r.v. clocks.  They should share an operator.
        # This requires some higher level tweaking
        if self.rate_variation:
            updown = ET.SubElement(run, "operator", {"id":"UpDownRV:%s" % self.name,"spec":"UpDownOperator","scaleFactor":"0.5", "weight":"30.0"})
            ET.SubElement(updown, "tree", {"idref":"Tree.t:beastlingTree", "name":"up"})
            if self.calibrations:
                ET.SubElement(updown, "parameter", {"idref":"birthRate.t:beastlingTree", "name":"down"})
            for trait in self.traits:
                traitname = "%s:%s" % (self.name, trait)
                ET.SubElement(updown, "parameter", {"idref":"traitClockRate.c:%s" % traitname, "name":"down"})
            for n, trait in enumerate(self.traits):
                traitname = "%s:%s" % (self.name, trait)
                ET.SubElement(run, "operator", {"id":"geoMuScaler.c:%s" % traitname, "spec":"ScaleOperator","parameter":"@traitClockRate.c:%s"%traitname, "scaleFactor":"1.0","weight":"10.0"})

    def add_param_logs(self, logger):
        if self.rate_variation:
            for trait in self.traits:
                traitname = "%s:%s" % (self.name, trait)
                ET.SubElement(logger,"log",{"idref":"traitClockRate.c:%s" % traitname})
