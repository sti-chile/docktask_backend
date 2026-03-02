# src/admin_routes.py (solo para admin)
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Usuario
from . import db
from datetime import datetime, timezone
admin = Blueprint("admin", __name__, url_prefix="/admin")

# Helper para verificar si el usuario es admin
def is_admin(user_id):
    user = db.session.get(Usuario, user_id)
    return user and user.rol == "admin"

# Obtener todos los usuarios
@admin.route("/api/usuarios", methods=["GET"])
@jwt_required()
def obtener_usuarios():
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Acceso denegado"}), 403

    usuarios = db.session.query(Usuario).all()
    data = [
        {"id": u.id, "username": u.username, "rol": u.rol}
        for u in usuarios
    ]
    return jsonify(data)

# Actualizar usuario
@admin.route("/api/usuarios/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar_usuario(id):
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Acceso denegado"}), 403

    user = db.session.get(Usuario, id)
    if not user:            
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json()
    user.username = data.get("username", user.username)
    user.password = data.get("password", user.password)
    user.rol = data.get("rol", user.rol)

    db.session.commit()
    return jsonify({"mensaje": "Usuario actualizado"})

# Eliminar usuario
@admin.route("/api/usuarios/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar_usuario(id):
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Acceso denegado"}), 403

    user = db.session.get(Usuario, id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"mensaje": "Usuario eliminado"})

# Añadir usuario
@admin.route("/api/usuarios", methods=["POST"])
@jwt_required()
def añadir_usuario():
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Acceso denegado"}), 403
    data = request.get_json()
    user = Usuario(
        username=data.get("username"),
        password=data.get("password"),
        rol=data.get("rol"),
        nombre=data.get("nombre"),
        apellido=data.get("apellido"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"mensaje": "Usuario añadido"})
