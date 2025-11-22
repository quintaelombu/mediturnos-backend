from sqlalchemy import Column, Integer, String
from database import Base

class Medic(Base):
    __tablename__ = "medics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
