# -*- encoding: utf-8 -*- 

"""Additional tests for the distribution module.

The beastling.distribution module contains doctests for core
functionality, but testing all bad paths would overload the docstring
with un-helpful examples, so they are delegated to here.

"""

import unittest
from nose.tools import raises

import beastling.distributions


class Tests(unittest.TestCase):
    @raises(ValueError)
    def run_with_string(self, string):
        print(string)
        beastling.distributions.parse_prior_string(
            string, string, is_point=True)

    def test_various(self):
        for string in [
                "0,, 1",
                " r_lognormal(1, 1)",
                "rlognormal(-1, 1)",
                "normal (1-5",
                "1 – 5",
                "1300>1200",
                ">12OO",
                ">1200,",
                "normal [1-5]",
                "300",
                "lognormal(1, 1) + 4"]:
            self.run_with_string.description = "Bad distribution {:}".format(
                string)
            yield self.run_with_string, string
