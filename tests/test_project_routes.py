# tests/test_project_routes.py

import pytest
from flask import Flask
from src import db, jwt
from src.models import Usuario, Proyecto
from src.project_routes import project
from src.main_routes import main

@pytest.fixture
def app():
    # Crea la app Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["JWT_SECRET_KEY"] = "testsecret"
    db.init_app(app)
    jwt.init_app(app)
    app.register_blueprint(project)
    app.register_blueprint(main)
    with app.app_context():
        db.create_all()
        # Usuario admin para login y autorización
        user = Usuario(username="test", password="test", rol="admin")
        db.session.add(user)
        db.session.commit()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

def get_token(client):
    # Obtén un JWT real usando el endpoint de login (ajusta si tu login tiene otro prefijo)
    res = client.post("/api/login", json={"username": "test", "password": "test"})
    assert res.status_code == 200
    return res.get_json()["access_token"]   

def test_crud_proyectos(client):
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # POST: crear un proyecto
    data = {"nombre": "Proyecto Test", "descripcion": "Descripción test"}
    res = client.post("/api/proyectos", headers=headers, json=data)
    assert res.status_code == 201
    assert b"Proyecto creado exitosamente" in res.data

    # GET: listar proyectos
    res = client.get("/api/proyectos", headers=headers)
    assert res.status_code == 200
    proyectos = res.get_json()
    assert isinstance(proyectos, list)
    assert proyectos[0]["nombre"] == "Proyecto Test"
    proyecto_id = proyectos[0]["id"]

    # PUT: actualizar el proyecto
    data_update = {"nombre": "Proyecto Actualizado", "descripcion": "desc nueva"}
    res = client.put(f"/api/proyectos/{proyecto_id}", headers=headers, json=data_update)
    assert res.status_code == 200
    assert b"actualizado exitosamente" in res.data

    # DELETE: eliminar el proyecto
    res = client.delete(f"/api/proyectos/{proyecto_id}", headers=headers)
    assert res.status_code == 200
    assert b"eliminado exitosamente" in res.data

    # GET: asegurar que el proyecto ya no existe
    res = client.get("/api/proyectos", headers=headers)
    proyectos = res.get_json()
    assert len(proyectos) == 0

