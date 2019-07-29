# -*- encoding: utf-8 -*-

from __future__ import division, unicode_literals
import collections
import importlib
import io
import itertools
import math
import os
import random
import re
import six
import sys

import newick
from appdirs import user_data_dir
from six.moves.urllib.request import FancyURLopener
from clldutils.inifile import INI
from clldutils.dsv import reader
from clldutils.path import Path

from beastling.fileio.datareaders import load_location_data
from .distributions import Distribution
import beastling.clocks.strict as strict
import beastling.clocks.relaxed as relaxed
import beastling.clocks.random as random_clock
import beastling.clocks.prior as prior_clock

import beastling.models.geo as geo
import beastling.models.binaryctmc as binaryctmc
import beastling.models.bsvs as bsvs
import beastling.models.covarion as covarion
import beastling.models.pseudodollocovarion as pseudodollocovarion
import beastling.models.mk as mk

import beastling.treepriors.base as treepriors
from beastling.treepriors.coalescent import CoalescentTree

_BEAST_MAX_LENGTH = 2147483647
GLOTTOLOG_NODE_LABEL = re.compile(
    "'(?P<name>[^\[]+)\[(?P<glottocode>[a-z0-9]{8})\](\[(?P<isocode>[a-z]{3})\])?(?P<appendix>-l-)?'")


class Calibration(
        collections.namedtuple(
            "Calibration", ["langs", "originate", "offset", "dist", "param"]),
        Distribution):
    pass


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
        self.alpha = 0.3
        """Alpha parameter for path sampling intervals."""
        self.basename = basename+"_prior" if prior else basename
        """This will be used as a common prefix for output filenames (e.g. the log will be called basename.log)."""
        self.calibration_configs = {}
        """A dictionary whose keys are glottocodes or lowercase Glottolog clade names, and whose values are length-2 tuples of flatoing point dates (lower and upper bounds of 95% credible interval)."""
        self.chainlength = 10000000
        """Number of iterations to run the Markov chain for."""
        self.clock_configs = []
        """A list of dictionaries, each of which specifies the configuration for a single clock model."""
        self.do_not_run = False
        """A boolean value, controlling whether or not BEAST should run path sampling analyses or just generate the file and scripts to do so."""
        self.embed_data = False
        """A list of languages to exclude from the analysis, or a name of a file containing such a list."""
        self.exclusions = ""
        """A boolean value, controlling whether or not to embed data files in the XML."""
        self.families = []
        """List of families to filter down to, or name of a file containing such a list."""
        self.geo_config = {}
        """A dictionary with keys and values corresponding to a [geography] section in a configuration file."""
        self.glottolog_release = '4.0'
        """A string representing a Glottolog release number."""
        self.languages = []
        """List of languages to filter down to, or name of a file containing such a list."""
        self.language_group_configs = collections.OrderedDict()
        """An ordered dictionary whose keys are language group names and whose values are language group definitions."""
        self.language_groups = {}
        """A dictionary giving names to arbitrary collections of tip languages."""
        self.location_data = None
        """Name of a file containing latitude/longitude data."""
        self._log_all = False
        """A boolean value, setting this True is a shortcut for setting log_params, log_probabilities, log_fine_probs and log_trees True."""
        self.log_burnin = 50
        """Proportion of logs to discard as burnin when calculating marginal likelihood from path sampling."""
        self.log_dp = 4
        """An integer value, setting the number of decimal points to use when logging rates, locations, etc.  Defaults to 4.  Use -1 to enable full precision."""
        self.log_every = 0
        """An integer indicating how many MCMC iterations should occurr between consecutive log entries."""
        self.log_params = False
        """A boolean value, controlling whether or not to log model parameters."""
        self.log_probabilities = True
        """A boolean value, controlling whether or not to log the prior, likelihood and posterior of the analysis."""
        self.log_fine_probs = False
        """A boolean value, controlling whether or not to log individual components of the prior and likelihood.  Setting this True automatically sets log_probabilities True."""
        self.log_trees = True
        """A boolean value, controlling whether or not to log the sampled trees."""
        self.log_pure_tree = False
        """A boolean value, controlling whether or not to log a separate file of the sampled trees with no metadata included."""
        self.macroareas = []
        """A floating point value, indicated the percentage of datapoints, across ALL models, which a language must have in order to be included in the analysis."""
        self.minimum_data = 0.0
        """List of Glottolog macro-areas to filter down to, or name of a file containing such a list."""
        self.model_configs = []
        """A list of dictionaries, each of which specifies the configuration for a single evolutionary model."""
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
        self.path_sampling = False
        """A boolean value, controlling whether to do a standard MCMC run or a Path Sampling analysis for marginal likelihood estimation."""
        self.preburnin = 10
        """Percentage of chainlength to discard as burnin for the first step in a path sampling analysis."""
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
        self.steps = 8
        """Number of steps between prior and posterior in path sampling analysis."""
        self.stdin_data = stdin_data
        """A boolean value, controlling whether or not to read data from stdin as opposed to the file given in the config."""
        self.subsample_size = 0
        """Number of languages to subsample from the set defined by the dataset(s) and other filtering options like "families" or "macroareas"."""
        self.tree_prior = "yule"
        """Tree prior. Can be overridden by calibrations."""

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
        self.urgent_messages = []
        self.message_flags = []

        if configfile:
            self.read_from_file(configfile)

    @property
    def log_all(self):
        return self._log_all

    @log_all.setter
    def log_all(self, log_all):
        self._log_all = log_all
        if log_all:
            self.log_trees = True
            self.log_params = True
            self.log_probabilities = True
            self.log_fine_probs = True

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

        # Set some logging options according to log_all
        # Note that these can still be overridden later
        self.log_all = p.get("admin", "log_all", fallback=False)

        for sec, getters in {
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
                'alpha': p.getfloat,
                'chainlength': p.getint,
                'do_not_run': p.getboolean,
                'log_burnin': p.getint,
                'path_sampling': p.getboolean,
                'preburnin': p.getint,
                'sample_from_prior': p.getboolean,
                'steps': p.getint,
            },
            'languages': {
                'exclusions': p.get,
                'languages': p.get,
                'families': p.get,
                'macroareas': p.get,
                'overlap': p.get,
                'starting_tree': p.get,
                'sample_branch_lengths': p.getboolean,
                'sample_topology': p.getboolean,
                'subsample_size': p.getint,
                'monophyly': p.getboolean,
                'monophyletic': p.getboolean,
                'monophyly_start_depth': p.getint,
                'monophyly_end_depth': p.getint,
                'monophyly_levels': p.getint,
                'monophyly_newick': p.get,
                'monophyly_direction': lambda s, o: p.get(s, o).lower(),
                'tree_prior': p.get,
            },
        }.items():
            if p.has_section(sec):
                for opt, val in p.items(sec):
                    try:
                        setattr(self, opt, getters[opt](sec, opt))
                    except KeyError:
                        raise ValueError("Unrecognised option %s in section %s!" % (opt, sec))

        # Handle some logical implications
        if self.log_fine_probs:
            self.log_probabilities = True

        ## MCMC
        self.sample_from_prior |= self.prior
        if self.prior and self.path_sampling:
            raise ValueError(
                "Cannot sample from the prior during a path sampling analysis."
            )
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
            self.monophyly = True
        if p.has_option(sec,'minimum_data'):
            self.minimum_data = p.getfloat(sec, "minimum_data")

        ## Language groups
        if p.has_section("language_groups"):
            for name, components_string in p.items("language_groups"):
                self.language_group_configs[name] = components_string

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

        # Geographic priors
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
            elif key in ('mean','variance'):
                value = p.getfloat(section, key)
            elif key in ('rate',):
                try:
                    value = p.getfloat(section, key)
                except ValueError:
                    pass # and hope it's a prior clock
            cfg[key] = value
        return cfg

    def get_model_config(self, p, section):
        section_parts = section.split(None, 1)
        if len(section_parts) == 1:
            raise ValueError("All model sections must have a name!")
        cfg = {
            'name': section_parts[1].strip().replace(" ","_"),
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
            if key in ("features", "reconstruct", "exclusions", "reconstruct_at"):
                value = self.handle_file_or_list(value)
            if key in ['ascertained','pruned','rate_variation', 'remove_constant_features', 'use_robust_eigensystem']:
                value = p.getboolean(section, key)

            if key in ['minimum_data']:
                value = p.getfloat(section, key)

            if key in ['data']:
                value = Path(value)
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
            elif key == "data":
                # Just set the Configuration class attribute, don't put it in this dict
                self.location_data = value
                continue 
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

        # Add dependency notices if required
        if self.monophyly and not self.starting_tree:
            self.messages.append("[DEPENDENCY] ConstrainedRandomTree is implemented in the BEAST package BEASTLabs.")
        if self.path_sampling:
            self.messages.append("[DEPENDENCY] Path sampling is implemented in the BEAST package MODEL_SELECTION.")

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
        self.define_language_groups()
        self.handle_monophyly()
        self.instantiate_calibrations()
        # At this point, we can tell whether or not the tree's length units
        # can be treated as arbitrary
        self.arbitrary_tree = self.sample_branch_lengths and not self.calibrations

        # We also know what kind of tree prior we need to have –
        # instantiate_calibrations may have changed the type if tip
        # calibrations exist.
        self.treeprior = {
            "uniform": treepriors.UniformTree,
            "yule": treepriors.YuleTree,
            "birthdeath": treepriors.BirthDeathTree,
            "coalescent": CoalescentTree
        }[self.tree_prior.lower()]()

        # Now we can set the value of the ascertained attribute of each model
        # Ideally this would happen during process_models, but this is impossible
        # as set_ascertained() relies upon the value of arbitrary_tree defined above,
        # which itself depends on process_models().  Ugly...
        for m in self.models:
            m.set_ascertained()
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

    def define_language_groups(self):
        """Parse the [language_groups] section.

        Every individual language is a language group of size one. Additional
        groups can be specified as comma-separated lists of already-defined
        groups. (This does of course include comma-separated lists of
        languages, but definitions can be nested.)

        TODO: In the future, the [languages] section should gain a property
        such that language groups can be specified using external sources.

        """
        self.language_groups = {language: {language} for language in self.languages}
        self.language_groups["root"] = set(self.languages)

        for name, specification in self.language_group_configs.items():
            taxa = set()
            for already_defined in specification.split(","):
                taxa |= set(self.language_group(already_defined.strip()))
            self.language_groups[name] = taxa

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
            ancestor = node.ancestor
            if not ancestor:
                # Node is root of some family
                return [label2name[node.name]]
            res = []
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

            if t.latitude and t.longitude:
                latlon = (float(t.latitude), float(t.longitude))
                self.locations[t.glottocode] = latlon
                for isocode in t.isocodes.split():
                    self.locations[isocode] = latlon

        # Second pass of geographic data to handle dialects, which inherit
        # their parent language's location
        for t in reader(
                get_glottolog_data('geo', self.glottolog_release), namedtuples=True):
            if t.level == "dialect":
                failed = False
                if node not in glottocode2node:
                    continue
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
        # Read location data from file, patching (rather than replacing) Glottolog
        location_files = [x.strip() for x in self.location_data.split(",")]
        for loc_file in location_files:
            for language, location in load_location_data(loc_file).items():
                self.locations[language] = location

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
                count += len([x for x in model.data[lang].values() if x])
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
        if len(langs) != len(self.languages):
            # Warn the user that some taxa aren't in Glottolog and hence will be
            # forced into an outgroup.
            missing_langs = [l for l in self.languages if l not in langs]
            missing_langs.sort()
            missing_str = ",".join(missing_langs[0:3])
            missing_count = len(missing_langs)
            if missing_count > 3:
                missing_str += ",..."
            self.messages.append("""[WARNING] %d languages could not be found in Glottolog (%s).  Monophyly constraints will force them into an outgroup.""" %
                    (missing_count, missing_str))
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

        N = len(langs)
        # Find the ancestor of all the given languages at at particular depth
        # (i.e. look `depth` nodes below the root of the Glottolog tree)
        groupings = list(set([subgroup(l, depth) for l in langs]))
        if len(groupings) == 1:
            # If all languages belong to the same classificatio at this depth,
            # there are two possibilities
            if groupings[0] == "":
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

            # Group up those languages which share a non-blank Glottolog classification
            partition = [[l for l in langs if subgroup(l, depth) == group] for group in groupings if group != ""]
            # Add those languages with blank classifications in their own isolate groups
            for l in langs:
                if subgroup(l, depth) == "":
                    partition.append([l,])
            # Get rid of any empty sets we may have accidentally created
            partition = [part for part in partition if part]
            # Make sure we haven't lost any langs
            assert sum((len(p) for p in partition)) == N
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

        # First, transform e.g. [['foo'], [['bar']], [[[['baz']]]]], into simply
        # ['foo','bar','baz'].
        def denester(l):
            if type(l) != list:
                return l
            if len(l) == 1:
                return denester(l[0])
            return [denester(x) for x in l]
        struct = denester(struct)
        # Now check for internal structure
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
            elif config["type"].lower() == "strict_with_prior":
                clock = prior_clock.StrictClockWithPrior(config, self)
            elif config["type"].lower() == "relaxed":
                clock = relaxed.relaxed_clock_factory(config, self)
            elif config["type"].lower() == "random":
                clock = random_clock.RandomLocalClock(config, self)
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
            elif config["model"].lower() == "binaryctmc":
                model = binaryctmc.BinaryCTMCModel(config, self)
            elif config["model"].lower() == "pseudodollocovarion":
                model = pseudodollocovarion.PseudoDolloCovarionModel(
                    config, self)
            elif config["model"].lower() == "mk":
                model = mk.MKModel(config, self)
                if "mk_used" not in self.message_flags:
                    self.message_flags.append("mk_used")
                    self.messages.append(mk.MKModel.package_notice)
            elif config["model"].lower() == "dollo": # pragma: no cover
                raise NotImplementedError("The stochastic Dollo model is not implemented yet.")
                model = dollo.StochasticDolloModel(config, self)
                if dollo.StochasticDolloModel.package_notice not in self.messages:
                    self.messages.append(dollo.StochasticDolloModel.package_notice)
            else:
                try:
                    sys.path.insert(0, os.getcwd())
                    module_path, class_name = config["model"].rsplit(".",1)
                    module = importlib.import_module(module_path)
                    UserClass = getattr(module, class_name)
                except:
                    raise ValueError("Unknown model type '%s' for model section '%s', and failed to import a third-party model." % (config["model"], config["name"]))
                model = UserClass(config, self)

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
            self.messages.extend(model.messages)

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
            if model.pruned and isinstance(model.clock, random_clock.RandomLocalClock):
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

        ## Perform subsampling, if requested
        self.languages = sorted(self.subsample_languages(self.languages))
        self.messages.append("[INFO] %d languages included in analysis." % len(self.languages))

        ## SPREAD THE WORD!
        for m in self.models:
            m.languages = [l for l in m.languages if l in self.languages]

    def subsample_languages(self, languages):
        """
        Return a random subsample of languages with a specified size
        """
        if not self.subsample_size:
            return languages
        if self.subsample_size > len(languages):
            self.messages.append("[INFO] Requested subsample size is %d, but only %d languages to work with!  Disabling subsampling." % (self.subsample_size, len(languages)))
            return languages
        # Seed PRNG with sorted language names
        # Python will convert to an integer hash
        # This means we always take the same subsample for a particular
        # initial language set.
        self.messages.append("[INFO] Subsampling %d languages down to %d." % (len(languages), self.subsample_size))
        random.seed(",".join(sorted(languages)))
        return random.sample(languages, self.subsample_size)

    def language_group(self, clade):
        """Look up a language group locally or as a glottolog clade."""
        try:
            return self.language_groups[clade]
        except KeyError:
            langs = self.get_languages_by_glottolog_clade(clade)
            self.language_groups[clade] = langs
            if not langs:
                raise ValueError(
                    "Language group or Glottolog clade {:} not found "
                    "or was empty for the languages given.".format(
                        clade))
            return langs

    def instantiate_calibrations(self):
        self.calibrations = {}
        """ Calibration distributions for calibrated clades """
        self.tip_calibrations = {}
        """ Starting heights for calibrated tips """
        useless_calibrations = []
        for clade, cs in self.calibration_configs.items():
            orig_clade = clade[:]
            originate = False
            is_tip_calibration = False
            # Parse the clade identifier
            # First check for originate()
            if clade.lower().startswith("originate(") and clade.endswith(")"):
                originate = True
                clade = clade[10:-1]
            # The clade is specified as a language_group, either
            # explicitly defined or the builtin "root" or a Glottolog
            # identifier
            langs = self.language_group(clade)

            if langs == self.language_groups["root"] and originate:
                raise ValueError("Root has no ancestor, but originate(root) was given a calibration.")

            # Figure out what kind of calibration this is and whether it's valid
            if len(langs) > 1:
                ## Calibrations on multiple taxa are always valid
                pass
            elif not langs: # pragma: no cover
                # Calibrations on zero taxa are never valid, so abort
                # and skip to the next cal. This should never happen,
                # because empty calibrations can only be specified by
                # empty language groups, which should be caught before
                # this.
                self.messages.append("[INFO] Calibration on clade '%s' ignored as no matching languages in analysis." % clade)
                continue
            # At this point we know that len(langs) == 1, so that condition is
            # implicit in the conditions for all the branches below
            elif originate:
                ## Originate calibrations on single taxa are always valid
                pass
            elif "," not in clade and clade in self.languages:
                ## This looks like a tip calibration, i.e. the user has specified
                ## only one identifier, not a comma-separated list, and that
                ## identifier matches a language, not a Glottolog family that we
                ## happen to only have one language for
                self.messages.append("[INFO] Calibration on '%s' taken as tip age calibration." % clade)
                is_tip_calibration = True
                self.tree_prior = "coalescent"
            else: # pragma: no cover
                # At this point we have a non-originate calibration on
                # a single taxa, which is not the result of
                # specifically asking for only this taxa. Probably the
                # user did not expect to get here. They might want
                # this to be an originate cal, or a tip cal, but we
                # can't tell with what we know and shouldn't
                # guess. Abort and skip to the next cal. This should
                # never happen, because empty calibrations can only be
                # specified by empty language groups, which should be
                # caught before this.

                self.messages.append("[INFO] Calibration on clade '%s' matches only one language.  Ignoring due to ambiguity.  Use 'originate(%s)' if this was supposed to be an originate calibration, or explicitly identify the single language using '%s' if this was supposed to be a tip calibration." % (clade, clade, langs[0]))
                continue

            # Make sure this calibration point, which will induce a monophyly
            # constraint, does not conflict with the overall monophyly
            # constraints from Glottolog or a user-tree
            if self.monophyly and len(langs) > 1:
                mono_tree = newick.loads(self.monophyly_newick)[0]
                cal_clade = set(langs)
                for node in mono_tree.walk():
                    mono_clade = set(node.get_leaf_names())
                    # If the calibration clade is not a subset of this monophyly clade, keep searching
                    if not cal_clade.issubset(mono_clade):
                        continue
                    # At this point, we can take it for granted the cal clade is a subset of the mono_clade
                    # We are happy if the calibration clade is exactly this monophyly clade
                    if mono_clade == cal_clade:
                        break
                    # We are also happy if this mono_clade is a "terminal clade", i.e. has no finer structure
                    # which the calibration clade may violate
                    elif all((child.is_leaf for child in node.descendants)):
                        break
                    # We are also happy if the calibration clade is a union of descendant mono clades
                    elif all(set(child.get_leaf_names()).issubset(cal_clade) or len(set(child.get_leaf_names()).intersection(cal_clade)) == 0 for child in node.descendants):
                        break
                else:
                    # If we didn't break out of this loop, then the languages
                    # in this calibration do not constitute a clade of the
                    # monophyly tree
                    raise ValueError("Calibration on for clade %s violates a monophyly constraint!" % (clade))

            # Next parse the calibration string and build a Calibration object
            cal_obj = Calibration.from_string(
                string=cs,
                context="calibration of clade {:}".format(orig_clade),
                is_point=is_tip_calibration,
                langs=langs,
                originate=originate)

            # Choose a name
            if originate:
                clade_identifier = "%s_originate" % clade
            elif is_tip_calibration:
                clade_identifier = "%s_tip" % clade
            else:
                clade_identifier = clade

            # Store the Calibration object under the chosen name
            if is_tip_calibration:
                self.tip_calibrations[clade_identifier] = cal_obj
            else:
                self.calibrations[clade_identifier] = cal_obj

    def get_languages_by_glottolog_clade(self, clade):
        """
        Given a comma-separated list of Glottolog ids, return a list of all
        languages descended from the corresponding Glottolog nodes.
        """
        langs = []
        clades = [c.strip() for c in clade.split(",")]
        matched_clades = []
        # First look for clades which are actually language identifiers
        for clade in clades:
            if clade in self.languages:
                langs.append(clade)
                matched_clades.append(clade)

        # Once a clade has matched against a language name, don't let it
        # subsequently match against anything in Glottolog!
        for clade in matched_clades:
            clades.remove(clade)

        # If all clades matched against language names, don't bother
        # searching Glottolog.
        if not clades:
            return langs

        # Now search against Glottolog
        clades = [c.lower() for c in clades]
        for l in self.languages:
            # No repeated matching!
            if l in langs:
                continue
            for name, glottocode in self.classifications.get(l.lower(),""):
                if name.lower() in clades or glottocode in clades:
                    langs.append(l)
                    break

        return langs

    def handle_user_supplied_tree(self, value, tree_type):
        """Load a tree from file or parse a string, and simplify.

        If the provided value is the name of an existing file, read
        the contents and treat it as a Newick tree
        specification. Otherwise, assume the provided value is a
        Newick tree specification.

        Trees consisting of only one leaf are considered errors,
        because they are never useful and can easily arise when a
        non-existing file name is parsed as tree, leading to confusing
        error messages down the line.

        In either case, inspect the tree and make appropriate minor
        changes so it is suitable for inclusion in the BEAST XML file.

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
            if ")" in value:
                # A tree with only one node (which is the only Newick
                # string without bracket) is not a useful tree
                # specification.
                value = self.sanitise_tree(value, tree_type)
            else:
                raise ValueError(
                    "Starting tree specification {:} is neither an existing"
                    " file nor does it look like a useful tree.".format(
                        value))
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
        if not tree_langs == set(self.languages):
            tree.prune_by_names(self.languages, inverse=True)
            self.messages.append("[INFO] %s tree includes languages not present in any data set and will be pruned." % tree_type.capitalize())
        # Get the tree looking nice
        tree.remove_redundant_nodes()
        tree.remove_internal_names()
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
