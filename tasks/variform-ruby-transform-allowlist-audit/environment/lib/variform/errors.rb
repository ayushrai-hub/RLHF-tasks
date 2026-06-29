# frozen_string_literal: true

module Variform
  class Error < StandardError; end

  class MalformedSpec < Error; end

  class UnsupportedTransformation < Error; end

  class UnknownProcessor < Error; end
end
