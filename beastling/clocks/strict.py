from .baseclock import BaseClock
from beastling.util import xml


class StrictClock(BaseClock):
    __type__ = 'strict'

    def __init__(self, clock_config, global_config):

        BaseClock.__init__(self, clock_config, global_config)
        self.branchrate_model_id = "StrictClockModel.c:%s" % self.name
        self.is_strict = True
        self.branchrate = None

    def add_branchrate_model(self, beast):
        xml.branchRateModel(
            beast,
            id="StrictClockModel.c:%s" % self.name,
            spec="beast.evolution.branchratemodel.StrictClockModel",
            attrib={"clock.rate":"@clockRate.c:%s" % self.name})

    def add_pruned_branchrate_model(self, distribution, name, tree_id):
        # For StrictClocks, it's safe to just reuse the global branchRateModel
        self.branchrate = xml.branchRateModel(distribution, idref=self.branchrate_model_id)
