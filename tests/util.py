# coding: utf8
from __future__ import unicode_literals
import unittest
from tempfile import mkdtemp
import sys
from contextlib import contextmanager
import unittest

from six import BytesIO, StringIO

from clldutils.path import Path, rmtree
from clldutils.testing import WithTempDirMixin
from clldutils.misc import nfilter

from beastling.configuration import Configuration


CACHE = dict(classifications=None, locations=None, glotto_macroareas=None)

#### Below is rescued code from clldutils/testing.py which has been removed.
#### This is a hacky temp fix until BEASTling adopts pytest.

class WithTempDirMixin(object):
    """
    Composable test fixture providing access to a temporary directory.

    http://nedbatchelder.com/blog/201210/multiple_inheritance_is_hard.html
    """
    def setUp(self):
        super(WithTempDirMixin, self).setUp()
        self.tmp = Path(mkdtemp())

    def tearDown(self):
        rmtree(self.tmp, ignore_errors=True)
        super(WithTempDirMixin, self).tearDown()

    def tmp_path(self, *comps):
        return self.tmp.joinpath(*comps)


class WithTempDir(WithTempDirMixin, unittest.TestCase):
    """
    Backwards compatible test base class.
    """


@contextmanager
def capture(func, *args, **kw):
    with capture_all(func, *args, **kw) as res:
        yield res[1]


@contextmanager
def capture_all(func, *args, **kw):
    out, sys.stdout = sys.stdout, StringIO()
    err, sys.stderr = sys.stderr, StringIO()
    ret = func(*args, **kw)
    sys.stdout.seek(0)
    sys.stderr.seek(0)
    yield ret, sys.stdout.read(), sys.stderr.read()
    sys.stdout, sys.stderr = out, err

#### End of clldutils/testing.py code

class WithConfigAndTempDir(WithTempDirMixin, unittest.TestCase):
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
def old_capture(func, *args, **kw):
    out, sys.stdout = sys.stdout, BytesIO()
    oute, sys.stderr = sys.stderr, BytesIO()
    func(*args, **kw)
    sys.stdout.seek(0)
    sys.stderr.seek(0)
    yield sys.stdout.read(), sys.stderr.read()
    sys.stdout, sys.stderr = out, oute
