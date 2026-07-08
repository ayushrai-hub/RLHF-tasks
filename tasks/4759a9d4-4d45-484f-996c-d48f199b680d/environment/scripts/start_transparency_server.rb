#!/usr/bin/env ruby
# frozen_string_literal: true

require "rack"
require "rackup"
require "rackup/handler/webrick"
require_relative "../service/transparency_app"

Rackup::Handler::WEBrick.run(
  TransparencyApp.new,
  Host: "127.0.0.1",
  Port: 9292,
  AccessLog: [],
  Logger: WEBrick::Log.new($stderr, WEBrick::Log::FATAL)
)
