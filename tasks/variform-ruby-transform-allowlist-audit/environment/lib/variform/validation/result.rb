# frozen_string_literal: true

module Variform
  module Validation
    class Result
      attr_reader :transformation, :error

      def initialize(transformation, error: nil)
        @transformation = transformation
        @error = error
      end

      def ok?
        error.nil?
      end

      def to_s
        ok? ? "ok: #{transformation.method_name}" : "rejected: #{error.message}"
      end
    end
  end
end
