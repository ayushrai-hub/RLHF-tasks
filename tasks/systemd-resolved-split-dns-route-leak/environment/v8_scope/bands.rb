# frozen_string_literal: true

module V8Scope
  BandRow = Struct.new(:link_id, :downgrade_level, keyword_init: true)

  class BandSet
    attr_reader :rows

    def initialize
      @rows = []
    end

    def push(link_id:, downgrade_level:)
      @rows << BandRow.new(link_id: link_id, downgrade_level: downgrade_level)
    end

    def max_level
      @rows.map(&:downgrade_level).max || 0
    end
  end
end
