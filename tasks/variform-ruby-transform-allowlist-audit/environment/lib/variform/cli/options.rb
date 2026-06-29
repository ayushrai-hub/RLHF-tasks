# frozen_string_literal: true

module Variform
  module CLI
    class Options
      attr_reader :command, :input, :processor

      def initialize(command:, input:, processor:)
        @command = command
        @input = input
        @processor = processor
      end

      def self.parse(argv)
        args = argv.dup
        command = args.shift
        processor = Variform.configuration.default_processor
        rest = []
        until args.empty?
          token = args.shift
          case token
          when '--processor' then processor = args.shift
          else rest << token
          end
        end
        new(command: command, input: rest.first, processor: processor)
      end

      def read_source
        if input
          File.read(input)
        else
          $stdin.read
        end
      end
    end
  end
end
