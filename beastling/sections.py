from configparser import ConfigParser

import attr

__all__ = ['Admin']


@attr.s
class Section(object):
    name = attr.ib()
    cli_params = attr.ib(attr.Factory(dict))

    @classmethod
    def from_config(cls, cli_params, section, cfg):
        kw = {}
        for field in attr.fields(cls):
            if field.name not in ['name', 'cli_params']:
                opt = field.name
                if opt.endswith('_'):
                    opt = opt[:-1]
                if (section in cfg) and (opt in cfg[section]):
                    method = field.metadata.get('getter', ConfigParser.get)
                    kw[field.name] = method(cfg, section, opt)
        return cls(name=section, cli_params=cli_params, **kw)


def opt(default, help, getter=ConfigParser.get, **kw):
    return attr.ib(default, metadata=dict(help=help, getter=getter), **kw)


@attr.s
class Admin(Section):
    basename_ = opt(
        'beastling',
        "Used as a common prefix for output filenames (e.g. the log will be called basename.log).",
        validator=attr.validators.instance_of(str))
    embed_data = opt(
        False,
        "A boolean value, controlling whether or not to embed data files in the XML.",
        getter=ConfigParser.getboolean)
    screenlog = opt(
        True,
        "A boolean parameter, controlling whether or not to log some basic output to stdout.",
        getter=ConfigParser.getboolean)
    log_all = opt(
        False,
        "A boolean value, setting this True is a shortcut for setting log_params, "
        "log_probabilities, log_fine_probs and log_trees True.",
        getter=ConfigParser.getboolean)
    log_dp = opt(
        4,
        "An integer value, setting the number of decimal points to use when logging rates, "
        "locations, etc.  Defaults to 4.  Use -1 to enable full precision.",
        getter=ConfigParser.getint)
    log_every = opt(
        0,
        "An integer indicating how many MCMC iterations should occurr between consecutive log "
        "entries.",
        getter=ConfigParser.getint)
    log_probabilities = opt(
        True,
        "A boolean value, controlling whether or not to log the prior, likelihood and posterior "
        "of the analysis.",
        getter=ConfigParser.getboolean)
    log_fine_probs = opt(
        False,
        "A boolean value, controlling whether or not to log individual components of the prior "
        "and likelihood.  Setting this True automatically sets log_probabilities True.",
        getter=ConfigParser.getboolean)
    log_params = opt(
        False,
        "A boolean value, controlling whether or not to log model parameters.",
        getter=ConfigParser.getboolean)
    log_trees = opt(
        True,
        "A boolean value, controlling whether or not to log the sampled trees.",
        getter=ConfigParser.getboolean)
    log_pure_tree = opt(
        False,
        "A boolean value, controlling whether or not to log a separate file of the sampled "
        "trees with no metadata included.",
        getter=ConfigParser.getboolean)
    glottolog_release = opt(
        "4.0",
        "A string representing a Glottolog release number.",
        getter=ConfigParser.get)

    def __attrs_post_init__(self):
        if self.log_all:
            self.log_trees = self.log_params = self.log_probabilities = self.log_fine_probs = True

    @property
    def basename(self):
        return '{0}_prior'.format(self.basename_) \
            if self.cli_params.get('prior') else self.basename_
