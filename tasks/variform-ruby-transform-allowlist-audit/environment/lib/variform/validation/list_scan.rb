# frozen_string_literal: true

module Variform
  module Validation
    module ListScan
      module_function

      def walk(list)
        list.each do |element|
          ScalarScan.check(element) if element.is_a?(String) || element.is_a?(Symbol)
        end
      end
    end
  end
end
