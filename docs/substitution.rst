===================
Substitution models
===================

BEAST models discrete data as evolving on a phylogenetic tree according to a Continuous Time Markov Chain.

When configuring a BEASTling analysis, for each model you must choose a substitution model.  Different substitution models are more or less appropriate for different kinds of data.  The following substitution models are currently supported:

Mk
--

(set ``model=mk`` in config file)

The `Lewis Mk model <http://sysbio.oxfordjournals.org/content/50/6/913.abstract>`_ is the simplest generic substitution model available in BEASTling.  It is a generalisation of the classic `JC69 <https://en.wikipedia.org/wiki/Models_of_DNA_evolution#JC69_model_.28Jukes_and_Cantor.2C_1969.29.5B1.5D>`_ model from genetics to a statespace of arbitrary size.  Transitions are possible from any state to any other state, and every transition is equally probable.  No parameters are estimated, increasing analysis speed.  This model could be used with any dataset, but the assumptions are not a good match for cognate data.

.. _covarion:

Binary Covarion
---------------

(set ``model=covarion`` in config file)

The binary Covarion model is defined for binary datasets, i.e. sets where every datapoint is either a 0 or a 1.  This model introduces a latent "fast" or "slow" state, which controls the rate of transitions between 0 and 1 (transitions in either direction are always equally probable).  This model is typically used for cognate data.

When the binary Covarion model is used, if the specified datafile contains multistate data, BEASTling will automatically translate this into the appropriate number of binary features.  This approach means that you can have a single data file which can be used to generate binary and multistate analyses, and also lets BEASTling share mutation rates across binary features corresponding to a single multistate feature.  This is the recommended way to use the binary Covarion model.

However, if you have pre-binarised data you wish to use, BEASTling should recognise this (by seeing that all features in the dataset have only two possible values) and will avoid binarising it a second time.  Note that when used this way, BEASTling will assign separate mutation rates to each binary feature, as it has no way to know which groups of binary features originally corresponded to a single multistate feature.

If BEASTling decides to treat your data as pre-binarised, a notification will be emitted in ``--verbose`` mode.  You can use the ``binarised`` (or ``binarized``) option in your config's ``[model]`` section to tell BEASTling explicitly whether or not your data has been binarised, and this will disable the automatic detection.

BSVS
----

(set ``model=bsvs`` in config file)

The Bayesian Stochastic Variable Selection (BSVS) model is a rich model suitable for structural data.  Compared to the Lewis Mk model, it permits non-equal transition probabilities between different states, and also tries to set a number of probabilities to zero, i.e. transitions from some states to others will be disallowed.  This model is suitable for attempting to uncover preferential directions of change in the evolution of particular linguistic features.  Note that this model is very parameter intensive and analyses will be much slower than Mk analyses for the same data.

A ``bsvs`` model accepts two additional parameters, ``symmetric`` and ``svsprior``.
They change the behaviour as follows.

A symmetric model (``symmetric=True``, which is the default value) assumes that transition rates between states are symmetric, i.e. for two states A and B, transitions from A to B occur at the same rate as transitions from B to A. An asymmetric model (``symmetric=False``) has double the number of parameters, because the rates A→B and B→A are estimated separately.

The ``svsprior`` property specifies the shape of the prior distribution which is placed over the number of non-zero rate.  Possible choices are ``poisson'' and ``exponential``, with ``poisson`` being the default.

The size of the statespace for a particular feature determines a maximum possible number of non-zero rates (the entire matrix), and also a minimum possible number (to ensure that the Markov chain is ergodic).  The non-zero rate prior is defined over this range, so both the Poisson and exponential priors have an offset, rather than beginning their support at zero.

The default Poisson prior is the more conservative choice.  BEASTling will set the mean of the Poisson distribution equal to the midpoint between the minimum and maximum possible number of non-zero rates.  In this way, the model has no strong preference for sparse matrices over dense matrices or vice versa (as the mean of the Poisson is usually approximately equal to the median), while still encouraging the setting of rates to zero if the data supports it.

The exponential prior, on the other hand, is biased toward sparse transition matrices.  BEASTling will set the mean of the exponential distribution such that 99% of the probability density lies between the minimum and maximum possible number of non-zero rates.  In this way, matrices with the majority of rates set to zero are much more probable a priori than matrices with the majority of rates being non-zero.  This prior is the better choice when you want to fit a model that permits the minimum number of transitions required to explain the data.
