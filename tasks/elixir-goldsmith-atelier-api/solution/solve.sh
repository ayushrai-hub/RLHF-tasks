#!/usr/bin/env bash
# Oracle solution. Overwrites every stubbed handler under
# /app/lib/goldsmith/handlers/ with the real implementation and adds the
# Goldsmith.Audit helper module. Then it recompiles and restarts the server.
set -uo pipefail

mkdir -p /app/data /app/logs

# ---------------- lib/goldsmith/audit.ex (helper) ----------------
cat > /app/lib/goldsmith/audit.ex <<'EX'
defmodule Goldsmith.Audit do
  @moduledoc "SHA-256 audit-chain helpers shared by mutating handlers."
  alias Goldsmith.{DB, JsonUtil}

  @genesis String.duplicate("0", 64)

  @doc "Append one row to `audit_entries`. Returns the new seq integer."
  def append!(action, payload) when is_binary(action) and is_binary(payload) do
    prev = prev_hash()
    occurred_at = JsonUtil.iso_now()
    entry_hash = compute_hash(prev, action, payload)

    {:ok, _} =
      DB.query(
        "INSERT INTO audit_entries (action, payload, prev_hash, entry_hash, occurred_at) VALUES (?, ?, ?, ?, ?)",
        [action, payload, prev, entry_hash, occurred_at]
      )

    DB.last_insert_rowid()
  end

  @doc "Compute the entry_hash for a given (prev, action, payload) triple."
  def compute_hash(prev, action, payload) do
    :crypto.hash(:sha256, "#{prev}|#{action}|#{payload}")
    |> Base.encode16(case: :lower)
  end

  def genesis, do: @genesis

  @doc "Return the entry_hash of the latest row, or the genesis if the chain is empty."
  def prev_hash do
    case DB.scalar("SELECT entry_hash FROM audit_entries ORDER BY seq DESC LIMIT 1") do
      nil -> @genesis
      h when is_binary(h) -> h
    end
  end
end
EX

# ---------------- handlers/assign.ex ----------------
cat > /app/lib/goldsmith/handlers/assign.ex <<'EX'
defmodule Goldsmith.Handlers.Assign do
  @moduledoc "POST /goldsmiths/:gid/assign — assign a piece to a goldsmith."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, gid_str) do
    with {:gid, gid} when is_integer(gid) <- {:gid, Stage.parse_id(gid_str)},
         {:smith, true} <- {:smith, Stage.goldsmith_exists?(gid)},
         {:body, {:ok, body, conn}} <- {:body, JsonUtil.parse_body(conn)},
         {:pid_raw, pid_raw} when is_integer(pid_raw) <- {:pid_raw, JsonUtil.i(body, "piece_id")},
         {:piece, piece} when not is_nil(piece) <- {:piece, Stage.lookup_piece(pid_raw)},
         {:assigned, false} <- {:assigned, not is_nil(piece.assigned_goldsmith)} do
      {:ok, _} =
        DB.query("UPDATE pieces SET assigned_goldsmith = ? WHERE id = ?", [gid, piece.id])
      JsonUtil.ok(conn, 200, %{goldsmith_id: gid, piece_id: piece.id})
    else
      {:gid, :error} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "non-integer goldsmith id")
      {:smith, false} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "no such goldsmith")
      {:body, {:halt, conn}} -> conn
      {:pid_raw, _} -> JsonUtil.err(conn, 422, "missing_field", "piece_id required")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
      {:assigned, true} -> JsonUtil.err(conn, 409, "already_assigned", "piece already assigned")
    end
  end
end
EX

# ---------------- handlers/assay.ex ----------------
cat > /app/lib/goldsmith/handlers/assay.ex <<'EX'
defmodule Goldsmith.Handlers.Assay do
  @moduledoc "POST /pieces/:id/assay — record an assay reading."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, piece} when not is_nil(piece) <- {:piece, Stage.lookup_piece(pid)},
         {:released, false} <- {:released, piece.stage == "released"},
         {:body, {:ok, body, conn}} <- {:body, JsonUtil.parse_body(conn)},
         {:gid, gid} when is_integer(gid) <- {:gid, JsonUtil.i(body, "goldsmith_id")},
         {:smith, true} <- {:smith, Stage.goldsmith_exists?(gid)},
         {:fine, fine} when is_integer(fine) and fine >= 0 and fine <= 1000 <-
           {:fine, JsonUtil.i(body, "fineness_per_mille")} do
      performed_at = JsonUtil.s(body, "performed_at") || JsonUtil.iso_now()
      {:ok, _} =
        DB.query(
          "INSERT INTO assays (piece_id, goldsmith_id, fineness_per_mille, performed_at) VALUES (?, ?, ?, ?)",
          [piece.id, gid, fine, performed_at]
        )
      assay_id = DB.last_insert_rowid()
      JsonUtil.ok(conn, 201, %{
        assay_id: assay_id,
        piece_id: piece.id,
        goldsmith_id: gid,
        fineness_per_mille: fine,
        performed_at: performed_at
      })
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
      {:released, true} -> JsonUtil.err(conn, 409, "already_released", "piece is released")
      {:body, {:halt, conn}} -> conn
      {:gid, _} -> JsonUtil.err(conn, 422, "missing_field", "goldsmith_id required")
      {:smith, false} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "no such goldsmith")
      {:fine, _} -> JsonUtil.err(conn, 422, "invalid_fineness", "fineness_per_mille must be 0..1000 integer")
    end
  end
end
EX

# ---------------- handlers/hallmark.ex ----------------
cat > /app/lib/goldsmith/handlers/hallmark.ex <<'EX'
defmodule Goldsmith.Handlers.Hallmark do
  @moduledoc "POST /pieces/:id/hallmark — add a graded hallmark."
  alias Goldsmith.{Audit, Config, DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, piece} when not is_nil(piece) <- {:piece, Stage.lookup_piece(pid)},
         {:released, false} <- {:released, piece.stage == "released"},
         {:stage, true} <- {:stage, piece.stage == "chased"},
         {:body, {:ok, body, conn}} <- {:body, JsonUtil.parse_body(conn)},
         {:gid_raw, gid} when is_integer(gid) <- {:gid_raw, JsonUtil.i(body, "goldsmith_id")},
         {:ts, recorded_at} when is_binary(recorded_at) <-
           {:ts, JsonUtil.s(body, "recorded_at") || JsonUtil.iso_now()},
         {:mono, :ok} <- {:mono, check_monotonic(gid, recorded_at)},
         {:smith, true} <- {:smith, Stage.goldsmith_exists?(gid)},
         {:letter, letter} when letter in ["A", "B", "C", "F"] <-
           {:letter, JsonUtil.s(body, "letter")} do
      notes = JsonUtil.s(body, "notes")
      {:ok, _} =
        DB.query(
          "INSERT INTO hallmarks (piece_id, goldsmith_id, letter, notes, recorded_at) VALUES (?, ?, ?, ?, ?)",
          [piece.id, gid, letter, notes, recorded_at]
        )
      hallmark_id = DB.last_insert_rowid()
      _ = Audit.append!("hallmark", "#{piece.id}|#{hallmark_id}|#{gid}|#{letter}")
      JsonUtil.ok(conn, 201, %{
        hallmark_id: hallmark_id,
        piece_id: piece.id,
        goldsmith_id: gid,
        letter: letter,
        notes: notes,
        recorded_at: recorded_at
      })
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
      {:released, true} -> JsonUtil.err(conn, 409, "already_released", "piece is released")
      {:stage, false} -> JsonUtil.err(conn, 409, "wrong_stage", "stage must be chased")
      {:body, {:halt, conn}} -> conn
      {:gid_raw, _} -> JsonUtil.err(conn, 422, "missing_field", "goldsmith_id required")
      {:ts, _} -> JsonUtil.err(conn, 422, "missing_field", "recorded_at must be a string when provided")
      {:mono, :violation} ->
        JsonUtil.err(conn, 409, "ts_not_monotonic",
          "recorded_at must exceed this goldsmith's most recent hallmark")
      {:smith, false} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "no such goldsmith")
      {:letter, _} -> JsonUtil.err(conn, 422, "invalid_letter", "letter must be A/B/C/F")
    end
  end

  defp check_monotonic(gid, recorded_at) do
    case DB.scalar(
           "SELECT MAX(recorded_at) FROM hallmarks WHERE goldsmith_id = ?",
           [gid]
         ) do
      nil -> :ok
      latest when is_binary(latest) ->
        if recorded_at > latest, do: :ok, else: :violation
      _ -> :ok
    end
  end
end
EX

# ---------------- handlers/release.ex ----------------
cat > /app/lib/goldsmith/handlers/release.ex <<'EX'
defmodule Goldsmith.Handlers.Release do
  @moduledoc "POST /pieces/:id/release — final transition hallmarked → released."
  alias Goldsmith.{Audit, DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, piece} when not is_nil(piece) <- {:piece, Stage.lookup_piece(pid)},
         {:released, false} <- {:released, piece.stage == "released"},
         {:stage, true} <- {:stage, piece.stage == "hallmarked"} do
      released_at = JsonUtil.iso_now()
      {:ok, _} =
        DB.query("UPDATE pieces SET stage = 'released', released_at = ? WHERE id = ?",
                 [released_at, piece.id])
      _ = Audit.append!("release", "#{piece.id}|#{released_at}")
      JsonUtil.ok(conn, 200, %{piece_id: piece.id, stage: "released", released_at: released_at})
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
      {:released, true} -> JsonUtil.err(conn, 409, "already_released", "piece is released")
      {:stage, false} -> JsonUtil.err(conn, 409, "wrong_stage", "stage must be hallmarked")
    end
  end
end
EX

# ---------------- handlers/advance.ex ----------------
cat > /app/lib/goldsmith/handlers/advance.ex <<'EX'
defmodule Goldsmith.Handlers.Advance do
  @moduledoc "POST /pieces/:id/advance-stage — drive the linear stage machine."
  alias Goldsmith.{Audit, Config, DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, piece} when not is_nil(piece) <- {:piece, Stage.lookup_piece(pid)},
         {:released, false} <- {:released, piece.stage == "released"},
         {:target, target} when is_binary(target) <-
           {:target, Map.get(Config.advance_targets(), piece.stage)},
         :ok <- precondition(piece, target) do
      {:ok, _} = DB.query("UPDATE pieces SET stage = ? WHERE id = ?", [target, piece.id])
      _ = Audit.append!("advance_stage", "#{piece.id}|#{target}")
      JsonUtil.ok(conn, 200, %{piece_id: piece.id, stage: target})
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
      {:released, true} -> JsonUtil.err(conn, 409, "already_released", "piece is released")
      {:target, _} -> JsonUtil.err(conn, 409, "wrong_stage", "no advance target from #{conn.path_info}")
      {:err, code, detail} -> JsonUtil.err(conn, 409, code, detail)
    end
  end

  defp precondition(piece, target) do
    case {piece.stage, target} do
      {"ingot_selected", "assayed"} ->
        case DB.scalar("SELECT COUNT(*) FROM assays WHERE piece_id = ?", [piece.id]) do
          n when is_integer(n) and n > 0 -> :ok
          _ -> {:err, "missing_assay", "no assay row for this piece"}
        end

      {"cast_active", "cast_complete"} ->
        now = JsonUtil.iso_now()
        case DB.scalar(
               "SELECT 1 FROM castings WHERE piece_id = ? AND ends_at <= ? ORDER BY ends_at DESC LIMIT 1",
               [piece.id, now]
             ) do
          1 -> :ok
          _ -> {:err, "wrong_stage", "no completed casting window for this piece"}
        end

      {"chased", "hallmarked"} ->
        case DB.scalar("SELECT COUNT(*) FROM hallmarks WHERE piece_id = ?", [piece.id]) do
          n when is_integer(n) and n > 0 -> :ok
          _ -> {:err, "missing_hallmark", "no hallmark for this piece"}
        end

      _ ->
        :ok
    end
  end
end
EX

# ---------------- handlers/cast.ex ----------------
cat > /app/lib/goldsmith/handlers/cast.ex <<'EX'
defmodule Goldsmith.Handlers.Cast do
  @moduledoc "POST /pieces/:id/cast — book a casting window on a crucible."
  alias Goldsmith.{Audit, DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, piece} when not is_nil(piece) <- {:piece, Stage.lookup_piece(pid)},
         {:released, false} <- {:released, piece.stage == "released"},
         {:stage, true} <- {:stage, piece.stage == "cast_active"},
         {:body, {:ok, body, conn}} <- {:body, JsonUtil.parse_body(conn)},
         {:gid, gid} when is_integer(gid) <- {:gid, JsonUtil.i(body, "goldsmith_id")},
         {:smith, true} <- {:smith, Stage.goldsmith_exists?(gid)},
         {:cid, cid} when is_integer(cid) <- {:cid, JsonUtil.i(body, "crucible_id")},
         {:cruc, %{capacity_g: cap}} <- {:cruc, Stage.crucible(cid)},
         {:starts, starts} when is_binary(starts) <- {:starts, JsonUtil.s(body, "starts_at")},
         {:ends, ends} when is_binary(ends) <- {:ends, JsonUtil.s(body, "ends_at")},
         {:mass, mass} when is_number(mass) <- {:mass, JsonUtil.f(body, "poured_mass_g")},
         {:window, true} <- {:window, starts < ends},
         {:mass_pos, true} <- {:mass_pos, mass > 0},
         {:alloy_ok, true} <- {:alloy_ok, alloy_permitted?(cid, piece.alloy_grade)},
         {:cap_ok, true} <- {:cap_ok, mass <= cap},
         {:rank_ok, true} <- {:rank_ok, rank_sufficient?(piece.alloy_grade, gid)},
         {:cruc_overlap, nil} <- {:cruc_overlap, crucible_overlap(cid, starts, ends)},
         {:smith_overlap, nil} <- {:smith_overlap, smith_overlap(gid, starts, ends)} do
      {:ok, _} =
        DB.query(
          "INSERT INTO castings (piece_id, crucible_id, goldsmith_id, poured_mass_g, starts_at, ends_at) VALUES (?, ?, ?, ?, ?, ?)",
          [piece.id, cid, gid, mass, starts, ends]
        )
      casting_id = DB.last_insert_rowid()
      _ = Audit.append!("cast",
            "#{piece.id}|#{casting_id}|#{cid}|#{gid}|#{JsonUtil.fmt6(mass)}")
      JsonUtil.ok(conn, 201, %{
        casting_id: casting_id, piece_id: piece.id,
        crucible_id: cid, goldsmith_id: gid,
        poured_mass_g: mass, starts_at: starts, ends_at: ends
      })
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
      {:released, true} -> JsonUtil.err(conn, 409, "already_released", "piece is released")
      {:stage, false} -> JsonUtil.err(conn, 409, "wrong_stage", "stage must be cast_active")
      {:body, {:halt, conn}} -> conn
      {:gid, _} -> JsonUtil.err(conn, 422, "missing_field", "goldsmith_id required")
      {:smith, false} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "no such goldsmith")
      {:cid, _} -> JsonUtil.err(conn, 422, "missing_field", "crucible_id required")
      {:cruc, nil} -> JsonUtil.err(conn, 404, "crucible_not_found", "no such crucible")
      {:starts, _} -> JsonUtil.err(conn, 422, "missing_field", "starts_at required")
      {:ends, _} -> JsonUtil.err(conn, 422, "missing_field", "ends_at required")
      {:mass, _} -> JsonUtil.err(conn, 422, "missing_field", "poured_mass_g required")
      {:window, false} -> JsonUtil.err(conn, 422, "invalid_window", "starts_at must precede ends_at")
      {:mass_pos, false} -> JsonUtil.err(conn, 422, "invalid_mass", "poured_mass_g must be > 0")
      {:alloy_ok, false} -> JsonUtil.err(conn, 422, "alloy_grade_incompatible",
                                         "crucible cannot pour this alloy grade")
      {:cap_ok, false} -> JsonUtil.err(conn, 422, "capacity_exceeded", "poured_mass_g exceeds crucible capacity")
      {:rank_ok, false} -> JsonUtil.err(conn, 422, "rank_insufficient",
                                        "24K alloy requires a master goldsmith")
      {:cruc_overlap, _} -> JsonUtil.err(conn, 409, "crucible_overlap", "crucible window overlaps existing")
      {:smith_overlap, _} -> JsonUtil.err(conn, 409, "goldsmith_busy", "goldsmith already casting in this window")
    end
  end

  defp alloy_permitted?(cid, alloy_grade) do
    case DB.scalar("SELECT permitted_alloys FROM crucibles WHERE id = ?", [cid]) do
      nil -> false
      json_str ->
        case Jason.decode(json_str) do
          {:ok, list} when is_list(list) -> alloy_grade in list
          _ -> false
        end
    end
  end

  defp rank_sufficient?(alloy_grade, gid) do
    if alloy_grade == "24K" do
      case Goldsmith.Stage.goldsmith(gid) do
        %{rank: "master"} -> true
        _ -> false
      end
    else
      true
    end
  end

  defp crucible_overlap(cid, starts, ends) do
    DB.scalar(
      "SELECT 1 FROM castings WHERE crucible_id = ? AND starts_at < ? AND ends_at > ? LIMIT 1",
      [cid, ends, starts]
    )
  end

  defp smith_overlap(gid, starts, ends) do
    DB.scalar(
      "SELECT 1 FROM castings WHERE goldsmith_id = ? AND starts_at < ? AND ends_at > ? LIMIT 1",
      [gid, ends, starts]
    )
  end
end
EX

# ---------------- handlers/bulk_cast.ex ----------------
cat > /app/lib/goldsmith/handlers/bulk_cast.ex <<'EX'
defmodule Goldsmith.Handlers.BulkCast do
  @moduledoc "POST /pieces/bulk-cast — atomic batch casting."
  alias Goldsmith.{Audit, DB, JsonUtil, Stage}

  def call(conn) do
    with {:body, {:ok, body, conn}} <- {:body, JsonUtil.parse_body(conn)},
         {:arr, arr} when is_list(arr) and arr != [] <- {:arr, Map.get(body, "casts")},
         :ok <- check_dup_piece(arr),
         {:rows, []} <- {:rows, collect_errors(arr)} do
      ids =
        Enum.map(arr, fn row ->
          {:ok, _} =
            DB.query(
              "INSERT INTO castings (piece_id, crucible_id, goldsmith_id, poured_mass_g, starts_at, ends_at) VALUES (?, ?, ?, ?, ?, ?)",
              [
                Map.get(row, "piece_id"),
                Map.get(row, "crucible_id"),
                Map.get(row, "goldsmith_id"),
                JsonUtil.f(row, "poured_mass_g"),
                Map.get(row, "starts_at"),
                Map.get(row, "ends_at")
              ]
            )

          DB.last_insert_rowid()
        end)

      _ = Audit.append!("bulk_cast", "#{length(ids)}|#{List.first(ids)}|#{List.last(ids)}")
      JsonUtil.ok(conn, 201, %{count: length(ids), casting_ids: ids})
    else
      {:body, {:halt, conn}} ->
        conn

      {:arr, _} ->
        JsonUtil.err(conn, 422, "empty_batch", "casts array required and non-empty")

      {:err, idx} ->
        JsonUtil.err(conn, 422, "dup_in_batch", "duplicate piece_id at index #{idx}")

      {:rows, errors} ->
        JsonUtil.err(conn, 422, "validation_failed", "see errors array", %{errors: errors})
    end
  end

  defp check_dup_piece(arr) do
    arr
    |> Enum.with_index()
    |> Enum.reduce_while(MapSet.new(), fn {row, idx}, seen ->
      pid = Map.get(row, "piece_id")

      if is_integer(pid) do
        if MapSet.member?(seen, pid) do
          {:halt, {:err, idx}}
        else
          {:cont, MapSet.put(seen, pid)}
        end
      else
        {:cont, seen}
      end
    end)
    |> case do
      %MapSet{} -> :ok
      {:err, idx} -> {:err, idx}
    end
  end

  defp collect_errors(arr) do
    {errors, _accepted} =
      arr
      |> Enum.with_index()
      |> Enum.reduce({[], []}, fn {row, idx}, {errs, accepted} ->
        case row_error(row, accepted) do
          nil -> {errs, accepted ++ [canonical_row(row)]}
          code -> {errs ++ [%{index: idx, code: code, detail: code}], accepted}
        end
      end)

    errors
  end

  defp canonical_row(row) do
    %{
      piece_id: Map.get(row, "piece_id"),
      crucible_id: Map.get(row, "crucible_id"),
      goldsmith_id: Map.get(row, "goldsmith_id"),
      starts_at: Map.get(row, "starts_at"),
      ends_at: Map.get(row, "ends_at")
    }
  end

  defp row_error(row, accepted) do
    pid = Map.get(row, "piece_id")
    gid = Map.get(row, "goldsmith_id")
    cid = Map.get(row, "crucible_id")
    mass = JsonUtil.f(row, "poured_mass_g")
    starts = JsonUtil.s(row, "starts_at")
    ends = JsonUtil.s(row, "ends_at")
    piece = Stage.lookup_piece(pid)

    cond do
      not is_integer(pid) ->
        "missing_field"

      is_nil(piece) ->
        "piece_not_found"

      piece.stage == "released" ->
        "already_released"

      piece.stage != "cast_active" ->
        "wrong_stage"

      not is_integer(gid) ->
        "missing_field"

      not Stage.goldsmith_exists?(gid) ->
        "goldsmith_not_found"

      not is_integer(cid) ->
        "missing_field"

      is_nil(Stage.crucible(cid)) ->
        "crucible_not_found"

      not is_number(mass) or not is_binary(starts) or not is_binary(ends) ->
        "missing_field"

      starts >= ends ->
        "invalid_window"

      mass <= 0 ->
        "invalid_mass"

      not alloy_permitted?(cid, piece.alloy_grade) ->
        "alloy_grade_incompatible"

      mass > Stage.crucible(cid).capacity_g ->
        "capacity_exceeded"

      not rank_sufficient?(piece.alloy_grade, gid) ->
        "rank_insufficient"

      existing_crucible_overlap(cid, starts, ends) ->
        "crucible_overlap_existing"

      existing_smith_overlap(gid, starts, ends) ->
        "goldsmith_busy_existing"

      batch_crucible_overlap?(accepted, cid, starts, ends) ->
        "crucible_overlap_batch"

      batch_smith_overlap?(accepted, gid, starts, ends) ->
        "goldsmith_busy_batch"

      true ->
        nil
    end
  end

  defp alloy_permitted?(cid, alloy_grade) do
    case DB.scalar("SELECT permitted_alloys FROM crucibles WHERE id = ?", [cid]) do
      nil ->
        false

      json_str ->
        case Jason.decode(json_str) do
          {:ok, list} when is_list(list) -> alloy_grade in list
          _ -> false
        end
    end
  end

  defp rank_sufficient?(alloy_grade, gid) do
    if alloy_grade == "24K" do
      case Stage.goldsmith(gid) do
        %{rank: "master"} -> true
        _ -> false
      end
    else
      true
    end
  end

  defp existing_crucible_overlap(cid, starts, ends) do
    not is_nil(
      DB.scalar(
        "SELECT 1 FROM castings WHERE crucible_id = ? AND starts_at < ? AND ends_at > ? LIMIT 1",
        [cid, ends, starts]
      )
    )
  end

  defp existing_smith_overlap(gid, starts, ends) do
    not is_nil(
      DB.scalar(
        "SELECT 1 FROM castings WHERE goldsmith_id = ? AND starts_at < ? AND ends_at > ? LIMIT 1",
        [gid, ends, starts]
      )
    )
  end

  defp batch_crucible_overlap?(accepted, cid, starts, ends) do
    Enum.any?(accepted, fn row ->
      row.crucible_id == cid and row.starts_at < ends and row.ends_at > starts
    end)
  end

  defp batch_smith_overlap?(accepted, gid, starts, ends) do
    Enum.any?(accepted, fn row ->
      row.goldsmith_id == gid and row.starts_at < ends and row.ends_at > starts
    end)
  end
end
EX

# ---------------- handlers/provenance.ex ----------------
cat > /app/lib/goldsmith/handlers/provenance.ex <<'EX'
defmodule Goldsmith.Handlers.Provenance do
  @moduledoc "GET /pieces/:id/provenance — parent_id chain with cycle guard."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, true} <- {:piece, Stage.piece_exists?(pid)} do
      chain = walk(pid, MapSet.new(), [])
      JsonUtil.ok(conn, 200, %{chain: Enum.reverse(chain)})
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, false} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
    end
  end

  defp walk(nil, _visited, acc), do: acc

  defp walk(pid, visited, acc) do
    if MapSet.member?(visited, pid) do
      acc
    else
      case DB.one(
             "SELECT id, serial, intent_kind, alloy_grade, parent_id FROM pieces WHERE id = ?",
             [pid]
           ) do
        nil -> acc
        [id, serial, kind, grade, parent] ->
          row = %{piece_id: id, serial: serial, intent_kind: kind, alloy_grade: grade}
          walk(parent, MapSet.put(visited, id), [row | acc])
      end
    end
  end
end
EX

# ---------------- handlers/contribution.ex ----------------
cat > /app/lib/goldsmith/handlers/contribution.ex <<'EX'
defmodule Goldsmith.Handlers.Contribution do
  @moduledoc "GET /pieces/:id/contribution — DAG walk."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, true} <- {:piece, Stage.piece_exists?(pid)} do
      result = walk(pid, 1.0, MapSet.new(), %{})
      ids = result |> Map.keys() |> Enum.sort()

      roots =
        Enum.map(ids, fn rid ->
          [serial, kind] =
            DB.one("SELECT serial, intent_kind FROM pieces WHERE id = ?", [rid])
          %{
            root_piece_id: rid,
            serial: serial,
            intent_kind: kind,
            contribution: Float.round(Map.get(result, rid), 6)
          }
        end)

      JsonUtil.ok(conn, 200, %{piece_id: pid, root_contributions: roots})
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, false} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
    end
  end

  defp walk(pid, weight, path, acc) do
    if MapSet.member?(path, pid) do
      acc
    else
      components =
        DB.query!(
          "SELECT source_piece_id, fraction FROM piece_components WHERE piece_id = ? ORDER BY source_piece_id ASC",
          [pid]
        )

      case components do
        [] ->
          Map.update(acc, pid, weight, &(&1 + weight))

        rows ->
          new_path = MapSet.put(path, pid)
          Enum.reduce(rows, acc, fn [src, frac], acc2 ->
            walk(src, weight * frac, new_path, acc2)
          end)
      end
    end
  end
end
EX

# ---------------- handlers/trend.ex ----------------
cat > /app/lib/goldsmith/handlers/trend.ex <<'EX'
defmodule Goldsmith.Handlers.Trend do
  @moduledoc "GET /pieces/:id/trend — four-statistic monthly assay-fineness trend."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, true} <- {:piece, Stage.piece_exists?(pid)} do
      buckets = bucketed(pid)
      stats = analyze(buckets)

      JsonUtil.ok(conn, 200, %{
        piece_id: pid,
        n_buckets: length(buckets),
        buckets: Enum.map(buckets, fn {m, v} -> %{month: m, mean_fineness: Float.round(v, 6)} end),
        slope: stats.slope,
        r2: stats.r2,
        mk_z: stats.mk_z,
        ts_slope: stats.ts_slope,
        direction: stats.direction
      })
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, false} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
    end
  end

  defp bucketed(pid) do
    DB.query!(
      "SELECT performed_at, fineness_per_mille FROM assays WHERE piece_id = ?",
      [pid]
    )
    |> Enum.group_by(fn [ts, _] -> String.slice(ts, 0, 7) end, fn [_, v] -> v * 1.0 end)
    |> Enum.map(fn {month, vs} -> {month, Enum.sum(vs) / length(vs)} end)
    |> Enum.sort_by(fn {m, _} -> m end)
  end

  defp analyze(buckets) do
    n = length(buckets)

    if n < 3 do
      %{slope: nil, r2: nil, mk_z: nil, ts_slope: nil, direction: nil}
    else
      xs = for i <- 0..(n - 1), do: i * 1.0
      ys = Enum.map(buckets, fn {_, v} -> v end)
      xbar = Enum.sum(xs) / n
      ybar = Enum.sum(ys) / n

      {num, den} =
        Enum.zip(xs, ys)
        |> Enum.reduce({0.0, 0.0}, fn {x, y}, {n_acc, d_acc} ->
          {n_acc + (x - xbar) * (y - ybar), d_acc + (x - xbar) * (x - xbar)}
        end)

      slope = if den == 0.0, do: 0.0, else: num / den
      intercept = ybar - slope * xbar

      {ss_res, ss_tot} =
        Enum.zip(xs, ys)
        |> Enum.reduce({0.0, 0.0}, fn {x, y}, {sr, st} ->
          pred = slope * x + intercept
          {sr + (y - pred) * (y - pred), st + (y - ybar) * (y - ybar)}
        end)

      r2 = if ss_tot == 0.0, do: 1.0, else: 1.0 - ss_res / ss_tot

      # Mann-Kendall S — guard with i < j because Elixir 1.16+ ranges
      # like (i+1)..(n-1) flip direction when i+1 > n-1.
      s_stat =
        for i <- 0..(n - 1), j <- 0..(n - 1), i < j do
          yi = Enum.at(ys, i)
          yj = Enum.at(ys, j)
          cond do
            yj > yi -> 1
            yj < yi -> -1
            true -> 0
          end
        end
        |> Enum.sum()

      # Tie correction
      tie_corr =
        ys
        |> Enum.frequencies()
        |> Map.values()
        |> Enum.filter(&(&1 >= 2))
        |> Enum.map(fn g -> g * (g - 1) * (2 * g + 5) end)
        |> Enum.sum()

      var_s = (n * (n - 1) * (2 * n + 5) - tie_corr) / 18.0

      mk_z =
        cond do
          var_s <= 0.0 -> 0.0
          s_stat > 0 -> (s_stat - 1) / :math.sqrt(var_s)
          s_stat < 0 -> (s_stat + 1) / :math.sqrt(var_s)
          true -> 0.0
        end

      # Theil-Sen median pairwise slope — same range-flip guard.
      slopes =
        for i <- 0..(n - 1), j <- 0..(n - 1), i < j do
          (Enum.at(ys, j) - Enum.at(ys, i)) / (Enum.at(xs, j) - Enum.at(xs, i))
        end
        |> Enum.sort()

      ts_slope =
        if rem(length(slopes), 2) == 1 do
          Enum.at(slopes, div(length(slopes), 2))
        else
          mid = div(length(slopes), 2)
          (Enum.at(slopes, mid - 1) + Enum.at(slopes, mid)) / 2.0
        end

      direction =
        cond do
          slope >= 0.5 and r2 >= 0.5 and mk_z >= 1.96 and ts_slope > 0 -> "refining"
          slope <= -0.5 and r2 >= 0.5 and mk_z <= -1.96 and ts_slope < 0 -> "degrading"
          true -> "stable"
        end

      %{
        slope: Float.round(slope, 6),
        r2: Float.round(r2, 6),
        mk_z: Float.round(mk_z, 6),
        ts_slope: Float.round(ts_slope, 6),
        direction: direction
      }
    end
  end
end
EX

# ---------------- handlers/workload.ex ----------------
cat > /app/lib/goldsmith/handlers/workload.ex <<'EX'
defmodule Goldsmith.Handlers.Workload do
  @moduledoc "GET /goldsmiths/:id/workload — composite_grade + active roster."
  alias Goldsmith.{Config, DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:gid, gid} when is_integer(gid) <- {:gid, Stage.parse_id(id_str)},
         {:smith, %{} = smith} <- {:smith, Stage.goldsmith(gid)} do
      actives =
        DB.query!(
          "SELECT id, serial, intent_kind, alloy_grade, stage FROM pieces WHERE assigned_goldsmith = ? AND stage != 'released' ORDER BY id ASC",
          [gid]
        )

      letter_map = Config.letter_values()

      grade_pairs =
        Enum.map(actives, fn [pid, _serial, intent, _grade, _stage] ->
          case DB.scalar(
                 "SELECT letter FROM hallmarks WHERE piece_id = ? ORDER BY recorded_at DESC LIMIT 1",
                 [pid]
               ) do
            nil -> nil
            letter ->
              factor =
                if intent == smith.specialty,
                  do: Config.threshold(["specialty_factor_match"]),
                  else: Config.threshold(["specialty_factor_default"])
              {Map.get(letter_map, letter, 0), factor}
          end
        end)
        |> Enum.reject(&is_nil/1)

      composite =
        case grade_pairs do
          [] -> nil
          pairs ->
            letter_base = Enum.sum(Enum.map(pairs, fn {l, _} -> l end)) / length(pairs)
            spec_factor = Enum.sum(Enum.map(pairs, fn {_, f} -> f end)) / length(pairs)

            streak_letters =
              DB.query!(
                "SELECT letter FROM hallmarks WHERE goldsmith_id = ? ORDER BY recorded_at DESC LIMIT ?",
                [gid, Config.threshold(["streak_letters_required"])]
              )
              |> Enum.map(fn [l] -> l end)

            required = Config.threshold(["streak_letters_required"])
            bonus =
              if length(streak_letters) == required and Enum.all?(streak_letters, &(&1 == "A")),
                do: Config.threshold(["streak_bonus"]),
                else: 0.0

            raw = letter_base * spec_factor * (1.0 + bonus)
            Float.round(raw, Config.threshold(["composite_round_decimals"]))
        end

      active_payload =
        Enum.map(actives, fn [pid, serial, intent, grade, stage] ->
          %{piece_id: pid, serial: serial, intent_kind: intent,
            alloy_grade: grade, stage: stage}
        end)

      JsonUtil.ok(conn, 200, %{
        goldsmith_id: gid,
        name: smith.name,
        specialty: smith.specialty,
        active_pieces: active_payload,
        composite_grade: composite
      })
    else
      {:gid, :error} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "non-integer id")
      {:smith, nil} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "no such goldsmith")
    end
  end
end
EX

# ---------------- handlers/cohort.ex ----------------
cat > /app/lib/goldsmith/handlers/cohort.ex <<'EX'
defmodule Goldsmith.Handlers.Cohort do
  @moduledoc "GET /goldsmiths/:id/cohort — BFS in the mentee direction."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:gid, gid} when is_integer(gid) <- {:gid, Stage.parse_id(id_str)},
         {:smith, true} <- {:smith, Stage.goldsmith_exists?(gid)} do
      [name] = DB.one("SELECT name FROM goldsmiths WHERE id = ?", [gid])
      members = bfs([{gid, name, 0}], MapSet.new([gid]), [{gid, name, 0}])

      payload =
        members
        |> Enum.sort_by(fn {id, _name, depth} -> {depth, id} end)
        |> Enum.map(fn {id, n, _depth} ->
          %{goldsmith_id: id, name: n, released_pieces: released_count(id)}
        end)

      total = Enum.sum(Enum.map(payload, & &1.released_pieces))

      JsonUtil.ok(conn, 200, %{
        root_goldsmith_id: gid,
        members: payload,
        cohort_total_released: total
      })
    else
      {:gid, :error} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "non-integer id")
      {:smith, false} -> JsonUtil.err(conn, 404, "goldsmith_not_found", "no such goldsmith")
    end
  end

  defp bfs([], _visited, acc), do: acc

  defp bfs([{parent_id, _name, depth} | rest], visited, acc) do
    children =
      DB.query!(
        "SELECT id, name FROM goldsmiths WHERE mentor_id = ? ORDER BY id ASC",
        [parent_id]
      )

    {new_visited, new_frontier, new_acc} =
      Enum.reduce(children, {visited, [], acc}, fn [cid, cname], {v, f, a} ->
        if MapSet.member?(v, cid) do
          {v, f, a}
        else
          {MapSet.put(v, cid), f ++ [{cid, cname, depth + 1}], a ++ [{cid, cname, depth + 1}]}
        end
      end)

    bfs(rest ++ new_frontier, new_visited, new_acc)
  end

  defp released_count(gid) do
    case DB.scalar(
           "SELECT COUNT(DISTINCT p.id) FROM pieces p JOIN hallmarks h ON h.piece_id = p.id WHERE p.stage = 'released' AND h.goldsmith_id = ?",
           [gid]
         ) do
      n when is_integer(n) -> n
      _ -> 0
    end
  end
end
EX

# ---------------- handlers/search.ex ----------------
cat > /app/lib/goldsmith/handlers/search.ex <<'EX'
defmodule Goldsmith.Handlers.Search do
  @moduledoc "GET /pieces/search — AND filter."
  alias Goldsmith.{Config, DB, JsonUtil}

  def call(conn) do
    qs = Plug.Conn.fetch_query_params(conn).query_params
    stage = Map.get(qs, "stage")
    intent = Map.get(qs, "intent_kind")
    grade = Map.get(qs, "alloy_grade")
    smith_raw = Map.get(qs, "goldsmith")

    cond do
      not is_nil(stage) and stage not in Config.valid_stages() ->
        JsonUtil.err(conn, 422, "invalid_filter", "unknown stage")

      not is_nil(intent) and intent not in Config.valid_kinds() ->
        JsonUtil.err(conn, 422, "invalid_filter", "unknown intent_kind")

      not is_nil(grade) and grade not in Config.valid_grades() ->
        JsonUtil.err(conn, 422, "invalid_filter", "unknown alloy_grade")

      not is_nil(smith_raw) and not Regex.match?(~r/^\d+$/, smith_raw) ->
        JsonUtil.err(conn, 422, "invalid_goldsmith_id", "goldsmith must be integer")

      true ->
        smith_id = if is_nil(smith_raw), do: nil, else: String.to_integer(smith_raw)
        {sql, params} = build_query(stage, intent, grade, smith_id)
        rows = DB.query!(sql, params)

        pieces =
          Enum.map(rows, fn [id, serial, kind, gr, stg, smith, parent] ->
            %{piece_id: id, serial: serial, intent_kind: kind, alloy_grade: gr,
              stage: stg, assigned_goldsmith: smith, parent_id: parent}
          end)

        JsonUtil.ok(conn, 200, %{pieces: pieces})
    end
  end

  defp build_query(stage, intent, grade, smith_id) do
    base = "SELECT id, serial, intent_kind, alloy_grade, stage, assigned_goldsmith, parent_id FROM pieces WHERE 1=1"
    {wheres, params} =
      [{stage, "stage = ?"}, {intent, "intent_kind = ?"}, {grade, "alloy_grade = ?"},
       {smith_id, "assigned_goldsmith = ?"}]
      |> Enum.reduce({[], []}, fn
        {nil, _}, acc -> acc
        {v, clause}, {ws, ps} -> {ws ++ [clause], ps ++ [v]}
      end)

    sql = base <> Enum.reduce(wheres, "", fn w, acc -> acc <> " AND " <> w end) <> " ORDER BY id ASC"
    {sql, params}
  end
end
EX

# ---------------- handlers/bulk_hallmark.ex ----------------
cat > /app/lib/goldsmith/handlers/bulk_hallmark.ex <<'EX'
defmodule Goldsmith.Handlers.BulkHallmark do
  @moduledoc "POST /pieces/bulk-hallmark — atomic batch."
  alias Goldsmith.{Audit, DB, JsonUtil, Stage}

  def call(conn) do
    with {:body, {:ok, body, conn}} <- {:body, JsonUtil.parse_body(conn)},
         {:arr, arr} when is_list(arr) and arr != [] <-
           {:arr, Map.get(body, "hallmarks")},
         :ok <- check_dup(arr),
         {:rows, []} <- {:rows, collect_errors(arr)} do
      recorded_at = JsonUtil.iso_now()

      ids =
        Enum.map(arr, fn row ->
          {:ok, _} =
            DB.query(
              "INSERT INTO hallmarks (piece_id, goldsmith_id, letter, notes, recorded_at) VALUES (?, ?, ?, ?, ?)",
              [Map.get(row, "piece_id"), Map.get(row, "goldsmith_id"),
               Map.get(row, "letter"), Map.get(row, "notes"), recorded_at]
            )
          DB.last_insert_rowid()
        end)

      first_id = List.first(ids)
      _ = Audit.append!("bulk_hallmark", "#{length(ids)}|#{first_id}|#{recorded_at}")

      JsonUtil.ok(conn, 201, %{
        count: length(ids),
        hallmark_ids: ids,
        recorded_at: recorded_at
      })
    else
      {:body, {:halt, conn}} -> conn
      {:arr, _} -> JsonUtil.err(conn, 422, "empty_batch", "hallmarks array required and non-empty")
      {:err, idx} -> JsonUtil.err(conn, 422, "dup_in_batch",
                                  "duplicate (piece_id, goldsmith_id) at index #{idx}")
      {:rows, errors} ->
        JsonUtil.err(conn, 422, "validation_failed", "see errors array",
                     %{errors: errors})
    end
  end

  defp check_dup(arr) do
    arr
    |> Enum.with_index()
    |> Enum.reduce_while(MapSet.new(), fn {row, idx}, seen ->
      pid = Map.get(row, "piece_id")
      gid = Map.get(row, "goldsmith_id")
      if is_integer(pid) and is_integer(gid) do
        key = {pid, gid}
        if MapSet.member?(seen, key) do
          {:halt, {:err, idx}}
        else
          {:cont, MapSet.put(seen, key)}
        end
      else
        {:cont, seen}
      end
    end)
    |> case do
      %MapSet{} -> :ok
      {:err, idx} -> {:err, idx}
    end
  end

  defp collect_errors(arr) do
    arr
    |> Enum.with_index()
    |> Enum.map(fn {row, idx} ->
      cond do
        not is_integer(Map.get(row, "piece_id")) ->
          %{index: idx, code: "missing_field", detail: "piece_id required"}

        is_nil(Stage.lookup_piece(Map.get(row, "piece_id"))) ->
          %{index: idx, code: "piece_not_found",
            detail: "no such piece #{Map.get(row, "piece_id")}"}

        Stage.lookup_piece(Map.get(row, "piece_id")).stage == "released" ->
          %{index: idx, code: "already_released",
            detail: "piece #{Map.get(row, "piece_id")} released"}

        Stage.lookup_piece(Map.get(row, "piece_id")).stage != "chased" ->
          %{index: idx, code: "wrong_stage",
            detail: "piece must be chased"}

        not is_integer(Map.get(row, "goldsmith_id")) ->
          %{index: idx, code: "missing_field", detail: "goldsmith_id required"}

        not Stage.goldsmith_exists?(Map.get(row, "goldsmith_id")) ->
          %{index: idx, code: "goldsmith_not_found",
            detail: "no such goldsmith #{Map.get(row, "goldsmith_id")}"}

        Map.get(row, "letter") not in ["A", "B", "C", "F"] ->
          %{index: idx, code: "invalid_letter", detail: "letter must be A/B/C/F"}

        true ->
          nil
      end
    end)
    |> Enum.reject(&is_nil/1)
  end
end
EX

# ---------------- handlers/audit.ex ----------------
cat > /app/lib/goldsmith/handlers/audit.ex <<'EX'
defmodule Goldsmith.Handlers.Audit do
  @moduledoc "GET /audit (paginate) + GET /audit/verify (validate chain)."
  alias Goldsmith.{Audit, Config, DB, JsonUtil}

  def list(conn) do
    qs = Plug.Conn.fetch_query_params(conn).query_params
    since = parse_int(Map.get(qs, "since", "0"), 0)
    default_limit = Config.threshold(["audit", "default_limit"])
    max_limit = Config.threshold(["audit", "max_limit"])
    limit =
      parse_int(Map.get(qs, "limit", to_string(default_limit)), default_limit)
      |> min(max_limit)
      |> max(1)

    rows =
      DB.query!(
        "SELECT seq, action, payload, prev_hash, entry_hash, occurred_at FROM audit_entries WHERE seq > ? ORDER BY seq ASC LIMIT ?",
        [since, limit]
      )

    entries =
      Enum.map(rows, fn [seq, action, payload, prev, hash, occurred_at] ->
        %{seq: seq, action: action, payload: payload, prev_hash: prev,
          entry_hash: hash, occurred_at: occurred_at}
      end)

    JsonUtil.ok(conn, 200, %{entries: entries})
  end

  def verify(conn) do
    rows =
      DB.query!(
        "SELECT seq, action, payload, prev_hash, entry_hash FROM audit_entries ORDER BY seq ASC"
      )

    result =
      Enum.reduce_while(rows, {Audit.genesis(), 0}, fn
        [seq, action, payload, prev, hash], {expected_prev, n} ->
          expected = Audit.compute_hash(prev, action, payload)
          cond do
            prev != expected_prev ->
              {:halt, {:broken, seq, n + 1}}
            hash != expected ->
              {:halt, {:broken, seq, n + 1}}
            true ->
              {:cont, {hash, n + 1}}
          end
      end)

    case result do
      {_hash, n} ->
        JsonUtil.ok(conn, 200, %{verified: true, entries_checked: n})

      {:broken, seq, n} ->
        JsonUtil.ok(conn, 200, %{verified: false, entries_checked: n,
                                 first_broken_seq: seq})
    end
  end

  defp parse_int(s, default) when is_binary(s) do
    case Integer.parse(s) do
      {n, ""} when n >= 0 -> n
      _ -> default
    end
  end

  defp parse_int(_, default), do: default
end
EX

# ---------------- handlers/lineage_grade.ex ----------------
cat > /app/lib/goldsmith/handlers/lineage_grade.ex <<'EX'
defmodule Goldsmith.Handlers.LineageGrade do
  @moduledoc "GET /pieces/:id/lineage-grade — depth-weighted ancestor walk."
  alias Goldsmith.{Config, DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, %{} = piece} <- {:piece, Stage.lookup_piece(pid)} do
      letter_values = Config.letter_values()
      ancestors = walk(piece.parent_id, 1, MapSet.new([piece.id]), [], letter_values)
      hallmarked = Enum.reject(ancestors, &(&1.mean_letter == nil))

      cond do
        length(hallmarked) < 2 ->
          JsonUtil.err(conn, 422, "empty_lineage",
            "fewer than 2 hallmarked ancestors reachable")

        true ->
          weighted_sum =
            Enum.reduce(hallmarked, 0.0, fn a, acc -> acc + a.weight * a.mean_letter end)

          weight_sum =
            Enum.reduce(hallmarked, 0.0, fn a, acc -> acc + a.weight end)

          lineage = weighted_sum / weight_sum

          payload =
            hallmarked
            |> Enum.sort_by(& &1.depth)
            |> Enum.map(fn a ->
              %{piece_id: a.piece_id, depth: a.depth,
                mean_letter: Float.round(a.mean_letter, 6),
                weight: Float.round(a.weight, 6)}
            end)

          JsonUtil.ok(conn, 200, %{
            piece_id: pid,
            lineage_grade: Float.round(lineage, 6),
            ancestors: payload
          })
      end
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
    end
  end

  defp walk(nil, _depth, _visited, acc, _letters), do: Enum.reverse(acc)

  defp walk(pid, depth, visited, acc, letters) do
    if MapSet.member?(visited, pid) do
      Enum.reverse(acc)
    else
      case DB.one("SELECT id, parent_id FROM pieces WHERE id = ?", [pid]) do
        nil -> Enum.reverse(acc)
        [id, parent] ->
          mean = mean_letter(id, letters)
          weight = :math.pow(0.5, depth)
          entry = %{piece_id: id, depth: depth, mean_letter: mean, weight: weight}
          walk(parent, depth + 1, MapSet.put(visited, id), [entry | acc], letters)
      end
    end
  end

  defp mean_letter(pid, letters) do
    rows = DB.query!("SELECT letter FROM hallmarks WHERE piece_id = ?", [pid])

    case rows do
      [] -> nil
      _ ->
        values = Enum.map(rows, fn [l] -> Map.get(letters, l, 0) end)
        Enum.sum(values) / length(values) * 1.0
    end
  end
end
EX

# ---------------- handlers/mass_attribution.ex ----------------
cat > /app/lib/goldsmith/handlers/mass_attribution.ex <<'EX'
defmodule Goldsmith.Handlers.MassAttribution do
  @moduledoc "GET /pieces/:id/mass-attribution — DAG walk that propagates grams."
  alias Goldsmith.{DB, JsonUtil, Stage}

  def call(conn, id_str) do
    with {:pid, pid} when is_integer(pid) <- {:pid, Stage.parse_id(id_str)},
         {:piece, %{} = piece} <- {:piece, Stage.lookup_piece(pid)} do
      result = walk(pid, piece.target_mass_g * 1.0, MapSet.new(), %{})
      ids = result |> Map.keys() |> Enum.sort()

      roots =
        Enum.map(ids, fn rid ->
          [serial, kind] =
            DB.one("SELECT serial, intent_kind FROM pieces WHERE id = ?", [rid])
          %{
            root_piece_id: rid,
            serial: serial,
            intent_kind: kind,
            attribution_g: Float.round(Map.get(result, rid), 6)
          }
        end)

      JsonUtil.ok(conn, 200, %{
        piece_id: pid,
        target_mass_g: piece.target_mass_g * 1.0,
        root_attributions: roots
      })
    else
      {:pid, :error} -> JsonUtil.err(conn, 404, "piece_not_found", "non-integer id")
      {:piece, nil} -> JsonUtil.err(conn, 404, "piece_not_found", "no such piece")
    end
  end

  defp walk(pid, mass, path, acc) do
    if MapSet.member?(path, pid) do
      acc
    else
      components =
        DB.query!(
          "SELECT source_piece_id, fraction FROM piece_components WHERE piece_id = ? ORDER BY source_piece_id ASC",
          [pid]
        )

      case components do
        [] ->
          Map.update(acc, pid, mass, &(&1 + mass))

        rows ->
          new_path = MapSet.put(path, pid)
          Enum.reduce(rows, acc, fn [src, frac], acc2 ->
            walk(src, mass * frac, new_path, acc2)
          end)
      end
    end
  end
end
EX

# Stop any running instance so the rebuild's binary actually serves.
pkill -f "elixir .* -S mix run" 2>/dev/null || true
sleep 1

# Rebuild and relaunch via start.sh (it handles the readiness probe).
cd /app
MIX_ENV=prod mix compile 2>&1 | tee /app/logs/build.log

bash /app/start.sh
