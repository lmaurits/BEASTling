from beastling.configuration import get_glottolog_data

from beastling.util.monophyly import *


def test_trivial():
    assert make_structure({}, [], 0, 0) == []
    assert check_structure([]) is False
    assert make_structure({}, ['x', 'y'], 1, 0) == ['x', 'y']


def test_glottolog():
    c, _, _ = classifications_from_newick(str(get_glottolog_data('newick', '4.0')))
    struct = make_structure(c, ['olde1238', 'sate1242', 'hind1273', 'schi1234'], 0, 9)
    assert check_structure(struct)
    assert make_newick(struct) == '(((hind1273,schi1234),sate1242),olde1238)'
