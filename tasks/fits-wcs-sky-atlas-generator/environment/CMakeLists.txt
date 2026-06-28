cmake_minimum_required(VERSION 3.16)
project(wcs_atlas LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(wcs-atlas
  src/main.cpp
  src/types.cpp
  src/keyword_lexer.cpp
  src/wcs_matrix.cpp
  src/projection.cpp
  src/pixel_map.cpp
  src/atlas_writer.cpp
  src/keyword_snapshot.cpp
  src/flux_decoy.cpp
  src/staging/fits_ingest_stamp.cpp
)

target_include_directories(wcs-atlas PRIVATE include)
target_link_libraries(wcs-atlas PRIVATE m)

install(TARGETS wcs-atlas RUNTIME DESTINATION bin)
