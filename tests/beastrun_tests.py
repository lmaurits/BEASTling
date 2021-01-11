import os
import subprocess
from xml.etree import ElementTree as et
import shutil
import pathlib
import warnings

import pytest

import beastling.configuration
import beastling.beastxml

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


@pytest.mark.beast
@pytest.mark.parametrize(
    'configs,assertion',
    [
        (("admin", "mk", "subsample"), None),
        (("admin", "mk", "cldf_data_with_nonstandard_value_column"), None),
        (("admin", "mk"), None),
        (("admin", "mk", "birthdeath"), None),
        (("admin", "mk", "uniform_treeprior"), None),
        (("admin", "mk_as_if_addon"), None),
        (("admin", "cldf_data"), None),
        (("admin", "cldf1_wordlist"), None),
        (("admin", "cldf1_wordlist_with_lang_table"), None),
        (("admin", "cldf1_wordlist_external_codes"), None),
        (("admin", "cldf1_structure"), None),
        (("admin", "nonnumeric"), None),
        (("admin", "noncode"), None),
        (("admin", "bsvs"), None),
        (("admin", "mk", "strictclockwithprior"), None),
        (("admin", "binaryctmc"), None),
        (("admin", "binaryctmc", "gamma_categories"), None),
        (("admin", "binaryctmc", "estimated_freqs"), None),
        (("admin", "binaryctmc", "rate_var"), None),
        (("admin", "binaryctmc", "estimated_freqs", "rate_var"), None),
        (("admin", "covarion_multistate"), None),
        (("admin", "covarion_multistate", "covarion_per_feature_params"), None),
        (("admin", "covarion_multistate", "ascertainment_true"), None),
        (("admin", "covarion_multistate", "rate_var"), None),
        (("admin", "covarion_multistate", "estimated_freqs"), None),
        (("admin", "covarion_multistate", "do_not_share_params"), None),
        (("admin", "covarion_multistate", "estimated_freqs", "rate_var"), None),
        (("admin", "covarion_true_binary"), None),
        (("admin", "covarion_binarised"), None),
        (("admin", "bsvs", "robust_eigen"), None),
        (("admin", "covarion_multistate", "robust_eigen"), None),
        (("admin", "mk", "families"), None),
        (("admin", "mk", "features"), None),
        (("admin", "mk", "estimated_freqs"), None),
        (("admin", "mk", "approx_freqs"), None),
        (("admin", "mk", "uniform_freqs"), None),
        (("admin", "bsvs", "estimated_freqs"), None),
        (("admin", "covarion_multistate", "estimated_freqs"), None),
        (("admin", "mk", "rate_var"), None),
        (("admin", "mk", "rate_var", "rate_var_user_rates"), None),
        (("admin", "mk", "rate_var", "rate_partition"), None),
        (("admin", "mk", "rate_var", "rate_partition", "rate_partition_user_rates"), None),
        (("admin", "mk", "rate_partition", "rate_partition_user_rates"), None),
        (("admin", "mk", "monophyletic"), None),
        (("admin", "mk", "monophyletic-bottom-up"), None),
        (("admin", "mk", "monophyletic-partial"), None),
        (("admin", "mk", "no_screen_logging"), None),
        (("admin", "mk", "no_file_logging"), None),
        (("admin", "mk", "starting_tree"), None),
        (("admin", "mk", "starting_tree_with_internal_names"), None),
        (("admin", "mk", "monophyly_tree"), None),
        (("admin", "mk", "monophyly_tree_with_internal_names"), None),
        (("admin", "mk", "sample_prior"), None),
        (("admin", "mk", "union"), None),
        (("admin", "mk", "intersection"), None),
        (("admin", "mk", "relaxed"), None),
        (("admin", "mk", "relaxed_params"), None),
        (("admin", "mk", "relaxed_expon"), None),
        (("admin", "mk", "relaxed_gamma"), None),
        (("admin", "mk", "random"), None),
        (("admin", "mk", "feature_with_comma"), None),
        (("admin", "mk", "cldf_data_with_comma"), None),
        (("admin", "mk", "cldf_data_with_comma", "rate_var"), None),
        (("admin", "mk", "calibration"), None),
        (("admin", "mk", "calibration_by_iso"), None),
        (("admin", "mk", "calibration_nested"), None),
        (("admin", "mk", "calibration_disjoint"), None),
        (("admin", "mk", "calibration_nested_root"), None),
        # Test below has calibration on Austronesian, but macroareas=Africa,
        # resulting in an emtpy calibration, which is the point of the test
        (("admin", "mk", "calibration", "macroareas"), None),
        (("admin", "mk", "calibration_originate"), None),
        (("admin", "mk", "calibration_uniform_params"), None),
        (("admin", "mk", "calibration_normal_params"), None),
        (("admin", "mk", "calibration_lognormal_params"), None),
        (("admin", "mk", "calibration_upper_bound"), None),
        (("admin", "mk", "calibration_lower_bound"), None),
        (("admin", "mk", "calibration", "relaxed"), None),
        (("admin", "mk", "calibration", "random"), None),
        (("admin", "mk", "calibration", "monophyletic"), None),
        (("admin", "mk", "calibration_tip"), None),
        (("admin", "mk", "calibration_tip_multiple"), None),
        (("admin", "mk", "calibration_tip_originate_explicit"), None),
        (("admin", "mk", "calibration_tip_fixed"), None),
        (("admin", "mk", "calibration_tip_before"), None),
        (("admin", "mk", "calibration_tip_after"), None),
        (("admin", "mk", "calibration_tip_uniform"), None),
        (("admin", "mk", "pruned"), None),
        (("admin", "mk", "pruned", "relaxed"), None),
        (("admin", "mk", "geo"), None),
        (("admin", "mk", "geo", "geo_user_loc"), None),
        (("admin", "mk", "geo", "geo_sampled_tip"), None),
        (("admin", "mk", "geo", "geo_tip_prior"), None),
        (("admin", "mk", "geo_own_clock"), None),
        (("admin", "mk", "monophyletic", "geo", "geo_sampled"), None),
        (("admin", "mk", "monophyletic", "geo", "geo_prior"), None),
        (("admin", "covarion_multistate", "pseudodollocovarion"), None),
        (("admin", "covarion_multistate", "log_fine_probs", "pseudodollocovarion"), None),
        (("admin", "covarion_multistate", "covarion_per_feature_params", "pseudodollocovarion"), None),
        # Currently, Beast's pseudodollocovarion model does not support the
        # robust eigensystem implementation.
        # (("admin", "covarion_multistate", "robust_eigen", "pseudodollocovarion"), None),
        (("admin", "covarion_multistate", "pseudodollocovarion_fix_freq"), None),
        # Test that for 'log_fine_probs=True', probabilites are logged:
        (
                ("admin", "covarion_multistate", "log_fine_probs"),
                lambda dir: dir.joinpath("beastling_test.log").exists()),
        # Test the root ASR output.
        (
                ("admin", "mk", "ancestral_state_reconstruction", "ascertainment_false"),
                lambda dir: dir.joinpath("beastling_test_reconstructed.log").exists()),
        # Test the root ASR output under a binary (covarion) model.
        (
                ("admin", "covarion_multistate", "ancestral_state_reconstruction", "ascertainment_false"),
                lambda dir: dir.joinpath("beastling_test.log").exists()),
        # Test the root ASR output under a Mk model with ascertainment correction.
        (
                ("admin", "mk", "ancestral_state_reconstruction", "ascertainment_true"),
                lambda dir: dir.joinpath("beastling_test.log").exists()),
        # Test the root ASR output under a binary model with ascertainment correction.
        (
                ("admin", "covarion_multistate", "ancestral_state_reconstruction", "ascertainment_true"),
                lambda dir: dir.joinpath("beastling_test.log").exists()),
        # Test the full-tree ASR output.
        (
                ("admin", "mk", "ancestral_state_reconstruction", "taxa", "reconstruct_all"),
                lambda dir: dir.joinpath("beastling_test.log").exists()),
        # Test the clade ASR output.
        (
                ("admin", "mk", "ancestral_state_reconstruction", "taxa", "reconstruct_one"),
                lambda dir: dir.joinpath("beastling_test.log").exists()),

    ]
)
def test_beastrun(configs, assertion, config_factory, tmppath):
    """Turn each BEASTling config file in tests/configs into a
    BEAST.xml, and feed it to BEAST, testing for a zero return
    value, which suggests no deeply mangled XML."""
    if configs in skip:
        return

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        temp_filename = tmppath / 'test'
        xml = beastling.beastxml.BeastXml(config_factory(*configs), validate=False)
        xml.write_file(str(temp_filename))
        debug_copy = pathlib.Path('_test.xml')
        shutil.copy(str(temp_filename), str(debug_copy))
        xml.validate_ids()

        if os.environ.get('CI'):
            et.parse(str(temp_filename))
        else:
            # Data files etc. are all referenced by paths relative to the repos root.
            shutil.copytree(str(pathlib.Path(__file__).parent), str(tmppath / 'tests'))
            try:
                subprocess.check_call(
                    ['beast', '-java', '-overwrite', str(temp_filename)],
                    cwd=str(tmppath),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                raise AssertionError(
                    "Beast run on {:} returned non-zero exit status "
                    "{:d}".format(configs, e.returncode))
            if assertion:
                assert assertion(tmppath)
        if debug_copy.exists():
            debug_copy.unlink()
