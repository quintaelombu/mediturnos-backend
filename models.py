from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    duracion_minutos = Column(Integer, default=15)
    email = Column(String, nullable=True)

    turnos = relationship("Turno", back_populates="doctor")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    fecha_hora = Column(DateTime, nullable=False)
    estado = Column(String, default="pendiente")
    mp_payment_id = Column(String, nullable=True)
    mp_status = Column(String, nullable=True)

    doctor = relationship("Doctor", back_populates="turnos")
