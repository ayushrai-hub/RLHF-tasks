require "json"
require "pathname"
require "sqlite3"
require "securerandom"

class ApplicationController < ActionController::API
  DB_PATH = ENV.fetch("CASE_DB_PATH", "/app/api/db/case.sqlite3")

  def db
    @db ||= ApplicationController.shared_db
  end

  def self.shared_db
    @shared ||= begin
      conn = SQLite3::Database.new(DB_PATH)
      conn.results_as_hash = true
      conn.busy_timeout = 5000
      conn.execute("PRAGMA foreign_keys = ON")
      conn.execute("PRAGMA journal_mode = WAL")
      conn
    end
  end

  def parse_json(text)
    return nil if text.nil? || text.empty?
    JSON.parse(text)
  end

  def render_not_found(what)
    render json: { error: "not_found", resource: what }, status: 404
  end

  def render_bad(reason, extra = {})
    render json: { error: "bad_request", reason: reason }.merge(extra), status: 422
  end

  def load_body
    raw = request.raw_post.to_s
    return {} if raw.strip.empty?
    JSON.parse(raw)
  rescue JSON::ParserError
    {}
  end
end
