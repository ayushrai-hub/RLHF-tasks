# frozen_string_literal: true

require_relative "bands"
require_relative "stub_fold"

module V8Scope
  module FoldM1
    module_function

    def fold_m1(band_set, view_q)
      _ = view_q
      StubFold.flatten_names(band_set)
      band_set.max_level
    end
  end
end

def fold_m1(band_set, view_q)
  V8Scope::FoldM1.fold_m1(band_set, view_q)
end
