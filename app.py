from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración de la clave secreta para sesiones
app.secret_key = os.urandom(24)

# Cargar usuario y contraseña desde las variables de entorno
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

# Crear un hash de la contraseña (solo una vez)
hashed_password = generate_password_hash(PASSWORD)

# Decorador para proteger rutas que solo pueden ser accesadas por usuarios autenticados
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))  # Redirigir al login si no está autenticado
        return f(*args, **kwargs)
    return wrapper

@app.route('/')
def home():
    # Verifica si el usuario está autenticado antes de mostrar la página de inicio
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

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

if __name__ == "__main__":
    app.run(debug=True)
