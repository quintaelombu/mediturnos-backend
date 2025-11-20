from pydantic import BaseModel, EmailStr
from datetime import datetime


class DoctorBase(BaseModel):
    nombre: str
    especialidad: str
    duracion_turno: int
    precio: int


class DoctorCreate(DoctorBase):
    pass


class Doctor(DoctorBase):
    id: int

    model_config = {"from_attributes": True}


class TurnoBase(BaseModel):
    paciente_nombre: str
    paciente_email: EmailStr
    doctor_id: int
    inicio: datetime
    fin: datetime


class TurnoCreate(TurnoBase):
    pass


class Turno(TurnoBase):
    id: int
    estado: str
    creado_en: datetime

    model_config = {"from_attributes": True}
