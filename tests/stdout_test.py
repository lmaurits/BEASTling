import beastling.beastxml
import beastling.configuration


def test_stdout(capsys, config_factory, tmppath):
    xml = beastling.beastxml.BeastXml(config_factory('basic'))
    xml.write_file(tmppath / 'test.xml')
    out, _ = capsys.readouterr()
    assert '<?xml version=', out
