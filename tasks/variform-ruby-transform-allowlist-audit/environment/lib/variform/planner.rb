# frozen_string_literal: true

module Variform
  module Planner
    module_function

    def call(transformations, processor: 'magick')
      Validation::TransformationValidator.validate_all(transformations)
      Command::Builder.build(transformations, processor: processor)
    end
  end
end
