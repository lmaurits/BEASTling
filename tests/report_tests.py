from beastling.report import BeastlingReport, BeastlingGeoJSON


def test_report(config_factory):
    config = config_factory('admin', 'basic', 'calibration')
    report = BeastlingReport(config)
    report.tostring()


def test_geojson(config_factory):
    config = config_factory('admin', 'basic', 'calibration')
    _ = BeastlingGeoJSON(config)
