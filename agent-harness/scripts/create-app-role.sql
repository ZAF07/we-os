-- The role the service connects as.
--
-- It is deliberately NOT a superuser. Row-level security does not constrain a
-- superuser, so connecting as one would give the app tenant isolation that
-- looks like it works and does not. `marketing-os init-db --app-role` grants it
-- table access after the schema exists.
CREATE ROLE marketing_os_app LOGIN PASSWORD 'marketing_os_app';
