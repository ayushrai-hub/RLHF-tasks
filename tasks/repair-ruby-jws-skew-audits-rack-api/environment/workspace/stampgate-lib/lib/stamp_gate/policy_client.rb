# frozen_string_literal: true

require "json"
require "stamp_gate/util"

module StampGate
  class PolicyClient
    def self.fetch_policy_cache(api:, out:)
      defaults = Util.read_json("/workspace/config/jwks.defaults.json")
      legacy = Util.http_get("#{api}/api/v2/jwks")
      issuers = Util.http_get("#{api}/api/issuers")

      active = issuers.map { |row| row["issuer_id"] }.sort
      doc = {
        "schema_version" => "1.0",
        "api_base" => api,
        "global_policy" => {
          "allowed_algorithms" => ["HS256"],
          "default_max_clock_skew_sec" => 300,
          "require_jti_min_length" => 3,
          "issuer_prefix" => legacy["issuer"]
        },
        "active_issuers" => active,
        "revoked_issuers" => [],
        "issuer_overrides" => {},
        "decoy_keys" => defaults["keys"]
      }

      Util.write_json(out, doc)
      doc
    end
  end
end
