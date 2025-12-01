import os
import json
import yaml
import smtplib
from email.message import EmailMessage
from datetime import date

from sqlalchemy.orm import Session
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

# Asegúrate de que estos imports funcionen con tus archivos locales
from database import init_db, get_db
from crud import create_or_update_sow



with open("config.yaml", "r") as f:
    try:
        config = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise e

for key, value in config.get("data", {}).items():
    os.environ[key] = str(value)

# Expected env vars (example)
email_setup = config.get('email', {}) # Usar un dict vacío como default

# Se cambió el modelo a 'mistral:7b'
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", email_setup.get('ALERT_EMAIL_FROM'))
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", email_setup.get('ALERT_EMAIL_TO'))
SMTP_HOST = os.getenv("SMTP_HOST", email_setup.get('SMTP_HOST'))
SMTP_PORT = int(os.getenv("SMTP_PORT", email_setup.get('SMTP_PORT', 587)))
SMTP_USER = os.getenv("SMTP_USER", ALERT_EMAIL_FROM)
SMTP_PASS = os.getenv("SMTP_PASS", email_setup.get('SMTP_PASS'))


# ---------- LangChain / Ollama setup ----------
llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=0.3,
)

email_prompt = PromptTemplate.from_template(
    """
You are an assistant that writes clear, concise email alerts.

Write an email to notify the SOW owner that a new SOW has been registered
and it is considered HIGH RISK.

Include:
- a short subject line (no "Subject:" prefix, just the text),
- a professional but friendly tone,
- a short summary of why it is high risk,
- key fields in bullet points.
- at then end of the email say "best regards, TOCC Team"

Return your response in this JSON format:

{{
  "subject": "<subject line>",
  "body": "<email body text>"
}}

SOW data (JSON):
{sow_json}
"""
)

email_chain = email_prompt | llm


# ---------- Email sending helper ----------
def send_email(subject: str, body: str, to_email: str):
    msg = EmailMessage()
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        # Esta línea ya no debería fallar con la App Password correcta
        server.login(SMTP_USER, SMTP_PASS) 
        server.send_message(msg)


# ---------- High-risk check helper ----------
def is_high_risk_or_status(risk: str | None, status: str | None) -> bool:
    """Checks if a record should trigger an alert."""
    risk_val = (risk or "").strip().lower()
    status_val = (status or "").strip().lower()
    # Enviará un correo si el riesgo es "high" O si el status es "flagged"
    return risk_val == "high" or status_val == "flagged"


# ----------------------------------------------------------------------
# ---------- Core logic for a single SOW dict (MODIFIED LOGIC) ----------
# ----------------------------------------------------------------------
def process_sow_record(db: Session, raw_sow_dict: dict):
    """
    Processes a single SOW record.
    1. Assigns default status ('flagged' or 'healthy') if status is missing.
    2. Inserts/updates the record.
    3. Sends an email if newly created and high risk/flagged.
    """
    # 1. Crear una copia mutable del diccionario de entrada
    sow_data = raw_sow_dict.copy()

    # Obtener el valor de 'risk' de manera segura
    risk_val = (sow_data.get('risk') or "").strip().lower()
    
    # 2. Lógica para asignar 'status' si no está presente en la entrada
    if 'status' not in sow_data:
        # Tu punto 1: si risk es 'high', asignar 'flagged' (y esto disparará el email)
        if risk_val == "high":
            sow_data['status'] = "flagged"
        # Tu punto 2: si no hay riesgo (o es bajo/medio), asignar 'healthy'
        else:
            sow_data['status'] = "healthy"
    
    # 3. Insertar/Actualizar el SOW en la base de datos
    sow_obj, action = create_or_update_sow(db, sow_data)

    # 4. Lógica de email: Solo cuando es recién creado Y es de alto riesgo/flagged
    if action == "created":
        if is_high_risk_or_status(sow_obj.risk, sow_obj.status):
            
            # Prepare JSON for the model
            sow_json = json.dumps(
                {
                    "sow_id": sow_obj.sow_id,
                    "sow_title": sow_obj.sow_title,
                    "sow_status": sow_obj.sow_status,
                    "risk": sow_obj.risk,
                    "status": sow_obj.status, # Esto ahora será 'flagged' o 'healthy'
                    "supplier": sow_obj.supplier,
                    "business_unit": sow_obj.business_unit,
                    "primary_lob": sow_obj.primary_lob,
                    "sow_owner": sow_obj.sow_owner,
                    "start_date": sow_obj.start_date.isoformat() if sow_obj.start_date else None,
                    "end_date": sow_obj.end_date.isoformat() if sow_obj.end_date else None,
                    "latest_maximum_budget": sow_obj.latest_maximum_budget,
                    "currency": sow_obj.currency,
                },
                default=str,
            )

            # Call Ollama via LangChain
            llm_response = email_chain.invoke({"sow_json": sow_json})

            # llm_response is a ChatMessage-like object; take its content
            try:
                content = llm_response.content
            except AttributeError:
                content = str(llm_response)

            # Parse JSON from the model output (be a bit defensive)
            try:
                # Intenta encontrar y cargar el bloque JSON
                email_data = json.loads(content) 
                subject = email_data.get("subject", f"High Risk SOW: {sow_obj.sow_id}")
                body = email_data.get("body", content)
            except json.JSONDecodeError:
                # If model didn't return perfect JSON, fallback
                subject = f"High Risk SOW: {sow_obj.sow_id}"
                body = content

            # Send the email
            send_email(subject, body, ALERT_EMAIL_TO)

            print(f"Email sent for HIGH RISK SOW {sow_obj.sow_id}")
        else:
            print(f"New SOW created (not high risk): {sow_obj.sow_id}")
    else:
        print(f"SOW updated: {sow_obj.sow_id}")

    return sow_obj, action


# ---------- Example dataset (pretend this came as a JSON file) ----------
dataset = [
    {
        "SOW ID": "SOW-2024-0022",
        "# Days before expiration": -6,
        "SOW Status": "Expired",
        "SOW title": "Software Development Services",
        "Contract Id": "CNT-2024-0022",
        "Active SOW workers": 1,
        "Start Date": "2025-05-27",
        "End date": "2025-11-23",
        "Latest maximum budget": 366656,
        "currency": "USD",
        "supplier": "Cognizant",
        "Business Unit": "Finance",
        "Primary LOB": "Quality Assurance",
        "SOW owner": "John Martinez",
        "risk": "high",       
    },
    {
        "SOW ID": "SOW-2024-0023",
        "# Days before expiration": 30,
        "SOW Status": "Active",
        "SOW title": "Data Migration",
        "Contract Id": "CNT-2024-0023",
        "Active SOW workers": 3,
        "Start Date": "2025-01-01",
        "End date": "2025-12-31",
        "Latest maximum budget": 120000,
        "currency": "USD",
        "supplier": "Infosys",
        "Business Unit": "IT",
        "Primary LOB": "Cloud",
        "SOW owner": "Alice Smith",
        "risk": "low",         
    },
    {
        "SOW ID": "SOW-2024-0024",
        "# Days before expiration": 30,
        "SOW Status": "Active",
        "SOW title": "Data Analytics",
        "Contract Id": "CNT-2024-0024",
        "Active SOW workers": 3,
        "Start Date": "2025-01-01",
        "End date": "2025-12-31",
        "Latest maximum budget": 120000,
        "currency": "USD",
        "supplier": "Infosys",
        "Business Unit": "IT",
        "Primary LOB": "Cloud",
        "SOW owner": "Bob Johnson",
        "risk": "high",       
        "status": "healthy",   
    },
]

# ---------- Main entry point ----------
def main():
    # 1) Create tables
    init_db()

    # 2) Use a DB session
    db_gen = get_db()
    db = next(db_gen)
    try:
        for raw_sow in dataset:
            sow_obj, action = process_sow_record(db, raw_sow)
            print(
                f"{action=}, id={sow_obj.id}, sow_id={sow_obj.sow_id}, "
                f"risk={sow_obj.risk}, status={sow_obj.status}"
            )
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    main()