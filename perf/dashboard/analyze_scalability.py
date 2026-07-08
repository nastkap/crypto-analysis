#!/usr/bin/env python3
"""
Analyze Scalability Test Results - Extract data from PostgreSQL and generate charts
showing latency degradation across VU phases
"""

import psycopg2
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# PostgreSQL connection
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "benchmark",
    "user": "benchmark",
    "password": "benchmark"
}

def get_scalability_data():
    """Extract scalability test results from database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get all scalability tests
    query = """
    SELECT 
        library_name,
        data_size_mb,
        avg_duration_ms,
        p50_ms,
        p95_ms,
        p99_ms,
        requests_per_sec,
        error_rate,
        timestamp
    FROM k6_load_results
    WHERE test_type = 'Scalability'
    ORDER BY library_name, timestamp
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return results

def parse_scalability_phases(raw_file):
    """Parse k6 raw JSON to extract per-phase metrics"""
    phases = {
        'Phase 1 (1 VU)': [],
        'Phase 2 (5 VU)': [],
        'Phase 3 (15 VU)': [],
        'Phase 4 (30 VU)': []
    }
    
    try:
        with open(raw_file, 'r') as f:
            for line in f:
                data = json.loads(line)
                if data.get('type') == 'Point' and 'metric' in data:
                    ts = data.get('data', {}).get('time', 0)
                    
                    # Determine phase based on timestamp
                    # Phase 1: 0-5s, Phase 2: 5-35s, Phase 3: 35-95s, Phase 4: 95-185s
                    if ts < 5:
                        phase = 'Phase 1 (1 VU)'
                    elif ts < 35:
                        phase = 'Phase 2 (5 VU)'
                    elif ts < 95:
                        phase = 'Phase 3 (15 VU)'
                    else:
                        phase = 'Phase 4 (30 VU)'
                    
                    if data['metric'] == 'http_req_duration' and data.get('data', {}).get('value'):
                        phases[phase].append(data['data']['value'])
    except Exception as e:
        print(f"Error parsing {raw_file}: {e}")
    
    return phases

def generate_report(raw_files_dir="perf/results"):
    """Generate scalability analysis report"""
    results_dir = Path(raw_files_dir)
    scalability_files = sorted(results_dir.glob("*-scalability-*-raw.json"))
    
    if not scalability_files:
        print(" No scalability test files found!")
        return
    
    print(f" Found {len(scalability_files)} scalability test files\n")
    
    # Parse each file and extract phase data
    library_data = {}
    
    for raw_file in scalability_files:
        filename = raw_file.name
        # Extract library name: "CPP_OpenSSL-scalability-..."
        lib_name = filename.split('-')[0]
        
        print(f" Analyzing {lib_name}...")
        phases = parse_scalability_phases(raw_file)
        
        library_data[lib_name] = {
            'phases': phases,
            'file': str(raw_file)
        }
        
        # Print summary
        for phase_name, durations in phases.items():
            if durations:
                avg_ms = np.mean(durations)
                p95_ms = np.percentile(durations, 95)
                print(f"  {phase_name}: avg={avg_ms:.0f}ms, p95={p95_ms:.0f}ms, n={len(durations)}")
            else:
                print(f"  {phase_name}: no data")
    
    return library_data

def plot_scalability_comparison(library_data, output_file="scalability_analysis.png"):
    """Generate comparison chart for scalability"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Scalability Test Analysis - Latency Degradation Across VU Phases', 
                 fontsize=16, fontweight='bold')
    
    libraries = list(library_data.keys())
    colors = plt.cm.Set3(np.linspace(0, 1, len(libraries)))
    phases = ['Phase 1 (1 VU)', 'Phase 2 (5 VU)', 'Phase 3 (15 VU)', 'Phase 4 (30 VU)']
    
    # Chart 1: Average Latency by Phase
    ax = axes[0, 0]
    x = np.arange(len(phases))
    width = 0.2
    
    for i, lib in enumerate(libraries):
        avgs = []
        for phase in phases:
            durations = library_data[lib]['phases'].get(phase, [])
            avgs.append(np.mean(durations) if durations else 0)
        ax.bar(x + i*width, avgs, width, label=lib, color=colors[i])
    
    ax.set_xlabel('Test Phase')
    ax.set_ylabel('Avg Latency (ms)')
    ax.set_title('Average Latency by Phase')
    ax.set_xticks(x + width)
    ax.set_xticklabels(phases, rotation=15, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Chart 2: P95 Latency by Phase
    ax = axes[0, 1]
    for i, lib in enumerate(libraries):
        p95s = []
        for phase in phases:
            durations = library_data[lib]['phases'].get(phase, [])
            p95s.append(np.percentile(durations, 95) if durations else 0)
        ax.bar(x + i*width, p95s, width, label=lib, color=colors[i])
    
    ax.set_xlabel('Test Phase')
    ax.set_ylabel('P95 Latency (ms)')
    ax.set_title('P95 Latency by Phase (SLA: < 5000ms)')
    ax.axhline(y=5000, color='red', linestyle='--', label='SLA Threshold', linewidth=2)
    ax.set_xticks(x + width)
    ax.set_xticklabels(phases, rotation=15, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Chart 3: Scalability Factor (Phase 4 / Phase 1)
    ax = axes[1, 0]
    factors = []
    for lib in libraries:
        phase1_durations = library_data[lib]['phases']['Phase 1 (1 VU)']
        phase4_durations = library_data[lib]['phases']['Phase 4 (30 VU)']
        
        if phase1_durations and phase4_durations:
            p1_avg = np.mean(phase1_durations)
            p4_avg = np.mean(phase4_durations)
            factor = p4_avg / p1_avg if p1_avg > 0 else 0
            factors.append(factor)
        else:
            factors.append(0)
    
    bars = ax.bar(libraries, factors, color=colors)
    ax.axhline(y=5.0, color='orange', linestyle='--', label='Acceptable (< 5.0)', linewidth=2)
    ax.axhline(y=10.0, color='red', linestyle='--', label='Bad (> 10.0)', linewidth=2)
    ax.set_ylabel('Scalability Factor (Phase4/Phase1)')
    ax.set_title('Scalability Factor - Linear Scaling = 1.0x')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (lib, factor) in enumerate(zip(libraries, factors)):
        ax.text(i, factor + 0.5, f'{factor:.1f}x', ha='center', fontweight='bold')
    
    # Chart 4: Box plot of Phase 4 distribution
    ax = axes[1, 1]
    phase4_data = []
    phase4_labels = []
    for lib in libraries:
        durations = library_data[lib]['phases']['Phase 4 (30 VU)']
        if durations:
            phase4_data.append(durations)
            phase4_labels.append(lib)
    
    if phase4_data:
        bp = ax.boxplot(phase4_data, labels=phase4_labels, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors[:len(phase4_data)]):
            patch.set_facecolor(color)
        ax.axhline(y=5000, color='red', linestyle='--', label='SLA: 5000ms', linewidth=2)
        ax.set_ylabel('Latency (ms)')
        ax.set_title('Phase 4 (30 VU) - Latency Distribution')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n Chart saved to: {output_file}")
    plt.show()

if __name__ == "__main__":
    print("🔍 Scalability Analysis Tool\n")
    
    # Generate report from raw JSON files
    library_data = generate_report()
    
    if library_data:
        print("\n" + "="*60)
        print(" SCALABILITY ANALYSIS SUMMARY")
        print("="*60)
        
        for lib, data in library_data.items():
            phase1_durations = data['phases']['Phase 1 (1 VU)']
            phase4_durations = data['phases']['Phase 4 (30 VU)']
            
            if phase1_durations and phase4_durations:
                p1_avg = np.mean(phase1_durations)
                p4_avg = np.mean(phase4_durations)
                factor = p4_avg / p1_avg if p1_avg > 0 else 0
                
                status = " GOOD" if factor < 5 else "⚠️ MEDIUM" if factor < 10 else "❌ POOR"
                print(f"\n{lib}: {status}")
                print(f"  Phase 1 (1 VU):  {p1_avg:.0f}ms")
                print(f"  Phase 4 (30 VU): {p4_avg:.0f}ms")
                print(f"  Scalability Factor: {factor:.1f}x")
        
        # Generate visualization
        plot_scalability_comparison(library_data)
    else:
        print(" No data to analyze")
