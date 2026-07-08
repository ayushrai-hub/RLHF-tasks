defmodule Goldsmith.Handlers.LineageGrade do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "lineage-grade handler is unimplemented")
  end
end
