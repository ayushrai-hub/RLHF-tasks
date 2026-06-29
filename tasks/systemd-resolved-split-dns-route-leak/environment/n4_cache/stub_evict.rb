# frozen_string_literal: true

require_relative "bucket"

module N4Cache
  module StubEvict
    TTL_SEC = 3600

    module_function

    def trim_ttl(bucket)
      cutoff = Time.now.to_i - TTL_SEC
      bucket.entries.reject! { |e| e.seen_at < cutoff }
      bucket.entries.size
    end
  end
end
