import xml.etree.ElementTree as ET

from .basemodel import BaseModel


class MKModel(BaseModel):

    package_notice = """[DEPENDENCY]: The Lewis Mk substitution model is implemented in the BEAST package "morph-models"."""

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        self.subst_models = {}

    def add_substmodel(self, sitemodel, feature, fname):
        key = self._get_substmodel_key(feature)
        if key and key in self.subst_models:
            substmodel = ET.SubElement(sitemodel, "substModel", {"idref":self.subst_models[key]})
        else:
            sm_id = "mk.s:%s"%fname
            substmodel = ET.SubElement(sitemodel, "substModel",{"id":sm_id,"spec":"LewisMK","datatype":"@featureDataType.%s" % fname})
            # Do empirical frequencies
            # We don't need to do anything for uniform freqs
            # as the implementation of LewisMK handles it
            if self.frequencies == "empirical":
                freq = ET.SubElement(substmodel,"frequencies",{"id":"feature_freqs.s:%s"%fname,"spec":"Frequencies", "data":"@data_%s"%fname})
            elif self.frequencies == "approx":
                freq = ET.SubElement(substmodel,"frequencies",{"id":"feature_freqs.s:%s"%fname,"spec":"Frequencies", "frequencies":self._get_approx_freq_string(feature)})
            elif self.frequencies == "estimate":
                freq = ET.SubElement(substmodel,"frequencies",{"id":"feature_freqs.s:%s"%fname,"spec":"Frequencies", "frequencies":"@feature_freqs_param.s:%s"%fname})
            self.subst_models[key] = sm_id
        return substmodel

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
        assert abs(1 - sum(freqs) < 1e-10)
        freq_string = " ".join([str(f) for f in freqs])
        return freq_string

    def _get_substmodel_key(self, feature):
        if self.frequencies == "uniform":
            # If we are using uniform frequencies, any two features with the
            # same sized state space may share a substmodel
            return self.valuecounts[feature]
        elif self.frequencies == "approx":
            # If we are using approximate empirical families, the state space
            # size and the frequency vector must match
            return (self.valuecounts[feature], self._get_approx_freq_string(feature))
        else:
            # If we're using fully empirical or estimated frequencies, we
            # can't share
            return None

