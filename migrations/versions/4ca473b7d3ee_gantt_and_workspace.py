"""gantt and workspace support

Revision ID: 4ca473b7d3ee
Revises: d0a42427232b
Create Date: 2026-03-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ca473b7d3ee'
down_revision = 'd0a42427232b'
branch_labels = None
depends_on = None


def upgrade():
    # Agrega start_date a mensaje (IF NOT EXISTS — idempotente)
    op.execute("""
        ALTER TABLE mensaje
        ADD COLUMN IF NOT EXISTS start_date TIMESTAMP NULL
    """)

    # Crea tabla workspace (IF NOT EXISTS — idempotente)
    op.execute("""
        CREATE TABLE IF NOT EXISTS workspace (
            id          SERIAL PRIMARY KEY,
            nombre      VARCHAR(100) NOT NULL,
            descripcion TEXT,
            is_shared   BOOLEAN NOT NULL DEFAULT FALSE,
            estado      VARCHAR(20) NOT NULL DEFAULT 'activo',
            owner_id    INTEGER NOT NULL REFERENCES usuario(id),
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS workspace")
    op.execute("ALTER TABLE mensaje DROP COLUMN IF EXISTS start_date")
