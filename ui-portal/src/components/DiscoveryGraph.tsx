"use client";

import { useMemo } from "react";
import type { BioNode, TripletData } from "@/services/bioService";

interface Props {
  data?: TripletData;
  isLoading?: boolean;
  isRefreshing?: boolean;
  isError?: boolean;
  errorMessage?: string;
  onRetry?: () => void;
  selectedOrgan?: string;
}

interface PositionedNode extends BioNode {
  x: number;
  y: number;
  fill: string;
}

const NODE_COLORS: Record<string, string> = {
  Disease: "#ffb4ab",
  Gene: "#81cfff",
  Medicine: "#ffba2c",
};

function StitchGraphSkeleton(): React.JSX.Element {
  return (
    <div className="w-full h-full m-4 rounded-xl border border-outline-variant/20 bg-surface p-6 animate-pulse flex flex-col gap-4">
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

function buildNodeLayout(nodes: readonly BioNode[]): PositionedNode[] {
  const anchors: Record<string, { x: number; y: number }> = {
    Gene: { x: 360, y: 120 },
    Disease: { x: 180, y: 320 },
    Medicine: { x: 540, y: 320 },
  };

  return nodes.map((node, index) => {
    const anchor = anchors[node.type] ?? {
      x: 180 + ((index % 3) * 180),
      y: 120 + (Math.floor(index / 3) * 120),
    };
    return {
      ...node,
      x: anchor.x,
      y: anchor.y,
      fill: NODE_COLORS[node.type] ?? "#c2c6d4",
    };
  });
}

export default function DiscoveryGraph({
  data,
  isLoading,
  isRefreshing,
  isError,
  errorMessage,
  onRetry,
  selectedOrgan,
}: Props): React.JSX.Element {
  const organLabel = selectedOrgan ? `${selectedOrgan} network` : "Neo4j Network";
  const positionedNodes = useMemo(() => buildNodeLayout(data?.nodes ?? []), [data]);
  const nodeMap = useMemo(
    () => new Map(positionedNodes.map((node) => [node.id, node])),
    [positionedNodes]
  );

  if (isLoading) {
    return <StitchGraphSkeleton />;
  }

  if (isError) {
    return (
      <div className="w-full h-full m-4 rounded-xl border border-error/40 bg-error-container/20 p-5 flex flex-col gap-3">
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

  if (!positionedNodes.length) {
    return (
      <div className="w-full h-full m-4 rounded-xl border border-outline-variant/20 bg-surface-container-lowest p-6 flex items-center justify-center">
        <p className="text-on-surface-variant text-xs uppercase tracking-wider">
          No graph records available for {selectedOrgan ?? "this"} organ selection yet.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative bg-surface border-outline-variant/10 border m-4 rounded-xl overflow-hidden shadow-2xl">
      <div className="absolute top-4 left-4 z-10 glass-panel px-4 py-2 rounded-md">
        <h3 className="text-primary font-headline font-bold text-sm">Discovery Graph</h3>
        <p className="text-on-surface-variant text-[10px] uppercase tracking-wider">{organLabel}</p>
      </div>
      {isRefreshing ? (
        <div className="absolute top-4 right-4 z-10 px-2 py-1 rounded border border-outline-variant/30 bg-surface-container-low text-[10px] uppercase tracking-wider text-on-surface-variant">
          Refreshing
        </div>
      ) : null}

      <svg className="h-full w-full" viewBox="0 0 720 420">
        {data?.edges.map((edge) => {
          const source = nodeMap.get(edge.source);
          const target = nodeMap.get(edge.target);
          if (!source || !target) {
            return null;
          }

          const labelX = (source.x + target.x) / 2;
          const labelY = (source.y + target.y) / 2;

          return (
            <g key={`${edge.source}-${edge.target}-${edge.relationship}`}>
              <line
                stroke="#424752"
                strokeWidth="3"
                x1={source.x}
                x2={target.x}
                y1={source.y}
                y2={target.y}
              />
              <text
                fill="#8c919d"
                fontSize="10"
                textAnchor="middle"
                x={labelX}
                y={labelY - 8}
              >
                {edge.relationship}
              </text>
            </g>
          );
        })}

        {positionedNodes.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} fill={node.fill} r="36" />
            <text
              fill="#e1e2eb"
              fontSize="13"
              fontWeight="700"
              textAnchor="middle"
              x={node.x}
              y={node.y + 58}
            >
              {node.label}
            </text>
            <text
              fill="#8c919d"
              fontSize="10"
              textAnchor="middle"
              x={node.x}
              y={node.y + 74}
            >
              {node.type}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
