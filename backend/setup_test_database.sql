-- ============================================================================
-- Test Database Setup for Academic Credential Verification Platform
-- ============================================================================
-- Run this as the postgres superuser:
--   psql -U postgres -f setup_test_database.sql
-- ============================================================================

-- Step 1: Create test database
CREATE DATABASE credential_db_test
    WITH ENCODING 'UTF8'
    TEMPLATE template0;

-- Step 2: Grant privileges to the application user
GRANT CONNECT ON DATABASE credential_db_test TO credential_app_user;

-- Step 3: Connect to test database and set up privileges
\c credential_db_test

-- Enable required extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Grant schema privileges
GRANT USAGE ON SCHEMA public TO credential_app_user;
GRANT CREATE ON SCHEMA public TO credential_app_user;

-- Grant table privileges (for tables created by Alembic migrations)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO credential_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO credential_app_user;

\echo '=== Test Database Setup Complete ==='
\echo 'Database: credential_db_test'
\echo 'User: credential_app_user'
