# frozen_string_literal: true

require_relative "types"

module R7Lane
  module StepQ2
    module_function

    def phase_label(step)
      step.fetch("kind", "noop")
    end

    def link_id(step)
      step.fetch("iface", 0)
    end
  end
end
