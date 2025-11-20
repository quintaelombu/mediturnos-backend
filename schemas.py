from pydantic import BaseModel, EmailStr
from datetime import datetime


class DoctorBase(BaseModel):
    nombre: str
    apellido: str
    especialidad: str
    duracion_minutos: int
    email: EmailStr | None = None


class DoctorCreate(DoctorBase):
    pass


class DoctorOut(DoctorBase):
    id: int

    class Config:
        orm_mode = True


class TurnoBase(BaseModel):
    paciente_nombre: str
    paciente_email: EmailStr
    doctor_id: int
    fecha_hora: datetime


class TurnoCreate(TurnoBase):
    pass


class TurnoOut(TurnoBase):
    id: int
    estado: str
    mp_payment_id: str | None
    mp_status: str | None

    class Config:
        orm_mode = True
