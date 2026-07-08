# frozen_string_literal: true

require "json"
require "rack"
require_relative "transparency_cli"

class TransparencyApp
  def call(env)
    req = Rack::Request.new(env)
    if req.get? && req.path =~ %r{\A/receipts/([^/]+)\z}
      seq = Regexp.last_match(1)
      body = { receipt_id: receipt_id_for(seq), seq: seq }
      [200, { "Content-Type" => "application/json" }, [JSON.generate(body)]]
    elsif req.post? && req.path == "/ledger/validate"
      payload = JSON.parse(req.body.read)
      row = payload.fetch("csv_row")
      ok = verify_row(row).zero?
      [200, { "Content-Type" => "application/json" }, [JSON.generate({ valid: ok })]]
    elsif req.get? && req.path == "/ledger/root"
      [200, { "Content-Type" => "application/json" }, [JSON.generate({ root: chain_root })]]
    else
      [404, { "Content-Type" => "application/json" }, [JSON.generate({ error: "not found" })]]
    end
  end
end
