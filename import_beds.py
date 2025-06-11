import json
from flask import Flask
from flask_pymongo import PyMongo
from pymongo import MongoClient

app = Flask(__name__)
app.config["MONGO_URI"] = 'mongodb://e2t:Infanteria1537@192.168.7.42:27017/Morpheus?authSource=admin'  # Ajusta si es necesario
mongo = PyMongo(app)

with open("listado_camas.json", "r", encoding="utf-8") as file:
    beds_data = json.load(file)

# Inserta los documentos en la colección "beds"
result = mongo.db.beds.insert_many(beds_data)
print(f"Insertados {len(result.inserted_ids)} documentos en la colección 'beds'.")

client = MongoClient("mongodb://e2t:Infanteria1537@192.168.7.42:27017/admin")
db = client["Morpheus"]

camas = db.beds.find()
actualizadas = 0

for cama in camas:
    campo = cama.get("habitacion")
    campo1 = cama.get("planta")
    campo2 = cama.get("modulo")
    if isinstance(campo, int):
        try:
            nuevo_valor = str(campo)
            db.beds.update_one({"_id": cama["_id"]}, {"$set": {"habitacion": nuevo_valor}})
            actualizadas += 1
        except ValueError:
            continue
        
    if isinstance(campo1, int):
        try:
            nuevo_valor = str(campo1)
            db.beds.update_one({"_id": cama["_id"]}, {"$set": {"planta": nuevo_valor}})
            actualizadas += 1
        except ValueError:
            continue
        
    if isinstance(campo2, int):
        try:
            nuevo_valor = str(campo2)
            db.beds.update_one({"_id": cama["_id"]}, {"$set": {"modulo": nuevo_valor}})
            actualizadas += 1
        except ValueError:
            continue

print(f"{actualizadas} camas actualizadas.")

# Actualizar todas las camas cuyo numero_alumno sea la cadena "null"
resultado = db.beds.update_many(
    {"numero_alumno": "null"},
    {"$set": {"numero_alumno": ""}}
)

# Mostrar cuántos documentos fueron modificados
print(f"{resultado.modified_count} camas actualizadas.")
