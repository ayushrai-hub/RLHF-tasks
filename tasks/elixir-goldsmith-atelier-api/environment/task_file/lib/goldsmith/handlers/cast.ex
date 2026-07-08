defmodule Goldsmith.Handlers.Cast do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "cast handler is unimplemented")
  end
end
