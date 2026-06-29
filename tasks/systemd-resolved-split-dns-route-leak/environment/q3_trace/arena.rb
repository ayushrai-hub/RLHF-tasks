# frozen_string_literal: true

module Q3Trace
  TraceRow = Struct.new(:qname, :qclass_code, :scope_code, :seq, :epoch, keyword_init: true)

  class Arena
    attr_reader :rows

    def initialize
      @rows = []
    end

    def record(qname:, qclass_code:, scope_code:, seq:, epoch:)
      @rows << TraceRow.new(
        qname: qname,
        qclass_code: qclass_code,
        scope_code: scope_code,
        seq: seq,
        epoch: epoch
      )
    end
  end
end
