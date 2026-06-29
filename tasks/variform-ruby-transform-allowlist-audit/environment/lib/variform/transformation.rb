# frozen_string_literal: true

module Variform
  class Transformation
    attr_reader :name, :argument

    def initialize(name, argument = nil)
      @name = name
      @argument = argument
    end

    def method_name
      name.to_s
    end

    def argument?
      !argument.nil?
    end

    def to_h
      { 'name' => name, 'argument' => argument }
    end
  end
end
