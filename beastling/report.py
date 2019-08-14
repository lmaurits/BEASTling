import itertools
import collections
import json
import pathlib

_COLOURS = ["#CADA45", "#D4A2E1", "#55E0C6", "#F0B13C", "#75E160"]
_SHAPES = ["circle", "square", "triangle", "star"]


class BeastlingReport(object):

    def __init__(self, config):
        self.config = config
        if not self.config.processed:
            self.config.process()
        self.build_report()

    def build_report(self):
        """
        Creates a report on a BEASTling analysis.
        """
        self.n_languages = len(self.config.languages.languages)
        self.family_tally = collections.Counter()
        self.macroarea_tally = collections.Counter()
        for l in self.config.languages.languages:
            if l in self.config.classifications:
                self.family_tally.update([
                   self.config.classifications[l][0][0]
                   if self.config.classifications[l] else "Unclassified"
                ])
            if l in self.config.glotto_macroareas:
                self.macroarea_tally.update([self.config.glotto_macroareas.get(l, "Unknown")])
        self.n_families = len(self.family_tally)
        self.n_macroareas = len(self.macroarea_tally)

    def tostring(self):
        lines = [
            "# BEASTling analysis report\n",
            "Analysis: %s" % self.config.admin.basename,
            "## Languages\n",
            "%d languages total, from %d Glottolog families and %d macroareas.\n" % (
                self.n_languages, self.n_families, self.n_macroareas),
        ]

        for title, tally in zip(("Family", "Macroarea"), (self.family_tally, self.macroarea_tally)):
            lines.append("### %s breakdown\n" % title)
            for n, items in itertools.groupby(tally.most_common(), lambda i: i[1]):
                # Sort alphabetically within size groups:
                for x, _ in sorted(items):
                    lines.append("* %s: %d" % (x, n))
            lines.append("")
       
        if self.config.calibrations:
            lines.append("### Calibration points\n")
            for clade in sorted(self.config.calibrations.keys()):
                cal = self.config.calibrations[clade]
                lines.append("* %s: %s%s" % (clade, cal.dist.title(), cal.param))
            lines.append("")
                
        lines.append("## Data\n")
        for model in self.config.models:
            lines.extend([
                "### Model: %s\n" % model.name,
                "* Number of features: %d" % len(model.features),
                "* Number of languages: %d" % len(model.data.keys()),
                "* Missing data: %.2f" % (
                    sum(model.missing_ratios.values())/len(model.missing_ratios)),
                "* Substitution model: %s" % model.substitution_name,
                ""])

        return "\n".join(lines)

    def write_file(self, filename=None):
        """
        Write the report to a file.
        """
        filename = pathlib.Path(filename) if filename else self.config.admin.path('.md')
        filename.write_text(self.tostring(), encoding='utf8')


class BeastlingGeoJSON(object):

    def __init__(self, config):
        self.config = config
        if not self.config.processed:
            self.config.process()
        self.build_geojson()

    def build_geojson(self):
        self.geojson = {}
        self.geojson["type"] = "FeatureCollection"
        features = []
        classifier_level = 0
        while True:
            all_classifiers = set([self.config.classifications[l][classifier_level][0] for l in
            self.config.languages.languages if self.config.classifications[l]])
            if len(all_classifiers) > 1:
                break
            classifier_level += 1
        style_map = dict(zip(all_classifiers, itertools.cycle(itertools.product(_SHAPES,_COLOURS))))
        style_map["Unclassified"] = ("circle", "#D3D3D3")
        for l in self.config.languages.languages:
            if l not in self.config.locations:
                continue
            fam = self.config.classifications[l][0][0] if self.config.classifications[l] else "Unclassified"
            classifier = self.config.classifications[l][classifier_level][0] if self.config.classifications[l] else "Unclassified"
            area = self.config.glotto_macroareas.get(l, "Unknown")
            lbit = {"type": "Feature"}
            (lat, lon) = self.config.locations[l]
            # TODO: This could be prettier (e.g. include N/S, E/W
            pretty_location = "Lat: %.2f, Long: %.2f" % (lat, lon)
            lbit["geometry"] = {"type":"Point", "coordinates": (lon, lat)}
            props = {"name":l, "family": fam, "macroarea": area, "location": pretty_location}
            if classifier_level > 0:
                props["subfamily"] = classifier
            shape, colour = style_map[classifier]
            props["marker-symbol"]  = shape
            props["marker-color"]  = colour
            lbit["properties"] = props
            features.append(lbit)
        self.geojson["features"] = features

    def write_file(self, filename=None):
        """
        Write the report to a file.
        """
        filename = pathlib.Path(filename) if filename else self.config.admin.path('.geojson')
        filename.write_text(json.dumps(self.geojson, sort_keys=True), encoding='utf8')
