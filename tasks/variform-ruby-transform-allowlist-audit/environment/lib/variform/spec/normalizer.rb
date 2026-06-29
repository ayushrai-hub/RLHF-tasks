# frozen_string_literal: true

module Variform
  module Spec
    module Normalizer
      module_function

      def transformation(entry)
        unless entry.is_a?(Hash)
          raise MalformedSpec, 'transform: malformed transformation spec'
        end

        name = entry['name'] || entry[:name]
        if name.nil? || name.to_s.empty?
          raise MalformedSpec, 'transform: transformation is missing a method name'
        end

        argument = if entry.key?('argument')
                     entry['argument']
                   else
                     entry[:argument]
                   end

        Transformation.new(name, argument)
      end
    end
  end
end
