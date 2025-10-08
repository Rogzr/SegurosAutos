# Production image for Railway with WeasyPrint system dependencies
FROM python:3.13-slim

# Install system libraries required by WeasyPrint (cairo, pango, gdk-pixbuf, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    libglib2.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run under uvicorn on the port provided by Railway ($PORT)
ENV PYTHONUNBUFFERED=1
CMD sh -c "uvicorn app:asgi_app --host 0.0.0.0 --port ${PORT:-8080}"
