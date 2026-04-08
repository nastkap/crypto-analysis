#!/usr/bin/env python3
"""
Skrypt do skanowania wszystkich obrazów Docker za pomocą Trivy
i generowania raportu podatności
"""

import subprocess
import json
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

def find_trivy():
    """Szuka Trivy w typowych lokalizacjach"""
    # Lista lokalizacji do sprawdzenia
    possible_paths = [
        # Windows temp directory
        Path(os.environ.get("TEMP", "")) / "trivy" / "trivy.exe",
        Path(os.environ.get("APPDATA", "")) / ".." / "Local" / "Temp" / "trivy" / "trivy.exe",
        Path(os.path.expanduser("~")) / "AppData" / "Local" / "Temp" / "trivy" / "trivy.exe",
        # Direct PATH check
        shutil.which("trivy"),
        shutil.which("trivy.exe"),
    ]
    
    for path in possible_paths:
        if path and isinstance(path, Path):
            if path.exists():
                return str(path)
        elif path and isinstance(path, str) and Path(path).exists():
            return path
    
    return None

def run_trivy_scan(trivy_cmd, image_name, severity="CRITICAL,HIGH"):
    """Uruchomia Trivy i zwraca wynik JSON"""
    cmd = [
        trivy_cmd, "image", image_name,
        "--severity", severity,
        "--format", "json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0 or result.returncode == 1:  # 1 = found vulnerabilities
            return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f" Błąd parsowania JSON dla {image_name}")
        return None
    except Exception as e:
        print(f" Błąd: {e}")
        return None

def analyze_results(trivy_cmd, images):
    """Analizuje wyniki skanowania i generuje raport"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "images": {}
    }
    
    all_critical = 0
    all_high = 0
    
    for image in images:
        print(f"\n Skanowanie: {image}...")
        data = run_trivy_scan(trivy_cmd, image)
        
        if not data:
            continue
        
        # Zliczanie zagrożeń
        critical_count = 0
        high_count = 0
        
        if "Results" in data:
            for result in data["Results"]:
                if "Misconfigurations" in result:
                    for misc in result["Misconfigurations"]:
                        if misc.get("Severity") == "CRITICAL":
                            critical_count += 1
                        elif misc.get("Severity") == "HIGH":
                            high_count += 1
                
                if "Vulnerabilities" in result:
                    for vuln in result["Vulnerabilities"]:
                        if vuln.get("Severity") == "CRITICAL":
                            critical_count += 1
                        elif vuln.get("Severity") == "HIGH":
                            high_count += 1
        
        report["images"][image] = {
            "critical": critical_count,
            "high": high_count,
            "status": "✅ PASS" if critical_count == 0 else "❌ FAIL"
        }
        
        all_critical += critical_count
        all_high += high_count
        
        severity_badge = "✅" if critical_count == 0 else "❌"
        print(f"  {severity_badge} CRITICAL: {critical_count}, HIGH: {high_count}")
    
    report["summary"] = {
        "total_critical": all_critical,
        "total_high": all_high,
        "overall_status": "PASS" if all_critical == 0 else "FAIL"
    }
    
    return report

def print_summary(report):
    """Wyświetla podsumowanie raportu"""
    print("\n" + "="*60)
    print("PODSUMOWANIE SKANOWANIA PODATNOŚCI (WARUNEK 4)")
    print("="*60)
    
    for image, results in report["images"].items():
        status = results["status"]
        print(f"\n{status} {image}")
        print(f"   CRITICAL: {results['critical']}, HIGH: {results['high']}")
    
    print("\n" + "-"*60)
    print(f"Łączne zagrożenia:")
    print(f"  CRITICAL: {report['summary']['total_critical']}")
    print(f"  HIGH:     {report['summary']['total_high']}")
    print(f"\nStatus: {report['summary']['overall_status']}")
    print("="*60)

if __name__ == "__main__":
    images = [
        "nastap/controller:latest",
        "nastap/crypto:latest",
        "nastap/pycryptodome:latest",
        "nastap/openssl:latest",
        "nastap/cryptopp:latest",
    ]
    
    # Znalezienie Trivy
    trivy_cmd = find_trivy()
    if not trivy_cmd:
        print("Trivy nie znaleziony w typowych lokalizacjach")
        print("Pobierz Trivy z: https://trivy.dev/")
        print("   lub zainstaluj: choco install trivy (Windows) / brew install trivy (macOS)")
        sys.exit(1)
    
    print(f"Znaleziono Trivy: {trivy_cmd}\n")
    print("Rozpoczęcie skanowania podatności...\n")
    
    report = analyze_results(trivy_cmd, images)
    print_summary(report)
    
    # Zapis raportu JSON
    output_file = "trivy_report.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nRaport zapisany do: {output_file}")
