cmake_minimum_required(VERSION 3.16)
project(p7lab CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ZLIB REQUIRED)

include_directories(include ${CMAKE_CURRENT_SOURCE_DIR})

set(P7CORE_SRC
  src/lib.cpp src/epoch_row.cpp src/scn.cpp src/wal.cpp src/state.cpp src/engine.cpp
  s5/s5_s.cpp s5/gateway.cpp s5/shadow_s5.cpp
  w3/w3_j.cpp w3/gateway.cpp w3/shadow_w3.cpp
  p8/p8_p.cpp p8/gateway.cpp p8/shadow_p8.cpp
  m6/m6_c.cpp m6/gateway.cpp m6/shadow_m6.cpp
  f2/f2_x.cpp f2/gateway.cpp f2/shadow_f2.cpp
  pack/mix_p7.cpp pack/fold_p7.cpp pack/emit_gateway.cpp pack/shadow_pack.cpp
)

add_library(p7core STATIC ${P7CORE_SRC})
target_link_libraries(p7core PRIVATE ${ZLIB_LIBRARIES})

foreach(bin p7_run p7_emit p7_recover p7_inspect)
  add_executable(${bin} cli/${bin}.cpp)
  target_link_libraries(${bin} PRIVATE p7core)
endforeach()
