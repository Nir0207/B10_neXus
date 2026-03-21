const SUPPORT_ITEMS: readonly [string, string][] = [
  ["API Gateway", "Verify http://localhost:8000/ returns {\"status\":\"ok\"} before signing in."],
  ["Credentials", "The default local development account is admin/password unless overridden by gateway env vars."],
  ["Neo4j", "If graph views are empty, confirm the Lake Neo4j container is healthy and the refinery pipeline has completed."],
  ["Logout", "Logout clears the browser session and forces a fresh JWT mint on the next sign-in."],
];

export default function SupportPage(): React.JSX.Element {
  return (
    <main className="flex-1 overflow-y-auto p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <section className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low p-8 shadow-2xl">
          <p className="text-xs uppercase tracking-[0.3em] text-primary mb-3">Support</p>
          <h1 className="text-4xl font-headline font-bold mb-4">Manual troubleshooting guide</h1>
          <p className="max-w-2xl text-sm leading-relaxed text-on-surface-variant">
            Use this page when a route renders but the data plane or session flow looks wrong.
            The checks below map directly to the services currently running in Docker.
          </p>
        </section>

        {SUPPORT_ITEMS.map(([label, copy]) => (
          <article
            className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl"
            key={label}
          >
            <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">{label}</p>
            <p className="text-sm leading-relaxed text-on-surface-variant">{copy}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
