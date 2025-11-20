from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import Base, engine, get_db
import models, schemas
import os
import mercadopago

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mercado Pago
mp = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


# ---------------- MÉDICOS ------------------

@app.post("/medicos/", response_model=schemas.MedicoOut)
def crear_medico(medico: schemas.MedicoCreate, db: Session = Depends(get_db), token: str = ""):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="No autorizado")

    db_med = models.Medico(**medico.model_dump())
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med


@app.get("/medicos/", response_model=list[schemas.MedicoOut])
def listar_medicos(db: Session = Depends(get_db)):
    return db.query(models.Medico).all()


# ---------------- TURNOS ------------------

@app.post("/turnos/", response_model=dict)
def crear_turno(turno: schemas.TurnoCreate, db: Session = Depends(get_db)):
    # validamos médico
    medico = db.query(models.Medico).filter(models.Medico.id == turno.medico_id).first()
    if not medico:
        raise HTTPException(404, "Médico no encontrado")

    # creamos turno en DB (sin pagar aún)
    db_turno = models.Turno(**turno.model_dump())
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)

    # creamos preferencia MP
    preference = {
        "items": [
            {
                "title": f"Consulta con {medico.nombre}",
                "quantity": 1,
                "unit_price": medico.precio
            }
        ],
        "back_urls": {
            "success": os.getenv("FRONTEND_URL") + "/success.html",
            "failure": os.getenv("FRONTEND_URL") + "/error.html",
            "pending": os.getenv("FRONTEND_URL") + "/pending.html"
        },
        "auto_return": "approved",
        "metadata": {"turno_id": db_turno.id}
    }

    result = mp.preference().create(preference)
    pay_url = result["response"]["init_point"]

    return {"payment_url": pay_url, "turno_id": db_turno.id}


@app.get("/turnos/{turno_id}", response_model=schemas.TurnoOut)
def obtener_turno(turno_id: int, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(404, "Turno no encontrado")
    return turno
