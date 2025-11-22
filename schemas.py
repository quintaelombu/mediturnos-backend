from pydantic import BaseModel
from typing import Optional


class DoctorBase(BaseModel):
    nombre: str
    especialidad: str
    duracion_turno: int
    precio: int


class DoctorCreate(DoctorBase):
    pass


class Doctor(DoctorBase):
    id: int

    class Config:
        orm_mode = True


class TurnoBase(BaseModel):
    doctor_id: int
    paciente_nombre: str
    paciente_email: str
    fecha: str  # formato YYYY-MM-DD
    hora: str   # formato HH:MM


class TurnoCreate(TurnoBase):
    pass


class Turno(TurnoBase):
    id: int

    class Config:
        orm_mode = True
