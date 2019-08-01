import pytest

from beastling.fileio import datareaders


def test_location_data(data_dir):
    assert len(datareaders.load_location_data(data_dir / 'location_data.csv')) == 11


@pytest.mark.parametrize(
    'spec',
    [
        dict(data='duplicated_iso.csv'),
        dict(data='no_iso.csv'),
        dict(data='cldf.csv', file_format='beastling'),
        dict(file_format='cldf'),
        dict(file_format='does_not_exist'),
    ]
)
def test_datafile_error(config_factory, data_dir, spec):
    config = config_factory("basic")
    if 'data' in spec:
        spec['data'] = data_dir / spec['data']
    config.model_configs[0].update(spec)
    with pytest.raises(ValueError):
        config.process()


@pytest.mark.parametrize(
    'spec',
    [
        dict(data='cldf.csv-metadata.json'),
    ]
)
def test_datafile(config_factory, data_dir, spec):
    config = config_factory("basic")
    if 'data' in spec:
        spec['data'] = data_dir / spec['data']
    config.model_configs[0].update(spec)
    config.process()
