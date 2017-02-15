import xml.etree.ElementTree as ET

from .basemodel import BaseModel


class BinaryModel(BaseModel):

    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        self.remove_constant_features = model_config.get("remove_constant_features", True)
        # Compute feature properties early to facilitate auto-detection of binarisation
        self.compute_feature_properties()
        # Don't need a separating comma because each datapoint is a string
        # of length 1
        self.data_separator = ""
        self.binarised = model_config.get("binarised", None)
        assert type(self.binarised) in (bool, type(None))
        # Do we need to recode multistate data?
        self.recoded = any([self.valuecounts[f]>2 for f in self.features])
        # Check for inconsistent configuration
        if self.recoded and self.binarised:
            raise ValueError("Data for model '%s' contains features with more than two states, but binarised=True was given.  Have you specified the correct data file or feature list?" % self.name)

    def set_ascertained(self):
        """
        Decide whether or not to do ascertainment correction for non-constant
        data, unless the user has provided an explicit setting.
        """
        if self.ascertained == None:
            # For binary models, it is possible to retain constant data
            # So we need to be more careful about automatically setting the value
            # of ascertained.
            if self.constant_feature:
                # There's a constant feature in the data, so we definitely shouldn't
                # do ascertainment correction for non-constant data
                self.ascertained = False
            elif self.constant_feature_removed:
                # BEASTling personally removed a constant feature, so we definitely
                # should do ascertainment correction if timing information is
                # important
                self.ascertained = not self.global_config.arbitrary_tree
            else:
                # We didn't see any constant features, but we also didn't remove
                # any.  So we don't quite know what to do...
                # Most data sources are *probably* non-constant, so do ascertainment
                # if the tree is calibrated, but inform the user.
                # This duplicates above, but this condition is a default guess
                # which we may change in future, whereas the above is a logical
                # necessity, so it makes sense to separate these cases
                self.ascertained = not self.global_config.arbitrary_tree
        elif self.ascertained and not self.remove_constant_features:
            raise ValueError("Incompatible settings for model '%s': ascertained=True and remove_constant_features=False together constitute a model misspecification.")
        # If the data has only two values, we need to decide what kind to treat
        # it as
        if not self.recoded:
            if type(self.binarised) == bool:
                self.recoded = self.binarised
            else:
                # Data is binary but we haven't been told if it's "real binary"
                # data or recoded multistate data.  Assume it's real but if
                # constant features have been retained then alert the user
                # because this could cause problems.
                self.recoded = False
                if not self.ascertained:
                    self.messages.append("""[INFO] Model "%s": Assuming that data source %s contains binary structural data (e.g. absence/presence).  If this is cognate set data which has been pre-binarised, please set "binarised=True" in your config to enable appropriate ascertainment correction for the recoding.  If you don't do this, estimates of branch lengths and clade ages may be biased.""" % (self.name, self.data_filename))

    def format_datapoint(self, feature, point):
        if not self.recoded:
            # This is "true binary" data, and doesn't need to be
            # treated any differently to usual.
            return BaseModel.format_datapoint(self, feature, point)
        else:
            # This is multistate data recoded into binary data.
            if self.ascertained:
                extra_columns = 2
            else:
                # If we are not ascertaining on non-constant data, we still
                # need to add one "all zeros" column to account for the recoding
                extra_columns = 1
            if point == "?":
                valuestring = "".join(["?" for i in range(0,self.valuecounts[feature]+extra_columns)])
            else:
                # Start with all zeros
                valuestring = ["0" for i in range(0,self.valuecounts[feature] +  extra_columns)]
                # If we're doing full ascertainment we need to set the 2nd extra column to 1
                if self.ascertained:
                    valuestring[1] = "1"
                # Set the appropriate data column to 1
                valuestring[extra_columns + self.unique_values[feature].index(point)] = "1"
                valuestring = "".join(valuestring)
            # Record the appropriate weight to use for computing mean mutation rate
            self.weights[feature] = self.valuecounts[feature]
            return valuestring

    def add_feature_data(self, distribution, index, feature, fname):
        data = BaseModel.add_feature_data(self, distribution, index, feature, fname)
        if self.recoded:
            data.set("ascertained", "true")
            data.set("excludefrom", "0")
            if self.ascertained:
                data.set("excludeto", "2")
            else:
                data.set("excludeto", "1")
