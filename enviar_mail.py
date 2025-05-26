import pandas as pd
import resend
import base64
from datetime import datetime
import locale

# === CONFIGURACIÓN ===
resend.api_key = "re_KpJgC5Dy_3tRQaeTWhwrBRSwLJ9VNYaCT"
EMAIL_FROM = "Tallers Clip <onboarding@resend.dev>"
EMAIL_TO = ["jclosacot@gmail.com"]

# Establecer locale a español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    # Si no está disponible el locale español, usar el disponible
    pass

# === 1. Preparar el Excel desde registre.csv ===
csv_file = "registre.csv"
excel_file = "registro_ordenado.xlsx"

# Obtener mes y año actuales
now = datetime.now()
current_month = now.month
current_year = now.year
month_name = now.strftime('%B')

print(f"Generando informe para {month_name} {current_year}")

df = pd.read_csv(csv_file)

# Convertir 'Data' a datetime para poder filtrar
df['Data_datetime'] = pd.to_datetime(df['Data'], errors='coerce')

# FILTRAR POR MES Y AÑO ACTUALES
df_filtered = df[
    (df['Data_datetime'].dt.month == current_month) & 
    (df['Data_datetime'].dt.year == current_year)
].copy()

print(f"Registros encontrados para {month_name} {current_year}: {len(df_filtered)}")

if len(df_filtered) == 0:
    print(f"⚠️ No se encontraron registros para {month_name} {current_year}")
    exit()

# Formatear la fecha para mostrar
df_filtered['Data'] = df_filtered['Data_datetime'].dt.strftime('%d/%m/%Y')

# Mantener las horas como texto y formatearlas correctamente
# Asumiendo que las horas vienen en formato HH:MM:SS
df_filtered['Hora_entrada_clean'] = df_filtered['Hora de entrada'].astype(str).str[:8]  # Solo tomar HH:MM:SS
df_filtered['Hora_sortida_clean'] = df_filtered['Hora de sortida'].astype(str).str[:8]  # Solo tomar HH:MM:SS

# Para calcular la duración, convertimos temporalmente a datetime pero solo para el cálculo
df_filtered['entrada_temp'] = pd.to_datetime(df_filtered['Hora de entrada'], format='%H:%M:%S', errors='coerce')
df_filtered['sortida_temp'] = pd.to_datetime(df_filtered['Hora de sortida'], format='%H:%M:%S', errors='coerce')

# Calcular duración
df_filtered['Duración'] = df_filtered['sortida_temp'] - df_filtered['entrada_temp']

# Convertir duración a string "X h Y min"
df_filtered['Duración'] = df_filtered['Duración'].apply(
    lambda x: f"{int(x.total_seconds() // 3600)} h {int((x.total_seconds() % 3600) // 60)} min" if pd.notnull(x) else ""
)

# Seleccionar columnas finales usando las horas limpias
df_final = df_filtered[['Data', 'Usuario', 'Hora_entrada_clean', 'Hora_sortida_clean', 'Duración']].copy()
df_final.rename(columns={
    'Usuario': 'Usuari',
    'Hora_entrada_clean': 'Hora d\'entrada',
    'Hora_sortida_clean': 'Hora de sortida',
    'Duración': 'Duració de la Jornada'
}, inplace=True)

# Ordenar por fecha y usuario
df_final.sort_values(by=['Data', 'Usuari'], inplace=True)

# Guardar Excel con formato
with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
    df_final.to_excel(writer, sheet_name="Resum", index=False)
    worksheet = writer.sheets['Resum']
    workbook = writer.book
    
    # Formato para encabezados
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
    
    # Escribir encabezados con formato
    for col_num, column in enumerate(df_final.columns):
        worksheet.write(0, col_num, column, header_format)
        worksheet.set_column(col_num, col_num, 20)

print(f"✅ Excel generado con {len(df_final)} registros de {month_name} {current_year}")

# === 2. Codificar el archivo en base64 ===
with open(excel_file, "rb") as f:
    file_data = f.read()
    attachment_b64 = base64.b64encode(file_data).decode()

# === 3. Enviar email usando Resend ===
params: resend.Emails.SendParams = {
    "from": EMAIL_FROM,
    "to": EMAIL_TO,
    "subject": f"🕒 Informe Mensual - Tallers Clip ({month_name} {current_year})",
    "html": f"""
        <p>Hola,</p>
        <p>A continuació t'adjunto l'informe mensual d'hores treballades del Control Horari corresponent a <strong>{month_name} {current_year}</strong>.</p>
        <p>Resum del mes:</p>
        <ul>
            <li>Total de registres: {len(df_final)}</li>
            <li>Mes: {month_name} {current_year}</li>
        </ul>
        <p>Salutacions,<br><strong>Tallers Clip S.L</strong></p>
    """,
    "attachments": [{
        "filename": f"informe_{month_name.lower()}_{current_year}.xlsx",
        "content": attachment_b64,
        "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }]
}

email = resend.Emails.send(params)
print("✅ Email enviat:", email)
print(f"Informe mensual de {month_name} {current_year} generat i enviat a {', '.join(EMAIL_TO)}.")
