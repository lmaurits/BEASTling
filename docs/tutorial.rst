========
Tutorial
========

This tutorial will explain step-by-step how to use BEASTling to set
up, configure, run and analyze a Bayesian phylogenetic analysis of
language data.  As an example, we will use data from the Austronesian
language family, both lexical and structural data.

First, create a new empty directory. We will collect 

Lexical data of austronesian languages is part of `Lexibank`_ in the
cross-linguistic data format supported by beastling. The Austronesian
Basic Vocabulary Dataset [1]_ which Lexibank provides comes from
Auckland's `ABVD`_ project and is licensed under a `CC-BY` 4.0 license.

The first step is to download the lexical data from Lexibank.

    $ curl -OL https://lexibank.clld.org/contributions/abvd.csv

This places the 

.. `Lexibank`: ???
.. `ABVD`: http://language.psy.auckland.ac.nz/austronesian/
.. 1: Greenhill, S.J., Blust. R, & Gray, R.D. (2008). The Austronesian Basic Vocabulary Database: From Bioinformatics to Lexomics. Evolutionary Bioinformatics, 4:271-283.
.. `CC-BY`: https://creativecommons.org/licenses/by/4.0/ 
