cmake_minimum_required(VERSION 3.25)
project(tb_iter_verifier LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(tb_iter_verifier
  main.cpp
  harness.cpp
  contract_model.cpp
)

target_include_directories(tb_iter_verifier PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
