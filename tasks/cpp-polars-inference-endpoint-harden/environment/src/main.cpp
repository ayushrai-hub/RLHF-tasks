#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cctype>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include <jsoncpp/json/json.h>

#include "score/http_service.hpp"
#include "score/ratified_policy.hpp"

namespace {
std::string read_file(const std::string& path) {
    std::ifstream in(path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    return buffer.str();
}

Json::Value parse_json(const std::string& body) {
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    std::istringstream stream(body);
    Json::parseFromStream(builder, stream, &root, &errs);
    return root;
}

std::string read_http_body(int client, const std::string& request) {
    auto header_end = request.find("\r\n\r\n");
    if (header_end == std::string::npos) {
        return "";
    }
    std::string body = request.substr(header_end + 4);
    std::string lowered = request.substr(0, header_end);
    for (char& ch : lowered) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    auto cl_pos = lowered.find("content-length:");
    if (cl_pos == std::string::npos) {
        return body;
    }
    auto line_end = lowered.find("\r\n", cl_pos);
    std::string line = lowered.substr(cl_pos, line_end - cl_pos);
    int content_length = std::atoi(line.c_str() + std::strlen("content-length:"));
    while (static_cast<int>(body.size()) < content_length) {
        char extra[8192];
        ssize_t n = read(client, extra, sizeof(extra));
        if (n <= 0) {
            break;
        }
        body.append(extra, static_cast<size_t>(n));
    }
    if (static_cast<int>(body.size()) > content_length) {
        body.resize(static_cast<size_t>(content_length));
    }
    return body;
}
}  // namespace

int main() {
    const int port = 19091;
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);
    bind(server_fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
    listen(server_fd, 8);

    RatifiedPolicy policy_loader;
    Policy policy = policy_loader.load("/app/docs/inference-operations-dossier.md",
                                       "/app/environment/config/endpoint_defaults.toml");
    Json::Value weights = parse_json(read_file("/app/environment/config/model_weights.json"));
    HttpService service;

    while (true) {
        int client = accept(server_fd, nullptr, nullptr);
        std::string request;
        char buffer[8192];
        ssize_t n = read(client, buffer, sizeof(buffer));
        if (n <= 0) {
            close(client);
            continue;
        }
        request.append(buffer, static_cast<size_t>(n));
        std::string body = read_http_body(client, request);
        Json::Value payload = parse_json(body);
        Json::Value response = service.handle_batch(payload, policy, weights);
        Json::StreamWriterBuilder builder;
        builder["indentation"] = "  ";
        std::string json_body = Json::writeString(builder, response);
        std::ostringstream http;
        http << "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
             << json_body.size() << "\r\nConnection: close\r\n\r\n"
             << json_body;
        std::string out = http.str();
        write(client, out.data(), out.size());
        close(client);
    }
    return 0;
}
