# tests/test_music_routes.py
"""
Tests para el módulo de música: tracks, playlists y colaboradores.
Usa mocking para S3 para evitar dependencias externas.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from src import db, jwt
from src.models import (
    Usuario,
    MusicTrack,
    Playlist,
    PlaylistTrack,
    PlaylistCollaborator,
)
from src.music_routes import music
from src.main_routes import main
from argon2 import PasswordHasher


@pytest.fixture
def app():
    """Crea app Flask con BD en memoria para testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "test-secret-key"

    db.init_app(app)
    jwt.init_app(app)
    app.register_blueprint(music)
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        # Crear usuario de prueba con password hasheado
        ph = PasswordHasher()
        user = Usuario(username="testuser", password=ph.hash("testpass"), rol="usuario")
        db.session.add(user)

        # Crear segundo usuario para tests de colaboración
        user2 = Usuario(
            username="collaborator", password=ph.hash("collabpass"), rol="usuario"
        )
        db.session.add(user2)
        db.session.commit()

        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_token(client, username="testuser", password="testpass"):
    """Obtiene JWT token para autenticación."""
    res = client.post("/api/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed: {res.data}"
    return res.get_json()["access_token"]


def auth_headers(client, username="testuser", password="testpass"):
    """Retorna headers con Authorization Bearer token."""
    token = get_token(client, username, password)
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Tests de configuración
# ============================================================================


def test_music_config(client):
    """Test: GET /api/v1/music/config retorna configuración."""
    headers = auth_headers(client)
    res = client.get("/api/v1/music/config", headers=headers)

    assert res.status_code == 200
    data = res.get_json()
    assert "max_file_size" in data
    assert "allowed_mime_types" in data
    assert data["max_file_size"] == 50 * 1024 * 1024  # 50 MB


def test_music_config_requires_auth(client):
    """Test: /api/v1/music/config requiere autenticación."""
    res = client.get("/api/v1/music/config")
    assert res.status_code == 401


# ============================================================================
# Tests de tracks
# ============================================================================


def test_list_tracks_empty(client):
    """Test: GET /api/v1/music/tracks retorna lista vacía inicialmente."""
    headers = auth_headers(client)
    res = client.get("/api/v1/music/tracks", headers=headers)

    assert res.status_code == 200
    assert res.get_json() == []


@patch("src.music_routes.get_s3_client")
def test_upload_track(mock_s3, client, app):
    """Test: POST /api/v1/music/tracks/upload crea track y retorna upload URL."""
    # Mock S3 client
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/upload-url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)
    data = {
        "title": "Mi Cancion",
        "artist": "Artista Test",
        "album": "Album Test",
        "file_size": 5 * 1024 * 1024,  # 5 MB
        "mime_type": "audio/mpeg",
    }

    res = client.post("/api/v1/music/tracks/upload", headers=headers, json=data)

    assert res.status_code == 200
    json_data = res.get_json()
    assert "upload_url" in json_data
    assert "track_id" in json_data
    assert "s3_key" in json_data

    # Verificar que el track se creó en BD
    with app.app_context():
        track = MusicTrack.query.get(json_data["track_id"])
        assert track is not None
        assert track.title == "Mi Cancion"
        assert track.artist == "Artista Test"


def test_upload_track_invalid_size(client):
    """Test: upload rechaza archivos mayores a 50MB."""
    headers = auth_headers(client)
    data = {
        "title": "Archivo Grande",
        "file_size": 100 * 1024 * 1024,  # 100 MB - excede límite
        "mime_type": "audio/mpeg",
    }

    res = client.post("/api/v1/music/tracks/upload", headers=headers, json=data)

    assert res.status_code == 400
    assert b"excede" in res.data or b"inv" in res.data.lower()


def test_upload_track_no_json(client):
    """Test: upload requiere JSON body."""
    headers = auth_headers(client)
    res = client.post("/api/v1/music/tracks/upload", headers=headers)

    # 415 = Unsupported Media Type (no Content-Type: application/json)
    # 400 = Bad Request (JSON vacío o inválido)
    assert res.status_code in (400, 415)


@patch("src.music_routes.get_s3_client")
def test_list_tracks_with_data(mock_s3, client, app):
    """Test: GET /api/v1/music/tracks retorna tracks del usuario."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/upload-url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear un track
    data = {"title": "Track 1", "file_size": 1024, "mime_type": "audio/mpeg"}
    client.post("/api/v1/music/tracks/upload", headers=headers, json=data)

    # Listar
    res = client.get("/api/v1/music/tracks", headers=headers)

    assert res.status_code == 200
    tracks = res.get_json()
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Track 1"


@patch("src.music_routes.get_s3_client")
def test_get_track(mock_s3, client, app):
    """Test: GET /api/v1/music/tracks/<id> retorna track específico."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear track
    data = {"title": "Mi Track", "file_size": 1024, "mime_type": "audio/mpeg"}
    res = client.post("/api/v1/music/tracks/upload", headers=headers, json=data)
    track_id = res.get_json()["track_id"]

    # Obtener
    res = client.get(f"/api/v1/music/tracks/{track_id}", headers=headers)

    assert res.status_code == 200
    assert res.get_json()["title"] == "Mi Track"


@patch("src.music_routes.get_s3_client")
def test_get_track_unauthorized(mock_s3, client, app):
    """Test: No se puede acceder a track de otro usuario."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    # Crear track con usuario 1
    headers1 = auth_headers(client, "testuser", "testpass")
    data = {"title": "Track Privado", "file_size": 1024, "mime_type": "audio/mpeg"}
    res = client.post("/api/v1/music/tracks/upload", headers=headers1, json=data)
    track_id = res.get_json()["track_id"]

    # Intentar acceder con usuario 2
    headers2 = auth_headers(client, "collaborator", "collabpass")
    res = client.get(f"/api/v1/music/tracks/{track_id}", headers=headers2)

    assert res.status_code == 403


@patch("src.music_routes.get_s3_client")
def test_stream_track(mock_s3, client, app):
    """Test: GET /api/v1/music/tracks/<id>/stream retorna URL de streaming."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = (
        "https://s3.fake/stream-url?signed=true"
    )
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear track
    data = {"title": "Stream Test", "file_size": 1024, "mime_type": "audio/mpeg"}
    res = client.post("/api/v1/music/tracks/upload", headers=headers, json=data)
    track_id = res.get_json()["track_id"]

    # Stream
    res = client.get(f"/api/v1/music/tracks/{track_id}/stream", headers=headers)

    assert res.status_code == 200
    assert "stream_url" in res.get_json()


@patch("src.music_routes.get_s3_client")
def test_confirm_upload(mock_s3, client, app):
    """Test: POST /api/v1/music/tracks/<id>/confirm actualiza duración."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear track
    data = {"title": "Confirm Test", "file_size": 1024, "mime_type": "audio/mpeg"}
    res = client.post("/api/v1/music/tracks/upload", headers=headers, json=data)
    track_id = res.get_json()["track_id"]

    # Confirmar con duración
    res = client.post(
        f"/api/v1/music/tracks/{track_id}/confirm",
        headers=headers,
        json={"duration": 180},  # 3 minutos
    )

    assert res.status_code == 200
    assert res.get_json()["duration"] == 180


@patch("src.music_routes.get_s3_client")
def test_delete_track(mock_s3, client, app):
    """Test: DELETE /api/v1/music/tracks/<id> elimina track."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_client.delete_object.return_value = {}
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear track
    data = {"title": "Delete Test", "file_size": 1024, "mime_type": "audio/mpeg"}
    res = client.post("/api/v1/music/tracks/upload", headers=headers, json=data)
    track_id = res.get_json()["track_id"]

    # Eliminar
    res = client.delete(f"/api/v1/music/tracks/{track_id}", headers=headers)

    assert res.status_code == 200
    assert b"eliminado" in res.data.lower()

    # Verificar que no existe
    res = client.get(f"/api/v1/music/tracks/{track_id}", headers=headers)
    assert res.status_code == 404


# ============================================================================
# Tests de playlists
# ============================================================================


def test_list_playlists_empty(client):
    """Test: GET /api/v1/music/playlists retorna lista vacía."""
    headers = auth_headers(client)
    res = client.get("/api/v1/music/playlists", headers=headers)

    assert res.status_code == 200
    assert res.get_json() == []


def test_create_playlist(client):
    """Test: POST /api/v1/music/playlists crea playlist."""
    headers = auth_headers(client)
    data = {
        "name": "Mi Playlist",
        "description": "Una playlist de prueba",
        "is_shared": False,
    }

    res = client.post("/api/v1/music/playlists", headers=headers, json=data)

    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["name"] == "Mi Playlist"
    assert json_data["is_shared"] == False


def test_create_playlist_no_name(client):
    """Test: crear playlist sin nombre falla."""
    headers = auth_headers(client)
    res = client.post("/api/v1/music/playlists", headers=headers, json={})

    assert res.status_code == 400


def test_get_playlist(client):
    """Test: GET /api/v1/music/playlists/<id> retorna playlist con tracks."""
    headers = auth_headers(client)

    # Crear playlist
    res = client.post(
        "/api/v1/music/playlists", headers=headers, json={"name": "Test Playlist"}
    )
    playlist_id = res.get_json()["id"]

    # Obtener
    res = client.get(f"/api/v1/music/playlists/{playlist_id}", headers=headers)

    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] == "Test Playlist"
    assert "tracks" in data


def test_get_playlist_unauthorized(client):
    """Test: No se puede acceder a playlist de otro usuario."""
    # Crear playlist con usuario 1
    headers1 = auth_headers(client, "testuser", "testpass")
    res = client.post(
        "/api/v1/music/playlists", headers=headers1, json={"name": "Playlist Privada"}
    )
    playlist_id = res.get_json()["id"]

    # Intentar acceder con usuario 2
    headers2 = auth_headers(client, "collaborator", "collabpass")
    res = client.get(f"/api/v1/music/playlists/{playlist_id}", headers=headers2)

    assert res.status_code == 403


@patch("src.music_routes.get_s3_client")
def test_add_track_to_playlist(mock_s3, client, app):
    """Test: POST /api/v1/music/playlists/<id>/tracks agrega track."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear track
    res = client.post(
        "/api/v1/music/tracks/upload",
        headers=headers,
        json={
            "title": "Track para Playlist",
            "file_size": 1024,
            "mime_type": "audio/mpeg",
        },
    )
    track_id = res.get_json()["track_id"]

    # Crear playlist
    res = client.post(
        "/api/v1/music/playlists", headers=headers, json={"name": "Playlist con Tracks"}
    )
    playlist_id = res.get_json()["id"]

    # Agregar track a playlist
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"track_id": track_id, "position": 0},
    )

    assert res.status_code == 201

    # Verificar que está en la playlist
    res = client.get(f"/api/v1/music/playlists/{playlist_id}", headers=headers)
    tracks = res.get_json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Track para Playlist"


@patch("src.music_routes.get_s3_client")
def test_add_duplicate_track_to_playlist(mock_s3, client, app):
    """Test: No se puede agregar el mismo track dos veces."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Crear track y playlist
    res = client.post(
        "/api/v1/music/tracks/upload",
        headers=headers,
        json={"title": "Track", "file_size": 1024, "mime_type": "audio/mpeg"},
    )
    track_id = res.get_json()["track_id"]

    res = client.post(
        "/api/v1/music/playlists", headers=headers, json={"name": "Playlist"}
    )
    playlist_id = res.get_json()["id"]

    # Agregar track
    client.post(
        f"/api/v1/music/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"track_id": track_id},
    )

    # Intentar agregar de nuevo
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"track_id": track_id},
    )

    assert res.status_code == 409  # Conflict


@patch("src.music_routes.get_s3_client")
def test_remove_track_from_playlist(mock_s3, client, app):
    """Test: DELETE /api/v1/music/playlists/<id>/tracks/<track_id> remueve track."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers = auth_headers(client)

    # Setup: crear track, playlist y agregar
    res = client.post(
        "/api/v1/music/tracks/upload",
        headers=headers,
        json={"title": "Track", "file_size": 1024, "mime_type": "audio/mpeg"},
    )
    track_id = res.get_json()["track_id"]

    res = client.post(
        "/api/v1/music/playlists", headers=headers, json={"name": "Playlist"}
    )
    playlist_id = res.get_json()["id"]

    client.post(
        f"/api/v1/music/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"track_id": track_id},
    )

    # Remover track
    res = client.delete(
        f"/api/v1/music/playlists/{playlist_id}/tracks/{track_id}", headers=headers
    )

    assert res.status_code == 200

    # Verificar que ya no está
    res = client.get(f"/api/v1/music/playlists/{playlist_id}", headers=headers)
    assert len(res.get_json()["tracks"]) == 0


# ============================================================================
# Tests de colaboradores
# ============================================================================


def test_add_collaborator(client, app):
    """Test: POST /api/v1/music/playlists/<id>/collaborators agrega colaborador."""
    headers = auth_headers(client, "testuser", "testpass")

    # Crear playlist compartida
    res = client.post(
        "/api/v1/music/playlists",
        headers=headers,
        json={"name": "Playlist Compartida", "is_shared": True},
    )
    playlist_id = res.get_json()["id"]

    # Obtener ID del colaborador
    with app.app_context():
        collab_user = Usuario.query.filter_by(username="collaborator").first()
        collab_id = collab_user.id

    # Agregar colaborador
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/collaborators",
        headers=headers,
        json={"user_id": collab_id, "permission": "view"},
    )

    assert res.status_code == 201
    assert res.get_json()["permission"] == "view"


def test_add_collaborator_to_private_playlist(client):
    """Test: No se pueden agregar colaboradores a playlist privada."""
    headers = auth_headers(client)

    # Crear playlist privada (is_shared=False por defecto)
    res = client.post(
        "/api/v1/music/playlists", headers=headers, json={"name": "Playlist Privada"}
    )
    playlist_id = res.get_json()["id"]

    # Intentar agregar colaborador
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/collaborators",
        headers=headers,
        json={"user_id": 999, "permission": "view"},
    )

    assert res.status_code == 400


def test_cannot_add_self_as_collaborator(client, app):
    """Test: No se puede agregar a uno mismo como colaborador."""
    headers = auth_headers(client, "testuser", "testpass")

    # Crear playlist compartida
    res = client.post(
        "/api/v1/music/playlists",
        headers=headers,
        json={"name": "Playlist", "is_shared": True},
    )
    playlist_id = res.get_json()["id"]

    # Obtener ID del usuario actual
    with app.app_context():
        user = Usuario.query.filter_by(username="testuser").first()
        user_id = user.id

    # Intentar agregarse a sí mismo
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/collaborators",
        headers=headers,
        json={"user_id": user_id, "permission": "edit"},
    )

    assert res.status_code == 400


def test_collaborator_can_view_shared_playlist(client, app):
    """Test: Colaborador puede ver playlist compartida."""
    headers1 = auth_headers(client, "testuser", "testpass")

    # Crear playlist compartida
    res = client.post(
        "/api/v1/music/playlists",
        headers=headers1,
        json={"name": "Compartida", "is_shared": True},
    )
    playlist_id = res.get_json()["id"]

    # Agregar colaborador
    with app.app_context():
        collab_user = Usuario.query.filter_by(username="collaborator").first()
        collab_id = collab_user.id

    client.post(
        f"/api/v1/music/playlists/{playlist_id}/collaborators",
        headers=headers1,
        json={"user_id": collab_id, "permission": "view"},
    )

    # Colaborador accede a la playlist
    headers2 = auth_headers(client, "collaborator", "collabpass")
    res = client.get(f"/api/v1/music/playlists/{playlist_id}", headers=headers2)

    assert res.status_code == 200
    assert res.get_json()["name"] == "Compartida"


@patch("src.music_routes.get_s3_client")
def test_collaborator_with_edit_can_add_tracks(mock_s3, client, app):
    """Test: Colaborador con permiso 'edit' puede agregar tracks."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers1 = auth_headers(client, "testuser", "testpass")

    # Owner crea playlist y track
    res = client.post(
        "/api/v1/music/playlists",
        headers=headers1,
        json={"name": "Editable", "is_shared": True},
    )
    playlist_id = res.get_json()["id"]

    res = client.post(
        "/api/v1/music/tracks/upload",
        headers=headers1,
        json={"title": "Track del Owner", "file_size": 1024, "mime_type": "audio/mpeg"},
    )
    track_id = res.get_json()["track_id"]

    # Agregar colaborador con permiso edit
    with app.app_context():
        collab_user = Usuario.query.filter_by(username="collaborator").first()
        collab_id = collab_user.id

    client.post(
        f"/api/v1/music/playlists/{playlist_id}/collaborators",
        headers=headers1,
        json={"user_id": collab_id, "permission": "edit"},
    )

    # Colaborador agrega track a playlist
    headers2 = auth_headers(client, "collaborator", "collabpass")
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/tracks",
        headers=headers2,
        json={"track_id": track_id},
    )

    assert res.status_code == 201


@patch("src.music_routes.get_s3_client")
def test_collaborator_with_view_cannot_add_tracks(mock_s3, client, app):
    """Test: Colaborador con solo 'view' NO puede agregar tracks."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.fake/url"
    mock_s3.return_value = mock_client

    headers1 = auth_headers(client, "testuser", "testpass")

    # Setup
    res = client.post(
        "/api/v1/music/playlists",
        headers=headers1,
        json={"name": "View Only", "is_shared": True},
    )
    playlist_id = res.get_json()["id"]

    res = client.post(
        "/api/v1/music/tracks/upload",
        headers=headers1,
        json={"title": "Track", "file_size": 1024, "mime_type": "audio/mpeg"},
    )
    track_id = res.get_json()["track_id"]

    # Agregar colaborador con permiso VIEW (no edit)
    with app.app_context():
        collab_user = Usuario.query.filter_by(username="collaborator").first()
        collab_id = collab_user.id

    client.post(
        f"/api/v1/music/playlists/{playlist_id}/collaborators",
        headers=headers1,
        json={"user_id": collab_id, "permission": "view"},
    )

    # Colaborador intenta agregar track
    headers2 = auth_headers(client, "collaborator", "collabpass")
    res = client.post(
        f"/api/v1/music/playlists/{playlist_id}/tracks",
        headers=headers2,
        json={"track_id": track_id},
    )

    assert res.status_code == 403
