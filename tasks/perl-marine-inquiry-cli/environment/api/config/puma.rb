bind "tcp://127.0.0.1:#{ENV.fetch("PORT") { 3000 }}"
environment ENV.fetch("RAILS_ENV") { "production" }
workers 0
threads 1, 4
preload_app! false
