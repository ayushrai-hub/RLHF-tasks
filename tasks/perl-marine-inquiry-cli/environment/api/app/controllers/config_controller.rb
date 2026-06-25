class ConfigController < ApplicationController
  def show
    rows = db.execute("SELECT key, value FROM config")
    payload = {}
    rows.each do |r|
      payload[r["key"]] = coerce(r["value"])
    end
    render json: payload
  end

  private

  def coerce(v)
    return v unless v.is_a?(String)
    begin
      JSON.parse(v)
    rescue JSON::ParserError
      v
    end
  end
end
