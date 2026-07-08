import json
import psycopg2
import argparse
import os
from datetime import datetime, timedelta

def calculate_percentile(values, percentile):
    """Oblicz percentyl z listy wartości"""
    if not values:
        return 0
    sorted_vals = sorted(values)
    index = (percentile / 100.0) * (len(sorted_vals) - 1)
    lower_idx = int(index)
    upper_idx = min(lower_idx + 1, len(sorted_vals) - 1)
    
    if lower_idx == upper_idx:
        return float(sorted_vals[lower_idx])
    
    # Interpolacja liniowa
    weight = index - lower_idx
    return sorted_vals[lower_idx] * (1 - weight) + sorted_vals[upper_idx] * weight

def import_raw_results(json_file, test_type, library_name, data_size):
    try:
        http_durations = []
        encrypt_durations = []
        decrypt_durations = []
        total_reqs = 0
        failed_reqs = 0
        
        # Dla S3: zbierz dane z czasami dla podziału na fazy
        if test_type == "ScalabilityS3":
            metric_points_by_time = []  # Lista (timestamp, metric, value)
            min_timestamp = None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        point = json.loads(line)
                        if point.get("type") == "Point":
                            metric = point.get("metric")
                            val = point.get("data", {}).get("value", 0)
                            time_str = point.get("data", {}).get("time", "")
                            
                            if time_str:
                                try:
                                    ts = datetime.fromisoformat(time_str.replace('+02:00', ''))
                                    if min_timestamp is None:
                                        min_timestamp = ts
                                    
                                    if metric == "http_req_duration":
                                        http_durations.append(val)
                                        metric_points_by_time.append((ts, "http_req_duration", val))
                                    elif metric == "encrypt_duration_ms":
                                        encrypt_durations.append(val)
                                        metric_points_by_time.append((ts, "encrypt_duration_ms", val))
                                    elif metric == "decrypt_duration_ms":
                                        decrypt_durations.append(val)
                                        metric_points_by_time.append((ts, "decrypt_duration_ms", val))
                                    elif metric == "http_reqs":
                                        total_reqs += val
                                    elif metric == "http_req_failed":
                                        failed_reqs += val
                                except:
                                    pass
                    except json.JSONDecodeError:
                        continue
            
            # Zapis 4 faz dla S3
            if min_timestamp and len(http_durations) > 0:
                phases = [
                    ("Phase 1 (1 VU)", min_timestamp, min_timestamp + timedelta(seconds=5)),
                    ("Phase 2 (5 VU)", min_timestamp + timedelta(seconds=5), min_timestamp + timedelta(seconds=35)),
                    ("Phase 3 (10 VU)", min_timestamp + timedelta(seconds=35), min_timestamp + timedelta(seconds=95)),
                    ("Phase 4 (25 VU)", min_timestamp + timedelta(seconds=95), min_timestamp + timedelta(seconds=185)),
                ]
                
                with psycopg2.connect(host="127.0.0.1", port=5433, dbname="benchmark", user="benchmark", password="benchmark") as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS k6_load_results (
                                id SERIAL PRIMARY KEY,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                test_type VARCHAR(50),
                                library_name VARCHAR(50),
                                data_size_mb INT,
                                phase_name VARCHAR(50),
                                avg_duration_ms FLOAT,
                                avg_encrypt_ms FLOAT,
                                avg_decrypt_ms FLOAT,
                                p50_ms FLOAT,
                                p95_ms FLOAT,
                                p99_ms FLOAT,
                                requests_per_sec FLOAT,
                                error_rate FLOAT,
                                total_requests INT
                            )
                        """)
                        
                        for phase_name, phase_start, phase_end in phases:
                            phase_durations = [v for t, m, v in metric_points_by_time if m == "http_req_duration" and phase_start <= t < phase_end]
                            phase_encrypt = [v for t, m, v in metric_points_by_time if m == "encrypt_duration_ms" and phase_start <= t < phase_end]
                            phase_decrypt = [v for t, m, v in metric_points_by_time if m == "decrypt_duration_ms" and phase_start <= t < phase_end]
                            
                            if phase_durations:
                                avg_duration = sum(phase_durations) / len(phase_durations)
                                p50 = calculate_percentile(phase_durations, 50)
                                p95 = calculate_percentile(phase_durations, 95)
                                p99 = calculate_percentile(phase_durations, 99)
                                avg_encrypt = sum(phase_encrypt) / len(phase_encrypt) if phase_encrypt else 0
                                avg_decrypt = sum(phase_decrypt) / len(phase_decrypt) if phase_decrypt else 0
                                
                                cur.execute("""
                                    INSERT INTO k6_load_results 
                                    (test_type, library_name, data_size_mb, phase_name, avg_duration_ms, avg_encrypt_ms, avg_decrypt_ms, p50_ms, p95_ms, p99_ms, requests_per_sec, error_rate, total_requests)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (test_type, library_name, data_size, phase_name, avg_duration, avg_encrypt, avg_decrypt, p50, p95, p99, 0, 0, len(phase_durations)))
                        
                        conn.commit()
                        print(f"S3 Sukces: {library_name} | 4 fazy zapisane")
            return
        
        # Standard import (dla S1, S2, S4, S5)
        with open(json_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    point = json.loads(line)
                    if point.get("type") == "Point":
                        metric = point.get("metric")
                        val = point.get("data", {}).get("value", 0)
                        
                        if metric == "http_req_duration":
                            http_durations.append(val)
                        elif metric == "encrypt_duration_ms":
                            encrypt_durations.append(val)
                        elif metric == "decrypt_duration_ms":
                            decrypt_durations.append(val)
                        elif metric == "http_reqs":
                            total_reqs += val
                        elif metric == "http_req_failed":
                            failed_reqs += val
                except json.JSONDecodeError:
                    continue

        # Oblicz średnią i percentyle
        avg_duration = sum(http_durations) / len(http_durations) if http_durations else 0
        p50_duration = calculate_percentile(http_durations, 50)
        p95_duration = calculate_percentile(http_durations, 95)
        p99_duration = calculate_percentile(http_durations, 99)
        
        # Oblicz średnie dla ENCRYPT i DECRYPT osobno
        avg_encrypt = sum(encrypt_durations) / len(encrypt_durations) if encrypt_durations else 0
        avg_decrypt = sum(decrypt_durations) / len(decrypt_durations) if decrypt_durations else 0
        
        error_rate = (failed_reqs / total_reqs) if total_reqs > 0 else 0
        reqs_per_sec = 0

        # Zapis do bazy
        with psycopg2.connect(host="127.0.0.1", port=5433, dbname="benchmark", user="benchmark", password="benchmark") as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS k6_load_results (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        test_type VARCHAR(50),
                        library_name VARCHAR(50),
                        data_size_mb INT,
                        phase_name VARCHAR(50),
                        avg_duration_ms FLOAT,
                        avg_encrypt_ms FLOAT,
                        avg_decrypt_ms FLOAT,
                        p50_ms FLOAT,
                        p95_ms FLOAT,
                        p99_ms FLOAT,
                        requests_per_sec FLOAT,
                        error_rate FLOAT,
                        total_requests INT
                    )
                """)
                cur.execute("""
                    INSERT INTO k6_load_results 
                    (test_type, library_name, data_size_mb, avg_duration_ms, avg_encrypt_ms, avg_decrypt_ms, p50_ms, p95_ms, p99_ms, requests_per_sec, error_rate, total_requests)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (test_type, library_name, data_size, avg_duration, avg_encrypt, avg_decrypt, p50_duration, p95_duration, p99_duration, reqs_per_sec, error_rate, total_reqs))
                conn.commit()
                print(f"Sukces: {library_name} | {test_type} | {data_size}MB | Encrypt: {avg_encrypt:.2f}ms | Decrypt: {avg_decrypt:.2f}ms")

    except Exception as e:
        print(f"BŁĄD ZAPISU ({os.path.basename(json_file)}): {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--lib", required=True)
    parser.add_argument("--size", required=True, type=int)
    
    args = parser.parse_args()
    import_raw_results(args.file, args.type, args.lib, args.size)