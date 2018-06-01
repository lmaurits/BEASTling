import sys
import math
import collections

import xml.etree.ElementTree as ET


registered_distributions = (
    ("Beta", "beast.math.distributions.Beta"),
    ("Exponential", "beast.math.distributions.Exponential"),
    ("InverseGamma", "beast.math.distributions.InverseGamma"),
    ("LogNormal", "beast.math.distributions.LogNormalDistributionModel"),
    ("Gamma", "beast.math.distributions.Gamma"),
    ("Uniform", "beast.math.distributions.Uniform"),
    ("LaplaceDistribution", "beast.math.distributions.LaplaceDistribution"),
    ("OneOnX", "beast.math.distributions.OneOnX"),
    ("Normal", "beast.math.distributions.Normal"),
)


DISTRIBUTIONS = {"normal": ("Normal", ("mean", "sigma")),
                 "lognormal": ("LogNormal", ("M", "S")),
                 "uniform": ("Uniform", ("lower", "upper"))}


def add_prior_density_description(compound_distribution, distribution):
    """Create a distribution of the specified type inside an ET element.

    Create an ET sub-element describing a Beast real-parameter
    distribution inside the ET element `compound_distribution`
    reflecting the properties of `distribution`.

    Parameters
    ----------
    compound_distribution: ET.Element
        The xml tag to which the distribution should be added.
    distribution: configuration.Calibration-like
        A description of the distribution.
        Must have a the offset, dist and param attributes.

    Returns
    -------
    None

    Side Effects
    ------------
    Creates a sub-element in `compound_distribution`.
    May register distributions with global map list.

    """
    dist_type, ps = DISTRIBUTIONS[distribution.dist]
    attribs = {"id": "DistributionFor{:}".format(
        compound_distribution.attrib["id"]), "name": "distr", "offset": "0.0"}
    if distribution.offset:
        attribs["offset"] = str(distribution.offset)
    for parameter, value in zip(ps, distribution.param):
        attribs[parameter] = str(value)
    ET.SubElement(compound_distribution, dist_type, attribs)


def parse_prior_string(cs, prior_name="?", is_point=False):
    """Parse a prior-describing string.

    The basic format of such a string is [offset + ]distribution
    Offset is a number, distribution can describe a probability
    density function of normal, lognormal (including rlognormal, a
    reparametrization where the mean is given in real space, not
    in log space) or uniform type in one of the following
    ways. Pseudo-densities with infinite integral are permitted.
    
    Parameters separated using `,` are directly the parameters of the
    distribution. A range separated by a `-` gives the 95% interval of
    that distribution. (This behaviour may change in the future.)

    >>> parse = parse_prior_string
    >>> # Parameters of a normal distribution
    >>> parse("0, 1")
    (0.0, 'normal', (0.0, 1.0))
    >>> # Parameters of some other distribution
    >>> parse(" rlognormal(1, 1)")
    (0.0, 'lognormal', (0.0, 1.0))
    >>> # A distribution shape and its 95%-interval
    >>> parse("normal (1-5)")
    (0.0, 'normal', (3.0, 1.0204081632653061))
    >>> parse("1 - 5")
    (0.0, 'normal', (3.0, 1.0204081632653061))
    >>> parse(">1200")
    (0.0, 'uniform', (1200.0, 9223372036854775807))
    >>> parse("< 1200")
    (0.0, 'uniform', (0.0, 1200.0))

    All of these strings can also be used for point distributions

    >>> parse("normal (1-5)", is_point=True)
    (0.0, 'normal', (3.0, 1.0204081632653061))

    but in addition, point distributions support fixed values.

    >>> parse("300", is_point=True)
    (0.0, 'point', (300.0, 300.0))

    In some cases, in particular for lognormal distributions, it may
    be useful to specify an offset. This is possibly with the syntax

    >>> parse("4 + lognormal(1, 1)")
    (4.0, 'lognormal', (1.0, 1.0))

    The offset must appear *before* the distribution, the other order
    is not permitted.

    >>> parse("lognormal(1, 1) + 4") # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
        parse("lognormal(1, 1) + 4")
      File "beastling/distributions.py", line 148, in parse_prior_string
        offset = float(os.strip())
    ValueError: could not convert string to float: 'lognormal(1, 1)'

    Note
    ====

    For uniform distributions, "uniform(0-1) does not give the 95%
    interval, but the lower and upper bounds.

    While the ">1" and "<1" notations generate uniform
    distributions, the bare "0-1" notation generates a normal
    distribution.

    Parameters
    ==========
    cs: str
        A string describing a single-value probability distribution.
    name: str
        The name of the prior distribution, used only for error
        reporting purposes.
    is_point: bool
        defines whether the distribution is permitted to be a constant
        (point) distribution.

    Returns
    =======
    offset: int
    type: str
        A known distribution type
    parameters: tuple of floats
        The parameters for that distribution

    """
    orig_cs = cs[:]
    # Find offset
    if cs.count("+") == 1:
        os, dist = cs.split("+")
        offset = float(os.strip())
        cs = dist.strip()
    else:
        offset = 0.0

    # Parse distribution
    if cs.count("(") == 1 and cs.count(")") == 1:
        dist_type, cs = cs.split("(", 1)
        dist_type = dist_type.strip().lower()
        if dist_type not in ("uniform", "normal", "lognormal", "rlognormal"):
            raise ValueError(
                "Prior specification '{:}' for {:}"
                " uses an unknown distribution {:}!".format(
                    orig_cs, prior_name, dist_type))
        cs = cs[0:-1]
    else:
        # Default to normal
        dist_type = "normal"

    # Parse / infer params
    if cs.count(",") == 1 and not any([x in cs for x in ("<", ">")]):
        # We've got explicit params
        p1, p2 = map(float, cs.split(","))
    elif cs.count("-") == 1 and not any([x in cs for x in (",", "<", ">")]):
        # We've got a 95% HPD range
        lower, upper = map(float, cs.split("-"))
        if upper <= lower:
            raise ValueError(
                "Prior specification '{:}' for {:}"
                " has an upper bound {:}"
                " which is not higher than its lower bound {:}!".format(
                    orig_cs, prior_name, upper, lower))
        mid = (lower + upper) / 2.0
        if dist_type == "normal":
            p1 = (upper + lower) / 2.0
            p2 = (upper - mid) / 1.96
        elif dist_type == "lognormal":
            p1 = math.log(mid)
            p2a = (p1 - math.log(lower)) / 1.96
            p2b = (math.log(upper) - p1) / 1.96
            p2 = (p2a + p2b) / 2.0
        elif dist_type == "uniform":
            p1 = lower
            p2 = upper
    elif (cs.count("<") == 1 or cs.count(">") == 1) and not any(
            [x in cs for x in (",", "-")]):
        # We've got a single bound
        dist_type = "uniform"
        sign, bound = cs[0], cs[1:]
        if sign == "<":
            p1 = 0.0
            p2 = float(bound.strip())
        elif sign == ">":
            p1 = float(bound.strip())
            p2 = sys.maxsize
        else:
            raise ValueError(
                "Prior specification '{:}' for {:}"
                " cannot be parsed!".format(
                    orig_cs, prior_name))
    elif is_point:
        # Last chance: It's a single language pinned to a
        # single date, so make sure to pin it to that date
        # late and nothing else is left to do with this
        # prior specification.
        try:
            dist_type = "point"
            p1 = float(cs)
            p2 = p1
        except ValueError:
            raise ValueError(
                "Prior specification '{:}' for {:}"
                " cannot be parsed!".format(
                    orig_cs, prior_name))
    else:
        raise ValueError(
            "Prior specification '{:}' for {:}"
            " cannot be parsed!".format(
                orig_cs, prior_name))

    # If this is a lognormal prior specification with the mean in
    # realspace, adjust
    if dist_type == "rlognormal":
        p1 = math.log(p1)
        dist_type = "lognormal"

    # All done!
    return offset, dist_type, (p1, p2)


class Distribution(collections.namedtuple(
        "Distribution", ["offset", "dist", "param"])):
    @classmethod
    def from_string(cls, string, context=None, is_point=False, **kwargs):
        """Create a Distribution object from a prior description string.

        """
        offset, dist, param = parse_prior_string(
            cs=string, prior_name=context, is_point=is_point)
        return cls(offset=offset, dist=dist, param=param, **kwargs)

    def generate_xml_element(self, parent):
        add_prior_density_description(compound_distribution=parent,
                                      distribution=self)

    def mean(self):
        if self.dist in ("normal", "point"):
            return self.offset + self.param[0]
        elif self.dist == "lognormal":
            return self.offset + math.exp(self.param[0])
        elif self.dist == "uniform":
            return self.offset + sum(self.param) / 2.0
        else:
            raise NotImplementedError
