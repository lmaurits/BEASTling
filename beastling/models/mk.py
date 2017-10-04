import xml.etree.ElementTree as ET

from .basemodel import BaseModel


class MKModel(BaseModel):

    package_notice = """[DEPENDENCY]: The Lewis Mk substitution model is implemented in the BEAST package "morph-models"."""

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)

    def add_sitemodel(self, distribution, feature, fname):

            # Sitemodel
            mr = self.get_mutation_rate(feature, fname)
            sitemodel = ET.SubElement(distribution, "siteModel", {"id":"SiteModel.%s"%fname,"spec":"SiteModel", "mutationRate":mr,"shape":"1","proportionInvariant":"0"})

            substmodel = ET.SubElement(sitemodel, "substModel",{"id":"mk.s:%s"%fname,"spec":"LewisMK","datatype":"@featureDataType.%s" % fname})
            # Do empirical frequencies
            # We don't need to do anything for uniform freqs
            # as the implementation of LewisMK handles it
            if self.frequencies == "empirical":
                freq = ET.SubElement(substmodel,"frequencies",{"id":"feature_freqs.s:%s"%fname,"spec":"Frequencies", "data":"@data_%s"%fname})
            elif self.frequencies == "approx":
                freq = ET.SubElement(substmodel, "parameter",{
                    "id":"feature_freqs.s:%s"%fname,
                    "name":"frequencies",
                    "dimension":str(self.valuecounts[feature]),
                    })
                freq.text = self._get_approx_freq_string(feature)
            elif self.frequencies == "estimate":
                freq = ET.SubElement(substmodel,"frequencies",{"id":"feature_freqs.s:%s"%fname,"spec":"Frequencies", "frequencies":"@feature_freqs_param.s:%s"%fname})

    def _get_approx_freq_string(self, feature):
        freqs = [
            self.counts[feature].get(
                self.unique_values[feature][v], 0)
            for v in range(self.valuecounts[feature])]
        norm = float(sum(freqs))
        freqs = [f/norm for f in freqs]
        rounded_freqs = [round(f,1) for f in freqs]
        if sum(rounded_freqs) == 1:
            freqs = rounded_freqs
        assert sum(freqs) == 1
        freq_string = " ".join([str(f) for f in freqs])
        return freq_string
