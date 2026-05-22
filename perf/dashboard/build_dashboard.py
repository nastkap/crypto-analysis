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

TEST_TYPE_LABELS = {
  'performance': 'Wydajnosc',
  'stability': 'Stabilnosc',
  'scalability': 'Skalowalnosc',
}


def parse_summary_filename(file_path: Path):
  stem = file_path.stem

  patterns = [
    # Python_Cryptography-stability-r2-10485760-20260424-121000-summary (CHECK FIRST!)
    (re.compile(r'^(?P<node>.+?)-stability-r(?P<repeat>\d+)-(?P<payload>\d+)-(?P<ts>\d{8}-\d{6})-summary$'), 'stability'),
    # Python_Cryptography-perf-10485760-20260424-121000-summary
    (re.compile(r'^(?P<node>.+?)-(?P<test>perf|scalability)-(?P<payload>\d+)-(?P<ts>\d{8}-\d{6})-summary$'), None),
    # Legacy: Python_Cryptography-10485760-20260424-121000-summary
    (re.compile(r'^(?P<node>.+?)-(?P<payload>\d+)-(?P<ts>\d{8}-\d{6})-summary$'), 'perf'),
  ]

  for pattern, forced_test in patterns:
    match = pattern.match(stem)
    if not match:
      continue

    groups = match.groupdict()
    raw_test = forced_test or groups.get('test') or 'perf'
    test_type = {
      'perf': 'performance',
      'stability': 'stability',
      'scalability': 'scalability',
    }.get(raw_test, 'performance')

    return {
      'node': groups['node'],
      'payload_bytes': int(groups['payload']),
      'timestamp': groups['ts'],
      'test_type': test_type,
      'repeat': int(groups['repeat']) if groups.get('repeat') else None,
    }

  return None


def metric_value(metrics, metric_name, value_name, default=0.0):
  """Extract metric value, handling different metric structures."""
  if metric_name in metrics:
    metric = metrics[metric_name]
    if isinstance(metric, dict):
      if 'values' in metric:
        return float(metric['values'].get(value_name, default))
      return float(metric.get(value_name, default))

  for key in metrics:
    if key.startswith(metric_name):
      metric = metrics[key]
      if isinstance(metric, dict):
        if 'values' in metric:
          return float(metric['values'].get(value_name, default))
        return float(metric.get(value_name, default))

  return float(default)


def load_summaries(results_dir: Path):
  rows = []
  all_files = list(results_dir.glob('**/*-summary.json'))

  for file in sorted(all_files):
    try:
      with file.open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    except (json.JSONDecodeError, ValueError):
      continue

    metadata = parse_summary_filename(file)
    if metadata is None:
      continue

    metrics = data.get('metrics', {})
    rows.append(
      {
        'node': metadata['node'],
        'payload_bytes': metadata['payload_bytes'],
        'test_type': metadata['test_type'],
        'timestamp': metadata['timestamp'],
        'repeat': metadata['repeat'],
        'iterations': int(metrics.get('iterations', {}).get('values', {}).get('count', 0)),
        'http_req_failed_rate': metric_value(metrics, 'http_req_failed', 'rate', 0.0),
        'http_req_duration_p95': metric_value(metrics, 'http_req_duration', 'p(95)', 0.0),
        'http_req_duration_avg': metric_value(metrics, 'http_req_duration', 'avg', 0.0),
        'http_reqs_rate': metric_value(metrics, 'http_reqs', 'rate', 0.0),
        'encrypt_duration_avg': metric_value(metrics, 'encrypt_duration_ms', 'avg', 0.0),
        'decrypt_duration_avg': metric_value(metrics, 'decrypt_duration_ms', 'avg', 0.0),
        'decrypt_mismatch_rate': metric_value(metrics, 'decrypt_mismatch_rate', 'rate', 0.0),
      }
    )
  return rows


def aggregate_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row['test_type'], row['node'], row['payload_bytes'])
        grouped[key].append(row)

    aggregated = []
    for (test_type, node, payload_bytes), values in grouped.items():
        p95_values = [v['http_req_duration_p95'] for v in values]
        req_values = [v['http_reqs_rate'] for v in values]
        fail_values = [v['http_req_failed_rate'] for v in values]

        aggregated.append(
            {
                'test_type': test_type,
                'node': node,
                'payload_bytes': payload_bytes,
                'payload_label': PAYLOAD_LABELS.get(payload_bytes, f'{payload_bytes}B'),
                'runs': len(values),
                'http_req_duration_avg': statistics.mean(v['http_req_duration_avg'] for v in values),
                'http_req_duration_p95_avg': statistics.mean(p95_values),
                'http_req_duration_p95_min': min(p95_values),
                'http_req_duration_p95_max': max(p95_values),
                'http_reqs_rate_avg': statistics.mean(req_values),
                'http_req_failed_rate_avg': statistics.mean(fail_values),
                'http_req_failed_rate_max': max(fail_values),
                'decrypt_mismatch_rate_avg': statistics.mean(v['decrypt_mismatch_rate'] for v in values),
                'iterations_avg': statistics.mean(v['iterations'] for v in values),
                'encrypt_duration_avg': statistics.mean(v['encrypt_duration_avg'] for v in values),
                'decrypt_duration_avg': statistics.mean(v['decrypt_duration_avg'] for v in values),
                'latest_timestamp': max(v['timestamp'] for v in values),
            }
        )

    return sorted(aggregated, key=lambda x: (x['test_type'], x['payload_bytes'], x['node']))


def build_overview(aggregated_rows):
    overview = {}
    for test_type in TEST_TYPE_LABELS:
        subset = [row for row in aggregated_rows if row['test_type'] == test_type]
        if not subset:
            overview[test_type] = {
                'best_latency': None,
                'best_throughput': None,
                'most_reliable': None,
            }
            continue

        best_latency = min(subset, key=lambda row: row['http_req_duration_p95_avg'])
        best_throughput = max(subset, key=lambda row: row['http_reqs_rate_avg'])
        most_reliable = min(subset, key=lambda row: (row['http_req_failed_rate_avg'], row['decrypt_mismatch_rate_avg']))

        overview[test_type] = {
            'best_latency': {
                'node': best_latency['node'],
                'value': round(best_latency['http_req_duration_p95_avg'], 2),
                'unit': 'ms (p95 avg)',
            },
            'best_throughput': {
                'node': best_throughput['node'],
                'value': round(best_throughput['http_reqs_rate_avg'], 2),
                'unit': 'req/s',
            },
            'most_reliable': {
                'node': most_reliable['node'],
                'value': round(most_reliable['http_req_failed_rate_avg'] * 100.0, 4),
                'unit': 'fail %',
            },
        }

    return overview


def get_library_names(rows):
    """Extract unique library names from raw rows."""
    libs = set()
    for row in rows:
        libs.add(row['node'])
    return sorted(libs)


def to_html(aggregated_rows, raw_rows=None):
    rows_json = json.dumps(aggregated_rows)
    overview_json = json.dumps(build_overview(aggregated_rows))
    test_type_labels_json = json.dumps(TEST_TYPE_LABELS)
    
    # Extract library names for dropdown
    library_names = []
    if raw_rows:
        library_names = sorted(set(row['node'] for row in raw_rows))
    libraries_json = json.dumps(library_names)

    return f"""<!doctype html>
<html lang=\"pl\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Crypto Benchmark Report Dashboard</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
  <link href=\"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap\" rel=\"stylesheet\" />
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
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
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 28px 16px 40px; }}
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
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .badge {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      padding: 6px 10px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 12px;
    }}
    .controls-row {{ display: flex; gap: 16px; margin: 16px 0 20px; flex-wrap: wrap; align-items: center; }}
    .link-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
    .link-card {{
      display: block;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fff;
      text-decoration: none;
      color: var(--ink);
      box-shadow: var(--shadow);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .link-card:hover {{ transform: translateY(-2px); box-shadow: 0 18px 36px rgba(39, 33, 18, 0.12); }}
    .link-card span {{ display: block; font-size: 13px; color: var(--muted); margin-top: 4px; }}
    .control-group {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .control-group label {{ font-weight: 600; font-size: 14px; }}
    .toggle {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 10px;
      padding: 8px 12px;
      cursor: pointer;
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 600;
      transition: all 0.2s ease;
    }}
    .toggle.active {{ background: var(--ink); color: #fff; border-color: var(--ink); }}
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
    .stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      box-shadow: var(--shadow);
    }}
    .stat h3 {{ margin: 0 0 8px; font-size: 13px; color: var(--muted); }}
    .stat .value {{ font-size: 18px; font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
    .card {{
      background: var(--panel);
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 14px;
      box-shadow: var(--shadow);
    }}
    .card h2 {{ margin: 0 0 12px; font-size: 1.05rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .pill {{
      display: inline-block;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 2px 8px;
      background: #fff;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
    }}
    .empty {{ color: var(--muted); font-style: italic; }}
    .hidden {{ display: none; }}
    @media (max-width: 900px) {{
      .stats {{ grid-template-columns: 1fr; }}
      .controls-row {{ flex-direction: column; align-items: flex-start; }}
      .link-grid {{ grid-template-columns: 1fr; }}
      th, td {{ padding: 7px; font-size: 12px; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>Crypto Benchmark Dashboard</h1>
      <p class=\"subtitle\">Porownanie bibliotek dla payloadow 1B, 10MB i 100MB. Widok gotowy pod sprawozdanie.</p>
      <div class=\"badge-row\">
        <span class=\"badge\">Wykresy: p95, throughput, fail rate</span>
        <span class=\"badge\">Tryby: wydajnosc / stabilnosc / skalowalnosc</span>
        <span class=\"badge\" id=\"recordsBadge\">Rekordy: 0</span>
      </div>
      <div class=\"link-grid\">
        <a class=\"link-card\" href=\"performance-report.html\">
          Performance Report
          <span>Szczegolowe metryki p50/p95/p99</span>
        </a>
        <a class=\"link-card\" href=\"stability-report.html\">
          Stability Report
          <span>Powtorzenia, fail rate, mismatch</span>
        </a>
        <a class=\"link-card\" href=\"scalability-report.html\">
          Scalability Report
          <span>Ramping VU i punkt zalamania</span>
        </a>
      </div>
    </section>

    <div class=\"controls-row\">
      <div class=\"control-group\" id=\"testTypeToggle\"></div>
      <div class=\"control-group\" id=\"librarySelector\"></div>
    </div>

    <section class=\"stats\">
      <article class=\"stat\">
        <h3>Najszybsza biblioteka (p95)</h3>
        <div class=\"value\" id=\"bestLatency\">-</div>
      </article>
      <article class=\"stat\">
        <h3>Najwyzszy throughput</h3>
        <div class=\"value\" id=\"bestThroughput\">-</div>
      </article>
      <article class=\"stat\">
        <h3>Najbardziej niezawodna</h3>
        <div class=\"value\" id=\"mostReliable\">-</div>
      </article>
    </section>

    <div class=\"grid\">
      <div class=\"card\" id=\"p95CardWrapper\">
        <h2>p95 czasu odpowiedzi [ms]</h2>
        <canvas id=\"p95Chart\"></canvas>
      </div>
      <div class=\"card\" id=\"throughputCardWrapper\">
        <h2>Throughput [req/s]</h2>
        <canvas id=\"throughputChart\"></canvas>
      </div>
      <div class=\"card\" id=\"failCardWrapper\">
        <h2>Fail rate [%]</h2>
        <canvas id=\"failChart\"></canvas>
      </div>
      <div class=\"card\">
        <h2>Tabela agregowana</h2>
        <div id=\"tableContainer\"></div>
      </div>
      <div class=\"card hidden\" id=\"perLibraryTableCard\">
        <h2>Szczegoly per repeat (Stability)</h2>
        <div id=\"perLibraryTableContainer\"></div>
      </div>
    </div>
  </div>

<script>
const rows = {rows_json};
const overview = {overview_json};
const testTypeLabels = {test_type_labels_json};
const libraries = {libraries_json};

const palette = ['#c1482e', '#1c7c7d', '#2d5b8a', '#a57c1b'];
let activeTestType = 'performance';
let activeLibrary = null;

const recordsBadge = document.getElementById('recordsBadge');
recordsBadge.textContent = `Rekordy: ${{rows.length}}`;

function uniqueSorted(values, sortNumeric = false) {{
  const uniq = [...new Set(values)];
  return sortNumeric ? uniq.sort((a, b) => a - b) : uniq.sort();
}}

function payloadLabel(payload) {{
  if (payload === 1) return '1B';
  if (payload === 10485760) return '10MB';
  if (payload === 104857600) return '100MB';
  return `${{payload}}B`;
}}

function rowsForActiveType() {{
  let filtered = rows.filter((row) => row.test_type === activeTestType);
  if (activeLibrary && activeTestType === 'stability') {{
    filtered = filtered.filter((row) => row.node === activeLibrary);
  }}
  return filtered;
}}

function chartDataForMetric(metricName, transform = (value) => value) {{
  const source = rowsForActiveType();
  
  if (activeLibrary && activeTestType === 'stability') {{
    // Per-library stability: repeats on X-axis
    const payloads = uniqueSorted(source.map((row) => row.payload_bytes), true);
    const repeats = uniqueSorted(source.map((row) => row.repeat), true);
    
    const datasets = payloads.map((payload, idx) => {{
      const data = repeats.map((repeat) => {{
        const row = source.find((entry) => entry.payload_bytes === payload && entry.repeat === repeat);
        return row ? Number(transform(row[metricName]).toFixed(4)) : null;
      }});
      return {{
        label: payloadLabel(payload),
        data,
        backgroundColor: palette[idx % palette.length],
        borderRadius: 6,
      }};
    }});
    
    return {{ labels: repeats.map((r) => `Repeat ${{r}}`), datasets }};
  }} else {{
    // Cross-library: libraries on X-axis
    const libList = uniqueSorted(source.map((row) => row.node));
    const payloads = uniqueSorted(source.map((row) => row.payload_bytes), true);

    const datasets = payloads.map((payload, idx) => {{
      const data = libList.map((node) => {{
        const row = source.find((entry) => entry.node === node && entry.payload_bytes === payload);
        return row ? Number(transform(row[metricName]).toFixed(4)) : null;
      }});
      return {{
        label: payloadLabel(payload),
        data,
        backgroundColor: palette[idx % palette.length],
        borderRadius: 6,
      }};
    }});

    return {{ labels: libList, datasets }};
  }}
}}

function fillOverviewCards() {{
  const block = overview[activeTestType] || {{}};
  const latency = block.best_latency;
  const throughput = block.best_throughput;
  const reliable = block.most_reliable;

  document.getElementById('bestLatency').textContent = latency
    ? `${{latency.node}} (${{latency.value}} ${{latency.unit}})`
    : '-';
  document.getElementById('bestThroughput').textContent = throughput
    ? `${{throughput.node}} (${{throughput.value}} ${{throughput.unit}})`
    : '-';
  document.getElementById('mostReliable').textContent = reliable
    ? `${{reliable.node}} (${{reliable.value}} ${{reliable.unit}})`
    : '-';
}}

function renderTable() {{
  const source = rowsForActiveType();
  const container = document.getElementById('tableContainer');

  if (!source.length) {{
    container.innerHTML = '<p class="empty">Brak danych dla wybranego typu testu.</p>';
    return;
  }}

  const bodyRows = source
    .sort((a, b) => (a.payload_bytes - b.payload_bytes) || a.node.localeCompare(b.node))
    .map((row) => `
      <tr>
        <td>${{row.node}}</td>
        <td><span class="pill">${{payloadLabel(row.payload_bytes)}}</span></td>
        <td>${{row.runs}}</td>
        <td>${{row.http_req_duration_p95_avg.toFixed(2)}}</td>
        <td>${{row.http_reqs_rate_avg.toFixed(2)}}</td>
        <td>${{(row.http_req_failed_rate_avg * 100).toFixed(4)}}</td>
        <td>${{(row.decrypt_mismatch_rate_avg * 100).toFixed(4)}}</td>
      </tr>
    `)
    .join('');

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Biblioteka</th>
          <th>Payload</th>
          <th>Liczba uruchomien</th>
          <th>p95 [ms]</th>
          <th>Throughput [req/s]</th>
          <th>Fail [%]</th>
          <th>Mismatch [%]</th>
        </tr>
      </thead>
      <tbody>${{bodyRows}}</tbody>
    </table>
  `;
}}

function renderPerLibraryTable() {{
  if (activeTestType !== 'stability' || !activeLibrary) {{
    document.getElementById('perLibraryTableCard').classList.add('hidden');
    return;
  }}
  
  document.getElementById('perLibraryTableCard').classList.remove('hidden');
  const source = rowsForActiveType();
  const container = document.getElementById('perLibraryTableContainer');

  if (!source.length) {{
    container.innerHTML = '<p class="empty">Brak danych dla wybranej biblioteki.</p>';
    return;
  }}

  const bodyRows = source
    .sort((a, b) => (a.payload_bytes - b.payload_bytes) || (a.repeat - b.repeat))
    .map((row) => `
      <tr>
        <td>Repeat ${{row.repeat}}</td>
        <td><span class="pill">${{payloadLabel(row.payload_bytes)}}</span></td>
        <td>${{row.iterations_avg.toFixed(0)}}</td>
        <td>${{row.http_req_duration_p95_avg.toFixed(2)}}</td>
        <td>${{row.http_reqs_rate_avg.toFixed(2)}}</td>
        <td>${{(row.http_req_failed_rate_avg * 100).toFixed(4)}}</td>
        <td>${{(row.decrypt_mismatch_rate_avg * 100).toFixed(4)}}</td>
      </tr>
    `)
    .join('');

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Run</th>
          <th>Payload</th>
          <th>Iteracje</th>
          <th>p95 [ms]</th>
          <th>Throughput [req/s]</th>
          <th>Fail [%]</th>
          <th>Mismatch [%]</th>
        </tr>
      </thead>
      <tbody>${{bodyRows}}</tbody>
    </table>
  `;
}}

function buildToggle() {{
  const host = document.getElementById('testTypeToggle');
  host.innerHTML = '';

  Object.keys(testTypeLabels).forEach((type) => {{
    const button = document.createElement('button');
    button.className = `toggle ${{type === activeTestType ? 'active' : ''}}`;
    button.textContent = testTypeLabels[type];
    button.onclick = () => {{
      activeTestType = type;
      activeLibrary = null;
      refresh();
    }};
    host.appendChild(button);
  }});
}}

function buildLibrarySelector() {{
  const host = document.getElementById('librarySelector');
  host.innerHTML = '';
  
  if (activeTestType !== 'stability') {{
    host.innerHTML = '';
    return;
  }}

  const label = document.createElement('label');
  label.textContent = 'Biblioteka:';
  host.appendChild(label);
  
  const select = document.createElement('select');
  select.id = 'librarySelect';
  
  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = 'Wszystkie biblioteki';
  select.appendChild(allOption);
  
  libraries.forEach((lib) => {{
    const option = document.createElement('option');
    option.value = lib;
    option.textContent = lib;
    select.appendChild(option);
  }});
  
  select.value = activeLibrary || '';
  select.onchange = (e) => {{
    activeLibrary = e.target.value || null;
    refresh();
  }};
  
  host.appendChild(select);
}}

let p95Chart;
let throughputChart;
let failChart;

function renderCharts() {{
  const commonOptions = {{
    responsive: true,
    maintainAspectRatio: true,
    plugins: {{ legend: {{ position: 'top' }} }},
    scales: {{ y: {{ beginAtZero: true }} }},
  }};

  const p95Data = chartDataForMetric('http_req_duration_p95_avg');
  const throughputData = chartDataForMetric('http_reqs_rate_avg');
  const failData = chartDataForMetric('http_req_failed_rate_avg', (value) => value * 100.0);

  if (p95Chart) p95Chart.destroy();
  if (throughputChart) throughputChart.destroy();
  if (failChart) failChart.destroy();

  p95Chart = new Chart(document.getElementById('p95Chart'), {{
    type: 'bar',
    data: p95Data,
    options: commonOptions,
  }});

  throughputChart = new Chart(document.getElementById('throughputChart'), {{
    type: 'bar',
    data: throughputData,
    options: commonOptions,
  }});

  failChart = new Chart(document.getElementById('failChart'), {{
    type: 'bar',
    data: failData,
    options: commonOptions,
  }});
}}

function refresh() {{
  buildToggle();
  buildLibrarySelector();
  fillOverviewCards();
  renderCharts();
  renderTable();
  renderPerLibraryTable();
}}

refresh();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description='Build benchmark HTML dashboard from k6 summary JSON files.')
    parser.add_argument('--results-dir', default='perf/results', help='Directory with *-summary.json files.')
    parser.add_argument('--output', default='perf/dashboard/index.html', help='Output HTML file path.')
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    rows = load_summaries(results_dir)
    aggregated_rows = aggregate_rows(rows)

    html = to_html(aggregated_rows, raw_rows=rows)
    output_file.write_text(html, encoding='utf-8')

    print(f'Wrote dashboard: {output_file}')


if __name__ == '__main__':
    main()
