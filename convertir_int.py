from pymongo import MongoClient

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
