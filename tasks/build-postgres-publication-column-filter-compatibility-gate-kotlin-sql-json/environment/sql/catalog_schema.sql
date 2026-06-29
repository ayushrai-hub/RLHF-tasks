CREATE TABLE tables (
  schema_name TEXT NOT NULL,
  table_name TEXT NOT NULL,
  replica_identity TEXT NOT NULL
);

CREATE TABLE columns (
  schema_name TEXT NOT NULL,
  table_name TEXT NOT NULL,
  column_name TEXT NOT NULL,
  data_type TEXT NOT NULL,
  nullable INTEGER NOT NULL,
  primary_key INTEGER NOT NULL
);

CREATE TABLE publications (
  publication_name TEXT NOT NULL
);

CREATE TABLE publication_tables (
  publication_name TEXT NOT NULL,
  schema_name TEXT NOT NULL,
  table_name TEXT NOT NULL,
  columns_json TEXT NOT NULL
);

CREATE TABLE subscriptions (
  subscription_name TEXT NOT NULL,
  publication_name TEXT NOT NULL
);

CREATE TABLE subscription_tables (
  subscription_name TEXT NOT NULL,
  schema_name TEXT NOT NULL,
  table_name TEXT NOT NULL,
  columns_json TEXT NOT NULL
);
