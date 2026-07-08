#!/usr/bin/env python3
import psycopg2

try:
    with psycopg2.connect(host="127.0.0.1", port=5433, dbname="benchmark", user="benchmark", password="benchmark") as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS k6_load_results;")
            conn.commit()
            print(" Tabela k6_load_results usunięta!")
except Exception as e:
    print(f" Błąd: {e}")
