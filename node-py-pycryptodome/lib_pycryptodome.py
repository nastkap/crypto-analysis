import os
from Crypto.PublicKey import ECC
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class ECIES:
    def __init__(self):
        """
        Inicjalizacja systemu w PyCryptodome. Wybieramy krzywą NIST P-256.
        """
        self.curve_name = 'P-256'

    def generate_keys(self):

        private_key = ECC.generate(curve=self.curve_name)
        public_key = private_key.public_key()
        return private_key, public_key

    def _derive_shared_key(self, private_key, peer_public_key):
        """KEM: Uzgadnianie klucza (ECDH + HKDF)."""

        shared_point = peer_public_key.pointQ * private_key.d


        shared_secret = int(shared_point.x).to_bytes(32, byteorder='big')

        # 2. HKDF
        derived_key = HKDF(
            master=shared_secret,
            key_len=32,
            salt=b'',
            hashmod=SHA256,
            context=b'ecies-handshake'
        )
        return derived_key

    def encrypt(self, receiver_public_key, plaintext):
        """Szyfrowanie: Zwraca (ephemeral_pub_bytes, nonce, ciphertext)."""
        ephemeral_priv, ephemeral_pub = self.generate_keys()
        aes_key = self._derive_shared_key(ephemeral_priv, receiver_public_key)

        # AES-GCM
        nonce = get_random_bytes(12)
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)

        # PyCryptodome zwraca osobno szyfrogram i tag (plombę bezpieczeństwa)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))

        # Łączymy je, aby zachować zgodność z formatem pierwszej biblioteki
        full_ciphertext = ciphertext + tag

        # Eksport klucza publicznego do formatu PEM
        ephemeral_pub_string = ephemeral_pub.export_key(format='PEM')
        ephemeral_pub_bytes = ephemeral_pub_string.encode('utf-8') if isinstance(ephemeral_pub_string, str) else ephemeral_pub_string

        return ephemeral_pub_bytes, nonce, full_ciphertext

    def decrypt(self, receiver_private_key, package):
        """Deszyfrowanie ECIES."""
        ephemeral_pub_bytes, nonce, full_ciphertext = package

        # 1. Odtworzenie klucza publicznego nadawcy z bajtów

        ephemeral_pub_key = ECC.import_key(ephemeral_pub_bytes.decode('utf-8'))

        # 2. Ponowne uzgodnienie tego samego klucza AES (KEM)
        aes_key = self._derive_shared_key(receiver_private_key, ephemeral_pub_key)

        # 3. Deszyfrowanie
        # Rozdzielamy szyfrogram i tag (ostatnie 16 bajtów)
        tag = full_ciphertext[-16:]
        ciphertext = full_ciphertext[:-16]

        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        try:
            # decrypt_and_verify sprawdza integralność na podstawie tagu
            plaintext_bytes = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext_bytes.decode('utf-8')
        except ValueError as e:
            return f"[BŁĄD DEKRYPCJI] Nieprawidłowy klucz lub uszkodzone dane: {e}"