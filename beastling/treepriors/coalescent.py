from .base import TreePrior
from beastling.util import xml


class CoalescentTree (TreePrior):
    def add_prior(self, beastxml):
        """Add a Yule tree prior."""
        coalescent = xml.distribution(
            beastxml.prior, id="Coalescent.t:beastlingTree", spec="Coalescent")
        popmod = xml.populationModel(
            coalescent, id="ConstantPopulation:beastlingTree", spec="ConstantPopulation")
        xml.parameter(popmod, idref="popSize.t:beastlingTree", name="popSize")
        xml.treeIntervals(
            coalescent, id="TreeIntervals", spec="TreeIntervals", tree="@Tree.t:beastlingTree")

    def add_operators(self, beastxml):
        xml.operator(
            beastxml.run,
            id="PopulationSizeScaler.t:beastlingTree",
            spec="ScaleOperator",
            parameter="@popSize.t:beastlingTree",
            scaleFactor="0.5",
            weight="3.0")

    def add_fine_logging(self, tracer_logger):
        xml.log(tracer_logger, idref="popSize.t:beastlingTree")

    def add_state_nodes(self, beastxml):
        super().add_state_nodes(beastxml)
        xml.parameter(
            beastxml.state, text="1.0", id="popSize.t:beastlingTree", name="stateNode")
