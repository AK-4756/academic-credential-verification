-- ============================================================================
-- Academic Credential Verification Platform — PostgreSQL Database Setup
-- ============================================================================
-- Source of truth: docs/implementation-roadmap.md L427-432
-- Run this script as the postgres superuser:
--   psql -U postgres -f setup_database.sql
-- ============================================================================

-- Step 1: Create application database
CREATE DATABASE credential_db
    WITH ENCODING 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE template0;

-- Step 2: Create application user
-- CHANGE THIS PASSWORD before running in production!
CREATE USER credential_app_user WITH PASSWORD 'dev_password_change_me';

-- Step 3: Grant privileges per database design
GRANT CONNECT ON DATABASE credential_db TO credential_app_user;

-- Step 4: Connect to the new database and set up privileges + extensions
\c credential_db

-- Enable required extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Grant schema privileges
GRANT USAGE ON SCHEMA public TO credential_app_user;
GRANT CREATE ON SCHEMA public TO credential_app_user;

-- Grant table privileges (for tables created by Alembic migrations later)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO credential_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO credential_app_user;

-- Verify setup
\echo '=== Database Setup Complete ==='
\echo 'Database: credential_db'
\echo 'User: credential_app_user'
\echo 'Extension: pgcrypto enabled'
\echo '=== Run verification: psql -U credential_app_user -d credential_db ==='
