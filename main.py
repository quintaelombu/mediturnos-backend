from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import schemas
import mercadopago
import os

# Crear tablas si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mediturnos Backend")

# CORS
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión DB por request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================================
#         MÉDICOS
# ================================
@app.post("/doctores", response_model=schemas.DoctorOut)
def crear_doctor(data: schemas.DoctorCreate, db: Session = Depends(get_db)):

    admin_token = os.getenv("ADMIN_TOKEN")

    if data.admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Token inválido")

    nuevo = models.Doctor(
        nombre=data.nombre,
        apellido=data.apellido,
        especialidad=data.especialidad,
        duracion_turno=data.duracion_turno,
        precio=data.precio,
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return nuevo


@app.get("/doctores", response_model=list[schemas.DoctorOut])
def listar_doctores(db: Session = Depends(get_db)):
    return db.query(models.Doctor).all()


# ================================
#         TURNOS
# ================================
@app.post("/turnos", response_model=schemas.TurnoOut)
def crear_turno(data: schemas.TurnoCreate, db: Session = Depends(get_db)):

    doctor = db.query(models.Doctor).filter(models.Doctor.id == data.doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    turno = models.Turno(
        doctor_id=data.doctor_id,
        paciente_nombre=data.paciente_nombre,
        paciente_email=data.paciente_email,
        fecha=data.fecha,
        hora=data.hora,
        estado="pendiente",
    )

    db.add(turno)
    db.commit()
    db.refresh(turno)

    return turno


@app.get("/turnos/{doctor_id}")
def obtener_turnos(doctor_id: int, db: Session = Depends(get_db)):
    turnos = (
        db.query(models.Turno)
        .filter(models.Turno.doctor_id == doctor_id)
        .order_by(models.Turno.fecha, models.Turno.hora)
        .all()
    )
    return turnos


# ================================
#   MERCADO PAGO — PREFERENCIA
# ================================
@app.post("/mp/preferencia")
def crear_preferencia(data: schemas.PagoCreate, db: Session = Depends(get_db)):

    doctor = db.query(models.Doctor).filter(models.Doctor.id == data.doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

    if not ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Falta MP_ACCESS_TOKEN")

    sdk = mercadopago.SDK(ACCESS_TOKEN)

    preference_data = {
        "items": [
            {
                "title": f"Consulta con Dr. {doctor.apellido}",
                "quantity": 1,
                "unit_price": float(doctor.precio),
            }
        ],
        "payer": {"email": data.paciente_email},
        "back_urls": {
            "success": data.success_url,
            "failure": data.failure_url,
            "pending": data.pending_url,
        },
        "auto_return": "approved",
    }

    result = sdk.preference().create(preference_data)
    return result["response"]
