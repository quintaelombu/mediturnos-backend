from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import Base, engine, get_db
import mercadopago

from models import Doctor, Turno
from schemas import DoctorCreate, Doctor, TurnoCreate, Turno
import os

app = FastAPI()

Base.metadata.create_all(bind=engine)

mp = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))


@app.get("/")
def root():
    return {"status": "backend ok"}


@app.post("/doctores", response_model=Doctor)
def crear_doctor(data: DoctorCreate, db: Session = Depends(get_db)):
    nuevo = Doctor(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/doctores")
def listar_doctores(db: Session = Depends(get_db)):
    return db.query(Doctor).all()


@app.post("/turnos", response_model=Turno)
def crear_turno(data: TurnoCreate, db: Session = Depends(get_db)):
    nuevo = Turno(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.post("/mp/preferencia")
def crear_preferencia(data: TurnoCreate):
    preference_data = {
        "items": [{
            "title": f"Consulta médica con ID doctor {data.doctor_id}",
            "quantity": 1,
            "currency_id": "ARS",
            "unit_price": 15000
        }],
        "payer": {
            "name": data.paciente_nombre,
            "email": data.paciente_email
        },
        "back_urls": {
            "success": "https://mediturnos-frontend-production.up.railway.app/success",
            "pending": "https://mediturnos-frontend-production.up.railway.app/pending",
            "failure": "https://mediturnos-frontend-production.up.railway.app/error"
        }
    }

    res = mp.preference().create(preference_data)
    return res
