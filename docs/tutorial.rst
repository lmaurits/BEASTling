========
Tutorial
========

This tutorial will explain step-by-step how to use BEASTling to set
up, configure, run and analyze a Bayesian phylogenetic analysis of
language data.  As an example, we will use data from the Austronesian
language family, both lexical and structural data.

BEASTling is a command line tool. The actual analysis tool, BEAST 2,
is most easily run from the command line interface, as well. We will
therefore begin by giving you a very short introduction to working
with the command line, which you can skip and go directly to
`Installation`_. If you have BEASTling and BEAST 2 installed and
accessible from your CLI, skip further to `Using BEASTling`_.

Fundamentals
------------

While you may be used to driving applications by pointing and clicking
with the mouse and very occasionally typing text, command-line
interfaces (CLI) use text commands to drive computer programs.

In some sense similar to human language, these text commands must obey
a specific syntax to be understood (but as opposed to human language,
if you don't follow the syntax strictly, nothing will happen), and
this syntax powers compositionality, which makes automatising complex
or repetitive tasks easier.  In addition, the text representation
means that command line instructions can be easily copied, shared,
reproduced, and modified.

BEASTling was created to automatise complex tasks and improve
reproduceability and adaptation for Bayesian inference on linguistic
data, so it has naturally been implemented as a command line tool –
and this part of the tutorial is there to ensure that BEASTling does
not fail its goal to make using inference tools less daunting just by
living on the CLI.

So here are some instructions to get you started using that powerful tool.

The CLI application, where you type commands and see their outputs,
is called a shell.

The most common shell these days is `bash` (or variants thereof),
which is the default on Linux and Mac systems in the Terminal
application. By default, Windows systems only include the Command
Prompt, which you can start by looking for `cmd.exe` and running
that. The Command Prompt is far less flexible and user-friendly than
other available shells, but sufficient for running beastling.

If you are working under windows, you will need a working Python
installation to run beastling, for which you will install `Anaconda`_
in the next section. Anaconda gives you a Command Prompt set up to
work more cleanly with its Python installation under the name Anaconda
Prompt. For the matters of this introduction to the command line,
Command Prompt and Anaconda Prompt are interchangeable.

Now, start your shell – open a Terminal application, start `cmd.exe`
or run an Anaconda Prompt, whichever is available to you. You should
now have a window that displays you some text – often some information
about you, then a directory name (where `~` means “your home
directory”) and then a prompt symbol (`$` or `>`), before a cursor.

Type `dir` and press Enter. The shell should show you the contents of
the directory you are in, which is probably your home directory.
For the remainder of this tutorial, we will use the notation

    $ echo Example Command
    Example Command

to show you what to type on the command line and what to expect as output.

The two lines above mean that you should type `echo Example Command`
after the prompt symbol (which may be `>` instead of `$`, if you are
working on Windows), and expect the output `Example Command`.
Sometimes, we will abbreviate the expected output, and write `[...]`.

It is important to know how to navigate the file system on the command
line, otherwise you will be stuck running all analyses inside your
home directory! So let us create a new directory

    $ mkdir example_directory

and step inside with the `cd` (“change directory”) command.

    $ cd example_directory
    $ dir

As you can see, this directory is empty – on the bash, `dir` outputs
nothing, while it lists two `<DIR>`ectories `.` and `..` on
Windows. These two directories are special: they are this directory
`example_directory` and its parent directory, where we have just come
from, respectively. We can use these special directories to move up
using `cd`:

    $ cd ..
    $ dir
    [... The same output as before, and the new directory:]
    example
    [...]
    $ cd example_directory

Paths like this can be compbined using `/`, so if you are inside `example_directory`,

    $ cd ../example_directory

will do nothing. This knowledge should allow you to go from any
directory to any other directory on your hard drive, and on Windows,
you can use your other hard drive's letter, such as `D:`, as a command
to change hard drives. (Under Linux, other hard drives etc. just
behave like any other directory, so you change hard drives like you
change directories.)

Unfortunately, the Command Prompt and `bash` understand
different languages. For example, while in `bash`, we might have

    $ echo This text is put into a file. > file.txt
    $ dir
    file.txt
    $ cat file.txt
    This text is put into a file.

The `cat` command does not exist in Windows, as the Prompt will tell
you: `'cat' is not recognized as an internal or external command,
operable program or batch file.` There is however a Windows command
called `type` that you can use in place of `cat`, which will output
the content of a file.  In this tutorial, we will use the language of
`bash` to give coded examples, but where needed we will give a Windows
command or a way outside the CLI to achieve the same result.

Installation
============

BEASTling is written in the `Python programming language`_, `BEAST 2`_
is written in `Java 8`_. We will therefore first have to install these
core dependencies.

Java 8
------
`Java 8`_ can be obtained from …

BEAST 2
-------
If you have a working Java 8 installation, download BEAST 2 from …

Install packages …

Python
------
Most current Linux distributions come with a pre-packaged Python
installation. If your python version (which you can see by running
`python --version` in a shell) is lower than 2.7, you will want to
upgrade your Python in the way you usually install new software.

If you want to run BEASTling on Windows, we recommend the `Anaconda`_
Python distribution. To install it, visit
https://www.continuum.io/downloads and download and run the Python 3.5
installer for your system.

BEASTling and its Python dependencies
-------------------------------------

If you want to control the details of your installation, refer to
`installation`_ instructions here in the BEASTling
documentation. Otherwise, BEASTling is available from the `Python
Package Index`_, which is easily accessible using the `pip` command
line tool, so it will be sufficient to run

    $ pip install beastling
    [...]

in order to install the package and all its dependencies.

All current Python versions (above 2.7.9 and above 3.4) are shipped
with `pip` – if you have an older version of Python installed, either
check how to get `pip` `elsewhere`_, consider upgrading your Python or
check the `installation` chapter for alternative installation
instructions.

Using BEASTling
===============

First, create a new empty directory. We will collect the data and run
the analyses inside that folder. Open a command line interface, and
make sure its working directory is that new folder. For example,
start terminal and execute

    $ mkdir indoeuropean
    $ cd indoeuropean

For this tutorial, we will be using lexical data, i.e. cognate judgements,
for a small set of Indo-European languages.  The data is stored in CLDF
format in a csv file called `ie_cognates.csv` which can be
downloaded as follows:

    $ curl -OL https://raw.githubusercontent.com/lmaurits/BEASTling/master/docs/tutorial_data/ie_cognates.csv

(curl is a command line tool do download files from URLs, available
under Linux and Windows. You can, of course, download the file
yourself using whatever method you are most comfortable with, and save
it as `.csv` in this folder.)

If you look at this data, using your preferred text editor or
importing it into Excel or however you prefer to look at csv files,
you will see that

    $ cat ie_cognates.csv
    Language_ID,Feature_ID,Value
    [...]

it is a comma-separated `CLDF`_ file, which is a format that BEASTling
supports out-of-the-box.

So let us start building the most basic BEASTling analysis using this
data. Create a new file called `ie_vocabulary.conf` with the
following content:

    ::
           [model ie_vocabulary]
           model=covarion
           data=ie_cognates..csv
    --- ie_cognates.conf

This is a minimal BEASTling file that will generate a BEAST 2 xml
configuration file that tries to infer a tree of Indo-European
languages from the dataset using a binary Covarion model.

Let's try it!

    $ beastling ie_vocabulary.conf
    $ dir
    [...]
    beastling.xml
    [...]
    $ cat beastling.xml
    <?xml version='1.0' encoding='UTF-8'?>
    <beast beautistatus="" beautitemplate="Standard" namespace="beast.core:beast.evolution.alignment:beast.evolution.tree.coalescent:beast.core.util:beast.evolution.nuc:beast.evolution.operators:beast.evolution.sitemodel:beast.evolution.substitutionmodel:beast.evolution.likelihood" version="2.0">
    <!--Generated by BEASTling [...] on [...].
    Original config file:
    [model ie_vocabulary]
    model=covarion
    data=ie_cognates.csv

    -->
    [...]
    </beast>

We would like to run this in BEAST to test it, but the `default chain
length`_ of 10000000 will make waiting for this analysis to finish tedious
(over an hour on most machines).  Because this is a small data set, we can
get away with a shorter chain length (we will discuss how to tell what chain
length is required later), so let's reduce it for the time being:

    ::
           [MCMC]
           chainlength=500000
           [model ie_vocabulary]
           model=covarion
           data=ie_cognates..csv
    --- ie_cognates.conf

Now we can run `beastling` again (after cleaning up the previous
output) and then run BEAST.

    $ rm beastling.xml
    $ beastling ie_vocabulary.conf
    $ beast beastling.xml
    Loading package [...]
    [...]

                                BEAST v2.4.3, 2002-2016
                 Bayesian Evolutionary Analysis Sampling Trees
                           Designed and developed by
     Remco Bouckaert, Alexei J. Drummond, Andrew Rambaut & Marc A. Suchard
     [...]
     ===============================================================================
     Start likelihood: [...]
     [...]
         Sample ESS(posterior)          prior     likelihood      posterior
     [...]
     
When BEAST has finished running, you should see two new files in your directory:

    $ dir
    [...]
    beastling.log       beastling.nex   beastling.xml
    [...]

beastling.log is a log file which contains various details of each of the 10,000 trees sampled in this analysis, including their prior probability, likelihood and posterior probability, as well as the height of the tree.  In more complicated analyses, this file will contain much more information, like rates of change for different features in the dataset, details of evolutionary clock models, the ages of certain clades in the tree and more.

beastling.log is a tab separated value (tsv) file.  You should be able to open it up in a spreadsheet program like Microsoft Excel, LibreOffice Calc or Gnumeric.

Let's look at the first few lines of the log file.

    $ head beastling.log
    Sample  prior   likelihood      posterior       treeHeight      YuleModel.t:beastlingTree       YuleBirthRatePrior.t:beastlingTree
    0       -8.98027012415235       -5608.380912705009      -5617.361182829161      1.6496578223508276      -6.504751489982865      0.0
    50      -8.82660343639428       -4626.223799582827      -4635.050403019221      2.4856227018065336      -6.432641217317366      0.0
    100     -7.333592357522035      -4244.591121595498      -4251.924713953021      1.7075847960102366      -4.939630138445121      0.0
    150     -3.4357217516230563     -4023.480891489457      -4026.91661324108       1.6559813844895233      -1.0417595325461422     0.0
    200     5.415801393056513       -3921.446533036334      -3916.0307316432777     0.85850188293608        7.809763612133427       0.0
    250     3.7952776836081137      -3907.6460566063784     -3903.85077892277       0.9697813606913859      6.189239902685028       0.0
    300     8.322120011155945       -3608.78640895754       -3600.464288946384      0.8648651865647997      10.716082230232859      0.0
    350     9.76865513833624        -3374.804298810213      -3365.0356436718766     0.5743386655139796      12.162617357413152      0.0
    400     15.039986971266185      -3337.727626512908      -3322.687639541642      0.4267277279981509      17.4339491903431        0.0

(head is a command available in most Unix-based platforms like Linux and OS X which prints the first 10 lines of a file.  You can just look at the first ten rows of your file in Excel or similar if you don't have head available)

Don't panic if you don't see exactly the same numbers in your file.  BEAST uses a technique called Markov Chain Monte Carlo (MCMC) which is based on random sampling of trees, so every run of a BEAST analysis will give slightly different results, but the overall statistics should be the same from run to run.  Imagine tossing a coin 100 times and writing down the result.  If two people do this and compare the first 10 lines of their results, they will not see exactly the same sequence of heads and tails, and the same is true of two BEAST runs.  But both people should see roughly 50 heads and roughly 50 tails over all 100 tosses.

Even though you will have different numbers, you should see the same 6 columns in your file.  Just for now, we will focus on the first five.  The Sample column simply indicates which sample each line corresponds to.  We asked BEAST to draw 500,000 samples (with the chain_length setting).  Usually, not ever sample in an MCMC analysis, because consecutive samples are too similar to one another.  Instead, some samples are thrown away, and samples are kept at some periodic interval.  By default, BEASTling keeps enough samples so that the log file contains 10,000 samples.  In this case, this means keeping every 50th sample, which is why we see 0, 50, 100, 150, etc in the first column.  The next three columns, prior, likelihood and posterior, record the important probabilities of the underlying model:  the prior probability of the tree and any model parameters, the likelihood of the data under the model, and the posterior probability which is the product of these two values.  These probabilities are stored logarithmically, e.g. the probability 0.5 would be stored as -0.69, which is the natural logarithm of 0.5.  This simply makes it easier for computers to store very small numbers, which are common in these analyses.  The fifth column, treeHeight, records the height of each of the sampled trees (the sum of all the branch lengths from the root to the leaves).  Later, we will provide calibration dates for some of the Indo-European languages, and then the treeHeights will be recorded in units of years, and these values will give us an estimate of the age of proto-Indo-European.  However, in this simple analysis, we have no calibrations, so the treeHeight is in units of the average number of changes which have happened in the data from the root to the leaves.

Log files like this one are usually inspected using specialist tools to extract information from them (such as the mean value of a parameter across all samples, which is commonly used as an estimate of the parameter).  A tool called Tracer is distributed with BEAST and can be used for this task.  We will discuss using Tracer later.  For now, let's turn our attention to the other log file.

beastling.nex is a tree log file which contains the actual 10,000 sampled trees themselves.  This file is in a format knows as Nexus, which itself expresses phylogenetic trees in a format known as Newick, which uses nested brackets to represent trees.  If you open this file in a text-editor like Notepad and scroll down a little, you will be able to see these Newick trees, but they are very hard to read directly, especially for large trees.  Instead, these files can be visualised using special purpose programs, which makes things much easier.  FigTree is a popular example.  Let's take a look at our trees!

Remember there are 10,000 trees saved in the beastling.nex file.  When you open the file in FigTree, by default it will show you the first one in the file (which corresponds to sample 0 in the beastling.log file).  There are Prev/Next arrows near the top right of the screen which let you examine each tree in turn.  The first tree in the file is the starting point of the Markov Chain, and BEAST chooses it at random.  So the first tree you are looking at will probably not look like a plausible history of Indo-European!  Here is an example:

.. image:: images/tutorial_tree_01.png

Once again, you should not expect to see the exact same tree in your file.  But you should have a random tree which does not reflectt what we know about Indo-European.  However, regardless of the random starting tree, the consecutive sampled trees will tend to have a better and better match to the data.  Let's look at the 10,000th and final tree in the file, which should look better:

.. image:: images/tutorial_tree_02.png

Here the Germanic, Romance and Slavic subfamilies have been correctly separated out, and the Germanic family is correctly divided into North and West Germanic.  You should see similar good agreement in your final tree, although the details may differ from here, and the fit might not be quite as good.  Bayesian MCMC does not sample trees which strictly improve on the fit to data one after the other.  Instead, well-fitting trees are sampled more often than ill-fitting trees, with a sampling ratio proportional to how well they fit.  So there is no guarantee that the last tree in the file is the best fit, but it will almost certainly be a better fit than the first tree.

Just like tools like Tracer are used on log files to summarise all of the 10,000 samples into a useful form, like the mean of a parameter, there are tools to summarise all of the 10,000 trees to produce a so-callled "summary tree".  One tool for doing this is distributed with BEAST and is called treeannotator.  If you are an advanced command line user you may like to use the tool "phyltr", which is also written by a BEASTling developer.

More advanced modelling
=======================

Our BEASTling analyses so far have had very short and neat configuration, but have not been based on a terribly realistic model of linguistic evolution, and so we may want to make some changes.  We will continue to use the Austronesian vocabulary example here, but everything in this section should be equally applicable to the typological analysis as well.

The main oversimplification in the default analysis is the treatment of the rate at which linguistic features change.  The default analysis makes two simplifications: first, all features in the dataset change at the same rate as each other.  Secondly, it assumes that the rate of change is fixed at all points in time annd at all locations on the phylogenetic tree.  BEASTling makes it easy to relax either of these assumptions, or both.  The cost you pay is that your analysis will not run as quickly, and you may experience convergance issues.

Rate variation
--------------

You can enable rate variation by adding `rate_variation = True` to your `[model]` section, like this:

    ::
           [model austronesian_vocabulary]
           model=mk
           data=abvd.csv
           rate_variation=True
    --- austronesian_vocabulary.conf

This will assign a separate rate of evolution to each feature in the dataset (each meaning slot in the case of our cognate data).  The words for some meaning slots, such as pronouns or body parts, may change very slowly compared to the average, while the words for other meaning slots may change very slowly.  With rate variation enabled, BEAST will attempt to figure out relative rates of change for each of your features.

Rebuild your XML file and run BEAST again:

(shell output here)

Permitting rate variation can impact the topology of the trees which are sampled.  If two languages have different words for a meaning slot which evolves very slowly, this is evidence the the languages are only distantly related.  However, if two languages have different words for a meaning slot which evolves rapidly, then this does not necessarily mean they cannot be closely related.  This kind of nuanced inference cannot be made in a model where all features are forced to evolve at the same rate, so the tree topology which comes out of the two models can differ significantly.  Let's look at our new trees:

(FigTree output here)

Clock variation
---------------

If you want the rate of language change to vary across different branches in the tree, you can specify your own clock model.

    ::
           [model austronesian_vocabulary]
           model=mk
           data=abvd.csv
           rate_variation=True
           [clock default]
           type=relaxed
    --- austronesian_vocabulary.conf

Here we have specified a relaxed clock model.  This means that every branch on the tree will have its own specific rate of change.  However, all of these rates will be sampled from one distribution, so that most branches will receive rates which are only slightly faster or slower than the average, while a small number of branches may have outlying rates.

Adding calibrations
-------------------

The trees we have been looking at up until now have all had branch lengths expressed in units of expected number of substitutions, or "change events", per feature.  One common application of phylogenetics in linguistics is to estimate the age of language families or subfamilies.  In order to do this, we need to calibrate our tree by providing BEAST with our best estimate of the age of some points on the tree.  If we do this, the trees in our .nex output file will instead have branch lenghts in units which match the units used for our calibration.

Calibrations are added to their own section in the configuration file:

(research sensible Austronesian calibrations and put some in here)

Adding geography
-------------------

.. `Lexibank`: ???
.. `ABVD`: http://language.psy.auckland.ac.nz/austronesian/
.. 1: Greenhill, S.J., Blust. R, & Gray, R.D. (2008). The Austronesian Basic Vocabulary Database: From Bioinformatics to Lexomics. Evolutionary Bioinformatics, 4:271-283.
.. `CC-BY`: https://creativecommons.org/licenses/by/4.0/ 
.. `CLDF`: https://github.com/glottobank/cldf
