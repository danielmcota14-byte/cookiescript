FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    requests \
    psutil

COPY . .

EXPOSE 8080

CMD ["python3", "cookie_ide_app.py"]
