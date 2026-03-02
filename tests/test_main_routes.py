# tests/test_main_routes.py

import pytest
from src.main_routes import main
from flask import Flask
import os

@pytest.fixture
def app():
    # Asegura ruta absoluta a templates
    template_dir = os.path.join(os.path.dirname(__file__), "../src/templates")
    app = Flask(__name__, template_folder=template_dir)
    app.register_blueprint(main)
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index(client):
    # GET /
    response = client.get("/")
    assert response.status_code == 200
    assert b"Desarrollador" in response.data  # si tu template usa "Desarrollador" por defecto

def test_saludo(client):
    # GET /saludo?nombre=Javi
    response = client.get("/saludo?nombre=Javi")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["mensaje"] == "Hola, Javi 👋"
