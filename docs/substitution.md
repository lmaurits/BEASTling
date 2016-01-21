# Substitution models

BEAST models discrete data as evolving on a phylogenetic tree according to a Continuous Time Markov Chain.

When configuring a BEASTling analysis, for each model you must choose a substitution model.  Different substitution models are more or less appropriate for different kinds of data.  The following substitution models are currently supported:

## Mk

(set `model=mk` in config file)

The [Lewis Mk model](http://sysbio.oxfordjournals.org/content/50/6/913.abstract) is the simplest generic substitution model available in BEASTling.  It is a generalisation of the classic [JC69](https://en.wikipedia.org/wiki/Models_of_DNA_evolution#JC69_model_.28Jukes_and_Cantor.2C_1969.29.5B1.5D) model from genetics to a statespace of arbitrary size.  Transitions are possible from any state to any other state, and every transition is equally probable.  No parameters are estimated, increasing analysis speed.  This model could be used with any dataset, but the assumptions are not a good match for cognate data.

## Binary Covarion

(set `model=covarion` in config file)

The binary Covarion model is suitable *only* for use with binary datasets, i.e. sets where every datapoint is either a 0 or a 1 (the most common example of this kind would be cognate class data which has been "binarised" in the traditional fashion).  This model introduces a latent "fast" or "slow" rate, which controls the rate of transitions between 0 and 1 (transitions in either direction are always equally probable).

## BSVS

(set `model=bsvs` in config file)

The Bayesian Stochastic Variable Selection (BSVS) model is a rich model suitable for structural data.  Compared to the Lewis Mk model, it permits non-equal transition probabilities between different states, and also tries to set a number of probabilities to zero, i.e. transitions from some states to others will be disallowed.  This model is suitable for attempting to uncover preferential directions of change in the evolution of particular linguistic features.  Note that this model is very parameter intensive and analyses will be much slower than Mk analyses for the same data.
