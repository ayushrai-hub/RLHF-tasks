require_relative "config/environment"
require "fileutils"
require "sqlite3"

# Two-layer per-request audit. The file log at /app/state/rails.log is the
# environment-fact the spec names; the SQLite table at
# /app/state/api-audit.sqlite3 is the verifier-only signal that survives
# agent-side file hygiene (rm -rf /app/state/*, log truncation, etc.) and
# launcher variance (custom rails-server, RAILS_LOG_TO_STDOUT, replaced
# Rails Logger). Every Rack request goes through this middleware before
# Rails routing, regardless of how the agent booted Rails.
class RequestPathLogger
  AUDIT_DB = "/app/state/api-audit.sqlite3".freeze

  def initialize(app, log_path)
    @app = app
    @log_path = log_path
    @db_ready = false
    @mutex = Mutex.new
  end

  def ensure_audit_db
    return if @db_ready
    @mutex.synchronize do
      return if @db_ready
      FileUtils.mkdir_p(File.dirname(AUDIT_DB))
      db = SQLite3::Database.new(AUDIT_DB)
      db.execute(
        "CREATE TABLE IF NOT EXISTS audit_requests (" \
        "ts REAL NOT NULL, method TEXT NOT NULL, path TEXT NOT NULL)"
      )
      db.close
      @db_ready = true
    end
  end

  def call(env)
    method = env["REQUEST_METHOD"]
    path = env["PATH_INFO"]

    begin
      dir = File.dirname(@log_path)
      Dir.mkdir(dir) unless Dir.exist?(dir)
      File.open(@log_path, "a") do |f|
        f.write("Started #{method} \"#{path}\"\n")
        f.fsync
      end
    rescue StandardError
    end

    begin
      ensure_audit_db
      db = SQLite3::Database.new(AUDIT_DB)
      begin
        db.execute(
          "INSERT INTO audit_requests (ts, method, path) VALUES (?, ?, ?)",
          [Time.now.to_f, method.to_s, path.to_s]
        )
      ensure
        db.close
      end
    rescue StandardError
    end

    @app.call(env)
  end
end

use RequestPathLogger, "/app/state/rails.log"
run Rails.application
