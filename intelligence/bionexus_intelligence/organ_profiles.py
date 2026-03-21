from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeaturedOrganProfile:
    organ_id: str
    label: str
    focus: str
    expression: str
    p_value: str
    primary_target: str
    key_risk: str


_FEATURED_ORGAN_PROFILES: dict[str, FeaturedOrganProfile] = {
    "liver": FeaturedOrganProfile(
        organ_id="liver",
        label="Liver",
        focus="metabolic response",
        expression="High",
        p_value="1.2e-9",
        primary_target="CYP3A4",
        key_risk="drug metabolism drift",
    ),
    "heart": FeaturedOrganProfile(
        organ_id="heart",
        label="Heart",
        focus="cardiac safety",
        expression="Moderate",
        p_value="4.8e-7",
        primary_target="KCNH2",
        key_risk="QT liability",
    ),
    "lung": FeaturedOrganProfile(
        organ_id="lung",
        label="Lung",
        focus="respiratory burden",
        expression="Elevated",
        p_value="2.1e-8",
        primary_target="MUC1",
        key_risk="fibrotic inflammation",
    ),
    "kidney": FeaturedOrganProfile(
        organ_id="kidney",
        label="Kidney",
        focus="clearance profile",
        expression="Adaptive",
        p_value="9.6e-8",
        primary_target="SLC22A2",
        key_risk="clearance bottleneck",
    ),
    "brain": FeaturedOrganProfile(
        organ_id="brain",
        label="Brain",
        focus="neuro-oncology",
        expression="Selective",
        p_value="7.4e-10",
        primary_target="GRIN2B",
        key_risk="blood-brain barrier",
    ),
}


def get_featured_organ_profile(organ_id: str) -> FeaturedOrganProfile | None:
    normalized = organ_id.strip().lower()
    if not normalized:
        return None
    return _FEATURED_ORGAN_PROFILES.get(normalized)
