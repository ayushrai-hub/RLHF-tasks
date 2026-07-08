defmodule Goldsmith.DB do
  @moduledoc """
  Tiny serialised SQLite wrapper around `Exqlite`. Everything goes through
  a single connection held by this GenServer; that way Exqlite's BUSY
  semantics never trip on a concurrent write. The runtime workload is low,
  so the simple setup is enough here.
  """
  use GenServer

  alias Exqlite.Sqlite3

  # ---- public API ----------------------------------------------------------

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "Run a parameterised SQL statement; returns {:ok, rows} | {:error, reason}."
  def query(sql, params \\ []) do
    GenServer.call(__MODULE__, {:query, sql, params}, 15_000)
  end

  @doc "Like `query/2` but raises on failure."
  def query!(sql, params \\ []) do
    case query(sql, params) do
      {:ok, rows} -> rows
      {:error, reason} -> raise "DB error #{inspect(reason)} sql=#{inspect(sql)}"
    end
  end

  @doc "Convenience: returns the first row or nil."
  def one(sql, params \\ []) do
    case query(sql, params) do
      {:ok, [row | _]} -> row
      _ -> nil
    end
  end

  @doc "Convenience: returns the first row's first column or nil."
  def scalar(sql, params \\ []) do
    case one(sql, params) do
      nil -> nil
      [v | _] -> v
      v when is_tuple(v) -> elem(v, 0)
      v -> v
    end
  end

  @doc "Returns the SQLite rowid for the last successful INSERT on the shared connection."
  def last_insert_rowid do
    GenServer.call(__MODULE__, :last_insert_rowid)
  end

  @doc "Runs the given 0-arg fn inside an immediate transaction."
  def transaction(fun) when is_function(fun, 0) do
    GenServer.call(__MODULE__, {:transaction, fun}, 30_000)
  end

  # ---- bootstrap (called once before children start) -----------------------

  def bootstrap!(db_path) do
    fresh? = not File.exists?(db_path)
    {:ok, conn} = Sqlite3.open(db_path)
    :ok = Sqlite3.execute(conn, "PRAGMA journal_mode = WAL;")
    :ok = Sqlite3.execute(conn, "PRAGMA foreign_keys = ON;")

    if fresh? do
      schema_sql = File.read!(seed_path("schema.sql"))
      seed_sql = File.read!(seed_path("seed.sql"))
      :ok = Sqlite3.execute(conn, schema_sql)
      :ok = Sqlite3.execute(conn, seed_sql)
    end

    :ok = Sqlite3.close(conn)
    :ok
  end

  defp seed_path(name) do
    base = Application.get_env(:goldsmith, :seed_dir, "/app/seed")
    Path.join(base, name)
  end

  # ---- GenServer plumbing --------------------------------------------------

  @impl true
  def init(opts) do
    db_path = Keyword.fetch!(opts, :db_path)
    {:ok, conn} = Sqlite3.open(db_path)
    :ok = Sqlite3.execute(conn, "PRAGMA foreign_keys = ON;")
    {:ok, %{conn: conn}}
  end

  @impl true
  def handle_call({:query, sql, params}, _from, %{conn: conn} = state) do
    {:reply, do_query(conn, sql, params), state}
  end

  def handle_call(:last_insert_rowid, _from, %{conn: conn} = state) do
    {:ok, stmt} = Sqlite3.prepare(conn, "SELECT last_insert_rowid()")
    {:row, [rowid]} = Sqlite3.step(conn, stmt)
    :ok = Sqlite3.release(conn, stmt)
    {:reply, rowid, state}
  end

  def handle_call({:transaction, fun}, _from, %{conn: conn} = state) do
    case do_query(conn, "BEGIN IMMEDIATE", []) do
      {:ok, _} ->
        try do
          result = fun.()
          {:ok, _} = do_query(conn, "COMMIT", [])
          {:reply, {:ok, result}, state}
        rescue
          err ->
            do_query(conn, "ROLLBACK", [])
            {:reply, {:error, {:exception, err, __STACKTRACE__}}, state}
        catch
          kind, reason ->
            do_query(conn, "ROLLBACK", [])
            {:reply, {:error, {kind, reason}}, state}
        end

      err ->
        {:reply, err, state}
    end
  end

  defp do_query(conn, sql, params) do
    with {:ok, stmt} <- Sqlite3.prepare(conn, sql),
         :ok <- Sqlite3.bind(stmt, params),
         {:ok, rows} <- fetch_all(conn, stmt, []) do
      :ok = Sqlite3.release(conn, stmt)
      {:ok, rows}
    else
      err -> err
    end
  end

  defp fetch_all(conn, stmt, acc) do
    case Sqlite3.step(conn, stmt) do
      :done -> {:ok, Enum.reverse(acc)}
      {:row, row} -> fetch_all(conn, stmt, [row | acc])
      err -> err
    end
  end
end
