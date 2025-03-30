from flask import Flask, request, jsonify
from flask_pymongo import PyMongo

app = Flask(__name__)

# Configura la conexión
# Dependiendo de tu red Docker, es posible que debas cambiar "localhost" por "mongodb_container".
app.config["MONGO_URI"] = "mongodb://localhost:27017/prueba"
mongo = PyMongo(app)

# Ejemplo de endpoint para actualizar el estado de una cama
@app.route('/api/update-bed/<bed_id>', methods=['PUT'])
def update_bed(bed_id):
    data = request.get_json()
    estado = data.get("estado")
    if not estado:
        return jsonify({"status": "error", "message": "No se proporcionó el campo 'estado'"}), 400

    # Aquí, se actualiza (o inserta) el registro en la colección "beds".
    result = mongo.db.beds.update_one(
        {"bed_id": bed_id},
        {"$set": {"estado": estado}},
        upsert=True
    )

    return jsonify({"status": "success", "message": f"Cama {bed_id} actualizada a: {estado}"}), 200

if __name__ == '__main__':
    app.run(debug=True)
