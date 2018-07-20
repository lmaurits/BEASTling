import collections

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

    def compute_weights(self):
        if not self.recoded:
            BaseModel.compute_weights(self)
        else:
            self.weights = []
            if self.rate_partition:
                for part in sorted(list(set(self.rate_partition.values()))):
                    weight = 0
                    for f in self.features:
                        if self.rate_partition[f] == part:
                            weight += self.valuecounts[f]
                    self.weights.append(weight)
            else:
                for f in self.features:
                    self.weights.append(self.valuecounts[f])

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

    def compute_feature_properties(self):
        """Compute various items of metadata for all remaining features.

        This is very similar to the `compute_feature_probability` method of
        BaseModel, but accounts for the possibility of having multiple values
        present.

        """

        self.valuecounts = {}
        self.extracolumns = collections.defaultdict(int)
        self.unique_values = {}
        self.missing_ratios = {}
        self.counts = {}
        self.codemaps = {}
        for f in self.features:
            # Compute various things
            all_values = []
            missing_data_ratio = 0
            for l, values in self.data.items():
                raw = values.get(f, None)
                if raw is None:
                    missing_data_ratio += 1
                elif raw:
                    try:
                        raw.remove("-")
                    except ValueError:
                        pass
                    all_values.append(raw)
            missing_data_ratio /= (1.0 * missing_data_ratio + len(all_values))
            non_q_values = [v for vs in all_values for v in vs]
            counts = {}
            for v in non_q_values:
                counts[v] = non_q_values.count(v)
            unique_values = list(set(non_q_values))
            # Sort unique_values carefully.
            # Possibly all feature values are numeric strings, e.g. "1", "2", "3".
            # If we sort these as strings then we get weird things like "10" < "2".
            # This can actually matter for things like ordinal models.
            # So convert these to ints first...
            if all([v.isdigit() for v in unique_values]):
                unique_values = list(map(int, unique_values))
                unique_values.sort()
                unique_values = list(map(str, unique_values))
            # ...otherwise, just sort normally
            else:
                unique_values.sort()
            self.unique_values[f] = unique_values

            N = len(unique_values)
            self.valuecounts[f] = N
            self.missing_ratios[f] = missing_data_ratio
            self.counts[f] = counts
            self.codemaps[f] = self.build_codemap(unique_values)


    def pattern_names(self, feature):
        """Content of the columns corresponding to this feature in the alignment.

        This method is used for displaying helpful column names in ancestral
        state reconstruction output. It gives column headers for actual value
        columns as well as for dummy columns used in ascertainment correction,
        if such columns exist.

        """
        return (["{:}_dummy{:d}".format(feature, i) for i in range(self.extracolumns[feature])] +
                ["{:}_{:}".format(feature, i) for i in self.unique_values[feature]])

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
            self.extracolumns[feature] = extra_columns
            if point == "?":
                valuestring = "".join(["?" for i in range(0,self.valuecounts[feature]+extra_columns)])
            else:
                # Start with all zeros
                valuestring = ["0" for i in range(0,self.valuecounts[feature] +  extra_columns)]
                # If we're doing full ascertainment we need to set the 2nd extra column to 1
                if self.ascertained:
                    valuestring[1] = "1"
                # Set the appropriate data column to 1
                for subpoint in point:
                    valuestring[extra_columns + self.unique_values[feature].index(subpoint)] = "1"
                valuestring = "".join(valuestring)
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
