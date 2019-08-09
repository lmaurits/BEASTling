from xml.etree import ElementTree

import pytest

from beastling.beastxml import collect_ids_and_refs


@pytest.mark.parametrize(
    'xml,assertion',
    [
        (
                '<plate range="a,b,c,d" var="x"><e id="thing$(x)"/></plate>',
                lambda r: len(r['id']) == 4 and len(r['idref']) == 0),
        (
                '<plate range="a,b,c,d" var="x"><e idref="thing$(x)"/></plate>',
                lambda r: len(r['idref']) == 4 and len(r['id']) == 0),
        (
                '<a attr="@b"><plate range="a" var="x"><e idref="thing$(x)"/></plate></a>',
                lambda r: len(r['idref']) == 2 and len(r['id']) == 0),
    ]
)
def test_collect_ids_and_refs(xml, assertion):
    res = collect_ids_and_refs(ElementTree.fromstring(xml))
    assert assertion(res)