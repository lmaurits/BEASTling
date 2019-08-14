from urllib.request import FancyURLopener

import newick

from beastling.util import log


def all_subclasses(cls):
    """
    We use subclassing as a cheap registration mechanism, thus we want to be able to enumerate
    all subclasses of a given class easily.
    """
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


class URLopener(FancyURLopener):
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        raise ValueError()  # pragma: no cover


def retrieve_url(url, fname):
    return URLopener().retrieve(url, str(fname))


def sanitise_tree(tree, tree_type, languages):
    """
    Makes any changes to a user-provided tree required to make
    it suitable for passing to BEAST.

    In particular, this method checks that the supplied string or the
    contents of the supplied file:
        * seems to be a valid Newick tree
        * contains no duplicate taxa
        * has taxa which are a superset of the languages in the analysis
        * has no polytomies or unifurcations.
    """
    # Make sure tree can be parsed
    _s = tree
    try:
        tree = newick.loads(tree)[0]
    except:
        raise ValueError("Could not parse %s tree.  Is it valid Newick?" % tree_type)
    # Make sure starting tree contains no duplicate taxa
    tree_langs = tree.get_leaf_names()
    if not len(set(tree_langs)) == len(tree_langs):
        dupes = set(l for l in tree_langs if tree_langs.count(l) > 1)
        dupestring = ",".join(["%s (%d)" % (d, tree_langs.count(d)) for d in dupes])
        raise ValueError(
            "%s tree contains duplicate taxa: %s" % (tree_type.capitalize(), dupestring))
    tree_langs = set(tree_langs)
    # Make sure languages in tree is a superset of languages in the analysis
    if not tree_langs.issuperset(languages):
        missing_langs = set(languages).difference(tree_langs)
        miss_string = ",".join(missing_langs)
        raise ValueError(
            "Some languages in the data are not in the %s tree: %s" % (tree_type, miss_string))
    # If the trees' language set is a proper superset, prune the tree to fit the analysis
    if not tree_langs == set(languages):
        tree.prune_by_names(languages, inverse=True)
        log.info(
            "%s tree includes languages not present in any data set and will be pruned.".format(
                tree_type.capitalize()))
    # Get the tree looking nice
    tree.remove_redundant_nodes()
    tree.remove_internal_names()
    if tree_type == "starting":
        tree.resolve_polytomies()
    # Remove lengths for a monophyly tree
    if tree_type == "monophyly":
        for n in tree.walk():
            n._length = None
    # Checks
    if tree_type == "starting":
        assert all(len(n.descendants) in (0, 2) for n in tree.walk())
    assert len(tree.get_leaves()) == len(languages)
    assert all(l.name for l in tree.get_leaves())
    return newick.dumps(tree)
