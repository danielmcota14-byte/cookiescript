FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Versão leve para cloud: sem torch/transformers (use GROQ_API_KEY).
# Para modelo local: pip install -r requirements-local-ai.txt e ENABLE_LOCAL_AI=1
RUN pip install --no-cache-dir requests psutil

RUN mkdir -p data uploads memory
COPY . .

EXPOSE 8080

CMD ["python3", "cookie_ide_app.py"]
