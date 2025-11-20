import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
import schemas
import mercadopago
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediTurnos API")

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

FRONTEND = os.getenv("FRONTEND_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# MERCADOPAGO SDK
# ---------------------------------------------------------

MP_TOKEN = os.getenv("MP_ACCESS_TOKEN")
mp = mercadopago.SDK(MP_TOKEN) if MP_TOKEN else None

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "1234")


# ---------------------------------------------------------
# AUTH ADMIN
# ---------------------------------------------------------

def check_admin(token: str):
    if token != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Token inválido")


# ---------------------------------------------------------
# RUTAS
# ---------------------------------------------------------

@app.get("/")
def root():
    return {"status": "OK", "message": "MediTurnos API funcionando"}


# --------------------------
# MÉDICOS
# --------------------------

@app.post("/admin/medicos")
def crear_medico(
    medico: schemas.MedicoCreate,
    token: str,
    db: Session = Depends(get_db)
):
    check_admin(token)

    nuevo = models.Medico(
        nombre=medico.nombre,
        especialidad=medico.especialidad,
        duracion_turno=medico.duracion_turno,
        precio=medico.precio
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/medicos")
def listar_medicos(db: Session = Depends(get_db)):
    return db.query(models.Medico).all()


# --------------------------
# TURNOS
# --------------------------

@app.post("/turnos")
def crear_turno(turno: schemas.TurnoCreate, db: Session = Depends(get_db)):

    medico = db.query(models.Medico).filter(models.Medico.id == turno.medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    # crear turno pendiente
    nuevo_turno = models.Turno(
        medico_id=turno.medico_id,
        paciente_nombre=turno.paciente_nombre,
        paciente_email=turno.paciente_email,
        fecha_hora=datetime.fromisoformat(turno.fecha_hora),
        estado="pendiente",
    )
    db.add(nuevo_turno)
    db.commit()
    db.refresh(nuevo_turno)

    # MERCADOPAGO
    if not mp:
        raise HTTPException(status_code=500, detail="MercadoPago no configurado")

    preference_data = {
        "items": [
            {
                "title": f"Consulta médica con {medico.nombre}",
                "quantity": 1,
                "unit_price": medico.precio,
            }
        ],
        "external_reference": str(nuevo_turno.id),
        "back_urls": {
            "success": f"{FRONTEND}/success.html",
            "failure": f"{FRONTEND}/error.html",
            "pending": f"{FRONTEND}/pending.html",
        },
        "auto_return": "approved",
    }

    pref = mp.preference().create(preference_data)
    pref_id = pref["response"]["id"]

    nuevo_turno.preference_id = pref_id
    db.commit()

    return {"preference_id": pref_id}


@app.get("/turnos/{medico_id}")
def obtener_turnos(medico_id: int, db: Session = Depends(get_db)):
    return db.query(models.Turno).filter(models.Turno.medico_id == medico_id).all()


# --------------------------
# WEBHOOK MERCADOPAGO
# --------------------------

@app.post("/webhook/mp")
async def mp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()

    if "data" not in data or "id" not in data["data"]:
        return {"status": "ignored"}

    payment_id = data["data"]["id"]

    info = mp.payment().get(payment_id)
    status = info["response"]["status"]
    turno_id = info["response"]["external_reference"]

    turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()
    if turno:
        if status == "approved":
            turno.estado = "pagado"
            db.commit()

    return {"status": "ok"}
