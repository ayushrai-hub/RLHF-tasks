defmodule Goldsmith.Handlers.BulkCast do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn) do
    JsonUtil.err(conn, 501, "not_implemented", "bulk cast handler is unimplemented")
  end
end
