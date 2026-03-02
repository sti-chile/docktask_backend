# src/project_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Proyecto, Mensaje, Usuario, db
from datetime import datetime
project = Blueprint("project", __name__, url_prefix="/api")

# ---------- helpers ----------
def is_admin(uid):
    u = Usuario.query.get(uid)
    return u and u.rol == "admin"

def owner_to_username(uid):
    u = Usuario.query.get(uid)
    return u.username if u else ""

def proyecto_to_dict(proyecto):
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "owner_id": proyecto.owner_id,
        "username": owner_to_username(proyecto.owner_id),
        "descripcion": proyecto.descripcion,
        "created_at": proyecto.created_at,
        "updated_at": proyecto.updated_at,
        "end_date": proyecto.end_date,
        "estado": proyecto.estado
    }

# -----------------ENDPOINT GET PROYECTOS-----------------

@project.route("/proyectos", methods=["GET"])
@jwt_required()
def get_proyectos():
    proyectos = Proyecto.query.all()
    return jsonify([proyecto_to_dict(p) for p in proyectos]), 200

# -----------------ENDPOINT POST PROYECTOS-----------------

@project.route("/proyectos", methods=["POST"])
@jwt_required()
def create_proyecto():
    data = request.json
    
    if not data or not data.get("nombre") or not data.get("descripcion"):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    end_date = None
    if data.get("end_date"):
        try:
            end_date = datetime.fromisoformat(data["end_date"])
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Usa ISO 8601."}), 400
    
    nuevo = Proyecto(
        nombre=data["nombre"],
        descripcion=data["descripcion"],
        owner_id=get_jwt_identity(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        end_date=end_date
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"message": "Proyecto creado exitosamente"}), 201

# -----------------ENDPOINT PUT PROYECTOS-----------------
@project.route("/proyectos/<int:proyecto_id>", methods=["PUT"])
@jwt_required()
def update_proyecto(proyecto_id):
    data = request.json
    proyecto = Proyecto.query.get(proyecto_id)
    if not proyecto:
        return jsonify({"error": "Proyecto no encontrado"}), 404
    
    proyecto.nombre = data.get("nombre", proyecto.nombre)
    proyecto.descripcion = data.get("descripcion", proyecto.descripcion)
    proyecto.end_date = data.get("end_date", proyecto.end_date)
    proyecto.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Proyecto actualizado exitosamente"}), 200

# -----------------ENDPOINT DELETE PROYECTOS-----------------
@project.route("/proyectos/<int:proyecto_id>", methods=["DELETE"])
@jwt_required()
def delete_proyecto(proyecto_id):
    proyecto = Proyecto.query.get(proyecto_id)
    if not proyecto:
        return jsonify({"error": "Proyecto no encontrado"}), 404
    
    db.session.delete(proyecto)
    db.session.commit()
    return jsonify({"message": "Proyecto eliminado exitosamente"}), 200


# --- extra: mensajes de un proyecto ---
@project.route("/proyectos/<int:pid>/mensajes", methods=["GET"])
@jwt_required()
def mensajes_de_proyecto(pid):
    p = Proyecto.query.get_or_404(pid)
    return jsonify([
        {
            "id": m.id,
            "nombre": m.nombre,
            "mensaje": m.mensaje,
            "estado": m.estado,
            "start_date": m.start_date.isoformat() if m.start_date else None,
            "expiration_date": m.expiration_date.isoformat() if m.expiration_date else None
        }
        for m in p.mensajes
    ])

# --- extra: crear mensaje para un proyecto ---
@project.route("/proyectos/<int:pid>/mensajes", methods=["POST"])
@jwt_required()
def crear_mensaje(pid):
    p = Proyecto.query.get_or_404(pid)
    data = request.json
    if not data or not data.get("mensaje") or not data.get("nombre"):
        return jsonify({"error": "Faltan campos requeridos (nombre y mensaje son obligatorios)"}), 400

    start_date = None
    if data.get("start_date"):
        try:
            start_date = datetime.fromisoformat(data["start_date"])
        except ValueError:
            return jsonify({"error": "Formato de start_date inválido. Usa ISO 8601."}), 400

    expiration_date = None
    if data.get("expiration_date"):
        try:
            expiration_date = datetime.fromisoformat(data["expiration_date"])
        except ValueError:
            return jsonify({"error": "Formato de expiration_date inválido. Usa ISO 8601."}), 400

    if start_date and expiration_date and start_date > expiration_date:
        return jsonify({"error": "start_date no puede ser mayor que expiration_date"}), 400

    nuevo = Mensaje(
        nombre=data.get("nombre"),
        mensaje=data.get("mensaje"),
        proyecto_id=pid,
        usuario_id=int(get_jwt_identity()),
        start_date=start_date,
        expiration_date=expiration_date
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"message": "Mensaje creado exitosamente"}), 201



    

    
    

