from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
from flask import jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

# Activar soporte para ON DELETE CASCADE en SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):  # Solo SQLite
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Cargar variables de entorno
load_dotenv()


# Configuración de la clave secreta para sesiones
app.secret_key = os.urandom(24)

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///control_visitas.db'  # Ruta de la base de datos
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desactivar la notificación de cambios en la base de datos

# Inicialización de SQLAlchemy
db = SQLAlchemy(app)

# Modelo de la tabla "apps" (para las webs)
class App(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    visitas = db.relationship('Visita', backref='app', lazy=True, cascade="all, delete-orphan")


# Modelo de la tabla "visitas" (para las visitas de las webs)
class Visita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('app.id', ondelete='CASCADE'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

# Crear la base de datos (solo si no existe)
with app.app_context():
    db.create_all()
    print("Base de datos creada en:", os.path.abspath("control_visitas.db"))

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
    apps = App.query.all()
    visitas = []
    for app in apps:
        # Obtener todas las visitas asociadas a la app
        app_visitas = Visita.query.filter_by(app_id=app.id).all()
        visitas_count = len(app_visitas)  # Contar las visitas
        visitas.append({'app': app, 'visitas_count': visitas_count, 'fechas': app_visitas})
    
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
        if App.query.filter_by(nombre=web_name).first():
            flash('La aplicación ya está registrada.')
        else:
            new_web = App(nombre=web_name)
            db.session.add(new_web)
            db.session.commit()
            flash(f'La aplicación {web_name} ha sido registrada exitosamente.')
    
    # Obtener todas las aplicaciones registradas
    apps = App.query.all()
    return render_template('admin.html', apps=apps)

# Ruta para eliminar una aplicación
@app.route('/admin/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_app(id):
    app_to_delete = App.query.get(id)
    
    if app_to_delete:
        db.session.delete(app_to_delete)
        db.session.commit()
        flash(f'La aplicación {app_to_delete.nombre} ha sido eliminada exitosamente.')
    else:
        flash('La aplicación no se encontró.')
    
    return redirect(url_for('admin'))

@app.route('/visita', methods=['POST'])
def visita():
    web_name = request.form.get('web_name')  # .get() evita errores si falta

    if not web_name:
        return jsonify({'error': 'Falta el parámetro web_name'}), 400

    app = App.query.filter_by(nombre=web_name).first()

    if app:
        new_visita = Visita(app_id=app.id)
        db.session.add(new_visita)
        db.session.commit()
        return jsonify({'message': f'Visita registrada para {web_name}'}), 200
    else:
        return jsonify({'error': f'La aplicación {web_name} no está registrada'}), 404

if __name__ == "__main__":
    app.run(debug=True)
