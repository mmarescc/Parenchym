-- Creates database roles and database for this project
-- XXX Must be superuser to run!

-- Do not use same name for user and a schema.
-- That schema then will be in search path, which leads to idiosyncrasies.
CREATE ROLE pym_user LOGIN ENCRYPTED PASSWORD 'pym';

CREATE DATABASE parenchym OWNER pym_user ENCODING 'utf-8';

\c parenchym postgres
CREATE EXTENSION hstore;
CREATE EXTENSION plpython3u;

\c parenchym pym_user

CREATE SCHEMA pym;
