# frozen_string_literal: true

module Variform
  class TransformationSet
    include Enumerable

    attr_reader :transformations

    def initialize(transformations = [])
      @transformations = transformations
    end

    def each(&block)
      return to_enum(:each) unless block_given?

      transformations.each(&block)
    end

    def size
      transformations.size
    end

    def empty?
      transformations.empty?
    end

    def names
      transformations.map(&:method_name)
    end

    def to_a
      transformations.map(&:to_h)
    end
  end
end
