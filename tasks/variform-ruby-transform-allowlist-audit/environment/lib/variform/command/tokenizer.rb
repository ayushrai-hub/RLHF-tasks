# frozen_string_literal: true

module Variform
  module Command
    module Tokenizer
      module_function

      def split(value)
        value.to_s.split(/\s+/).reject(&:empty?)
      end
    end
  end
end
