# frozen_string_literal: true

require_relative "types"
require_relative "stub_merge"

module R7Lane
  module MergeK2
    module_function

    def merge_k2(lane_view, sink)
      StubMerge.write_smoke_rows(sink, lane_view.rows)
      lane_view.current_epoch
    end
  end
end

def merge_k2(lane_view, sink)
  R7Lane::MergeK2.merge_k2(lane_view, sink)
end
