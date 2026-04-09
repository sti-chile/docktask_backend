# src/main_routes.py
# Rutas HTML básicas (sin API)
from flask import Blueprint, request, jsonify, render_template
from .models import Mensaje
from . import db, r

main = Blueprint("main", __name__)


@main.route("/")
def index():
    nombre = request.args.get("nombre", "Desarrollador")
    return render_template("index.html", nombre=nombre)


@main.route("/saludo", methods=["GET"])
def saludo():
    nombre = request.args.get("nombre", "Desarrollador")
    return jsonify({"mensaje": f"Hola, {nombre} 👋"})


@main.route("/contacto", methods=["GET", "POST"])
def contacto():
    respuesta = None
    if request.method == "POST":
        nombre = request.form.get("nombre")
        mensaje = request.form.get("mensaje")

        nuevo_mensaje = Mensaje(nombre=nombre, mensaje=mensaje)
        db.session.add(nuevo_mensaje)
        db.session.commit()

        r.set("ultimo_mensaje", mensaje)
        respuesta = f"Gracias por tu mensaje, {nombre}! 📬"
    return render_template("contacto.html", respuesta=respuesta)


@main.route("/mensajes", methods=["GET"])
def ver_mensajes():
    mensajes = Mensaje.query.order_by(Mensaje.id.desc()).all()
    return render_template("mensajes.html", mensajes=mensajes)
