"use client";

import Link from "next/link";
import { EXPLORER_VIEW_OPTIONS, type ExplorerView, ORGAN_OPTIONS } from "@/lib/organs";

interface Props {
  isExportDisabled?: boolean;
  onExport?: () => void;
  onSelectExplorerView?: (view: ExplorerView) => void;
  selectedOrgan: string;
  selectedExplorerView?: ExplorerView;
  onSelectOrgan: (organ: string) => void;
}

export default function OrganNavigator({
  isExportDisabled,
  onExport,
  onSelectExplorerView,
  selectedOrgan,
  selectedExplorerView,
  onSelectOrgan,
}: Props): React.JSX.Element {
  return (
    <aside className="flex flex-col h-full py-4 border-r border-outline-variant/15 bg-surface-container-lowest w-64 shrink-0">
      <div className="px-6 mb-8">
        <div className="flex items-center gap-3 mb-1">
          <span className="material-symbols-outlined text-primary text-2xl">
            biotech
          </span>
          <h2 className="text-lg font-bold text-primary font-headline">
            Organ Atlas
          </h2>
        </div>
        <p className="text-[0.6875rem] font-medium text-on-surface-variant opacity-70">
          Precision Visualization
        </p>
      </div>

      <nav className="flex-1 space-y-1">
        {ORGAN_OPTIONS.map((organ) => {
          const isActive = selectedOrgan === organ.id;
          return (
            <button
              aria-pressed={isActive}
              data-organ={organ.id}
              key={organ.id}
              onClick={() => onSelectOrgan(organ.id)}
              className={`w-full flex items-center gap-4 px-6 py-3 transition-all duration-200 ${
                isActive
                  ? "bg-surface-container-low text-primary border-l-4 border-primary"
                  : "text-on-surface-variant opacity-70 hover:bg-surface-container-high hover:opacity-100 border-l-4 border-transparent"
              }`}
              type="button"
            >
              <span className="material-symbols-outlined">{organ.icon}</span>
              <div className="flex flex-col items-start">
                <span className="text-xs font-medium font-body">{organ.label}</span>
                <span className="text-[10px] uppercase tracking-[0.18em] opacity-70">
                  {organ.focus}
                </span>
              </div>
            </button>
          );
        })}
      </nav>

      {selectedExplorerView && onSelectExplorerView ? (
        <div className="px-4 mt-3">
          <p className="px-2 text-[10px] uppercase tracking-[0.24em] text-on-surface-variant mb-2">
            Explorer Views
          </p>
          <div className="space-y-1">
            {EXPLORER_VIEW_OPTIONS.map((view) => {
              const isActive = selectedExplorerView === view.id;
              return (
                <button
                  className={`w-full flex items-center gap-3 rounded-2xl px-4 py-3 text-left transition-colors ${
                    isActive
                      ? "bg-surface-container-low text-primary border border-primary/30"
                      : "border border-transparent text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                  key={view.id}
                  onClick={() => onSelectExplorerView(view.id)}
                  type="button"
                >
                  <span className="material-symbols-outlined">{view.icon}</span>
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold">{view.label}</span>
                    <span className="text-[10px] uppercase tracking-[0.18em] opacity-70">
                      {view.description}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="px-6 mt-auto">
        <button
          className="w-full py-2 bg-gradient-to-br from-primary to-primary-container text-on-primary-fixed rounded-md text-xs font-bold transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          disabled={Boolean(isExportDisabled)}
          onClick={onExport}
          type="button"
        >
          Export Sequence
        </button>
        <div className="mt-6 space-y-2">
          <Link
            href="/documentation"
            className="flex items-center gap-3 text-on-surface-variant opacity-70 hover:opacity-100 text-[10px] uppercase tracking-wider font-semibold"
          >
            <span className="material-symbols-outlined text-sm">help</span>
            Documentation
          </Link>
          <Link
            href="/support"
            className="flex items-center gap-3 text-on-surface-variant opacity-70 hover:opacity-100 text-[10px] uppercase tracking-wider font-semibold"
          >
            <span
              className="material-symbols-outlined text-sm"
            >
              contact_support
            </span>
            Support
          </Link>
        </div>
      </div>
    </aside>
  );
}
