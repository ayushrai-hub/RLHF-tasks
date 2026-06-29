# frozen_string_literal: true

module Variform
  module Validation
    module MethodCatalog
      module_function

      def resizing
        MethodAllowlist::ALLOWED.select { |m| m.include?('resize') || m == 'scale' || m == 'thumbnail' }
      end

      def color
        %w[colorspace grayscale modulate sepia_tone tint negate level gamma].select do |m|
          MethodAllowlist::ALLOWED.include?(m)
        end
      end

      def count
        MethodAllowlist::ALLOWED.size
      end
    end
  end
end
