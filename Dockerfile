FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências base
RUN pip install --no-cache-dir \
    requests \
    psutil

# torch CPU (sem CUDA — mais leve, ~800MB vs 6GB com CUDA)
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# transformers e accelerate
RUN pip install --no-cache-dir \
    transformers \
    accelerate

COPY . .

EXPOSE 8080

CMD ["python3", "cookie_ide_app.py"]
