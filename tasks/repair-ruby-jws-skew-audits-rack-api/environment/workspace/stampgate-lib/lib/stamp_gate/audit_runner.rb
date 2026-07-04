# frozen_string_literal: true

require "csv"
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

    def self.run_policy(api:, out:)
      PolicyClient.fetch_policy_cache(api: api, out: out)
    end

    def self.run_verify(api:, ledger:, policy:, out:)
      cache = Util.read_json(policy)
      events = load_ledger(ledger).map do |row|
        issuer = row["issuer"]
        decision = cache["revoked_issuers"].include?(issuer) ? "revoked" : "valid_window"
        {
          "assertion_id" => row["assertion_id"],
          "issuer" => issuer,
          "observed_at_utc" => row["observed_at_utc"].to_i,
          "decision" => decision
        }
      end
      doc = {
        "schema_version" => "1.0",
        "ledger_path" => ledger,
        "policy_path" => policy,
        "events" => events
      }
      Util.write_json(out, doc)
    end

    def self.run_report(api:, ledger:, policy:, cache:, out:)
      cache_doc = Util.read_json(policy)
      events = load_ledger(ledger).map do |row|
        {
          "assertion_id" => row["assertion_id"],
          "issuer" => row["issuer"],
          "observed_at_utc" => row["observed_at_utc"].to_i,
          "decision" => "valid"
        }
      end
      doc = {
        "schema_version" => "1.0",
        "ledger_path" => ledger,
        "policy_path" => policy,
        "cache_path" => cache,
        "events" => events
      }
      Util.write_json(out, doc)
    end
  end
end
