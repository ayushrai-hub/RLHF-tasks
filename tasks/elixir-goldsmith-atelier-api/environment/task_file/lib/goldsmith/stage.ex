defmodule Goldsmith.Stage do
  @moduledoc """
  Lookup + existence helpers shared by handlers. Kept tiny on purpose;
  business rules live in the per-endpoint handler modules.
  """
  alias Goldsmith.DB

  def lookup_piece(id) when is_integer(id) do
    case DB.one(
           "SELECT id, serial, intent_kind, alloy_grade, target_mass_g, stage, assigned_goldsmith, parent_id, released_at FROM pieces WHERE id = ?",
           [id]
         ) do
      nil -> nil
      [pid, serial, intent, grade, mass, stage, smith, parent, released_at] ->
        %{
          id: pid,
          serial: serial,
          intent_kind: intent,
          alloy_grade: grade,
          target_mass_g: mass,
          stage: stage,
          assigned_goldsmith: smith,
          parent_id: parent,
          released_at: released_at
        }
    end
  end

  def lookup_piece(_), do: nil

  def piece_exists?(id) when is_integer(id) do
    case DB.one("SELECT 1 FROM pieces WHERE id = ?", [id]) do
      [1] -> true
      _ -> false
    end
  end
  def piece_exists?(_), do: false

  def goldsmith_exists?(id) when is_integer(id) do
    case DB.one("SELECT 1 FROM goldsmiths WHERE id = ?", [id]) do
      [1] -> true
      _ -> false
    end
  end
  def goldsmith_exists?(_), do: false

  def crucible_exists?(id) when is_integer(id) do
    case DB.one("SELECT 1 FROM crucibles WHERE id = ?", [id]) do
      [1] -> true
      _ -> false
    end
  end
  def crucible_exists?(_), do: false

  def crucible(id) when is_integer(id) do
    case DB.one("SELECT id, label, capacity_g FROM crucibles WHERE id = ?", [id]) do
      nil -> nil
      [cid, label, cap] -> %{id: cid, label: label, capacity_g: cap}
    end
  end

  def goldsmith(id) when is_integer(id) do
    case DB.one(
           "SELECT id, name, rank, specialty, mentor_id, joined_at FROM goldsmiths WHERE id = ?",
           [id]
         ) do
      nil -> nil
      [gid, name, rank, spec, mentor, joined] ->
        %{id: gid, name: name, rank: rank, specialty: spec, mentor_id: mentor, joined_at: joined}
    end
  end

  @doc "Parse a non-negative integer from a path-param string. Returns integer or :error."
  def parse_id(s) when is_binary(s) do
    case Integer.parse(s) do
      {n, ""} when n >= 0 -> n
      _ -> :error
    end
  end

  def parse_id(_), do: :error
end
