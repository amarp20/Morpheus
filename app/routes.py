from flask import Blueprint, flash, render_template, request, jsonify, redirect, url_for, current_app, flash, session
from app import mongo
import os
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from functools import wraps

bp = Blueprint('main', __name__, template_folder='templates')

ALLOWED = {"xls", "xlsx", "csv"}

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED
    )

def login_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        print("✔️ Verificando sesión de usuario...")
        if not session.get('usuario'):
            flash("Acceso no permitido. Inicia sesión.", "danger")
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorado

def rol_requerido(*roles):
    def decorador(f):
        @wraps(f)
        def decorado(*args, **kwargs):
            if not session.get('usuario'):
                flash("Acceso no permitido. Inicia sesión.", "danger")
                return redirect(url_for('main.login'))
            if session.get('rol') not in roles:
                flash("No tiene privilegios para acceder a esta sección.", "warning")
                return redirect(url_for('main.panel'))
            return f(*args, **kwargs)
        return decorado
    return decorador

@bp.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('main.panel'))
    return redirect(url_for('main.login'))

    
def get_all_beds():
    return list(mongo.db.beds.find({}, {
        "_id": 0,
        "bed_id": 1,
        "planta": 1,
        "zona": 1,
        "modulo": 1,
        "habitacion": 1,
        "numero": 1,
        "estado": 1,
        "nombre_alumno": 1,
        "apellido1": 1,
        "apellido2": 1,
        "brigada": 1,
        "especialidad": 1,
        "numero_alumno": 1,
        "genero": 1
    }))

@bp.route('/consulta')
@login_requerido
def consulta():
    beds = get_all_beds()
    planta = request.args.get('planta', '').strip()
    zona = request.args.get('zona', '').strip()
    modulo = request.args.get('modulo', '').strip()
    habitacion = request.args.get('habitacion', '').strip()
    genero = request.args.get('genero', '').strip()
    numero_alumno = request.args.get('numero_alumno', '').strip()
    brigada = request.args.get('brigada', '').strip()
    consultar = 'consultar' in request.args

    plantas = sorted(set(b['planta'] for b in beds))
    zonas = sorted(set(b['zona'] for b in beds if not planta or b['planta'] == planta))
    modulos = sorted(set(b['modulo'] for b in beds if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona)))
    habitaciones = sorted(set(b['habitacion'] for b in beds if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona) and (not modulo or b['modulo'] == modulo)))
    generos = sorted(set(b.get('genero', '') for b in beds if b.get('genero', '')))
    numeros_alumno = sorted(set(b.get('numero_alumno', '') for b in beds if b.get('numero_alumno', '')))
    brigadas = sorted(set(b.get('brigada', '') for b in beds if b.get('brigada')))


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
            and (not brigada or b.get('brigada', '') == brigada)
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
        camas=camas,
        brigada=brigada,
        brigadas=brigadas,

    )
#Este es el upload de subir excel
@bp.route('/upload')
@rol_requerido('admin')
def upload_page():
    return render_template('upload.html')

# Esta es la preview de subir excel
@bp.route('/preview', methods=['GET'])
def preview_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@rol_requerido('admin')
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
    for col in ['planta', 'zona', 'modulo', 'habitacion', 'numero']:
        if col in df.columns:
            df[col] = df[col].astype(str)

    records = df.to_dict(orient="records")
    return render_template("preview.html", camas=records, filename=file.filename)

#Con este bp se aplican los cambios de subir excel
@bp.route('/apply-update', methods=['GET'])
def apply_update_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@bp.route("/apply-update", methods=["POST"])
@rol_requerido('admin')
def apply_update():
    filename = request.form.get("filename")
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    df = pd.read_excel(path, engine="openpyxl", dtype=str)
    for col in ['planta', 'zona', 'modulo', 'habitacion', 'numero']:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    updated = 0
    for _, row in df.iterrows():
        bed_id = row.get("bed_id")
        if bed_id:
            bed_id = str(bed_id).strip()
        new_vals = {}

        campos_actualizables = [
            "estado", "nombre_alumno", "numero_alumno",
            "apellido1", "apellido2", "brigada", "especialidad", "genero"
        ]

        for campo in campos_actualizables:
            valor = row.get(campo)
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

#Este bp inicia el asignar camas
@bp.route('/assign', methods=['GET', 'POST'])
@rol_requerido('admin', 'usuario')
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
    else:
        students = []  
        free_beds = [b['bed_id'] for b in mongo.db.beds.find({"estado": "Desocupada"}, {"_id": 0, "bed_id": 1})]

    return render_template(
        'assign.html',
        students=students,
        free_beds=free_beds,
        assign_message=assign_message,
        asignaciones=asignaciones
    )
#este bp realiza la carga de datos de la base de datos en asignar camas
@bp.route('/assign-upload', methods=['GET', 'POST'])
@rol_requerido('admin', 'usuario')
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
        return render_template('assign_preview.html', students=students, free_beds=free_beds, camas_asignadas=camas_asignadas)
    return render_template('assign_upload.html')

#Este bp es el que realiza los cambios en la base de datos una vez confirmamos los cambios al asignar camas
@bp.route('/assign-confirm', methods=['GET'])
def assign_confirm_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@bp.route('/assign-confirm', methods=['POST'])
@rol_requerido('admin', 'usuario')
def assign_confirm():
    students = session.get('students', [])
    total = int(request.form.get('total', 0))
    asignados = 0
    asignacion_info = []

    for i in range(total):
        nombre = request.form.get(f'nombre_alumno_{i}')
        numero = request.form.get(f'numero_alumno_{i}')
        apellido1 = request.form.get(f'apellido1_{i}')
        apellido2 = request.form.get(f'apellido2_{i}')
        brigada = request.form.get(f'brigada_{i}')
        especialidad = request.form.get(f'especialidad_{i}')
        genero = request.form.get(f'genero_{i}')
        bed_id = request.form.get(f'bed_id_{i}')

        if bed_id:
            bed_id = bed_id.strip()
            res = mongo.db.beds.update_one(
                {"bed_id": bed_id},
                {"$set": {
                    "estado": "Ocupada",
                    "nombre_alumno": nombre or "",
                    "numero_alumno": numero or "",
                    "apellido1": apellido1 or "",
                    "apellido2": apellido2 or "",
                    "brigada": brigada or "",
                    "especialidad": especialidad or "",
                    "genero": genero or ""
                }}
            )
            if res.matched_count > 0:
                asignados += 1
                asignacion_info.append({
                    "nombre": nombre,
                    "apellido1": apellido1,
                    "apellido2": apellido2,
                    "numero": numero,
                    "brigada": brigada,
                    "especialidad": especialidad,
                    "bed_id": bed_id
                })
            else:
                print(f"No se encontró bed_id: '{bed_id}'")

    session.pop('students', None)
    return render_template("assign_result.html", asignados=asignados, asignaciones=asignacion_info)

#este bp desocupa las camas una vez realizada una consulta pulsando el botón desocupar
@bp.route('/desocupar', methods=['GET'])
def desocupar_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@login_requerido
@bp.route('/desocupar', methods=['POST'])
def desocupar_cama():
    bed_id = request.form.get('bed_id')
    if bed_id:
        mongo.db.beds.update_one(
            {"bed_id": bed_id},
            {"$set": {
                "estado": "Desocupada",
                "nombre_alumno": "",
                "numero_alumno": "",
                "apellido1": "",
                "apellido2": "",
                "genero": "",
                "especialidad": "",
                "brigada": ""
            }}
        )
        flash(f'Cama {bed_id} desocupada correctamente.', 'success')

    return redirect(url_for('main.consulta',
        planta=request.form.get('planta', ''),
        zona=request.form.get('zona', ''),
        modulo=request.form.get('modulo', ''),
        habitacion=request.form.get('habitacion', ''),
        genero=request.form.get('genero', ''),
        numero_alumno=request.form.get('numero_alumno', ''),
        brigada=request.form.get('brigada', ''),
        consultar=1
    ))
#Este bp redirecciona a la página correspondiente depues de loguearse
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        contraseña = request.form.get('contraseña')
        usuario = mongo.db.usuarios.find_one({'nombre': nombre})
        
        if usuario and check_password_hash(usuario['contraseña'], contraseña):
            session['usuario'] = usuario['nombre']
            session['rol'] = usuario['rol']
            session.permanent = False
            return redirect(url_for('main.panel'))
        else:
            flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

#este bp redirige a login después de cerrar sesión
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

#Este bp cierra sesión automáticamente al cerrar la ventana o pestaña
@bp.route('/logout_auto', methods=['POST'])
def logout_auto():
    session.clear()
    return '', 204

#Este bp añade, elimina, consulta y cambia claves desde el panel admin
@bp.route('/gestion-usuarios', methods=['GET', 'POST'])
@rol_requerido('admin')
def gestion_usuarios():
    
    accion = request.form.get('accion')
    usuarios = []

    if accion == "registrar":
        nombre = request.form.get('nombre')
        clave = request.form.get('contraseña')
        confirmar = request.form.get('confirmar')
        rol = request.form.get('rol')

        if mongo.db.usuarios.find_one({'nombre': nombre}):
            flash("Ese nombre de usuario ya existe.", "danger")
        elif clave != confirmar:
            flash("Las contraseñas no coinciden.", "danger")
        else:
            hash_pw = generate_password_hash(clave)
            mongo.db.usuarios.insert_one({'nombre': nombre, 'contraseña': hash_pw, 'rol': rol})
            flash("Usuario creado correctamente.", "success")

    elif accion == "consultar":
        usuarios = list(mongo.db.usuarios.find({}, {'_id': 0, 'nombre': 1, 'rol': 1}))

    elif accion == "cambiar_clave":
        usuario = request.form.get('usuario')
        nueva = request.form.get('nueva')
        confirmar = request.form.get('confirmar')
        if nueva != confirmar:
            flash(f"Las contraseñas no coinciden para {usuario}.", "danger")
        else:
            hash_pw = generate_password_hash(nueva)
            mongo.db.usuarios.update_one({'nombre': usuario}, {'$set': {'contraseña': hash_pw}})
            flash(f"Contraseña actualizada para {usuario}.", "success")
        usuarios = list(mongo.db.usuarios.find({}, {'_id': 0, 'nombre': 1, 'rol': 1}))

    elif accion == "eliminar":
        usuario = request.form.get('usuario')
        mongo.db.usuarios.delete_one({'nombre': usuario})
        flash(f"Usuario {usuario} eliminado.", "success")
        usuarios = list(mongo.db.usuarios.find({}, {'_id': 0, 'nombre': 1, 'rol': 1}))

    return render_template('gestion_usuarios.html', usuarios=usuarios)

#Este bp es para buscar los datos en la base de datos para mostrar en los desplegables
@bp.route('/gestion-edificio')
@rol_requerido('admin')
def gestion_edificio():

    camas = []  # vacías por defecto
    plantas = sorted(mongo.db.beds.distinct("planta"))
    zonas = sorted(mongo.db.beds.distinct("zona"))
    modulos = sorted(mongo.db.beds.distinct("modulo"))

    return render_template('gestion_edificio.html', camas=camas, plantas=plantas, zonas=zonas, modulos=modulos)

#Este bp es para previsualizar la configuración del edificio antes de aplicarla
@bp.route('/gestion-edificio/preview', methods=['GET'])
def gestion_edificio_preview_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@rol_requerido('admin')
@bp.route('/gestion-edificio/preview', methods=['POST'])
def gestion_edificio_preview():

    file = request.files.get('edificio_excel')

    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash("Archivo inválido o no seleccionado.", "danger")
        return redirect(url_for('main.gestion_edificio'))

    filename = f"{uuid.uuid4().hex}.xlsx"
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    df = pd.read_excel(path, engine='openpyxl', dtype=str)
    registros = df.to_dict(orient='records')

    session['gestion_edificio_tempfile'] = filename

    return render_template('gestion_edificio_preview.html', registros=registros, filename=filename)

#Este bp es para cambiar la configuración del edificio en la base de datos
@bp.route('/gestion-edificio/apply', methods=['GET'])
def gestion_edificio_apply_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@rol_requerido('admin')
@bp.route('/gestion-edificio/apply', methods=['POST'])
def gestion_edificio_apply():

    filename = session.get('gestion_edificio_tempfile')

    if not filename:
        flash("No se encontró archivo para aplicar.", "danger")
        return redirect(url_for('main.gestion_edificio'))

    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    try:
        df = pd.read_excel(path, engine='openpyxl', dtype=str)
        for col in ['planta', 'zona', 'modulo', 'habitacion', 'numero']:
            if col in df.columns:
                df[col] = df[col].astype(str)

        total_agregadas = 0

        for _, row in df.iterrows():
            planta = str(row.get('planta', '')).strip()
            zona = str(row.get('zona', '')).strip()
            modulo = str(row.get('modulo', '')).strip()
            habitacion = str(row.get('habitacion', '')).strip()
            numero = row.get('numero', 0)
            bed_id = f"{planta}-{zona}-{modulo}-{habitacion}-Cama{numero}"

            if not mongo.db.beds.find_one({"bed_id": bed_id}):
                cama = {
                    "bed_id": bed_id,
                    "planta": planta,
                    "zona": zona,
                    "modulo": modulo,
                    "habitacion": habitacion,
                    "numero": numero,
                    "estado": "Desocupada",
                    "nombre_alumno": "",
                    "numero_alumno": "",
                    "apellido1": "",
                    "apellido2": "",
                    "brigada": "",
                    "especialidad": "",
                    "genero": ""
                }
                mongo.db.beds.insert_one(cama)
                total_agregadas += 1

        os.remove(path)
        session.pop('gestion_edificio_tempfile', None)

        flash(f"Proceso completado. {total_agregadas} camas añadidas.", "success")
    except Exception as e:
        flash(f"Error al aplicar cambios: {str(e)}", "danger")

    return redirect(url_for('main.gestion_edificio'))

#bp para filtrar camas a mostrar para eliminar luego
@bp.route('/gestion-edificio/filtrar', methods=['GET'])
def gestion_edificio_filtrar_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@rol_requerido('admin')
@bp.route('/gestion-edificio/filtrar', methods=['POST'])
def gestion_edificio_filtrar():

    planta = request.form.get('planta', '').strip()
    zona = request.form.get('zona', '').strip()
    modulo = request.form.get('modulo', '').strip()
    buscar = request.form.get('buscar') == '1'

    # Calcular todas las zonas y módulos filtradas según planta y zona seleccionadas
    todas = list(mongo.db.beds.find({}, {"_id": 0}))
    zonas = sorted(set(b['zona'] for b in todas if not planta or b['planta'] == planta))
    modulos = sorted(set(b['modulo'] for b in todas if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona)))
    plantas = sorted(set(b['planta'] for b in todas))

    camas = []
    if buscar:
        query = {}
        if planta:
            query["planta"] = planta
        if zona:
            query["zona"] = zona
        if modulo:
            query["modulo"] = modulo
        camas = list(mongo.db.beds.find(query, {"_id": 0}))

    return render_template("gestion_edificio.html",
        camas=camas,
        plantas=plantas,
        zonas=zonas,
        modulos=modulos,
        planta=planta,
        zona=zona,
        modulo=modulo
    )
#bp para eliminar camas individualmente
@bp.route('/eliminar-cama', methods=['GET'])
def eliminar_cama_redirect():
    flash("Acceso no permitido", "danger")
    return redirect(url_for('main.login'))

@rol_requerido('admin')
@bp.route('/eliminar-cama', methods=['POST'])
def eliminar_cama():

    bed_id = request.form.get('bed_id')
    planta = request.form.get('planta', '').strip()
    zona = request.form.get('zona', '').strip()
    modulo = request.form.get('modulo', '').strip()

    query = {}
    if planta:
        query["planta"] = planta
    if zona:
        query["zona"] = zona
    if modulo:
        query["modulo"] = modulo

    if bed_id:
        result = mongo.db.beds.delete_one({"bed_id": bed_id})
        if result.deleted_count > 0:
            flash(f"Cama {bed_id} eliminada correctamente.", "success")
        else:
            flash(f"No se encontró la cama {bed_id}.", "danger")

    camas = list(mongo.db.beds.find(query, {"_id": 0}))
    plantas = sorted(mongo.db.beds.distinct("planta"))
    zonas = sorted(mongo.db.beds.distinct("zona"))
    modulos = sorted(mongo.db.beds.distinct("modulo"))

    return render_template("gestion_edificio.html", camas=camas, plantas=plantas, zonas=zonas, modulos=modulos)

#Este bp sirve para desocupar todas las camas de una brigada
@bp.route('/eliminar-brigada', methods=['GET', 'POST'])
@rol_requerido('admin', 'usuario')
def eliminar_brigada():

    if request.method == 'POST':
        brigada = request.form.get('brigada')
        if brigada:
            result = mongo.db.beds.update_many(
                {"brigada": brigada},
                {"$set": {
                    "nombre_alumno": "",
                    "numero_alumno": "",
                    "apellido1": "",
                    "apellido2": "",
                    "genero": "",
                    "especialidad": "",
                    "brigada": "",
                    "estado": "Desocupada"
                }}
            )
            flash(f"{result.modified_count} camas actualizadas para brigada {brigada}.", "success")
            return redirect(url_for('main.eliminar_brigada'))

    brigadas = sorted(mongo.db.beds.distinct("brigada"))
    return render_template("eliminar_brigada.html", brigadas=brigadas)

#este bp es el que muestra las estadísticas de ocupación
@bp.route('/panel')
@login_requerido
def panel():

    camas = list(mongo.db.beds.find({}, {'_id': 0}))
    plantas = sorted(set(b['planta'] for b in camas))

    resumen_por_planta = {}
    camas_por_planta = {}

    for planta in plantas:
        camas_planta = [b for b in camas if b['planta'] == planta]
        total = len(camas_planta)
        ocupadas = sum(1 for b in camas_planta if b.get('estado') == 'Ocupada')
        desocupadas = total - ocupadas

        resumen_por_planta[planta] = {
            'ocupadas': ocupadas,
            'desocupadas': desocupadas,
            'porcentaje_ocupadas': round((ocupadas / total) * 100, 1) if total else 0,
            'porcentaje_desocupadas': round((desocupadas / total) * 100, 1) if total else 0
        }
        camas_por_planta[planta] = camas_planta

    return render_template('index.html',
        plantas=plantas,
        resumen_por_planta=resumen_por_planta,
        camas_por_planta=camas_por_planta
    )
#Este bp realiza la plantilla para imprimir la tarjeta de una habitación
@bp.route('/imprimir-consulta')
@login_requerido
def imprimir_consulta():
    beds = get_all_beds()
    planta = request.args.get('planta', '')
    zona = request.args.get('zona', '')
    modulo = request.args.get('modulo', '')
    habitacion = request.args.get('habitacion', '')
    genero = request.args.get('genero', '')
    numero_alumno = request.args.get('numero_alumno', '')
    brigada = request.args.get('brigada', '')

    plantas = sorted(set(b['planta'] for b in beds))
    zonas = sorted(set(b['zona'] for b in beds if not planta or b['planta'] == planta))
    modulos = sorted(set(b['modulo'] for b in beds if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona)))
    habitaciones_lista = sorted(set(b['habitacion'] for b in beds if (not planta or b['planta'] == planta) and (not zona or b['zona'] == zona) and (not modulo or b['modulo'] == modulo)))
    generos = sorted(set(b.get('genero', '') for b in beds if b.get('genero', '')))
    numeros_alumno = sorted(set(b.get('numero_alumno', '') for b in beds if b.get('numero_alumno', '')))
    brigadas = sorted(set(b.get('brigada', '') for b in beds if b.get('brigada')))

    query = {}
    if planta: query["planta"] = planta
    if zona: query["zona"] = zona
    if modulo: query["modulo"] = modulo
    if habitacion: query["habitacion"] = habitacion
    if genero: query["genero"] = genero
    if numero_alumno: query["numero_alumno"] = numero_alumno
    if brigada: query["brigada"] = brigada

    query["estado"] = "Ocupada"

    camas = list(mongo.db.beds.find(query, {"_id": 0}))
    habitaciones = {}

    for cama in camas:
        clave = f"{cama['planta']}-{cama['zona']}-{cama['modulo']}-{cama['habitacion']}"
        habitaciones.setdefault(clave, []).append(cama)

    return render_template(
        "imprimir_consulta.html",
        habitaciones=habitaciones,
        plantas=plantas,
        zonas=zonas,
        modulos=modulos,
        habitaciones_lista=habitaciones_lista,
        generos=generos,
        numeros_alumno=numeros_alumno,
        brigadas=brigadas,
        planta=planta,
        zona=zona,
        modulo=modulo,
        habitacion=habitacion,
        genero=genero,
        numero_alumno=numero_alumno,
        brigada=brigada,
        camas=camas
    )

@bp.route('/vista-impresion')
@login_requerido
def vista_impresion():
    query = {}
    for campo in ["planta", "zona", "modulo", "habitacion", "genero", "numero_alumno", "brigada"]:
        valor = request.args.get(campo)
        if valor:
            query[campo] = valor

    query["estado"] = "Ocupada"

    camas = list(mongo.db.beds.find(query, {"_id": 0}))
    habitaciones = {}

    for cama in camas:
        clave = f"{cama['planta']}-{cama['zona']}-{cama['modulo']}-{cama['habitacion']}"
        habitaciones.setdefault(clave, []).append(cama)

    return render_template("vista_impresion.html", habitaciones=habitaciones)

# Este bp accede a la visión de ocupación de las plantas desde los botones de la página panel_graficos.html
@bp.route('/plano_planta1')
@login_requerido
def plano_planta1():
    from app import mongo
    beds = list(mongo.db.beds.find({}, {'_id': 0, 'planta': 1, 'zona': 1, 'modulo': 1, 'estado': 1}))
    
    resumen = {}
    for b in beds:
        key = f"{b['planta']}{b['zona'].lower()}{b['modulo']}"
        if key not in resumen:
            resumen[key] = {'modulo': b['modulo'], 'camas': 0, 'libres': 0}
        resumen[key]['camas'] += 1
        if b['estado'] == 'Desocupada':
            resumen[key]['libres'] += 1

    return render_template('plano_planta1.html', resumen=resumen)

@bp.route('/plano_planta2')
@login_requerido
def plano_planta2():
    # Permitir solo si el rol está permitido
    if session.get('rol') not in ['admin', 'usuario', 'mando']:
        flash("No tiene privilegios para acceder a esta sección", "danger")
        return redirect(url_for('main.login'))

    # Obtener todos los documentos de planta "2"
    camas = mongo.db.beds.find({"planta": "2"})
    resumen = {}

    for cama in camas:
        zona = cama.get("zona", "").lower()
        modulo = cama.get("modulo", "").lower()
        if not zona or not modulo:
            continue
        clave = f"2{zona}{modulo}"
        if clave not in resumen:
            resumen[clave] = {"modulo": modulo, "camas": 0, "libres": 0}
        resumen[clave]["camas"] += 1
        if cama.get("estado") == "Desocupada":
            resumen[clave]["libres"] += 1

    return render_template("plano_planta2.html", resumen=resumen)

@bp.route('/plano_planta3')
@login_requerido
def plano_planta3():
    if session.get('rol') not in ['admin', 'usuario', 'mando']:
        flash("No tiene privilegios para acceder a esta sección", "danger")
        return redirect(url_for('main.login'))

    resumen = {}
    camas = mongo.db.beds.find({"planta": "3"})
    for cama in camas:
        key = cama["bed_id"].split("-")[0].lower() + cama["bed_id"].split("-")[1].lower() + cama["modulo"]
        if key not in resumen:
            resumen[key] = {"modulo": cama["modulo"], "camas": 0, "libres": 0}
        resumen[key]["camas"] += 1
        if cama["estado"] == "Desocupada":
            resumen[key]["libres"] += 1

    return render_template('plano_planta3.html', resumen=resumen)
