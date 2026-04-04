import csv
import io
import json
import os
import uuid
from typing import Any

import redis as redis_lib

BROKER_URL = os.environ.get("BROKER_URL", "redis://message-broker:6379")

# Znane węzły szyfrujące (klucze muszą zgadzać się z NODE_NAME w każdym serwisie)
NODES: list[str] = [
    "Python_Cryptography",
    "Python_PyCryptodome",
    "CPP_OpenSSL",
    "CPP_CryptoPP",
]


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(BROKER_URL, decode_responses=True)


def run_node_benchmark(
    node_name: str,
    message: str,
    iterations: int,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Wysyła zadania do węzła przez kolejki Redis i zbiera wyniki."""
    r = _get_redis()

    # Pobierz klucz publiczny węzła ze skrzynki Redis
    pub_key_pem: str | None = r.get(f"pubkey:{node_name}")
    if not pub_key_pem:
        raise RuntimeError(
            f"Węzeł '{node_name}' nie jest zarejestrowany w Redis. "
            "Sprawdź czy serwis jest uruchomiony."
        )

    results: list[dict[str, Any]] = []

    for i in range(iterations):
        # ---- Zadanie: szyfrowanie ----
        enc_task_id = str(uuid.uuid4())
        enc_task = {
            "task_id": enc_task_id,
            "type": "encrypt",
            "message": message,
            "receiver_public_key_pem": pub_key_pem,
        }
        r.lpush(f"tasks:{node_name}", json.dumps(enc_task))

        enc_item = r.brpop(f"results:{enc_task_id}", timeout=timeout)
        if not enc_item:
            raise TimeoutError(f"[{node_name}] iteracja {i+1}: brak odpowiedzi na szyfrowanie")
        enc_result = json.loads(enc_item[1])
        t_encrypt_ms: float = enc_result["execution_time_ms"]
        package: dict = enc_result["package"]

        # Zaszyfrowany pakiet jest teraz w Redis (wynik właśnie przyszedł przez kolejkę)

        # ---- Zadanie: deszyfrowanie ----
        dec_task_id = str(uuid.uuid4())
        dec_task = {"task_id": dec_task_id, "type": "decrypt", **package}
        r.lpush(f"tasks:{node_name}", json.dumps(dec_task))

        dec_item = r.brpop(f"results:{dec_task_id}", timeout=timeout)
        if not dec_item:
            raise TimeoutError(f"[{node_name}] iteracja {i+1}: brak odpowiedzi na deszyfrowanie")
        dec_result = json.loads(dec_item[1])
        t_decrypt_ms: float = dec_result["execution_time_ms"]
        decrypted: str = dec_result["decrypted_message"]

        if decrypted != message:
            raise ValueError(
                f"[{node_name}] iteracja {i+1}: błąd deszyfrowania! "
                f"Otrzymano: '{decrypted}'"
            )

        results.append({
            "Biblioteka": node_name,
            "Iteracja":   i + 1,
            "Encrypt_ms": t_encrypt_ms,
            "Decrypt_ms": t_decrypt_ms,
            "Total_ms":   t_encrypt_ms + t_decrypt_ms,
        })

    return results


def run_full_benchmark(
    message: str,
    iterations: int,
    selected_nodes: list[str] | None = None,
) -> list[dict[str, Any]]:
    nodes = selected_nodes if selected_nodes is not None else NODES

    all_results: list[dict[str, Any]] = []
    for node_name in nodes:
        node_results = run_node_benchmark(node_name, message, iterations)
        all_results.extend(node_results)

    return all_results


def results_to_csv(results: list[dict[str, Any]]) -> str:
    """Konwertuje wyniki do formatu CSV (separator ';', dziesiętny ',')."""
    if not results:
        return ""
    output = io.StringIO()
    fieldnames = ["Biblioteka", "Iteracja", "Encrypt_ms", "Decrypt_ms", "Total_ms"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    for row in results:
        formatted = dict(row)
        for key in ("Encrypt_ms", "Decrypt_ms", "Total_ms"):
            formatted[key] = str(formatted[key]).replace(".", ",")
        writer.writerow(formatted)
    return output.getvalue()