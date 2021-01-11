import os
from pathlib import Path
import shutil

import pytest

from beastling.configuration import Configuration


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


@pytest.fixture
def tests_dir(tmppath):
    # Data files etc. are all referenced by paths in tests/ relative to the repos root.
    # To prevent tests from littering cwd, we copy the tests/ directory to a temporary
    # location.
    shutil.copytree(str(Path(__file__).parent), str(tmppath / 'tests'))
    orig = os.getcwd()
    os.chdir(str(tmppath))
    yield tmppath / 'tests'
    os.chdir(orig)


@pytest.fixture
def data_dir(tests_dir):
    return tests_dir / 'data'


@pytest.fixture
def tree_dir(tests_dir):
    return tests_dir / 'trees'


@pytest.fixture
def config_dir(tests_dir):
    return tests_dir / 'configs'


@pytest.fixture
def bad_config_dir(tests_dir):
    return tests_dir / 'configs' / 'bad_configs'


@pytest.fixture
def config_factory(config_dir, bad_config_dir):
    def make_cfg(*configfiles, **kw):
        def path(name):
            if not name.endswith('.conf'):
                name += '.conf'
            res = config_dir / name
            if (not res.exists()) and (bad_config_dir / name).exists():
                return bad_config_dir / name
            return res

        if len(configfiles) == 1 and isinstance(configfiles[0], dict):
            # Configuration is passed as dict:
            configfiles = configfiles[0]
        else:
            configfiles = [str(path(n)) for n in configfiles]

        return Configuration(configfile=configfiles)
    return make_cfg
