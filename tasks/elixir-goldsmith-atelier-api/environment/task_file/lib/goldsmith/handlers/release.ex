defmodule Goldsmith.Handlers.Release do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "release handler is unimplemented")
  end
end
