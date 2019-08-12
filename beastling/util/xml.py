import re
import functools
from xml.etree import ElementTree as ET

ElementTree = ET.ElementTree


def valid_id(s):
    return re.sub('\s+', '', s).replace(',', '_')


def _to_string(v, attrib=None):
    # Serialize boolean constants as expected by BEAST:
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    # Serialize range attributes for plate tags:
    if isinstance(v, (list, tuple)) and attrib == 'range':
        return ','.join('{0}'.format(vv) for vv in v)
    return '{0}'.format(v)


def comment(value):
    return ET.Comment(_to_string(value))


def _string_attrib(attrib):
    return {k: _to_string(v, k) for k, v in attrib.items()}


def _element(tag, **attrib):
    return ET.Element(tag, attrib=_string_attrib(attrib))

beast = functools.partial(_element, 'beast')


def _subelement(tag, parent, text=None, attrib=None, **kw):
    """
    Append a child element to parent.

    :param parent: The parent element.
    :param tag: The name of the new element.
    :param text: Text content of the new element.
    :param attrib: A dict containing attributes of the new element. Use this if attribute names are\
    not valid Python keyword parameter names, e.g. contain a ".".
    :param kw: Remaining keyword arguments are used as attributes of the new element.
    :return: The newly created element.
    """
    attrib = attrib or {}
    attrib.update(kw)
    if parent is None:
        e = ET.Element(tag, attrib=_string_attrib(attrib))
    else:
        e = ET.SubElement(parent, tag, attrib=_string_attrib(attrib))
    if text is not None:
        e.text = _to_string(text)
    return e


alignment = functools.partial(_subelement, 'alignment')
branchratemodel = functools.partial(_subelement, 'branchratemodel')  # FIXME: check!
branchRateModel = functools.partial(_subelement, 'branchRateModel')
data = functools.partial(_subelement, 'data')
dist = functools.partial(_subelement, 'dist')  # FIXME: Should this be distr?
distr = functools.partial(_subelement, 'distr')
distribution = functools.partial(_subelement, 'distribution')
Exponential = functools.partial(_subelement, 'Exponential')
frequencies = functools.partial(_subelement, 'frequencies')
Gamma = functools.partial(_subelement, 'Gamma')
geoprior = functools.partial(_subelement, 'geoprior')
init = functools.partial(_subelement, 'init')
input = functools.partial(_subelement, 'input')
log = functools.partial(_subelement, 'log')
logger = functools.partial(_subelement, 'logger')
LogNormal = functools.partial(_subelement, 'LogNormal')
map = functools.partial(_subelement, 'map')
mcmc = functools.partial(_subelement, 'mcmc')
metadata = functools.partial(_subelement, 'metadata')
multiGeoprior = functools.partial(_subelement, 'multiGeoprior')
Normal = functools.partial(_subelement, 'Normal')
operator = functools.partial(_subelement, 'operator')
parameter = functools.partial(_subelement, 'parameter')
plate = functools.partial(_subelement, 'plate')
populationModel = functools.partial(_subelement, 'populationModel')
popSize = functools.partial(_subelement, 'popSize')
prior = functools.partial(_subelement, 'prior')
region = functools.partial(_subelement, 'region')
run = functools.partial(_subelement, 'run')
sequence = functools.partial(_subelement, 'sequence')
siteModel = functools.partial(_subelement, 'siteModel')
source = functools.partial(_subelement, 'source')
state = functools.partial(_subelement, 'state')
stateNode = functools.partial(_subelement, 'stateNode')
substModel = functools.partial(_subelement, 'substModel')
tree = functools.partial(_subelement, 'tree')
treeIntervals = functools.partial(_subelement, 'treeIntervals')
taxon = functools.partial(_subelement, 'taxon')
taxonset = functools.partial(_subelement, 'taxonset')
trait = functools.partial(_subelement, 'trait')
traitMap = functools.partial(_subelement, 'traitMap')
Uniform = functools.partial(_subelement, 'Uniform')
userDataType = functools.partial(_subelement, 'userDataType')
var = functools.partial(_subelement, 'var')
vfrequencies = functools.partial(_subelement, 'vfrequencies')
weightvector = functools.partial(_subelement, 'weightvector')
x = functools.partial(_subelement, 'x')
