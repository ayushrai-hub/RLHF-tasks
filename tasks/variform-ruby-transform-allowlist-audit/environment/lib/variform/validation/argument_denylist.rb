# frozen_string_literal: true

module Variform
  module Validation
    module ArgumentDenylist
      FORBIDDEN = %w[
        -debug
        -define
        -distribute-cache
        -authenticate
        -help
        -path
        -print
        -set
        -verbose
        -version
        -write
        -write-mask
      ].freeze
    end
  end
end
