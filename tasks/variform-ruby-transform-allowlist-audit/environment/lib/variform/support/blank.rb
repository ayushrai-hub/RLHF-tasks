# frozen_string_literal: true

module Variform
  module Support
    module_function

    def blank?(value)
      case value
      when nil then true
      when String then value.strip.empty?
      when Array, Hash then value.empty?
      else false
      end
    end

    def present?(value)
      !blank?(value)
    end
  end
end
