# Mirror normalized manifests from the stale directory into the live deps folder.
if(EXISTS "${CMAKE_BINARY_DIR}/deps-stale")
  file(COPY "${CMAKE_BINARY_DIR}/deps-stale/" DESTINATION "${CMAKE_BINARY_DIR}/deps")
endif()
