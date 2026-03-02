-- Migration: 002_create_workspace
-- Descripción: Crea la tabla workspace para gestión de espacios de trabajo
-- Fecha: 2026-02-23
-- NOTA: Esta migración NO está gestionada por Flask-Migrate/Alembic (no hay revision
-- correspondiente en migrations/versions). Debe ejecutarse de forma explícita
-- como parte del flujo de despliegue.
-- Ejecución recomendada:
--   psql "$DATABASE_URL" -f migrations/sql/002_create_workspace.sql
-- o integrar este archivo en el script de despliegue que aplica migraciones SQL
-- manuales antes o después de ejecutar `flask db upgrade`.

CREATE TABLE IF NOT EXISTS workspace (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    is_shared   BOOLEAN NOT NULL DEFAULT FALSE,
    estado      VARCHAR(20) NOT NULL DEFAULT 'activo',
    owner_id    INTEGER NOT NULL REFERENCES usuario(id),
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'workspace'
ORDER BY ordinal_position;
