import itertools
import json
import sys

from beastling import __version__

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
        self.n_languages = len(self.config.languages)
        self.family_tally = {}
        self.macroarea_tally = {}
        for l in self.config.languages:
            if l in self.config.classifications:
                fam = self.config.classifications[l][0][0] or "Unclassified"
                self.family_tally[fam] = self.family_tally.get(fam, 0) + 1
            if l in self.config.glotto_macroareas:
                area = self.config.glotto_macroareas.get(l, "Unknown")
                self.macroarea_tally[area] = self.macroarea_tally.get(area, 0) + 1
        self.n_families = len(self.family_tally)
        self.n_macroareas = len(self.macroarea_tally)

    def tostring(self):
        lines = []
        lines.append("# BEASTling analysis report\n")
        lines.append("Analysis: %s" % self.config.basename)

        lines.append("## Languages\n")
        lines.append("%d languages total, from %d Glottolog families and %d macroareas." % (self.n_languages, self.n_families, self.n_macroareas))
        lines.append("")

        for title, tally in zip(("Family", "Macroarea"), (self.family_tally, self.macroarea_tally)):
            lines.append("### %s breakdown\n" % title)
            ranked = [(tally[f],f) for f in tally]
            ranked.sort()
            ranked.reverse()
            for n, x in ranked:
                lines.append("* %s: %d" % (x, n))
            lines.append("")
       
        if self.config.calibrations:
            lines.append("### Calibration points\n")
            for clade in sorted(self.config.calibrations.keys()):
                cal = self.config.calibrations[clade]
                lines.append("* %s: %s(%s, %s)" % (clade, cal.dist.title(), str(cal.param1), str(cal.param2)))
            lines.append("")
                
        lines.append("## Data\n")
        for model in self.config.models:
            lines.append("### Model: %s\n" % model.name)
            lines.append("* Number of features: %d" % len(model.features))
            lines.append("* Number of languages: %d" % len(model.data.keys()))
            lines.append("* Missing data: %.2f" % (sum(model.missing_ratios.values())/len(model.missing_ratios)))
            lines.append("* Substitution model: %s" % model.substitution_name)
            lines.append("")

        return "\n".join(lines)

    def write_file(self, filename=None):
        """
        Write the report to a file.
        """
        with open(filename or self.config.basename + ".md", "w") as fp:
            fp.write(self.tostring())

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
        all_families = set([self.config.classifications.get(l,[["Unclassified"]])[0][0] for l in self.config.languages])
        style_map = dict(zip(all_families, itertools.cycle(itertools.product(_SHAPES,_COLOURS))))
        for l in self.config.languages:
            if l not in self.config.locations:
                continue
            fam = self.config.classifications[l][0][0] or "Unclassified"
            area = self.config.glotto_macroareas.get(l, "Unknown")
            lbit = {}
            lbit["type"] = "Feature"
            (lat, lon) = self.config.locations[l]
            # TODO: This could be prettier (e.g. include N/S, E/W
            pretty_location = "Lat: %.2f, Long: %.2f" % (lat, lon)
            lbit["geometry"] = {"type":"Point", "coordinates": (lon, lat)}
            props = {"name":l, "family": fam, "macroarea": area, "location": pretty_location}
            shape, colour = style_map[fam]
            props["marker-symbol"]  = shape
            props["marker-color"]  = colour
            lbit["properties"] = props
            features.append(lbit)
        self.geojson["features"] = features

    def write_file(self, filename=None):
        """
        Write the report to a file.
        """
        with open(filename or self.config.basename + ".md", "w") as fp:
            fp.write(json.dumps(self.geojson, sort_keys=True))

