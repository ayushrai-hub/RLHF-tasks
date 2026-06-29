# frozen_string_literal: true

require_relative "types"

module R7Lane
  module StubMerge
    module_function

    def write_smoke_rows(sink, rows)
      payload = rows.map { |r| [r.iface, r.domain].join(":") }.join("|")
      sink.write(payload)
      payload.bytesize
    end
  end
end
