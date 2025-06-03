from pymongo import MongoClient

# Conexión a la base de datos
client = MongoClient("mongodb://e2t:Infanteria1537@192.168.7.42:27017/admin")
db = client["Morpheus"]

# Actualizar todas las camas cuyo numero_alumno sea la cadena "null"
resultado = db.beds.update_many(
    {"numero_alumno": "null"},
    {"$set": {"numero_alumno": ""}}
)

# Mostrar cuántos documentos fueron modificados
print(f"{resultado.modified_count} camas actualizadas.")
