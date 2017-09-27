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

BEASTling configuration files can range from very simple (the only section which is compulsory is one or more ``model`` sections) to relatively complicated - although in all cases they are vastly simpler than any BEAST XML file.  If you provide minimal configuration information, "sensible defaults" will be used for all settings. 

*It is your responsibility to know what the defaults are and to make sure that they truly are sensible for your application*.

The recognised config file sections are as follows:

admin section
-------------

The ``admin`` section may contain the following parameters:

* ``basename``: this is any user-friendly string which will be used in e.g. filenames.  If the basename is, say, "IE_cognates", then the BEAST XML file which BEASTling produces will be named IE_cognates.xml, and when the BEAST analysis is run, the trees will be logged in IE_trees.nex, etc.  If unspecified, it will default to "beastling".

* ``glottolog_release``: the number of a Glottolog release (>=2.7), from which to obtain the language classification.

* ``screenlog``: this must be set to "True" or "False" and controls whether or not BEAST should output basic MCMC data like ESS to the screen while running.  Default is True.

* ``log_probabilities``: "True" or "False".  Controls whether or not the prior, likelihood and posterior should be logged to a file called basename.log.  This is generally a good idea, so that you can check e.g. ESSes for these things in Tracer, so the default is True.

* ``log_params``: "True" or "False".  Controls whether or not all model parameters are also included in basename.log.  Default is False.

* ``log_trees``: "True" or "False".  Controls whether or not sampled trees should be logged to basename.nex.  Default is True.

* ``log_all``: "True" or "False".  Setting this true is simply a shorthand for setting ``log_probabilities`` and ``log_params`` and ``log_trees`` to all be true.  Default is False.

* ``log_every``: an integer specifying how many MCMC samples should elapse between consecutive entries in the log file.  If not specified, BEASTling will set this based on the chainlength such that the log file will be 10,000 entries long.  This is a good compromise between getting lots of information about the posterior and conserving disk space.

MCMC section
------------

The ``MCMC`` section may contain the following parameters:

* ``chainlength``: number of iterations to run the MCMC chain for.  Default is 10,000,000.

* ``sample_from_prior``: "True" or "False".  If True, BEAST will ignore all supplied data and the tree, all clock rates and any model parameters will all be sampled from their prior distributions.  Default is False.

languages section
-----------------

The ``languages`` section may contain the following parameters:

* ``exclusions``: One of:
   * A comma-separated list of language names or codes to exclude from the analysis, spelled exactly as they are in the data file(s).
   * The path to a file which contains one language per line.

This can be used by itself to remove a few problematic languages from a data file, or in conjunction with ``families`` or ``macroareas`` to better control which languages are included, e.g. you may set ``macroareas = Africa``, but use ``excludes`` to remove some outliers like Austronesian languages on Madagascar or Indo-European languages in South Africa.

* ``families``: One of:
   * A comma-separated list of language families to include in the analysis, spelled exactly as they are in Glottolog.  E.g. ``Indo-European, Uralic, Dravidian``.
   * The path to a file which contains one language family per line.

If no value is assigned to this parameter, all languages present in the data file will be included (unless ``languages`` (see below) is used.  ``families`` and ``languages`` cannot both be used in a single configuration.

* ``languages``: One of:
   * A comma-separated list of language names or codes to include in the analysis, spelled exactly as they are in the data file(s).
   * The path to a file which contains one language per line.  

If no value is assigned to this parameter, all languages present in the data file will be included (unless ``families`` (see above) is used.  ``languages`` and ``families`` cannot both be used in a single configuration.

* ``macroareas``: One of:
   * A comma-separated list of Glottolog macroareas to include in the analysis
   * The path to a file which contains one macroarea per line.  

Valid macroareas are: ``Africa``, ``Australia``, ``Eurasia``, ``North America``, ``Papunesia``, ``South America``.  This can be used in conjunction with ``languages`` or ``families``, in which case a language must meet both criteria to be included.  E.g. if you set ``families = Afro-Asiatic`` and ``macroareas = Africa``, you will get only the Afro-Asiatic languages located in Africa, and those located in Eurasia will be excluded.

* ``monophyly`` (or ``monophyletic``): "True" or "False".  Controls whether or not to impose the family structure in Glottolog as monophyly constraints in the BEAST analysis.  Default is False.  If True, very fine-grained control over exactly how much constraint is opposed can be gained by using additional options, documented below.

* ``monophyly_levels``: An integer specifying how many levels of the Glottolog classification to impost as a monophyly constraints.  By default, levels are added in a top-down fashion (but see ``monophyly_direction`` below).  E.g. if ``monophyly_levels = 3`` is specified, then Indo-European languages will be constrained to be monophyletic (one level), and so will Armenian, Celtic and Germanic, among others (two levels), and so will be Gothic and Northwest Germanic, among others (three levels), but North Germanic and West Germanic, or any descendant groups, will *not* be.  This allows one to enforce the high level structure of Glottolog, while leaving the "fine details" of relationships among leaves to be inferred from data.  If no value is specified, the entire Glottolog classification will be imposed.

* ``monophyly_direction``: One of ``top_down`` (the default) or ``bottom_up``.  Determines the effect of ``monophyly_levels``.  If ``monophyly_direction = top_down``, constraints will be added from the roots of Glottolog trees downward (e.g. Indo-European, Germanic, North Germanic,...).  If ``bottom_up``, constraints will be added from the leaves upward (e.g. Macro-Swedish, East Scandinavian, North Germanic,...).

* ``monophyly_newick``: If you disagree with Glottolog's classification of the languages in your dataset (or would simply like to refine them by resolving some polytomies), you can use this option to do so.  The value should either be a filename containing a tree in Newick format, or a valid Newick tree string (unless your analysis has very few languages, using an external file is probably preferable to keep your BEASTling config short and neat).  The provided tree should not be a fully resolved binary tree, but should use polytomies to represent your beliefs about relatedness of languages.  If you believe that a grou of languages are related, but know nothing about the internal structure of the clade, they should all descend from a single parent node.  The languages in the provided tree may be a superset of the languages in your analysis - the monophyly tree will be pruned appropriately.

  * ``monophyly_start_depth``: An integer specifying an initial number of levels of the Glottolog classification to skip over when implying constraints (default 0).  E.g., with top down constraints, setting ``monophyly_start_depth=2`` will skip over Indo-European and Germanic, so that if ``monophyly_levles=3``, the imposed levels will be, e.g. Western Germanic, Franconian and High Franconian.  With bottom up constraints, this controls skipping initial levels above the leaves.

* ``monophyly_end_depth``: An integer specifying a level in the Glottolog classification below which constraints will not be imposed.  If ``monophyly_end_depth`` is specified, then ``monophyly_direction`` and ``monophyly_levels`` are ignored.  The imposed constraints will be those between ``monophyly_start_depth`` and ``monophyly_end_depth``, interpreted in a top down fashion.  This is a "low level" approach to controling monophyly, and in general the "configurational sugar" of using ``monophyly_direction``, ``monophyly_start`` and ``monophyly_levels`` should be preferred.

* ``overlap``: One of ``union`` or ``intersection``.  Controls how to deal with language sets mismatches between input data.
   * If set to ``union`` (the default), languages missing in one data set will be added with missing datapoints ("?") for all features.
   * If set to ``intersection``, only languages present in all data sets will be used.

* ``starting_tree``: Used to provide a starting tree.  Can be a Newick format tree or the name of a file which contains a Newick format tree.  If not specified, a random starting tree (compatible with monophyly constraints, if active) will be used.

* ``sample_branch_lengths``: If True, the branch lengths of the starting tree.  If False, the starting branch lengths will be kept fixed.  Use this in conjunction with ``starting_tree`` when you have a tree you trust and want to fit model parameters to it.  Default is True.

* ``sample_topology``: If true, the topology of the starting tree (i.e. the details of which leaves are connected to which and how) will be sampled during the analysis to fit the data.  If false, the topology will be kept fixed.  Use this in conjunction with ``starting_tree`` when you have a tree you trust and want to fit model parameters to it.  Default is True.


calibration section
-------------------

The ``calibration`` section should contain one parameter for each distinct calibration point that you wish to include in the analysis.

The name of each parameter should be a comma-separated list of family names or Glottocodes.  Optionally, the name can be enclosed in ``originate( )`` to place the calibration not on the MRCA of the languages/families specificed, but on the originate, i.e. the top of the branch leading to the MRCA.  The value for each calibration can be a string in one of several supported formats.  The two simplest formats are to specify a range of ages, or a single upper or lower bounding age.

Ranges can be specified as follows:

::

	Austronesian = 4750 - 5800

You may use arbitrary units without problems, i.e. you could provide dates in millenia BP:

::

	Austronesian = 4.75 - 5.8

The only time this matters is when it comes time to interpret tree heights or clock and/or mutation rates.  With this kind of calibration, BEASTling will set a normal distribution prior on the age of the family indicated.  The mean of the distribution will be equal to the midpoint of the provided range (5275 in the above case).  The standard deviation will be set such that 95\% of the probability mass will lie within the range provided.  In other words, the range you provide is treated as a 95\% credibility interval.

Bounds can be specified as follows:

::

	Austronesian = > 4750
       
or

::

        Austronesian = < 5800

With this kind of calibration, BEASTling will set a uniform distribution prior on the age of the family indicated.  The upper or lower bound will be set to the provided age, and the other bound will be set to zero or infinity as appropriate.

If you require more control over your priors, you can explicitly provide the type of distribution (either normal, lognormal or uniform) and the parameters, as well as specify an offset, as follows:

::

	Austronesian = normal(5275, 535.71)           # First param is mean, second is standard deviation
	Austronesian = lognormal(8.57, 0.05)          # First param is mean (in log space), second is standard deviation
	Austronesian = rognormal(5275, 0.05)          # First param is mean (in real space), second is standard deviation
	Iranian = 2600 + rlognormal(400, 0.8)         # As per above but with an offset

Finally, it is possible to specify an age range and ask for a lognormal distribution to be fitted to it, as follows:

::

	Austronesian = lognormal(4750 - 5800)

With this kind of calibration, BEASTling will set a lognormal distribution prior on the age of the family indicated.  The mean of the distribution will be set so that the median of the lognormal distribution equals the midpoint of the range provided.  The standard deviation will be set to the mean of two values: one with the property that the provided lower bound is at the 5th percentile of the lognormal distribution, and one with the property that the provided upper bound is at the 95th percentile.  The provided interval does not quite end up being a 95% credible interval, but it is roughly so.  Explicitly set the lognormal parameters as shown above if you need more control over the matching than this.

model sections
--------------

A BEASTling config file *must* include at least one model section, but it can contain several.  Model sections are different from almost all other sections in that you must give each one a name.  A ``[model]`` section is invalid, but ``[model mymodel]`` will work.  Suppose you want to perform an analysis using both cognate data and structural data, and you want to use different model settings for the different kinds of data (say different substitution models).  You could have a ``[model cognate]`` section and a ``[model structure]`` section.  You can have as many models as you like, as long as each one gets a unique name.

Each model section *must* contain the following parameters, i.e. they are mandatory and BEASTling will refuse to work if you ommit them:

* ``model``: should specify the name of the substitution model type you want to use.  Available models are:
   * "covarion" (Binary covarion model)
   * "bsvs" (Bayesian Stochastic Variable Selection)
   * "mk" (Lewis Mk model)

   For more information on the available models, see :doc:`substitution`.

* ``data``: should be one of:
   * A path to a file containing your language data in a compatible .csv format
   * The string "stdin" if you wish for data to be read from ``stdin`` rather than a file.

   Note that if ``data`` is a relative path, this will be interpreted relative to the current working directory when ``beastling`` is run, *not* relative to the location of the configuration file.

   Regardless of whether data is read from a file or from ``stdin``, it must be in one of the two compatible .csv formats.  These are described in :doc:`data`.  Note that BEASTling can also be made to read data from ``stdin`` by using the ``--stdin`` command line argument.

Additionally, each model section *may* contain the following parameters, i.e.  they are optional:

* ``ascertained``: "True" or "False".  Controls whether or not to perform ascertainment correction for the absence of non-constant features in the data.  This will have no effect on the sampled tree topology but will influence estimates of branch lengths and the age the tree and clades.  By default, this will be set to true if you provided any calibrations (because in this case you most likely care about estimated ages) and to false if you have not (on the assumption that in this case you are more interested in topology).  Use this parameter to make your intention explicit.  Note that if you have set ``remove_constant_features = False`` in a binary covarion analysis (see below) and your analysis does indeed contain constant features, you cannot set this parameter to "True".

* ``binarised`` or ``binarized``: "True" or "False".  This option is only relevant if the binary covarion model is being used (see :ref:`covarion`).  If your data set only contains features with two possible values, in some situations BEASTling needs to know whether this represents "true" binary data (e.g. presense or absence of some syntactic trait) or whether your data is a "binarisation" of some multistate data (such as cognate class assignments).  Set this to False for true binary data and True for binarised cognate data.

* ``clock``: Assigns the clock to use for this model.  See :ref:`clock_sections` below for details.

* ``features``: Is used to select a subset of the features in the given data file.  Should be one of:
   * A comma-separated list of feature names (as they are given in the data CSV's header line)
   * A path to a file which contains one feature name per line

   * ``file_format``: Can be used to explicitly set which of the two supported .csv file formats the data for this model is supplied in, to be used if BEASTling is mistakenly trying to parse one format as the other (which should be very rare).  Should be one of:
   * "beastling"
   * "cldf"

* ``language_column``: Can be used to indicate the column name in the .csv file header which corresponds to the unique language identifier.  If the column name is one of "iso", "iso_code", "glotto", "glotto_code", "language", "language_id", "lang" or "lang_id", BEASTling will recognise it automatically.  This parameter is only needed if you have a pre-existing data file which uses a different column name which you don't want to change (perhaps because it would break compatibility with another tool).

* ``pruned``: "True" or "False".  Make use of "pruned trees".  This can improve performance in data sets with a lot of missing data.  Default is False.

* ``rate_variation``: "True" or "False".  Estimate a separate substitution rate for each feature (using a Gamma prior).

* ``remove_constant_features``: "True" or "False".  This option is only relevant if the binary covarion model is being used (see :ref:`covarion`).  Your setting will be ignored if you are using the Lewis Mk or BSVS models, as these models cannot sensible accommodate constant features.  By default, this is set to "True", which means that if your data set contains any features which have the same value for all of the languages in your analysis (which is not necessarily all of the languages in your data file, if you are using the "families" parameter in your "languages" section!), BEASTling will automatically remove that feature from the analysis (since it cannot possibly provide any phylogenetic information).  If you want to keep these constant features in, you must explicitly set this parameter to False.  You may want to do this if you have rate variation enabled to help estimate the distribution of rates across features, but if your data set contains many constant features you should be careful about interpreting the results.

* ``minimum_data``: Indicates the minimum percentage of languages that a feature should have data present for to be included in an analysis.  E.g, if set to 50, any feature in the dataset which has more question marks than actual values for the selected languages will be excluded.

.. _clock_sections:

clock sections
--------------

``clock`` sections are quite similar to ``model`` sections, in that they must be given names, e.g. ``[clock myclock]``.  A BEASTling config file may include any number of ``clock`` sections, including zero, but it makes no practical sense to define more ``clock`` sections than you have ``model`` sections.  ``clock`` sections are used to define clock models, which determine how tree branch lengths are transformed into a measure of evolutionary time.  Each ``model`` in your analysis has an associated clock model.  You can share one clock across all your models, or give each model its own clock, or assign clocks in any other way you like.

If no ``clock`` section is defined, all models will be associated with a default clock (of ``type`` "strict").  Alternatively:

* You may define your own ``[clock default]`` section.  Because the name is ``default``, this clock will be associated with all model sections, unless those sections have a different clock specifically assigned.
* You may explicitly assign a clock to a model by setting the model section's ``clock`` option equal to the name of a ``clock`` section.
* If a ``model`` section and a ``clock`` section have the same name, then they are automatically associated with each other (unless the ``model`` section explicitly assigns a different clock.

Each clock section *must* contain the following parameters, i.e. they are mandatory and BEASTling will refuse to work if you ommit them:

* ``type``: should specify the type of clock model type you want to use.  Available models are:
   * "strict" (Strict clock)
   * "relaxed" (Uncorrelated relaxed clock)
   * "random" (Random local clock)

For more information on the available models, see :doc:`clocks`.

geography section
-----------------

Adding a ``geography`` section to your BEASTling config file will include a phylogeographic component in your analysis.  Only a single ``geography`` section can exist in a configuration file, and unlike ``clock`` and ``model`` sections, ``geography`` sections do not need to be named (i.e. do not use ``[geography mygeo]`` or similar).

A ``geography`` section does not require any parameters.  Spherical phylogeography is the only phylogeographic model currently supported.  This model requires latitude and longitude coordinates for each language in the analysis.  If your languages are labelled using Glottocodes or ISO codes, location information will automatically be sourced from Glottolog.  Languages for which Glottolog is missing location data will be excluded from the analysis (and if BEASTling is run in ``--verbose`` mode you will be notified of this).  If you are not using Glottocodes or ISO codes, you can provide your own location data using using 

Your ``geography`` section *may* optionally contain any of the following parameters.

* ``clock``: should specify the name of a clock model (just like the ``clock`` parameter in a ``[model]`` section) which will be used for the phylogeographic diffusion model.  If this is not provided, the phylogeographic model will use the analysis' default clock, which will be shared with any language models in the analysis.  In general, this is not desirable, so unless you are running a geography-only analysis, you should specify a separate geographic clock.
* ``data``: by default, phylogeographic analyses will use latitude and longitude data from Glottolog to provide the locations for languages, assuming languages are labelled with ISO codes or Glottocodes.  If your languages are not labelled this way (or Glottolog is missing location data for your languages, or you disagree with Glottolog's location and would like to override it with your own), you will need to provide your own loaction data using this parameter.  The value should be a filename, or a comma-separated list of filenames.  The files should be CSV or TSV files with at least three columns.  One should provide language identifiers which match your data, and the header should be one of the same names that are allowed for data files (i.e. ``iso``, ``iso_code``, ``glotto``, ``glottocode``, ``language``, ``language_id``, ``lang`` or ``lang_id``).  The other two should provide latitude and longitude values and should be labelled ``latitude`` or ``lat`` and ``longitude`` or ``lon`` respectively.  Latitude and longitude values should be decimal values using positive or negative sign to indicate North/South and East/West (i.e. do not use "60N" or similar formats), or question marks if they are unknown (languages with unknown location will be dropped from the analysis).  If multiple filenames are provided, later (i.e. rightmost) files will override earlier (i.e. leftmost) files if they contain locations for the same languages.  In this way you can list multiple sources of location data from least to most reliable and each language will receive the most reliable location.
* ``sampling_points``: by default, phylogeographic analyses integrate over the locations of all internal nodes in the trees.  You can ask BEAST to sample the locations for some interior points using this parameter.  Perhaps you are actually interested in inferring the location of some well-defined point in your tree (e.g. in a phylogeographic analysis of Indo-European you may be interested in the location of proto-Germanic or proto-Balto-Slavic).  Even if you are not interested in these locations, specifying some sampling points (say 5) may actually speed the analysis up somewhat, as changes to the tree topology do not require likelihood calculations to propagate all the way up the tree.  Your sampling points may be specified using Glottocodes or names from Glottolog (e.g. "Germanic").

geo_priors section
------------------

In the same way that a ``[calibration]`` section is used to add temporal calibrations to an analysis, a ``[geo_priors]`` section can be used to add spatial calibrations to an analysis.  This only makes sense for analyses which include a phylogeographic component, and if your configuration file contains a ``[geo_priors]`` section but not a ``[geography]`` section, BEASTling will complain loudly.

The name of each parameter should be a comma-separated list of family names or Glottocodes, exactly as per temporal calibrations.  The value should be a path to a `KML <https://en.wikipedia.org/wiki/Keyhole_Markup_Language>`_ file specifying a polygon which represents the region you believe the MRCA of the listed family/families should be confined to.  Note that, unlike data files, the contents of the KML file will not end up included in the BEAST XML.  This means the XML and KML file(s) will need to be distributed together for the analysis to be reproducable.
