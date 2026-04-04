#!/bin/bash
# Install PostgreSQL 18 client tools on Debian/Ubuntu

set -e

echo "Installing PostgreSQL 18 client tools..."

# Add PostgreSQL official repository
sudo apt-get update
sudo apt-get install -y curl ca-certificates gnupg

# Import repository signing key
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg

# Add repository
sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Install PostgreSQL 18 client
sudo apt-get update
sudo apt-get install -y postgresql-client-18

echo ""
echo "✅ PostgreSQL client installed:"
pg_dump --version
