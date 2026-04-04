import base64
import json
import os
import threading
import time

import redis as redis_lib
from Crypto.PublicKey import ECC
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from lib_pycryptodome import ECIES

NODE_NAME = os.environ.get("NODE_NAME", "Python_PyCryptodome")
BROKER_URL = os.environ.get("BROKER_URL", "redis://localhost:6379")

app = FastAPI(title="ECIES Node - Python PyCryptodome")
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
                receiver_pub = ECC.import_key(task["receiver_public_key_pem"])
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
        pub_pem = node_public_key.export_key(format="PEM")
        if not isinstance(pub_pem, str):
            pub_pem = pub_pem.decode("utf-8")
        r.set(f"pubkey:{NODE_NAME}", pub_pem)
        print(f"[{NODE_NAME}] Klucz publiczny zarejestrowany w Redis", flush=True)
    except Exception as exc:
        print(f"[{NODE_NAME}] Blad rejestracji w Redis: {exc}", flush=True)
    threading.Thread(target=_redis_worker, daemon=True).start()


class EncryptRequest(BaseModel):
    message: str
    receiver_public_key_pem: str


class DecryptRequest(BaseModel):
    ephemeral_pub_bytes_b64: str
    nonce_b64: str
    ciphertext_b64: str


@app.get("/")
def read_root():
    return {"status": "ok", "node": "Python-PyCryptodome", "message": "Mikroserwis dziala!"}


@app.get("/health")
def health_check():
    """Health check endpoint dla Docker health checks"""
    return {"status": "healthy", "node": "Python-PyCryptodome"}


@app.get("/public-key")
def get_public_key():
    pub_pem = node_public_key.export_key(format="PEM")
    return {"public_key_pem": pub_pem if isinstance(pub_pem, str) else pub_pem.decode("utf-8")}


@app.post("/encrypt")
def encrypt_message(req: EncryptRequest):
    try:
        start_time = time.perf_counter()
        receiver_pub = ECC.import_key(req.receiver_public_key_pem)
        eph_pub, nonce, ciphertext = crypto_system.encrypt(receiver_pub, req.message)
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "success",
            "execution_time_ms": execution_time_ms,
            "package": {
                "ephemeral_pub_bytes_b64": base64.b64encode(eph_pub).decode("utf-8"),
                "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
                "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/decrypt")
def decrypt_message(req: DecryptRequest):
    try:
        start_time = time.perf_counter()
        package = (
            base64.b64decode(req.ephemeral_pub_bytes_b64),
            base64.b64decode(req.nonce_b64),
            base64.b64decode(req.ciphertext_b64),
        )
        decrypted_text = crypto_system.decrypt(node_private_key, package)
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "success",
            "execution_time_ms": execution_time_ms,
            "decrypted_message": decrypted_text,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
