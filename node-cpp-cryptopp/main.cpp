#include "httplib.h"
#include "lib-cryptopp.hpp"
#include <nlohmann/json.hpp>
#include <hiredis/hiredis.h>
#include <cryptopp/base64.h>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

using json = nlohmann::json;
using namespace CryptoPP;

// ---- Base64 helpers using Crypto++ ----
static std::string base64_encode(const unsigned char* data, size_t len) {
    std::string result;
    StringSource ss(data, len, true,
        new Base64Encoder(new StringSink(result), false));
    return result;
}

static std::string base64_encode_str(const std::string& data) {
    return base64_encode(
        reinterpret_cast<const unsigned char*>(data.data()), data.size());
}

static SecByteBlock base64_decode_sbb(const std::string& encoded) {
    std::string decoded;
    StringSource ss(encoded, true, new Base64Decoder(new StringSink(decoded)));
    return SecByteBlock(
        reinterpret_cast<const byte*>(decoded.data()), decoded.size());
}

// ---- PEM serialization for P-256 raw ECDH public key ----
// DER SubjectPublicKeyInfo prefix for P-256 (secp256r1), 26 bytes
// Followed by 65-byte uncompressed EC point (04 || x || y)
static const unsigned char P256_SPKI_PREFIX[26] = {
    0x30, 0x59, 0x30, 0x13, 0x06, 0x07,
    0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01,
    0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07,
    0x03, 0x42, 0x00
};

static std::string raw_ec_pub_to_pem(const SecByteBlock& rawPub) {
    std::vector<unsigned char> der(P256_SPKI_PREFIX, P256_SPKI_PREFIX + 26);
    der.insert(der.end(), rawPub.begin(), rawPub.end());
    std::string b64;
    StringSource ss(der.data(), der.size(), true,
        new Base64Encoder(new StringSink(b64), true, 64));
    return "-----BEGIN PUBLIC KEY-----\n" + b64 + "-----END PUBLIC KEY-----\n";
}

static SecByteBlock pem_to_raw_ec_pub(const std::string& pem) {
    std::string b64;
    std::istringstream iss(pem);
    std::string line;
    while (std::getline(iss, line)) {
        if (line.find("-----") == std::string::npos)
            b64 += line;
    }
    std::string decoded;
    StringSource ss(b64, true, new Base64Decoder(new StringSink(decoded)));
    if (decoded.size() < 26 + 65)
        throw std::runtime_error("Nieprawidlowy format klucza PEM");
    return SecByteBlock(
        reinterpret_cast<const byte*>(decoded.data() + 26), 65);
}

// ---- Redis URL parser ----
static void parse_redis_url(const std::string& url, std::string& host, int& port) {
    host = "message-broker"; port = 6379;
    auto pos = url.find("://");
    if (pos == std::string::npos) return;
    std::string hp = url.substr(pos + 3);
    auto colon = hp.rfind(':');
    if (colon != std::string::npos) { host = hp.substr(0, colon); port = std::stoi(hp.substr(colon + 1)); }
}

// ---- Redis worker thread ----
static void redis_worker(const std::string& node_name,
                         const std::string& redis_host, int redis_port,
                         SecByteBlock node_priv) {
    redisContext* r = redisConnect(redis_host.c_str(), redis_port);
    if (!r || r->err) { std::cerr << "[" << node_name << "] Redis worker: blad polaczenia" << std::endl; return; }
    ECIES_CryptoPP ecies;
    std::string queue_key = "tasks:" + node_name;
    std::cout << "[" << node_name << "] Worker Redis uruchomiony, nasluchuje: " << queue_key << std::endl;

    while (true) {
        redisReply* reply = (redisReply*)redisCommand(r, "BRPOP %s 5", queue_key.c_str());
        if (!reply) { redisFree(r); r = redisConnect(redis_host.c_str(), redis_port); continue; }
        if (reply->type != REDIS_REPLY_ARRAY || reply->elements < 2) { freeReplyObject(reply); continue; }
        std::string task_json = reply->element[1]->str;
        freeReplyObject(reply);
        try {
            auto task = json::parse(task_json);
            std::string task_id   = task.at("task_id");
            std::string task_type = task.at("type");
            json result;

            if (task_type == "encrypt") {
                SecByteBlock recv_pub = pem_to_raw_ec_pub(task.at("receiver_public_key_pem").get<std::string>());
                std::string message   = task.at("message");
                auto t0 = std::chrono::high_resolution_clock::now();
                PackageCPP pkg = ecies.Encrypt(recv_pub, message);
                double ms = std::chrono::duration<double, std::milli>(
                    std::chrono::high_resolution_clock::now() - t0).count();
                result = {
                    {"status", "success"}, {"execution_time_ms", ms},
                    {"package", {
                        {"ephemeral_pub_bytes_b64", base64_encode_str(pkg.ephemeral_pub)},
                        {"nonce_b64",               base64_encode_str(pkg.nonce)},
                        {"ciphertext_b64",           base64_encode_str(pkg.ciphertext)}
                    }}
                };
            } else if (task_type == "decrypt") {
                PackageCPP pkg;
                SecByteBlock eph = base64_decode_sbb(task.at("ephemeral_pub_bytes_b64").get<std::string>());
                pkg.ephemeral_pub.assign(reinterpret_cast<const char*>(eph.BytePtr()), eph.size());
                SecByteBlock n = base64_decode_sbb(task.at("nonce_b64").get<std::string>());
                pkg.nonce.assign(reinterpret_cast<const char*>(n.BytePtr()), n.size());
                SecByteBlock ct = base64_decode_sbb(task.at("ciphertext_b64").get<std::string>());
                pkg.ciphertext.assign(reinterpret_cast<const char*>(ct.BytePtr()), ct.size());
                auto t0 = std::chrono::high_resolution_clock::now();
                std::string decrypted = ecies.Decrypt(node_priv, pkg);
                double ms = std::chrono::duration<double, std::milli>(
                    std::chrono::high_resolution_clock::now() - t0).count();
                result = {{"status", "success"}, {"execution_time_ms", ms}, {"decrypted_message", decrypted}};
            } else {
                result = {{"status", "error"}, {"detail", "Nieznany typ zadania"}};
            }

            std::string res_str = result.dump();
            std::string res_key = "results:" + task_id;
            redisReply* pr = (redisReply*)redisCommand(r, "LPUSH %s %s", res_key.c_str(), res_str.c_str());
            if (pr) freeReplyObject(pr);
            redisReply* er = (redisReply*)redisCommand(r, "EXPIRE %s 60", res_key.c_str());
            if (er) freeReplyObject(er);
        } catch (const std::exception& e) {
            std::cerr << "[" << node_name << "] Worker blad: " << e.what() << std::endl;
        }
    }
    redisFree(r);
}

int main() {
    const char* name_env   = std::getenv("NODE_NAME");
    const char* broker_env = std::getenv("BROKER_URL");
    std::string node_name  = name_env   ? name_env   : "CPP_CryptoPP";
    std::string broker_url = broker_env ? broker_env : "redis://message-broker:6379";
    std::string redis_host; int redis_port;
    parse_redis_url(broker_url, redis_host, redis_port);

    ECIES_CryptoPP ecies;
    SecByteBlock node_priv, node_pub;
    ecies.GenerateKeys(node_priv, node_pub);

    // --- Rejestracja klucza publicznego w Redis ---
    {
        redisContext* r = redisConnect(redis_host.c_str(), redis_port);
        if (r && !r->err) {
            std::string pem = raw_ec_pub_to_pem(node_pub);
            redisReply* rep = (redisReply*)redisCommand(r, "SET pubkey:%s %s",
                node_name.c_str(), pem.c_str());
            if (rep) freeReplyObject(rep);
            redisFree(r);
            std::cout << "[" << node_name << "] Klucz publiczny zarejestrowany w Redis" << std::endl;
        } else {
            std::cerr << "[" << node_name << "] Blad polaczenia z Redis" << std::endl;
        }
    }

    // --- Worker thread (Redis queue) ---
    std::thread(redis_worker, node_name, redis_host, redis_port, node_priv).detach();

    httplib::Server svr;

    svr.Get("/", [](const httplib::Request&, httplib::Response& res) {
        json resp = {{"status", "ok"}, {"node", "C++-CryptoPP"}, {"message", "Mikroserwis dziala!"}};
        res.set_content(resp.dump(), "application/json");
    });

    svr.Get("/public-key", [&](const httplib::Request&, httplib::Response& res) {
        std::string pem = raw_ec_pub_to_pem(node_pub);
        json resp = {{"public_key_pem", pem}};
        res.set_content(resp.dump(), "application/json");
    });

    svr.Post("/encrypt", [&](const httplib::Request& req, httplib::Response& res) {
        try {
            auto body       = json::parse(req.body);
            std::string message = body.at("message");
            std::string pub_pem = body.at("receiver_public_key_pem");

            auto t0 = std::chrono::high_resolution_clock::now();
            SecByteBlock recv_pub = pem_to_raw_ec_pub(pub_pem);
            PackageCPP pkg        = ecies.Encrypt(recv_pub, message);
            double ms = std::chrono::duration<double, std::milli>(
                std::chrono::high_resolution_clock::now() - t0).count();

            // ciphertext already contains GCM tag appended by AuthenticatedEncryptionFilter
            json resp = {
                {"status", "success"},
                {"execution_time_ms", ms},
                {"package", {
                    {"ephemeral_pub_bytes_b64", base64_encode_str(pkg.ephemeral_pub)},
                    {"nonce_b64",               base64_encode_str(pkg.nonce)},
                    {"ciphertext_b64",           base64_encode_str(pkg.ciphertext)}
                }}
            };
            res.set_content(resp.dump(), "application/json");
        } catch (const std::exception& e) {
            res.status = 400;
            res.set_content(json{{"detail", e.what()}}.dump(), "application/json");
        }
    });

    svr.Post("/decrypt", [&](const httplib::Request& req, httplib::Response& res) {
        try {
            auto body = json::parse(req.body);

            PackageCPP pkg;
            SecByteBlock eph = base64_decode_sbb(body.at("ephemeral_pub_bytes_b64"));
            pkg.ephemeral_pub.assign(
                reinterpret_cast<const char*>(eph.BytePtr()), eph.size());

            SecByteBlock nonce_raw = base64_decode_sbb(body.at("nonce_b64"));
            pkg.nonce.assign(
                reinterpret_cast<const char*>(nonce_raw.BytePtr()), nonce_raw.size());

            SecByteBlock ct_raw = base64_decode_sbb(body.at("ciphertext_b64"));
            pkg.ciphertext.assign(
                reinterpret_cast<const char*>(ct_raw.BytePtr()), ct_raw.size());

            auto t0 = std::chrono::high_resolution_clock::now();
            std::string decrypted = ecies.Decrypt(node_priv, pkg);
            double ms = std::chrono::duration<double, std::milli>(
                std::chrono::high_resolution_clock::now() - t0).count();

            json resp = {
                {"status", "success"},
                {"execution_time_ms", ms},
                {"decrypted_message", decrypted}
            };
            res.set_content(resp.dump(), "application/json");
        } catch (const std::exception& e) {
            res.status = 400;
            res.set_content(json{{"detail", e.what()}}.dump(), "application/json");
        }
    });

    std::cout << "[" << node_name << "] C++ Crypto++ ECIES serwer uruchomiony na porcie 8000" << std::endl;
    svr.listen("0.0.0.0", 8000);
    return 0;
}