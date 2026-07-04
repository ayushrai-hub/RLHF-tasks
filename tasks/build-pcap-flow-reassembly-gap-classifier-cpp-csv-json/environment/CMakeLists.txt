cmake_minimum_required(VERSION 3.16)
project(flowgap LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(flowgap src/main.cpp)
target_compile_options(flowgap PRIVATE -Wall -Wextra -pedantic)
