from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from datetime import datetime
from flask import jsonify
from flask_cors import CORS
from bson import ObjectId

app = Flask(__name__)

CORS(app)

# Cargar variables de entorno
load_dotenv()

# Configuración de la clave secreta para sesiones
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Configuración de MongoDB
app.config['MONGO_URI'] = os.getenv('MONGO_URI')  # URI de conexión a MongoDB (obtenido desde MongoDB Atlas)
mongo = PyMongo(app)

# Cargar usuario y contraseña desde las variables de entorno
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

# Crear un hash de la contraseña (solo una vez)
hashed_password = generate_password_hash(PASSWORD)

# Decorador para proteger rutas que solo pueden ser accedidas por usuarios autenticados
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))  # Redirigir al login si no está autenticado
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__  # Evitar que Flask sobrescriba el nombre de la vista
    return wrapper


@app.route('/')
@login_required
def home():
    # Obtener la información de visitas de todas las apps
    apps = mongo.db.apps.find()  # Accedemos a la colección 'apps'
    visitas = []
    for app in apps:
        # Obtener todas las visitas asociadas a la app
        app_visitas = mongo.db.visitas.find({'app_id': app['_id']})
        visitas_count = mongo.db.visitas.count_documents({'app_id': app['_id']})  # Contar las visitas
        visitas.append({'app': app, 'visitas_count': visitas_count, 'fechas': list(app_visitas)})
    
    return render_template('home.html', visitas=visitas)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verificar las credenciales
        if username == USERNAME and check_password_hash(hashed_password, password):
            session['user'] = username  # Almacenar el nombre del usuario en la sesión
            return redirect(url_for('home'))
        else:
            flash("Credenciales incorrectas, inténtalo de nuevo.")
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)  # Eliminar al usuario de la sesión
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        web_name = request.form['web_name']
        # Asegurarse de que la app no exista ya en la base de datos
        if mongo.db.apps.find_one({'nombre': web_name}):
            flash('La aplicación ya está registrada.')
        else:
            new_web = {'nombre': web_name}
            mongo.db.apps.insert_one(new_web)
            flash(f'La aplicación {web_name} ha sido registrada exitosamente.')
    
    # Obtener todas las aplicaciones registradas
    apps = mongo.db.apps.find()
    return render_template('admin.html', apps=apps)

# Ruta para eliminar una aplicación
@app.route('/admin/eliminar/<app_id>', methods=['POST'])
@login_required
def eliminar_app(app_id):
    # Convertir el app_id a ObjectId
    try:
        app_id = ObjectId(app_id)
    except Exception as e:
        flash('ID de aplicación no válido.')
        return redirect(url_for('admin'))

    app_to_delete = mongo.db.apps.find_one({'_id': app_id})
    
    if app_to_delete:
        mongo.db.apps.delete_one({'_id': app_id})
        mongo.db.visitas.delete_many({'app_id': app_id})  # Eliminar las visitas asociadas
        flash(f'La aplicación {app_to_delete["nombre"]} ha sido eliminada exitosamente.')
    else:
        flash('La aplicación no se encontró.')
    
    return redirect(url_for('admin'))


@app.route('/visita', methods=['POST'])
def visita():
    web_name = request.form.get('web_name')  # .get() evita errores si falta

    if not web_name:
        return jsonify({'error': 'Falta el parámetro web_name'}), 400

    app = mongo.db.apps.find_one({'nombre': web_name})

    if app:
        new_visita = {'app_id': app['_id'], 'fecha': datetime.utcnow()}
        mongo.db.visitas.insert_one(new_visita)
        return jsonify({'message': f'Visita registrada para {web_name}'}), 200
    else:
        return jsonify({'error': f'La aplicación {web_name} no está registrada'}), 404


if __name__ == "__main__":
    # Usa el puerto de la variable de entorno, si no está presente, usa el puerto 5000
    port = int(os.environ.get("PORT", 6000))
    app.run(host="0.0.0.0", port=port)
