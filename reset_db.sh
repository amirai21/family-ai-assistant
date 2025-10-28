#!/bin/bash
# Reset database and apply fresh migration for POC

echo "🗑️  Dropping existing database..."
docker-compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS family_assistant;"

echo "✨ Creating fresh database..."
docker-compose exec -T db psql -U postgres -c "CREATE DATABASE family_assistant;"

echo "📦 Running migrations..."
docker-compose exec app alembic upgrade head

echo "✅ Database reset complete!"
echo ""
echo "Your database now has:"
echo "  - users"
echo "  - families"
echo "  - family_members"
echo "  - recurring_patterns (NEW!)"
echo "  - tasks (with recurring support)"
echo "  - reminders"

