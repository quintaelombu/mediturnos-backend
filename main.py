import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

import mercadopago

from database import SessionLocal, engine
from models import Base, Appointment, Doctor

# ─────────────────────────────────────────────
# Inicializar base de datos
# ─────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────
# Configuración de entorno
# ─────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "").rstrip("/")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "supersecret")  # ponelo en Railway

if not MP_ACCESS_TOKEN:
    # Si falta el token, levantamos la app igual, pero avisamos en logs
    print("⚠️  MP_ACCESS_TOKEN NO configurado. Mercado Pago no va a funcionar.")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN) if MP_ACCESS_TOKEN else None

# ─────────────────────────────────────────────
# App FastAPI
# ─────────────────────────────────────────────
app = FastAPI(title="Mediturnos API")

# CORS (por ahora liberado, luego se puede ajustar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # si querés más seguro, poné solo tu FRONTEND_URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Dependencia de DB
# ─────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# MODELOS Pydantic (sin forward refs)
# ─────────────────────────────────────────────

class TurnoCreate(BaseModel):
    nombre: str
    email: EmailStr
    especialidad: str
    fecha: str    # yyyy-mm-dd (lo manejamos como string sencilla)
    hora: str     # hh:mm
    motivo: str
    doctor_id: Optional[int] = None  # opcional


class TurnoOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    especialidad: str
    fecha: str
    hora: str
    motivo: str
    status: str

    class Config:
        orm_mode = True


class DoctorCreate(BaseModel):
    nombre: str
    especialidad: str
    precio: int         # en ARS
    duracion_minutos: int
    activo: bool = True


class DoctorOut(BaseModel):
    id: int
    nombre: str
    especialidad: str
    precio: int
    duracion_minutos: int
    activo: bool

    class Config:
        orm_mode = True


# ─────────────────────────────────────────────
# RUTAS BÁSICAS
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "OK", "message": "Mediturnos backend funcionando"}


# ─────────────────────────────────────────────
# ENDPOINTS PARA MÉDICOS (administrador)
# ─────────────────────────────────────────────

@app.post("/api/doctores", response_model=DoctorOut)
def crear_doctor(
    doctor: DoctorCreate,
    db: Session = Depends(get_db),
    x_admin_token: str = Header(default="", alias="X-Admin-Token"),
):
    """
    Crear médico nuevo.
    SOLO si se envía el header:  X-Admin-Token: <ADMIN_TOKEN>
    """
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="No autorizado")

    db_doctor = Doctor(
        nombre=doctor.nombre,
        especialidad=doctor.especialidad,
        precio=doctor.precio,
        duracion_minutos=doctor.duracion_minutos,
        activo=doctor.activo,
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor


@app.get("/api/doctores", response_model=List[DoctorOut])
def listar_doctores(db: Session = Depends(get_db)):
    """
    Lista todos los médicos activos.
    """
    doctores = db.query(Doctor).filter(Doctor.activo == True).order_by(Doctor.nombre).all()
    return doctores


# ─────────────────────────────────────────────
# CREAR PREFERENCIA DE PAGO + TURNO
# ─────────────────────────────────────────────

@app.post("/api/crear-preferencia")
def crear_preferencia(turno: TurnoCreate, db: Session = Depends(get_db)):
    """
    1) Crea un turno en BD con status='pending'
    2) Crea una preferencia de Mercado Pago
    3) Devuelve el init_point para redirigir al pago
    """

    if not sdk:
        raise HTTPException(
            status_code=500,
            detail="Mercado Pago no configurado (falta MP_ACCESS_TOKEN)",
        )

    # Buscar doctor si viene doctor_id
    price = 40000  # valor por defecto
    if turno.doctor_id:
        doctor = db.query(Doctor).filter(Doctor.id == turno.doctor_id, Doctor.activo == True).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Médico no encontrado")
        price = doctor.precio

    # 1) Guardar turno en BD
    db_turno = Appointment(
        nombre=turno.nombre,
        email=turno.email,
        especialidad=turno.especialidad,
        fecha=turno.fecha,
        hora=turno.hora,
        motivo=turno.motivo,
        status="pending",
        doctor_id=turno.doctor_id,
    )
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)

    # 2) Crear preferencia en Mercado Pago
    preference_data = {
        "items": [
            {
                "id": str(db_turno.id),
                "title": f"Consulta {turno.especialidad}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": price,
            }
        ],
        "payer": {
            "name": turno.nombre,
            "email": turno.email,
        },
        "back_urls": {
            "success": f"{FRONTEND_URL}/success.html",
            "failure": f"{FRONTEND_URL}/error.html",
            "pending": f"{FRONTEND_URL}/pending.html",
        },
        "auto_return": "approved",
        "notification_url": os.getenv("BASE_URL", "").rstrip("/") + "/webhook",
        "external_reference": str(db_turno.id),
    }

    try:
        pref = sdk.preference().create(preference_data)
    except Exception as e:
        # Si falla Mercado Pago, borramos el turno pendiente
        db.delete(db_turno)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error al crear preferencia: {e}")

    init_point = pref["response"].get("init_point")
    if not init_point:
        raise HTTPException(status_code=500, detail="No se pudo obtener init_point de Mercado Pago")

    return {"init_point": init_point}


# ─────────────────────────────────────────────
# WEBHOOK DE MERCADO PAGO
# ─────────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Mercado Pago envía acá las notificaciones.
    Solo marcamos el turno como 'paid' si el pago está 'approved'.
    """

    if not sdk:
        # Si no hay SDK configurado, ignoramos silenciosamente
        return {"message": "mp not configured"}

    try:
        data = await request.json()
    except Exception:
        return {"message": "invalid json"}

    # MP puede enviar distintos tipos de mensaje; filtramos los de pago
    if "data" not in data or "id" not in data["data"]:
        return {"message": "ignored"}

    payment_id = data["data"]["id"]

    try:
        payment_info = sdk.payment().get(payment_id)["response"]
    except Exception as e:
        print("Error obteniendo pago MP:", e)
        return {"message": "error getting payment"}

    if payment_info.get("status") != "approved":
        return {"message": "payment not approved"}

    # Recuperamos id de turno (lo guardamos como external_reference)
    turno_id_str = payment_info.get("external_reference")
    if not turno_id_str:
        # fallback: intentar por additional_info.items[0].id
        try:
            turno_id_str = payment_info["additional_info"]["items"][0]["id"]
        except Exception:
            return {"message": "turno id not found"}

    try:
        turno_id = int(turno_id_str)
    except ValueError:
        return {"message": "invalid turno id"}

    turno = db.query(Appointment).filter(Appointment.id == turno_id).first()
    if not turno:
        return {"message": "appointment not found"}

    turno.status = "paid"
    db.commit()

    return {"message": "ok"}


# ─────────────────────────────────────────────
# LISTADO DE TURNOS PARA PANEL DE MÉDICOS
# ─────────────────────────────────────────────

@app.get("/api/turnos", response_model=List[TurnoOut])
def listar_turnos(
    solo_pagados: bool = True,
    db: Session = Depends(get_db),
):
    """
    Lista turnos.
    - solo_pagados=true (default): solo status='paid'
    - solo_pagados=false: todos
    """
    query = db.query(Appointment)
    if solo_pagados:
        query = query.filter(Appointment.status == "paid")

    turnos = query.order_by(Appointment.id.desc()).all()
    return turnos
