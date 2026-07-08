import Config

config :goldsmith,
  port: String.to_integer(System.get_env("PORT", "8080")),
  db_path: System.get_env("DB_PATH", "/app/data/atelier.db"),
  seed_dir: "/app/seed",
  config_dir: "/app/config"

config :logger,
  level: :info,
  truncate: 4096
