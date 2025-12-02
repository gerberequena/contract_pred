FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de entrenamiento
COPY feature_engineering.py .
COPY train_criticality_model.py .
COPY config.yaml .

# Variables de entorno
ENV PYTHONUNBUFFERED=1

# Comando por defecto: ejecutar entrenamiento
CMD ["python", "train_criticality_model.py"]