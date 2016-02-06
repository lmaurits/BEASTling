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

Example valid BEASTling format data files are shown below.

Using ISO codes and numeric data:
::

        iso,f0,f1,f2,f3,f4,f5,f6,f7,f8,f9
        aiw,1,1,1,1,1,1,?,1,?,1
        aas,2,2,2,1,2,2,?,?,1,3
        kbt,3,3,1,1,2,3,?,2,?,5
        abg,4,2,2,1,1,4,?,?,3,4
        abf,5,1,1,1,2,5,?,3,?,2

Using Glottocodes and alphabetical data:
::

        glotto,f0,f1,f2,f3,f4,f5,f6,f7,f8,f9
        aari1239,A,A,A,A,A,A,?,A,?,A
        aasa1238,B,B,B,A,B,B,?,?,A,C
        abad1241,C,C,A,A,B,C,?,B,?,E
        abag1245,D,B,B,A,A,D,?,?,C,D
        abai1240,E,A,A,A,B,E,?,C,?,B

CLDF format
-----------

BEASTling also supports the `Cross-Linguistic Data Format <https://github.com/glottobank/cldf>`_ standard.  In this format, each line of the CSV file contains a single data point for a single language.

The first line of the file must be a header, giving the column names for the rest of the file.  The three column names must be ``Language_ID``, ``Feature_ID`` or ``Parameter_ID``, and ``Value`` (these column names are how BEASTling recognises a file as a CLDF file, so if you change them the file will be parsed as a BEASTling format file).  As before, Language_IDs can be arbitrary strings, but must be ISO codes or Glottocodes if you want to use all features of BEASTling.  Feature_IDs and Values can be arbitrary strings, and ``?`` can be used to indicate missing data.

An example valid CLDF format data file is shown below.  It specifies precisely the same data set as the first example BEASTling format data file above.

::

        Language_ID, Feature_ID, Value
        aiw, f0, 1
        aiw, f1, 1
        aiw, f2, 1
        aiw, f3, 1
        aiw, f4, 1
        aiw, f5, 1
        aiw, f6, ?
        aiw, f7, 1
        aiw, f8, ?
        aiw, f9, 1
        aas, f0, 2
        aas, f1, 2
        aas, f2, 2
        aas, f3, 1
        aas, f4, 2
        aas, f5, 2
        aas, f6, ?
        aas, f7, ?
        aas, f8, 1
        aas, f9, 3
        kbt, f0, 3
        kbt, f1, 3
        kbt, f2, 1
        kbt, f3, 1
        kbt, f4, 2
        kbt, f5, 3
        kbt, f6, ?
        kbt, f7, 2
        kbt, f8, ?
        kbt, f9, 5
        abg, f0, 4
        abg, f1, 2
        abg, f2, 2
        abg, f3, 1
        abg, f4, 1
        abg, f5, 4
        abg, f6, ?
        abg, f7, ?
        abg, f8, 3
        abg, f9, 4
        abf, f0, 5
        abf, f1, 1
        abf, f2, 1
        abf, f3, 1
        abf, f4, 2
        abf, f5, 5
        abf, f6, ?
        abf, f7, 3
        abf, f8, ?
