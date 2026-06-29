#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require_relative "engine"

options = { matrix_full: false, out: nil }
OptionParser.new do |opts|
  opts.on("--matrix-full") { options[:matrix_full] = true }
  opts.on("--out PATH") { |v| options[:out] = v }
end.parse!

raise "usage: var_check --matrix-full --out PATH" unless options[:matrix_full] && options[:out]

VarCheck::Engine.run_matrix(options[:out])
