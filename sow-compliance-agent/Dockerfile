# Dockerfile - Imagen de la API SOW Compliance Agent
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# 1) Instalar dependencias de Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copiar el código de la app
COPY app /app/app
COPY models /app/models
COPY data /app/data

# Puerto de la API
EXPOSE 8000

# 3) Comando de arranque
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
