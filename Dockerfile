# Matches the playwright pip version in requirements.txt — this base image
# already has matching Chromium + all its system deps preinstalled, so no
# `playwright install` step is needed.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stream logs immediately instead of buffering — matters for `docker logs -f`
ENV PYTHONUNBUFFERED=1

CMD ["python3", "main.py"]
