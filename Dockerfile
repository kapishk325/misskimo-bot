FROM python:3.12-slim

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root system user for secure container execution
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy application source code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "main.py"]
