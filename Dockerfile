FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bridge.py server.py ./
RUN useradd --create-home --uid 10001 relay && mkdir /data && chown relay:relay /data
USER relay
ENV STATE_DIR=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "server.py"]
