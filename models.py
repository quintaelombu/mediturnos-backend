from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    duracion = Column(Integer, nullable=False)  # minutos por turno
    activo = Column(Boolean, default=True)

    turnos = relationship("Turno", back_populates="medico")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"))
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    pagado = Column(Boolean, default=False)

    medico = relationship("Medico", back_populates="turnos")
