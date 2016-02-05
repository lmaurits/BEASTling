import codecs
import os
import math
import xml.etree.ElementTree as ET

from .basemodel import BaseModel

class BSVSModel(BaseModel):

    package_notice = """[DEPENDENCY]: The BSVS substitution model is implemented in the BEAST package "BEAST_CLASSIC"."""
    def __init__(self, model_config, global_config):

        BaseModel.__init__(self, model_config, global_config)
        self.symmetric = model_config.get("symmetric", True)
        self.svsprior = model_config.get("svsprior", "poisson")

    def add_state(self, state):

        BaseModel.add_state(self, state)
        for trait in self.traits:
            traitname = "%s:%s" % (self.name, trait)

            attribs = {}
            attribs["dimension"] = str(self.dimensions[trait])
            attribs["id"] = "rateIndicator.s:%s" % traitname
            attribs["spec"] = "parameter.BooleanParameter"
            statenode = ET.SubElement(state, "stateNode", attribs)
            statenode.text="true"

            attribs = {}
            attribs["dimension"] = str(self.dimensions[trait])
            attribs["id"] = "relativeGeoRates.s:%s" % traitname
            attribs["name"] = "stateNode"
            parameter = ET.SubElement(state, "parameter", attribs)
            parameter.text="1.0"

    def add_prior(self, prior):

        BaseModel.add_prior(self, prior)
        for n, trait in enumerate(self.traits):
            traitname = "%s:%s" % (self.name, trait)

            # Boolean Rate on/off
            sub_prior = ET.SubElement(prior, "prior", {"id":"nonZeroRatePrior.s:%s" % traitname, "name":"distribution"})
            x = ET.SubElement(sub_prior, "x", {"arg":"@rateIndicator.s:%s" % traitname, "spec":"util.Sum"})
            N = self.valuecounts[trait]
            if self.symmetric:
                offset = N-1
                maxx = N*(N-1)/2
            else:
                offset = N
                maxx = N*(N-1)
            if maxx == offset:
                # In this situation (e.g. N=2, symmetric), we have no real
                # freedom in the number of non-zero rates.  So just set a
                # uniform prior
                distr  = ET.SubElement(sub_prior, "distr", {"id":"Poisson:%s.%d" % (traitname, n), "offset":str(offset),"spec":"beast.math.distributions.Uniform", "lower":"0.0","upper":"Infinity"})
            elif self.svsprior == "poisson":
                distr  = ET.SubElement(sub_prior, "distr", {"id":"Poisson:%s.%d" % (traitname, n), "offset":str(self.valuecounts[trait]-1),"spec":"beast.math.distributions.Poisson"})
                param = ET.SubElement(distr, "parameter", {"id":"RealParameter:%s.%d.0" % (traitname, n),"lower":"0.0","name":"lambda","upper":"0.0"})
                # Set Poisson mean equal to the midpoint of therange of
                # sensible values
                poisson_mean = (maxx - offset)/2.0
                param.text = str(poisson_mean)
            elif self.svsprior == "exponential":
                # Set Exponential mean so that 99% of probability density
                # lies inside the sensible range
                # Exponential quantile function is
                # F(p,lambda) = -ln(1-p) / lambda
                exponential_mean = math.log(100.0) / (maxx - offset)
                distr  = ET.SubElement(sub_prior, "distr", {"id":"Exponential:%s.%d" % (traitname, n), "offset":str(offset),"spec":"beast.math.distributions.Exponential"})
                param = ET.SubElement(distr, "parameter", {"id":"RealParameter:%s.%d.0" % (traitname, n),"lower":"0.0","name":"mean","upper":"0.0"})
                param.text = str(exponential_mean)

            # Relative rate
            sub_prior = ET.SubElement(prior, "prior", {"id":"relativeGeoRatesPrior.s:%s" % traitname, "name":"distribution","x":"@relativeGeoRates.s:%s"% traitname})
            gamma  = ET.SubElement(sub_prior, "Gamma", {"id":"Gamma:%s.%d.0" % (traitname, n), "name":"distr"})
            param = ET.SubElement(gamma, "parameter", {"id":"RealParameter:%s.%d.1" % (traitname, n),"lower":"0.0","name":"alpha","upper":"0.0"})
            param.text = "1.0"
            param = ET.SubElement(gamma, "parameter", {"id":"RealParameter:%s.%d.2" % (traitname, n),"lower":"0.0","name":"beta","upper":"0.0"})
            param.text = "1.0"

    def add_sitemodel(self, distribution, trait, traitname):

            # Sitemodel
            if self.rate_variation:
                mr = "@mutationRate:%s" % traitname
            else:
                mr = "1.0"
            sitemodel = ET.SubElement(distribution, "siteModel", {"id":"SiteModel.%s"%traitname,"spec":"SiteModel", "mutationRate":mr,"shape":"1","proportionInvariant":"0"})

            if self.symmetric:
                substmodel = ET.SubElement(sitemodel, "substModel",{"id":"svs.s:%s"%traitname,"rateIndicator":"@rateIndicator.s:%s"%traitname,"rates":"@relativeGeoRates.s:%s"%traitname,"spec":"SVSGeneralSubstitutionModel"})
            else:
                substmodel = ET.SubElement(sitemodel, "substModel",{"id":"svs.s:%s"%traitname,"rateIndicator":"@rateIndicator.s:%s"%traitname,"rates":"@relativeGeoRates.s:%s"%traitname,"spec":"SVSGeneralSubstitutionModel", "symmetric":"false"})
            freq = ET.SubElement(substmodel,"frequencies",{"id":"traitfreqs.s:%s"%traitname,"spec":"Frequencies"})
            if self.frequencies == "uniform":
                freq_string = str(1.0/self.valuecounts[trait])
            elif self.frequencies == "empirical":
                freqs = [self.counts[trait].get(str(v),0) for v in range(1,self.valuecounts[trait]+1)]
                norm = float(sum(freqs))
                freqs = [f/norm for f in freqs]
                # Sometimes, due to WALS oddities, there's a zero frequency, and that makes BEAST sad.  So do some smoothing in these cases:
                if 0 in freqs:
                    freqs = [0.1/self.valuecounts[trait] + 0.9*f for f in freqs]
                norm = float(sum(freqs))
                freq_string = " ".join([str(c/norm) for c in freqs])
            ET.SubElement(freq,"parameter",{
                "dimension":str(self.valuecounts[trait]),
                "id":"traitfrequencies.s:%s"%traitname,
                "name":"frequencies"}).text=freq_string

    def add_operators(self, run):

        BaseModel.add_operators(self, run)
        for n, trait in enumerate(self.traits):
            traitname = "%s:%s" % (self.name, trait)
            ET.SubElement(run, "operator", {"id":"onGeorateScaler.s:%s"% traitname,"spec":"ScaleOperator","parameter":"@relativeGeoRates.s:%s"%traitname, "indicator":"@rateIndicator.s:%s" % traitname, "scaleAllIndependently":"true","scaleFactor":"1.0","weight":"10.0"})

            ET.SubElement(run, "operator", {"id":"indicatorFlip.s:%s"%traitname,"spec":"BitFlipOperator","parameter":"@rateIndicator.s:%s"%traitname, "weight":"30.0"})
            if self.rate_variation:
                ET.SubElement(run, "operator", {"id":"BSSVSoperator.c:%s"%traitname,"spec":"BitFlipBSSVSOperator","indicator":"@rateIndicator.s:%s"%traitname, "mu":"@mutationRate:%s" % traitname,"weight":"30.0"})
            else:
                ET.SubElement(run, "operator", {"id":"BSSVSoperator.c:%s"%traitname,"spec":"BitFlipBSSVSOperator","indicator":"@rateIndicator.s:%s"%traitname, "mu":"@clockRate.c:%s" % self.name,"weight":"30.0"})
            sampoffop = ET.SubElement(run, "operator", {"id":"offGeorateSampler:%s" % traitname,"spec":"SampleOffValues","all":"false","values":"@relativeGeoRates.s:%s"%traitname, "indicators":"@rateIndicator.s:%s" % traitname, "weight":"30.0"})
            ET.SubElement(sampoffop, "dist", {"idref":"Gamma:%s.%d.0" % (traitname, n)})

    def add_param_logs(self, logger):
        BaseModel.add_param_logs(self, logger)
        for trait in self.traits:
            traitname = "%s:%s" % (self.name, trait)
            ET.SubElement(logger,"log",{"idref":"rateIndicator.s:%s" % traitname})
            ET.SubElement(logger,"log",{"idref":"relativeGeoRates.s:%s" % traitname})
