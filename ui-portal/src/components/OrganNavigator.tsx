"use client";

interface Props {
  selectedOrgan: string;
  onSelectOrgan: (organ: string) => void;
}

const organs = [
  { id: "liver", label: "Liver", icon: "vital_signs" },
  { id: "heart", label: "Heart", icon: "favorite" },
  { id: "lung", label: "Lung", icon: "air" },
  { id: "kidney", label: "Kidney", icon: "opacity" },
  { id: "brain", label: "Brain", icon: "psychology" },
];

export default function OrganNavigator({ selectedOrgan, onSelectOrgan }: Props) {
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
        {organs.map((organ) => {
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
              <span className="text-xs font-medium font-body">{organ.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="px-6 mt-auto">
        <button className="w-full py-2 bg-gradient-to-br from-primary to-primary-container text-on-primary-fixed rounded-md text-xs font-bold transition-all active:scale-[0.98]">
          Export Sequence
        </button>
        <div className="mt-6 space-y-2">
          <a
            href="#"
            className="flex items-center gap-3 text-on-surface-variant opacity-70 hover:opacity-100 text-[10px] uppercase tracking-wider font-semibold"
          >
            <span className="material-symbols-outlined text-sm">help</span>
            Documentation
          </a>
          <a
            href="#"
            className="flex items-center gap-3 text-on-surface-variant opacity-70 hover:opacity-100 text-[10px] uppercase tracking-wider font-semibold"
          >
            <span
              className="material-symbols-outlined text-sm"
            >
              contact_support
            </span>
            Support
          </a>
        </div>
      </div>
    </aside>
  );
}
