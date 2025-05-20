from werkzeug.security import generate_password_hash
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["Morpheus"]

db.usuarios.insert_one({
    "nombre": "admin",
    "contraseña": generate_password_hash("admin"),
    "rol": "admin"
})