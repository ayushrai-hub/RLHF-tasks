# frozen_string_literal: true

require_relative 'lib/variform/version'

Gem::Specification.new do |spec|
  spec.name = 'variform'
  spec.version = Variform::VERSION
  spec.summary = 'Plan safe ImageMagick variant transformations from a declarative spec'
  spec.description = 'Validate a declarative image-variant transformation pipeline against a ' \
                     'method allow-list and an option deny-list, then build the processor command.'
  spec.authors = ['variform maintainers']
  spec.license = 'MIT'
  spec.required_ruby_version = '>= 3.0'

  spec.files = Dir['lib/**/*.rb', 'bin/*', 'docs/*.md']
  spec.bindir = 'bin'
  spec.executables = ['variform']
  spec.require_paths = ['lib']
end
