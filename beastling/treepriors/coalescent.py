import xml.etree.ElementTree as ET
from .base import TreePrior

class CoalescentTree (TreePrior):
    def __init__(self):
        super(CoalescentTree, self).__init__()
        self.type = "coalescent"

    def add_prior(self, beastxml):
        """Add a Yule tree prior."""
        coalescent = ET.SubElement(beastxml.prior, "distribution", {
            "id": "Coalescent.t:beastlingTree",
            "spec": "Coalescent",
            })
        popmod = ET.SubElement(coalescent, "populationModel", {
            "id": "ConstantPopulation:beastlingTree",
            "spec": "ConstantPopulation",
            })
        ET.SubElement(popmod, "parameter", {
            "idref": "popSize.t:beastlingTree",
            "name": "popSize",
            })
        ET.SubElement(coalescent, "treeIntervals", {
            "id": "TreeIntervals",
            "spec": "TreeIntervals",
            "tree": "@Tree.t:beastlingTree",
            })

