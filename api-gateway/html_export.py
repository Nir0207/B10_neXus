from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from schemas import ExportChartRequest


def build_export_html(payload: ExportChartRequest) -> str:
    report_id = payload.report_id or f"BNX-{uuid4().hex[:12].upper()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    chart_title = payload.title.strip() or "BioNexus Intelligence Report"
    disease_label = payload.disease_name or payload.disease_id or chart_title
    summary = payload.clinical_summary.strip() or "No clinical summary was supplied."
    traces = _build_plotly_traces(payload)
    table_headers = _build_table_headers(payload.datasets)
    table_rows = _build_table_rows(payload.datasets)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioNexus | Intelligence Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{ --primary: #0f172a; --accent: #2563eb; --bg: #f8fafc; --text: #334155; }}
        body {{ font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; padding: 40px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
        .header {{ border-bottom: 2px solid var(--primary); padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-weight: 800; font-size: 24px; color: var(--primary); letter-spacing: -1px; }}
        .meta {{ font-size: 12px; text-align: right; color: #64748b; }}
        .summary-box {{ background: #eff6ff; border-left: 4px solid var(--accent); padding: 20px; margin-bottom: 30px; border-radius: 0 4px 4px 0; }}
        h1, h2 {{ color: var(--primary); margin-top: 0; }}
        #chart-container {{ width: 100%; height: 450px; margin-bottom: 40px; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
        .data-table th {{ background: #f1f5f9; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; }}
        .data-table td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
        .footer {{ margin-top: 50px; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
        @media print {{ body {{ padding: 0; background: white; }} .container {{ border: none; box-shadow: none; width: 100%; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">BIONEXUS <span style="font-weight: 300; font-size: 16px;">FORGE</span></div>
            <div class="meta">
                Report ID: {html.escape(report_id)}<br>
                Generated: {html.escape(timestamp)}<br>
                Model: {html.escape(payload.model_name)}
            </div>
        </header>

        <section class="summary-box">
            <h2>Clinical Executive Summary</h2>
            <p>{html.escape(summary)}</p>
        </section>

        <section>
            <h2>Visual Intelligence: {html.escape(disease_label)}</h2>
            <div id="chart-container"></div>
        </section>

        <section>
            <h2>Detailed Data Matrix</h2>
            <table class="data-table">
                <thead>{table_headers}</thead>
                <tbody>{table_rows}</tbody>
            </table>
        </section>

        <footer class="footer">
            <strong>Compliance &amp; Data Lineage:</strong> This report is generated from de-identified metadata sourced from NCBI, Open Targets, UniProt, and ChEMBL. <br>
            <strong>Disclaimer:</strong> This is an AI-assisted research tool. Findings must be validated by a certified clinical professional. 100% Local Processing - GxP Ready.
        </footer>
    </div>

    <script>
        const chartData = {json.dumps(traces)};
        const layout = {{
            title: {json.dumps(chart_title)},
            font: {{ family: 'Inter', size: 14 }},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: {{ l: 50, r: 50, b: 50, t: 80 }},
            polar: {{ radialaxis: {{ visible: true }} }}
        }};
        Plotly.newPlot('chart-container', chartData, layout, {{ responsive: true }});
    </script>
</body>
</html>"""


def _build_plotly_traces(payload: ExportChartRequest) -> list[dict[str, Any]]:
    if payload.chart_type == "line":
        return [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": [row.get(payload.x_key) for row in payload.datasets],
                "y": [row.get(payload.y_key) for row in payload.datasets],
                "name": payload.title,
                "line": {"color": "#2563eb", "width": 3},
                "marker": {"color": "#0f172a", "size": 8},
            }
        ]

    if payload.chart_type == "radar":
        return [
            {
                "type": "scatterpolar",
                "r": [row.get(payload.y_key) for row in payload.datasets],
                "theta": [row.get(payload.x_key) for row in payload.datasets],
                "fill": "toself",
                "name": payload.title,
                "marker": {"color": "#2563eb"},
            }
        ]

    return [
        {
            "type": "bar",
            "x": [row.get(payload.x_key) for row in payload.datasets],
            "y": [row.get(payload.y_key) for row in payload.datasets],
            "name": payload.title,
            "marker": {"color": "#2563eb"},
        }
    ]


def _build_table_headers(datasets: list[dict[str, Any]]) -> str:
    if not datasets:
        return "<tr><th>No data</th></tr>"

    headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in datasets[0].keys())
    return f"<tr>{headers}</tr>"


def _build_table_rows(datasets: list[dict[str, Any]]) -> str:
    if not datasets:
        return "<tr><td>No rows available.</td></tr>"

    rows: list[str] = []
    for row in datasets:
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in row.values())
        rows.append(f"<tr>{cells}</tr>")
    return "".join(rows)
