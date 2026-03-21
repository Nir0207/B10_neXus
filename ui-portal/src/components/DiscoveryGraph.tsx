"use client";

import type { Core, ElementDefinition } from "cytoscape";
import { useRef } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import { TripletData } from "@/services/bioService";

interface Props {
  data?: TripletData;
  isLoading?: boolean;
  isRefreshing?: boolean;
  isError?: boolean;
  errorMessage?: string;
  onRetry?: () => void;
}

const STITCH_COLORS = {
  nodeDefault: "#c2c6d4",
  primary: "#81cfff",
  error: "#ffb4ab",
  tertiary: "#ffba2c",
  onSurface: "#e1e2eb",
  outline: "#8c919d",
  outlineVariant: "#424752",
} as const;

function StitchGraphSkeleton() {
  return (
    <div className="w-full flex-1 m-4 rounded-xl border border-outline-variant/20 bg-surface p-6 animate-pulse flex flex-col gap-4">
      <div className="h-6 w-40 bg-surface-container-high rounded" />
      <div className="flex gap-3">
        <div className="h-3 w-28 bg-surface-container-high rounded" />
        <div className="h-3 w-20 bg-surface-container-high rounded" />
        <div className="h-3 w-24 bg-surface-container-high rounded" />
      </div>
      <div className="flex-1 rounded-lg bg-surface-container-lowest border border-outline-variant/15" />
    </div>
  );
}

export default function DiscoveryGraph({
  data,
  isLoading,
  isRefreshing,
  isError,
  errorMessage,
  onRetry,
}: Props) {
  const cyRef = useRef<Core | null>(null);

  if (isLoading) {
    return <StitchGraphSkeleton />;
  }

  if (isError) {
    return (
      <div className="w-full flex-1 m-4 rounded-xl border border-error/40 bg-error-container/20 p-5 flex flex-col gap-3">
        <h3 className="text-error font-semibold text-sm">Network unavailable</h3>
        <p className="text-error/90 text-xs leading-relaxed">
          {errorMessage ?? "The knowledge graph request failed."}
        </p>
        <button
          className="self-start px-3 py-1.5 rounded-md bg-primary text-on-primary text-xs font-semibold hover:opacity-90 transition-opacity"
          onClick={onRetry}
          type="button"
        >
          Retry fetch
        </button>
      </div>
    );
  }

  const elements: ElementDefinition[] = [
    ...(data?.nodes || []).map((node) => ({
      data: { id: node.id, label: node.label, type: node.type },
      classes: node.type.toLowerCase(),
    })),
    ...(data?.edges || []).map((edge, idx) => ({
      data: {
        id: `e${idx}`,
        source: edge.source,
        target: edge.target,
        label: edge.relationship,
      },
    })),
  ];

  if (!elements.length) {
    return (
      <div className="w-full flex-1 m-4 rounded-xl border border-outline-variant/20 bg-surface-container-lowest p-6 flex items-center justify-center">
        <p className="text-on-surface-variant text-xs uppercase tracking-wider">
          No graph records available for this organ selection yet.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full flex-1 relative bg-surface border-outline-variant/10 border m-4 rounded-xl overflow-hidden shadow-2xl">
      <div className="absolute top-4 left-4 z-10 glass-panel px-4 py-2 rounded-md">
        <h3 className="text-primary font-headline font-bold text-sm">Discovery Graph</h3>
        <p className="text-on-surface-variant text-[10px] uppercase tracking-wider">Neo4j Network</p>
      </div>
      {isRefreshing ? (
        <div className="absolute top-4 right-4 z-10 px-2 py-1 rounded border border-outline-variant/30 bg-surface-container-low text-[10px] uppercase tracking-wider text-on-surface-variant">
          Refreshing
        </div>
      ) : null}
      <CytoscapeComponent
        elements={elements}
        style={{ width: "100%", height: "100%" }}
        cy={(cy) => {
          cyRef.current = cy;
        }}
        layout={{ name: "cose", padding: 50 }}
        stylesheet={[
          {
            selector: "node",
            style: {
              label: "data(label)",
              "background-color": STITCH_COLORS.nodeDefault,
              color: STITCH_COLORS.onSurface,
              "text-valign": "bottom",
              "text-margin-y": 8,
              "font-size": "12px",
              "font-family": "var(--font-body)",
            },
          },
          {
            selector: "node.gene",
            style: {
              "background-color": STITCH_COLORS.primary,
            },
          },
          {
            selector: "node.disease",
            style: {
              "background-color": STITCH_COLORS.error,
            },
          },
          {
            selector: "node.medicine",
            style: {
              "background-color": STITCH_COLORS.tertiary,
            },
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": STITCH_COLORS.outlineVariant,
              "target-arrow-color": STITCH_COLORS.outlineVariant,
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              label: "data(label)",
              "text-rotation": "autorotate",
              "font-size": "8px",
              color: STITCH_COLORS.outline,
              "text-margin-y": -10,
            },
          },
        ]}
      />
    </div>
  );
}
