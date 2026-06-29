# frozen_string_literal: true

module Variform
  module CLI
    module Commands
      module Methods
        module_function

        def run(_options)
          $stdout.puts(Validation::MethodCatalog.count)
          0
        end
      end
    end
  end
end
