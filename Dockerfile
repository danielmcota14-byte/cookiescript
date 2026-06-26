FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Instala dependências sem torch/transformers (muito pesados pra cloud)
# Se quiser IA local via Ollama, ela se conecta externamente
RUN pip install --no-cache-dir \
    websockets \
    requests \
    flask \
    fastapi \
    uvicorn \
    pillow \
    psutil

COPY . .

EXPOSE 8080

CMD ["python3", "cookie_ide_app.py"]
