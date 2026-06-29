# frozen_string_literal: true

require_relative "bucket"
require_relative "stub_evict"

module N4Cache
  module EvictP5
    module_function

    def evict_p5(bucket, epoch)
      StubEvict.trim_ttl(bucket)
      bucket.entries.count { |e| e.link_epoch <= epoch }
    end
  end
end

def evict_p5(bucket, epoch)
  N4Cache::EvictP5.evict_p5(bucket, epoch)
end
