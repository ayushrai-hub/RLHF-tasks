# frozen_string_literal: true

module Variform
  module Command
    class Plan
      attr_reader :argv

      def initialize(argv)
        @argv = argv
      end

      def to_a
        argv
      end

      def to_s
        argv.join(' ')
      end

      def options
        argv.drop(1)
      end
    end
  end
end
