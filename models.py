from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    duracion_turno = Column(Integer, default=15)  # minutos por turno
    precio = Column(Integer, default=0)  # precio de la consulta

    turnos = relationship("Turno", back_populates="medico")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"))
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    estado = Column(String, default="pendiente")  # pendiente / pagado / cancelado
    preference_id = Column(String, nullable=True)  # ID MercadoPago

    medico = relationship("Medico", back_populates="turnos")
