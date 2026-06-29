# frozen_string_literal: true

module Variform
  module Validation
    module HashScan
      module_function

      def walk(hash)
        hash.each_value do |value|
          ArgumentScan.check(value)
        end
      end
    end
  end
end
