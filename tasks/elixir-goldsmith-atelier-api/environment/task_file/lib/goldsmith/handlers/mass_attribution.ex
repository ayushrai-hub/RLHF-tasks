defmodule Goldsmith.Handlers.MassAttribution do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "mass-attribution handler is unimplemented")
  end
end
