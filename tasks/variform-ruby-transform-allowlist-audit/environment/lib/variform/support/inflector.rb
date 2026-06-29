# frozen_string_literal: true

module Variform
  module Support
    module Inflector
      module_function

      def camelize(term)
        term.to_s.split(/[_\s]+/).map { |part| part.empty? ? part : part[0].upcase + part[1..] }.join
      end

      def underscore(term)
        term.to_s
            .gsub(/([A-Z]+)([A-Z][a-z])/, '\1_\2')
            .gsub(/([a-z\d])([A-Z])/, '\1_\2')
            .tr('-', '_')
            .downcase
      end
    end
  end
end
