import os
from subprocess import check_call, PIPE, CalledProcessError
from xml.etree import ElementTree as et

from clldutils.path import copytree
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest

import beastling.configuration
import beastling.beastxml
from .util import WithConfigAndTempDir, config_path, tests_path


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
        ("admin", "mk", "ancestral_state_reconstruction"),
        ("admin", "mk", "cldf_data_with_nonstandard_value_column"),
        ("admin", "mk"),
        ("admin", "cldf_data"),
        ("admin", "nonnumeric"),
        ("admin", "noncode"),
        ("admin", "bsvs"),
        ("admin", "covarion_multistate"),
        ("admin", "covarion_true_binary"),
        ("admin", "covarion_binarised"),
        ("admin", "bsvs", "robust_eigen"),
        ("admin", "covarion_multistate", "robust_eigen"),
        ("admin", "mk", "families"),
        ("admin", "mk", "features"),
        ("admin", "mk", "estimated_freqs"),
        ("admin", "bsvs", "estimated_freqs"),
        ("admin", "covarion_multistate", "estimated_freqs"),
        ("admin", "mk", "rate_var"),
        ("admin", "mk", "rate_var", "rate_var_user_rates"),
        ("admin", "mk", "monophyletic"),
        ("admin", "mk", "monophyletic-bottom-up"),
        ("admin", "mk", "monophyletic-partial"),
        ("admin", "mk", "no_screen_logging"),
        ("admin", "mk", "no_file_logging"),
        ("admin", "mk", "starting_tree"),
        ("admin", "mk", "starting_tree_with_internal_names"),
        ("admin", "mk", "monophyly_tree"),
        ("admin", "mk", "monophyly_tree_with_internal_names"),
        ("admin", "mk", "sample_prior"),
        ("admin", "mk", "union"),
        ("admin", "mk", "intersection"),
        ("admin", "mk", "relaxed"),
        ("admin", "mk", "relaxed_params"),
        ("admin", "mk", "relaxed_expon"),
        ("admin", "mk", "relaxed_gamma"),
        ("admin", "mk", "random"),
        ("admin", "mk", "feature_with_comma"),
        ("admin", "mk", "cldf_data_with_comma"),
        ("admin", "mk", "cldf_data_with_comma", "rate_var"),
        ("admin", "mk", "calibration"),
        ("admin", "mk", "calibration_by_iso"),
        ("admin", "mk", "calibration_nested"),
        ("admin", "mk", "calibration_disjoint"),
        ("admin", "mk", "calibration_nested_root"),
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
        ("admin", "mk", "calibration_tip"),
        ("admin", "mk", "calibration_tip_multiple"),
        ("admin", "mk", "calibration_tip_originate"),
        ("admin", "mk", "calibration_tip_fixed"),
        ("admin", "mk", "calibration_tip_before"),
        ("admin", "mk", "calibration_tip_after"),
        ("admin", "mk", "pruned"),
        ("admin", "mk", "pruned", "relaxed"),
        ("admin", "mk", "geo"),
        ("admin", "mk", "geo", "geo_user_loc"),
        ("admin", "mk", "geo_own_clock"),
        ("admin", "mk", "monophyletic", "geo", "geo_sampled"),
        ("admin", "mk", "monophyletic", "geo", "geo_prior"),
    ]:
        # To turn each config into a separate test, we
        yield _do_test, configs


skip = [
    ("admin", "mk", "cldf_data_with_comma", "rate_var"),
    # Beast interprets commas as separating alternative IDs (we
    # think), so identical text before the comma -- as happens for the
    # rate parameters in this test, because of the features' IDs --
    # leads to beast finding duplicate IDs and dying. This behaviour
    # is documented in the guidelines for IDs, but it would be nice to
    # get rid of it, either by not creating objects with commas in IDs
    # or by fixing beast not to split IDs.
    ]


def _do_test(config_files):
    config = TEST_CASE.make_cfg([config_path(cf).as_posix() for cf in config_files])
    xml = beastling.beastxml.BeastXml(config)
    temp_filename = TEST_CASE.tmp_path('test').as_posix()
    xml.write_file(temp_filename)
    if os.environ.get('TRAVIS'):
        et.parse(temp_filename)
    else:
        if not TEST_CASE.tmp_path('tests').exists():
            copytree(tests_path(), TEST_CASE.tmp_path('tests'))
        try:
            if config_files in skip:
                raise SkipTest
            check_call(
                ['beast', '-java', '-overwrite', temp_filename],
                cwd=TEST_CASE.tmp.as_posix(),
                stdout=PIPE,
                stderr=PIPE)
        except CalledProcessError as e:
            raise AssertionError(
                "Beast run on {:} returned non-zero exit status "
                "{:d}".format(
                    config_files, e.returncode))
