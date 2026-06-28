#pragma once

#include <map>
#include <string>
#include <vector>

struct Package {
    std::string name;
    std::string version;
    std::string description;
    std::vector<std::string> requires;
    std::vector<std::string> requires_private;
    std::vector<std::string> libs;
    std::vector<std::string> libs_private;
    std::vector<std::string> cflags;
};

struct Manifest {
    std::vector<std::string> roots;
    std::vector<std::string> allowed_static_flags;
    std::vector<std::string> static_only_flags;
};

struct Edge {
    std::string from;
    std::string to;
    std::string kind;
};

struct RootResolution {
    std::string name;
    std::vector<std::string> public_libs;
    std::vector<std::string> static_libs;
    std::vector<Edge> dependency_edges;
};

struct Finding {
    std::string kind;
    std::string package;
    std::string detail;
};
