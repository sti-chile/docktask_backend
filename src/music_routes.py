# src/music_routes.py
# Endpoints para funcionalidad de música en DockTask.
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import (
    db,
    Usuario,
    MusicTrack,
    Playlist,
    PlaylistTrack,
    PlaylistCollaborator,
)
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
import uuid
import json

music = Blueprint("music", __name__, url_prefix="/api/v1/music")


def get_current_user_id() -> int:
    """Helper: obtiene el user_id del JWT como entero."""
    return int(get_jwt_identity())


# Configuración S3
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "docktask-media")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


# Cliente S3 (se crea bajo demanda para no sobrecargar si no se usa)
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


# ============================================================================
# Endpoints de tracks (pistas de audio)
# ============================================================================


@music.route("/tracks", methods=["GET"])
@jwt_required()
def list_tracks():
    """Lista todas las pistas del usuario autenticado."""
    current_user_id = get_current_user_id()
    tracks = (
        MusicTrack.query.filter_by(user_id=current_user_id)
        .order_by(MusicTrack.created_at.desc())
        .all()
    )
    return jsonify([track.to_dict() for track in tracks])


@music.route("/tracks/<int:track_id>", methods=["GET"])
@jwt_required()
def get_track(track_id):
    """Obtiene metadata de una pista específica (si pertenece al usuario o es compartida)."""
    current_user_id = get_current_user_id()
    track = MusicTrack.query.get_or_404(track_id)

    # Verificar permisos: dueño o playlist compartida con el usuario
    if track.user_id == current_user_id:
        return jsonify(track.to_dict())

    # Buscar si el track está en alguna playlist compartida con el usuario
    shared = (
        db.session.query(PlaylistCollaborator)
        .join(Playlist)
        .join(PlaylistTrack)
        .filter(
            PlaylistCollaborator.user_id == current_user_id,
            PlaylistTrack.track_id == track_id,
        )
        .first()
    )
    if shared:
        return jsonify(track.to_dict())

    return jsonify({"error": "No autorizado"}), 403


@music.route("/tracks/<int:track_id>/stream", methods=["GET"])
@jwt_required()
def stream_track(track_id):
    """Genera una pre‑signed URL temporal para streaming del archivo MP3 desde S3."""
    current_user_id = get_current_user_id()
    track = MusicTrack.query.get_or_404(track_id)

    # Verificar permisos (mismo que get_track)
    if track.user_id != current_user_id:
        shared = (
            db.session.query(PlaylistCollaborator)
            .join(Playlist)
            .join(PlaylistTrack)
            .filter(
                PlaylistCollaborator.user_id == current_user_id,
                PlaylistTrack.track_id == track_id,
            )
            .first()
        )
        if not shared:
            return jsonify({"error": "No autorizado"}), 403

    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": AWS_S3_BUCKET,
                "Key": track.s3_key,
                "ResponseContentType": track.mime_type,
            },
            ExpiresIn=3600,  # 1 hora
        )
        return jsonify({"stream_url": url})
    except ClientError as e:
        return jsonify({"error": str(e)}), 500


@music.route("/tracks/upload", methods=["POST"])
@jwt_required()
def upload_track():
    """Crea una pre‑signed URL para subida directa a S3 y registra el track en BD."""
    current_user_id = get_current_user_id()
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requiere JSON"}), 400

    title = data.get("title", "Sin título")
    artist = data.get("artist", "")
    album = data.get("album", "")
    file_size = data.get("file_size")  # bytes
    mime_type = data.get("mime_type", "audio/mpeg")

    if not file_size or file_size > 50 * 1024 * 1024:  # 50 MB
        return jsonify({"error": "Tamaño de archivo inválido o excede 50MB"}), 400

    # Generar S3 key única: {user_id}/tracks/{uuid}.mp3
    file_ext = "mp3" if mime_type == "audio/mpeg" else "bin"
    s3_key = f"{current_user_id}/tracks/{uuid.uuid4().hex}.{file_ext}"

    try:
        s3_client = get_s3_client()
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": AWS_S3_BUCKET,
                "Key": s3_key,
                "ContentType": mime_type,
                "ContentLength": file_size,
                "Metadata": {
                    "user_id": str(current_user_id),
                    "title": title[:200],
                    "artist": artist[:200] if artist else "",
                    "album": album[:200] if album else "",
                },
            },
            ExpiresIn=3600,  # 1 hora para subir
        )

        # Crear registro en BD (pendiente hasta que el frontend confirme subida exitosa)
        # Podemos crear el track con un estado "uploading" o simplemente devolver la URL
        # y que el frontend luego llame a un endpoint de confirmación.
        # Por simplicidad, creamos el track inmediatamente (duración se actualiza luego).
        track = MusicTrack(
            user_id=current_user_id,
            title=title,
            artist=artist,
            album=album,
            duration=None,  # se actualizará después de analizar el archivo
            s3_key=s3_key,
            file_size=file_size,
            mime_type=mime_type,
        )
        db.session.add(track)
        db.session.commit()

        return jsonify(
            {
                "upload_url": upload_url,
                "track_id": track.id,
                "s3_key": s3_key,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@music.route("/tracks/<int:track_id>/confirm", methods=["POST"])
@jwt_required()
def confirm_upload(track_id):
    """Confirma que la subida a S3 fue exitosa y actualiza metadatos (duración, etc.)."""
    current_user_id = get_current_user_id()
    track = MusicTrack.query.filter_by(
        id=track_id, user_id=current_user_id
    ).first_or_404()

    data = request.get_json() or {}
    duration = data.get("duration")  # segundos

    if duration:
        track.duration = int(duration)

    # Aquí podríamos verificar que el objeto existe en S3 (head_object)
    # Pero por simplicidad asumimos éxito.

    db.session.commit()
    return jsonify(track.to_dict())


@music.route("/tracks/<int:track_id>", methods=["DELETE"])
@jwt_required()
def delete_track(track_id):
    """Elimina track (y su archivo en S3) si es dueño."""
    current_user_id = get_current_user_id()
    track = MusicTrack.query.filter_by(
        id=track_id, user_id=current_user_id
    ).first_or_404()

    try:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=AWS_S3_BUCKET, Key=track.s3_key)
    except ClientError:
        # Si el archivo no existe, continuamos
        pass

    db.session.delete(track)
    db.session.commit()
    return jsonify({"message": "Track eliminado"})


# ============================================================================
# Endpoints de playlists
# ============================================================================


@music.route("/playlists", methods=["GET"])
@jwt_required()
def list_playlists():
    """Lista playlists propias y compartidas con el usuario."""
    current_user_id = get_current_user_id()
    # Propias
    own = Playlist.query.filter_by(user_id=current_user_id).all()
    # Compartidas con el usuario
    shared = (
        Playlist.query.join(PlaylistCollaborator)
        .filter(PlaylistCollaborator.user_id == current_user_id)
        .all()
    )

    result = [p.to_dict() for p in own]
    result.extend([p.to_dict() for p in shared])
    return jsonify(result)


@music.route("/playlists", methods=["POST"])
@jwt_required()
def create_playlist():
    """Crea una nueva playlist."""
    current_user_id = get_current_user_id()
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Se requiere nombre"}), 400

    playlist = Playlist(
        user_id=current_user_id,
        name=data["name"],
        description=data.get("description"),
        is_shared=data.get("is_shared", False),
    )
    db.session.add(playlist)
    db.session.commit()
    return jsonify(playlist.to_dict()), 201


@music.route("/playlists/<int:playlist_id>", methods=["GET"])
@jwt_required()
def get_playlist(playlist_id):
    """Obtiene playlist con sus tracks (si tiene permiso)."""
    current_user_id = get_current_user_id()
    playlist = Playlist.query.get_or_404(playlist_id)

    # Verificar permisos
    if playlist.user_id != current_user_id:
        collab = PlaylistCollaborator.query.filter_by(
            playlist_id=playlist_id, user_id=current_user_id
        ).first()
        if not collab:
            return jsonify({"error": "No autorizado"}), 403

    # Obtener tracks ordenados
    tracks = (
        db.session.query(MusicTrack)
        .join(PlaylistTrack)
        .filter(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position)
        .all()
    )

    result = playlist.to_dict()
    result["tracks"] = [track.to_dict() for track in tracks]
    return jsonify(result)


@music.route("/playlists/<int:playlist_id>/tracks", methods=["POST"])
@jwt_required()
def add_track_to_playlist(playlist_id):
    """Añade un track a una playlist (si tiene permiso de edición)."""
    current_user_id = get_current_user_id()
    playlist = Playlist.query.get_or_404(playlist_id)

    # Verificar permisos de edición: dueño o colaborador con permiso 'edit'
    can_edit = False
    if playlist.user_id == current_user_id:
        can_edit = True
    else:
        collab = PlaylistCollaborator.query.filter_by(
            playlist_id=playlist_id, user_id=current_user_id, permission="edit"
        ).first()
        if collab:
            can_edit = True

    if not can_edit:
        return jsonify({"error": "Sin permiso de edición"}), 403

    data = request.get_json()
    track_id = data.get("track_id")
    position = data.get("position", 0)

    track = MusicTrack.query.get_or_404(track_id)
    # Verificar que el track sea del dueño o compartido (simplificado)
    if track.user_id != playlist.user_id and track.user_id != current_user_id:
        # Podría ser track de otro usuario, pero si está en una playlist compartida, ¿permitir?
        # Por ahora solo dueños.
        return jsonify({"error": "Track no pertenece al dueño de la playlist"}), 403

    # Verificar si ya existe en la playlist
    existing = PlaylistTrack.query.filter_by(
        playlist_id=playlist_id, track_id=track_id
    ).first()
    if existing:
        return jsonify({"error": "Track ya en playlist"}), 409

    playlist_track = PlaylistTrack(
        playlist_id=playlist_id,
        track_id=track_id,
        position=position,
    )
    db.session.add(playlist_track)
    db.session.commit()

    return jsonify(playlist_track.to_dict()), 201


@music.route("/playlists/<int:playlist_id>/tracks/<int:track_id>", methods=["DELETE"])
@jwt_required()
def remove_track_from_playlist(playlist_id, track_id):
    """Elimina track de playlist (si tiene permiso de edición)."""
    current_user_id = get_current_user_id()
    playlist = Playlist.query.get_or_404(playlist_id)

    # Verificar permisos de edición (igual que add_track_to_playlist)
    can_edit = False
    if playlist.user_id == current_user_id:
        can_edit = True
    else:
        collab = PlaylistCollaborator.query.filter_by(
            playlist_id=playlist_id, user_id=current_user_id, permission="edit"
        ).first()
        if collab:
            can_edit = True

    if not can_edit:
        return jsonify({"error": "Sin permiso de edición"}), 403

    playlist_track = PlaylistTrack.query.filter_by(
        playlist_id=playlist_id, track_id=track_id
    ).first_or_404()

    db.session.delete(playlist_track)
    db.session.commit()
    return jsonify({"message": "Track removido de playlist"})


@music.route("/playlists/<int:playlist_id>/collaborators", methods=["POST"])
@jwt_required()
def add_collaborator(playlist_id):
    """Añade un colaborador a una playlist compartida (solo dueño)."""
    current_user_id = get_current_user_id()
    playlist = Playlist.query.filter_by(
        id=playlist_id, user_id=current_user_id
    ).first_or_404()

    if not playlist.is_shared:
        return jsonify({"error": "Playlist no está marcada como compartida"}), 400

    data = request.get_json()
    collaborator_user_id = data.get("user_id")
    permission = data.get("permission", "view")

    if collaborator_user_id == current_user_id:
        return jsonify({"error": "No puedes agregarte a ti mismo"}), 400

    # Verificar que el usuario colaborador exista
    user = Usuario.query.get(collaborator_user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    existing = PlaylistCollaborator.query.filter_by(
        playlist_id=playlist_id, user_id=collaborator_user_id
    ).first()
    if existing:
        return jsonify({"error": "Usuario ya es colaborador"}), 409

    collab = PlaylistCollaborator(
        playlist_id=playlist_id,
        user_id=collaborator_user_id,
        permission=permission,
    )
    db.session.add(collab)
    db.session.commit()
    return jsonify(collab.to_dict()), 201


# ============================================================================
# Endpoints de utilidad (health, configuración)
# ============================================================================


@music.route("/config", methods=["GET"])
@jwt_required()
def music_config():
    """Devuelve configuración necesaria para el cliente (límites, bucket, etc.)."""
    return jsonify(
        {
            "max_file_size": 50 * 1024 * 1024,  # 50 MB
            "allowed_mime_types": ["audio/mpeg", "audio/mp4", "audio/wav", "audio/ogg"],
            "bucket": AWS_S3_BUCKET,
            "region": AWS_REGION,
        }
    )
