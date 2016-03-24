# coding: utf8
from __future__ import unicode_literals

from clldutils.testing import WithTempDir

from beastling.configuration import Configuration


CACHE = dict(classifications=None, locations=None, glotto_macroareas=None)


class WithConfigAndTempDir(WithTempDir):
    def make_cfg(self, configfile, from_cache=True):
        config = Configuration(configfile=configfile)
        if from_cache:
            if not CACHE['classifications']:
                try:
                    config.process()
                    for k in CACHE:
                        CACHE[k] = getattr(config, k)
                except:
                    pass
            if CACHE['classifications']:
                for k, v in CACHE.items():
                    setattr(config, k, v)
        return config
