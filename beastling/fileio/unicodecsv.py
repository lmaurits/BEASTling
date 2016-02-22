import csv, codecs, cStringIO

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeDictReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, header, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        fieldnames = csv.reader([header,]).next()
        self.reader = csv.DictReader(f, fieldnames=fieldnames, dialect=dialect, **kwds)
        self.fieldnames = [fn.strip() for fn in self.reader.fieldnames]

    def next(self):
        row = self.reader.next()
        newrow = {}
        for key in row:
            newrow[unicode(key.strip(), "utf-8")] = unicode(row[key].strip(), "utf-8")
        return newrow

    def __iter__(self):
        return self
