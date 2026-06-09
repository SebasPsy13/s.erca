"""
SISTEMA ERCA - Backend FastAPI
Soporte dual: SQLite (local) / PostgreSQL (Railway)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

app = FastAPI(title="SISTEMA ERCA API")

# ======================== CONFIG ========================
# Railway inyecta DATABASE_URL automáticamente cuando activas el plugin Postgres.
# Si no está definida, cae a SQLite para desarrollo local.
_DATABASE_URL = os.environ.get("DATABASE_URL", "")
if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(_DATABASE_URL)
SQLITE_PATH = "sistema_erca.db"

# La contraseña de administrador debe definirse como variable de entorno en Railway.
# Railway Dashboard → tu servicio → Variables → ADMIN_PASSWORD=tu_contraseña_segura
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    PH = "%s"
else:
    import sqlite3
    PH = "?"

# ======================== MODELOS ========================
class Paciente(BaseModel):
    dni: str
    nombre: str
    edad: int
    dx: str
    cap: str

class Evaluacion(BaseModel):
    dni_p: str
    fecha: str
    crea: float
    urea: float
    hb: float
    k: float
    na: float
    acr: float
    tfg: float
    estadio: str
    asistio: str
    notas: str

class Cita(BaseModel):
    dni_p: str
    fecha_cita: str
    tipo: str
    estado: str

# ======================== PARÁMETROS DE LABORATORIO ========================
PARAMETROS_LABORATORIO = {
    "crea": {"nombre": "Creatinina",          "unidad": "mg/dL",           "min": 0.6,  "max": 1.2},
    "urea": {"nombre": "Urea",                "unidad": "mg/dL",           "min": 7,    "max": 20},
    "hb":   {"nombre": "Hemoglobina",         "unidad": "g/dL",            "min": 12,   "max": 17.5},
    "k":    {"nombre": "Potasio",             "unidad": "mEq/L",           "min": 3.5,  "max": 5.0},
    "na":   {"nombre": "Sodio",               "unidad": "mEq/L",           "min": 136,  "max": 145},
    "acr":  {"nombre": "Albúmina/Creatinina", "unidad": "mg/g",            "min": 0,    "max": 30},
    "tfg":  {"nombre": "TFG (CKD-EPI)",       "unidad": "mL/min/1.73m2",  "min": 90,   "max": 999},
}

# ======================== DATABASE MANAGER ========================
class DatabaseManager:

    @staticmethod
    def get_connection():
        if USE_POSTGRES:
            return psycopg2.connect(_DATABASE_URL)
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    @staticmethod
    def rows_to_dicts(cursor, rows):
        if USE_POSTGRES:
            cols = [d.name for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]
        return [dict(row) for row in rows]

    @staticmethod
    def row_to_dict(cursor, row):
        if USE_POSTGRES:
            cols = [d.name for d in cursor.description]
            return dict(zip(cols, row)) if row else None
        return dict(row) if row else None

    @staticmethod
    def fetchone_as_dict(cursor):
        row = cursor.fetchone()
        return DatabaseManager.row_to_dict(cursor, row)

    @staticmethod
    def fetchall_as_dicts(cursor):
        rows = cursor.fetchall()
        return DatabaseManager.rows_to_dicts(cursor, rows)

    @staticmethod
    def init_db():
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pacientes (
                    dni TEXT PRIMARY KEY,
                    paciente TEXT NOT NULL,
                    edad INTEGER,
                    dx TEXT,
                    cap TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seguimiento (
                    id_registro SERIAL PRIMARY KEY,
                    dni_p TEXT NOT NULL REFERENCES pacientes(dni),
                    fecha TEXT,
                    urea REAL,
                    crea REAL,
                    hb REAL,
                    k REAL,
                    na REAL,
                    acr REAL,
                    tfg REAL,
                    estadio TEXT,
                    asistio TEXT,
                    notas TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agenda (
                    id_cita SERIAL PRIMARY KEY,
                    dni_p TEXT NOT NULL REFERENCES pacientes(dni),
                    fecha_cita TEXT,
                    tipo TEXT,
                    estado TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pacientes (
                    dni TEXT PRIMARY KEY,
                    paciente TEXT NOT NULL,
                    edad INTEGER,
                    dx TEXT,
                    cap TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seguimiento (
                    id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni_p TEXT NOT NULL,
                    fecha TEXT,
                    urea REAL,
                    crea REAL,
                    hb REAL,
                    k REAL,
                    na REAL,
                    acr REAL,
                    tfg REAL,
                    estadio TEXT,
                    asistio TEXT,
                    notas TEXT,
                    FOREIGN KEY (dni_p) REFERENCES pacientes(dni)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agenda (
                    id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni_p TEXT NOT NULL,
                    fecha_cita TEXT,
                    tipo TEXT,
                    estado TEXT,
                    FOREIGN KEY (dni_p) REFERENCES pacientes(dni)
                )
            """)

        conn.commit()
        conn.close()


# Inicializar BD al startup
DatabaseManager.init_db()

# ======================== RUTAS API - PACIENTES ========================
@app.get("/api/pacientes")
def get_pacientes():
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes ORDER BY paciente ASC")
    result = DatabaseManager.fetchall_as_dicts(cursor)
    conn.close()
    return result


@app.get("/api/pacientes/{dni}")
def get_paciente(dni: str):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM pacientes WHERE dni = {PH}", (dni,))
    paciente = DatabaseManager.fetchone_as_dict(cursor)
    conn.close()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente


@app.post("/api/pacientes")
def crear_paciente(paciente: Paciente):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"INSERT INTO pacientes (dni, paciente, edad, dx, cap) VALUES ({PH},{PH},{PH},{PH},{PH})",
            (paciente.dni, paciente.nombre, paciente.edad, paciente.dx, paciente.cap),
        )
        conn.commit()
        conn.close()
        return {"mensaje": "Paciente creado", "dni": paciente.dni}
    except Exception as e:
        conn.close()
        # Tanto psycopg2 como sqlite3 lanzan IntegrityError para PK duplicada
        if "unique" in str(e).lower() or "UNIQUE" in str(e) or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="El DNI ya existe")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/pacientes/{dni}")
def actualizar_paciente(dni: str, paciente: Paciente):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE pacientes SET paciente={PH}, edad={PH}, dx={PH}, cap={PH} WHERE dni={PH}",
        (paciente.nombre, paciente.edad, paciente.dx, paciente.cap, dni),
    )
    conn.commit()
    conn.close()
    return {"mensaje": "Paciente actualizado"}


# ======================== RUTAS API - EVALUACIONES ========================
@app.get("/api/evaluaciones/{dni_p}")
def get_evaluaciones(dni_p: str):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM seguimiento WHERE dni_p = {PH} ORDER BY fecha DESC",
        (dni_p,),
    )
    result = DatabaseManager.fetchall_as_dicts(cursor)
    conn.close()
    return result


@app.post("/api/evaluaciones")
def crear_evaluacion(eval_data: Evaluacion):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""INSERT INTO seguimiento
                (dni_p, fecha, crea, urea, hb, k, na, acr, tfg, estadio, asistio, notas)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})""",
            (
                eval_data.dni_p, eval_data.fecha,
                eval_data.crea, eval_data.urea, eval_data.hb,
                eval_data.k, eval_data.na, eval_data.acr,
                eval_data.tfg, eval_data.estadio,
                eval_data.asistio, eval_data.notas,
            ),
        )
        conn.commit()
        conn.close()
        return {"mensaje": "Evaluación registrada"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))


# ======================== RUTAS API - ALERTAS ========================
@app.get("/api/alertas")
def get_alertas():
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT p.dni, p.paciente, p.edad, p.dx,
               (SELECT tfg FROM seguimiento
                WHERE dni_p = p.dni
                ORDER BY fecha DESC LIMIT 1) AS tfg_actual
        FROM pacientes p
        WHERE (SELECT tfg FROM seguimiento
               WHERE dni_p = p.dni
               ORDER BY fecha DESC LIMIT 1) < 30
        ORDER BY tfg_actual ASC
    """)
    result = DatabaseManager.fetchall_as_dicts(cursor)
    conn.close()
    return result


# ======================== RUTAS API - ESTADÍSTICAS ========================
@app.get("/api/estadisticas")
def get_estadisticas():
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM pacientes")
    total_pacientes = DatabaseManager.fetchone_as_dict(cursor)["total"]

    cursor.execute("SELECT dx, COUNT(*) AS cantidad FROM pacientes GROUP BY dx")
    por_estadio = {r["dx"]: r["cantidad"] for r in DatabaseManager.fetchall_as_dicts(cursor)}

    # strftime funciona igual en SQLite y Postgres para este formato
    if USE_POSTGRES:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM seguimiento WHERE TO_CHAR(fecha::date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')"
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM seguimiento WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')"
        )
    evaluaciones_mes = DatabaseManager.fetchone_as_dict(cursor)["total"]

    conn.close()
    return {
        "total_pacientes": total_pacientes,
        "por_estadio": por_estadio,
        "evaluaciones_mes": evaluaciones_mes,
    }


# ======================== RUTAS API - CITAS ========================
@app.get("/api/citas/{dni_p}")
def get_citas(dni_p: str):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM agenda WHERE dni_p = {PH} ORDER BY fecha_cita DESC",
        (dni_p,),
    )
    result = DatabaseManager.fetchall_as_dicts(cursor)
    conn.close()
    return result


@app.post("/api/citas")
def crear_cita(cita: Cita):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO agenda (dni_p, fecha_cita, tipo, estado) VALUES ({PH},{PH},{PH},{PH})",
        (cita.dni_p, cita.fecha_cita, cita.tipo, cita.estado),
    )
    conn.commit()
    conn.close()
    return {"mensaje": "Cita creada"}


# ======================== RUTAS API - PARÁMETROS ========================
@app.get("/api/parametros")
def get_parametros():
    return PARAMETROS_LABORATORIO


# ======================== RUTAS API - ADMINISTRACIÓN ========================
@app.post("/api/admin/limpiar-registros")
def limpiar_registros(data: dict):
    password = data.get("password", "")

    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="La variable de entorno ADMIN_PASSWORD no está configurada en el servidor.",
        )

    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM seguimiento")
    conn.commit()
    registros = cursor.rowcount
    conn.close()
    return {"mensaje": "Registros eliminados exitosamente", "registros_eliminados": registros}


# ======================== RUTAS API - DEBUG ========================
@app.get("/api/debug")
def debug_info():
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pacientes")
    pacientes_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM seguimiento")
    evaluaciones_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM agenda")
    citas_count = cursor.fetchone()[0]

    conn.close()
    return {
        "status": "ok",
        "db_backend": "postgres" if USE_POSTGRES else "sqlite",
        "pacientes": pacientes_count,
        "evaluaciones": evaluaciones_count,
        "citas": citas_count,
        "api_version": "3.0",
    }


# ======================== HEALTH CHECK ========================
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "SISTEMA ERCA API v3.0 - OK"}


# ======================== SERVIR HTML ========================
@app.get("/")
def serve_root():
    return FileResponse("index.html", media_type="text/html")

@app.get("/index.html")
def serve_html():
    return FileResponse("index.html", media_type="text/html")


# ======================== ARRANQUE LOCAL ========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"""
    ╔════════════════════════════════════════╗
    ║   SISTEMA ERCA - Backend FastAPI      ║
    ║   http://localhost:{port}              ║
    ╚════════════════════════════════════════╝
    BD: {"PostgreSQL" if USE_POSTGRES else f"SQLite ({SQLITE_PATH})"}
    """)
    uvicorn.run(app, host="0.0.0.0", port=port)
