defmodule Goldsmith.Handlers.Workload do
  @moduledoc false
  alias Goldsmith.JsonUtil

  def call(conn, _id_str) do
    JsonUtil.err(conn, 501, "not_implemented", "workload handler is unimplemented")
  end
end
