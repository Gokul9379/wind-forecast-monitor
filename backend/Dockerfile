FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 1) create the data snapshot from Elexon if it does not exist yet
# 2) start the API
CMD ["sh", "-c", "python -m scripts.fetch_data --if-missing; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
