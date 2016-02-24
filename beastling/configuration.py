import codecs
import ConfigParser
import os
import sys
import re

import newick
from appdirs import user_data_dir
from six.moves.urllib.request import FancyURLopener

import beastling.models.bsvs as bsvs
import beastling.models.covarion as covarion
import beastling.models.mk as mk


GLOTTOLOG_NODE_LABEL = re.compile(
    "'(?P<name>[^\[]+)\[(?P<glottocode>[a-z0-9]{8})\](\[(?P<isocode>[a-z]{3})\])?'")


class URLopener(FancyURLopener):
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        raise ValueError()

class UniversalSet(set):
    """Set which intersects fully with any other set."""
    # Based on https://stackoverflow.com/a/28565931
    def __and__(self, other):
        return other

    def __rand__(self, other):
        return other

def get_glottolog_newick(release):
    fname = 'glottolog-%s.newick' % release
    path = os.path.join(os.path.dirname(__file__), 'data', fname)
    if not os.path.exists(path):
        data_dir = user_data_dir('beastling')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            try:
                URLopener().retrieve(
                    'http://glottolog.org/static/download/%s/tree-glottolog-newick.txt'
                    % release,
                    path)
            except (IOError, ValueError):
                raise ValueError(
                    'Could not retrieve classification for Glottolog %s' % release)
    return newick.read(path)


class Configuration(object):

    def __init__(self, basename="beastling", configfile=None, stdin_data=False):
        self.processed = False
        self.messages = []
        self.message_flags = []

        # Set up default options
        self.basename = basename
        self.configfile = None
        self.configfile_text = None
        self.chainlength = 10000000
        self.embed_data = False
        self.sample_from_prior = False
        self.families = "*"
        self.overlap = "union"
        self.starting_tree = ""
        self.sample_branch_lengths = True
        self.sample_topology = True
        self.model_configs = []
        self.monophyly = False
        self.monophyly_start_depth = 0
        self.monophyly_end_depth = sys.maxint
        self.monophyly_grip = "tight"
        self.screenlog = True
        self.log_all = False
        self.log_every = 0
        self.log_params = False
        self.log_probabilities = True
        self.log_trees = True
        self.stdin_data = stdin_data
        self.calibrations = {}
        self.glottolog_release = '2.7'

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

        for sec, opts in {
            'admin': {
                'basename': p.get,
                'embed_data': p.getboolean,
                'screenlog': p.getboolean,
                'log_every': p.getint,
                'log_all': p.getboolean,
                'log_probabilities': p.getboolean,
                'log_params': p.getboolean,
                'log_trees': p.getboolean,
                'glottolog_release': p.get,
            },
            'MCMC': {
                'chainlength': p.getint,
                'sample_from_prior': p.getboolean,
            },
            'languages': {
                'families': p.get,
                'overlap': p.get,
                'starting_tree': p.get,
                'sample_branch_lengths': p.getboolean,
                'sample_topology': p.getboolean,
                'monophyly_start_depth': p.getint,
                'monophyly_end_depth': p.getint,
                'monophyly_grip': lambda s, o: p.get(s, o).lower(),
            },
        }.items():
            for opt, getter in opts.items():
                if p.has_option(sec, opt):
                    setattr(self, opt, getter(sec, opt))

        ## Languages
        sec = "languages"
        if self.overlap.lower() not in ("union", "intersection"):  # pragma: no cover
            raise ValueError(
                "Value for overlap needs to be either 'union', or 'intersection'."
            )
        if (self.starting_tree and not
                (self.sample_topology or self.sample_branch_lengths)):
            self.tree_logging_pointless = True
            self.messages.append(
                "[INFO] Tree logging disabled because starting tree is known and fixed.")
        else:
            self.tree_logging_pointless = False

        if p.has_option(sec, "monophyletic"):
            self.monophyly = p.getboolean(sec, "monophyletic")
        elif p.has_option(sec, "monophyly"):
            self.monophyly = p.getboolean(sec, "monophyly")

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
            # Build a dict of all options in the section
            config = {option:p.get(section, option) for option in options}
            # Now explicitly handle type casting (boolean, float, etc.) for
            # those options which are generic to all model types.
            # Substitution-model-specific options must be cast inside the
            # appropriate BaseModel subclass.

            # "binarised" is the canonical name for this option and used everywhere internally,
            # but "binarized" is accepted in the config file.
            if "binarised" in config:
                config["binarised"] = p.getboolean(section,"binarised")
            elif "binarized" in config:
                config["binarised"] = p.getboolean(section,"binarized")
            else:
                config["binarised"] = None
            if "rate_variation" in config:
                config["rate_variation"] = p.getboolean(section,"rate_variation")
            else:
                config["rate_variation"] = False
            if "remove_constant_features" in config:
                config["remove_constant_features"] = p.getboolean(section,"remove_constant_features")
            else:
                config["remove_constant_features"] = True
            if "minimum_data" in config:
                config["minimum_data"] = p.getfloat(section,"minimum_data")
            config["name"] = section[5:].strip() # Chop off "model" prefix
            self.model_configs.append(config)

    def load_glotto_class(self):
        self.classifications = {}
        label2name = {}

        def parse_label(label):
            match = GLOTTOLOG_NODE_LABEL.match(label)
            label2name[label] = (match.group('name').strip(), match.group('glottocode'))
            return (
                match.group('name').strip(),
                match.group('glottocode'),
                match.group('isocode'))

        def get_classification(node):
            res = []
            ancestor = node.ancestor
            while ancestor:
                res.append(label2name[ancestor.name])
                ancestor = ancestor.ancestor
            return list(reversed(res))

        glottolog_trees = get_glottolog_newick(self.glottolog_release)
        for tree in glottolog_trees:
            for node in tree.walk():
                name, glottocode, isocode = parse_label(node.name)
                classification = get_classification(node)
                self.classifications[glottocode] = classification
                if isocode:
                    self.classifications[isocode] = classification

    def process(self):
        # Add dependency notice if required
        if self.monophyly and not self.starting_tree:
            self.messages.append("[DEPENDENCY] ConstrainedRandomTree is implemented in the BEAST package BEASTLabs.")

        # If log_every was not explicitly set to some non-zero
        # value, then set it such that we expect 10,000 log
        # entries
        if not self.log_every:
            self.log_every = self.chainlength / 10000
            ## If chainlength < 10000, this results in log_every = zero.
            ## This causes BEAST to die.
            ## So in this case, just log everything.
            if self.log_every == 0:
                self.log_every = 1

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
            self.lang_filter = UniversalSet()
        else:
            self.lang_filter = {
                l for l in self.classifications
                if any([family in [n for t in self.classifications[l] for n in t]
                        for family in self.families])}

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
                if "bsvs_used" not in self.message_flags:
                    self.message_flags.append("bsvs_used")
                    self.messages.append(bsvs.BSVSModel.package_notice)
            elif config["model"].lower() == "covarion":
                model = covarion.CovarionModel(config, self)
            elif config["model"].lower() == "mk":
                model = mk.MKModel(config, self)
                if "mk_used" not in self.message_flags:
                    self.message_flags.append("mk_used")
                    self.messages.append(mk.MKModel.package_notice)
            else:
                raise ValueError("Unknown model type '%s' for model section '%s'." % (config["model"], config["name"]))
            if config["model"].lower() != "covarion":
                self.messages.append("""[DEPENDENCY] Model %s: AlignmentFromTrait is implemented in the BEAST package "BEAST_CLASSIC".""" % config["name"])
            self.messages.extend(model.messages)
            self.models.append(model)

        # Finalise language list.
        # We start out setting self.languages to the set of languages in the
        # data file of the first model, filtered by the user's list of
        # famlies...
        self.languages = set(self.models[0].data.keys()) & self.lang_filter
        self.overlap_warning = False
        for model in self.models:
            # For each model, we take the list of langs in the data, and apply
            # the filter representing the user's request.  We then compare
            # this to the current value of self.languages.  Depending upon
            # self.overlap, we either add it to self.langs, or set self.langs
            # to the intersection of itself with the addition.
            addition = set(model.data.keys()) & self.lang_filter
            # If we're about to do a non-trivial union/intersect, alert the
            # user.
            if addition != self.languages and not self.overlap_warning:
                self.messages.append("""[INFO] Not all data files have equal language sets.  BEASTling will use the %s of all language sets.  Set the "overlap" option in [languages] to change this.""" % self.overlap.lower())
                self.overlap_warning = True
            if self.overlap.lower() == "union":
                self.languages = set.union(self.languages, addition)
            elif self.overlap.lower() == "intersection":
                self.languages = set.intersection(self.languages, addition)

        ## Apply family-based filtering
        ## Make sure there's *something* left
        if not self.languages:
            raise ValueError("No languages specified!")

        ## Convert back into a sorted list
        self.languages = sorted(self.languages)
        self.messages.append("[INFO] %d languages included in analysis." % len(self.languages))

        self.processed = True
