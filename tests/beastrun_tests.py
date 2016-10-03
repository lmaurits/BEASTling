import os
from subprocess import check_call, PIPE
from xml.etree import ElementTree as et

from nose.plugins.attrib import attr

import beastling.configuration
import beastling.beastxml
from .util import WithConfigAndTempDir, config_path


# To reuse the setup/teardown functionality of WithConfigAndTempDir, we keep a module
# global instance of this class.
TEST_CASE = None


def setup():
    global TEST_CASE
    if TEST_CASE is None:
        TEST_CASE = WithConfigAndTempDir('setUp')
    TEST_CASE.setUp()


def teardown():
    TEST_CASE.tearDown()


@attr('with_beast')
def test_basic():
    """Turn each BEASTling config file in tests/configs into a
    BEAST.xml, and feed it to BEAST, testing for a zero return
    value, which suggests no deeply mangled XML."""
    for configs in [
        ("admin", "mk"),
        ("admin", "cldf_data"),
        ("admin", "nonnumeric"),
        ("admin", "noncode"),
        ("admin", "bsvs"),
        ("admin", "covarion"),
        ("admin", "mk", "families"),
        ("admin", "mk", "features"),
        ("admin", "mk", "monophyletic"),
        ("admin", "mk", "monophyletic-bottom-up"),
        ("admin", "mk", "monophyletic-partial"),
        ("admin", "mk", "no_screen_logging"),
        ("admin", "mk", "no_file_logging"),
        ("admin", "mk", "starting_tree"),
        ("admin", "mk", "sample_prior"),
        ("admin", "mk", "union"),
        ("admin", "mk", "intersection"),
        ("admin", "mk", "relaxed"),
        ("admin", "mk", "relaxed_expon"),
        ("admin", "mk", "relaxed_gamma"),
        ("admin", "mk", "random"),
        ("admin", "mk", "calibration"),
        # Test below has calibration on Austronesian, but macroareas=Africa,
        # resulting in an emtpy calibration, which is the point of the test
        ("admin", "mk", "calibration", "macroareas"),
        ("admin", "mk", "calibration_originate"),
        ("admin", "mk", "calibration_uniform_params"),
        ("admin", "mk", "calibration_normal_params"),
        ("admin", "mk", "calibration_lognormal_params"),
        ("admin", "mk", "calibration_upper_bound"),
        ("admin", "mk", "calibration_lower_bound"),
        ("admin", "mk", "calibration", "relaxed"),
        ("admin", "mk", "calibration", "random"),
        ("admin", "mk", "pruned"),
        ("admin", "mk", "pruned", "relaxed"),
        ("admin", "mk", "geo"),
        ("admin", "mk", "geo_own_clock"),
        ("admin", "mk", "geo", "geo_sampled"),
    ]:
        # To turn each config into a separate test, we
        yield _do_test, configs


def _do_test(config_files):
    config = TEST_CASE.make_cfg([config_path(cf).as_posix() for cf in config_files])
    xml = beastling.beastxml.BeastXml(config)
    temp_filename = TEST_CASE.tmp_path('test').as_posix()
    xml.write_file(temp_filename)
    if os.environ.get('TRAVIS'):
        et.parse(temp_filename)
    else:
        check_call(
            ['beast', '-overwrite', temp_filename],
            cwd=TEST_CASE.tmp.as_posix(),
            stdout=PIPE,
            stderr=PIPE)
