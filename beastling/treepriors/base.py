import typing as t
from abc import ABC, abstractmethod

from math import log

from beastling.util import xml


class TreePrior (ABC):
    tree_id = "Tree.t:beastlingTree"

    def __init__(self):
        # Define loggable states, together with a log level
        # TODO: This is not yet used at all.
        self.loggables = set()

    def add_state_nodes(self, beastxml):
        """
        Add tree-related <state> sub-elements.
        """
        state = beastxml.state
        self.tree = xml.tree(state, id=self.tree_id, name="stateNode")
        xml.taxonset(self.tree, idref="taxa")
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
                                         * (log(len(config.config.languages.languages))
                                            + 0.5772156649 - 1), 4)

    def add_tip_heights(self, tip_calibrations):
        """Add the <trait> element for tip dates to self.treeheight

        Take the tip calibrations passed and add a tree <trait> which
        represents the ages of the tips, in arbitrary (but consistent) time
        units befor a reference date, eg. BP.

        """
        if tip_calibrations:
            string_bits = []
            for cal in tip_calibrations.values():
                initial_height = cal.mean()
                string_bits.append("{:s} = {:}".format(next(cal.langs.__iter__()), initial_height))
            xml.trait(
                self.tree,
                text=",\n".join(string_bits),
                id="datetrait",
                spec="beast.evolution.tree.TraitSet",
                taxa="@taxa",
                traitname="date-backward")

    def add_init(self, beastxml):
        """
        Add the <init> element for the tree.
        """
        # If a starting tree is specified, use it...
        if beastxml.config.languages.starting_tree:
            beastxml.init = xml.init(
                beastxml.run,
                estimate="false",
                id="startingTree",
                initial="@Tree.t:beastlingTree",
                spec="beast.util.TreeParser",
                IsLabelledNewick="true",
                newick=beastxml.config.languages.starting_tree)
        # ...if not, use the simplest random tree initialiser possible
        else:
            # If we have non-trivial monophyly constraints, use ConstrainedRandomTree
            if beastxml.config.languages.monophyly and len(beastxml.config.languages.languages) > 2:
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
        beastxml.init = xml.init(beastxml.run, attrib=attribs)
        popmod = xml.populationModel(beastxml.init, spec="ConstantPopulation")
        xml.popSize(popmod, spec="parameter.RealParameter", value="1")

    def add_simplerandomtree_init(self, beastxml):
        attribs = {"estimate":"false", "id":"startingTree", "initial":"@Tree.t:beastlingTree", "taxonset":"@taxa", "spec":"beast.evolution.tree.SimpleRandomTree"}
        if self.birthrate_estimate is not None:
            attribs["rootHeight"] = str(self.treeheight_estimate)
        beastxml.init = xml.init(beastxml.run, attrib=attribs)

    def add_constrainedrandomtree_init(self, beastxml):
        attribs = {"estimate":"false", "id":"startingTree", "initial":"@Tree.t:beastlingTree", "taxonset":"@taxa", "spec":"beast.evolution.tree.ConstrainedRandomTree", "constraints":"@constraints"}
        if self.birthrate_estimate is not None:
            attribs["rootHeight"] = str(self.treeheight_estimate)
        beastxml.init = xml.init(beastxml.run, attrib=attribs)
        popmod = xml.populationModel(beastxml.init, spec="ConstantPopulation")
        xml.popSize(popmod, spec="parameter.RealParameter", value="1")

    @abstractmethod
    def add_prior(self, beastxml):
        ...

    def add_operators(self, beastxml):
        """
        Add all <operator>s which act on the tree topology and branch lengths.
        """
        # Tree operators
        # Operators which affect the tree must respect the sample_topology and
        # sample_branch_length options.
        if beastxml.config.languages.sample_topology:
            ## Tree topology operators
            xml.operator(beastxml.run, attrib={"id":"SubtreeSlide.t:beastlingTree","spec":"SubtreeSlide","tree":"@Tree.t:beastlingTree","markclades":"true", "weight":"15.0"})
            xml.operator(beastxml.run, attrib={"id":"narrow.t:beastlingTree","spec":"Exchange","tree":"@Tree.t:beastlingTree","markclades":"true", "weight":"15.0"})
            xml.operator(beastxml.run, attrib={"id":"wide.t:beastlingTree","isNarrow":"false","spec":"Exchange","tree":"@Tree.t:beastlingTree","markclades":"true", "weight":"3.0"})
            xml.operator(beastxml.run, attrib={"id":"WilsonBalding.t:beastlingTree","spec":"WilsonBalding","tree":"@Tree.t:beastlingTree","markclades":"true","weight":"3.0"})
        if beastxml.config.languages.sample_branch_lengths:
            ## Branch length operators
            xml.operator(beastxml.run, attrib={"id":"UniformOperator.t:beastlingTree","spec":"Uniform","tree":"@Tree.t:beastlingTree","weight":"30.0"})
            xml.operator(beastxml.run, attrib={"id":"treeScaler.t:beastlingTree","scaleFactor":"0.5","spec":"ScaleOperator","tree":"@Tree.t:beastlingTree","weight":"3.0"})
            xml.operator(beastxml.run, attrib={"id":"treeRootScaler.t:beastlingTree","scaleFactor":"0.5","spec":"ScaleOperator","tree":"@Tree.t:beastlingTree","rootOnly":"true","weight":"3.0"})
            ## Up/down operator which scales tree height

        # Add a Tip Date scaling operator if required
        if beastxml.config.tip_calibrations and beastxml.config.languages.sample_branch_lengths:
            # Get a list of taxa with non-point tip cals
            tip_taxa = [next(cal.langs.__iter__()) for cal in beastxml.config.tip_calibrations.values() if cal.dist != "point"]
            for taxon in tip_taxa:
                tiprandomwalker = xml.operator(
                    beastxml.run,
                    attrib={"id": "TipDatesandomWalker:%s" % taxon,
                     "spec": "TipDatesRandomWalker",
                     "windowSize": "1",
                     "tree": "@Tree.t:beastlingTree",
                     "weight": "3.0",
                     })
                beastxml.add_taxon_set(tiprandomwalker, taxon, (taxon,))

    def add_logging(self, beastxml, tracer_logger):
        # Log tree height
        if not beastxml.config.tree_logging_pointless:
            xml.log(
                tracer_logger,
                id="treeStats",
                spec="beast.evolution.tree.TreeStatLogger",
                tree="@Tree.t:beastlingTree")

        # Fine-grained logging
        if beastxml.config.admin.log_params:
            self.add_fine_logging(tracer_logger)

    @abstractmethod
    def add_fine_logging(self, tracer_logger):
        pass


class YuleTree (TreePrior):
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
        xml.distribution(beastxml.prior, attrib=attribs)

        # Birth rate prior
        sub_prior = xml.prior(
            beastxml.prior,
            id="YuleBirthRatePrior.t:beastlingTree",
            name="distribution",
            x="@birthRate.t:beastlingTree")
        xml.Uniform(sub_prior, id="Uniform.0", name="distr", upper="Infinity")

    def add_fine_logging(self, tracer_logger):
        # Log tree model parameters
        xml.log(tracer_logger, idref="birthRate.t:beastlingTree")
        xml.log(tracer_logger, idref="YuleModel.t:beastlingTree")
        xml.log(tracer_logger, idref="YuleBirthRatePrior.t:beastlingTree")

    def add_state_nodes(self, beastxml):
        """
        Add tree-related <state> sub-elements.
        """
        super().add_state_nodes(beastxml)
        state = beastxml.state
        param = xml.parameter(state, id="birthRate.t:beastlingTree", name="stateNode")
        if self.birthrate_estimate is not None:
            param.text=str(self.birthrate_estimate)
        else:
            param.text="1.0"

    def add_operators(self, beastxml):
        super().add_operators(beastxml)
        if beastxml.config.languages.sample_branch_lengths:
            updown = xml.operator(
                beastxml.run,
                attrib={
                    "id": "UpDown",
                    "spec": "UpDownOperator",
                    "scaleFactor": "0.5",
                    "weight": "3.0"})
            xml.tree(updown, idref="Tree.t:beastlingTree", name="up")
            xml.parameter(updown, idref="birthRate.t:beastlingTree", name="down")
            ### Include clock rates in up/down only if calibrations are given
            if beastxml.config.calibrations:
                for clock in beastxml.config.clocks:
                    if clock.estimate_rate:
                        xml.parameter(updown, idref=clock.mean_rate_id, name="down")

        # Birth rate scaler
        # Birth rate is *always* scaled.
        xml.operator(
            beastxml.run,
            attrib={"id": "YuleBirthRateScaler.t:beastlingTree",
                    "spec": "ScaleOperator",
                    "parameter": "@birthRate.t:beastlingTree",
                    "scaleFactor": "0.5",
                    "weight": "3.0"})

    def add_logging(self, beastxml, tracer_logger):
        super().add_logging(beastxml, tracer_logger)
        xml.log(
            tracer_logger,
            idref="birthRate.t:beastlingTree")


class BirthDeathTree (TreePrior):
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
        attribs["type"] = "unscaled" #TODO: Someone dropped the "restricted" type here, which does not exist.
        xml.distribution(beastxml.prior, attrib=attribs)

        # Birth rate prior
        attribs = {}
        attribs["id"] = "BirthRatePrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@birthRate.t:beastlingTree"
        sub_prior = xml.prior(beastxml.prior, attrib=attribs)
        xml.Uniform(sub_prior, id="Uniform.0", name="distr", upper="Infinity")

        # Relative death rate prior
        attribs = {}
        attribs["id"] = "relativeDeathRatePrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@deathRate.t:beastlingTree"
        sub_prior = xml.prior(beastxml.prior, attrib=attribs)
        xml.Uniform(sub_prior, id="Uniform.1", name="distr", upper="Infinity")

        # Sample probability prior
        attribs = {}
        attribs["id"] = "samplingPrior.t:beastlingTree"
        attribs["name"] = "distribution"
        attribs["x"] = "@sampling.t:beastlingTree"
        sub_prior = xml.prior(beastxml.prior, attrib=attribs)
        xml.Uniform(sub_prior, id="Uniform.3", name="distr", lower="0", upper="1")

    def add_state_nodes(self, beastxml):
        """
        Add tree-related <state> sub-elements.
        """
        super().add_state_nodes(beastxml)
        state = beastxml.state
        param = xml.parameter(state, id="birthRate.t:beastlingTree", name="stateNode")
        if self.birthrate_estimate is not None:
            param.text = str(self.birthrate_estimate)
        else:
            param.text = "1.0"
        xml.parameter(
            beastxml.state,
            text="0.5",
            id="deathRate.t:beastlingTree",
            name="stateNode")
        xml.parameter(
            beastxml.state,
            text="0.2",
            id="sampling.t:beastlingTree",
            name="stateNode")

    def add_operators(self, beastxml):
        if beastxml.config.languages.sample_branch_lengths:
            updown = xml.operator(
                beastxml.run,
                attrib={
                    "id": "UpDown",
                    "spec": "UpDownOperator",
                    "scaleFactor": "0.5",
                    "weight": "3.0"})
            xml.tree(updown, idref="Tree.t:beastlingTree", name="up")
            xml.parameter(updown, idref="birthRate.t:beastlingTree", name="down")
            ### Include clock rates in up/down only if calibrations are given
            if beastxml.config.calibrations:
                for clock in beastxml.config.clocks:
                    if clock.estimate_rate:
                        xml.parameter(updown, idref=clock.mean_rate_id, name="down")

        # Birth rate scaler
        # Birth rate is *always* scaled.
        xml.operator(
            beastxml.run,
            attrib={
                "id": "YuleBirthRateScaler.t:beastlingTree",
                "spec": "ScaleOperator",
                "parameter": "@birthRate.t:beastlingTree",
                "scaleFactor": "0.5",
                "weight": "3.0"})
        xml.operator(
            beastxml.run,
            attrib={
                "id": "SamplingScaler.t:beastlingTree",
                "spec": "ScaleOperator",
                "parameter": "@sampling.t:beastlingTree",
                "scaleFactor": "0.8",
                "weight": "1.0"})
        xml.operator(
            beastxml.run,
            attrib={
                "id": "DeathRateScaler.t:beastlingTree",
                "spec": "ScaleOperator",
                "parameter": "@deathRate.t:beastlingTree",
                "scaleFactor": "0.5",
                "weight": "3.0"})

    def add_fine_logging(self, tracer_logger):
        # Log tree model parameters
        xml.log(tracer_logger, idref="birthRate.t:beastlingTree")
        xml.log(tracer_logger, idref="deathRate.t:beastlingTree")
        xml.log(tracer_logger, idref="sampling.t:beastlingTree")


class UniformTree (TreePrior):
    def add_prior(self, beastxml):
        """Add nothing.

        For a uniform tree prior, all trees have the same probability, so the
        tree prior can remain implicit and unspecified.

        """
        pass

    def add_fine_logging(self, tracer_logger):
        """Add nothing.

        For a uniform tree prior, there are no parameters to log.

        """
