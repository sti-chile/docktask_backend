from . import db
from datetime import datetime


class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    is_shared = db.Column(db.Boolean, default=False, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="activo")
    owner_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("Usuario", backref=db.backref("workspaces", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "is_shared": self.is_shared,
            "estado": self.estado,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# tabla de unión many‑to‑many Usuario ↔ Proyecto
usuario_proyecto = db.Table(
    'usuario_proyecto',
    db.Column('usuario_id',  db.Integer, db.ForeignKey('usuario.id'),  primary_key=True),
    db.Column('proyecto_id', db.Integer, db.ForeignKey('proyecto.id'), primary_key=True),
    db.Column('rol', db.String(10), nullable=False, default='usuario'),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    db.Column('updated_at', db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)



class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=True)
    expiration_date = db.Column(db.DateTime, nullable=True)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=True)
    
    # solo **back_populates**, sin backref
    usuario  = db.relationship("Usuario",  back_populates="mensajes")
    proyecto = db.relationship("Proyecto", back_populates="mensajes")
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "mensaje": self.mensaje,
            "usuario_id": self.usuario_id,
            "proyecto_id": self.proyecto_id,
            "estado": self.estado,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # argon2 hash
    rol = db.Column(db.String(10), nullable=False, default='usuario')
    nombre = db.Column(db.String(50), nullable=True)
    apellido = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relacion N a N entre usuario y proyecto ↙─── back_populates enlaza

    proyecto = db.relationship(
        'Proyecto',     
        secondary='usuario_proyecto',
        back_populates='usuarios',
        lazy='dynamic')
    # 1‑a‑N con Mensaje
    mensajes = db.relationship(
        'Mensaje',
        back_populates='usuario',
        cascade='all, delete-orphan'
        )
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "rol": self.rol,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "phone": self.phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Proyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    end_date= db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='pendiente')

    # contraparte de la relación N‑a‑N
    usuarios = db.relationship(
        "Usuario",
        secondary=usuario_proyecto,
        back_populates="proyecto",
        lazy="dynamic",
    )

    # 1‑a‑N con Mensaje
    mensajes = db.relationship(
        "Mensaje",
        back_populates="proyecto",
        cascade="all, delete-orphan",
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "estado": self.estado
        }


# ============================================================================
# Módulo de Música
# ============================================================================

class MusicTrack(db.Model):
    """Pista de audio MP3 subida por un usuario."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=True)
    album = db.Column(db.String(200), nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # segundos
    s3_key = db.Column(db.String(500), nullable=False, unique=True)  # ruta en bucket S3
    file_size = db.Column(db.Integer, nullable=False)  # bytes
    mime_type = db.Column(db.String(50), default='audio/mpeg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user = db.relationship('Usuario', backref=db.backref('music_tracks', lazy='dynamic'))
    playlists = db.relationship('PlaylistTrack', back_populates='track', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "s3_key": self.s3_key,
        }


class Playlist(db.Model):
    """Playlist de música, puede ser privada o compartida."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_shared = db.Column(db.Boolean, default=False, nullable=False)  # compartida con otros usuarios
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user = db.relationship('Usuario', backref=db.backref('playlists', lazy='dynamic'))
    tracks = db.relationship('PlaylistTrack', back_populates='playlist', cascade='all, delete-orphan')
    # Colaboradores (si is_shared=True)
    collaborators = db.relationship('PlaylistCollaborator', back_populates='playlist', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "is_shared": self.is_shared,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PlaylistTrack(db.Model):
    """Asociación entre playlist y track, con orden."""
    __tablename__ = 'playlist_track'
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey('music_track.id'), primary_key=True)
    position = db.Column(db.Integer, nullable=False, default=0)  # orden dentro de la playlist
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    playlist = db.relationship('Playlist', back_populates='tracks')
    track = db.relationship('MusicTrack', back_populates='playlists')

    def to_dict(self):
        return {
            "playlist_id": self.playlist_id,
            "track_id": self.track_id,
            "position": self.position,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }


class PlaylistCollaborator(db.Model):
    """Usuarios con acceso a playlist compartida."""
    __tablename__ = 'playlist_collaborator'
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), primary_key=True)
    permission = db.Column(db.String(10), default='view')  # 'view' o 'edit'
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    playlist = db.relationship('Playlist', back_populates='collaborators')
    user = db.relationship('Usuario', backref=db.backref('shared_playlists', lazy='dynamic'))

    def to_dict(self):
        return {
            "playlist_id": self.playlist_id,
            "user_id": self.user_id,
            "permission": self.permission,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }
