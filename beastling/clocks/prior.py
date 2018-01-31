import xml.etree.ElementTree as ET

from .baseclock import BaseClock
from .strict import StrictClock


class RatePriorClock (BaseClock):
    # Class stub for putting priors on clock rates
    def __init__(self, clock_config, global_config):
        super().__init__(clock_config, global_config)
        self.prior = clock_config.get(
            "prior", "lognormal(-6.9077552789821368, 2.3025850929940459)")
        self.initial_mean = 1e-3

    def add_prior(self, prior):
        # TODO: Lift some logic from beastxml.BeastXML.add_calibration
        # and surroundings to parse prior specifications.

        # Uniform prior on mean clock rate
        sub_prior = ET.SubElement(
            prior, "prior",
            {"id": "clockPrior:%s" % self.name,
             "name": "distribution",
             "x": "@clockRate.c:%s" % self.name})
        ET.SubElement(
            sub_prior, "LogNormal",
            {"id": "UniformClockPrior:%s" % self.name,
             "name": "distr",
             "M": "-6.9077552789821368",
             "S": "2.3025850929940459"})


class StrictClockWithPrior (RatePriorClock, StrictClock):
    pass
