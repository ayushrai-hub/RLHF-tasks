dl_dep = meson.get_compiler('c').find_library('dl', required: true)
install_libdir = get_option('prefix') / get_option('libdir')

capsule_sources = files(
  'core.c',
  'identity.c',
  'origin.c',
  'text.c',
  'score.c',
  'state.c',
  'codec.c'
)

capsule_lib = shared_library(
  'capsule',
  capsule_sources,
  include_directories: [project_inc, configured_inc],
  dependencies: [dl_dep],
  c_args: ['-DCAPSULE_INSTALL_LIBDIR="@0@"'.format(install_libdir)],
  version: meson.project_version(),
  soversion: '2',
  install: true
)

capsule_dep = declare_dependency(
  link_with: capsule_lib,
  include_directories: [project_inc, configured_inc]
)
