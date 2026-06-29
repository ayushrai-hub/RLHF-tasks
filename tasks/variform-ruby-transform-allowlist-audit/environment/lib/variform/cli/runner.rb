# frozen_string_literal: true

module Variform
  module CLI
    module Runner
      module_function

      def run(argv)
        options = Options.parse(argv)
        exit(dispatch(options))
      rescue Variform::Error => e
        warn "error: #{e.message}"
        exit 1
      end

      def dispatch(options)
        case options.command
        when 'check'
          Commands::Check.run(options)
        when 'plan'
          Commands::Plan.run(options)
        when 'methods'
          Commands::Methods.run(options)
        when 'version', '--version'
          $stdout.puts(Variform::VERSION)
          0
        else
          warn Usage.text
          2
        end
      end
    end
  end
end
