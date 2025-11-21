import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

import mercadopago

# ─────────────────────────────────────────────
# Configuración Mercado Pago
# ─────────────────────────────────────────────
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
sdk = mercadopago.SDK(MP_ACCESS_TOKEN) if MP_ACCESS_TOKEN else None

# ─────────────────────────────────────────────
# App FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="Mediturnos Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # luego lo afinamos si querés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Modelo de datos que viene del frontend
# ─────────────────────────────────────────────
class Turno(BaseModel):
    nombre: str
    email: EmailStr
    especialidad: str
    fecha: str   # "2025-03-10"
    hora: str    # "15:30"
    motivo: str


# ─────────────────────────────────────────────
# Endpoint raíz (para probar en el navegador)
# ─────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "mediturnos-backend",
        "version": "1.0.0",
    }


# ─────────────────────────────────────────────
# Crear preferencia de pago en Mercado Pago
# ─────────────────────────────────────────────
@app.post("/api/crear-preferencia")
def crear_preferencia(turno: Turno):
    if sdk is None:
        raise HTTPException(
            status_code=500,
            detail="MP_ACCESS_TOKEN no está configurado en el servidor."
        )

    # Precios distintos por especialidad
    precios = {
        "Pediatría": 10000,
        "Infectología pediátrica": 40000,
        "Dermatología": 15000,
    }
    price = precios.get(turno.especialidad, 20000)

    preference_data = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "title": f"Consulta {turno.especialidad}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(price),
            }
        ],
        "payer": {
            "name": turno.nombre,
            "email": turno.email,
        },
        "back_urls": {
            "success": "https://mediturnos-frontend-production.up.railway.app/success.html",
            "failure": "https://mediturnos-frontend-production.up.railway.app/error.html",
            "pending": "https://mediturnos-frontend-production.up.railway.app/pending.html",
        },
        "auto_return": "approved",
    }

    try:
        pref = sdk.preference().create(preference_data)
        init_point = pref["response"].get("init_point")

        if not init_point:
            raise HTTPException(
                status_code=500,
                detail="Mercado Pago no devolvió init_point."
            )

        return {"init_point": init_point}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error MP: {str(e)}")
