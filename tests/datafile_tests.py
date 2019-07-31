import pytest


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
def test_datafile(config_factory, data_dir, spec):
    config = config_factory("basic")
    if 'data' in spec:
        spec['data'] = data_dir / spec['data']
    config.model_configs[0].update(spec)
    with pytest.raises(ValueError):
        config.process()
