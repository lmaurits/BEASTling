import pytest

from beastling.fileio import datareaders


def test_location_data(data_dir):
    assert len(list(datareaders.iterlocations(data_dir / 'location_data.csv'))) == 11


@pytest.mark.parametrize(
    'data,file_format',
    [
        ('duplicated_iso.csv', None),
        ('no_iso.csv', None),
        ('cldf.csv', 'beastling'),
        (None, 'cldf'),
        (None, 'does_not_exist'),
    ]
)
def test_datafile_error(config_factory, data_dir, data, file_format):
    config = config_factory("basic")
    if data:
        config.models[0].data = data_dir / data
    if file_format:
        config.models[0].options['file_format'] = file_format
    with pytest.raises(ValueError):
        config.process()


@pytest.mark.parametrize(
    'data',
    [
        'cldf.csv-metadata.json',
    ]
)
def test_datafile(config_factory, data_dir, data):
    config = config_factory("basic")
    config.models[0].data = data_dir / data
    config.process()
