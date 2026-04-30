FROM python:3.11-slim

LABEL maintainer="Zyphraxis Team"
LABEL description="Zyphraxis Treatment Planning API + UI"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs data reports

EXPOSE 8000
EXPOSE 8501

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
