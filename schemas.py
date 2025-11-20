from pydantic import BaseModel, EmailStr

class MedicoBase(BaseModel):
    nombre: str
    especialidad: str
    duracion_turno: int
    email: EmailStr


class MedicoCreate(MedicoBase):
    pass


class MedicoOut(MedicoBase):
    id: int
    class Config:
        from_attributes = True


class TurnoBase(BaseModel):
    medico_id: int
    fecha: str
    hora: str
    paciente_nombre: str
    paciente_email: EmailStr


class TurnoCreate(TurnoBase):
    pass


class TurnoOut(TurnoBase):
    id: int
    estado: str
    preference_id: str | None = None
    
    class Config:
        from_attributes = True
