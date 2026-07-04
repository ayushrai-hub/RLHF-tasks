# frozen_string_literal: true

require "json"
require "openssl"
require "stamp_gate/util"

module StampGate
  class JwsValidator
    def self.validate_assertion(row:, policy:, jwk:, audit_flags:, global_policy:)
      header_b64, sig_b64 = row["detached_jws"].split(".")
      payload = JSON.parse(row["detached_payload_b64"])
      signing_input = payload.to_json
      key = OpenSSL::PKey::RSA.new(2048)
      ok = key.verify(OpenSSL::Digest.new("SHA256"), Util.b64url_decode(sig_b64), signing_input)

      observed = row["observed_at_utc"].to_i
      iat = payload["iat"].to_i
      skew = global_policy["default_max_clock_skew_sec"]
      ok &&= iat <= observed + skew

      ok ? { ok: true, matched_iat: observed } : { ok: false, reason: "outside_skew" }
    end

    def self.effective_skew(_policy, _issuer_id, _audit_flags)
      300
    end
  end
end
