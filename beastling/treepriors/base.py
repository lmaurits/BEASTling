# -*- encoding: utf-8 -*-
import xml.etree.ElementTree as ET
from math import log, exp

class TreePrior (object):
    tree_id = "Tree.t:beastlingTree"
    type = None

    def __init__(self):
        pass

    def add_state_nodes(self, beastxml):
        """
        Add tree-related <state> sub-elements.
        """
        state = beastxml.state
        self.tree = ET.SubElement(state, "tree", {"id": self.tree_id, "name": "stateNode"})
        ET.SubElement(self.tree, "taxonset", {"idref": "taxa"})
        if self.type in ["yule", "birthdeath"]:
            param = ET.SubElement(state, "parameter", {"id":"birthRate.t:beastlingTree","name":"stateNode"})
            if self.birthrate_estimate is not None:
                param.text=str(self.birthrate_estimate)
            else:
                param.text="1.0"
            if self.type in ["birthdeath"]:
                ET.SubElement(beastxml.state, "parameter",
                              {"id": "deathRate.t:beastlingTree",
                               "name": "stateNode"}).text = "0.5"
                ET.SubElement(beastxml.state, "parameter",
                              {"id": "sampling.t:beastlingTree",
                               "name": "stateNode"}).text = "0.2"

        elif self.type == "coalescent":
            param = ET.SubElement(beastxml.state, "parameter", {"id":"popSize.t:beastlingTree","name":"stateNode"})
            param.text="1.0"
        if beastxml.config.tip_calibrations:
            self.add_tip_heights(beastxml.config.tip_calibrations)

    def estimate_height(self, config):
        birthrate_estimates = []
        for cal in config.config.calibrations.values():
            if len(cal.langs) == 1 or cal.dist not in ("normal", "lognormal"):
                continue
            # Find the midpoint of this cal
            mid = cal.mean()
            # Find the Yule birthrate which results in an expected height for
            # a tree of this many taxa which equals the midpoint of the
            # calibration.
            # The expected height of a Yule tree with n taxa and
            # birthrate λ is 1/λ * (Hn - 1), where Hn is the nth
            # harmonic number.  Hn can be asymptotically approximated
            # by Hn = log(n) + 0.5772156649. So λ = (Hn - 1) / h.
            birthrate = (log(len(cal.langs)) + 0.5772156649 - 1) / mid
            birthrate_estimates.append(birthrate)
        # If there were no calibrations that could be used, return a non-esitmate
        if not birthrate_estimates:
            self.birthrate_estimate = None
            self.treeheight_estimate = None
            return
        # Find the mean birthrate estimate
        self.birthrate_estimate = round(sum(birthrate_estimates) / len(birthrate_estimates), 4)
        # Find the expected height of a tree with this birthrate
        self.treeheight_estimate = round((1.0 / self.birthrate_estimate)
                                         * (log(len(config.config.languages))
                                            + 0.5772156649 - 1), 4)

    def add_tip_heights(self, tip_calibrations):
        """Add the <trait> element for tip dates to self.treeheight

        Take the tip calibrations passed and add a tree <trait> which
        represents the ages of the tips, in arbitrary (but consistent) time
        units befor a reference date, eg. BP.

        """
        if not tip_calibrations:
            return
        string_bits = []
        for cal in tip_calibrations.values():
            initial_height = cal.mean()
            string_bits.append("{:s} = {:}".format(next(cal.langs.__iter__()), initial_height))
        trait_string = ",\n".join(string_bits)

        datetrait = ET.SubElement(self.tree, "trait",
                      {"id": "datetrait",
                       "spec": "beast.evolution.tree.TraitSet",
                       "taxa": "@taxa",
                       "traitname": "date-backward"})
        datetrait.text = trait_string

    def add_init(self, beastxml):
        """
        Add the <init> element for the tree.
        """
        # If a starting tree is specified, use it...
        if beastxml.config.starting_tree:
            beastxml.init = ET.SubElement(beastxml.run, "init", {"estimate":"false", "id":"startingTree", "initial":"@Tree.t:beastlingTree", "spec":"beast.util.TreeParser","IsLabelledNewick":"true", "newick":beastxml.config.starting_tree})
        # ...if not, use the simplest random tree initialiser possible
        else:
            # If we have non-trivial monophyly constraints, use ConstrainedRandomTree
            if beastxml.config.monophyly and len(beastxml.config.languages) > 2:
                self.add_constrainedrandomtree_init(beastxml)
            # If we have hard-bound calibrations, use SimpleRandomTree
            elif any([c.dist == "uniform" for c in beastxml.config.calibrations.values()]):
                self.add_simplerandomtree_init(beastxml)
            # Otherwise, just use RandomTree
            else:
                self.add_randomtree_init(beastxml)

    def add_randomtree_init(self, beastxml):
        attribs = {"estimate":"false", "id":"startingTree", "initial":"@Tree.t:beastlingTree", "taxonset":"@taxa", "spec":"beast.evolution.tree.RandomTree"}
        if self.birthrate_estimate is not None:
            attribs["rootHeight"] = str(self.treeheight_estimate)
        beastxml.init = ET.SubElement(beastxml.run, "init", attribs)
        popmod = ET.SubElement(beastxml.init, "populationModel", {"spec":"ConstantPopulation"})
        ET.SubElement(popmod, "popSize", {"spec":"parameter.RealParameter","value":"1"})

    def add_simplerandomtree_init(self, beastxml):
        attribs = {"estimate":"false", "id":"startingTree", "initial":"@Tree.t:beastlingTree", "taxonset":"@taxa", "spec":"beast.evolution.tree.SimpleRandomTree"}
        if self.birthrate_estimate is not None:
            attribs["rootHeight"] = str(self.treeheight_estimate)
        beastxml.init = ET.SubElement(beastxml.run, "init", attribs)

    def add_constrainedrandomtree_init(self, beastxml):
        attribs = {"estimate":"false", "id":"startingTree", "initial":"@Tree.t:beastlingTree", "taxonset":"@taxa", "spec":"beast.evolution.tree.ConstrainedRandomTree", "constraints":"@constraints"}
        if self.birthrate_estimate is not None:
            attribs["rootHeight"] = str(self.treeheight_estimate)
        beastxml.init = ET.SubElement(beastxml.run, "init", attribs)
        popmod = ET.SubElement(beastxml.init, "populationModel", {"spec":"ConstantPopulation"})
        ET.SubElement(popmod, "popSize", {"spec":"parameter.RealParameter","value":"1"})

    def add_prior(self, beastxml):
        raise ValueError("Tree prior {:} is unknown.".format(
            self.type))

    def add_operators(self, beastxml):
        """
        Add all <operator>s which act on the tree topology and branch lengths.
        """
        """
        Add all <operator>s which act on the tree topology and branch lengths.
        """
        # Tree operators
        # Operators which affect the tree must respect the sample_topology and
        # sample_branch_length options.
        if beastxml.config.sample_topology:
            ## Tree topology operators
            ET.SubElement(beastxml.run, "operator", {"id":"SubtreeSlide.t:beastlingTree","spec":"SubtreeSlide","tree":"@Tree.t:beastlingTree","markclades":"true", "weight":"15.0"})
            ET.SubElement(beastxml.run, "operator", {"id":"narrow.t:beastlingTree","spec":"Exchange","tree":"@Tree.t:beastlingTree","markclades":"true", "weight":"15.0"})
            ET.SubElement(beastxml.run, "operator", {"id":"wide.t:beastlingTree","isNarrow":"false","spec":"Exchange","tree":"@Tree.t:beastlingTree","markclades":"true", "weight":"3.0"})
            ET.SubElement(beastxml.run, "operator", {"id":"WilsonBalding.t:beastlingTree","spec":"WilsonBalding","tree":"@Tree.t:beastlingTree","markclades":"true","weight":"3.0"})
        if beastxml.config.sample_branch_lengths:
            ## Branch length operators
            ET.SubElement(beastxml.run, "operator", {"id":"UniformOperator.t:beastlingTree","spec":"Uniform","tree":"@Tree.t:beastlingTree","weight":"30.0"})
            ET.SubElement(beastxml.run, "operator", {"id":"treeScaler.t:beastlingTree","scaleFactor":"0.5","spec":"ScaleOperator","tree":"@Tree.t:beastlingTree","weight":"3.0"})
            ET.SubElement(beastxml.run, "operator", {"id":"treeRootScaler.t:beastlingTree","scaleFactor":"0.5","spec":"ScaleOperator","tree":"@Tree.t:beastlingTree","rootOnly":"true","weight":"3.0"})
            ## Up/down operator which scales tree height
            if self.type in ["yule", "birthdeath"]:
                updown = ET.SubElement(beastxml.run, "operator", {"id":"UpDown","spec":"UpDownOperator","scaleFactor":"0.5", "weight":"3.0"})
                ET.SubElement(updown, "tree", {"idref":"Tree.t:beastlingTree", "name":"up"})
                ET.SubElement(updown, "parameter", {"idref":"birthRate.t:beastlingTree", "name":"down"})
                ### Include clock rates in up/down only if calibrations are given
                if beastxml.config.calibrations:
                    for clock in beastxml.config.clocks:
                        if clock.estimate_rate:
                            ET.SubElement(updown, "parameter", {"idref":clock.mean_rate_id, "name":"down"})

        if self.type in ["yule", "birthdeath"]:
            # Birth rate scaler
            # Birth rate is *always* scaled.
            ET.SubElement(beastxml.run, "operator", {"id":"YuleBirthRateScaler.t:beastlingTree","spec":"ScaleOperator","parameter":"@birthRate.t:beastlingTree", "scaleFactor":"0.5", "weight":"3.0"})
        elif self.type == "coalescent":
            ET.SubElement(beastxml.run, "operator", {"id":"PopulationSizeScaler.t:beastlingTree","spec":"ScaleOperator","parameter":"@popSize.t:beastlingTree", "scaleFactor":"0.5", "weight":"3.0"})

        if self.type in ["birthdeath"]:
            ET.SubElement(beastxml.run, "operator",
                          {"id": "SamplingScaler.t:beastlingTree",
                           "spec": "ScaleOperator",
                           "parameter": "@sampling.t:beastlingTree",
                           "scaleFactor": "0.8",
                           "weight": "1.0"})
            ET.SubElement(beastxml.run, "operator",
                          {"id": "DeathRateScaler.t:beastlingTree",
                           "spec": "ScaleOperator",
                           "parameter": "@deathRate.t:beastlingTree",
                           "scaleFactor": "0.5",
                           "weight": "3.0"})
 
        # Add a Tip Date scaling operator if required
        if beastxml.config.tip_calibrations and beastxml.config.sample_branch_lengths:
            # Get a list of taxa with non-point tip cals
            tip_taxa = [next(cal.langs.__iter__()) for cal in beastxml.config.tip_calibrations.values() if cal.dist != "point"]
            for taxon in tip_taxa:
                tiprandomwalker = ET.SubElement(beastxml.run, "operator",
                    {"id": "TipDatesandomWalker:%s" % taxon,
                     "spec": "TipDatesRandomWalker",
                     "windowSize": "1",
                     "tree": "@Tree.t:beastlingTree",
                     "weight": "3.0",
                     })
                beastxml.add_taxon_set(tiprandomwalker, taxon, (taxon,))

    def add_logging(self, beastxml, tracer_logger):
        if self.type in ["yule", "birthdeath"]:
            ET.SubElement(tracer_logger,"log",{"idref":"birthRate.t:beastlingTree"})
            if self.type in ["birthdeath"]:
                ET.SubElement(tracer_logger, "log",
                                {"idref": "deathRate.t:beastlingTree"})
                ET.SubElement(tracer_logger, "log",
                                {"idref": "sampling.t:beastlingTree"})
        elif self.type == "coalescent":
            ET.SubElement(tracer_logger,"log",{"idref":"popSize.t:beastlingTree"})

        if self.type == "yule":
            ET.SubElement(tracer_logger,"log",{"idref":"birthRate.t:beastlingTree"})
        elif self.type == "coalescent":
            ET.SubElement(tracer_logger,"log",{"idref":"popSize.t:beastlingTree"})

        # Log tree height
        if not beastxml.config.tree_logging_pointless:
            ET.SubElement(tracer_logger,"log",{
                "id":"treeStats",
                "spec":"beast.evolution.tree.TreeStatLogger",
                "tree":"@Tree.t:beastlingTree"})

        # Fine-grained logging
        if beastxml.config.log_fine_probs:
            ET.SubElement(tracer_logger,"log",{"idref":"YuleModel.t:beastlingTree"})
            ET.SubElement(tracer_logger,"log",{"idref":"YuleBirthRatePrior.t:beastlingTree"})


class YuleTree (TreePrior):
    def __init__(self):
        super(YuleTree, self).__init__()
        self.type = "yule"

    def add_prior(self, beastxml):
        """
        Add Yule birth-process tree prior.
        """
        # Tree prior
        ## Decide whether to use the standard Yule or the fancy calibrated one
        if len(beastxml.config.calibrations) == 1:
            yule = "calibrated"
        elif len(beastxml.config.calibrations) == 2:
            # Two calibrations can be handled by the calibrated Yule if they
            # are nested
            langs1, langs2 = [c.langs for c in beastxml.config.calibrations.values()]
            if len(set(langs1) & set(langs2)) in (len(langs1), len(langs2)):
                yule = "calibrated"
            else:
                yule = "standard"
        else:
            yule = "standard"

        attribs = {}
        attribs["id"] = "YuleModel.t:beastlingTree"
        attribs["tree"] = "@Tree.t:beastlingTree"
        if yule == "standard":
            attribs["spec"] = "beast.evolution.speciation.YuleModel"
            attribs["birthDiffRate"] = "@birthRate.t:beastlingTree"
            if "root" in beastxml.config.calibrations:
                attribs["conditionalOnRoot"] = "true"
        elif yule == "calibrated":
            attribs["spec"] = "beast.evolution.speciation.CalibratedYuleModel"
            attribs["birthRate"] = "@birthRate.t:beastlingTree"
        ET.SubElement(beastxml.prior, "distribution", attribs)

        # Birth rate prior
        attribs = {}
        attribs["id"] = "YuleBirthRatePrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@birthRate.t:beastlingTree"
        sub_prior = ET.SubElement(beastxml.prior, "prior", attribs)
        uniform = ET.SubElement(sub_prior, "Uniform", {"id":"Uniform.0","name":"distr","upper":"Infinity"})


class BirthDeathTree (TreePrior):
    def __init__(self):
        super(BirthDeathTree, self).__init__()
        self.type = "birthdeath"

    def add_prior(self, beastxml):
        """Add a (calibrated) birth-death tree prior."""
        # Tree prior

        attribs = {}
        attribs["id"] = "BirthDeathModel.t:beastlingTree"
        attribs["tree"] = "@Tree.t:beastlingTree"
        attribs["spec"] = "beast.evolution.speciation.BirthDeathGernhard08Model"
        attribs["birthDiffRate"] = "@birthRate.t:beastlingTree"
        attribs["relativeDeathRate"] = "@deathRate.t:beastlingTree"
        attribs["sampleProbability"] = "@sampling.t:beastlingTree"
        attribs["type"] = "unscaled" # Is this right?
        ET.SubElement(beastxml.prior, "distribution", attribs)

        # Birth rate prior
        attribs = {}
        attribs["id"] = "BirthRatePrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@birthRate.t:beastlingTree"
        sub_prior = ET.SubElement(beastxml.prior, "prior", attribs)
        uniform = ET.SubElement(sub_prior, "Uniform",
                                {"id": "Uniform.0",
                                 "name": "distr",
                                 "upper": "Infinity"})

        # Relative death rate prior
        attribs = {}
        attribs["id"] = "relativeDeathRatePrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@deathRate.t:beastlingTree"
        sub_prior = ET.SubElement(beastxml.prior, "prior", attribs)
        uniform = ET.SubElement(sub_prior, "Uniform",
                                {"id": "Uniform.1",
                                 "name": "distr",
                                 "upper": "Infinity"})

        # Sample probability prior
        attribs = {}
        attribs["id"] = "samplingPrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@sampling.t:beastlingTree"
        sub_prior = ET.SubElement(beastxml.prior, "prior", attribs)
        uniform = ET.SubElement(sub_prior, "Uniform",
                                {"id": "Uniform.3",
                                 "name": "distr",
                                 "lower": "0",
                                 "upper": "1"})


class UniformTree (TreePrior):
    def __init__(self):
        super(UniformTree, self).__init__()
        self.type = "uniform"

    def add_prior(self, beastxml):
        """Add nothing.

        For a uniform tree prior, all trees have the same probability, so the
        tree prior can remain implicit and unspecified.

        """
        pass
