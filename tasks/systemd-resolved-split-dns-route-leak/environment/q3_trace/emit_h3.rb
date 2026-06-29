# frozen_string_literal: true

require_relative "arena"
require_relative "../r7_lane/types"

module Q3Trace
  module EmitH3
    module_function

    def emit_h3(trace_rows, sink)
      ordered = trace_rows.rows.sort_by(&:qname)
      ordered.each do |row|
        sink.puts([row.qname, row.qclass_code, row.scope_code, row.seq, row.epoch].join("\t"))
      end
      ordered.map do |row|
        {
          name_digest: R7Lane::RtPack.name_digest(row.qname),
          qclass_code: row.qclass_code,
          scope_code: row.scope_code,
          seq: row.seq,
          epoch: row.epoch
        }
      end
    end
  end
end

def emit_h3(trace_rows, sink)
  Q3Trace::EmitH3.emit_h3(trace_rows, sink)
end
