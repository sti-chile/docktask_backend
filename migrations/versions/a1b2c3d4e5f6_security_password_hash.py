"""security: extend password column to 255 for argon2 hashes

Revision ID: a1b2c3d4e5f6
Revises: 4ca473b7d3ee
Create Date: 2026-03-04 21:30:00

Contexto: Las contraseñas se almacenaban en texto plano.
Se migra a argon2 hashing. Esta migration extiende la columna
para que quepa el hash (≈95 chars, usamos 255 por margen).
Los usuarios existentes se rehashean automáticamente al primer login.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '4ca473b7d3ee'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'usuario',
        'password',
        existing_type=sa.String(100),
        type_=sa.String(255),
        existing_nullable=False
    )


def downgrade():
    # ADVERTENCIA: downgrade trunca hashes a 100 chars — no usar en producción
    op.alter_column(
        'usuario',
        'password',
        existing_type=sa.String(255),
        type_=sa.String(100),
        existing_nullable=False
    )
