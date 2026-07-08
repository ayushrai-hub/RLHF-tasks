defmodule Goldsmith.Router do
  @moduledoc """
  Plug.Router top-level. We deliberately do NOT mount Plug.Parsers so that a
  malformed JSON payload can be rendered as `422 invalid_body` rather than
  surfaced as a 500. Handlers call `Goldsmith.JsonUtil.parse_body/1` to read
  and decode JSON on demand.
  """
  use Plug.Router
  alias Goldsmith.JsonUtil
  alias Goldsmith.Handlers

  plug :match
  plug :dispatch

  # ---- already implemented -------------------------------------------------

  get "/health" do
    JsonUtil.ok(conn, 200, %{status: "ok"})
  end

  post "/goldsmiths" do
    Handlers.Goldsmiths.create(conn)
  end

  post "/pieces" do
    Handlers.Pieces.create(conn)
  end

  get "/pieces/search" do
    Handlers.Search.call(conn)
  end

  get "/pieces/:id" do
    Handlers.Pieces.show(conn, id)
  end

  # ---- remaining endpoints -------------------------------------------------

  post "/goldsmiths/:gid/assign" do
    Handlers.Assign.call(conn, gid)
  end

  post "/pieces/:id/advance-stage" do
    Handlers.Advance.call(conn, id)
  end

  post "/pieces/:id/cast" do
    Handlers.Cast.call(conn, id)
  end

  post "/pieces/bulk-cast" do
    Handlers.BulkCast.call(conn)
  end

  post "/pieces/:id/assay" do
    Handlers.Assay.call(conn, id)
  end

  post "/pieces/:id/hallmark" do
    Handlers.Hallmark.call(conn, id)
  end

  post "/pieces/:id/release" do
    Handlers.Release.call(conn, id)
  end

  post "/pieces/bulk-hallmark" do
    Handlers.BulkHallmark.call(conn)
  end

  get "/pieces/:id/provenance" do
    Handlers.Provenance.call(conn, id)
  end

  get "/pieces/:id/contribution" do
    Handlers.Contribution.call(conn, id)
  end

  get "/pieces/:id/lineage-grade" do
    Handlers.LineageGrade.call(conn, id)
  end

  get "/pieces/:id/mass-attribution" do
    Handlers.MassAttribution.call(conn, id)
  end

  get "/pieces/:id/trend" do
    Handlers.Trend.call(conn, id)
  end

  get "/goldsmiths/:id/workload" do
    Handlers.Workload.call(conn, id)
  end

  get "/goldsmiths/:id/cohort" do
    Handlers.Cohort.call(conn, id)
  end

  get "/audit" do
    Handlers.Audit.list(conn)
  end

  get "/audit/verify" do
    Handlers.Audit.verify(conn)
  end

  match _ do
    JsonUtil.err(conn, 404, "route_not_found", "no route #{conn.request_path}")
  end
end
