from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS
import os

mongo = PyMongo()

def create_app():
    # Le indicamos explícitamente dónde están estáticos y plantillas
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
        instance_relative_config=False
    )
    app.config.from_object('app.config.Config')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Inicializar extensiones
    mongo.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Registrar blueprint
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app