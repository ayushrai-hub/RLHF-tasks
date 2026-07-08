defmodule Goldsmith.MixProject do
  use Mix.Project

  def project do
    [
      app: :goldsmith,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      elixirc_paths: ["lib"]
    ]
  end

  def application do
    [
      extra_applications: [:logger, :crypto],
      mod: {Goldsmith.Application, []}
    ]
  end

  defp deps do
    [
      {:plug, "== 1.15.3"},
      {:plug_cowboy, "== 2.7.0"},
      {:jason, "== 1.4.4"},
      {:exqlite, "== 0.37.0"}
    ]
  end
end
