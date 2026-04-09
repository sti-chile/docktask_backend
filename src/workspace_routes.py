from flask import Blueprint, request, jsonify
from datetime import datetime
from .models import db, Workspace
from flask_jwt_extended import jwt_required, get_jwt_identity

workspace = Blueprint("workspace", __name__)


# 🔹 Crear un nuevo workspace
@workspace.route("/workspaces/", methods=["POST"])
@jwt_required()
def create_workspace():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"error": "Se esperaba un body JSON válido"}), 400

    nombre = data.get("nombre")
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    ws = Workspace(
        nombre=nombre,
        descripcion=data.get("descripcion", ""),
        is_shared=data.get("is_shared", False),
        owner_id=user_id,
    )
    db.session.add(ws)
    db.session.commit()
    return jsonify(ws.to_dict()), 201


# 🔹 Listar workspaces propios + compartidos
@workspace.route("/workspaces/", methods=["GET"])
@jwt_required()
def get_workspaces():
    user_id = int(get_jwt_identity())
    propios = Workspace.query.filter_by(owner_id=user_id).all()
    compartidos = Workspace.query.filter(
        Workspace.is_shared == True, Workspace.owner_id != user_id
    ).all()
    return jsonify([w.to_dict() for w in propios + compartidos]), 200


# 🔹 Obtener un workspace específico
@workspace.route("/workspaces/<int:id>", methods=["GET"])
@jwt_required()
def get_workspace(id):
    user_id = int(get_jwt_identity())
    ws = Workspace.query.get_or_404(id)

    # Solo el dueño puede ver workspaces privados
    if ws.owner_id != user_id and not ws.is_shared:
        return jsonify({"error": "Sin permisos para ver este workspace"}), 403

    return jsonify(ws.to_dict()), 200


# 🔹 Actualizar un workspace (solo el dueño)
@workspace.route("/workspaces/<int:id>", methods=["PUT"])
@jwt_required()
def update_workspace(id):
    user_id = int(get_jwt_identity())
    ws = Workspace.query.get_or_404(id)

    if ws.owner_id != user_id:
        return jsonify({"error": "Sin permisos para editar este workspace"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Se esperaba un body JSON válido"}), 400

    ws.nombre = data.get("nombre", ws.nombre)
    ws.descripcion = data.get("descripcion", ws.descripcion)
    ws.is_shared = data.get("is_shared", ws.is_shared)
    ws.estado = data.get("estado", ws.estado)
    ws.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(ws.to_dict()), 200


# 🔹 Eliminar un workspace (solo el dueño)
@workspace.route("/workspaces/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_workspace(id):
    user_id = int(get_jwt_identity())
    ws = Workspace.query.get_or_404(id)

    if ws.owner_id != user_id:
        return jsonify({"error": "Sin permisos para eliminar este workspace"}), 403

    db.session.delete(ws)
    db.session.commit()
    return jsonify({"message": "Workspace eliminado correctamente"}), 200
