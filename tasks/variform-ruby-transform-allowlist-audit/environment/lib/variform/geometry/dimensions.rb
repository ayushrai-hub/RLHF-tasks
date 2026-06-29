# frozen_string_literal: true

module Variform
  module Geometry
    class Dimensions
      attr_reader :width, :height

      def initialize(width, height)
        @width = width
        @height = height
      end

      def self.parse(text)
        match = text.to_s.match(/\A(\d+)?x(\d+)?/)
        return nil unless match

        new(match[1]&.to_i, match[2]&.to_i)
      end

      def to_s
        "#{width}x#{height}"
      end
    end
  end
end
