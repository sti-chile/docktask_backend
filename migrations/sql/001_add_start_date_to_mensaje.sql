-- Migration: 001_add_start_date_to_mensaje
-- Descripción: Agrega campo start_date a la tabla mensaje para soporte de Gantt
-- Fecha: 2026-02-23

ALTER TABLE mensaje ADD COLUMN IF NOT EXISTS start_date TIMESTAMP NULL;

-- Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'mensaje'
ORDER BY ordinal_position;
