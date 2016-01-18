# Usage

BEASTling is a command-line tool, with no graphical interface.  On Linux or OS X machines, it can be used from a terminal.  On Windows machines, it can be run from the command prompt or, for a less painful experience, you can use [cygwin](https://www.cygwin.com/).

Typical usage is to run:

	$ beastling my_config.conf

where "my_config.conf" is a valid BEASTling configuration file.  This will produce an XML file, whose name is determined by the "basename" parameter in the config file.  Alternatively, the output filename can be specified as a second parameter:
	
        $ beastling my_config.conf my_output.xml

If the `my_output.xml` file already exists and you want to overwrite it, use the `--overwrite` option:
	
        $ beastling --overwrite my_config.conf my_output.xml

To write the XML output to `stdout` instead of a file, use `-` in place of an output filename:
	
        $ beastling my_config.conf -

Once you have your output XML file, you can get BEAST to run your analysis by simply running:
        
        $ beast my_output.xml

These usage patterns will cover the vast majority of uses of BEASTling.  If you're feeling funky, you can read the linguistic data from `stdin` instead of a .csv file (see :ref:`data`), or you can generate XML files directly from a Python script, using BEASTling as a library (see :ref:`scripting`).
