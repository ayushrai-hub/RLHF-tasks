class HealthController < ApplicationController
  def show
    row = db.get_first_row("SELECT value FROM config WHERE key = 'schema_version'")
    render json: { ok: true, service: "case-api", schema_version: row && row["value"] }
  end
end
