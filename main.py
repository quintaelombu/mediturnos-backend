import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import mercadopago

# ─────────────────────────────────────────
# VARIABLES DE ENTORNO
# ─────────────────────────────────────────
BACKEND_URL = os.getenv(
    "BASE_URL",
    "https://mediturnos-backend-production.up.railway.app"
).rstrip("/")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://mediturnos-frontend-production.up.railway.app"
).rstrip("/")

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")

if not MP_ACCESS_TOKEN:
    # No rompemos la app, pero avisamos en logs
    print("⚠️ MP_ACCESS_TOKEN NO CONFIGURADO")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ─────────────────────────────────────────
# APP FASTAPI
# ─────────────────────────────────────────
app = FastAPI(title="Mediturnos Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # si quieres, luego lo limitamos al FRONTEND_URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────
class Turno(BaseModel):
    nombre: str
    email: EmailStr
    especialidad: str
    fecha: str
    hora: str
    motivo: str


# ─────────────────────────────────────────
# ENDPOINTS BÁSICOS
# ─────────────────────────────────────────
@app.get("/")
def root():
    """Health check simple."""
    return {"status": "OK", "service": "mediturnos-backend"}


@app.get("/health")
def health():
    return {"ok": True}


# ─────────────────────────────────────────
# CREAR PREFERENCIA DE MERCADO PAGO
# ─────────────────────────────────────────
@app.post("/api/crear-preferencia")
def crear_preferencia(turno: Turno):
    if not MP_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="MP_ACCESS_TOKEN no configurado en el backend",
        )

    # Precios de prueba por especialidad
    precios = {
        "Pediatría": 1000.0,
        "Infectología pediátrica": 2000.0,
    }
    price = precios.get(turno.especialidad, 1500.0)

    preference_data = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "title": f"Consulta: {turno.especialidad}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(price),
            }
        ],
        "payer": {
            "name": turno.nombre,
            "email": turno.email,
        },
        # NO usamos webhook todavía, solo back_urls
        "back_urls": {
            "success": f"{FRONTEND_URL}/success.html",
            "failure": f"{FRONTEND_URL}/error.html",
            "pending": f"{FRONTEND_URL}/pending.html",
        },
        "auto_return": "approved",
    }

    try:
        pref = sdk.preference().create(preference_data)
        init_point = pref["response"].get("init_point")

        if not init_point:
            raise HTTPException(
                status_code=500,
                detail="No se pudo obtener init_point de Mercado Pago",
            )

        return {"init_point": init_point}

    except Exception as e:
        print("❌ Error creando preferencia:", str(e))
        raise HTTPException(status_code=500, detail="Error con Mercado Pago")

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))   # Railway asigna PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
