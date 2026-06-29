# frozen_string_literal: true

module Variform
  class Variant
    attr_reader :blob, :transformations

    def initialize(blob, transformations)
      @blob = blob
      @transformations = transformations
    end

    def self.from_json(blob, source)
      new(blob, Spec::Parser.parse(source))
    end

    def digest
      blob.key.to_s + ':' + transformations.names.join('|')
    end
  end
end
