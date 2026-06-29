# frozen_string_literal: true

module Variform
  module CLI
    module Commands
      module Check
        module_function

        def run(options)
          Processor.plan_from_json(options.read_source, processor: options.processor)
          $stdout.puts('ok')
          0
        end
      end
    end
  end
end
