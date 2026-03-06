FROM python:3.11-slim

LABEL maintainer="Cory Lawson / The Lawson Group"
LABEL description="MortgageFintechOS — 24/7 Autonomous AI Operating System"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python main.py health || exit 1

ENTRYPOINT ["python", "main.py"]
CMD ["start"]
