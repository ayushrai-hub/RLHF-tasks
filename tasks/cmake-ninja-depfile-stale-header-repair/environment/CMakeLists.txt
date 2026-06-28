cmake_minimum_required(VERSION 3.22)
project(depfix_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include("${CMAKE_SOURCE_DIR}/build_support/CompilerFlags.cmake")
include("${CMAKE_SOURCE_DIR}/build_support/TargetDefaults.cmake")
include("${CMAKE_SOURCE_DIR}/build_support/depfix.cmake")

add_library(depfix_hash STATIC src/detail/hash_mix.cpp)
target_include_directories(depfix_hash PUBLIC "${CMAKE_SOURCE_DIR}/include")
depfix_enable_depfiles(depfix_hash src/detail/hash_mix.cpp)

add_library(depfix_core STATIC src/core.cpp)
target_link_libraries(depfix_core PUBLIC depfix_hash)
target_include_directories(depfix_core PUBLIC "${CMAKE_SOURCE_DIR}/include")
target_compile_options(depfix_core PRIVATE ${DEPFIX_WARNING_FLAGS})
depfix_enable_depfiles(depfix_core src/core.cpp)

add_library(depfix_util STATIC src/util.cpp)
target_include_directories(depfix_util PUBLIC "${CMAKE_SOURCE_DIR}/include")
target_link_libraries(depfix_util PUBLIC depfix_core)
depfix_enable_depfiles(depfix_util src/util.cpp)

add_executable(depfix_app src/main.cpp)
target_link_libraries(depfix_app PRIVATE depfix_util depfix_core)
depfix_enable_depfiles(depfix_app src/main.cpp)

depfix_register_header_sync()
