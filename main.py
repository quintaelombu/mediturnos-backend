from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

app = FastAPI()

# CORS para que el frontend lo use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- BASE DE DATOS SQLite ----------
def init_db():
    conn = sqlite3.connect("mediturnos.db")
    c = conn.cursor()

    # Tabla médicos
    c.execute("""
    CREATE TABLE IF NOT EXISTS doctores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        especialidad TEXT NOT NULL
    )
    """)

    # Tabla turnos
    c.execute("""
    CREATE TABLE IF NOT EXISTS turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        paciente TEXT NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# --------- MODELOS ---------
class DoctorIn(BaseModel):
    nombre: str
    especialidad: str

class TurnoIn(BaseModel):
    doctor_id: int
    paciente: str
    fecha: str
    hora: str

@app.get("/")
def root():
    return {"status": "backend ok"}

# --------- ENDPOINTS ---------

@app.post("/doctores")
def crear_doctor(data: DoctorIn):
    conn = sqlite3.connect("mediturnos.db")
    c = conn.cursor()

    c.execute("INSERT INTO doctores (nombre, especialidad) VALUES (?, ?)",
              (data.nombre, data.especialidad))

    conn.commit()
    conn.close()
    return {"message": "doctor creado"}

@app.get("/doctores")
def listar_doctores():
    conn = sqlite3.connect("mediturnos.db")
    c = conn.cursor()
    c.execute("SELECT * FROM doctores")
    result = c.fetchall()
    conn.close()

    lista = []
    for r in result:
        lista.append({
            "id": r[0],
            "nombre": r[1],
            "especialidad": r[2]
        })

    return lista

@app.post("/turnos")
def crear_turno(data: TurnoIn):
    conn = sqlite3.connect("mediturnos.db")
    c = conn.cursor()

    c.execute("INSERT INTO turnos (doctor_id, paciente, fecha, hora) VALUES (?, ?, ?, ?)",
              (data.doctor_id, data.paciente, data.fecha, data.hora))

    conn.commit()
    conn.close()
    return {"message": "turno creado"}

@app.get("/turnos")
def listar_turnos():
    conn = sqlite3.connect("mediturnos.db")
    c = conn.cursor()
    c.execute("SELECT * FROM turnos")
    result = c.fetchall()
    conn.close()

    lista = []
    for r in result:
        lista.append({
            "id": r[0],
            "doctor_id": r[1],
            "paciente": r[2],
            "fecha": r[3],
            "hora": r[4]
        })

    return lista
