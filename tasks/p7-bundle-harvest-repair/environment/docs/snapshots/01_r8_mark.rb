# frozen_string_literal: true

require "net/http"
require "uri"
require "json"

module R8Mark
  module_function

  def hold_mark(batch_stream, retry_policy, dedup_key_fn)
    want_retry = retry_policy.fetch("retry", "false") == "true"
    acc = []
    batch_stream.each { |row| acc << row }

    band = retry_policy.fetch("prio", "")
    acc.concat(supplement_rows(retry_policy)) unless band.empty?

    return acc unless want_retry

    tok = "c7"
    since_t = retry_policy.fetch("since")
    until_t = retry_policy.fetch("until")
    prio = retry_policy.fetch("prio", "")
    uri = URI("http://127.0.0.1:9292/v1/k6/entries?cursor=#{tok}&since=#{since_t}&until=#{until_t}&prio=#{prio}")
    res = Net::HTTP.get_response(uri)
    if res.code.to_i == 503
      res = Net::HTTP.get_response(uri)
    end
    if res.is_a?(Net::HTTPSuccess)
      acc.concat(JSON.parse(res.body).fetch("entries"))
    end
    acc
  end

  def supplement_rows(retry_policy)
    since_t = retry_policy.fetch("since")
    until_t = retry_policy.fetch("until")
    target = retry_policy.fetch("prio", "")
    wide = URI("http://127.0.0.1:9292/v1/k6/entries?cursor=c0&since=#{since_t}&until=#{until_t}&prio=")
    wide_res = Net::HTTP.get_response(wide)
    return [] unless wide_res.is_a?(Net::HTTPSuccess)

    band_map = File.readlines("/app/environment/docs/k6_levels.txt", chomp: true).each_with_object({}) do |ln, h|
      k, v = ln.split("=", 2)
      h[k.to_i] = v
    end
    JSON.parse(wide_res.body).fetch("entries").select do |row|
      band_map[row["priority"].to_i] != target
    end
  end
end
