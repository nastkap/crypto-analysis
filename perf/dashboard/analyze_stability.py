#!/usr/bin/env python3
"""
Analyze stability metrics from k6 stability tests.
Calculates:
  - Mean, StdDev, CoV (Coefficient of Variation)
  - Stability Score (0-100%)
  - Consistency Ratio (Min/Max)
"""

import json
import sys
import os
from pathlib import Path
from statistics import mean, stdev
from collections import defaultdict

def extract_avg_duration(json_file):
    """Extract average http_req_duration from k6 raw JSON Lines output."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            durations = []
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'Point' and data.get('metric') == 'http_req_duration':
                        durations.append(data['data']['value'])
                except json.JSONDecodeError:
                    continue
            
            if durations:
                return mean(durations)
    except Exception as e:
        print(f"Warning: Could not read {json_file}: {e}")
    return None

def calculate_stability_score(cov):
    """Calculate stability score based on Coefficient of Variation."""
    if cov < 5:
        return 100.0  # Very stable
    elif cov < 10:
        return (100 - (cov - 5) * 4)  # 100 -> 80%
    elif cov < 20:
        return (80 - (cov - 10) * 2)  # 80 -> 60%
    else:
        return max(0, 60 - (cov - 20))  # 60% -> 0%

def main():
    results_dir = Path("perf/results")
    
    # Group results by library
    library_runs = defaultdict(list)
    
    # Find all stability test files
    for f in sorted(results_dir.glob("*-stabilitys3-r*-*-raw.json")):
        # Parse filename: {Name}-stabilitys3-r{i}-{payload}-{timestamp}-raw.json
        parts = f.stem.replace('-raw', '').split('-')
        
        # Find library name (everything before 'stabilitys3')
        stability_idx = None
        for i, p in enumerate(parts):
            if p == 'stabilitys3':
                stability_idx = i
                break
        
        if stability_idx is None:
            continue
        
        library_name = '-'.join(parts[:stability_idx])
        avg_duration = extract_avg_duration(str(f))
        
        if avg_duration is not None:
            library_runs[library_name].append(avg_duration)
    
    # Calculate metrics
    print("\n" + "="*80)
    print("STABILITY TEST ANALYSIS - 10MB Payload (10 runs per library)")
    print("="*80 + "\n")
    
    results = {}
    
    for library in sorted(library_runs.keys()):
        runs = sorted(library_runs[library])
        
        if len(runs) < 2:
            print(f"  {library}: Only {len(runs)} run(s) - skipping (need at least 2)")
            continue
        
        # Calculate statistics
        avg = mean(runs)
        sd = stdev(runs)
        cov = (sd / avg) * 100  # Coefficient of Variation in %
        consistency = (min(runs) / max(runs))  # Min/Max ratio
        stability_score = calculate_stability_score(cov)
        
        # Determine status
        if consistency > 0.95:
            consistency_status = " Excellent"
        elif consistency > 0.85:
            consistency_status = " Acceptable"
        else:
            consistency_status = " Poor"
        
        if stability_score >= 80:
            stability_status = " Stable"
        elif stability_score >= 60:
            stability_status = "Moderate"
        else:
            stability_status = " Unstable"
        
        results[library] = {
            'runs': len(runs),
            'mean_ms': avg,
            'stdev_ms': sd,
            'cov_percent': cov,
            'min_ms': min(runs),
            'max_ms': max(runs),
            'consistency_ratio': consistency,
            'stability_score': stability_score
        }
        
        # Print results
        print(f"{library}")
        print(f"   Runs: {len(runs)}/10")
        print(f"   Mean:             {avg:8.2f} ms")
        print(f"   StdDev:           {sd:8.2f} ms")
        print(f"   CoV:              {cov:8.2f}%")
        print(f"   Min/Max:          {min(runs):8.2f} / {max(runs):8.2f} ms")
        print(f"   Consistency:      {consistency:8.4f} ({consistency_status})")
        print(f"   Stability Score:  {stability_score:6.1f}% ({stability_status})")
        print()
    
    # Summary ranking
    print("="*80)
    print("RANKING (by Stability Score)")
    print("="*80 + "\n")
    
    sorted_libs = sorted(results.items(), key=lambda x: x[1]['stability_score'], reverse=True)
    for rank, (library, metrics) in enumerate(sorted_libs, 1):
        print(f"{rank}. {library:<30} Score: {metrics['stability_score']:6.1f}%  CoV: {metrics['cov_percent']:6.2f}%")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
