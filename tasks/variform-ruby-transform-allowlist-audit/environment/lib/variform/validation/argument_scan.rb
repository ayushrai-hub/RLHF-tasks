# frozen_string_literal: true

module Variform
  module Validation
    module ArgumentScan
      module_function

      def check(argument)
        case argument
        when nil, Integer, Float, true, false
          nil
        when String, Symbol
          ScalarScan.check(argument)
        when Array
          ListScan.walk(argument)
        when Hash
          HashScan.walk(argument)
        else
          ScalarScan.check(argument.to_s)
        end
      end
    end
  end
end
