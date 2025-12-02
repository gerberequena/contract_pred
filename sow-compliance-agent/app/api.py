"""
api.py
======

Este archivo expone la API REST del SOW Compliance Agent usando FastAPI.

Se apoya en la lógica que ya se tiene en:
- app/main.py   → process_sow_record, email_chain, send_email, config de correo
- app/database.py → init_db, get_db (manejo de SQLite)
- app/models.py → modelo ORM SOW
"""

from typing import List

import json

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

# Imports del paquete local "app"
from .database import init_db, get_db
from .models import SOW
from .main import (
    process_sow_record,  # lógica que guarda/actualiza y dispara correo si aplica
    email_chain,         # cadena de LangChain + Ollama ya configurada
    send_email,          # helper para enviar correo vía SMTP
    ALERT_EMAIL_TO,      # correo de destino configurado en config.yaml / env
)

# ---------------------------------------------------------------------------
# Creación de la aplicación FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SOW Compliance Agent API",
    version="1.0.0",
    description=(
        "API para analizar SOWs, calcular riesgo, persistirlos en base de datos "
        "y disparar alertas automáticas por correo."
    ),
)


# ---------------------------------------------------------------------------
# Eventos de ciclo de vida
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    """
    Evento que se ejecuta cuando arranca la API.

    Aquí inicializamos la base de datos (crea tablas si no existen).
    """
    init_db()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    """
    Endpoint de salud simple.

    Útil para chequeos de Docker / Kubernetes / monitoreo.
    """
    return {"status": "ok"}


@app.post("/upload")
def upload_sows(
    sows: List[dict],          # lista de registros SOW crudos en formato JSON
    db: Session = Depends(get_db),
) -> dict:
    """
    Recibe un listado de SOWs en formato JSON (como vienen del CSV o de otro sistema),
    y para cada uno:

    1. Llama a `process_sow_record` (app/main.py), que:
       - normaliza risk/status,
       - inserta/actualiza en la tabla SOW,
       - si es NUEVO y de alto riesgo/flagged, llama al LLM y envía correo.

    2. Cuenta cuántos fueron creados vs actualizados.

    Ejemplo de body (lista con 1 elemento):

    [
      {
        "SOW ID": "SOW-2024-9999",
        "# Days before expiration": -5,
        "SOW Status": "Active",
        "SOW title": "Test Contract",
        "Contract Id": "CNT-TEST-001",
        "Active SOW workers": 3,
        "Start Date": "2025-01-01",
        "End date": "2025-06-01",
        "Latest maximum budget": 100000,
        "currency": "USD",
        "supplier": "Test Supplier",
        "Business Unit": "IT",
        "Primary LOB": "Software",
        "SOW owner": "John Doe",
        "risk": "high"
      }
    ]
    """
    created = 0
    updated = 0
    sow_ids: List[str] = []

    for raw_sow in sows:
        # process_sow_record devuelve (objeto_SOW, "created" | "updated")
        sow_obj, action = process_sow_record(db, raw_sow)
        sow_ids.append(sow_obj.sow_id)

        if action == "created":
            created += 1
        else:
            updated += 1

    return {
        "message": "Dataset procesado correctamente",
        "total_received": len(sows),
        "created": created,
        "updated": updated,
        "sow_ids": sow_ids,
    }


@app.get("/analyze")
def analyze_sows(db: Session = Depends(get_db)) -> dict:
    """
    Devuelve todos los SOWs almacenados con su nivel de riesgo y campos clave.

    Este endpoint sirve como fuente de datos para el dashboard.
    """
    sows = db.query(SOW).all()

    items: List[dict] = []
    for sow in sows:
        items.append(
            {
                "sow_id": sow.sow_id,
                "contract_id": sow.contract_id,
                "title": sow.sow_title,
                "status": sow.status,                    # flagged / healthy
                "risk": sow.risk,                        # high / medium / low
                "days_before_expiration": sow.days_before_expiration,
                "active_workers": sow.active_sow_workers,
                "latest_maximum_budget": sow.latest_maximum_budget,
                "currency": sow.currency,
                "supplier": sow.supplier,
                "business_unit": sow.business_unit,
                "primary_lob": sow.primary_lob,
                "sow_owner": sow.sow_owner,
            }
        )

    return {
        "total": len(items),
        "items": items,
    }


@app.post("/generate-email/{sow_id}")
def generate_email(
    sow_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Genera (con el LLM) y envía un correo de alerta para un SOW específico,
    aunque ya exista o no sea "nuevo".

    Flujo:

    1. Busca el SOW en la base de datos por `sow_id`.
    2. Construye un JSON con los campos relevantes.
    3. Llama a `email_chain.invoke({"sow_json": sow_json})`.
    4. Intenta parsear la respuesta como JSON:
       {
         "subject": "...",
         "body": "..."
       }
       Si el modelo no devuelve JSON perfecto, usa el texto crudo.
    5. Llama a `send_email(subject, body, ALERT_EMAIL_TO)`.
    """
    sow_obj: SOW | None = db.query(SOW).filter(SOW.sow_id == sow_id).first()
    if sow_obj is None:
        raise HTTPException(status_code=404, detail="SOW no encontrado")

    # Construimos un diccionario con los datos del SOW
    sow_payload = {
        "sow_id": sow_obj.sow_id,
        "sow_title": sow_obj.sow_title,
        "sow_status": sow_obj.sow_status,
        "risk": sow_obj.risk,
        "status": sow_obj.status,  # flagged / healthy
        "supplier": sow_obj.supplier,
        "business_unit": sow_obj.business_unit,
        "primary_lob": sow_obj.primary_lob,
        "sow_owner": sow_obj.sow_owner,
        "start_date": sow_obj.start_date.isoformat() if sow_obj.start_date else None,
        "end_date": sow_obj.end_date.isoformat() if sow_obj.end_date else None,
        "days_before_expiration": sow_obj.days_before_expiration,
        "active_sow_workers": sow_obj.active_sow_workers,
        "latest_maximum_budget": sow_obj.latest_maximum_budget,
        "currency": sow_obj.currency,
    }

    # Convertimos el dict a JSON string para pasarlo al prompt
    sow_json = json.dumps(sow_payload, default=str)

    # Invocamos la cadena del LLM ya configurada en main.py
    llm_response = email_chain.invoke({"sow_json": sow_json})

    # Obtenemos el contenido (algunos modelos devuelven .content, otros un string)
    try:
        content = llm_response.content
    except AttributeError:
        content = str(llm_response)

    # Intentamos parsear la respuesta como JSON con campos "subject" y "body"
    try:
        email_data = json.loads(content)
        subject = email_data.get(
            "subject",
            f"[SOW Compliance] High Risk SOW {sow_obj.sow_id}",
        )
        body = email_data.get("body", content)
    except json.JSONDecodeError:
        # Si el modelo no devolvió JSON bien formado, usamos texto completo
        subject = f"[SOW Compliance] High Risk SOW {sow_obj.sow_id}"
        body = content

    # Enviar el correo usando la función helper de main.py
    send_email(subject=subject, body=body, to_email=ALERT_EMAIL_TO)

    return {
        "message": "Email generado y enviado",
        "sow_id": sow_obj.sow_id,
        "subject": subject,
        "to": ALERT_EMAIL_TO,
    }
