# Lightweight base image (under 300MB requirement)
FROM python:3.12-alpine

# Create non-root user (security requirement)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Switch to non-root user
USER appuser

EXPOSE 3000

# Use gunicorn (production server, not flask dev server)
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "2", "main:app"]
