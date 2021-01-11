"""Additional tests for the distribution module.

The beastling.distribution module contains doctests for core
functionality, but testing all bad paths would overload the docstring
with un-helpful examples, so they are delegated to here.

"""
import pytest

import beastling.distributions


@pytest.mark.parametrize(
    'string',
    [
        "0,, 1",
        " r_lognormal(1, 1)",
        "rlognormal(-1, 1)",
        "normal (1-5",
        "1 – 5",
        "1300>1200",
        ">12OO",
        ">1200,",
        "normal [1-5]",
        "lognormal(1, 1) + 4",
    ]
)
def test_with_string(string):
    with pytest.raises(ValueError):
        beastling.distributions.parse_prior_string(string, string, is_point=True)
