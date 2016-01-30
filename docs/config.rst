==================
Configuration file
==================

Understanding BEASTling is, mostly, a matter of understanding the configuration file format.  Config files have the following form:

::

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

i.e. they are divided into *sections*, which are indicated by names enclosed in square brackets (in the above, the section names are ``section1``, ``section2``, etc.), and each section consists of some number of *parameters* and assigned *values*.  Each line of each section corresponds to assigning one value to one parameter, the the parameter name on the left of the equals sign and the value on the right.

BEASTling configuration files can range from very simple (the only section which is compulsory is one or more ``model`` sections) to relatively complicated - although in all cases they are vastly simpler than any BEAST XML file.  If you provide minimal configuration information, "sensible defaults" will be used for all settings.  *It is your responsibility to know what the defaults are and to make sure that they truly are sensible for you rapplication*.

The recognised config file sections are as follows:

admin section
-------------

The ``admin`` section may contain the following parameters:

* ``basename``: this is any user-friendly string which will be used in e.g. filenames.  If the basename is, say, "IE_cognates", then the BEAST XML file which BEASTling produces will be named IE_cognates.xml, and when the BEAST analysis is run, the trees will be logged in IE_trees.nex, etc.  If unspecified, it will default to "beastling".

* ``screenlog``: this must be set to "True" or "False" and controls whether or not BEAST should output basic MCMC data like ESS to the screen while running.  Default is True.

* ``log_probabilities``: "True" or "False".  Controls whether or not the prior, likelihood and posterior should be logged to a file called basename.log.  This is generally a good idea, so that you can check e.g. ESSes for these things in Tracer, so the default is True.

* ``log_params``: "True" or "False".  Controls whether or not all model parameters are also included in basename.log.  Default is False.

* ``log_trees``: "True" or "False".  Controls whether or not sampled trees should be logged to basename.nex.  Default is True.

* ``log_all``: "True" or "False".  Setting this true is simply a shorthand for setting ``log_probabilities`` and ``log_params`` and ``log_trees`` to all be true.  Default is False.

MCMC section
------------

The ``MCMC`` section may contain the following parameters:

* ``chainlength``: number of iterations to run the MCMC chain for.  Default is 10,000,000.

languages section
-----------------

The ``languages`` section may contain the following parameters:

* ``families``: One of:
   * A comma-separated list of language families to include in the analysis, spelled exactly as they are in Glottolog.  E.g. ``Indo-European, Uralic, Dravidian``.
   * The path to a file which contains one language family per line.  If no value is assigned to this parameter, all languages present in the data file will be included.

* ``monophyletic``: "True" or "False".  Controls whether or not to impose the family structure in Glottolog as monophyly constraints in the BEAST analysis.  Default is False.

calibration section
-------------------

The ``calibration`` section should contain one parameter for each distinct calibration point that you wish to include in the analysis.

The name of each parameter should be a comma-separated list of family names, and the corresponding values should be two ages, expressed in units of time before present (BP), corresponding to a 95% confidence interval for the age of the most recent common ancestor (MRCA) of those families.  Note that the parameter name may just be a single family.  E.g. if you want to tell your analysis that you are 95% sure that Austronesian is between 4,750 and 5,800 years old, include the following line in your calibration section:

::

	Austronesian = 4750 - 5800

You may use arbitrary units without problems, i.e. you could provide dates in millenia BP:

::

	Austronesian = 4.75 - 5.8

The only time this matters is when it comes time to interpret tree heights or clock and/or mutation rates.

model sections
--------------

A BEASTling config file *must* include at least one model section, but it can contain several.  Model sections are different from all other sections in that you must give each one a name.  A ``[model]`` section is invalid, but ``[model mymodel]`` will work.  Suppose you want to perform an analysis using both cognate data and structural data, and you want to use different model settings for the different kinds of data (say different substitution models).  You could have a ``[model cognate]`` section and a ``[model structure]`` section.  You can have as many models as you like, as long as each one gets a unique name.

Each model section *must* contain the following parameters, i.e. they are mandatory and BEASTling will refuse to work if you ommit them:

* ``model``: should specify the name of the substitution model type you want to use.  Available models are:
   * "covarion" (Binary covarion model)
   * "bsvs" (Bayesian Stochastic Variable Selection)
   * "mk" (Lewis Mk model)

   For more information on the available models, see :doc:`substitution`.

* ``data``: should be one of:
   * A path to a file containing your language data in a compatible .csv format
   * The string "stdin" if you wish for data to be read from ``stdin`` rather than a file.

   Regardless of whether data is read from a file or from ``stdin``, it must be in one of the two compatible .csv formats.  These are described in :doc:`data`.  Note that BEASTling can also be made to read data from ``stdin`` by using the ``--stdin`` command line argument.

Additionally, each model section *may* contain the following parameters, i.e.  they are optional:

* ``data_format``: Can be used to explicitly set which of the two supported .csv formats the data for this model is supplied in, to be used if BEASTling is mistakenly trying to parse one format as the other (which should be very rare).  Should be one of:
   * "beastling"
   * "cldf"

* ``language_column``: Can be used to indicate the column name in the .csv file header which corresponds to the unique language identifier.  If the column name is one of "iso", "iso_code", "glotto", "glotto_code", "language", "language_id", "lang" or "lang_id", BEASTling will recognise it automatically.  This parameter is only needed if you have a pre-existing data file which uses a different column name which you don't want to change (perhaps because it would break compatibility with another tool).

* ``pruned``: "True" or "False".  Make use of "pruned trees".  This can improve performance in data sets with a lot of missing data.  Default is False.

* ``rate_variation``: "True" or "False".  Estimate a separate substitution rate for each feature (using a Gamma prior).

* ``remove_constant_traits``: "True" or "False".  By default, this is set to "True", which means that if your data set contains any features which have the same value for all of the languages in your analysis (which is not necessarily all of the languages in your data file, if you are using the "families" parameter in your "languages" section!), BEASTling will automatically remove that feature from the analysis (since it cannot possibly provide any phylogenetic information).  If you want to keep these constant features in for some reason, you must explicitly set this parameter to False.
* ``traits``: Is used to select a subset of the features in the given data file.  Should be one of:
   * A comma-separated list of feature names (as they are given in the data CSV's header line)
   * A path to a file which contains one feature name per line

