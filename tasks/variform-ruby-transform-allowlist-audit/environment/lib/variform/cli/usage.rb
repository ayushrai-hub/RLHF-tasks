# frozen_string_literal: true

module Variform
  module CLI
    module Usage
      TEXT = 'usage: variform <check|plan|methods|version> [SPEC_FILE]'

      module_function

      def text
        TEXT
      end
    end
  end
end
