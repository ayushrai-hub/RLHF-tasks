# frozen_string_literal: true

require "json"
require "open3"
require "stamp_gate/util"

module StampGate
  class JwsValidator
    HELPER = "/tmp/stampgate-oracle-jws-verify.py"

    def self.validate_assertion(row:, policy:, jwk:, audit_flags:, global_policy:)
      jti = row["jti"]
      min_len = global_policy["require_jti_min_length"]
      return { ok: false, reason: "invalid_jti" } if jti.nil? || jti.length < min_len

      parts = row["detached_jws"].split("..", 2)
      return { ok: false, reason: "invalid_signature" } unless parts.length == 2

      header_b64, sig_b64 = parts
      payload_b64 = row["detached_payload_b64"]
      header = JSON.parse(Util.b64url_decode(header_b64))
      payload = JSON.parse(Util.b64url_decode(payload_b64))

      expected_iss = "#{global_policy['issuer_prefix']}#{row['issuer']}"
      return { ok: false, reason: "invalid_signature" } if payload["iss"] != expected_iss

      return { ok: false, reason: "invalid_signature" } if jwk.nil?
      return { ok: false, reason: "alg_mismatch" } if header["alg"] != jwk["alg"]
      return { ok: false, reason: "alg_mismatch" } if header["alg"] != row["alg"]
      return { ok: false, reason: "invalid_signature" } unless verify_signature(header["alg"], header_b64, payload_b64, sig_b64, jwk)

      observed = row["observed_at_utc"].to_i
      iat = payload["iat"].to_i
      nbf = payload.key?("nbf") ? payload["nbf"].to_i : iat
      return { ok: false, reason: "outside_skew" } if nbf > observed

      skew = effective_skew(policy, row["issuer"], audit_flags)
      if audit_flags["require_exact_iat"]
        return { ok: false, reason: "outside_skew" } unless iat == observed
      elsif (observed - iat).abs > skew
        return { ok: false, reason: "outside_skew" }
      end

      { ok: true, matched_iat: iat }
    end

    def self.effective_skew(policy, issuer_id, audit_flags)
      return 0 if audit_flags["require_exact_iat"]

      override = policy["issuer_overrides"][issuer_id]
      return override["max_clock_skew_sec"] if override && override.key?("max_clock_skew_sec")

      policy["global_policy"]["default_max_clock_skew_sec"]
    end

    def self.verify_signature(alg, header_b64, payload_b64, sig_b64, jwk)
      payload = {
        alg: alg,
        header_b64: header_b64,
        payload_b64: payload_b64,
        sig_b64: sig_b64,
        jwk: jwk
      }
      stdout, _stderr, status = Open3.capture3(
        "python3", HELPER,
        stdin_data: JSON.generate(payload)
      )
      status.success? && stdout.strip == "ok"
    end
  end
end
