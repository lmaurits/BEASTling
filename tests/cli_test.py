import os
from pathlib import Path

import pytest

import beastling.cli
from beastling.cli import main
import beastling.__main__

# Now we must reset the `wrap_errors` global which was altered in __main__:
beastling.cli.wrap_errors = Exception


def _run_main(commandline='', status=0):
    with pytest.raises(SystemExit) as context:
        main(*commandline.split())
        assert context.code == status


def test_main(capsys):
    _run_main(status=2)


def test_help(capsys):
    _run_main('--help')
    out, err = capsys.readouterr()
    assert out.lower().startswith('usage:')


def test_extract_errors(capsys, tmppath):
    _run_main('--extract abcd cdef', status=1)
    out, err = capsys.readouterr()
    assert all(s in err for s in ['only', 'from', 'one'])

    _run_main('--extract abcd', status=2)
    out, err = capsys.readouterr()
    assert all(s in err for s in ['No', 'such', 'file'])

    xml = tmppath / 'test.xml'
    with xml.open('w') as fp:
        fp.write('<xml>')
    _run_main('--extract {0}'.format(str(xml)), status=3)
    out, err = capsys.readouterr()
    assert err.startswith('Error')


def test_generate_errors(capsys, bad_config_dir, config_dir, mocker):
    if 'TRAVIS' in os.environ:
        return
    _run_main('abcd', status=1)
    out, err = capsys.readouterr()
    assert all(s in err for s in ['No', 'such', 'file'])

    _run_main(str(bad_config_dir / 'no_data.conf'), status=2)

    mocker.patch('beastling.cli.BeastXml', mocker.Mock(side_effect=ValueError()))
    _run_main(str(config_dir / 'basic.conf'), status=3)


def test_generate_extract(capsys, tmppath, config_dir, caplog):
    xml = tmppath / 'test.xml'
    _run_main('-v -o {0} {1}'.format(xml, config_dir / 'basic.conf'))
    assert xml.exists()
    assert len([r for r in caplog.records if r.levelname == 'INFO']) > 0
    # Overwriting existing files must be specified explicitely:
    _run_main('-o {0} {1}'.format(xml, config_dir / 'basic.conf'), status=4)
    _run_main('--overwrite -o {0} {1}'.format(xml, config_dir / 'basic.conf'), status=0)
    tcfg = Path('beastling_test.conf')
    _run_main('--extract {0}'.format(xml))
    assert tcfg.exists()
    tcfg.unlink()
