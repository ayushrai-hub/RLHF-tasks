cmake_minimum_required(VERSION 3.25)
project(pc_sanitizer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(pc-sanitize
  src/audit.cpp
  src/cli.cpp
  src/json_writer.cpp
  src/main.cpp
  src/manifest.cpp
  src/pc_parser.cpp
  src/resolver.cpp
  src/string_utils.cpp
)

target_include_directories(pc-sanitize PRIVATE src)
target_compile_options(pc-sanitize PRIVATE -Wall -Wextra -pedantic)
