# frozen_string_literal: true
#
# Output bundle under /app/output/p7_bundle/ carries per-profile CSV files,
# bundle.db table k6_facts, and rollup.toml groups.
#
# Route path collapse for route_tmpl:
#   Split route_path on "/" and replace every all-digit segment with "{n}".
#
# Rollup per route_tmpl group from k6_facts rows in the active population:
#   req_total  — row count in the group
#   err_share  — fraction of rows where stat_cd != 200
#   tail_p95_ms — 95th percentile of lat_ms (nearest-rank on sorted values)
#
# bundle_digest in rollup.toml:
#   1. Sort route_tmpl keys ascending.
#   2. For each group emit: route_tmpl|req_total|err_share|tail_p95_ms
#        where err_share is formatted with six digits after the decimal point.
#   3. Join segments with newline.
#   4. Accumulate ((idx + 1) * ord(ch)) mod 2**64 across the payload.
#   5. Emit the low 32 bits as eight lowercase hex digits.

require "csv"
require "sqlite3"
require "time"

module B3Stat
  module_function

  def fold_stat(rows, sink_cfg, rollup_header)
    _ = rollup_header
    root = sink_cfg.fetch(:root)
    prof = sink_cfg.fetch(:profile)
    db = sink_cfg.fetch(:db)
    prof_id = prof.fetch("id")

    band_map = load_band_map
    shaped = rows.map { |r| shape_row(r, band_map) }
    csv_path = File.join(root, "#{prof_id}.csv")
    write_csv(csv_path, shaped, utc: true)
    shaped.each { |r| persist_row(db, r) }
    reduce_groups(shaped)
  end

  def persist_row(db, row)
    utc_at = aligned_rec_at(row["rec_at"])
    db.execute(
      "INSERT OR REPLACE INTO k6_facts VALUES (?,?,?,?,?,?)",
      [row["rec_key"], row["route_tmpl"], row["prio_band"], utc_at, row["lat_ms"], row["stat_cd"]]
    )
  end

  def aligned_rec_at(value)
    Time.parse(value).utc.iso8601
  end

  def load_band_map
    File.readlines("/app/environment/docs/k6_levels.txt", chomp: true).each_with_object({}) do |ln, h|
      k, v = ln.split("=", 2)
      h[k.to_i] = v
    end
  end

  def shape_row(raw, band_map)
    route = raw["route_path"] || raw["route"]
    {
      "rec_key" => raw["rec_key"],
      "route_tmpl" => collapse_route(route),
      "prio_band" => band_map[raw["priority"].to_i] || "unknown",
      "rec_at" => raw["recorded_at"],
      "lat_ms" => raw["lat_ms"].to_i,
      "stat_cd" => raw["status_code"].to_i
    }
  end

  def collapse_route(path)
    path.split("/").map { |seg| seg.match?(/\A\d+\z/) ? "{n}" : seg }.join("/")
  end

  def write_csv(path, rows, utc:)
    CSV.open(path, "w") do |csv|
      csv << %w[rec_key route_tmpl prio_band rec_at lat_ms stat_cd]
      rows.each do |r|
        at = Time.parse(r["rec_at"])
        at = at.utc if utc
        csv << [r["rec_key"], r["route_tmpl"], r["prio_band"], at.iso8601, r["lat_ms"], r["stat_cd"]]
      end
    end
  end

  def reduce_groups(rows)
    pool = rows
    by = pool.group_by { |r| r["route_tmpl"] }
    by.transform_values do |grp|
      total = grp.length
      errs = grp.count { |r| r["stat_cd"] != 200 }
      share = total.zero? ? 0.0 : errs.to_f / total
      lats = grp.map { |r| r["lat_ms"] }.sort
      p95 = percentile(lats, 95)
      { "req_total" => total, "err_share" => share, "tail_p95_ms" => p95 }
    end
  end

  def groups_from_db(db)
    rows = db.execute("SELECT rec_key, route_tmpl, prio_band, rec_at, lat_ms, stat_cd FROM k6_facts").map do |r|
      {
        "rec_key" => r[0],
        "route_tmpl" => r[1],
        "prio_band" => r[2],
        "rec_at" => r[3],
        "lat_ms" => r[4],
        "stat_cd" => r[5]
      }
    end
    reduce_groups(rows)
  end

  def percentile(sorted, pct)
    return 0 if sorted.empty?

    rank = ((pct / 100.0) * sorted.length).ceil - 1
    sorted[[rank, 0].max]
  end

  def bundle_digest(groups)
    parts = groups.sort_by { |k, _| k }.map do |tmpl, g|
      share = format("%.6f", g["err_share"])
      "#{tmpl}|#{g['req_total']}|#{share}|#{g['tail_p95_ms']}"
    end
    payload = parts.join("\n")
    mask64 = (1 << 64) - 1
    total = 0
    payload.each_char.with_index do |ch, idx|
      total = (total + ((idx + 1) * ch.ord)) & mask64
    end
    format("%08x", total & 0xFFFFFFFF)
  end

  def write_rollup(path, groups)
    digest = bundle_digest(groups)
    lines = ["bundle_digest = \"#{digest}\""]
    groups.sort_by { |k, _| k }.each do |tmpl, g|
      share = format("%.6f", g["err_share"])
      lines << "[groups.\"#{tmpl}\"]"
      lines << "req_total = #{g['req_total']}"
      lines << "err_share = #{share}"
      lines << "tail_p95_ms = #{g['tail_p95_ms']}"
    end
    File.write(path, lines.join("\n") + "\n")
    digest
  end
end
