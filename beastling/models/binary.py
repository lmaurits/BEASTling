import xml.etree.ElementTree as ET

from .basemodel import BaseModel


class BinaryModel(BaseModel):

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        # Compute feature properties early to facilitate auto-detection of binarisation
        self.compute_feature_properties()
        self.data_separator = ""
        if model_config.get("binarised", None) is None:
            # We've not been explicitly told if the data has been binarised
            # or not.  So attempt automagic:
            if all([self.valuecounts[f]==2 for f in self.features]):
                self.binarised = True
                self.messages.append("""[INFO] Model "%s": Assuming that data source %s contains pre-binarised cognate data.  Set "binarised=False" in config to stop this.""" % (self.name, self.data_filename))
            else:
                self.binarised = False
        else:
            # If we've been told, listen.
            self.binarised = model_config["binarised"]
        if self.constant_feature:
            self.ascertained = False
            self.messages.append("""[INFO] Model "%s": Constant features in data have been retained, so ascertainment correction will be disabled.""" % (self.name))
        else:
            self.ascertained = model_config.get("ascertained", True)
            if str(self.ascertained).lower() == "false":
                self.ascertained = False

    def format_datapoint(self, feature, point):
        extra_columns = 1 if self.ascertained else 0
        if self.binarised:
            if point == "?":
                valuestring = "??" if self.ascertained else "?"
            else:
                valuestring = str(self.unique_values[feature].index(point))
                if self.ascertained:
                    valuestring = "0" + valuestring
        else:
            if point == "?":
                valuestring = "".join(["?" for i in range(0,len(self.unique_values[feature])+extra_columns)])
            else:
                valuestring = ["0" for i in range(0,len(self.unique_values[feature])+extra_columns)]
                valuestring[self.unique_values[feature].index(point)+extra_columns] = "1"
                valuestring = "".join(valuestring)
        return valuestring

    def add_feature_data(self, distribution, index, feature, fname):
        data = BaseModel.add_feature_data(self, distribution, index, feature, fname)
        if self.ascertained:
            data.set("ascertained", "true")
            data.set("excludefrom", "0")
            data.set("excludeto", "1")
        else:
            data.set("ascertained", "false")
