from flask import Blueprint, request, jsonify
from datetime import datetime
from .models import db, Workspace, Proyecto
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Usuario

workspace = Blueprint("workspace", __name__)

# 🔹 Crear un nuevo workspace
@workspace.route("/", methods=["POST"])
@jwt_required()
def create_workspace():
    user_id = get_jwt_identity()
    data = request.get_json()

    nombre = data.get("nombre")
    descripcion = data.get("descripcion", "")
    is_shared = data.get("is_shared", False)

    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    new_workspace = Workspace(
        nombre=nombre,
        descripcion=descripcion,
        is_shared=is_shared,
        owner_id=user_id,
    )

    db.session.add(new_workspace)
    db.session.commit()
    return jsonify(new_workspace.to_dict()), 201


# 🔹 Listar todos los workspaces del usuario actual
@workspace.route("/", methods=["GET"])
@jwt_required()
def get_workspaces():
    user_id = get_jwt_identity()
    workspaces = Workspace.query.filter_by(owner_id=user_id).all()
    return jsonify([w.to_dict() for w in workspaces]), 200


# 🔹 Obtener un workspace específico
@workspace.route("/<int:id>", methods=["GET"])
@jwt_required()
def get_workspace(id):
    workspace = Workspace.query.get_or_404(id)
    return jsonify(workspace.to_dict()), 200


# 🔹 Actualizar un workspace
@workspace.route("/<int:id>", methods=["PUT"])
@jwt_required()
def update_workspace(id):
    data = request.get_json()
    workspace = Workspace.query.get_or_404(id)

    workspace.nombre = data.get("nombre", workspace.nombre)
    workspace.descripcion = data.get("descripcion", workspace.descripcion)
    workspace.is_shared = data.get("is_shared", workspace.is_shared)
    workspace.estado = data.get("estado", workspace.estado)
    workspace.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(workspace.to_dict()), 200


# 🔹 Eliminar un workspace
@workspace.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_workspace(id):
    workspace = Workspace.query.get_or_404(id)
    db.session.delete(workspace)
    db.session.commit()
    return jsonify({"message": "Workspace eliminado correctamente"}), 200
