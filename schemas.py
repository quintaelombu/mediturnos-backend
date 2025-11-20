from enum import Enum as PyEnum
from pydantic import BaseModel, ConfigDict, EmailStr


class AppointmentStatus(str, PyEnum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"


# ───────────── DOCTORES ─────────────

class DoctorBase(BaseModel):
    nombre: str
    especialidad: str
    email: EmailStr
    precio: int
    duracion_minutos: int = 30


class DoctorCreate(DoctorBase):
    pass


class DoctorOut(DoctorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ───────────── TURNOS / APPOINTMENTS ─────────────

class TurnoBase(BaseModel):
    doctor_id: int
    paciente_nombre: str
    paciente_email: EmailStr
    fecha: str
    hora: str
    motivo: str | None = None


class TurnoCreate(TurnoBase):
    pass


class TurnoOut(TurnoBase):
    id: int
    status: AppointmentStatus
    mp_preference_id: str | None = None
    mp_payment_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PreferenceResponse(BaseModel):
    init_point: str
