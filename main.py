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

if not MP_ACCESS_TOKEN:
    raise RuntimeError("MP_ACCESS_TOKEN no está configurado en las variables de entorno.")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ─────────────────────────────────────────────
# App FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="Mediturnos Backend",
    version="1.0.0",
)

# CORS (de momento, abierto)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # luego se puede restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Esquema de datos que llega desde el frontend
# ─────────────────────────────────────────────
class TurnoIn(BaseModel):
    nombre: str
    email: EmailStr
    especialidad: str
    fecha: str   # "2025-03-10"
    hora: str    # "17:30"
    motivo: str

class PreferenciaOut(BaseModel):
    init_point: str

# ─────────────────────────────────────────────
# Rutas
# ─────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "service": "mediturnos-backend"}

@app.post("/api/crear-preferencia", response_model=PreferenciaOut)
def crear_preferencia(turno: TurnoIn):
    """
    Crea una preferencia de pago en Mercado Pago para el turno enviado
    y devuelve la URL (init_point) donde el paciente paga.
    """

    # Precio fijo de prueba, luego lo cambiamos
    precio = 100.0

    preference_data = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "title": f"Consulta {turno.especialidad}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": precio,
            }
        ],
        "payer": {
            "name": turno.nombre,
            "email": turno.email,
        },
        "statement_descriptor": "MEDITURNOS",
        "back_urls": {
            # Por ahora, URLs de prueba (luego las apuntamos a tu frontend)
            "success": "https://example.com/success",
            "failure": "https://example.com/failure",
            "pending": "https://example.com/pending",
        },
        "auto_return": "approved",
    }

    try:
        pref = sdk.preference().create(preference_data)
        init_point = pref["response"].get("init_point")

        if not init_point:
            raise HTTPException(status_code=500, detail="No se pudo obtener init_point de Mercado Pago.")

        return PreferenciaOut(init_point=init_point)

    except Exception as e:
        # Para debug rápido
        print("Error Mercado Pago:", str(e))
        raise HTTPException(status_code=500, detail=f"Error al crear preferencia: {str(e)}")
