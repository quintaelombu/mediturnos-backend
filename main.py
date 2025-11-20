from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, schemas
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import os

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mediturnos Backend",
)

# CORS
origins = [
    "*",  # si querés lo limitamos luego al dominio del frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# ENDPOINTS DOCTORES
# -----------------------------
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "123456")


@app.post("/admin/doctor", response_model=schemas.Doctor)
def crear_doctor(
    doctor: schemas.DoctorCreate,
    token: str,
    db: Session = Depends(get_db),
):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    nuevo = models.Doctor(**doctor.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/doctores", response_model=list[schemas.Doctor])
def listar_doctores(db: Session = Depends(get_db)):
    return db.query(models.Doctor).all()


@app.get("/doctores/{doctor_id}", response_model=schemas.Doctor)
def obtener_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="No encontrado")
    return doctor


# -----------------------------
# ENDPOINTS TURNOS
# -----------------------------

@app.post("/turnos", response_model=schemas.Turno)
def crear_turno(turno: schemas.TurnoCreate, db: Session = Depends(get_db)):

    # Verificar que no se superponga
    solapa = (
        db.query(models.Turno)
        .filter(
            models.Turno.doctor_id == turno.doctor_id,
            models.Turno.inicio < turno.fin,
            turno.inicio < models.Turno.fin,
        )
        .first()
    )

    if solapa:
        raise HTTPException(status_code=400, detail="El turno está ocupado")

    nuevo = models.Turno(**turno.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/turnos/{doctor_id}", response_model=list[schemas.Turno])
def turnos_del_doctor(doctor_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Turno)
        .filter(models.Turno.doctor_id == doctor_id)
        .order_by(models.Turno.inicio)
        .all()
    )
