# BEASTling
A linguistics-focussed command line tool for generating [BEAST](http://beast2.org) XML files.  Only
BEAST 2.x is supported.

BEASTling is aimed (at least in part) at making BEAST somewhat more accessible
to linguists who have, or want to develop, a quantitative bent; people who might
read a historical linguistics paper published by biologists and computer
scientists and think ``gee, that's interesting.  I wonder what would happen if
you relaxed this constraint, or added this extra datapoint?'', but have no hope
in hell of investigating this because, being linguists, none of their data sits
around in NEXUS files and they quite reasonably don't yet know how to write a
Python script to programmatically generate a 100,000 line XML file.  If at any
point in using BEASTling to set up a BEAST analysis of linguistic data you have
to understand or give any thought to:

* NEXUS and/or Newick
* XML and associated concepts like namespaces, ids or idrefs
* Sequences, alignments, populations, or anything else to do with biology
* Codemaps
* Class names, method names or call signatures of any Objects in the BEAST
source code

then BEASTling has failed in its goal.  Of course, you *should* still understand
at least the basics of the model you are using and MCMC in general.  The idea is
not to let you easily play with black boxes you don't understand.  The idea is
to cut away the many, many layers of irrelevant technical detail that you would
otherwise have to understand in addition to the linguistics problem at hand.

BEASTling is also aimed at people who are quite comfortable wrangling XML but
would like a convenient, consistent, easily scriptable way to do it which, for
example, makes generating thousands of BEAST configs for a simulation study
managable.

## Overview

BEASTling is designed to take short, clear, high level configuration files
which are human readable and writable, like this:

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

The [model my_model] section of the config allows you to specify which
substitution model you'd like to use (Lewis Mk in this case), as well as control
various high-level features of the model, like whether or not rate variation is
permitted.  Any details of the model which are not specified in the config will
be automatically set to sensible, generic defaults.

## Installation

BEASTling depends upon [SciPy](http://www.scipy.org/).  For boring technical reasons, it's best if you
install SciPy first (if you don't already have it installed) either by using
your operating system's package management facility (apt, yum, etc.) or a Python
packaging tool like easy_install or pip.

BEASTling is installed using the setup.py script in the root of the repository.
Installation will look something like this:

	$ git clone https://github.com/lmaurits/BEASTling.git
	$ cd BEASTling
	$ sudo python ./setup.py install

This will install an executable "beastling", which should be put somewhere in
your default PATH, so you can run it from the command line simply by typing
"beastling" and hitting enter.

Typical usage is to run:

	$ beastling ./my_config.conf

where "my_config.conf" is a valid BEASTling configuration file.  This will
produce an XML file, whose name is determined by the "basename" parameter in the
config file.

## Configuration file

Understanding BEASTling is, mostly, a matter of understanding the configuration
file format.  Config files look like this:

	[section1]
	param1a = value1a
	param2a = value2a
	param3a = value3a
	param4a = value4a
	param5a = value5a
	[section2]
	param1b = value1b
	param2b = value2b
	param3b = value3b
	[section3]
	param1c = value1c
	param2c = value2c
	param3c = value3c
	param4c = value4c
	...

i.e. they are divided into *sections*, which are indicated by names enclosed in
square brackets, and each section consists of some number of *parameters* and
assigned *values*.  Each line of each section corresponds to assigning one value
to one parameter.  The valid sections are:

### "admin" section

The admin section may contain the following parameters:

basename: this is any user-friendly string which will be used in e.g. filenames.
If the basename is, say, "IE_cognates", then the BEAST XML file which BEASTling
produces will be named IE_cognates.xml, and when the BEAST analysis is run, the
trees will be logged in IE_trees.nex, etc.  If unspecified, it will default to
"beastling".

screenlog: this must be set to "True" or "False" and controls whether or not
BEAST should output basic MCMC data like ESS to the screen while running.
Default is True.

log_probabilities: "True" or "False".  Controls whether or not the prior,
likelihood and posterior should be logged to a file called basename.log.  This
is generally a good idea, so that you can check e.g. ESSes for these things in
Tracer, so the default is True.

log_params: "True" or "False".  Controls whether or not all model parameters are
also included in basename.log.  Default is False.

log_trees: "True" or "False".  Controls whether or not sampled trees should be
logged to basename.nex.  Default is True.

## "MCMC" section

The MCMC section may contain the following parameters:

chainlength: number of iterations to run the MCMC chain for.  Default is
10,000,000.

## "languages" section

The languages section may contain the following parameters:

families: One of:
* A comma-separated list of language families to include in the
analysis, spelled exactly as they are in Glottolog.  E.g. "Indo-European,
Uralic, Dravidian".
* The path to a file which contains one language family per line.
If no value is assigned to this parameter, all languages present in the data
file will be included.

monophyly: "True" or "False".  Controls whether or not to impose the family
structure in Glottolog as monophyly constraints in the BEAST analysis.  Default
is False.

## "calibration" section

The calibration section should contain one parameter for each distinct
calibration point that you wish to include in the analysis.

The name of each parameter should be a comma-separated list of family names, and
the corresponding values should be two ages, expressed in years before present
(BP), corresponding to a 95% confidence interval for the age of the most recent
common ancestor (MRCA) of those families.  Note that the parameter name may just
be a single family.  E.g. if you want to tell your analysis that you are 95%
sure that Austronesian is between 4,750 and 5,800 years old, include the
following line in your calibration section:

	Austronesian = 4750 - 5800

## 'model' sections

A BEASTling config file must include at least one model section, but it can
contain several.  The name of each model section must begin with "model " (note
the space), but the remainder of the name is unrestricted.  Suppose you want to
perform an analysis using cognate data and structural data, and you want to use
different models for the different kinds of data.  You could have a [model
cognate] section and a [model structural] section.  You can have as many models
as you like, as long as each one gets a unique name.

Each model section *must* contain the following parameters, i.e. they are
mandatory and BEASTling will refuse to work if you ommit them:

model: should specify the name of the model type you want to use.  Must be one
of:

* mk (Lewis Mk model: a generalisation of Jukes-Cantor)
* bsvs (Bayesian Stochastic Variable Selection)

data: should be a path to a file containing your language data in .csv format.
The first line of the CSV file must be a header line giving the column names,
and one of the column names must be "iso".  That column must contain valid ISO
codes for the languages in your analysis.  The other columns should correspond
to your features of interest.  At the moment, feature values must be integers
beginning from 1, but this restriction will soon be lifted.  Question marks
("?") can be used to indicate missing data.

Additionally, each model section *may* contain the following parameters, i.e.
they are optional:

traits: Is used to select a subset of the features in the given data file.  Should be one of:
* A comma-separated list of feature names (as they are given in the data CSV's
  header line)
* A path to a file which contains one feature name per line

pruned: "True" or "False".  Make use of "pruned trees".  This can improve
performance in data sets with a lot of missing data.  Default is False.

rate_variation: "True" or "False".  Estimate a separate substitution rate for
each feature (using a Gamma prior).

remove_constant_traits: "True" or "False".  By default, this is set to "True",
which means that if your data set contains any features which have the same
value for all of the languages in your analysis (which is not necessarily all of
the languages in your data file, if you are using the "families" parameter in
your "languages" section!), BEASTling will automatically remove that feature
from the analysis (since it cannot possibly provide any phylogenetic
information).  If you want to keep these constant features in for some reason,
you must explicitly set this parameter to False.
