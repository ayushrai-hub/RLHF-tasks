# frozen_string_literal: true

module Variform
  module Processor
    module_function

    def plan_from_json(source, processor: Variform.configuration.default_processor)
      set = Spec::Parser.parse(source)
      Planner.call(set, processor: processor)
    end

    def plan_for(variant, processor: Variform.configuration.default_processor)
      Planner.call(variant.transformations, processor: processor)
    end
  end
end
