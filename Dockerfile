FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Puerto expuesto para Streamlit
EXPOSE 8080

# Comando de arranque para la Nube
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
