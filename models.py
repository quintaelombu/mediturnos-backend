from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Doctor(Base):
    __tablename__ = "doctores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    duracion_turno = Column(Integer, nullable=False)
    precio = Column(Integer, nullable=False)

    turnos = relationship("Turno", back_populates="doctor")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctores.id"))
    paciente_nombre = Column(String, nullable=False)
    paciente_email = Column(String, nullable=False)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)

    doctor = relationship("Doctor", back_populates="turnos")
