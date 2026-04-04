#pragma once
#include <string>
#include <vector>
#include <stdexcept>
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/kdf.h>
#include <openssl/rand.h>
#include <openssl/params.h>
#include <openssl/pem.h>
#include <openssl/bio.h>
#include <openssl/core_names.h>

struct PackageOSSL {
    std::vector<unsigned char> ephemeral_pub;
    std::vector<unsigned char> nonce;
    std::vector<unsigned char> ciphertext;
    std::vector<unsigned char> tag; // OpenSSL rozdziela szyfrogram od tagu w GCM
};

class ECIES_OpenSSL {
public:
    EVP_PKEY* GenerateKey() {
        // Generowanie klucza NIST P-256
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
        EVP_PKEY_keygen_init(ctx);
        EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_X9_62_prime256v1);
        EVP_PKEY* pkey = NULL;
        EVP_PKEY_keygen(ctx, &pkey);
        EVP_PKEY_CTX_free(ctx);
        return pkey;
    }

    std::vector<unsigned char> DeriveSharedKey(EVP_PKEY* myPriv, EVP_PKEY* peerPub) {
        // 1. ECDH
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new(myPriv, NULL);
        EVP_PKEY_derive_init(ctx);
        EVP_PKEY_derive_set_peer(ctx, peerPub);

        size_t secretLen;
        EVP_PKEY_derive(ctx, NULL, &secretLen);
        std::vector<unsigned char> sharedSecret(secretLen);
        EVP_PKEY_derive(ctx, sharedSecret.data(), &secretLen);
        EVP_PKEY_CTX_free(ctx);

        // 2. HKDF (Zwracamy 32 bajty dla AES-256)
        EVP_KDF* kdf = EVP_KDF_fetch(NULL, "HKDF", NULL);
        EVP_KDF_CTX* kctx = EVP_KDF_CTX_new(kdf);
        EVP_KDF_free(kdf);

        std::vector<unsigned char> aesKey(32);
        OSSL_PARAM params[4];
        params[0] = OSSL_PARAM_construct_utf8_string(OSSL_KDF_PARAM_DIGEST, (char*)"SHA256", 0);
        params[1] = OSSL_PARAM_construct_octet_string(OSSL_KDF_PARAM_KEY, sharedSecret.data(), sharedSecret.size());
        params[2] = OSSL_PARAM_construct_octet_string(OSSL_KDF_PARAM_INFO, (char*)"ecies-handshake", 15);
        params[3] = OSSL_PARAM_construct_end();

        EVP_KDF_derive(kctx, aesKey.data(), aesKey.size(), params);
        EVP_KDF_CTX_free(kctx);

        return aesKey;
    }

    PackageOSSL Encrypt(EVP_PKEY* receiverPub, const std::string& plaintext) {
        PackageOSSL pkg;
        EVP_PKEY* ephKey = GenerateKey();

        // Eksport klucza publicznego do przesyłu (DER format)
        int pubLen = i2d_PUBKEY(ephKey, NULL);
        pkg.ephemeral_pub.resize(pubLen);
        unsigned char* p = pkg.ephemeral_pub.data();
        i2d_PUBKEY(ephKey, &p);

        // Uzgodnienie klucza AES
        std::vector<unsigned char> aesKey = DeriveSharedKey(ephKey, receiverPub);
        EVP_PKEY_free(ephKey); // Sprzątanie pamięci C-style

        // AES-GCM
        pkg.nonce.resize(12);
        RAND_bytes(pkg.nonce.data(), 12);

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
        EVP_EncryptInit_ex(ctx, NULL, NULL, aesKey.data(), pkg.nonce.data());

        pkg.ciphertext.resize(plaintext.size());
        int len;
        EVP_EncryptUpdate(ctx, pkg.ciphertext.data(), &len, (const unsigned char*)plaintext.data(), plaintext.size());

        int finalLen;
        EVP_EncryptFinal_ex(ctx, pkg.ciphertext.data() + len, &finalLen);

        pkg.tag.resize(16);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, pkg.tag.data());
        EVP_CIPHER_CTX_free(ctx);

        return pkg;
    }

    std::string Decrypt(EVP_PKEY* receiverPriv, const PackageOSSL& pkg) {
        // Odtworzenie klucza z bajtów
        const unsigned char* p = pkg.ephemeral_pub.data();
        EVP_PKEY* ephPub = d2i_PUBKEY(NULL, &p, pkg.ephemeral_pub.size());

        std::vector<unsigned char> aesKey = DeriveSharedKey(receiverPriv, ephPub);
        EVP_PKEY_free(ephPub);

        // Deszyfrowanie AES-GCM
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
        EVP_DecryptInit_ex(ctx, NULL, NULL, aesKey.data(), pkg.nonce.data());

        std::string plaintext;
        plaintext.resize(pkg.ciphertext.size());
        int len;
        EVP_DecryptUpdate(ctx, (unsigned char*)plaintext.data(), &len, pkg.ciphertext.data(), pkg.ciphertext.size());

        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, (void*)pkg.tag.data());

        int ret = EVP_DecryptFinal_ex(ctx, (unsigned char*)plaintext.data() + len, &len);
        EVP_CIPHER_CTX_free(ctx);

        if (ret > 0) {
            return plaintext;
        } else {
            return "[BLAD] OpenSSL: Integralnosc naruszona!";
        }
    }
};