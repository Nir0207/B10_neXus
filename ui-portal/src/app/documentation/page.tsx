import Link from "next/link";

const COMMANDS: readonly string[] = [
  "python3 test_suite_master.py",
  "docker-compose up -d",
  "npm run dev --prefix ui-portal",
];

export default function DocumentationPage(): React.JSX.Element {
  return (
    <main className="flex-1 overflow-y-auto p-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low p-8 shadow-2xl">
          <p className="text-xs uppercase tracking-[0.3em] text-primary mb-3">Documentation</p>
          <h1 className="text-4xl font-headline font-bold mb-4">BioNexus operator quickstart</h1>
          <p className="max-w-3xl text-sm leading-relaxed text-on-surface-variant">
            This portal sits on top of the API gateway, Lake services, and the graph staging flow.
            Use the commands below to validate the stack before manual exploratory testing.
          </p>
        </section>

        <section className="grid gap-5 md:grid-cols-3">
          {COMMANDS.map((command) => (
            <article
              className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl"
              key={command}
            >
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">Command</p>
              <code className="block text-sm leading-relaxed text-on-surface">{command}</code>
            </article>
          ))}
        </section>

        <section className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-8 shadow-xl">
          <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">Manual Validation</p>
          <div className="grid gap-4 text-sm text-on-surface-variant md:grid-cols-2">
            <p>1. Sign in on the login route with the telemetry admin credentials.</p>
            <p>2. Open Explorer and switch organs to confirm graph refresh behavior.</p>
            <p>3. Open Pathways and verify the UniProt-backed gene detail panel populates.</p>
            <p>4. Open Clinical Trials and confirm therapeutic candidate rows are present.</p>
          </div>
          <div className="mt-6">
            <Link className="text-primary text-sm font-semibold hover:underline" href="/support">
              Need runtime troubleshooting? Open the support guide.
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
