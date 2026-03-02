# Imagen base oficial de Python
FROM python:3.11-slim

# Establece directorio de trabajo
WORKDIR /app

# Copia dependencias y código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src
COPY migrations/ ./migrations

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expone el puerto que Flask usará
EXPOSE 5000

# Comando para ejecutar la app
CMD ["flask", "--app", "src/manage.py", "run", "--host=0.0.0.0"]
