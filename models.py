from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    duracion_turno = Column(Integer, nullable=False)  # minutos
    email = Column(String, nullable=False)

    turnos = relationship("Turno", back_populates="medico")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    fecha = Column(String, nullable=False)  # "2025-11-20"
    hora = Column(String, nullable=False)   # "17:00"
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    estado = Column(String, default="pendiente")  # pendiente / pagado / cancelado
    preference_id = Column(String, nullable=True)

    medico = relationship("Medico", back_populates="turnos")
