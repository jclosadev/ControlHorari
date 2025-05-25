from flask import Flask, render_template_string, redirect, request, url_for, session, flash
from datetime import datetime, timedelta, date
import csv
import os
import socket
from functools import wraps
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'

passwords_file = 'passwords.json'

# Cargar contraseñas desde archivo
if os.path.exists(passwords_file):
    try:
        with open(passwords_file, 'r') as f:
            USERS = json.load(f)
    except json.JSONDecodeError:
        USERS = {}
else:
    USERS = {}

csv_file = 'registre.csv'

# Crear el CSV si no existe con el nuevo header
if not os.path.exists(csv_file):
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Data', 'User', 'Hora de entrada', 'Hora de sortida'])

# Página de inicio (registro de horas)
html_page = '''
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Control Horari - Tallers Clip</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        background: #f5f7fa;
        text-align: center;
        padding: 20px;
      }
      h1 {
        color: #333;
        font-size: 2em;
      }
      .info {
        margin-bottom: 20px;
        font-size: 1.1em;
      }
      .button {
        background-color: #4CAF50;
        border: none;
        color: white;
        padding: 15px 30px;
        margin: 15px;
        font-size: 1.2em;
        cursor: pointer;
        border-radius: 8px;
        width: 90%%;
        max-width: 300px;
      }
      .button:hover {
        background-color: #45a049;
      }
      .msg {
        font-size: 1.2em;
        color: #007bff;
        margin-top: 20px;
      }
      a.logout {
        display: block;
        margin-top: 20px;
        text-decoration: none;
        color: #4CAF50;
        font-weight: bold;
      }
    </style>
  </head>
  <body>
    <div class="info">
      Benvingut, {{ user }} <br>
      Avui ès: {{ current_time }}
    </div>
    <h1>Registre d'Hores</h1>
    <form method="post" action="/registrar">
        <button class="button" name="accion" value="entrada">Registrar Entrada</button>
        <button class="button" name="accion" value="salida">Registrar Sortida</button>
    </form>
    <a class="logout" href="{{ url_for('mis_horas') }}">Les meves hores</a>
    {% if user == 'Ramon' %}
<a class="logout" href="{{ url_for('admin') }}">Registre d'hores</a>
{% endif %}
    <a class="logout" href="{{ url_for('logout') }}">Tancar Sessió</a>
    {% if mensaje %}
    <div class="msg">{{ mensaje }}</div>
    {% endif %}
  </body>
</html>
'''

# Página de visor de horas (administración)
html_registros = '''
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Visor d'hores</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        background: #f9fafb;
        padding: 20px;
      }
      h1, h2 {
        text-align: center;
        color: #333;
      }
      table {
        width: 100%%;
        max-width: 800px;
        margin: 30px auto;
        border-collapse: collapse;
        background-color: white;
      }
      th, td {
        border: 1px solid #ddd;
        padding: 10px;
        text-align: center;
      }
      th {
        background-color: #4CAF50;
        color: white;
      }
      tr:nth-child(even) {
        background-color: #f2f2f2;
      }
      form {
        text-align: center;
        margin-bottom: 20px;
      }
      select {
        font-size: 16px;
        padding: 5px 10px;
        margin: 0 10px;
      }
      a {
        display: block;
        text-align: center;
        margin-top: 20px;
        color: #4CAF50;
        text-decoration: none;
      }
      .summary {
        text-align: center;
        margin-top: 20px;
        font-size: 1.2em;
      }
    </style>
  </head>
  <body>
    <h1>Visor d'Hores</h1>
    <form method="get" action="/registros">
      <label for="mes">Filtrar per mes:</label>
      <select name="mes" id="mes" onchange="this.form.submit()">
        <option value="Todos" {% if mes_actual == 'Todos' %}selected{% endif %}>Tots</option>
        {% for mes in meses %}
        <option value="{{ mes }}" {% if mes == mes_actual %}selected{% endif %}>{{ mes }}</option>
        {% endfor %}
      </select>
      &nbsp;&nbsp;
      <label for="user_filter">Filtrar per usuari:</label>
      <select name="user" id="user_filter" onchange="this.form.submit()">
        <option value="Todos" {% if user_filter == 'Todos' %}selected{% endif %}>Tots</option>
        {% for u in users %}
        <option value="{{ u }}" {% if u == user_filter %}selected{% endif %}>{{ u }}</option>
        {% endfor %}
      </select>
    </form>

    <div class="summary">
      Total d'hores treballades: {{ total_horas }} h <br>
      Total d'absències: {{ total_absences }}
    </div>

   <table>
  <tr>
    <th>Usuari</th>
    <th>Data</th>
    <th>Hora d'entrada</th>
    <th>Hora de sortida</th>
  </tr>
  {% for fila in registros %}
  <tr>
    <td>{{ fila[1] }}</td>
    <td>{{ fila[0] }}</td>
    <td>{{ fila[2] }}</td>
    <td>{{ fila[3] }}</td>
  </tr>
  {% endfor %}
</table>
    <a href="/">Tornar al registre</a>
  </body>
</html>
'''

# Página de login
login_template = '''
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Iniciar Sessió - Control Horari</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        background: #ffffff;
        margin: 0;
        padding: 40px 20px;
      }
      .login-container {
        background: #f9fafb;
        padding: 50px 30px;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
        box-sizing: border-box;
      }
      h1 {
        text-align: center;
        font-size: 30px;
        margin-bottom: 40px;
        color: #222;
        font-weight: 600;
      }
      label {
        display: block;
        text-align: left;
        margin: 12px 0 6px;
        font-size: 16px;
        color: #333;
      }
      select, input[type="password"] {
        width: 100%;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ccc;
        border-radius: 12px;
        margin-bottom: 20px;
        background-color: #f1f3f5;
        box-sizing: border-box;
      }
      .button {
        background-color: #4CAF50;
        border: none;
        color: white;
        padding: 16px;
        width: 100%;
        border-radius: 12px;
        font-size: 18px;
        cursor: pointer;
        margin-top: 10px;
      }
      .button:hover {
        background-color: #45a049;
      }
      .error {
        color: #e74c3c;
        text-align: center;
        margin-top: 10px;
        font-size: 14px;
      }
    </style>
  </head>
  <body>
    <div class="login-container">
      <h1>Iniciar Sessió</h1>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="error">
            {% for message in messages %}
              {{ message }}
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      <form method="post" action="/login">
        <label for="username">Usuari</label>
        <select name="username" id="username" required>
          {% for u in users %}
          <option value="{{ u }}">{{ u }}</option>
          {% endfor %}
        </select>
        <label for="password">Contrasenya</label>
        <input type="password" name="password" id="password" placeholder="Contrasenya" required>
        <button class="button" type="submit">Entrar</button>
      </form>
    <a href="/cambiar_password" style="
    display: block;
    text-align: center;
    margin-top: 15px;
    color: #4CAF50;
    font-weight: bold;
    text-decoration: none;
">Canviar la Contrasenya</a>
    </div>
  </body>
</html>
'''
# Crear una nueva contraseña
crear_password_template = '''
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Crear Contrasenya - Control Horari</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        background: #ffffff;
        margin: 0;
        padding: 40px 20px;
      }
      .login-container {
        background: #f9fafb;
        padding: 50px 30px;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
        box-sizing: border-box;
      }
      h1 {
        text-align: center;
        font-size: 30px;
        margin-bottom: 40px;
        color: #222;
        font-weight: 600;
      }
      label {
        display: block;
        text-align: left;
        margin: 12px 0 6px;
        font-size: 16px;
        color: #333;
      }
      select, input[type="password"] {
        width: 100%;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ccc;
        border-radius: 12px;
        margin-bottom: 20px;
        background-color: #f1f3f5;
        box-sizing: border-box;
      }
      .button {
        background-color: #4CAF50;
        border: none;
        color: white;
        padding: 16px;
        width: 100%;
        border-radius: 12px;
        font-size: 18px;
        cursor: pointer;
        margin-top: 10px;
      }
      .button:hover {
        background-color: #45a049;
      }
      .error {
        color: #e74c3c;
        text-align: center;
        margin-top: 10px;
        font-size: 14px;
      }
    </style>
  </head>
  <body>
    <div class="login-container">
      <h1>Crear Contrasenya</h1>
      <form method="post">
        <label for="username">Usuari</label>
        <select name="username" id="username" required>
          {% for u in users %}
          <option value="{{ u }}">{{ u }}</option>
          {% endfor %}
        </select>
        <label for="password">Nova Contrasenya</label>
        <input type="password" name="password" id="password" placeholder="Nova contrasenya" required>
        <button class="button" type="submit">Crear</button>
      </form>
    </div>
  </body>
</html>
'''

cambiar_password_template = '''
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Canviar Contrasenya</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        background: #ffffff;
        margin: 0;
        padding: 40px 20px;
      }
      .login-container {
        background: #f9fafb;
        padding: 50px 30px;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
        box-sizing: border-box;
      }
      h1 {
        text-align: center;
        font-size: 26px;
        margin-bottom: 30px;
        color: #222;
        font-weight: 600;
      }
      label {
        display: block;
        text-align: left;
        margin: 12px 0 6px;
        font-size: 16px;
        color: #333;
      }
      select, input[type="password"] {
        width: 100%;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ccc;
        border-radius: 12px;
        margin-bottom: 20px;
        background-color: #f1f3f5;
        box-sizing: border-box;
      }
      .button {
        background-color: #4CAF50;
        border: none;
        color: white;
        padding: 16px;
        width: 100%;
        border-radius: 12px;
        font-size: 18px;
        cursor: pointer;
        margin-top: 10px;
      }
      .button:hover {
        background-color: #45a049;
      }
      .error {
        color: #e74c3c;
        text-align: center;
        margin-top: 10px;
        font-size: 14px;
      }
    </style>
  </head>
  <body>
    <div class="login-container">
      <h1>Canviar Contrasenya</h1>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="error">
            {% for message in messages %}
              {{ message }}
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      <form method="post">
        <label for="username">Usuari</label>
        <select name="username" id="username" required>
          {% for u in users %}
          <option value="{{ u }}">{{ u }}</option>
          {% endfor %}
        </select>
        <label for="old_password">Contrasenya antiga</label>
        <input type="password" name="old_password" id="old_password" placeholder="Contrasenya actual" required>
        <label for="new_password">Nova contrasenya</label>
        <input type="password" name="new_password" id="new_password" placeholder="Nova contrasenya" required>
        <button class="button" type="submit">Canviar</button>
      </form>
    </div>
  </body>
</html>
'''

# Cambiar Contraseña
@app.route('/cambiar_password', methods=['GET', 'POST'])
def cambiar_password():
    if request.method == 'POST':
        username = request.form['username']
        old_pw = request.form['old_password']
        new_pw = request.form['new_password']

        if USERS.get(username) != old_pw:
            flash("Contrasenya antiga incorrecta.")
        else:
            USERS[username] = new_pw
            with open(passwords_file, 'w') as f:
                json.dump(USERS, f)
            flash("Contrasenya actualitzada correctament.")
            return redirect(url_for('login'))

    return render_template_string(cambiar_password_template, users=list(USERS.keys()))

@app.route('/crear_password', methods=['GET', 'POST'])
def crear_password():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        USERS[username] = password
        with open(passwords_file, 'w') as f:
            json.dump(USERS, f)
        flash("")
        return redirect(url_for('login'))
    # Solo usuarios sin contraseña
    all_users = ["Ramon", "Xevi", "Jordi"]
    sin_password = [u for u in all_users if u not in USERS]
    return render_template_string(crear_password_template, users=sin_password)

# Funció per actualitzar absències d'un usuari
def update_absences(user):
    today_date = date.today()
    with open(csv_file, 'r', newline='') as file:
        reader = list(csv.reader(file))
    header = reader[0]
    records = reader[1:]
    
    # Filtrar els registres de l'usuari
    user_records = [row for row in records if row[1] == user]
    if user_records:
        try:
            last_record_date = max(datetime.strptime(row[0], "%Y-%m-%d").date() for row in user_records)
        except Exception:
            last_record_date = today_date
    else:
        last_record_date = today_date

    missing_date = last_record_date + timedelta(days=1)
    updated = False
    while missing_date < today_date:
        if not any(row for row in user_records if row[0] == missing_date.strftime("%Y-%m-%d")):
            new_record = [missing_date.strftime("%Y-%m-%d"), user, "Ausente", "Ausente"]
            records.append(new_record)
            updated = True
        missing_date += timedelta(days=1)
    
    if updated:
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(records)

# Decorador per protegir rutes que requereixen login
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username not in USERS:
            flash("S'ha asignat una Contrasenya al usuari correctament.")
            return redirect(url_for('crear_password'))

        if USERS.get(username) == password:
          session['user'] = username
          return redirect(url_for('index'))

        else:
            flash("Credencials incorrectes. Torna-ho a intentar.")

    return render_template_string(login_template, users=list(set(["Ramon", "Xevi", "Jordi"])))  # Mostrar usuaris disponibles

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/mis_horas')
@login_required
def mis_horas():
    user = session['user']

    with open(csv_file, 'r', newline='') as file:
        registros = list(csv.reader(file))
    header = registros[0]
    registros = registros[1:]

    # Filtro por mes
    mes_actual = request.args.get('mes', 'Todos')
    meses_disponibles = sorted({row[0][:7] for row in registros if row[1] == user}, reverse=True)

    # Filtrar por usuario y por mes
    registros_filtrados = [r for r in registros if r[1] == user]
    if mes_actual != 'Todos':
        registros_filtrados = [r for r in registros_filtrados if r[0].startswith(mes_actual)]

    # Agrupar por fecha
    from collections import defaultdict
    agrupados = defaultdict(list)
    for row in registros_filtrados:
        clave = row[0]  # fecha
        agrupados[clave].append(row)

    total_horas = 0.0
    total_absences = 0
    registros_resultado = []

    for fecha, registros_dia in agrupados.items():
        entradas = []
        salidas = []
        horas_dia = 0.0

        for r in registros_dia:
            if r[2] and r[2] != "Ausente":
                entradas.append(datetime.strptime(f"{r[0]} {r[2]}", "%Y-%m-%d %H:%M:%S"))
            if r[3] and r[3] != "Ausente":
                salidas.append(datetime.strptime(f"{r[0]} {r[3]}", "%Y-%m-%d %H:%M:%S"))

        for entrada, salida in zip(entradas, salidas):
            if salida > entrada:
                horas_dia += (salida - entrada).total_seconds() / 3600

        if horas_dia == 0 and not entradas and not salidas:
            total_absences += 1

        total_horas += horas_dia

        lista_entradas = ', '.join(e.strftime('%H:%M:%S') for e in entradas)
        lista_salidas = ', '.join(s.strftime('%H:%M:%S') for s in salidas)
        registros_resultado.append([fecha, lista_entradas, lista_salidas])

    total_horas = round(total_horas, 2)
    registros_resultado.sort(key=lambda x: x[0], reverse=True)

    return render_template_string('''
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Les meves hores</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; padding: 20px; background: #f5f5f5; }
            h1 { text-align: center; }
            table { width: 100%%; max-width: 800px; margin: auto; background: white; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
            th { background: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .summary, form { text-align: center; margin-top: 20px; font-size: 1.1em; }
            select { font-size: 16px; padding: 5px 10px; margin: 0 10px; }
            a { display: block; text-align: center; margin-top: 30px; color: #4CAF50; font-weight: bold; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>Les meves hores</h1>
        <form method="get" action="/mis_horas">
          <label for="mes">Filtrar per mes:</label>
          <select name="mes" id="mes" onchange="this.form.submit()">
            <option value="Todos" {% if mes_actual == 'Todos' %}selected{% endif %}>Tots</option>
            {% for mes in meses %}
              <option value="{{ mes }}" {% if mes == mes_actual %}selected{% endif %}>{{ mes }}</option>
            {% endfor %}
          </select>
        </form>
        <div class="summary">
            Total d'hores treballades: {{ total_horas }} h <br>
            Total d'absències: {{ total_absences }}
        </div>
        <table>
            <tr>
                <th>Data</th>
                <th>Entrades</th>
                <th>Sortides</th>
            </tr>
            {% for fila in registros %}
            <tr>
                <td>{{ fila[0] }}</td>
                <td>{{ fila[1] }}</td>
                <td>{{ fila[2] }}</td>
            </tr>
            {% endfor %}
        </table>
        <a href="/">Tornar al menú</a>
    </body>
    </html>
    ''', registros=registros_resultado,
         total_horas=total_horas,
         total_absences=total_absences,
         meses=meses_disponibles,
         mes_actual=mes_actual)

@app.route('/')
@login_required
def index():
    mensaje = request.args.get('mensaje')
    user = session['user']
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_absences(user)
    return render_template_string(html_page, mensaje=mensaje, user=user, current_time=current_time)

@app.route('/registrar', methods=['POST'])
@login_required
def registrar():
    user = session['user']
    accion = request.form['accion']
    ahora = datetime.now()
    fecha = ahora.strftime('%Y-%m-%d')
    hora = ahora.strftime('%H:%M:%S')

    with open(csv_file, 'r', newline='') as file:
        reader = list(csv.reader(file))
    header = reader[0]
    records = reader[1:]

    mensaje = ''
    actualizado = False

    if accion == 'entrada':
        # Registrar nueva entrada
        records.append([fecha, user, hora, ''])
        mensaje = '✅ Entrada registrada correctament.'

    elif accion == 'salida':
        # Buscar la última entrada del mismo día sin salida
        for row in reversed(records):
            if row[0] == fecha and row[1] == user and row[2] != '' and row[3] == '':
                row[3] = hora
                mensaje = '✅ Sortida registrada correctament.'
                actualizado = True
                break
        if not actualizado:
            # Si no hay entrada previa sin salida, registrar una nueva salida sola
            records.append([fecha, user, '', hora])
            mensaje = '⚠️ No hi havia entrada prèvia. Sortida registrada igualment.'

    # Guardar los cambios
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(records)
        print(f"✔️ Registro guardado en {csv_file}: {fecha}, {user}, {hora}")


    return redirect(url_for('index', mensaje=mensaje))

@app.route('/registros')
@login_required
def admin():
    with open(csv_file, 'r', newline='') as file:
        registros = list(csv.reader(file))
    header = registros[0]
    registros = registros[1:]

    mes_actual = request.args.get('mes', 'Todos')
    user_filter = request.args.get('user', 'Todos')

    # Listas únicas de meses y usuarios
    meses_disponibles = sorted({row[0][:7] for row in registros if row[0]}, reverse=True)
    users = sorted({row[1] for row in registros if row[1]})

    # Filtrado por mes y usuario
    registros_filtrados = registros
    if mes_actual != 'Todos':
        registros_filtrados = [r for r in registros_filtrados if r[0].startswith(mes_actual)]
    if user_filter != 'Todos':
        registros_filtrados = [r for r in registros_filtrados if r[1] == user_filter]

    # Agrupación por (fecha, usuario)
    from collections import defaultdict
    agrupados = defaultdict(list)
    for row in registros_filtrados:
        clave = (row[0], row[1])
        agrupados[clave].append(row)

    total_horas = 0.0
    total_absences = 0
    registros_resultado = []

    for (fecha, usuario), registros_dia in agrupados.items():
        entradas = []
        salidas = []
        horas_dia = 0.0

        for r in registros_dia:
            if r[2] and r[2] != "Ausente":
                entradas.append(datetime.strptime(f"{r[0]} {r[2]}", "%Y-%m-%d %H:%M:%S"))
            if r[3] and r[3] != "Ausente":
                salidas.append(datetime.strptime(f"{r[0]} {r[3]}", "%Y-%m-%d %H:%M:%S"))

        for entrada, salida in zip(entradas, salidas):
            if salida > entrada:
                horas_dia += (salida - entrada).total_seconds() / 3600

        if horas_dia == 0 and not entradas and not salidas:
            total_absences += 1

        total_horas += horas_dia

        lista_entradas = ', '.join(e.strftime('%H:%M:%S') for e in entradas)
        lista_salidas = ', '.join(s.strftime('%H:%M:%S') for s in salidas)
        registros_resultado.append([fecha, usuario, lista_entradas, lista_salidas])

    total_horas = round(total_horas, 2)

    # Ordenar por fecha descendente
    registros_resultado.sort(key=lambda x: x[1], reverse=True)

    return render_template_string(html_registros,
                                  registros=registros_resultado,
                                  total_horas=total_horas,
                                  total_absences=total_absences,
                                  meses=meses_disponibles,
                                  mes_actual=mes_actual,
                                  users=users,
                                  user_filter=user_filter)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    ip_local = get_ip()
    print(f"\n✅ Obre aquesta URL al teu mòbil: http://{ip_local}:5000")
    print("Pots generar un codi QR amb aquesta adreça.\n")
    app.run(host='0.0.0.0', port=5000)
