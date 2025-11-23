import os
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import Base, engine, get_db
import mercadopago

from models import Doctor, Turno
from schemas import DoctorCreate, Doctor as DoctorSchema, TurnoCreate, Turno as TurnoSchema

app = FastAPI()

Base.metadata.create_all(bind=engine)

mp = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

@app.get("/")
def root():
    return {"status": "backend ok"}
