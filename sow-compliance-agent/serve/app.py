# serve/app.py
from typing import List
import json

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import init_db, get_db
from app.models import SOW
from app.main import process_sow_record, email_chain, send_email, ALERT_EMAIL_TO

app = FastAPI(
    title="SOW Compliance Agent API",
    version="1.0.0",
    description="API para analizar SOWs, calcular riesgo y enviar alertas por email.",
)

# ----------------- Eventos de inicio -----------------
@app.on_event("startup")
def on_startup() -> None:
    """Inicializa la base de datos al arrancar la API."""
    init_db()


# ----------------- Endpoints -----------------
@app.get("/health")
def health() -> dict:
    """Endpoint de salud para verificar que el servicio está vivo."""
    return {"status": "ok"}


@app.post("/upload")
def upload_sows(
    sows: List[dict],  # lista de SOWs crudos (como vienen del CSV/JSON)
    db: Session = Depends(get_db),
) -> dict:
    """
    Recibe una lista de SOWs, los normaliza, calcula status/riesgo y
    los inserta/actualiza en la base de datos.
    Dispara correos SOLO para SOWs nuevos de alto riesgo (lógica en process_sow_record).
    """
    created = 0
    updated = 0
    sow_ids: List[str] = []

    for raw in sows:
        sow_obj, action = process_sow_record(db, raw)
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
    Devuelve todos los SOWs almacenados con su nivel de riesgo y status.
    Este endpoint alimenta el dashboard.
    """
    sows = db.query(SOW).all()
    items = []

    for sow in sows:
        items.append(
            {
                "sow_id": sow.sow_id,
                "contract_id": sow.contract_id,
                "title": sow.sow_title,
                "status": sow.status,
                "risk": sow.risk,
                "days_before_expiration": sow.days_before_expiration,
                "active_workers": sow.active_sow_workers,
                "latest_maximum_budget": sow.latest_maximum_budget,
                "currency": sow.currency,
            }
        )

    return {"total": len(items), "items": items}


@app.post("/generate-email/{sow_id}")
def generate_email(
    sow_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Genera (con el LLM) y envía un correo de alerta para un SOW específico,
    aunque ya exista en la base de datos.
    """
    sow_obj: SOW | None = db.query(SOW).filter(SOW.sow_id == sow_id).first()
    if sow_obj is None:
        raise HTTPException(status_code=404, detail="SOW no encontrado")

    sow_json = {
        "sow_id": sow_obj.sow_id,
        "sow_title": sow_obj.sow_title,
        "sow_status": sow_obj.sow_status,
        "risk": sow_obj.risk,
        "status": sow_obj.status,
        "supplier": sow_obj.supplier,
        "business_unit": sow_obj.business_unit,
        "primary_lob": sow_obj.primary_lob,
        "sow_owner": sow_obj.sow_owner,
        "start_date": sow_obj.start_date.isoformat() if sow_obj.start_date else None,
        "end_date": sow_obj.end_date.isoformat() if sow_obj.end_date else None,
        "latest_maximum_budget": sow_obj.latest_maximum_budget,
        "currency": sow_obj.currency,
    }

    # Reutilizamos la misma cadena LLM que en process_sow_record
    llm_response = email_chain.invoke({"sow_json": json.dumps(sow_json, default=str)})

    try:
        content = llm_response.content
    except AttributeError:
        content = str(llm_response)

    try:
        email_data = json.loads(content)
        subject = email_data.get("subject", f"High Risk SOW: {sow_obj.sow_id}")
        body = email_data.get("body", content)
    except json.JSONDecodeError:
        subject = f"High Risk SOW: {sow_obj.sow_id}"
        body = content

    send_email(subject, body, ALERT_EMAIL_TO)

    return {
        "message": "Email generado y enviado",
        "sow_id": sow_obj.sow_id,
        "subject": subject,
        "to": ALERT_EMAIL_TO,
    }
