from werkzeug.security import generate_password_hash
from pymongo import MongoClient

client = MongoClient('mongodb://e2t:Infanteria1537@192.168.7.42:27017/admin')
db = client["Morpheus"]

db.usuarios.insert_one({
    "nombre": "admin123",
    "contraseña": generate_password_hash("admin123"),
    "rol": "admin"
})