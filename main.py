import os
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import mercadopago

from database import SessionLocal, engine
from models import Base, Doctor, Appointment, AppointmentStatus
import schemas


# ──────────────────────────────────────────────────────────────
# Configuración inicial
# ──────────────────────────────────────────────────────────────

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediTurnos Backend")

# CORS (por ahora abrimos todo; luego se puede restringir)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # luego podemos poner solo tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno importantes
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
if not MP_ACCESS_TOKEN:
    print("⚠️  MP_ACCESS_TOKEN no configurado. Mercado Pago no funcionará.")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "supersecreto")  # cámbialo en Railway


# ──────────────────────────────────────────────────────────────
# Dependencia de DB
# ──────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# Rutas simples
# ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "MediTurnos backend funcionando"}


# ──────────────────────────────────────────────────────────────
# DOCTORES
# ──────────────────────────────────────────────────────────────

@app.post(
    "/api/doctores",
    response_model=schemas.DoctorOut,
    tags=["doctores"],
)
def crear_doctor(
    doctor: schemas.DoctorCreate,
    admin_token: str = Query(..., description="Token de administrador"),
    db: Session = Depends(get_db),
):
    """
    Solo vos podés crear médicos usando un `admin_token` que
    configurás en la variable de entorno ADMIN_TOKEN.
    """
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token admin inválido")

    db_doctor = Doctor(
        nombre=doctor.nombre,
        especialidad=doctor.especialidad,
        email=doctor.email,
        precio=doctor.precio,
        duracion_minutos=doctor.duracion_minutos,
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor


@app.get(
    "/api/doctores",
    response_model=List[schemas.DoctorOut],
    tags=["doctores"],
)
def listar_doctores(
    especialidad: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lista de médicos. Si se pasa `especialidad`, filtra.
    """
    query = db.query(Doctor)
    if especialidad:
        query = query.filter(Doctor.especialidad == especialidad)
    return query.order_by(Doctor.nombre.asc()).all()


# ──────────────────────────────────────────────────────────────
# TURNOS + MERCADO PAGO
# ──────────────────────────────────────────────────────────────

@app.post(
    "/api/crear-preferencia",
    response_model=schemas.PreferenceResponse,
    tags=["turnos"],
)
def crear_preferencia(turno: schemas.TurnoCreate, db: Session = Depends(get_db)):
    """
    Crea un turno en estado 'pending' y genera la preferencia
    de pago en Mercado Pago. Devuelve `init_point` para redirigir.
    """

    if not MP_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Mercado Pago no está configurado (MP_ACCESS_TOKEN faltante).",
        )

    doctor = db.query(Doctor).filter(Doctor.id == turno.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    # Guardar turno en BD como pendiente
    db_turno = Appointment(
        doctor_id=doctor.id,
        paciente_nombre=turno.paciente_nombre,
        paciente_email=turno.paciente_email,
        fecha=turno.fecha,
        hora=turno.hora,
        motivo=turno.motivo,
        status=AppointmentStatus.pending,
    )
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)

    # Crear preferencia en MP
    preference_data = {
        "items": [
            {
                "id": str(db_turno.id),  # lo usamos luego en el webhook
                "title": f"Consulta {doctor.especialidad} - {doctor.nombre}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": doctor.precio,
            }
        ],
        "payer": {
            "name": turno.paciente_nombre,
            "email": turno.paciente_email,
        },
        "back_urls": {
            "success": f"{FRONTEND_URL}/success.html",
            "failure": f"{FRONTEND_URL}/error.html",
            "pending": f"{FRONTEND_URL}/pending.html",
        },
        "notification_url": f"{BASE_URL}/webhook",
        "auto_return": "approved",
    }

    pref = sdk.preference().create(preference_data)
    init_point = pref["response"]["init_point"]
    preference_id = pref["response"]["id"]

    db_turno.mp_preference_id = preference_id
    db.commit()

    return schemas.PreferenceResponse(init_point=init_point)


# Webhook de Mercado Pago
@app.post("/webhook", tags=["mercadopago"])
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Mercado Pago llama acá cuando cambia el estado del pago.
    Actualizamos el turno a 'paid' si el pago fue aprobado.
    """
    try:
        data = await request.json()
    except Exception:
        return {"message": "invalid json"}

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return {"message": "no payment id, ignored"}

    payment_info = sdk.payment().get(payment_id)["response"]

    status = payment_info.get("status")
    items = payment_info.get("additional_info", {}).get("items", [])
    if not items:
        return {"message": "no items in payment, ignored"}

    try:
        turno_id = int(items[0]["id"])
    except Exception:
        return {"message": "invalid turno id"}

    turno = db.query(Appointment).filter(Appointment.id == turno_id).first()
    if not turno:
        return {"message": "turno not found"}

    if status == "approved":
        turno.status = AppointmentStatus.paid
        turno.mp_payment_id = str(payment_id)
        db.commit()

    return {"message": "ok"}


# Lista de turnos (para panel de médicos)
@app.get(
    "/api/turnos",
    response_model=List[schemas.TurnoOut],
    tags=["turnos"],
)
def listar_turnos(
    solo_pagados: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(Appointment)
    if solo_pagados:
        query = query.filter(Appointment.status == AppointmentStatus.paid)
    return query.order_by(Appointment.id.desc()).all()
