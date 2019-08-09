from configparser import ConfigParser

import pytest

from beastling.sections import Admin, MCMC, Languages


def _make_cfg(section, d):
    cfg = ConfigParser()
    cfg.read_dict({section: d})
    return cfg


def test_Admin():
    admin = Admin.from_config({}, 'admin', _make_cfg('admin', {}))
    assert admin.basename == 'beastling'

    admin = Admin.from_config({}, 'admin', _make_cfg('admin', {'basename': 'x'}))
    assert admin.basename == 'x'

    admin = Admin.from_config(
        {'prior': True}, 'admin', _make_cfg('admin', {'basename': 'x'}))
    assert admin.basename == 'x_prior'

    admin = Admin.from_config({}, 'admin', _make_cfg('admin', {}))
    assert admin.log_fine_probs == False

    admin = Admin.from_config({}, 'admin', _make_cfg('admin', {'log_all': 'true'}))
    assert admin.log_fine_probs == True


def test_MCMC():
    mcmc = MCMC.from_config({}, 'mcmc', _make_cfg('mcmc', {}))
    assert mcmc.log_burnin == 50


def test_Languages(tmppath):
    sec = Languages.from_config({}, 'languages', _make_cfg('languages', {}))
    assert sec.exclusions == []

    sec = Languages.from_config({}, 'languages', _make_cfg('languages', {'languages': 'a,b'}))
    assert sec.languages == ['a', 'b']

    langs = tmppath / 'languages.csv'
    langs.write_text('ä\nö\nü', encoding='utf8')
    sec = Languages.from_config({}, 'languages', _make_cfg('languages', {'languages': langs}))
    assert sec.languages == ['ä', 'ö', 'ü']

    with pytest.raises(ValueError):
        Languages.from_config({}, 'languages', _make_cfg('languages', {'starting_tree': 'a'}))

    tree = tmppath / 'tree.newick'
    tree.write_text('(a,b,(d,c))', encoding='utf8')
    sec = Languages.from_config(
        {}, 'languages', _make_cfg('languages', {'languages': 'a,b,c', 'starting_tree': tree}))
    assert sec.starting_tree == '(a,(c:0.0,b):0.0);'