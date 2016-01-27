import codecs
import os
import xml.etree.ElementTree as ET

from .basemodel import BaseModel
from ..unicodecsv import UnicodeDictReader

class MKModel(BaseModel):

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)

    def add_sitemodel(self, distribution, trait, traitname):

            # Sitemodel
            if self.rate_variation:
                mr = "@mutationRate:%s" % traitname
            else:
                mr = "1.0"
            sitemodel = ET.SubElement(distribution, "siteModel", {"id":"SiteModel.%s"%traitname,"spec":"SiteModel", "mutationRate":mr,"shape":"1","proportionInvariant":"0"})

            substmodel = ET.SubElement(sitemodel, "substModel",{"id":"mk.s:%s"%traitname,"spec":"LewisMK","datatype":"@traitDataType.%s" % traitname})
            # Do empirical frequencies
            # We don't need to do anything for uniform freqs
            # as the implementation of LewisMK handles it
            if self.frequencies == "empirical":
                if self.pruned:
                    freq = ET.SubElement(substmodel,"frequencies",{"id":"traitfreqs.s:%s"%traitname,"spec":"Frequencies", "data":"@%s.filt"%traitname})
                else:
                    freq = ET.SubElement(substmodel,"frequencies",{"id":"traitfreqs.s:%s"%traitname,"spec":"Frequencies", "data":"@%s"%traitname})
