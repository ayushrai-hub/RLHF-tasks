cmake_minimum_required(VERSION 3.16)
project(vlt_env LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(vlt_run
  runner/main.cpp
  common/digest.cpp
  common/stage_load.cpp
  common/stage_fold.cpp
  common/stage_peek.cpp
  common/stage_tally.cpp
  common/stage_seal.cpp
  m02/t2_pull.cpp
  m02/j4_shadow.cpp
  m02/extra_m1.cpp
  m02/extra_m2.cpp
  r04/tape_lane.cpp
  n09/delta_lane.cpp
  q11/h2_shadow.cpp
  q11/extra_q1.cpp
  q11/extra_q2.cpp
  w33/k9_mux.cpp
  w33/k9_filter.cpp
  w33/s1_shadow.cpp
  w33/extra_w1.cpp
  w33/extra_w2.cpp
  persist/vlt_journal.cpp
)
target_include_directories(vlt_run PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}/common
  ${CMAKE_CURRENT_SOURCE_DIR}/r04
  ${CMAKE_CURRENT_SOURCE_DIR}/persist)
set_target_properties(vlt_run PROPERTIES RUNTIME_OUTPUT_DIRECTORY /app/build)
