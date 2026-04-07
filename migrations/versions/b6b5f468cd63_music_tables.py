"""music tables: tracks, playlists, sharing, offline cache support

Revision ID: b6b5f468cd63
Revises: a1b2c3d4e5f6
Create Date: 2026-04-06 22:00:00

Contexto: Feature de música en DockTask.
Permite subir MP3 a S3, crear playlists, compartir con otros usuarios,
y cache offline en móvil (Tauri).
"""
from alembic import op
import sqlalchemy as sa


revision = 'b6b5f468cd63'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Tabla music_track
    op.execute("""
        CREATE TABLE IF NOT EXISTS music_track (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES usuario(id),
            title       VARCHAR(200) NOT NULL,
            artist      VARCHAR(200),
            album       VARCHAR(200),
            duration    INTEGER,  -- segundos
            s3_key      VARCHAR(500) NOT NULL UNIQUE,
            file_size   INTEGER NOT NULL,  -- bytes
            mime_type   VARCHAR(50) DEFAULT 'audio/mpeg',
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS music_track_user_id_idx ON music_track (user_id)")

    # Tabla playlist
    op.execute("""
        CREATE TABLE IF NOT EXISTS playlist (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES usuario(id),
            name        VARCHAR(200) NOT NULL,
            description TEXT,
            is_shared   BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS playlist_user_id_idx ON playlist (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS playlist_is_shared_idx ON playlist (is_shared)")

    # Tabla playlist_track (ordenada)
    op.execute("""
        CREATE TABLE IF NOT EXISTS playlist_track (
            playlist_id INTEGER NOT NULL REFERENCES playlist(id) ON DELETE CASCADE,
            track_id    INTEGER NOT NULL REFERENCES music_track(id) ON DELETE CASCADE,
            position    INTEGER NOT NULL DEFAULT 0,
            added_at    TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (playlist_id, track_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS playlist_track_playlist_id_idx ON playlist_track (playlist_id)")
    op.execute("CREATE INDEX IF NOT EXISTS playlist_track_track_id_idx ON playlist_track (track_id)")

    # Tabla playlist_collaborator (compartir con usuarios específicos)
    op.execute("""
        CREATE TABLE IF NOT EXISTS playlist_collaborator (
            playlist_id INTEGER NOT NULL REFERENCES playlist(id) ON DELETE CASCADE,
            user_id     INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            permission  VARCHAR(10) DEFAULT 'view',
            added_at    TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (playlist_id, user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS playlist_collaborator_playlist_id_idx ON playlist_collaborator (playlist_id)")
    op.execute("CREATE INDEX IF NOT EXISTS playlist_collaborator_user_id_idx ON playlist_collaborator (user_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS playlist_collaborator")
    op.execute("DROP TABLE IF EXISTS playlist_track")
    op.execute("DROP TABLE IF EXISTS playlist")
    op.execute("DROP TABLE IF EXISTS music_track")