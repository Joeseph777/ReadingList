FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data && useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["python", "run.py"]
