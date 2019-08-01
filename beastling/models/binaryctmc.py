from .binary import BinaryModelWithShareParams as BinaryModel
from beastling.util import xml


class BinaryCTMCModel(BinaryModel):

    def __init__(self, model_config, global_config):

        BinaryModel.__init__(self, model_config, global_config)
        self.subst_model_id = None

    def get_userdatatype(self, feature, fname):
        if not self.beastxml._binary_userdatatype_created:
            self.beastxml._binary_userdatatype_created = True
            return xml.userDataType(None, id="BinaryDatatype", spec="beast.evolution.datatype.Binary")
        return xml.userDataType(None, idref="BinaryDatatype")

    def add_substmodel(self, sitemodel, feature, fname):
        # If we're sharing one substmodel across all features and have already
        # created it, just reference it and that's it
        if self.subst_model_id:
            sitemodel.set("substModel", "@%s" % self.subst_model_id)
            return

        # Otherwise, create a substmodel
        name = self.name if self.share_params else fname
        subst_model_id = "binaryCTMC.s:%s" % name
        if self.share_params:
            self.subst_model_id = subst_model_id
        substmodel = xml.substModel(sitemodel, id=subst_model_id, spec="GeneralSubstitutionModel")
        xml.parameter(
            substmodel,
            text="1.0 1.0",
            id="rates.s:%s" % name,
            dimension=2,
            estimate="false",
            name="rates")

        if self.frequencies == "estimate":
            xml.frequencies(
                substmodel,
                id="estimatedFrequencies.s:%s" % name,
                spec="Frequencies",
                frequencies="@freqs_param.s:%s" % name)
        elif self.frequencies == "empirical":
            attribs = {"id": "empiricalFrequencies.s:%s" % name, "spec": "Frequencies"}
            if self.share_params:
                if self.single_sitemodel:
                    attribs["data"] = "@filtered_data_%s" % name
                else:
                    attribs["frequencies"] = self.build_freq_str()
            else:
                attribs["data"] = "@feature_data_%s" % name
            xml.frequencies(substmodel, attrib=attribs)
        elif self.frequencies == "uniform":
            xml.frequencies(
                substmodel,
                text="0.5 0.5",
                id="frequencies.s:%s" % name,
                dimension="2",
                spec="parameter.RealParameter")
