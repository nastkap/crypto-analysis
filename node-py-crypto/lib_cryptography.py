import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class ECIES:
    def __init__(self):
        """
        Inicjalizacja systemu. Wybieramy krzywą NISTP-256.
        """
        self.curve = ec.SECP256R1()

    def generate_keys(self):
        private_key = ec.generate_private_key(self.curve)
        public_key = private_key.public_key()
        return private_key, public_key

    def _derive_shared_key(self, private_key, peer_public_key):
        """KEM: Uzgadnianie klucza (ECDH + HKDF)."""
        shared_secret = private_key.exchange(ec.ECDH(), peer_public_key)
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'ecies-handshake',
        ).derive(shared_secret)
        return derived_key

    def encrypt(self, receiver_public_key, plaintext):
        """Szyfrowanie: Zwraca (ephemeral_pub_bytes, nonce, ciphertext)."""
        ephemeral_priv, ephemeral_pub = self.generate_keys()
        aes_key = self._derive_shared_key(ephemeral_priv, receiver_public_key)

        aes = AESGCM(aes_key)
        nonce = os.urandom(12)
        ciphertext = aes.encrypt(nonce, plaintext.encode('utf-8'), None)

        ephemeral_pub_bytes = ephemeral_pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return ephemeral_pub_bytes, nonce, ciphertext

    def decrypt(self, receiver_private_key, package):
        """
        Deszyfrowanie ECIES.
        1. Odtwarza klucz publiczny nadawcy.
        2. Uzgadnia ten sam klucz AES (KEM).
        3. Odszyfrowuje treść (DEM).
        """
        ephemeral_pub_bytes, nonce, ciphertext = package

        # 1. Odtworzenie klucza publicznego nadawcy z bajtów
        ephemeral_pub_key = serialization.load_pem_public_key(ephemeral_pub_bytes)

        # 2. Ponowne uzgodnienie tego samego klucza AES
        # Odbiorca używa SWOJEGO klucza prywatnego i klucza publicznego NADAWCY (z paczki)
        aes_key = self._derive_shared_key(receiver_private_key, ephemeral_pub_key)

        # 3. Deszyfrowanie
        aes = AESGCM(aes_key)
        try:
            # AES-GCM sprawdza też integralność (czy nikt nie zmienił treści)
            plaintext_bytes = aes.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            return f"[BŁĄD DEKRYPCJI] Nieprawidłowy klucz lub uszkodzone dane: {e}"


if __name__ == "__main__":
    print("TEST")
    system = ECIES()

    # 1. Alice (Odbiorca) generuje swoje stałe klucze
    alice_priv, alice_pub = system.generate_keys()

    # 2. Bob (Nadawca) szyfruje wiadomość dla Alice
    wiadomosc = "To jest tajny projekt na zaliczenie!"
    print(f"1. Bob wysyła: '{wiadomosc}'")

    # Bob tworzy paczkę. Zauważ, że nie potrzebuje klucza prywatnego Alice!
    paczka = system.encrypt(alice_pub, wiadomosc)
    print(f"2. Przesyłana paczka (Szyfrogram + Klucz + Nonce)")

    # 3. Alice odbiera paczkę i deszyfruje
    odczytana = system.decrypt(alice_priv, paczka)
    print(f"3. Alice odczytała: '{odczytana}'")

    if odczytana == wiadomosc:
        print("[SUKCES] System działa poprawnie w obie strony!")
    else:
        print("[BŁĄD] Treści się różnią!")