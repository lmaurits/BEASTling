============
Data formats
============

BEASTling relies on data being provided in CSV files.  Two particular CSV formats are supported.

BEASTling format
----------------

In this format, each line of the CSV file contains all of the data for a single languge.

The first line of the file must be a header, giving the column names for the rest of the file.  The column which contains each language's unique identifier should be named one of:

  * ``iso``
  * ``iso_code``
  * ``glotto``
  * ``glottocode``
  * ``language``
  * ``language_id``
  * ``lang``
  * ``lang_id``

  A column with one of these names will be automatically recognised as containing language identifiers.  If you absolutely have to use a different column name, use the `language_column` parameter in your configuration file's ``[model]`` section to tell BEASTling the name.

Languages can be identified by arbitrary strings, provided each language has a unique identifier, *however* certain features of BEASTling will not function unless your language identifiers are either:

* three character ISO 639 codes
  * Glottocodes as assigned by the `Glottolog project <http://glottolog.org/glottolog/glottologinformation>`_

  All columns other than the language identifier column correspond to independent language features.  The names and values of features can both be arbitrary strings, so long as each feature has a unique name.  Question marks ("?") can be used to indicate missing data.

CLDF format
-----------

BEASTling also supports the `Cross-Linguistic Data Format <https://github.com/glottobank/cldf>`_ standard.  In this format, each line of the CSV file contains a single data point for a single language.

The first line of the file must be a header, giving the column names for the rest of the file.  The three column names must be ``Language_ID``, ``Feature_ID`` or ``Parameter_ID``, and ``Value`` (these column names are how BEASTling recognises a file as a CLDF file, so if you change them the file will be parsed as a BEASTling format file).  As before, Language_IDs can be arbitrary strings, but must be ISO codes or Glottocodes if you want to use all features of BEASTling.  Feature_IDs and Values can be arbitrary strings, and ``?`` can be used to indicate missing data.
