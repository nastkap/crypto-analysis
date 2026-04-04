#include "httplib.h"
#include "lib-openssl.hpp"
#include <nlohmann/json.hpp>
#include <hiredis/hiredis.h>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using json = nlohmann::json;

static std::string base64_encode(const std::vector<unsigned char>& data) {
    BIO* b64 = BIO_new(BIO_f_base64());
    BIO* mem = BIO_new(BIO_s_mem());
    BIO_push(b64, mem);
    BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
    BIO_write(b64, data.data(), static_cast<int>(data.size()));
    BIO_flush(b64);
    BUF_MEM* bptr;
    BIO_get_mem_ptr(b64, &bptr);
    std::string result(bptr->data, bptr->length);
    BIO_free_all(b64);
    return result;
}

static std::vector<unsigned char> base64_decode(const std::string& encoded) {
    BIO* b64 = BIO_new(BIO_f_base64());
    BIO* mem = BIO_new_mem_buf(encoded.data(), static_cast<int>(encoded.size()));
    BIO_push(b64, mem);
    BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
    std::vector<unsigned char> buf(encoded.size());
    int len = BIO_read(b64, buf.data(), static_cast<int>(buf.size()));
    BIO_free_all(b64);
    buf.resize(len > 0 ? static_cast<size_t>(len) : 0UL);
    return buf;
}

static std::string pubkey_to_pem(EVP_PKEY* key) {
    BIO* bio = BIO_new(BIO_s_mem());
    PEM_write_bio_PUBKEY(bio, key);
    BUF_MEM* bptr;
    BIO_get_mem_ptr(bio, &bptr);
    std::string pem(bptr->data, bptr->length);
    BIO_free(bio);
    return pem;
}

static EVP_PKEY* pem_to_pubkey(const std::string& pem) {
    BIO* bio = BIO_new_mem_buf(pem.data(), static_cast<int>(pem.size()));
    EVP_PKEY* key = PEM_read_bio_PUBKEY(bio, nullptr, nullptr, nullptr);
    BIO_free(bio);
    return key;
}

// ---- Redis URL parser ----
static void parse_redis_url(const std::string& url, std::string& host, int& port) {
    host = "message-broker";
    port = 6379;
    auto pos = url.find("://");
    if (pos == std::string::npos) return;
    std::string hostport = url.substr(pos + 3);
    auto colon = hostport.rfind(':');
    if (colon != std::string::npos) {
        host = hostport.substr(0, colon);
        port = std::stoi(hostport.substr(colon + 1));
    }
}

// ---- Redis worker thread ----
static void redis_worker(const std::string& node_name,
                         const std::string& redis_host, int redis_port,
                         ECIES_OpenSSL ecies, EVP_PKEY* node_priv) {
    redisContext* r = redisConnect(redis_host.c_str(), redis_port);
    if (!r || r->err) {
        std::cerr << "[" << node_name << "] Redis worker: blad polaczenia" << std::endl;
        return;
    }
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
                std::string pub_pem = task.at("receiver_public_key_pem");
                std::string message = task.at("message");
                auto t0 = std::chrono::high_resolution_clock::now();
                EVP_PKEY* recv_pub = pem_to_pubkey(pub_pem);
                if (!recv_pub) throw std::runtime_error("Nieprawidlowy klucz PEM");
                PackageOSSL pkg = ecies.Encrypt(recv_pub, message);
                EVP_PKEY_free(recv_pub);
                double ms = std::chrono::duration<double, std::milli>(
                    std::chrono::high_resolution_clock::now() - t0).count();
                std::vector<unsigned char> ct_tag = pkg.ciphertext;
                ct_tag.insert(ct_tag.end(), pkg.tag.begin(), pkg.tag.end());
                result = {
                    {"status", "success"}, {"execution_time_ms", ms},
                    {"package", {
                        {"ephemeral_pub_bytes_b64", base64_encode(pkg.ephemeral_pub)},
                        {"nonce_b64",               base64_encode(pkg.nonce)},
                        {"ciphertext_b64",           base64_encode(ct_tag)}
                    }}
                };
            } else if (task_type == "decrypt") {
                auto eph    = base64_decode(task.at("ephemeral_pub_bytes_b64").get<std::string>());
                auto nonce  = base64_decode(task.at("nonce_b64").get<std::string>());
                auto ct_tag = base64_decode(task.at("ciphertext_b64").get<std::string>());
                if (ct_tag.size() < 16) throw std::runtime_error("Zbyt krotki szyfrogram");
                PackageOSSL pkg;
                pkg.ephemeral_pub = eph;
                pkg.nonce         = nonce;
                pkg.tag.assign(ct_tag.end() - 16, ct_tag.end());
                pkg.ciphertext.assign(ct_tag.begin(), ct_tag.end() - 16);
                auto t0 = std::chrono::high_resolution_clock::now();
                std::string decrypted = ecies.Decrypt(node_priv, pkg);
                double ms = std::chrono::duration<double, std::milli>(
                    std::chrono::high_resolution_clock::now() - t0).count();
                result = {{"status", "success"}, {"execution_time_ms", ms},
                          {"decrypted_message", decrypted}};
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
    // --- Env vars ---
    const char* name_env   = std::getenv("NODE_NAME");
    const char* broker_env = std::getenv("BROKER_URL");
    std::string node_name  = name_env   ? name_env   : "CPP_OpenSSL";
    std::string broker_url = broker_env ? broker_env : "redis://message-broker:6379";
    std::string redis_host; int redis_port;
    parse_redis_url(broker_url, redis_host, redis_port);

    ECIES_OpenSSL ecies;
    EVP_PKEY* node_priv = ecies.GenerateKey();

    // --- Rejestracja klucza publicznego w Redis ---
    {
        redisContext* r = redisConnect(redis_host.c_str(), redis_port);
        if (r && !r->err) {
            std::string pem = pubkey_to_pem(node_priv);
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
    std::thread(redis_worker, node_name, redis_host, redis_port, ecies, node_priv).detach();

    httplib::Server svr;

    svr.Get("/", [](const httplib::Request&, httplib::Response& res) {
        json resp = {{"status", "ok"}, {"node", "C++-OpenSSL"}, {"message", "Mikroserwis dziala!"}};
        res.set_content(resp.dump(), "application/json");
    });

    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        json resp = {{"status", "healthy"}, {"node", "C++-OpenSSL"}};
        res.set_content(resp.dump(), "application/json");
    });

    svr.Get("/public-key", [&](const httplib::Request&, httplib::Response& res) {
        std::string pem = pubkey_to_pem(node_priv);
        json resp = {{"public_key_pem", pem}};
        res.set_content(resp.dump(), "application/json");
    });

    svr.Post("/encrypt", [&](const httplib::Request& req, httplib::Response& res) {
        try {
            auto body       = json::parse(req.body);
            std::string message  = body.at("message");
            std::string pub_pem  = body.at("receiver_public_key_pem");

            auto t0 = std::chrono::high_resolution_clock::now();
            EVP_PKEY* recv_pub = pem_to_pubkey(pub_pem);
            if (!recv_pub) throw std::runtime_error("Nieprawidlowy klucz PEM");
            PackageOSSL pkg = ecies.Encrypt(recv_pub, message);
            EVP_PKEY_free(recv_pub);
            double ms = std::chrono::duration<double, std::milli>(
                std::chrono::high_resolution_clock::now() - t0).count();

            // Concatenate ciphertext + GCM tag (consistent with Python nodes)
            std::vector<unsigned char> ct_tag = pkg.ciphertext;
            ct_tag.insert(ct_tag.end(), pkg.tag.begin(), pkg.tag.end());

            json resp = {
                {"status", "success"},
                {"execution_time_ms", ms},
                {"package", {
                    {"ephemeral_pub_bytes_b64", base64_encode(pkg.ephemeral_pub)},
                    {"nonce_b64",               base64_encode(pkg.nonce)},
                    {"ciphertext_b64",           base64_encode(ct_tag)}
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
            auto body        = json::parse(req.body);
            auto eph         = base64_decode(body.at("ephemeral_pub_bytes_b64"));
            auto nonce       = base64_decode(body.at("nonce_b64"));
            auto ct_tag      = base64_decode(body.at("ciphertext_b64"));

            if (ct_tag.size() < 16)
                throw std::runtime_error("Zbyt krotki szyfrogram");

            PackageOSSL pkg;
            pkg.ephemeral_pub = eph;
            pkg.nonce         = nonce;
            pkg.tag.assign(ct_tag.end() - 16, ct_tag.end());
            pkg.ciphertext.assign(ct_tag.begin(), ct_tag.end() - 16);

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

    std::cout << "[" << node_name << "] C++ OpenSSL ECIES serwer uruchomiony na porcie 8000" << std::endl;
    svr.listen("0.0.0.0", 8000);
    EVP_PKEY_free(node_priv);
    return 0;
}