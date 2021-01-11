import pytest

from beastling.util import xml


@pytest.mark.parametrize(
    'kw,assertion',
    [
        ({}, lambda e: e.tag == 'run' and not e.attrib),
        # Attribute creation for non-valid-python-keyword args:
        ({'attrib': {'a.b': 1}}, lambda e: e.get('a.b') == '1'),
        # Attribute creation with attributes as keyword arguments:
        ({'a': 1}, lambda e: e.get('a') == '1'),
        # Casting to string:
        ({'a': True}, lambda e: e.get('a') == 'true'),
        ({'a': False}, lambda e: e.get('a') == 'false'),
        ({'range': [1, 2]}, lambda e: e.get('range') == '1,2'),
        # Creation of text content of elements:
        ({'text': 1}, lambda e: e.text == '1'),
    ]
)
def test_subelement(kw, assertion):
    assert assertion(xml.run(None, **kw))


def test_comment():
    assert xml.comment(1).text == '1'


def test_nesting():
    e = xml.beast()
    xml.run(xml.beast())
    for ee in e:
        assert ee.tag == 'run'
