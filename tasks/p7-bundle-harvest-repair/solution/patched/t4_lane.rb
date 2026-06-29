# frozen_string_literal: true

require "net/http"
require "json"
require "uri"
require "time"

module T4Lane
  PAGE_SLICE = 4

  module_function

  def shift_lane(api_base, table_cfg, cursor_hdr)
    since_t = table_cfg.fetch("since")
    until_t = table_cfg.fetch("until")
    band = table_cfg.fetch("prio", "")
    tok = cursor_hdr || "c0"
    Enumerator.new do |y|
      loop do
        uri = build_entries_uri(api_base, since_t, until_t, band, tok)
        res = Net::HTTP.start(uri.hostname, uri.port) { |http| http.get(uri.request_uri) }
        raise "pull failed #{res.code}" unless res.is_a?(Net::HTTPSuccess)

        body = JSON.parse(res.body)
        batch = body.fetch("entries")
        emit_batch(batch, until_t) { |row| y << row }
        hdr_tok = res["X-Next-Cursor"].to_s
        tok = pick_next_token(body, hdr_tok)
        break if stop_walking?(batch, tok)
      end
    end
  end

  def build_entries_uri(api_base, since_t, until_t, band, tok)
    uri = URI("#{api_base}/v1/k6/entries")
    uri.query = URI.encode_www_form(
      since: since_t,
      until: until_t,
      prio: band,
      cursor: tok
    )
    uri
  end

  def emit_batch(batch, until_t)
    batch.each do |row|
      yield row if row_in_window?(row, until_t)
    end
  end

  def row_in_window?(row, until_t)
    Time.iso8601(row["recorded_at"]) < Time.iso8601(until_t)
  end

  def pick_next_token(body, hdr_tok)
    return hdr_tok.to_s unless hdr_tok.to_s.empty?

    body["next_token"].to_s
  end

  def stop_walking?(batch, tok)
    batch.empty? || tok.empty?
  end
end
