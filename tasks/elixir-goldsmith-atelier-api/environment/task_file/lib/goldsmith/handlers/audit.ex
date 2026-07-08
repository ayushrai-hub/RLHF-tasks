defmodule Goldsmith.Handlers.Audit do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def list(conn) do
    JsonUtil.err(conn, 501, "not_implemented", "audit list handler is unimplemented")
  end

  def verify(conn) do
    JsonUtil.err(conn, 501, "not_implemented", "audit verify handler is unimplemented")
  end
end
