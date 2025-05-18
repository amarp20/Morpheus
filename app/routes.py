from flask import Blueprint, flash, render_template, request, jsonify, redirect, url_for, current_app, flash
from app import mongo
import os
import pandas as pd

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

def get_all_beds():
    # Devuelve una lista de dicts con los campos necesarios desde la colección beds
    return list(mongo.db.beds.find({}, {"_id": 0}))

@bp.route('/consulta')
def consulta():
    beds = get_all_beds()
    planta = request.args.get('planta', '')
    zona = request.args.get('zona', '')
    modulo = request.args.get('modulo', '')
    habitacion = request.args.get('habitacion', '')
    genero = request.args.get('genero', '')
    numero_alumno = request.args.get('numero_alumno', '')
    consultar = 'consultar' in request.args

    plantas = sorted(set(b['planta'] for b in beds))
    zonas = sorted(set(b['zona'] for b in beds if not planta or b['planta'] == planta))
    modulos = sorted(set(b['modulo'] for b in beds if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona)))
    habitaciones = sorted(set(b['habitacion'] for b in beds if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona) and (not modulo or b['modulo'] == modulo)))
    generos = sorted(set(b.get('genero', '') for b in beds if b.get('genero', '')))
    numeros_alumno = sorted(set(b.get('numero_alumno', '') for b in beds if b.get('numero_alumno', '')))

    if consultar:
        camas = [
            dict(b, genero=b.get('genero', ''), numero_alumno=b.get('numero_alumno', ''))
            for b in beds
            if (not planta or b['planta'] == planta)
            and (not zona or b['zona'] == zona)
            and (not modulo or b['modulo'] == modulo)
            and (not habitacion or b['habitacion'] == habitacion)
            and (not genero or b.get('genero', '') == genero)
            and (not numero_alumno or b.get('numero_alumno', '') == numero_alumno)
        ]
    else:
        camas = []

    return render_template(
        'consulta.html',
        plantas=plantas,
        zonas=zonas,
        modulos=modulos,
        habitaciones=habitaciones,
        generos=generos,
        numeros_alumno=numeros_alumno,
        planta=planta,
        zona=zona,
        modulo=modulo,
        habitacion=habitacion,
        genero=genero,
        numero_alumno=numero_alumno,
        camas=camas
    )

@bp.route('/upload')
def upload_page():
    return render_template('upload.html')

@bp.route("/preview", methods=["POST"])
def preview():
    file = request.files.get("excel")  
    if not file or not allowed_file(file.filename):
        flash("Ningún archivo seleccionado o formato no permitido.")
        return redirect(url_for("main.upload_page"))

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, file.filename)
    file.save(path)

    df = pd.read_excel(path, engine="openpyxl", dtype=str)
    records = df.to_dict(orient="records")

    return render_template("preview.html", records=records, filename=file.filename)

# filepath: c:\Users\knigh\Desktop\Prueba\Morpheus\app\routes.py
from flask import flash

# ...existing code...

@bp.route("/apply-update", methods=["POST"])
def apply_update():
    filename = request.form.get("filename")
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    df = pd.read_excel(path, engine="openpyxl", dtype=str)

    updated = 0
    for _, row in df.iterrows():
        bed_id = row.get("bed_id")
        if bed_id:
            bed_id = str(bed_id).strip()
        new_vals = {}
        # Para cada campo que quieras actualizar:
        for campo in ["estado", "nombre_alumno", "numero_alumno"]:
            valor = row.get(campo)
            # Si el valor es NaN o None, lo ponemos como cadena vacía
            if pd.isna(valor) or valor is None:
                new_vals[campo] = ""
            else:
                new_vals[campo] = str(valor).strip()
        if bed_id:
            res = mongo.db.beds.update_one({"bed_id": bed_id}, {"$set": new_vals})
            if res.modified_count > 0:
                updated += 1

    flash(f"Actualización realizada con éxito. {updated} camas actualizadas.", "success")
    return render_template("apply_update_result.html", updated=updated)


@bp.route('/assign', methods=['GET', 'POST'])
def assign():
    assign_message = None
    asignaciones = None
    if request.method == 'POST':
        total = int(request.form.get('total', 0))
        asignaciones = []
        asignados = []
        for i in range(total):
            nombre = request.form.get(f'nombre_alumno_{i}')
            numero = request.form.get(f'numero_alumno_{i}')
            bed_id = request.form.get(f'bed_id_{i}')
            asignaciones.append(bed_id)
            if bed_id:
                mongo.db.beds.update_one(
                    {"bed_id": bed_id},
                    {"$set": {
                        "estado": "Ocupada",
                        "nombre_alumno": nombre,
                        "numero_alumno": numero
                    }}
                )
                asignados.append(bed_id)
        assign_message = f"{len(asignados)} asignaciones guardadas."
        # Recargar los datos para mostrar el resultado
        students = []
        free_beds = []
        # Si quieres mostrar los mismos estudiantes y camas, recarga aquí
        # O redirige a otra página si prefieres
    else:
        # GET: muestro el formulario de subida
        # Debes tener students y free_beds listos aquí
        # Por ejemplo, puedes obtenerlos de una subida previa o de la base de datos
        students = []  # Ajusta según tu lógica
        free_beds = [b['bed_id'] for b in mongo.db.beds.find({"estado": "Desocupada"}, {"_id": 0, "bed_id": 1})]

    return render_template(
        'assign.html',
        students=students,
        free_beds=free_beds,
        assign_message=assign_message,
        asignaciones=asignaciones
    )

from flask import session

@bp.route('/assign-upload', methods=['GET', 'POST'])
def assign_upload():
    if request.method == 'POST':
        # Si es la primera vez, carga el Excel
        if 'alumnos_excel' in request.files:
            file = request.files.get("alumnos_excel")
            if not file or not allowed_file(file.filename):
                flash("Ningún archivo seleccionado o formato no permitido.")
                return redirect(url_for("main.assign_upload"))
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)
            path = os.path.join(upload_folder, file.filename)
            file.save(path)
            df = pd.read_excel(path, engine="openpyxl", dtype=str)
            students = df.to_dict(orient="records")
            session['students'] = students
        else:
            students = session.get('students', [])
        # Recupera las camas seleccionadas
        total = int(request.form.get('total', len(students)))
        camas_asignadas = []
        for i in range(total):
            bed_id = request.form.get(f'bed_id_{i}')
            if bed_id:
                camas_asignadas.append(bed_id)
        # Excluye las camas ya seleccionadas
        free_beds = [b['bed_id'] for b in mongo.db.beds.find({"estado": "Desocupada"}, {"_id": 0, "bed_id": 1}) if b['bed_id'] not in camas_asignadas]
        return render_template('assign_preview.html', students=students, free_beds=free_beds)
    return render_template('assign_upload.html')

@bp.route('/assign-confirm', methods=['POST'])
def assign_confirm():
    students = session.get('students', [])
    total = int(request.form.get('total', 0))
    asignados = 0
    for i in range(total):
        nombre = request.form.get(f'nombre_alumno_{i}')
        numero = request.form.get(f'numero_alumno_{i}')
        genero = request.form.get(f'genero_{i}')  # <-- Añadido
        bed_id = request.form.get(f'bed_id_{i}')
        if bed_id:
            bed_id = bed_id.strip()
            res = mongo.db.beds.update_one(
                {"bed_id": bed_id},
                {"$set": {
                    "estado": "Ocupada",
                    "nombre_alumno": nombre if nombre is not None else "",
                    "numero_alumno": numero if numero is not None else "",
                    "genero": genero if genero is not None else ""  # <-- Añadido
                }}
            )
            if res.matched_count > 0:
                asignados += 1
            else:
                print(f"No se encontró bed_id: '{bed_id}'")
    session.pop('students', None)
    return render_template('assign_result.html', asignados=asignados)

@bp.route('/desocupar-cama', methods=['POST'])
def desocupar_cama():
    bed_id = request.form.get('bed_id')
    if bed_id:
        mongo.db.beds.update_one(
            {"bed_id": bed_id},
            {"$set": {
                "estado": "Desocupada",
                "nombre_alumno": "",
                "numero_alumno": "",
                "genero": ""  # <-- Añadido para vaciar el género
            }}
        )
        flash(f"Cama {bed_id} desocupada correctamente.", "success")
    return redirect(request.referrer or url_for('main.consulta'))