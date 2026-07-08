defmodule Goldsmith.Handlers.Search do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn) do
    JsonUtil.err(conn, 501, "not_implemented", "search handler is unimplemented")
  end
end
