add_library(tb_lane STATIC
  ../q4/edge_scan.c
  ../q4/edge_shadow.c
  ../w7/stamp_lane.c
  ../w7/stamp_shadow.c
  ../p2/slot_lane.c
  ../p2/slot_shadow.c
  ../k9/cache_ring.c
  ../r3/journal_tail.c
  ../host/lane_notify.c
  ../host/lane_stamp.c
  ../host/lane_slot.c
  ../host/paths.c
  ../src/emit_trace.c
  ../decoys_d1/hash_stub.c
  ../third_stub/arc_util.c
)
target_include_directories(
  tb_lane PUBLIC ${CMAKE_SOURCE_DIR}/host ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/libcore
)
