# frozen_string_literal: true

module Variform
  class Blob
    attr_reader :key, :filename, :content_type, :byte_size

    def initialize(key:, filename:, content_type:, byte_size: 0)
      @key = key
      @filename = filename
      @content_type = content_type
      @byte_size = byte_size
    end

    def image?
      content_type.to_s.start_with?('image/')
    end

    def extension
      File.extname(filename.to_s).delete_prefix('.')
    end
  end
end
