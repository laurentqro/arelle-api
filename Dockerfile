FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ ./app/
COPY taxonomy/ ./taxonomy/

# Expose port
EXPOSE 8000

# Run with single worker (Arelle is not thread-safe)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
