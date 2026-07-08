cmake_minimum_required(VERSION 3.16)
project(beam-envelope LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(${CMAKE_SOURCE_DIR}/include)

add_executable(beam-envelope
    src/cmd/main.cpp
    src/io/parser.cpp
    src/io/validate.cpp
    src/model/amend.cpp
    src/model/normalize.cpp
    src/stage/journal.cpp
    src/stage/commit.cpp
    src/load/resolve.cpp
    src/load/combinations.cpp
    src/analysis/common.cpp
    src/analysis/equilibrium.cpp
    src/analysis/piecewise.cpp
    src/analysis/extrema.cpp
    src/analysis/curvature.cpp
    src/analysis/constraints.cpp
    src/analysis/deflection.cpp
    src/cache/key.cpp
    src/cache/store.cpp
    src/report/envelope.cpp
    src/report/schema.cpp
    src/report/digest.cpp
    src/report/writer.cpp
    src/seal/sha256.cpp
)
