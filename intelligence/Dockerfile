FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY intelligence/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY intelligence/bionexus_intelligence /app/bionexus_intelligence
COPY ops /app/ops

ENV PYTHONPATH=/app

CMD ["python", "-m", "bionexus_intelligence.rest_api"]
