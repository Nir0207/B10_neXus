"use client";

import type { ExportChartRequest, ExportHtmlResponse } from "@/services/analyticsService";
import { analyticsService } from "@/services/analyticsService";

function buildPlotlyTrace(payload: ExportChartRequest): Array<Record<string, unknown>> {
  if (payload.chart_type === "line") {
    return [
      {
        type: "scatter",
        mode: "lines+markers",
        x: payload.datasets.map((row) => row[payload.x_key]),
        y: payload.datasets.map((row) => row[payload.y_key]),
        name: payload.title,
      },
    ];
  }

  if (payload.chart_type === "radar") {
    return [
      {
        type: "scatterpolar",
        r: payload.datasets.map((row) => row[payload.y_key]),
        theta: payload.datasets.map((row) => row[payload.x_key]),
        fill: "toself",
        name: payload.title,
      },
    ];
  }

  return [
    {
      type: "bar",
      x: payload.datasets.map((row) => row[payload.x_key]),
      y: payload.datasets.map((row) => row[payload.y_key]),
      name: payload.title,
    },
  ];
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildTableHeaders(datasets: ExportChartRequest["datasets"]): string {
  if (!datasets.length) {
    return "<tr><th>No data</th></tr>";
  }

  return `<tr>${Object.keys(datasets[0])
    .map((key) => `<th>${escapeHtml(key)}</th>`)
    .join("")}</tr>`;
}

function buildTableRows(datasets: ExportChartRequest["datasets"]): string {
  if (!datasets.length) {
    return "<tr><td>No rows available.</td></tr>";
  }

  return datasets
    .map(
      (row) =>
        `<tr>${Object.values(row)
          .map((value) => `<td>${escapeHtml(String(value ?? ""))}</td>`)
          .join("")}</tr>`
    )
    .join("");
}

export function buildPharmaHtml(payload: ExportChartRequest): string {
  const reportId = payload.report_id ?? `BNX-${crypto.randomUUID().slice(0, 12).toUpperCase()}`;
  const timestamp = new Date().toISOString();
  const plotlyData = JSON.stringify(buildPlotlyTrace(payload));

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioNexus | Intelligence Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root { --primary: #0f172a; --accent: #2563eb; --bg: #f8fafc; --text: #334155; }
        body { font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; padding: 40px; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .header { border-bottom: 2px solid var(--primary); padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-weight: 800; font-size: 24px; color: var(--primary); letter-spacing: -1px; }
        .meta { font-size: 12px; text-align: right; color: #64748b; }
        .summary-box { background: #eff6ff; border-left: 4px solid var(--accent); padding: 20px; margin-bottom: 30px; border-radius: 0 4px 4px 0; }
        #chart-container { width: 100%; height: 450px; margin-bottom: 40px; }
        .data-table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
        .data-table th { background: #f1f5f9; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; }
        .data-table td { padding: 12px; border-bottom: 1px solid #e2e8f0; }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">BIONEXUS <span style="font-weight: 300; font-size: 16px;">FORGE</span></div>
            <div class="meta">
                Report ID: ${escapeHtml(reportId)}<br>
                Generated: ${escapeHtml(timestamp)}<br>
                Model: ${escapeHtml(payload.model_name ?? "BioMistral-7B-Instruct")}
            </div>
        </header>
        <section class="summary-box">
            <h2>Clinical Executive Summary</h2>
            <p>${escapeHtml(payload.clinical_summary)}</p>
        </section>
        <section>
            <h2>Visual Intelligence: ${escapeHtml(payload.title)}</h2>
            <div id="chart-container"></div>
        </section>
        <section>
            <h2>Detailed Data Matrix</h2>
            <table class="data-table">
                <thead>${buildTableHeaders(payload.datasets)}</thead>
                <tbody>${buildTableRows(payload.datasets)}</tbody>
            </table>
        </section>
    </div>
    <script>
        const chartData = ${plotlyData};
        const layout = {
            title: ${JSON.stringify(payload.title)},
            font: { family: 'Inter', size: 14 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            polar: { radialaxis: { visible: true } },
            margin: { l: 50, r: 50, b: 50, t: 80 }
        };
        Plotly.newPlot('chart-container', chartData, layout, { responsive: true });
    </script>
</body>
</html>`;
}

function downloadHtmlFile(result: ExportHtmlResponse): void {
  const blob = new Blob([result.html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = result.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function exportToPharmaHTML(payload: ExportChartRequest): Promise<void> {
  try {
    const result = await analyticsService.exportChart(payload);
    downloadHtmlFile(result);
    return;
  } catch (_error) {
    const fallback: ExportHtmlResponse = {
      filename: `bionexus-${(payload.disease_id ?? payload.title).toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}.html`,
      html: buildPharmaHtml(payload),
    };
    downloadHtmlFile(fallback);
  }
}
