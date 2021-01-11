import re

import newick

__all__ = ['classifications_from_newick', 'make_newick', 'make_structure', 'check_structure']

GLOTTOLOG_NODE_LABEL = re.compile(
    "'(?P<name>[^\[]+)\[(?P<glottocode>[a-z0-9]{8})\](\[(?P<isocode>[a-z]{3})\])?(?P<appendix>-l-)?'")


def classifications_from_newick(string, label_pattern=GLOTTOLOG_NODE_LABEL):
    label2name = {}

    def parse_label(label):
        match = {
            k: v.strip() if v else '' for k, v in label_pattern.match(label).groupdict().items()}
        assert match['glottocode']
        label2name[label] = (
            match.get('name', '').strip().replace("\\'", "'"),
            match['glottocode'])
        return match

    def get_classification(node):
        ancestor = node.ancestor
        if not ancestor:
            # Node is root of some family
            return [label2name[node.name]]
        res = []
        while ancestor:
            res.append(label2name[ancestor.name])
            ancestor = ancestor.ancestor
        return list(reversed(res))

    classifications, nodemap = {}, {}
    # Walk the tree and build the classifications dictionary
    trees = newick.read(string)
    for tree in trees:
        for node in tree.walk():
            label = parse_label(node.name)
            classification = get_classification(node)
            classifications[label['glottocode']] = classification
            if label.get('isocode'):
                classifications[label['isocode']] = classification
            nodemap[label['glottocode']] = node
    return classifications, nodemap, label2name


def make_structure(classification, langs, depth, maxdepth):
    """
    Recursively partition a list of languages (ISO or Glottocodes) into
    lists corresponding to their Glottolog classification.  The process
    may be halted part-way down the Glottolog tree.

    :param classification: `dict` {glottocode: [(name, glottocode), ...]}
    """
    if depth > maxdepth:
        # We're done, so terminate recursion
        return langs

    def subgroup(name, depth):
        ancestors = classification[name.lower()]
        return ancestors[depth][0] if depth < len(ancestors) else ''

    def sortkey(i):
        """
        Callable to pass into `sorted` to port sorting behaviour from py2 to py3.

        :param i: Either a string or a list (of lists, ...) of strings.
        :return: Pair (nesting level, first string)
        """
        d = 0
        while isinstance(i, list):
            d -= 1
            i = i[0] if i else ''
        return d, i

    N = len(langs)
    # Find the ancestor of all the given languages at at particular depth
    # (i.e. look `depth` nodes below the root of the Glottolog tree)
    groupings = list(set([subgroup(l, depth) for l in langs]))
    if len(groupings) == 1:
        # If all languages belong to the same classificatio at this depth,
        # there are two possibilities
        if groupings[0] == "":
            # If the common classification is an empty string, then we know
            # that there is no further refinement possible, so stop
            # the recursion here.
            langs.sort()
            return langs
        else:
            # If the common classification is non-empty, we need to
            # descend further, since some languages might get
            # separated later
            return make_structure(classification, langs, depth + 1, maxdepth)
    else:
        # If the languages belong to multiple classifications, split them
        # up accordingly and then break down each classification
        # individually.

        # Group up those languages which share a non-blank Glottolog classification
        partition = [[l for l in langs if subgroup(l, depth) == group] for group in groupings if group != ""]
        # Add those languages with blank classifications in their own isolate groups
        for l in langs:
            if subgroup(l, depth) == "":
                partition.append([l, ])
        # Get rid of any empty sets we may have accidentally created
        partition = [part for part in partition if part]
        # Make sure we haven't lost any langs
        assert sum((len(p) for p in partition)) == N
        return sorted(
            [make_structure(classification, group, depth + 1, maxdepth)
             for group in partition],
            key=sortkey)


def check_structure(struct):
    """
    Return True if the monophyly structure represented by struct is
    considered "meaningful", i.e. encodes something other than an
    unstructured polytomy.
    """

    # First, transform e.g. [['foo'], [['bar']], [[[['baz']]]]], into simply
    # ['foo','bar','baz'].
    def denester(l):
        if type(l) != list:
            return l
        if len(l) == 1:
            return denester(l[0])
        return [denester(x) for x in l]

    struct = denester(struct)
    # Now check for internal structure
    if not any([type(x) == list for x in struct]):
        # Struct is just a list of language names, with no internal structure
        return False
    return True


def make_newick(struct):
    """
    Converts a structure of nested lists into Newick string.
    """
    if not type([]) in [type(x) for x in struct]:
        return "(%s)" % ",".join(struct) if len(struct) > 1 else struct[0]
    else:
        return "(%s)" % ",".join([make_newick(substruct) for substruct in struct])
