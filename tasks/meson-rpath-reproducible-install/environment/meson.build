project(
  'capsule',
  'c',
  version: '2.7.4',
  default_options: ['c_std=c11', 'warning_level=2']
)

catalog_profile = get_option('catalog_profile')

cfg = configuration_data()
cfg.set('CAPSULE_VERSION', meson.project_version())
cfg.set('CAPSULE_PACKAGE_ID', 'capsule-meson-rpath-' + meson.project_version())
cfg.set('CAPSULE_CONFIG_SOURCE', 'generated')
cfg.set('CAPSULE_CONFIG_PROVENANCE', 'meson-configured')
cfg.set('CAPSULE_CATALOG_PROFILE', catalog_profile)

config_h = configure_file(
  input: 'include/capsule_config.h.in',
  output: 'capsule_config.h',
  configuration: cfg
)

project_inc = include_directories('include')
configured_inc = include_directories(meson.current_build_dir())

subdir('src')
subdir('tools')
subdir('client')
subdir('checks')

install_headers('include/capsule.h', 'include/capsule_config.h')

pkg = import('pkgconfig')
pkg.generate(
  capsule_lib,
  name: 'capsule',
  filebase: 'capsule',
  description: 'Capsule runtime metadata library',
  version: meson.project_version()
)
