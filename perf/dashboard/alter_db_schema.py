#!/usr/bin/env python3
import psycopg2

try:
    with psycopg2.connect(host="127.0.0.1", port=5433, dbname="benchmark", user="benchmark", password="benchmark") as conn:
        with conn.cursor() as cur:
            # Dodaj kolumny dla encrypt i decrypt jeśli ich brakuje
            cur.execute("""
                ALTER TABLE k6_load_results
                ADD COLUMN IF NOT EXISTS avg_encrypt_ms FLOAT;
            """)
            print(" Kolumna avg_encrypt_ms dodana")
            
            cur.execute("""
                ALTER TABLE k6_load_results
                ADD COLUMN IF NOT EXISTS avg_decrypt_ms FLOAT;
            """)
            print(" Kolumna avg_decrypt_ms dodana")
            
            conn.commit()
            print(" Schemat bazy zaktualizowany!")
except Exception as e:
    print(f" Błąd: {e}")
