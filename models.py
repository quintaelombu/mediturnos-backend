from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    duracion_turno = Column(Integer, nullable=False)  # minutos
    precio = Column(Integer, nullable=False)


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    doctor_id = Column(Integer, nullable=False)
    inicio = Column(DateTime, nullable=False)
    fin = Column(DateTime, nullable=False)
    estado = Column(String, default="pendiente")  
    creado_en = Column(DateTime, default=datetime.utcnow)
