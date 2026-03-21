from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeaturedGeneProfile:
    gene_symbol: str
    canonical_name: str
    summary: str
    translational_relevance: str
    uniprot_id: str | None = None


_FEATURED_GENE_PROFILES: dict[str, FeaturedGeneProfile] = {
    "CYP3A4": FeaturedGeneProfile(
        gene_symbol="CYP3A4",
        canonical_name="Cytochrome P450 Family 3 Subfamily A Member 4",
        uniprot_id="P08684",
        summary=(
            "CYP3A4 encodes a major hepatic drug-metabolizing enzyme that clears many small-molecule therapies "
            "and can strongly influence exposure, half-life, and drug-drug interactions."
        ),
        translational_relevance=(
            "It is central to liver ADME risk assessment, dose optimization, and metabolism-driven safety review."
        ),
    ),
    "EGFR": FeaturedGeneProfile(
        gene_symbol="EGFR",
        canonical_name="Epidermal Growth Factor Receptor",
        uniprot_id="P00533",
        summary=(
            "EGFR encodes a receptor tyrosine kinase that regulates growth, survival, and differentiation signaling."
        ),
        translational_relevance=(
            "It is a validated oncology target with direct relevance to targeted therapy selection and resistance analysis."
        ),
    ),
    "GRIN2B": FeaturedGeneProfile(
        gene_symbol="GRIN2B",
        canonical_name="Glutamate Ionotropic Receptor NMDA Type Subunit 2B",
        uniprot_id="Q13224",
        summary=(
            "GRIN2B encodes the GluN2B subunit of the NMDA receptor, a glutamate-gated ion channel that shapes "
            "synaptic signaling, neuronal plasticity, and excitatory neurotransmission."
        ),
        translational_relevance=(
            "It is relevant to neurodevelopmental biology, excitotoxicity, and CNS-targeted therapeutic strategy design."
        ),
    ),
    "KCNH2": FeaturedGeneProfile(
        gene_symbol="KCNH2",
        canonical_name="Potassium Voltage-Gated Channel Subfamily H Member 2",
        uniprot_id="Q12809",
        summary=(
            "KCNH2 encodes the hERG potassium channel, a core determinant of cardiac repolarization."
        ),
        translational_relevance=(
            "It is a critical cardiac safety marker because inhibition can prolong QT interval and trigger arrhythmia risk."
        ),
    ),
    "MUC1": FeaturedGeneProfile(
        gene_symbol="MUC1",
        canonical_name="Mucin 1, Cell Surface Associated",
        uniprot_id="P15941",
        summary=(
            "MUC1 encodes a heavily glycosylated epithelial surface protein involved in barrier biology and signaling."
        ),
        translational_relevance=(
            "It is relevant to inflammatory remodeling, epithelial stress, and multiple solid-tumor programs."
        ),
    ),
    "SLC22A2": FeaturedGeneProfile(
        gene_symbol="SLC22A2",
        canonical_name="Solute Carrier Family 22 Member 2",
        uniprot_id="O15244",
        summary=(
            "SLC22A2 encodes OCT2, a renal transporter that influences uptake and clearance of endogenous metabolites "
            "and cationic drugs."
        ),
        translational_relevance=(
            "It is important for kidney disposition modeling, transporter-mediated DDI review, and nephrotoxicity assessment."
        ),
    ),
}


def get_featured_gene_profile(gene_or_uniprot: str) -> FeaturedGeneProfile | None:
    normalized = gene_or_uniprot.strip().upper()
    if not normalized:
        return None

    profile = _FEATURED_GENE_PROFILES.get(normalized)
    if profile is not None:
        return profile

    for candidate in _FEATURED_GENE_PROFILES.values():
        if candidate.uniprot_id and candidate.uniprot_id.upper() == normalized:
            return candidate

    return None
