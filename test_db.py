import psycopg2

try:
    conn = psycopg2.connect(host='127.0.0.1', port=5433, dbname='benchmark', user='benchmark', password='benchmark')
    cur = conn.cursor()
    
    # Query z fazami
    query = """
    SELECT
      library_name,
      phase_name,
      ROUND(p95_ms::numeric, 0) as p95_latency_ms
    FROM k6_load_results
    WHERE test_type = 'ScalabilityS3'
    ORDER BY library_name, phase_name;
    """
    
    cur.execute(query)
    print("Phase Results:")
    print("=" * 60)
    for row in cur.fetchall():
        print(row)
    
    cur.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
