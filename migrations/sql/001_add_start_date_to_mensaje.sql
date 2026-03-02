-- Migration: 001_add_start_date_to_mensaje
-- Descripción: Agrega campo start_date a la tabla mensaje para soporte de Gantt
-- Fecha: 2026-02-23
-- NOTA: Esta migración NO está gestionada por Flask-Migrate/Alembic (no hay revision
-- correspondiente en migrations/versions). Debe ejecutarse de forma explícita
-- como parte del flujo de despliegue.
-- Ejecución recomendada:
--   psql "$DATABASE_URL" -f migrations/sql/001_add_start_date_to_mensaje.sql
-- o integrar este archivo en el script de despliegue que aplica migraciones SQL
-- manuales antes o después de ejecutar `flask db upgrade`.

ALTER TABLE mensaje ADD COLUMN IF NOT EXISTS start_date TIMESTAMP NULL;

-- Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'mensaje'
ORDER BY ordinal_position;
