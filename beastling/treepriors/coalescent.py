from .base import TreePrior
from beastling.util import xml


class CoalescentTree (TreePrior):
    def __init__(self):
        super(CoalescentTree, self).__init__()
        self.type = "coalescent"

    def add_prior(self, beastxml):
        """Add a Yule tree prior."""
        coalescent = xml.distribution(
            beastxml.prior, id="Coalescent.t:beastlingTree", spec="Coalescent")
        popmod = xml.populationModel(
            coalescent, id="ConstantPopulation:beastlingTree", spec="ConstantPopulation")
        xml.parameter(popmod, idref="popSize.t:beastlingTree", name="popSize")
        xml.treeIntervals(
            coalescent, id="TreeIntervals", spec="TreeIntervals", tree="@Tree.t:beastlingTree")
