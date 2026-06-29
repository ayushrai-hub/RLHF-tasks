# frozen_string_literal: true

require "digest"

module R7Lane
  LaneRow = Struct.new(:iface, :domain, :epoch, keyword_init: true)

  class LaneView
    attr_reader :rows, :current_epoch

    def initialize
      @rows = []
      @current_epoch = 0
    end

    def restore_epoch(value)
      @current_epoch = value
    end

    def attach(iface:, domain:, bump: false)
      @current_epoch += 1 if bump
      @rows << LaneRow.new(iface: iface, domain: domain, epoch: @current_epoch)
      @current_epoch
    end

    def detach(iface:)
      @rows.reject! { |r| r.iface == iface }
    end
  end

  module RtPack
    MAGIC = "RTv1"
    ROW_SIZE = 32
    HEADER_SIZE = 16

    module_function

    def name_digest(qname)
      Digest::SHA256.digest(qname)[0, 16]
    end

    def pack_header(epoch:, link_id:, band_class:, row_count:)
      MAGIC.b + [epoch, link_id, band_class, row_count].pack("NnnN")
    end

    def pack_row(qname:, qclass_code:, scope_code:, seq:, epoch:)
      name_digest(qname) + [qclass_code, scope_code, seq, 0].pack("NNNN")
    end

    def canonical_bytes(header:, rows:)
      sorted = rows.sort_by { |r| [r[:epoch], r[:seq], r[:name_digest]] }
      body = sorted.map do |r|
        r[:name_digest] + [r[:qclass_code], r[:scope_code], r[:seq], 0].pack("NNNN")
      end.join
      header + body
    end

    def digest_hex(bytes)
      Digest::SHA256.hexdigest(bytes)
    end
  end
end
