from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from app import mongo
from io import BytesIO
import pandas as pd
import os

bp = Blueprint('main', __name__, template_folder='templates')

ALLOWED = {"xls", "xlsx", "csv"}

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED
    )

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/consulta')
def consulta():
    return render_template('consulta.html')

@bp.route('/upload')
def upload_page():
    return render_template('upload.html')

@bp.route('/update')
def update():
    return render_template('update.html')


@bp.route("/preview", methods=["POST"])
def preview():
    # 1) Recoger el fichero
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        return redirect(url_for("main.upload_page"))

    # 2) Guardar temporalmente
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, file.filename)
    file.save(path)

    # 3) Leer con pandas usando openpyxl
    df = pd.read_excel(path, engine="openpyxl", dtype=str)
    records = df.to_dict(orient="records")

    # 4) Renderizar la vista previa
    return render_template("preview.html", records=records, filename=file.filename)

@bp.route("/apply-update", methods=["POST"])
def apply_update():
    filename = request.form.get("filename")
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    df = pd.read_excel(path, engine="openpyxl", dtype=str)

    updated = 0
    for _, row in df.iterrows():
        bed_id = row.get("bed_id")  # Ajusta el nombre de la columna si es distinto
        new_vals = {}
        if "estado" in row:
            new_vals["estado"] = row["estado"]
        if "alumno" in row:
            new_vals["alumno"] = row["alumno"]
        if new_vals:
            res = mongo.db.beds.update_one({"bed_id": bed_id}, {"$set": new_vals})
            if res.matched_count:
                updated += 1

    return jsonify(status="success", updated=updated)

@bp.route("/api/search-beds")
def api_search_beds():
    filtro = {}
    for campo in ("planta", "zona", "modulo", "habitacion"):
        val = request.args.get(campo)
        if val:
            filtro[campo] = val
    resultados = list(mongo.db.beds.find(filtro, {"_id": 0}))
    return jsonify(beds=resultados)

@bp.route('/api/available-beds-count')#Proporciona el número total de camas cuyo estado sea "Desocupada".
def available_beds_count():
    count = mongo.db.beds.count_documents({"estado": "Desocupada"})
    return jsonify({"available_beds": count})

@bp.route('/api/update-bed/<bed_id>', methods=['PUT'])#Actualizar el estado de una cama concreta, identificada por su bed_id.
def update_bed(bed_id):
    data = request.get_json()
    estado = data.get('estado')
    if not estado:
        return jsonify({"status": "error", "message": "Falta 'estado'"}), 400

    mongo.db.beds.update_one(
        {"bed_id": bed_id},
        {"$set": {"estado": estado}},
        upsert=True
    )
    return jsonify({"status": "success", "message": f"{bed_id}→{estado}"}), 200

@bp.route('/assign', methods=['GET', 'POST'])
def assign():
    if request.method == 'POST':
        # 1) leo el Excel subido en memoria
        f = request.files.get('file')
        if not f or not allowed_file(f.filename):
            return redirect(url_for('main.assign'))

        df = pd.read_excel(f, engine='openpyxl', dtype=str)
        students = df.to_dict(orient='records')

        # 2) saco las camas libres
        free_beds = mongo.db.beds.find(
            {"estado": "Desocupada"},
            {"_id": 0, "bed_id": 1}
        )
        bed_ids = [b['bed_id'] for b in free_beds]

        # 3) renderizo la tabla de asignaciones
        return render_template('assign.html',
                               students=students,
                               free_beds=bed_ids)

    # GET: muestro el formulario de subida
    return render_template('assign_upload.html')

@bp.route('/api/apply-assignments', methods=['POST'])
def apply_assignments():
    data = request.get_json()
    for a in data.get('assignments', []):
        # Para cada asignación, actualizamos el documento:
        # 1) marcamos la cama como ocupada
        # 2) guardamos nombre y número de alumno
        mongo.db.beds.update_one(
          {"bed_id": a['bed_id']},
          {"$set": {
              "estado": "Ocupada",
              "nombre_alumno": a['nombre_alumno'],
              "numero_alumno": a['numero_alumno']
           }}
        )
    return jsonify({"message": f"{len(data.get('assignments', []))} asignaciones guardadas."})

