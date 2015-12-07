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
            sitemodel = ET.SubElement(distribution, "siteModel", {"id":"geoSiteModel.%s"%traitname,"spec":"SiteModel", "mutationRate":"1","shape":"1","proportionInvariant":"0"})

            substmodel = ET.SubElement(sitemodel, "substModel",{"id":"svs.s:%s"%traitname,"spec":"LewisMK","datatype":"@traitDataType.%s" % traitname})
            if self.pruned:
                freq = ET.SubElement(substmodel,"frequencies",{"id":"traitfreqs.s:%s"%traitname,"spec":"Frequencies", "data":"@%s.filt"%traitname})
            else:
                freq = ET.SubElement(substmodel,"frequencies",{"id":"traitfreqs.s:%s"%traitname,"spec":"Frequencies", "data":"@%s"%traitname})
