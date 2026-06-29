# frozen_string_literal: true

module Variform
  module Validation
    module TransformationValidator
      module_function

      def validate(transformation)
        name = transformation.method_name

        unless MethodGate.permitted?(name)
          raise UnsupportedTransformation,
                "transform: unsupported transformation method '#{name}'"
        end

        ArgumentScan.check(transformation.argument)
        Result.new(transformation)
      end

      def validate_all(transformations)
        transformations.map { |transformation| validate(transformation) }
      end
    end
  end
end
