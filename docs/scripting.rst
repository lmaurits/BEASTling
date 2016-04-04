===================
Scripting BEASTling
===================

It is possible, though currently a little awkward, to use BEASTling as a Python library so that you can generate XML files from scripts, without creating a config file first.  This is especially useful for generating  large number of XML files where only one or two options differ across the files.

Example
-------

As an illustrative example, suppose we have a directory ``my_data`` with several different CSV files in it, corresponding to different datasets, and we have a BEASTling configuration file ``my_config.conf`` which contains the details of a BEASTling analysis, and we want to generate one BEAST XML file for each data file.  All analyses should use the same settings (e.g. substitution models, calibration points, etc.), but the data should be different for each analysis.  We can generate these XML files easily, even for 1,000 different data files (suppose you are doing a simulation study and have generated 1,000 synthetic data sets), using the following script:

.. code-block:: python

    from glob import glob

    # Import relevant parts of BEASTling
    from beastling.configuration import Configuration
    from beastling.beastxml import BeastXml

    # For several different data files...
    for data_filename in glob("my_data/*.csv"):
        # Build a Configuration object
        config = Configuration(configfile="my_config.conf")
        config.model_configs[0]["data"] = data_filename

        # Create a BeastXML object from the Configuration object
        beastxml = BeastXml(config)

        # Save BeastXML to file
        xml_filename = data_filename.replace("csv", "xml")
        xml.write_file(xml filename)

The essential process for creating a file from within a script is to create first a ``Configuration`` and object, and then feed this to the constructor of a ``BeastXML`` object.  One instantiated, the ``BeastXML`` object's ``write_file`` method can be used to save to generated XML to the filesystem.

Creating Configurations from scratch
------------------------------------

In the above example, a ``Configuration`` object was created from a BEASTling config file, using the ``configfile`` argument to the ``Configuration`` constructor.  We then overrode one aspect of that configuration before creating an XML file.

It is also possible to create a ``Configuration`` object from scratch, without any corresponding configuration file:

::

    from beastling.configuration import Configuration
    config = Configuration()
   
Such a ``Configuration`` object will be created with all options set to their default values.  The one essential step before feeding this object to a ``BeastXml`` is to populate the ``model_configs`` attribute, which by default is an empty list.

``model_configs`` should end up list of Python dictionaries.  The keys and values of these dictionaries should mirror the structure of a ``[model]`` section in a BEASTling configuration file.  At the bare minimum, you *must* set the ``name``, ``model`` and ``data`` keys to appropriate values:

::

    config["name"] = "my_model"
    config["model"] = "mk" # or "covarion", "bsvs", etc.
    config["data"] = "my_data.csv"

If you want to include non-default clock models, you should similarly populate the ``clock_configs`` attribute, which by default is an empty list and should end up full of dictionaries which mirror the structure of a ``[clock]`` section.

Other details of the configuration can be specified by overwriting the following instance attributes:

.. autoclass:: beastling.configuration.Configuration
    :members: basename, calibrations, clock_configs, embed_data, families, glottolog_release, languages, log_all, log_every, log_params, log_probabilities, log_trees, macroareas, monophyly, monophyly_direction, monophyly_end_depth, monophyly_levels, monophyly_start_depth, overlap, sample_branch_lengths, sample_topology, screenlog, self.location_data, starting_tree
