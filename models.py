from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Doctor(Base):
    __tablename__ = "doctores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    email = Column(String, nullable=True)
    precio = Column(Integer, nullable=False)        # ARS
    duracion_min = Column(Integer, nullable=False)  # minutos (15, 30, 45, etc.)

    turnos = relationship("Appointment", back_populates="doctor")


class Appointment(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    motivo = Column(String, nullable=True)

    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)

    estado = Column(String, nullable=False, default="pending")  # pending / paid / canceled

    doctor_id = Column(Integer, ForeignKey("doctores.id"), nullable=False)
    mp_preference_id = Column(String, nullable=True)
    mp_payment_id = Column(String, nullable=True)

    doctor = relationship("Doctor", back_populates="turnos")
