import logging

import pytest
from pycldf import Wordlist

import beastling
from beastling.fileio.datareaders import load_data, sniff, build_lang_ids, read_cldf_dataset


@pytest.fixture
def cldf_factory(tmppath):
    def factory(with_languages=True, **data):
        ds = Wordlist.in_dir(tmppath)
        if with_languages:
            ds.add_component('LanguageTable')
        ds.add_component('ParameterTable')
        data_ = dict(
            FormTable=[dict(ID='1', Form='form', Language_ID='l', Parameter_ID='p')],
            ParameterTable=[dict(ID='p', Name='pname')],
        )
        if with_languages:
            data_['LanguageTable'] = [dict(ID='l', Name='l name', Glottocode='abcd1234')]
        data_.update(data)
        ds.write(tmppath / 'metadata.json', **data_)
        return ds
    return factory


def test_read_cldf_dataset(cldf_factory, tmppath):
    _ = cldf_factory()
    with pytest.raises(ValueError):
        read_cldf_dataset(tmppath / 'metadata.json')

    data, _ = read_cldf_dataset(tmppath / 'metadata.json', code_column='Parameter_ID')
    assert data['l_name']['pname'] == 'p'


def test_build_lang_ids(cldf_factory, caplog):
    ds = cldf_factory(with_languages=False)
    assert build_lang_ids(ds, ds.column_names) == ({}, {})

    ds = cldf_factory()
    lmap, lcmap = build_lang_ids(ds, ds.column_names)
    assert lmap['l'] == 'l_name'
    assert lcmap['l_name'] == 'abcd1234'

    ds = cldf_factory(LanguageTable=[
        dict(ID='l', Name='l name', Glottocode='abcd1234'),
        dict(ID='l2', Name='l name', Glottocode='dcba1234'),
    ])
    with caplog.at_level(logging.INFO, logger=beastling.__name__):
        lmap, lcmap = build_lang_ids(ds, ds.column_names)
        assert 'Glottocodes' in caplog.records[-1].message
        assert lmap['l'] == 'abcd1234'

    ds = cldf_factory(LanguageTable=[
        dict(ID='l', Name='l name'),
        dict(ID='l2', Name='l name'),
    ])
    with caplog.at_level(logging.INFO, logger=beastling.__name__):
        lmap, lcmap = build_lang_ids(ds, ds.column_names)
        assert 'local' in caplog.records[-1].message
        assert lmap['l'] == 'l'


def test_load_data(data_dir):
    for p in data_dir.iterdir():
        if p.suffix == '.csv':
            if p.stem in ['duplicated_iso', 'no_iso', 'nonstandard_lang_col']:
                with pytest.raises(ValueError):
                    load_data(p)
            elif p.stem in ['forms', 'cognatesets']:
                # Metadata-free CLDF Wordlist has no default value column
                continue
            else:
                if p.stem == "cldf_value_col":
                    data, x = load_data(p, file_format='cldf-legacy', value_column="Cognate_Set")
                else:
                    data, x = load_data(p)
                assert len(data) != 0


@pytest.mark.parametrize(
    'fname,kw',
    [
        ('cldf.csv', dict()),
        ('cldf.csv', dict(file_format='cldf-legacy')),
        ('cldf_value_col.csv', dict(file_format='cldf-legacy', value_column="Cognate_Set")),
        ('cldf.tsv', dict()),
        ('cldf.tsv', dict(file_format='cldf-legacy')),
    ]
)
def test_load_data_2(data_dir, fname, kw):
    beastling_format, x = load_data(data_dir / "basic.csv")
    format, _ = load_data(data_dir / fname, **kw)

    assert set(list(beastling_format.keys())) == set(list(format.keys()))
    for key in beastling_format:
        assert set(beastling_format[key].items()), set(format[key].items())


@pytest.mark.parametrize(
    'fname',
    [
        "basic.csv",
        "basic_with_comma.csv",
        "binary.csv",
        "cldf2.csv",
        "cldf.csv",
        "cldf_value_col.csv",
        "cldf_with_comma.csv",
        "cognatesets.csv",
        "duplicated_iso.csv",
        "forms.csv",
        "germanic.csv",
        "glottocode.csv",
        "isolates.csv",
        "location_data.csv",
        "mixedcode.csv",
        "more_location_data.csv",
        "no_iso.csv",
        "noncode.csv",
        "nonnumeric.csv",
        "nonstandard_lang_col.csv",
        "values.csv",
        "cldf.tsv",
    ]
)
def test_sniffer(data_dir, fname):
    dialect = sniff(data_dir / fname)
    assert dialect.delimiter == "," if fname.endswith('.csv') else '\t'
