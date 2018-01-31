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
    DISTRIBUTIONS = {"normal": ("Normal", ("mean", "sigma")),
                     "lognormal": ("LogNormal", ("M", "S")),
                     "uniform": ("Uniform", ("lower", "upper"))}
    dist_type, ps = DISTRIBUTIONS[distribution.dist]
    attribs = {"id": "DistributionFor{:}".format(
        compound_distribution.attrib["id"]), "name": "distr", "offset": "0.0"}
    if distribution.offset:
        attribs["offset"] = str(distribution.offset)
    for parameter, value in zip(ps, distribution.param):
        attribs[parameter] = str(value)
    ET.SubElement(compound_distribution, dist_type, attribs)
