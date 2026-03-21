"use client";

import { arc, pie, type PieArcDatum } from "d3-shape";
import { useMemo } from "react";

interface GenomicMapProps {
  selectedOrgan: string;
  isLoading?: boolean;
  isError?: boolean;
}

const RING_WEIGHTS: readonly number[] = [34, 26, 22, 18];

function StitchMapSkeleton() {
  return (
    <div
      aria-label="Genomic map loading"
      className="w-[500px] h-[500px] rounded-full border border-outline-variant/20 bg-surface-container-lowest flex items-center justify-center"
      data-testid="stitch-skeleton-map"
    >
      <div className="w-64 h-64 rounded-full bg-surface-container-highest/70 animate-pulse border border-outline-variant/20 flex items-center justify-center">
        <div className="w-32 h-32 rounded-full bg-surface-container/80 animate-pulse" />
      </div>
    </div>
  );
}

export default function GenomicMap({ selectedOrgan, isLoading, isError }: GenomicMapProps) {
  const segments = useMemo(() => pie<number>().sort(null).value((value) => value)([...RING_WEIGHTS]), []);
  const outerArc = useMemo(
    () => arc<PieArcDatum<number>>().innerRadius(165).outerRadius(212).padAngle(0.03),
    []
  );
  const innerArc = useMemo(
    () => arc<PieArcDatum<number>>().innerRadius(130).outerRadius(155).padAngle(0.04),
    []
  );

  if (isLoading) {
    return <StitchMapSkeleton />;
  }

  return (
    <div
      className="relative w-[500px] h-[500px] flex items-center justify-center"
      data-testid="genomic-map"
    >
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 500 500">
        <g transform="translate(250 250)">
          <circle cx="0" cy="0" fill="none" r="220" stroke="var(--color-outline-variant)" strokeDasharray="4 12" strokeOpacity="0.3" strokeWidth="1.25" />
          {segments.map((segment, index) => {
            const d = outerArc(segment);
            if (!d) {
              return null;
            }

            return (
              <path
                key={`outer-${index}`}
                d={d}
                fill={index % 2 === 0 ? "var(--color-surface-container-low)" : "var(--color-surface-container-high)"}
                opacity={0.78}
              />
            );
          })}
          {segments.map((segment, index) => {
            const d = innerArc(segment);
            if (!d) {
              return null;
            }

            return (
              <path
                key={`inner-${index}`}
                d={d}
                fill={index % 2 === 0 ? "var(--color-primary)" : "var(--color-tertiary)"}
                opacity={0.18}
              />
            );
          })}
          <path d="M-185 -10 Q 0 -190 185 15" fill="none" stroke="var(--color-primary)" strokeDasharray="3 5" strokeLinecap="round" strokeWidth="2" />
          <path d="M-200 80 Q 5 165 198 40" fill="none" stroke="var(--color-tertiary)" strokeLinecap="round" strokeOpacity="0.75" strokeWidth="1.5" />
        </g>
      </svg>

      <div className="z-10 bg-surface-container-highest w-44 h-44 rounded-full flex flex-col items-center justify-center border border-outline-variant/30 shadow-2xl">
        <span className="text-primary font-headline font-extrabold text-3xl tracking-widest">CYP3A4</span>
        <span className="text-on-surface-variant text-[10px] uppercase tracking-[0.22em]">
          {selectedOrgan} target
        </span>
      </div>

      <div className="absolute top-10 left-12 glass-panel border border-outline-variant/20 px-3 py-1.5 rounded-full flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <span className="text-xs font-semibold text-primary">p-value: 1.2e-9</span>
      </div>
      <div className="absolute bottom-20 right-8 glass-panel border border-outline-variant/20 px-3 py-1.5 rounded-full flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-tertiary" />
        <span className="text-xs font-semibold text-tertiary">Expression: High</span>
      </div>

      {isError ? (
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 text-[11px] px-3 py-1.5 rounded-full border border-error/40 bg-error-container/30 text-error">
          Data feed degraded. Showing static locus view.
        </div>
      ) : null}
    </div>
  );
}
