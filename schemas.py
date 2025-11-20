from pydantic import BaseModel, EmailStr
from datetime import datetime

class MedicoBase(BaseModel):
    nombre: str
    especialidad: str
    precio: float
    duracion: int
    activo: bool = True

class MedicoCreate(MedicoBase):
    pass

class MedicoOut(MedicoBase):
    id: int

    model_config = {"from_attributes": True}


class TurnoBase(BaseModel):
    paciente_nombre: str
    paciente_email: EmailStr
    fecha_hora: datetime

class TurnoCreate(TurnoBase):
    medico_id: int

class TurnoOut(TurnoBase):
    id: int
    medico_id: int
    pagado: bool

    model_config = {"from_attributes": True}
