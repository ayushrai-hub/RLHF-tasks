# frozen_string_literal: true

module Variform
  module Geometry
    module Flags
      ONLY_SHRINK = '>'
      ONLY_ENLARGE = '<'
      FILL = '^'
      IGNORE_ASPECT = '!'
      PERCENT = '%'

      ALL = [ONLY_SHRINK, ONLY_ENLARGE, FILL, IGNORE_ASPECT, PERCENT].freeze

      module_function

      def flag?(token)
        ALL.include?(token.to_s)
      end
    end
  end
end
