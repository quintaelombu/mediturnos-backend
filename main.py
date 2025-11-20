import os
from datetime import date, time, datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import Doctor, Appointment

# ─────────────────────────────────────
# Inicializar BD (crear tablas)
# ─────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────
# App FastAPI
# ─────────────────────────────────────
app = FastAPI(title="Mediturnos API")

FRONTEND_URL = os.getenv("FRONTEND_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────
# Dependencia de sesión de BD
# ─────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────
# Esquemas Pydantic (sólo para request)
# ─────────────────────────────────────
class TurnoCreate(BaseModel):
    paciente_nombre: str
    paciente_email: EmailStr
    medico_id: int
    fecha: str          # "2025-11-20"
    hora: str           # "17:00"
    motivo: str | None = None

class DoctorCreate(BaseModel):
    nombre: str
    especialidad: str
    duracion_minutos: int = 30
    precio_ars: int = 40000

# ─────────────────────────────────────
# Rutas básicas
# ─────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Mediturnos backend activo"}

# ─────────────────────────────────────
# 1) Listar especialidades
# ─────────────────────────────────────
@app.get("/api/especialidades")
def listar_especialidades(db: Session = Depends(get_db)):
    filas = db.query(Doctor.especialidad).distinct().all()
    # filas viene como lista de tuplas: [("Infectología",), ("Pediatría",)...]
    return [f[0] for f in filas]

# ─────────────────────────────────────
# 2) Listar médicos (opcionalmente filtrados por especialidad)
# ─────────────────────────────────────
@app.get("/api/medicos")
def listar_medicos(especialidad: str | None = None,
                   db: Session = Depends(get_db)):
    q = db.query(Doctor)
    if especialidad:
        q = q.filter(Doctor.especialidad == especialidad)
    medicos = q.order_by(Doctor.nombre).all()

    return [
        {
            "id": m.id,
            "nombre": m.nombre,
            "especialidad": m.especialidad,
            "duracion_minutos": m.duracion_minutos,
            "precio_ars": m.precio_ars,
        }
        for m in medicos
    ]

# ─────────────────────────────────────
# 3) Agenda de un médico en un día
# ─────────────────────────────────────
@app.get("/api/agenda")
def agenda_medico(medico_id: int,
                  fecha: str,
                  db: Session = Depends(get_db)):
    """
    Devuelve slots de ese día para ese médico.
    Formato respuesta: [{ "hora": "09:00", "disponible": True }, ...]
    """

    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

    medico = db.query(Doctor).get(medico_id)
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    # Por ahora horario fijo 09:00–20:00. Luego lo volvemos configurable.
    inicio_jornada = time(9, 0)
    fin_jornada = time(20, 0)
    paso = timedelta(minutes=medico.duracion_minutos)

    # Obtener turnos ya reservados de ese día
    turnos = db.query(Appointment).filter(
        Appointment.medico_id == medico_id,
        Appointment.fecha == dia,
        Appointment.estado != "cancelado"
    ).all()

    ocupados = {(t.hora_inicio.hour, t.hora_inicio.minute) for t in turnos}

    slots = []
    current_dt = datetime.combine(dia, inicio_jornada)
    end_dt = datetime.combine(dia, fin_jornada)

    while current_dt <= end_dt:
        h = current_dt.time()
        key = (h.hour, h.minute)
        libre = key not in ocupados
        slots.append({
            "hora": h.strftime("%H:%M"),
            "disponible": libre
        })
        current_dt += paso

    return {
        "medico_id": medico_id,
        "fecha": fecha,
        "duracion_minutos": medico.duracion_minutos,
        "slots": slots,
    }

# ─────────────────────────────────────
# 4) Crear turno (sin pago todavía)
# ─────────────────────────────────────
@app.post("/api/turnos")
def crear_turno(body: TurnoCreate,
                db: Session = Depends(get_db)):
    # Parsear fecha y hora
    try:
        dia = date.fromisoformat(body.fecha)
        hora = datetime.strptime(body.hora, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha u hora inválidas")

    medico = db.query(Doctor).get(body.medico_id)
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    # Verificar que el slot esté libre
    existente = db.query(Appointment).filter(
        Appointment.medico_id == body.medico_id,
        Appointment.fecha == dia,
        Appointment.hora_inicio == hora,
        Appointment.estado != "cancelado"
    ).first()

    if existente:
        raise HTTPException(status_code=409, detail="Ese horario ya está ocupado")

    nuevo = Appointment(
        paciente_nombre=body.paciente_nombre,
        paciente_email=body.paciente_email,
        medico_id=body.medico_id,
        fecha=dia,
        hora_inicio=hora,
        duracion_minutos=medico.duracion_minutos,
        motivo=body.motivo or "",
        estado="reservado",
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Por ahora sólo devolvemos datos del turno; luego le sumamos Mercado Pago
    return {
        "ok": True,
        "turno_id": nuevo.id,
        "medico_id": medico.id,
        "fecha": body.fecha,
        "hora": body.hora,
    }

# ─────────────────────────────────────
# 5) Endpoint sencillo para listar turnos (panel médico futuro)
# ─────────────────────────────────────
@app.get("/api/turnos")
def listar_turnos(medico_id: int | None = None,
                  db: Session = Depends(get_db)):
    q = db.query(Appointment)
    if medico_id is not None:
        q = q.filter(Appointment.medico_id == medico_id)
    turnos = q.order_by(Appointment.fecha, Appointment.hora_inicio).all()

    return [
        {
            "id": t.id,
            "paciente_nombre": t.paciente_nombre,
            "paciente_email": t.paciente_email,
            "medico_id": t.medico_id,
            "fecha": t.fecha.isoformat(),
            "hora": t.hora_inicio.strftime("%H:%M"),
            "estado": t.estado,
            "motivo": t.motivo,
        }
        for t in turnos
    ]

# ─────────────────────────────────────
# 6) Endpoint para crear médicos (por ahora sin auth)
#    Más adelante lo protegemos con contraseña.
# ─────────────────────────────────────
@app.post("/api/medicos")
def crear_medico(body: DoctorCreate,
                 db: Session = Depends(get_db)):
    medico = Doctor(
        nombre=body.nombre,
        especialidad=body.especialidad,
        duracion_minutos=body.duracion_minutos,
        precio_ars=body.precio_ars,
    )
    db.add(medico)
    db.commit()
    db.refresh(medico)
    return {
        "id": medico.id,
        "nombre": medico.nombre,
        "especialidad": medico.especialidad,
        "duracion_minutos": medico.duracion_minutos,
        "precio_ars": medico.precio_ars,
    }
