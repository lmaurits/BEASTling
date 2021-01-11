import pytest

from beastling.util import fileio


def test_missing_file():
    with pytest.raises(ValueError):
        list(fileio.iterlines('xyz'))
