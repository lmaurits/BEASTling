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

    $ mkdir austronesian
    $ cd austronesian

Lexical data of austronesian languages is part of `Lexibank`_ in the
cross-linguistic data format supported by beastling. The Austronesian
Basic Vocabulary Dataset [1]_ which Lexibank provides comes from
Auckland's `ABVD`_ project and is licensed under a `CC-BY` 4.0 license.

The first step is to download the lexical data from Lexibank.

    $ curl -OL https://lexibank.clld.org/contributions/abvd.csv

(curl is a command line tool do download files from URLs, available
under Linux and Windows. You can, of course, download the file
yourself using whatever method you are most comfortable with, and save
it as `abvd.csv` in this folder.)

If you look at this data, using your preferred text editor or
importing it into Excel or however you prefer to look at csv files,
you will see that

    $ cat abvd.csv
    Language_ID,Feature_ID,Value
    [...]

it is a comma-separated `CLDF`_ file, which is a format that BEASTling
supports out-of-the-box.

So let us start building the most basic BEASTling analysis using this
data. Create a new file called `austronesian_vocabulary.conf` with the
following content:

    ::
           [model austronesian_vocabulary]
           model=mk
           data=abvd.csv
    --- austronesian_vocabulary.conf

This is a minimal BEASTling file that will generate a BEAST 2 xml
configuration file that tries to infer a tree of Austronesian
languages from the ABVD data using a naïve `Lewis Mk model`_.

Let's try it!

    $ beastling austronesian_vocabulary.conf
    $ dir
    [...]
    beastling.xml
    [...]
    $ cat beastling.xml
    <?xml version='1.0' encoding='UTF-8'?>
    <beast beautistatus="" beautitemplate="Standard" namespace="beast.core:beast.evolution.alignment:beast.evolution.tree.coalescent:beast.core.util:beast.evolution.nuc:beast.evolution.operators:beast.evolution.sitemodel:beast.evolution.substitutionmodel:beast.evolution.likelihood" version="2.0">
    <!--Generated by BEASTling [...] on [...].
    Original config file:
    [model austronesian_vocabulary]
    model=mk
    data=abvd.csv

    -->
    [...]
    </beast>

We would like to run this in BEAST to test it, but the `default chain
length`_ of 10000000 will make waiting for this analysis (which we
don't trust) to finish very tedious, so let's reduce the chain length
for the time being.

    ::
           [mcmc]
           chainlength=100
           [model austronesian_vocabulary]
           model=mk
           data=abvd.csv
    --- austronesian_vocabulary.conf

Now we can run `beastling` again (after cleaning up the previous
output) and then run BEAST.

    $ rm beastling.xml
    $ beastling austronesian_vocabulary.conf
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
     

.. `Lexibank`: ???
.. `ABVD`: http://language.psy.auckland.ac.nz/austronesian/
.. 1: Greenhill, S.J., Blust. R, & Gray, R.D. (2008). The Austronesian Basic Vocabulary Database: From Bioinformatics to Lexomics. Evolutionary Bioinformatics, 4:271-283.
.. `CC-BY`: https://creativecommons.org/licenses/by/4.0/ 
.. `CLDF`: https://github.com/glottobank/cldf
