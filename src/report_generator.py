"""Generates machine-readable JSON reports and standalone interactive HTML reports."""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.mutant_model import Mutant, MutationStatus
from src.scoring import CampaignMetrics


class ReportGenerator:
    """Produces JSON and standalone HTML reports from mutation campaign results."""

    def __init__(
        self,
        output_dir: Path,
        project_name: str,
        solidity_version: str,
        framework: str,
        command_line: str = ""
    ):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = project_name
        self.solidity_version = solidity_version
        self.framework = framework
        self.command_line = command_line
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_json(
        self,
        mutants: List[Mutant],
        metrics: CampaignMetrics,
        filename: str = "mutation_report.json"
    ) -> Path:
        """Write detailed campaign data to a JSON file."""
        report_data = {
            "meta": {
                "project_name": self.project_name,
                "timestamp": self.timestamp,
                "solidity_version": self.solidity_version,
                "framework": self.framework,
                "command_line": self.command_line,
                "tool_version": "1.0.0"
            },
            "metrics": metrics.to_dict(),
            "mutants": [m.to_dict() for m in mutants]
        }

        output_file = self.output_dir / filename
        output_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        return output_file

    def generate_html(
        self,
        mutants: List[Mutant],
        metrics: CampaignMetrics,
        filename: str = "mutation_report.html"
    ) -> Path:
        """Write interactive standalone HTML report."""
        output_file = self.output_dir / filename
        html_content = self._render_html(mutants, metrics)
        output_file.write_text(html_content, encoding="utf-8")
        return output_file

    def _render_html(self, mutants: List[Mutant], metrics: CampaignMetrics) -> str:
        """Construct standalone HTML document with embedded CSS, JS, and diff viewer."""
        # Calculate survivors with recommendations
        survivors = [m for m in mutants if m.status == MutationStatus.SURVIVED]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Solidity Mutation Testing Report — {self.project_name}</title>
<style>
  :root {{
    --bg: #0f172a;
    --card-bg: #1e293b;
    --card-border: #334155;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --accent: #38bdf8;
    --success: #22c55e;
    --danger: #ef4444;
    --warning: #f59e0b;
    --neutral: #64748b;
    --code-bg: #0b1120;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 2rem;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  header {{
    border-bottom: 1px solid var(--card-border);
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
  }}
  h1 {{ font-size: 2rem; color: var(--text-primary); margin-bottom: 0.5rem; }}
  .meta-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }}
  .meta-item strong {{ color: var(--text-primary); }}

  /* Metric cards */
  .grid-metrics {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.25rem;
    margin-bottom: 2.5rem;
  }}
  .metric-card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 1.25rem;
    text-align: center;
  }}
  .metric-card .value {{
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0.25rem 0;
  }}
  .metric-card .label {{
    color: var(--text-secondary);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .val-score {{ color: var(--accent); }}
  .val-killed {{ color: var(--success); }}
  .val-survived {{ color: var(--danger); }}
  .val-invalid {{ color: var(--warning); }}

  /* Sections */
  .section {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }}
  .section h2 {{
    font-size: 1.3rem;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid var(--card-border);
    padding-bottom: 0.5rem;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
    text-align: left;
  }}
  th, td {{
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--card-border);
  }}
  th {{
    background-color: rgba(255, 255, 255, 0.03);
    color: var(--text-secondary);
    font-weight: 600;
  }}
  tr:hover {{ background-color: rgba(255, 255, 255, 0.02); }}

  /* Badges */
  .badge {{
    display: inline-block;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
  }}
  .badge-killed {{ background-color: rgba(34, 197, 94, 0.2); color: var(--success); border: 1px solid var(--success); }}
  .badge-survived {{ background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }}
  .badge-invalid {{ background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }}
  .badge-equivalent {{ background-color: rgba(148, 163, 184, 0.2); color: var(--text-secondary); border: 1px solid var(--neutral); }}
  .badge-timeout {{ background-color: rgba(234, 88, 12, 0.2); color: #ea580c; border: 1px solid #ea580c; }}
  .badge-unresolved {{ background-color: rgba(100, 116, 139, 0.2); color: var(--neutral); border: 1px solid var(--neutral); }}

  /* Code & Diffs */
  pre, code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: var(--code-bg);
    border-radius: 4px;
  }}
  code {{ padding: 0.15rem 0.3rem; font-size: 0.85rem; }}
  pre {{ padding: 0.75rem; overflow-x: auto; margin-top: 0.5rem; border: 1px solid var(--card-border); }}
  .diff-del {{ color: #f87171; background: rgba(239, 68, 68, 0.1); }}
  .diff-add {{ color: #4ade80; background: rgba(34, 197, 94, 0.1); }}

  /* Filter controls */
  .filter-bar {{
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    padding: 0.4rem 0.8rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
  }}
  .filter-btn.active {{
    background: var(--accent);
    color: #0f172a;
    font-weight: 600;
  }}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>Solidity Mutation Testing Report</h1>
    <div class="meta-bar">
      <div class="meta-item">Project: <strong>{self.project_name}</strong></div>
      <div class="meta-item">Compiler: <strong>{self.solidity_version}</strong></div>
      <div class="meta-item">Framework: <strong>{self.framework}</strong></div>
      <div class="meta-item">Timestamp: <strong>{self.timestamp}</strong></div>
    </div>
  </header>

  <!-- Metric Summary Cards -->
  <div class="grid-metrics">
    <div class="metric-card">
      <div class="label">Mutation Score</div>
      <div class="value val-score">{metrics.mutation_score}%</div>
      <div class="label">K / (M - I - E) * 100</div>
    </div>
    <div class="metric-card">
      <div class="label">Total Mutants</div>
      <div class="value">{metrics.total_mutants}</div>
      <div class="label">{metrics.total_candidates_discovered} Candidates Discovered</div>
    </div>
    <div class="metric-card">
      <div class="label">Killed Mutants</div>
      <div class="value val-killed">{metrics.killed}</div>
      <div class="label">Detected by Tests</div>
    </div>
    <div class="metric-card">
      <div class="label">Surviving Mutants</div>
      <div class="value val-survived">{metrics.survived}</div>
      <div class="label">Undetected Faults</div>
    </div>
    <div class="metric-card">
      <div class="label">Compilation Rate</div>
      <div class="value">{metrics.compilation_success_rate}%</div>
      <div class="label">{metrics.invalid} Invalid / Uncompilable</div>
    </div>
    <div class="metric-card">
      <div class="label">Avg Execution Time</div>
      <div class="value">{metrics.average_execution_time_seconds}s</div>
      <div class="label">Total {metrics.total_execution_time_seconds}s</div>
    </div>
  </div>

  <!-- Operator Breakdown Table -->
  <div class="section">
    <h2>Operator Performance Analysis</h2>
    <table>
      <thead>
        <tr>
          <th>Operator</th>
          <th>Total</th>
          <th>Killed</th>
          <th>Survived</th>
          <th>Invalid</th>
          <th>Timeout</th>
          <th>Mutation Score</th>
        </tr>
      </thead>
      <tbody>
"""
        for op_name, op in metrics.operator_scores.items():
            html += f"""
        <tr>
          <td><strong>{op_name}</strong></td>
          <td>{op.total_mutants}</td>
          <td><span style="color:var(--success)">{op.killed}</span></td>
          <td><span style="color:var(--danger)">{op.survived}</span></td>
          <td>{op.invalid}</td>
          <td>{op.timeout}</td>
          <td><strong>{op.mutation_score}%</strong></td>
        </tr>
"""

        html += """
      </tbody>
    </table>
  </div>

  <!-- Surviving Mutants Details -->
  <div class="section">
    <h2>Surviving Mutants & Recommendations</h2>
"""
        if not survivors:
            html += "<p style='color:var(--success)'>No surviving mutants! The test suite killed 100% of valid mutants.</p>"
        else:
            html += """
    <p style="color:var(--text-secondary); margin-bottom: 1rem;">
      The following mutants were not detected by the test suite. Each represents an undetected behavioral alteration.
    </p>
    <table>
      <thead>
        <tr>
          <th>Mutant ID</th>
          <th>Operator</th>
          <th>Source Location</th>
          <th>Transformation</th>
          <th>Reason & Recommended Test</th>
        </tr>
      </thead>
      <tbody>
"""
            for s in survivors:
                rec = "Add targeted boundary assertions or invariant checks."
                if s.operator_name == "TIMESTAMP_RELIANCE":
                    rec = "Add boundary test exercising block.timestamp at exact deadline (vm.warp(deadline))."
                elif s.operator_name == "REENTRANCY":
                    rec = "Add attacker contract test verifying state balance reduction during reentrant call."
                elif s.operator_name == "UNCHECKED_MATH":
                    rec = "Add edge-case test exercising max integer values to verify overflow revert."

                orig_code = s.transformation.get("original", "")
                mut_code = s.transformation.get("mutated", "")

                html += f"""
        <tr>
          <td><strong>{s.mutant_id}</strong></td>
          <td><span class="badge badge-survived">{s.operator_name}</span></td>
          <td><code>{s.source_file}:{s.line_number}</code></td>
          <td>
            <pre><span class="diff-del">- {orig_code}</span><br><span class="diff-add">+ {mut_code}</span></pre>
          </td>
          <td>
            <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.25rem;">{s.status_reason}</div>
            <div style="color:var(--accent); font-size:0.85rem;"><strong>Suggestion:</strong> {rec}</div>
          </td>
        </tr>
"""
            html += """
      </tbody>
    </table>
"""

        html += """
  </div>

  <!-- Complete Mutants List -->
  <div class="section">
    <h2>All Evaluated Mutants</h2>
    <div class="filter-bar">
      <button class="filter-btn active" onclick="filterTable('all')">All</button>
      <button class="filter-btn" onclick="filterTable('KILLED')">Killed</button>
      <button class="filter-btn" onclick="filterTable('SURVIVED')">Survived</button>
      <button class="filter-btn" onclick="filterTable('INVALID')">Invalid</button>
    </div>
    <table id="mutantsTable">
      <thead>
        <tr>
          <th>ID</th>
          <th>Operator</th>
          <th>Location</th>
          <th>Status</th>
          <th>Duration</th>
          <th>Transformation</th>
          <th>Failing Tests / Summary</th>
        </tr>
      </thead>
      <tbody>
"""
        for m in mutants:
            badge_class = f"badge-{m.status.value.lower()}"
            failing_str = ", ".join(m.failing_tests) if m.failing_tests else m.status_reason
            orig_t = m.transformation.get("original", "")
            mut_t = m.transformation.get("mutated", "")

            html += f"""
        <tr data-status="{m.status.value}">
          <td><strong>{m.mutant_id}</strong></td>
          <td>{m.operator_name}</td>
          <td><code>{m.source_file}:{m.line_number}</code></td>
          <td><span class="badge {badge_class}">{m.status.value}</span></td>
          <td>{m.execution_time_seconds:.2f}s</td>
          <td>
            <pre style="margin:0;"><span class="diff-del">- {orig_t}</span><br><span class="diff-add">+ {mut_t}</span></pre>
          </td>
          <td style="font-size:0.85rem; color:var(--text-secondary); max-width: 300px; word-break: break-word;">
            {failing_str}
          </td>
        </tr>
"""

        html += """
      </tbody>
    </table>
  </div>

  <!-- Reproducibility Metadata -->
  <div class="section">
    <h2>Reproducibility & Execution Metadata</h2>
    <p style="color:var(--text-secondary); font-size:0.9rem;">
      Command line executed: <code>""" + (self.command_line or "python main.py") + """</code><br>
      Execution environment: Python 3.11+, Foundry/Forge toolchain.<br>
      All mutants evaluated in disposable isolated workspaces.
    </p>
  </div>

</div>

<script>
function filterTable(status) {
  const rows = document.querySelectorAll('#mutantsTable tbody tr');
  const buttons = document.querySelectorAll('.filter-btn');
  buttons.forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  rows.forEach(r => {
    if (status === 'all' || r.getAttribute('data-status') === status) {
      r.style.display = '';
    } else {
      r.style.display = 'none';
    }
  });
}
</script>
</body>
</html>
"""
        return html
