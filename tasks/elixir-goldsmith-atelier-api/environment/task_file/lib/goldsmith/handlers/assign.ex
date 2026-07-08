defmodule Goldsmith.Handlers.Assign do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _gid_str) do
    JsonUtil.err(conn, 501, "not_implemented", "assign handler is unimplemented")
  end
end
