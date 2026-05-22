import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


PAYLOAD_LABELS = {
    1: '1B',
    10485760: '10MB',
    104857600: '100MB',
}


def parse_scalability_filename(file_path: Path):
    """Parse scalability test result filename."""
    stem = file_path.stem
    # Python_Cryptography-scalability-10485760-20260424-121000-summary
    pattern = re.compile(r'^(?P<node>.+?)-scalability-(?P<payload>\d+)-(?P<ts>\d{8}-\d{6})-summary$')
    match = pattern.match(stem)
    if not match:
        return None
    
    groups = match.groupdict()
    return {
        'node': groups['node'],
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


def load_scalability_results(results_dir: Path):
    """Load all scalability test results."""
    results = {}  # {library: {payload: data}}
    
    for file in sorted(results_dir.glob('**/scalability/*-summary.json')):
        try:
            with file.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, ValueError):
            continue
        
        metadata = parse_scalability_filename(file)
        if metadata is None:
            continue
        
        metrics = data.get('metrics', {})
        
        run_data = {
            'payload_bytes': metadata['payload_bytes'],
            'timestamp': metadata['timestamp'],
            'iterations': int(metrics.get('iterations', {}).get('count', 0)) if isinstance(metrics.get('iterations'), dict) else 0,
            'http_req_failed_rate': metric_value(metrics, 'http_req_failed', 'rate', 0.0),
            'http_req_duration_med': metric_value(metrics, 'http_req_duration', 'med', 0.0),
            'http_req_duration_p90': metric_value(metrics, 'http_req_duration', 'p(90)', 0.0),
            'http_req_duration_p95': metric_value(metrics, 'http_req_duration', 'p(95)', 0.0),
            'http_req_duration_avg': metric_value(metrics, 'http_req_duration', 'avg', 0.0),
            'http_reqs_rate': metric_value(metrics, 'http_reqs', 'rate', 0.0),
            'iteration_duration_avg': metric_value(metrics, 'iteration_duration', 'avg', 0.0),
            'round_trip_duration_avg': metric_value(metrics, 'round_trip_duration_ms', 'avg', 0.0),
            'vus_max': metric_value(metrics, 'vus_max', 'value', 0.0),
        }
        
        lib = metadata['node']
        if lib not in results:
            results[lib] = {}
        results[lib][metadata['payload_bytes']] = run_data
    
    return results


def generate_all_libraries_html(all_results):
    """Generate single HTML with dropdown for all libraries."""
    
    libraries = sorted(all_results.keys())
    
    # Convert results to JSON for JavaScript
    results_json = json.dumps({
        lib: {
            str(payload): {
                'payload_bytes': all_results[lib][payload]['payload_bytes'],
                'iterations': all_results[lib][payload]['iterations'],
                'http_req_duration_med': all_results[lib][payload]['http_req_duration_med'],
                'http_req_duration_p90': all_results[lib][payload]['http_req_duration_p90'],
                'http_req_duration_p95': all_results[lib][payload]['http_req_duration_p95'],
                'http_req_duration_avg': all_results[lib][payload]['http_req_duration_avg'],
                'http_reqs_rate': all_results[lib][payload]['http_reqs_rate'],
                'http_req_failed_rate': all_results[lib][payload]['http_req_failed_rate'],
                'iteration_duration_avg': all_results[lib][payload]['iteration_duration_avg'],
                'round_trip_duration_avg': all_results[lib][payload]['round_trip_duration_avg'],
                'vus_max': all_results[lib][payload]['vus_max'],
            }
            for payload in all_results[lib]
        }
        for lib in libraries
    })
    
    libraries_json = json.dumps(libraries)
    
    html = """<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Scalability Report Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #f5f2ea;
      --ink: #1b1f24;
      --muted: #5d6672;
      --panel: #fffdf8;
      --line: #e9e2d3;
      --shadow: 0 14px 32px rgba(39, 33, 18, 0.1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 0% 0%, #ece7db 0%, transparent 40%),
        radial-gradient(circle at 100% 100%, #efe9da 0%, transparent 35%),
        var(--bg);
    }
    .wrap { max-width: 1400px; margin: 0 auto; padding: 28px 16px 40px; }
    .hero {
      background: linear-gradient(120deg, #fcf6e7 0%, #fffdf7 40%, #eef6f5 100%);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      box-shadow: var(--shadow);
      margin-bottom: 20px;
    }
    h1 { margin: 0 0 8px; font-size: clamp(1.4rem, 2.5vw, 2rem); }
    .subtitle { margin: 0; color: var(--muted); }
    .controls { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; margin: 16px 0 0; }
    .control-group { display: flex; gap: 10px; align-items: center; }
    .control-group label { font-weight: 600; }
    select {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 10px;
      padding: 8px 12px;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 14px;
      cursor: pointer;
    }
    .badge { border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 6px 10px; font-family: 'IBM Plex Mono', monospace; font-size: 12px; display: inline-block; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 20px; }
    .card {
      background: var(--panel);
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 16px;
      box-shadow: var(--shadow);
    }
    .card h2 { margin: 0 0 16px; font-size: 1.1rem; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px; border-bottom: 1px solid var(--line); text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    th { background: rgba(27, 31, 36, 0.05); font-weight: 600; }
    tr:hover { background: rgba(27, 31, 36, 0.02); }
    .metric-good { color: #1c7c7d; font-weight: 600; }
    .metric-warn { color: #a57c1b; font-weight: 600; }
    .metric-bad { color: #c1482e; font-weight: 600; }
    .payload-section { margin-bottom: 24px; }
    .chart-card { padding: 12px 16px 6px; }
    canvas { max-height: 320px; }
    @media (max-width: 900px) {
      th, td { padding: 8px; font-size: 12px; }
      .controls { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Scalability Test Report</h1>
      <p class="subtitle">Wyniki testu skalowalności z ramping VU dla wybranej biblioteki</p>
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
const allResults = """ + results_json + """;
const libraries = """ + libraries_json + """;

const payloadLabels = {'1': '1B', '10485760': '10MB', '104857600': '100MB'};

let activeLibrary = libraries[0] || null;

function getPayloadLabel(payload) {
  return payloadLabels[String(payload)] || payload + 'B';
}

function buildLibrarySelector() {
  const select = document.getElementById('librarySelect');
  select.innerHTML = '';
  
  libraries.forEach((lib) => {
    const option = document.createElement('option');
    option.value = lib;
    option.textContent = lib;
    if (lib === activeLibrary) option.selected = true;
    select.appendChild(option);
  });
  
  select.onchange = (e) => {
    activeLibrary = e.target.value;
    refresh();
  };
}

function renderContent() {
  const container = document.getElementById('contentContainer');
  container.innerHTML = '';
  
  if (!activeLibrary || !allResults[activeLibrary]) {
    container.innerHTML = '<div class="card">Brak danych dla wybranej biblioteki.</div>';
    return;
  }
  
  const libraryData = allResults[activeLibrary];
  const payloads = Object.keys(libraryData).map(p => parseInt(p)).sort((a, b) => a - b);
  
  document.getElementById('payloadBadge').textContent = 
    'Payloads: ' + payloads.map(getPayloadLabel).join(', ');
  
  const tableRows = payloads.map((payload) => {
    const data = libraryData[String(payload)];
    const payloadLabel = getPayloadLabel(payload);
    
    const failPct = data.http_req_failed_rate * 100;
    const failClass = failPct < 1 ? 'metric-good' : (failPct < 5 ? 'metric-warn' : 'metric-bad');
    
    return `
      <tr>
        <td><strong>${payloadLabel}</strong></td>
        <td>${data.iterations}</td>
        <td>${Math.round(data.vus_max)}</td>
        <td>${data.http_req_duration_med.toFixed(2)}</td>
        <td>${data.http_req_duration_p90.toFixed(2)}</td>
        <td>${data.http_req_duration_p95.toFixed(2)}</td>
        <td>${data.http_req_duration_avg.toFixed(2)}</td>
        <td>${data.http_reqs_rate.toFixed(2)}</td>
        <td>${data.iteration_duration_avg.toFixed(2)}</td>
        <td>${data.round_trip_duration_avg.toFixed(2)}</td>
        <td class="${failClass}">${failPct.toFixed(4)}%</td>
      </tr>
    `;
  }).join('');
  
  const section = document.createElement('section');
  section.className = 'payload-section';
  section.innerHTML = `
    <div class="card">
      <h2>Wyniki skalowalności</h2>
      <table>
        <thead>
          <tr>
            <th>Payload</th>
            <th>Iteracje</th>
            <th>Max VU</th>
            <th>Med [ms]</th>
            <th>p90 [ms]</th>
            <th>p95 [ms]</th>
            <th>Avg [ms]</th>
            <th>Throughput [req/s]</th>
            <th>Iteration avg [ms]</th>
            <th>RTT avg [ms]</th>
            <th>Fail [%]</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>
    </div>
    <div class="card chart-card">
      <h2>Latencja (p50/p95/p99/avg)</h2>
      <canvas id="latencyChart"></canvas>
    </div>
    <div class="card chart-card">
      <h2>Iteration Duration vs Round Trip Time</h2>
      <canvas id="cryptoChart"></canvas>
    </div>
  `;
  container.appendChild(section);

  renderCharts(payloads, libraryData);
}

let latencyChart;
let cryptoChart;

function renderCharts(payloads, libraryData) {
  const labels = payloads.map(getPayloadLabel);
  const med = payloads.map((payload) => libraryData[String(payload)].http_req_duration_med || 0);
  const p90 = payloads.map((payload) => libraryData[String(payload)].http_req_duration_p90 || 0);
  const p95 = payloads.map((payload) => libraryData[String(payload)].http_req_duration_p95 || 0);
  const avg = payloads.map((payload) => libraryData[String(payload)].http_req_duration_avg || 0);
  const iterDuration = payloads.map((payload) => libraryData[String(payload)].iteration_duration_avg || 0);
  const rttDuration = payloads.map((payload) => libraryData[String(payload)].round_trip_duration_avg || 0);

  const latencyCanvas = document.getElementById('latencyChart');
  const cryptoCanvas = document.getElementById('cryptoChart');

  if (latencyChart) latencyChart.destroy();
  if (cryptoChart) cryptoChart.destroy();

  latencyChart = new Chart(latencyCanvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Med [ms]', data: med, backgroundColor: 'rgba(45, 91, 138, 0.6)' },
        { label: 'p90 [ms]', data: p90, backgroundColor: 'rgba(28, 124, 125, 0.6)' },
        { label: 'p95 [ms]', data: p95, backgroundColor: 'rgba(165, 124, 27, 0.6)' },
        { label: 'Avg [ms]', data: avg, backgroundColor: 'rgba(93, 102, 114, 0.6)' },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { position: 'top' } },
      scales: { y: { beginAtZero: true } }
    }
  });

  cryptoChart = new Chart(cryptoCanvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Iteration Duration [ms]', data: iterDuration, backgroundColor: 'rgba(28, 124, 125, 0.6)' },
        { label: 'Round Trip Time [ms]', data: rttDuration, backgroundColor: 'rgba(193, 72, 46, 0.6)' },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { position: 'top' } },
      scales: { y: { beginAtZero: true } }
    }
  });
}

function refresh() {
  buildLibrarySelector();
  renderContent();
}

refresh();
</script>
</body>
</html>
"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description='Generate scalability test report with library selector.')
    parser.add_argument('--results-dir', default='perf/results', help='Directory with test results.')
    parser.add_argument('--output', default='perf/dashboard/scalability-report.html', help='Output HTML file.')
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load all scalability results
    results = load_scalability_results(results_dir)
    
    if not results:
        print('No scalability test results found.')
        return

    # Generate single HTML for all libraries
    html = generate_all_libraries_html(results)
    output_file.write_text(html, encoding='utf-8')
    print('Generated: {}'.format(output_file))


if __name__ == '__main__':
    main()
