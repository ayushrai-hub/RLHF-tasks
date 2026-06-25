cmake_minimum_required(VERSION 3.25)
project(tb_iter LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(/app/include)

add_executable(tb_iter
  /app/main.cpp
  /app/core/metric_fabric.cpp
  /app/mpi/reduce_bridge.cpp
  /app/io/trace_sink.cpp
  /app/sim/engine.cpp
  /app/sim/loader.cpp
  /app/sim/math_utils.cpp
  /app/sim/checkpoint.cpp
  /app/sim/run_journal.cpp
  /app/sim/epoch_coordinator.cpp
  /app/util/audit_digest.cpp
  /app/util/layout.cpp
  /app/core/op_a_shadow.cpp
  /app/mpi/op_b_aux.cpp
  /app/io/op_c_buffer.cpp
)