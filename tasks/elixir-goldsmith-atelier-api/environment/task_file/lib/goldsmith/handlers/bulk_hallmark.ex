defmodule Goldsmith.Handlers.BulkHallmark do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn) do
    JsonUtil.err(conn, 501, "not_implemented", "bulk-hallmark handler is unimplemented")
  end
end
