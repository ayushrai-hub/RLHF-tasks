require_relative "boot"

require "rails"
require "action_controller/railtie"

Bundler.require(*Rails.groups)

module CaseApi
  class Application < Rails::Application
    config.load_defaults 7.1

    config.api_only = true
    config.eager_load = true
    config.cache_classes = true
    config.consider_all_requests_local = false
    config.hosts.clear

    config.log_level = :info
    require "fileutils"
    FileUtils.mkdir_p("/app/state")
    config.logger = ActiveSupport::Logger.new("/app/state/rails.log")

    config.secret_key_base = "halverson-case-deterministic-key-do-not-rotate"
  end
end
