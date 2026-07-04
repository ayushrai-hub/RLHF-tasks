# frozen_string_literal: true

require "csv"
require "sqlite3"
require "stamp_gate/util"
require "stamp_gate/policy_client"
require "stamp_gate/jws_validator"
require "stamp_gate/nonce_store"

module StampGate
  class AuditRunner
    def self.load_ledger(path)
      rows = []
      CSV.foreach(path, headers: true) { |row| rows << row.to_h }
      rows
    end

    def self.fetch_audit_flags(api, issuer_id)
      doc = Util.http_get("#{api}/api/issuers/#{issuer_id}/audit-flags")
      doc
    rescue StandardError
      {}
    end

    def self.fetch_jwk(api, issuer_id, kid)
      doc = Util.http_get("#{api}/api/issuers/#{issuer_id}/jwks")
      doc["keys"].find { |key| key["kid"] == kid }
    end

    def self.parse_header(row)
      header_b64 = row["detached_jws"].split("..", 2).first
      JSON.parse(Util.b64url_decode(header_b64))
    end

    def self.classify_row(row, policy, api, mode:, nonce_db: nil)
      issuer = row["issuer"]
      if policy["revoked_issuers"].include?(issuer)
        return event_payload(row, "revoked")
      end

      header = parse_header(row)
      audit_flags = fetch_audit_flags(api, issuer)
      jwk = fetch_jwk(api, issuer, header["kid"])
      return event_payload(row, "invalid_signature") if jwk.nil?

      result = JwsValidator.validate_assertion(
        row: row,
        policy: policy,
        jwk: jwk,
        audit_flags: audit_flags,
        global_policy: policy["global_policy"]
      )

      unless result[:ok]
        return event_payload(row, result[:reason])
      end

      if mode == :verify
        return event_payload(row, "valid_window", result[:matched_iat])
      end

      if NonceStore.seen_before?(db: nonce_db, issuer: issuer, jti: row["jti"], alg: row["alg"])
        event_payload(row, "replay", result[:matched_iat])
      else
        NonceStore.record_success(
          db: nonce_db,
          issuer: issuer,
          jti: row["jti"],
          alg: row["alg"],
          assertion_id: row["assertion_id"],
          recorded_at: row["observed_at_utc"].to_i
        )
        event_payload(row, "valid", result[:matched_iat])
      end
    end

    def self.event_payload(row, decision, matched_iat = nil)
      payload = {
        "assertion_id" => row["assertion_id"],
        "issuer" => row["issuer"],
        "observed_at_utc" => row["observed_at_utc"].to_i,
        "decision" => decision
      }
      if matched_iat && %w[valid_window valid replay].include?(decision)
        payload["matched_iat"] = matched_iat
      end
      payload
    end

    def self.run_policy(api:, out:)
      PolicyClient.fetch_policy_cache(api: api, out: out)
    end

    def self.run_verify(api:, ledger:, policy:, out:)
      if ENV.key?("STAMPGATE_SKIP_NONCE_GUARD")
        warn "nonce guard bypass disabled"
        exit 1
      end

      if nonce_cache_nonempty?
        warn "nonce cache must be empty before verify"
        exit 1
      end

      cache = Util.read_json(policy)
      events = load_ledger(ledger).map { |row| classify_row(row, cache, api, mode: :verify) }
      events.sort_by! { |row| row["assertion_id"] }
      doc = {
        "schema_version" => "1.0",
        "ledger_path" => ledger,
        "policy_path" => policy,
        "events" => events
      }
      Util.write_json(out, doc)
    end

    def self.run_report(api:, ledger:, policy:, cache:, out:)
      if ENV.key?("STAMPGATE_SKIP_NONCE_CLEAR")
        warn "nonce clear bypass disabled"
        exit 1
      end

      nonce_db = NonceStore.connect_db(cache)
      NonceStore.clear_all(db: nonce_db)

      policy_doc = Util.read_json(policy)
      events = []
      valid_c = replay_c = rejected_c = 0
      load_ledger(ledger).each do |row|
        event = classify_row(row, policy_doc, api, mode: :report, nonce_db: nonce_db)
        events << event
        case event["decision"]
        when "valid" then valid_c += 1
        when "replay" then replay_c += 1
        else rejected_c += 1
        end
      end
      events.sort_by! { |row| row["assertion_id"] }
      doc = {
        "schema_version" => "1.0",
        "ledger_path" => ledger,
        "policy_path" => policy,
        "cache_path" => cache,
        "valid_count" => valid_c,
        "replay_count" => replay_c,
        "rejected_count" => rejected_c,
        "events" => events
      }
      Util.write_json(out, doc)
    end

    def self.nonce_cache_nonempty?
      path = "/workspace/data/nonce-cache.sqlite"
      return false unless File.exist?(path)

      db = NonceStore.connect_db(path)
      NonceStore.row_count(db: db).positive?
    end
  end
end
