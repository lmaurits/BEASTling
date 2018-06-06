from .distributions import registered_distributions

maps = registered_distributions + (
    ("prior", "beast.math.distributions.Prior"),
    ("taxon", "beast.evolution.alignment.Taxon"),
    ("taxonset", "beast.evolution.alignment.TaxonSet"),
)
