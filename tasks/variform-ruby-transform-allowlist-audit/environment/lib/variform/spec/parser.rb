# frozen_string_literal: true

require 'json'

module Variform
  module Spec
    module Parser
      module_function

      def parse(source)
        data = decode(source)

        unless data.is_a?(Array)
          raise MalformedSpec, 'transform: malformed transformation spec'
        end

        TransformationSet.new(data.map { |entry| Normalizer.transformation(entry) })
      end

      def decode(source)
        JSON.parse(source.to_s)
      rescue JSON::ParserError
        raise MalformedSpec, 'transform: malformed transformation spec'
      end
    end
  end
end
