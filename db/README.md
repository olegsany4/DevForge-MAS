# DevForge-MAS DB

## Быстрый старт (PostgreSQL)

```bash
export DB_URL="postgresql://user:pass@localhost:5432/devforge_mas"
psql "$DB_URL" -f migrations/001_init.sql
psql "$DB_URL" -f migrations/002_seed_minimal.sql
psql "$DB_URL" -f seeds/dev_seed.sql  # опционально
