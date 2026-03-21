export interface OrganOption {
  id: string;
  label: string;
  icon: string;
  focus: string;
  expression: string;
  pValue: string;
  primaryTarget: string;
  keyRisk: string;
  accentColor: string;
  tertiaryColor: string;
}

export const ORGAN_OPTIONS: readonly OrganOption[] = [
  {
    id: "liver",
    label: "Liver",
    icon: "vital_signs",
    focus: "metabolic response",
    expression: "High",
    pValue: "1.2e-9",
    primaryTarget: "CYP3A4",
    keyRisk: "drug metabolism drift",
    accentColor: "#81cfff",
    tertiaryColor: "#ffba2c",
  },
  {
    id: "heart",
    label: "Heart",
    icon: "favorite",
    focus: "cardiac safety",
    expression: "Moderate",
    pValue: "4.8e-7",
    primaryTarget: "KCNH2",
    keyRisk: "QT liability",
    accentColor: "#ffa6ad",
    tertiaryColor: "#f6c453",
  },
  {
    id: "lung",
    label: "Lung",
    icon: "air",
    focus: "respiratory burden",
    expression: "Elevated",
    pValue: "2.1e-8",
    primaryTarget: "MUC1",
    keyRisk: "fibrotic inflammation",
    accentColor: "#9be7c4",
    tertiaryColor: "#8dd9ff",
  },
  {
    id: "kidney",
    label: "Kidney",
    icon: "opacity",
    focus: "clearance profile",
    expression: "Adaptive",
    pValue: "9.6e-8",
    primaryTarget: "SLC22A2",
    keyRisk: "clearance bottleneck",
    accentColor: "#b6c6ff",
    tertiaryColor: "#66d1ff",
  },
  {
    id: "brain",
    label: "Brain",
    icon: "psychology",
    focus: "neuro-oncology",
    expression: "Selective",
    pValue: "7.4e-10",
    primaryTarget: "GRIN2B",
    keyRisk: "blood-brain barrier",
    accentColor: "#8ab4ff",
    tertiaryColor: "#ff88c2",
  },
];

export type ExplorerView = "genomic-map" | "discovery-graph";

export interface ExplorerViewOption {
  id: ExplorerView;
  label: string;
  description: string;
  icon: string;
}

export const EXPLORER_VIEW_OPTIONS: readonly ExplorerViewOption[] = [
  {
    id: "genomic-map",
    label: "Genomic Map",
    description: "target locus",
    icon: "genetics",
  },
  {
    id: "discovery-graph",
    label: "Discovery Graph",
    description: "neo4j network",
    icon: "hub",
  },
];

export function getOrganOption(organId: string): OrganOption {
  return ORGAN_OPTIONS.find((option) => option.id === organId) ?? ORGAN_OPTIONS[0];
}
