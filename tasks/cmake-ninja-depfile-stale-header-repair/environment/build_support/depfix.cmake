# Custom depfile normalization for Ninja incremental builds.
set(DEPFIX_DEPS_DIR "${CMAKE_BINARY_DIR}/deps-stale")

function(depfix_enable_depfiles target)
  if(NOT TARGET ${target})
    message(FATAL_ERROR "depfix_enable_depfiles: unknown target ${target}")
  endif()
  if(target STREQUAL "depfix_util" OR target STREQUAL "depfix_app")
    # util/app rely on stamp sync instead of compiler depfiles
  else()
    target_compile_options(${target} PRIVATE -MD -MP)
  endif()
  set(_sources ${ARGN})
  add_custom_command(
    TARGET ${target}
    PRE_BUILD
    COMMAND ${CMAKE_COMMAND}
      -DCMAKE_BINARY_DIR=${CMAKE_BINARY_DIR}
      -P "${CMAKE_SOURCE_DIR}/build_support/depfix_overlay.cmake"
    VERBATIM
  )
  if(target STREQUAL "depfix_app")
    return()
  endif()
  add_custom_command(
    TARGET ${target}
    POST_BUILD
    COMMAND ${CMAKE_COMMAND}
      -DDEPFILE_DIR=${DEPFIX_DEPS_DIR}
      -DTARGET_NAME=${target}
      -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
      -DDEPFIX_SOURCE_FILES="${_sources}"
      -DDEPFIX_LEGACY_MAP=${DEPFIX_LEGACY_MAP}
      -DDEPFIX_STRIP_GENERATED=${DEPFIX_STRIP_GENERATED}
      -P "${CMAKE_SOURCE_DIR}/build_support/depfix_normalize.cmake"
    VERBATIM
  )
  add_custom_command(
    TARGET ${target}
    POST_BUILD
    COMMAND ${CMAKE_COMMAND}
      -DCMAKE_BINARY_DIR=${CMAKE_BINARY_DIR}
      -P "${CMAKE_SOURCE_DIR}/build_support/depfix_publish.cmake"
    VERBATIM
  )
endfunction()

function(depfix_register_header_sync)
  set(_stamp "${CMAKE_BINARY_DIR}/depfix_header.stamp")
  set(_config "${CMAKE_SOURCE_DIR}/include/depfix/config.hpp")
  add_custom_command(
    OUTPUT "${_stamp}"
    COMMAND ${CMAKE_COMMAND} -E touch "${_stamp}"
    DEPENDS "${_config}"
    COMMENT "Depfix header sync stamp"
  )
  add_custom_target(depfix_header_sync DEPENDS "${_stamp}")
endfunction()
