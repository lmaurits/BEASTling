=====
Usage
=====

BEASTling is a command-line tool, with no graphical interface.  On Linux or OS X machines, it can be used from a terminal.  On Windows machines, it can be run from the command prompt or, for a less painful experience, you can use `cygwin <https://www.cygwin.com/>`_.

Typical usage is to run:

::

	$ beastling my_config.conf

where "my_config.conf" is a valid BEASTling configuration file.  This will produce an XML file, whose name is determined by the "basename" parameter in the config file.  Alternatively, the output filename can be specified as a second parameter:
	
::

        $ beastling my_config.conf my_output.xml

If the ``my_output.xml`` file already exists and you want to overwrite it, use the ``--overwrite`` option:
	
::

        $ beastling --overwrite my_config.conf my_output.xml

To write the XML output to ``stdout`` instead of a file, use ``-`` in place of an output filename:
	
::

        $ beastling my_config.conf -

If you run BEASTling in verbose mode, using either ``-v`` or ``--verbose``, BEASTling will print messages while processing your configuration file.  These messages will let you know of BEAST packages that your analysis depends upon, and of various decisions it makes which you may like to be aware of.  For example:

::

        $ beastling -v my_config.conf my_output.xml
        [DEPENDENCY] ConstrainedRandomTree is implemented in the BEAST package BEASTLabs.
        [DEPENDENCY] The Lewis Mk substitution model is implemented in the BEAST package "morph-models".
        [INFO] Model "my_model": Trait f3 excluded because its value is constant across selected languages.  Set "remove_constant_features=False" in config to stop this.
        [INFO] Model "my_model": Trait f6 excluded because there are no datapoints for selected languages.
        [INFO] Model "my_model": Using 8 features from data file ./tests/data/basic.csv
        [INFO] 5 languages included in analysis.

In future, BEASTling in verbose mode may also offer hints on hwo you can tweak your configuration to improve performance.

Once you have your output XML file, you can get BEAST to run your analysis by simply running:
        
::

        $ beast my_output.xml

These usage patterns will cover the vast majority of uses of BEASTling.  If you're feeling funky, you can read the linguistic data from ``stdin`` instead of a .csv file (see :doc:`data`), or you can generate XML files directly from a Python script, using BEASTling as a library (see :doc:`scripting`).
