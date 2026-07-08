defmodule Goldsmith.Handlers.Pieces do
  @moduledoc false
  alias Goldsmith.{Config, DB, JsonUtil, Stage}

  def create(conn) do
    with {:ok, body, conn} <- JsonUtil.parse_body(conn) do
      serial = JsonUtil.s(body, "serial")
      intent = JsonUtil.s(body, "intent_kind")
      grade  = JsonUtil.s(body, "alloy_grade")
      mass   = JsonUtil.f(body, "target_mass_g")
      parent = Map.get(body, "parent_id")

      cond do
        is_nil(serial) or serial == "" ->
          JsonUtil.err(conn, 422, "missing_field", "serial required")

        intent not in Config.valid_kinds() ->
          JsonUtil.err(conn, 422, "missing_field",
            "intent_kind must be one of #{Enum.join(Config.valid_kinds(), ", ")}")

        grade not in Config.valid_grades() ->
          JsonUtil.err(conn, 422, "missing_field",
            "alloy_grade must be one of #{Enum.join(Config.valid_grades(), ", ")}")

        is_nil(mass) or mass <= 0 ->
          JsonUtil.err(conn, 422, "missing_field", "target_mass_g must be > 0")

        not is_nil(parent) and not is_integer(parent) ->
          JsonUtil.err(conn, 422, "missing_field", "parent_id must be integer or null")

        not is_nil(parent) and not Stage.piece_exists?(parent) ->
          JsonUtil.err(conn, 404, "piece_not_found", "parent piece #{parent} not found")

        DB.one("SELECT 1 FROM pieces WHERE serial = ?", [serial]) != nil ->
          JsonUtil.err(conn, 409, "duplicate_serial", "serial #{serial} already in use")

        true ->
          {:ok, _} =
            DB.query(
              "INSERT INTO pieces (serial, intent_kind, alloy_grade, target_mass_g, parent_id) VALUES (?, ?, ?, ?, ?)",
              [serial, intent, grade, mass, parent]
            )
          pid = DB.last_insert_rowid()
          JsonUtil.ok(conn, 201, %{
            piece_id: pid,
            serial: serial,
            intent_kind: intent,
            alloy_grade: grade,
            target_mass_g: mass,
            stage: "ingot_selected",
            parent_id: parent
          })
      end
    else
      {:halt, conn} -> conn
    end
  end

  def show(conn, id_str) do
    case Stage.parse_id(id_str) do
      :error ->
        JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")

      id ->
        case Stage.lookup_piece(id) do
          nil ->
            JsonUtil.err(conn, 404, "piece_not_found", "piece #{id} not found")

          piece ->
            JsonUtil.ok(conn, 200, %{
              piece_id: piece.id,
              serial: piece.serial,
              intent_kind: piece.intent_kind,
              alloy_grade: piece.alloy_grade,
              target_mass_g: piece.target_mass_g,
              stage: piece.stage,
              assigned_goldsmith: piece.assigned_goldsmith,
              parent_id: piece.parent_id,
              released_at: piece.released_at
            })
        end
    end
  end
end
