defmodule Goldsmith.Application do
  use Application

  @impl true
  def start(_type, _args) do
    port = Application.get_env(:goldsmith, :port, 8080)
    db_path = Application.get_env(:goldsmith, :db_path, "/app/data/atelier.db")

    File.mkdir_p!(Path.dirname(db_path))
    Goldsmith.DB.bootstrap!(db_path)

    children = [
      {Goldsmith.DB, [db_path: db_path]},
      {Plug.Cowboy, scheme: :http, plug: Goldsmith.Router, options: [port: port]}
    ]

    opts = [strategy: :one_for_one, name: Goldsmith.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
