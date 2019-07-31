import pytest

from beastling.fileio.datareaders import load_data, sniff


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
