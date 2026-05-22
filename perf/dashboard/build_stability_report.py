import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


PAYLOAD_LABELS = {
    1: '1B',
    10485760: '10MB',
    104857600: '100MB',
}


def parse_stability_filename(file_path: Path):
    """Parse stability test result filename."""
    stem = file_path.stem
    # Python_Cryptography-stability-r1-1-20260430-005236-summary
    pattern = re.compile(r'^(?P<node>.+?)-stability-r(?P<repeat>\d+)-(?P<payload>\d+)-(?P<ts>\d{8}-\d{6})-summary$')
    match = pattern.match(stem)
    if not match:
        return None
    
    groups = match.groupdict()
    return {
        'node': groups['node'],
        'repeat': int(groups['repeat']),
        'payload_bytes': int(groups['payload']),
        'timestamp': groups['ts'],
    }


def metric_value(metrics, metric_name, value_name, default=0.0):
    """Extract metric value, handling different metric structures."""
    if metric_name in metrics:
        metric = metrics[metric_name]
        if isinstance(metric, dict):
            if 'values' in metric:
                return float(metric['values'].get(value_name, default))
            return float(metric.get(value_name, default))
    
    # Try with suffix for http_req_* metrics
    for key in metrics:
        if key.startswith(metric_name):
            metric = metrics[key]
            if isinstance(metric, dict):
                if 'values' in metric:
                    return float(metric['values'].get(value_name, default))
                return float(metric.get(value_name, default))
    
    return float(default)


def calc_stats(values):
    """Calculate min, max, avg, std dev, and coefficient of variation."""
    if not values or len(values) == 0:
        return {'min': 0, 'max': 0, 'avg': 0, 'std_dev': 0, 'cv_percent': 0}
    
    avg = statistics.mean(values)
    min_val = min(values)
    max_val = max(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0
    cv_percent = (std_dev / avg * 100) if avg > 0 else 0
    
    return {
        'min': min_val,
        'max': max_val,
        'avg': avg,
        'std_dev': std_dev,
        'cv_percent': cv_percent
    }


def load_stability_results(results_dir: Path):
    """Load all stability test results."""
    results = defaultdict(lambda: defaultdict(list))  # {library: {payload: [runs]}}
    
    for file in sorted(results_dir.glob('**/stability/*-summary.json')):
        try:
            with file.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, ValueError):
            continue
        
        metadata = parse_stability_filename(file)
        if metadata is None:
            continue
        
        metrics = data.get('metrics', {})
        
        run_data = {
            'repeat': metadata['repeat'],
            'payload_bytes': metadata['payload_bytes'],
            'timestamp': metadata['timestamp'],
            'iterations': int(metrics.get('iterations', {}).get('count', 0)) if isinstance(metrics.get('iterations'), dict) else 0,
            'http_req_failed_rate': metric_value(metrics, 'http_req_failed', 'rate', 0.0),
          'http_req_duration_p50': metric_value(metrics, 'http_req_duration', 'p(50)', 0.0),
            'http_req_duration_p95': metric_value(metrics, 'http_req_duration', 'p(95)', 0.0),
          'http_req_duration_p99': metric_value(metrics, 'http_req_duration', 'p(99)', 0.0),
            'http_req_duration_avg': metric_value(metrics, 'http_req_duration', 'avg', 0.0),
            'http_reqs_rate': metric_value(metrics, 'http_reqs', 'rate', 0.0),
            'encrypt_duration_avg': metric_value(metrics, 'encrypt_duration_ms', 'avg', 0.0),
            'decrypt_duration_avg': metric_value(metrics, 'decrypt_duration_ms', 'avg', 0.0),
            'decrypt_mismatch_rate': metric_value(metrics, 'decrypt_mismatch_rate', 'rate', 0.0),
        }
        
        results[metadata['node']][metadata['payload_bytes']].append(run_data)
    
    return results


def generate_all_libraries_html(all_results):
    """Generate single HTML with dropdown for all libraries."""
    
    libraries = sorted(all_results.keys())
    
    # Pre-calculate statistics per library/payload
    stats_data = {}
    for lib in libraries:
        stats_data[lib] = {}
        for payload in all_results[lib]:
            runs = all_results[lib][payload]
            
            # Extract values for each metric
            p50_vals = [r['http_req_duration_p50'] for r in runs]
            p95_vals = [r['http_req_duration_p95'] for r in runs]
            p99_vals = [r['http_req_duration_p99'] for r in runs]
            avg_vals = [r['http_req_duration_avg'] for r in runs]
            throughput_vals = [r['http_reqs_rate'] for r in runs]
            fail_vals = [r['http_req_failed_rate'] * 100 for r in runs]
            encrypt_vals = [r['encrypt_duration_avg'] for r in runs]
            decrypt_vals = [r['decrypt_duration_avg'] for r in runs]
            mismatch_vals = [r['decrypt_mismatch_rate'] * 100 for r in runs]
            
            stats_data[lib][payload] = {
                'p50': calc_stats(p50_vals),
                'p95': calc_stats(p95_vals),
                'p99': calc_stats(p99_vals),
                'avg': calc_stats(avg_vals),
                'throughput': calc_stats(throughput_vals),
                'fail': calc_stats(fail_vals),
                'encrypt': calc_stats(encrypt_vals),
                'decrypt': calc_stats(decrypt_vals),
                'mismatch': calc_stats(mismatch_vals),
            }
    
    # Convert results to JSON for JavaScript
    results_json = json.dumps({
        lib: {
            str(payload): [
                {
                    'repeat': r['repeat'],
                    'iterations': r['iterations'],
                    'http_req_duration_p50': r['http_req_duration_p50'],
                    'http_req_duration_p95': r['http_req_duration_p95'],
                    'http_req_duration_p99': r['http_req_duration_p99'],
                    'http_req_duration_avg': r['http_req_duration_avg'],
                    'http_reqs_rate': r['http_reqs_rate'],
                    'http_req_failed_rate': r['http_req_failed_rate'],
                    'decrypt_mismatch_rate': r['decrypt_mismatch_rate'],
                    'encrypt_duration_avg': r['encrypt_duration_avg'],
                    'decrypt_duration_avg': r['decrypt_duration_avg'],
                }
                for r in sorted(all_results[lib][payload], key=lambda x: x['repeat'])
            ]
            for payload in all_results[lib]
        }
        for lib in libraries
    })
    
    # Convert stats to JSON
    stats_json = json.dumps({
        lib: {
            str(payload): {k: v for k, v in stats_data[lib][payload].items()}
            for payload in stats_data[lib]
        }
        for lib in libraries
    })
    
    html = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Stability Report Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #f5f2ea;
      --ink: #1b1f24;
      --muted: #5d6672;
      --panel: #fffdf8;
      --line: #e9e2d3;
      --shadow: 0 14px 32px rgba(39, 33, 18, 0.1);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 0% 0%, #ece7db 0%, transparent 40%),
        radial-gradient(circle at 100% 100%, #efe9da 0%, transparent 35%),
        var(--bg);
    }}
    .wrap {{ max-width: 1400px; margin: 0 auto; padding: 28px 16px 40px; }}
    .hero {{
      background: linear-gradient(120deg, #fcf6e7 0%, #fffdf7 40%, #eef6f5 100%);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      box-shadow: var(--shadow);
      margin-bottom: 20px;
    }}
    h1 {{ margin: 0 0 8px; font-size: clamp(1.4rem, 2.5vw, 2rem); }}
    .subtitle {{ margin: 0; color: var(--muted); }}
    .controls {{ display: flex; gap: 16px; align-items: center; flex-wrap: wrap; margin: 16px 0 0; }}
    .control-group {{ display: flex; gap: 10px; align-items: center; }}
    .control-group label {{ font-weight: 600; }}
    select {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 10px;
      padding: 8px 12px;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 14px;
      cursor: pointer;
    }}
    .badge {{ border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 6px 10px; font-family: 'IBM Plex Mono', monospace; font-size: 12px; display: inline-block; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
    .card {{
      background: var(--panel);
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 16px;
      box-shadow: var(--shadow);
    }}
    .card h2 {{ margin: 0 0 16px; font-size: 1.1rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px; border-bottom: 1px solid var(--line); text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: rgba(27, 31, 36, 0.05); font-weight: 600; }}
    tr:hover {{ background: rgba(27, 31, 36, 0.02); }}
    .metric-good {{ color: #1c7c7d; font-weight: 600; }}
    .metric-warn {{ color: #a57c1b; font-weight: 600; }}
    .metric-bad {{ color: #c1482e; font-weight: 600; }}
    canvas {{ max-height: 300px; }}
    .payload-section {{ margin-bottom: 24px; }}
    .chart-card {{ padding: 12px 16px 6px; }}
    @media (max-width: 900px) {{
      th, td {{ padding: 8px; font-size: 12px; }}
      .controls {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Stability Test Report</h1>
      <p class="subtitle">Porównanie wyników między powtórzeniami (repeaty) dla wybranej biblioteki</p>
      <div class="controls">
        <div class="control-group">
          <label for="librarySelect">Biblioteka:</label>
          <select id="librarySelect"></select>
        </div>
        <span class="badge" id="payloadBadge">Payloads: -</span>
      </div>
    </section>

    <div class="grid" id="contentContainer">
      <!-- Dynamicznie generowane -->
    </div>
  </div>

<script>
const allResults = {results_json};
const allStats = {stats_json};
const libraries = {json.dumps(libraries)};

const payloadLabels = {{
  '1': '1B',
  '10485760': '10MB',
  '104857600': '100MB',
}};

let activeLibrary = libraries[0] || null;
const charts = {{}};
const cryptoCharts = {{}};
const variabilityCharts = {{}};

function getPayloadLabel(payload) {{
  return payloadLabels[String(payload)] || payload + 'B';
}}

function buildLibrarySelector() {{
  const select = document.getElementById('librarySelect');
  select.innerHTML = '';
  
  libraries.forEach((lib) => {{
    const option = document.createElement('option');
    option.value = lib;
    option.textContent = lib;
    if (lib === activeLibrary) option.selected = true;
    select.appendChild(option);
  }});
  
  select.onchange = (e) => {{
    activeLibrary = e.target.value;
    refresh();
  }};
}}

function renderContent() {{
  const container = document.getElementById('contentContainer');
  container.innerHTML = '';
  
  if (!activeLibrary || !allResults[activeLibrary]) {{
    container.innerHTML = '<div class="card">Brak danych dla wybranej biblioteki.</div>';
    return;
  }}
  
  const libraryData = allResults[activeLibrary];
  const payloads = Object.keys(libraryData).map(p => parseInt(p)).sort((a, b) => a - b);
  
  // Update badge
  document.getElementById('payloadBadge').textContent = 
    'Payloads: ' + payloads.map(getPayloadLabel).join(', ');
  
  // Render each payload
  payloads.forEach((payload) => {{
    const payloadStr = String(payload);
    const runs = libraryData[payloadStr];
    const payloadLabel = getPayloadLabel(payload);
    const stats = allStats[activeLibrary][payloadStr];
    
    // Table rows
    const tableRows = runs.map((run) => {{
      const mismatchPct = run.decrypt_mismatch_rate * 100;
      const failPct = run.http_req_failed_rate * 100;
      
      const mismatchClass = mismatchPct === 0 ? 'metric-good' : (mismatchPct < 5 ? 'metric-warn' : 'metric-bad');
      const failClass = failPct < 1 ? 'metric-good' : (failPct < 5 ? 'metric-warn' : 'metric-bad');
      
      return `
        <tr>
          <td>Repeat ${{run.repeat}}</td>
          <td>${{run.iterations}}</td>
          <td>${{run.http_req_duration_p50.toFixed(2)}}</td>
          <td>${{run.http_req_duration_p95.toFixed(2)}}</td>
          <td>${{run.http_req_duration_p99.toFixed(2)}}</td>
          <td>${{run.http_req_duration_avg.toFixed(2)}}</td>
          <td>${{run.http_reqs_rate.toFixed(2)}}</td>
          <td>${{run.encrypt_duration_avg.toFixed(2)}}</td>
          <td>${{run.decrypt_duration_avg.toFixed(2)}}</td>
          <td class="${{failClass}}">${{failPct.toFixed(4)}}%</td>
          <td class="${{mismatchClass}}">${{mismatchPct.toFixed(4)}}%</td>
        </tr>
      `;
    }}).join('');
    
    // Summary row
    const summaryRow = `
      <tr style="background: rgba(27, 31, 36, 0.08); font-weight: 600;">
        <td>AVG / CV%</td>
        <td>-</td>
        <td>${{stats.p50.avg.toFixed(2)}} / ${{stats.p50.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.p95.avg.toFixed(2)}} / ${{stats.p95.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.p99.avg.toFixed(2)}} / ${{stats.p99.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.avg.avg.toFixed(2)}} / ${{stats.avg.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.throughput.avg.toFixed(2)}} / ${{stats.throughput.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.encrypt.avg.toFixed(2)}} / ${{stats.encrypt.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.decrypt.avg.toFixed(2)}} / ${{stats.decrypt.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.fail.avg.toFixed(4)}}% / ${{stats.fail.cv_percent.toFixed(1)}}%</td>
        <td>${{stats.mismatch.avg.toFixed(4)}}% / ${{stats.mismatch.cv_percent.toFixed(1)}}%</td>
      </tr>
    `;
    
    const section = document.createElement('section');
    section.className = 'payload-section';
    section.innerHTML = `
      <div class="card">
        <h2>Payload: ${{payloadLabel}}</h2>
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Iteracje</th>
              <th>p50 [ms]</th>
              <th>p95 [ms]</th>
              <th>p99 [ms]</th>
              <th>Avg [ms]</th>
              <th>Throughput [req/s]</th>
              <th>Encrypt avg [ms]</th>
              <th>Decrypt avg [ms]</th>
              <th>Fail [%]</th>
              <th>Mismatch [%]</th>
            </tr>
          </thead>
          <tbody>
            ${{tableRows}}
            ${{summaryRow}}
          </tbody>
        </table>
      </div>
      <div class="card">
        <h2>Wykresy: ${{payloadLabel}}</h2>
        <canvas id="chart-${{payloadStr}}"></canvas>
      </div>
      <div class="card chart-card">
        <h2>Encrypt vs Decrypt: ${{payloadLabel}}</h2>
        <canvas id="crypto-chart-${{payloadStr}}"></canvas>
      </div>
      <div class="card chart-card">
        <h2>Stabilność Metryk (Coefficient of Variation): ${{payloadLabel}}</h2>
        <canvas id="variability-chart-${{payloadStr}}"></canvas>
      </div>
    `;
    container.appendChild(section);
    
    // Render charts
    setTimeout(() => {{
      renderChart(payloadStr, runs);
      renderCryptoChart(payloadStr, runs);
      renderVariabilityChart(payloadStr, allStats[activeLibrary][payloadStr]);
    }}, 0);
  }});
}}

function renderChart(payloadStr, runs) {{
  const repeats = runs.map((r) => `r${{r.repeat}}`);
  const p95Values = runs.map((r) => r.http_req_duration_p95);
  const failValues = runs.map((r) => r.http_req_failed_rate * 100);
  const mismatchValues = runs.map((r) => r.decrypt_mismatch_rate * 100);
  
  const canvasEl = document.getElementById(`chart-${{payloadStr}}`);
  if (!canvasEl) return;
  
  if (charts[payloadStr]) charts[payloadStr].destroy();
  
  charts[payloadStr] = new Chart(canvasEl.getContext('2d'), {{
    type: 'line',
    data: {{
      labels: repeats,
      datasets: [
        {{
          label: 'p95 [ms]',
          data: p95Values,
          borderColor: '#1c7c7d',
          backgroundColor: 'rgba(28, 124, 125, 0.1)',
          tension: 0.3,
          yAxisID: 'y',
        }},
        {{
          label: 'Fail [%]',
          data: failValues,
          borderColor: '#c1482e',
          backgroundColor: 'rgba(193, 72, 46, 0.1)',
          tension: 0.3,
          yAxisID: 'y1',
        }},
        {{
          label: 'Mismatch [%]',
          data: mismatchValues,
          borderColor: '#a57c1b',
          backgroundColor: 'rgba(165, 124, 27, 0.1)',
          tension: 0.3,
          yAxisID: 'y1',
        }},
      ],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y: {{
          type: 'linear',
          display: true,
          position: 'left',
          title: {{ display: true, text: 'p95 [ms]' }},
        }},
        y1: {{
          type: 'linear',
          display: true,
          position: 'right',
          title: {{ display: true, text: 'Fail / Mismatch [%]' }},
          grid: {{ drawOnChartArea: false }},
        }},
      }},
      plugins: {{
        legend: {{ position: 'top' }},
      }},
    }},
  }});
}}

function renderCryptoChart(payloadStr, runs) {{
  const repeats = runs.map((r) => `r${{r.repeat}}`);
  const encryptValues = runs.map((r) => r.encrypt_duration_avg);
  const decryptValues = runs.map((r) => r.decrypt_duration_avg);

  const canvasEl = document.getElementById(`crypto-chart-${{payloadStr}}`);
  if (!canvasEl) return;

  if (cryptoCharts[payloadStr]) cryptoCharts[payloadStr].destroy();

  cryptoCharts[payloadStr] = new Chart(canvasEl.getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: repeats,
      datasets: [
        {{
          label: 'Encrypt avg [ms]',
          data: encryptValues,
          backgroundColor: 'rgba(28, 124, 125, 0.6)'
        }},
        {{
          label: 'Decrypt avg [ms]',
          data: decryptValues,
          backgroundColor: 'rgba(193, 72, 46, 0.6)'
        }}
      ],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'top' }} }},
      scales: {{ y: {{ beginAtZero: true }} }}
    }}
  }});
}}

function renderVariabilityChart(payloadStr, stats) {{
  const metricNames = ['p50', 'p95', 'p99', 'avg', 'throughput', 'encrypt', 'decrypt', 'fail', 'mismatch'];
  const labels = ['p50', 'p95', 'p99', 'avg', 'Throughput', 'Encrypt', 'Decrypt', 'Fail', 'Mismatch'];
  const cvValues = metricNames.map(m => stats[m].cv_percent);
  
  const canvasEl = document.getElementById(`variability-chart-${{payloadStr}}`);
  if (!canvasEl) return;
  
  if (variabilityCharts[payloadStr]) variabilityCharts[payloadStr].destroy();
  
  // Color code CV: green < 5%, yellow 5-15%, red > 15%
  const colors = cvValues.map(cv => {{
    if (cv < 5) return 'rgba(28, 124, 125, 0.7)';    // green - stable
    if (cv < 15) return 'rgba(165, 124, 27, 0.7)';   // yellow - moderate
    return 'rgba(193, 72, 46, 0.7)';                 // red - unstable
  }});
  
  variabilityCharts[payloadStr] = new Chart(canvasEl.getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [
        {{
          label: 'Coefficient of Variation [%]',
          data: cvValues,
          backgroundColor: colors,
        }}
      ],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      scales: {{ y: {{ beginAtZero: true, max: 30 }} }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            afterLabel: function(context) {{
              const cv = context.parsed.y;
              if (cv < 5) return '✓ Stabilne';
              if (cv < 15) return '⚠ Umiarkowane';
              return '✗ Zmienne';
            }}
          }}
        }}
      }}
    }}
  }});
}}

function refresh() {{
  buildLibrarySelector();
  renderContent();
}}

refresh();
</script>
</body>
</html>
"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description='Generate stability test report with library selector.')
    parser.add_argument('--results-dir', default='perf/results', help='Directory with test results.')
    parser.add_argument('--output', default='perf/dashboard/stability-report.html', help='Output HTML file.')
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load all stability results
    results = load_stability_results(results_dir)
    
    if not results:
        print('No stability test results found.')
        return

    # Generate single HTML for all libraries
    html = generate_all_libraries_html(results)
    output_file.write_text(html, encoding='utf-8')
    print(f'Generated: {output_file}')


if __name__ == '__main__':
    main()
