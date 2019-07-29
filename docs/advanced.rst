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

.. NOTE::
  This reconstruction reports internal states of the model. For example, the
  internal hot states of the :ref:`covarion` model are shown in the output, so
  eg. when running ASR using the covarion model, you will see ``a`` for the
  hot-0 state and ``b`` for the hot-1 state, in addition to ``0`` and ``1`` for
  presence and absence of a class.

By default, all features specified in this manner will be reconstructed at the
root of the tree. The option ``reconstruct_at`` can be used to modify this
behavior.

You can specify one :ref:`language_group`, or multiple ones separated by comma,
for ``reconstruct_at``. The ancestral states will then be reconstructed for the
most recest common ancestor (MRCA) of each of these groups of languages. Unless
you also specify :ref:`monophyly_constraints`, the MRCA may vary widely between
trees and may also be an ancestor of languages outside the language group you
specified!

If you add ASR for one or multiple language groups to an analysis, in addition
to the standard logs, a log with the suffix ``_reconstructed.log`` will be
written, with sampled values for the reconstructed features included. This file
contains tab-separated reconstructions for all features to be reconstructed, for
each MRCA specified.

.. WARNING::
  Currently, BEASTling uses a somewhat naïve way of logging ancestral states
  shipped with standard beast packages. Among other things, this
  AncestralStateLogger class does not permit more than one MRCA to be
  reconstructed and generates sub-par output.

Alternatively, it is possible to reconstruct ancestral states for every node in
the tree. If you set ``reconstruct_at = *``, BEAST will output a file ending in
``_reconstructed.nex``, which a Nexus file with a (nonstandard) node annotation.
Every node obtains a comment (some text between ``[&`` and ``]``), which is a
comma-separated list of strings of the form ``feature1="0011``, with each digit
corresponding to one column of the alignment for ``feature1``.

Examples
~~~~~~~~

Given appropriate data, the following snippet ::

    [language_groups]
    west_germanic = deu,eng,nld

    [model vocabulary]
    data = european_vocabulary
    model = covarion
    reconstruct = mountain,I
    reconstruct_at = west_germanic

could be used to reconstruct the binary classes for the meanings ‘I’ and
‘mountain’ for the most recent common ancestor of these west germanic languages.
If Flemish was included in the data and consistently grouped as sister language
of Dutch, the reconstruction would occur in the common ancestor of German,
English, Dutch and Flemish. The output might look like this::

    Sample	west_germanic:mountain0	west_germanic:mountain1	west_germanic:mountain2	west_germanic:I0	west_germanic:I1
    0	0	1 a	1	0
    1000	0	b 0	1	0
    2000	0	1 b	1	0
    3000	0	1 0	1	0

and would idicate that class 0 for the meaning ‘mountain’ is reconstructed for
this node in none of the sampled generations, class 1 in 100% of the samples
(sometimes as a hot-presence), and class 2 in 25% of the trees (and then only
hotly). For the two forms of ‘I’ observed in the data, the first (``I0``) is
reconstructed in 100% of all cases, the other one never.

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
* ``steps``: The total number of chains to use in forming a path from prior
  to posterior.  Default is 8.
