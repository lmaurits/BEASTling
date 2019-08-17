import itertools
import random
from pathlib import Path
from configparser import ConfigParser

import newick
from appdirs import user_data_dir
from csvw.dsv import reader

from beastling.fileio.datareaders import iterlocations
import beastling.clocks.random as random_clock

import beastling.models.geo as geo

from beastling import sections
from beastling.util import log
from beastling.util import monophyly
from beastling.util.misc import retrieve_url

import beastling.treepriors.base as treepriors
from beastling.treepriors.coalescent import CoalescentTree
from beastling.distributions import Calibration

_BEAST_MAX_LENGTH = 2147483647


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

    path = Path(__file__).parent / 'data' / fname
    if not path.exists():
        data_dir = Path(user_data_dir('beastling'))
        if not data_dir.exists():
            data_dir.mkdir(parents=True)
        path = data_dir / fname
        if not path.exists():
            try:
                retrieve_url(
                    'https://glottolog.org/static/download/{0}/{1}'.format(release, fname_source),
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

    def __init__(self, basename="beastling", configfile=None, stdin_data=False, prior=False, force_glottolog_load=False):
        """
        Set all options to their default values and then, if a configuration
        file has been provided, override the default values for those options
        set in the file.
        """
        cli_params = {k: v for k, v in locals().items()}

        # Options set by the user, with default values
        """A dictionary whose keys are glottocodes or lowercase Glottolog clade names, and whose values are length-2 tuples of flatoing point dates (lower and upper bounds of 95% credible interval)."""
        self.calibration_configs = {}
        """A list of `sections.Clock`s, each of which specifies the configuration for a single clock model."""
        self.clocks = []
        self.clocks_by_name = {}

        """An ordered dictionary whose keys are language group names and whose values are language group definitions."""
        self.language_groups = {}
        """A dictionary giving names to arbitrary collections of tip languages."""

        """A list of dictionaries, each of which specifies the configuration for a single evolutionary model."""
        self.models = []
        self.stdin_data = stdin_data
        """A boolean value, controlling whether or not to read data from stdin as opposed to the file given in the config."""

        # Glottolog data
        self.glottolog_loaded = False
        self.force_glottolog_load = force_glottolog_load
        self.classifications = {}
        self.glotto_macroareas = {}
        self.locations = {}

        # Options set from the command line interface
        self.prior = prior

        # Stuff we compute ourselves
        self.processed = False
        self._files_to_embed = []

        # Now read the config ...
        self.cfg = ConfigParser(interpolation=None)
        self.cfg.optionxform = str
        if configfile:
            if isinstance(configfile, dict):
                self.cfg.read_dict(configfile)
            else:
                if isinstance(configfile, str):
                    configfile = (configfile,)
                self.cfg.read([str(c) for c in configfile])

        # ... and process the sections:
        # [geography]
        if 'geography' in self.cfg.sections():
            self.geography = sections.Geography.from_config(cli_params, 'geography', self.cfg)
        else:
            self.geography = None

        # [calibration]
        for clade, calibration in sections.Calibration.from_config(
                {}, "calibration", self.cfg).options.items():
            self.calibration_configs[clade] = calibration

        # [model ...] and [clock ...]
        for prefix, cfg_cls in [('clock', sections.Clock), ('model', sections.Model)]:
            for section in [s for s in self.cfg.sections() if s.lower().startswith(prefix)]:
                getattr(self, prefix + 's').append(
                    cfg_cls.from_config({}, section, self.cfg))

        # Make sure analysis is non-empty
        if not (self.models or self.geography):
            raise ValueError("Config file contains no model sections and no geography section.")

        # [geo_priors]
        if self.cfg.has_section("geo_priors"):
            if not self.geography:
                raise ValueError("Config file contains geo_priors section but no geography section.")
            for clade, klm in sections.GeoPriors.from_config(
                    {}, 'geo_priors', self.cfg).iterpriors():
                if clade not in self.geography.sampling_points:
                    self.geography.sampling_points.append(clade)
                self.geography.priors[clade] = klm

        # [admin]
        self.admin = sections.Admin.from_config(cli_params, 'admin', self.cfg)
        # [mcmc]
        self.mcmc = sections.MCMC.from_config(
            cli_params, 'mcmc' if self.cfg.has_section('mcmc') else 'MCMC', self.cfg)
        # [languages]
        self.languages = sections.Languages.from_config(cli_params, 'languages', self.cfg)
        # [language_groups]
        self.language_group_configs = sections.LanguageGroups.from_config(
            {}, 'language_groups', self.cfg).options

        # If log_every was not explicitly set to some non-zero
        # value, then set it such that we expect 10,000 log
        # entries
        if not self.admin.log_every:
            # If chainlength < 10000, this results in log_every = zero.
            # This causes BEAST to die.
            # So in this case, just log everything.
            self.admin.log_every = self.mcmc.chainlength // 10000 or 1

        if self.geography \
                and [p for p in self.geography.sampling_points if p.lower() != "root"] \
                and self.languages.sample_topology and not self.languages.monophyly:
            log.warning(
                "Geographic sampling and/or prior specified for clades other than root, but tree "
                "topology is being sampled without monophyly constraints. BEAST may crash.")

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
        if self.processed:
            log.warning('Configuration has already been processed')
            return

        # Add dependency notices if required
        if self.languages.monophyly and not self.languages.starting_tree:
            log.dependency("ConstrainedRandomTree", "BEASTLabs")
        if self.mcmc.path_sampling:
            log.dependency("Path sampling", "MODEL_SELECTION")

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
        self.arbitrary_tree = self.languages.sample_branch_lengths and not self.calibrations

        # We also know what kind of tree prior we need to have –
        # instantiate_calibrations may have changed the type if tip
        # calibrations exist.
        self.treeprior = {
            "uniform": treepriors.UniformTree,
            "yule": treepriors.YuleTree,
            "birthdeath": treepriors.BirthDeathTree,
            "coalescent": CoalescentTree
        }[self.languages.tree_prior]()

        # Now we can set the value of the ascertained attribute of each model
        # Ideally this would happen during process_models, but this is impossible
        # as set_ascertained() relies upon the value of arbitrary_tree defined above,
        # which itself depends on process_models().  Ugly...
        for m in self.models:
            m.set_ascertained()
        self.instantiate_clocks()
        self.link_clocks_to_models()
        self.processed = True

        # Decide whether or not to log trees
        if (
            self.languages.starting_tree and
            not self.languages.sample_topology and
            not self.languages.sample_branch_lengths and
            all([c.is_strict for c in self.clocks if c.is_used])
        ):
            self.tree_logging_pointless = True
            log.info(
                "Tree logging disabled because starting tree is known and fixed and all clocks "
                "are strict.")
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
        self.language_groups = {language: {language} for language in self.languages.languages}
        self.language_groups["root"] = set(self.languages.languages)

        for name, specification in self.language_group_configs.items():
            taxa = set()
            for already_defined in specification:
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
            log.warning('Glottolog data has already been loaded')
            return
        self.glottolog_loaded = True

        self.classifications, glottocode2node, label2name = monophyly.classifications_from_newick(
           str(get_glottolog_data('newick', self.admin.glottolog_release)))

        # Load geographic metadata
        dialects = []
        for t in reader(
                get_glottolog_data('geo', self.admin.glottolog_release), dicts=True):
            identifiers = [t['glottocode']] +t['isocodes'].split()
            if t['level'] == "dialect":
                dialects.append((t, identifiers))
            if t['macroarea']:
                for id_ in identifiers:
                    self.glotto_macroareas[id_] = t['macroarea']

            if t['latitude'] and t['longitude']:
                latlon = (float(t['latitude']), float(t['longitude']))
                for id_ in identifiers:
                    self.locations[id_] = latlon

        # Second pass of geographic data to handle dialects, which inherit
        # their parent language's location
        for t, identifiers in dialects:
            failed = False
            if t['glottocode'] not in glottocode2node:  # pragma: no cover
                # This may only happen for newick downloads of older Glottolog releases, where
                # possibly isolates may not be included.
                continue
            node = glottocode2node[t['glottocode']]
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
            for id_ in identifiers:
                self.locations[id_] = latlon

    def check_glottolog_required(self):
        # We need Glottolog if...
        return (
            # ...we've been given a list of families
            self.languages.families
            # ...we've been given a list of macroareas
            or self.languages.macroareas
            # ...we're using monophyly constraints
            or self.languages.monophyly
            # ...we're using calibrations (well, sometimes)
            or self.calibration_configs
            # ...we're using geography
            or self.geography
            # ...we've been forced to by greater powers (like the CLI)
            or self.force_glottolog_load
        )

    def load_user_geo(self):
        if self.geography:
            # Read location data from file, patching (rather than replacing) Glottolog
            for loc_file in self.geography.data:
                self.locations.update(dict(iterlocations(loc_file)))

    def build_language_filter(self):
        """
        Examines the values of various options, including self.languages.languages and
        self.languages.families, and constructs self.lang_filter.

        self.lang_filter is a Set object containing all ISO and glotto codes
        which are compatible with the provided settings (e.g. belong to the
        requested families).  This set is later used as a mask with data sets.
        Datapoints with language identifiers not in this set will not be used
        in an analysis.
        """
        # Load requirements
        if len(self.languages.families) == 1:
            log.warning("value of 'families' has length 1: have you misspelled a filename?")

        # Enforce minimum data constraint
        all_langs = set(itertools.chain(*[model.data.keys() for model in self.models]))
        N = sum([max([len(lang.keys()) for lang in model.data.values()]) for model in self.models])
        datapoint_props = {}
        for lang in all_langs:
            count = 0
            for model in self.models:
                count += len([x for x in model.data[lang].values() if x])
            datapoint_props[lang] = 1.0*count / N
        self.sparse_languages = [
            l for l in all_langs if datapoint_props[l] < self.languages.minimum_data]

    @property
    def files_to_embed(self):
        res = set(fname for fname in self._files_to_embed)
        for section in [self.admin, self.mcmc, self.languages]:
            res = res.union(section.files_to_embed)
        return res

    def filter_language(self, l):
        if self.languages.languages and l not in self.languages.languages:
            return False
        if self.languages.families and not any(
                name in self.languages.families or glottocode in self.languages.families
                for (name, glottocode) in self.classifications.get(l,[])):
            return False
        if self.languages.macroareas and self.glotto_macroareas.get(l,None) not in self.languages.macroareas:
            return False
        if self.languages.exclusions and l in self.languages.exclusions:
            return False
        if l in self.sparse_languages:
            return False
        return True

    def handle_monophyly(self):
        """
        Construct a representation of the Glottolog monophyly constraints
        for the languages in self.languages.languages.  If the constraints are
        meaningful, create and store a Newick tree representation of
        them.  If the constraints are not meaningful, e.g. all
        languages are classified identically by Glottolog, then override
        the monophyly=True setting.
        """
        if (not self.languages.monophyly) or self.languages.monophyly_newick:
            return
        if len(self.languages.languages) < 3:
            # Monophyly constraints are meaningless for so few languages
            self.languages.monophyly = False
            log.info(
                "Disabling Glottolog monophyly constraints because there are only %d languages in "
                "analysis." % len(self.languages.languages))
            return
        # Build a list-based representation of the Glottolog monophyly constraints
        # This can be done in either a "top-down" or "bottom-up" way.
        langs = [l for l in self.languages.languages if l.lower() in self.classifications]
        if len(langs) != len(self.languages.languages):
            # Warn the user that some taxa aren't in Glottolog and hence will be
            # forced into an outgroup.
            missing_langs = [l for l in self.languages.languages if l not in langs]
            missing_langs.sort()
            missing_str = ",".join(missing_langs[0:3])
            missing_count = len(missing_langs)
            if missing_count > 3:
                missing_str += ",..."
            log.warning(
                "%d languages could not be found in Glottolog (%s). Monophyly constraints will "
                "force them into an outgroup." % (missing_count, missing_str))
        if self.languages.monophyly_end_depth is not None:
            # A power user has explicitly provided start and end depths
            start = self.languages.monophyly_start_depth
            end = self.languages.monophyly_end_depth
        elif self.languages.monophyly_direction == "top_down":
            # Compute start and end in a top-down fashion
            start = self.languages.monophyly_start_depth
            end = start + self.languages.monophyly_levels
        elif self.languages.monophyly_direction == "bottom_up":
            # Compute start and end in a bottom-up fashion
            classifications = [self.classifications[name.lower()] for name in langs]
            end = max([len(c) for c in classifications]) - self.languages.monophyly_start_depth
            start = max(0, end - self.languages.monophyly_levels)
        struct = monophyly.make_structure(self.classifications, langs, depth=start, maxdepth=end)
        # Make sure this struct is not pointlessly flat
        if not monophyly.check_structure(struct):
            self.languages.monophyly = False
            log.info(
                "Disabling Glottolog monophyly constraints because all languages in the analysis "
                "are classified identically.")
        # At this point everything looks good, so keep monophyly on and serialise the "monophyly structure" into a Newick tree.
        self.languages.monophyly_newick = monophyly.make_newick(struct)

    def instantiate_clocks(self):
        """
        Populates self.clocks with a list of BaseClock subclasses, one for each
        dictionary of settings in self.clock_configs.
        """
        self.clocks = [clock.get_clock(self) for clock in self.clocks]
        self.clocks_by_name = {clock.name: clock for clock in self.clocks}

        if "default" not in self.clocks_by_name:
            clock = sections.Clock(cli_params={}, name='clock default').get_clock(self)
            self.clocks.append(clock)
            self.clocks_by_name[clock.name] = clock

    def instantiate_models(self):
        """
        Populates self.models with a list of BaseModel subclasses, one for each
        dictionary of settings in self.model_configs.
        """
        # Handle request to read data from stdin
        if self.stdin_data:
            for config in self.models:
                config["data"] = "stdin"

        self.models = [model.get_model(self) for model in self.models]

        if self.geography:
            self.geo_model = geo.GeoModel(self.geography, self)
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
            if model.pruned and isinstance(model.clock, random_clock.RandomLocalClock):
                model.pruned = False
                log.info(
                    "Disabling pruned trees because associated clock %s is a "
                    "RandomLocalClock. Pruned trees are currently only compatible with "
                    "StrictClocks and RelaxedClocks." % model.clock.name,
                    model=model)

        # Warn user about unused clock(s) (but not the default clock)
        for clock in self.clocks:
            if clock.name != "default" and not clock.is_used:
                log.info(
                    "Clock %s is not being used. Change its name to \"default\", or explicitly "
                    "associate it with a model." % clock.name)

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
                log.info(
                    "Clock \"%s\" has had it's mean rate fixed to 1.0. Tree branch lengths are in "
                    "units of expected substitutions for features in models using this "
                    "clock." % free_clocks[0].name)

        # Determine whether or not precision-scaling is required
        if self.geography:
            self.geo_model.scale_precision = False
            geo_clock = self.geo_model.clock
            for m in self.models:
                if m.clock == geo_clock:
                    log.warning(
                        "Geography model is sharing a clock with one or more data models. This may lead to a bad fit.")
                    self.geo_model.scale_precision = True
                    break
            # If geo has it's own clock, estimate the mean
            if not self.geo_model.scale_precision:
                self.geo_model.clock.estimate_rate = True

    def build_language_list(self):
        """
        Combines the language sets of each model's data set, according to the
        value of self.languages.overlap, to construct a final list of all the languages
        in the analysis.
        """
        if self.models:
            self.languages.languages = set(self.models[0].data.keys())
        else:
            # There are no models
            # So this must be a geography-only analysis
            # Start with all languages in Glottolog, then apply filters
            self.languages.languages = [l for l in self.classifications if self.filter_language(l)]
        self.overlap_warning = False
        for model in self.models:
            addition = set(model.data.keys())
            # If we're about to do a non-trivial union/intersect, alert the
            # user.
            if addition != self.languages.languages and not self.overlap_warning:
                log.info(
                    "Not all data files have equal language sets. BEASTling will use the %s of all "
                    "language sets. Set the \"overlap\" option in [languages] to change "
                    "this." % self.languages.overlap)
                self.overlap_warning = True
            self.languages.languages = getattr(set, self.languages.overlap)(
                self.languages.languages, addition)

        ## Make sure there's *something* left
        if not self.languages.languages:
            raise ValueError("No languages specified!")

        ## Convert back into a sorted list
        self.languages.languages = sorted(self.languages.languages)

        ## Perform subsampling, if requested
        self.languages.languages = sorted(self.subsample_languages(self.languages.languages))
        log.info("%d languages included in analysis." % len(self.languages.languages))

        ## SPREAD THE WORD!
        for m in self.models:
            m.languages = [l for l in m.languages if l in self.languages.languages]

        self.languages.sanitise_trees()

    def subsample_languages(self, languages):
        """
        Return a random subsample of languages with a specified size
        """
        if not self.languages.subsample_size:
            return languages
        if self.languages.subsample_size > len(languages):
            log.info(
                "Requested subsample size is %d, but only %d languages to work with! Disabling "
                "subsampling." % (self.languages.subsample_size, len(languages)))
            return languages
        # Seed PRNG with sorted language names
        # Python will convert to an integer hash
        # This means we always take the same subsample for a particular
        # initial language set.
        log.info("Subsampling %d languages down to %d." % (
            len(languages), self.languages.subsample_size))
        random.seed(",".join(sorted(languages)))
        return random.sample(languages, self.languages.subsample_size)

    def language_group(self, clade):
        """Look up a language group locally or as a glottolog clade."""
        if clade not in self.language_groups:
            self.language_groups[clade] = self.get_languages_by_glottolog_clade(clade)
            if not self.language_groups[clade]:
                raise ValueError(
                    "Language group or Glottolog clade {:} not found "
                    "or was empty for the languages given.".format(clade))
        return self.language_groups[clade]

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
                log.info("Calibration on clade '%s' ignored as no matching languages in analysis." % clade)
                continue
            # At this point we know that len(langs) == 1, so that condition is
            # implicit in the conditions for all the branches below
            elif originate:
                ## Originate calibrations on single taxa are always valid
                pass
            elif "," not in clade and clade in self.languages.languages:
                ## This looks like a tip calibration, i.e. the user has specified
                ## only one identifier, not a comma-separated list, and that
                ## identifier matches a language, not a Glottolog family that we
                ## happen to only have one language for
                log.info("Calibration on '%s' taken as tip age calibration." % clade)
                is_tip_calibration = True
                self.languages.tree_prior = "coalescent"
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

                log.info(
                    "Calibration on clade '%s' matches only one language. Ignoring due to "
                    "ambiguity. Use 'originate(%s)' if this was supposed to be an originate "
                    "calibration, or explicitly identify the single language using '%s' if this "
                    "was supposed to be a tip calibration." % (clade, clade, langs[0]))
                continue

            # Make sure this calibration point, which will induce a monophyly
            # constraint, does not conflict with the overall monophyly
            # constraints from Glottolog or a user-tree
            if self.languages.monophyly and len(langs) > 1:
                mono_tree = newick.loads(self.languages.monophyly_newick)[0]
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
        clades = set(c.strip() for c in clade.split(","))

        # First look for clades which are actually language identifiers
        langs = matched_clades = clades.intersection(self.languages.languages)

        # Once a clade has matched against a language name, don't let it
        # subsequently match against anything in Glottolog!
        clades = clades - matched_clades

        if clades:
            # Now search against Glottolog
            clades = [c.lower() for c in clades]
            for l in self.languages.languages:
                # No repeated matching!
                if l not in langs:
                    for name, glottocode in self.classifications.get(l.lower(), ""):
                        if name.lower() in clades or glottocode in clades:
                            langs.add(l)
                            break

        return list(langs)
