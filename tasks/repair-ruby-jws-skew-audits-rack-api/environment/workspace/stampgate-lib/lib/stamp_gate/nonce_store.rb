# frozen_string_literal: true

require "sqlite3"

module StampGate
  class NonceStore
    def self.connect_db(path)
      SQLite3::Database.new(path)
    end

    def self.seen_before?(*)
      false
    end

    def self.record_success(*)
      0
    end

    def self.clear_all(*)
      0
    end

    def self.row_count(*)
      0
    end
  end
end
