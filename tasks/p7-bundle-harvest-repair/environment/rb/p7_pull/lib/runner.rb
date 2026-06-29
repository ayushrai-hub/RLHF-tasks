# frozen_string_literal: true

require_relative "t4_lane"
require_relative "../../../net/r8_mark"
require_relative "b3_stat"
require_relative "m9_index"

class Runner
  HTTP = "http://127.0.0.1:9292"
  OUT = "/app/output/p7_bundle"

  def initialize(table_path)
    @table_path = table_path
    @corpus = File.dirname(table_path)
  end

  def run
    profiles = load_profiles(@table_path)
    M9Index.build(profiles, @corpus)
    Dir.mkdir(OUT) unless Dir.exist?(OUT)
    db_path = File.join(OUT, "bundle.db")
    File.delete(db_path) if File.exist?(db_path)
    db = SQLite3::Database.new(db_path)
    db.execute(
      "CREATE TABLE k6_facts (rec_key TEXT PRIMARY KEY, route_tmpl TEXT, prio_band TEXT, rec_at TEXT, lat_ms INTEGER, stat_cd INTEGER)"
    )

    profiles.each do |prof|
      stream = T4Lane.shift_lane(HTTP, prof, nil)
      rows = R8Mark.hold_mark(stream, prof, method(:key_fn))
      B3Stat.fold_stat(rows, { root: OUT, profile: prof, db: db }, rollup_hd)
    end
    groups = B3Stat.groups_from_db(db)
    B3Stat.write_rollup(File.join(OUT, "rollup.toml"), groups)
    M9Index.export_diag(@corpus, profiles.length)
    db.close
  end

  private

  def rollup_hd
    File.read("/app/environment/rb/p7_pull/lib/b3_stat.rb").lines.take(22).join
  end

  def key_fn(row)
    row["rec_key"]
  end

  def load_profiles(path)
    current = {}
    out = []
    File.readlines(path, chomp: true).each do |ln|
      next if ln.strip.empty?

      if ln.start_with?("[[profiles]]")
        out << current unless current.empty?
        current = {}
        next
      end
      k, v = ln.split("=", 2).map(&:strip)
      next unless k && v

      current[k] = v.delete_prefix('"').delete_suffix('"')
    end
    out << current unless current.empty?
    out
  end
end

require "sqlite3"
