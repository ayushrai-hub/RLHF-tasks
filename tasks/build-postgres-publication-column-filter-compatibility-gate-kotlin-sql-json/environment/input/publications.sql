CREATE PUBLICATION app_pub FOR TABLE public.accounts (id, email, status), public.orders (id, account_id, state);

CREATE PUBLICATION audit_pub;
ALTER PUBLICATION audit_pub ADD TABLE public.audit_log (id, actor_id, action);
