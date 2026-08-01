FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEQUENTIAL_WRAPPER_HOST=0.0.0.0 \
    SEQUENTIAL_WRAPPER_PORT=38001 \
    SEQUENTIAL_WRAPPER_PATH=/mcp

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py ./

EXPOSE 38001
CMD ["python", "server.py"]
