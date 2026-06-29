# frozen_string_literal: true

require_relative 'variform/version'
require_relative 'variform/errors'
require_relative 'variform/configuration'

require_relative 'variform/support/blank'
require_relative 'variform/support/inflector'

require_relative 'variform/geometry/dimensions'
require_relative 'variform/geometry/region'
require_relative 'variform/geometry/flags'
require_relative 'variform/geometry'

require_relative 'variform/transformation'
require_relative 'variform/transformation_set'
require_relative 'variform/blob'
require_relative 'variform/variant'

require_relative 'variform/validation/method_allowlist'
require_relative 'variform/validation/method_catalog'
require_relative 'variform/validation/method_gate'
require_relative 'variform/validation/argument_denylist'
require_relative 'variform/validation/scalar_scan'
require_relative 'variform/validation/list_scan'
require_relative 'variform/validation/hash_scan'
require_relative 'variform/validation/argument_scan'
require_relative 'variform/validation/result'
require_relative 'variform/validation/transformation_validator'

require_relative 'variform/command/tokenizer'
require_relative 'variform/command/plan'
require_relative 'variform/command/builder'

require_relative 'variform/spec/normalizer'
require_relative 'variform/spec/parser'

require_relative 'variform/planner'
require_relative 'variform/processor'

require_relative 'variform/cli/usage'
require_relative 'variform/cli/options'
require_relative 'variform/cli/commands/check'
require_relative 'variform/cli/commands/plan'
require_relative 'variform/cli/commands/methods'
require_relative 'variform/cli/runner'

module Variform
end
