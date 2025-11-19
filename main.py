import os
from datetime import datetime, date, time

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import Doctor, Appointment

import mercadopago

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

# Mercado Pago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
if not MP_ACCESS_TOKEN:
    print("⚠️ MP_ACCESS_TOKEN NO configurado (sin pagos reales).")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN) if MP_ACCESS_TOKEN else None

# FRONTEND_URL (para back_urls si querés luego)
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

# Admin “secreto” simple para crear médicos (luego se mejora)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "supersecreto")


# ─────────────────────────────
# DB
# ─────────────────────────────

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────
# SCHEMAS (Pydantic)
# ─────────────────────────────

class DoctorCreate(BaseModel):
    nombre: str
    especialidad: str
    email: EmailStr | None = None
    precio: int      # ARS
    duracion_min: int  # minutos


class DoctorOut(BaseModel):
    id: int
    nombre: str
    especialidad: str
    email: EmailStr | None
    precio: int
    duracion_min: int

    class Config:
        orm_mode = True


class TurnoCreate(BaseModel):
    paciente_nombre: str
    paciente_email: EmailStr
    motivo: str | None = None
    fecha: str          # "2025-01-20"
    hora: str           # "17:00"
    doctor_id: int


class TurnoOut(BaseModel):
    id: int
    paciente_nombre: str
    paciente_email: EmailStr
    motivo: str | None
    fecha: date
    hora: time
    estado: str
    doctor_id: int

    class Config:
        orm_mode = True


# ─────────────────────────────
# APP
# ─────────────────────────────

app = FastAPI(title="Mediturnos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # después lo afinamos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────
# RUTAS BÁSICAS
# ─────────────────────────────

@app.get("/")
def root():
    return {"status": "OK", "service": "Mediturnos backend"}


# ─────────────────────────────
# MÉDICOS (solo vos los podés crear)
# ─────────────────────────────

@app.post("/api/doctores", response_model=DoctorOut)
def crear_doctor(
    doctor: DoctorCreate,
    admin_token: str,
    db: Session = Depends(get_db),
):
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="No autorizado")

    nuevo = Doctor(
        nombre=doctor.nombre,
        especialidad=doctor.especialidad,
        email=doctor.email,
        precio=doctor.precio,
        duracion_min=doctor.duracion_min,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/api/doctores", response_model=list[DoctorOut])
def listar_doctores(db: Session = Depends(get_db)):
    return db.query(Doctor).order_by(Doctor.nombre.asc()).all()


# ─────────────────────────────
# CREAR TURNO + PREFERENCIA MP
# ─────────────────────────────

@app.post("/api/turnos/crear-preferencia")
def crear_preferencia(turno: TurnoCreate, db: Session = Depends(get_db)):
    """
    1) Crea el turno en BD como 'pending'
    2) Crea preferencia en MP (si hay MP_ACCESS_TOKEN)
    3) Devuelve init_point para redirigir al checkout
    """
    doctor = db.query(Doctor).filter(Doctor.id == turno.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    # parsear fecha y hora
    try:
        f = date.fromisoformat(turno.fecha)
        h = time.fromisoformat(turno.hora)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha u hora inválido")

    # crear turno pending
    nuevo = Appointment(
        paciente_nombre=turno.paciente_nombre,
        paciente_email=turno.paciente_email,
        motivo=turno.motivo or "",
        fecha=f,
        hora=h,
        estado="pending",
        doctor_id=doctor.id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # si no tenemos MP configurado, devolvemos “falso pago”
    if not sdk:
        # modo pruebas sin Mercado Pago real
        return {
            "init_point": None,
            "fake": True,
            "message": "MP no configurado. Turno creado en estado 'pending'.",
            "turno_id": nuevo.id,
        }

    # preferencia real
    preference_data = {
        "items": [
            {
                "id": str(nuevo.id),
                "title": f"Consulta con {doctor.nombre} ({doctor.especialidad})",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(doctor.precio),
            }
        ],
        "payer": {
            "name": turno.paciente_nombre,
            "email": turno.paciente_email,
        },
        "back_urls": {
            "success": FRONTEND_URL or "",
            "failure": FRONTEND_URL or "",
            "pending": FRONTEND_URL or "",
        },
        "auto_return": "approved",
        "metadata": {
            "turno_id": nuevo.id,
            "doctor_id": doctor.id,
        },
        # notification_url la configuramos cuando tengas dominio estable
    }

    try:
        pref = sdk.preference().create(preference_data)
        init_point = pref["response"].get("init_point")
        preference_id = pref["response"].get("id")

        nuevo.mp_preference_id = preference_id
        db.commit()

        return {
            "init_point": init_point,
            "turno_id": nuevo.id,
        }
    except Exception as e:
        # si falla MP, dejamos el turno pending pero avisamos
        raise HTTPException(status_code=500, detail=f"Error MP: {str(e)}")


# ─────────────────────────────
# LISTAR TURNOS (para panel médico)
# ─────────────────────────────

@app.get("/api/turnos", response_model=list[TurnoOut])
def listar_turnos(
    doctor_id: int | None = None,
    fecha: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Appointment)

    if doctor_id is not None:
        q = q.filter(Appointment.doctor_id == doctor_id)

    if fecha is not None:
        try:
            f = date.fromisoformat(fecha)
            q = q.filter(Appointment.fecha == f)
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida")

    q = q.order_by(Appointment.fecha.asc(), Appointment.hora.asc())
    return q.all()


# ─────────────────────────────
# WEBHOOK MP (cuando paguen)
# ─────────────────────────────

@app.post("/webhook/mp")
async def webhook_mp(request: Request, db: Session = Depends(get_db)):
    """
    Cuando Mercado Pago notifica un pago, marcamos el turno como 'paid'.
    Esto se termina de configurar cuando tengamos dominio público estable.
    """
    if not sdk:
        return {"message": "MP no configurado"}

    body = await request.json()

    if body.get("type") != "payment":
        return {"message": "ignored"}

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        return {"message": "no payment id"}

    payment = sdk.payment().get(payment_id)
    p = payment.get("response", {})

    if p.get("status") == "approved":
        # recuperamos turno_id de metadata
        turno_id = p.get("metadata", {}).get("turno_id")
        if turno_id:
            turno = db.query(Appointment).filter(Appointment.id == turno_id).first()
            if turno:
                turno.estado = "paid"
                turno.mp_payment_id = str(payment_id)
                db.commit()

    return {"message": "ok"}
