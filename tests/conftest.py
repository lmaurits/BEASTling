from pathlib import Path

import pytest

from beastling.configuration import Configuration

CACHE = dict(classifications=None, locations=None, glotto_macroareas=None)


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


@pytest.fixture
def tests_dir():
    return Path(__file__).parent


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

        config = Configuration(configfile=configfiles)
        if kw.get('from_cache', True):
            if not CACHE['classifications']:
                try:
                    config.process()
                    for k in CACHE:
                        CACHE[k] = getattr(config, k)
                except:
                    pass
            if CACHE['classifications']:
                for k, v in CACHE.items():
                    setattr(config, k, v)
        return config
    return make_cfg
