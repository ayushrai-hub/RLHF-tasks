# frozen_string_literal: true

module Variform
  module Validation
    module ScalarScan
      module_function

      def check(value)
        text = value.to_s
        forbidden = ArgumentDenylist::FORBIDDEN.find { |token| text.include?(token) }
        return unless forbidden

        raise UnsupportedTransformation,
              "transform: argument names a forbidden image option (#{forbidden})"
      end
    end
  end
end
