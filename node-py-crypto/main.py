import base64
import json
import os
import threading
import time

import redis as redis_lib
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from lib_cryptography import ECIES

NODE_NAME = os.environ.get("NODE_NAME", "Python_Cryptography")
BROKER_URL = os.environ.get("BROKER_URL", "redis://localhost:6379")

app = FastAPI(title="ECIES Node - Python Cryptography")
crypto_system = ECIES()

node_private_key, node_public_key = crypto_system.generate_keys()


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(BROKER_URL, decode_responses=True)


def _redis_worker() -> None:
    r = _get_redis()
    queue_key = f"tasks:{NODE_NAME}"
    print(f"[{NODE_NAME}] Worker Redis uruchomiony, nasluchuje: {queue_key}", flush=True)
    while True:
        try:
            item = r.brpop(queue_key, timeout=5)
            if item is None:
                continue
            _, task_json = item
            task = json.loads(task_json)
            task_id: str = task["task_id"]
            task_type: str = task["type"]

            if task_type == "encrypt":
                receiver_pub = serialization.load_pem_public_key(
                    task["receiver_public_key_pem"].encode("utf-8")
                )
                t0 = time.perf_counter()
                eph_pub, nonce, ciphertext = crypto_system.encrypt(receiver_pub, task["message"])
                execution_time_ms = (time.perf_counter() - t0) * 1000
                result = {
                    "status": "success",
                    "execution_time_ms": execution_time_ms,
                    "package": {
                        "ephemeral_pub_bytes_b64": base64.b64encode(eph_pub).decode("utf-8"),
                        "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
                        "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
                    },
                }
            elif task_type == "decrypt":
                package = (
                    base64.b64decode(task["ephemeral_pub_bytes_b64"]),
                    base64.b64decode(task["nonce_b64"]),
                    base64.b64decode(task["ciphertext_b64"]),
                )
                t0 = time.perf_counter()
                decrypted_text = crypto_system.decrypt(node_private_key, package)
                execution_time_ms = (time.perf_counter() - t0) * 1000
                result = {
                    "status": "success",
                    "execution_time_ms": execution_time_ms,
                    "decrypted_message": decrypted_text,
                }
            else:
                result = {"status": "error", "detail": f"Nieznany typ zadania: {task_type}"}

            r.lpush(f"results:{task_id}", json.dumps(result))
            r.expire(f"results:{task_id}", 60)
        except Exception as exc:
            print(f"[{NODE_NAME}] Worker blad: {exc}", flush=True)


@app.on_event("startup")
def startup_event() -> None:
    try:
        r = _get_redis()
        pub_bytes = node_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        r.set(f"pubkey:{NODE_NAME}", pub_bytes.decode("utf-8"))
        print(f"[{NODE_NAME}] Klucz publiczny zarejestrowany w Redis", flush=True)
    except Exception as exc:
        print(f"[{NODE_NAME}] Blad rejestracji w Redis: {exc}", flush=True)
    threading.Thread(target=_redis_worker, daemon=True).start()

# Modele danych (jak wyglądają paczki, które wysyłamy/odbieramy przez sieć)
class EncryptRequest(BaseModel):
    message: str
    receiver_public_key_pem: str

class DecryptRequest(BaseModel):
    ephemeral_pub_bytes_b64: str
    nonce_b64: str
    ciphertext_b64: str

@app.get("/")
def read_root():
    return {"status": "ok", "node": "Python-Cryptography", "message": "Mikroserwis dziala!"}

@app.get("/health")
def health_check():
    """Health check endpoint dla Docker health checks"""
    return {"status": "healthy", "node": "Python-Cryptography"}

@app.get("/public-key")
def get_public_key():
    """Zwraca klucz publiczny tego węzła, żeby inni wiedzieli jak do niego szyfrować."""
    pub_bytes = node_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return {"public_key_pem": pub_bytes.decode('utf-8')}

@app.post("/encrypt")
def encrypt_message(req: EncryptRequest):
    """Szyfruje wiadomość dla podanego odbiorcy i mierzy czas."""
    try:
        start_time = time.perf_counter()

        # Ładowanie klucza odbiorcy z tekstu PEM
        receiver_pub = serialization.load_pem_public_key(req.receiver_public_key_pem.encode('utf-8'))

        # Szyfrowanie
        eph_pub, nonce, ciphertext = crypto_system.encrypt(receiver_pub, req.message)

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Zwracamy paczkę zakodowaną w Base64 (bo JSON nie lubi surowych bajtów)
        return {
            "status": "success",
            "execution_time_ms": execution_time_ms,
            "package": {
                "ephemeral_pub_bytes_b64": base64.b64encode(eph_pub).decode('utf-8'),
                "nonce_b64": base64.b64encode(nonce).decode('utf-8'),
                "ciphertext_b64": base64.b64encode(ciphertext).decode('utf-8')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/decrypt")
def decrypt_message(req: DecryptRequest):
    """Deszyfruje paczkę używając klucza prywatnego tego węzła."""
    try:
        start_time = time.perf_counter()

        # Odkodowanie z Base64
        package = (
            base64.b64decode(req.ephemeral_pub_bytes_b64),
            base64.b64decode(req.nonce_b64),
            base64.b64decode(req.ciphertext_b64)
        )

        # Deszyfrowanie
        decrypted_text = crypto_system.decrypt(node_private_key, package)
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return {
            "status": "success",
            "execution_time_ms": execution_time_ms,
            "decrypted_message": decrypted_text
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))