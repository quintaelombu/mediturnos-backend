from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import Base, engine, get_db
import models, schemas
import mercadopago
import os

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI()

mp_access_token = os.getenv("MP_ACCESS_TOKEN")
mercado_pago = mercadopago.SDK(mp_access_token)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "SECRETO123")


@app.get("/")
def root():
    return {"status": "ok", "service": "Mediturnos Backend activo"}


# ----------------------
# ADMIN - CREAR MÉDICO
# ----------------------

@app.post("/medics", response_model=schemas.MedicOut)
def create_medic(
    medic: schemas.MedicCreate,
    token: str,
    db: Session = Depends(get_db)
):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    db_medic = models.Medic(**medic.dict())
    db.add(db_medic)
    db.commit()
    db.refresh(db_medic)
    return db_medic


# ----------------------
# LISTAR MÉDICOS
# ----------------------

@app.get("/medics", response_model=list[schemas.MedicOut])
def list_medics(db: Session = Depends(get_db)):
    return db.query(models.Medic).all()


# ----------------------
# GENERAR PREFERENCIA MP
# ----------------------

@app.post("/pay/{medic_id}")
def generate_payment(medic_id: int, db: Session = Depends(get_db)):
    medic = db.query(models.Medic).filter(models.Medic.id == medic_id).first()

    if not medic:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    preference_data = {
        "items": [
            {
                "title": f"Consulta con {medic.name}",
                "description": medic.specialty,
                "quantity": 1,
                "unit_price": medic.price,
                "currency_id": "ARS"
            }
        ],
        "back_urls": {
            "success": "https://mediturnos-frontend-production.up.railway.app/success",
            "failure": "https://mediturnos-frontend-production.up.railway.app/error",
            "pending": "https://mediturnos-frontend-production.up.railway.app/pending"
        },
        "auto_return": "approved",
    }

    pref = mercado_pago.preference().create(preference_data)
    return {"init_point": pref["response"]["init_point"]}


# ----------------------
# RAILWAY START
# ----------------------

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
