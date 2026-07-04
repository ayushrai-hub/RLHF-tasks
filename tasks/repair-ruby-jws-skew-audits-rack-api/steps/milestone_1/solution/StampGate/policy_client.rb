# frozen_string_literal: true

require "json"
require "stamp_gate/util"

module StampGate
  class PolicyClient
    def self.fetch_policy_cache(api:, out:)
      if ENV.key?("STAMPGATE_USE_STATIC_POLICY")
        warn "static policy bypass disabled"
        exit 1
      end

      policy = Util.http_get("#{api}/api/policy")
      issuers = Util.http_get("#{api}/api/issuers")

      active = []
      revoked = []
      overrides = {}

      issuers.each do |row|
        case row["status"]
        when "active"
          active << row["issuer_id"]
          if row.key?("skew_override")
            overrides[row["issuer_id"]] = { "max_clock_skew_sec" => row["skew_override"] }
          end
        when "revoked"
          revoked << row["issuer_id"]
        end
      end

      doc = {
        "schema_version" => "1.0",
        "api_base" => api,
        "global_policy" => policy,
        "active_issuers" => active.sort,
        "revoked_issuers" => revoked.sort,
        "issuer_overrides" => overrides,
        "issuer_count" => active.length,
        "revoked_count" => revoked.length,
        "policy_sources" => ["/api/policy", "/api/issuers"]
      }

      Util.write_json(out, doc)
      doc
    end
  end
end
