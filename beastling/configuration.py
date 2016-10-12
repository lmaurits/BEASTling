from __future__ import division, unicode_literals
import collections
import importlib
import io
import itertools
import math
import os
import re
import six
import sys

import newick
from appdirs import user_data_dir
from six.moves.urllib.request import FancyURLopener
from clldutils.inifile import INI
from clldutils.dsv import reader

import beastling.clocks.strict as strict
import beastling.clocks.relaxed as relaxed
import beastling.clocks.random as random

import beastling.models.geo as geo
import beastling.models.bsvs as bsvs
import beastling.models.covarion as covarion
import beastling.models.mk as mk


_BEAST_MAX_LENGTH = 2147483647
GLOTTOLOG_NODE_LABEL = re.compile(
    "'(?P<name>[^\[]+)\[(?P<glottocode>[a-z0-9]{8})\](\[(?P<isocode>[a-z]{3})\])?'")

Calibration = collections.namedtuple("Calibration", ["langs", "originate", "dist", "param1", "param2"])
class URLopener(FancyURLopener):
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        raise ValueError()  # pragma: no cover


def get_glottolog_data(datatype, release):
    """
    Lookup or download data from Glottolog.

    :param datatype: 'newick'|'geo'
    :param release: Glottolog release number >= '2.4'
    :return: the path of the data file
    """
    path_spec = {
        'newick': ('glottolog-{0}.newick', 'tree-glottolog-newick.txt'),
        'geo': ('glottolog-{0}-geo.csv', 'languages-and-dialects-geo.csv'),
    }
    fname_pattern, fname_source = path_spec[datatype]
    fname = fname_pattern.format(release)
    path = os.path.join(os.path.dirname(__file__), 'data', fname)
    if not os.path.exists(path):
        data_dir = user_data_dir('beastling')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            try:
                URLopener().retrieve(
                    'http://glottolog.org/static/download/{0}/{1}'.format(
                        release, fname_source),
                    path)
            except (IOError, ValueError):
                raise ValueError(
                    'Could not retrieve %s data for Glottolog %s' % (datatype, release))
    return path


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

        # Options set by the user, with default values
        self.basename = basename+"_prior" if prior else basename
        """This will be used as a common prefix for output filenames (e.g. the log will be called basename.log)."""
        self.calibration_configs = {}
        """A dictionary whose keys are glottocodes or lowercase Glottolog clade names, and whose values are length-2 tuples of flatoing point dates (lower and upper bounds of 95% credible interval)."""
        self.chainlength = 10000000
        """Number of iterations to run the Markov chain for."""
        self.clock_configs = []
        """A list of dictionaries, each of which specifies the configuration for a single clock model."""
        self.embed_data = False
        """A list of languages to exclude from the analysis, or a name of a file containing such a list."""
        self.exclusions = ""
        """A boolean value, controlling whether or not to embed data files in the XML."""
        self.families = []
        """List of families to filter down to, or name of a file containing such a list."""
        self.geo_config = {}
        """A dictionary with keys and values corresponding to a [geography] section in a configuration file."""
        self.glottolog_release = '2.7'
        """A string representing a Glottolog release number."""
        self.languages = []
        """List of languages to filter down to, or name of a file containing such a list."""
        self.location_data = None
        """Name of a file containing latitude/longitude data."""
        self.log_all = False
        """A boolean value, setting this True is a shortcut for setting log_params, log_probabilities and log_trees True."""
        self.log_dp = 4
        """An integer value, setting the number of decimal points to use when logging rates, locations, etc.  Defaults to 4.  Use -1 to enable full precision."""
        self.log_every = 0
        """An integer indicating how many MCMC iterations should occurr between consecutive log entries."""
        self.log_params = False
        """A boolean value, controlling whether or not to log model parameters."""
        self.log_probabilities = True
        """A boolean value, controlling whether or not to log the prior, likelihood and posterior of the analysis."""
        self.log_fine_probs = True
        """A boolean value, controlling whether or not to log individuaal components of the prior and likelihood,."""
        self.log_trees = True
        """A boolean value, controlling whether or not to log the sampled trees."""
        self.log_pure_tree = False
        """A boolean value, controlling whether or not to log a separate file of the sampled trees with no metadata included."""
        self.macroareas = []
        """A floating point value, indicated the percentage of datapoints, across ALL models, which a language must have in order to be included in the analysis."""
        self.minimum_data = 0.0
        """List of Glottolog macro-areas to filter down to, or name of a file containing such a list."""
        self.model_configs = []
        """A list of dictionaries, each of which specifies the configuration for a single clock model."""
        self.monophyly = False
        """A boolean parameter, controlling whether or not to enforce monophyly constraints derived from Glottolog's classification."""
        self.monophyly_start_depth = 0
        """Integer; Starting depth in the Glottlog classification hierarchy for monophyly constraints"""
        self.monophyly_end_depth = None
        """Integer; Ending depth in the Glottlog classification hierarchy for monophyly constraints"""
        self.monophyly_levels = sys.maxsize
        """Integer; Number of levels of the Glottolog classification to include in monophyly constraints."""
        self.monophyly_direction = "top_down"
        """Either the string 'top_down' or 'bottom_up', controlling whether 'monophyly_levels' counts from roots (families) or leaves (languages) of the Glottolog classification."""
        self.monophyly_newick = None
        """Either a Newick tree string or the name of a file containing a Newick tree string which represents the desired monophyly constraints if a classification other than Glottolog is required."""
        self.overlap = "union"
        """Either the string 'union' or the string 'intersection', controlling how to handle multiple datasets with non-equal language sets."""
        self.sample_branch_lengths = True
        """A boolean value, controlling whether or not to estimate tree branch lengths."""
        self.sample_from_prior = False
        """Boolean parameter; if True, data is ignored and the MCMC chain will sample from the prior."""
        self.sample_topology = True
        """A boolean value, controlling whether or not to estimate tree topology."""
        self.screenlog = True
        """A boolean parameter, controlling whether or not to log some basic output to stdout."""
        self.starting_tree = ""
        """A starting tree in Newick format, or the name of a file containing the same."""
        self.stdin_data = stdin_data

        # Glottolog data
        self.glottolog_loaded = False
        self.classifications = {}
        self.glotto_macroareas = {}
        self.locations = {}

        # Options set from the command line interface
        self.prior = prior

        # Stuff we compute ourselves
        self.processed = False
        self.configfile = None
        self.files_to_embed = []
        self.messages = []
        self.message_flags = []

        if configfile:
            self.read_from_file(configfile)

    def read_from_file(self, configfile):
        """
        Read one or several INI-style configuration files and overwrite
        default option settings accordingly.
        """
        self.configfile = INI(interpolation=None)
        self.configfile.optionxform = str
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
                'log_all': p.getboolean,
                'log_dp': p.getint,
                'log_every': p.getint,
                'log_probabilities': p.getboolean,
                'log_fine_probs': p.getboolean,
                'log_params': p.getboolean,
                'log_trees': p.getboolean,
                'log_pure_tree': p.getboolean,
                'glottolog_release': p.get,
            },
            'MCMC': {
                'chainlength': p.getint,
                'sample_from_prior': p.getboolean,
            },
            'languages': {
                'exclusions': p.get,
                'languages': p.get,
                'families': p.get,
                'macroareas': p.get,
                'location_data': p.get,
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
        if p.has_option(sec, "monophyletic"):
            self.monophyly = p.getboolean(sec, "monophyletic")
        elif p.has_option(sec, "monophyly"):
            self.monophyly = p.getboolean(sec, "monophyly")
        if p.has_option(sec, "monophyly_newick"):
            value = p.get(sec, "monophyly_newick")
            if os.path.exists(value):
                with io.open(value, encoding="UTF-8") as fp:
                    self.monophyly_newick = fp.read()
            else:
                self.monophyly_newick = value
        if p.has_option(sec,'minimum_data'):
            self.minimum_data = p.getfloat(sec, "minimum_data")

        ## Calibration
        if p.has_section("calibration"):
            for clade, calibration in p.items("calibration"):
                self.calibration_configs[clade] = calibration

        ## Clocks
        clock_sections = [s for s in p.sections() if s.lower().startswith("clock")]
        for section in clock_sections:
            self.clock_configs.append(self.get_clock_config(p, section))

        ## Models
        model_sections = [s for s in p.sections() if s.lower().startswith("model")]
        for section in model_sections:
            self.model_configs.append(self.get_model_config(p, section))
        # Geography
        if p.has_section("geography"):
            self.geo_config = self.get_geo_config(p, "geography")
        else:
            self.geo_config = {}
        if p.has_section("geo_priors"):
            if not p.has_section("geography"):
                raise ValueError("Config file contains geo_priors section but no geography section.")
            self.geo_config["geo_priors"] = {}
            for clades, klm in p.items("geo_priors"):
                for clade in clades.split(','):
                    clade = clade.strip()
                    if clade not in self.geo_config["sampling_points"]:
                        self.geo_config["sampling_points"].append(clade)
                    self.geo_config["geo_priors"][clade] = klm
        sampled_points = self.geo_config.get("sampling_points",[])
        if [p for p in sampled_points if p.lower() != "root"] and self.sample_topology and not self.monophyly:
            self.messages.append("[WARNING] Geographic sampling and/or prior specified for clades other than root, but tree topology is being sampled without monophyly constraints.  BEAST may crash.")

        # Make sure analysis is non-empty
        if not model_sections and not self.geo_config:
            raise ValueError("Config file contains no model sections and no geography section.")

    def get_clock_config(self, p, section):
        cfg = {
            'name': section[5:].strip(),
        }
        for key, value in p[section].items():
            if key in ('estimate_mean', 'estimate_rate','estimate_variance', 'correlated'):
                value = p.getboolean(section, key)
            elif key in ('mean','rate','variance'):
                value = p.getfloat(section, key)
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
            if key in ("features", "exclusions"):
                value = self.handle_file_or_list(value)
            if key in ['pruned','rate_variation', 'remove_constant_features']:
                value = p.getboolean(section, key)

            if key in ['minimum_data']:
                value = p.getfloat(section, key)

            cfg[key] = value
        return cfg

    def get_geo_config(self, p, section):
        cfg = {
            'name': 'geography',
            'model': 'geo',
            'log_locations': True,
            'sampling_points': [],
        }
        for key, value in p[section].items():
            if key == "log_locations":
                value = p.getboolean(section, key)
            elif key == "sampling_points":
                value = self.handle_file_or_list(value)
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

        self.load_glottolog_data()
        self.load_user_geo()
        self.instantiate_models()
        self.build_language_filter()
        self.process_models()
        self.build_language_list()
        self.handle_monophyly()
        self.instantiate_calibrations()
        # At this point, we can tell whether or not the tree's length units
        # can be treated as arbitrary
        self.arbitrary_tree = self.sample_branch_lengths and not self.calibrations
        self.instantiate_clocks()
        self.link_clocks_to_models()
        self.starting_tree = self.handle_user_supplied_tree(self.starting_tree, "starting")
        self.processed = True

        # Decide whether or not to log trees
        if (
            self.starting_tree and
            not self.sample_topology and
            not self.sample_branch_lengths and
            all([c.is_strict for c in self.clocks if c.is_used])
        ):
            self.tree_logging_pointless = True
            self.messages.append(
                "[INFO] Tree logging disabled because starting tree is known and fixed and all clocks are strict.")
        else:
            self.tree_logging_pointless = False

    def load_glottolog_data(self):
        """
        Loads the Glottolog classification information from the appropriate
        newick file, parses it and stores the required datastructure in
        self.classification.
        """
        # Don't load if the analysis doesn't use it
        if not self.check_glottolog_required():
            return
        # Don't load if we already have - can this really happen?
        if self.glottolog_loaded:
            return
        self.glottolog_loaded = True

        label2name = {}
        glottocode2node = {}

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

        # Walk the tree and build the classifications dictionary
        glottolog_trees = newick.read(get_glottolog_data('newick', self.glottolog_release))
        for tree in glottolog_trees:
            for node in tree.walk():
                name, glottocode, isocode = parse_label(node.name)
                classification = get_classification(node)
                self.classifications[glottocode] = classification
                if isocode:
                    self.classifications[isocode] = classification
                glottocode2node[glottocode] = node

        # Load geographic metadata
        for t in reader(
                get_glottolog_data('geo', self.glottolog_release), namedtuples=True):
            if t.macroarea:
                self.glotto_macroareas[t.glottocode] = t.macroarea
                for isocode in t.isocodes.split():
                    self.glotto_macroareas[isocode] = t.macroarea
            if self.location_data:
                continue # Use user-supplied data instead

            if t.latitude and t.longitude:
                latlon = (float(t.latitude), float(t.longitude))
                self.locations[t.glottocode] = latlon
                for isocode in t.isocodes.split():
                    self.locations[isocode] = latlon

        if self.location_data:
            return

        # Second pass of geographic data to handle dialects, which inherit
        # their parent language's location
        for t in reader(
                get_glottolog_data('geo', self.glottolog_release), namedtuples=True):
            if t.level == "dialect":
                failed = False
                node = glottocode2node[t.glottocode]
                ancestor = node.ancestor
                while label2name[ancestor.name][1] not in self.locations:
                    if not ancestor.ancestor:
                        # We've hit the root without finding an ancestral node
                        # with location data!
                        failed = True
                        break
                    else:
                        ancestor = ancestor.ancestor
                if failed:
                    continue
                latlon = self.locations[label2name[ancestor.name][1]]
                self.locations[t.glottocode] = latlon
                for isocode in t.isocodes.split():
                    self.locations[isocode] = latlon

    def check_glottolog_required(self):
        # We need Glottolog if...
        return (
            # ...we've been given a list of families
            self.families
            # ...we've been given a list of macroareas
            or self.macroareas
            # ...we're using monophyly constraints
            or self.monophyly
            # ...we're using calibrations (well, sometimes)
            or self.calibration_configs
            # ...we're using geography
            or self.geo_config
        )

    def load_user_geo(self):
        if not self.location_data:
            return
        with io.open(self.location_data, encoding="UTF-8") as fp:
            # Skip header
            fp.readline()
            for line in fp:
                iso, lat, lon = line.split(",")
                self.locations[iso.strip().lower()] = map(float, (lat, lon))

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
        if len(self.families) == 1:
            self.messages.append("""[WARNING] value of 'families' has length 1: have you misspelled a filename?""")
        self.families = self.handle_file_or_list(self.families)

        self.exclusions = set(self.handle_file_or_list(self.exclusions))
        self.macroareas = self.handle_file_or_list(self.macroareas)
        # Enforce minimum data constraint
        all_langs = set(itertools.chain(*[model.data.keys() for model in self.models]))
        N = sum([max([len(lang.keys()) for lang in model.data.values()]) for model in self.models])
        datapoint_props = {}
        for lang in all_langs:
            count = 0
            for model in self.models:
                count += len([x for x in model.data[lang].values() if x != "?"])
            datapoint_props[lang] = 1.0*count / N
        self.sparse_languages = [l for l in all_langs if datapoint_props[l] < self.minimum_data]

    def handle_file_or_list(self, value):
        if not (isinstance(value, list) or isinstance(value, set)):
            if os.path.exists(value):
                with io.open(value, encoding="UTF-8") as fp:
                    result = [x.strip() for x in fp.readlines()]
                self.files_to_embed.append(value)
            else:
                result = [x.strip() for x in value.split(",")]
        else:
            result = value
        return result

    def filter_language(self, l):
        if self.languages and l not in self.languages:
            return False
        if self.families and not any([name in self.families or glottocode in self.families for (name, glottocode) in self.classifications.get(l,[])]):
            return False
        if self.macroareas and self.glotto_macroareas.get(l,None) not in self.macroareas:
            return False
        if self.exclusions and l in self.exclusions:
            return False
        if self.geo_config and l not in self.locations:
            self.messages.append("""[INFO] All models: Language %s excluded due to lack of location data.""" % l)
            return False
        if l in self.sparse_languages:
            return False
        return True

    def handle_monophyly(self):
        """
        Construct a representation of the Glottolog monophyly constraints
        for the languages in self.languages.  If the constraints are
        meaningful, create and store a Newick tree representation of
        them.  If the constraints are not meaningful, e.g. all
        languages are classified identically by Glottolog, then override
        the monophyly=True setting.
        """
        if not self.monophyly:
            return
        if len(self.languages) < 3:
            # Monophyly constraints are meaningless for so few languages
            self.monophyly = False
            self.messages.append("""[INFO] Disabling Glottolog monophyly constraints because there are only %d languages in analysis.""" % len(self.languages))
            return
        if self.monophyly_newick:
            # The user has provided a tree, so no need to build our own
            self.monophyly_newick = self.handle_user_supplied_tree(self.monophyly_newick, "monophyly")
            return
        # Build a list-based representation of the Glottolog monophyly constraints
        # This can be done in either a "top-down" or "bottom-up" way.
        langs = [l for l in self.languages if l.lower() in self.classifications]
        if self.monophyly_end_depth is not None:
            # A power user has explicitly provided start and end depths
            start = self.monophyly_start_depth
            end = self.monophyly_end_depth
        elif self.monophyly_direction == "top_down":
            # Compute start and end in a top-down fashion
            start = self.monophyly_start_depth
            end = start + self.monophyly_levels
        elif self.monophyly_direction == "bottom_up":
            # Compute start and end in a bottom-up fashion
            classifications = [self.classifications[name.lower()] for name in langs]
            end = max([len(c) for c in classifications]) - self.monophyly_start_depth
            start = max(0, end - self.monophyly_levels)
        struct = self.make_monophyly_structure(langs, depth=start, maxdepth=end)
        # Make sure this struct is not pointlessly flat
        if not self.check_monophyly_structure(struct):
            self.monophyly = False
            self.messages.append("""[INFO] Disabling Glottolog monophyly constraints because all languages in the analysis are classified identically.""")
        # At this point everything looks good, so keep monophyly on and serialise the "monophyly structure" into a Newick tree.
        self.monophyly_newick = self.make_monophyly_string(struct)

    def make_monophyly_structure(self, langs, depth, maxdepth):
        """
        Recursively partition a list of languages (ISO or Glottocodes) into
        lists corresponding to their Glottolog classification.  The process
        may be halted part-way down the Glottolog tree.
        """
        if depth > maxdepth:
            # We're done, so terminate recursion
            return langs

        def subgroup(name, depth):
            ancestors = self.classifications[name.lower()]
            return ancestors[depth][0] if depth < len(ancestors) else ''

        def sortkey(i):
            """
            Callable to pass into `sorted` to port sorting behaviour from py2 to py3.

            :param i: Either a string or a list (of lists, ...) of strings.
            :return: Pair (nesting level, first string)
            """
            d = 0
            while isinstance(i, list):
                d -= 1
                i = i[0] if i else ''
            return d, i

        # Find the ancestor of all the given languages at at particular depth
        # (i.e. look `depth` nodes below the root of the Glottolog tree)
        levels = list(set([subgroup(l, depth) for l in langs]))
        if len(levels) == 1:
            # If all languages belong to the same classificatio at this depth,
            # there are two possibilities
            if levels[0] == "":
                # If the common classification is an empty string, then we know
                # that there is no further refinement possible, so stop
                # the recursion here.
                langs.sort()
                return langs
            else:
                # If the common classification is non-empty, we need to
                # descend further, since some languages might get
                # separated later
                return self.make_monophyly_structure(langs, depth+1, maxdepth)
        else:
            # If the languages belong to multiple classifications, split them
            # up accordingly and then break down each classification
            # individually.

            partition = [[l for l in langs if subgroup(l, depth) == level] for level in levels]
            partition = [part for part in partition if part]
            return sorted(
                [self.make_monophyly_structure(group, depth+1, maxdepth)
                 for group in partition],
                key=sortkey)

    def check_monophyly_structure(self, struct):
        """
        Return True if the monophyly structure represented by struct is
        considered "meaningful", i.e. encodes something other than an
        unstructured polytomy.
        """

        # TODO: Make this more rigorous.
        # Current test will fail ['foo', 'bar', 'baz'], but
        # will pass [['foo'], ['bar'], ['baz']], which is no better.
        if not any([type(x) == list for x in struct]):
            # Struct is just a list of language names, with no internal structure
            return False
        return True

    def make_monophyly_string(self, struct, depth=0):
        """
        Converts a structure of nested lists into Newick string.
        """
        if not type([]) in [type(x) for x in struct]:
            return "(%s)" % ",".join(struct) if len(struct) > 1 else struct[0]
        else:
            return "(%s)" % ",".join([self.make_monophyly_string(substruct) for substruct in struct])

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
                except:
                    raise ValueError("Unknown model type '%s' for model section '%s', and failed to import a third-party model." % (config["model"], config["name"]))
                model = UserClass(config, self)

            self.messages.extend(model.messages)
            self.models.append(model)
            
        if self.geo_config:
            self.geo_model = geo.GeoModel(self.geo_config, self)
            self.messages.extend(self.geo_model.messages)
            self.all_models = [self.geo_model] + self.models
        else:
            self.all_models = self.models

    def process_models(self):
        for model in self.models:
            model.process()

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

        # Disable pruned trees in models using RLCs
        for model in self.models:
            if model.pruned and isinstance(model.clock, random.RandomLocalClock):
                model.pruned = False
                self.messages.append("""[INFO] Disabling pruned trees in model %s because associated clock %s is a RandomLocalClock.  Pruned trees are currently only compatible with StrictClocks and RelaxedClocks.""" % (model.name, model.clock.name))

        # Warn user about unused clock(s) (but not the default clock)
        for clock in self.clocks:
            if clock.name != "default" and not clock.is_used:
                self.messages.append("""[INFO] Clock %s is not being used.  Change its name to "default", or explicitly associate it with a model.""" % clock.name)

        # Remove unused clocks from the master clock list
        self.clocks = [c for c in self.clocks if c.is_used]

        # Get a list of model (i.e. non-geo) clocks for which the user has not
        # indicated a preference on whether the mean should be estimated
        free_clocks = list(set([m.clock for m in self.models
            if m.clock.is_used
            and m.clock.estimate_rate == None]))
        if free_clocks:
            # To begin with, estimate all free clocks
            for clock in free_clocks:
                clock.estimate_rate = True
            # But if the tree is arbitrary, then fix one free clock, unless the
            # user has fixed an un-free clock
            if self.arbitrary_tree and all(
                [m.clock.estimate_rate for m in self.models]):
                free_clocks[0].estimate_rate = False
                self.messages.append("""[INFO] Clock "%s" has had it's mean rate fixed to 1.0.  Tree branch lengths are in units of expected substitutions for features in models using this clock.""" % free_clocks[0].name)

        # Determine whether or not precision-scaling is required
        if self.geo_config:
            self.geo_model.scale_precision = False
            geo_clock = self.geo_model.clock
            for m in self.models:
                if m.clock == geo_clock:
                    self.messages.append("""[WARNING] Geography model is sharing a clock with one or more data models.  This may lead to a bad fit.""")
                    self.geo_model.scale_precision = True
                    break
            # If geo has it's own clock, estimate the mean
            if not self.geo_model.scale_precision:
                self.geo_model.clock.estimate_rate = True

    def build_language_list(self):
        """
        Combines the language sets of each model's data set, according to the
        value of self.overlap, to construct a final list of all the languages
        in the analysis.
        """
        if self.models:
            self.languages = set(self.models[0].data.keys())
        else:
            # There are no models
            # So this must be a geography-only analysis
            # Start with all languages in Glottolog, then apply filters
            self.languages = [l for l in self.classifications if self.filter_language(l)]
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

    def instantiate_calibrations(self):
        self.calibrations = {}
        useless_calibrations = []
        for clade, cs in self.calibration_configs.items():
            orig_clade = clade[:]
            orig_cs = cs[:]
            originate = False
            # First parse the clade identifier
            # Might be "root", or else a Glottolog identifier
            if clade.lower() == "root":
                langs = self.languages
            else:
                # First check for originate()
                if clade.lower().startswith("originate(") and clade.endswith(")"):
                    originate = True
                    clade = clade[10:-1]
                langs = self.get_languages_by_glottolog_clade(clade)
            if len(langs) < 2 and not originate:
                self.messages.append("[INFO] Calibration on clade %s MRCA ignored as one or zero matching languages in analysis." % clade)
                continue
            
            # Next parse the calibration string
            if cs.count("(") == 1 and cs.count(")") == 1:
                dist_type, cs = cs.split("(", 1)
                dist_type = dist_type.lower()
                cs = cs[0:-1]
            else:
                # Default to normal
                dist_type = "normal"

            if cs.count(",") == 1 and not any([x in cs for x in ("<", ">")]):
                # We've got explicit params
                p1, p2 = map(float,cs.split(","))
            elif cs.count("-") == 1 and not any([x in cs for x in (",", "<", ">")]):
                # We've got a 95% HPD range
                lower, upper = map(float, cs.split("-"))
                mid = (lower+upper) / 2.0
                if dist_type == "normal":
                    p1 = (upper + lower) / 2.0
                    p2 = (upper - mid) / 1.96
                elif dist_type == "lognormal":
                    p1 = math.log(mid)
                    p2a = (p1 - math.log(lower)) / 1.96
                    p2b = (math.log(upper) - p1) / 1.96
                    p2 = (p2a+p2b)/2.0
                elif dist_type == "uniform":
                    p1 = lower
                    p2 = upper
            elif (cs.count("<") == 1 or cs.count(">") == 1) and not any([x in cs for x in (",", "-")]):
                # We've got a single bound
                dist_type = "uniform"
                sign, bound = cs.split()
                if sign.strip() == "<":
                    p1 = 0.0
                    p2 = float(bound.strip())
                else:
                    p1 = float(bound.strip())
                    p2 = "Infinity"
            else:
                raise ValueError("Could not parse calibration \"%s\" for clade %s" % (orig_cs, orig_clade))
            clade_identifier = "%s_originate" % clade if originate else clade
            self.calibrations[clade_identifier] = Calibration(langs, originate, dist_type, p1, p2)

    def get_languages_by_glottolog_clade(self, clade):
        langs = []
        for l in self.languages:
            for name, glottocode in self.classifications.get(l.lower(),""):
                if clade.lower() == name.lower() or clade.lower() == glottocode:
                    langs.append(l)
                    break
        return langs

    def handle_user_supplied_tree(self, value, tree_type):
        """
        If the provided value is a filename, read the contents and treat it
        as a Newick tree specification.  Otherwise, assume the provided value
        is a Neick tree specification.  In either case, inspect the tree and
        make appropriate minor changes so it is suitable for inclusion in the
        BEAST XML file.
        """
        # Make sure we've got a legitimate tree type
        tree_type = tree_type.lower()
        if tree_type not in ("starting", "monophyly"):
            raise ValueError("Valid tree types for sanitising are 'starting' and 'monophyly', not %s." % tree_type)
        # Read from file if necessary
        if os.path.exists(value):
            with io.open(value, encoding="UTF-8") as fp:
                value = fp.read().strip()
        # Sanitise
        if value:
            value = self.sanitise_tree(value, tree_type)
        # Done
        return value

    def sanitise_tree(self, tree, tree_type):
        """
        Makes any changes to a user-provided tree required to make
        it suitable for passing to BEAST.

        In particular, this method checks that the supplied string or the
        contents of the supplied file:
            * seems to be a valid Newick tree
            * contains no duplicate taxa
            * has taxa which are a superset of the languages in the analysis
            * has no polytomies or unifurcations.
        """
        # Make sure tree can be parsed
        try:
            tree = newick.loads(tree)[0]
        except:
            raise ValueError("Could not parse %s tree.  Is it valid Newick?" % tree_type)
        # Make sure starting tree contains no duplicate taxa
        tree_langs = tree.get_leaf_names()
        if not len(set(tree_langs)) == len(tree_langs):
            dupes = set([l for l in tree_langs if tree_langs.count(l) > 1])
            dupestring = ",".join(["%s (%d)" % (d, tree_langs.count(d)) for d in dupes])
            raise ValueError("%s tree contains duplicate taxa: %s" % (tree_type.capitalize(), dupestring))
        tree_langs = set(tree_langs)
        # Make sure languges in tree is a superset of languages in the analysis
        if not tree_langs.issuperset(self.languages):
            missing_langs = set(self.languages).difference(tree_langs)
            miss_string = ",".join(missing_langs)
            raise ValueError("Some languages in the data are not in the %s tree: %s" % (tree_type, miss_string))
        # If the trees' language set is a proper superset, prune the tree to fit the analysis
        if not tree_langs == self.languages:
            tree.prune_by_names(self.languages, inverse=True)
            self.messages.append("[INFO] %s tree includes languages not present in any data set and will be pruned." % tree_type.capitalize())
        # Get the tree looking nice
        tree.remove_redundant_nodes()
        if tree_type == "starting":
            tree.resolve_polytomies()
        # Remove lengths for a monophyly tree
        if tree_type == "monophyly":
            for n in tree.walk():
                n._length = None
        # Checks
        if tree_type == "starting":
            assert all([len(n.descendants) in (0,2) for n in tree.walk()])
        assert len(tree.get_leaves()) == len(self.languages)
        assert all([l.name for l in tree.get_leaves()])
        # Done
        return newick.dumps(tree)
