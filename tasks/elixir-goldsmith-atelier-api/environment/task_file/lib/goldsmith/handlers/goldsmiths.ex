defmodule Goldsmith.Handlers.Goldsmiths do
  @moduledoc false
  alias Goldsmith.{Config, DB, JsonUtil, Stage}

  def create(conn) do
    with {:ok, body, conn} <- JsonUtil.parse_body(conn) do
      name = JsonUtil.s(body, "name")
      rank = JsonUtil.s(body, "rank")
      spec = JsonUtil.s(body, "specialty")
      mentor_raw = Map.get(body, "mentor_id")

      cond do
        is_nil(name) or name == "" ->
          JsonUtil.err(conn, 422, "missing_field", "name required")

        rank not in Config.valid_ranks() ->
          JsonUtil.err(conn, 422, "missing_field",
            "rank must be one of #{Enum.join(Config.valid_ranks(), ", ")}")

        spec not in Config.valid_specialties() ->
          JsonUtil.err(conn, 422, "missing_field",
            "specialty must be one of #{Enum.join(Config.valid_specialties(), ", ")}")

        not is_nil(mentor_raw) and not is_integer(mentor_raw) ->
          JsonUtil.err(conn, 422, "missing_field", "mentor_id must be integer or null")

        not is_nil(mentor_raw) and not Stage.goldsmith_exists?(mentor_raw) ->
          JsonUtil.err(conn, 404, "goldsmith_not_found",
            "mentor #{mentor_raw} not found")

        DB.one("SELECT 1 FROM goldsmiths WHERE name = ?", [name]) != nil ->
          JsonUtil.err(conn, 409, "duplicate_name", "name #{name} already in use")

        true ->
          joined_at = JsonUtil.iso_now()
          {:ok, _} =
            DB.query(
              "INSERT INTO goldsmiths (name, rank, specialty, mentor_id, joined_at) VALUES (?, ?, ?, ?, ?)",
              [name, rank, spec, mentor_raw, joined_at]
            )
          gid = DB.last_insert_rowid()
          JsonUtil.ok(conn, 201, %{
            goldsmith_id: gid,
            name: name,
            rank: rank,
            specialty: spec,
            mentor_id: mentor_raw,
            joined_at: joined_at
          })
      end
    else
      {:halt, conn} -> conn
    end
  end
end
