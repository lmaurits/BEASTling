# coding: utf8
from __future__ import unicode_literals
import sys
from contextlib import contextmanager

from six import BytesIO

from clldutils.path import Path
from clldutils.testing import WithTempDir
from clldutils.misc import nfilter

from beastling.configuration import Configuration


CACHE = dict(classifications=None, locations=None, glotto_macroareas=None)


class WithConfigAndTempDir(WithTempDir):
    def make_cfg(self, configfile, from_cache=True):
        config = Configuration(configfile=configfile)
        if from_cache:
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


def tests_path(*comps):
    return Path(__file__).parent.joinpath(*nfilter(comps))


def data_path(*comps):
    return tests_path('data', *comps)


def config_path(name, bad=False):
    if not name.endswith('.conf'):
        name += '.conf'
    return tests_path('configs', 'bad_configs' if bad else None, name)


@contextmanager
def capture(func, *args, **kw):
    out, sys.stdout = sys.stdout, BytesIO()
    oute, sys.stderr = sys.stderr, BytesIO()
    func(*args, **kw)
    sys.stdout.seek(0)
    sys.stderr.seek(0)
    yield sys.stdout.read(), sys.stderr.read()
    sys.stdout, sys.stderr = out, oute
