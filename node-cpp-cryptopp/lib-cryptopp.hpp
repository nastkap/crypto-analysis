#pragma once
#include <string>
#include <stdexcept>
#include <cryptopp/eccrypto.h>
#include <cryptopp/oids.h>
#include <cryptopp/osrng.h>
#include <cryptopp/hkdf.h>
#include <cryptopp/sha.h>
#include <cryptopp/gcm.h>
#include <cryptopp/aes.h>
#include <cryptopp/filters.h>

using namespace CryptoPP;

struct PackageCPP {
    std::string ephemeral_pub;
    std::string nonce;
    std::string ciphertext;
};

class ECIES_CryptoPP {
private:
    ECDH<ECP>::Domain ecdh;
    AutoSeededRandomPool prng;

public:
    ECIES_CryptoPP() : ecdh(ASN1::secp256r1()) {}

    void GenerateKeys(SecByteBlock& privKey, SecByteBlock& pubKey) {
        privKey.New(ecdh.PrivateKeyLength());
        pubKey.New(ecdh.PublicKeyLength());
        ecdh.GenerateKeyPair(prng, privKey, pubKey);
    }

    SecByteBlock DeriveSharedKey(const SecByteBlock& myPriv, const SecByteBlock& peerPub) {
        SecByteBlock sharedSecret(ecdh.AgreedValueLength());
        if (!ecdh.Agree(sharedSecret, myPriv, peerPub))
            throw std::runtime_error("Crypto++: Blad ECDH");

        SecByteBlock aesKey(32);
        HKDF<SHA256> hkdf;
        std::string info = "ecies-handshake";

        hkdf.DeriveKey(aesKey, aesKey.size(), sharedSecret, sharedSecret.size(),
                       nullptr, 0, (const byte*)info.data(), info.size());
        return aesKey;
    }

    PackageCPP Encrypt(const SecByteBlock& receiverPub, const std::string& plaintext) {
        PackageCPP pkg;
        SecByteBlock ephPriv, ephPub;
        GenerateKeys(ephPriv, ephPub);
        pkg.ephemeral_pub.assign((const char*)ephPub.BytePtr(), ephPub.size());

        SecByteBlock aesKey = DeriveSharedKey(ephPriv, receiverPub);

        SecByteBlock nonce(12);
        prng.GenerateBlock(nonce, nonce.size());
        pkg.nonce.assign((const char*)nonce.BytePtr(), nonce.size());

        GCM<AES>::Encryption gcm;
        gcm.SetKeyWithIV(aesKey, aesKey.size(), nonce, nonce.size());

        StringSource ss(plaintext, true, new AuthenticatedEncryptionFilter(gcm, new StringSink(pkg.ciphertext)));
        return pkg;
    }

    std::string Decrypt(const SecByteBlock& receiverPriv, const PackageCPP& pkg) {
        SecByteBlock ephPub((const byte*)pkg.ephemeral_pub.data(), pkg.ephemeral_pub.size());
        SecByteBlock aesKey = DeriveSharedKey(receiverPriv, ephPub);
        SecByteBlock nonce((const byte*)pkg.nonce.data(), pkg.nonce.size());

        GCM<AES>::Decryption gcm;
        gcm.SetKeyWithIV(aesKey, aesKey.size(), nonce, nonce.size());

        std::string recoveredText;
        StringSource ss(pkg.ciphertext, true, new AuthenticatedDecryptionFilter(gcm, new StringSink(recoveredText)));
        return recoveredText;
    }
};