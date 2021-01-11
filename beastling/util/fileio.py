import pathlib


def iterlines(fname, name='file'):
    fname = pathlib.Path(fname)
    if not fname.exists():
        raise ValueError("Could not find {0} {1}".format(name, fname))
    with fname.open(encoding='utf8') as fp:
        for line in fp:
            yield line
