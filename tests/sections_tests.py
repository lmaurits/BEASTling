from configparser import ConfigParser

from beastling.sections import Admin


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
