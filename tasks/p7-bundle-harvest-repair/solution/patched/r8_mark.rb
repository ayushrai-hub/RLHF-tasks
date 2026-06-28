# frozen_string_literal: true

require "net/http"
require "uri"
require "json"

module R8Mark
  module_function

  def hold_mark(batch_stream, retry_policy, dedup_key_fn)
    want_retry = retry_policy.fetch("retry", "false") == "true"
    seen = {}
    acc = absorb_unique([], seen, batch_stream, dedup_key_fn)

    return acc unless want_retry

    retry_glitch_batch(retry_policy, seen, dedup_key_fn, acc)
  end

  def absorb_unique(acc, seen, rows, dedup_key_fn)
    rows.each do |row|
      k = dedup_key_fn.call(row)
      next if seen[k]

      seen[k] = true
      acc << row
    end
    acc
  end

  def retry_glitch_batch(policy, seen, dedup_key_fn, acc)
    tok = "c7"
    since_t = policy.fetch("since")
    until_t = policy.fetch("until")
    band = policy.fetch("prio", "")
    uri = glitch_uri(tok, since_t, until_t, band)
    res = Net::HTTP.get_response(uri)
    if res.code.to_i == 503
      res2 = Net::HTTP.get_response(uri)
      if res2.is_a?(Net::HTTPSuccess)
        body = JSON.parse(res2.body)
        absorb_unique(acc, seen, body.fetch("entries"), dedup_key_fn)
      end
    end
    acc
  end

  def glitch_uri(tok, since_t, until_t, band)
    URI("http://127.0.0.1:9292/v1/k6/entries?cursor=#{tok}&since=#{since_t}&until=#{until_t}&prio=#{band}")
  end
end
