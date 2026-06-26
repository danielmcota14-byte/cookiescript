FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir \
    websockets \
    requests \
    flask \
    fastapi \
    uvicorn \
    pillow \
    psutil && \
    pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    transformers \
    bitsandbytes \
    accelerate

COPY . .

EXPOSE 8080

CMD ["python3", "cookie_ide_app.py"]