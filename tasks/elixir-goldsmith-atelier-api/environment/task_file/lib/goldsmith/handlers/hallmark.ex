defmodule Goldsmith.Handlers.Hallmark do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "hallmark handler is unimplemented")
  end
end
