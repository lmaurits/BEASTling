# coding: utf8
from nose.tools import *

from beastling.configuration import Configuration
from beastling.report import BeastlingReport, BeastlingGeoJSON

from .util import WithConfigAndTempDir, config_path


class Tests(WithConfigAndTempDir):

    def _make_cfg(self, *names):
        return self.make_cfg([config_path(name).as_posix() for name in names])

    def test_report(self):
        config = self._make_cfg('admin', 'basic', 'calibration')
        report = BeastlingReport(config)
        report.tostring()

    def test_geojson(self):
        config = self._make_cfg('admin', 'basic', 'calibration')
        report = BeastlingGeoJSON(config)
