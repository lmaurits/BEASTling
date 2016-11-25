============
Clock models
============

The branch lengths of trees in BEAST need to be converted to some measure of evolutionary time in order to compute transition probabilities.  For example, if you have provided calibration dates, then the branch lengths of your tree are in the same units as your calibration data (typically years or kiloyears), but they need to be in units of expected substitutions in order to assess how well the tree fits the data.  This conversion is performed by a clock model.  Clock models may be very simple, such as specifying a single, unchanging expected number of substitutions per unit of branch length (e.g. substitutions per year) which is valid all over the tree, or more complex, with each branch on the tree having a different conversion rate, corresponding to changes in the rate of evolution over time and/or space.

When configuring a BEASTling analysis, each substitution model you configure in a ``model`` section must be associated with a clock model (via a ``clock`` section), and there are several clock models to choose from.  The following clock models are currently supported:

Strict
------

(set ``type=strict`` in config file)

A strict clock is the simplest clock model available in BEASTling.  It is basically a single value which represents a conversion rate between branch lengths and evolutionary time.  This same value is valid over all branches on the tree.  Strict clocks are simple and result in fast-running analyses, but they represent an assumption about language change which most linguists do not believe is plausible for most situations, i.e. that the rate at which a particular feature changes is fixed at all points in time and all subfamilies in a tree.

Uncorrelated Relaxed Clock
--------------------------

(set ``type=relaxed`` in config file)

`Uncorrelated relaxed clocks <http://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.0040088>`_ allow each branch of a phylogenetic tree to have its own clock rate.  This is in contrast to a strict clock where one rate is applied all over the tree.  These are called "uncorrelated" because the rate at one branch does not depend upon the rate at the branch immediately above it.  This means that the rate of evolutionary change can potential change abruptly, i.e. going from fast to slow or slow to fast at a single point, rather than needing to "accelerate smoothly" over multiple branching events.

The different rates are sampled from a probability distribution, whose parameters are also sampled by the MCMC chain.  The supported distributions are `Lognormal <https://en.wikipedia.org/wiki/Log-normal_distribution>`_ (add ``distribution=lognormal`` to the config file's ``clock`` section), `Exponential <https://en.wikipedia.org/wiki/Exponential_distribution>`_ (add ``distribution=exponential`` to the ``clock`` section) and `Gamma <https://en.wikipedia.org/wiki/Gamma_distribution>`_ (``distribution=gamma``).

The relaxed clock implementation in BEAST works by assigning each branch one rate from a fixed number of discrete rates.  The number of discrete rates can be set using the ``rates`` option in the config file.  For example, if rates were set to 11, the provided distribution would be sampled at the 0.0, 0.1, 0.2,..., and 1.0 quartiles, and each branch would be assigned one of these 11 rates.  Lower numbers of rates resulting in better Markov chain mixing, but result a less accurate representation of the underlying distribution, and may skew estimates of the clock rate's mean or standard deviation.  If no rate count is explicitly set, the number of discrete rates will be set equal to the number of branches in the tree.

Random Local Clock
------------------

(set ``type=random`` in config file)

`Random local clocks <http://bmcbiol.biomedcentral.com/articles/10.1186/1741-7007-8-114>`_ permit an amount of variation in clock rate across a tree which is more than the strict clock (which has no variation) but less than the relaxed clock (which has a different rate for each branch).  They work by permiting the clock rate to change a fixed number of times at certain locations on the tree.  The number of changes may be zero (in which case the resulting clock is a strict clock), or it may be equal to the number of branches (in which case the resulting clock is a relaxed clock), or it may be somewhere in between.  The MCMC chain samples over both the number of changes and their locations on the tree.  A Poisson prior is placed on the number of changes.

The various rates are sampled from a Gamma distribution.  The random local clock can be configured in uncorrelated mode (``correlated=false``, the default), where each rate is sampled independently from the Gamma distribution, and in correlated mode (``correlated=true``), where what are sampled from the Gamma distribution are *multipliers*, with each new rate being a scaling of the rate before the change point.

