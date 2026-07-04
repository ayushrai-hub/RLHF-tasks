# frozen_string_literal: true

require "sqlite3"

module StampGate
  class NonceStore
    def self.connect_db(path)
      db = SQLite3::Database.new(path)
      db.busy_timeout = 5000
      db
    end

    def self.seen_before?(db:, issuer:, jti:, alg:)
      count = db.get_first_value(
        "SELECT COUNT(*) FROM nonce_seen WHERE issuer = ? AND jti = ? AND alg = ?",
        [issuer, jti, alg]
      )
      count.to_i.positive?
    end

    def self.record_success(db:, issuer:, jti:, alg:, assertion_id:, recorded_at:)
      db.execute(
        "INSERT INTO nonce_seen (issuer, jti, alg, assertion_id, recorded_at) VALUES (?, ?, ?, ?, ?)",
        [issuer, jti, alg, assertion_id, recorded_at]
      )
    end

    def self.clear_all(db:)
      db.execute("DELETE FROM nonce_seen")
    end

    def self.row_count(db:)
      db.get_first_value("SELECT COUNT(*) FROM nonce_seen").to_i
    end
  end
end
