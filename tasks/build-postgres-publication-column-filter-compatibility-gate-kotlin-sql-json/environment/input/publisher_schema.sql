CREATE TABLE public.accounts (
  id bigint PRIMARY KEY,
  email text NOT NULL,
  status text NOT NULL,
  updated_at timestamptz NOT NULL,
  internal_note text
);

CREATE TABLE public.orders (
  id bigint PRIMARY KEY,
  account_id bigint NOT NULL,
  total_cents integer NOT NULL,
  state text NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE public.audit_log (
  id bigint PRIMARY KEY,
  actor_id bigint NOT NULL,
  action text NOT NULL,
  metadata jsonb,
  created_at timestamptz NOT NULL
);

ALTER TABLE public.audit_log REPLICA IDENTITY FULL;
