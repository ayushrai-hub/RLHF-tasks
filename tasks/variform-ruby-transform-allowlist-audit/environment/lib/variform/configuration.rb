# frozen_string_literal: true

module Variform
  class Configuration
    attr_accessor :default_processor

    def initialize
      @default_processor = 'magick'
    end
  end

  class << self
    def configuration
      @configuration ||= Configuration.new
    end

    def configure
      yield configuration
      configuration
    end
  end
end
