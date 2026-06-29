#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

Path("/app/build_support/TargetDefaults.cmake").write_text(
    """# Default visibility and PIC for static libraries in the depfix demo.
set(DEPFIX_POSITION_INDEPENDENT_CODE ON)
set(DEPFIX_LEGACY_MAP FALSE)
set(DEPFIX_STRIP_GENERATED FALSE)
""",
    encoding="utf-8",
)

Path("/app/build_support/depfix.cmake").write_text(
    """# Custom depfile normalization for Ninja incremental builds.
set(DEPFIX_DEPS_DIR "${CMAKE_BINARY_DIR}/deps")

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
    POST_BUILD
    COMMAND ${CMAKE_COMMAND}
      -DDEPFILE_DIR=${DEPFIX_DEPS_DIR}
      -DTARGET_NAME=${target}
      -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
      -DDEPFIX_SOURCE_FILES="${_sources}"
      -P "${CMAKE_SOURCE_DIR}/build_support/depfix_normalize.cmake"
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
""",
    encoding="utf-8",
)

Path("/app/build_support/depfix_normalize.cmake").write_text(
    r"""# Invoked post-build to rewrite compiler dep snippets for Ninja.
if(NOT DEFINED DEPFILE_DIR)
  message(FATAL_ERROR "DEPFILE_DIR not set")
endif()
if(NOT DEFINED DEPFIX_SOURCE_FILES)
  set(DEPFIX_SOURCE_FILES "")
endif()

macro(depfix_collect_headers file headers_var)
  if(NOT EXISTS "${file}")
    return()
  endif()
  file(READ "${file}" _content)
  string(REGEX MATCHALL "#include \"depfix/[^\"]+\"" _matches "${_content}")
  foreach(_match IN LISTS _matches)
    string(REGEX REPLACE "#include \"depfix/([^\"]+)\"" "\\1" _suffix "${_match}")
    set(_rel "include/depfix/${_suffix}")
    list(FIND ${headers_var} "${_rel}" _idx)
    if(_idx EQUAL -1)
      list(APPEND ${headers_var} "${_rel}")
      depfix_collect_headers("${SOURCE_DIR}/${_rel}" ${headers_var})
    endif()
  endforeach()
endmacro()

file(MAKE_DIRECTORY "${DEPFILE_DIR}")
set(_out "${DEPFILE_DIR}/${TARGET_NAME}.dep")
file(WRITE "${_out}" "# depfix normalized deps for ${TARGET_NAME}\n")

set(_headers "")
separate_arguments(_src_list UNIX_COMMAND "${DEPFIX_SOURCE_FILES}")
foreach(_src IN LISTS _src_list)
  depfix_collect_headers("${SOURCE_DIR}/${_src}" _headers)
endforeach()
list(SORT _headers)
set(_canonical "")
foreach(_rel IN LISTS _headers)
  set(_canonical "${_canonical}${_rel}\n")
endforeach()
string(SHA256 _digest "${_canonical}")
list(LENGTH _headers _line_count)
foreach(_rel IN LISTS _headers)
  file(APPEND "${_out}" "${_rel}\n")
endforeach()
file(APPEND "${_out}" "# depfix-lines=${_line_count}\n")
file(APPEND "${_out}" "# depfix-digest=${_digest}\n")
""",
    encoding="utf-8",
)
PY

rm -rf /app/build/deps-stale

cmake -G Ninja -S /app -B /app/build
for t in depfix_hash depfix_core depfix_util depfix_app; do
  ninja -C /app/build -t clean "$t" || true
done
j="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
cmake --build /app/build -j"${j}"
