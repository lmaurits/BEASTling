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
    os.remove(temp_filename)
    os.remove(os.path.basename(temp_filename)+".state")

def test_basic():
    """Turn each BEASTling config file in tests/configs into a
    BEAST.xml, and feed it to BEAST, testing for a zero return
    value, which suggests no deeply mangled XML."""
    for test_file in test_files:
        config = beastling.configuration.Configuration(configfile=test_file)
        xml = beastling.beastxml.BeastXml(config)
        xml.write_file(temp_filename)
        ret = os.system("beast -overwrite %s" % temp_filename)
        assert ret == 0
