defmodule Goldsmith.Handlers.Contribution do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "contribution handler is unimplemented")
  end
end
