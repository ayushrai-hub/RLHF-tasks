# frozen_string_literal: true

require_relative "bands"

module V8Scope
  module StubFold
    module_function

    def flatten_names(band_set)
      band_set.rows.map { |r| r.link_id.to_s }.join(",")
    end
  end
end
