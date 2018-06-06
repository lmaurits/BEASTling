import sys

import xml.etree.ElementTree as ET

from ..distributions import Distribution
from .baseclock import BaseClock
from .strict import StrictClock


class RatePriorClock (BaseClock):
    # Class stub for putting priors on clock rates
    def __init__(self, clock_config, global_config):
        try:
            super().__init__(clock_config, global_config)
        except TypeError:
            # Python 2 has no argument-less super()
            super(RatePriorClock, self).__init__(clock_config, global_config)
        self.distribution = Distribution.from_string(
            clock_config.get(
                "rate", "lognormal(-6.9077552789821368, 2.3025850929940459)"),
            context="clock {:s}".format(self.name),
            is_point=True)
        self.initial_mean = self.distribution.mean()
        if clock_config.get(
                "estimate_rate", True) and self.distribution.dist == "point":
            self.distribution = Distribution(0, "uniform", (0, sys.maxsize))

    def add_prior(self, prior):
        # TODO: Lift some logic from beastxml.BeastXML.add_calibration
        # and surroundings to parse prior specifications.

        # Uniform prior on mean clock rate
        sub_prior = ET.SubElement(
            prior, "prior",
            {"id": "clockPrior:%s" % self.name,
             "name": "distribution",
             "x": "@clockRate.c:%s" % self.name})
        self.distribution.generate_xml_element(
            sub_prior)


class StrictClockWithPrior (RatePriorClock, StrictClock):
    pass
