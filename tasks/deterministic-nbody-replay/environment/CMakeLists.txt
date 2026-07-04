cmake_minimum_required(VERSION 3.16)
project(nbody CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -ffast-math -march=native")

add_executable(nbody
    src/main.cpp
    src/scenario.cpp
    src/force_kernel.cpp
    src/integrator.cpp
    src/serialization.cpp
)

target_include_directories(nbody PRIVATE src)
target_link_libraries(nbody m)

install(TARGETS nbody DESTINATION bin)
