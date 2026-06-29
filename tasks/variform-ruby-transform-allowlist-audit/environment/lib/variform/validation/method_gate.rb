# frozen_string_literal: true

module Variform
  module Validation
    module MethodGate
      module_function

      def permitted?(name)
        candidate = name.to_s.strip.split(/\s+/).first.to_s
        MethodAllowlist::ALLOWED.any? { |method| candidate.include?(method) }
      end
    end
  end
end
