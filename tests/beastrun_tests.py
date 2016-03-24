import glob
import os
import tempfile

from nose.tools import *

import beastling.configuration
import beastling.beastxml

test_files = []
temp_filename = None

def setup():
    global test_files, temp_filename
    test_files.extend(glob.glob("tests/configs/*.conf"))
    assert len(test_files)
    fp = tempfile.NamedTemporaryFile(mode="w", delete=False)
    temp_filename = fp.name
    fp.close()

def teardown():
    for ext in (".log", ".nex", ".state"):
        if os.path.exists(os.path.basename(temp_filename)+ext):
            os.unlink(os.path.basename(temp_filename)+ext)

def _do_test(*config_files):
    config_files = [os.path.join("tests/configs/",cf+".conf") for cf in config_files]
    config = beastling.configuration.Configuration(configfile=config_files)
    xml = beastling.beastxml.BeastXml(config)
    xml.write_file(temp_filename)
    ret = os.system("beast -java -overwrite %s" % temp_filename)
    assert ret == 0

def test_beastrun():
    """Turn each BEASTling config file in tests/configs into a
    BEAST.xml, and feed it to BEAST, testing for a zero return
    value, which suggests no deeply mangled XML."""
    _do_test("admin", "mk")
    _do_test("admin", "mk", "embed_data")
    _do_test("admin", "cldf_data")
    _do_test("admin", "bsvs")
    _do_test("admin", "covarion")
    _do_test("admin", "mk", "families")
    _do_test("admin", "mk", "features")
    _do_test("admin", "mk", "monophyletic")
    _do_test("admin", "mk", "monophyletic-bottom-up")
    _do_test("admin", "mk", "monophyletic-partial")
    _do_test("admin", "mk", "no_screen_logging")
    _do_test("admin", "mk", "no_file_logging")
    _do_test("admin", "mk", "starting_tree")
    _do_test("admin", "mk", "sample_prior")
    _do_test("admin", "mk", "union")
    _do_test("admin", "mk", "intersection")
    _do_test("admin", "mk", "relaxed")
    _do_test("admin", "mk", "random")
    _do_test("admin", "mk", "calibration")
    _do_test("admin", "mk", "calibration", "relaxed")
    _do_test("admin", "mk", "calibration", "random")
    _do_test("admin", "mk", "pruned")
    _do_test("admin", "mk", "pruned", "relaxed")
    _do_test("admin", "mk", "geo")
    _do_test("admin", "mk", "geo_own_clock")
