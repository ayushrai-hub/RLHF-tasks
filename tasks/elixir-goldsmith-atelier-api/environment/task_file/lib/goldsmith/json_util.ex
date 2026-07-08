defmodule Goldsmith.JsonUtil do
  @moduledoc """
  Centralised JSON helpers. Use `ok/3` and `err/4` from every handler to
  ensure response bodies follow the `{error, detail}` contract.
  """
  import Plug.Conn

  @doc "Send a 200/201 JSON success body. Returns the modified conn."
  def ok(conn, status, body) when is_map(body) or is_list(body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end

  @doc "Send a 4xx/5xx JSON error body with the shared `{error, detail}` shape."
  def err(conn, status, code, detail, extra \\ %{}) do
    payload = Map.merge(%{error: code, detail: detail}, extra)
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(payload))
  end

  @doc """
  Parses the JSON body. Returns `{:ok, parsed, conn}` or already sends a
  422 invalid_body and returns `{:halt, conn}`.
  """
  def parse_body(conn) do
    case conn.body_params do
      %Plug.Conn.Unfetched{} ->
        # Plug.Parsers didn't run (or content-type isn't json) — try a raw read.
        case read_body_full(conn) do
          {:ok, "", conn2} ->
            {:ok, %{}, conn2}

          {:ok, raw, conn2} ->
            case Jason.decode(raw) do
              {:ok, parsed} when is_map(parsed) -> {:ok, parsed, conn2}
              {:ok, _other} -> {:halt, err(conn2, 422, "invalid_body", "JSON body must be an object")}
              {:error, _} -> {:halt, err(conn2, 422, "invalid_body", "JSON body is malformed")}
            end

          _ ->
            {:halt, err(conn, 422, "invalid_body", "unable to read request body")}
        end

      %{} = body ->
        {:ok, body, conn}
    end
  end

  defp read_body_full(conn) do
    case Plug.Conn.read_body(conn, length: 1_000_000) do
      {:ok, raw, conn2} -> {:ok, raw, conn2}
      {:more, _partial, _conn2} -> :error
      err -> err
    end
  end

  @doc "Current time as ISO-8601 Zulu second-resolution."
  def iso_now do
    DateTime.utc_now()
    |> DateTime.truncate(:second)
    |> DateTime.to_iso8601()
    |> String.replace("+00:00", "Z")
  end

  @doc "Format a float to 6 decimal places (string)."
  def fmt6(x) when is_number(x) do
    :erlang.float_to_binary(x * 1.0, decimals: 6)
  end

  @doc "Round a float to n decimals using bankers-style binary (Float.round)."
  def round_to(x, n) when is_number(x) do
    Float.round(x * 1.0, n)
  end

  @doc "Read a string field from a parsed body or return nil."
  def s(body, key) do
    case Map.get(body, key) do
      v when is_binary(v) -> v
      _ -> nil
    end
  end

  @doc "Read an integer field, accepting JSON integers but not floats."
  def i(body, key) do
    case Map.get(body, key) do
      v when is_integer(v) -> v
      _ -> nil
    end
  end

  @doc "Read a numeric field as float (accepts integers and floats)."
  def f(body, key) do
    case Map.get(body, key) do
      v when is_number(v) -> v * 1.0
      _ -> nil
    end
  end
end
