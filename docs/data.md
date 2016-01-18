# Data formats

BEASTling relies on data being provided in CSV files.  Two particular CSV formats are supported.

## BEASTling format

The first line of the CSV file must be a header line giving the column names, and one of the column names must be "iso".  That column must contain valid ISO codes for the languages in your analysis.  The other columns should correspond to your features of interest.  At the moment, feature values must be integers beginning from 1, but this restriction will soon be lifted.  Question marks ("?") can be used to indicate missing data.

## CLDF format

BEASTling relies on data being provided in CSV format.  If your data is not
already in CSV or some format which can be easily programmatically transformed
into CSV, you're doing something wrong.  The expected CSV format is one in
which every row corresponds to one language, every column to one feature, and
languages are represented using three letter [ISO
639](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (the header for the
language column must be "iso").  The insistence on using ISO codes allows
BEASTling to have some situational awareness of the data it is working with.
E.g., the example config above includes the line:

	families = Indo-European, Uralic

This means that even if the provided data file "my_data.csv" contains data for
all the languages on Earth, BEASTling will pick out only the languages which
belong to the Indo-European or Uralic language families (as determined by
[Glottolog](http://glottolog.org/)).  Because of the line:

	monophyletic = True

BEASTling will automatically apply monophyly constraints derived from
Glottolog's family classifications, i.e. the resulting BEAST analysis will
enforce that e.g. all Germanic languages belong in a single clade.
