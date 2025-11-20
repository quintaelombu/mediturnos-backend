from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import mercadopago

from models import Base, Medico, Turno
from schemas import MedicoCreate, TurnoCreate, MedicoOut, TurnoOut
from database import get_db

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("ERROR: Falta la variable DATABASE_URL en Railway")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
if not MP_ACCESS_TOKEN:
    raise Exception("ERROR: Falta MP_ACCESS_TOKEN en Railway")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "1234")


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------

app = FastAPI(title="Mediturnos Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------
# DEPENDENCIA DB
# ------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# ENDPOINTS — MÉDICOS
# ---------------------------------------------------------

@app.post("/admin/medicos", response_model=MedicoOut)
def crear_medico(m: MedicoCreate, db: Session = Depends(get_db), token: str = ""):

    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    nuevo = Medico(
        nombre=m.nombre,
        especialidad=m.especialidad,
        valor_consulta=m.valor_consulta,
        duracion_min=m.duracion_min
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/medicos", response_model=list[MedicoOut])
def listar_medicos(db: Session = Depends(get_db)):
    return db.query(Medico).all()


# ---------------------------------------------------------
# ENDPOINTS — TURNOS
# ---------------------------------------------------------

@app.post("/turnos", response_model=TurnoOut)
def crear_turno(t: TurnoCreate, db: Session = Depends(get_db)):

    medico = db.query(Medico).filter(Medico.id == t.medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="No existe ese médico")

    # verificar superposición
    inicio = t.inicio
    fin = t.inicio + medico.duracion_min * 60

    overlapping = (
        db.query(Turno)
        .filter(Turno.medico_id == medico.id)
        .filter(Turno.inicio < fin)
        .filter(Turno.fin > inicio)
        .first()
    )

    if overlapping:
        raise HTTPException(status_code=400, detail="El horario está ocupado")

    nuevo = Turno(
        nombre_paciente=t.nombre_paciente,
        email_paciente=t.email_paciente,
        medico_id=t.medico_id,
        inicio=inicio,
        fin=fin,
        pagado=False
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # crear preferencia Mercado Pago
    preference_data = {
        "items": [
            {
                "title": f"Consulta con {medico.nombre}",
                "quantity": 1,
                "unit_price": float(medico.valor_consulta)
            }
        ],
        "external_reference": str(nuevo.id),
        "back_urls": {
            "success": "https://mediturnos-frontend-production.up.railway.app/success.html",
            "failure": "https://mediturnos-frontend-production.up.railway.app/error.html",
            "pending": "https://mediturnos-frontend-production.up.railway.app/pending.html"
        }
    }

    pref = sdk.preference().create(preference_data)
    init_point = pref["response"]["init_point"]

    # adjuntar link
    nuevo.url_pago = init_point
    db.commit()
    db.refresh(nuevo)

    return nuevo


@app.get("/turnos/medico/{medico_id}", response_model=list[TurnoOut])
def turnos_por_medico(medico_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Turno)
        .filter(Turno.medico_id == medico_id)
        .order_by(Turno.inicio.asc())
        .all()
    )
