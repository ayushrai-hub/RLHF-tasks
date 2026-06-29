# frozen_string_literal: true

module Variform
  module Geometry
    module_function

    def parse(text)
      Region.parse(text) || Dimensions.parse(text)
    end
  end
end
