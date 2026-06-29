# frozen_string_literal: true

module Variform
  module Geometry
    class Region
      attr_reader :dimensions, :x_offset, :y_offset

      def initialize(dimensions, x_offset, y_offset)
        @dimensions = dimensions
        @x_offset = x_offset
        @y_offset = y_offset
      end

      def self.parse(text)
        dims = Dimensions.parse(text)
        return nil unless dims

        offsets = text.to_s.scan(/([+-]\d+)/).flatten
        new(dims, offsets[0]&.to_i || 0, offsets[1]&.to_i || 0)
      end

      def to_s
        "#{dimensions}#{format('%+d%+d', x_offset, y_offset)}"
      end
    end
  end
end
