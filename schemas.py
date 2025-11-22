from pydantic import BaseModel

class MedicBase(BaseModel):
    name: str
    specialty: str
    price: int
    duration_minutes: int

class MedicCreate(MedicBase):
    pass

class MedicOut(MedicBase):
    id: int

    class Config:
        orm_mode = True
