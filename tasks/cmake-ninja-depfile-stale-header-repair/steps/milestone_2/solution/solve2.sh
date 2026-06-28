#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

path = Path("/app/build_support/depfix.cmake")
text = path.read_text(encoding="utf-8")

text = text.replace(
    """  if(target STREQUAL "depfix_util" OR target STREQUAL "depfix_app")
    # util/app rely on stamp sync instead of compiler depfiles
  else()
    target_compile_options(${target} PRIVATE -MD -MP)
  endif()""",
    "  target_compile_options(${target} PRIVATE -MD -MP)",
)

needle = '    DEPENDS "${_config}"\n    COMMENT "Depfix header sync stamp"'
replacement = (
    '    DEPENDS "${_config}" "${CMAKE_SOURCE_DIR}/include/depfix/version.hpp"\n'
    '    COMMENT "Depfix header sync stamp"'
)
if needle not in text:
    raise SystemExit("depfix.cmake stamp rule layout changed")
text = text.replace(needle, replacement)

if "add_dependencies(depfix_util depfix_header_sync)" not in text:
    needle = (
        '  add_custom_target(depfix_header_sync DEPENDS "${_stamp}")\n'
        "endfunction()\n"
    )
    replacement = (
        '  add_custom_target(depfix_header_sync DEPENDS "${_stamp}")\n'
        "  if(TARGET depfix_util)\n"
        "    add_dependencies(depfix_util depfix_header_sync)\n"
        "  endif()\n"
        "  if(TARGET depfix_core)\n"
        "    add_dependencies(depfix_core depfix_header_sync)\n"
        "  endif()\n"
        "  if(TARGET depfix_app)\n"
        "    add_dependencies(depfix_app depfix_header_sync)\n"
        "  endif()\n"
        "endfunction()\n"
    )
    if needle not in text:
        raise SystemExit("depfix.cmake header sync block layout changed")
    text = text.replace(needle, replacement)

path.write_text(text, encoding="utf-8")
PY

cmake -G Ninja -S /app -B /app/build
ninja -C /app/build -t clean depfix_util depfix_core depfix_app || true
j="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
cmake --build /app/build -j"${j}"
