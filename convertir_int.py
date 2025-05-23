from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["Morpheus"]

camas = db.beds.find()
actualizadas = 0

for cama in camas:
    numero = cama.get("numero")
    if isinstance(numero, str):
        try:
            nuevo_valor = int(numero)
            db.beds.update_one({"_id": cama["_id"]}, {"$set": {"numero": nuevo_valor}})
            actualizadas += 1
        except ValueError:
            continue

print(f"{actualizadas} camas actualizadas.")
