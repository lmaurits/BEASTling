from __future__ import division, unicode_literals
import collections
import importlib
import itertools
import io
import os
import re
import six
import sys
from random import uniform as uniformrand
from random import sample as randsample

import newick
from appdirs import user_data_dir
from six.moves.urllib.request import FancyURLopener
from clldutils.inifile import INI

import beastling.clocks.strict as strict
import beastling.clocks.relaxed as relaxed
import beastling.clocks.random as random

import beastling.models.geo as geo
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

def get_glottolog_macroareas(glottolog_release):
        """MOCK"""

        def parse_label(label):
            match = GLOTTOLOG_NODE_LABEL.match(label)
            return (
                match.group('name').strip(),
                match.group('glottocode'),
                match.group('isocode'))

        macro = {}
        trees = get_glottolog_newick(glottolog_release)
        for t in trees:
            for lang in t.get_leaf_names():
                name, glotto, iso = parse_label(lang)
                macro[glotto] = randsample(["Africa","Australia", "Eurasia","North America", "South America", "Papunesia"],1)[0]
                macro[iso] = macro[glotto]
        return macro

def get_glottolog_locations(glottolog_release):
        """MOCK"""
        return collections.defaultdict(lambda: (uniformrand(-90,90), uniformrand(-180,180)))

class Configuration(object):
    """
    A container object for all of the settings which define a BEASTling
    analysis.  Configuration objects are initialised with default values
    for all options.
    """

    def __init__(self, basename="beastling", configfile=None, stdin_data=False, prior=False):
        """
        Set all options to their default values and then, if a configuration
        file has been provided, override the default values for those options
        set in the file.
        """
        self.processed = False
        self.messages = []
        self.message_flags = []

        # Set up default options
        self.basename = basename+"_prior" if prior else basename
        self.clock_configs = []
        self.configfile = None
        self.configfile_text = None
        self.chainlength = 10000000
        self.embed_data = False
        self.files_to_embed = []
        # We need two different attributes, because specifying prior
        # sampling in the config file does not affect names, whereas
        # it does on the command line to avoid overwriting generated
        # beast output. Also, the command line switch has precendent
        # over the config file setting.
        self.prior = prior
        self.sample_from_prior = False
        self.families = "*"
        self.languages = "*"
        self.macroareas = "*"
        self.overlap = "union"
        self.starting_tree = ""
        self.sample_branch_lengths = True
        self.sample_topology = True
        self.model_configs = []
        self.monophyly = False
        self.monophyly_start_depth = 0
        self.monophyly_end_depth = None
        self.monophyly_levels = sys.maxsize
        self.monophyly_direction = "top_down"
        self.screenlog = True
        self.log_all = False
        self.log_every = 0
        self.log_params = False
        self.log_probabilities = True
        self.log_trees = True
        self.stdin_data = stdin_data
        self.calibrations = {}
        self.glottolog_release = '2.7'
        self.classifications = {}
        self.glotto_macroareas = {}
        self.locations = {}

        if configfile:
            self.read_from_file(configfile)

    def read_from_file(self, configfile):
        """
        Read one or several INI-style configuration files and overwrite
        default option settings accordingly.
        """
        self.configfile = INI(interpolation=None)
        if isinstance(configfile, dict):
            self.configfile.read_dict(configfile)
        else:
            if isinstance(configfile, six.string_types):
                configfile = (configfile,)
            for conf in configfile:
                self.configfile.read(conf)
        p = self.configfile

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
                'languages': p.get,
                'families': p.get,
                'macroareas': p.get,
                'overlap': p.get,
                'starting_tree': p.get,
                'sample_branch_lengths': p.getboolean,
                'sample_topology': p.getboolean,
                'monophyly_start_depth': p.getint,
                'monophyly_end_depth': p.getint,
                'monophyly_levels': p.getint,
                'monophyly_direction': lambda s, o: p.get(s, o).lower(),
            },
        }.items():
            for opt, getter in opts.items():
                if p.has_option(sec, opt):
                    setattr(self, opt, getter(sec, opt))

        ## MCMC
        self.sample_from_prior |= self.prior
        if self.prior and not self.basename.endswith("_prior"):
            self.basename += "_prior"

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
            for clades, dates in p.items("calibration"):
                for clade in clades.split(','):
                    clade = clade.strip()
                    if clade:
                        self.calibrations[clade.lower()] = [
                            float(x.strip()) for x in dates.split("-", 1)]

        # At this point, we can tell whether or not the tree's length units
        # can be treated as arbitrary
        self.arbitrary_tree = self.sample_branch_lengths and not self.calibrations

        ## Clocks
        clock_sections = [s for s in p.sections() if s.lower().startswith("clock")]
        for section in clock_sections:
            self.clock_configs.append(self.get_clock_config(p, section))

        ## Models
        model_sections = [s for s in p.sections() if s.lower().startswith("model")]
        if not model_sections:
            raise ValueError("Config file contains no model sections.")
        for section in model_sections:
            self.model_configs.append(self.get_model_config(p, section))
        
        # Geography
        if p.has_section("geography"):
            self.geo_config = self.get_geo_config(p, "geography")
        else:
            self.geo_config = {}

    def get_clock_config(self, p, section):
        cfg = {
            'name': section[5:].strip(),
        }
        for key, value in p[section].items():
            if key == 'estimate_mean':
                value = p.getboolean(section, key)
            cfg[key] = value
        return cfg

    def get_model_config(self, p, section):
        cfg = {
            'name': section[5:].strip(),
            'binarised': None,
            'rate_variation': False,
            'remove_constant_features': True,
        }
        for key, value in p[section].items():
            # "binarised" is the canonical name for this option and used everywhere
            # internally, but "binarized" is accepted in the config file.
            if key in ('binarised', 'binarized'):
                value = p.getboolean(section, key)
                key = 'binarised'
            if key == "features":
                value = self.handle_file_or_list(value)
            if key in ['rate_variation', 'remove_constant_features']:
                value = p.getboolean(section, key)

            if key in ['minimum_data']:
                value = p.getfloat(section, key)

            cfg[key] = value
        return cfg

    def get_geo_config(self, p, section):
        cfg = {
            'name': 'geography',
            'model': 'geo',
        }
        for key, value in p[section].items():
            if key == "log_locations":
                value = p.getboolean(section, key)
            cfg[key] = value
        return cfg

    def process(self):
        """
        Prepares a Configuration object for being passed to the BeastXml

        constructor.

        This method checks the values of all options for invalid or ambiguous
        settings, internal consistency, etc.  Information is read from
        external files as required.  If this method returns without raising
        any exceptions then this should function as a guarantee that a
        BeastXml object can be instantiated from this Configuration with no
        problems.
        """

        # Add dependency notice if required
        if self.monophyly and not self.starting_tree:
            self.messages.append("[DEPENDENCY] ConstrainedRandomTree is implemented in the BEAST package BEASTLabs.")

        # BEAST can't handle really long chains
        _BEAST_MAX_LENGTH = 2147483647
        if self.chainlength > _BEAST_MAX_LENGTH:
            self.chainlength = _BEAST_MAX_LENGTH
            self.messages.append("[INFO] Chain length truncated to %d, as BEAST cannot handle longer chains." % self.chainlength)
        # If log_every was not explicitly set to some non-zero
        # value, then set it such that we expect 10,000 log
        # entries
        if not self.log_every:
            # If chainlength < 10000, this results in log_every = zero.
            # This causes BEAST to die.
            # So in this case, just log everything.
            self.log_every = self.chainlength // 10000 or 1

        self.load_glotto_class()
        self.load_glotto_geo()
        self.build_language_filter()
        self.instantiate_clocks()
        self.instantiate_models()
        self.link_clocks_to_models()
        self.build_language_list()
        self.handle_starting_tree()
        self.processed = True

    def load_glotto_class(self):
        """
        Loads the Glottolog classification information from the appropriate
        newick file, parses it and stores the required datastructure in
        self.classification.
        """
        label2name = {}

        def parse_label(label):
            match = GLOTTOLOG_NODE_LABEL.match(label)
            label2name[label] = (match.group('name').strip().replace("\\'","'"), match.group('glottocode'))
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

    def load_glotto_geo(self):
        """
        Loads the Glottolog geographic information from the appropriate .csv
        file, parses it and stores the required datastructures in
        self.glotto_macroareas and self.locations.
        """

        self.glotto_macroareas = get_glottolog_macroareas(self.glottolog_release)
        self.locations = get_glottolog_locations(self.glottolog_release)

    def build_language_filter(self):
        """
        Examines the values of various options, including self.languages and
        self.families, and constructs self.lang_filter.

        self.lang_filter is a Set object containing all ISO and glotto codes
        which are compatible with the provided settings (e.g. belong to the
        requested families).  This set is later used as a mask with data sets.
        Datapoints with language identifiers not in this set will not be used
        in an analysis.
        """
        # Load requirements
        self.languages = self.handle_file_or_list(self.languages)
        self.families = self.handle_file_or_list(self.families)
        self.macroareas = self.handle_file_or_list(self.macroareas)

        # Build language filter based on languages or families
        if self.languages != ["*"] and self.families != ["*"]:
            # Can't filter by languages and families at same time!
            raise ValueError("languages and families both defined in [languages]!")
        elif self.languages != ["*"]:
            # Filter by language
            self.lang_filter = set(self.languages)
        elif self.families != ["*"]:
            # Filter by glottolog classification
            self.lang_filter = {
                l for l in self.classifications
                if any([family in [n for t in self.classifications[l] for n in t]
                        for family in self.families])}
        else:
            self.lang_filter = UniversalSet()
        
        # Impose macro-area requirements
        if self.macroareas != ["*"]:
            self.geo_filter = {
                    l for l in self.glotto_macroareas if self.glotto_macroareas[l] in self.macroareas}
            self.lang_filter = self.lang_filter & self.geo_filter

    def handle_file_or_list(self, value):
        if os.path.exists(value):
            with io.open(value, encoding="UTF-8") as fp:
                result = [x.strip() for x in fp.readlines()]
            self.files_to_embed.append(value)
        else:
            result = [x.strip() for x in value.split(",")]
        return result

    def instantiate_clocks(self):
        """
        Populates self.clocks with a list of BaseClock subclasses, one for each
        dictionary of settings in self.clock_configs.
        """
        self.clocks = []
        self.clocks_by_name = {}
        for config in self.clock_configs:
            if config["type"].lower() == "strict":
                clock = strict.StrictClock(config, self) 
            elif config["type"].lower() == "relaxed":
                clock = relaxed.relaxed_clock_factory(config, self)
            elif config["type"].lower() == "random":
                clock = random.RandomLocalClock(config, self) 
            self.clocks.append(clock)
            self.clocks_by_name[clock.name] = clock
        # Create default clock if necessary
        if "default" not in self.clocks_by_name:
            config = {}
            config["name"] = "default"
            config["type"] = "strict"
            clock = strict.StrictClock(config, self)
            self.clocks.append(clock)
            self.clocks_by_name[clock.name] = clock

    def instantiate_models(self):
        """
        Populates self.models with a list of BaseModel subclasses, one for each
        dictionary of settings in self.model_configs.
        """
        if not (self.model_configs or self.geo_config):
            raise ValueError("No models or geography specified!")

        # Handle request to read data from stdin
        if self.stdin_data:
            for config in self.model_configs:
                config["data"] = "stdin"

        self.models = []
        for config in self.model_configs:
            # Validate config
            if "model" not in config:
                raise ValueError("Model not specified for model section %s." % config["name"])
            if "data" not in config:
                raise ValueError("Data source not specified in model section %s." % config["name"])

            # Instantiate model
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
                try:
                    sys.path.insert(0, os.getcwd())
                    module_path, class_name = config["model"].rsplit(".",1)
                    module = importlib.import_module(module_path)
                    UserClass = getattr(module, class_name)
                    model = UserClass(config, self)
                except:
                    raise ValueError("Unknown model type '%s' for model section '%s', and failed to import a third-party model." % (config["model"], config["name"]))

            if config["model"].lower() != "covarion":
                self.messages.append("""[DEPENDENCY] Model %s: AlignmentFromTrait is implemented in the BEAST package "BEAST_CLASSIC".""" % config["name"])
            self.messages.extend(model.messages)
            self.models.append(model)
            
        if self.geo_config:
            self.geo_model = geo.GeoModel(self.geo_config, self)
            self.messages.extend(self.geo_model.messages)
            self.all_models = [self.geo_model] + self.models
        else:
            self.all_models = self.models

    def link_clocks_to_models(self):
        """
        Ensures that for each model object in self.models, the attribute
        "clock" is a reference to one of the clock objects in self.clocks.
        Also determine which clock to estimate the mean of.
        """
        for model in self.all_models:
            if model.clock:
                # User has explicitly specified a clock
                if model.clock not in self.clocks_by_name:
                    raise ValueError("Unknown clock '%s' for model section '%s'." % (model.clock, model.name))
                model.clock = self.clocks_by_name[model.clock]
            elif model.name in self.clocks_by_name:
                # Clock is associated by a common name
                model.clock = self.clocks_by_name[model.name]
            else:
                # No clock specification - use default
                model.clock = self.clocks_by_name["default"]
            model.clock.is_used = True

        # Warn user about unused clock(s)
        for clock in self.clocks:
            if not clock.is_used:
                self.messages.append("""[INFO] Clock %s is not being used.  Change its name to "default", or explicitly associate it with a model.""" % clock.name)

        # Get a list of model (i.e. non-geo) clocks for which the user has not
        # indicated a preference on whether the mean should be estimated
        free_clocks = list(set([m.clock for m in self.models
            if m.clock.is_used
            and m.clock.estimate_mean == None]))
        if free_clocks:
            # To begin with, estimate all free clocks
            for clock in free_clocks:
                clock.estimate_mean = True
            # But if the tree is arbitrary, then fix one free clock, unless the
            # user has fixed an un-free clock
            if self.arbitrary_tree and all(
                [m.clock.estimate_mean for m in self.models]):
                free_clocks[0].estimate_mean = False
                self.messages.append("""[INFO] Clock "%s" has had it's mean fixed to 1.0.  Tree branch lengths are in units of expected substitutions for features in models using this clock.""" % free_clocks[0].name)

    def build_language_list(self):
        """
        Combines the language sets of each model's data set, according to the
        value of self.overlap, to construct a final list of all the languages
        in the analysis.
        """
        self.languages = set(self.models[0].data.keys())
        self.overlap_warning = False
        for model in self.models:
            addition = set(model.data.keys())
            # If we're about to do a non-trivial union/intersect, alert the
            # user.
            if addition != self.languages and not self.overlap_warning:
                self.messages.append("""[INFO] Not all data files have equal language sets.  BEASTling will use the %s of all language sets.  Set the "overlap" option in [languages] to change this.""" % self.overlap.lower())
                self.overlap_warning = True
            if self.overlap.lower() == "union":
                self.languages = set.union(self.languages, addition)
            elif self.overlap.lower() == "intersection":
                self.languages = set.intersection(self.languages, addition)

        ## Make sure there's *something* left
        if not self.languages:
            raise ValueError("No languages specified!")

        ## Convert back into a sorted list
        self.languages = sorted(self.languages)
        self.messages.append("[INFO] %d languages included in analysis." % len(self.languages))

    def handle_starting_tree(self):
        """
        Makes any changes to the user-provided starting tree required to make
        it suitable for passing to BEAST.

        In particular, this method checks that the supplied string or the
        contents of the supplied file:
            * seems to be a valid Newick tree
            * contains no duplicate taxa
            * has taxa which are a superset of the languages in the analysis
            * has no polytomies or unifurcations.
        """
        if os.path.exists(self.starting_tree):
            with io.open(self.starting_tree, encoding="UTF-8") as fp:
                self.starting_tree = fp.read().strip()
        if self.starting_tree:
            # Make sure starting tree can be parsed
            try:
                tree = newick.loads(self.starting_tree)[0]
            except:
                raise ValueError("Could not parse starting tree.  Is it valid Newick?")
            # Make sure starting tree contains no duplicate taxa
            tree_langs = [n.name for n in tree.walk() if n.is_leaf]
            if not len(set(tree_langs)) == len(tree_langs):
                dupes = [l for l in tree_langs if tree_langs.count(l) > 1]
                dupestring = ",".join(["%s (%d)" % (d, tree_langs.count(d)) for d in dupes])
                raise ValueError("Starting tree contains duplicate taxa: %s" % dupestring)
            tree_langs = set(tree_langs)
            # Make sure languges in tree is a superset of languages in the analysis
            if not tree_langs.issuperset(self.languages):
                missing_langs = self.languages.difference(tree_langs)
                miss_string = ",".join(missing_langs)
                raise ValueError("Some languages in the data are not in the starting tree: %s" % miss_string)
            # If the trees' language set is a proper superset, prune the tree to fit the analysis
            if not tree_langs == self.languages:
                tree.prune_by_names(self.languages, inverse=True)
                self.messages.append("[INFO] Starting tree includes languages not present in any data set and will be pruned.")
            # Get the tree looking nice
            tree.remove_redundant_nodes()
            tree.resolve_polytomies()
            # Replace the starting_tree from the config with the new one
            self.starting_tree = newick.dumps(tree)

