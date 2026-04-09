from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

import os
import redis

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True
)


def create_app():
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Pool de conexiones: verificar conexión antes de usar (evita error en primer request)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,  # Reciclar conexiones cada 5 minutos
    }

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # CORS configurado con origins específicos
    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS(app, origins=allowed_origins, supports_credentials=True)

    from .main_routes import main
    from .admin_routes import admin
    from .project_routes import project
    from .workspace_routes import workspace
    from .music_routes import music
    from .api_v1_routes import api_v1

    app.register_blueprint(main)

    # ═══════════════════════════════════════════════════════════════════
    # API v1 - Rutas principales (USAR ESTAS)
    # ═══════════════════════════════════════════════════════════════════
    app.register_blueprint(api_v1, url_prefix="/api/v1")
    app.register_blueprint(admin, url_prefix="/api/v1")
    app.register_blueprint(project, url_prefix="/api/v1")
    app.register_blueprint(workspace, url_prefix="/api/v1")
    app.register_blueprint(music)  # ya tiene url_prefix="/api/v1/music"

    # ═══════════════════════════════════════════════════════════════════
    # API Legacy - Compatibilidad con frontend actual (DEPRECADO)
    # TODO: Migrar frontend a /api/v1/* y eliminar estos registros
    # ═══════════════════════════════════════════════════════════════════
    app.register_blueprint(api_v1, url_prefix="/api", name="api_legacy")
    app.register_blueprint(admin, url_prefix="/api", name="admin_legacy")
    app.register_blueprint(project, url_prefix="/api", name="project_legacy")
    app.register_blueprint(workspace, url_prefix="/api", name="workspace_legacy")

    return app
