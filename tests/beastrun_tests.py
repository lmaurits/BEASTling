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
        ("admin", "mk", "subsample"),
        ("admin", "mk", "cldf_data_with_nonstandard_value_column"),
        ("admin", "mk"),
        ("admin", "mk_as_if_addon"),
        ("admin", "cldf_data"),
        ("admin", "cldf1_wordlist"),
        ("admin", "cldf1_wordlist_external_codes"),
        ("admin", "cldf1_structure"),
        ("admin", "nonnumeric"),
        ("admin", "noncode"),
        ("admin", "bsvs"),
        ("admin", "mk", "strictclockwithprior"),
        ("admin", "covarion_multistate"),
        ("admin", "covarion_multistate", "covarion_per_feature_params"),
        ("admin", "covarion_multistate", "ascertainment_true"),
        ("admin", "covarion_multistate", "rate_var"),
        ("admin", "covarion_multistate", "estimated_freqs"),
        ("admin", "covarion_true_binary"),
        ("admin", "covarion_binarised"),
        ("admin", "bsvs", "robust_eigen"),
        ("admin", "covarion_multistate", "robust_eigen"),
        ("admin", "mk", "families"),
        ("admin", "mk", "features"),
        ("admin", "mk", "estimated_freqs"),
        ("admin", "mk", "approx_freqs"),
        ("admin", "mk", "uniform_freqs"),
        ("admin", "bsvs", "estimated_freqs"),
        ("admin", "covarion_multistate", "estimated_freqs"),
        ("admin", "mk", "rate_var"),
        ("admin", "mk", "rate_var", "rate_var_user_rates"),
        ("admin", "mk", "rate_var", "rate_partition"),
        ("admin", "mk", "rate_var", "rate_partition", "rate_partition_user_rates"),
        ("admin", "mk", "rate_partition", "rate_partition_user_rates"),
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
        ("admin", "mk", "calibration", "monophyletic"),
        ("admin", "mk", "calibration_tip"),
        ("admin", "mk", "calibration_tip_multiple"),
        ("admin", "mk", "calibration_tip_originate_explicit"),
        ("admin", "mk", "calibration_tip_fixed"),
        ("admin", "mk", "calibration_tip_before"),
        ("admin", "mk", "calibration_tip_after"),
        ("admin", "mk", "calibration_tip_uniform"),
        ("admin", "mk", "pruned"),
        ("admin", "mk", "pruned", "relaxed"),
        ("admin", "mk", "geo"),
        ("admin", "mk", "geo", "geo_user_loc"),
        ("admin", "mk", "geo", "geo_sampled_tip"),
        ("admin", "mk", "geo", "geo_tip_prior"),
        ("admin", "mk", "geo_own_clock"),
        ("admin", "mk", "monophyletic", "geo", "geo_sampled"),
        ("admin", "mk", "monophyletic", "geo", "geo_prior"),
        ("admin", "covarion_multistate", "pseudodollocovarion"),
        ("admin", "covarion_multistate", "log_fine_probs",
         "pseudodollocovarion"),
        ("admin", "covarion_multistate", "covarion_per_feature_params",
         "pseudodollocovarion"),
        # Currently, Beast's pseudodollocovarion model does not support the
        # robust eigensystem implementation.
        # ("admin", "covarion_multistate", "robust_eigen",
        #  "pseudodollocovarion"),
        ("admin", "covarion_multistate", "pseudodollocovarion_fix_freq"),
    ]:
        # To turn each config into a separate test, we
        _do_test.description = "BeastRun with " + " ".join(configs)
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


def _do_test(config_files, inspector=None):
    configs = [config_path(cf).as_posix() for cf in config_files]
    config = TEST_CASE.make_cfg(configs)
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
        if inspector:
            inspector(TEST_CASE.tmp)


def test_fine_probabilites_are_logged():
    """Test that for 'log_fine_probs=True', probabilites are logged."""
    def assert_fine_probs(dir):
        assert dir.joinpath("beastling_test.log").exists()
    _do_test((
        "admin", "covarion_multistate", "log_fine_probs"
    ), inspector=assert_fine_probs)


def test_asr_root_output_files():
    """Test the root ASR output.

    Generate a Beast config file for ASR at the root and run Beast. Check that
    beast returns a `0` return value, and check some properties of the data
    generated.

    """
    def assert_asr_logfile(dir):
        assert dir.joinpath("beastling_test_reconstructed.log").exists()
    _do_test((
        "admin", "mk", "ancestral_state_reconstruction", "ascertainment_false"
    ), inspector=assert_asr_logfile)


def test_asr_binary_root_output_files():
    """Test the root ASR output under a binary (covarion) model.

    Generate a Beast config file for ASR at the root and run Beast. Check that
    beast returns a `0` return value, and check some properties of the data
    generated.

    """
    def assert_asr_logfile(dir):
        assert dir.joinpath("beastling_test_reconstructed.log").exists()
    _do_test((
        "admin", "covarion_multistate", "ancestral_state_reconstruction", "ascertainment_false"
    ), inspector=assert_asr_logfile)


def test_ascertained_asr_root_output_files():
    """Test the root ASR output under a Mk model with ascertainment correction.

    Generate a Beast config file for ASR at the root and run Beast. Check that
    beast returns a `0` return value, and check some properties of the data
    generated.

    """
    def assert_asr_logfile(dir):
        assert dir.joinpath("beastling_test_reconstructed.log").exists()
    _do_test((
        "admin", "mk", "ancestral_state_reconstruction", "ascertainment_true"
    ), inspector=assert_asr_logfile)


def test_ascertained_asr_binary_root_output_files():
    """Test the root ASR output under a binary model with ascertainment correction.

    Generate a Beast config file for ASR at the root and run Beast. Check that
    beast returns a `0` return value, and check some properties of the data
    generated.

    """
    def assert_asr_logfile(dir):
        assert dir.joinpath("beastling_test_reconstructed.log").exists()
    _do_test((
        "admin", "covarion_multistate", "ancestral_state_reconstruction", "ascertainment_true"
    ), inspector=assert_asr_logfile)


def test_asr_tree_output():
    """Test the full-tree ASR output.

    Generate a Beast config file for ASR in every node of the tree and run
    Beast. Check that beast returns a `0` return value, and check some
    properties of the data generated.

    """
    def assert_asr_logfile(dir):
        assert dir.joinpath("beastling_test_reconstructed.nex").exists()
    _do_test(("admin", "mk", "ancestral_state_reconstruction", "taxa", "reconstruct_all"), inspector=assert_asr_logfile)


def test_asr_clade_output():
    """Test the clade ASR output.

    Generate a Beast config file for ASR at the MRCA of a taxonset and run
    Beast. Check that beast returns a `0` return value, and check some
    properties of the data generated.

    """
    def assert_asr_logfile(dir):
        assert dir.joinpath("beastling_test_reconstructed.log").exists()
    _do_test(("admin", "mk", "ancestral_state_reconstruction", "taxa", "reconstruct_one"), inspector=assert_asr_logfile)


