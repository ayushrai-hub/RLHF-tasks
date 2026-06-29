#!/usr/bin/env ruby
# frozen_string_literal: true

require_relative "run"

profile = ARGV.fetch(0)
path_kind = ARGV.fetch(1, "uninterrupted")
result = VarDaemon::Run.execute_profile(profile, path_kind: path_kind)
puts JSON.generate(result)
