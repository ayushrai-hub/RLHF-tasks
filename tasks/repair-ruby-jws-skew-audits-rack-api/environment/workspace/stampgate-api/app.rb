#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "sqlite3"
require "webrick"

DB_PATH = "/workspace/data/stampgate-policy.sqlite"
DB_MUTEX = Mutex.new

def connect_db
  db = SQLite3::Database.new(DB_PATH)
  db.results_as_hash = true
  db
end

def with_db
  DB_MUTEX.synchronize do
    db = connect_db
    yield db
  end
end

class StampGateApiServlet < WEBrick::HTTPServlet::AbstractServlet
  def do_GET(request, response)
    path = request.path
    case path
    when "/health"
      response.status = 200
      response["Content-Type"] = "application/json"
      response.body = { "status" => "ok", "service" => "stampgate" }.to_json
    when "/api/policy"
      with_db do |db|
        row = db.execute("SELECT * FROM policy WHERE id = 1").first
        allowed = JSON.parse(row["allowed_algorithms"])
        response.status = 200
        response["Content-Type"] = "application/json"
        response.body = {
          "allowed_algorithms" => allowed,
          "default_max_clock_skew_sec" => row["default_max_clock_skew_sec"],
          "require_jti_min_length" => row["require_jti_min_length"],
          "issuer_prefix" => row["issuer_prefix"]
        }.to_json
      end
    when "/api/v2/jwks"
      response.status = 200
      response["Content-Type"] = "application/json"
      response.body = { "keys" => [], "issuer" => "stampgate-legacy", "status" => "deprecated" }.to_json
    when "/api/issuers"
      with_db do |db|
        rows = db.execute("SELECT issuer_id, status, skew_override FROM issuers ORDER BY issuer_id")
        payload = rows.map do |row|
          item = { "issuer_id" => row["issuer_id"], "status" => row["status"] }
          item["skew_override"] = row["skew_override"] unless row["skew_override"].nil?
          item
        end
        response.status = 200
        response["Content-Type"] = "application/json"
        response.body = payload.to_json
      end
    else
      if path.start_with?("/api/issuers/") && path.end_with?("/jwks")
        issuer_id = path.split("/")[3].encode("UTF-8")
        with_db do |db|
          row = db.get_first_row("SELECT status FROM issuers WHERE issuer_id = ?", issuer_id)
          unless row
            response.status = 404
            response["Content-Type"] = "application/json"
            response.body = { "error" => "unknown_issuer" }.to_json
            next
          end
          if row["status"] != "active"
            response.status = 404
            response["Content-Type"] = "application/json"
            response.body = { "error" => "issuer_unavailable", "issuer_id" => issuer_id }.to_json
            next
          end
          keys = db.execute(
            "SELECT kid, alg, jwk_json FROM issuer_keys WHERE issuer_id = ? ORDER BY kid",
            issuer_id
          )
          response.status = 200
          response["Content-Type"] = "application/json"
          response.body = {
            "issuer_id" => issuer_id,
            "keys" => keys.map { |entry| JSON.parse(entry["jwk_json"]) }
          }.to_json
        end
      elsif path.start_with?("/api/issuers/") && path.end_with?("/audit-flags")
        issuer_id = path.split("/")[3].encode("UTF-8")
        with_db do |db|
          row = db.get_first_row(
            "SELECT require_exact_iat FROM issuer_flags WHERE issuer_id = ?",
            issuer_id
          )
          unless row
            response.status = 404
            response["Content-Type"] = "application/json"
            response.body = { "error" => "no_audit_flags" }.to_json
            next
          end
          response.status = 200
          response["Content-Type"] = "application/json"
          response.body = {
            "issuer_id" => issuer_id,
            "require_exact_iat" => row["require_exact_iat"].to_i == 1
          }.to_json
        end
      else
        response.status = 404
        response["Content-Type"] = "application/json"
        response.body = { "error" => "not_found" }.to_json
      end
    end
  end
end

if $PROGRAM_NAME == __FILE__
  server = WEBrick::HTTPServer.new(
    BindAddress: "0.0.0.0",
    Port: 8966,
    Logger: WEBrick::Log.new($stderr, WEBrick::Log::WARN),
    AccessLog: []
  )
  server.mount "/", StampGateApiServlet
  trap("INT") { server.shutdown }
  server.start
end
