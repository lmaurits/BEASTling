========
Overview
========

Motivation
----------

BEASTling is aimed (at least in part) at making BEAST somewhat more accessible
to linguists who have, or want to develop, a quantitative bent; people who might
read a historical linguistics paper published by biologists and computer
scientists and think "Gee, that's interesting.  I wonder what would happen if
you relaxed this constraint, or added this extra datapoint?", but have no hope
in hell of investigating this because, being linguists, none of their data sits
around in NEXUS files and they quite reasonably don't yet know how to write a
Python script to programmatically generate a 100,000 line XML file.  If at any
point in using BEASTling to set up a BEAST analysis of linguistic data you have
to understand or give any thought to:

* NEXUS and/or Newick
* XML and associated concepts like namespaces, ids or idrefs
* Sequences, alignments, populations, or anything else to do with biology
* Codemaps
* Class names, method names or call signatures of any Objects in the BEAST source code

then BEASTling has failed in its goal.  Of course, you *should* still understand
at least the basics of the model you are using and MCMC in general.  The idea is
not to let you easily play with black boxes you don't understand.  The idea is
to cut away the many, many layers of irrelevant technical detail that you would
otherwise have to understand in addition to the linguistics problem at hand.

BEASTling is also aimed at people who are quite comfortable wrangling XML but
would like a convenient, consistent, easily scriptable way to do it which, for
example, makes generating thousands of BEAST configs for a simulation study
managable.

What does BEASTling actually do?
--------------------------------

BEASTling is designed to take short, clear, high level configuration files
which are human readable and writable, like this::

	[admin]
	basename = my_analysis
	log_trees = True
	log_params = True
	[MCMC]
	chainlength = 50000
	[languages]
	families = Indo-European, Uralic
	monophyletic = True
	[model my_model]
	data = my_data.csv
	model = mk
	rate_variation = False

and turn them into corresponding 100,000 line XML files.  The text of the
configuration file is embedded as a comment at the top of the XML file, along
with the time and date the XML was generated and the version of BEASTling which
did the generating.  This means you can quickly get a feel for what an XML file
you generated six months ago does, without spending an hour grepping around for
details.

BEASTling relies on data being provided in CSV format.  If your data is not
already in CSV or some format which can be easily programmatically transformed
into CSV, you're doing something wrong.  The expected CSV format is one in
which every row corresponds to one language, every column to one feature, and
languages are represented using three letter `ISO 639 <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_ (the header for the
language column must be "iso").  The insistence on using ISO codes allows
BEASTling to have some situational awareness of the data it is working with.
E.g., the example config above includes the line::

	families = Indo-European, Uralic

This means that even if the provided data file "my_data.csv" contains data for
all the languages on Earth, BEASTling will pick out only the languages which
belong to the Indo-European or Uralic language families (as determined by
`Glottolog <http://glottolog.org/>`_).  Because of the line::

	monophyletic = True

BEASTling will automatically apply monophyly constraints derived from
Glottolog's family classifications, i.e. the resulting BEAST analysis will
enforce that e.g. all Germanic languages belong in a single clade.

The ``[model my_model]`` section of the config allows you to specify which
substitution model you'd like to use (Lewis Mk in this case), as well as control
various high-level features of the model, like whether or not rate variation is
permitted.  Any details of the model which are not specified in the config will
be automatically set to sensible, generic defaults.
