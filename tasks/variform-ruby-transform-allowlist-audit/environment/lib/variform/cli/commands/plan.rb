# frozen_string_literal: true

module Variform
  module CLI
    module Commands
      module Plan
        module_function

        def run(options)
          plan = Processor.plan_from_json(options.read_source, processor: options.processor)
          plan.to_a.each { |token| $stdout.puts(token) }
          0
        end
      end
    end
  end
end
