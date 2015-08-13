import codecs
import ConfigParser
import csv
import pkgutil
import os
import sys

import beastling.models.bsvs as bsvs
import beastling.models.mk as mk

class Configuration:

    def __init__(self, basename="beastling", configfile=None):

        self.processed = False

        # Set up default options
        self.basename = basename
        self.configfile = None
        self.configfile_text = None
        self.chainlength = 10000000
        self.families = "*"
        self.model_configs = []
        self.monophyly = False
        self.monophyly_start_depth = 0
        self.monophyly_end_depth = sys.maxint
        self.monophyly_grip = "tight"
        self.screenlog = True
        self.log_params = False
        self.log_probabilities = True
        self.log_trees = True
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

        if p.has_option(sec, "monophyly"):
            try:
                self.monophyly = p.getboolean(sec, "monophyly")
            except:
                self.monophyly = p.get(sec, "monophyly").split(",")
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
            config["name"] = section[5:].strip() # Chop off "model" prefix
            self.model_configs.append(config)

    def load_glotto_class(self):
        self.classifications = {}
        binary_glotto = pkgutil.get_data('beastling', 'data/iso-glotto.csv')
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

            self.classifications[lang] = clazz

    def process(self):

        if os.path.exists(self.families):
            fp = codecs.open(families, "r", "UTF-8")
            self.families = [x.strip() for x in fp.readlines()]
            fp.close()
        else:
            self.families = [x.strip() for x in self.families.split(",")]

        ## Load Glottolog classifications
        self.load_glotto_class()

        ## Determine final list of languages
        if self.families == ["*"]:
            langs = [iso for iso in self.classifications]
        else:
            langs = [iso for iso in self.classifications if any([family in self.classifications[iso] for family in self.families])]
        # Hack to fix Glottolog's broken Bontok
        if "bnc" in langs:
            langs.remove("bnc")
            langs.append("lbk")
        if not len(langs):
            raise ValueError("No languages found for families: ", self.families)
        self.languages = langs

        # Instantiate models
        self.models = []
        for config in self.model_configs:
            if "model" not in config:
                raise ValueError("Model not specified for model section %s." % config["name"])
            if "data" not in config:
                raise ValueError("Data source not specified in model section %s." % config["name"])
            if config["model"].lower() == "bsvs":
                model = bsvs.BSVSModel(config, self)
            elif config["model"].lower() == "mk":
                model = mk.MKModel(config, self)
            else:
                raise ValueError("Unknown model type '%s' for model section '%s'." % (config["model"], config["name"]))
            self.models.append(model)

        # Trim language list based on model data
        self.languages = [l for l in self.languages if any([l in model.data for model in self.models])]
        assert self.languages

        self.languages.sort()
        self.processed = True

if __name__ == "__main__":
    main()
