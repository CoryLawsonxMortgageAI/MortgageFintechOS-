FROM python:3.11-slim

LABEL maintainer="Cory Lawson / The Lawson Group"
LABEL description="MortgageFintechOS — 24/7 Autonomous AI Operating System"

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PORT=8080

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/healthz || exit 1

ENTRYPOINT ["python", "main.py"]
CMD ["start", "--host", "0.0.0.0"]
