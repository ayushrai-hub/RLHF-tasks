# frozen_string_literal: true

module N4Cache
  NegEntry = Struct.new(:qname, :link_epoch, :seen_at, keyword_init: true)

  class Bucket
    attr_reader :entries

    def initialize
      @entries = []
    end

    def remember(qname:, link_epoch:)
      @entries << NegEntry.new(qname: qname, link_epoch: link_epoch, seen_at: Time.now.to_i)
    end

    def active_for(qname, current_epoch)
      @entries.select { |e| e.qname == qname && e.link_epoch <= current_epoch }
    end
  end
end
