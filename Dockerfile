# --- Build stage ---
FROM python:3.13-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Final stage ---
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy only what the app needs
COPY Map/           ./Map/
COPY app/           ./app/
COPY CreateFhir.py  .
COPY ResolveTags.py .
COPY main.py        .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

