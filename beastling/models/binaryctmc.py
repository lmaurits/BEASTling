import xml.etree.ElementTree as ET

from .binary import BinaryModelWithShareParams as BinaryModel


class BinaryCTMCModel(BinaryModel):

    def __init__(self, model_config, global_config):

        BinaryModel.__init__(self, model_config, global_config)
        self.subst_model_id = None

    def get_userdatatype(self, feature, fname):
        if not self.beastxml._binary_userdatatype_created:
            self.beastxml._binary_userdatatype_created = True
            return ET.Element("userDataType", {"id":"BinaryDatatype", "spec":"beast.evolution.datatype.Binary"})
        else:
            return ET.Element("userDataType", {"idref":"BinaryDatatype"})


    def add_substmodel(self, sitemodel, feature, fname):
        # If we're sharing one substmodel across all features and have already
        # created it, just reference it and that's it
        if self.subst_model_id:
            sitemodel.set("substModel", "@%s" % self.subst_model_id)
            return

        if feature:
            name = "%s:%s" % (self.name, feature)
        else:
            name = self.name

        subst_model_id = "%s:binaryCTMC.s" % name
        if not feature:
            self.subst_model_id = "%s:binaryCTMC.s" % name
        substmodel = ET.SubElement(sitemodel, "substModel",{"id":subst_model_id,"spec":"GeneralSubstitutionModel"})

        rates = ET.SubElement(substmodel, "parameter",{"id":"rates.s:%s" % name, "dimension":"2", "estimate":"false","name":"rates"})
        rates.text="1.0 1.0"
        
        if self.frequencies == "estimate":
            freq = ET.SubElement(substmodel,"frequencies",{"id":"estimatedFrequencies.s:%s"%name,"spec":"Frequencies", "frequencies":"@freqs_param.s:%s"%name})
        elif self.frequencies == "empirical":
            freq = ET.SubElement(substmodel,"frequencies",{"id":"empiricalFrequencies.s:%s"%name,"spec":"Frequencies", "data":"@feature_data_%s"%name})
        elif self.frequencies == "uniform":
            freq = ET.SubElement(substmodel, "frequencies", {"id":"frequencies.s:%s" % name, "dimension":"2","spec":"parameter.RealParameter"})
            freq.text="0.5 0.5"
