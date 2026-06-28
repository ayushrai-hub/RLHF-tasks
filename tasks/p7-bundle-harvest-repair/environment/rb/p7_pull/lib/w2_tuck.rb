# frozen_string_literal: true

require "csv"

module W2Tuck
  module_function

  def emit_csv_only(rows, path)
    CSV.open(path, "w") do |csv|
      csv << %w[rec_key route_tmpl prio_band rec_at lat_ms stat_cd]
      rows.each { |r| csv << r.values_at("rec_key", "route_tmpl", "prio_band", "rec_at", "lat_ms", "stat_cd") }
    end
  end
end
