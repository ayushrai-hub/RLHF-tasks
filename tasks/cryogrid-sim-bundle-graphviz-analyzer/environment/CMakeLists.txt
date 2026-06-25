cmake_minimum_required(VERSION 3.16)
project(cryogrid_analyzer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(nlohmann_json 3.11.2 REQUIRED)

add_executable(cryogrid-analyze
    src/main.cpp
    src/bundle_spec_loader.cpp
    src/stage_graph.cpp
    src/variance_engine.cpp
    src/stability_check.cpp
    src/dot_emitter.cpp
    src/metrics_json.cpp
    src/legacy_dot_writer.cpp
)

target_include_directories(cryogrid-analyze PRIVATE include)
target_link_libraries(cryogrid-analyze PRIVATE nlohmann_json::nlohmann_json)
