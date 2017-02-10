# coding: utf8
from __future__ import unicode_literals
import sys


from mock import patch, Mock
from six import StringIO
from clldutils.path import Path, remove

from beastling.cli import main
from .util import config_path as _config_path
from .util import WithTempDir


def config_path(*args, **kw):
    return _config_path(*args, **kw).as_posix()


class Tests(WithTempDir):
    def setUp(self):
        WithTempDir.setUp(self)
        self._stdout, sys.stdout = sys.stdout, StringIO()
        self._stderr, sys.stderr = sys.stderr, StringIO()

    def tearDown(self):
        sys.stdout, sys.stderr = self._stdout, self._stderr
        WithTempDir.tearDown(self)

    @property
    def stdout(self):
        sys.stdout.seek(0)
        return sys.stdout.read()

    @property
    def stderr(self):
        sys.stderr.seek(0)
        return sys.stderr.read()

    def _run_main(self, commandline='', status=0):
        with self.assertRaises(SystemExit) as context:
            main(*commandline.split())
        self.assertEqual(context.exception.code, status)

    def test_main(self):
        self._run_main(status=2)

    def test_help(self):
        self._run_main('--help')
        self.assertTrue(self.stdout.strip().lower().startswith('usage:'))

    def test_extract_multiple_error(self):
        self._run_main('--extract abcd cdef', status=2)

    def test_extract_notfound_error(self):
        self._run_main('--extract abcd', status=2)

    def test_extract_notbeastling_error(self):
        xml = self.tmp_path('test.xml')
        with xml.open('w') as fp:
            fp.write('<xml>')
        self._run_main('--extract {0}'.format(xml.as_posix()), status=3)
        self.assertTrue('error', self.stderr.lower())

    def test_generate_notfound_errors(self):
        self._run_main('abcd', status=2)

    def test_generate_badconfig_error(self):
        self._run_main(config_path('no_data', bad=True), status=2)
        self.assertTrue('error', self.stderr.lower())

    def test_generate_error(self):
        with patch('beastling.cli.BeastXml', Mock(side_effect=ValueError())):
            self._run_main(config_path('basic'), status=3)

    def test_generate_extract(self):
        xml = self.tmp_path('test.xml')
        self._run_main('-v -o {0} {1}'.format(xml.as_posix(), config_path('basic')))
        self.assertTrue(xml.exists())
        # Overwriting existing files must be specified explicitely:
        self._run_main('-o {0} {1}'.format(
            xml.as_posix(), config_path('basic')), status=4)
        self._run_main('--overwrite -o {0} {1}'.format(
            xml.as_posix(), config_path('basic')), status=0)
        tcfg = Path('beastling_test.conf')
        self._run_main('--extract {0}'.format(xml.as_posix()))
        self.assertTrue(tcfg.exists())
        remove(tcfg)
