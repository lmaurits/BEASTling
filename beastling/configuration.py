import codecs
import ConfigParser
import csv
import itertools
import pkgutil
import os
import sys

import beastling.models.bsvs as bsvs
import beastling.models.covarion as covarion
import beastling.models.mk as mk

class Configuration:

    def __init__(self, basename="beastling", configfile=None, stdin_data=False):

        self.processed = False

        # Set up default options
        self.basename = basename
        self.configfile = None
        self.configfile_text = None
        self.chainlength = 10000000
        self.families = "*"
        self.starting_tree = ""
        self.sample_topology = True
        self.model_configs = []
        self.monophyly = False
        self.monophyly_start_depth = 0
        self.monophyly_end_depth = sys.maxint
        self.monophyly_grip = "tight"
        self.screenlog = True
        self.log_all = False
        self.log_params = False
        self.log_probabilities = True
        self.log_trees = True
        self.stdin_data = stdin_data
        self.calibrations = {}

        if configfile:
            self.read_from_file(configfile)

    def read_from_file(self, configfile):
        # Read config file and overwrite defaults
        self.configfile = configfile
        fp = open(self.configfile, "r")
        self.configfile_text = fp.read()
        fp.close()
        p = ConfigParser.SafeConfigParser()
        p.read(self.configfile)

        ## Admin
        sec = "admin"
        if p.has_option(sec, "basename"):
            self.basename = p.get(sec, "basename")
        if p.has_option(sec, "screenlog"):
            self.screenlog = p.getboolean(sec, "screenlog")
        if p.has_option(sec, "log_all"):
            self.log_all = p.getboolean(sec, "log_all")
        if p.has_option(sec, "log_probabilities"):
            self.log_probabilities = p.getboolean(sec, "log_probabilities")
        if p.has_option(sec, "log_params"):
            self.log_params = p.getboolean(sec, "log_params")
        if p.has_option(sec, "log_trees"):
            self.log_trees = p.getboolean(sec, "log_trees")
            
        ## MCMC
        sec = "MCMC"
        if p.has_option(sec, "chainlength"):
            self.chainlength = p.get(sec, "chainlength")

        ## Languages
        sec = "languages"
        if p.has_option(sec, "families"):
            self.families = p.get(sec, "families")
        if p.has_option(sec, "starting_tree"):
            self.starting_tree = p.get(sec, "starting_tree")
        if p.has_option(sec, "sample_topology"):
            self.sample_topology = p.getboolean(sec, "sample_topology")
        if p.has_option(sec, "monophyletic"):
            try:
                self.monophyly = p.getboolean(sec, "monophyletic")
            except:
                self.monophyly = p.get(sec, "monophyletic").split(",")
        if p.has_option(sec, "monophyly_start_depth"):
            self.monophyly_start_depth = p.getint(sec, "monophyly_start_depth")
        if p.has_option(sec, "monophyly_end_depth"):
            self.monophyly_end_depth = p.getint(sec, "monophyly_end_depth") - 1
        if p.has_option(sec, "monophyly_grip"):
            self.monophyly_grip = p.get(sec, "monophyly_grip").lower()

        ## Calibration
        if p.has_section("calibration"):
            for clade, dates in p.items("calibration"):
                self.calibrations[clade] = [float(x.strip()) for x in dates.split("-")]
            
        ## Models
        sections = p.sections()
        model_sections = [s for s in sections if s.lower().startswith("model")]
        if not model_sections:
            raise ValueError("Config file contains no model sections.")
        for section in model_sections:
            options = p.options(section)
            config = {option:p.get(section, option) for option in options}
            if "rate_variation" in config:
                config["rate_variation"] = p.getboolean(section,"rate_variation")
            else:
                config["rate_variation"] = False
            if "remove_constant_traits" in config:
                config["remove_constant_traits"] = p.getboolean(section,"remove_constant_traits")
            else:
                config["remove_constant_traits"] = True
            if "data_format" in config:
                config["data_format"] = p.getboolean(section,"data_format")
            if "language_column" in config:
                config["language_column"] = p.get(section,"language_column")
            config["name"] = section[5:].strip() # Chop off "model" prefix
            self.model_configs.append(config)

    def load_glotto_class(self):
        self.classifications = {}
        glotto_data = pkgutil.get_data('beastling', 'data/glotto.csv')
        glotto_classifications = self.parse_glotto_class(glotto_data)
        iso_glotto_data = pkgutil.get_data('beastling', 'data/iso-glotto.csv')
        iso_classifications = self.parse_glotto_class(iso_glotto_data)
        for key in glotto_classifications:
            self.classifications[key] = glotto_classifications[key]
        for key in iso_classifications:
            self.classifications[key] = iso_classifications[key]

    def parse_glotto_class(self, binary_glotto):
        classifications = {}
        unicode_glotto = unicode(binary_glotto, "UTF-8")
        glotto_lines = unicode_glotto.split("\n")
        glotto_lines = [l for l in glotto_lines if l]
        for line in glotto_lines:
            lang, clazz = line.split(",",1)
            lang = lang.strip().lstrip().lower()
            if clazz.lstrip().strip() == "Unclassified":
                continue

            clazz = clazz.split(",")
            if not clazz[0]:
                clazz[0] = "Isolate_" + lang
            clazz = ",".join(clazz)
            classifications[lang] = clazz
        return classifications

    def process(self):

        if os.path.exists(self.families):
            fp = codecs.open(self.families, "r", "UTF-8")
            self.families = [x.strip() for x in fp.readlines()]
            fp.close()
        else:
            self.families = [x.strip() for x in self.families.split(",")]

        # Read starting tree from file
        if os.path.exists(self.starting_tree):
            fp = codecs.open(self.starting_tree, "r", "UTF-8")
            self.starting_tree = fp.read().strip()
            fp.close()

        ## Load Glottolog classifications
        self.load_glotto_class()

        ## Determine final list of languages
        if self.families == ["*"]:
            self.lang_filter = []
        else:
            self.lang_filter = [l for l in self.classifications if any([family in self.classifications[l] for family in self.families])]

        # Hack to fix Glottolog's broken Bontok
        if "bnc" in self.lang_filter:
            self.lang_filter.remove("bnc")
            self.lang_filter.append("lbk")

        # Handle request to read data from stdin
        if self.stdin_data:
            for config in self.model_configs:
                config["data"] = "stdin"
        # Instantiate models
        if not self.model_configs:
            raise ValueError("No models specified!")
        self.models = []
        for config in self.model_configs:
            if "model" not in config:
                raise ValueError("Model not specified for model section %s." % config["name"])
            if "data" not in config:
                raise ValueError("Data source not specified in model section %s." % config["name"])
            if config["model"].lower() == "bsvs":
                model = bsvs.BSVSModel(config, self)
            elif config["model"].lower() == "covarion":
                model = covarion.CovarionModel(config, self)
            elif config["model"].lower() == "mk":
                model = mk.MKModel(config, self)
            else:
                raise ValueError("Unknown model type '%s' for model section '%s'." % (config["model"], config["name"]))
            self.models.append(model)

        # Finalise language list
        ## Start with all languages in data
        self.languages = list(itertools.chain(*[model.data.keys() for model in self.models]))
        ## Apply family-based filtering
        if self.lang_filter:
            self.languages = [l for l in self.languages if l in self.lang_filter]
        ## Make sure there's *something* left
        if not self.languages:
            raise ValueError("No languages specified!")
        self.languages.sort()
        self.processed = True

if __name__ == "__main__":
    main()
