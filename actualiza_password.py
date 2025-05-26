from flask import Flask
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash

# Configuración de la app y la conexión
app = Flask(__name__)
app.config['MONGO_URI'] = 'MONGO_URI', 'mongodb://localhost:27017/Morpheus'
mongo = PyMongo(app)

with app.app_context():
    result = mongo.db.usuarios.update_one(
        {"nombre": "admin"},
        {"$set": {"contraseña": generate_password_hash("admin")}}
    )
    if result.matched_count:
        print("Contraseña actualizada correctamente para admin.")
    else:
        print("Usuario admin no encontrado.")