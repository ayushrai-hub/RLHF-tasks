cmake_minimum_required(VERSION 3.16)
project(stale_bld C)

include(toolchain/constraints.cmake)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)

add_subdirectory(driver)

add_executable(bld_host host/bld_host.c host/bld_core.c host/digest_util.c host/dep_audit.c)
target_link_libraries(bld_host tb_lane)
target_include_directories(bld_host PRIVATE ${CMAKE_SOURCE_DIR}/host ${CMAKE_SOURCE_DIR}/src)

add_executable(trace_host host/trace_host.c host/bld_core.c host/digest_util.c)
target_link_libraries(trace_host tb_lane)
target_include_directories(trace_host PRIVATE ${CMAKE_SOURCE_DIR}/host ${CMAKE_SOURCE_DIR}/src)
