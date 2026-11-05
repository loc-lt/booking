-- Runs once, when the Postgres volume is created.
-- The application role is NOT a superuser and has no BYPASSRLS: those skip row-level
-- security even with FORCE. CREATEDB lets pytest-django create its test database; drop it
-- outside local and CI.
CREATE ROLE booking_app LOGIN PASSWORD 'booking_app' NOSUPERUSER NOBYPASSRLS CREATEDB;
CREATE DATABASE booking_core OWNER booking_app;
