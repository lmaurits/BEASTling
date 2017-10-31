=================
Advanced features
=================

Ancestral state reconstruction
------------------------------

You can use Ancestral State Reconstruction (ASR) to infer the values of
linguistic features (either structural features of cognate judgements) at
points of the phylogenetic tree other than the leaves (such as at the root, or
at the MRCA of monophyletic clades).  For example, in analysing WALS data you
might be interested in inferring the word order of proto-Austronesian.

ASR can be enabled on a model-per-model basis, by using the ``reconstruct``
option in any ``[model]`` section of your config.  The value of this option
should be set to a comma-separated list of the particular features/meaning
classes in that model which you would like to reconstruct values for.  You can
reconstruct all features in a model by setting ``reconstruct = *``.

If you add ASR to an analysis, in addition to the standard Nexus tree log, a
second log with the suffix ``_reconstructed`` will be written, with sampled
values for the reconstructed features included.

Path sampling
-------------

Model selection in a Bayesian framework is best performed using `Bayes Factors
<https://en.wikipedia.org/wiki/Bayes_factor>`_ (BFs).  BFs between models are
computed using each model's marginal likelihood (the expected value of the
likelihood when integrating over all model parameters, weighted by their prior
probability).  Unfortunately, marginal likelihoods are difficult and
computationally expensive to compute reliably.  The current gold standard is
to use an approach known as path sampling.  BEAST supports path sampling, but
using it is not quite straightforward.

Path sampling involves running multiple MCMC chains.  One of these samples from
the posterior, just like a standard BEAST analysis.  Another samples from the
prior (just as if you'd added ``sample_from_prior=True`` to ``[MCMC]``).  The
others sample from distributions which are somewhere inbetween these two - they
provide a "path" from the prior to the posterior.  The number of steps in the
path can be customised (see below), but defaults to 8.  Once all 8 chains are
run, the logs from each are combined to get an estimate of the marginal
likelihood.  BEAST gives you a lot of control over how all this is performed.

The simplest possible approach to path sampling using BEASTling is to add
``path_sampling = True`` to the ``[MCMC]`` section of your configuration.  This
will produce a single XML file as usual, and when you tell BEAST to run using
this file, BEAST will run all 8 MCMC chains, perform the log combination, and
report the estimated marginal likelihood.  This is just as easy as doing a
standard BEAST run, with the downside that it takes much longer because all 8
chains have to run.

One way to speed things up is to run the 8 chains separately on different
computers.  This saves time, but has the disadvantage that BEAST can't combine
the different log files to calculate the marginal likelihood for you.  You need
to do this as a manual step yourself after all 8 BEAST runs have finished and
you've moved the log files to the one location.  To take this approach, add
``do_not_run = True`` to the ``[MCMC]`` section of your configuration.  When you
feed BEAST the resulting XML file, it will not run any of the analyses, but will
create 8 individual XML files in a directory named (by default)
``basename_path_sampling``, where ``basename`` is the value set in your
``[admin]`` section (the XML files will actually be in subdirectories ``step0``,
``step1``, ``step2``, etc.).  You can then run these XML files individually on
separate computers, on a HPC cluster, etc.  For a brief guide on how to
manually combine the results after these separate runs, see
`the BEAST 2 website <https://beast2.org/path-sampling/>`_.

Regardless of whether you let BEAST run all of your chains or whether you do it
manually, you can add the following options to your ``[MCMC]`` section to
customise a path sampling analysis:

* ``alpha``: This parameter is used to control how the distributions sampled by
  the different chains move from the prior to the posterior.  Each chain samples
  from the poduct of the prior raised to some power ``x`` and the posterior
  raised to the power ``1-x``.  When ``x=0`` we are sampling the posterior and
  when ``x=1`` we are sampling the prior.  If ``x`` is inbetween these two
  values, we are sampling some mix of the two.  In path sampling, the different
  values of ``x`` are chosen from the quantiles of a Beta distribution with
  parameters ``alpha`` and 1.0.  The default value is 0.3 and you shouldn't
  change this unless you know what you're doing.
* ``log_burnin``: percentage of samples from all chains except the first (see
  below) to discard as burnin before calculating marginal likelihood.  Default
  is 50%.
* ``preBurnin``: number of samples (not percentage!) to discarded as burnin from
  the first chain.  By default this is calculated using the regular ``burnin``
  and ``chainlength`` options.
* ``nrOfSteps``: The total number of chains to use in forming a path from prior
  to posterior.  Default is 8.
