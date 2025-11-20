from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from database import Base


class AppointmentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    email = Column(String, nullable=False)
    precio = Column(Integer, nullable=False)          # ARS
    duracion_minutos = Column(Integer, nullable=False, default=30)

    appointments = relationship("Appointment", back_populates="doctor")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    fecha = Column(String, nullable=False)            # "2025-12-12"
    hora = Column(String, nullable=False)             # "11:15"
    motivo = Column(String, nullable=True)

    status = Column(
        SAEnum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.pending,
    )

    mp_preference_id = Column(String, nullable=True)
    mp_payment_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="appointments")
