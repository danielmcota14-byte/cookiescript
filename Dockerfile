FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Dependências base (leves, sempre instaladas)
RUN pip install --no-cache-dir \
    websockets \
    requests \
    flask \
    fastapi \
    uvicorn \
    pillow \
    psutil

# torch + transformers são opcionais e pesados (~2GB).
# Instalar somente se a variável INSTALL_TORCH=1 for definida no build.
# No Fly.io com 4GB RAM e sem GPU, o modelo DeepSeek raramente cabe;
# o fallback para Ollama é usado automaticamente.
ARG INSTALL_TORCH=0
RUN if [ "$INSTALL_TORCH" = "1" ]; then \
      pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir transformers accelerate; \
    fi

COPY . .

EXPOSE 8080

CMD ["python3", "cookie_ide_app.py"]