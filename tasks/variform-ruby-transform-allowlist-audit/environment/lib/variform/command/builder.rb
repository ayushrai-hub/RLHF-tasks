# frozen_string_literal: true

module Variform
  module Command
    module Builder
      module_function

      def build(transformations, processor: 'magick')
        argv = [processor.to_s]
        transformations.each do |transformation|
          argv.concat(Tokenizer.split("-#{transformation.method_name}"))
          argv.concat(argument_tokens(transformation.argument))
        end
        Plan.new(argv)
      end

      def argument_tokens(argument)
        case argument
        when nil
          []
        when Integer, Float
          [argument.to_s]
        when true, false
          [argument.to_s]
        when String, Symbol
          Tokenizer.split(argument.to_s)
        when Array
          argument.flat_map { |element| argument_tokens(element) }
        when Hash
          argument.flat_map { |key, value| Tokenizer.split(key.to_s) + argument_tokens(value) }
        else
          Tokenizer.split(argument.to_s)
        end
      end
    end
  end
end
