defmodule Goldsmith.Config do
  @moduledoc """
  Loads the JSON configuration files in /app/config/*.json. The contents are
  cached in :persistent_term so we only hit disk once per file.
  """

  @config_files ~w(letter_values stage_order alloy_grades intent_kinds thresholds)

  def all do
    Enum.into(@config_files, %{}, fn name -> {name, load(name)} end)
  end

  def get(name) do
    case :persistent_term.get({__MODULE__, name}, :miss) do
      :miss ->
        loaded = load(name)
        :persistent_term.put({__MODULE__, name}, loaded)
        loaded

      cached ->
        cached
    end
  end

  defp load(name) do
    base = Application.get_env(:goldsmith, :config_dir, "/app/config")
    path = Path.join(base, name <> ".json")
    path |> File.read!() |> Jason.decode!()
  end

  # ---- shortcuts -----------------------------------------------------------

  def valid_stages, do: get("stage_order")["stages"]
  def advance_targets, do: get("stage_order")["advance_targets"]
  def valid_grades, do: get("alloy_grades")["valid_grades"]
  def valid_kinds, do: get("intent_kinds")["valid_kinds"]
  def valid_specialties, do: get("intent_kinds")["valid_specialties"]
  def valid_ranks, do: get("intent_kinds")["valid_ranks"]
  def letter_values, do: get("letter_values")
  def valid_letters, do: Map.keys(letter_values()) |> Enum.sort()

  def threshold(path) when is_list(path) do
    get_in(get("thresholds"), path)
  end
end
