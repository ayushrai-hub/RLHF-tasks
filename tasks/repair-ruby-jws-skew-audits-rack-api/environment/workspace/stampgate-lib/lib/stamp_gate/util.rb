# frozen_string_literal: true

require "json"
require "net/http"
require "uri"

module StampGate
  module Util
    module_function

    def http_get(url)
      uri = URI(url)
      response = Net::HTTP.get_response(uri)
      raise "http error #{response.code} for #{url}" unless response.is_a?(Net::HTTPSuccess)

      JSON.parse(response.body)
    end

    def read_json(path)
      JSON.parse(File.read(path))
    end

    def write_json(path, doc)
      File.write(path, JSON.pretty_generate(doc) + "\n")
    end

    def b64url_decode(str)
      pad = "=" * ((4 - str.length % 4) % 4)
      Base64.urlsafe_decode64(str + pad)
    end
  end
end

require "base64"
