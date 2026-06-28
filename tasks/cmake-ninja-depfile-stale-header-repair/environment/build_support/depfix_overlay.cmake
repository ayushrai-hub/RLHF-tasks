# Refresh live dep manifests from the stale mirror before each target build.
if(EXISTS "${CMAKE_BINARY_DIR}/deps-stale")
  file(COPY "${CMAKE_BINARY_DIR}/deps-stale/" DESTINATION "${CMAKE_BINARY_DIR}/deps")
endif()
